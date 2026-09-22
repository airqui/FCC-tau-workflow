#!/usr/bin/env python3
"""Fail-closed orchestration for a future FCC-tau TrackMerger B benchmark.

The default behavior is informational. Reconstruction, assignment extraction,
and analysis each require a stage-specific --execute-* option. Frozen A is
always an input and is never reconstructed by this driver.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
from typing import Iterable


REPO = Path(__file__).resolve().parents[2]
FROZEN_SIM = Path(
    "/lustre/ific.uv.es/prj/gl/abehep.flc/FCC/ILD20260821_2k/outputs/"
    "events_000242385/events_000242385_SIM.edm4hep.root"
)
FROZEN_SIM_SHA256 = "1f8adc41bf67f68cd981206abd23bf7d4b8e4a6d6aefa1d3ebb810f1215db5cc"
FROZEN_A_REC = Path(
    "/lustre/ific.uv.es/prj/gl/abehep.flc/FCC/TrackMerger_Pandora_AB/"
    "nightly_20260916/benchmark2000/A/"
    "events_000242385_A_MarlinTrkTracks_REC.edm4hep.root"
)
FROZEN_A_REC_SHA256 = "c86ac1eda781c206ee3ec29c0e37caf5d8c93d81a83b866db1860a61d433257d"
FROZEN_A_DIRECT = Path(
    "/lhome/ific/a/airqui/FCC/trackmerger_pandora_ab/audit/benchmark2000/A/direct.parquet"
)
FROZEN_A_ANCESTOR = Path(
    "/lhome/ific/a/airqui/FCC/trackmerger_pandora_ab/audit/benchmark2000/A/ancestor.parquet"
)
FROZEN_K4REC_SHA = "5b048492ebd0a5b780c012854be14be79d497b2d"
FROZEN_ILDCONFIG_SHA = "a0b43f645e0c27f356d82a37ed0b3f67840f3895"
FROZEN_ANALYSIS_COMMIT = "a85f4fae5666089562ca3dafe25a81d99381db93"
FROZEN_ANALYSIS_SCRIPT_SHA256 = "c25254878e1d51c2b0835052aea621c83ddd02bc9f89fdaa88048f19aeba211e"
SOURCE_FILE_ID = "000242385"
DETECTOR = "ILD_FCCee_v01"
CMS_ENERGY_GEV = 91
FULL_EVENTS = 2000
FAMILIES = ("part12", "part3", "part3b", "part4", "photon_diagnostic", "performance")
ILD_SENTINEL_PATHS = (
    "StandardConfig/production/ILDReconstruction.py",
    "StandardConfig/production/Tracking/TrackMerging_FCCee.py",
    "StandardConfig/production/Tracking/TrackingReco_FCCeeMDI.py",
    "StandardConfig/production/ParticleFlow/PandoraPFA.py",
    "StandardConfig/production/HighLevelReco/HighLevelReco_FCCee.py",
)
REQUIRED_CONFIG = (
    "BENCHMARK_LABEL",
    "KEY4HEP_NIGHTLY",
    "KEY4HEP_SETUP",
    "K4RECTRACKER_SOURCE",
    "K4RECTRACKER_COMMIT",
    "TRACKMERGER_CPP_SHA256",
    "ILDCONFIG_SOURCE",
    "ILDCONFIG_COMMIT",
    "TRACK_COLLECTION",
    "TRACK_TRUTH_LINK_COLLECTION",
    "B_SMOKE_STEERING",
    "B_FULL_STEERING",
    "B_PANDORA_CONFIG",
    "B_HIGHLEVEL_CONFIG",
    "RECONSTRUCTION_WORKDIR",
    "SMOKE_EVENTS",
    "SMOKE_EVENT_ARGS",
    "FULL_EVENT_ARGS",
    "B_OUTPUT_ROOT",
    "TAUSFCCEE_REPO",
    "FROZEN_ANALYSIS_CONFIG",
)


class StopError(RuntimeError):
    """A deliberate fail-closed stop."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_config(path: Path, *, allow_placeholders: bool = False) -> dict[str, str]:
    if not path.is_file():
        raise StopError(f"configuration is missing: {path}")
    values: dict[str, str] = {}
    for number, raw in enumerate(path.read_text().splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            raise StopError(f"{path}:{number}: expected KEY=VALUE")
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", key):
            raise StopError(f"{path}:{number}: invalid key {key!r}")
        if key in values:
            raise StopError(f"{path}:{number}: duplicate key {key}")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key] = value
    empty_allowed = {"SMOKE_EVENT_ARGS", "FULL_EVENT_ARGS"}
    missing = [
        key for key in REQUIRED_CONFIG
        if key not in values or (not values[key] and key not in empty_allowed)
    ]
    if missing:
        raise StopError("missing required configuration keys: " + ", ".join(missing))
    if not allow_placeholders:
        placeholders = [key for key, value in values.items() if "<" in value or ">" in value]
        if placeholders:
            raise StopError("replace placeholder values before use: " + ", ".join(placeholders))
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", values["BENCHMARK_LABEL"]):
        raise StopError("BENCHMARK_LABEL must contain only letters, digits, dot, underscore, or hyphen")
    if not allow_placeholders:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", values["TRACK_COLLECTION"]):
            raise StopError("TRACK_COLLECTION is not a valid collection identifier")
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", values["TRACK_TRUTH_LINK_COLLECTION"]):
            raise StopError("TRACK_TRUTH_LINK_COLLECTION is not a valid collection identifier")
    try:
        smoke_events = int(values["SMOKE_EVENTS"])
    except ValueError as exc:
        raise StopError("SMOKE_EVENTS must be an integer") from exc
    if not 0 < smoke_events < FULL_EVENTS:
        raise StopError(f"SMOKE_EVENTS must be between 1 and {FULL_EVENTS - 1}")
    return values


