"""Schema checks for external FCC tau runtime-smoke fixtures."""
from __future__ import annotations

from pathlib import Path

import yaml


SCHEMA_VERSION = "fcc_tau_smoke_fixture_v1"


def load_smoke_fixture(path: str | Path) -> dict:
    source = Path(path)
    data = yaml.safe_load(source.read_text())
    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported smoke fixture schema")
    for key in ("fixture_id", "source_file_id", "sample", "source_rec", "golden_linked_rec", "provenance"):
        if key not in data:
            raise ValueError(f"smoke fixture missing {key}")
    if not str(data["source_file_id"]).isdigit():
        raise ValueError("source_file_id must be decimal")
    rec = data["source_rec"]
    for key in ("path", "sha256", "total_events", "smoke_events", "expected_collections", "forbidden_output_collision"):
        if key not in rec:
            raise ValueError(f"source_rec missing {key}")
    if int(rec["smoke_events"]) <= 0 or int(rec["smoke_events"]) > int(rec["total_events"]):
        raise ValueError("invalid smoke event count")
    if len(str(rec["sha256"])) != 64:
        raise ValueError("invalid source REC SHA-256")
    golden = data["golden_linked_rec"]
    for key in ("path", "sha256", "events", "relation_collection", "relation_count"):
        if key not in golden:
            raise ValueError(f"golden_linked_rec missing {key}")
    return data
