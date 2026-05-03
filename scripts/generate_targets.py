#!/usr/bin/env python3
"""
Generate Armbian target YAML files from image-info.json

This script reads image-info.json and generates multiple YAML files for different
release types based on board support levels and use cases.
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml


# Release-codename substitution tokens. Both the manual override files
# (release-targets/*.manual) and this generator's own hardcoded YAML
# stanzas use these symbolic names instead of pinning a specific
# Debian/Ubuntu codename. A pair of `--debian-<scope>` / `--ubuntu-<scope>`
# CLI flags per output target decides what gets substituted just before
# each YAML file is written. Promoting nightly to a new Debian (e.g.
# moving from forky to whatever the next Debian testing is) becomes a
# single flag flip, not a 30-place codename rename, and the four output
# files (standard / nightly / community / apps) can each be on their
# own (debian, ubuntu) pair — e.g. standard on trixie + noble while
# nightly is on forky + resolute, which is exactly the current state
# the defaults below preserve.
RELEASE_TOKEN_DEBIAN = "DEBIAN"
RELEASE_TOKEN_UBUNTU = "UBUNTU"

# Per-output-file default codename pairs. Match the literal pins these
# files used before the substitution refactor — running the generator
# with no flags reproduces the previous behaviour exactly.
SCOPE_DEFAULTS = {
    "standard":  {"debian": "trixie", "ubuntu": "resolute"},
    "nightly":   {"debian": "forky",  "ubuntu": "resolute"},
    "community": {"debian": "trixie", "ubuntu": "resolute"},
    "apps":      {"debian": "trixie", "ubuntu": "noble"},
}


def resolve_release_tokens(yaml_text: str, debian: str, ubuntu: str) -> str:
    """
    Substitute the symbolic RELEASE_TOKEN_* placeholders with real
    Debian/Ubuntu codenames.

    Anchored to start-of-line (with optional leading whitespace) so
    only the literal `RELEASE:` YAML key is matched — a hypothetical
    sibling key like `KERNEL_RELEASE: UBUNTU` would otherwise have
    its `RELEASE: UBUNTU` substring matched and overwritten too,
    leaving `KERNEL_RELEASE: noble` (corrupted value, `KERNEL_`
    preserved). No such key exists today; the anchor forward-proofs
    against future additions.

    `\\b` word-boundary stays so a token that happens to be a
    substring of an unrelated string isn't touched. Indentation is
    captured and restored in the replacement so the YAML's leading
    whitespace stays intact. Applied to the *fully-assembled* YAML,
    so it covers both this generator's emit functions and any manual
    content appended via load_manual_overrides().
    """
    yaml_text = re.sub(
        r"(?m)^(\s*)RELEASE:\s*" + re.escape(RELEASE_TOKEN_DEBIAN) + r"\b",
        lambda m: f"{m.group(1)}RELEASE: {debian}",
        yaml_text,
    )
    yaml_text = re.sub(
        r"(?m)^(\s*)RELEASE:\s*" + re.escape(RELEASE_TOKEN_UBUNTU) + r"\b",
        lambda m: f"{m.group(1)}RELEASE: {ubuntu}",
        yaml_text,
    )
    return yaml_text


def load_image_info(json_path):
    """Load and parse image-info.json file."""
    with open(json_path, 'r') as f:
        return json.load(f)


def load_extensions_map(map_path):
    """
    Load manual extensions mapping file.

    Format: BOARD_NAME:branch1:branch2:...:ENABLE_EXTENSIONS="ext1,ext2"
    Returns dict: {(BOARD, BRANCH): "ext1,ext2"}
    If branches are empty (just ::), applies to all branches for that board.
    """
    extensions_map = {}

    if not Path(map_path).exists():
        return extensions_map

    with open(map_path, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue

            # Parse line: BOARD:branch1:branch2:...:ENABLE_EXTENSIONS="..."
            if '::ENABLE_EXTENSIONS=' not in line:
                continue

            try:
                # Split on ENABLE_EXTENSIONS
                parts = line.split('ENABLE_EXTENSIONS=')
                if len(parts) != 2:
                    continue

                # Parse board and branches
                board_part = parts[0].rstrip(':')
                extensions = parts[1].strip('"')

                # Split by : to get board and branches
                if ':' in board_part:
                    board_branches = board_part.split(':')
                    board = board_branches[0]
                    branches = [b for b in board_branches[1:] if b]  # Filter empty strings
                else:
                    board = board_part
                    branches = []

                # Store mapping
                if branches:
                    # Specific branches
                    for branch in branches:
                        extensions_map[(board, branch)] = extensions
                else:
                    # All branches - use empty branch as wildcard
                    extensions_map[(board, '')] = extensions

            except Exception as e:
                print(f"Warning: Failed to parse line: {line} ({e})", file=sys.stderr)
                continue

    return extensions_map


def load_remove_extensions_map(map_path):
    """
    Load remove extensions mapping file (blacklist).

    Format: BOARD_NAME:branch1:branch2:...:REMOVE_EXTENSIONS="ext1,ext2"
    Returns dict: {(BOARD, BRANCH): set(["ext1", "ext2"])}
    If branches are empty (just ::), applies to all branches for that board.
    Extensions in this set are removed from both auto-added and manual extensions.
    """
    remove_map = {}

    if not Path(map_path).exists():
        return remove_map

    with open(map_path, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue

            # Parse line: BOARD:branch1:branch2:...:REMOVE_EXTENSIONS="..."
            if '::REMOVE_EXTENSIONS=' not in line:
                continue

            try:
                # Split on REMOVE_EXTENSIONS
                parts = line.split('REMOVE_EXTENSIONS=')
                if len(parts) != 2:
                    continue

                # Parse board and branches
                board_part = parts[0].rstrip(':')
                extensions = parts[1].strip('"')

                # Split by : to get board and branches
                if ':' in board_part:
                    board_branches = board_part.split(':')
                    board = board_branches[0]
                    branches = [b for b in board_branches[1:] if b]  # Filter empty strings
                else:
                    board = board_part
                    branches = []

                # Convert to set for easy removal
                ext_set = {ext.strip() for ext in extensions.split(',') if ext.strip()}

                # Store mapping
                if branches:
                    # Specific branches
                    for branch in branches:
                        remove_map[(board, branch)] = ext_set
                else:
                    # All branches - use empty branch as wildcard
                    remove_map[(board, '')] = ext_set

            except Exception as e:
                print(f"Warning: Failed to parse line: {line} ({e})", file=sys.stderr)
                continue

    return remove_map


def load_manual_overrides(base_path):
    """
    Load manual target overrides from .manual files.

    Returns the content of the manual file as a string to append to generated YAML,
    or empty string if file doesn't exist.
    """
    manual_path = Path(base_path).with_suffix('.manual')

    if not manual_path.exists():
        return ""

    try:
        with open(manual_path, 'r') as f:
            content = f.read()
        print(f"  Loaded manual overrides from {manual_path.name}", file=sys.stderr)
        return content
    except Exception as e:
        print(f"Warning: Failed to load {manual_path}: {e}", file=sys.stderr)
        return ""


def load_exposed_overrides(path):
    """
    Load per-board(family) overrides for exposed.map regex generation.

    The file (typically `<output_dir>/exposed.map.overrides.yaml`) lets a
    vendor BSP redirect either of the two regex patterns
    generate_exposed_map emits per board. Useful when, e.g., the SpacemiT
    K1 boardfamily has a Bianbu desktop image on noble/legacy that the
    generic riscv64 → xfce path doesn't reach, and the matching minimal
    image lives on noble/legacy too rather than on the default Debian
    codename.

    Schema:

        overrides:
          - boardfamily: <name>          # match all boards in this family
            # AND/OR (in a separate entry)
            boards: [b1, b2, ...]        # specific board slugs

            # Optional override for pattern 1 (the "minimal" image).
            # Defaults to: debian_codename + board's selected branch + "minimal".
            minimal:
              release: <codename>        # literal codename (NOT a UBUNTU/DEBIAN token)
              branch:  <branch>
              suffix:  <token>           # tail of the regex; default "minimal"

            # Optional override for pattern 2 (the "desktop" image).
            # Defaults to: ubuntu_codename + board's selected branch +
            # algorithmic suffix (xfce_desktop / gnome_desktop / minimal).
            desktop:
              release: <codename>
              branch:  <branch>
              suffix:  <token>           # full literal tail, e.g. "bianbu_desktop"

    Either inner block may be omitted to leave that pattern untouched.
    Inside each block, every field is optional and falls through to the
    algorithmic default the generator would have used.

    A per-board entry (`boards: [...]`) overlays the boardfamily entry,
    block-by-block then field-by-field — so a per-board entry that only
    sets `minimal:` keeps the family's `desktop:` block intact, and a
    per-board `desktop: {suffix: x}` keeps the family's
    `desktop.{release, branch}` while replacing only `suffix`. See
    match_exposed_override() for the merge rules.

    Missing file → []. Malformed entries (no match key, non-mapping
    inner blocks) are dropped with a warning so a typo can't silently
    rewrite the recommended-image set for every board in the world.
    """
    if not path.exists():
        return []
    try:
        with open(path) as f:
            data = yaml.safe_load(f) or {}
    except (yaml.YAMLError, OSError) as e:
        print(f"Warning: could not parse {path}: {e}", file=sys.stderr)
        return []

    raw = data.get('overrides', [])
    if not isinstance(raw, list):
        print(f"Warning: {path}: 'overrides' must be a list", file=sys.stderr)
        return []

    valid = []
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            print(f"Warning: {path}: overrides[{i}] is not a mapping; skipped", file=sys.stderr)
            continue
        # An entry without any match key would silently match everything.
        has_boards = isinstance(entry.get('boards'), list) and entry['boards']
        has_family = isinstance(entry.get('boardfamily'), str) and entry['boardfamily']
        if not (has_boards or has_family):
            print(f"Warning: {path}: overrides[{i}] needs `boards` or `boardfamily`; skipped", file=sys.stderr)
            continue
        # Inner blocks must be mappings if present. A flat-schema typo
        # (e.g. someone writing `release: noble` at the top level instead
        # of nesting it under `desktop:`) silently has no effect, so we
        # warn — that's the only way to catch a misplaced override.
        ok = True
        for block in ('minimal', 'desktop'):
            if block in entry and not isinstance(entry[block], dict):
                print(f"Warning: {path}: overrides[{i}].{block} must be a mapping; entry skipped", file=sys.stderr)
                ok = False
                break
        if not ok:
            continue
        for top in entry.keys():
            if top in ('boards', 'boardfamily', 'minimal', 'desktop'):
                continue
            print(f"Warning: {path}: overrides[{i}] has unknown top-level key {top!r}; ignored", file=sys.stderr)
        valid.append(entry)
    if valid:
        print(f"  Loaded exposed.map overrides from {path.name}: {len(valid)} entries", file=sys.stderr)
    return valid


def match_exposed_override(overrides, *, board, boardfamily):
    """
    Pick the effective override for a given board, or None.

    A per-board entry (`boards: [...]`) is overlaid on top of the
    boardfamily entry (`boardfamily: ...`) — block by block, then
    field by field within each block. Fields the per-board entry
    sets win; fields it omits fall through to the family. This lets
    a single board carve out a partial exception (e.g. different
    minimal release) without having to repeat the rest of the
    family's blocks.

    Examples (with a family `{boardfamily: spacemit, minimal: {...}, desktop: {...}}`):

      - boards: [musebook]                   → returns the family entry verbatim
      - boards: [musepipro]
        minimal: { release: trixie, branch: current }
                                              → keeps family.desktop, replaces
                                                family.minimal entirely
      - boards: [bananapif3]
        desktop: { suffix: xfce_desktop }    → keeps family.minimal, keeps
                                                family.desktop.{release, branch},
                                                replaces only desktop.suffix

    With no per-board match the family entry is returned as-is; with
    no family match the per-board entry is returned as-is; with neither,
    None.
    """
    family_entry = None
    if boardfamily:
        for entry in overrides:
            if entry.get('boardfamily') == boardfamily:
                family_entry = entry
                break

    board_entry = None
    for entry in overrides:
        if board in (entry.get('boards') or []):
            board_entry = entry
            break

    if board_entry is None and family_entry is None:
        return None
    if board_entry is None:
        return family_entry
    if family_entry is None:
        return board_entry

    # Both present — overlay board on family. Block-level: a missing
    # block on the per-board entry leaves the family's block intact.
    # Field-level: inside a block the per-board fields update the
    # family's, leaving unset fields alone.
    merged = {}
    for block in ('minimal', 'desktop'):
        family_block = family_entry.get(block) if isinstance(family_entry.get(block), dict) else None
        board_block = board_entry.get(block) if isinstance(board_entry.get(block), dict) else None
        if family_block is None and board_block is None:
            continue
        merged_block = dict(family_block) if family_block else {}
        if board_block:
            merged_block.update(board_block)
        merged[block] = merged_block
    return merged


def load_blacklist(base_path):
    """
    Load blacklist of boards to exclude from automation.

    Returns a set of board names to exclude, or empty set if file doesn't exist.
    Format: one board name per line, comments starting with # are ignored.
    """
    blacklist_path = Path(base_path).with_suffix('.blacklist')

    if not blacklist_path.exists():
        return set()

    blacklist = set()
    try:
        with open(blacklist_path, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                blacklist.add(line)
        print(f"  Loaded blacklist from {blacklist_path.name}: {len(blacklist)} boards", file=sys.stderr)
        return blacklist
    except Exception as e:
        print(f"Warning: Failed to load {blacklist_path}: {e}", file=sys.stderr)
        return set()


def is_fast_hardware(entry):
    """
    Determine if board is fast/slow/riscv64/loongarch/headless based on ARCH.
    - First check BOARD_HAS_VIDEO: if false, return None (headless)
    - For boards with video: check architecture
    - arm/armhf (32-bit): slow hardware
    - BOARDFAMILY sun50iw*/sun55iw* (Allwinner H3/H5/H6): slow hardware
    - BOARDFAMILY meson-gxbb/meson-gxl/meson-g12a/meson-g12b/meson-sm1 (Amlogic): slow hardware
    - BOARDFAMILY nuvoton-ma35d1 (Nuvoton): slow hardware
    - BOOT_SOC rk3328/rk3399/rk3399pro (Rockchip): slow hardware
    - arm64, x86: fast hardware
    - riscv64: separate category
    - loongarch: separate category
    Returns: False for slow, True for fast, 'riscv64' for riscv64, 'loongarch' for loongarch, None for headless
    """
    inventory = entry.get('in', {}).get('inventory', {})
    board = inventory.get('BOARD', '')
    board_family = inventory.get('BOARDFAMILY', '')
    boot_soc = inventory.get('BOOT_SOC', '')
    has_video = inventory.get('BOARD_HAS_VIDEO', False)

    # Also check BOARD_TOP_LEVEL_VARS for BOARDFAMILY and BOOT_SOC
    toplevel_vars = inventory.get('BOARD_TOP_LEVEL_VARS', {})
    if isinstance(toplevel_vars, dict):
        if not board_family:
            board_family = toplevel_vars.get('BOARDFAMILY', '')
        if not boot_soc:
            boot_soc = toplevel_vars.get('BOOT_SOC', '')

    # Check output section for BOOT_SOC if still not found
    if not boot_soc:
        out = entry.get('out', {})
        boot_soc = out.get('BOOT_SOC', '')

    # Headless boards don't go into fast/slow/riscv64/loongarch categories
    if not has_video:
        return None

    out = entry.get('out', {})
    arch = out.get('ARCH', '')

    # Special case: uefi-loong64 gets its own category
    if board == 'uefi-loong64':
        return 'loongarch'

    # arm (32-bit) is slow - both 'arm' and 'armhf'
    if arch in ['arm', 'armhf']:
        return False

    # Allwinner H3/H5/H6/H616 etc. (sun50iw*, sun55iw*) are slow
    if board_family and (board_family.startswith('sun50iw') or board_family.startswith('sun55iw')):
        return False

    # Amlogic S905X/S912/S905X2/S922X/A311D (meson-gxbb, meson-gxl, meson-g12a, meson-g12b, meson-sm1) are slow
    if board_family in ['meson-gxbb', 'meson-gxl', 'meson-g12a', 'meson-g12b', 'meson-sm1']:
        return False

    # Nuvoton MA35D1 is slow
    if board_family == 'nuvoton-ma35d1':
        return False

    # Rockchip RK3328, RK3399 and RK3399PRO are slow
    if boot_soc in ['rk3328', 'rk3399', 'rk3399pro']:
        return False

    # riscv64 gets its own category
    if arch == 'riscv64':
        return 'riscv64'
    # loongarch gets its own category
    elif arch == 'loongarch64':
        return 'loongarch'
    # everything else is fast (arm64, x86)
    else:
        return True


def get_soc_extensions(entry, extensions_map=None, remove_extensions_map=None):
    """
    Determine which build extensions a board needs.
    For fast HDMI boards, automatically adds v4l2loopback-dkms.
    Also merges manual extensions from the extensions map.
    Removes extensions specified in remove_extensions_map.
    Returns a comma-separated string of extensions or empty string.
    """
    inventory = entry.get('in', {}).get('inventory', {})
    vars_dict = entry.get('in', {}).get('vars', {})
    board = inventory.get('BOARD', '')
    branch = vars_dict.get('BRANCH', '')

    extensions = []

    # Add automatic extensions for all fast HDMI boards.
    # mesa-vpu used to live here too; it was retired when its
    # responsibilities moved to armbian-config's module_desktops
    # (armbian/build PR #9683 deletes the extension itself).
    if is_fast_hardware(entry) is True:
        extensions.append('v4l2loopback-dkms')

    # Then, add manual extensions (merges with automatic ones)
    if extensions_map:
        manual_ext = None
        # Check for specific (board, branch) match
        if (board, branch) in extensions_map:
            manual_ext = extensions_map[(board, branch)]
        # Check for wildcard (board, '') match
        elif (board, '') in extensions_map:
            manual_ext = extensions_map[(board, '')]

        if manual_ext:
            # Split and add each extension
            for ext in manual_ext.split(','):
                ext = ext.strip()
                if ext and ext not in extensions:
                    extensions.append(ext)

    # Remove extensions specified in remove_extensions_map
    if remove_extensions_map:
        remove_ext = None
        # Check for specific (board, branch) match
        if (board, branch) in remove_extensions_map:
            remove_ext = remove_extensions_map[(board, branch)]
        # Check for wildcard (board, '') match
        elif (board, '') in remove_extensions_map:
            remove_ext = remove_extensions_map[(board, '')]

        if remove_ext:
            # Filter out extensions in the remove list
            extensions = [ext for ext in extensions if ext not in remove_ext]

    return ','.join(extensions) if extensions else ''


def extract_boards_by_support_level(image_info, extensions_map=None, remove_extensions_map=None, blacklist=None):
    """
    Extract and categorize boards by support level.

    Args:
        image_info: Image information data
        extensions_map: Optional extensions mapping
        remove_extensions_map: Optional remove extensions mapping
        blacklist: Optional set of board names to exclude

    Returns:
        - conf_wip_boards: Boards with conf or wip support level
        - csc_tvb_boards: Boards with csc or tvb support level
    """
    if blacklist is None:
        blacklist = set()

    board_data = {}  # (BOARD, BRANCH) -> entry data

    # First pass: collect all unique board/branch combos
    for entry in image_info:
        inventory = entry.get('in', {}).get('inventory', {})
        vars_dict = entry.get('in', {}).get('vars', {})
        out = entry.get('out', {})

        board = inventory.get('BOARD')
        branch = vars_dict.get('BRANCH')
        support_level = inventory.get('BOARD_SUPPORT_LEVEL')
        arch = out.get('ARCH', '')
        build_desktop = vars_dict.get('BUILD_DESKTOP', 'no')

        if not board or not branch:
            continue

        # Skip blacklisted boards
        if board in blacklist:
            continue

        # Only include relevant support levels
        if support_level not in ['conf', 'csc', 'tvb', 'wip']:
            continue

        key = (board, branch)

        # Initialize or update board data
        if key not in board_data:
            board_data[key] = {
                'board': board,
                'branch': branch,
                'support_level': support_level,
                'arch': arch,
                'entry': entry,
                'has_desktop_variant': build_desktop == 'yes',
                'extensions': get_soc_extensions(entry, extensions_map, remove_extensions_map),
                'is_fast': is_fast_hardware(entry)
            }
        else:
            if build_desktop == 'yes':
                board_data[key]['has_desktop_variant'] = True
                # Don't overwrite is_fast - keep the first entry's classification
                # Desktop variants might have different BOARDFAMILY values

    # Categorize by support level
    conf_wip_boards = []
    csc_tvb_boards = []

    for key, data in board_data.items():
        # Get KERNEL_TEST_TARGET from the board's inventory
        # If set, only include branches that are in KERNEL_TEST_TARGET
        entry = data['entry']
        inventory = entry.get('in', {}).get('inventory', {})
        # KERNEL_TEST_TARGET is in BOARD_TOP_LEVEL_VARS
        toplevel_vars = inventory.get('BOARD_TOP_LEVEL_VARS', {})
        kernel_test_target = toplevel_vars.get('KERNEL_TEST_TARGET', '')

        if kernel_test_target:
            # Parse KERNEL_TEST_TARGET - comma-separated list of branches
            allowed_branches = [b.strip() for b in kernel_test_target.split(',') if b.strip()]
            if data['branch'] not in allowed_branches:
                continue
        else:
            # Filter branches: prefer current, vendor, and legacy
            if data['branch'] not in ['current', 'vendor', 'legacy', 'edge']:
                continue

        if data['support_level'] in ['conf', 'wip']:
            conf_wip_boards.append(data)
        elif data['support_level'] in ['csc', 'tvb']:
            csc_tvb_boards.append(data)

    return conf_wip_boards, csc_tvb_boards


def select_one_branch_per_board(boards):
    """
    Select one branch per board, preferring current over vendor over edge.
    Respects KERNEL_TEST_TARGET if set on the board.
    Returns list of unique boards.
    """
    # Define branch preference priority (lower number = higher priority)
    default_branch_priority = {
        'current': 1,
        'vendor': 2,
        'legacy': 2,
        'edge': 3
    }

    seen_boards = {}
    for board_data in boards:
        board = board_data['board']
        branch = board_data['branch']
        entry = board_data['entry']
        inventory = entry.get('in', {}).get('inventory', {})
        # KERNEL_TEST_TARGET is in BOARD_TOP_LEVEL_VARS
        toplevel_vars = inventory.get('BOARD_TOP_LEVEL_VARS', {})
        kernel_test_target = toplevel_vars.get('KERNEL_TEST_TARGET', '')

        # Determine branch priority for this board
        if kernel_test_target:
            # Use KERNEL_TEST_TARGET order as priority
            allowed_branches = [b.strip() for b in kernel_test_target.split(',') if b.strip()]
            branch_priority = {branch: idx for idx, branch in enumerate(allowed_branches, 1)}
        else:
            branch_priority = default_branch_priority

        # Skip if branch is not in our priority list
        if branch not in branch_priority:
            continue

        # Select this board if:
        # 1. Board hasn't been seen yet, OR
        # 2. This branch has higher priority (lower number) than the stored one
        if board not in seen_boards:
            seen_boards[board] = board_data
        elif branch_priority[branch] < branch_priority[seen_boards[board]['branch']]:
            seen_boards[board] = board_data

    return list(seen_boards.values())


def generate_yaml_header():
    """Generate common YAML header."""
    return """#
