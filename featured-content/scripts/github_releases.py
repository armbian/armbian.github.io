#!/usr/bin/env python3
"""
GitHub Releases Module - Fetches Armbian build releases from GitHub API.

This module can be used standalone or imported by the main orchestrator.
Outputs JSON array of contribution entries.
"""
import json
import os
import sys
import re


def fetch_releases(limit=5):
    """
    Fetch Armbian build releases from GitHub API.

    Args:
        limit: Number of releases to fetch (default: 5)

    Returns:
        List of contribution entry dictionaries
    """
    import urllib.request

    url = f"https://api.github.com/repos/armbian/build/releases?per_page={limit}"

    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            print(f"Fetched {len(data)} releases from GitHub", file=sys.stderr)
            return data
    except Exception as e:
        print(f"Error fetching releases: {e}", file=sys.stderr)
        return []


def process_releases(releases, limit=5, use_ai=True):
    """
    Process GitHub releases into contribution entries.

    Args:
        releases: Raw releases data from GitHub API
        limit: Maximum number of releases to process
        use_ai: Whether to use AI to rewrite summaries

    Returns:
        List of contribution entry dictionaries
    """
    contribution_entries = []

    for release in releases[:limit]:
        if release.get('prerelease', False):
            continue

        tag_name = release.get('tag_name', 'unknown')
        name = release.get('name', '') or tag_name
        body = release.get('body', '')
        html_url = release.get('html_url', '')
        published_at = release.get('published_at', '')

        # Extract key highlights from release body
        highlights = []
        if body:
            lines = body.split('\n')
            for line in lines:
                line = line.strip()
                if re.match(r'^[\*\-\+•]\s+\*\*', line):
                    match = re.search(r'\*\*(.+?)\*\*', line)
                    if match:
                        highlights.append(match.group(1))
                elif re.match(r'^\d+\.\s+', line):
                    highlights.append(line.split(' ', 1)[1][:100] if len(line.split(' ', 1)) > 1 else line[:100])

                if len(highlights) >= 3:
                    break

        # Create a summary from body
        summary = body[:200].strip() + '...' if len(body) > 200 else body.strip()
        if not summary:
            summary = f"Armbian release {tag_name} with various improvements and bug fixes."

        contribution = {
            "type": "contribution",
            "id": f"release-{tag_name}",
            "name": name,
            "url": html_url,
            "title": f"Armbian {name} Released",
            "summary": summary,
            "published_at": published_at,
            "highlights": highlights[:3],
            "tags": ["release", "update", "armbian"]
        }
        contribution_entries.append(contribution)

    return contribution_entries


def main():
    """CLI interface for testing GitHub releases functionality."""
    import argparse

    parser = argparse.ArgumentParser(description='Fetch GitHub releases')
    parser.add_argument('--limit', type=int, default=5, help='Number of releases to fetch')
    parser.add_argument('--no-ai', action='store_true', help='Skip AI rewriting')
    args = parser.parse_args()

    print(f"Fetching {args.limit} releases from GitHub...", file=sys.stderr)

    # Fetch releases
    releases = fetch_releases(args.limit)

    # Process into entries
    entries = process_releases(releases, args.limit, use_ai=not args.no_ai)

    # Output JSON
    print(json.dumps(entries, indent=2))


if __name__ == "__main__":
    main()
