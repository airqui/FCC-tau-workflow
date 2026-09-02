#!/usr/bin/env bash
set -euo pipefail

usage() {
    echo "usage: $0 --fixture FILE --output-root DIR [--dry-run]" >&2
}
fixture=""; output_root=""; dry_run=0
while (( $# )); do
    case "$1" in
        --fixture) [[ $# -ge 2 ]] || { usage; exit 2; }; fixture=$2; shift 2 ;;
        --output-root) [[ $# -ge 2 ]] || { usage; exit 2; }; output_root=$2; shift 2 ;;
        --dry-run) dry_run=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) usage; exit 2 ;;
    esac
done
[[ -n "$fixture" && -n "$output_root" ]] || { usage; exit 2; }

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
fixture=$(readlink -f "$fixture")
output_root=$(readlink -m "$output_root")
[[ -r "$fixture" ]] || { echo "fixture is not readable: $fixture" >&2; exit 3; }
export PYTHONPATH="$repo_root/src${PYTHONPATH:+:$PYTHONPATH}"
# shellcheck source=../workflow/env.sh
source "$repo_root/scripts/workflow/env.sh"

readarray -t fixture_fields < <(python -c \
    'import sys; from fcc_tau_workflow.smoke_fixture import load_smoke_fixture; d=load_smoke_fixture(sys.argv[1]); print(d["sample"]); print(d["source_file_id"]); print(d["source_rec"]["path"]); print(d["source_rec"]["smoke_events"])' \
    "$fixture")
sample=${fixture_fields[0]}; source_id=${fixture_fields[1]}; source_rec=${fixture_fields[2]}; events=${fixture_fields[3]}

printf 'fixture=%s\nsample=%s\nsource_file_id=%s\nsource_rec=%s\nevents=%s\noutput_root=%s\n' \
    "$fixture" "$sample" "$source_id" "$source_rec" "$events" "$output_root"
(( dry_run == 0 )) || exit 0
[[ ! -e "$output_root" ]] || { echo "output root already exists: $output_root" >&2; exit 3; }
mkdir -p "$output_root"

fixture_validation="$output_root/smoke_fixture_validation.json"
linked_rec="$output_root/smoke_truthlinked.edm4hep.root"
direct="$output_root/ldirect_smoke.parquet"
candidates="$output_root/ldirect_candidates_smoke.parquet"
direct_summary="$output_root/ldirect_smoke_summary.json"
ancestor="$output_root/lancestor_smoke.parquet"
ancestor_summary="$output_root/lancestor_smoke_summary.json"
invariance="$output_root/linker_invariance.json"
products="$output_root/smoke_products.yaml"

python "$repo_root/scripts/validation/validate_smoke_fixture.py" \
    --fixture "$fixture" --output "$fixture_validation"
"$repo_root/condor/wrappers/run_truthlink_assignment_job.sh" \
    "$source_id" "$source_rec" "$direct" "$candidates" "$direct_summary" "$linked_rec" "$events"
"$repo_root/condor/wrappers/run_lancestor_job.sh" \
    "$sample" "$source_id" "$linked_rec" "$direct" "$ancestor" "$ancestor_summary" "$events"
python "$repo_root/scripts/validation/validate_smoke_outputs.py" \
    --fixture "$fixture" --linked-rec "$linked_rec" --direct "$direct" \
    --ancestor "$ancestor" --output "$invariance"
python "$repo_root/scripts/validation/write_smoke_product_manifest.py" \
    --sample "$sample" --source-file-id "$source_id" --source-rec "$linked_rec" \
    --direct "$direct" --ancestor "$ancestor" --provenance "$direct_summary" --output "$products"
python "$repo_root/scripts/validation/validate_contracts.py" --product-manifest "$products"
printf 'FCC_TAU_SMOKE_TEST=PASS products=%s\n' "$products"