# Armbian release template. Auto-generated from image-info.json
#
common-gha-configs:
armbian-gha: &armbian-gha
  runners:
    default: "ubuntu-latest"
    by-name:
      kernel: [ "self-hosted", "Linux", "alfa" ]
      uboot: [ "self-hosted", "Linux", "fast", "X64" ]
      armbian-bsp-cli: [ "X64" ]
    by-name-and-arch:
      rootfs-armhf: [ "ubuntu-latest" ]
      rootfs-arm64: [ "ubuntu-24.04-arm" ]
      rootfs-amd64: [ "self-hosted", "Linux", "X64" ]
      rootfs-riscv64: [ "ubuntu-latest" ]
      rootfs-loong64: [ "self-hosted", "Linux", "X64" ]
      image-armhf: [ "self-hosted", "Linux", 'images', 'X64' ]
      image-arm64: [ "self-hosted", "Linux", 'images', 'ARM64' ]
      image-amd64: [ "self-hosted", "Linux", 'images', "X64" ]
      image-riscv64: [ "self-hosted", "Linux", 'images', "X64" ]
      image-loong64: [ "self-hosted", "Linux", 'images', "X64" ]

lists:
"""


def format_board_item(board_data, include_extensions=True):
    """Format a board entry for YAML, optionally including extensions."""
    board = board_data['board']
    branch = board_data['branch']

    if include_extensions and board_data['extensions']:
        extensions = board_data['extensions']
        return f'    - {{ BOARD: {board}, BRANCH: {branch}, ENABLE_EXTENSIONS: "{extensions}" }}'
    else:
        return f'    - {{ BOARD: {board}, BRANCH: {branch} }}'


def generate_apps_yaml(conf_wip_boards, manual_content=""):
    """
    Generate apps.yml with one image per board with different extensions.
    For conf/wip boards only.
    manual_content: Additional YAML to append inside the targets section
    """
    yaml = generate_yaml_header()

    # Select one branch per board for apps
    boards = select_one_branch_per_board(conf_wip_boards)
    # Exclude armhf, riscv64, and loongarch64 from apps builds
    boards = [b for b in boards if b['arch'] not in ['armhf', 'riscv64', 'loongarch64']]
    boards.sort(key=lambda x: x['board'])

    yaml += """# Apps builds - one image per board with various extensions
  apps-builds: &apps-builds
  # auto generated section
