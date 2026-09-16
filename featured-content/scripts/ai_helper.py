#!/usr/bin/env python3
"""
AI Helper Module - Provides AI-powered content rewriting functionality.

This module can be used standalone to rewrite content, or imported by other modules.
"""
import json
import os
import sys


def rewrite_summary_with_ai(title, summary, entry_name, entry_type="software"):
    """
    Use AI to rewrite summary as engaging description.

    Args:
        title: The original title
        summary: The original summary to rewrite
        entry_name: Name of the software/item
        entry_type: Type of entry ("software" or "contribution")

    Returns:
        Rewritten summary string, or original if AI fails
    """
    api_key = os.environ.get('GEMINI_API_KEY')

    if not api_key:
        print(f"  No API key found, keeping original summary", file=sys.stderr)
        return summary

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        model_name = 'gemini-2.5-flash'

        # Create context-specific prompt
        if entry_type == "contribution":
            context = f"""Convert the title and summary into an engaging description.

Title: {title}
Summary: {summary[:200]}

Requirements:
- 15 to 80 characters
- Return ONLY the description text"""
        else:
            context = f"""Convert the title and summary into an engaging description.

Software: {entry_name}
Title: {title}
Summary: {summary}

Requirements:
- 15 to 80 characters
- Make it engaging and informative"""

        response = client.models.generate_content(
            model=model_name,
            contents=context,
            config=types.GenerateContentConfig(
                temperature=0.9,
                max_output_tokens=100,
            )
        )

        # Handle empty or blocked responses
        if response.text is None:
            print(f"  AI returned empty response, using original summary", file=sys.stderr)
            return summary

        new_summary = response.text.strip().strip('"\'')
        # Remove any markdown formatting
        import re
        new_summary = re.sub(r'^[\*\_\-]+|[\*\_\-]+$', '', new_summary).strip()

        # Ensure it's under 80 chars and not empty
        if len(new_summary) > 80:
            new_summary = new_summary[:77] + "..."

        if not new_summary or len(new_summary) < 15:
            print(f"  AI returned too short result, using original summary", file=sys.stderr)
            return summary

        print(f"  AI summary rewrite: '{summary[:30]}...' -> '{new_summary}' ({len(new_summary)} chars)")
        return new_summary

    except ImportError as e:
        print(f"  AI rewrite failed: google-genai not installed ({e}), using original summary", file=sys.stderr)
        return summary
    except Exception as e:
        print(f"  AI rewrite failed: {e}, using original summary", file=sys.stderr)
        return summary


def process_entries_with_ai(entries):
    """
    Process a list of entries and rewrite their summaries with AI.

    Args:
        entries: List of entry dictionaries with 'title', 'summary', 'name', 'type' keys

    Returns:
        List of entries with rewritten summaries (adds 'summary_original' key)
    """
    for entry in entries:
        if 'summary' in entry:
            original_summary = entry['summary']
            entry['summary'] = rewrite_summary_with_ai(
                entry.get('title', ''),
                original_summary,
                entry.get('name', ''),
                entry.get('type', 'software')
            )
            entry['summary_original'] = original_summary  # Keep original for reference

    return entries


def main():
    """CLI interface for testing AI functionality."""
    if len(sys.argv) < 3:
        print("Usage: ai_helper.py <title> <summary> [entry_name] [entry_type]")
        print("Example: ai_helper.py 'My Software' 'This is a description.' 'MySoftware' software")
        sys.exit(1)

    title = sys.argv[1]
    summary = sys.argv[2]
    entry_name = sys.argv[3] if len(sys.argv) > 3 else title
    entry_type = sys.argv[4] if len(sys.argv) > 4 else "software"

    result = rewrite_summary_with_ai(title, summary, entry_name, entry_type)
    print(f"\nOriginal: {summary}")
    print(f"Rewritten: {result}")


if __name__ == "__main__":
    main()
