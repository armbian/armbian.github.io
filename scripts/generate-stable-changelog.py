#!/usr/bin/env python3
"""Write the changelog of one weekly stable release (armbian/ci X.Y.Z tag).

Compares the artifacts-info.json of two stable builds and writes:

- CHANGELOG.md: kernel updates, CVE patches, upstream changes, framework PRs,
  changed packages.
- counts.json: the numbers for the one-line summary in the release body.

Git history comes from local clones, so the script makes few API calls:
armbian/build (commit range -> PRs), armbian/cve (CVE patches), the kernel
vulns repo (upstream CVE IDs) and a kernel stable clone (upstream changes).
"""

import argparse
import collections
import datetime
import json
import os
import re
import subprocess
import sys
import time

MAINLINE_SOURCE = "https://github.com/armbian/linux.git"
BOT_AUTHORS = {"armbianworker", "armbianworker[bot]", "github-actions[bot]",
               "dependabot[bot]", "renovate[bot]"}
AUTOMATION_TITLE = re.compile(r"^(cve|patches)\s*:", re.I)
# Version part letter -> reason. Parts are "<KEY><hash>" after the version number.
PART_REASON = {"S": "upstream", "D": "patches", "P": "patches", "C": "config",
               "HK": "config", "CVE": "CVE", "H": "framework", "V": "framework",
               "B": "framework", "R": "framework"}
PART_RE = re.compile(r"^(CVE|HK|[A-Z])([0-9a-f]+)$")
AREAS_SHOWN = 5


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], check=True,
                          capture_output=True, text=True).stdout


def gh_api(path, attempts=3):
    """Parsed JSON, or None after the last failed attempt."""
    for attempt in range(attempts):
        out = subprocess.run(["gh", "api", path], capture_output=True, text=True)
        if out.returncode == 0:
            return json.loads(out.stdout)
        if attempt + 1 < attempts:
            time.sleep(5 * (attempt + 1))
    return None


# ---------------------------------------------------------------- artifacts

def load_artifacts(path):
    """artifact name -> {version, inputs, needed_by, type}."""
    result = {}
    with open(path) as f:
        data = json.load(f)
    for a in data:
        out = a.get("out") or {}
        name = out.get("artifact_name")
        if not name or not out.get("artifact_version"):
            continue
        result[name] = {
            "version": out["artifact_version"],
            "reason": out.get("artifact_version_reason", ""),
            "inputs": a["in"].get("inputs", {}),
            "needed_by": a["in"].get("needed_by", 0),
            "type": a["in"].get("artifact_name"),
            "release": out.get("artifact_final_version_reversioned"),
        }
    return result


def split_version(version):
    """'7.3.5-S9881-...-CVE276a-R448a' -> ('7.3.5', {'S': '9881', ...})."""
    head, *parts = version.split("-")
    keyed = {}
    for p in parts:
        m = PART_RE.match(p)
        if m:
            keyed[m.group(1)] = m.group(2)
    return head, keyed


def change_reasons(old, new):
    old_head, old_parts = split_version(old)
    new_head, new_parts = split_version(new)
    reasons = []
    if old_head != new_head:
        reasons.append("upstream")
    for key in sorted(set(old_parts) | set(new_parts)):
        if old_parts.get(key) != new_parts.get(key):
            reason = PART_REASON.get(key, "framework")
            if reason not in reasons:
                reasons.append(reason)
    return reasons


def kernel_revision(art):
    m = re.search(r'git revision "([0-9a-f]{40})"', art["reason"])
    return m.group(1) if m else None


def branch_series(arts):
    """'current'/'edge' -> most used mainline series in this build."""
    count = collections.defaultdict(collections.Counter)
    for a in arts.values():
        i = a["inputs"]
        if a["type"] == "kernel" and i.get("KERNELSOURCE") == MAINLINE_SOURCE \
                and i.get("BRANCH") in ("current", "edge"):
            count[i["BRANCH"]][i["KERNEL_MAJOR_MINOR"]] += a["needed_by"] or 1
    return {b: c.most_common(1)[0][0] for b, c in count.items()}


def branch_kernels(arts, branch, series):
    """Mainline kernel artifacts of one branch and series."""
    return [a for a in arts.values() if a["type"] == "kernel"
            and a["inputs"].get("KERNELSOURCE") == MAINLINE_SOURCE
            and a["inputs"].get("BRANCH") == branch
            and a["inputs"].get("KERNEL_MAJOR_MINOR") == series]


