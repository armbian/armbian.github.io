#!/usr/bin/env python3
"""Render a quarterly digest into a docs.armbian.com release page.

Consumes the artefacts the "Reporting: Release summary" workflow already
produces (the AI narrative and the merged-PR TSV) plus two label/diff-driven
inputs, and writes ``docs/releases/<version>.md`` for armbian/documentation.

Nothing here invents content: every line traces back to the digest body, PR
metadata, or a labelled issue. Sections without qualifying entries are omitted
rather than emitted empty.
"""

import argparse
import csv
import os
import re
import sys
from collections import OrderedDict

# Support tiers, keyed by the config/boards/<board>.<ext> suffix that armbian
# uses to encode them. A rename between two of these is a tier transition.
TIERS = {
    "conf": "Standard support",
    "csc": "CSC",
    "eos": "EOS",
    "tvb": "TV box",
    "wip": "WIP",
}

# Group order is the reading order on the page.
GROUPS = [
    "Boards",
    "Kernel and U-Boot",
    "Desktop",
    "Build framework and CI",
    "Tooling",
    "Other",
]

RE_DESKTOP = re.compile(
    r"\b(desktops?|xfce|gnome|kde|plasma|neon|cinnamon|mate|i3(-wm)?|xmonad|"
    r"enlightenment|budgie|lxde|lxqt|wayland|xorg|lightdm|sddm|gdm|greeter|"
    r"chromium|firefox|appgroups?|desktop_[a-z_]+)\b"
)

# Explicit kernel / bootloader vocabulary. Deliberately narrow: anything that
# also reads as build-framework work is left to the later, weaker rules.
RE_KERNEL = re.compile(
    r"\b(kernels?|u-?boot|spl|atf|trusted[- ]firmware|edk2|bootloaders?|"
    r"extlinux|bootscript|patch|patches|patchset|patchsets|dts|dtb|dtsi|dtso|"
    r"device[- ]?tree|defconfig|overlays?|mainline|bleedingedge|dkms|"
    r"\d+\.\d+\.y|linux[- ]\d+\.\d+|config_[a-z0-9_]+|compil(e|es|ed|ing|ation)|modules?)\b"
)

# 'Update odroidxu4-current to 6.6.139' carries no kernel noun but is plainly a
# kernel bump: a move verb plus either a version triple or a branch name.
RE_KERNEL_BUMP = re.compile(
    r"\b(bump|bumps|bumped|upgrade|upgrades|upgraded|update|updates|updated|"
    r"switch|switches|switched|move|moves|moved|rebase|rebased)\b"
    r"(?=.*(\b\d+\.\d+(\.\d+)?\b|"
    r"\b(current|edge|legacy|vendor|bleedingedge)\b))"
)

# SoC part numbers. Boards are matched by real config/boards slugs; these cover
# the titles that name the chip instead of the board.
RE_SOC = re.compile(
    r"\b(rk3[0-9]{3}[a-z]?[0-9]?|rv11[0-9]{2}|px30|a64|a20|a133|h[0-9]{1,3}|"
    r"h6(16|18)|s9[0-9]{3}[a-z]?|imx[0-9]{1,2}[a-z]*|sm[0-9]{4}|qrb[0-9]{4}|"
    r"bcm2[0-9]{3}|jh7110|d1|k1|th1520|meson-[a-z0-9]+|sun[0-9]+i)\b"
)

RE_BOARD_GENERIC = re.compile(
    r"\b(boards?|board[- ]configs?|sbc|tv[- ]?box(es)?|"
    r"support[- ]tier|csc|eos|tvb)\b"
)

# Tightened: bare 'build', 'image', 'test' and 'apt' appear across every group
# and are not evidence on their own.
RE_CI = re.compile(
    r"\b(ci|cd|workflows?|github[- ]actions?|runners?|pipelines?|"
    r"build[- ](framework|system|script|matrix|host)|makefiles?|"
    r"shellcheck|linter|linting|unit[- ]tests?|artifacts?|"
    r"debootstrap|chroot|qemu|ccache|release[- ]targets?|nightl(y|ies)|"
    r"repositor(y|ies)|mirrors?|torrents?|dependabot|codeowners)\b"
)

RE_TOOLING = re.compile(
    r"\b(armbian-config|configng|armbian-install|armbian-software|imager|"
    r"docs?|documentation|readme|website|motd|cli|installer|redirector|"
    r"router|sdk|changelog)\b"
)

