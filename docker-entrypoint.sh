#!/bin/sh
set -eu

if [ ! -f "${RWS_WORKSPACE}/.rws-workspace.json" ]; then
    rws init "${RWS_WORKSPACE}"
fi

exec "$@"
