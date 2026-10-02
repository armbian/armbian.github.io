<h2 align="center">
  <a href=#><img src="https://raw.githubusercontent.com/armbian/.github/master/profile/logosmall.png" alt="Armbian logo"></a>
  <br><br>
</h2>

# armbian.github.io

## Purpose of This Repository

This repository is the central **automation and orchestration hub** for the Armbian project. It hosts the CI/CD workflows, generator scripts and image/logo assets used to produce the machine-readable metadata that powers [armbian.com](https://www.armbian.com), [docs.armbian.com](https://docs.armbian.com), the download index, the release-target build matrices and related infrastructure.

Generated artifacts (JSON indexes, YAML build-target lists, keyrings, torrent lists, etc.) are published to the repository's `data` branch and exposed via [github.armbian.com](https://github.armbian.com/).

---

## Repository Layout

```text
armbian.github.io/
├── board-images/         # Per-board product photos (PNG) used across Armbian sites
├── board-vendor-logos/   # Vendor / SoC / manufacturer logos (PNG, JPG, SVG)
├── release-targets/      # Config for the build-target YAML generator (see below)
├── scripts/              # Python, Bash and Node scripts driven by the workflows
├── templates/            # Shared templates
├── .github/              # GitHub Actions workflows, labels, Dependabot config
├── CNAME
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
├── LICENSE               # GPL-2.0
└── README.md
```

### Notable subsystems

| Area | Description |
|---|---|
| `release-targets/` | Inputs (extension maps, blacklists, per-scope manual overrides, `exposed.map.overrides.yaml`, `reusable.yml`) consumed by `scripts/generate_targets.py` to emit the CI/CD pipeline matrices for `apps`, `nightly`, `standard-support` and `community-maintained` builds. See [`release-targets/README.md`](release-targets/README.md) for schemas and examples. |
| `scripts/` | Generator utilities invoked by workflows — e.g. `generate_targets.py` (release-target YAML), `generate_kernel_descriptions.py`, `generate-base-files-info-json.py`, `generate-armbian-images-json.sh`, `generate-rpi-imager-json.py`, `generate-actions-report.mjs`, `days_since_last_commit.py`. |
| `board-images/` | Product images referenced by board records — over 400 SBC pictures. |
| `board-vendor-logos/` | Vendor / partner logos rendered on Armbian sites. |
| `templates/` | Shared template assets. |

---

## How It Works

Most workflows run on a schedule (or in response to `repository_dispatch` events) and follow the same pattern:

1. Check out this repo and, where needed, sibling Armbian repos (`armbian/build`, `armbian/os`, …).
2. Run a Python / Bash / Node script from `scripts/` to fetch or compute data.
3. Commit the generated artifact to the **`data` branch** (published as [github.armbian.com](https://github.armbian.com/)).
4. Fire a follow-up `repository_dispatch` event to notify downstream consumers (redirector config, web directory listing, `actions.armbian.com`, etc.).

Sources of truth pulled from during generation include the Armbian mirror network (`rsync://fi.mirror.armbian.de`), the `armbian/build` inventory (`image-info.json`), NetBox (server/runner inventory), Zoho Bigin (partners & maintainers), Atlassian Jira (release excerpts), the Ubuntu / Debian archive indexes (keyrings) and the GitHub API.

---

## Build Targets (release-targets/)

The `release-targets/` directory drives the Armbian image build matrix. `scripts/generate_targets.py` reads `image-info.json` together with the config files in that directory and emits:

- `targets-release-apps.yaml`
- `targets-release-standard-support.yaml`
- `targets-release-nightly.yaml`
- `targets-release-community-maintained.yaml`
- `exposed.map` (per-board regex patterns used by the website to pick the recommended image)

Quick start:

```bash
python3 scripts/generate_targets.py image-info.json release-targets/
```

Full schema, board classification rules and codename-substitution flags are documented in [`release-targets/README.md`](release-targets/README.md).

---

## Published Data

Generated files are published on the `data` branch and served via [github.armbian.com](https://github.armbian.com/). Typical outputs include:

- `data/armbian-images.json` — Download index for the Armbian image catalog
- `data/all-torrents.zip` — Bundled `.torrent` files
- `data/image-info.json` — Per-board build inventory (mirrored from `armbian/build`)
- `data/base-files.json` — Debian/Ubuntu `base-files` package index
- `data/rpi-imager.json` — Raspberry Pi Imager catalog
- `data/release-targets/` — Generated build-target YAMLs, `exposed.map`, `kernel-description.json`
- `data/servers/{download,cache,upload,github-runners}.jq` — Mirror & runner inventory from NetBox
- `data/servers/best-torrent-servers.txt` — Aggregated tracker announce list
- `data/keyrings/` — Latest Debian & Ubuntu keyring `.deb` files with per-variant symlinks
- `data/jira-current.html`, `data/jira-next.html` — Release excerpts from Jira
- `data/partners.json`, `data/maintainers_with_avatars.json` — Partner and maintainer data from Zoho Bigin (enriched with GitHub metadata)
- `data/actions-report/` — CI status aggregation for the Armbian org
- `data/quotes.txt` — MOTD payload for Armbian OS

---

## Built With

- **Python 3** — Most generators (`scripts/*.py`); commonly relies on `requests` and `lxml`.
- **Bash** — Shell logic in workflow `run:` steps and helper scripts (e.g. `generate-armbian-images-json.sh`).
- **Node.js 20** — CI reporting (`scripts/generate-actions-report.mjs`, using `fast-glob` and `js-yaml`).
- **YAML** — GitHub Actions workflows and release-target configuration.
- **JSON / jq** — Data interchange format and command-line transformation.
- **GraphicsMagick + pngquant** — Board & vendor thumbnail generation.
- **rsync, curl, zip** — Mirror synchronization and artifact packaging.

---

## Automation & Workflow Status

All CI/CD activity for this repository is tracked centrally on the Armbian automation dashboard:

**[Actions dashboard for `armbian.github.io`](https://actions.armbian.com/?repo=armbian.github.io)**

The dashboard exposes:

- **Execution history** — Past workflow runs with timestamps and outcomes
- **Performance metrics** — Runtime duration, resource usage, success/failure rates
- **Live status** — Current state of running CI/CD pipelines and scheduled tasks
- **Debugging tools** — Detailed logs and error traces for failed workflows

---

## Contributing

Contributions are welcome — bug reports, PRs, documentation improvements and infrastructure changes alike. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the workflow and [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) for community expectations.

Other ways to help:

- [Become a board maintainer](https://docs.armbian.com/Board_Maintainers_Procedures_and_Guidelines/)
- [Apply for a staff position](https://forum.armbian.com/staffapplications/)
- [Support the project financially](https://forum.armbian.com/subscriptions/)
- [Help community members on the Forum](https://forum.armbian.com/)

---

## License

Released under the [GNU General Public License v2.0](LICENSE).
