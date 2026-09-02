#!/usr/bin/env python3
"""Validate an external runtime-smoke fixture without modifying it."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import uproot
from podio import root_io

from fcc_tau_workflow.smoke_fixture import load_smoke_fixture


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def event_count(path: Path) -> int:
    with uproot.open(path) as source:
        return int(source["events"].num_entries)


def object_index(obj) -> int:
    return int(obj.getObjectID().index)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    data = load_smoke_fixture(args.fixture)
    source = data["source_rec"]
    source_path = Path(source["path"])
    golden = data["golden_linked_rec"]
    golden_path = Path(golden["path"])

    source_hash = sha256(source_path)
    golden_hash = sha256(golden_path)
    source_frame = next(iter(root_io.Reader(str(source_path)).get("events")))
    available = set(source_frame.getAvailableCollections())
    counts = {name: len(source_frame.get(name)) for name in source["expected_collections"] if name in available}
    golden_frame = next(iter(root_io.Reader(str(golden_path)).get("events")))
    relations = list(golden_frame.get(golden["relation_collection"]))
    pfos = list(golden_frame.get("PandoraPFOs"))
    mcparticles = list(golden_frame.get("MCParticles"))
    invalid_endpoints = sum(
        not (0 <= object_index(relation.getFrom()) < len(pfos)
             and 0 <= object_index(relation.getTo()) < len(mcparticles))
        for relation in relations
    )
    result = {
        "schema_version": "fcc_tau_smoke_fixture_validation_v1",
        "fixture_id": data["fixture_id"],
        "source_path": str(source_path),
        "source_size": source_path.stat().st_size,
        "source_sha256": source_hash,
        "source_sha256_matches": source_hash == source["sha256"],
        "source_total_events": event_count(source_path),
        "smoke_events": int(source["smoke_events"]),
        "event0_collection_counts": counts,
        "missing_expected_collections": sorted(set(source["expected_collections"]) - available),
        "output_collection_collision": source["forbidden_output_collision"] in available,
        "golden_path": str(golden_path),
        "golden_sha256": golden_hash,
        "golden_sha256_matches": golden_hash == golden["sha256"],
        "golden_events": event_count(golden_path),
        "golden_relation_count": len(relations),
        "golden_invalid_endpoints": invalid_endpoints,
    }
    passed = (
        result["source_sha256_matches"]
        and result["source_total_events"] == int(source["total_events"])
        and not result["missing_expected_collections"]
        and not result["output_collection_collision"]
        and counts.get("EventHeader") == 1
        and result["golden_sha256_matches"]
        and result["golden_events"] == int(golden["events"])
        and result["golden_relation_count"] == int(golden["relation_count"])
        and invalid_endpoints == 0
    )
    result["status"] = "PASS" if passed else "FAIL"
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        if args.output.exists() or not args.output.parent.is_dir():
            raise FileExistsError(args.output)
        args.output.write_text(text)
    print(text, end="")
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
