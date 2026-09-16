#!/usr/bin/env python3
"""
Software List Module - Extracts software entries from Armbian config.json.

This module can be used standalone or imported by the main orchestrator.
Outputs JSON array of software entries.

Handles the actual config.software.json structure with nested menu format.
"""
import json
import os
import sys


def load_software_config(config_path='config.software.json'):
    """
    Load software configuration from Armbian config.json file.

    Args:
        config_path: Path to config.software.json file

    Returns:
        Dictionary containing software configuration data
    """
    if not os.path.exists(config_path):
        print(f"Error: {config_path} not found", file=sys.stderr)
        return {}

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            print(f"Loaded software config from {config_path}", file=sys.stderr)
            return config
    except Exception as e:
        print(f"Error loading config: {e}", file=sys.stderr)
        return {}


def extract_software_from_menu(menu_items, parent_id=""):
    """
    Recursively extract software items from menu structure.

    Args:
        menu_items: List of menu items (can be nested)
        parent_id: Parent menu ID for context

    Returns:
        List of software entry dictionaries
    """
    software_entries = []

    for item in menu_items:
        item_id = item.get('id', '')
        description = item.get('description', '')
        short = item.get('short', description)
        author = item.get('author', '')
        status = item.get('status', '')

        # Check if this has nested items (submenu)
        if 'sub' in item:
            # Recursively process submenu
            software_entries.extend(
                extract_software_from_menu(item['sub'], item_id)
            )

        # Only include first item in each software group (xxx001 = install)
        # Skip xxx002, xxx003, etc. which are remove/purge/config actions
        if not item_id.endswith('001'):
            continue

        # Skip remove/purge/uninstall/disable actions
        name_lower = (short or description).lower()
        skip_keywords = ['remove', 'purge', 'uninstall', 'disable']
        if any(keyword in name_lower for keyword in skip_keywords):
            continue

        # Only include items that look like installable software
        # They typically have a module, command, or are not just containers
        is_container = 'sub' in item and not item.get('module')

        if not is_container and item_id:
            # Build entry
            entry = {
                'id': item_id,
                'name': short or description,
                'description': description,
                'author': author,
                'status': status,
                'parent_menu': parent_id
            }

            # Get URL if available (from about or other fields)
            about = item.get('about', '')
            if about and about.startswith('http'):
                entry['url'] = about

            software_entries.append(entry)

    return software_entries


def process_software_entries(config, limit=None, featured_only=True, use_ai=True):
    """
    Process software entries from Armbian config into featured entries.

    Args:
        config: Loaded configuration dictionary
        limit: Maximum number of entries to process (default: all)
        featured_only: Only include entries marked as featured (not used for menu format)
        use_ai: Whether to use AI to rewrite summaries

    Returns:
        List of software entry dictionaries
    """
    from ai_helper import rewrite_summary_with_ai

    # Extract all software from menu structure
    menu = config.get('menu', [])
    all_software = extract_software_from_menu(menu)

    print(f"Found {len(all_software)} software items in menu", file=sys.stderr)

    # For menu format, we'll feature items from key categories
    # Priority categories that contain popular software
    featured_categories = {
        'DNS', 'Backup', 'Media', 'Smart Home', 'Cloud',
        'Containers', 'Desktop', 'Network', 'Security'
    }

    # Filter to items in featured categories or with high-quality metadata
    featured_items = []
    for item in all_software:
        parent = item.get('parent_menu', '')
        name = item.get('name', '').lower()
        description = item.get('description', '').lower()

        # Include if in featured category or has good metadata
        if (parent in featured_categories or
            item.get('status') == 'Stable' or
            any(cat in name or cat in description for cat in
                ['server', 'cloud', 'dns', 'media', 'home', 'backup', 'docker', 'desktop'])):
            featured_items.append(item)

    print(f"Filtered to {len(featured_items)} featured items", file=sys.stderr)

    # Shuffle for variety (if not using AI, we want some randomness)
    import random
    random.shuffle(featured_items)

    # Apply limit
    if limit:
        featured_items = featured_items[:limit]

    # Convert to featured entry format
    software_entries = []
    for item in featured_items:
        item_id = item.get('id', '')
        name = item.get('name', item_id)
        description = item.get('description', f'{name} software for ARM devices')
        url = item.get('url', '')
        author_name = item.get('author', 'Armbian').lstrip('@')

        # Clean up author handle
        author_handle = item.get('author', '').lstrip('@')

        # Determine tags based on parent category and keywords
        parent = item.get('parent_menu', '')
        desc_lower = description.lower()

        tags = [parent.lower()] if parent else []

        # Add keyword-based tags
        keyword_tags = {
            'dns': 'dns',
            'backup': 'backup',
            'media': 'media',
            'server': 'server',
            'cloud': 'cloud',
            'home': 'smart-home',
            'container': 'containers',
            'docker': 'containers',
            'desktop': 'desktop',
            'network': 'networking',
            'security': 'security',
            'privacy': 'privacy'
        }

        for keyword, tag in keyword_tags.items():
            if keyword in desc_lower and tag not in tags:
                tags.append(tag)

        # Create motd
        motd_line = f"Featured: {name}"
        motd_hint = "armbian-config → Software"

        # Rewrite summary with AI
        title = name
        summary = rewrite_summary_with_ai(title, description, name, "software")

        software_entry = {
            "type": "software",
            "id": item_id,
            "name": name,
            "url": url,
            "title": title,
            "summary": summary,
            "author": {
                "name": author_name,
                "handle": author_handle
            },
            "tags": tags[:5],  # Limit to 5 tags
            "motd": {
                "line": motd_line,
                "hint": motd_hint
            }
        }
        software_entries.append(software_entry)

    print(f"Processed {len(software_entries)} software entries", file=sys.stderr)
    return software_entries


def main():
    """CLI interface for testing software list functionality."""
    import argparse

    parser = argparse.ArgumentParser(description='Extract software from Armbian config')
    parser.add_argument('--config', default='config.software.json', help='Path to config.software.json')
    parser.add_argument('--limit', type=int, help='Limit number of entries')
    parser.add_argument('--all', action='store_true', help='Include all entries (not just featured)')
    parser.add_argument('--no-ai', action='store_true', help='Skip AI rewriting')
    args = parser.parse_args()

    print("Loading software configuration...", file=sys.stderr)

    # Load config
    config = load_software_config(args.config)

    # Process entries
    entries = process_software_entries(
        config,
        limit=args.limit,
        featured_only=not args.all,
        use_ai=not args.no_ai
    )

    # Output JSON
    print(json.dumps(entries, indent=2))


if __name__ == "__main__":
    main()
