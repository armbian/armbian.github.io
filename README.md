<p align="center">
  <h2 align=center><a href="#build-framework">
  <img src="https://raw.githubusercontent.com/armbian/.github/master/profile/logo.png" alt="Armbian logo" width="50%">
  </a>
<br><br>
</h2>

### What does armbian.github.io do?

Monitors the CI workflows of the Armbian project and generates various data exchange files to support automation, integration, and reporting across the development pipeline.

| Action  | Status  |
|:--|---:|
|Build artifacts assembly|<a href=https://github.com/armbian/os><img alt="Artifacts generation" src="https://img.shields.io/github/actions/workflow/status/armbian/os/complete-artifact-matrix-all.yml?logo=dependabot&label=Status&style=for-the-badge&branch=main&logoColor=white"></a>|
|Generate APT Repository|<a href=https://github.com/armbian/os/actions/workflows/repository-update.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/os/repository-update.yml?logo=githubactions&label=Status&style=for-the-badge&branch=main"></a>|
| [Publish content](https://github.armbian.com/) of what is pushed to `data` folder inside `data` repository.  |  <a href=https://github.com/armbian/armbian.github.io/actions/workflows/directory-listing.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/directory-listing.yml?logo=githubactions&label=Status&style=for-the-badge&branch=main"></a>  |
| Extract and store information about _base-files_. | <a href=https://github.com/armbian/armbian.github.io/actions/workflows/generate-base-files-info-json.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/generate-base-files-info-json.yml?logo=githubactions&label=Status&style=for-the-badge&branch=main"></a> | 
| Compare all mirrors contents and generate redirector configs | <a href=https://github.com/armbian/armbian.github.io/actions/workflows/generate-redirector-config.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/generate-redirector-config.yml?logo=githubactions&label=Status&style=for-the-badge&branch=main"></a> | 
| Update download JSON index|<a href=https://github.com/armbian/armbian.github.io/actions/workflows/generate-web-index.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/generate-web-index.yml?logo=githubactions&label=Status&style=for-the-badge&branch=main"></a>|
| Pull excerpts from Armbian Jira|<a href=https://github.com/armbian/armbian.github.io/actions/workflows/generate-jira-excerpt.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/generate-jira-excerpt.yml?logo=githubactions&label=Status&style=for-the-badge&branch=main"></a>|
| [Wireless performance testing](https://docs.armbian.com/WifiPerformance/) |<a href=https://github.com/armbian/armbian.github.io/actions/workflows/wireless-performance-autotest.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/wireless-performance-autotest.yml?logo=githubactions&label=Status&style=for-the-badge&branch=main"></a>|
| Mirror repository artifacts to our CDN |<a href=https://github.com/armbian/armbian.github.io/actions/workflows/mirror.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/mirror.yml?logo=githubactions&label=Status&style=for-the-badge&branch=main"></a>|
| Invite recent contributors to organization |<a href=https://github.com/armbian/armbian.github.io/actions/workflows/invite-contributors.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/invite-contributors.yml?logo=githubactions&label=Status&style=for-the-badge&branch=main"></a>|
| Generate authors and partners JSON |<a href=https://github.com/armbian/armbian.github.io/actions/workflows/generate-partners-json.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/generate-partners-json.yml?logo=githubactions&label=Status&style=for-the-badge&branch=main"></a>|
