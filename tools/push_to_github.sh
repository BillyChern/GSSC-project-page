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
# Anything appended AFTER an asset's real extension is scratch by construction
# (fig4_da_pipeline.png.prePS3bak, *.webp.preOrderNeutral, *.svg.bak2, *.pdf.dybak).
# A served asset's name ends at its extension, so this can never match one.
assets/**/*.png.*
assets/**/*.webp.*
assets/**/*.jpg.*
assets/**/*.svg.*
assets/**/*.ply.*
assets/**/*.pdf.*
EOF
fi

# Belt-and-braces: even if an older/edited .gitignore is present, make sure the
# scratch/backup/PDF cruft can never be staged by the `git add` below.
git rm -r --cached --ignore-unmatch \
  'assets/**/*_backup_*.png' 'assets/**/*_backup_*.pdf' \
  'assets/figures/*.pdf' 'assets/**/*.pdf' \
  'assets/**/*.prepatch.bak' 'assets/**/*.bak' \
  'assets/**/*.png.*' 'assets/**/*.webp.*' 'assets/**/*.jpg.*' \
  'assets/**/*.svg.*' 'assets/**/*.ply.*' 'assets/**/*.pdf.*' \
  '.audit' >/dev/null 2>&1 || true

git add .
# Distinguish "nothing staged" from a genuine commit failure: `|| true` hid both,
# and then pushed whatever HEAD happened to be.
if git diff --cached --quiet; then
  echo "Nothing staged; pushing the existing HEAD."
else
  git commit -m "${COMMIT_MSG:-Update project page}"
fi

# `git branch -M main` force-renames, so running this from a feature branch in an
# already-initialised repo would DISCARD the existing main. Refuse instead.
current="$(git symbolic-ref --quiet --short HEAD || echo '')"
if [[ "$current" != "main" ]]; then
  if git show-ref --verify --quiet refs/heads/main; then
    echo "On branch '$current' while 'main' already exists." >&2
    echo "Refusing to force-rename onto it (that would discard main)." >&2
    echo "Switch to main, or merge this branch into it, then re-run." >&2
    exit 1
  fi
  git branch -m main
fi

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
