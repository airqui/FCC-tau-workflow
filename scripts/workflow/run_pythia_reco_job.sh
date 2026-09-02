#!/usr/bin/env bash
set -euo pipefail

fail() { local message=$1 status=${2:-1}; echo "ERROR: $message" >&2; exit "$status"; }
[[ $# -eq 2 ]] || { echo "usage: $0 INPUT_SIM JOB_ID" >&2; exit 2; }
script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=env.sh
source "$script_dir/env.sh"
: "${FCC_TAU_PYTHIA_SIM_ROOT:?set FCC_TAU_PYTHIA_SIM_ROOT}"
: "${FCC_TAU_PYTHIA_RECO_ROOT:?set FCC_TAU_PYTHIA_RECO_ROOT}"
sim_root=$(readlink -f "$FCC_TAU_PYTHIA_SIM_ROOT")
campaign_root=$(readlink -f "$FCC_TAU_PYTHIA_RECO_ROOT")
output_root="${FCC_TAU_OUTPUT:-$campaign_root/outputs}"
tmp_root="${FCC_TAU_TMP:-$campaign_root/tmp}"
log_root="${FCC_TAU_LOG:-$FCC_TAU_REPO/run/logs/PYTHIA8_ourReco/reco}"

input_file=$(readlink -f "$1"); job_id=$2
[[ "$job_id" =~ ^[0-9]+[.][0-9]+$ ]] || fail "invalid Condor job id: $job_id" 3
test -s "$input_file" || fail "missing, unreadable, or empty SIM: $input_file" 10
case "$input_file" in "$sim_root"/out_sim_edm4hep_*.root) ;; *) fail "SIM outside configured input root: $input_file" 11 ;; esac
input_name=$(basename "$input_file")
[[ "$input_name" =~ ^out_sim_edm4hep_([0-9]+)[.]root$ ]] || fail "unexpected SIM name: $input_name" 12
suffix=${BASH_REMATCH[1]}; output_base="$output_root/out_sim_edm4hep_${suffix}"
rec_file="${output_base}_REC.edm4hep.root"; log_dir="$log_root/out_sim_edm4hep_${suffix}"
lock_dir="$output_root/.out_sim_edm4hep_${suffix}.reco.lock"; metrics_file="$log_dir/metrics.txt"

mkdir -p "$output_root" "$tmp_root" "$log_root"
for existing in "${output_base}"_*; do test ! -e "$existing" || fail "existing output requires review: $existing" 13; done
test ! -e "$log_dir" || fail "existing sample log directory requires review: $log_dir" 14
mkdir "$log_dir"; mkdir "$lock_dir" 2>/dev/null || fail "active or residual lock: $lock_dir" 15
work_dir=""
cleanup() {
    local status=$?
    if [[ -n "$work_dir" && "$work_dir" == "$tmp_root"/out_sim_edm4hep_"$suffix".* ]]; then rm -rf -- "$work_dir"; fi
    rmdir "$lock_dir" 2>/dev/null || true
    return "$status"
}
trap cleanup EXIT
work_dir=$(mktemp -d "$tmp_root/out_sim_edm4hep_${suffix}.XXXXXX"); export TMPDIR="$work_dir"

test -r "$ILDCONFIG_DIR/ILDReconstruction.py" || fail "missing ILDReconstruction.py" 18
command -v k4run >/dev/null || fail "k4run unavailable" 19
command -v podio-dump >/dev/null || fail "podio-dump unavailable" 20
start_epoch=$(date +%s)
{
    echo "campaign=PYTHIA8_ourReco"; echo "job_id=$job_id"; echo "host=$(hostname)"; echo "start=$(date --iso-8601=seconds)"
    echo "input=$input_file"; echo "input_bytes=$(stat -c %s "$input_file")"; echo "output=$rec_file"
    echo "key4hep_setup=$KEY4HEP_SETUP"; echo "detector_model=$FCC_TAU_DETECTOR_MODEL"; echo "compact_file=$COMPACT_FILE"
    echo "compact_sha256=$FCC_TAU_GEOMETRY_SHA256"; echo "ildconfig_commit=$(git -C "$ILDCONFIG_ROOT" rev-parse HEAD)"
    echo "reconstruction_command=k4run ILDReconstruction.py --detectorModel=$FCC_TAU_DETECTOR_MODEL --inputFiles=$input_file --outputFileBase=$output_base --num-events=-1"
    echo "no_beamcal_reco_flag=absent"
} > "$metrics_file"
cd "$ILDCONFIG_DIR"; set +e
/usr/bin/time -v -o "$log_dir/reconstruction.time" k4run ILDReconstruction.py \
    --detectorModel="$FCC_TAU_DETECTOR_MODEL" --inputFiles="$input_file" \
    --outputFileBase="$output_base" --num-events=-1 > "$log_dir/reconstruction.log" 2>&1
reco_status=$?; set -e
printf 'reconstruction_exit_code=%s\nreconstruction_wall_seconds=%s\n' "$reco_status" "$(( $(date +%s) - start_epoch ))" >> "$metrics_file"
(( reco_status == 0 )) || fail "ILDReconstruction failed with code $reco_status; partial products preserved" "$reco_status"
test -s "$rec_file" || fail "REC missing or empty after successful command: $rec_file" 21
event_counts=$(python -c 'import ROOT,sys
vals=[]
for path in sys.argv[1:]:
 f=ROOT.TFile.Open(path,"READ")
 if not f or f.IsZombie(): raise SystemExit(f"unreadable ROOT: {path}")
 t=f.Get("events")
 if not t: raise SystemExit(f"missing events tree: {path}")
 vals.append(int(t.GetEntries())); f.Close()
print(f"sim_events={vals[0]} rec_events={vals[1]}")' "$input_file" "$rec_file")
echo "$event_counts" >> "$metrics_file"
sim_events=${event_counts#sim_events=}; sim_events=${sim_events%% *}; rec_events=${event_counts##*rec_events=}
[[ "$sim_events" == "$rec_events" ]] || fail "event-count mismatch: $event_counts" 22
podio-dump -e 0 "$rec_file" > "$log_dir/podio_dump_event0.txt"
printf 'rec_bytes=%s\nend=%s\nstatus=PASS\n' "$(stat -c %s "$rec_file")" "$(date --iso-8601=seconds)" >> "$metrics_file"
printf 'RECO-only job completed\nSIM: %s\nREC: %s\nEvents: %s\nLogs: %s\n' "$input_file" "$rec_file" "$sim_events" "$log_dir"