def config_sha256(path: Path) -> str:
    return sha256(path)


def slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_")


def derived(cfg: dict[str, str]) -> dict[str, Path | str | int]:
    label = slug(cfg["BENCHMARK_LABEL"])
    collection = slug(cfg["TRACK_COLLECTION"])
    root = Path(cfg["B_OUTPUT_ROOT"]).expanduser().resolve(strict=False)
    smoke_base = root / "smoke" / f"events_{SOURCE_FILE_ID}_{label}_B_{collection}_smoke"
    full_base = root / "full" / f"events_{SOURCE_FILE_ID}_{label}_B_{collection}"
    return {
        "label": label,
        "root": root,
        "smoke_base": smoke_base,
        "smoke_rec": Path(f"{smoke_base}_REC.edm4hep.root"),
        "full_base": full_base,
        "full_rec": Path(f"{full_base}_REC.edm4hep.root"),
        "smoke_assign": root / "smoke" / "assignments",
        "full_assign": root / "full" / "assignments",
        "smoke_gate": root / "smoke" / "validation" / "smoke_gate.json",
        "analysis_config": root / "analysis" / "comparison_config.candidate.yaml",
        "analysis_results": root / "analysis" / "results",
        "registry_candidate": root / "summary" / "trackmerger_benchmark_candidate.csv",
        "smoke_events": int(cfg["SMOKE_EVENTS"]),
    }


def shell_display(setup: Path, cwd: Path, command: Iterable[str], python_prefix: str = "") -> str:
    lines = [f"source {shlex.quote(str(setup))}"]
    if python_prefix:
        lines.append(f"export PYTHONPATH={shlex.quote(python_prefix)}${{PYTHONPATH:+:$PYTHONPATH}}")
    lines.append(f"cd {shlex.quote(str(cwd))}")
    lines.append(shlex.join([str(part) for part in command]))
    return "\n".join(lines)


def run_in_setup(
    setup: Path,
    cwd: Path,
    command: list[str],
    log_path: Path,
    exit_path: Path,
    *,
    python_prefix: str = "",
) -> None:
    for path in (log_path, exit_path):
        if path.exists():
            raise StopError(f"refusing to overwrite: {path}")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    wrapper = (
        'source "$1"; shift; '
        'if [[ -n "$1" ]]; then export PYTHONPATH="$1${PYTHONPATH:+:$PYTHONPATH}"; fi; shift; '
        'cd "$1"; shift; exec "$@"'
    )
    with log_path.open("xb") as log:
        result = subprocess.run(
            ["bash", "--noprofile", "--norc", "-c", wrapper, "bash", str(setup), python_prefix, str(cwd), *command],
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )
    exit_path.write_text(f"{result.returncode}\n")
    if result.returncode:
        raise StopError(f"command failed with exit {result.returncode}; see {log_path}")


def git_output(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], text=True, capture_output=True, check=False)
    if result.returncode:
        raise StopError(result.stderr.strip() or f"git {' '.join(args)} failed in {repo}")
    return result.stdout.strip()


def require_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise StopError(f"{label} is missing: {path}")


def require_hash(path: Path, expected: str, label: str) -> None:
    require_file(path, label)
    actual = sha256(path)
    if actual != expected:
        raise StopError(f"{label} SHA256 mismatch: expected {expected}, got {actual}")


def require_commit(repo: Path, expected: str, label: str) -> None:
    actual = git_output(repo, "rev-parse", "HEAD")
    if actual != expected:
        raise StopError(f"{label} HEAD mismatch: expected {expected}, got {actual}")


def require_event_control(steering: Path, args_value: str, expected: int, label: str) -> None:
    args = shlex.split(args_value)
    text = steering.read_text(errors="replace")
    args_have_limit = str(expected) in args and any("event" in item.lower() for item in args)
    literal_limit = re.search(rf"\bEvtMax\s*=\s*{expected}\b", text) is not None
    if not (args_have_limit or literal_limit):
        raise StopError(
            f"{label} does not visibly constrain the run to {expected} events; "
            "set explicit event arguments or use a reviewed steering with that EvtMax"
        )


