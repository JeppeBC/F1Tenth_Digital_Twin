#!/usr/bin/env bash
# Shared setup sourced by every lifecycle script. Not a lifecycle phase itself.
set -euo pipefail

LIFECYCLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
F1TENTH_DIR="$(cd "$LIFECYCLE_DIR/../../.." && pwd)"     # dtaas/, POSIX-style (/c/Users/...)
CONFIG_DIR="$LIFECYCLE_DIR/../config"
COMPOSE_FILE="$F1TENTH_DIR/compose/docker-compose.f1tenth.yml"

# docker-compose.f1tenth.yml's bind mounts use ${F1TENTH_DIR_WIN} rather than
# relative paths: when merged via `-f base.yml -f overlay.yml`, Compose
# resolves ALL relative host paths against the *base* file's directory, not
# each file's own — so a plain `../data` here silently resolved into
# workspace-dex-localhost/ instead of dtaas/ (and Grafana's provisioning
# mounts the same way, meaning it started with no datasource/dashboard).
# Needs the Windows-style form (C:/... ), not the POSIX /c/... pwd gives by
# default, for Docker Desktop to resolve it as a host bind-mount source.
F1TENTH_DIR_WIN="$(cd "$F1TENTH_DIR" && pwd -W)"
export F1TENTH_DIR_WIN

if [ -f "$CONFIG_DIR/dt.env" ]; then
    # shellcheck disable=SC1091
    source "$CONFIG_DIR/dt.env"
else
    echo "WARNING: $CONFIG_DIR/dt.env not found — copy dt.env.example to dt.env" \
         "and set DTAAS_DIR / PT_HOST for your machine. Using example defaults." >&2
    # shellcheck disable=SC1091
    source "$CONFIG_DIR/dt.env.example"
fi

if [ ! -f "$DTAAS_DIR/docker-compose.yml" ]; then
    echo "ERROR: DTAAS_DIR ($DTAAS_DIR) has no docker-compose.yml." \
         "Fix DTAAS_DIR in $CONFIG_DIR/dt.env." >&2
    exit 1
fi

export PT_HOST

dtaas_compose() {
    docker compose -f "$DTAAS_DIR/docker-compose.yml" -f "$COMPOSE_FILE" "$@"
}

latest_run_dir() {
    find "$F1TENTH_DIR/data" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort | tail -n 1
}
