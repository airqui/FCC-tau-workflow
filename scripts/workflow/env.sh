#!/usr/bin/env bash

# Source this file to load the validated FCC-tau software environment.
_fcc_tau_script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_fcc_tau_resolved_repo="$(cd "$_fcc_tau_script_dir/../.." && pwd)"
if [[ ${FCC_TAU_ENV_LOADED_REPO:-} == "$_fcc_tau_resolved_repo" ]]; then
    unset _fcc_tau_resolved_repo _fcc_tau_script_dir
    return 0 2>/dev/null || exit 0
fi
export FCC_TAU_REPO="${FCC_TAU_REPO:-$_fcc_tau_resolved_repo}"
export FCC_TAU_CAMPAIGN="${FCC_TAU_CAMPAIGN:-ILD20260821_2k}"
export FCC_TAU_DEPENDENCY_ROOT="${FCC_TAU_DEPENDENCY_ROOT:-${XDG_CACHE_HOME:-$HOME/.cache}/fcc-tau-workflow}"
export ILDCONFIG_ROOT="${ILDCONFIG_ROOT:-$FCC_TAU_DEPENDENCY_ROOT/ILDConfig}"
export ILDCONFIG_DIR="${ILDCONFIG_DIR:-$ILDCONFIG_ROOT/StandardConfig/production}"
export KEY4HEP_SETUP="${KEY4HEP_SETUP:-/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2026-08-21/x86_64-almalinux9-gcc14.2.0-opt/key4hep-stack/2026-08-21-5qmpe6/setup.sh}"
export FCC_TAU_DETECTOR_MODEL="${FCC_TAU_DETECTOR_MODEL:-ILD_FCCee_v01}"
export FCC_TAU_GEOMETRY_SHA256="${FCC_TAU_GEOMETRY_SHA256:-ab48a78ef69f6ee417233e34cffa75a0fd41742fb02130c57303f402abd87e29}"

if ! test -r "$KEY4HEP_SETUP"; then
    echo "ERROR: validated Key4hep setup is not readable: $KEY4HEP_SETUP" >&2
    return 1 2>/dev/null || exit 1
fi
_fcc_tau_had_nounset=0
case "$-" in *u*) _fcc_tau_had_nounset=1; set +u ;; esac
# shellcheck disable=SC1090
_fcc_tau_load_key4hep() { source "$KEY4HEP_SETUP"; }
_fcc_tau_load_key4hep || {
    _fcc_tau_setup_status=$?; (( _fcc_tau_had_nounset )) && set -u
    unset -f _fcc_tau_load_key4hep
    return "$_fcc_tau_setup_status" 2>/dev/null || exit "$_fcc_tau_setup_status"
}
unset -f _fcc_tau_load_key4hep
(( _fcc_tau_had_nounset )) && set -u

export COMPACT_FILE="${COMPACT_FILE:-$k4geo_DIR/FCCee/ILD_FCCee/compact/ILD_FCCee_v01/ILD_FCCee_v01.xml}"
test -r "$COMPACT_FILE" || { echo "ERROR: detector compact file is not readable: $COMPACT_FILE" >&2; return 1 2>/dev/null || exit 1; }
_fcc_tau_actual_sha256=$(sha256sum "$COMPACT_FILE" | awk '{print $1}')
[[ "$_fcc_tau_actual_sha256" == "$FCC_TAU_GEOMETRY_SHA256" ]] || {
    echo "ERROR: unexpected geometry SHA-256: $_fcc_tau_actual_sha256" >&2
    return 1 2>/dev/null || exit 1
}
test -d "$ILDCONFIG_ROOT/.git" || {
    echo "ERROR: ILDConfig is unavailable at $ILDCONFIG_ROOT; run bootstrap_ildconfig.sh" >&2
    return 1 2>/dev/null || exit 1
}
[[ "$(git -C "$ILDCONFIG_ROOT" rev-parse HEAD)" == "279b180a88597e45dfaf84f35d1b8b5358300079" ]] || {
    echo "ERROR: ILDConfig is not at the validated commit" >&2
    return 1 2>/dev/null || exit 1
}
export FCC_TAU_ENV_LOADED_REPO="$_fcc_tau_resolved_repo"
unset _fcc_tau_actual_sha256 _fcc_tau_had_nounset _fcc_tau_resolved_repo _fcc_tau_script_dir
