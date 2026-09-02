#!/usr/bin/env python3
"""Apply frozen L_ancestor semantics to REC plus L_direct products.

The output schema is the authoritative ancestor-assignment schema used by the
validated Pythia production extractor. Tau-lineage diagnostics are deliberately
outside this core-only executable.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
import os
from pathlib import Path
import time

import pyarrow as pa
import pyarrow.parquet as pq
import podio.root_io as root_io

from fcc_tau_workflow.truthlink_ancestor_assignment import assign_selected_ancestor

VERSION = "truthlink_ancestor_assignment_v1"
ANCESTOR_SCHEMA = pa.schema([
    ("sample", pa.string()), ("source_file_id", pa.string()), ("event_in_file", pa.int32()),
    ("event_id", pa.int64()), ("pfo_index", pa.int32()), ("pfo_type", pa.int32()),
    ("pfo_energy", pa.float64()), ("pfo_theta", pa.float64()), ("nTracks", pa.int32()),
    ("nClusters", pa.int32()), ("pfo_topology", pa.string()), ("direct_status", pa.string()),
    ("direct_mc_index", pa.int32()), ("direct_mc_pdg", pa.int32()), ("ancestor_status", pa.string()),
    ("ancestor_mc_index", pa.int32()), ("ancestor_mc_pdg", pa.int32()), ("ancestor_depth", pa.int32()),
    ("n_selected_at_nearest_depth", pa.int32()), ("direct_to_ancestor_changed", pa.bool_()),
    ("track_component", pa.float64()), ("cluster_component", pa.float64()),
    ("track_permille", pa.int32()), ("cluster_permille", pa.int32()), ("raw_weight", pa.int64()),
    ("decision_branch", pa.string()), ("n_truth_candidates", pa.int32()),
])


def object_index(value) -> int:
    return int(value.getObjectID().index)


def momentum(value) -> tuple[float, float, float]:
    vector = value.getMomentum()
    return float(vector.x), float(vector.y), float(vector.z)


def is_selected_truth(value) -> bool:
    vector = momentum(value)
    return (
        int(value.getGeneratorStatus()) == 1
        and abs(int(value.getPDG())) not in (12, 14, 16)
        and math.sqrt(sum(component * component for component in vector)) >= 1e-10
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_parquet(path: Path, rows: list[dict]) -> None:
    if path.exists():
        raise FileExistsError(path)
    if not path.parent.is_dir():
        raise FileNotFoundError(path.parent)
    temporary = path.with_name(f".{path.name}.partial.{os.getpid()}")
    try:
        table = pa.Table.from_pylist(rows, schema=ANCESTOR_SCHEMA).replace_schema_metadata({b"version": VERSION.encode()})
        pq.write_table(table, temporary, compression="zstd", use_dictionary=True, write_statistics=True)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", required=True)
    parser.add_argument("--source-file-id", required=True)
    parser.add_argument("--source-rec", type=Path, required=True)
    parser.add_argument("--direct-assignment", type=Path, required=True)
    parser.add_argument("--ancestor-output", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path, required=True)
    parser.add_argument("--expected-events", type=int, default=2000)
    args = parser.parse_args()
    started = time.monotonic()
    for source in (args.source_rec, args.direct_assignment):
        if not source.is_file():
            raise FileNotFoundError(source)
    for output in (args.ancestor_output, args.summary_output):
        if output.exists():
            raise FileExistsError(output)
        if not output.parent.is_dir():
            raise FileNotFoundError(output.parent)

    direct_rows = pq.read_table(args.direct_assignment).to_pylist()
    direct_by_event = defaultdict(list)
    for row in direct_rows:
        direct_by_event[int(row["event_in_file"])].append(row)
    output_rows = []
    status_counts = Counter(); promoted_depths = Counter(); seen = set(); invalid_references = 0; events = 0
    for event_in_file, event in enumerate(root_io.Reader(str(args.source_rec)).get("events")):
        events += 1
        mcparticles = list(event.get("MCParticles")); pfos = list(event.get("PandoraPFOs"))
        event_direct = sorted(direct_by_event[event_in_file], key=lambda row: int(row["pfo_index"]))
        if len(event_direct) != len(pfos):
            raise AssertionError(("PFO join", event_in_file, len(event_direct), len(pfos)))
        parents = [[object_index(parent) for parent in particle.getParents()] for particle in mcparticles]
        if any(index < 0 or index >= len(mcparticles) for group in parents for index in group):
            raise AssertionError(("invalid genealogy", event_in_file))
        selected = {index for index, particle in enumerate(mcparticles) if is_selected_truth(particle)}
        cache = {}
        for pfo_index, (direct, pfo) in enumerate(zip(event_direct, pfos)):
            key = (args.source_file_id, event_in_file, pfo_index)
            if key in seen:
                raise AssertionError(("duplicate PFO key", key))
            seen.add(key)
            direct_index = direct["assigned_mc_index"]
            if direct_index is not None and not 0 <= int(direct_index) < len(mcparticles):
                invalid_references += 1
            cache_key = (str(direct["truthlink_status"]), direct_index)
            if cache_key not in cache:
                cache[cache_key] = assign_selected_ancestor(cache_key[0], cache_key[1], parents, selected)
            result = cache[cache_key]; ancestor_index = result.assigned_mc_index
            status_counts[result.status] += 1
            if result.ancestor_depth is not None:
                promoted_depths[result.ancestor_depth] += 1
            vector = pfo.getMomentum(); n_tracks = len(list(pfo.getTracks())); n_clusters = len(list(pfo.getClusters()))
            output_rows.append({
                "sample": args.sample, "source_file_id": args.source_file_id, "event_in_file": event_in_file,
                "event_id": int(args.source_file_id) * 10000 + event_in_file, "pfo_index": pfo_index,
                "pfo_type": int(pfo.getPDG()), "pfo_energy": float(pfo.getEnergy()),
                "pfo_theta": math.atan2(math.hypot(float(vector.x), float(vector.y)), float(vector.z)),
                "nTracks": n_tracks, "nClusters": n_clusters,
                "pfo_topology": "SIMPLE" if n_tracks <= 1 and n_clusters <= 1 else "COMPLEX",
                "direct_status": direct["truthlink_status"], "direct_mc_index": direct_index,
                "direct_mc_pdg": direct["assigned_mc_pdg"], "ancestor_status": result.status,
                "ancestor_mc_index": ancestor_index,
                "ancestor_mc_pdg": None if ancestor_index is None else int(mcparticles[int(ancestor_index)].getPDG()),
                "ancestor_depth": result.ancestor_depth,
                "n_selected_at_nearest_depth": result.n_selected_at_nearest_depth,
                "direct_to_ancestor_changed": bool(ancestor_index is not None and ancestor_index != direct_index),
                "track_component": direct["track_component"], "cluster_component": direct["cluster_component"],
                "track_permille": direct["track_permille"], "cluster_permille": direct["cluster_permille"],
                "raw_weight": direct["raw_weight"], "decision_branch": direct["decision_branch"],
                "n_truth_candidates": direct["n_truth_candidates"],
            })
    if events != args.expected_events or len(output_rows) != len(direct_rows) or invalid_references:
        raise AssertionError(("validation", events, len(output_rows), len(direct_rows), invalid_references))
    atomic_parquet(args.ancestor_output, output_rows)
    summary = {
        "version": VERSION, "status": "PASS", "sample": args.sample,
        "source_file_id": args.source_file_id, "source_rec": str(args.source_rec),
        "direct_assignment": str(args.direct_assignment), "events": events, "pfos": len(output_rows),
        "ancestor_status_counts": dict(status_counts),
        "promoted_depths": {str(key): value for key, value in promoted_depths.items()},
        "invalid_references": invalid_references, "wall_seconds": time.monotonic() - started,
        "ancestor_output": str(args.ancestor_output), "ancestor_sha256": sha256(args.ancestor_output),
        "authoritative_event_key": ["sample", "source_file_id", "event_in_file"],
    }
    temporary = args.summary_output.with_name(f".{args.summary_output.name}.partial.{os.getpid()}")
    temporary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, args.summary_output)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
