#!/usr/bin/env python3
"""Refresh the live blocks in the Armbian organisation profile READMEs.

A block is the text between two markers:

    <!-- auto:NAME -->
    ...generated...
    <!-- /auto:NAME -->

Text outside the markers is hand-written and stays untouched. Each file holds
only the blocks it wants, so one script serves the public profile
(armbian/.github) and the member profile (armbian/.github-private).

Blocks:
  public-status  latest stable release, next release, board counts (public)
  release        next release, due date, open milestone items (members)
  help           good-first-issue / help-wanted counts, boards without a maintainer
  teams          who to ask: the visible organisation teams

A block whose data source fails keeps its previous content, so one API error
never blanks the page.
"""

import argparse
import calendar
import difflib
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime

ORG = "armbian"
RELEASE_MONTHS = (2, 5, 8, 11)
VIRTUAL_TARGETS = ("uefi-", "qemu-")  # not hardware anyone can adopt
RELEASE_MODEL = "https://docs.armbian.com/releases/release-model/"
BUILD = f"{ORG}/build"
DOCS = f"{ORG}/documentation"
API = "https://api.github.com"

RE_RELEASE_FILE = re.compile(r"^(\d+)\.(\d+)\.md$")
RE_RELEASE_TITLE = re.compile(r"^# Armbian (\S+)\s*$", re.MULTILINE)
RE_RELEASED = re.compile(r"^\*Released ([^*]+)\*\s*$", re.MULTILINE)

RE_BLOCK = re.compile(
    r"(<!-- auto:(?P<name>[a-z-]+) -->\n)(?P<body>.*?)(<!-- /auto:(?P=name) -->)",
    re.DOTALL,
)
RE_MAINTAINER = re.compile(
    r"^\s*(?:declare\s+-g\s+|export\s+)?BOARD_MAINTAINER=[\"']?([^\"'\n]*)", re.MULTILINE
)


def gh(path, **params):
    url = f"{API}/{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def search_url(query):
    return "https://github.com/search?" + urllib.parse.urlencode({"q": query, "type": "issues"})


# ---- data -----------------------------------------------------------------

def latest_stable():
    """Newest published release page in armbian/documentation (docs/releases/X.Y.md).

    The page is the project's record of a stable release: its H1 carries the
    point version ("Armbian 26.8.3") and a "*Released 23 August 2026*" line.
    GitHub releases on armbian/build are weekly trunk digests, not stable.
    """
    pages = []
    for item in gh(f"repos/{DOCS}/contents/docs/releases"):
        m = RE_RELEASE_FILE.match(item["name"])
        if m:
            pages.append((tuple(int(p) for p in m.groups()), item))
    for _, item in sorted(pages, key=lambda p: p[0], reverse=True):
        req = urllib.request.Request(item["download_url"])
        with urllib.request.urlopen(req, timeout=30) as resp:
            text = resp.read().decode("utf-8")
        title, released = RE_RELEASE_TITLE.search(text), RE_RELEASED.search(text)
        if title and released:
            when = datetime.strptime(released.group(1).strip(), "%d %B %Y")
            short = item["name"][: -len(".md")]
            return {
                "short": short,
                "version": title.group(1),
                "date": when.strftime("%-d %b %Y"),
                "url": f"https://docs.armbian.com/releases/{short}/",
            }
    raise RuntimeError("no released page in docs/releases")


def next_release(stable, today=None):
    """Next quarterly release after `stable`, from the fixed calendar.

    Releases ship by the end of RELEASE_MONTHS (docs/releases/release-model.md).
    The next release is the first release month after the latest published
    page, so a release that slips past its month still shows as "next" until
    its page lands.
    """
    today = today or date.today()
    published = tuple(int(p) for p in stable["short"].split("."))
    now = (today.year % 100, today.month)
    year = published[0]
    while True:
        for m in RELEASE_MONTHS:
            if (year, m) > published:
                full = 2000 + year
                end = date(full, m, calendar.monthrange(full, m)[1])
                return {
                    "version": f"{year}.{m}",
                    "due": end.strftime("end of %B %Y"),
                    "in_release_month": (year, m) == now,
                }
        year += 1


def milestone(title):
    """Open armbian/build milestone with this title, or None."""
    for ms in gh(f"repos/{BUILD}/milestones", state="open", per_page=100):
        if ms["title"] == title:
            return ms
    return None


def label_query(label):
    return f'org:{ORG} is:open is:issue label:"{label}"'


def label_count(label):
    return gh("search/issues", q=label_query(label), per_page=1)["total_count"]


