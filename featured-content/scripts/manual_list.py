#!/usr/bin/env python3
"""
Manual List Module - Manually curated featured software entries.

This module can be used standalone or imported by the main orchestrator.
Reads from YAML file and outputs JSON array of manual software entries.

YAML format example:
    entries:
      - id: my-software
        name: "My Software"
        type: software
        url: https://example.com
        title: "Amazing Software"
        summary: "Brief description"
        author:
          name: "Author Name"
          handle: "@author"
        tags: [tag1, tag2]
        motd:
          line: "Message line"
          hint: "Hint text"
"""
import json
import os
import sys

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


def load_manual_list(manual_path='manual_featured.yml'):
    """
    Load manually curated featured entries from YAML file.

    Args:
        manual_path: Path to manual featured YAML file

    Returns:
        Dictionary containing manual entries data
    """
    if not os.path.exists(manual_path):
        print(f"Warning: {manual_path} not found, returning empty list", file=sys.stderr)
        return {"entries": []}

    if not HAS_YAML:
        print(f"Warning: PyYAML not installed, run 'pip install pyyaml'", file=sys.stderr)
        return {"entries": []}

    try:
        with open(manual_path, 'r') as f:
            data = yaml.safe_load(f)
            # Handle nested structure (armbian_featured_software.entries)
            if isinstance(data, dict):
                # Check for nested structure
                if 'armbian_featured_software' in data:
                    entries = data['armbian_featured_software'].get('entries', [])
                else:
                    entries = data.get('entries', [])
            elif isinstance(data, list):
                entries = data
            else:
                entries = []
            print(f"Loaded {len(entries)} manual entries from YAML", file=sys.stderr)
            return {"entries": entries}
    except Exception as e:
        print(f"Error loading manual list: {e}", file=sys.stderr)
        return {"entries": []}


def process_manual_entries(data, use_ai=True):
    """
    Process manual entries into featured entries.

    Args:
        data: Data dictionary containing entries array
        use_ai: Whether to use AI to rewrite summaries

    Returns:
        List of software entry dictionaries
    """
    from ai_helper import rewrite_summary_with_ai

    entries = data.get('entries', [])
    manual_entries = []

    for entry in entries:
        entry_type = entry.get('type', 'software')
        name = entry.get('name', entry.get('id', ''))
        title = entry.get('title', name)
        summary = entry.get('summary', '')
        url = entry.get('url', '')
        entry_id = entry.get('id', name)

        # Get author
        author_data = entry.get('author', {})
        if isinstance(author_data, dict):
            author = {"name": author_data.get('name', 'Armbian'), "handle": author_data.get('handle', '')}
        else:
            author = {"name": 'Armbian'}

        # Get tags
        tags = entry.get('tags', [])
        if not isinstance(tags, list):
            tags = []

        # Get motd
        motd = entry.get('motd', {})
        if not motd or not isinstance(motd, dict):
            motd = {"line": f"Featured: {name}", "hint": ""}

        # Rewrite summary with AI
        summary = rewrite_summary_with_ai(title, summary, name, entry_type)

        manual_entry = {
            "type": entry_type,
            "id": entry_id,
            "name": name,
            "url": url,
            "title": title,
            "summary": summary,
            "author": author,
            "tags": tags,
            "motd": motd,
            "manual": True  # Mark as manual entry
        }
        manual_entries.append(manual_entry)

    return manual_entries


def main():
    """CLI interface for testing manual list functionality."""
    import argparse

    parser = argparse.ArgumentParser(description='Load manual featured entries from YAML')
    parser.add_argument('--file', default='manual_featured.yml', help='Path to manual featured YAML file')
    parser.add_argument('--no-ai', action='store_true', help='Skip AI rewriting')
    args = parser.parse_args()

    print(f"Loading manual entries from {args.file}...", file=sys.stderr)

    # Load data
    data = load_manual_list(args.file)

    # Process entries
    entries = process_manual_entries(data, use_ai=not args.no_ai)

    # Output JSON
    print(json.dumps(entries, indent=2))


if __name__ == "__main__":
    main()
