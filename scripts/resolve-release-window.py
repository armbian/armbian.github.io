#!/usr/bin/env python3
"""Resolve the date and the PR window for one quarterly release note.

Both have to be reproducible. Regenerating a quarter months later must
produce the same page, so neither the date nor the window may be read from
the clock once the quarter has been published.

The window is anchored to the releases either side of it rather than to a
rolling three months. A clock-based window slides: rebuilding 26.8 three
weeks late would drop three weeks of PRs off the start -- PRs that belong to
26.8 and appear in no other note -- and pull in three weeks of post-release
work that belongs to the next quarter. Same length, wrong contents.

The previous quarter's date comes from its own published page, which is the
project's record of where quarters begin and end and owes nothing to tag or
release retention in other repositories.
"""

import argparse
import os
import re
import sys
from datetime import datetime, timedelta, timezone

RE_RELEASED = re.compile(r"^\*Released ([^*]+)\*\s*$", re.MULTILINE)
RE_VERSION_FILE = re.compile(r"^(\d+)\.(\d+)(?:\.(\d+))?\.md$")

HUMAN = "%-d %B %Y"


def human(dt):
    # %-d is glibc; the workflow runs on ubuntu. Avoids a leading zero.
    return dt.strftime(HUMAN)


def parse_human(text):
    """Parse the '29 May 2026' form the pages carry. Returns None if it isn't."""
    try:
        return datetime.strptime(text.strip(), "%d %B %Y").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def sort_key(match):
    return tuple(int(p) for p in match.groups(default="0"))


def released_on(path):
    try:
        with open(path, encoding="utf-8") as fh:
            match = RE_RELEASED.search(fh.read())
    except OSError:
        return None
    return parse_human(match.group(1)) if match else None


def scan(releases_dir):
    """Every release page that carries a date, newest first."""
    found = []
    try:
        names = os.listdir(releases_dir)
    except OSError:
        return found
    for name in sorted(names):
        match = RE_VERSION_FILE.match(name)
        if not match:
            continue
        date = released_on(os.path.join(releases_dir, name))
        if date:
            found.append((sort_key(match), name[: -len(".md")], date))
    found.sort(reverse=True)
    return found


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--releases-dir", required=True)
    ap.add_argument("--docs-version", required=True,
                    help="the quarter being written, e.g. 26.8")
    ap.add_argument("--release-date", default="",
                    help="explicit override, e.g. '29 May 2026'")
    ap.add_argument("--published-at", default="",
                    help="published_at of the armbian/build release, if one exists")
    ap.add_argument("--today", default="",
                    help="ISO date to treat as today; defaults to the real clock")
    ap.add_argument("--fallback-months", type=int, default=3)
    args = ap.parse_args()

    today = (datetime.fromisoformat(args.today.replace("Z", "+00:00"))
             if args.today else datetime.now(timezone.utc))

    pages = scan(args.releases_dir)
    this_key = sort_key(RE_VERSION_FILE.match(args.docs_version + ".md"))

    # --- the release date -------------------------------------------------
    # Ordered by how durable each source is, not by convenience.
    date, source = None, None
    if args.release_date:
        date = parse_human(args.release_date)
        if not date:
            print("::error::--release-date {!r} is not of the form "
                  "'29 May 2026'".format(args.release_date), file=sys.stderr)
            return 1
        source = "the release_date input"
    if not date:
        # Already published: its date is a matter of record and must not move.
        for key, _version, when in pages:
            if key == this_key:
                date, source = when, "the published page, which is the record"
                break
    if not date and args.published_at:
        stamp = args.published_at.replace("Z", "+00:00")
        try:
            date = datetime.fromisoformat(stamp)
            source = "the armbian/build release"
        except ValueError:
            date = None
    if not date:
        # A fresh quarter, published the day this runs. Pinned by the page
        # from the next run onwards.
        date, source = today, "today, the day this ran"

    # --- the window -------------------------------------------------------
    previous = next((p for p in pages if p[0] < this_key), None)
    if previous:
        since = previous[2]
        window_source = "the {} page, released {}".format(previous[1], human(since))
    else:
        since = date - timedelta(days=args.fallback_months * 31)
        window_source = ("no earlier release page; falling back to {} months "
                         "before the release".format(args.fallback_months))
        print("::warning title=Release window::No release page older than {}; "
              "the window start is approximate".format(args.docs_version),
              file=sys.stderr)

    # Midnight of the previous release day through the end of this one. The
    # overlap that costs -- a few PRs merged earlier on the previous release
    # day get listed twice -- is deliberate: a duplicate is visible in the
    # page, a dropped PR is not.
    since = since.replace(hour=0, minute=0, second=0, microsecond=0)
    until = date.replace(hour=23, minute=59, second=59, microsecond=0)

    if since >= until:
        print("::error::window start {} is not before its end {}".format(
            since.isoformat(), until.isoformat()), file=sys.stderr)
        return 1

    out = [
        ("RELEASE_DATE", human(date)),
        ("RELEASE_DATE_SOURCE", source),
        ("SINCE_UTC", since.strftime("%Y-%m-%dT%H:%M:%SZ")),
        ("UNTIL_UTC", until.strftime("%Y-%m-%dT%H:%M:%SZ")),
        ("WINDOW_SOURCE", window_source),
    ]
    for key, value in out:
        print("{}={}".format(key, value))
    return 0


if __name__ == "__main__":
    sys.exit(main())
