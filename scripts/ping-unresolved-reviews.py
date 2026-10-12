#!/usr/bin/env python3
"""Ping PR authors about new unresolved review conversations.

For each open, non-draft PR in REPOS: if a review thread is still unresolved
GRACE_HOURS after it was started, post one comment that asks the author to
resolve or dismiss it. Each ping stores its cutoff time, so the next run checks
only threads started after it (and within LOOKBACK_HOURS).

Env: GH_TOKEN, REPOS ("owner/repo ..."), LOOKBACK_HOURS (default 6),
GRACE_HOURS (default 48), DRY_RUN.
"""
import functools
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

MARKER = "<!-- unresolved-review-ping"  # prefix; new pings append " cutoff=<ISO time> -->"
CUTOFF_RE = re.compile(re.escape(MARKER) + r" cutoff=(\S+) -->")
API = "https://api.github.com"
TOKEN = os.environ["GH_TOKEN"]
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"
LOOKBACK = timedelta(hours=float(os.environ.get("LOOKBACK_HOURS", "6")))
GRACE = timedelta(hours=float(os.environ.get("GRACE_HOURS", "48")))

QUERY = """
query($owner: String!, $name: String!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    pullRequests(states: OPEN, first: 30, after: $cursor) {
      pageInfo { hasNextPage endCursor }
      nodes {
        number isDraft url
        author { login __typename }
        reviewThreads(first: 100) {
          pageInfo { hasNextPage }
          nodes {
            isResolved
            comments(first: 1) { nodes { createdAt url author { login } } }
          }
        }
        comments(last: 50) {
          pageInfo { hasPreviousPage startCursor }
          nodes { createdAt body author { login } }
        }
      }
    }
  }
}
"""

# Older PR comments, newest page first, to find the last ping beyond the first 50
OLDER_COMMENTS = """
query($owner: String!, $name: String!, $number: Int!, $before: String) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      comments(last: 100, before: $before) {
        pageInfo { hasPreviousPage startCursor }
        nodes { createdAt body author { login } }
      }
    }
  }
}
"""


def request(method, url, data=None):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method, headers={
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def graphql(variables, query=QUERY):
    out = request("POST", f"{API}/graphql", {"query": query, "variables": variables})
    if out.get("errors"):
        raise RuntimeError(out["errors"])
    return out["data"]


def ts(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def open_prs(repo):
    owner, name = repo.split("/")
    cursor = None
    while True:
        page = graphql({"owner": owner, "name": name, "cursor": cursor})
        prs = page["repository"]["pullRequests"]
        yield from prs["nodes"]
        if not prs["pageInfo"]["hasNextPage"]:
            return
        cursor = prs["pageInfo"]["endCursor"]


@functools.lru_cache(maxsize=None)
def ping_login():
    """The account that posts pings: the owner of GH_TOKEN."""
    return graphql({}, "query { viewer { login } }")["viewer"]["login"]


def pings_in(nodes):
    """Cutoff of each ping posted by ping_login(): the stored cutoff, but never
    later than the comment, else the comment time (pings made before GRACE_HOURS)."""
    out = []
    for c in nodes:
        body = c.get("body") or ""
        if MARKER not in body or (c.get("author") or {}).get("login") != ping_login():
            continue
        posted = ts(c["createdAt"])
        m = CUTOFF_RE.search(body)
        try:
            cutoff = ts(m.group(1)) if m else posted
        except ValueError:
            cutoff = posted
        out.append(min(cutoff, posted))
    return out


def last_ping(repo, pr):
    """Time of the last ping. Pages back through older comments, else a ping can repeat."""
    page = pr["comments"]
    pings = pings_in(page["nodes"])
    owner, name = repo.split("/")
    while not pings and page["pageInfo"]["hasPreviousPage"]:
        data = graphql({"owner": owner, "name": name, "number": pr["number"],
                        "before": page["pageInfo"]["startCursor"]}, OLDER_COMMENTS)
        page = data["repository"]["pullRequest"]["comments"]
        pings = pings_in(page["nodes"])
    return max(pings) if pings else None


def new_unresolved(repo, pr, now):
    """Threads unresolved for GRACE, started after the last ping cutoff, by someone other than the author."""
    author = (pr.get("author") or {}).get("login", "")
    if pr["reviewThreads"]["pageInfo"]["hasNextPage"]:
        print(f"warning: {repo}#{pr['number']} has more than 100 review threads, later ones are not checked")
    ping = last_ping(repo, pr)
    since = max([now - GRACE - LOOKBACK] + ([ping] if ping else []))
    cutoff = now - GRACE
    found = []
    for thread in pr["reviewThreads"]["nodes"]:
        first = (thread["comments"]["nodes"] or [None])[0]
        if thread["isResolved"] or not first:
            continue
        reviewer = (first.get("author") or {}).get("login", "")
        if reviewer == author or not since < ts(first["createdAt"]) <= cutoff:
            continue
        found.append((reviewer, first["url"]))
    return found


def comment(repo, pr, threads, cutoff):
    author = pr["author"]["login"]
    lines = [
        f"@{author} This PR has {len(threads)} review "
        f"conversation{'s' if len(threads) != 1 else ''} unresolved for more than {GRACE.total_seconds() / 3600:g} hours. "
        "Resolve each one, or reply why it does not apply and resolve it.",
        "",
    ]
    lines += [f"- {url} ({reviewer})" for reviewer, url in threads]
    lines += ["", f"{MARKER} cutoff={cutoff.strftime('%Y-%m-%dT%H:%M:%SZ')} -->"]
    body = "\n".join(lines)
    if DRY_RUN:
        print(f"[dry-run] {repo}#{pr['number']}:\n{body}\n")
        return
    request("POST", f"{API}/repos/{repo}/issues/{pr['number']}/comments", {"body": body})
    print(f"pinged {repo}#{pr['number']} @{author}: {len(threads)} thread(s)")


def main():
    """Scan all repositories. Return 1 if any PR or repository failed, else 0."""
    now = datetime.now(timezone.utc)
    pinged = failed = 0
    for repo in os.environ["REPOS"].split():
        try:
            for pr in open_prs(repo):
                author = pr.get("author") or {}
                if pr["isDraft"] or author.get("__typename") == "Bot" or not author.get("login"):
                    continue
                try:
                    threads = new_unresolved(repo, pr, now)
                    if threads:
                        comment(repo, pr, threads, now - GRACE)
                        pinged += 1
                except Exception as e:  # noqa: BLE001 - one PR must not stop the scan
                    print(f"error: {repo}#{pr['number']}: {e}")
                    failed += 1
        except Exception as e:  # noqa: BLE001 - one repository must not stop the scan
            print(f"error: {repo}: {e}")
            failed += 1
    print(f"done: {pinged} PR(s) pinged, {failed} error(s)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