"""
    for board_data in boards:
        # Don't include SoC-specific extensions in the base list
        yaml += format_board_item(board_data, include_extensions=False) + '\n'

    yaml += '  # end of auto generated section\n\n'

    yaml += """# automated lists stop

targets:
  # Images with app-specific extensions
  apps-ha:
    enabled: yes
    configs: [ armbian-apps ]
    pipeline:
      gha: *armbian-gha
    build-image: "yes"
    vars:
      RELEASE: DEBIAN
      BUILD_MINIMAL: "no"
      BUILD_DESKTOP: "no"
      ENABLE_EXTENSIONS: "ha"
    items:
      - *apps-builds

  apps-omv:
    enabled: yes
    configs: [ armbian-apps ]
    pipeline:
      gha: *armbian-gha
    build-image: "yes"
    vars:
      RELEASE: DEBIAN
      BUILD_MINIMAL: "yes"
      BUILD_DESKTOP: "no"
      ENABLE_EXTENSIONS: "omv"
    items:
      - *apps-builds

  apps-openhab:
    enabled: yes
    configs: [ armbian-apps ]
    pipeline:
      gha: *armbian-gha
    build-image: "yes"
    vars:
      RELEASE: DEBIAN
      BUILD_MINIMAL: "no"
      BUILD_DESKTOP: "no"
      ENABLE_EXTENSIONS: "openhab"
    items:
      - *apps-builds

  apps-kali:
    enabled: yes
    configs: [ armbian-apps ]
    pipeline:
      gha: *armbian-gha
    build-image: "yes"
    vars:
      RELEASE: sid
      BUILD_MINIMAL: "no"
      BUILD_DESKTOP: "no"
      ENABLE_EXTENSIONS: "kali"
    items:
      - *apps-builds
"""
    if manual_content:
        # Indent manual content by 2 spaces to be under targets:
        indented_manual = '\n'.join('  ' + line if line.strip() else line for line in manual_content.split('\n'))
        yaml += '\n' + indented_manual

    return yaml


def generate_stable_yaml(conf_wip_boards, manual_content=""):
    """
    Generate stable.yml with full set of images.
    For conf/wip boards only.
    Separates fast, slow, riscv64, and loongarch boards based on CPU performance.
    manual_content: Additional YAML to append inside the targets section
    """
    yaml = generate_yaml_header()

    # Separate by branch and performance/architecture
    # Only separate by actual branch names, not by category
    current_fast = [b for b in conf_wip_boards if b['branch'] == 'current' and b['is_fast'] is True]
    current_slow = [b for b in conf_wip_boards if b['branch'] == 'current' and b['is_fast'] is False]
    current_riscv64 = [b for b in conf_wip_boards if b['branch'] == 'current' and b['is_fast'] == 'riscv64']
    current_loongarch = [b for b in conf_wip_boards if b['branch'] == 'current' and b['is_fast'] == 'loongarch']
    current_headless = [b for b in conf_wip_boards if b['branch'] == 'current' and b['is_fast'] is None]
    vendor_fast = [b for b in conf_wip_boards if b['branch'] == 'vendor' and b['is_fast'] is True]
    vendor_slow = [b for b in conf_wip_boards if b['branch'] == 'vendor' and b['is_fast'] is False]
    vendor_riscv64 = [b for b in conf_wip_boards if b['branch'] == 'vendor' and b['is_fast'] == 'riscv64']
    vendor_loongarch = [b for b in conf_wip_boards if b['branch'] == 'vendor' and b['is_fast'] == 'loongarch']
    vendor_headless = [b for b in conf_wip_boards if b['branch'] == 'vendor' and b['is_fast'] is None]
    legacy_fast = [b for b in conf_wip_boards if b['branch'] == 'legacy' and b['is_fast'] is True]
    legacy_slow = [b for b in conf_wip_boards if b['branch'] == 'legacy' and b['is_fast'] is False]
    legacy_riscv64 = [b for b in conf_wip_boards if b['branch'] == 'legacy' and b['is_fast'] == 'riscv64']
    legacy_loongarch = [b for b in conf_wip_boards if b['branch'] == 'legacy' and b['is_fast'] == 'loongarch']
    legacy_headless = [b for b in conf_wip_boards if b['branch'] == 'legacy' and b['is_fast'] is None]

    # Build set of boards that have current branch (to exclude from edge)
    current_boards = {b['board'] for b in conf_wip_boards if b['branch'] == 'current'}

    # Only include edge boards for boards that don't have current branch
    edge_fast = [b for b in conf_wip_boards if b['branch'] == 'edge' and b['is_fast'] is True and b['board'] not in current_boards]
    edge_slow = [b for b in conf_wip_boards if b['branch'] == 'edge' and b['is_fast'] is False and b['board'] not in current_boards]
    edge_riscv64 = [b for b in conf_wip_boards if b['branch'] == 'edge' and b['is_fast'] == 'riscv64' and b['board'] not in current_boards]
    edge_loongarch = [b for b in conf_wip_boards if b['branch'] == 'edge' and b['is_fast'] == 'loongarch' and b['board'] not in current_boards]
    edge_headless = [b for b in conf_wip_boards if b['branch'] == 'edge' and b['is_fast'] is None and b['board'] not in current_boards]

    # Current branch lists
    yaml += """# Stable builds - fast HDMI (quad-core+ or modern SoCs)
  stable-current-fast-hdmi: &stable-current-fast-hdmi
  # auto generated section
