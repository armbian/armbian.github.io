#!/usr/bin/env python3
import sys
import requests
from datetime import datetime, timezone

API = "https://api.github.com"


def gh_get(url, token, params=None):
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "org-last-commit-check",
    }
    r = requests.get(url, headers=headers, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def get_all_repos(org, token):
    repos = []
    page = 1
    while True:
        batch = gh_get(
            f"{API}/orgs/{org}/repos",
            token,
            params={"per_page": 100, "page": page, "type": "all"},
        )
        if not batch:
            break
        repos.extend(batch)
        page += 1
    return repos


def get_latest_commit_date(org, repo, user, token):
    commits = gh_get(
        f"{API}/repos/{org}/{repo}/commits",
        token,
        params={"author": user, "per_page": 1},
    )
    if not commits:
        return None

    # commit.author.date is ISO8601
    return commits[0]["commit"]["author"]["date"]


def days_since_last_commit(org, user, token):
    repos = get_all_repos(org, token)

    latest_date = None
    latest_repo = None

    for repo in repos:
        name = repo["name"]
        try:
            date_str = get_latest_commit_date(org, name, user, token)
            if date_str:
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                if not latest_date or dt > latest_date:
                    latest_date = dt
                    latest_repo = name
        except Exception as e:
            print(f"[WARN] {name}: {e}", file=sys.stderr)

    if not latest_date:
        return None, None

    now = datetime.now(timezone.utc)
    return (now - latest_date).days, latest_repo


def main():
    days_only = "--days-only" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--days-only"]

    if len(args) != 3:
        print("Usage: script.py [--days-only] ORG USER TOKEN")
        sys.exit(1)

    org, user, token = args[0], args[1], args[2]
    delta_days, latest_repo = days_since_last_commit(org, user, token)

    if delta_days is None:
        if days_only:
            print(-1)
        else:
            print(f"No commits found for {user} in org {org}")
        sys.exit(0)

    if days_only:
        print(delta_days)
    else:
        print(f"Repository: {org}/{latest_repo}")
        print(f"Days since last commit: {delta_days}")


if __name__ == "__main__":
    main()
