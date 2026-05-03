# Armbian Target YAML Generator

`scripts/generate_targets.py` reads `image-info.json` (the per-board build inventory) plus the configuration files in this directory and emits the YAML files that drive Armbian's CI/CD pipeline matrix.

## Quick start

```bash
# From repository root
python3 scripts/generate_targets.py image-info.json release-targets/
```

All inputs and outputs live in `release-targets/`. With no flags, the output reproduces the previous literal codename pins exactly (modulo the symbolic-token round-trip — see [Release codename substitution](#release-codename-substitution)).

## Inputs

Files the script reads from the output directory. Every input is optional unless noted; missing files are treated as empty.

| File | Purpose |
|---|---|
| `targets-extensions.map` | Add per-board / per-branch `ENABLE_EXTENSIONS` entries. |
| `targets-extensions.map.blacklist` | Remove auto- or manually-added extensions per board / branch. |
| `targets-release-<type>.blacklist` | Boards to exclude from a target type (one per line). |
| `targets-release-<type>.manual` | YAML appended to the auto-generated section for that type. |
| `exposed.map.overrides.yaml` | Per-board / boardfamily overrides for the regex patterns in `exposed.map`. |
| `reusable.yml` | "Virtual board" definitions that reuse another board's image set with custom branding (see [reusable.yml header](reusable.yml) for schema and examples). |

`<type>` is one of: `apps`, `nightly`, `standard-support`, `community-maintained`.

## Outputs

Five files written to the output directory.

| File | What it drives |
|---|---|
| `targets-release-apps.yaml` | Application-specific images (Home Assistant, openHAB, Kali). |
| `targets-release-standard-support.yaml` | Standard-support release images for `conf` / `wip` boards, split by performance class and branch. |
| `targets-release-nightly.yaml` | Nightly builds for `conf` / `wip` boards. |
| `targets-release-community-maintained.yaml` | Community / experimental builds for `csc` / `tvb` boards. |
| `exposed.map` | Per-board regex patterns the website uses to pick the "recommended image" link from the live image set. |

### Targets emitted in each file

The four `targets-release-*.yaml` files share a common shape: a header, a set of YAML anchors (`stable-current-fast-hdmi: &stable-current-fast-hdmi …`) listing the boards in each (branch, performance) bucket, and a set of build targets (`desktop-stable-ubuntu-…`, `minimal-stable-debian-…`, …) that compose those anchors via `*alias` references.

Targets are emitted only for combinations that have at least one board:

- `minimal-…` — Debian or Ubuntu CLI image, per branch (current / vendor / legacy / edge), per architecture class (default / riscv64 / loongarch).
- `desktop-…` — Ubuntu desktop image, per `DESKTOP_ENVIRONMENT` (xfce / gnome / bianbu) the matrix supports for that release × arch combo. Fast HDMI boards get GNOME; slow / riscv64 get XFCE; the SpacemiT K1 family on the legacy branch gets the Bianbu desktop.
- `apps-…` — Home Assistant + openHAB on Ubuntu (the `apps` scope tracks the last LTS for build-image stability), Kali on `sid`.

The exact codename each `RELEASE:` line resolves to depends on which `--<distro>-<scope>` flags the workflow was dispatched with — see [Per-scope codename flags](#per-scope-codename-flags).

## Board classification

### By performance / arch (driven by `KERNEL_SRC_ARCH` and `BOARD_HAS_VIDEO`)

- **Fast HDMI** — `arm64`, `x86` boards with video. Get `gnome_desktop` recommendation, automatic `v4l2loopback-dkms` extension.
- **Slow HDMI** — `arm` (32-bit) boards with video. Get `xfce_desktop` recommendation.
- **Headless** — `BOARD_HAS_VIDEO: false`. Get `minimal` (CLI) recommendation.
- **RISC-V** — `riscv64`. Separate category, single XFCE desktop pattern (with the SpacemiT K1 family overridden to Bianbu via `exposed.map.overrides.yaml`).
- **LoongArch** — `loongarch64`. Separate category, currently Debian-minimal only (no Ubuntu image).

### By support level (driven by file extension under `config/boards/`)

- **`conf` / `wip`** — first-tier support. Land in `standard-support` and `nightly`.
- **`csc` / `tvb`** — community / experimental. Land in `community-maintained`.

## Configuration file formats

### `targets-extensions.map`

```ini
# Format: BOARD:branch1:branch2:...:ENABLE_EXTENSIONS="ext1,ext2"
# An empty branch list (e.g. board:::) means "all branches".

khadas-vim1s:legacy:current:edge::ENABLE_EXTENSIONS="image-output-oowow"
rock-5b:current::ENABLE_EXTENSIONS="custom-extension"
nanopi-r4s:::ENABLE_EXTENSIONS="test-extension"
```

Manual entries are **merged** with the automatic fast-HDMI extension (`v4l2loopback-dkms`).

### `targets-extensions.map.blacklist`

```ini
# Format: BOARD:branch1:branch2:...:REMOVE_EXTENSIONS="ext1,ext2"

radxa-e54c:::REMOVE_EXTENSIONS="v4l2loopback-dkms"
uefi-x86:current::REMOVE_EXTENSIONS="v4l2loopback-dkms"
```

The blacklist takes precedence over both automatic and manual extensions.

### `targets-release-<type>.blacklist`

One board name per line. `#` comments allowed.

```text
# Boards we don't want in standard-support builds
ayn-odin2
bananapim5
```

### `targets-release-<type>.manual`

YAML fragment appended verbatim to the auto-generated targets section. Use the symbolic `RELEASE: UBUNTU` / `RELEASE: DEBIAN` tokens unless the block needs to pin to a specific codename regardless of the scope flag (see the Bianbu emit in `generate_targets.py` for that pattern).

```yaml
desktop-stable-ubuntu-cinnamon:
  enabled: yes
  configs: [ armbian-images ]
  pipeline:
    gha: *armbian-gha
  build-image: "yes"
  vars:
    RELEASE: UBUNTU                 # substituted at generation time
    BUILD_MINIMAL: "no"
    BUILD_DESKTOP: "yes"
    DESKTOP_ENVIRONMENT: "cinnamon"
    DESKTOP_ENVIRONMENT_CONFIG_NAME: "config_base"
    DESKTOP_APPGROUPS_SELECTED: ""
    DESKTOP_TIER: "mid"             # required for desktop blocks; armbian-config picks
                                    # minimal / mid / full from this when assembling
                                    # the rootfs
  items:
    - *stable-current-fast-hdmi
    - *stable-vendor-fast-hdmi
```

### `exposed.map.overrides.yaml`

Per-board / boardfamily overrides for the regex patterns in `exposed.map`. The generator picks `(release, branch, suffix)` algorithmically (riscv64 → `xfce_desktop`, fast video → `gnome_desktop`, etc.); when a vendor BSP needs a combination outside that algorithm, redirect via this file.

```yaml
overrides:
  - boardfamily: <name>     # OR boards: [b1, b2, ...]
    minimal:                # pattern 1 override (default: Debian + board's branch + "minimal")
      release: <codename>
      branch:  <branch>
      suffix:  <token>      # default: "minimal"
    desktop:                # pattern 2 override (default: Ubuntu + board's branch + algorithmic suffix)
      release: <codename>
      branch:  <branch>
      suffix:  <token>      # full literal tail, e.g. "bianbu_desktop"
```

Either inner block may be omitted to leave that pattern at its algorithmic default. Inside each block, every field is optional and falls through.

A per-board entry **overlays** a boardfamily entry block-by-block then field-by-field — a per-board entry that sets only `minimal:` keeps the family's `desktop:` block intact; a per-board `desktop: {suffix: x}` keeps the family's `desktop.{release, branch}` while replacing only `suffix`. Use this to carve a partial exception out of a family rule without repeating its other blocks.

Schema is regex-only (no bash sourcing); cycles in source-via-yaml references are guarded; malformed entries (missing match key, non-mapping inner blocks, unknown top-level keys) are dropped with a warning at load time.

## Release codename substitution

Both this generator's hardcoded YAML stanzas and every `*.manual` override file use **two symbolic release tokens** instead of literal Debian / Ubuntu codenames:

| Token | Substituted with |
|---|---|
| `DEBIAN` | the codename passed via `--debian-<scope>` |
| `UBUNTU` | the codename passed via `--ubuntu-<scope>` |

Each output file (`apps`, `standard`, `nightly`, `community`) gets its own (debian, ubuntu) flag pair, so promoting one release line is independent of the others.

The substitution is anchored to start-of-line so a sibling key like `KERNEL_RELEASE: UBUNTU` won't have its `RELEASE: UBUNTU` substring corrupted.

**Promoting a release line** is a flag flip on the workflow dispatch inputs — no script edit, no manual-file edit:

```bash
# Move nightly Ubuntu to the next interim while standard stays on its current LTS
python3 scripts/generate_targets.py image-info.json release-targets/ \
    --ubuntu-nightly questing
```

`apps-kali` keeps `RELEASE: sid` literal — Kali tracks Debian unstable forever, that's not a "current Debian stable" pin. Same trick is used in the Bianbu emit (`RELEASE: noble` literal) where the SpacemiT Mesa fork is only published for noble.

## Per-scope codename flags

| Flag | Default | Used in |
|---|---|---|
| `--debian-standard` | `trixie` | `targets-release-standard-support.yaml` |
| `--ubuntu-standard` | `resolute` | `targets-release-standard-support.yaml` |
| `--debian-nightly` | `forky` | `targets-release-nightly.yaml` |
| `--ubuntu-nightly` | `resolute` | `targets-release-nightly.yaml` |
| `--debian-community` | `trixie` | `targets-release-community-maintained.yaml` |
| `--ubuntu-community` | `resolute` | `targets-release-community-maintained.yaml` |
| `--debian-apps` | `trixie` | `targets-release-apps.yaml` |
| `--ubuntu-apps` | `noble` | `targets-release-apps.yaml` |

The same per-scope codenames also drive the regex patterns in `exposed.map`, so the build matrix and the "recommended images" filter on the website stay in lockstep — bumping `--ubuntu-standard` updates both atomically.

`SCOPE_DEFAULTS` in `scripts/generate_targets.py` is the single place to change the project-wide default; per-run overrides are passed via the workflow's `workflow_dispatch` inputs.

## Automatic extensions

All fast-HDMI boards (64-bit boards with video output) automatically get:

- `v4l2loopback-dkms`

Manual entries from `targets-extensions.map` are merged with these; entries in `targets-extensions.map.blacklist` are removed from both automatic and manual sets. The blacklist wins.

## Examples

```bash
# Default — produces the configured-default codenames for every scope
python3 scripts/generate_targets.py image-info.json release-targets/

# Roll standard-support's Ubuntu line back to the previous LTS for one invocation
python3 scripts/generate_targets.py image-info.json release-targets/ \
    --ubuntu-standard noble

# Pin nightly to a forward-looking interim while leaving everything else alone
python3 scripts/generate_targets.py image-info.json release-targets/ \
    --ubuntu-nightly questing

# Fetch the live inventory then regenerate
curl -L -o image-info.json https://github.armbian.com/image-info.json
python3 scripts/generate_targets.py image-info.json release-targets/
```

## Requirements

- Python 3.6+
- `image-info.json` from the Armbian build framework (or `https://github.armbian.com/image-info.json`)
- `pyyaml` (loaded for `exposed.map.overrides.yaml`; available by default on most CI images)

All other inputs (`targets-extensions.map`, blacklists, `*.manual`, `exposed.map.overrides.yaml`, `reusable.yml`) are optional.