"""
    for board_data in sorted(current_fast, key=lambda x: x['board']):
        yaml += format_board_item(board_data, include_extensions=True) + '\n'
    yaml += '  # end of auto generated section\n\n'

    if current_slow:
        yaml += '  stable-current-slow-hdmi: &stable-current-slow-hdmi\n'
        yaml += '  # auto generated section\n'
        for board_data in sorted(current_slow, key=lambda x: x['board']):
            yaml += format_board_item(board_data, include_extensions=True) + '\n'
        yaml += '  # end of auto generated section\n\n'

    if current_riscv64:
        yaml += '  stable-current-riscv64: &stable-current-riscv64\n'
        yaml += '  # auto generated section\n'
        for board_data in sorted(current_riscv64, key=lambda x: x['board']):
            yaml += format_board_item(board_data, include_extensions=True) + '\n'
        yaml += '  # end of auto generated section\n\n'

    if current_loongarch:
        yaml += '  stable-current-loongarch: &stable-current-loongarch\n'
        yaml += '  # auto generated section\n'
        for board_data in sorted(current_loongarch, key=lambda x: x['board']):
            yaml += format_board_item(board_data, include_extensions=True) + '\n'
        yaml += '  # end of auto generated section\n\n'

    if current_headless:
        yaml += '  stable-current-headless: &stable-current-headless\n'
        yaml += '  # auto generated section\n'
        for board_data in sorted(current_headless, key=lambda x: x['board']):
            yaml += format_board_item(board_data, include_extensions=True) + '\n'
        yaml += '  # end of auto generated section\n\n'

    # Vendor branch lists
    if vendor_fast:
        yaml += '  stable-vendor-fast-hdmi: &stable-vendor-fast-hdmi\n'
        yaml += '  # auto generated section\n'
        for board_data in sorted(vendor_fast, key=lambda x: x['board']):
            yaml += format_board_item(board_data, include_extensions=True) + '\n'
        yaml += '  # end of auto generated section\n\n'

    if vendor_slow:
        yaml += '  stable-vendor-slow-hdmi: &stable-vendor-slow-hdmi\n'
        yaml += '  # auto generated section\n'
        for board_data in sorted(vendor_slow, key=lambda x: x['board']):
            yaml += format_board_item(board_data, include_extensions=True) + '\n'
        yaml += '  # end of auto generated section\n\n'

    if vendor_riscv64:
        yaml += '  stable-vendor-riscv64: &stable-vendor-riscv64\n'
        yaml += '  # auto generated section\n'
        for board_data in sorted(vendor_riscv64, key=lambda x: x['board']):
            yaml += format_board_item(board_data, include_extensions=True) + '\n'
        yaml += '  # end of auto generated section\n\n'

    if vendor_loongarch:
        yaml += '  stable-vendor-loongarch: &stable-vendor-loongarch\n'
        yaml += '  # auto generated section\n'
        for board_data in sorted(vendor_loongarch, key=lambda x: x['board']):
            yaml += format_board_item(board_data, include_extensions=True) + '\n'
        yaml += '  # end of auto generated section\n\n'

    if vendor_headless:
        yaml += '  stable-vendor-headless: &stable-vendor-headless\n'
        yaml += '  # auto generated section\n'
        for board_data in sorted(vendor_headless, key=lambda x: x['board']):
            yaml += format_board_item(board_data, include_extensions=True) + '\n'
        yaml += '  # end of auto generated section\n\n'

    # Legacy branch lists
    if legacy_fast:
        yaml += '  stable-legacy-fast-hdmi: &stable-legacy-fast-hdmi\n'
        yaml += '  # auto generated section\n'
        for board_data in sorted(legacy_fast, key=lambda x: x['board']):
            yaml += format_board_item(board_data, include_extensions=True) + '\n'
        yaml += '  # end of auto generated section\n\n'

    if legacy_slow:
        yaml += '  stable-legacy-slow-hdmi: &stable-legacy-slow-hdmi\n'
        yaml += '  # auto generated section\n'
        for board_data in sorted(legacy_slow, key=lambda x: x['board']):
            yaml += format_board_item(board_data, include_extensions=True) + '\n'
        yaml += '  # end of auto generated section\n\n'

    if legacy_riscv64:
        yaml += '  stable-legacy-riscv64: &stable-legacy-riscv64\n'
        yaml += '  # auto generated section\n'
        for board_data in sorted(legacy_riscv64, key=lambda x: x['board']):
            yaml += format_board_item(board_data, include_extensions=True) + '\n'
        yaml += '  # end of auto generated section\n\n'

    if legacy_loongarch:
        yaml += '  stable-legacy-loongarch: &stable-legacy-loongarch\n'
        yaml += '  # auto generated section\n'
        for board_data in sorted(legacy_loongarch, key=lambda x: x['board']):
            yaml += format_board_item(board_data, include_extensions=True) + '\n'
        yaml += '  # end of auto generated section\n\n'

    if legacy_headless:
        yaml += '  stable-legacy-headless: &stable-legacy-headless\n'
        yaml += '  # auto generated section\n'
        for board_data in sorted(legacy_headless, key=lambda x: x['board']):
            yaml += format_board_item(board_data, include_extensions=True) + '\n'
        yaml += '  # end of auto generated section\n\n'

    # Edge branch lists
    if edge_fast:
        yaml += '  stable-edge-fast-hdmi: &stable-edge-fast-hdmi\n'
        yaml += '  # auto generated section\n'
        for board_data in sorted(edge_fast, key=lambda x: x['board']):
            yaml += format_board_item(board_data, include_extensions=True) + '\n'
        yaml += '  # end of auto generated section\n\n'

    if edge_slow:
        yaml += '  stable-edge-slow-hdmi: &stable-edge-slow-hdmi\n'
        yaml += '  # auto generated section\n'
        for board_data in sorted(edge_slow, key=lambda x: x['board']):
            yaml += format_board_item(board_data, include_extensions=True) + '\n'
        yaml += '  # end of auto generated section\n\n'

    if edge_riscv64:
        yaml += '  stable-edge-riscv64: &stable-edge-riscv64\n'
        yaml += '  # auto generated section\n'
        for board_data in sorted(edge_riscv64, key=lambda x: x['board']):
            yaml += format_board_item(board_data, include_extensions=True) + '\n'
        yaml += '  # end of auto generated section\n\n'

    if edge_loongarch:
        yaml += '  stable-edge-loongarch: &stable-edge-loongarch\n'
        yaml += '  # auto generated section\n'
        for board_data in sorted(edge_loongarch, key=lambda x: x['board']):
            yaml += format_board_item(board_data, include_extensions=True) + '\n'
        yaml += '  # end of auto generated section\n\n'

    if edge_headless:
        yaml += '  stable-edge-headless: &stable-edge-headless\n'
        yaml += '  # auto generated section\n'
        for board_data in sorted(edge_headless, key=lambda x: x['board']):
            yaml += format_board_item(board_data, include_extensions=True) + '\n'
        yaml += '  # end of auto generated section\n\n'

    yaml += """# automated lists stop

targets:
  # Debian stable minimal
  minimal-stable-debian:
    enabled: yes
    configs: [ armbian-images ]
    pipeline:
      gha: *armbian-gha
    build-image: "yes"
    vars:
      RELEASE: DEBIAN
      BUILD_MINIMAL: "yes"
      BUILD_DESKTOP: "no"
    items:
      - *stable-current-fast-hdmi
"""
    if current_slow:
        yaml += '      - *stable-current-slow-hdmi\n'
    if current_riscv64:
        yaml += '      - *stable-current-riscv64\n'
    if current_loongarch:
        yaml += '      - *stable-current-loongarch\n'
    if current_headless:
        yaml += '      - *stable-current-headless\n'
    if vendor_fast:
        yaml += '      - *stable-vendor-fast-hdmi\n'
    if vendor_slow:
        yaml += '      - *stable-vendor-slow-hdmi\n'
    if vendor_riscv64:
        yaml += '      - *stable-vendor-riscv64\n'
    if vendor_loongarch:
        yaml += '      - *stable-vendor-loongarch\n'
    if vendor_headless:
        yaml += '      - *stable-vendor-headless\n'
    if legacy_fast:
        yaml += '      - *stable-legacy-fast-hdmi\n'
    if legacy_slow:
        yaml += '      - *stable-legacy-slow-hdmi\n'
    if legacy_riscv64:
        yaml += '      - *stable-legacy-riscv64\n'
    if legacy_loongarch:
        yaml += '      - *stable-legacy-loongarch\n'
    if legacy_headless:
        yaml += '      - *stable-legacy-headless\n'
    if edge_fast:
        yaml += '      - *stable-edge-fast-hdmi\n'
    if edge_slow:
        yaml += '      - *stable-edge-slow-hdmi\n'
    if edge_riscv64:
        yaml += '      - *stable-edge-riscv64\n'
    if edge_loongarch:
        yaml += '      - *stable-edge-loongarch\n'
    if edge_headless:
        yaml += '      - *stable-edge-headless\n'

    yaml += """
  # Ubuntu stable minimal
  minimal-stable-ubuntu:
    enabled: yes
    configs: [ armbian-images ]
    pipeline:
      gha: *armbian-gha
    build-image: "yes"
    vars:
      RELEASE: UBUNTU
      BUILD_MINIMAL: "yes"
      BUILD_DESKTOP: "no"
    items:
      - *stable-current-fast-hdmi
"""
    if current_slow:
        yaml += '      - *stable-current-slow-hdmi\n'
    if current_riscv64:
        yaml += '      - *stable-current-riscv64\n'
    if current_loongarch:
        yaml += '      - *stable-current-loongarch\n'
    if current_headless:
        yaml += '      - *stable-current-headless\n'
    if vendor_fast:
        yaml += '      - *stable-vendor-fast-hdmi\n'
    if vendor_slow:
        yaml += '      - *stable-vendor-slow-hdmi\n'
    if vendor_riscv64:
        yaml += '      - *stable-vendor-riscv64\n'
    if vendor_loongarch:
        yaml += '      - *stable-vendor-loongarch\n'
    if vendor_headless:
        yaml += '      - *stable-vendor-headless\n'
    if legacy_fast:
        yaml += '      - *stable-legacy-fast-hdmi\n'
    if legacy_slow:
        yaml += '      - *stable-legacy-slow-hdmi\n'
    if legacy_riscv64:
        yaml += '      - *stable-legacy-riscv64\n'
    if legacy_loongarch:
        yaml += '      - *stable-legacy-loongarch\n'
    if legacy_headless:
        yaml += '      - *stable-legacy-headless\n'
    if edge_fast:
        yaml += '      - *stable-edge-fast-hdmi\n'
    if edge_slow:
        yaml += '      - *stable-edge-slow-hdmi\n'
    if edge_riscv64:
        yaml += '      - *stable-edge-riscv64\n'
    if edge_loongarch:
        yaml += '      - *stable-edge-loongarch\n'
    if edge_headless:
        yaml += '      - *stable-edge-headless\n'

    # Ubuntu stable XFCE desktop (slow HDMI only)
    if current_slow or edge_slow:
        yaml += """
  # Ubuntu stable XFCE desktop (slow HDMI only)
  desktop-stable-ubuntu-xfce:
    enabled: yes
    configs: [ armbian-images ]
    pipeline:
      gha: *armbian-gha
    build-image: "yes"
    vars:
      RELEASE: UBUNTU
      BUILD_MINIMAL: "no"
      BUILD_DESKTOP: "yes"
      DESKTOP_ENVIRONMENT: "xfce"
      DESKTOP_ENVIRONMENT_CONFIG_NAME: "config_base"
      DESKTOP_APPGROUPS_SELECTED: "programming"
      DESKTOP_TIER: "mid"
    items:
      - *stable-current-slow-hdmi
