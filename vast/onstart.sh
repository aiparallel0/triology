#!/usr/bin/env bash
# vast.ai onstart hook for the Paper 3 AAD experiment harness.
#
# Use this in the "On-start Script" field of a vast.ai instance template,
# or run it manually after first SSH:
#
#     # Public repo:
#     curl -fsSL https://raw.githubusercontent.com/<owner>/<repo>/<branch>/vast/onstart.sh | bash
#
#     # Private repo (this one) — pass a GitHub PAT or fine-grained token
#     # with read access via the GITHUB_TOKEN env var:
#     export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxx
#     curl -fsSL -H "Authorization: token $GITHUB_TOKEN" \
#         https://raw.githubusercontent.com/aiparallel0/triology/claude/transfer-to-github-MHAZT/vast/onstart.sh \
#         | bash
#
# It installs system + Python deps and runs the synthetic smoke test as a
# sanity check. Real-corpus runs (SROIE / CORD-v2) require you to mount or
# download the data separately and re-invoke the relevant `paper3.scripts.*`
# modules.

set -euo pipefail

REPO_OWNER="${REPO_OWNER:-aiparallel0}"
REPO_NAME="${REPO_NAME:-triology}"
REPO_BRANCH="${REPO_BRANCH:-claude/transfer-to-github-MHAZT}"
WORKDIR="${WORKDIR:-/workspace/paper3}"

# Build the clone URL with optional token auth (for private repos).
if [ -n "${GITHUB_TOKEN:-}" ]; then
  REPO_URL="${REPO_URL:-https://x-access-token:${GITHUB_TOKEN}@github.com/${REPO_OWNER}/${REPO_NAME}.git}"
else
  REPO_URL="${REPO_URL:-https://github.com/${REPO_OWNER}/${REPO_NAME}.git}"
fi

# Mask the token in any echoed URL.
SAFE_URL="$(echo "$REPO_URL" | sed -E 's#://[^@]+@#://***@#')"
echo "[onstart] cloning $SAFE_URL ($REPO_BRANCH) -> $WORKDIR"
mkdir -p "$(dirname "$WORKDIR")"
if [ -d "$WORKDIR/.git" ]; then
  git -C "$WORKDIR" remote set-url origin "$REPO_URL"
  git -C "$WORKDIR" fetch --depth=1 origin "$REPO_BRANCH"
  git -C "$WORKDIR" checkout -f "$REPO_BRANCH"
  git -C "$WORKDIR" reset --hard "origin/$REPO_BRANCH"
else
  git clone --depth=1 --branch "$REPO_BRANCH" "$REPO_URL" "$WORKDIR"
fi
# Drop the token from the recorded remote so it doesn't sit in .git/config.
git -C "$WORKDIR" remote set-url origin \
  "https://github.com/${REPO_OWNER}/${REPO_NAME}.git"

echo "[onstart] installing Python deps"
python3 -m pip install --upgrade pip
python3 -m pip install -r "$WORKDIR/requirements.txt"
if [ "${INSTALL_GPU:-0}" = "1" ] && [ -f "$WORKDIR/requirements.gpu.txt" ]; then
  echo "[onstart] INSTALL_GPU=1 -> installing GPU/model deps"
  python3 -m pip install -r "$WORKDIR/requirements.gpu.txt"
fi

echo "[onstart] running synthetic smoke test"
cd "$(dirname "$WORKDIR")"
PKG="$(basename "$WORKDIR")"
# Run smoke test as a module so relative imports resolve.
python3 -m "$PKG.tests.test_smoke" || {
  echo "[onstart] smoke test failed — likely the data/ loader module is not yet implemented."
  echo "[onstart] see STATUS.md for details. Continuing so the box stays usable."
}

echo "[onstart] done. cd $WORKDIR and run e.g.:"
echo "  python3 -m $PKG.scripts.s1_T_distribution --corpus synthetic --n 500"
