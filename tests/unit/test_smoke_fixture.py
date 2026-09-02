import json
from pathlib import Path

import pytest
import yaml

from fcc_tau_workflow.smoke_fixture import load_smoke_fixture


FIXTURE = Path(__file__).parents[1] / "fixtures/manifests/smoke_fixture_v1.yaml"
GOLDEN = Path(__file__).parents[1] / "fixtures/golden/smoke_event0_expected_v1.json"


def test_frozen_smoke_fixture_manifest_parses():
    data = load_smoke_fixture(FIXTURE)
    assert data["source_file_id"] == "033851393"
    assert data["source_rec"]["smoke_events"] == 1
    assert data["golden_linked_rec"]["relation_count"] == 7


def test_smoke_fixture_rejects_unknown_schema(tmp_path):
    data = yaml.safe_load(FIXTURE.read_text())
    data["schema_version"] = "unknown"
    bad = tmp_path / "bad.yaml"
    bad.write_text(yaml.safe_dump(data))
    with pytest.raises(ValueError, match="unsupported"):
        load_smoke_fixture(bad)


def test_independent_textual_golden_is_self_consistent():
    data = json.loads(GOLDEN.read_text())
    assert data["schema_version"] == "fcc_tau_smoke_golden_v1"
    assert data["provenance"]["independent_of_consolidated_implementation"] is True
    assert len(data["relations"]) == 7
    assert len(data["direct"]) == data["collection_counts"]["PandoraPFOs"] == 4
    assert len(data["ancestor"]) == 4
