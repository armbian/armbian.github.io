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
            "--format=%x01%s",
            "--", "config/boards",
        ],
        check=True, capture_output=True, text=True,
    ).stdout
    for record in out.split("\x01"):
        record = record.strip("\n")
        if not record:
            continue
        subject, _, body = record.partition("\n")
        yield subject.strip(), body


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


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--build-tree", required=True, help="armbian/build checkout")
    ap.add_argument("--since", required=True, help="ISO timestamp, window start")
    ap.add_argument("--until", required=True, help="ISO timestamp, window end")
    ap.add_argument("--digest", help="merged-PR TSV, used to recover PR links")
    ap.add_argument("--out", required=True, help="output TSV path")
    args = ap.parse_args()

    digest = load_digest_index(args.digest)
    seen, changes = set(), []

    for subject, body in git_log(args.build_tree, args.since, args.until):
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
            if old_stem in seen:
                continue
            seen.add(old_stem)
            changes.append((old_stem, old_ext, new_ext, ref, url))

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
