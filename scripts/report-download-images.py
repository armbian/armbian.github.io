#!/usr/bin/env python3
#
# SPDX-License-Identifier: GPL-2.0
#
# Report on the images we actually provide for download, from the source of
# truth armbian-images.json, and surface anomalies. Output is GitHub-flavoured
# Markdown written to $GITHUB_STEP_SUMMARY (and stdout).
#
# Anomalies reported:
#   1. Outdated boards       - newest live image older than --stale-days.
#   2. Non-conf on stable    - csc/wip/tvb boards published to the stable
#                              ("distribution") download.
#   3. Supported not on stable - conf boards with NO image in the stable download.
#   4. Desktop w/o video     - desktop-variant images for boards whose inventory
#                              says BOARD_HAS_VIDEO is false (needs image-info.json).
#
# Sources (fetched or passed as local files):
#   - armbian-images.json   https://github.armbian.com/armbian-images.json
#   - image-info.json       https://github.armbian.com/image-info.json  (for the
#                           board -> BOARD_HAS_VIDEO map; optional)

import argparse
import collections
import datetime as dt
import json
import os
import re
import sys
import urllib.request

IMAGES_URL = "https://github.armbian.com/armbian-images.json"
INFO_URL = "https://github.armbian.com/image-info.json"

# download_repository values that are "live" (offered now), vs 'archive' (old).
LIVE_REPOS = ("distribution", "community", "ci")
# the stable / main download users land on
STABLE_REPO = "distribution"
# variants that are NOT a desktop (everything else is a desktop environment)
NON_DESKTOP_VARIANTS = {"minimal", "cli", "server", ""}


def load(src, what):
    """Load JSON from a URL or a local path."""
    try:
        if re.match(r"^https?://", src):
            with urllib.request.urlopen(src, timeout=60) as r:
                return json.load(r)
        with open(src) as f:
            return json.load(f)
    except Exception as e:
        print(f"::warning::could not load {what} from {src}: {e}", file=sys.stderr)
        return None


def version_key(v):
    """Sortable key for Armbian versions: X.Y.Z and X.Y.Z-trunk.N."""
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:-trunk\.(\d+))?$", str(v or ""))
    if not m:
        return (0, 0, 0, 0, str(v))
    maj, mnr, pat, trunk = m.groups()
    # a release (no -trunk) sorts above the same-numbered trunk build
    return (int(maj), int(mnr), int(pat), int(trunk) if trunk is not None else 10**9, "")


def is_release(v):
    return bool(re.match(r"^\d+\.\d+\.\d+$", str(v or "")))


def parse_date(s):
    try:
        return dt.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None


def md_table(headers, rows):
    out = ["| " + " | ".join(headers) + " |",
           "| " + " | ".join("---" for _ in headers) + " |"]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


