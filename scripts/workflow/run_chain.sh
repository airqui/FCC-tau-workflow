#!/usr/bin/env bash

set -euo pipefail

usage() {
    echo "Uso: $0 [--force] INPUT_FILE [N_EVENTS]" >&2
    echo "N_EVENTS debe ser positivo; para esta campaña el valor por defecto es 2000." >&2
}
fail() { local message="$1" status="${2:-1}"; echo "ERROR: $message" >&2; exit "$status"; }

FORCE=0
if [[ "${1:-}" == "--force" ]]; then FORCE=1; shift; fi
if [[ $# -lt 1 || $# -gt 2 ]]; then usage; exit 2; fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=env.sh
source "$SCRIPT_DIR/env.sh"
: "${FCC_TAU_PRODUCTION:?set FCC_TAU_PRODUCTION to the campaign root}"
export FCC_TAU_OUTPUT="${FCC_TAU_OUTPUT:-$FCC_TAU_PRODUCTION/outputs}"
export FCC_TAU_TMP="${FCC_TAU_TMP:-$FCC_TAU_PRODUCTION/tmp}"
export FCC_TAU_LOG="${FCC_TAU_LOG:-$FCC_TAU_REPO/run/logs/$FCC_TAU_CAMPAIGN}"

INPUT_ARGUMENT="$1"
N_EVENTS="${2:-2000}"
[[ "$N_EVENTS" =~ ^[1-9][0-9]*$ ]] || fail "N_EVENTS debe ser un entero positivo" 3

if [[ "$INPUT_ARGUMENT" = /* ]]; then INPUT_FILE="$INPUT_ARGUMENT"; else : "${FCC_TAU_DATA:?set FCC_TAU_DATA for relative inputs}"; INPUT_FILE="$FCC_TAU_DATA/$INPUT_ARGUMENT"; fi
test -f "$INPUT_FILE" && test -r "$INPUT_FILE" || fail "no se puede leer la entrada: $INPUT_FILE" 10
case "$INPUT_FILE" in *.stdhep|*.stdhep.gz) ;; *) fail "entrada no STDHEP: $INPUT_FILE" 11 ;; esac
INPUT_FILE="$(cd "$(dirname "$INPUT_FILE")" && pwd)/$(basename "$INPUT_FILE")"

INPUT_BASENAME="$(basename "$INPUT_FILE")"
SAMPLE_NAME="${INPUT_BASENAME%.gz}"; SAMPLE_NAME="${SAMPLE_NAME%.stdhep}"
OUTPUT_DIR="$FCC_TAU_OUTPUT/$SAMPLE_NAME"
LOG_DIR="$FCC_TAU_LOG/$SAMPLE_NAME"
SIM_FILE="$OUTPUT_DIR/${SAMPLE_NAME}_SIM.edm4hep.root"
OUTPUT_BASE="$OUTPUT_DIR/$SAMPLE_NAME"
REC_FILE="${OUTPUT_BASE}_REC.edm4hep.root"
LOCK_DIR="$OUTPUT_DIR/.run_chain.lock"
METRICS_FILE="$LOG_DIR/metrics.txt"

mkdir -p "$OUTPUT_DIR" "$LOG_DIR" "$FCC_TAU_TMP"
test -d "$FCC_TAU_TMP" && test -w "$FCC_TAU_TMP" || fail "tmp no escribible: $FCC_TAU_TMP" 13
if ! mkdir "$LOCK_DIR" 2>/dev/null; then fail "ejecucion activa o lock residual: $LOCK_DIR" 22; fi

WORK_DIR=""
cleanup() {
    local status=$?
    [[ -z "$WORK_DIR" ]] || rm -rf -- "$WORK_DIR"
    rmdir "$LOCK_DIR" 2>/dev/null || true
    return "$status"
}
trap cleanup EXIT

if (( ! FORCE )); then
    if test -s "$REC_FILE"; then fail "REC no vacio existente; no se sobrescribe: $REC_FILE" 12
    elif test -e "$REC_FILE"; then fail "REC vacio; requiere revision explicita: $REC_FILE" 17
    elif test -s "$SIM_FILE"; then fail "SIM parcial sin REC; requiere revision explicita: $SIM_FILE" 18
    elif test -e "$SIM_FILE"; then fail "SIM vacio; requiere revision explicita: $SIM_FILE" 19
    fi
fi

RUN_START_EPOCH=$(date +%s)
RUN_START_ISO=$(date --iso-8601=seconds)
FREE_BEFORE=$(df -B1 --output=avail "$FCC_TAU_PRODUCTION" | awk 'NR==2 {print $1}')
INPUT_SIZE=$(stat -c %s "$INPUT_FILE")
{
    echo "campaign=$FCC_TAU_CAMPAIGN"
    echo "start=$RUN_START_ISO"
    echo "input=$INPUT_FILE"
    echo "requested_events=$N_EVENTS"
    echo "input_compressed_bytes=$INPUT_SIZE"
    echo "lustre_free_before_bytes=$FREE_BEFORE"
} > "$METRICS_FILE"

WORK_DIR="$(mktemp -d "$FCC_TAU_TMP/${SAMPLE_NAME}.XXXXXX")"
if [[ "$INPUT_FILE" == *.gz ]]; then
    LOCAL_INPUT="$WORK_DIR/${SAMPLE_NAME}.stdhep"
    echo "Verificando y descomprimiendo temporalmente en Lustre..."
    gzip -t "$INPUT_FILE"
    gzip -cd "$INPUT_FILE" > "$LOCAL_INPUT"
else
    LOCAL_INPUT="$INPUT_FILE"
fi
test -s "$LOCAL_INPUT" || fail "STDHEP vacio: $LOCAL_INPUT" 14
echo "input_uncompressed_bytes=$(stat -c %s "$LOCAL_INPUT")" >> "$METRICS_FILE"
test -r "$ILDCONFIG_DIR/ddsim_steer.py" || fail "falta ddsim_steer.py" 15
test -r "$ILDCONFIG_DIR/ILDReconstruction.py" || fail "falta ILDReconstruction.py" 16

{
    echo "Fecha: $RUN_START_ISO"; echo "Host: $(hostname)"; echo "Campaña: $FCC_TAU_CAMPAIGN"
    echo "Entrada: $INPUT_FILE"; echo "STDHEP usado: $LOCAL_INPUT"; echo "Eventos: $N_EVENTS"
    echo "Geometria: $COMPACT_FILE"; echo "Modelo: $FCC_TAU_DETECTOR_MODEL"; echo "ILDConfig: $ILDCONFIG_DIR"
} | tee "$LOG_DIR/run_information.txt"

if (( FORCE )); then rm -f -- "$SIM_FILE" "$REC_FILE"; fi
TIME_COMMAND=()
if test -x /usr/bin/time; then TIME_COMMAND=(/usr/bin/time -v); fi

cd "$ILDCONFIG_DIR"
echo "=== Simulacion DD4hep ==="
DDSIM_START=$(date +%s)
set +e
if (( ${#TIME_COMMAND[@]} )); then
    "${TIME_COMMAND[@]}" -o "$LOG_DIR/ddsim.time" ddsim --steeringFile ddsim_steer.py \
        --compactFile "$COMPACT_FILE" --inputFiles "$LOCAL_INPUT" --outputFile "$SIM_FILE" \
        --numberOfEvents "$N_EVENTS" --crossingAngleBoost 15.e-3 2>&1 | tee "$LOG_DIR/ddsim.log"
else
    ddsim --steeringFile ddsim_steer.py --compactFile "$COMPACT_FILE" --inputFiles "$LOCAL_INPUT" \
        --outputFile "$SIM_FILE" --numberOfEvents "$N_EVENTS" --crossingAngleBoost 15.e-3 2>&1 | tee "$LOG_DIR/ddsim.log"
fi
DDSIM_STATUS=${PIPESTATUS[0]}
set -e
DDSIM_END=$(date +%s)
printf 'ddsim_exit_code=%d\nddsim_wall_seconds=%d\n' "$DDSIM_STATUS" "$((DDSIM_END-DDSIM_START))" >> "$METRICS_FILE"
(( DDSIM_STATUS == 0 )) || fail "ddsim fallo con codigo $DDSIM_STATUS" "$DDSIM_STATUS"
test -s "$SIM_FILE" || fail "SIM ausente o vacio: $SIM_FILE" 20
echo "sim_bytes=$(stat -c %s "$SIM_FILE")" >> "$METRICS_FILE"

echo "=== Reconstruccion ILD ==="
RECO_START=$(date +%s)
set +e
if (( ${#TIME_COMMAND[@]} )); then
    "${TIME_COMMAND[@]}" -o "$LOG_DIR/reconstruction.time" k4run ILDReconstruction.py \
        --detectorModel="$FCC_TAU_DETECTOR_MODEL" --inputFiles="$SIM_FILE" \
        --outputFileBase="$OUTPUT_BASE" --num-events=-1 2>&1 | tee "$LOG_DIR/reconstruction.log"
else
    k4run ILDReconstruction.py --detectorModel="$FCC_TAU_DETECTOR_MODEL" --inputFiles="$SIM_FILE" \
        --outputFileBase="$OUTPUT_BASE" --num-events=-1 2>&1 | tee "$LOG_DIR/reconstruction.log"
fi
RECO_STATUS=${PIPESTATUS[0]}
set -e
RECO_END=$(date +%s)
printf 'reconstruction_exit_code=%d\nreconstruction_wall_seconds=%d\n' "$RECO_STATUS" "$((RECO_END-RECO_START))" >> "$METRICS_FILE"
(( RECO_STATUS == 0 )) || fail "reconstruccion fallo con codigo $RECO_STATUS" "$RECO_STATUS"
test -s "$REC_FILE" || fail "REC ausente o vacio: $REC_FILE" 21

RUN_END_ISO=$(date --iso-8601=seconds)
FREE_AFTER=$(df -B1 --output=avail "$FCC_TAU_PRODUCTION" | awk 'NR==2 {print $1}')
{
    echo "end=$RUN_END_ISO"; echo "total_wall_seconds=$(( $(date +%s)-RUN_START_EPOCH ))"
    echo "rec_bytes=$(stat -c %s "$REC_FILE")"; echo "lustre_free_after_bytes=$FREE_AFTER"
    for suffix in AIDA.root PfoAnalysis.root; do
        product="${OUTPUT_BASE}_${suffix}"
        if test -e "$product"; then echo "${suffix%%.*}_bytes=$(stat -c %s "$product")"; else echo "${suffix%%.*}_bytes=absent"; fi
    done
} >> "$METRICS_FILE"

echo "Cadena completada."
echo "SIM: $SIM_FILE"; echo "REC: $REC_FILE"; echo "Logs: $LOG_DIR"; echo "Metricas: $METRICS_FILE"
