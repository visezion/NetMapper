#!/bin/bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCKER_DIR="${DOCKER_DIR:-$REPO_ROOT/docker}"
BRANCH="${1:-}"
ALLOW_DIRTY="${ALLOW_DIRTY:-0}"

cd "$REPO_ROOT"

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
TARGET_BRANCH="${BRANCH:-$CURRENT_BRANCH}"
CURRENT_COMMIT="$(git rev-parse HEAD)"

echo "Repository: $REPO_ROOT"
echo "Branch: $TARGET_BRANCH"
echo "Current commit: $CURRENT_COMMIT"

if [ "$ALLOW_DIRTY" != "1" ] && [ -n "$(git status --short)" ]; then
    echo "Refusing to deploy from a dirty working tree."
    echo "Commit or stash local changes first, or rerun with ALLOW_DIRTY=1 if intentional."
    exit 1
fi

git fetch --all --prune

if [ "$CURRENT_BRANCH" != "$TARGET_BRANCH" ]; then
    git checkout "$TARGET_BRANCH"
fi

git pull --ff-only

UPDATED_COMMIT="$(git rev-parse HEAD)"
echo "Deploying commit: $UPDATED_COMMIT"

cd "$DOCKER_DIR"

docker compose build --no-cache netbox netbox-worker netbox-housekeeping
docker compose run --rm --no-deps netbox /opt/netbox/venv/bin/python -c "import pathlib, netdoc; print('Imported:', netdoc.__file__); source = pathlib.Path(netdoc.__file__).read_text(); assert 'getattr(extras_models, \"ReportModule\", None)' in source; print('NetDoc image verification passed')"
docker compose up -d netbox netbox-worker netbox-housekeeping
docker compose logs --tail=100 netbox
