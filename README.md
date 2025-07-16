<p align="center">
  <h2 align=center><a href="#build-framework">
  <img src="https://raw.githubusercontent.com/armbian/.github/master/profile/logo.png" alt="Armbian logo" width="50%">
  </a>
<br><br>
</h2>

### What does armbian.github.io do?

Monitors the CI workflows of the Armbian project and generates various [data exchange files](https://github.armbian.com/) to support automation, integration, and reporting across the development pipeline.

- **Build Artifacts Assembly**
<br><a href=https://github.com/armbian/os/actions/workflows/complete-artifact-matrix-all.yml><img alt="Artifacts generation" src="https://img.shields.io/github/actions/workflow/status/armbian/os/complete-artifact-matrix-all.yml?logo=githubactions&label=Status&style=for-the-badge&branch=main&logoColor=white"></a>
<br>Assembles packages and stores them into [ORAS cache](https://github.com/orgs/armbian/packages).
- **Generate APT Repository**
<br><a href=https://github.com/armbian/os/actions/workflows/repository-update.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/os/repository-update.yml?logo=githubactions&label=Status&style=for-the-badge&branch=main&logoColor=white"></a>
<br>Fetch packages from the [ORAS cache](https://github.com/orgs/armbian/packages) and [third-party sources](https://github.com/armbian/os/tree/main/external), then publish them to Debian-compatible APT repositories.
- **Applications Install Testing**
<br><a href=https://github.com/armbian/configng/actions/workflows/unit-tests.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/configng/unit-tests.yml?logo=githubactions&label=Status&style=for-the-badge&branch=main&logoColor=white"></a>
<br>Executes automated unit tests on `armbian-config` modules and related scripts to ensure functionality, detect regressions, and validate behavior across supported configurations.
- **Extract Base-Files Metadata**
<br><a href=https://github.com/armbian/armbian.github.io/actions/workflows/generate-base-files-info-json.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/generate-base-files-info-json.yml?logo=githubactions&label=Status&style=for-the-badge&branch=main&logoColor=white"></a>
<br>Parses Armbian-specific metadata—such as version details, build signatures, and release identifiers—and embeds it into upstream base-files packages for distribution.
- **Mirror Comparison & Redirector Config Generation**
<br><a href=https://github.com/armbian/armbian.github.io/actions/workflows/generate-redirector-config.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/generate-redirector-config.yml?logo=githubactions&label=Status&style=for-the-badge&branch=main&logoColor=white"></a>
<br>Compares contents of all Armbian mirror servers and generates dynamic redirector configurations to optimize download reliability and speed.
- **Update Download JSON Index**
<br><a href=https://github.com/armbian/armbian.github.io/actions/workflows/generate-web-index.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/generate-web-index.yml?logo=githubactions&label=Status&style=for-the-badge&branch=main&logoColor=white"></a>
<br>Automatically updates the download index to reflect the latest available images and metadata for all supported platforms.
- **Pull Excerpts from Armbian Jira**
<br><a href=https://github.com/armbian/armbian.github.io/actions/workflows/generate-jira-excerpt.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/generate-jira-excerpt.yml?logo=githubactions&label=Status&style=for-the-badge&branch=main&logoColor=white"></a>
<br>Extracts public issue data and selected metadata from Armbian’s Jira project management system for integration or reporting purposes.
- **Wireless Performance Testing**
<br><a href=https://github.com/armbian/armbian.github.io/actions/workflows/wireless-performance-autotest.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/wireless-performance-autotest.yml?logo=githubactions&label=Status&style=for-the-badge&branch=main&logoColor=white"></a>
<br>Runs automated [wireless network benchmarks](https://docs.armbian.com/WifiPerformance/) to assess driver performance and identify regressions.
- **Mirror GitHub Artifacts to CDN**
<br><a href=https://github.com/armbian/armbian.github.io/actions/workflows/mirror.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/mirror.yml?logo=githubactions&label=Status&style=for-the-badge&branch=main&logoColor=white"></a>
<br>Pushes release images to [Armbian’s Content Delivery Network](http://cache.armbian.com/) for fast and distributed access worldwide.
- **Invite Recent Contributors**
<br><a href=https://github.com/armbian/armbian.github.io/actions/workflows/invite-contributors.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/invite-contributors.yml?logo=githubactions&label=Status&style=for-the-badge&branch=main&logoColor=white"></a>
<br>Identifies recent external contributors and automatically sends GitHub invitations to join [the Armbian organization](https://github.com/orgs/armbian/people).
- **Generate Authors and Partners JSON**
<br><a href=https://github.com/armbian/armbian.github.io/actions/workflows/generate-partners-json.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/generate-partners-json.yml?logo=githubactions&label=Status&style=for-the-badge&branch=main&logoColor=white"></a>
<br>Creates machine-readable JSON files listing current contributors, authors, sponsors, and partners for use in website, dashboard, or credits rendering.
