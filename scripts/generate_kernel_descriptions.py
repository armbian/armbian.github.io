#!/usr/bin/env python3
"""
Generate kernel-description.json from image-info.json

This script analyzes image-info.json and generates descriptions for all kernel families
and their branches, categorizing them as current, edge, legacy, or vendor kernels.

Options:
  --use-ai    Use Claude API to generate richer descriptions (requires ANTHROPIC_API_KEY env var)
"""

import json
import os
import sys
import tempfile
import urllib.request
from pathlib import Path


def categorize_kernel_branch(kernel_branch, family):
    """
    Categorize a kernel branch into current, edge, legacy, or vendor.
    Returns the category name or 'custom' if it doesn't fit standard categories.
    """
    kb = kernel_branch.lower()

    # edge: release candidates and latest tags
    if 'rc' in kb or 'tag:v' in kb:
        return 'edge'

    # vendor: vendor-specific kernels
    if any(x in kb for x in ['rk-6.1', 'ti-linux', 'rpi-', '11.02.08', 'khadas-vims', 'v6.6.54-xpressreal', 'odroid-6.6']):
        return 'vendor'

    # Check for version patterns to categorize as current vs legacy
    import re

    # Extract version numbers
    match = re.search(r'(\d+\.\d+)', kb)
    if match:
        major, minor = map(int, match.group(1).split('.'))

        # Current: 6.12+, 6.18+
        if (major == 6 and minor >= 12) or major > 6:
            # Special cases for 6.6 - it's legacy (old)
            if minor == 6:
                return 'legacy'
            return 'current'

        # Legacy: older versions
        if major < 6 or (major == 6 and minor < 12):
            return 'legacy'

    # vendor kernels without version numbers
    if 'master' in kb or 'commit:' in kb:
        return 'custom'

    # Default to legacy for unknown patterns
    return 'legacy'


def generate_fullname(branch, kernel_branch, family):
    """Generate a full name for the kernel branch."""
    version = extract_version(kernel_branch)

    if branch == 'current':
        if '6.18' in kernel_branch or '6.12' in kernel_branch:
            return f"{version} - Current Kernel"
        return f"{version} Kernel"

    elif branch == 'edge':
        return f"{version} - Edge Kernel"

    elif branch == 'legacy':
        return f"{version} - Legacy Kernel"

    elif branch == 'vendor':
        return f"{version} - Vendor Kernel"

    elif branch == 'custom':
        return f"{version} - Custom Kernel"

    return kernel_branch


def extract_version(kernel_branch):
    """Extract version number from kernel branch string."""
    import re

    # Try most specific pattern first (x.y.z), then x.y
    match = re.search(r'(\d+\.\d+\.\d+)', kernel_branch)
    if match:
        return match.group(1)

    match = re.search(r'(\d+\.\d+)', kernel_branch)
    if match:
        return match.group(1)

    # No version found
    return "Custom"


def generate_description(branch, kernel_branch, family):
    """Generate description for a kernel branch."""
    version = extract_version(kernel_branch)

    descriptions = {
        'current': f"Stable mainline kernel based on Linux {version}.",
        'edge': f"Latest mainline kernel {version} with bleeding edge features. May not be as stable as current.",
        'legacy': f"Older kernel {version}. Maintained for compatibility with older hardware.",
        'vendor': f"Vendor-provided kernel {version}. May include proprietary drivers and hardware-specific optimizations.",
        'custom': f"Custom kernel build: {kernel_branch}"
    }

    base_desc = descriptions.get(branch, descriptions['custom'])

    # Add family-specific information
    family_info = {
        'bcm2711': 'Raspberry Pi',
        'rockchip': 'Rockchip',
        'rockchip64': 'Rockchip (64-bit)',
        'rk35xx': 'Rockchip (legacy)',
        'sunxi': 'Allwinner',
        'sunxi64': 'Allwinner (64-bit)',
        'meson64': 'Amlogic',
        'meson': 'Amlogic (legacy)',
        'mvebu': 'Marvell',
        'mvebu64': 'Marvell (64-bit)',
        'riscv64': 'RISC-V',
        'loong64': 'LoongArch',
        'imx6': 'NXP i.MX6',
        'imx8m': 'NXP i.MX8M',
        'k3': 'Texas Instruments K3',
        'k3-beagle': 'TI K3 (BeagleBone)',
        'arm64': 'Generic ARM64',
        'x86': 'Generic x86',
    }

    if family in family_info:
        return f"{base_desc} Optimized for {family_info[family]} platforms."

    return base_desc


