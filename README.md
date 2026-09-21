<h2 align="center">
  <a href=#><img src="https://raw.githubusercontent.com/armbian/.github/master/profile/logosmall.png" alt="Armbian logo"></a>
  <br><br>
</h2>

# armbian.github.io

## Purpose of This Repository

This repository is Armbian's **automation and orchestration hub**. It hosts the CI workflows, scripts, and reference assets (board photos, vendor logos, release-target configuration) that generate the machine-readable data files driving [armbian.com](https://www.armbian.com), [docs.armbian.com](https://docs.armbian.com), the download index, the Raspberry Pi Imager list, mirror/redirector configuration, and other Armbian infrastructure.

Generated artefacts are published to the [`data` branch](https://github.com/armbian/armbian.github.io/tree/data) and exposed via [github.armbian.com](https://github.armbian.com/).

---

## Repository Layout

```text
.
├── board-images/          PNG photos of supported single-board computers
├── board-vendor-logos/    Logos for board vendors / SoC families
├── release-targets/       Inputs & generated YAML for the CI build matrix
│                          (see release-targets/README.md)
├── scripts/               Python / shell / Node scripts invoked by workflows
├── templates/             Templates used by generators
├── .github/               Dependabot, labels, issue/PR automation, workflows
├── CNAME
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
├── LICENSE                GNU GPL v2
└── README.md
```

### Key subsystems

| Area | Where | What it does |
|---|---|---|
| Build-target generation | [`release-targets/`](release-targets/) + `scripts/generate_targets.py` | Reads `image-info.json` (the per-board build inventory) plus the config files in `release-targets/` and emits the YAML files that drive Armbian's CI/CD pipeline matrix (`targets-release-apps.yaml`, `targets-release-standard-support.yaml`, `targets-release-nightly.yaml`, `targets-release-community-maintained.yaml`) and the website's `exposed.map`. See [`release-targets/README.md`](release-targets/README.md). |
| Board & vendor artwork | `board-images/`, `board-vendor-logos/` | Source PNG/SVG assets. CI generates multi-width thumbnails from these and publishes them for the website/download pages. |
| Data generation scripts | `scripts/` | Python, shell and Node scripts invoked by the workflows to build JSON/HTML/YAML artefacts (download index, RPi imager JSON, base-files package info, Jira excerpts, partners & maintainers, keyring downloads, MOTD, server inventory from NetBox, actions reports, kernel descriptions, …). |

---

## How It Works

- Scheduled and dispatched workflows in `.github/workflows/` run scripts from `scripts/` against source data from sibling Armbian repositories ([`armbian/build`](https://github.com/armbian/build), [`armbian/os`](https://github.com/armbian/os), …) and external services (Zoho Bigin, Atlassian Jira, NetBox, Ubuntu/Debian package archives, mirror rsync endpoints).
- Generated artefacts are committed to the `data` branch under `data/` and served publicly via [github.armbian.com](https://github.armbian.com/).
- Workflows chain via `repository_dispatch` events (e.g. new build inventory → regenerated build lists → refreshed website directory listing → redirector config update).

The workflow files themselves are YAML; their `run:` steps use Bash, and they invoke Python 3 scripts (with dependencies such as `requests`, `lxml`) and Node.js tooling (`fast-glob`, `js-yaml`) as needed. Image processing steps use GraphicsMagick and `pngquant`.

## Workflow Status & Monitoring

**[GitHub actions dashboard for this repo](https://actions.armbian.com/?repo=armbian.github.io)**

The dashboard aggregates every workflow in this repository with:

- **Execution history** — past runs with timestamps and outcomes
- **Performance metrics** — runtime, resource usage, success/failure rates
- **Live status** — current state of running pipelines and scheduled tasks
- **Debugging tools** — logs and error traces for failed runs

## Contributing

Contributions are welcome — bug reports, feature discussion, PRs, and documentation help. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the development workflow and other ways to get involved (board maintenance, staff applications, forum help). Please also read the [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

Related links:

- [Armbian documentation](https://docs.armbian.com)
- [Board maintainer procedures](https://docs.armbian.com/Board_Maintainers_Procedures_and_Guidelines/)
- [Armbian forum](https://forum.armbian.com/)
- [Issues](https://github.com/armbian/armbian.github.io/issues)

## License

Released under the GNU General Public License v2 — see [`LICENSE`](LICENSE).
