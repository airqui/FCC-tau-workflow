from pathlib import Path
import pytest
from fcc_tau_workflow.truthlinked_preflight import REQUIRED_COLLECTIONS, inspect_events, require_stable_file

class FakeEvent:
    def __init__(self, sizes=None):
        self.sizes = {name: 1 for name in REQUIRED_COLLECTIONS}; self.sizes.update(sizes or {})
    def getAvailableCollections(self): return list(self.sizes)
    def get(self, name): return range(self.sizes[name])

def test_event_preflight_counts_every_collection():
    result = inspect_events([FakeEvent(), FakeEvent()], 2)
    assert result["events"] == 2
    assert result["collection_entries"]["RecoMCTruthLinkTruthlinkV1"] == 2

def test_event_preflight_rejects_missing_and_globally_empty():
    missing = FakeEvent(); del missing.sizes["PandoraPFOs"]
    with pytest.raises(ValueError, match="missing collections"): inspect_events([missing], 1)
    with pytest.raises(ValueError, match="empty over all events"): inspect_events([FakeEvent({"ClusterMCTruthLinkTruthlinkV1": 0})], 1)

def test_stability_gate(tmp_path: Path):
    path = tmp_path / "linked.root"; path.write_bytes(b"not empty")
    with pytest.raises(RuntimeError, match="require 300s stability"): require_stable_file(path, 300, now=path.stat().st_mtime + 1)
    assert require_stable_file(path, 0).size == 9
