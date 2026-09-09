"""Protect unsigned EDM EventHeader serialization used by KKMCee."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pyarrow as pa


ROOT = Path(__file__).resolve().parents[2]


def _schema(script_name: str):
    path = ROOT / "scripts/workflow" / script_name
    spec = spec_from_file_location("assignment_schema_under_test", path)
    module = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.ASSIGNMENT_SCHEMA


def test_event_header_fields_preserve_uint32_domain():
    for script in ("extract_truthlink_assignments.py", "extract_truthlink_assignments_pythia.py"):
        schema = _schema(script)
        assert schema.field("event_header_run").type == pa.uint32()
        assert schema.field("event_header_event").type == pa.uint32()
        pa.array([2**32 - 1], type=schema.field("event_header_run").type)
