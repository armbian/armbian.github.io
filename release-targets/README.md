# Armbian Target YAML Generator

This script generates Armbian CI/CD pipeline configuration YAML files from `image-info.json`.

## Quick Start

All configuration files should be in this directory (`release-targets/`):

```bash
# From repository root
python3 scripts/generate_targets.py image-info.json release-targets/
```

## Configuration Files

The script reads the following files from the output directory (same location as generated files):

- **`targets-extensions.map`** - Manual extensions for specific boards/branches (optional)
- **`targets-extensions.map.blacklist`** - Extensions to remove from specific boards/branches (optional)
- **`targets-release-<type>.blacklist`** - Boards to exclude from each target type (optional)
- **`targets-release-<type>.manual`** - Additional YAML to append to each target (optional)

## Generated Files

The script generates 4 YAML files with the naming pattern `targets-release-<type>.yaml`:

### 1. targets-release-apps.yaml
Application-specific images for conf/wip boards
- `apps-ha`: Home Assistant images (Ubuntu Noble + Gnome)
- `apps-openhab`: openHAB images (Ubuntu Noble + Gnome)
- `apps-kali`: Kali Linux images (Kali rolling + XFCE)

### 2. targets-release-standard-support.yaml
Standard support release images for conf/wip boards, split by performance:

**Lists:**
- `stable-current-fast-hdmi`: Fast 64-bit boards with video
- `stable-current-slow-hdmi`: Slow 32-bit boards with video
- `stable-current-headless`: Boards without video output
- `stable-vendor-fast-hdmi`: Fast 64-bit vendor branch boards
- `stable-vendor-slow-hdmi`: Slow 32-bit vendor branch boards
- `stable-vendor-headless`: Headless vendor branch boards

**Targets:**
- `minimal-stable-debian`: Debian Trixie minimal
- `minimal-stable-ubuntu`: Ubuntu Noble minimal
- `desktop-stable-ubuntu`: Ubuntu Noble XFCE desktop (fast-hdmi only)

### 3. targets-release-nightly.yaml
Nightly builds for conf/wip boards, split by performance:

**Lists:**
- `nightly-fast-hdmi`: Fast 64-bit boards with video
- `nightly-slow-hdmi`: Slow 32-bit boards with video
- `nightly-headless`: Boards without video output

**Targets:**
- `nightly-forky-all`: Debian Forky minimal CLI for all boards
- `nightly-noble-gnome`: Ubuntu Noble GNOME desktop (fast HDMI)
- `nightly-noble-xfce`: Ubuntu Noble XFCE desktop (slow HDMI)
- `nightly-noble-minimal`: Ubuntu Noble minimal CLI (headless/exotic)

### 4. targets-release-community-maintained.yaml
Community-maintained builds for csc/tvb boards:

**Lists:**
- `community-current`: Current branch community boards
- `community-vendor`: Vendor branch community boards

**Targets:**
- `community-forky-all`: Debian Forky minimal CLI for all boards
- `community-noble-gnome`: Ubuntu Noble GNOME desktop (fast HDMI)
- `community-noble-xfce`: Ubuntu Noble XFCE desktop (slow HDMI)
- `community-noble-minimal`: Ubuntu Noble minimal CLI (headless/exotic)

## Board Classification

### By Performance (KERNEL_SRC_ARCH)
- **Slow HDMI**: `arm` (32-bit boards)
- **Fast HDMI**: `arm64`, `x86` (modern 64-bit boards)
- **RISC-V**: `riscv64` (separate category)
- **LoongArch**: `loongarch64` (separate category)
- **Headless**: Boards with `BOARD_HAS_VIDEO: false`

### By Support Level
- **conf/wip**: Higher quality support (stable and nightly builds)
- **csc/tvb**: Community/experimental support (community builds)

## Configuration File Formats

### targets-extensions.map

Add manual extensions for specific boards (merged with automatic fast‑HDMI extensions):

```ini
# Format: BOARD_NAME:branch1:branch2:...:ENABLE_EXTENSIONS="extension1,extension2"

# Add to specific branches
khadas-vim1s:legacy:current:edge::ENABLE_EXTENSIONS="image-output-oowow"

# Add to single branch
rock-5b:current::ENABLE_EXTENSIONS="custom-extension"

# Add to all branches
nanopi-r4s:::ENABLE_EXTENSIONS="test-extension"

# Multiple extensions
board-name:current::ENABLE_EXTENSIONS="ext1,ext2,ext3"
```

### targets-extensions.map.blacklist

Remove extensions from specific boards (overrides automatic and manual extensions):

```ini
# Format: BOARD_NAME:branch1:branch2:...:REMOVE_EXTENSIONS="extension1,extension2"

# Remove from all branches
radxa-e54c:::REMOVE_EXTENSIONS="v4l2loopback-dkms,mesa-vpu"

# Remove from specific branch only
uefi-x86:current::REMOVE_EXTENSIONS="mesa-vpu"

# Remove from multiple branches
board-name:vendor:edge::REMOVE_EXTENSIONS="ext1,ext2"
```

**Note**: The REMOVE_EXTENSIONS blacklist takes precedence over both automatic extensions (like `mesa-vpu` for fast HDMI boards) AND manual extensions from `targets-extensions.map`. Extensions listed here will be removed even if they were added by either mechanism.

