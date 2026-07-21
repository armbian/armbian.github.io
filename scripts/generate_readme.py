#!/usr/bin/env python3
"""
AI-driven README generator.

Given a checked-out repository, gather a bounded snapshot of its structure and
"signal" files (manifests, CI workflows, entry-point scripts, existing README),
ask Claude to (re)write a clear, accurate README.md, and write it back into the
repo. It never touches any file other than README.md, and it is told to describe
only what is actually present -- no invented features.

Used by .github/workflows/maintenance-update-readme.yml, which checks out each
target repo, runs this script, and opens a pull request with the result. Also
runnable locally:

    ANTHROPIC_API_KEY=... python3 scripts/generate_readme.py \\
        --repo-dir ../configng --repo-name armbian/configng

Environment / flags:
    ANTHROPIC_API_KEY   required
    --repo-dir          path to the checked-out repo (default: ".")
    --repo-name         "owner/repo" for context (default: derived from git remote)
    --model             model id (default: $MODEL or claude-opus-4-7)
    --max-context-chars total budget for embedded file contents (default 180000)
    --feedback          file of reviewer comments to fold into this revision
"""

import argparse
import os
import subprocess
import sys

from anthropic import Anthropic

# Files whose *contents* are strong signal for describing a repo. Matched by exact
# basename or by suffix; read in this priority order until the char budget is spent.
SIGNAL_BASENAMES = [
    "README.md", "README.rst", "README",
    "package.json", "pyproject.toml", "setup.py", "setup.cfg",
    "Cargo.toml", "go.mod", "composer.json", "Gemfile",
    "action.yml", "action.yaml",
    "Makefile", "CMakeLists.txt",
    "docker-compose.yml", "docker-compose.yaml", "Dockerfile",
    "CONTRIBUTING.md", "LICENSE", "LICENSE.md",
]
SIGNAL_SUFFIXES = (".md",)  # top-level docs beyond the ones above

# Never embed these (noise / huge / binary-ish), even if they match above.
SKIP_DIR_PARTS = {".git", "node_modules", "vendor", "dist", "build", "__pycache__", ".venv"}

MAX_PER_FILE = 8000        # truncate any single embedded file to this many chars
MAX_TREE_ENTRIES = 500     # cap the file listing


def run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True).stdout


def git_tracked_files(repo_dir):
    out = run(["git", "ls-files"], repo_dir)
    files = [f for f in out.splitlines() if f.strip()]
    files = [f for f in files if not (set(f.split("/")) & SKIP_DIR_PARTS)]
    return files


