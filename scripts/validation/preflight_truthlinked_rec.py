#!/usr/bin/env python3
"""Read-only completion/interface preflight for a TruthlinkV1 REC file."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import podio.root_io as root_io

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
from fcc_tau_workflow.truthlinked_preflight import inspect_events, require_stable_file, require_unchanged  # noqa: E402

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--expected-events", type=int, required=True)
    parser.add_argument("--minimum-age-seconds", type=int, default=300)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--checksum", action="store_true")
    args = parser.parse_args()
    if args.expected_events <= 0 or args.minimum_age_seconds < 0:
        parser.error("expected events must be positive and minimum age non-negative")
    before = require_stable_file(args.input, args.minimum_age_seconds)
    result = inspect_events(root_io.Reader(str(args.input)).get("events"), args.expected_events)
    require_unchanged(before)
    result.update({"status": "PASS", "input": str(args.input.resolve()), "bytes": before.size,
                   "expected_events": args.expected_events, "minimum_age_seconds": args.minimum_age_seconds})
    if args.checksum:
        result["sha256"] = sha256(args.input)
        require_unchanged(before)
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output_json:
        if args.output_json.exists():
            raise FileExistsError(args.output_json)
        if not args.output_json.parent.is_dir():
            raise FileNotFoundError(args.output_json.parent)
        args.output_json.write_text(payload)
    print(payload, end="")

if __name__ == "__main__":
    main()