def series_revision(arts, branch, series, version):
    """armbian/linux commit of the most used kernel with this upstream version."""
    best = max((a for a in branch_kernels(arts, branch, series)
                if split_version(a["version"])[0] == version),
               key=lambda a: a["needed_by"], default=None)
    return kernel_revision(best) if best else None


def series_versions(arts, branch, series):
    """Upstream versions of the mainline kernels of one branch and series."""
    return sorted({split_version(a["version"])[0] for a in branch_kernels(arts, branch, series)},
                  key=vkey)


def point_releases(series, old, new):
    """Stable releases in (old, new] of one series: 6.18.5 -> 6.18.7 gives .6 and .7."""
    lo = (vkey(old) + (0, 0, 0))[2]
    hi = (vkey(new) + (0, 0, 0))[2]
    return [f"{series}.{i}" for i in range(lo + 1, hi + 1)]


def vkey(v):
    return tuple(int(x) for x in re.findall(r"\d+", v))


# ---------------------------------------------------------------- upstream CVEs

def load_dyads(vulns_dir):
    """series -> list of (fixed version, CVE ID)."""
    fixed = collections.defaultdict(list)
    root = os.path.join(vulns_dir, "cve", "published")
    for year in os.listdir(root):
        ydir = os.path.join(root, year)
        if not os.path.isdir(ydir):
            continue
        for f in os.listdir(ydir):
            if not f.endswith(".dyad"):
                continue
            cve = f[:-5]
            with open(os.path.join(ydir, f), errors="replace") as fh:
                lines = fh.readlines()
            for line in lines:
                if line.startswith("#"):
                    continue
                fields = line.strip().split(":")
                if len(fields) != 4 or not fields[2] or fields[2] == "0":
                    continue
                ver = fields[2]
                series = ".".join(ver.split(".")[:2])
                fixed[series].append((ver, cve))
    return fixed


def upstream_cves(dyads, series, old, new):
    """Point release -> sorted CVE IDs fixed in (old, new]."""
    lo, hi = vkey(old), vkey(new)
    by_release = collections.defaultdict(set)
    for ver, cve in dyads.get(series, []):
        if lo < vkey(ver) <= hi:
            by_release[ver].add(cve)
    return {v: sorted(c, key=vkey) for v, c in sorted(by_release.items(), key=lambda x: vkey(x[0]))}


# ---------------------------------------------------------------- armbian/cve

def cve_patches(cve_repo, ref, series):
    """Upstream commit (12 hex) -> {cve, subject, file} at one armbian/cve commit."""
    path = f"patches/{series}/"
    try:
        names = git(cve_repo, "ls-tree", "--name-only", ref, path).split()
    except subprocess.CalledProcessError:
        return {}
    result = {}
    for name in names:
        m = re.match(r".*/\d+-([0-9a-f]{12})-.*\.patch$", name)
        if not m:
            continue
        head = git(cve_repo, "show", f"{ref}:{name}")[:4000]
        cve = re.search(r"^X-Fasttrack-CVE:\s*(\S+)", head, re.M)
        subject = re.search(r"^Subject:\s*(?:\[PATCH[^\]]*\]\s*)?(.+(?:\n[ \t].+)*)", head, re.M)
        result[m.group(1)] = {"cve": cve.group(1) if cve else "",
                              "subject": " ".join(subject.group(1).split()) if subject else name,
                              "file": name}
    return result


def added_date(cve_repo, old_ref, new_ref, path):
    out = git(cve_repo, "log", "--diff-filter=A", "--format=%cs", "--reverse",
              f"{old_ref}..{new_ref}", "--", path)
    return out.split()[0] if out.split() else ""


# ---------------------------------------------------------------- kernel stable

def upstream_changes(linux_repo, old_rev, new_rev):
    """(commit count, Counter of areas) for old_rev..new_rev in armbian/linux, or None.

    Each commit counts once, under the area that holds most of its files.
    """
    try:
        out = git(linux_repo, "log", "--no-merges", "--format=%x00", "--name-only",
                  f"{old_rev}..{new_rev}")
    except subprocess.CalledProcessError:
        return None
    commits = out.split("\x00")[1:]
    areas = collections.Counter()
    for c in commits:
        files = [f for f in c.split("\n") if f]
        if files:
            areas[collections.Counter(area_of(f) for f in files).most_common(1)[0][0]] += 1
    return len(commits), areas


