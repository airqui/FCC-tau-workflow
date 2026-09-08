"""Read-only preflight helpers for completed TruthlinkV1 REC products."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import time

REQUIRED_COLLECTIONS = (
    "MCParticles", "PandoraPFOs", "RecoMCTruthLinkTruthlinkV1",
    "MCTruthRecoLinkTruthlinkV1", "MarlinTrkTracksMCTruthLinkTruthlinkV1",
    "ClusterMCTruthLinkTruthlinkV1",
)

@dataclass(frozen=True)
class StableFile:
    path: Path
    size: int
    mtime_ns: int

def require_stable_file(path: Path, minimum_age_seconds: int, *, now: float | None = None) -> StableFile:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    stat = path.stat()
    if stat.st_size <= 0:
        raise ValueError(f"empty input: {path}")
    age = (time.time() if now is None else now) - stat.st_mtime
    if age < minimum_age_seconds:
        raise RuntimeError(f"input is only {age:.1f}s old; require {minimum_age_seconds}s stability before reading: {path}")
    return StableFile(path=path, size=stat.st_size, mtime_ns=stat.st_mtime_ns)

def inspect_events(events, expected_events: int) -> dict:
    collection_entries = Counter()
    nonempty_events = Counter()
    event_count = 0
    for event_count, event in enumerate(events, start=1):
        available = set(event.getAvailableCollections())
        missing = set(REQUIRED_COLLECTIONS) - available
        if missing:
            raise ValueError(f"event {event_count - 1}: missing collections {sorted(missing)}")
        for name in REQUIRED_COLLECTIONS:
            count = len(list(event.get(name)))
            collection_entries[name] += count
            nonempty_events[name] += int(count > 0)
    if event_count != expected_events:
        raise ValueError(f"event count {event_count} != expected {expected_events}")
    for name in REQUIRED_COLLECTIONS:
        if collection_entries[name] == 0:
            raise ValueError(f"collection is empty over all events: {name}")
    return {"events": event_count, "collection_entries": dict(collection_entries), "nonempty_events": dict(nonempty_events)}

def require_unchanged(before: StableFile) -> None:
    after = before.path.stat()
    if (after.st_size, after.st_mtime_ns) != (before.size, before.mtime_ns):
        raise RuntimeError(f"input changed while being inspected: {before.path}")