def require_wiring(cfg: dict[str, str]) -> None:
    pandora = Path(cfg["B_PANDORA_CONFIG"])
    highlevel = Path(cfg["B_HIGHLEVEL_CONFIG"])
    require_file(pandora, "B Pandora configuration")
    require_file(highlevel, "B high-level configuration")
    ptext = pandora.read_text(errors="replace")
    htext = highlevel.read_text(errors="replace")
    required_pandora = (cfg["TRACK_COLLECTION"], cfg["TRACK_TRUTH_LINK_COLLECTION"])
    required_high = (
        cfg["TRACK_COLLECTION"],
        cfg["TRACK_TRUTH_LINK_COLLECTION"],
        "RecoMCTruthLink",
        "MCTruthRecoLink",
        "FullRecoRelation",
        "true",
    )
    missing_p = [token for token in required_pandora if token not in ptext]
    missing_h = [token for token in required_high if token not in htext]
    if missing_p or missing_h:
        raise StopError(f"B wiring text check failed: Pandora missing {missing_p}; HighLevelReco missing {missing_h}")


def ensure_b_only_root(root: Path) -> None:
    frozen_a_dir = FROZEN_A_REC.resolve(strict=False).parent
    root = root.resolve(strict=False)
    if root == frozen_a_dir or root in frozen_a_dir.parents or frozen_a_dir in root.parents:
        raise StopError(f"B_OUTPUT_ROOT overlaps the frozen A location: {root}")


def run_preflight(cfg: dict[str, str], cfg_path: Path) -> dict:
    paths = derived(cfg)
    setup = Path(cfg["KEY4HEP_SETUP"])
    require_file(setup, "Key4hep setup")
    k4repo = Path(cfg["K4RECTRACKER_SOURCE"])
    ildrepo = Path(cfg["ILDCONFIG_SOURCE"])
    require_commit(k4repo, cfg["K4RECTRACKER_COMMIT"], "k4RecTracker")
    require_commit(ildrepo, cfg["ILDCONFIG_COMMIT"], "ILDConfig")
    if not re.fullmatch(r"[0-9a-f]{40}", cfg["K4RECTRACKER_COMMIT"]):
        raise StopError("K4RECTRACKER_COMMIT must be a full 40-character SHA")
    if not re.fullmatch(r"[0-9a-f]{40}", cfg["ILDCONFIG_COMMIT"]):
        raise StopError("ILDCONFIG_COMMIT must be a full 40-character SHA")
    trackmerger = k4repo / "Tracking/components/TrackMerger.cpp"
    require_hash(trackmerger, cfg["TRACKMERGER_CPP_SHA256"], "TrackMerger.cpp")
    for path in ILD_SENTINEL_PATHS:
        require_file(ildrepo / path, f"native ILDConfig path {path}")
    smoke_steering = Path(cfg["B_SMOKE_STEERING"])
    full_steering = Path(cfg["B_FULL_STEERING"])
    require_file(smoke_steering, "B smoke steering")
    require_file(full_steering, "B full steering")
    require_file(Path(cfg["RECONSTRUCTION_WORKDIR"]) / "py_utils.py", "ILDConfig py_utils.py")
    require_event_control(smoke_steering, cfg["SMOKE_EVENT_ARGS"], int(cfg["SMOKE_EVENTS"]), "smoke steering")
    require_event_control(full_steering, cfg["FULL_EVENT_ARGS"], FULL_EVENTS, "full steering")
    require_wiring(cfg)
    require_hash(FROZEN_SIM, FROZEN_SIM_SHA256, "frozen SIM")
    require_hash(FROZEN_A_REC, FROZEN_A_REC_SHA256, "frozen A REC")
    require_file(FROZEN_A_DIRECT, "frozen A L_direct")
    require_file(FROZEN_A_ANCESTOR, "frozen A L_ancestor")
    taus = Path(cfg["TAUSFCCEE_REPO"])
    require_commit(taus, FROZEN_ANALYSIS_COMMIT, "TausFCCee")
    analysis_script = taus / "scripts/analysis/build_mc_comparison.py"
    require_hash(analysis_script, FROZEN_ANALYSIS_SCRIPT_SHA256, "maintained analysis script")
    require_file(Path(cfg["FROZEN_ANALYSIS_CONFIG"]), "frozen benchmark-v1 analysis config")
    ensure_b_only_root(paths["root"])
    k4_log = git_output(
        k4repo, "log", "--oneline", f"{FROZEN_K4REC_SHA}..{cfg['K4RECTRACKER_COMMIT']}", "--",
        "Tracking/components/TrackMerger.cpp",
    )
    k4_diff = git_output(
        k4repo, "diff", "--stat", f"{FROZEN_K4REC_SHA}..{cfg['K4RECTRACKER_COMMIT']}", "--",
        "Tracking/components/TrackMerger.cpp",
    )
    ild_log = git_output(
        ildrepo, "log", "--oneline", f"{FROZEN_ILDCONFIG_SHA}..{cfg['ILDCONFIG_COMMIT']}", "--",
        *ILD_SENTINEL_PATHS,
    )
    ild_diff = git_output(
        ildrepo, "diff", "--stat", f"{FROZEN_ILDCONFIG_SHA}..{cfg['ILDCONFIG_COMMIT']}", "--",
        *ILD_SENTINEL_PATHS,
    )
    return {
        "status": "PASS",
        "benchmark_label": cfg["BENCHMARK_LABEL"],
        "config": str(cfg_path.resolve()),
        "config_sha256": config_sha256(cfg_path),
        "nightly": cfg["KEY4HEP_NIGHTLY"],
        "key4hep_setup": str(setup.resolve()),
        "k4rectracker_commit": cfg["K4RECTRACKER_COMMIT"],
        "trackmerger_cpp_sha256": cfg["TRACKMERGER_CPP_SHA256"],
        "ildconfig_commit": cfg["ILDCONFIG_COMMIT"],
        "track_collection": cfg["TRACK_COLLECTION"],
        "track_truth_link_collection": cfg["TRACK_TRUTH_LINK_COLLECTION"],
        "frozen_sim_sha256": FROZEN_SIM_SHA256,
        "frozen_a_rec_sha256": FROZEN_A_REC_SHA256,
        "output_root": str(paths["root"]),
        "sentinel": {
            "trackmerger_log": k4_log,
            "trackmerger_diff_stat": k4_diff,
            "ildconfig_log": ild_log,
            "ildconfig_diff_stat": ild_diff,
        },
    }