# Conventional-commit types carry no area information. Strip them so the next
# colon-delimited token gets a chance to act as the real prefix.
TRANSPARENT_PREFIXES = {
    "feat", "feature", "fix", "bugfix", "hotfix", "refactor", "chore", "style",
    "perf", "enh", "enhancement", "revert", "wip", "hack", "misc", "cleanup",
    "temp", "tmp", "rfc", "draft",
}

# Prefixes that name an area outright.
PREFIX_GROUPS = {
    "Build framework and CI": {
        "ci", "cd", "gha", "gh", "workflow", "workflows", "action", "actions",
        "runner", "runners", "runner-cleanup", "nightly", "targets",
        "release-targets", "docker", "deps", "dependencies", "maint",
        "maintenance", "test", "tests", "unit-tests", "lint", "shellcheck",
        "repo", "repository", "extension", "extensions", "rootfs", "packaging",
    },
    "Desktop": {
        "desktop", "desktops", "xfce", "gnome", "kde", "plasma", "cinnamon",
        "mate", "i3", "i3-wm", "xmonad", "budgie", "enlightenment", "lxde",
        "lxqt", "postinst",
    },
    "Kernel and U-Boot": {
        "kernel", "kernels", "patch", "patches", "u-boot", "uboot", "dt", "dts",
        "arm64", "arm", "armhf", "riscv", "riscv64", "driver", "drivers",
        "firmware", "mainline", "arch", "atf", "spl",
    },
    "Tooling": {
        "docs", "doc", "documentation", "readme", "motd", "cli", "config",
        "armbian-config", "imager", "website", "sdk", "script", "scripts",
        "software",
    },
}

# Compound prefixes such as 'json-generation' or 'generate-armbian-images-json'
# are CI plumbing; match them on any component rather than in full.
RE_PREFIX_CI_PART = re.compile(
    r"(^|-)(ci|cd|gha|workflow|action|runner|nightly|target|targets|json|"
    r"generate|generation|release|repo|docker|deps|dispatch|sync)(-|$)"
)

# Repos whose entire output belongs to one group regardless of title.
REPO_FIXED = {
    "armbian/linux-rockchip": "Kernel and U-Boot",
    "armbian/rkbin": "Kernel and U-Boot",
    "armbian/firmware": "Kernel and U-Boot",
    "armbian/qcombin": "Kernel and U-Boot",
}

# Single-purpose repos supply a fallback when no title rule fires. armbian/build
# and armbian/armbian.github.io are deliberately absent: they span every group,
# so an unmatched title there is genuinely unclassified and belongs in "Other".
REPO_FALLBACK = {
    "armbian/os": "Build framework and CI",
    "armbian/actions": "Build framework and CI",
    "armbian/docker-armbian-build": "Build framework and CI",
    "armbian/sdk": "Build framework and CI",
    "armbian/ci": "Build framework and CI",
    "armbian/configng": "Tooling",
    "armbian/imager": "Tooling",
    "armbian/documentation": "Tooling",
    "armbian/website": "Tooling",
    "armbian/armbian-router": "Tooling",
}


def load_vocabulary(build_tree):
    """Read the real board slugs and kernel family names out of an armbian/build tree.

    Deriving the vocabulary from the tree beats a hand-written keyword list: it
    stays correct as boards come and go, and it keeps the classifier from
    guessing at names it has never seen. Four sources between them cover every
    name Armbian uses in a PR title:

      config/boards/<slug>.<tier>            board slugs
      config/sources/families/<family>.conf  concrete kernel families
      config/sources/families/include/*.inc  umbrella families (sunxi, meson64)
      patch/{kernel,u-boot}/<dir>            patch-set names (sunxi, rockchip64)

    Names are normalised to bare alphanumerics so 'Odroid-M2' and 'NanoPC T6'
    both resolve to the slugs odroidm2 and nanopct6.
    """
    boards, families = set(), set()
    if not build_tree or not os.path.isdir(build_tree):
        return boards, families

    def listdir(*parts):
        path = os.path.join(build_tree, *parts)
        return os.listdir(path) if os.path.isdir(path) else []

    for entry in listdir("config", "boards"):
        stem, dot, ext = entry.rpartition(".")
        if dot and ext in TIERS:
            boards.add(normalise(stem))

    for entry in listdir("config", "sources", "families"):
        if entry.endswith(".conf"):
            families.add(normalise(entry[: -len(".conf")]))

    for entry in listdir("config", "sources", "families", "include"):
        if entry.endswith(".inc"):
            families.add(normalise(re.sub(r"_common$", "", entry[: -len(".inc")])))

    for sub in ("kernel", "u-boot"):
        for entry in listdir("patch", sub):
            name = re.sub(r"^u-boot-", "", entry)
            # Trim branch and version suffixes: sunxi-6.18, rockchip64-current.
            name = re.sub(
                r"-(current|edge|legacy|vendor|bleedingedge|v?\d+(\.\d+)*.*)$",
                "",
                name,
            )
            families.add(normalise(name))

    # patch/u-boot also holds bare version directories (v2026.04); they are
    # release tags, not family names, and would match kernel-bump titles.
    noise = {"", "archive", "integrate", "legacy", "crustfirmware", "include"}
    is_version = re.compile(r"^v?\d").match
    return (
        {b for b in boards if b and b not in noise},
        {f for f in families if f and f not in noise and not is_version(f)},
    )


