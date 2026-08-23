#!/usr/bin/env python3
"""Find board support-tier transitions in an armbian/build window.

Armbian encodes a board's support tier in its config file extension
(config/boards/<board>.conf|csc|eos|tvb|wip), so a tier change is exactly a
rename between two of those extensions. Reading the renames out of git is both
cheaper and more reliable than inferring the transition from PR titles, and it
catches the changes a title never mentions.

Emits a TSV of: board, old extension, new extension, PR reference, PR URL.
"""

import argparse
import csv
import json
import os
import re
import subprocess
import sys

TIER_EXTS = ("conf", "csc", "eos", "tvb", "wip")

RE_PR_IN_SUBJECT = re.compile(r"\(#(\d+)\)\s*$")


def git_log(tree, since, until):
    """Rename-only log over config/boards, one record per commit."""
    out = subprocess.run(
        [
            "git", "-C", tree, "log",
            "--since", since, "--until", until,
            "--diff-filter=R", "--find-renames=40%",
            "--name-status", "--no-merges",
            "--format=%x01%H %s",
            "--", "config/boards",
        ],
        check=True, capture_output=True, text=True,
    ).stdout
    for record in out.split("\x01"):
        record = record.strip("\n")
        if not record:
            continue
        header, _, body = record.partition("\n")
        sha, _, subject = header.strip().partition(" ")
        yield sha, subject.strip(), body


def tier_of(path):
    stem, dot, ext = os.path.basename(path).rpartition(".")
    return (stem, ext) if dot and ext in TIER_EXTS else (None, None)


def load_digest_index(path):
    """Map lowercased PR title -> (repo, number, url) for link recovery.

    Squashed commits keep the PR number in the subject; merge-queue commits do
    not, but their subject is the PR title verbatim, so the digest can supply
    the link.
    """
    index = {}
    if not path or not os.path.exists(path):
        return index
    with open(path, newline="", encoding="utf-8") as fh:
        for rec in csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE):
            if len(rec) < 5:
                continue
            title, _author, repo, number, url = (c.strip() for c in rec[:5])
            index.setdefault(title.rstrip(".").lower(), (repo, number, url))
    return index


def pr_for_commit(sha, repo="armbian/build", cache={}):
    """Ask GitHub which pull request a commit arrived in.

    Last resort, and worth the call: a rebase or merge-queue merge leaves the
    individual commits without a "(#123)" subject, and their subjects are the
    commit messages rather than the PR title, so neither of the cheap paths
    can match. Only unlinked commits reach here -- four in 26.8 -- and the
    result is cached, so this stays a handful of requests.
    """
    if sha in cache:
        return cache[sha]
    cache[sha] = ("", "")
    try:
        out = subprocess.run(
            ["gh", "api", "repos/{}/commits/{}/pulls".format(repo, sha),
             "--jq", "[.[] | {number, url: .html_url}]"],
            check=True, capture_output=True, text=True, timeout=30,
        ).stdout.strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        return cache[sha]
    try:
        hits = json.loads(out) if out else []
    except ValueError:
        return cache[sha]
    if len(hits) == 1:
        # More than one means the commit is in several PRs and picking would
        # be a guess; leave it unlinked rather than attribute it wrongly.
        cache[sha] = ("{}#{}".format(repo, hits[0]["number"]), hits[0]["url"])
    return cache[sha]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--build-tree", required=True, help="armbian/build checkout")
    ap.add_argument("--since", required=True, help="ISO timestamp, window start")
    ap.add_argument("--until", required=True, help="ISO timestamp, window end")
    ap.add_argument("--digest", help="merged-PR TSV, used to recover PR links")
    ap.add_argument("--out", required=True, help="output TSV path")
    ap.add_argument("--no-api", action="store_true",
                    help="skip the gh lookup for commits nothing else linked")
    args = ap.parse_args()

    digest = load_digest_index(args.digest)
    # git log runs newest first, so the first record for a board fixes the tier
    # it ends the window on and each older record widens where it started. A
    # board that moved twice in one quarter (wip -> csc -> conf) has to report
    # wip -> conf rather than the last hop alone, and one that round-tripped
    # back to where it began reports nothing at all.
    merged, changes = {}, []

    for sha, subject, body in git_log(args.build_tree, args.since, args.until):
        ref = url = ""
        match = RE_PR_IN_SUBJECT.search(subject)
        if match:
            ref = "armbian/build#{}".format(match.group(1))
            url = "https://github.com/armbian/build/pull/{}".format(match.group(1))
        else:
            hit = digest.get(subject.rstrip(".").lower())
            if hit:
                repo, number, url = hit
                ref = "{}#{}".format(repo, number)
            elif not args.no_api:
                ref, url = pr_for_commit(sha)

        for line in body.splitlines():
            fields = line.split("\t")
            if len(fields) != 3 or not fields[0].startswith("R"):
                continue
            _status, old_path, new_path = fields
            old_stem, old_ext = tier_of(old_path)
            new_stem, new_ext = tier_of(new_path)
            # A pure tier change keeps the board name and swaps the extension.
            # Renames that also change the stem are board renames, not tier
            # transitions, and are left out rather than guessed at.
            if not old_ext or not new_ext:
                continue
            if old_stem != new_stem or old_ext == new_ext:
                continue
            if old_stem in merged:
                merged[old_stem][0] = old_ext
            else:
                merged[old_stem] = [old_ext, new_ext, ref, url]

    changes = [
        (board, old, new, ref, url)
        for board, (old, new, ref, url) in merged.items()
        if old != new
    ]
    changes.sort(key=lambda c: c[0].lower())
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, delimiter="\t", quoting=csv.QUOTE_NONE,
                            escapechar="\\", lineterminator="\n")
        writer.writerows(changes)

    print("{} board tier change(s) written to {}".format(len(changes), args.out))
    for board, old, new, ref, _url in changes:
        print("  {}: {} -> {} {}".format(board, old, new, ref or "(no PR link)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
