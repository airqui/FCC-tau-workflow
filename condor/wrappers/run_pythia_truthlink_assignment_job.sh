#!/usr/bin/env bash
set -euo pipefail
[[ $# -eq 7 ]] || { echo "usage: $0 SOURCE_ID INPUT_REC ASSIGNMENT_PARQUET CANDIDATE_PARQUET SUMMARY_JSON RETAINED_LINKED_REC_OR_DASH EXPECTED_EVENTS" >&2; exit 2; }
source_id=$1; input_rec=$2; assignment_output=$3; candidate_output=$4; summary_output=$5; retained_linked_rec=$6; expected_events=$7
[[ "$source_id" =~ ^[0-9]{9}$ ]] || { echo "invalid source id: $source_id" >&2; exit 2; }
[[ "$expected_events" =~ ^[1-9][0-9]*$ ]] || { echo "invalid event count: $expected_events" >&2; exit 2; }
[[ -r "$input_rec" ]] || { echo "missing input REC: $input_rec" >&2; exit 2; }
for output in "$assignment_output" "$candidate_output" "$summary_output"; do
    [[ ! -e "$output" && -d "$(dirname "$output")" ]] || { echo "invalid/pre-existing output: $output" >&2; exit 3; }
done
if [[ "$retained_linked_rec" != "-" ]]; then
    [[ ! -e "$retained_linked_rec" && -d "$(dirname "$retained_linked_rec")" ]] || { echo "invalid retained REC output" >&2; exit 3; }
fi
repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
code_contract="${FCC_TAU_CODE_CONTRACT:-$repo_root/configs/truthlink/code_checksums.sha256}"
(cd "$repo_root" && sha256sum --check --quiet "$code_contract") || { echo "workflow code checksum mismatch" >&2; exit 3; }
# shellcheck source=../../scripts/workflow/env.sh
source "$repo_root/scripts/workflow/env.sh"
export OMP_NUM_THREADS=1 OMP_THREAD_LIMIT=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 ROOT_MAX_THREADS=1 PYTHON_CPU_COUNT=1 TBB_NUM_THREADS=1
scratch_parent=${TMPDIR:-/tmp}; job_tmp=$(mktemp -d "$scratch_parent/truthlink_${source_id}_XXXXXX")
cleanup() { if [[ -n ${job_tmp:-} && -d "$job_tmp" && "$job_tmp" == "$scratch_parent"/truthlink_${source_id}_* ]]; then rm -rf -- "$job_tmp"; fi; }
trap cleanup EXIT
linked_tmp="$job_tmp/events_${source_id}_REC_truthlinked_v1.edm4hep.root"; time_file="$job_tmp/linker_time.txt"
export TRUTHLINK_INPUT_REC=$input_rec TRUTHLINK_OUTPUT_REC=$linked_tmp TRUTHLINK_EVTMAX=$expected_events
/usr/bin/time -v -o "$time_file" k4run "$repo_root/scripts/workflow/run_truthlink_linker_v1.py"
[[ -s "$linked_tmp" ]] || { echo "linker produced no output" >&2; exit 4; }
extract_args=(--linked-rec "$linked_tmp" --source-rec "$input_rec" --source-file-id "$source_id" --expected-events "$expected_events" --assignment-output "$assignment_output" --candidate-output "$candidate_output" --summary-output "$summary_output" --linker-time-file "$time_file")
if [[ "$retained_linked_rec" != "-" ]]; then extract_args+=(--retained-linked-rec "$retained_linked_rec" --checksum-linked-rec); fi
python "$repo_root/scripts/workflow/extract_truthlink_assignments_pythia.py" "${extract_args[@]}"
if [[ "$retained_linked_rec" != "-" ]]; then mv "$linked_tmp" "$retained_linked_rec"; [[ -s "$retained_linked_rec" ]]; fi
printf 'TRUTHLINK_ASSIGNMENT_V1_COMPLETE source_file_id=%s events=%s\n' "$source_id" "$expected_events"
