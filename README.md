<h2 align="center">
  <a href=#><img src="https://raw.githubusercontent.com/armbian/.github/master/profile/logosmall.png" alt="Armbian logo"></a>
  <br><br>
</h2>

# armbian.github.io

## Purpose of This Repository

This repository is the central **automation and orchestration hub** for the Armbian project. It coordinates CI workflows, generates machine-readable metadata, publishes board/vendor assets, and produces the data exchange files that power [armbian.com](https://www.armbian.com), [docs.armbian.com](https://docs.armbian.com), download mirrors, and related Armbian services.

## What's Inside

The repository holds the source assets, scripts, and workflow definitions that drive Armbian's data pipelines. Generated artefacts are published to the `data` branch (served from [github.armbian.com](https://github.armbian.com/)) rather than kept on `main`.

| Path | Contents |
|---|---|
| `scripts/` | Python, shell, and Node helpers invoked by the CI workflows (image inventory, target generation, JSON indexes, review bots, etc.). |
| `release-targets/` | Inputs that drive the image build matrix. See the [release-targets README](release-targets/README.md) for the full generator schema. |
| `board-images/` | Per-board product photos (PNG), one file per supported board. |
| `board-vendor-logos/` | Vendor logo assets used across Armbian websites. |
| `templates/` | Shared template fragments used by the generators. |
| `.github/workflows/` | GitHub Actions workflow definitions for scheduled and dispatched automation. |

## Workflow Status & Monitoring

**[GitHub Actions dashboard for this repo](https://actions.armbian.com/?repo=armbian.github.io)**

Armbian maintains a dedicated CI overview that tracks all automation in this repository, including:

- **Execution history** — Past workflow runs with timestamps and outcomes
- **Performance metrics** — Runtime duration and success/failure rates
- **Live status** — Current state of scheduled jobs and dispatched tasks
- **Debugging** — Detailed logs and error traces for failed runs

Rather than listing individual workflows here, use the dashboard above as the single source of truth.

## Release Targets

The `release-targets/` directory drives Armbian's image build matrix. `scripts/generate_targets.py` reads `image-info.json` (the per-board build inventory) together with the configuration files in that directory, and emits the YAML files consumed by the build pipeline:

- `targets-release-apps.yaml` — application images (Home Assistant, OMV, Kali)
- `targets-release-standard-support.yaml` — standard-support images for `conf` / `wip` boards
- `targets-release-nightly.yaml` — nightly builds for `conf` / `wip` boards
- `targets-release-community-maintained.yaml` — community/experimental builds for `csc` / `tvb` boards
- `exposed.map` — per-board regex patterns used by the website to pick the recommended image

Full schema, input/output format, codename substitution rules, and board classification details live in [`release-targets/README.md`](release-targets/README.md).

## Built With

- **Python 3** — target generation, inventory tooling, Jira/Bigin integrations, data enrichment scripts
- **Bash** — glue logic inside workflow `run:` steps and standalone shell helpers in `scripts/`
- **Node.js** — the actions report generator (`scripts/generate-actions-report.mjs`)
- **GitHub Actions (YAML)** — scheduling, dispatch, and orchestration
- Common tooling invoked by the workflows: `jq`, `curl`, `rsync`, `git`, `graphicsmagick`, `pngquant`

## Data Branch

Generated artefacts (JSON indexes, release target YAMLs, keyrings, torrent bundles, server lists, MOTD data, actions reports, …) are committed to the `data` branch and served publicly from [github.armbian.com](https://github.armbian.com/). The `main` branch holds only sources and automation; nothing is generated into `main`.

## Contributing

Contributions are welcome — bug reports, pull requests, documentation improvements, and infrastructure enhancements. See [CONTRIBUTING.md](CONTRIBUTING.md) for the development workflow and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for community guidelines.

Other ways to help:

- [Become a board maintainer](https://docs.armbian.com/Board_Maintainers_Procedures_and_Guidelines/)
- [Apply for an open position](https://forum.armbian.com/staffapplications/)
- [Help cover project costs](https://forum.armbian.com/subscriptions/)
- [Help community members in the forum](https://forum.armbian.com/)

## License

Released under the **GNU General Public License v2.0**. See [LICENSE](LICENSE) for the full text.
