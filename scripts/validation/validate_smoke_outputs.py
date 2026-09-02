#!/usr/bin/env python3
"""Validate linked-REC invariance and independent Stage-6 goldens."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

import pyarrow.parquet as pq
import uproot
from podio import root_io

from fcc_tau_workflow.smoke_fixture import load_smoke_fixture


def object_index(obj) -> int:
    return int(obj.getObjectID().index)


def vector(value):
    return tuple(float(getattr(value, axis)) for axis in ("x", "y", "z"))


def references(values):
    return tuple(object_index(value) for value in values)


def fixed_array(value, length):
    return tuple(float(value[index]) for index in range(length))


def pfo_value(obj):
    decay = obj.getDecayVertex()
    return (
        int(obj.getPDG()), float(obj.getCharge()), float(obj.getEnergy()), float(obj.getMass()),
        vector(obj.getMomentum()), vector(obj.getReferencePoint()), fixed_array(obj.getCovMatrix(), 10),
        float(obj.getGoodnessOfPID()), bool(obj.isCompound()), references(obj.getTracks()),
        references(obj.getClusters()), references(obj.getParticles()),
        object_index(decay) if decay.isAvailable() else None,
    )


def track_state_value(state):
    return (
        int(state.location), float(state.D0), float(state.phi), float(state.omega),
        float(state.Z0), float(state.tanLambda), float(state.time),
        vector(state.referencePoint), fixed_array(state.covMatrix, 21),
    )


def track_value(obj):
    return (
        int(obj.getType()), float(obj.getChi2()), int(obj.getNdf()), int(obj.getNholes()),
        tuple(obj.getSubdetectorHitNumbers()), tuple(obj.getSubdetectorHoleNumbers()),
        tuple(track_state_value(state) for state in obj.getTrackStates()),
        references(obj.getTrackerHits()), references(obj.getTracks()),
    )


def cluster_value(obj):
    return (
        int(obj.getType()), float(obj.getEnergy()), float(obj.getEnergyError()),
        vector(obj.getPosition()), fixed_array(obj.getPositionError(), 6), fixed_array(obj.getDirectionError(), 3),
        float(obj.getITheta()), float(obj.getIPhi()), float(obj.getPhi()),
        tuple(obj.getShapeParameters()), tuple(obj.getSubdetectorEnergies()),
        references(obj.getHits()), references(obj.getClusters()),
    )


def mc_value(obj):
    return (
        int(obj.getPDG()), int(obj.getGeneratorStatus()), int(obj.getSimulatorStatus()),
        float(obj.getCharge()), float(obj.getTime()), float(obj.getMass()),
        float(obj.getEnergy()), float(obj.getHelicity()), vector(obj.getMomentum()),
        vector(obj.getMomentumAtEndpoint()), vector(obj.getVertex()), vector(obj.getEndpoint()),
        references(obj.getParents()), references(obj.getDaughters()),
        bool(obj.isCreatedInSimulation()), bool(obj.isBackscatter()), bool(obj.isDecayedInCalorimeter()),
        bool(obj.isDecayedInTracker()), bool(obj.isStopped()), bool(obj.isOverlay()), bool(obj.isHandledByFastSim()),
    )


def header_value(obj):
    return (int(obj.getRunNumber()), int(obj.getEventNumber()), int(obj.getTimeStamp()), float(obj.getWeight()), tuple(obj.getWeights()))


SERIALIZERS = {
    "EventHeader": header_value,
    "PandoraPFOs": pfo_value,
    "MarlinTrkTracks": track_value,
    "PandoraClusters": cluster_value,
    "MCParticles": mc_value,
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def event_count(path: Path) -> int:
    with uproot.open(path) as source:
        return int(source["events"].num_entries)


def normalize(value):
    if isinstance(value, float) and math.isnan(value):
        return "NaN"
    return value


def rows_for_event(path: Path) -> list[dict]:
    return pq.read_table(path, filters=[("event_in_file", "=", 0)]).to_pylist()


def selected_rows(rows, fields):
    return [tuple(normalize(row.get(field)) for field in fields) for row in sorted(rows, key=lambda row: int(row["pfo_index"]))]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--linked-rec", type=Path, required=True)
    parser.add_argument("--direct", type=Path, required=True)
    parser.add_argument("--ancestor", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or not args.output.parent.is_dir():
        raise FileExistsError(args.output)
    data = load_smoke_fixture(args.fixture)
    source_path = Path(data["source_rec"]["path"])
    source_reader = root_io.Reader(str(source_path))
    linked_reader = root_io.Reader(str(args.linked_rec))
    source = next(iter(source_reader.get("events")))
    linked = next(iter(linked_reader.get("events")))
    source_names = set(source.getAvailableCollections())
    linked_names = set(linked.getAvailableCollections())
    missing = sorted(source_names - linked_names)
    count_mismatches = {
        name: [len(source.get(name)), len(linked.get(name))]
        for name in sorted(source_names & linked_names)
        if len(source.get(name)) != len(linked.get(name))
    }
    content = {}
    for name, serializer in SERIALIZERS.items():
        before = [serializer(obj) for obj in source.get(name)]
        after = [serializer(obj) for obj in linked.get(name)]
        content[name] = {"count": len(before), "exact": before == after}

    relation_name = "RecoMCTruthLinkTruthlinkV1"
    relations = list(linked.get(relation_name))
    pfos = list(linked.get("PandoraPFOs"))
    mcparticles = list(linked.get("MCParticles"))
    invalid_endpoints = sum(
        not (0 <= object_index(relation.getFrom()) < len(pfos)
             and 0 <= object_index(relation.getTo()) < len(mcparticles))
        for relation in relations
    )
    relation_rows = [
        (object_index(relation.getFrom()), object_index(relation.getTo()), int(round(float(relation.getWeight()))))
        for relation in relations
    ]
    golden_path = Path(data["golden_linked_rec"]["path"])
    golden_reader = root_io.Reader(str(golden_path))
    golden = next(iter(golden_reader.get("events")))
    golden_rows = [
        (object_index(relation.getFrom()), object_index(relation.getTo()), int(round(float(relation.getWeight()))))
        for relation in golden.get(data["golden_linked_rec"]["relation_collection"])
    ]

    direct_fields = (
        "source_file_id", "event_in_file", "pfo_index", "pfo_type", "pfo_charge", "pfo_energy",
        "pfo_px", "pfo_py", "pfo_pz", "truthlink_status", "assigned_mc_index", "assigned_mc_pdg",
        "track_permille", "cluster_permille", "raw_weight", "decision_branch", "n_truth_candidates",
    )
    golden_products = data["golden_products"]
    direct_new = rows_for_event(args.direct)
    direct_golden = rows_for_event(Path(golden_products["direct_assignment"]))
    ancestor_fields = (
        "source_file_id", "event_in_file", "pfo_index", "direct_status", "direct_mc_index",
        "direct_mc_pdg", "ancestor_status", "ancestor_mc_index", "ancestor_mc_pdg", "ancestor_depth",
        "direct_to_ancestor_changed", "track_permille", "cluster_permille", "raw_weight", "decision_branch",
        "n_truth_candidates", "nTracks", "nClusters", "pfo_topology",
    )
    ancestor_new = rows_for_event(args.ancestor)
    ancestor_golden = rows_for_event(Path(golden_products["ancestor_assignment"]))

    result = {
        "schema_version": "fcc_tau_linker_invariance_v1",
        "status": "PASS",
        "linked_rec": str(args.linked_rec),
        "linked_rec_sha256": sha256(args.linked_rec),
        "linked_events": event_count(args.linked_rec),
        "source_collections": len(source_names),
        "linked_collections": len(linked_names),
        "missing_preexisting_collections": missing,
        "preexisting_collection_count_mismatches": count_mismatches,
        "content_invariance": content,
        "relation_collection": relation_name,
        "relation_count": len(relations),
        "invalid_relation_endpoints": invalid_endpoints,
        "golden_relation_order_equal": relation_rows == golden_rows,
        "golden_relation_multiset_equal": Counter(relation_rows) == Counter(golden_rows),
        "direct_rows": len(direct_new),
        "direct_golden_event0_rows": len(direct_golden),
        "direct_golden_core_equal": selected_rows(direct_new, direct_fields) == selected_rows(direct_golden, direct_fields),
        "ancestor_rows": len(ancestor_new),
        "ancestor_golden_event0_rows": len(ancestor_golden),
        "ancestor_golden_core_equal": selected_rows(ancestor_new, ancestor_fields) == selected_rows(ancestor_golden, ancestor_fields),
    }
    passed = (
        result["linked_events"] == int(data["source_rec"]["smoke_events"])
        and not missing and not count_mismatches
        and all(item["exact"] for item in content.values())
        and len(relations) > 0 and invalid_endpoints == 0
        and result["golden_relation_multiset_equal"]
        and result["direct_golden_core_equal"]
        and result["ancestor_golden_core_equal"]
    )
    result["status"] = "PASS" if passed else "FAIL"
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