def area_of(path):
    parts = path.split("/")
    if parts[0] in ("drivers", "arch", "sound") and len(parts) > 2:
        return "/".join(parts[:2])
    return parts[0] if len(parts) > 1 else "other"


def changelog_url(version):
    major = version.split(".")[0]
    return f"https://cdn.kernel.org/pub/linux/kernel/v{major}.x/ChangeLog-{version}"


# ---------------------------------------------------------------- framework PRs

def framework_prs(build_repo, old, new):
    """Merged PRs in old..new, without bots and CVE automation."""
    log = git(build_repo, "log", "--format=%x00%H%x09%s", "--name-only", f"{old}..{new}")
    prs = {}
    commits = 0
    lost_commits = []
    for chunk in log.split("\x00")[1:]:
        lines = [l for l in chunk.split("\n") if l]
        sha, subject = lines[0].split("\t", 1)
        commits += 1
        m = re.search(r"\(#(\d+)\)$", subject)
        if m:
            numbers = [int(m.group(1))]
        else:
            pulls = gh_api(f"repos/armbian/build/commits/{sha}/pulls")
            if pulls is None:
                lost_commits.append(sha)
                continue
            numbers = [p["number"] for p in pulls]
        for n in numbers:
            prs.setdefault(n, set()).update(lines[1:])
    shown, hidden, unknown = [], 0, []
    for n, files in sorted(prs.items()):
        pr = gh_api(f"repos/armbian/build/pulls/{n}")
        if not pr:
            # Cannot tell automation from real work: list the number apart, do not count it.
            unknown.append(n)
            continue
        title = pr.get("title", f"#{n}")
        author = (pr.get("user") or {}).get("login", "")
        if author in BOT_AUTHORS or AUTOMATION_TITLE.match(title):
            hidden += 1
            continue
        shown.append({"number": n, "title": title, "author": author,
                      "group": pr_group(files)})
    return commits, shown, hidden, unknown, lost_commits


def pr_group(files):
    def any_prefix(*prefixes):
        return any(f.startswith(prefixes) for f in files)
    if any_prefix("patch/kernel/", "config/kernel/"):
        return "Kernel"
    if any_prefix("patch/u-boot/", "patch/atf/"):
        return "U-Boot"
    if any_prefix("config/boards/", "packages/bsp/", "config/sources/families/"):
        return "Boards and BSP"
    return "Build system"


# ---------------------------------------------------------------- provenance

def at(repo, when):
    """main tip at a time. --first-parent: a merged branch can hold older commits."""
    return git(repo, "rev-list", "-1", "--first-parent", f"--before={when}", "origin/main").strip()


def cve_commit(cve_repo, arts, when):
    """armbian/cve commit of a build.

    Kernels with CVE patches carry the first 4 hex of that commit in the version
    (part "CVE"). Take the newest main commit with this prefix that existed before
    the kernel builds ended. Without the part, use the main tip at the build time.
    """
    prefixes = collections.Counter(split_version(a["version"])[1]["CVE"] for a in arts.values()
                                   if a["type"] == "kernel" and "CVE" in split_version(a["version"])[1])
    if prefixes:
        prefix = prefixes.most_common(1)[0][0]
        end = datetime.datetime.fromisoformat(when.replace("Z", "+00:00")) + datetime.timedelta(hours=24)
        for sha in git(cve_repo, "rev-list", "--first-parent", f"--before={end.isoformat()}",
                       "origin/main").split():
            if sha.startswith(prefix):
                return sha
    return at(cve_repo, when)


# ---------------------------------------------------------------- render

