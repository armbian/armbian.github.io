#!/usr/bin/env python3
"""
GitHub Sponsors Module - Fetches sponsors for armbian/build.

This module can be used standalone or imported by the main orchestrator.
Outputs JSON array of sponsor entries.
"""
import json
import os
import sys
import urllib.request


def fetch_sponsors(repo="armbian/build", limit=10):
    """
    Fetch sponsors from GitHub Sponsors API.

    Args:
        repo: GitHub repository (default: armbian/build)
        limit: Number of sponsors to fetch (default: 10)

    Returns:
        List of sponsor dictionaries
    """
    # GitHub GraphQL API for sponsors
    api_key = os.environ.get('GITHUB_TOKEN')
    if not api_key:
        print("Error: GITHUB_TOKEN environment variable not set", file=sys.stderr)
        print("Hint: Ensure the workflow has: GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}", file=sys.stderr)
        return []

    # Debug: Show token presence (truncated for security)
    token_preview = api_key[:8] + "..." if len(api_key) > 8 else "..."
    print(f"Debug: GITHUB_TOKEN found: {token_preview} (len={len(api_key)})", file=sys.stderr)

    # GraphQL query for organization sponsors (as maintainer receiving sponsors)
    query = {
        "query": f"""
        {{
          organization(login: "armbian") {{
            sponsorshipsAsMaintainer(first: {limit}, includePrivate: true) {{
              nodes {{
                createdAt
                sponsorEntity {{
                  __typename
                  ... on Organization {{
                    name
                    login
                    url
                    description
                    avatarUrl
                    location
                    websiteUrl
                  }}
                  ... on User {{
                    name
                    login
                    url
                    avatarUrl
                    location
                    websiteUrl
                  }}
                }}
                tier {{
                  monthlyPriceInDollars
                  name
                  description
                }}
              }}
            }}
          }}
        }}
        """
    }

    url = "https://api.github.com/graphql"
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'User-Agent': 'Armbian-Featured-Content/1.0'
    }

    try:
        print(f"Debug: Sending request to {url}", file=sys.stderr)
        req = urllib.request.Request(url, headers=headers, data=json.dumps(query).encode())
        with urllib.request.urlopen(req) as response:
            status = response.status
            body = response.read().decode()
            print(f"Debug: Response status: {status}", file=sys.stderr)
            print(f"Debug: Response length: {len(body)} bytes", file=sys.stderr)

            data = json.loads(body)

            # Debug: Show full response for small responses
            if len(body) < 200:
                print(f"Debug: Full response: {body}", file=sys.stderr)

            # Debug: Show response structure
            if 'errors' in data:
                print(f"Debug: GraphQL errors:", file=sys.stderr)
                for err in data.get('errors', []):
                    print(f"  - {err.get('message', 'Unknown error')}", file=sys.stderr)
                    if 'type' in err:
                        print(f"    Type: {err['type']}", file=sys.stderr)
                    if 'path' in err:
                        print(f"    Path: {err['path']}", file=sys.stderr)

            org_data = data.get('data', {}).get('organization')
            if not org_data:
                print("Debug: No 'organization' in response data", file=sys.stderr)
                print(f"Debug: Available keys in data: {list(data.get('data', {}).keys())}", file=sys.stderr)
                return []

            sponsors_data = org_data.get('sponsorshipsAsMaintainer')
            if not sponsors_data:
                print("Debug: No 'sponsorshipsAsMaintainer' field in organization data", file=sys.stderr)
                print(f"Debug: Available keys in organization: {list(org_data.keys())}", file=sys.stderr)
                return []

            # Debug: Show if the field exists but is null/empty
            if sponsors_data is None:
                print("Debug: 'sponsorshipsAsMaintainer' is null - GitHub Sponsors may not be enabled for this org", file=sys.stderr)
                return []

            sponsors = sponsors_data.get('nodes', [])
            print(f"Fetched {len(sponsors)} sponsors from GitHub", file=sys.stderr)

            # Debug: Show first sponsor structure if available
            if sponsors:
                print(f"Debug: First sponsor keys: {list(sponsors[0].keys())}", file=sys.stderr)

            return sponsors
    except urllib.error.HTTPError as e:
        print(f"Error: HTTP {e.code} - {e.reason}", file=sys.stderr)
        body = e.read().decode()
        print(f"Debug: Error response: {body[:500]}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Error fetching sponsors: {type(e).__name__}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return []


def process_sponsors(sponsors, use_ai=True):
    """
    Process GitHub sponsors into contribution entries.

    Args:
        sponsors: Raw sponsors data from GitHub GraphQL API
        use_ai: Whether to use AI to rewrite summaries

    Returns:
        List of sponsor entry dictionaries
    """
    from ai_helper import rewrite_summary_with_ai

    sponsor_entries = []
    print(f"Debug: Processing {len(sponsors)} raw sponsor nodes", file=sys.stderr)

    for idx, sponsor_node in enumerate(sponsors):
        sponsor = sponsor_node.get('sponsorEntity', {})
        tier = sponsor_node.get('tier') or {}
        monthly_price = tier.get('monthlyPriceInDollars', 0)

        # Debug: Show sponsor processing info
        sponsor_name = sponsor.get('name') or sponsor.get('login', 'Unknown')
        tier_info = f"${monthly_price}/mo" if monthly_price > 0 else "no tier info"
        print(f"Debug: Sponsor {idx+1}: {sponsor_name} | {tier_info}", file=sys.stderr)

        # Get sponsor info
        name = sponsor.get('name', 'Unknown Sponsor')
        login = sponsor.get('login') if 'login' in sponsor else None
        description = sponsor.get('description', f"Sponsor of Armbian build")[:200]

        url = sponsor.get('url') or sponsor.get('websiteUrl', '')
        avatar_url = sponsor.get('avatarUrl', '')
        location = sponsor.get('location', '')

        # Create entry name
        entry_name = f"Sponsor: {name}"
        if login:
            entry_name = f"Sponsor: {login}"

        # Rewrite summary with AI
        summary = description
        if use_ai:
            summary = rewrite_summary_with_ai(name, description, entry_name, "sponsor")

        # Get tier based on monthly price (or default to "Supporter" if no pricing info)
        if monthly_price >= 1000:
            tier_name = "Platinum"
        elif monthly_price >= 100:
            tier_name = "Gold"
        elif monthly_price > 0:
            tier_name = "Silver"
        else:
            tier_name = "Supporter"

        entry = {
            "type": "sponsor",
            "id": f"sponsor-{idx}",
            "name": entry_name,
            "url": url,
            "title": f"{name} - {tier_name} Sponsor",
            "summary": summary,
            "image": avatar_url,
            "author": {"name": name, "handle": f"@{login}"} if login else {"name": name},
            "tags": ["sponsor", tier_name.lower(), "community"],
            "motd": {"line": f"{tier_name} level supporter"}
        }
        sponsor_entries.append(entry)
        print(f"  ✓ Added as {tier_name} sponsor", file=sys.stderr)

    print(f"Debug: Processed {len(sponsor_entries)} active sponsors", file=sys.stderr)
    return sponsor_entries


def main():
    """CLI interface for testing sponsors functionality."""
    import argparse

    parser = argparse.ArgumentParser(description='Fetch GitHub sponsors')
    parser.add_argument('--repo', default='armbian/build', help='GitHub repository')
    parser.add_argument('--limit', type=int, default=10, help='Number of sponsors to fetch')
    parser.add_argument('--no-ai', action='store_true', help='Skip AI rewriting')
    args = parser.parse_args()

    print(f"Fetching up to {args.limit} sponsors from {args.repo}...", file=sys.stderr)

    # Fetch sponsors
    sponsors = fetch_sponsors(args.repo, args.limit)

    # Process into entries
    entries = process_sponsors(sponsors, use_ai=not args.no_ai)

    # Output JSON
    print(json.dumps(entries, indent=2))


if __name__ == "__main__":
    main()