def build_video_map(info):
    """board_slug -> BOARD_HAS_VIDEO (bool), from image-info.json inventory."""
    vid = {}
    if not info:
        return vid
    entries = info["assets"] if isinstance(info, dict) and "assets" in info else info
    for e in entries:
        inv = (e.get("in") or {}).get("inventory") or {}
        b, hv = inv.get("BOARD"), inv.get("BOARD_HAS_VIDEO")
        if b is not None and hv is not None:
            vid[b] = bool(hv)
    return vid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", default=IMAGES_URL, help="armbian-images.json URL or path")
    ap.add_argument("--image-info", default=INFO_URL, help="image-info.json URL or path (video flag)")
    ap.add_argument("--stale-days", type=int, default=45, help="a board is 'outdated' if its newest live image is older than this")
    ap.add_argument("--top", type=int, default=40, help="max rows in the outdated table")
    args = ap.parse_args()

    data = load(args.images, "armbian-images.json")
    if not data:
        print("::error::armbian-images.json unavailable; cannot report", file=sys.stderr)
        return 1
    assets = data["assets"] if isinstance(data, dict) and "assets" in data else data
    video = build_video_map(load(args.image_info, "image-info.json"))

    now = dt.datetime.now(dt.timezone.utc)
    boards = {a["board_slug"]: a for a in assets}  # any asset, for board_name/support
    board_support = {a["board_slug"]: a.get("board_support", "?") for a in assets}
    board_name = {a["board_slug"]: a.get("board_name", a["board_slug"]) for a in assets}

    # ---- overview ----
    by_repo = collections.Counter(a.get("download_repository", "") for a in assets)
    by_support = collections.Counter(a.get("board_support", "") for a in assets)
    repo_versions = collections.defaultdict(set)
    for a in assets:
        repo_versions[a.get("download_repository", "")].add(a.get("armbian_version", ""))

    out = []
    out.append("# Download images report")
    out.append(f"_Source: `{args.images}` — {len(assets)} image assets across "
               f"{len(boards)} boards, generated {now:%Y-%m-%d %H:%M UTC}._\n")
    out.append("## Overview")
    out.append(md_table(
        ["download_repository", "images", "version(s)"],
        [[r or "(empty)", n, ", ".join(sorted(repo_versions[r], key=version_key)) if len(repo_versions[r]) <= 3
          else f"{len(repo_versions[r])} versions"]
         for r, n in by_repo.most_common()]))
    out.append("")
    out.append("Support levels: " + ", ".join(f"`{s or '?'}` {n}" for s, n in by_support.most_common()))
    out.append("")

    # ---- per-board freshness (live repos only) ----
    live_by_board = collections.defaultdict(list)
    for a in assets:
        if a.get("download_repository") in LIVE_REPOS:
            live_by_board[a["board_slug"]].append(a)

    # ---- CHECK 1: outdated boards ----
    outdated = []
    for b, imgs in live_by_board.items():
        dates = [parse_date(i.get("file_date")) for i in imgs]
        dates = [d for d in dates if d]
        newest = max(dates) if dates else None
        newest_ver = max((i.get("armbian_version", "") for i in imgs), key=version_key)
        age = (now - newest).days if newest else None
        if age is not None and age > args.stale_days:
            outdated.append((age, b, board_support.get(b, "?"), newest_ver, newest.strftime("%Y-%m-%d")))
    outdated.sort(reverse=True)
    out.append(f"## ⏳ Outdated boards — newest live image older than {args.stale_days} days ({len(outdated)})")
    if outdated:
        rows = [[b, f"`{s}`", v, d, f"{age} d"] for age, b, s, v, d in outdated[:args.top]]
        out.append(md_table(["board", "support", "newest version", "date", "age"], rows))
        if len(outdated) > args.top:
            out.append(f"\n_…and {len(outdated) - args.top} more._")
    else:
        out.append("_None._")
    out.append("")

    # ---- CHECK 2: non-conf boards on the stable download ----
    nonconf_stable = collections.defaultdict(set)
    for a in assets:
        if a.get("download_repository") == STABLE_REPO and a.get("board_support") != "conf":
            nonconf_stable[a["board_slug"]].add(a.get("board_support", "?"))
    out.append(f"## ⚠️ Non-standard boards on the stable download (`{STABLE_REPO}`) ({len(nonconf_stable)})")
    out.append(f"_These are `csc`/`wip`/`tvb` boards published to the main download._")
    if nonconf_stable:
        rows = [[b, f"`{'/'.join(sorted(s))}`", board_name.get(b, b)] for b, s in sorted(nonconf_stable.items())]
        out.append(md_table(["board", "support", "name"], rows))
    else:
        out.append("_None._")
    out.append("")

    # ---- CHECK 3: supported (conf) boards missing from the stable download ----
    conf_boards = {b for b, s in board_support.items() if s == "conf"}
    in_stable = {a["board_slug"] for a in assets if a.get("download_repository") == STABLE_REPO}
    missing_stable = sorted(conf_boards - in_stable)
    out.append(f"## ❓ Supported boards with no stable image (`{STABLE_REPO}`) ({len(missing_stable)})")
    out.append("_`conf` (standard-support) boards that have no image on the main download._")
    if missing_stable:
        rows = []
        for b in missing_stable:
            elsewhere = sorted({a.get("download_repository", "") for a in assets
                                if a["board_slug"] == b and a.get("download_repository") != STABLE_REPO})
            rows.append([b, board_name.get(b, b), ", ".join(r or "(none)" for r in elsewhere) or "—"])
        out.append(md_table(["board", "name", "present in"], rows))
    else:
        out.append("_None._")
    out.append("")

    # ---- CHECK 4: desktop images for no-video boards ----
    novideo_desktop = collections.defaultdict(set)
    for a in assets:
        b = a["board_slug"]
        if a.get("variant") not in NON_DESKTOP_VARIANTS and video.get(b) is False:
            novideo_desktop[b].add(f"{a.get('variant')}·{a.get('branch')}·{a.get('download_repository')}")
    out.append(f"## 🖥️ Desktop images for boards without video output ({len(novideo_desktop)})")
    if not video:
        out.append("_Skipped: image-info.json (BOARD_HAS_VIDEO) was not available._")
    elif novideo_desktop:
        rows = [[b, board_name.get(b, b), ", ".join(sorted(s))] for b, s in sorted(novideo_desktop.items())]
        out.append(md_table(["board", "name", "desktop images (variant·branch·repo)"], rows))
    else:
        out.append("_None._")
    out.append("")

    report = "\n".join(out)
    print(report)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as f:
            f.write(report + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