"""
        if vendor_slow:
            yaml += '      - *stable-vendor-slow-hdmi\n'
        if edge_slow:
            yaml += '      - *stable-edge-slow-hdmi\n'

    # Ubuntu stable GNOME desktop (fast HDMI only)
    if current_fast or legacy_fast or edge_fast:
        yaml += """
  # Ubuntu stable GNOME desktop (fast HDMI only)
  desktop-stable-ubuntu-gnome:
    enabled: yes
    configs: [ armbian-images ]
    pipeline:
      gha: *armbian-gha
    build-image: "yes"
    vars:
      RELEASE: UBUNTU
      BUILD_MINIMAL: "no"
      BUILD_DESKTOP: "yes"
      DESKTOP_ENVIRONMENT: "gnome"
      DESKTOP_ENVIRONMENT_CONFIG_NAME: "config_base"
      DESKTOP_APPGROUPS_SELECTED: "programming"
      DESKTOP_TIER: "mid"
    items:
"""
        if current_fast:
            yaml += '      - *stable-current-fast-hdmi\n'
        if vendor_fast:
            yaml += '      - *stable-vendor-fast-hdmi\n'
        if legacy_fast:
            yaml += '      - *stable-legacy-fast-hdmi\n'
        if edge_fast:
            yaml += '      - *stable-edge-fast-hdmi\n'

    # Ubuntu stable KDE Neon desktop (fast HDMI only)
    if current_fast or edge_fast:
        yaml += """
  # Ubuntu stable KDE Neon desktop (fast HDMI only)
  desktop-stable-ubuntu-kde-neon:
    enabled: yes
    configs: [ armbian-images ]
    pipeline:
      gha: *armbian-gha
    build-image: "yes"
    vars:
      RELEASE: UBUNTU
      BUILD_MINIMAL: "no"
      BUILD_DESKTOP: "yes"
      DESKTOP_ENVIRONMENT: "kde-neon"
      DESKTOP_ENVIRONMENT_CONFIG_NAME: "config_base"
      DESKTOP_APPGROUPS_SELECTED: "programming"
      DESKTOP_TIER: "mid"
    items:
      - *stable-current-fast-hdmi
"""
        if vendor_fast:
            yaml += '      - *stable-vendor-fast-hdmi\n'
        if edge_fast:
            yaml += '      - *stable-edge-fast-hdmi\n'

    # Ubuntu stable XFCE desktop for legacy fast HDMI boards
    if legacy_fast:
        yaml += """
  # Ubuntu stable XFCE desktop for legacy fast HDMI boards
  desktop-stable-ubuntu-legacy-xfce:
    enabled: yes
    configs: [ armbian-images ]
    pipeline:
      gha: *armbian-gha
    build-image: "yes"
    vars:
      RELEASE: UBUNTU
      BUILD_MINIMAL: "no"
      BUILD_DESKTOP: "yes"
      DESKTOP_ENVIRONMENT: "xfce"
      DESKTOP_ENVIRONMENT_CONFIG_NAME: "config_base"
      DESKTOP_APPGROUPS_SELECTED: "programming"
      DESKTOP_TIER: "mid"
    items:
      - *stable-legacy-fast-hdmi
"""

    # Ubuntu stable XFCE desktop for RISC-V boards
    if current_riscv64 or vendor_riscv64 or legacy_riscv64 or edge_riscv64:
        yaml += """
  # Ubuntu stable XFCE desktop for RISC-V boards
  desktop-stable-ubuntu-riscv64-xfce:
    enabled: yes
    configs: [ armbian-images ]
    pipeline:
      gha: *armbian-gha
    build-image: "yes"
    vars:
      RELEASE: UBUNTU
      BUILD_MINIMAL: "no"
      BUILD_DESKTOP: "yes"
      DESKTOP_ENVIRONMENT: "xfce"
      DESKTOP_ENVIRONMENT_CONFIG_NAME: "config_base"
      DESKTOP_APPGROUPS_SELECTED: ""
      DESKTOP_TIER: "minimal"
    items:
"""
        if current_riscv64:
            yaml += '      - *stable-current-riscv64\n'
        if vendor_riscv64:
            yaml += '      - *stable-vendor-riscv64\n'
        if legacy_riscv64:
            yaml += '      - *stable-legacy-riscv64\n'
        if edge_riscv64:
            yaml += '      - *stable-edge-riscv64\n'

    # Ubuntu noble Bianbu desktop for RISC-V (SpacemiT K1, legacy branch only).
    # Bianbu's PVR-DRI userspace is tied to the SpacemiT BSP kernel that lives
    # on the legacy branch, and the SpacemiT archive only ships its Mesa fork
    # (24.01bbx, pinned via configng's bianbu.yaml) on noble — `RELEASE: noble`
    # is therefore literal here, not the substitutable `UBUNTU` token.
    # Tier=mid because bianbu-minimal is intentionally bare; mid is the
    # canonical Bianbu desktop experience.
    if legacy_riscv64:
        yaml += """
  # Ubuntu noble Bianbu desktop for SpacemiT K1 boards (legacy branch)
  desktop-stable-ubuntu-riscv64-bianbu:
    enabled: yes
    configs: [ armbian-images ]
    pipeline:
      gha: *armbian-gha
    build-image: "yes"
    vars:
      RELEASE: noble
      BUILD_MINIMAL: "no"
      BUILD_DESKTOP: "yes"
      DESKTOP_ENVIRONMENT: "bianbu"
      DESKTOP_ENVIRONMENT_CONFIG_NAME: "config_base"
      DESKTOP_APPGROUPS_SELECTED: ""
      DESKTOP_TIER: "mid"
    items:
      - *stable-legacy-riscv64
"""

    if manual_content:
        # Indent manual content by 2 spaces to be under targets:
        indented_manual = '\n'.join('  ' + line if line.strip() else line for line in manual_content.split('\n'))
        yaml += '\n' + indented_manual

    # Add riscv64 minimal target if any riscv64 boards exist
    if current_riscv64 or vendor_riscv64 or edge_riscv64:
        yaml += """
  # Ubuntu stable minimal - RISC-V
  minimal-stable-ubuntu-riscv:
    enabled: yes
    configs: [ armbian-images ]
    pipeline:
      gha: *armbian-gha
    build-image: "yes"
    vars:
      RELEASE: UBUNTU
      BUILD_MINIMAL: "yes"
      BUILD_DESKTOP: "no"
    items:
"""
        if current_riscv64:
            yaml += '      - *stable-current-riscv64\n'
        if vendor_riscv64:
            yaml += '      - *stable-vendor-riscv64\n'
        if edge_riscv64:
            yaml += '      - *stable-edge-riscv64\n'
        yaml += '\n'

    # Add loongarch target if any loongarch boards exist
    if current_loongarch or vendor_loongarch or edge_loongarch:
        yaml += """
  # Ubuntu stable minimal - LoongArch
  minimal-stable-ubuntu-loongarch:
    enabled: yes
    configs: [ armbian-images ]
    pipeline:
      gha: *armbian-gha
    build-image: "yes"
    vars:
      RELEASE: UBUNTU
      BUILD_MINIMAL: "yes"
      BUILD_DESKTOP: "no"
    items:
"""
        if current_loongarch:
            yaml += '      - *stable-current-loongarch\n'
        if vendor_loongarch:
            yaml += '      - *stable-vendor-loongarch\n'
        if edge_loongarch:
            yaml += '      - *stable-edge-loongarch\n'
        yaml += '\n'

    return yaml


def generate_nightly_yaml(conf_wip_boards, manual_content=""):
    """
    Generate nightly.yml with:
    - One minimal Debian Forky CLI image for all boards
    - For fast HDMI: Ubuntu Resolute GNOME desktop
    - For slow HDMI: Ubuntu Resolute XFCE desktop
    - For headless and exotics (riscv64, loongarch): Ubuntu Resolute minimal CLI
    One image per board for conf/wip boards.
    Separates fast, slow, riscv64, loongarch, and headless boards based on CPU performance.
    manual_content: Additional YAML to append inside the targets section
    """
    yaml = generate_yaml_header()

    # Select one branch per board, prefer current
    boards = select_one_branch_per_board(conf_wip_boards)

    # Separate by performance/architecture
    fast_boards = [b for b in boards if b['is_fast'] is True]
    slow_boards = [b for b in boards if b['is_fast'] is False]
    riscv64_boards = [b for b in boards if b['is_fast'] == 'riscv64']
    loongarch_boards = [b for b in boards if b['is_fast'] == 'loongarch']
    headless_boards = [b for b in boards if b['is_fast'] is None]

    yaml += """# Nightly builds - fast HDMI (quad-core+ or modern SoCs)
  nightly-fast-hdmi: &nightly-fast-hdmi
  # auto generated section
"""
    for board_data in sorted(fast_boards, key=lambda x: x['board']):
        yaml += format_board_item(board_data, include_extensions=True) + '\n'

    yaml += '  # end of auto generated section\n\n'

    if slow_boards:
        yaml += '  nightly-slow-hdmi: &nightly-slow-hdmi\n'
        yaml += '  # auto generated section\n'
        for board_data in sorted(slow_boards, key=lambda x: x['board']):
            yaml += format_board_item(board_data, include_extensions=True) + '\n'
        yaml += '  # end of auto generated section\n\n'

    if riscv64_boards:
        yaml += '  nightly-riscv64: &nightly-riscv64\n'
        yaml += '  # auto generated section\n'
        for board_data in sorted(riscv64_boards, key=lambda x: x['board']):
            yaml += format_board_item(board_data, include_extensions=True) + '\n'
        yaml += '  # end of auto generated section\n\n'

    if loongarch_boards:
        yaml += '  nightly-loongarch: &nightly-loongarch\n'
        yaml += '  # auto generated section\n'
        for board_data in sorted(loongarch_boards, key=lambda x: x['board']):
            yaml += format_board_item(board_data, include_extensions=True) + '\n'
        yaml += '  # end of auto generated section\n\n'

    if headless_boards:
        yaml += '  nightly-headless: &nightly-headless\n'
        yaml += '  # auto generated section\n'
        for board_data in sorted(headless_boards, key=lambda x: x['board']):
            yaml += format_board_item(board_data, include_extensions=True) + '\n'
        yaml += '  # end of auto generated section\n\n'

    yaml += """# automated lists stop

targets:
  # Debian minimal CLI for all boards
  nightly-forky-all:
    enabled: yes
    configs: [ armbian-images ]
    pipeline:
      gha: *armbian-gha
    build-image: "yes"
    vars:
      RELEASE: DEBIAN
      BUILD_MINIMAL: "yes"
      BUILD_DESKTOP: "no"
    items:
"""
    # Combine all lists for Debian Forky
    yaml += '      - *nightly-fast-hdmi\n'
    if slow_boards:
        yaml += '      - *nightly-slow-hdmi\n'
    if headless_boards:
        yaml += '      - *nightly-headless\n'
    if riscv64_boards:
        yaml += '      - *nightly-riscv64\n'
    if loongarch_boards:
        yaml += '      - *nightly-loongarch\n'

    yaml += """
  # Ubuntu GNOME desktop for fast HDMI boards
  nightly-resolute-gnome:
    enabled: yes
    configs: [ armbian-images ]
    pipeline:
      gha: *armbian-gha
    build-image: "yes"
    vars:
      RELEASE: UBUNTU
      BUILD_MINIMAL: "no"
      BUILD_DESKTOP: "yes"
      DESKTOP_ENVIRONMENT: "gnome"
      DESKTOP_ENVIRONMENT_CONFIG_NAME: "config_base"
      DESKTOP_APPGROUPS_SELECTED: ""
      DESKTOP_TIER: "minimal"
    items:
      - *nightly-fast-hdmi
