#!/usr/bin/env python3
"""Extract compact truthlink_assignment_v1 Parquet products from a linked REC."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
import os
from pathlib import Path
import re
import resource
import time

import pyarrow as pa
import pyarrow.parquet as pq
import podio.root_io as root_io


from fcc_tau_workflow.truthlink_assignment import (  # noqa: E402
    ASSIGNED,
    ORPHAN_AMBIGUOUS,
    TruthCandidate,
    assign_truth_to_pfo,
)

VERSION = "truthlink_assignment_v1"
EVENT_ID_MULTIPLIER = 10_000

ASSIGNMENT_SCHEMA = pa.schema([
    ("source_file", pa.string()),
    ("source_file_id", pa.string()),
    ("event_in_file", pa.int32()),
    ("event_id", pa.int64()),
    ("event_header_run", pa.int32()),
    ("event_header_event", pa.int32()),
    ("pfo_index", pa.int32()),
    ("pfo_type", pa.int32()),
    ("pfo_charge", pa.float64()),
    ("pfo_energy", pa.float64()),
    ("pfo_px", pa.float64()),
    ("pfo_py", pa.float64()),
    ("pfo_pz", pa.float64()),
    ("pfo_theta", pa.float64()),
    ("pfo_phi", pa.float64()),
    ("truthlink_status", pa.string()),
    ("assigned_mc_index", pa.int32()),
    ("assigned_mc_pdg", pa.int32()),
    ("assigned_mc_charge", pa.float64()),
    ("assigned_mc_generatorStatus", pa.int32()),
    ("assigned_mc_createdInSimulation", pa.bool_()),
    ("track_component", pa.float64()),
    ("cluster_component", pa.float64()),
    ("track_permille", pa.int32()),
    ("cluster_permille", pa.int32()),
    ("raw_weight", pa.int64()),
    ("decision_branch", pa.string()),
    ("n_truth_candidates", pa.int32()),
    ("n_track_candidates", pa.int32()),
    ("n_maxT_ties", pa.int32()),
    ("n_maxC_ties", pa.int32()),
    ("neutral_tiebreak_used", pa.bool_()),
    ("ambiguity_reason", pa.string()),
]).with_metadata({
    b"truthlink_assignment_version": VERSION.encode(),
    b"event_id_definition": b"int(source_file_id) * 10000 + event_in_file",
    b"track_cluster_semantics": b"separate exact integer permille; never summed",
})

CANDIDATE_SCHEMA = pa.schema([
    ("source_file", pa.string()),
    ("source_file_id", pa.string()),
    ("event_in_file", pa.int32()),
    ("event_id", pa.int64()),
    ("pfo_index", pa.int32()),
    ("candidate_mc_index", pa.int32()),
    ("candidate_pdg", pa.int32()),
    ("candidate_charge", pa.float64()),
    ("candidate_generatorStatus", pa.int32()),
    ("candidate_createdInSimulation", pa.bool_()),
    ("track_component", pa.float64()),
    ("cluster_component", pa.float64()),
    ("track_permille", pa.int32()),
    ("cluster_permille", pa.int32()),
    ("raw_weight", pa.int64()),
    ("is_selected_by_new_rule", pa.bool_()),
]).with_metadata({
    b"truthlink_assignment_version": VERSION.encode(),
    b"candidate_scope": b"all persisted FullRecoRelation=true PFO-to-MC relations",
})


def object_index(obj) -> int:
    return int(obj.getObjectID().index)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_time_file(path: Path | None) -> dict:
    if path is None or not path.is_file():
        return {}
    result = {}
    for line in path.read_text(errors="replace").splitlines():
        if "Elapsed (wall clock) time" in line:
            value = line.rsplit(": ", 1)[-1].strip()
            parts = value.split(":")
            seconds = 0.0
            for part in parts:
                seconds = seconds * 60 + float(part)
            result["linker_wall_seconds"] = seconds
        elif "Maximum resident set size (kbytes)" in line:
            result["linker_peak_rss_kb"] = int(line.rsplit(":", 1)[-1].strip())
    return result


def atomic_parquet(path: Path, schema: pa.Schema, rows: list[dict]) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite: {path}")
    if not path.parent.is_dir():
        raise FileNotFoundError(path.parent)
    temporary = path.with_name(f".{path.name}.partial.{os.getpid()}")
    try:
        table = pa.Table.from_pylist(rows, schema=schema)
        pq.write_table(
            table,
            temporary,
            compression="zstd",
            use_dictionary=True,
            write_statistics=True,
        )
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--linked-rec", required=True, type=Path)
    parser.add_argument("--source-rec", required=True, type=Path)
    parser.add_argument("--source-file-id", required=True)
    parser.add_argument("--relation-collection", default="RecoMCTruthLinkTruthlinkV1")
    parser.add_argument("--expected-events", type=int, default=2000)
    parser.add_argument("--assignment-output", required=True, type=Path)
    parser.add_argument("--candidate-output", required=True, type=Path)
    parser.add_argument("--summary-output", required=True, type=Path)
    parser.add_argument("--linker-time-file", type=Path)
    parser.add_argument("--retained-linked-rec", type=Path)
    parser.add_argument("--checksum-linked-rec", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    started = time.monotonic()
    if not re.fullmatch(r"\d{9}", args.source_file_id):
        raise ValueError("source_file_id must be exactly nine decimal digits")
    if not args.linked_rec.is_file() or not args.source_rec.is_file():
        raise FileNotFoundError("linked REC or source REC is missing")
    for path in (args.assignment_output, args.candidate_output, args.summary_output):
        if path.exists():
            raise FileExistsError(f"refusing to overwrite: {path}")

    assignment_rows = []
    candidate_rows = []
    status_counts = Counter()
    branch_counts = Counter()
    ambiguity_counts = Counter()
    event_header_pairs = []
    seen_pfo_keys = set()
    duplicate_pfo_keys = 0
    invalid_references = 0
    raw_zero_relations = 0
    neutral_tiebreak_count = 0
    pfo_per_event = []
    candidate_per_event = []

    reader = root_io.Reader(str(args.linked_rec))
    for event_in_file, event in enumerate(reader.get("events")):
        mcparticles = list(event.get("MCParticles"))
        pfos = list(event.get("PandoraPFOs"))
        header = list(event.get("EventHeader"))
        if len(header) != 1:
            raise AssertionError(f"event {event_in_file}: expected one EventHeader")
        run_number = int(header[0].getRunNumber())
        event_number = int(header[0].getEventNumber())
        event_header_pairs.append((run_number, event_number))
        event_id = int(args.source_file_id) * EVENT_ID_MULTIPLIER + event_in_file
        by_pfo = defaultdict(list)
        relation_count = 0
        for relation in event.get(args.relation_collection):
            pfo_index = object_index(relation.getFrom())
            mc_index = object_index(relation.getTo())
            if not (0 <= pfo_index < len(pfos) and 0 <= mc_index < len(mcparticles)):
                invalid_references += 1
                continue
            mc = mcparticles[mc_index]
            candidate = TruthCandidate.from_packed(
                mc_index=mc_index,
                pdg=int(mc.getPDG()),
                charge=float(mc.getCharge()),
                generator_status=int(mc.getGeneratorStatus()),
                created_in_simulation=bool(mc.isCreatedInSimulation()),
                raw_weight=float(relation.getWeight()),
            )
            by_pfo[pfo_index].append(candidate)
            relation_count += 1
            raw_zero_relations += int(candidate.raw_weight == 0)
        candidate_per_event.append(relation_count)
        pfo_per_event.append(len(pfos))

        for pfo_index, pfo in enumerate(pfos):
            if object_index(pfo) != pfo_index:
                raise AssertionError(f"non-canonical PFO index at event {event_in_file}")
            key = (args.source_file_id, event_in_file, pfo_index)
            if key in seen_pfo_keys:
                duplicate_pfo_keys += 1
            seen_pfo_keys.add(key)
            result = assign_truth_to_pfo(by_pfo[pfo_index])
            selected = result.candidate
            status_counts[result.status] += 1
            branch_counts[result.decision_branch] += 1
            if result.ambiguity_reason:
                ambiguity_counts[result.ambiguity_reason] += 1
            neutral_tiebreak_count += int(result.neutral_tiebreak_used)
            p = pfo.getMomentum()
            px, py, pz = float(p.x), float(p.y), float(p.z)
            theta = math.atan2(math.hypot(px, py), pz)
            phi = math.atan2(py, px)
            assignment_rows.append({
                "source_file": str(args.source_rec),
                "source_file_id": args.source_file_id,
                "event_in_file": event_in_file,
                "event_id": event_id,
                "event_header_run": run_number,
                "event_header_event": event_number,
                "pfo_index": pfo_index,
                "pfo_type": int(pfo.getPDG()),
                "pfo_charge": float(pfo.getCharge()),
                "pfo_energy": float(pfo.getEnergy()),
                "pfo_px": px,
                "pfo_py": py,
                "pfo_pz": pz,
                "pfo_theta": theta,
                "pfo_phi": phi,
                "truthlink_status": result.status,
                "assigned_mc_index": None if selected is None else selected.mc_index,
                "assigned_mc_pdg": None if selected is None else selected.pdg,
                "assigned_mc_charge": None if selected is None else selected.charge,
                "assigned_mc_generatorStatus": None if selected is None else selected.generator_status,
                "assigned_mc_createdInSimulation": None if selected is None else selected.created_in_simulation,
                "track_component": None if selected is None else selected.track_component,
                "cluster_component": None if selected is None else selected.cluster_component,
                "track_permille": None if selected is None else selected.track_permille,
                "cluster_permille": None if selected is None else selected.cluster_permille,
                "raw_weight": None if selected is None else selected.raw_weight,
                "decision_branch": result.decision_branch,
                "n_truth_candidates": result.n_candidates,
                "n_track_candidates": result.n_track_candidates,
                "n_maxT_ties": result.n_maxT_ties,
                "n_maxC_ties": result.n_maxC_ties,
                "neutral_tiebreak_used": result.neutral_tiebreak_used,
                "ambiguity_reason": result.ambiguity_reason,
            })
            for candidate in by_pfo[pfo_index]:
                candidate_rows.append({
                    "source_file": str(args.source_rec),
                    "source_file_id": args.source_file_id,
                    "event_in_file": event_in_file,
                    "event_id": event_id,
                    "pfo_index": pfo_index,
                    "candidate_mc_index": candidate.mc_index,
                    "candidate_pdg": candidate.pdg,
                    "candidate_charge": candidate.charge,
                    "candidate_generatorStatus": candidate.generator_status,
                    "candidate_createdInSimulation": candidate.created_in_simulation,
                    "track_component": candidate.track_component,
                    "cluster_component": candidate.cluster_component,
                    "track_permille": candidate.track_permille,
                    "cluster_permille": candidate.cluster_permille,
                    "raw_weight": candidate.raw_weight,
                    "is_selected_by_new_rule": bool(
                        selected is not None and selected.mc_index == candidate.mc_index
                    ),
                })

    event_count = len(event_header_pairs)
    if event_count != args.expected_events:
        raise AssertionError(f"expected {args.expected_events} events, found {event_count}")
    if invalid_references or duplicate_pfo_keys:
        raise AssertionError(
            f"invalid_references={invalid_references}, duplicate_pfo_keys={duplicate_pfo_keys}"
        )
    if len(set(event_header_pairs)) != event_count:
        raise AssertionError("duplicate EventHeader pair within input file")
    if sum(status_counts.values()) != len(assignment_rows):
        raise AssertionError("truthlink status partition mismatch")
    if len(candidate_rows) != sum(candidate_per_event):
        raise AssertionError("candidate row count mismatch")
    if sum(row["is_selected_by_new_rule"] for row in candidate_rows) != status_counts[ASSIGNED]:
        raise AssertionError("selected candidate count does not match assigned PFO count")

    atomic_parquet(args.assignment_output, ASSIGNMENT_SCHEMA, assignment_rows)
    atomic_parquet(args.candidate_output, CANDIDATE_SCHEMA, candidate_rows)
    extraction_wall = time.monotonic() - started
    linker_metrics = parse_time_file(args.linker_time_file)
    peak_rss_kb = max(
        int(linker_metrics.get("linker_peak_rss_kb", 0)),
        int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
    )
    output_bytes = args.assignment_output.stat().st_size + args.candidate_output.stat().st_size
    summary = {
        "version": VERSION,
        "source_file": str(args.source_rec),
        "source_file_id": args.source_file_id,
        "linked_rec_input": str(args.linked_rec),
        "retained_linked_rec": None if args.retained_linked_rec is None else str(args.retained_linked_rec),
        "relation_collection": args.relation_collection,
        "event_id_definition": "int(source_file_id) * 10000 + event_in_file",
        "n_events": event_count,
        "event_header_run_min": min(x[0] for x in event_header_pairs),
        "event_header_run_max": max(x[0] for x in event_header_pairs),
        "event_header_event_min": min(x[1] for x in event_header_pairs),
        "event_header_event_max": max(x[1] for x in event_header_pairs),
        "n_pfos": len(assignment_rows),
        "n_candidate_relations": len(candidate_rows),
        "n_assigned": status_counts[ASSIGNED],
        "n_orphan_no_relation": status_counts["truthlink_orphan_no_relation"],
        "n_orphan_ambiguous": status_counts[ORPHAN_AMBIGUOUS],
        "status_counts": dict(status_counts),
        "branch_counts": dict(branch_counts),
        "track_branch_used": sum(v for k, v in branch_counts.items() if k.startswith("track")),
        "cluster_branch_used": sum(v for k, v in branch_counts.items() if k.startswith("cluster")),
        "neutral_tiebreak_used": neutral_tiebreak_count,
        "ambiguity_reason_counts": dict(ambiguity_counts),
        "raw_zero_relations": raw_zero_relations,
        "invalid_mc_or_pfo_references": invalid_references,
        "duplicate_pfo_keys": duplicate_pfo_keys,
        "assignment_output": str(args.assignment_output),
        "candidate_output": str(args.candidate_output),
        "assignment_bytes": args.assignment_output.stat().st_size,
        "candidate_bytes": args.candidate_output.stat().st_size,
        "output_bytes": output_bytes,
        "assignment_sha256": sha256(args.assignment_output),
        "candidate_sha256": sha256(args.candidate_output),
        "linked_rec_bytes": args.linked_rec.stat().st_size,
        "linked_rec_sha256": sha256(args.linked_rec) if args.checksum_linked_rec else None,
        "temporary_disk_bytes_conservative": args.linked_rec.stat().st_size + output_bytes,
        "extraction_wall_seconds": extraction_wall,
        "linker_wall_seconds": linker_metrics.get("linker_wall_seconds"),
        "peak_rss_kb": peak_rss_kb,
        "pfo_per_event_min": min(pfo_per_event),
        "pfo_per_event_max": max(pfo_per_event),
        "candidate_per_event_min": min(candidate_per_event),
        "candidate_per_event_max": max(candidate_per_event),
    }
    temporary_summary = args.summary_output.with_name(
        f".{args.summary_output.name}.partial.{os.getpid()}"
    )
    try:
        with temporary_summary.open("x") as stream:
            json.dump(summary, stream, indent=2, sort_keys=True)
            stream.write("\n")
        os.replace(temporary_summary, args.summary_output)
    finally:
        if temporary_summary.exists():
            temporary_summary.unlink()
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