def boards(build_dir):
    """Return {extension: [board, ...]} and the community boards without a maintainer."""
    by_ext, orphans = {}, []
    path = os.path.join(build_dir, "config", "boards")
    for name in sorted(os.listdir(path)):
        stem, _, ext = name.rpartition(".")
        if ext not in ("conf", "csc", "tvb", "wip", "eos"):
            continue
        by_ext.setdefault(ext, []).append(stem)
        if ext == "csc" and not stem.startswith(VIRTUAL_TARGETS):
            with open(os.path.join(path, name), encoding="utf-8", errors="replace") as fh:
                match = RE_MAINTAINER.search(fh.read())
            if not match or not match.group(1).strip():
                orphans.append(stem)
    if not by_ext:
        raise RuntimeError(f"no board configs in {path}")
    return by_ext, orphans


def teams():
    out, page = [], 1
    while True:
        batch = gh(f"orgs/{ORG}/teams", per_page=100, page=page)
        out += [t for t in batch if t.get("privacy") == "closed"]
        if len(batch) < 100:
            return sorted(out, key=lambda t: t["slug"])
        page += 1


# ---- blocks ---------------------------------------------------------------

def block_public_status(ctx):
    stable = latest_stable()
    nxt = next_release(stable)
    by_ext, _ = boards(ctx.build_dir)
    return (
        '<p align="center"><sub>\n'
        f'  Latest stable <a href="{stable["url"]}"><b>{stable["version"]}</b></a>'
        f' ({stable["date"]}) &nbsp;·&nbsp;\n'
        f'  next <a href="{RELEASE_MODEL}"><b>{nxt["version"]}</b></a> by the {nxt["due"]} &nbsp;·&nbsp;\n'
        f'  <b>{len(by_ext.get("conf", []))}</b> boards with standard support,'
        f' <b>{len(by_ext.get("csc", []))}</b> community\n'
        "</sub></p>\n"
    )


def block_release(ctx):
    stable = latest_stable()
    nxt = next_release(stable)
    out = f'Next release **{nxt["version"]}** ships by the **{nxt["due"]}**.'
    if nxt["in_release_month"]:
        out += " This is the release month: bug fixes and hardware testing only."
    try:
        ms = milestone(nxt["version"])
    except Exception as exc:  # the milestone is optional decoration
        print(f"warning: milestone lookup failed: {exc}", file=sys.stderr)
        ms = None
    if ms:
        n = ms["open_issues"]
        out += f' [{n} open item{"s" if n != 1 else ""}]({ms["html_url"]}) on the milestone.'
    out += (
        f'\nLatest stable: [{stable["version"]}]({stable["url"]}), released {stable["date"]}.'
        f' [How releases work]({RELEASE_MODEL}).\n'
    )
    return out


def block_help(ctx):
    links = []
    for label, text in (("good first issue", "Good first issues"), ("help wanted", "Help wanted")):
        links.append(f"[{text} ({label_count(label)})]({search_url(label_query(label))})")
    _, orphans = boards(ctx.build_dir)
    out = " · ".join(links) + "\n"
    if orphans:
        out += (
            "\n<details><summary>"
            f"<b>{len(orphans)}</b> community boards have no maintainer. Adopt one.</summary>\n\n"
            + " · ".join(f"`{b}`" for b in orphans)
            + "\n\n[What maintaining a board means](https://docs.armbian.com/contribute/board-maintainer/)\n"
            "</details>\n"
        )
    return out


def block_teams(ctx):
    rows = []
    for t in teams():
        desc = (t.get("description") or "").strip().rstrip(".")
        link = f"[@{ORG}/{t['slug']}]({t['html_url']})"
        rows.append(f"- {link}" + (f": {desc}" if desc else ""))
    if not rows:
        raise RuntimeError("no visible teams")
    return "\n".join(rows) + "\n"


BLOCKS = {
    "public-status": block_public_status,
    "release": block_release,
    "help": block_help,
    "teams": block_teams,
}


# ---- main -----------------------------------------------------------------

def refresh(text, ctx):
    def sub(m):
        name = m.group("name")
        render = BLOCKS.get(name)
        if render is None:
            print(f"warning: unknown block '{name}', kept", file=sys.stderr)
            return m.group(0)
        try:
            body = render(ctx)
        except Exception as exc:  # keep the old block on any source failure
            print(f"warning: block '{name}' failed, kept: {exc}", file=sys.stderr)
            return m.group(0)
        return m.group(1) + body + m.group(4)

    return RE_BLOCK.sub(sub, text)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+", help="profile README.md files to refresh in place")
    ap.add_argument("--build-dir", required=True, help="checkout of armbian/build (config/boards is enough)")
    ap.add_argument("--dry-run", action="store_true", help="print a diff, write nothing")
    ctx = ap.parse_args()

    for path in ctx.files:
        with open(path, encoding="utf-8") as fh:
            old = fh.read()
        new = refresh(old, ctx)
        if new == old:
            print(f"{path}: unchanged")
            continue
        if ctx.dry_run:
            sys.stdout.writelines(difflib.unified_diff(
                old.splitlines(True), new.splitlines(True), path, path))
        else:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(new)
            print(f"{path}: updated")


if __name__ == "__main__":
    main()
