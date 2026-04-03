#!/usr/bin/env python3
import sys
import requests
from datetime import datetime, timezone

API = "https://api.github.com"


def days_since_last_commit(org, user, token):
    headers = {
        "Accept": "application/vnd.github.cloak-preview+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "org-last-commit-check",
    }
    r = requests.get(
        f"{API}/search/commits",
        headers=headers,
        params={"q": f"author:{user} org:{org}", "sort": "author-date", "order": "desc", "per_page": 1},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()

    if data.get("total_count", 0) == 0:
        return None

    date_str = data["items"][0]["commit"]["author"]["date"]
    dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    return (datetime.now(timezone.utc) - dt).days


def main():
    days_only = "--days-only" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--days-only"]

    if len(args) != 3:
        print("Usage: script.py [--days-only] ORG USER TOKEN")
        sys.exit(1)

    org, user, token = args[0], args[1], args[2]
    delta_days = days_since_last_commit(org, user, token)

    if delta_days is None:
        if days_only:
            print(-1)
        else:
            print(f"No commits found for {user} in org {org}")
        sys.exit(0)

    if days_only:
        print(delta_days)
    else:
        print(f"Days since last commit: {delta_days}")


if __name__ == "__main__":
    main()