"""

    # Ubuntu XFCE desktop for slow HDMI boards
    if slow_boards:
        yaml += """
  # Ubuntu XFCE desktop for slow HDMI boards
  nightly-resolute-xfce:
    enabled: yes
    configs: [ armbian-images ]
    pipeline:
      gha: *armbian-gha
    build-image: "yes"
    vars:
      RELEASE: UBUNTU
      BUILD_MINIMAL: "no"
      BUILD_DESKTOP: "yes"
      DESKTOP_ENVIRONMENT: "xfce"
      DESKTOP_ENVIRONMENT_CONFIG_NAME: "config_base"
      DESKTOP_APPGROUPS_SELECTED: ""
      DESKTOP_TIER: "minimal"
    items:
      - *nightly-slow-hdmi
"""

    # Ubuntu XFCE desktop for RISC-V boards
    if riscv64_boards:
        yaml += """
  # Ubuntu XFCE desktop for RISC-V boards
  nightly-resolute-riscv64-xfce:
    enabled: yes
    configs: [ armbian-images ]
    pipeline:
      gha: *armbian-gha
    build-image: "yes"
    vars:
      RELEASE: UBUNTU
      BUILD_MINIMAL: "no"
      BUILD_DESKTOP: "yes"
      DESKTOP_ENVIRONMENT: "xfce"
      DESKTOP_ENVIRONMENT_CONFIG_NAME: "config_base"
      DESKTOP_APPGROUPS_SELECTED: ""
      DESKTOP_TIER: "minimal"
    items:
      - *nightly-riscv64
"""

    # Ubuntu minimal CLI for headless boards only
    if headless_boards:
        yaml += """
  # Ubuntu minimal CLI for headless boards
  nightly-resolute-minimal:
    enabled: yes
    configs: [ armbian-images ]
    pipeline:
      gha: *armbian-gha
    build-image: "yes"
    vars:
      RELEASE: UBUNTU
      BUILD_MINIMAL: "yes"
      BUILD_DESKTOP: "no"
    items:
      - *nightly-headless
"""

    # Note: loongarch boards don't get resolute images, only bookworm minimal

    if manual_content:
        # Indent manual content by 2 spaces to be under targets:
        indented_manual = '\n'.join('  ' + line if line.strip() else line for line in manual_content.split('\n'))
        yaml += '\n' + indented_manual

    return yaml


def generate_community_yaml(csc_tvb_boards, manual_content=""):
    """
    Generate community.yml for csc+tvb boards with hardware-based desktop selection.
    - Debian Forky minimal CLI for all boards
    - Ubuntu Noble with desktops based on hardware speed (like nightly)
    manual_content: Additional YAML to append inside the targets section
    """
    yaml = generate_yaml_header()

    # Separate by branch and performance
    current_fast = [b for b in csc_tvb_boards if b['branch'] == 'current' and b['is_fast'] is True]
    current_slow = [b for b in csc_tvb_boards if b['branch'] == 'current' and b['is_fast'] is False]
    current_headless = [b for b in csc_tvb_boards if b['branch'] == 'current' and b['is_fast'] is None]
    current_riscv64 = [b for b in csc_tvb_boards if b['branch'] == 'current' and b['is_fast'] == 'riscv64']
    current_loongarch = [b for b in csc_tvb_boards if b['branch'] == 'current' and b['is_fast'] == 'loongarch']

    vendor_fast = [b for b in csc_tvb_boards if b['branch'] == 'vendor' and b['is_fast'] is True]
    vendor_slow = [b for b in csc_tvb_boards if b['branch'] == 'vendor' and b['is_fast'] is False]
    vendor_headless = [b for b in csc_tvb_boards if b['branch'] == 'vendor' and b['is_fast'] is None]
    vendor_riscv64 = [b for b in csc_tvb_boards if b['branch'] == 'vendor' and b['is_fast'] == 'riscv64']
    vendor_loongarch = [b for b in csc_tvb_boards if b['branch'] == 'vendor' and b['is_fast'] == 'loongarch']

    legacy_fast = [b for b in csc_tvb_boards if b['branch'] == 'legacy' and b['is_fast'] is True]
    legacy_slow = [b for b in csc_tvb_boards if b['branch'] == 'legacy' and b['is_fast'] is False]
    legacy_headless = [b for b in csc_tvb_boards if b['branch'] == 'legacy' and b['is_fast'] is None]
    legacy_riscv64 = [b for b in csc_tvb_boards if b['branch'] == 'legacy' and b['is_fast'] == 'riscv64']
    legacy_loongarch = [b for b in csc_tvb_boards if b['branch'] == 'legacy' and b['is_fast'] == 'loongarch']

    # Build set of boards that have current branch (to exclude from edge)
    current_boards = {b['board'] for b in csc_tvb_boards if b['branch'] == 'current'}

    # Only include edge boards for boards that don't have current branch
    edge_fast = [b for b in csc_tvb_boards if b['branch'] == 'edge' and b['is_fast'] is True and b['board'] not in current_boards]
    edge_slow = [b for b in csc_tvb_boards if b['branch'] == 'edge' and b['is_fast'] is False and b['board'] not in current_boards]
    edge_headless = [b for b in csc_tvb_boards if b['branch'] == 'edge' and b['is_fast'] is None and b['board'] not in current_boards]
    edge_riscv64 = [b for b in csc_tvb_boards if b['branch'] == 'edge' and b['is_fast'] == 'riscv64' and b['board'] not in current_boards]
    edge_loongarch = [b for b in csc_tvb_boards if b['branch'] == 'edge' and b['is_fast'] == 'loongarch' and b['board'] not in current_boards]

    yaml += """# Community builds - fast HDMI (current branch)
  community-current-fast-hdmi: &community-current-fast-hdmi
  # auto generated section
"""
    for board_data in sorted(current_fast, key=lambda x: x['board']):
        yaml += format_board_item(board_data, include_extensions=True) + '\n'

    yaml += '  # end of auto generated section\n\n'

    if current_slow:
        yaml += '  community-current-slow-hdmi: &community-current-slow-hdmi\n'
        yaml += '  # auto generated section\n'
        for board_data in sorted(current_slow, key=lambda x: x['board']):
            yaml += format_board_item(board_data, include_extensions=True) + '\n'
        yaml += '  # end of auto generated section\n\n'

    if current_headless:
        yaml += '  community-current-headless: &community-current-headless\n'
        yaml += '  # auto generated section\n'
        for board_data in sorted(current_headless, key=lambda x: x['board']):
            yaml += format_board_item(board_data, include_extensions=True) + '\n'
        yaml += '  # end of auto generated section\n\n'

    if current_riscv64:
        yaml += '  community-current-riscv64: &community-current-riscv64\n'
        yaml += '  # auto generated section\n'
        for board_data in sorted(current_riscv64, key=lambda x: x['board']):
            yaml += format_board_item(board_data, include_extensions=True) + '\n'
        yaml += '  # end of auto generated section\n\n'

    if current_loongarch:
        yaml += '  community-current-loongarch: &community-current-loongarch\n'
        yaml += '  # auto generated section\n'
        for board_data in sorted(current_loongarch, key=lambda x: x['board']):
            yaml += format_board_item(board_data, include_extensions=True) + '\n'
        yaml += '  # end of auto generated section\n\n'

    # Vendor branch lists
    if vendor_fast:
        yaml += '  community-vendor-fast-hdmi: &community-vendor-fast-hdmi\n'
        yaml += '  # auto generated section\n'
        for board_data in sorted(vendor_fast, key=lambda x: x['board']):
            yaml += format_board_item(board_data, include_extensions=True) + '\n'
        yaml += '  # end of auto generated section\n\n'

    if vendor_slow:
        yaml += '  community-vendor-slow-hdmi: &community-vendor-slow-hdmi\n'
        yaml += '  # auto generated section\n'
        for board_data in sorted(vendor_slow, key=lambda x: x['board']):
            yaml += format_board_item(board_data, include_extensions=True) + '\n'
        yaml += '  # end of auto generated section\n\n'

    if vendor_headless:
        yaml += '  community-vendor-headless: &community-vendor-headless\n'
        yaml += '  # auto generated section\n'
        for board_data in sorted(vendor_headless, key=lambda x: x['board']):
            yaml += format_board_item(board_data, include_extensions=True) + '\n'
        yaml += '  # end of auto generated section\n\n'

    if vendor_riscv64:
        yaml += '  community-vendor-riscv64: &community-vendor-riscv64\n'
        yaml += '  # auto generated section\n'
        for board_data in sorted(vendor_riscv64, key=lambda x: x['board']):
            yaml += format_board_item(board_data, include_extensions=True) + '\n'
        yaml += '  # end of auto generated section\n\n'

    if vendor_loongarch:
        yaml += '  community-vendor-loongarch: &community-vendor-loongarch\n'
        yaml += '  # auto generated section\n'
        for board_data in sorted(vendor_loongarch, key=lambda x: x['board']):
            yaml += format_board_item(board_data, include_extensions=True) + '\n'
        yaml += '  # end of auto generated section\n\n'

    # Edge branch lists
    if edge_fast:
        yaml += '  community-edge-fast-hdmi: &community-edge-fast-hdmi\n'
        yaml += '  # auto generated section\n'
        for board_data in sorted(edge_fast, key=lambda x: x['board']):
            yaml += format_board_item(board_data, include_extensions=True) + '\n'
        yaml += '  # end of auto generated section\n\n'

    if edge_slow:
        yaml += '  community-edge-slow-hdmi: &community-edge-slow-hdmi\n'
        yaml += '  # auto generated section\n'
        for board_data in sorted(edge_slow, key=lambda x: x['board']):
            yaml += format_board_item(board_data, include_extensions=True) + '\n'
        yaml += '  # end of auto generated section\n\n'

    if edge_headless:
        yaml += '  community-edge-headless: &community-edge-headless\n'
        yaml += '  # auto generated section\n'
        for board_data in sorted(edge_headless, key=lambda x: x['board']):
            yaml += format_board_item(board_data, include_extensions=True) + '\n'
        yaml += '  # end of auto generated section\n\n'

    if edge_riscv64:
        yaml += '  community-edge-riscv64: &community-edge-riscv64\n'
        yaml += '  # auto generated section\n'
        for board_data in sorted(edge_riscv64, key=lambda x: x['board']):
            yaml += format_board_item(board_data, include_extensions=True) + '\n'
        yaml += '  # end of auto generated section\n\n'

    if edge_loongarch:
        yaml += '  community-edge-loongarch: &community-edge-loongarch\n'
        yaml += '  # auto generated section\n'
        for board_data in sorted(edge_loongarch, key=lambda x: x['board']):
            yaml += format_board_item(board_data, include_extensions=True) + '\n'
        yaml += '  # end of auto generated section\n\n'

    yaml += """# automated lists stop