### targets-release-<type>.blacklist

Exclude specific boards from a target type (one board name per line):

```
# Lines starting with # are comments
ayn-odin2
mekotronics-r58hd
mekotronics-r58-4x4
bananapim5
```

### targets-release-<type>.manual

Additional YAML that gets appended to the auto-generated targets section:

```yaml
# Ubuntu minimal cloud
minimal-cli-stable-ubuntu-cloud:
  enabled: yes
  configs: [ armbian-cloud ]
  pipeline:
    gha: *armbian-gha
  build-image: "yes"
  vars:
    # Symbolic codename token — substituted with the actual codename
    # by scripts/generate_targets.py (defaults to whatever
    # --ubuntu-<scope> flag the workflow was dispatched with).
    # Use literal codenames only when a block must pin to a specific
    # codename regardless of the per-scope flag.
    RELEASE: UBUNTU
    BUILD_MINIMAL: "yes"
    BUILD_DESKTOP: "no"
  items:
  - { BOARD: uefi-arm64, BRANCH: cloud, ENABLE_EXTENSIONS: "image-output-qcow2" }
```

## Automatic Extensions

All fast HDMI boards (64-bit boards with video output) automatically get:
- `v4l2loopback-dkms`
- `mesa-vpu`

**Note**:
- Manual extensions from `targets-extensions.map` are MERGED with automatic extensions.
- Extensions in `targets-extensions.map.blacklist` are REMOVED from both automatic and manual extensions.
- The blacklist takes precedence over all other extension sources.

## Release codename substitution

Both this generator's hardcoded YAML stanzas and every `*.manual`
override file use **two symbolic release tokens** instead of literal
Debian/Ubuntu codenames:

| Token    | Substituted with                    |
|----------|-------------------------------------|
| `DEBIAN` | the codename passed via `--debian-<scope>` |
| `UBUNTU` | the codename passed via `--ubuntu-<scope>` |

Each output file (`apps`, `standard`, `nightly`, `community`) gets its
own (debian, ubuntu) flag pair, so promoting one release line is
independent of the others.

**Promoting a release** is now a flag flip on the workflow dispatch
inputs — no script edit, no manual-file edit:

```bash
# Standard support stays on noble; nightly moves Ubuntu to oracular
python3 scripts/generate_targets.py image-info.json release-targets/ \
    --ubuntu-nightly oracular
```

`apps-kali` keeps `RELEASE: sid` literal — Kali tracks Debian unstable
forever, that's not a "current Debian stable" pin.

## Usage

```bash
python3 scripts/generate_targets.py <image-info.json> [output_directory] \
    [--debian-standard CODENAME] [--ubuntu-standard CODENAME] \
    [--debian-nightly  CODENAME] [--ubuntu-nightly  CODENAME] \
    [--debian-community CODENAME] [--ubuntu-community CODENAME] \
    [--debian-apps     CODENAME] [--ubuntu-apps     CODENAME]
```

`image-info.json` is required. `output_directory` defaults to the
current directory and should contain `targets-extensions.map` plus any
`.blacklist` / `.manual` files.

### Per-scope codename flags

| Flag                  | Default    | Substitutes `RELEASE: …` in   |
|-----------------------|------------|-------------------------------|
| `--debian-standard`   | `trixie`   | `targets-release-standard-support.yaml` |
| `--ubuntu-standard`   | `resolute` | `targets-release-standard-support.yaml` |
| `--debian-nightly`    | `forky`    | `targets-release-nightly.yaml`          |
| `--ubuntu-nightly`    | `resolute` | `targets-release-nightly.yaml`          |
| `--debian-community`  | `trixie`   | `targets-release-community-maintained.yaml` |
| `--ubuntu-community`  | `resolute` | `targets-release-community-maintained.yaml` |
| `--debian-apps`       | `trixie`   | `targets-release-apps.yaml`             |
| `--ubuntu-apps`       | `noble`    | `targets-release-apps.yaml`             |

The same per-scope codenames also drive the regex patterns in
`exposed.map`, so the build matrix and the "recommended images" filter
on the website stay in lockstep — bumping `--ubuntu-standard` updates
both atomically.

Defaults reproduce the previous literal pins exactly; running with no
flags is byte-identical to the pre-substitution behaviour (modulo the
symbolic-token round-trip).

## Example

```bash
# Download latest image-info.json
curl -L -o image-info.json https://github.armbian.com/image-info.json

# Generate target YAML files using all default codenames
python3 scripts/generate_targets.py image-info.json release-targets/

# Roll standard-support's Ubuntu line back to the previous LTS
# (default is resolute; this pins to noble for one invocation)
python3 scripts/generate_targets.py image-info.json release-targets/ \
    --ubuntu-standard noble
```

## Requirements

- Python 3.6+
- image-info.json (from Armbian build framework or github.armbian.com)
- targets-extensions.map (optional, for adding manual extensions)
- targets-extensions.map.blacklist (optional, for removing unwanted extensions)
- targets-release-<type>.blacklist (optional, per target type)
- targets-release-<type>.manual (optional, per target type)
