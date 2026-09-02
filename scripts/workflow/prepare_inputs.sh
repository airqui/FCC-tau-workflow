#!/usr/bin/env bash
set -euo pipefail

usage() { echo "usage: $0 [--write OUTPUT_MANIFEST] DATA_ROOT OUTPUT_ROOT" >&2; }
destination=""; write=0
if [[ "${1:-}" == "--write" ]]; then
    [[ $# -ge 2 ]] || { usage; exit 2; }
    write=1; destination=$2; shift 2
fi
[[ $# -eq 2 ]] || { usage; exit 2; }
data_root=$1; output_root=$2
test -d "$data_root" || { echo "ERROR: missing data root: $data_root" >&2; exit 3; }
test -d "$output_root" || { echo "ERROR: missing output root: $output_root" >&2; exit 3; }

candidate=$(mktemp "${TMPDIR:-/tmp}/fcc-tau-inputs.XXXXXX")
trap 'rm -f -- "$candidate"' EXIT
complete=0; partial=0; pending=0
while IFS= read -r input; do
    name=${input##*/}; sample=${name%.gz}; sample=${sample%.stdhep}
    sim="$output_root/$sample/${sample}_SIM.edm4hep.root"
    rec="$output_root/$sample/${sample}_REC.edm4hep.root"
    if test -s "$rec"; then complete=$((complete+1))
    elif test -e "$rec" || test -e "$sim"; then partial=$((partial+1)); echo "PARTIAL excluded: $sample" >&2
    else echo "$input" >> "$candidate"; pending=$((pending+1)); fi
done < <(find "$data_root" -maxdepth 1 -type f -name '*.stdhep.gz' -size +0c -print | sort)
printf 'complete=%d partial=%d pending=%d\n' "$complete" "$partial" "$pending" >&2
if (( write )); then
    test ! -e "$destination" || { echo "ERROR: refusing overwrite: $destination" >&2; exit 4; }
    mkdir -p "$(dirname "$destination")"
    temporary="${destination}.partial.$$"
    cp "$candidate" "$temporary"; mv "$temporary" "$destination"
else
    cat "$candidate"
fi