def normalise(text):
    return re.sub(r"[^a-z0-9]", "", text.lower())


def title_prefix(title):
    """The colon-delimited area prefix, with conventional-commit types stripped.

    'fix(sunxi-6.18): drop r-spi backport' -> 'sunxi-6.18'
    'feat: add ZFS pool import'            -> '' (no area named)
    """
    remainder = title
    for _ in range(3):
        head, sep, tail = remainder.partition(":")
        if not sep or len(head) > 48:
            return ""
        head = head.strip().lower()
        scope = re.match(r"^([a-z0-9_.+-]+)\(([^)]+)\)$", head)
        if scope:
            if scope.group(1) in TRANSPARENT_PREFIXES:
                return scope.group(2).strip().lower()
            return scope.group(1)
        if head in TRANSPARENT_PREFIXES:
            remainder = tail
            continue
        return head
    return ""


def prefix_parts(prefix):
    """Split 'desktops/mate' or 'rockchip64-6.18' into usable identifiers."""
    parts = set()
    for chunk in re.split(r"[,/ ]+", prefix):
        chunk = chunk.strip()
        if not chunk:
            continue
        parts.add(chunk)
        # Strip a trailing kernel version, e.g. sunxi-6.18 -> sunxi.
        parts.add(re.sub(r"-\d+(\.\d+)*$", "", chunk))
    return {p for p in parts if p}


def names_a_board(title, boards, families):
    """True when the title names a real board slug or kernel family.

    Candidates are runs of one to four consecutive words joined without
    separators, so multi-word board names in prose ('Add NanoPC T6 plus image')
    match the same slug as the hyphenated form. Four characters minimum keeps
    short family names such as 'd1' from matching incidental text.
    """
    words = [normalise(w) for w in re.split(r"[\s/,.()\[\]:;_`'\"-]+", title)]
    words = [w for w in words if w]
    vocabulary = boards | families
    for i in range(len(words)):
        candidate = ""
        for j in range(i, min(i + 4, len(words))):
            candidate += words[j]
            if len(candidate) >= 4 and candidate in vocabulary:
                return True
    return False


def repo_fixed_group(repo):
    """Kernel-tree, firmware-blob and out-of-tree driver repos, by pattern."""
    if repo in REPO_FIXED:
        return REPO_FIXED[repo]
    name = repo.split("/", 1)[-1].lower()
    if name.startswith(("linux-", "wifi-", "rtl", "rtw")) or name.endswith("-dkms"):
        return "Kernel and U-Boot"
    return None


def classify(title, repo, boards, families):
    """Assign one change to a group, or to 'Other' when nothing is conclusive.

    Rules run strongest-evidence first: repo identity, then an explicit area
    prefix, then distinctive vocabulary, then a real board name, then the weaker
    generic vocabularies. Titles that survive all of that are not guessed at.
    """
    fixed = repo_fixed_group(repo)
    if fixed:
        return fixed

    low = title.lower()
    parts = prefix_parts(title_prefix(title))

    for group, prefixes in PREFIX_GROUPS.items():
        if parts & prefixes:
            return group
    if any(RE_PREFIX_CI_PART.search(p) for p in parts):
        return "Build framework and CI"

    if RE_DESKTOP.search(low):
        return "Desktop"
    if RE_KERNEL.search(low) or RE_KERNEL_BUMP.search(low):
        return "Kernel and U-Boot"
    if names_a_board(title, boards, families) or RE_SOC.search(low):
        return "Boards"
    if RE_BOARD_GENERIC.search(low):
        return "Boards"
    if RE_CI.search(low):
        return "Build framework and CI"
    if RE_TOOLING.search(low):
        return "Tooling"
    return REPO_FALLBACK.get(repo, "Other")


