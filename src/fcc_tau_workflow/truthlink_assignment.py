"""Deterministic PFO -> MC reduction for ``truthlink_assignment_v1``.

The reducer consumes the complete per-PFO candidate set produced by
RecoMCTruthLinker with ``FullRecoRelation=true``.  Track and cluster components
remain separate integer permille quantities throughout the decision.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Optional

ASSIGNED = "assigned"
ORPHAN_NO_RELATION = "truthlink_orphan_no_relation"
ORPHAN_AMBIGUOUS = "truthlink_orphan_ambiguous"
VALID_STATUSES = frozenset({ASSIGNED, ORPHAN_NO_RELATION, ORPHAN_AMBIGUOUS})


@dataclass(frozen=True)
class TruthCandidate:
    mc_index: int
    pdg: int
    charge: float
    generator_status: int
    created_in_simulation: bool
    raw_weight: int
    track_permille: int
    cluster_permille: int

    @property
    def track_component(self) -> float:
        return self.track_permille / 1000.0

    @property
    def cluster_component(self) -> float:
        return self.cluster_permille / 1000.0

    @classmethod
    def from_packed(
        cls,
        *,
        mc_index: int,
        pdg: int,
        charge: float,
        generator_status: int,
        created_in_simulation: bool,
        raw_weight: int | float,
    ) -> "TruthCandidate":
        packed, track_permille, cluster_permille = decode_packed_weight(raw_weight)
        return cls(
            mc_index=int(mc_index),
            pdg=int(pdg),
            charge=float(charge),
            generator_status=int(generator_status),
            created_in_simulation=bool(created_in_simulation),
            raw_weight=packed,
            track_permille=track_permille,
            cluster_permille=cluster_permille,
        )


@dataclass(frozen=True)
class AssignmentResult:
    status: str
    candidate: Optional[TruthCandidate]
    decision_branch: str
    ambiguity_reason: str
    n_candidates: int
    n_track_candidates: int
    n_maxT_ties: int
    n_maxC_ties: int
    neutral_tiebreak_used: bool

    def __post_init__(self) -> None:
        if self.status not in VALID_STATUSES:
            raise ValueError(f"invalid assignment status: {self.status}")
        if (self.status == ASSIGNED) != (self.candidate is not None):
            raise ValueError("assigned status and selected candidate disagree")


def decode_packed_weight(raw_weight: int | float) -> tuple[int, int, int]:
    """Decode the audited exact packed relation representation.

    ``W = 10000 * clusterPermille + trackPermille``.  Persisted weights are
    exactly integral floats in the frozen EDM4hep sample.  Refusing a
    non-integral value prevents tolerance-dependent tie behaviour.
    """
    value = float(raw_weight)
    if not math.isfinite(value) or value < 0 or value != int(value):
        raise ValueError(f"packed weight must be a finite non-negative integer: {raw_weight!r}")
    packed = int(value)
    return packed, packed % 10000, packed // 10000


def _result(
    status: str,
    candidate: Optional[TruthCandidate],
    branch: str,
    reason: str,
    candidates: list[TruthCandidate],
    track_candidates: list[TruthCandidate],
    n_maxT_ties: int,
    n_maxC_ties: int,
    neutral_tiebreak_used: bool,
) -> AssignmentResult:
    return AssignmentResult(
        status=status,
        candidate=candidate,
        decision_branch=branch,
        ambiguity_reason=reason,
        n_candidates=len(candidates),
        n_track_candidates=len(track_candidates),
        n_maxT_ties=n_maxT_ties,
        n_maxC_ties=n_maxC_ties,
        neutral_tiebreak_used=neutral_tiebreak_used,
    )


def assign_truth_to_pfo(pfo_relations: Iterable[TruthCandidate]) -> AssignmentResult:
    """Apply the frozen, order-invariant ``truthlink_assignment_v1`` rule."""
    candidates = list(pfo_relations)
    mc_indices = [candidate.mc_index for candidate in candidates]
    if len(mc_indices) != len(set(mc_indices)):
        raise ValueError("duplicate MC candidate for one PFO")
    if not candidates:
        return _result(
            ORPHAN_NO_RELATION, None, "none", "no_valid_relation",
            candidates, [], 0, 0, False,
        )

    track_candidates = [c for c in candidates if c.track_permille > 0]
    if track_candidates:
        max_t = max(c.track_permille for c in track_candidates)
        max_t_candidates = [c for c in track_candidates if c.track_permille == max_t]
        if len(max_t_candidates) == 1:
            return _result(
                ASSIGNED, max_t_candidates[0], "track_maxT", "",
                candidates, track_candidates, 1, 1, False,
            )
        max_c = max(c.cluster_permille for c in max_t_candidates)
        finalists = [c for c in max_t_candidates if c.cluster_permille == max_c]
        if len(finalists) == 1:
            return _result(
                ASSIGNED, finalists[0], "track_maxT_then_maxC", "",
                candidates, track_candidates, len(max_t_candidates), 1, False,
            )
        return _result(
            ORPHAN_AMBIGUOUS, None, "track_maxT_then_maxC",
            "track_maxT_maxC_exact_tie", candidates, track_candidates,
            len(max_t_candidates), len(finalists), False,
        )

    max_c = max(c.cluster_permille for c in candidates)
    max_c_candidates = [c for c in candidates if c.cluster_permille == max_c]
    if len(max_c_candidates) == 1:
        return _result(
            ASSIGNED, max_c_candidates[0], "cluster_maxC", "",
            candidates, track_candidates, 0, 1, False,
        )

    neutral_candidates = [c for c in max_c_candidates if c.charge == 0.0]
    if len(neutral_candidates) == 1:
        return _result(
            ASSIGNED, neutral_candidates[0], "cluster_maxC_neutral_priority", "",
            candidates, track_candidates, 0, len(max_c_candidates), True,
        )
    if len(neutral_candidates) > 1:
        reason = "cluster_maxC_multiple_neutral_exact_tie"
    else:
        reason = "cluster_maxC_multiple_charged_exact_tie"
    return _result(
        ORPHAN_AMBIGUOUS, None, "cluster_maxC_neutral_priority", reason,
        candidates, track_candidates, 0, len(max_c_candidates), True,
    )