def main():
    # Helper for the workflow: which armbian/linux branches to fetch for this build.
    if len(sys.argv) >= 3 and sys.argv[1] == "--list-series":
        series = set()
        for info in sys.argv[2:]:
            series |= set(branch_series(load_artifacts(info)).values())
        print(" ".join(sorted(series, key=vkey)))
        return 0

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--prev-info", required=True)
    ap.add_argument("--cur-info", required=True)
    ap.add_argument("--prev-version", required=True)
    ap.add_argument("--cur-version", required=True)
    ap.add_argument("--prev-time", required=True, help="ISO time of the previous build")
    ap.add_argument("--cur-time", required=True, help="ISO time of this build")
    ap.add_argument("--build-repo", required=True, help="clone of armbian/build")
    ap.add_argument("--cve-repo", required=True, help="clone of armbian/cve")
    ap.add_argument("--vulns", required=True, help="kernel vulns repo (.dyad files)")
    ap.add_argument("--linux-repo", required=True, help="clone of armbian/linux with both kernel revisions")
    ap.add_argument("--prev-build-sha", help="armbian/build commit of the previous build (from its log)")
    ap.add_argument("--cur-build-sha", help="armbian/build commit of this build (from its log)")
    ap.add_argument("--out", default="CHANGELOG.md")
    ap.add_argument("--counts", default="counts.json")
    args = ap.parse_args()

    prev, cur = load_artifacts(args.prev_info), load_artifacts(args.cur_info)

    build_old = args.prev_build_sha or at(args.build_repo, args.prev_time)
    build_new = args.cur_build_sha or at(args.build_repo, args.cur_time)
    cve_old = cve_commit(args.cve_repo, prev, args.prev_time)
    cve_new = cve_commit(args.cve_repo, cur, args.cur_time)

    built = datetime.datetime.fromisoformat(args.cur_time.replace("Z", "+00:00"))
    since = datetime.datetime.fromisoformat(args.prev_time.replace("Z", "+00:00"))
    days = max(1, round((built - since).total_seconds() / 86400))

    branches = branch_series(cur)
    prev_branches = branch_series(prev)
    dyads = load_dyads(args.vulns)
    md = []
    counts = collections.Counter()

    md.append(f"# Armbian {args.cur_version} changelog\n")
    md.append(f"Previous: {args.prev_version} · Built: {built:%d %b %Y %H:%M} UTC  ")
    n_build = len(git(args.build_repo, "rev-list", f"{build_old}..{build_new}").split())
    md.append(f"Framework: [armbian/build {build_old[:7]} → {build_new[:7]}]"
              f"(https://github.com/armbian/build/compare/{build_old[:12]}...{build_new[:12]})"
              f" ({n_build} commits) · CVE: [armbian/cve {cve_old[:7]} → {cve_new[:7]}]"
              f"(https://github.com/armbian/cve/compare/{cve_old[:12]}...{cve_new[:12]})\n")

    # ---- per branch data
    per_branch = {}
    for branch in ("current", "edge"):
        series = branches.get(branch)
        if not series:
            continue
        # The branch can move to a new series (6.12 -> 6.18): then compare versions only.
        old_series = prev_branches.get(branch, series)
        old_v = series_versions(prev, branch, old_series)
        new_v = series_versions(cur, branch, series)
        old_top, new_top = (old_v[-1] if old_v else None), (new_v[-1] if new_v else None)
        same = old_series == series and old_top and new_top
        pkgs = [n for n, a in cur.items() if a["type"] == "kernel"
                and a["inputs"].get("BRANCH") == branch
                and a["inputs"].get("KERNEL_MAJOR_MINOR") == series
                and n in prev and prev[n]["version"] != a["version"]]
        ups = upstream_cves(dyads, series, old_top, new_top) if same else {}
        releases = point_releases(series, old_top, new_top) if same else []
        old_p, new_p = cve_patches(args.cve_repo, cve_old, series), cve_patches(args.cve_repo, cve_new, series)
        added = {k: v for k, v in new_p.items() if k not in old_p}
        dropped = {k: v for k, v in old_p.items() if k not in new_p}
        per_branch[branch] = dict(series=series, old_series=old_series, same=same,
                                  old=old_top, new=new_top, pkgs=pkgs, releases=releases,
                                  old_rev=series_revision(prev, branch, old_series, old_top) if same else None,
                                  new_rev=series_revision(cur, branch, series, new_top) if same else None,
                                  ups=ups, added=added, dropped=dropped)
        counts["upstream_cves"] += sum(len(v) for v in ups.values())
        counts["cve_patches"] += len(added)
        counts["point_releases"] += len(releases)

    # ---- kernel updates
    md.append("## Kernel updates\n")
    md.append("| Branch | Series | Upstream | Packages | Upstream CVEs | Armbian CVE patches |")
    md.append("|--------|--------|----------|----------|---------------|---------------------|")
    for branch, b in per_branch.items():
        upstream = f"{b['old'] or '—'} → {b['new']}" if b["old"] != b["new"] else f"{b['new']} (unchanged)"
        series = b["series"] if b["same"] or not b["old"] else f"{b['old_series']} → {b['series']}"
        md.append(f"| {branch.upper()} | {series} | {upstream} | {len(b['pkgs'])} | "
                  f"{sum(len(v) for v in b['ups'].values()) or '—'} | "
                  f"+{len(b['added'])} / −{len(b['dropped'])} |")
    vendor = []
    for n, a in sorted(cur.items()):
        if a["type"] == "kernel" and a["inputs"].get("KERNELSOURCE") != MAINLINE_SOURCE \
                and n in prev and kernel_revision(prev[n]) != kernel_revision(a):
            vendor.append(f"{n.removeprefix('kernel-')} ({(kernel_revision(prev[n]) or '?')[:7]} → "
                          f"{(kernel_revision(a) or '?')[:7]})")
    md.append("\nVendor kernels with a new revision: " + (", ".join(vendor) if vendor else "none") + "\n")

    # ---- security
    md.append(f"## Security: CVE patches added in the last {days} days\n")
    md.append("Armbian backports from [armbian/cve](https://github.com/armbian/cve). "
              "Upstream stable has not released these fixes yet.\n")
    for branch, b in per_branch.items():
        md.append(f"### {branch.upper()} ({b['series']}) — {len(b['added'])} added, "
                  f"{len(b['dropped'])} dropped\n")
        if b["added"]:
            md.append("| CVE | Fix | Upstream commit | Added |")
            md.append("|-----|-----|-----------------|-------|")
            for up, p in sorted(b["added"].items(), key=lambda x: vkey(x[1]["cve"] or "0")):
                cve = p["cve"]
                cve_link = f"[{cve}](https://www.cve.org/CVERecord?id={cve})" if cve.startswith("CVE-") else (cve or "—")
                date = added_date(args.cve_repo, cve_old, cve_new, p["file"])
                md.append(f"| {cve_link} | {p['subject']} | "
                          f"[{up}](https://git.kernel.org/linus/{up}) | {date} |")
            md.append("")
        if b["dropped"]:
            # Claim an upstream fix only when the vulns repo shows it in this update.
            fixed_in = {c: v for v, cs in b["ups"].items() for c in cs}
            upstream = [f"{p['cve']} ({fixed_in[p['cve']]})" for _, p in sorted(b["dropped"].items())
                        if p["cve"] in fixed_in]
            removed = [p["cve"] or up for up, p in sorted(b["dropped"].items())
                       if p["cve"] not in fixed_in]
            if upstream:
                md.append("Dropped, fixed upstream: " + ", ".join(upstream) + "\n")
            if removed:
                md.append("Dropped from armbian/cve: " + ", ".join(removed) + "\n")

    # ---- upstream changes
    md.append("## Upstream changes\n")
    for branch, b in per_branch.items():
        if not b["old"]:
            md.append(f"### {branch.upper()}: {b['new']} (new)\n")
            continue
        if not b["same"]:
            md.append(f"### {branch.upper()}: {b['old']} → {b['new']} (new series)\n")
            continue
        if b["old"] == b["new"]:
            md.append(f"### {branch.upper()}: {b['new']} (unchanged)\n")
            continue
        md.append(f"### {branch.upper()}: {b['old']} → {b['new']}\n")
        ch = upstream_changes(args.linux_repo, b["old_rev"], b["new_rev"]) \
            if b["old_rev"] and b["new_rev"] else None
        links = " · ".join(f"[ChangeLog-{v}]({changelog_url(v)})" for v in b["releases"])
        n_cves = sum(len(v) for v in b["ups"].values())
        compare = (f"[{ch[0]} commits](https://github.com/armbian/linux/compare/"
                   f"{b['old_rev'][:12]}...{b['new_rev'][:12]})") if ch else "? commits"
        md.append(f"{compare} · {n_cves} CVEs fixed · {links}\n")
        if ch:
            md.append("| Area | Commits |")
            md.append("|------|---------|")
            top = ch[1].most_common(AREAS_SHOWN)
            for area, n in top:
                md.append(f"| {area} | {n} |")
            rest = ch[0] - sum(n for _, n in top)
            if rest > 0:
                md.append(f"| other | {rest} |")
            md.append("")
        if b["ups"]:
            md.append(f"<details><summary>CVEs fixed upstream ({n_cves})</summary>\n")
            for v, cves in b["ups"].items():
                md.append(f"**{v}**: " + ", ".join(cves) + "\n")
            md.append("</details>\n")

    # ---- framework
    n_commits, prs, hidden, unknown, lost_commits = framework_prs(args.build_repo, build_old, build_new)
    counts["framework_prs"] = len(prs)
    md.append(f"## Framework changes ({len(prs)} PRs, {hidden} automated hidden)\n")
    if unknown:
        md.append(f"Incomplete: the GitHub API did not return {len(unknown)} PRs: "
                  + ", ".join(f"[#{n}](https://github.com/armbian/build/pull/{n})" for n in unknown) + "\n")
    if lost_commits:
        md.append(f"Incomplete: the GitHub API did not return the PRs of {len(lost_commits)} commits: "
                  + ", ".join(f"[{c[:7]}](https://github.com/armbian/build/commit/{c})" for c in lost_commits) + "\n")
    groups = collections.defaultdict(list)
    for pr in prs:
        groups[pr["group"]].append(pr)
    for g in ("Kernel", "U-Boot", "Boards and BSP", "Build system"):
        if not groups[g]:
            continue
        md.append(f"<details><summary>{g} ({len(groups[g])})</summary>\n")
        for pr in sorted(groups[g], key=lambda p: p["title"].lower()):
            md.append(f"- {pr['title']} [#{pr['number']}](https://github.com/armbian/build/pull/{pr['number']})"
                      + (f" @{pr['author']}" if pr["author"] else ""))
        md.append("\n</details>\n")

    # ---- changed packages
    changed = collections.defaultdict(list)
    for n, a in cur.items():
        if n in prev and prev[n]["version"] != a["version"]:
            changed[a["type"]].append((n, prev[n], a))
    counts["kernel_packages"] = len(changed["kernel"])
    uboot_new = [x for x in changed["uboot"]
                 if split_version(x[1]["version"])[0] != split_version(x[2]["version"])[0]]
    uboot_patches = [x for x in changed["uboot"] if x not in uboot_new
                     and "patches" in change_reasons(x[1]["version"], x[2]["version"])]
    md.append("## Changed packages\n")
    md.append(f"<details><summary>{len(changed['kernel'])} kernel packages, "
              f"{len(uboot_new)} U-Boot version updates</summary>\n")
    md.append("| Package | Old → new | Why | Boards |")
    md.append("|---------|-----------|-----|--------|")
    for n, old, new in sorted(changed["kernel"] + uboot_new, key=lambda x: (x[2]["type"] != "kernel", -x[2]["needed_by"])):
        ov, nv = split_version(old["version"])[0], split_version(new["version"])[0]
        md.append(f"| {n} | {ov} → {nv} | {', '.join(change_reasons(old['version'], new['version']))} "
                  f"| {new['needed_by']} |")
    rebuilt = len(changed["uboot"]) - len(uboot_new) - len(uboot_patches)
    md.append(f"\nAlso rebuilt: {len(uboot_patches)} U-Boot packages with patch changes, "
              f"{rebuilt} U-Boot and {len(changed['armbian-bsp-cli'])} BSP packages "
              "for framework changes only.\n")
    md.append("</details>\n")
    for kind, names in (("New", sorted(n for n in cur if n not in prev)),
                        ("Removed", sorted(n for n in prev if n not in cur))):
        kernels = [n for n in names if (cur.get(n) or prev[n])["type"] == "kernel"]
        if names:
            md.append(f"{kind} packages: {len(names)}"
                      + (f" (kernels: {', '.join(kernels)})" if kernels else "") + "\n")

    # ---- notes
    skipped = sorted(n.removeprefix("kernel-") for n, a in cur.items()
                     if a["type"] == "kernel" and a["inputs"].get("KERNEL_CVE_PATCHES") == "yes"
                     and a["inputs"].get("KERNELSOURCE") == MAINLINE_SOURCE
                     and a["inputs"].get("KERNEL_MAJOR_MINOR") in {b["series"] for b in per_branch.values()}
                     and "CVE" not in split_version(a["version"])[1])
    md.append("## Notes\n")
    md.append(f"- CVE patches not applied ({len(skipped)} kernels, kernel commit is not the series base): "
              + (", ".join(skipped) if skipped else "none"))

    with open(args.out, "w") as f:
        f.write("\n".join(md) + "\n")
    with open(args.counts, "w") as f:
        json.dump(counts, f, indent=1)
    print(json.dumps(counts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
