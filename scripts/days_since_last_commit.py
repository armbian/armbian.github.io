#!/usr/bin/env python3
import sys
import time
import requests
from datetime import datetime, timezone

API = "https://api.github.com"


def search_with_retry(url, headers, params, retries=5):
    for attempt in range(retries):
        r = requests.get(url, headers=headers, params=params, timeout=30)

        if r.status_code == 403:
            retry_after = int(r.headers.get("Retry-After", 10 * (2 ** attempt)))
            print(f"Rate limited, retrying in {retry_after}s (attempt {attempt + 1}/{retries})...", file=sys.stderr)
            time.sleep(retry_after)
            continue

        if r.status_code == 422:
            return None

        r.raise_for_status()
        return r.json()

    return None


def get_latest_commit_date(org, user, headers):
    data = search_with_retry(
        f"{API}/search/commits", headers,
        {"q": f"author:{user} org:{org}", "sort": "author-date", "order": "desc", "per_page": 1},
    )
    if not data or data.get("total_count", 0) == 0:
        return None
    date_str = data["items"][0]["commit"]["author"]["date"]
    return datetime.fromisoformat(date_str.replace("Z", "+00:00"))


def get_latest_issue_date(org, user, headers):
    data = search_with_retry(
        f"{API}/search/issues", headers,
        {"q": f"author:{user} org:{org}", "sort": "created", "order": "desc", "per_page": 1},
    )
    if not data or data.get("total_count", 0) == 0:
        return None
    date_str = data["items"][0]["created_at"]
    return datetime.fromisoformat(date_str.replace("Z", "+00:00"))


def get_latest_comment_date(org, user, headers):
    data = search_with_retry(
        f"{API}/search/issues", headers,
        {"q": f"commenter:{user} org:{org}", "sort": "updated", "order": "desc", "per_page": 1},
    )
    if not data or data.get("total_count", 0) == 0:
        return None
    date_str = data["items"][0]["updated_at"]
    return datetime.fromisoformat(date_str.replace("Z", "+00:00"))


def days_since_last_activity(org, user, token):
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "org-activity-check",
    }

    dates = []
    for fetch in (get_latest_commit_date, get_latest_issue_date, get_latest_comment_date):
        dt = fetch(org, user, headers)
        if dt:
            dates.append(dt)
        time.sleep(1)

    if not dates:
        return None

    latest = max(dates)
    return (datetime.now(timezone.utc) - latest).days


def main():
    days_only = "--days-only" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--days-only"]

    if len(args) != 3:
        print("Usage: script.py [--days-only] ORG USER TOKEN")
        sys.exit(1)

    org, user, token = args[0], args[1], args[2]
    delta_days = days_since_last_activity(org, user, token)

    if delta_days is None:
        if days_only:
            print(-1)
        else:
            print(f"No activity found for {user} in org {org}")
        sys.exit(0)

    if days_only:
        print(delta_days)
    else:
        print(f"Days since last activity: {delta_days}")


if __name__ == "__main__":
    main()
