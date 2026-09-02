#!/usr/bin/env bash
set -euo pipefail
[[ $# -eq 2 ]] || { echo "usage: $0 DATA_ROOT OUTPUT_ROOT" >&2; exit 2; }
data_root=$1; output_root=$2
complete=0; partial=0; missing=0
while IFS= read -r input; do
    name=${input##*/}; sample=${name%.gz}; sample=${sample%.stdhep}
    sim="$output_root/$sample/${sample}_SIM.edm4hep.root"
    rec="$output_root/$sample/${sample}_REC.edm4hep.root"
    if test -s "$rec"; then complete=$((complete+1))
    elif test -e "$rec" || test -e "$sim"; then partial=$((partial+1)); echo "PARTIAL $sample"
    else missing=$((missing+1)); fi
done < <(find "$data_root" -maxdepth 1 -type f -name '*.stdhep.gz' -size +0c -print | sort)
printf 'REC_NONEMPTY=%d PARTIAL=%d MISSING=%d\n' "$complete" "$partial" "$missing"
