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

if [[ ! -f index.html ]]; then
  echo "Must be run from the s2d2_website/ root (index.html not found)" >&2
  exit 1
fi

if [[ -d .git ]]; then
  echo "Repo already initialized. Skipping 'git init'."
else
  git init
fi

# A tiny .gitignore so we don't push server logs / editor junk.
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
EOF

git add .
git commit -m "Initial project page scaffold with interactive 3D viewer" || true
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
