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
| Extract and store information about base-files. | <a href=https://github.com/armbian/armbian.github.io/actions/workflows/generate-base-files-info-json.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/generate-base-files-info-json.yml?logo=githubactions&label=Status&style=for-the-badge&branch=main"></a> | 
| Compare all mirrors content and generate redirector configs | <a href=https://github.com/armbian/armbian.github.io/actions/workflows/generate-redirector-config.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/generate-redirector-config.yml?logo=githubactions&label=Status&style=for-the-badge&branch=main"></a> | 
|Update download JSON index|<a href=https://github.com/armbian/armbian.github.io/actions/workflows/generate-web-index.yml><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/armbian/armbian.github.io/generate-web-index.yml?logo=githubactions&label=Status&style=for-the-badge&branch=main"></a>|
