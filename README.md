<h2 align="center">
  <a href=#><img src="https://raw.githubusercontent.com/armbian/.github/master/profile/logosmall.png" alt="Armbian logo"></a>
  <br><br>
</h2>

### Purpose of This Repository

This repository acts as a central **automation and orchestration hub** for the Armbian project. It coordinates CI workflows, maintains metadata, syncs external data, and generates machine-readable output to power [armbian.com](https://www.armbian.com), [docs.armbian.com](https://docs.armbian.com), and related services.

It also produces [data exchange files](https://github.armbian.com/) used for automation, reporting, and content delivery across the Armbian infrastructure.

### Build & Packaging Automation

- **Build Artifacts Assembly**  
  <a href=https://github.com/armbian/os/actions/workflows/complete-artifact-matrix-all.yml><img alt="Artifacts generation" src="https://img.shields.io/github/actions/workflow/status/armbian/os/complete-artifact-matrix-all.yml?logo=githubactions&label=Status&style=for-the-badge&branch=main&logoColor=white"></a>  
  Assembles packages and stores them in the [ORAS cache](https://github.com/orgs/armbian/packages).

- **Linux Kernel Shallow Bundles**  
  <a href=https://github.com/armbian/shallow/actions/workflows/git-trees-oras.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/shallow/git-trees-oras.yml?logo=linux&label=Status&style=for-the-badge&branch=main&logoColor=white"></a>
  <br>Packages minimal (shallow) kernel source trees for fast and efficient CI use, reducing clone depth and speeding up build workflows.
  
- **Build Armbian Docker Image**  
  <a href=https://github.com/armbian/docker-armbian-build/actions/workflows/update_docker.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/docker-armbian-build/update_docker.yml?logo=githubactions&label=Status&style=for-the-badge&branch=main&logoColor=white"></a>  
  Builds and publishes Docker images for the [Armbian Build Framework](https://github.com/armbian/build) to the [GitHub Container Registry](https://github.com/orgs/armbian/packages).

- **Generate APT Repository**  
  <a href=https://github.com/armbian/os/actions/workflows/repository-update.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/os/repository-update.yml?logo=githubactions&label=Status&style=for-the-badge&branch=main&logoColor=white"></a>  
  Publishes packages from the [ORAS cache](https://github.com/orgs/armbian/packages) and [external sources](https://github.com/armbian/os/tree/main/external) to APT repositories.

### Testing & Validation

- **Applications Install Testing**  
  <a href=https://github.com/armbian/configng/actions/workflows/unit-tests.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/configng/unit-tests.yml?logo=githubactions&label=Status&style=for-the-badge&branch=main&logoColor=white"></a>  
  Runs unit tests on `armbian-config` modules to validate install, upgrade, and configuration logic.

- **Wireless Performance Testing**  
  <a href=https://github.com/armbian/armbian.github.io/actions/workflows/wireless-performance-autotest.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/wireless-performance-autotest.yml?logo=githubactions&label=Status&style=for-the-badge&branch=main&logoColor=white"></a>  
  Executes Wi-Fi benchmarks on supported devices to identify performance regressions.  
  [Docs →](https://docs.armbian.com/WifiPerformance/)

### Metadata & Content Generation

- **Extract Base-Files Metadata**  
  <a href=https://github.com/armbian/armbian.github.io/actions/workflows/generate-base-files-info-json.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/generate-base-files-info-json.yml?logo=githubactions&label=Status&style=for-the-badge&branch=main&logoColor=white"></a>  
  Embeds build metadata into Armbian’s `base-files` packages.

- **Generate weekly release for entire organisation**  
  <a href=https://github.com/armbian/armbian.github.io/actions/workflows/generate-release-logs.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/generate-release-logs.yml?logo=githubactions&label=Status&style=for-the-badge&branch=main&logoColor=white"></a>  
  Compiles a Markdown digest of merged pull requests across one or more repos or an entire org.

- **Update Download JSON Index**  
  <a href=https://github.com/armbian/armbian.github.io/actions/workflows/generate-web-index.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/generate-web-index.yml?logo=githubactions&label=Status&style=for-the-badge&branch=main&logoColor=white"></a>
  Regenerates image download indexes across all supported devices.

- **Mirror Comparison & Redirector Config**  
  <a href=https://github.com/armbian/armbian.github.io/actions/workflows/generate-redirector-config.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/generate-redirector-config.yml?logo=githubactions&label=Status&style=for-the-badge&branch=main&logoColor=white"></a>  
  Compares [mirror](https://docs.armbian.com/Mirrors/) contents and updates download redirector configs.  
  [Redirector →](https://github.com/armbian/armbian-router)

- **Generate Authors and Partners JSON**  
  <a href=https://github.com/armbian/armbian.github.io/actions/workflows/generate-partners-json.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/generate-partners-json.yml?logo=githubactions&label=Status&style=for-the-badge&branch=main&logoColor=white"></a>  
  Generates machine-readable lists of authors, sponsors, and partners.

- **Pull Excerpts from Armbian Jira**  
  <a href=https://github.com/armbian/armbian.github.io/actions/workflows/generate-jira-excerpt.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/generate-jira-excerpt.yml?logo=githubactions&label=Status&style=for-the-badge&branch=main&logoColor=white"></a>  
  Extracts metadata and summaries from public Jira issues.

### Infrastructure & Community

- **Mirror GitHub Artifacts to CDN**  
  <a href=https://github.com/armbian/armbian.github.io/actions/workflows/mirror.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/mirror.yml?logo=githubactions&label=Status&style=for-the-badge&branch=main&logoColor=white"></a>  
  Syncs release images to [Armbian’s CDN](http://cache.armbian.com/) for global distribution.

- **Invite Recent Contributors**  
  <a href=https://github.com/armbian/armbian.github.io/actions/workflows/invite-contributors.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/invite-contributors.yml?logo=githubactions&label=Status&style=for-the-badge&branch=main&logoColor=white"></a>  
  Automatically invites external contributors to join the [Armbian GitHub organization](https://github.com/orgs/armbian/people).

### Documentation

- **Generate Documentation**  
  <a href=https://github.com/armbian/documentation/actions/workflows/release.yaml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/documentation/release.yaml?logo=githubactions&label=Status&style=for-the-badge&branch=main&logoColor=white"></a>  
  Builds and deploys docs from Markdown sources using [MkDocs Material](https://squidfunk.github.io/mkdocs-material/).  
  Published to: [docs.armbian.com](https://docs.armbian.com)
