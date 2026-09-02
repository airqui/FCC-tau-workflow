#!/usr/bin/env bash
set -euo pipefail
[[ $# -eq 7 ]] || { echo "usage: $0 SAMPLE SOURCE_ID SOURCE_REC DIRECT ANCESTOR SUMMARY EXPECTED" >&2; exit 2; }
repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
# shellcheck source=../../scripts/workflow/env.sh
source "$repo_root/scripts/workflow/env.sh"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 ROOT_MAX_THREADS=1 TBB_NUM_THREADS=1
python "$repo_root/scripts/workflow/extract_lancestor_assignments.py" --sample "$1" --source-file-id "$2" --source-rec "$3" --direct-assignment "$4" --ancestor-output "$5" --summary-output "$6" --expected-events "$7"
