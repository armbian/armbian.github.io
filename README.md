<h2 align="center">
  <a href=#><img src="https://raw.githubusercontent.com/armbian/.github/master/profile/logosmall.png" alt="Armbian logo"></a>
  <br><br>
</h2>

# armbian.github.io

## Purpose of This Repository

This repository is Armbian's central **automation and orchestration hub**. It schedules and runs the CI workflows that generate, enrich, and publish the metadata, image indexes, release-target matrices, and asset thumbnails that power [armbian.com](https://www.armbian.com), [docs.armbian.com](https://docs.armbian.com), the download redirector, and related Armbian services.

Generated artifacts are published to the `data` branch and served from [github.armbian.com](https://github.armbian.com/).

## Workflow Status & Monitoring

**[GitHub actions dashboard →](https://actions.armbian.com/?repo=armbian.github.io)**

The dashboard tracks every automation in this repository: execution history, runtime and success/failure rates, live state of running pipelines, and logs for debugging failed runs. Instead of enumerating individual workflows here, consult the dashboard for the authoritative, up-to-date view.

## What's in this Repository

| Area | Contents |
|---|---|
| `.github/workflows/` | GitHub Actions workflows (YAML) for data generation, infrastructure maintenance, community/label automation, monitoring, and reporting. |
| `scripts/` | Automation scripts invoked by the workflows — Python (`generate_targets.py`, `generate_kernel_descriptions.py`, `generate-base-files-info-json.py`, `generate-rpi-imager-json.py`, `days_since_last_commit.py`, …), shell (`generate-armbian-images-json.sh`, …) and Node (`generate-actions-report.mjs`). |
| `release-targets/` | Inputs and generated outputs for the Armbian build matrix. See [`release-targets/README.md`](release-targets/README.md) for the full input/output contract, codename substitution rules, and schema of each configuration file. |
| `board-images/` | Per-board source PNGs (one per supported board) that feed the thumbnail generator. |
| `board-vendor-logos/` | Per-vendor logo source files that feed the thumbnail generator. |
| `templates/` | Shared templates used by generation scripts. |
| `CNAME` | Custom domain for the GitHub Pages site. |

## How the Pipeline Fits Together

1. **Source of truth** — Board definitions in [`armbian/build`](https://github.com/armbian/build), vendor/partner records in Zoho Bigin, mirror topology in NetBox, images on the Armbian mirror network, issues in Jira, and the sources (board images, vendor logos, release-target config) in this repository.
2. **Generation** — Scheduled and dispatch-triggered workflows run the scripts in `scripts/` to produce JSON/YAML/HTML artifacts (image inventory, download index, Raspberry Pi Imager JSON, release targets, kernel descriptions, Jira excerpts, MOTD quotes, keyring packages, server lists, torrent trackers, actions reports, …).
3. **Publication** — Each workflow commits its outputs to the `data` branch under `data/`, which is served at [github.armbian.com](https://github.armbian.com/).
4. **Fan-out** — Workflows chain via `repository_dispatch` events (e.g. `Web: Directory listing`, `Infrastructure: Update redirector`, `Generate lists`) so that an upstream change propagates to the directory listing, redirector config, and downstream consumers.

## Release Targets

The Armbian CI/CD build matrix is generated from `release-targets/` by `scripts/generate_targets.py`, which consumes the live `image-info.json` board inventory and a set of per-type blacklists, extension maps, manual YAML fragments, and regex overrides.

Quick start:

```bash
# From repository root
python3 scripts/generate_targets.py image-info.json release-targets/
```

Full documentation of inputs, outputs, board classification (fast HDMI / slow HDMI / headless / RISC-V / LoongArch), the `DEBIAN` / `UBUNTU` codename substitution tokens, and the per-scope promotion flags lives in [`release-targets/README.md`](release-targets/README.md).

## Built With

- **Python 3** — most data generators (`scripts/*.py`), invoked both locally and from CI.
- **Bash** — glue shell inside workflows and standalone scripts (`scripts/*.sh`).
- **Node.js** — the AI-assisted actions-report generator (`scripts/generate-actions-report.mjs`, uses `fast-glob` and `js-yaml`).
- **GitHub Actions** — orchestration layer (`.github/workflows/*.yml`, `*.yaml`).
- **Standard tooling** invoked from CI: `jq`, `curl`, `rsync`, `git`, `graphicsmagick`, `pngquant`, `xz-utils`.

## Contributing

Contributions are welcome — bug reports, pull requests, infrastructure improvements, and documentation help. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the development workflow and other ways to get involved, and [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) for community expectations.

Other ways to contribute:

- [Become a board maintainer](https://docs.armbian.com/Board_Maintainers_Procedures_and_Guidelines/)
- [Apply for an open position](https://forum.armbian.com/staffapplications/)
- [Help cover infrastructure costs](https://forum.armbian.com/subscriptions/)
- [Help on the Armbian Forum](https://forum.armbian.com/)

## License

Licensed under the **GNU General Public License v2.0**. See [`LICENSE`](LICENSE) for the full text.

## Related

- Armbian website — <https://www.armbian.com>
- Documentation — <https://docs.armbian.com>
- Published data artifacts — <https://github.armbian.com/>
- Build framework — <https://github.com/armbian/build>
