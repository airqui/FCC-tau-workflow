#!/usr/bin/env python3
"""Write the small data-only manifest produced by a workflow smoke run."""
from __future__ import annotations

import argparse
from pathlib import Path

import yaml


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", required=True)
    parser.add_argument("--source-file-id", required=True)
    parser.add_argument("--source-rec", required=True)
    parser.add_argument("--direct", required=True)
    parser.add_argument("--ancestor", required=True)
    parser.add_argument("--provenance", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or not args.output.parent.is_dir():
        raise FileExistsError(args.output)
    payload = {
        "schema_version": "fcc_tau_workflow_product_manifest_v1",
        "association_contract": "fcc_tau_association_v1",
        "sample": args.sample,
        "products": [{
            "source_file_id": str(args.source_file_id),
            "source_rec": str(Path(args.source_rec).resolve()),
            "direct_assignment": str(Path(args.direct).resolve()),
            "ancestor_assignment": str(Path(args.ancestor).resolve()),
            "truth_definition_version": "selected_truth_v1",
            "input_provenance": str(Path(args.provenance).resolve()),
        }],
    }
    args.output.write_text(yaml.safe_dump(payload, sort_keys=False))
    print(args.output)


if __name__ == "__main__":
    main()
