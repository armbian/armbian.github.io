---
description: "Keep open pull requests rebased on the default branch"

on:
  schedule:
    - cron: "0 4 * * *"   # daily, 04:00 UTC
  workflow_dispatch:

# Read-only by default; every write goes through the sanitized safe-outputs job.
permissions:
  contents: read
  pull-requests: read

engine: claude

network: defaults

timeout-minutes: 25

concurrency:
  group: keep-prs-rebased
  cancel-in-progress: false

tools:
  github:
    toolsets: [repos, pull_requests]
  bash: ["git:*"]

safe-outputs:
  # Push the rebased branch back to the PR. Restricted to same-repo PRs that
  # carry the opt-in label; forks are rejected by the safe-output itself.
  push-to-pull-request-branch:
    target: "*"
    required-labels: [keep-rebased]
    max: 10
    if-no-changes: "ignore"
    # A rebase rewrites history (non-fast-forward), so use a direct git push
    # rather than the signed-commit replay API, which cannot represent it.
    signed-commits: false
  # Leave a note on PRs that need a manual rebase (unresolvable conflicts).
  add-comment:
    target: "*"
    max: 20
---

# Keep open pull requests rebased on the default branch

Your job is to keep this repository's open pull requests rebased on top of the
default branch, so they merge cleanly and their CI runs against current code.

## Which PRs to process

Act only on pull requests in **this** repository (`${{ github.repository }}`) that are **all** of:

- **open**,
- **not draft**,
- from a branch in **this same repository** — never a fork (pushing to fork PRs is not supported and must be skipped),
- labelled **`keep-rebased`** (the opt-in signal; the push safe-output also enforces this),
- **behind** the default branch (if a PR is already up to date, there is nothing to do — skip it).

## For each such PR

1. Find the repository's default branch and make sure you have its latest commit locally (`git fetch`).
2. Check out the PR's head branch and rebase it onto the default branch: `git rebase <default-branch>`.
3. **Clean rebase** → use the `push-to-pull-request-branch` safe output to update that PR's branch with the rebased commits.
4. **Conflicts** → only resolve them if the fix is trivial and unambiguous (e.g. each side added unrelated lines). If you cannot resolve them with high confidence:
   - `git rebase --abort`,
   - do **not** push,
   - use the `add-comment` safe output on that PR to say it needs a manual rebase, and list the conflicting files.

## Rules

- Never modify a PR that lacks the `keep-rebased` label.
- Never touch fork PRs.
- At most one push per PR. Do not open new PRs, and do not close or merge anything.
- Never force a questionable conflict resolution — when in doubt, skip and comment.
- Keep comments short and factual.
