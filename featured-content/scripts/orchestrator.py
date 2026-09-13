#!/usr/bin/env python3
"""
Featured Content Orchestrator - Main script that merges all content sources.

This script:
1. Fetches content from multiple sources (releases, news, forum, sponsors, software, manual)
2. Merges all entries into a unified list
3. Selects a subset of entries (3-5) with type diversity
4. Outputs final featured-content.json
"""
import argparse
import json
import os
import random
import sys
from typing import List, Dict, Any


def fetch_all_content(config_file: str, forum_url: str, ghost_url: str,
                      software_limit: int = 10, releases_limit: int = 5,
                      sponsors_limit: int = 10, forum_limit: int = 5,
                      ghost_limit: int = 5, use_ai: bool = True) -> tuple:
    """
    Fetch content from all available sources.

    Args:
        config_file: Path to config.software.json
        forum_url: Discourse forum URL
        ghost_url: Ghost CMS API URL
        software_limit: Max software entries to fetch
        releases_limit: Max releases to fetch
        sponsors_limit: Max sponsors to fetch
        forum_limit: Max forum posts to fetch
        ghost_limit: Max news posts to fetch
        use_ai: Whether to use AI rewriting

    Returns:
        Tuple of (all_entries, counts_dict) where counts_dict has actual counts per source
    """
    all_entries = []
    counts = {
        "github_releases": 0,
        "ghost_news": 0,
        "forum_posts": 0,
        "sponsors": 0,
        "software": 0,
        "manual": 0
    }

    # Import modules
    import github_releases
    import ghost_news
    import sponsors
    import software_list
    import manual_list

    # Conditionally import forum_posts if forum_url is provided
    if forum_url:
        import forum_posts

    # 1. GitHub Releases
    print("Fetching GitHub releases...", file=sys.stderr)
    releases = github_releases.fetch_releases(limit=releases_limit)
    if releases:
        release_entries = github_releases.process_releases(releases, limit=releases_limit, use_ai=use_ai)
        all_entries.extend(release_entries)
        counts["github_releases"] = len(release_entries)
        print(f"  Added {len(release_entries)} release entries", file=sys.stderr)

    # 2. Ghost News
    if ghost_url:
        print("Fetching Ghost news...", file=sys.stderr)
        posts = ghost_news.fetch_ghost_news(ghost_url, limit=ghost_limit)
        if posts:
            news_entries = ghost_news.process_ghost_news(posts, use_ai=use_ai)
            all_entries.extend(news_entries)
            counts["ghost_news"] = len(news_entries)
            print(f"  Added {len(news_entries)} news entries", file=sys.stderr)

    # 3. Forum Posts
    if forum_url:
        print("Fetching forum posts...", file=sys.stderr)
        topics, users = forum_posts.fetch_promoted_posts(forum_url, limit=forum_limit)
        if topics:
            forum_entries = forum_posts.process_forum_posts(topics, users, use_ai=use_ai)
            all_entries.extend(forum_entries)
            counts["forum_posts"] = len(forum_entries)
            print(f"  Added {len(forum_entries)} forum entries", file=sys.stderr)

    # 4. GitHub Sponsors
    print("Fetching GitHub sponsors...", file=sys.stderr)
    sponsor_data = sponsors.fetch_sponsors(limit=sponsors_limit)
    if sponsor_data:
        sponsor_entries = sponsors.process_sponsors(sponsor_data, use_ai=use_ai)
        all_entries.extend(sponsor_entries)
        counts["sponsors"] = len(sponsor_entries)
        print(f"  Added {len(sponsor_entries)} sponsor entries", file=sys.stderr)

    # 5. Software List from Armbian config
    if config_file and os.path.exists(config_file):
        print(f"Loading software config from {config_file}...", file=sys.stderr)
        config = software_list.load_software_config(config_file)
        if config:
            software_entries = software_list.process_software_entries(
                config, limit=software_limit, featured_only=True, use_ai=use_ai
            )
            all_entries.extend(software_entries)
            counts["software"] = len(software_entries)
            print(f"  Added {len(software_entries)} software entries", file=sys.stderr)

    # 6. Manual curated entries
    print("Loading manual featured entries...", file=sys.stderr)
    # Look in parent directory (featured-content/) for manual_featured.yml
    import os
    manual_path = os.path.join(os.path.dirname(__file__), '..', 'manual_featured.yml')
    manual_data = manual_list.load_manual_list(manual_path)
    if manual_data:
        manual_entries = manual_list.process_manual_entries(manual_data, use_ai=use_ai)
        all_entries.extend(manual_entries)
        counts["manual"] = len(manual_entries)
        print(f"  Added {len(manual_entries)} manual entries", file=sys.stderr)

    return all_entries, counts


