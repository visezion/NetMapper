#!/bin/bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NETBOX_DOCKER_DIR="${NETBOX_DOCKER_DIR:-${DOCKER_DIR:-$REPO_ROOT/../netbox-docker}}"
OVERRIDE_FILE="${OVERRIDE_FILE:-$REPO_ROOT/docker/docker-compose.override.yml}"
export NETMAPPER_PATH="${NETMAPPER_PATH:-${NETDOC_PATH:-$REPO_ROOT}}"
INSTALL_LOCAL_OVERRIDE="${INSTALL_LOCAL_OVERRIDE:-1}"
BUILD_NO_CACHE="${BUILD_NO_CACHE:-0}"
PULL_BASE_IMAGES="${PULL_BASE_IMAGES:-1}"
TARGET_REF="${1:-}"
ALLOW_DIRTY="${ALLOW_DIRTY:-0}"
NETBOX_STARTUP_TIMEOUT="${NETBOX_STARTUP_TIMEOUT:-600}"
NETBOX_WORKER_STARTUP_TIMEOUT="${NETBOX_WORKER_STARTUP_TIMEOUT:-180}"

cd "$REPO_ROOT"

CURRENT_BRANCH="$(git symbolic-ref --quiet --short HEAD || true)"
TARGET_REF="${TARGET_REF:-$CURRENT_BRANCH}"
CURRENT_COMMIT="$(git rev-parse HEAD)"

echo "Repository: $REPO_ROOT"
echo "Target ref: ${TARGET_REF:-<current detached HEAD>}"
echo "Current commit: $CURRENT_COMMIT"
echo "NetBox Docker directory: $NETBOX_DOCKER_DIR"
echo "Compose override: $OVERRIDE_FILE"
echo "NETMAPPER_PATH: $NETMAPPER_PATH"
echo "Install local override into netbox-docker: $INSTALL_LOCAL_OVERRIDE"
echo "Build without cache: $BUILD_NO_CACHE"
echo "Pull base images: $PULL_BASE_IMAGES"
echo "NetBox startup timeout: ${NETBOX_STARTUP_TIMEOUT}s"
echo "NetBox worker startup timeout: ${NETBOX_WORKER_STARTUP_TIMEOUT}s"

if [ ! -f "$NETBOX_DOCKER_DIR/docker-compose.yml" ]; then
    echo "Could not find netbox-docker compose file at: $NETBOX_DOCKER_DIR/docker-compose.yml"
    exit 1
fi

if [ ! -f "$OVERRIDE_FILE" ]; then
    echo "Could not find NetMapper compose override at: $OVERRIDE_FILE"
    exit 1
fi

if [ "$INSTALL_LOCAL_OVERRIDE" = "1" ]; then
    LOCAL_OVERRIDE_PATH="$NETBOX_DOCKER_DIR/docker-compose.override.yml"
    ln -sfn "$OVERRIDE_FILE" "$LOCAL_OVERRIDE_PATH"
    echo "Linked compose override: $LOCAL_OVERRIDE_PATH -> $OVERRIDE_FILE"
fi

compose() {
    docker compose \
        --project-directory "$NETBOX_DOCKER_DIR" \
        -f "$NETBOX_DOCKER_DIR/docker-compose.yml" \
        -f "$OVERRIDE_FILE" \
        "$@"
}

log_step() {
    local message="$1"
    echo
    echo "==> $message"
}

compose_quiet_up() {
    compose up -d "$@" >/dev/null
}

wait_for_container_state() {
    local container_name="$1"
    local expected_state="$2"
    local timeout_seconds="${3:-120}"
    local status=""
    local elapsed=0
    local last_reported_status=""

    echo "Waiting for $container_name to reach '$expected_state' (timeout: ${timeout_seconds}s)"

    for _ in $(seq 1 "$timeout_seconds"); do
        status="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container_name" 2>/dev/null || true)"
        if [ "$status" = "$expected_state" ]; then
            echo "$container_name reached '$expected_state' after ${elapsed}s"
            return 0
        fi
        if [ "$status" != "$last_reported_status" ] || [ $((elapsed % 15)) -eq 0 ]; then
            echo "  ${container_name}: current state='${status:-unknown}' elapsed=${elapsed}s"
            last_reported_status="$status"
        fi
        sleep 1
        elapsed=$((elapsed + 1))
    done

    echo "Container $container_name did not reach state '$expected_state' in ${timeout_seconds}s."
    return 1
}

if [ "$ALLOW_DIRTY" != "1" ] && [ -n "$(git status --short)" ]; then
    echo "Refusing to deploy from a dirty working tree."
    echo "Commit or stash local changes first, or rerun with ALLOW_DIRTY=1 if intentional."
    exit 1
fi

git fetch --all --prune

if [ -n "$TARGET_REF" ] && [ "$CURRENT_BRANCH" != "$TARGET_REF" ]; then
    git checkout "$TARGET_REF"
fi

if git symbolic-ref -q HEAD >/dev/null; then
    git pull --ff-only
else
    echo "Detached HEAD detected (tag or commit checkout); skipping git pull."
fi

UPDATED_COMMIT="$(git rev-parse HEAD)"
SHORT_COMMIT="$(git rev-parse --short=12 HEAD)"
export NETMAPPER_IMAGE_TAG="${NETMAPPER_IMAGE_TAG:-netmapper-${SHORT_COMMIT}}"
echo "Deploying commit: $UPDATED_COMMIT"
echo "Docker image tag: netbox:${NETMAPPER_IMAGE_TAG}"

log_step "Starting dependency containers"
compose_quiet_up postgres redis redis-cache
wait_for_container_state netbox-docker-postgres-1 healthy 120
wait_for_container_state netbox-docker-redis-1 healthy 60
wait_for_container_state netbox-docker-redis-cache-1 healthy 60

log_step "Removing any previous image for this commit tag"
docker image rm -f "netbox:${NETMAPPER_IMAGE_TAG}" || true

log_step "Building NetMapper image"
BUILD_ARGS=()
if [ "$PULL_BASE_IMAGES" = "1" ]; then
    BUILD_ARGS+=(--pull)
fi
if [ "$BUILD_NO_CACHE" = "1" ]; then
    BUILD_ARGS+=(--no-cache)
fi
compose build "${BUILD_ARGS[@]}" netbox netbox-worker

log_step "Verifying NetMapper import inside the built image"
compose run --rm --no-deps netbox /opt/netbox/venv/bin/python -c "import pathlib, netmapper; print('Imported:', netmapper.__file__); source = pathlib.Path(netmapper.__file__).read_text(); assert 'getattr(extras_models, \"ReportModule\", None)' in source; print('NetMapper image verification passed')"

log_step "Starting NetBox"
compose_quiet_up --remove-orphans --force-recreate netbox
if ! wait_for_container_state netbox-docker-netbox-1 healthy "$NETBOX_STARTUP_TIMEOUT"; then
    echo "NetBox container did not become healthy in time."
    compose logs --tail=100 netbox
    exit 1
fi

log_step "Starting NetBox worker"
compose_quiet_up --remove-orphans --force-recreate netbox-worker
wait_for_container_state netbox-docker-netbox-worker-1 healthy "$NETBOX_WORKER_STARTUP_TIMEOUT"

log_step "Synchronizing plugin assets"
compose exec -T netbox /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py shell -c "from netmapper import sync_plugin_assets; sync_plugin_assets(); print('NetMapper asset sync passed')"

log_step "Recent NetBox logs"
compose logs --tail=100 netbox
