#!/usr/bin/env python3
"""Build a Condor TSV from a truth-link campaign manifest without site defaults."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign-manifest", required=True, type=Path)
    parser.add_argument("--queue-output", required=True, type=Path)
    parser.add_argument("--expected-total", required=True, type=int)
    parser.add_argument("--expected-remaining", type=int)
    args = parser.parse_args()
    if args.queue_output.exists():
        raise FileExistsError(args.queue_output)
    with args.campaign_manifest.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != args.expected_total:
        raise AssertionError(f"expected {args.expected_total} manifest rows, found {len(rows)}")
    queue = []
    for row in rows:
        outputs = [Path(row[key]) for key in ("output_assignment", "output_candidates", "output_summary")]
        if all(path.is_file() and path.stat().st_size > 0 for path in outputs):
            continue
        if any(path.exists() for path in outputs):
            raise AssertionError(f"partial pre-existing output set for {row['source_file_id']}")
        retained = row.get("output_truthlinked_REC") or "-"
        if retained != "-" and Path(retained).exists():
            raise AssertionError(f"orphan retained REC exists for {row['source_file_id']}")
        queue.append({
            "source_id": row["source_file_id"], "input_rec": row["input_REC"],
            "assignment_output": row["output_assignment"], "candidate_output": row["output_candidates"],
            "summary_output": row["output_summary"], "retained_linked_rec": retained,
            "expected_events": row["expected_events"],
        })
    if args.expected_remaining is not None and len(queue) != args.expected_remaining:
        raise AssertionError(f"expected {args.expected_remaining} remaining jobs, found {len(queue)}")
    args.queue_output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.queue_output.with_name(f".{args.queue_output.name}.partial")
    with temporary.open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=("source_id", "input_rec", "assignment_output", "candidate_output", "summary_output", "retained_linked_rec", "expected_events"), delimiter="\t", lineterminator="\n")
        writer.writerows(queue)
    temporary.replace(args.queue_output)
    print(f"remaining_jobs={len(queue)}")
    print(f"shareable_remaining={sum(row['retained_linked_rec'] != '-' for row in queue)}")


if __name__ == "__main__":
    main()
