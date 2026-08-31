<h2 align="center">
  <a href=#><img src="https://raw.githubusercontent.com/armbian/.github/master/profile/logosmall.png" alt="Armbian logo"></a>
  <br><br>
</h2>

# armbian.github.io

## Purpose of This Repository

This repository is the central **automation and orchestration hub** for the Armbian project. It coordinates scheduled CI workflows, aggregates metadata from Armbian and third-party sources, and generates the machine-readable data files that power [armbian.com](https://www.armbian.com), [docs.armbian.com](https://docs.armbian.com), and related Armbian services.

Generated artifacts are published to the repository's `data` branch and served under [github.armbian.com](https://github.armbian.com/) as data-exchange files consumed by downstream automation, reporting, and content delivery pipelines.

## Workflow Status & Monitoring

**[GitHub Actions dashboard for this repo](https://actions.armbian.com/?repo=armbian.github.io)**

The Armbian Actions dashboard aggregates all workflows in this repository and provides:

- **Execution history** — full log of past runs with timestamps and outcomes
- **Performance metrics** — runtime duration, resource usage, success/failure rates
- **Live status** — current state of running CI/CD pipelines and scheduled tasks
- **Debugging tools** — detailed logs and error traces for failed workflows

## Repository Layout

```
.
├── board-images/          # Per-board product photos (PNG) — source for cache.armbian.com thumbnails
├── board-vendor-logos/    # Vendor / manufacturer logos (PNG) — source for vendor thumbnails
├── release-targets/       # Configuration and generator inputs for the CI build matrix
├── scripts/               # Python / Node / shell scripts invoked by the workflows
├── templates/             # Templates used by the automation scripts
├── .github/workflows/     # Scheduled and event-driven automation
├── CNAME
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

Generated outputs (image indexes, partner data, keyrings, server lists, actions reports, release-target YAMLs, etc.) are not stored on `main`; they are committed to the repository's `data` branch by the workflows.

## What Lives Here

### Board & vendor artwork

- `board-images/` — one PNG per Armbian-supported board (Banana Pi, Orange Pi, Radxa, Rock, Khadas, NanoPi, ODROID, Raspberry Pi, RISC-V boards, QEMU/UEFI/WSL2 targets, …).
- `board-vendor-logos/` — one logo per board vendor (Allwinner, Amlogic, Radxa, FriendlyELEC, Khadas, Hardkernel, Libre Computer, …).

These are the master images. A workflow generates resized thumbnails at multiple widths and publishes them to Armbian's asset cache.

### Release targets and build-matrix generator

`release-targets/` contains the inputs to `scripts/generate_targets.py`, which reads the per-board build inventory (`image-info.json`) and emits the YAML files that drive Armbian's CI/CD build matrix.

Inputs (all optional):

| File | Purpose |
|---|---|
| `targets-extensions.map` | Add per-board / per-branch `ENABLE_EXTENSIONS` entries. |
| `targets-extensions.map.blacklist` | Remove auto- or manually-added extensions. |
| `targets-release-<type>.blacklist` | Boards to exclude from a target type. |
| `targets-release-<type>.manual` | YAML appended to the auto-generated section. |
| `exposed.map.overrides.yaml` | Per-board / boardfamily overrides for the "recommended image" regex patterns. |
| `reusable.yml` | "Virtual board" definitions that reuse another board's image set. |

`<type>` is one of: `apps`, `nightly`, `standard-support`, `community-maintained`.

Outputs are five files written back to `release-targets/`:

| File | What it drives |
|---|---|
| `targets-release-apps.yaml` | Application images (Home Assistant, OMV, Kali). |
| `targets-release-standard-support.yaml` | Standard-support builds for `conf` / `wip` boards. |
| `targets-release-nightly.yaml` | Nightly builds for `conf` / `wip` boards. |
| `targets-release-community-maintained.yaml` | Community / experimental builds for `csc` / `tvb` boards. |
| `exposed.map` | Regex patterns used by the website to pick the "recommended image" per board. |

Run the generator manually:

```bash
python3 scripts/generate_targets.py image-info.json release-targets/
```

See [`release-targets/README.md`](release-targets/README.md) for the full schema, per-scope codename flags, and the `DEBIAN` / `UBUNTU` symbolic-token substitution model.

### Automation scripts

`scripts/` holds the helpers invoked from workflows. Languages evidenced in this repo:

- **Python 3** — build-matrix generator (`generate_targets.py`), kernel description generator, image-index generators, Jira, Raspberry Pi Imager JSON, activity lookups (e.g. `days_since_last_commit.py`), etc.
- **Bash** — image-index shell generators (`generate-armbian-images-json.sh` and similar), inline `run:` steps in workflows.
- **Node.js** — the Actions-report generator (`generate-actions-report.mjs`, using `fast-glob` and `js-yaml`).

## CI / Automation Overview

Automation in this repo falls into a few themes; individual workflows are tracked on the [dashboard](https://actions.armbian.com/?repo=armbian.github.io) rather than enumerated here.

- **Data pipelines** — periodically build JSON/HTML indexes (image inventory, download index, Raspberry Pi Imager JSON, Jira excerpts, `base-files` package index, partners & maintainers, torrent tracker lists, Debian/Ubuntu keyrings, MOTD quotes) and commit them to the `data` branch.
- **Release-target generation** — regenerate the CI build-matrix YAMLs whenever `release-targets/**` or `scripts/generate_targets.py` change, or when a fresh `image-info.json` is published.
- **Asset generation** — resize `board-images/` and `board-vendor-logos/` into multi-width thumbnails.
- **Infrastructure orchestration** — mirror artifacts, refresh the download redirector, dispatch website sync, cache NetBox server inventories (download/cache/upload mirrors and self-hosted runners) as JSON, and validate board assets.
- **Community & repository hygiene** — invite recurring contributors to the Armbian organization, enforce the "All-repository triage" role, sync labels, auto-label PRs, clean workflow logs, and produce release / repository-status reports.

Most workflows are gated by `github.repository_owner == 'Armbian'` and coordinate via GitHub `repository_dispatch` events so that a data change here can fan out to sibling repositories (e.g. `armbian/build`, `armbian/os`, `armbian/actions`).

## Data Branch

Generated artifacts are published to the `data` branch and mirrored under:

- <https://github.armbian.com/>

Typical layout on `data`:

```
data/
├── actions-report/           # Per-repo automation status snapshots
├── keyrings/                 # Latest Debian & Ubuntu keyring .deb files (+ stable symlinks)
├── release-targets/          # Generated build-matrix YAMLs, exposed.map, kernel-description.json
├── servers/                  # Cached NetBox server JSONs, torrent tracker list
├── armbian-images.json       # Master image inventory
├── base-files.json
├── image-info.json           # Build-engine board inventory (mirrored from armbian/build)
├── jira-current.html
├── jira-next.html
├── rpi-imager.json
├── quotes.txt                # MOTD messages
└── all-torrents.zip
```

## Contributing

We welcome contributions:

- **Bug reports** — [open an issue](https://github.com/armbian/armbian.github.io/issues)
- **Feature requests** — let's discuss
- **Pull requests** — code, workflow, and data-pipeline improvements
- **Documentation** — help others get started

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the development workflow and other ways to help the project (board maintainership, staff applications, forum support, sponsorship).

Other useful links:

- [Become a board maintainer](https://docs.armbian.com/Board_Maintainers_Procedures_and_Guidelines/)
- [Staff applications](https://forum.armbian.com/staffapplications/)
- [Support Armbian](https://forum.armbian.com/subscriptions/)
- [Armbian forum](https://forum.armbian.com/)

Please also read the [Code of Conduct](CODE_OF_CONDUCT.md).

## License

This project is licensed under the **GNU General Public License v2.0**. See [`LICENSE`](LICENSE) for the full text.