def reconstruction_command(cfg: dict[str, str], scope: str) -> list[str]:
    paths = derived(cfg)
    steering_key = "B_SMOKE_STEERING" if scope == "smoke" else "B_FULL_STEERING"
    args_key = "SMOKE_EVENT_ARGS" if scope == "smoke" else "FULL_EVENT_ARGS"
    base = paths[f"{scope}_base"]
    return [
        "k4run", cfg[steering_key],
        "--inputFiles", str(FROZEN_SIM),
        "--outputFileBase", str(base),
        "--detectorModel", DETECTOR,
        "--cmsEnergy", str(CMS_ENERGY_GEV),
        "--trackMerge", "--noBeamCalReco", "--noAIDA",
        *shlex.split(cfg[args_key]),
    ]


def assignment_paths(cfg: dict[str, str], scope: str) -> dict[str, Path]:
    paths = derived(cfg)
    root = paths[f"{scope}_assign"]
    return {
        "root": root,
        "direct": root / "direct.parquet",
        "candidates": root / "candidates.parquet",
        "direct_summary": root / "direct_summary.json",
        "ancestor": root / "ancestor.parquet",
        "ancestor_summary": root / "ancestor_summary.json",
    }


def assignment_commands(cfg: dict[str, str], scope: str) -> tuple[list[str], list[str]]:
    paths = derived(cfg)
    outputs = assignment_paths(cfg, scope)
    rec = paths[f"{scope}_rec"]
    events = int(cfg["SMOKE_EVENTS"]) if scope == "smoke" else FULL_EVENTS
    sample = f"W_TM_{paths['label']}_{scope.upper()}"
    direct = [
        "python", str(REPO / "scripts/workflow/extract_truthlink_assignments.py"),
        "--linked-rec", str(rec), "--source-rec", str(rec),
        "--source-file-id", SOURCE_FILE_ID,
        "--relation-collection", "RecoMCTruthLink",
        "--expected-events", str(events),
        "--assignment-output", str(outputs["direct"]),
        "--candidate-output", str(outputs["candidates"]),
        "--summary-output", str(outputs["direct_summary"]),
    ]
    ancestor = [
        "python", str(REPO / "scripts/workflow/extract_lancestor_assignments.py"),
        "--sample", sample, "--source-file-id", SOURCE_FILE_ID,
        "--source-rec", str(rec), "--direct-assignment", str(outputs["direct"]),
        "--ancestor-output", str(outputs["ancestor"]),
        "--summary-output", str(outputs["ancestor_summary"]),
        "--expected-events", str(events),
    ]
    return direct, ancestor


def require_smoke_gate(cfg: dict[str, str], cfg_path: Path) -> dict:
    gate_path = derived(cfg)["smoke_gate"]
    if not gate_path.is_file():
        raise StopError("STOP: full benchmark not authorized by smoke gate")
    gate = json.loads(gate_path.read_text())
    if gate.get("status") != "PASS" or gate.get("config_sha256") != config_sha256(cfg_path):
        raise StopError("STOP: full benchmark not authorized by smoke gate")
    return gate


def relation_endpoints(relation):
    if hasattr(relation, "getFrom") and hasattr(relation, "getTo"):
        return relation.getFrom(), relation.getTo()
    if hasattr(relation, "getRec") and hasattr(relation, "getSim"):
        return relation.getRec(), relation.getSim()
    raise StopError(f"unsupported relation type: {type(relation).__name__}")


def object_id(value) -> tuple[int, int]:
    oid = value.getObjectID()
    return int(oid.collectionID), int(oid.index)


def available(value) -> bool:
    return value is not None and (not hasattr(value, "isAvailable") or value.isAvailable())