def generate_description_with_ai(branch, kernel_branch, family, api_key=None):
    """
    Generate description for a kernel branch using Claude AI.

    This uses the Anthropic Claude API to generate more informative descriptions
    based on the kernel version, category, and hardware family.
    """
    if not api_key:
        # Fall back to template-based generation
        return generate_description(branch, kernel_branch, family)

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)

        version = extract_version(kernel_branch)

        # Build context for the AI
        family_names = {
            'bcm2711': 'Raspberry Pi',
            'rockchip': 'Rockchip',
            'rockchip64': 'Rockchip (64-bit)',
            'rk35xx': 'Rockchip (legacy)',
            'sunxi': 'Allwinner',
            'sunxi64': 'Allwinner (64-bit)',
            'meson64': 'Amlogic',
            'meson': 'Amlogic (legacy)',
            'mvebu': 'Marvell',
            'mvebu64': 'Marvell (64-bit)',
            'riscv64': 'RISC-V',
            'loong64': 'LoongArch',
            'imx6': 'NXP i.MX6',
            'imx8m': 'NXP i.MX8M',
            'k3': 'Texas Instruments K3',
            'k3-beagle': 'TI K3 (BeagleBone)',
            'arm64': 'Generic ARM64',
            'x86': 'Generic x86',
        }

        family_name = family_names.get(family, family)

        category_descriptions = {
            'current': 'stable mainline kernel with good hardware support and stability',
            'edge': 'bleeding-edge kernel with latest features but may be less stable',
            'legacy': 'older kernel maintained for compatibility with legacy hardware',
            'vendor': 'vendor-specific kernel with proprietary drivers and optimizations',
            'custom': 'custom kernel build with specific modifications'
        }

        category_desc = category_descriptions.get(branch, 'custom kernel build')

        prompt = f"""Generate a concise, one-sentence description (max 25 words) for this Linux kernel option:

Kernel version: {version}
Category: {branch} ({category_desc})
Hardware family: {family_name}
Branch identifier: {kernel_branch}

The description should:
- Be clear and user-friendly
- Highlight the key characteristics or use case
- Help users understand when to choose this kernel
- Be factual and avoid marketing language

Description only, no additional text."""

        message = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=100,
            temperature=0.5,
            messages=[{"role": "user", "content": prompt}]
        )

        description = message.content[0].text.strip()

        # Clean up any quotes or extra formatting
        description = description.strip('"').strip("'")

        return description

    except Exception as e:
        print(f"Warning: AI generation failed for {family}/{branch}: {e}", file=sys.stderr)
        # Fall back to template-based generation
        return generate_description(branch, kernel_branch, family)


def generate_kernel_descriptions(image_info_path, use_ai=False):
    """Generate kernel-description.json from image-info.json."""

    # Load image-info.json
    with open(image_info_path) as f:
        data = json.load(f)

    # Get API key if using AI
    api_key = None
    if use_ai:
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            print("Warning: ANTHROPIC_API_KEY environment variable not set. Using template-based descriptions.", file=sys.stderr)
            use_ai = False
        else:
            print("Using AI to generate kernel descriptions...", file=sys.stderr)

    # Collect kernel families and their branches
    family_data = {}

    for entry in data:
        out = entry.get('out', {})
        vars = entry.get('vars', {})

        family = out.get('LINUXFAMILY', '')
        kernel_branch = out.get('KERNELBRANCH', '')

        if not family or not kernel_branch:
            continue

        if family not in family_data:
            family_data[family] = {}

        # Categorize the branch
        branch = categorize_kernel_branch(kernel_branch, family)

        # Skip if we already have this kernel branch
        if branch in family_data[family]:
            continue

        # Generate fullname and description
        fullname = generate_fullname(branch, kernel_branch, family)
        if use_ai:
            description = generate_description_with_ai(branch, kernel_branch, family, api_key)
        else:
            description = generate_description(branch, kernel_branch, family)

        family_data[family][branch] = {
            'fullname': fullname,
            'description': description
        }

    # Sort and return
    result = dict(sorted(family_data.items()))
    return json.dumps(result, indent=4)


def main():
    """Main entry point."""
    import sys

    # Parse arguments
    use_ai = '--use-ai' in sys.argv

    # Remove --use-ai from argv for positional argument parsing
    clean_argv = [arg for arg in sys.argv if arg != '--use-ai']

    if len(clean_argv) < 2:
        print("Usage: generate_kernel_descriptions.py [--use-ai] <image-info.json> [output_file]")
        print()
        print("Options:")
        print("  --use-ai    Use Claude API to generate richer descriptions")
        print("              Requires ANTHROPIC_API_KEY environment variable")
        print()
        print("If image-info.json is a URL, it will be downloaded first.")
        sys.exit(1)

    input_path = clean_argv[1]

    # Check if input is a URL
    temp_file = None
    if input_path.startswith('http'):
        print(f"Downloading {input_path}...")
        # Use tempfile for unique, secure temporary file
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.json', delete=False) as temp_file:
            local_path = temp_file.name

        # Download with timeout to prevent indefinite hanging
        try:
            with urllib.request.urlopen(input_path, timeout=30) as response:
                temp_data = response.read()
            with open(local_path, 'wb') as f:
                f.write(temp_data)
        except Exception as e:
            # Clean up temp file on error
            if os.path.exists(local_path):
                os.unlink(local_path)
            print(f"Error downloading {input_path}: {e}", file=sys.stderr)
            sys.exit(1)

        input_path = local_path

    # Determine output path
    if len(clean_argv) >= 3:
        output_path = Path(clean_argv[2])
    else:
        # Use tempfile for output as well to avoid collisions
        fd, output_path = tempfile.mkstemp(suffix='-kernel-description.json')
        os.close(fd)
        output_path = Path(output_path)

    # Register cleanup for the input temp file if we created one
    if temp_file is not None:
        def cleanup_temp_file():
            try:
                os.unlink(input_path)
            except OSError:
                pass
        import atexit
        atexit.register(cleanup_temp_file)

    # Generate descriptions
    print("Analyzing kernels...")
    result = generate_kernel_descriptions(input_path, use_ai=use_ai)

    # Write output
    output_path.write_text(result + '\n')
    print(f"Generated kernel descriptions written to: {output_path}")
    print(f"\nTotal kernel families: {len(json.loads(result))}")


if __name__ == '__main__':
    main()
