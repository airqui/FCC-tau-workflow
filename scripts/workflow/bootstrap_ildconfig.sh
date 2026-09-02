#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
expected_commit=$(<"$repo_root/configs/detector/ILDConfig.commit")
dependency_root="${FCC_TAU_DEPENDENCY_ROOT:-${XDG_CACHE_HOME:-$HOME/.cache}/fcc-tau-workflow}"
ildconfig_root="${ILDCONFIG_ROOT:-$dependency_root/ILDConfig}"
ildconfig_url="${ILDCONFIG_URL:-https://github.com/iLCSoft/ILDConfig.git}"

if test -e "$ildconfig_root" && ! test -d "$ildconfig_root/.git"; then
    echo "ERROR: refusing non-Git ILDConfig path: $ildconfig_root" >&2
    exit 2
fi
mkdir -p "$(dirname "$ildconfig_root")"
if ! test -d "$ildconfig_root/.git"; then
    git clone "$ildconfig_url" "$ildconfig_root"
fi
git -C "$ildconfig_root" fetch origin "$expected_commit"
git -C "$ildconfig_root" checkout --detach "$expected_commit"
actual_commit=$(git -C "$ildconfig_root" rev-parse HEAD)
[[ "$actual_commit" == "$expected_commit" ]] || { echo "ERROR: ILDConfig commit mismatch" >&2; exit 3; }
test -r "$ildconfig_root/StandardConfig/production/ddsim_steer.py"
test -r "$ildconfig_root/StandardConfig/production/ILDReconstruction.py"
printf 'ILDConfig ready: %s at %s\n' "$actual_commit" "$ildconfig_root"