def read_digest(path):
    rows = []
    if not path or not os.path.exists(path):
        return rows
    with open(path, newline="", encoding="utf-8") as fh:
        for rec in csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE):
            if len(rec) < 5:
                continue
            title, author, repo, number, url = (c.strip() for c in rec[:5])
            labels = [l.strip().lower() for l in rec[5].split(",")] if len(rec) > 5 else []
            rows.append(
                {
                    "title": title.rstrip("."),
                    "author": author,
                    "repo": repo,
                    "number": number,
                    "url": url,
                    "labels": [l for l in labels if l],
                }
            )
    return rows


def read_tsv(path, fields):
    rows = []
    if not path or not os.path.exists(path):
        return rows
    with open(path, newline="", encoding="utf-8") as fh:
        for rec in csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE):
            if len(rec) < len(fields):
                continue
            rows.append(dict(zip(fields, (c.strip() for c in rec))))
    return rows


def clean_intro(text):
    """Strip the GitHub-release furniture from the narrative body.

    The digest body carries a cover image, a trailing hashtag line and a blog
    subscribe badge. None of that belongs on a docs page, and the hashtag line
    is actively harmful: Python-Markdown does not require a space after the
    hash, so '#Armbian #EmbeddedLinux ...' would render as an <h1>.

    Also tolerates being handed a whole release body rather than the narrative
    alone, so the script can be re-run against a published release.
    """
    text = text.split("\n## Changes\n", 1)[0]

    lines = text.strip().splitlines()
    # Leading cover image.
    while lines and re.match(r"^!\[[^\]]*\]\([^)]*\)\s*$", lines[0]):
        lines.pop(0)
        while lines and not lines[0].strip():
            lines.pop(0)

    kept = []
    for line in lines:
        stripped = line.strip()
        # Trailing hashtag line, e.g. '#Armbian #EmbeddedLinux #SBC'.
        if stripped and re.fullmatch(r"(#[A-Za-z0-9_]+\s*)+", stripped):
            continue
        # Blog subscribe badge and its horizontal rule.
        if stripped.startswith(("<a href=", "<img src=", "</a>", "<p>Stay up to date")):
            continue
        kept.append(line)

    while kept and (not kept[-1].strip() or kept[-1].strip() == "---"):
        kept.pop()
    return "\n".join(kept).strip()


def entry_line(row):
    return "* {title}. by @{author} in [{repo}#{number}]({url})".format(**row)


def build_groups(rows, boards, families):
    grouped = OrderedDict((g, []) for g in GROUPS)
    for row in rows:
        grouped[classify(row["title"], row["repo"], boards, families)].append(row)
    for entries in grouped.values():
        entries.sort(key=lambda r: r["title"].lower())
    return OrderedDict((g, e) for g, e in grouped.items() if e)


def fallback_description(version, date_human, grouped, total):
    """Deterministic stand-in when the AI-written description is unavailable.

    Grows or trims the theme list until the result lands inside the 140-155
    character window the front matter requires.
    """
    themes = [g.lower() for g in grouped if g != "Other"]
    for count in (3, 2, 4, 1, 5):
        picked = themes[:count]
        if not picked:
            continue
        joined = (
            ", ".join(picked[:-1]) + " and " + picked[-1]
            if len(picked) > 1
            else picked[0]
        )
        text = (
            "Armbian {v} release notes, published {d}: {n} merged changes "
            "spanning {t} across the Armbian project.".format(
                v=version, d=date_human, n=total, t=joined
            )
        )
        text = " ".join(text.split())
        if 140 <= len(text) <= 155:
            return text
    return None


def check_description(text):
    """Front-matter descriptions must be a single unique line of 140-155 chars."""
    text = " ".join(text.split())
    if not 140 <= len(text) <= 155:
        return None
    if "Official documentation for Armbian OS" in text:
        return None
    return text


