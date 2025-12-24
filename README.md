<h2 align="center">
  <a href=#><img src="https://raw.githubusercontent.com/armbian/.github/master/profile/logosmall.png" alt="Armbian logo"></a>
  <br><br>
</h2>

### Purpose of This Repository

This repository acts as a central **automation and orchestration hub** for the Armbian project. It coordinates CI workflows, maintains metadata, syncs external data, and generates machine-readable output to power [armbian.com](https://www.armbian.com), [docs.armbian.com](https://docs.armbian.com), and related services.

It also produces [data exchange files](https://github.armbian.com/) used for automation, reporting, and content delivery across the Armbian infrastructure.


## Build & Packaging Automation

| Workflow | Status | Description |
|----------|--------|-------------|
| [Build Artifacts Assembly](https://github.com/armbian/os/actions/workflows/complete-artifact-matrix-all.yml) | <a href=https://github.com/armbian/os/actions/workflows/complete-artifact-matrix-all.yml><img alt="Artifacts generation" src="https://img.shields.io/github/actions/workflow/status/armbian/os/complete-artifact-matrix-all.yml?label=&style=for-the-badge&branch=main&logoColor=white"></a> | Assembles packages and stores them in the [ORAS cache](https://github.com/orgs/armbian/packages) |
| [Linux Kernel Shallow Bundles](https://github.com/armbian/shallow/actions/workflows/git-trees-oras.yml) | <a href=https://github.com/armbian/shallow/actions/workflows/git-trees-oras.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/shallow/git-trees-oras.yml?style=for-the-badge&branch=main&logoColor=white"></a> | Packages minimal (shallow) kernel source trees for fast and efficient CI use, reducing clone depth and speeding up build workflows |
| [Build Armbian Docker Image](https://github.com/armbian/docker-armbian-build/actions/workflows/update_docker.yml) | <a href=https://github.com/armbian/docker-armbian-build/actions/workflows/update_docker.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/docker-armbian-build/update_docker.yml?label=&style=for-the-badge&branch=main&logoColor=white"></a> | Builds and publishes Docker images for the [Armbian Build Framework](https://github.com/armbian/build) to the [GitHub Container Registry](https://github.com/orgs/armbian/packages) |
| [Generate APT Repository](https://github.com/armbian/os/actions/workflows/repository-update.yml) | <a href=https://github.com/armbian/os/actions/workflows/repository-update.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/os/repository-update.yml?label=&style=for-the-badge&branch=main&logoColor=white"></a> | Publishes packages from the [ORAS cache](https://github.com/orgs/armbian/packages) and [external sources](https://github.com/armbian/os/tree/main/external) to APT repositories |


## Testing & Validation

| Workflow | Status | Description |
|----------|--------|-------------|
| [Applications Install Testing](https://github.com/armbian/configng/actions/workflows/unit-tests.yml) | <a href=https://github.com/armbian/configng/actions/workflows/unit-tests.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/configng/unit-tests.yml?label=&style=for-the-badge&branch=main&logoColor=white"></a> | Runs unit tests on `armbian-config` modules to validate install, upgrade, and configuration logic |
| [Wireless Performance Testing](https://github.com/armbian/armbian.github.io/actions/workflows/testing-wireless-performance-test.yml) | <a href=https://github.com/armbian/armbian.github.io/actions/workflows/testing-wireless-performance-test.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/testing-wireless-performance-test.yml?label=&style=for-the-badge&branch=main&logoColor=white"></a> | Executes Wi-Fi benchmarks on supported devices to identify performance regressions ([Docs →](https://docs.armbian.com/WifiPerformance/)) |


## Data & Content Generation

| Workflow | Status | Description |
|----------|--------|-------------|
| [Generate Board Thumbnails](https://github.com/armbian/armbian.github.io/actions/workflows/assets-generate-board-thumbnails.yml) | <a href=https://github.com/armbian/armbian.github.io/actions/workflows/assets-generate-board-thumbnails.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/assets-generate-board-thumbnails.yml?label=&style=for-the-badge&branch=main&logoColor=white"></a> | Generates thumbnails from `board-images/` and `board-vendor-logos/` and publishes to Armbian cache mirrors |
| [Update Base-Files Metadata](https://github.com/armbian/armbian.github.io/actions/workflows/data-update-base-files-info.yml) | <a href=https://github.com/armbian/armbian.github.io/actions/workflows/data-update-base-files-info.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/data-update-base-files-info.yml?label=&style=for-the-badge&branch=main&logoColor=white"></a> | Embeds build metadata into Armbian's `base-files` packages |
| [Cache Debian & Ubuntu Keyrings](https://github.com/armbian/armbian.github.io/actions/workflows/generate-keyring-data.yaml) | <a href=https://github.com/armbian/armbian.github.io/actions/workflows/generate-keyring-data.yaml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/generate-keyring-data.yaml?label=&style=for-the-badge&branch=main&logoColor=white"></a> | Improves reliability of build process |
| [Weekly Release Summary](https://github.com/armbian/armbian.github.io/actions/workflows/reporting-release-summary.yml) | <a href=https://github.com/armbian/armbian.github.io/actions/workflows/reporting-release-summary.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/reporting-release-summary.yml?label=&style=for-the-badge&branch=main&logoColor=white"></a> | Compiles a Markdown digest of merged pull requests across repos or org |
| [Update Download Index](https://github.com/armbian/armbian.github.io/actions/workflows/data-update-download-index.yml) | <a href=https://github.com/armbian/armbian.github.io/actions/workflows/data-update-download-index.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/data-update-download-index.yml?label=&style=for-the-badge&branch=main&logoColor=white"></a> | Regenerates image download indexes and torrent files |
| [Update Redirector Config](https://github.com/armbian/armbian.github.io/actions/workflows/infrastructure-update-redirector-config.yml) | <a href=https://github.com/armbian/armbian.github.io/actions/workflows/infrastructure-update-redirector-config.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/infrastructure-update-redirector-config.yml?label=&style=for-the-badge&branch=main&logoColor=white"></a> | Compares [mirror](https://docs.armbian.com/Mirrors/) contents and updates download redirector configs ([Redirector →](https://github.com/armbian/armbian-router)) |
| [Update Partners Data](https://github.com/armbian/armbian.github.io/actions/workflows/data-update-partners-data.yml) | <a href=https://github.com/armbian/armbian.github.io/actions/workflows/data-update-partners-data.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/data-update-partners-data.yml?label=&style=for-the-badge&branch=main&logoColor=white"></a> | Generates machine-readable lists of authors, sponsors, and partners |
| [Update Jira Excerpts](https://github.com/armbian/armbian.github.io/actions/workflows/data-update-jira-excerpt.yml) | <a href=https://github.com/armbian/armbian.github.io/actions/workflows/data-update-jira-excerpt.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/data-update-jira-excerpt.yml?label=&style=for-the-badge&branch=main&logoColor=white"></a> | Extracts metadata and summaries from public Jira issues |
| [Fetch Kernel Versions](https://github.com/armbian/armbian.github.io/actions/workflows/repository-status.yaml) | <a href=https://github.com/armbian/armbian.github.io/actions/workflows/repository-status.yaml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/repository-status.yaml?label=&style=for-the-badge&branch=main&logoColor=white"></a> | Fetches the latest CURRENT and EDGE kernel package versions and generates badges |


## Infrastructure & Community

| Workflow | Status | Description |
|----------|--------|-------------|
| [Mirror Artifacts to CDN](https://github.com/armbian/armbian.github.io/actions/workflows/infrastructure-mirror-repository-artifacts.yml) | <a href=https://github.com/armbian/armbian.github.io/actions/workflows/infrastructure-mirror-repository-artifacts.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/infrastructure-mirror-repository-artifacts.yml?label=&style=for-the-badge&branch=main&logoColor=white"></a> | Syncs release images to [Armbian's CDN](http://cache.armbian.com/) for global distribution |
| [Invite Recent Contributors](https://github.com/armbian/armbian.github.io/actions/workflows/community-invite-contributors.yml) | <a href=https://github.com/armbian/armbian.github.io/actions/workflows/community-invite-contributors.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/community-invite-contributors.yml?label=&style=for-the-badge&branch=main&logoColor=white"></a> | Automatically invites external contributors to join the [Armbian GitHub organization](https://github.com/orgs/armbian/people) |
| [Enforce Triage Role](https://github.com/armbian/armbian.github.io/actions/workflows/community-enforce-triage-role.yml) | <a href=https://github.com/armbian/armbian.github.io/actions/workflows/community-enforce-triage-role.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/community-enforce-triage-role.yml?label=&style=for-the-badge&branch=main&logoColor=white"></a> | Automatically grants the All-repository triage role to all organization members |
| [Runners Status](https://github.com/armbian/armbian.github.io/actions/workflows/monitoring-runners-status.yml) | <a href=https://github.com/armbian/armbian.github.io/actions/workflows/monitoring-runners-status.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/monitoring-runners-status.yml?label=&style=for-the-badge&branch=main&logoColor=white"></a> | Generates a status table of self-hosted runners with CPU, memory, storage, and runner status |


## Documentation

| Workflow | Status | Description |
|----------|--------|-------------|
| [Generate Documentation](https://github.com/armbian/documentation/actions/workflows/release.yaml) | <a href=https://github.com/armbian/documentation/actions/workflows/release.yaml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/documentation/release.yaml?label=&style=for-the-badge&branch=main&logoColor=white"></a> | Builds and deploys docs from Markdown sources using [MkDocs Material](https://squidfunk.github.io/mkdocs-material/) - Published to: [docs.armbian.com](https://docs.armbian.com) |
