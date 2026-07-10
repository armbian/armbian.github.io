#!/usr/bin/env python3
"""
Select diverse featured entries from all sources.

Reads multiple JSON files with entries and selects N items from each type.
"""
import json
import random
import sys
from collections import defaultdict
from pathlib import Path


def main():
    if len(sys.argv) < 3:
        print("Usage: select_featured.py <per_category_count> <input1.json> [input2.json] ...")
        sys.exit(1)

    per_category_count = int(sys.argv[1])
    input_files = sys.argv[2:]

    # Load all entries
    all_entries = []
    for input_file in input_files:
        try:
            with open(input_file) as f:
                entries = json.load(f)
                if isinstance(entries, list):
                    all_entries.extend(entries)
                    print(f"Loaded {len(entries)} from {input_file}", file=sys.stderr)
        except Exception as e:
            print(f"Warning: Could not load {input_file}: {e}", file=sys.stderr)

    if not all_entries:
        print("No entries loaded", file=sys.stderr)
        print(json.dumps({"entries": [], "count": 0, "sources": {}}, indent=2))
        sys.exit(0)

    # Group by type
    by_type = defaultdict(list)
    for entry in all_entries:
        entry_type = entry.get('type', 'unknown')
        by_type[entry_type].append(entry)

    # Count sources
    sources = {}
    for entry_type, entries_list in by_type.items():
        sources[entry_type] = len(entries_list)

    # Select N random entries from each type
    selected = []
    random.seed()

    for entry_type, entries in by_type.items():
        # Shuffle and take first N
        random.shuffle(entries)
        count = min(per_category_count, len(entries))
        selected.extend(entries[:count])
        print(f"Selected {count}/{len(entries)} from type '{entry_type}'", file=sys.stderr)

    # Shuffle final selection for variety
    random.shuffle(selected)

    # Output
    output = {
        "entries": selected,
        "count": len(selected),
        "sources": sources
    }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
