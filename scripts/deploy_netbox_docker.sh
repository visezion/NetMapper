#!/bin/bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCKER_DIR="${DOCKER_DIR:-$REPO_ROOT/docker}"
BRANCH="${1:-}"

cd "$REPO_ROOT"

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
TARGET_BRANCH="${BRANCH:-$CURRENT_BRANCH}"

echo "Repository: $REPO_ROOT"
echo "Branch: $TARGET_BRANCH"

git fetch --all --prune

if [ "$CURRENT_BRANCH" != "$TARGET_BRANCH" ]; then
    git checkout "$TARGET_BRANCH"
fi

git pull --ff-only

cd "$DOCKER_DIR"

docker compose build --no-cache netbox netbox-worker netbox-housekeeping
docker compose up -d netbox netbox-worker netbox-housekeeping
docker compose logs --tail=100 netbox