targets:
  # Debian minimal CLI for all community boards
  community-trixie-all:
    enabled: yes
    configs: [ armbian-community ]
    pipeline:
      gha: *armbian-gha
    build-image: "yes"
    vars:
      RELEASE: DEBIAN
      BUILD_MINIMAL: "yes"
      BUILD_DESKTOP: "no"
    items:
"""
    # Combine all lists for Debian Trixie
    yaml += '      - *community-current-fast-hdmi\n'
    if current_slow:
        yaml += '      - *community-current-slow-hdmi\n'
    if current_headless:
        yaml += '      - *community-current-headless\n'
    if current_riscv64:
        yaml += '      - *community-current-riscv64\n'
    if current_loongarch:
        yaml += '      - *community-current-loongarch\n'
    if vendor_fast:
        yaml += '      - *community-vendor-fast-hdmi\n'
    if vendor_slow:
        yaml += '      - *community-vendor-slow-hdmi\n'
    if vendor_headless:
        yaml += '      - *community-vendor-headless\n'
    if vendor_riscv64:
        yaml += '      - *community-vendor-riscv64\n'
    if vendor_loongarch:
        yaml += '      - *community-vendor-loongarch\n'
    if edge_fast:
        yaml += '      - *community-edge-fast-hdmi\n'
    if edge_slow:
        yaml += '      - *community-edge-slow-hdmi\n'
    if edge_headless:
        yaml += '      - *community-edge-headless\n'
    if edge_riscv64:
        yaml += '      - *community-edge-riscv64\n'
    if edge_loongarch:
        yaml += '      - *community-edge-loongarch\n'

    yaml += """
  # Ubuntu GNOME desktop for fast HDMI community boards
  community-noble-gnome:
    enabled: yes
    configs: [ armbian-community ]
    pipeline:
      gha: *armbian-gha
    build-image: "yes"
    vars:
      RELEASE: UBUNTU
      BUILD_MINIMAL: "no"
      BUILD_DESKTOP: "yes"
      DESKTOP_ENVIRONMENT: "gnome"
      DESKTOP_ENVIRONMENT_CONFIG_NAME: "config_base"
      DESKTOP_APPGROUPS_SELECTED: ""
      DESKTOP_TIER: "minimal"
    items:
      - *community-current-fast-hdmi
"""
    if vendor_fast:
        yaml += '      - *community-vendor-fast-hdmi\n'
    if edge_fast:
        yaml += '      - *community-edge-fast-hdmi\n'

    # Ubuntu KDE Neon desktop for fast HDMI community boards
    if current_fast or vendor_fast or edge_fast:
        yaml += """
  # Ubuntu KDE Neon desktop for fast HDMI community boards
  community-noble-kde-neon:
    enabled: yes
    configs: [ armbian-community ]
    pipeline:
      gha: *armbian-gha
    build-image: "yes"
    vars:
      RELEASE: UBUNTU
      BUILD_MINIMAL: "no"
      BUILD_DESKTOP: "yes"
      DESKTOP_ENVIRONMENT: "kde-neon"
      DESKTOP_ENVIRONMENT_CONFIG_NAME: "config_base"
      DESKTOP_APPGROUPS_SELECTED: ""
      DESKTOP_TIER: "minimal"
    items:
      - *community-current-fast-hdmi
"""
        if vendor_fast:
            yaml += '      - *community-vendor-fast-hdmi\n'
        if edge_fast:
            yaml += '      - *community-edge-fast-hdmi\n'

    # Ubuntu XFCE desktop for slow HDMI community boards
    if current_slow or vendor_slow or edge_slow:
        yaml += """
  # Ubuntu XFCE desktop for slow HDMI community boards
  community-noble-xfce:
    enabled: yes
    configs: [ armbian-community ]
    pipeline:
      gha: *armbian-gha
    build-image: "yes"
    vars:
      RELEASE: UBUNTU
      BUILD_MINIMAL: "no"
      BUILD_DESKTOP: "yes"
      DESKTOP_ENVIRONMENT: "xfce"
      DESKTOP_ENVIRONMENT_CONFIG_NAME: "config_base"
      DESKTOP_APPGROUPS_SELECTED: ""
      DESKTOP_TIER: "minimal"
    items:
"""
        if current_slow:
            yaml += '      - *community-current-slow-hdmi\n'
        if vendor_slow:
            yaml += '      - *community-vendor-slow-hdmi\n'
        if edge_slow:
            yaml += '      - *community-edge-slow-hdmi\n'

    # Ubuntu XFCE desktop for RISC-V community boards
    if current_riscv64 or vendor_riscv64 or edge_riscv64:
        yaml += """
  # Ubuntu XFCE desktop for RISC-V community boards
  community-noble-riscv64-xfce:
    enabled: yes
    configs: [ armbian-community ]
    pipeline:
      gha: *armbian-gha
    build-image: "yes"
    vars:
      RELEASE: UBUNTU
      BUILD_MINIMAL: "no"
      BUILD_DESKTOP: "yes"
      DESKTOP_ENVIRONMENT: "xfce"
      DESKTOP_ENVIRONMENT_CONFIG_NAME: "config_base"
      DESKTOP_APPGROUPS_SELECTED: ""
      DESKTOP_TIER: "minimal"
    items:
"""
        if current_riscv64:
            yaml += '      - *community-current-riscv64\n'
        if vendor_riscv64:
            yaml += '      - *community-vendor-riscv64\n'
        if edge_riscv64:
            yaml += '      - *community-edge-riscv64\n'

    # Ubuntu minimal CLI for headless community boards
    if current_headless or vendor_headless or edge_headless:
        yaml += """
  # Ubuntu minimal CLI for headless community boards
  community-noble-minimal:
    enabled: yes
    configs: [ armbian-community ]
    pipeline:
      gha: *armbian-gha
    build-image: "yes"
    vars:
      RELEASE: UBUNTU
      BUILD_MINIMAL: "yes"
      BUILD_DESKTOP: "no"
    items:
