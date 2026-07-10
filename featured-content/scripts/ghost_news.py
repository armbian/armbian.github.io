#!/usr/bin/env python3
"""
Ghost News Module - Fetches news from Ghost CMS.

This module can be used standalone or imported by the main orchestrator.
Outputs JSON array of news/contribution entries.
"""
import json
import os
import sys
import urllib.request


def fetch_ghost_news(api_url, limit=5):
    """
    Fetch news posts from Ghost CMS API.

    Args:
        api_url: Ghost CMS API URL (e.g., https://blog.example.com/ghost/api/v3/content/posts/)
        limit: Number of posts to fetch (default: 5)

    Returns:
        List of news post dictionaries
    """
    api_key = os.environ.get('GHOST_API_KEY', os.environ.get('GHOST_ADMIN_API_KEY'))

    if not api_key:
        print("Warning: No Ghost API key found, returning empty list", file=sys.stderr)
        return []

    url = f"{api_url}?key={api_key}&limit={limit}&include=tags,authors"
    headers = {
        'Accept': 'application/json',
        'User-Agent': 'Armbian-Featured-Content/1.0'
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            posts = data.get('posts', [])
            print(f"Fetched {len(posts)} posts from Ghost", file=sys.stderr)
            return posts
    except Exception as e:
        print(f"Error fetching Ghost posts: {e}", file=sys.stderr)
        return []


def process_ghost_news(posts, use_ai=True):
    """
    Process Ghost posts into news entries.

    Args:
        posts: Raw posts data from Ghost API
        use_ai: Whether to use AI to rewrite summaries

    Returns:
        List of news entry dictionaries
    """
    from ai_helper import rewrite_summary_with_ai

    news_entries = []

    for post in posts:
        title = post.get('title', '')
        url = post.get('url', '')
        published_at = post.get('published_at', '')
        excerpt = post.get('excerpt', '')
        feature_image = post.get('feature_image', '')

        # Get author info
        authors = post.get('authors', [])
        author_name = authors[0].get('name', 'Armbian Team') if authors else 'Armbian Team'

        # Get tags
        tags = post.get('tags', [])
        tag_names = [tag.get('name', '') for tag in tags]

        # Get primary tag (first tag)
        primary_tag = tags[0].get('name', '') if tags else ''
        entry_name = primary_tag.replace('-', ' ').title() if primary_tag else 'Armbian News'

        # Use excerpt or create summary from HTML
        summary = excerpt
        if not summary:
            # Could parse HTML content here, but for now use a placeholder
            summary = f"Latest update from {title}"

        # Rewrite summary with AI
        if use_ai:
            summary = rewrite_summary_with_ai(title, summary, entry_name, "news")

        entry = {
            "type": "news",
            "id": f"ghost-{post.get('id', 'unknown')}",
            "name": entry_name,
            "url": url,
            "title": title,
            "summary": summary,
            "published_at": published_at,
            "image": feature_image,
            "author": {"name": author_name},
            "tags": tag_names
        }
        news_entries.append(entry)

    return news_entries


def main():
    """CLI interface for testing Ghost news functionality."""
    import argparse

    parser = argparse.ArgumentParser(description='Fetch Ghost news')
    parser.add_argument('--url', required=True, help='Ghost API URL (e.g., https://blog.example.com/ghost/api/v3/content/posts/)')
    parser.add_argument('--limit', type=int, default=5, help='Number of posts to fetch')
    parser.add_argument('--no-ai', action='store_true', help='Skip AI rewriting')
    args = parser.parse_args()

    print(f"Fetching {args.limit} posts from Ghost...", file=sys.stderr)

    # Fetch posts
    posts = fetch_ghost_news(args.url, args.limit)

    # Process into entries
    entries = process_ghost_news(posts, use_ai=not args.no_ai)

    # Output JSON
    print(json.dumps(entries, indent=2))


if __name__ == "__main__":
    main()