def internal_validate_smoke(cfg: dict[str, str], cfg_path: Path) -> None:
    try:
        import podio.root_io as root_io
    except ImportError as exc:
        raise StopError("podio is unavailable after sourcing the configured Key4hep setup") from exc
    paths = derived(cfg)
    rec = paths["smoke_rec"]
    direct_summary_path = assignment_paths(cfg, "smoke")["direct_summary"]
    require_file(rec, "smoke REC")
    require_file(direct_summary_path, "smoke L_direct summary")
    exit_path = paths["root"] / "smoke" / "logs" / "reconstruction.exit"
    require_file(exit_path, "smoke reconstruction exit status")
    job_exit = int(exit_path.read_text().strip())
    totals = {
        "events": 0,
        "pandora_pfos": 0,
        "pfo_track_references": 0,
        "pfo_cluster_references": 0,
        "invalid_pfo_track_references": 0,
        "invalid_pfo_cluster_references": 0,
        "invalid_pfo_truth_references": 0,
        "invalid_inverse_truth_references": 0,
        "tracked_pfos_without_usable_track_truth": 0,
        "unexpected_track_collection_references": 0,
    }
    required = {
        cfg["TRACK_COLLECTION"], "PandoraClusters", "PandoraPFOs",
        cfg["TRACK_TRUTH_LINK_COLLECTION"], "RecoMCTruthLink", "MCTruthRecoLink",
    }
    for event_index, event in enumerate(root_io.Reader(str(rec)).get("events")):
        names = set(event.getAvailableCollections())
        missing = required - names
        if missing:
            raise StopError(f"smoke event {event_index}: missing collections {sorted(missing)}")
        tracks = event.get(cfg["TRACK_COLLECTION"])
        clusters = event.get("PandoraClusters")
        pfos = event.get("PandoraPFOs")
        track_ids = {object_id(value) for value in tracks}
        cluster_ids = {object_id(value) for value in clusters}
        linked_track_ids = set()
        for relation in event.get(cfg["TRACK_TRUTH_LINK_COLLECTION"]):
            first, second = relation_endpoints(relation)
            if available(first) and available(second):
                first_id = object_id(first)
                second_id = object_id(second)
                if first_id in track_ids:
                    linked_track_ids.add(first_id)
                elif second_id in track_ids:
                    linked_track_ids.add(second_id)
        for pfo in pfos:
            pfo_tracks = list(pfo.getTracks())
            if pfo_tracks and any(not available(track) or object_id(track) not in linked_track_ids for track in pfo_tracks):
                totals["tracked_pfos_without_usable_track_truth"] += 1
            for track in pfo_tracks:
                totals["pfo_track_references"] += 1
                if not available(track):
                    totals["invalid_pfo_track_references"] += 1
                elif object_id(track) not in track_ids:
                    totals["unexpected_track_collection_references"] += 1
            for cluster in pfo.getClusters():
                totals["pfo_cluster_references"] += 1
                if not available(cluster) or object_id(cluster) not in cluster_ids:
                    totals["invalid_pfo_cluster_references"] += 1
        pfo_ids = {object_id(value) for value in pfos}
        for relation in event.get("RecoMCTruthLink"):
            first, second = relation_endpoints(relation)
            if not available(first) or not available(second) or (object_id(first) not in pfo_ids and object_id(second) not in pfo_ids):
                totals["invalid_pfo_truth_references"] += 1
        for relation in event.get("MCTruthRecoLink"):
            first, second = relation_endpoints(relation)
            if not available(first) or not available(second) or (object_id(first) not in pfo_ids and object_id(second) not in pfo_ids):
                totals["invalid_inverse_truth_references"] += 1
        totals["events"] += 1
        totals["pandora_pfos"] += len(pfos)
    direct = json.loads(direct_summary_path.read_text())
    require_wiring(cfg)
    checks = {
        "job_exit_zero": job_exit == 0,
        "expected_events": totals["events"] == int(cfg["SMOKE_EVENTS"]),
        "track_collection_present": totals["events"] > 0,
        "pandora_pfos_present": totals["pandora_pfos"] > 0,
        "pfo_track_references_valid": totals["invalid_pfo_track_references"] == 0,
        "pfo_cluster_references_valid": totals["invalid_pfo_cluster_references"] == 0,
        "pfo_truth_references_valid": totals["invalid_pfo_truth_references"] == 0,
        "inverse_truth_references_valid": totals["invalid_inverse_truth_references"] == 0,
        "tracked_pfos_have_usable_truth": totals["tracked_pfos_without_usable_track_truth"] == 0,
        "pandora_uses_configured_track_collection": totals["unexpected_track_collection_references"] == 0,
        "track_maxT_nonzero": int(direct.get("track_branch_used", 0)) > 0,
        "assignment_references_valid": int(direct.get("invalid_mc_or_pfo_references", -1)) == 0,
        "assignment_event_count": int(direct.get("n_events", -1)) == int(cfg["SMOKE_EVENTS"]),
        "assignment_relation_collection": direct.get("relation_collection") == "RecoMCTruthLink",
        "static_pandora_linker_wiring_match": True,
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    gate = {
        "status": status,
        "benchmark_label": cfg["BENCHMARK_LABEL"],
        "config_sha256": config_sha256(cfg_path),
        "track_collection": cfg["TRACK_COLLECTION"],
        "track_truth_link_collection": cfg["TRACK_TRUTH_LINK_COLLECTION"],
        "smoke_rec": str(rec),
        "checks": checks,
        "totals": totals,
        "direct_summary": str(direct_summary_path),
        "track_maxT": int(direct.get("track_branch_used", 0)),
    }
    gate_path = paths["smoke_gate"]
    if gate_path.exists():
        raise StopError(f"refusing to overwrite smoke gate: {gate_path}")
    gate_path.parent.mkdir(parents=True, exist_ok=True)
    gate_path.write_text(json.dumps(gate, indent=2, sort_keys=True) + "\n")
    print(json.dumps(gate, indent=2, sort_keys=True))
    if status != "PASS":
        raise StopError("STOP: full benchmark not authorized by smoke gate")


def prepare_analysis_config(cfg: dict[str, str]) -> Path:
    paths = derived(cfg)
    source = Path(cfg["FROZEN_ANALYSIS_CONFIG"])
    require_file(source, "frozen analysis config")
    target = paths["analysis_config"]
    if target.exists():
        raise StopError(f"refusing to overwrite candidate analysis config: {target}")
    text = source.read_text()
    comparison_old = "  trackmerger_pandora_ab_2000:"
    marker = "      - internal_name: W_TM_AB_B\n"
    if text.count(comparison_old) != 1 or text.count(marker) != 1:
        raise StopError("frozen config structure is not the expected benchmark-v1 structure")
    comparison_new = f"  {paths['label']}:"
    prefix, block = text.replace(comparison_old, comparison_new, 1).split(marker, 1)
    replacements = {
        "        presentation_label: B — RefittedGreedyMergedTracks":
            f"        presentation_label: B {cfg['BENCHMARK_LABEL']} — {cfg['TRACK_COLLECTION']}",
        "        rec: /lustre/ific.uv.es/prj/gl/abehep.flc/FCC/TrackMerger_Pandora_AB/nightly_20260916/benchmark2000/B/events_000242385_B_RefittedGreedyMergedTracks_REC.edm4hep.root":
            f"        rec: {paths['full_rec']}",
        "        direct: /lhome/ific/a/airqui/FCC/trackmerger_pandora_ab/audit/benchmark2000/B/direct.parquet":
            f"        direct: {assignment_paths(cfg, 'full')['direct']}",
        "        ancestor: /lhome/ific/a/airqui/FCC/trackmerger_pandora_ab/audit/benchmark2000/B/ancestor.parquet":
            f"        ancestor: {assignment_paths(cfg, 'full')['ancestor']}",
        "        provenance: authoritative B; RefittedGreedyMergedTracks to Pandora and repaired equivalent primary truth linker":
            f"        provenance: candidate B {cfg['BENCHMARK_LABEL']}; {cfg['TRACK_COLLECTION']} to Pandora and equivalent primary truth linker",
    }
    for old, new in replacements.items():
        if block.count(old) != 1:
            raise StopError(f"frozen B config field was not uniquely found: {old}")
        block = block.replace(old, new, 1)
    block = block.replace("        internal_name: W_TM_AB_B", f"        internal_name: W_TM_{paths['label']}", 1)
    candidate = prefix + f"      - internal_name: W_TM_{paths['label']}\n" + block
    if candidate.split("comparisons:\n", 1)[0] != text.split("comparisons:\n", 1)[0]:
        raise StopError("scientific contract changed while preparing analysis config")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(candidate)
    return target


def analysis_command(cfg: dict[str, str], reviewed_config: Path) -> list[str]:
    paths = derived(cfg)
    return [
        "python", "scripts/analysis/build_mc_comparison.py",
        "--comparison", str(paths["label"]),
        "--config", str(reviewed_config),
        "--output-root", str(paths["analysis_results"]),
        "--families", *FAMILIES,
    ]


def validate_reviewed_analysis_config(cfg: dict[str, str], path: Path) -> None:
    require_file(path, "reviewed analysis config")
    frozen = Path(cfg["FROZEN_ANALYSIS_CONFIG"]).read_text()
    candidate = path.read_text()
    if frozen.split("comparisons:\n", 1)[0] != candidate.split("comparisons:\n", 1)[0]:
        raise StopError("reviewed analysis config changes the frozen scientific/performance contract")
    for required in (str(FROZEN_A_REC), str(FROZEN_A_DIRECT), str(FROZEN_A_ANCESTOR), str(derived(cfg)["full_rec"])):
        if required not in candidate:
            raise StopError(f"reviewed analysis config is missing required frozen/new product: {required}")


def create_registry_candidate(cfg: dict[str, str]) -> Path:
    paths = derived(cfg)
    target = paths["registry_candidate"]
    if target.exists():
        raise StopError(f"refusing to overwrite registry candidate: {target}")
    require_file(paths["full_rec"], "full B REC")
    analysis_summary = paths["analysis_results"] / "summary/benchmark_summary.json"
    require_file(analysis_summary, "reviewed analysis summary")
    fieldnames = [
        "benchmark_version", "status", "nightly", "k4rectracker_sha", "trackmerger_cpp_sha256",
        "ildconfig_sha", "sim_path", "sim_sha256", "events", "detector", "cms_energy_gev",
        "a_reference_version", "a_rec_path", "a_rec_sha256", "b_rec_path", "b_rec_sha256",
        "analysis_commit", "analysis_script_sha256", "b_combined_charged_efficiency_percent",
        "b_tpc_covered_combined_charged_efficiency_percent", "authoritative_summary_path",
    ]
    row = {
        "benchmark_version": cfg["BENCHMARK_LABEL"],
        "status": "CANDIDATE_REVIEW_REQUIRED",
        "nightly": cfg["KEY4HEP_NIGHTLY"],
        "k4rectracker_sha": cfg["K4RECTRACKER_COMMIT"],
        "trackmerger_cpp_sha256": cfg["TRACKMERGER_CPP_SHA256"],
        "ildconfig_sha": cfg["ILDCONFIG_COMMIT"],
        "sim_path": str(FROZEN_SIM), "sim_sha256": FROZEN_SIM_SHA256,
        "events": str(FULL_EVENTS), "detector": DETECTOR, "cms_energy_gev": str(CMS_ENERGY_GEV),
        "a_reference_version": "frozen_A_v1", "a_rec_path": str(FROZEN_A_REC),
        "a_rec_sha256": FROZEN_A_REC_SHA256, "b_rec_path": str(paths["full_rec"]),
        "b_rec_sha256": sha256(paths["full_rec"]), "analysis_commit": FROZEN_ANALYSIS_COMMIT,
        "analysis_script_sha256": FROZEN_ANALYSIS_SCRIPT_SHA256,
        "b_combined_charged_efficiency_percent": "REVIEW_REQUIRED",
        "b_tpc_covered_combined_charged_efficiency_percent": "REVIEW_REQUIRED",
        "authoritative_summary_path": str(analysis_summary),
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(row)
    return target


def print_plan(cfg: dict[str, str]) -> None:
    paths = derived(cfg)
    setup = Path(cfg["KEY4HEP_SETUP"])
    workdir = Path(cfg["RECONSTRUCTION_WORKDIR"])
    print("FROZEN A (read-only):", FROZEN_A_REC)
    print("FROZEN SIM:", FROZEN_SIM)
    print("NEW B root:", paths["root"])
    print("\n[smoke reconstruction; dry-run]")
    print(shell_display(setup, workdir, reconstruction_command(cfg, "smoke")))
    print("\n[smoke assignments; dry-run]")
    for command in assignment_commands(cfg, "smoke"):
        print(shell_display(setup, REPO, command, str(REPO / "src")))
    print("\n[full B reconstruction; requires PASS smoke gate and --execute-full]")
    print(shell_display(setup, workdir, reconstruction_command(cfg, "full")))
    print("\n[full assignments; dry-run]")
    for command in assignment_commands(cfg, "full"):
        print(shell_display(setup, REPO, command, str(REPO / "src")))
    print("\n[analysis config candidate]", paths["analysis_config"])
    print("[analysis results]", paths["analysis_results"])
    print("[registry candidate; never auto-appended]", paths["registry_candidate"])


def add_config_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", required=True, type=Path, help="KEY=VALUE future benchmark configuration")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="stage")
    plan = sub.add_parser("plan", help="print all derived paths and commands; execute nothing")
    add_config_argument(plan)
    preflight = sub.add_parser("preflight", help="run read-only provenance, hash, wiring, and change checks")
    add_config_argument(preflight)
    smoke = sub.add_parser("smoke", help="print or explicitly execute the small B reconstruction")
    add_config_argument(smoke); smoke.add_argument("--execute-smoke", action="store_true")
    assignments = sub.add_parser("assignments", help="print or explicitly execute frozen assignments")
    add_config_argument(assignments); assignments.add_argument("--scope", choices=("smoke", "full"), required=True)
    assignments.add_argument("--execute-assignments", action="store_true")
    validate = sub.add_parser("validate-smoke", help="validate smoke REC plus its L_direct summary and write gate JSON")
    add_config_argument(validate)
    full = sub.add_parser("full", help="print or explicitly execute full 2000-event B; requires PASS smoke gate")
    add_config_argument(full); full.add_argument("--execute-full", action="store_true")
    prepare = sub.add_parser("prepare-analysis", help="write a candidate config preserving the frozen contract")
    add_config_argument(prepare)
    analysis = sub.add_parser("analysis", help="print or explicitly execute maintained comparison analysis")
    add_config_argument(analysis); analysis.add_argument("--reviewed-config", required=True, type=Path)
    analysis.add_argument("--execute-analysis", action="store_true")
    analysis.add_argument("--confirm-reviewed-config", action="store_true")
    registry = sub.add_parser("registry-candidate", help="write a review-required CSV row; never append registry")
    add_config_argument(registry)
    return parser


def main() -> int:
    if len(sys.argv) == 3 and sys.argv[1] == "--internal-validate-smoke":
        cfg_path = Path(sys.argv[2])
        cfg = load_config(cfg_path)
        internal_validate_smoke(cfg, cfg_path)
        return 0
    parser = build_parser()
    args = parser.parse_args()
    if args.stage is None:
        parser.print_help()
        return 0
    cfg = load_config(args.config, allow_placeholders=args.stage == "plan")
    paths = derived(cfg)
    setup = Path(cfg["KEY4HEP_SETUP"])
    workdir = Path(cfg["RECONSTRUCTION_WORKDIR"])
    if args.stage == "plan":
        print_plan(cfg)
    elif args.stage == "preflight":
        print(json.dumps(run_preflight(cfg, args.config), indent=2, sort_keys=True))
    elif args.stage == "smoke":
        command = reconstruction_command(cfg, "smoke")
        print(shell_display(setup, workdir, command))
        if args.execute_smoke:
            run_preflight(cfg, args.config)
            if paths["smoke_rec"].exists():
                raise StopError(f"refusing to overwrite smoke REC: {paths['smoke_rec']}")
            run_in_setup(
                setup, workdir, command,
                paths["root"] / "smoke/logs/reconstruction.log",
                paths["root"] / "smoke/logs/reconstruction.exit",
            )
    elif args.stage == "assignments":
        commands = assignment_commands(cfg, args.scope)
        for command in commands:
            print(shell_display(setup, REPO, command, str(REPO / "src")))
        if args.execute_assignments:
            if args.scope == "full":
                require_smoke_gate(cfg, args.config)
            run_preflight(cfg, args.config)
            require_file(paths[f"{args.scope}_rec"], f"{args.scope} B REC")
            outputs = assignment_paths(cfg, args.scope)
            for name, path in outputs.items():
                if name != "root" and path.exists():
                    raise StopError(f"refusing to overwrite {name}: {path}")
            outputs["root"].mkdir(parents=True, exist_ok=True)
            run_in_setup(
                setup, REPO, commands[0], outputs["root"] / "direct.log", outputs["root"] / "direct.exit",
                python_prefix=str(REPO / "src"),
            )
            run_in_setup(
                setup, REPO, commands[1], outputs["root"] / "ancestor.log", outputs["root"] / "ancestor.exit",
                python_prefix=str(REPO / "src"),
            )
    elif args.stage == "validate-smoke":
        command = ["python", str(Path(__file__).resolve()), "--internal-validate-smoke", str(args.config.resolve())]
        print(shell_display(setup, REPO, command))
        result = subprocess.run(
            ["bash", "--noprofile", "--norc", "-c", 'source "$1"; shift; cd "$1"; shift; exec "$@"',
             "bash", str(setup), str(REPO), *command],
            check=False,
        )
        if result.returncode:
            return result.returncode
    elif args.stage == "full":
        command = reconstruction_command(cfg, "full")
        print(shell_display(setup, workdir, command))
        if args.execute_full:
            require_smoke_gate(cfg, args.config)
            run_preflight(cfg, args.config)
            if paths["full_rec"].exists():
                raise StopError(f"refusing to overwrite full B REC: {paths['full_rec']}")
            run_in_setup(
                setup, workdir, command,
                paths["root"] / "full/logs/reconstruction.log",
                paths["root"] / "full/logs/reconstruction.exit",
            )
    elif args.stage == "prepare-analysis":
        target = prepare_analysis_config(cfg)
        print(f"candidate analysis config: {target}")
        print("REVIEW REQUIRED: only B product/provenance fields may differ before analysis execution")
    elif args.stage == "analysis":
        validate_reviewed_analysis_config(cfg, args.reviewed_config)
        command = analysis_command(cfg, args.reviewed_config)
        print(shell_display(setup, Path(cfg["TAUSFCCEE_REPO"]), command, str(Path(cfg["TAUSFCCEE_REPO"]) / "src")))
        if args.execute_analysis:
            if not args.confirm_reviewed_config:
                raise StopError("--execute-analysis also requires --confirm-reviewed-config")
            require_smoke_gate(cfg, args.config)
            run_preflight(cfg, args.config)
            require_file(paths["full_rec"], "full B REC")
            require_file(assignment_paths(cfg, "full")["direct"], "full B L_direct")
            require_file(assignment_paths(cfg, "full")["ancestor"], "full B L_ancestor")
            if paths["analysis_results"].exists():
                raise StopError(f"refusing to overwrite analysis results: {paths['analysis_results']}")
            run_in_setup(
                setup, Path(cfg["TAUSFCCEE_REPO"]), command,
                paths["root"] / "analysis/analysis.log", paths["root"] / "analysis/analysis.exit",
                python_prefix=str(Path(cfg["TAUSFCCEE_REPO"]) / "src"),
            )
    elif args.stage == "registry-candidate":
        target = create_registry_candidate(cfg)
        print(f"candidate registry row: {target}")
        print("REVIEW REQUIRED: efficiency fields and acceptance status are intentionally not populated")
        print("The maintained registry was NOT modified.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except StopError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
