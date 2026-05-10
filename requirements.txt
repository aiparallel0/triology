#!/usr/bin/env bash
# push-to-github.sh — one-command publish to GitHub via the `gh` CLI.
#
# Usage:
#   ./push-to-github.sh                          # default name + private
#   ./push-to-github.sh paper3-aad              # custom name, private
#   ./push-to-github.sh paper3-aad --public     # custom name, public
#
# If you don't have `gh` installed, see MIGRATION.md for Option B (manual
# `git push`) or Option C (web-UI drag-drop).

set -euo pipefail

REPO_NAME="${1:-paper3-aad-harness}"
VISIBILITY="${2:---private}"

# 1. Are we sitting inside the unpacked paper3 directory?
if [ ! -f "README.md" ] || [ ! -d "core" ] || [ ! -d "scripts" ]; then
    echo "Error: run this from inside the unpacked paper3/ directory." >&2
    echo "       (Looking for README.md, core/, scripts/ — none of them found.)" >&2
    exit 1
fi

# 2. Is git installed?
if ! command -v git > /dev/null; then
    echo "Error: 'git' is not installed. Install git first." >&2
    exit 1
fi

# 3. Mark this directory as safe (some setups need it after a cross-volume unzip)
git config --global --add safe.directory "$(pwd)" 2>/dev/null || true

# 4. Verify the prepared commit is intact
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "Error: this directory is not a git repository. The bundle should already" >&2
    echo "       contain a .git/ folder; if it doesn't, re-extract the zip." >&2
    exit 1
fi

if [ "$(git rev-list --count HEAD 2>/dev/null || echo 0)" = "0" ]; then
    echo "Error: no commits in the repository. Run 'git log' to inspect; if empty," >&2
    echo "       the bundle is corrupted and you should re-extract." >&2
    exit 1
fi

# 5. Is gh installed and authenticated?
if ! command -v gh > /dev/null; then
    echo "Error: 'gh' CLI not found. Install from https://cli.github.com" >&2
    echo "       OR follow MIGRATION.md Option B for the manual 'git push' path." >&2
    exit 1
fi

if ! gh auth status > /dev/null 2>&1; then
    echo "Error: gh is not authenticated. Run 'gh auth login' first." >&2
    exit 1
fi

# 6. Push it.
echo "Creating GitHub repository: $REPO_NAME ($VISIBILITY)"
echo "Source: $(pwd)"
echo ""
gh repo create "$REPO_NAME" "$VISIBILITY" --source=. --push

echo ""
echo "Done. Repository URL:"
gh repo view --json url -q .url
echo ""
echo "Sanity-check it worked:"
echo "  git clone \$(gh repo view --json url -q .url) /tmp/paper3-check"
echo "  cd /tmp/paper3-check && python -m paper3.tests.test_smoke"
