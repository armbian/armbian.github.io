#!/usr/bin/env python3
"""Ping PR authors about new unresolved review conversations.

For each open, non-draft PR in REPOS: if a review thread was started after the
last ping on that PR (or within LOOKBACK_HOURS, whichever is later) and is still
unresolved, post one comment that asks the author to resolve or dismiss it.

Env: GH_TOKEN, REPOS ("owner/repo ..."), LOOKBACK_HOURS (default 6), DRY_RUN.
"""
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone

MARKER = "<!-- unresolved-review-ping -->"
API = "https://api.github.com"
TOKEN = os.environ["GH_TOKEN"]
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"
LOOKBACK = timedelta(hours=float(os.environ.get("LOOKBACK_HOURS", "6")))

QUERY = """
query($owner: String!, $name: String!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    pullRequests(states: OPEN, first: 30, after: $cursor) {
      pageInfo { hasNextPage endCursor }
      nodes {
        number isDraft url
        author { login __typename }
        reviewThreads(first: 100) {
          nodes {
            isResolved
            comments(first: 1) { nodes { createdAt url author { login } } }
          }
        }
        comments(last: 50) { nodes { createdAt body } }
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


def graphql(variables):
    out = request("POST", f"{API}/graphql", {"query": QUERY, "variables": variables})
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


def new_unresolved(pr, now):
    """Unresolved threads started after the last ping, by someone other than the author."""
    author = (pr.get("author") or {}).get("login", "")
    pings = [ts(c["createdAt"]) for c in pr["comments"]["nodes"] if MARKER in (c.get("body") or "")]
    since = max(pings + [now - LOOKBACK])
    found = []
    for thread in pr["reviewThreads"]["nodes"]:
        first = (thread["comments"]["nodes"] or [None])[0]
        if thread["isResolved"] or not first:
            continue
        reviewer = (first.get("author") or {}).get("login", "")
        if reviewer == author or ts(first["createdAt"]) <= since:
            continue
        found.append((reviewer, first["url"]))
    return found


def comment(repo, pr, threads):
    author = pr["author"]["login"]
    lines = [
        f"@{author} This PR has {len(threads)} new unresolved review "
        f"conversation{'s' if len(threads) != 1 else ''}. "
        "Resolve each one, or reply why it does not apply and resolve it.",
        "",
    ]
    lines += [f"- {url} ({reviewer})" for reviewer, url in threads]
    lines += ["", MARKER]
    body = "\n".join(lines)
    if DRY_RUN:
        print(f"[dry-run] {repo}#{pr['number']}:\n{body}\n")
        return
    request("POST", f"{API}/repos/{repo}/issues/{pr['number']}/comments", {"body": body})
    print(f"pinged {repo}#{pr['number']} @{author}: {len(threads)} thread(s)")


def main():
    now = datetime.now(timezone.utc)
    pinged = 0
    for repo in os.environ["REPOS"].split():
        for pr in open_prs(repo):
            author = pr.get("author") or {}
            if pr["isDraft"] or author.get("__typename") == "Bot" or not author.get("login"):
                continue
            threads = new_unresolved(pr, now)
            if threads:
                comment(repo, pr, threads)
                pinged += 1
    print(f"done: {pinged} PR(s) pinged")


if __name__ == "__main__":
    main()
