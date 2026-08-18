#!/usr/bin/env bash
# Push the s2d2_website/ directory to a private GitHub repo.
# Usage:
#   ./tools/push_to_github.sh git@github.com:YOUR_USERNAME/s2d2-project-page.git
# or
#   ./tools/push_to_github.sh https://github.com/YOUR_USERNAME/s2d2-project-page.git
#
# Run from the project root. Assumes the repo was created PRIVATE on github.com
# and is currently empty (no README yet).

set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <git-remote-url>" >&2
  exit 1
fi
REMOTE="$1"
# Override the commit subject for anything past the first push:
#   COMMIT_MSG="..." ./tools/push_to_github.sh <remote>

if [[ ! -f index.html ]]; then
  echo "Must be run from the s2d2_website/ root (index.html not found)" >&2
  exit 1
fi

if [[ -d .git ]]; then
  echo "Repo already initialized. Skipping 'git init'."
else
  git init
fi

# .gitignore: never overwrite a committed .gitignore (it already carries the
# backup/scratch/PDF exclusion globs below). Only write a default if the repo
# has none, and keep that default in lockstep with the committed .gitignore so
# a fresh init can't leak the multi-MB figure backups, *.prepatch.bak / *.bak
# scratch copies, or the source-render fig*.pdf into the public deploy.
if [[ ! -f .gitignore ]]; then
  cat > .gitignore <<'EOF'
# Editor
.DS_Store
.vscode/
.idea/

# Server logs
*.log
/tmp/*

# Python artifacts from the PLY exporter
__pycache__/
*.pyc

# SVG + PLY intermediates we keep regenerating
*.swp

# Dated backups of figure assets (kept locally for rollback only)
assets/**/*_backup_*.png
assets/**/*_backup_*.pdf
assets/**/*_20[0-9][0-9][0-9][0-9][0-9][0-9]_*.png
assets/**/*_20[0-9][0-9][0-9][0-9][0-9][0-9]_*.pdf

# Source-render PDFs and pre-patch backups never belong in the public deploy.
assets/figures/*.pdf
assets/**/*.pdf
assets/**/*.prepatch.bak
assets/**/*.bak

# Development render/audit scratch. Never deploy: .nojekyll makes Pages serve
# dotdirs verbatim, so tracked .audit screenshots of superseded versions of the
# page stay publicly fetchable long after the page itself has been corrected.
.audit/
EOF
fi

# Belt-and-braces: even if an older/edited .gitignore is present, make sure the
# scratch/backup/PDF cruft can never be staged by the `git add` below.
git rm -r --cached --ignore-unmatch \
  'assets/**/*_backup_*.png' 'assets/**/*_backup_*.pdf' \
  'assets/figures/*.pdf' 'assets/**/*.pdf' \
  'assets/**/*.prepatch.bak' 'assets/**/*.bak' \
  '.audit' >/dev/null 2>&1 || true

git add .
git commit -m "${COMMIT_MSG:-Update project page}" || true
git branch -M main

if git remote | grep -q '^origin$'; then
  git remote set-url origin "$REMOTE"
else
  git remote add origin "$REMOTE"
fi

git push -u origin main
echo
echo "----------------------------------------------------------------"
echo "Pushed to $REMOTE (main)."
echo "Verify on github.com that the repo visibility is 'Private'."
echo "Do NOT enable GitHub Pages until the patents are filed."
echo "----------------------------------------------------------------"