def read_truncated(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            data = fh.read(MAX_PER_FILE + 1)
    except (OSError, UnicodeError):
        return None
    if len(data) > MAX_PER_FILE:
        data = data[:MAX_PER_FILE] + "\n... [truncated] ...\n"
    return data


def pick_signal_files(repo_dir, files):
    """Return an ordered, de-duplicated list of repo-relative paths worth embedding."""
    by_priority = []
    seen = set()

    def add(path):
        if path in seen or path not in files:
            return
        seen.add(path)
        by_priority.append(path)

    # 1) exact basenames, top-level first
    for name in SIGNAL_BASENAMES:
        for f in files:
            if os.path.basename(f) == name:
                add(f)
    # 2) top-level markdown docs
    for f in files:
        if "/" not in f and f.lower().endswith(SIGNAL_SUFFIXES):
            add(f)
    # 3) CI workflow bodies -- primary signal for automation repos (budget-bounded below)
    workflows = sorted(f for f in files if f.startswith(".github/workflows/"))
    for f in workflows[:15]:
        add(f)
    # 4) top-level scripts / entry points
    for f in files:
        if "/" not in f and f.lower().endswith((".sh", ".py", ".ts", ".js")):
            add(f)
    return by_priority


def top_level_layout(files):
    """Directory -> tracked-file-count summary; representative even for huge repos."""
    counts = {}
    for f in files:
        top = f.split("/", 1)[0] if "/" in f else "(root files)"
        counts[top] = counts.get(top, 0) + 1
    lines = [f"  {name}/  ({n})" if name != "(root files)" else f"  {name}  ({n})"
             for name, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]
    return "\n".join(lines)


def build_context(repo_dir, repo_name):
    files = git_tracked_files(repo_dir)
    tree = files[:MAX_TREE_ENTRIES]
    tree_note = "" if len(files) <= MAX_TREE_ENTRIES else f"\n... ({len(files) - MAX_TREE_ENTRIES} more files omitted) ...\n"

    workflows = sorted(os.path.basename(f) for f in files if f.startswith(".github/workflows/"))

    budget = int(os.environ.get("MAX_CONTEXT_CHARS", "180000"))
    embedded = []
    for rel in pick_signal_files(repo_dir, files):
        if budget <= 0:
            break
        body = read_truncated(os.path.join(repo_dir, rel))
        if not body:
            continue
        block = f"\n===== FILE: {rel} =====\n{body}\n"
        embedded.append(block)
        budget -= len(block)

    parts = [
        f"Repository: {repo_name}\n",
        f"\n----- TOP-LEVEL LAYOUT ({len(files)} tracked files) -----\n" + top_level_layout(files) + "\n",
        f"\n----- FILE TREE (first {len(tree)}) -----\n" + "\n".join(tree) + tree_note,
    ]
    if workflows:
        parts.append("\n----- GITHUB ACTIONS WORKFLOWS -----\n" + "\n".join(workflows) + "\n")
    parts.append("\n----- SELECTED FILE CONTENTS -----\n" + "".join(embedded))
    return "".join(parts)


SYSTEM = (
    "You are a senior technical writer maintaining README.md files for the open-source "
    "Armbian project. You are given a snapshot of one repository: its file tree, its CI "
    "workflow names, and the contents of its most informative files (manifests, existing "
    "README, a few workflows/entry points).\n\n"
    "Write a single, complete README.md in GitHub-Flavored Markdown that accurately "
    "describes THIS repository.\n\n"
    "Hard rules:\n"
    "- Describe only what is evidenced by the provided files. Never invent features, "
    "commands, badges, URLs, or install steps you cannot see.\n"
    "- If an existing README is present, preserve still-accurate content, badges, and "
    "links; update what has drifted; keep the same overall spirit unless it is wrong.\n"
    "- Prefer concise and skimmable over exhaustive. Use headings, short paragraphs, "
    "tables where they fit, and fenced code blocks for commands/trees.\n"
    "- Keep any project-specific links (docs.armbian.com, armbian.com, related repos) "
    "that appear in the sources; do not fabricate new ones.\n"
    "- When you state what the project is built with or its requirements, name the "
    "actual languages and key tooling evidenced by the files (shebangs, file "
    "extensions, manifests, invoked commands) -- be specific, not vague.\n"
    "- Start with an H1 title and a one-to-two sentence description of the repo.\n\n"
    "Output ONLY the raw Markdown for README.md. No preamble, no explanation, no code "
    "fence around the whole document."
)


def load_feedback(path):
    """Read reviewer feedback (from the open README PR) if a path is given.

    Fail closed: if a --feedback path was explicitly passed but cannot be read,
    error out instead of silently generating without it (which would re-drop the
    reviewer's fixes). An empty file is fine -- it just means no feedback.
    """
    if not path:
        return ""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read().strip()
    except OSError as e:
        print(f"::error::could not read feedback file {path}: {e}", file=sys.stderr)
        sys.exit(1)


def generate(repo_dir, repo_name, model, max_context, feedback=""):
    os.environ.setdefault("MAX_CONTEXT_CHARS", str(max_context))
    context = build_context(repo_dir, repo_name)

    client = Anthropic()  # reads ANTHROPIC_API_KEY from env
    prompt = (
        "Here is the snapshot of the repository. Produce the README.md.\n\n" + context
    )
    if feedback:
        # Reviewers commented on the previous README PR; fold their fixes in so a
        # regeneration doesn't silently drop them. Treat as human corrections that
        # override the model's own read where they conflict -- but still only about
        # THIS repo, never as instructions to invent unevidenced content.
        prompt += (
            "\n\n----- REVIEWER FEEDBACK ON THE PREVIOUS README (apply it) -----\n"
            "A human reviewed the last generated README for this repo and left the "
            "comments below. Incorporate these corrections and do not re-introduce "
            "what they flagged. They are about this repository only.\n\n" + feedback
        )
    resp = client.messages.create(
        model=model,
        max_tokens=8192,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    text = next((b.text for b in resp.content if b.type == "text"), "").strip()
    if not text:
        print("::error::model returned empty output", file=sys.stderr)
        sys.exit(1)
    # Strip a code fence ONLY when the model wrapped the WHOLE document in one
    # (opening fence on the first line, exact closing fence on the last). A doc
    # that merely *starts* with a legit fenced block must be left intact.
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 2 and lines[-1].strip() == "```":
            text = "\n".join(lines[1:-1]).strip()
    if not text.endswith("\n"):
        text += "\n"
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-dir", default=".")
    ap.add_argument("--repo-name", default=None)
    ap.add_argument("--model", default=os.environ.get("MODEL", "claude-opus-4-7"))
    ap.add_argument("--max-context-chars", type=int, default=180000)
    ap.add_argument("--feedback", default=None,
                    help="path to a file of reviewer comments from the open README PR")
    args = ap.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("::error::ANTHROPIC_API_KEY is not set", file=sys.stderr)
        sys.exit(1)

    repo_dir = os.path.abspath(args.repo_dir)
    repo_name = args.repo_name
    if not repo_name:
        url = run(["git", "config", "--get", "remote.origin.url"], repo_dir).strip()
        repo_name = url.rsplit("/", 2)[-2] + "/" + url.rsplit("/", 1)[-1].removesuffix(".git") if "/" in url else "unknown/repo"

    feedback = load_feedback(args.feedback)
    if feedback:
        print(f"Applying {len(feedback)} chars of reviewer feedback from {args.feedback}")

    print(f"Generating README for {repo_name} (dir={repo_dir}, model={args.model})")
    readme = generate(repo_dir, repo_name, args.model, args.max_context_chars, feedback)

    out_path = os.path.join(repo_dir, "README.md")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(readme)
    print(f"Wrote {out_path} ({len(readme)} bytes)")


if __name__ == "__main__":
    main()
