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
# Ubuntu stable minimal cloud
minimal-cli-stable-ubuntu-cloud:
  enabled: yes
  configs: [ armbian-cloud ]
  pipeline:
    gha: *armbian-gha
  build-image: "yes"
  vars:
    RELEASE: noble
    BUILD_MINIMAL: "yes"
    BUILD_DESKTOP: "no"
  items:
  - { BOARD: uefi-arm64, BRANCH: cloud, ENABLE_EXTENSIONS: "image-output-qcow2" }
```

## Automatic Extensions

All fast HDMI boards (64-bit boards with video output) automatically get:
- `v4l2loopback-dkms`
- `mesa-vpu`

**Note**: Manual extensions from `targets-extensions.map` are MERGED with automatic extensions.

## Usage

```bash
python3 scripts/generate_targets.py <image-info.json> <output_directory>
```

Both arguments are required. The output directory should contain `targets-extensions.map` and any `.blacklist`/`.manual` files.

## Example

```bash
# Download latest image-info.json
curl -L -o image-info.json https://github.armbian.com/image-info.json

# Generate target YAML files to https://github.armbian.com/release-targets/ directory
python3 scripts/generate_targets.py image-info.json release-targets/
```

## Requirements

- Python 3.6+
- image-info.json (from Armbian build framework or github.armbian.com)
- targets-extensions.map (optional, but recommended in output directory)
- .blacklist and .manual files (optional, per target type)
