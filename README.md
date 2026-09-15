<h2 align="center">
  <a href=#><img src="https://raw.githubusercontent.com/armbian/.github/master/profile/logosmall.png" alt="Armbian logo"></a>
  <br><br>
</h2>

# armbian.github.io

## Purpose of This Repository

This repository is the **automation and data hub** for the Armbian project. It hosts the CI workflows, Python and shell scripts, board/vendor artwork, and release-target configuration that together generate the metadata powering [armbian.com](https://www.armbian.com), [docs.armbian.com](https://docs.armbian.com), and Armbian's download and mirror infrastructure.

Generated data (image indices, partner lists, torrent trackers, release-target YAML, keyrings, MOTD, etc.) is published to the repository's `data` branch and served from [github.armbian.com](https://github.armbian.com/).

## Repository Layout

```
board-images/          Per-board product photos (PNG), thumbnailed by CI
board-vendor-logos/    Per-vendor logo files, thumbnailed by CI
release-targets/       Inputs & config for the build-target YAML generator
scripts/               Python, Bash and Node scripts run by the workflows
templates/             Templates used by generation scripts
.github/workflows/     Scheduled and event-driven automation
```

The `release-targets/` directory has its own [README](release-targets/README.md) covering the target-YAML generator, its inputs (`targets-extensions.map`, `exposed.map.overrides.yaml`, `reusable.yml`, `targets-release-<type>.blacklist`, `targets-release-<type>.manual`) and outputs (`targets-release-*.yaml`, `exposed.map`).

## What This Repository Produces

The workflows here maintain — on the `data` branch — a set of machine-readable files consumed by the Armbian website, the build framework, and third-party tools. Highlights:

| File / path (on `data` branch) | Description |
|---|---|
| `data/image-info.json` | Inventory of all boards known to `armbian/build`. |
| `data/armbian-images.json` | Full download index cross-referenced with the mirror source of truth. |
| `data/release-targets/targets-release-*.yaml` | Build-matrix definitions for standard-support, nightly, community and apps images. |
| `data/release-targets/exposed.map` | Regex patterns the website uses to pick each board's "recommended image". |
| `data/release-targets/kernel-description.json` | Human-readable kernel branch descriptions. |
| `data/partners.json`, `data/maintainers_with_avatars.json` | Partner and maintainer data enriched from Zoho Bigin and GitHub. |
| `data/rpi-imager.json` | Armbian catalog for the Raspberry Pi Imager tool. |
| `data/base-files.json` | Index of the Armbian `base-files` package versions. |
| `data/keyrings/` | Latest Debian and Ubuntu archive-keyring `.deb` packages. |
| `data/servers/{download,cache,upload,github-runners}.jq` | Live server inventory pulled from NetBox. |
| `data/servers/best-torrent-servers.txt` | Curated BitTorrent tracker list for image torrents. |
| `data/actions-report/` | CI status snapshots for the Armbian repositories. |
| `data/quotes.txt` | MOTD messages for installed Armbian systems. |
| `data/jira-current.html`, `data/jira-next.html` | Rendered Jira excerpts of current and next release scope. |

## Built With

- **Python 3** — data generators under `scripts/` (e.g. `generate_targets.py`, `generate_kernel_descriptions.py`, `generate-base-files-info-json.py`, `generate-rpi-imager-json.py`, `days_since_last_commit.py`).
- **Bash** — glue and mirror-side shell scripts (e.g. `generate-armbian-images-json.sh`) plus the `run:` steps embedded in the workflows.
- **Node.js** — `scripts/generate-actions-report.mjs` for the CI status reports.
- **GitHub Actions (YAML)** — orchestration of scheduled, dispatched and event-driven jobs.
- **jq**, **curl**, **rsync**, **GraphicsMagick + pngquant** — invoked from the workflows for JSON shaping, HTTP/rsync transfers and image thumbnailing.

## Branches

- **`master`** — source of truth: workflows, scripts, board & vendor artwork, release-target configuration.
- **`data`** — machine-generated outputs, committed by CI and served from [github.armbian.com](https://github.armbian.com/). Do not edit by hand.

## Workflow Status & Monitoring

**[GitHub Actions dashboard for this repository](https://actions.armbian.com/?repo=armbian.github.io)**

Rather than enumerating every workflow here, the Armbian Actions dashboard provides:

- **Execution history** — every past workflow run with timestamps and outcomes
- **Performance metrics** — runtime duration, success/failure rates
- **Live status** — current state of scheduled and dispatched jobs
- **Debugging tools** — logs and error traces for failed runs

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to propose changes, and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for community expectations. Additional ways to help:

- [Become a board maintainer](https://docs.armbian.com/Board_Maintainers_Procedures_and_Guidelines/)
- [Apply for a project position](https://forum.armbian.com/staffapplications/)
- [Help cover costs](https://forum.armbian.com/subscriptions/)
- [Answer questions on the forum](https://forum.armbian.com/)

## License

Distributed under the terms of the GNU General Public License v2. See [LICENSE](LICENSE) for the full text.
