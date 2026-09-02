"""Validation for the data-only workflow product manifest."""
from __future__ import annotations

import json
from pathlib import Path

import yaml


SCHEMA_VERSION = "fcc_tau_workflow_product_manifest_v1"
ASSOCIATION_CONTRACT = "fcc_tau_association_v1"
DIRECT_COLUMNS = {"source_file_id", "event_in_file", "pfo_index", "truthlink_status", "assigned_mc_index"}
ANCESTOR_COLUMNS = {"sample", "source_file_id", "event_in_file", "pfo_index", "ancestor_status", "ancestor_mc_index"}


def load_product_manifest(path: str | Path, *, check_products: bool = False) -> dict:
    source = Path(path)
    data = json.loads(source.read_text()) if source.suffix.lower() == ".json" else yaml.safe_load(source.read_text())
    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported workflow product manifest schema")
    if data.get("association_contract") != ASSOCIATION_CONTRACT:
        raise ValueError("unsupported association contract")
    if not isinstance(data.get("sample"), str) or not data["sample"]:
        raise ValueError("product manifest requires sample")
    products = data.get("products")
    if not isinstance(products, list) or not products:
        raise ValueError("product manifest requires products")
    required = {"source_file_id", "source_rec", "direct_assignment", "ancestor_assignment", "truth_definition_version", "input_provenance"}
    seen = set()
    for entry in products:
        if not isinstance(entry, dict) or required - set(entry):
            raise ValueError("incomplete product entry")
        source_id = str(entry["source_file_id"])
        if source_id in seen:
            raise ValueError(f"duplicate source_file_id: {source_id}")
        seen.add(source_id)
        if check_products:
            _validate_product_files(entry)
    return data


def _validate_product_files(entry: dict) -> None:
    import pyarrow.parquet as pq

    for field in ("source_rec", "direct_assignment", "ancestor_assignment", "input_provenance"):
        if not Path(entry[field]).is_file():
            raise FileNotFoundError(entry[field])
    direct = set(pq.ParquetFile(entry["direct_assignment"]).schema_arrow.names)
    ancestor = set(pq.ParquetFile(entry["ancestor_assignment"]).schema_arrow.names)
    if missing := DIRECT_COLUMNS - direct:
        raise ValueError(f"direct product missing columns: {sorted(missing)}")
    if missing := ANCESTOR_COLUMNS - ancestor:
        raise ValueError(f"ancestor product missing columns: {sorted(missing)}")