def yaml_quote(text):
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def render(version, date_human, intro, description, grouped, board_changes,
           breaking, known_issues):
    out = []
    out.append("---")
    out.append("title: Armbian {}".format(version))
    out.append("description: {}".format(yaml_quote(description)))
    out.append("---")
    out.append("")
    out.append("# Armbian {}".format(version))
    out.append("")
    out.append("*Released {}*".format(date_human))
    out.append("")
    if intro:
        out.append(intro.strip())
        out.append("")

    if board_changes:
        out.append("## Board status changes")
        out.append("")
        for change in board_changes:
            line = "* {board}: {old} &rarr; {new}".format(**change)
            if change.get("url"):
                line += " ([{ref}]({url}))".format(**change)
            out.append(line)
        out.append("")

    if breaking:
        out.append("## Breaking changes / actions required")
        out.append("")
        for row in breaking:
            out.append(entry_line(row))
        out.append("")

    if known_issues:
        out.append("## Known issues")
        out.append("")
        for issue in known_issues:
            out.append("* {title} ([{ref}]({url}))".format(**issue))
        out.append("")

    if grouped:
        total = sum(len(v) for v in grouped.values())
        out.append("## All changes")
        out.append("")
        out.append('??? abstract "{} merged pull requests in this release"'.format(total))
        out.append("")
        for group, entries in grouped.items():
            out.append("    ### {}".format(group))
            out.append("")
            for row in entries:
                out.append("    " + entry_line(row))
            out.append("")

    while out and out[-1] == "":
        out.pop()
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--version", required=True, help="release version, e.g. 26.5.1")
    ap.add_argument("--date", required=True, help="release date, e.g. '29 May 2026'")
    ap.add_argument("--intro", help="file holding the narrative body")
    ap.add_argument("--digest", required=True, help="merged-PR TSV")
    ap.add_argument("--board-changes", help="TSV: board, old ext, new ext, ref, url")
    ap.add_argument("--known-issues", help="TSV: title, ref, url")
    ap.add_argument("--description", help="file holding the front-matter description")
    ap.add_argument("--build-tree", help="armbian/build checkout, for board and family names")
    ap.add_argument("--out", required=True, help="output markdown path")
    args = ap.parse_args()

    boards, families = load_vocabulary(args.build_tree)
    rows = read_digest(args.digest)
    grouped = build_groups(rows, boards, families)

    # 'Breaking change' already exists in armbian/build and armbian/configng;
    # 'user-visible' is the newer opt-in label. Match both, case-insensitively.
    breaking_labels = {"breaking", "breaking change", "user-visible", "user visible"}
    breaking = sorted(
        (r for r in rows if breaking_labels & set(r["labels"])),
        key=lambda r: r["title"].lower(),
    )

    board_changes = []
    for rec in read_tsv(args.board_changes, ["board", "old", "new", "ref", "url"]):
        board_changes.append(
            {
                "board": rec["board"],
                "old": TIERS.get(rec["old"], rec["old"]),
                "new": TIERS.get(rec["new"], rec["new"]),
                "ref": rec.get("ref", ""),
                "url": rec.get("url", ""),
            }
        )
    board_changes.sort(key=lambda c: c["board"].lower())

    known_issues = read_tsv(args.known_issues, ["title", "ref", "url"])
    known_issues.sort(key=lambda i: i["title"].lower())

    intro = ""
    if args.intro and os.path.exists(args.intro):
        with open(args.intro, encoding="utf-8") as fh:
            intro = clean_intro(fh.read())

    description = None
    if args.description and os.path.exists(args.description):
        with open(args.description, encoding="utf-8") as fh:
            description = check_description(fh.read())
    if not description:
        generated = fallback_description(args.version, args.date, grouped, len(rows))
        description = check_description(generated) if generated else None
    if not description:
        # Last resort. Still unique per release, and padded with a fixed clause
        # rather than filler so it stays readable in a search result.
        base = " ".join(
            ("Armbian {} release notes, published {}: merged changes across "
             "boards, kernels, desktops, the build framework and Armbian "
             "tooling.").format(args.version, args.date).split()
        )
        # Whole-sentence fillers, shortest first, so the punctuation survives
        # and a short version or date string still reaches the 140 minimum this
        # branch exists to guarantee.
        for filler in (
            "",
            " Full list below.",
            " See the full list below.",
            " See the full change list below.",
            " See the full change list for this release below.",
        ):
            candidate = base + filler
            if 140 <= len(candidate) <= 155:
                base = candidate
                break
        else:
            if len(base) > 155:
                base = base[:155].rsplit(" ", 1)[0]
        description = base

    page = render(
        args.version,
        args.date,
        intro,
        description,
        grouped,
        board_changes,
        breaking,
        known_issues,
    )

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(page)

    print("wrote {} ({} changes, {} groups)".format(args.out, len(rows), len(grouped)))
    for group, entries in grouped.items():
        print("  {:<24} {}".format(group, len(entries)))
    print("  board status changes: {}".format(len(board_changes)))
    print("  breaking / user-visible: {}".format(len(breaking)))
    print("  known issues: {}".format(len(known_issues)))
    print("  description ({} chars): {}".format(len(description), description))
    return 0


if __name__ == "__main__":
    sys.exit(main())
