#!/usr/bin/env bash
set -euo pipefail
[[ $# -eq 3 ]] || { echo "usage: $0 INPUT_FILE JOB_ID N_EVENTS" >&2; exit 2; }
repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
printf 'Condor job: %s\nHost: %s\nInput: %s\nEvents: %s\n' "$2" "$(hostname)" "$1" "$3"
exec "$repo_root/scripts/workflow/run_chain.sh" "$1" "$3"
