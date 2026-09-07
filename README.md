<h2 align="center">
  <a href=#><img src="https://raw.githubusercontent.com/armbian/.github/master/profile/logosmall.png" alt="Armbian logo"></a>
  <br><br>
</h2>

# armbian.github.io

## Purpose of This Repository

This repository is the central **automation and orchestration hub** for the Armbian project. It coordinates CI workflows, maintains metadata, syncs external data sources, and produces the machine-readable outputs that power [armbian.com](https://www.armbian.com), [docs.armbian.com](https://docs.armbian.com), and related infrastructure.

The generated data files are published on the `data` branch and served under [github.armbian.com](https://github.armbian.com/) for use by automation, reporting, and content delivery across Armbian services.

## Workflow Status & Monitoring

All scheduled and event-driven automation for this repository is visible in the Armbian actions dashboard:

**➡ [actions.armbian.com](https://actions.armbian.com/?repo=armbian.github.io)**

The dashboard exposes execution history, runtime metrics, live status of running pipelines, and detailed logs for debugging failed runs.

## Repository Layout

```
armbian.github.io/
├── board-images/          PNG artwork per supported board
├── board-vendor-logos/    PNG / SVG vendor & manufacturer logos
├── release-targets/       CI/CD build target inputs (see release-targets/README.md)
├── scripts/               Python and Bash generators invoked by workflows
├── templates/             Shared templates used by generators
├── .github/workflows/     GitHub Actions automation
├── CNAME                  Custom domain for GitHub Pages
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
├── LICENSE                GNU GPL v2
└── README.md
```

Generated artifacts (JSON indexes, release-target YAMLs, keyrings, server lists, MOTD data, Jira excerpts, etc.) are not committed to the default branch — they are produced by workflows and pushed to the `data` branch, then served publicly.

## Build Target Generation

The `release-targets/` directory holds the configuration that feeds Armbian's build matrix. `scripts/generate_targets.py` reads `image-info.json` (the per-board build inventory) together with the map/blacklist/manual files in `release-targets/` and emits the YAML files that drive the release, nightly, community, and application-image pipelines.

See [`release-targets/README.md`](release-targets/README.md) for the full input/output reference, board classification rules, and codename substitution behaviour.

Quick run from a checkout:

```bash
python3 scripts/generate_targets.py image-info.json release-targets/
```

## Assets: Boards and Vendors

- `board-images/` — one PNG per board (filename matches the board id used by `armbian/build`).
- `board-vendor-logos/` — one image per vendor / manufacturer.

Thumbnails at multiple widths are regenerated automatically when files under either directory change on `main`.

## Built With

- **Python 3** — data generators under `scripts/` (target/YAML generation, Jira excerpts, image index, RPi Imager JSON, activity lookups).
- **Bash** — shell generators under `scripts/` and inline `run:` steps in the workflows.
- **Node.js** — actions report generator (`scripts/generate-actions-report.mjs`), driven by `fast-glob` and `js-yaml`.
- **GitHub Actions** — YAML workflows under `.github/workflows/` orchestrate every scheduled and event-driven task.
- **jq**, **curl**, **rsync**, **GraphicsMagick**, **pngquant** — used by workflows for JSON shaping, downloads, mirroring, and image processing.

## Contributing

Contributions are welcome — bug reports, pull requests, documentation improvements, and infrastructure work. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the development workflow and [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) for community guidelines.

Additional ways to help:

- [Become a board maintainer](https://docs.armbian.com/Board_Maintainers_Procedures_and_Guidelines/)
- [Apply for a project position](https://forum.armbian.com/staffapplications/)
- [Support the project financially](https://forum.armbian.com/subscriptions/)
- [Help other users in the forum](https://forum.armbian.com/)

## License

Released under the **GNU General Public License v2.0**. See [`LICENSE`](LICENSE) for the full text.