def select_diverse_entries(entries: List[Dict[str, Any]], target_count: int = 5) -> List[Dict[str, Any]]:
    """
    Select a diverse subset of entries by type with randomization.

    Args:
        entries: All available entries
        target_count: Target number of entries to select

    Returns:
        Selected entries with type diversity and randomness
    """
    if not entries:
        return []

    # Group entries by type
    by_type: Dict[str, List[Dict[str, Any]]] = {}
    for entry in entries:
        entry_type = entry.get('type', 'unknown')
        if entry_type not in by_type:
            by_type[entry_type] = []
        by_type[entry_type].append(entry)

    # Shuffle each type list
    for entry_type in by_type:
        random.shuffle(by_type[entry_type])

    # Create a pool of all entries with their types
    pool = []
    for entry_type, entries_list in by_type.items():
        for entry in entries_list:
            pool.append((entry_type, entry))

    # Shuffle the entire pool for randomness
    random.shuffle(pool)

    # Select entries ensuring type diversity
    selected = []
    used_types = set()
    diversifying = True

    for entry_type, entry in pool:
        if len(selected) >= target_count:
            break

        # While diversifying, try to get one from each type first
        if diversifying:
            if entry_type not in used_types:
                selected.append(entry)
                used_types.add(entry_type)

                # Once we've seen all types, stop diversifying
                if len(used_types) == len(by_type):
                    diversifying = False
        else:
            # After diversity achieved, take anything
            selected.append(entry)

    # If we still don't have enough, just add more entries
    if len(selected) < target_count:
        for entry in entries:
            if entry not in selected:
                selected.append(entry)
            if len(selected) >= target_count:
                break

    return selected


def sort_entries(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sort entries by type for consistent output.

    Args:
        entries: Entries to sort

    Returns:
        Sorted entries
    """
    type_order = {
        'software': 0,
        'contribution': 1,
        'news': 2,
        'discussion': 3,
        'sponsor': 4,
        'manual': 5
    }

    def sort_key(entry):
        entry_type = entry.get('type', 'unknown')
        return type_order.get(entry_type, 999)

    return sorted(entries, key=sort_key)


def main():
    """CLI interface for orchestrator."""
    parser = argparse.ArgumentParser(description='Featured Content Orchestrator')
    parser.add_argument('--config', default='config.software.json', help='Path to config.software.json')
    parser.add_argument('--forum-url', help='Discourse forum URL (e.g., https://forum.armbian.com)')
    parser.add_argument('--ghost-url', help='Ghost CMS API URL')
    parser.add_argument('--software-limit', type=int, default=10, help='Max software entries')
    parser.add_argument('--releases-limit', type=int, default=5, help='Max releases to fetch')
    parser.add_argument('--sponsors-limit', type=int, default=10, help='Max sponsors to fetch')
    parser.add_argument('--forum-limit', type=int, default=5, help='Max forum posts')
    parser.add_argument('--ghost-limit', type=int, default=5, help='Max news posts')
    parser.add_argument('--count', type=int, default=5, help='Target number of final entries')
    parser.add_argument('--no-ai', action='store_true', help='Skip AI rewriting')
    parser.add_argument('--no-shuffle', action='store_true', help='Disable randomization (useful for testing)')
    parser.add_argument('--all', action='store_true', help='Output all entries (no selection)')
    args = parser.parse_args()

    # Set random seed for reproducibility (unless disabled)
    if not args.no_shuffle:
        random.seed()

    print("=== Featured Content Orchestrator ===", file=sys.stderr)
    print(f"Target entries: {args.count}", file=sys.stderr)
    print(f"AI rewriting: {not args.no_ai}", file=sys.stderr)

    # Fetch all content
    all_entries, counts = fetch_all_content(
        config_file=args.config,
        forum_url=args.forum_url,
        ghost_url=args.ghost_url,
        software_limit=args.software_limit,
        releases_limit=args.releases_limit,
        sponsors_limit=args.sponsors_limit,
        forum_limit=args.forum_limit,
        ghost_limit=args.ghost_limit,
        use_ai=not args.no_ai
    )

    print(f"\nTotal entries fetched: {len(all_entries)}", file=sys.stderr)

    if not all_entries:
        print("No entries fetched, outputting empty array", file=sys.stderr)
        print("[]")
        return

    # Select subset (unless --all specified)
    if args.all:
        final_entries = all_entries
    else:
        final_entries = select_diverse_entries(all_entries, target_count=args.count)

    print(f"Selected {len(final_entries)} entries for output", file=sys.stderr)

    # Sort by type
    final_entries = sort_entries(final_entries)

    # Output JSON
    output = {
        "entries": final_entries,
        "count": len(final_entries),
        "sources": counts
    }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
