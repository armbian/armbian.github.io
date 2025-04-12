<p align="center">
  <a href="#build-framework">
   <img src="https://raw.githubusercontent.com/armbian/build/master/.github/armbian-logo.png" alt="Armbian logo" width="144">
  </a><br>
  <a href=https://github.armbian.com/>https://github.armbian.com/</a>
  <br> 
  Build jobs artifacts sharing
  <br>
<br>
</p>

## What does this project do?

It prepares several data exchange files.

| Action  | Status  |
|:--|---:|
| [Publish content](https://github.armbian.com/) of what is pushed to `data` folder inside `data` repository.  |  <a href=https://github.com/armbian/armbian.github.io/actions/workflows/directory-listing.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/directory-listing.yml?logo=githubactions&label=Status&style=for-the-badge&branch=main"></a>  |
| Extract and store information about _base-files_. | <a href=https://github.com/armbian/armbian.github.io/actions/workflows/generate-base-files-info-json.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/generate-base-files-info-json.yml?logo=githubactions&label=Status&style=for-the-badge&branch=main"></a> | 
| Compare all mirrors contents and generate redirector configs | <a href=https://github.com/armbian/armbian.github.io/actions/workflows/generate-redirector-config.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/generate-redirector-config.yml?logo=githubactions&label=Status&style=for-the-badge&branch=main"></a> | 
| Update download JSON index|<a href=https://github.com/armbian/armbian.github.io/actions/workflows/generate-web-index.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/generate-web-index.yml?logo=githubactions&label=Status&style=for-the-badge&branch=main"></a>|
| Pull excerpts from Armbian Jira|<a href=https://github.com/armbian/armbian.github.io/actions/workflows/generate-jira-excerpt.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/generate-jira-excerpt.yml?logo=githubactions&label=Status&style=for-the-badge&branch=main"></a>|
| [Wireless performance testing](https://docs.armbian.com/WifiPerformance/) |<a href=https://github.com/armbian/armbian.github.io/actions/workflows/wireless-performance-autotest.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/wireless-performance-autotest.yml?logo=githubactions&label=Status&style=for-the-badge&branch=main"></a>|
| Mirror repository artifacts to our CDN |<a href=https://github.com/armbian/armbian.github.io/actions/workflows/mirror.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/mirror.yml?logo=githubactions&label=Status&style=for-the-badge&branch=main"></a>|