"""
        if current_headless:
            yaml += '      - *community-current-headless\n'
        if vendor_headless:
            yaml += '      - *community-vendor-headless\n'
        if edge_headless:
            yaml += '      - *community-edge-headless\n'

    # Note: loongarch boards don't get noble images, only bookworm minimal

    if manual_content:
        # Indent manual content by 2 spaces to be under targets:
        indented_manual = '\n'.join('  ' + line if line.strip() else line for line in manual_content.split('\n'))
        yaml += '\n' + indented_manual

    return yaml


def capitalize_board_name(board):
    """Capitalize board name for exposed.map pattern (e.g., bananapim4zero -> Bananapim4zero)."""
    return board.capitalize()


def generate_exposed_map(
    conf_wip_boards,
    csc_tvb_boards=None,
    *,
    debian_standard,
    ubuntu_standard,
    debian_community,
    ubuntu_community,
    overrides=None,
):
    """
    Generate exposed.map with regex patterns for recommended images.
    For each board, generates 2 patterns:
    1. Minimal: Debian + current branch
    2. For boards with video: Ubuntu + desktop (gnome/xfce)
       For headless:   Ubuntu + minimal
       For riscv64:    Ubuntu + xfce desktop

    conf_wip_boards: stable boards (conf/wip support level) - images have no 'community_' prefix
    csc_tvb_boards:  community boards (csc/tvb support level) - images have 'community_' prefix

    The Debian/Ubuntu codenames baked into each generated regex are picked
    per board based on its support tier — stable boards use the standard-
    support codenames, community boards use the community codenames — so
    the exposed.map patterns track whatever codename the YAML files were
    last generated with. Without this, `generate_*_yaml` could be promoted
    to a new release while exposed.map kept matching the old one and
    "recommended images" would silently drop off the website.

    overrides: list returned by load_exposed_overrides(). Each entry
    may carry a `minimal:` block (overrides pattern 1) and/or a
    `desktop:` block (overrides pattern 2). Each block can swap in a
    custom (release, branch, suffix) tuple. Used by vendor BSPs whose
    recommended images live off the algorithmic default — see
    exposed.map.overrides.yaml.
    """
    if csc_tvb_boards is None:
        csc_tvb_boards = []
    if overrides is None:
        overrides = []

    lines = []
    single_image_boards = []  # Track boards with only minimal image (loongarch only)

    # Mark boards with their type (stable vs community)
    stable_boards = [{**board, 'board_type': 'stable'} for board in conf_wip_boards]
    community_boards = [{**board, 'board_type': 'community'} for board in csc_tvb_boards]

    # Combine and select one branch per board
    all_boards = select_one_branch_per_board(stable_boards + community_boards)

    # Sort by board name
    all_boards.sort(key=lambda x: x['board'])

    for board_data in all_boards:
        board = board_data['board']
        branch = board_data['branch']
        is_fast = board_data['is_fast']
        board_type = board_data.get('board_type', 'stable')  # 'stable' or 'community'
        entry = board_data['entry']
        extensions = board_data.get('extensions', '')

        # Get inventory data for checking extensions
        inventory = entry.get('in', {}).get('inventory', {})
        board_has_video = inventory.get('BOARD_HAS_VIDEO', False)
        # BOARDFAMILY for override matching — same fallback path as
        # is_fast_hardware uses, since some boards only set it under
        # BOARD_TOP_LEVEL_VARS rather than at the inventory root.
        boardfamily = (
            inventory.get('BOARDFAMILY', '')
            or inventory.get('BOARD_TOP_LEVEL_VARS', {}).get('BOARDFAMILY', '')
        )
        override = match_exposed_override(overrides, board=board, boardfamily=boardfamily)

        # Determine file extension based on extensions
        # Check for special output formats
        file_ext = '.img.xz'
        if 'image-output-oowow' in extensions:
            file_ext = '.oowow.img.xz'

        # Pattern prefix: boardname/archive/
        # Use lowercase board name for directory
        dir_prefix = f"{board}/archive/"

        # Pattern format: Armbian_[0-9].*BoardName_Release_Branch_[0-9]*.[0-9]*.[0-9]*_Type.ext
        # Community images have 'community_' prefix, stable images don't
        # This excludes nightly images (which come from armbian/os repo without 'community_' prefix)
        community_prefix = '(community_)?' if board_type == 'community' else ''
        # Capitalize board name for pattern
        board_pattern = capitalize_board_name(board)

        # Per-board (debian, ubuntu) codename pair — stable boards
        # follow the standard-support flags, community boards follow
        # the community flags. Keeps exposed.map regex patterns in
        # lockstep with whatever codenames the YAML files were just
        # generated against.
        if board_type == 'community':
            debian_codename = debian_community
            ubuntu_codename = ubuntu_community
        else:
            debian_codename = debian_standard
            ubuntu_codename = ubuntu_standard

        # 1. Minimal: Debian + board's branch + "minimal" by default.
        # Apply override.minimal (if any) — vendor BSPs whose minimal
        # image lives off the default Debian release/branch combination
        # can redirect both the release codename and the regex tail
        # (e.g. spacemit's K1 boards have no Debian-trixie-legacy image
        # but do have Ubuntu-noble-legacy minimal).
        m_release = debian_codename
        m_branch = branch
        m_suffix = 'minimal'
        if override and isinstance(override.get('minimal'), dict):
            mb = override['minimal']
            m_release = mb.get('release', m_release)
            m_branch = mb.get('branch', m_branch)
            m_suffix = mb.get('suffix', m_suffix)

        minimal_pattern = f"{dir_prefix}Armbian_{community_prefix}[0-9].*{board_pattern}_{m_release}_{m_branch}_[0-9]*.[0-9]*.[0-9]*_{m_suffix}{file_ext}"
        minimal_pattern_no_prefix = f"Armbian_{community_prefix}[0-9].*{board_pattern}_{m_release}_{m_branch}_[0-9]*.[0-9]*.[0-9]*_{m_suffix}{file_ext}"
        lines.append(minimal_pattern)
        lines.append(minimal_pattern_no_prefix)

        # 2. Second pattern: Ubuntu image, suffix depends on board type.
        # loongarch is the exception — only the Debian minimal pattern
        # above is emitted, no Ubuntu image exists for it yet.
        if is_fast == 'loongarch':
            single_image_boards.append(board)
            continue

        # Default suffix (the `..._<suffix>{file_ext}` tail of the regex)
        # mirrors the historical behaviour:
        #   riscv64        → xfce_desktop
        #   video + fast   → gnome_desktop
        #   video + slow   → xfce_desktop
        #   headless       → minimal
        if is_fast == 'riscv64':
            default_suffix = 'xfce_desktop'
        elif board_has_video and is_fast is not None:
            default_suffix = 'gnome_desktop' if is_fast is True else 'xfce_desktop'
        else:
            default_suffix = 'minimal'

        # Apply override.desktop (if any). suffix is the literal regex
        # tail (e.g. "bianbu_desktop"), not just the desktop name —
        # keeps the schema symmetric with the minimal block above.
        d_release = ubuntu_codename
        d_branch = branch
        d_suffix = default_suffix
        if override and isinstance(override.get('desktop'), dict):
            db = override['desktop']
            d_release = db.get('release', d_release)
            d_branch = db.get('branch', d_branch)
            d_suffix = db.get('suffix', d_suffix)

        second_pattern = f"{dir_prefix}Armbian_{community_prefix}[0-9].*{board_pattern}_{d_release}_{d_branch}_[0-9]*.[0-9]*.[0-9]*_{d_suffix}{file_ext}"
        second_pattern_no_prefix = f"Armbian_{community_prefix}[0-9].*{board_pattern}_{d_release}_{d_branch}_[0-9]*.[0-9]*.[0-9]*_{d_suffix}{file_ext}"
        lines.append(second_pattern)
        lines.append(second_pattern_no_prefix)

    # Display warning for boards with only one image (loongarch only)
    if single_image_boards:
        print(f"Warning: {len(single_image_boards)} boards with only minimal image (loongarch):", file=sys.stderr)
        for board in sorted(single_image_boards):
            print(f"  - {board}", file=sys.stderr)

    return '\n'.join(lines) + '\n'


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Generate Armbian target YAML files. The emitted YAML carries "
            "symbolic RELEASE tokens (DEBIAN / UBUNTU) that get substituted "
            "with codenames passed via per-scope flags "
            f"(--debian-<{'|'.join(SCOPE_DEFAULTS)}> / "
            f"--ubuntu-<{'|'.join(SCOPE_DEFAULTS)}>) just before each output "
            "file is written. Defaults preserve the previous literal pins, "
            "so running with no flags reproduces the old behaviour exactly. "
            "Promoting a release line is a flag flip, not a multi-place rename."
        )
    )
    parser.add_argument(
        "json_path",
        type=Path,
        help="Path to image-info.json",
    )
    parser.add_argument(
        "output_dir",
        type=Path,
        nargs="?",
        default=Path.cwd(),
        help="Where to write the generated YAML files (default: cwd)",
    )
    # One pair of (--debian-<scope>, --ubuntu-<scope>) flags per output
    # file, registered in a loop so adding a new scope is a one-line
    # change to SCOPE_DEFAULTS.
    for scope, defaults in SCOPE_DEFAULTS.items():
        parser.add_argument(
            f"--debian-{scope}",
            default=defaults["debian"],
            metavar="CODENAME",
            dest=f"debian_{scope}",
            help=f"Debian codename used in the {scope} output file "
                 f"(default: {defaults['debian']})",
        )
        parser.add_argument(
            f"--ubuntu-{scope}",
            default=defaults["ubuntu"],
            metavar="CODENAME",
            dest=f"ubuntu_{scope}",
            help=f"Ubuntu codename used in the {scope} output file "
                 f"(default: {defaults['ubuntu']})",
        )
    args = parser.parse_args()

    json_path = args.json_path
    output_dir = args.output_dir

    if not json_path.exists():
        print(f"Error: {json_path} does not exist")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Load extensions map (optional) - look in output directory, then release-targets, then script directory
    extensions_map_path = output_dir / 'targets-extensions.map'
    if not extensions_map_path.exists():
        extensions_map_path = Path(__file__).parent.parent / 'release-targets' / 'targets-extensions.map'
    if not extensions_map_path.exists():
        extensions_map_path = Path(__file__).parent / 'targets-extensions.map'
    print(f"Loading extensions map from {extensions_map_path}...", file=sys.stderr)
    extensions_map = load_extensions_map(extensions_map_path)
    if extensions_map:
        print(f"  Loaded {len(extensions_map)} extension rules", file=sys.stderr)
    else:
        print("  No extensions map found or empty", file=sys.stderr)

    # Load remove extensions map (optional) - look in output directory, then release-targets, then script directory
    remove_extensions_map_path = output_dir / 'targets-extensions.map.blacklist'
    if not remove_extensions_map_path.exists():
        remove_extensions_map_path = Path(__file__).parent.parent / 'release-targets' / 'targets-extensions.map.blacklist'
    if not remove_extensions_map_path.exists():
        remove_extensions_map_path = Path(__file__).parent / 'targets-extensions.map.blacklist'
    print(f"Loading remove extensions map from {remove_extensions_map_path}...", file=sys.stderr)
    remove_extensions_map = load_remove_extensions_map(remove_extensions_map_path)
    if remove_extensions_map:
        print(f"  Loaded {len(remove_extensions_map)} remove extension rules", file=sys.stderr)
    else:
        print("  No remove extensions map found or empty", file=sys.stderr)

    # Load image info
    print(f"Loading {json_path}...", file=sys.stderr)
    image_info = load_image_info(json_path)
    print(f"Loaded {len(image_info)} entries", file=sys.stderr)

    # Generate YAML files
    print("Generating YAML files...", file=sys.stderr)

    # targets-release-apps.yaml
    apps_path = output_dir / 'targets-release-apps.yaml'
    blacklist_apps = load_blacklist(str(apps_path))
    manual_apps = load_manual_overrides(str(apps_path))
    conf_wip_boards_apps, _ = extract_boards_by_support_level(image_info, extensions_map, remove_extensions_map, blacklist_apps)
    print(f"  apps: {len(conf_wip_boards_apps)} boards after blacklist", file=sys.stderr)
    apps_yaml = generate_apps_yaml(conf_wip_boards_apps, manual_apps)
    apps_path.write_text(resolve_release_tokens(apps_yaml, args.debian_apps, args.ubuntu_apps))
    print(f"  Written {apps_path}", file=sys.stderr)

    # targets-release-standard-support.yaml
    stable_path = output_dir / 'targets-release-standard-support.yaml'
    blacklist_stable = load_blacklist(str(stable_path))
    manual_stable = load_manual_overrides(str(stable_path))
    conf_wip_boards_stable, _ = extract_boards_by_support_level(image_info, extensions_map, remove_extensions_map, blacklist_stable)
    print(f"  stable: {len(conf_wip_boards_stable)} boards after blacklist", file=sys.stderr)
    stable_yaml = generate_stable_yaml(conf_wip_boards_stable, manual_stable)
    stable_path.write_text(resolve_release_tokens(stable_yaml, args.debian_standard, args.ubuntu_standard))
    print(f"  Written {stable_path}", file=sys.stderr)

    # targets-release-nightly.yaml
    nightly_path = output_dir / 'targets-release-nightly.yaml'
    blacklist_nightly = load_blacklist(str(nightly_path))
    manual_nightly = load_manual_overrides(str(nightly_path))
    conf_wip_boards_nightly, _ = extract_boards_by_support_level(image_info, extensions_map, remove_extensions_map, blacklist_nightly)
    print(f"  nightly: {len(conf_wip_boards_nightly)} boards after blacklist", file=sys.stderr)
    nightly_yaml = generate_nightly_yaml(conf_wip_boards_nightly, manual_nightly)
    nightly_path.write_text(resolve_release_tokens(nightly_yaml, args.debian_nightly, args.ubuntu_nightly))
    print(f"  Written {nightly_path}", file=sys.stderr)

    # targets-release-community-maintained.yaml
    community_path = output_dir / 'targets-release-community-maintained.yaml'
    blacklist_community = load_blacklist(str(community_path))
    manual_community = load_manual_overrides(str(community_path))
    _, csc_tvb_boards_community = extract_boards_by_support_level(image_info, extensions_map, remove_extensions_map, blacklist_community)
    print(f"  community: {len(csc_tvb_boards_community)} boards after blacklist", file=sys.stderr)
    community_yaml = generate_community_yaml(csc_tvb_boards_community, manual_community)
    community_path.write_text(resolve_release_tokens(community_yaml, args.debian_community, args.ubuntu_community))
    print(f"  Written {community_path}", file=sys.stderr)

    # exposed.map
    # Generate from stable + community boards (exclude nightly targets).
    # Per-board(family) overrides for the recommended-image regex (used
    # by vendor BSPs whose desktop image lives on a non-default
    # branch/release/desktop combo) live next to the output file.
    exposed_map_path = output_dir / 'exposed.map'
    exposed_overrides = load_exposed_overrides(output_dir / 'exposed.map.overrides.yaml')
    exposed_map = generate_exposed_map(
        conf_wip_boards_stable,
        csc_tvb_boards_community,
        debian_standard=args.debian_standard,
        ubuntu_standard=args.ubuntu_standard,
        debian_community=args.debian_community,
        ubuntu_community=args.ubuntu_community,
        overrides=exposed_overrides,
    )
    exposed_map_path.write_text(exposed_map)
    print(f"  Written {exposed_map_path}", file=sys.stderr)

    print("Done!", file=sys.stderr)


if __name__ == '__main__':
    main()
