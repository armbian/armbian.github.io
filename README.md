<h2 align="center">
  <a href=#><img src="https://raw.githubusercontent.com/armbian/.github/master/profile/logosmall.png" alt="Armbian logo"></a>
  <br><br>
</h2>

# armbian.github.io

## Purpose of This Repository

This repository is Armbian's **automation and data-publishing hub**. It stores curated board assets (images, pinouts, schematics, instructions, vendor logos), the release-target configuration that drives Armbian's image build matrix, and the scripts and GitHub Actions workflows that generate the data exchange files consumed by [armbian.com](https://www.armbian.com), [docs.armbian.com](https://docs.armbian.com), the Armbian download redirector, and related infrastructure.

Generated artefacts (JSON indexes, YAML target lists, HTML excerpts, torrent bundles, keyrings, DUT inventory, etc.) are published on the `data` branch and served from [github.armbian.com](https://github.armbian.com/).

## Repository Layout

| Path | Contents |
|---|---|
| `board-images/` | PNG product shots per supported board (used to generate thumbnails at multiple widths). |
| `board-vendor-logos/` | Vendor logo artwork (PNG/JPG/SVG). |
| `board-pinouts/` | Pinout references per board. |
| `board-schematics/` | Board schematic documents. |
| `board-instructions/` | Per-board Markdown instructions. |
| `release-targets/` | Inputs for the build-target YAML generator (`targets-extensions.map`, `*.blacklist`, `*.manual`, `exposed.map.overrides.yaml`, `reusable.yml`). See [`release-targets/README.md`](release-targets/README.md). |
| `scripts/` | Python, shell and Node generators invoked by the workflows (target YAML generation, image/base-files/RPi-Imager indexes, Jira excerpts, actions report, etc.). |
| `templates/` | Templates used by the data generators. |
| `.github/workflows/` | Scheduled and dispatch-driven automation (data refresh, asset generation, infrastructure, community/labelling, monitoring). |
| `CNAME` | Custom domain mapping for GitHub Pages. |

## Branches

- **`main`** — source of truth for board assets, release-target configuration, scripts and workflows.
- **`data`** — publication branch. Workflows regenerate JSON/YAML/HTML artefacts under `data/` (e.g. `data/base-files.json`, `data/armbian-images.json`, `data/all-torrents.zip`, `data/rpi-imager.json`, `data/jira-current.html`, `data/jira-next.html`, `data/release-targets/`, `data/actions-report/`, `data/keyrings/`, `data/duts/`) and push them here with retry/rebase logic. These files are what downstream services consume.

## Release-Target Generator

The core build-matrix tooling lives in [`scripts/generate_targets.py`](scripts/generate_targets.py) and is configured from [`release-targets/`](release-targets/). It reads the per-board inventory (`image-info.json`, itself regenerated from the `armbian/build` repository) and emits:

- `targets-release-apps.yaml` — application images (Home Assistant, OMV, Kali).
- `targets-release-standard-support.yaml` — standard-support release matrix.
- `targets-release-nightly.yaml` — nightly builds.
- `targets-release-community-maintained.yaml` — community / experimental builds.
- `exposed.map` — regex patterns used by the website to pick the "recommended image" for each board.

Release codenames are symbolic in the configuration (`DEBIAN`, `UBUNTU`) and are resolved per scope at generation time via the workflow's dispatch inputs. See [`release-targets/README.md`](release-targets/README.md) for the full input/output schema, board classification rules, and codename substitution model.

Run locally from the repository root:

```bash
python3 scripts/generate_targets.py image-info.json release-targets/
```

## Board & Vendor Thumbnails

Pushes to `board-images/` or `board-vendor-logos/` on `main` trigger thumbnail generation (GraphicsMagick + pngquant) at a fixed set of widths (`100 150 272 300 360 480 768 960 1024 1920`) and upload to the Armbian cache mirror network. Vendor filenames are normalised (lowercased, `_`→`-`, logo/size suffixes stripped) before matching against `BOARD_VENDOR=` entries in `armbian/build`'s `config/boards/`.

## Built With

- **Python 3** — most data generators (`scripts/generate_targets.py`, `scripts/generate_kernel_descriptions.py`, `scripts/generate-base-files-info-json.py`, `scripts/generate-rpi-imager-json.py`, `scripts/days_since_last_commit.py`, `scripts/ping-unresolved-reviews.py`, …).
- **Bash** — shell generators and the shell driving CI steps (`scripts/generate-armbian-images-json.sh`, workflow `run:` blocks).
- **Node.js** — the GitHub Actions scanner (`scripts/generate-actions-report.mjs`, using `fast-glob` and `js-yaml`).
- **GitHub Actions** (YAML workflows under `.github/workflows/`) — scheduling, dispatch, and orchestration.
- External tooling invoked from CI: `jq`, `curl`, `rsync`, `graphicsmagick`, `pngquant`, `xz-utils`, `python3-requests`, `python3-lxml`.

Data sources include the Armbian build inventory (`armbian/build`), the Armbian download mirror (`rsync://fi.mirror.armbian.de`), the Armbian NetBox instance (cache servers, DUT inventory), Zoho Bigin (partners and maintainers), the Armbian Jira (release tracking), Debian/Ubuntu archive pages (keyrings), and the GitHub API.

## Workflow Status & Monitoring

All automation in this repository is tracked on the Armbian CI dashboard:

**[→ actions.armbian.com — armbian.github.io](https://actions.armbian.com/?repo=armbian.github.io)**

- Execution history with timestamps and outcomes
- Runtime / resource metrics and success-failure rates
- Live status of running pipelines and scheduled tasks
- Logs and error traces for failed runs

## Contributing

Contributions are welcome — bug reports, pull requests, documentation improvements, and infrastructure/automation changes. See [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

Other ways to help:

- [Become a board maintainer](https://docs.armbian.com/Board_Maintainers_Procedures_and_Guidelines/)
- [Apply for a staff position](https://forum.armbian.com/staffapplications/)
- [Support the project](https://forum.armbian.com/subscriptions/)
- [Help in the forum](https://forum.armbian.com/) and [announcements section](https://forum.armbian.com/forum/37-announcements/)

## License

Released under the **GNU General Public License v2.0** — see [`LICENSE`](LICENSE).
