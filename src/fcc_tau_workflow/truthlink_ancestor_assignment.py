"""Deterministic promotion of frozen direct truth-link assignments.

The direct PFO-to-MC decision is an immutable input. This module only walks
the MC parent graph and, when needed, promotes it to the nearest selected truth
ancestor. It never inspects or re-reduces relation weights.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AncestorAssignment:
    status: str
    assigned_mc_index: int | None
    ancestor_depth: int | None
    n_selected_at_nearest_depth: int


def _assert_acyclic(parents: list[list[int]], start: int) -> None:
    state: dict[int, int] = {}

    def visit(index: int) -> None:
        mark = state.get(index, 0)
        if mark == 1:
            raise ValueError("cycle in MC ancestry")
        if mark == 2:
            return
        state[index] = 1
        for parent in parents[index]:
            visit(int(parent))
        state[index] = 2

    visit(int(start))


def assign_selected_ancestor(
    direct_status: str,
    direct_mc_index: int | None,
    parents: list[list[int]],
    selected_indices: set[int],
) -> AncestorAssignment:
    """Map one frozen direct assignment to its nearest selected ancestor."""
    if direct_status != "assigned" or direct_mc_index is None:
        return AncestorAssignment("direct_unassigned", None, None, 0)

    start = int(direct_mc_index)
    _assert_acyclic(parents, start)
    if start in selected_indices:
        return AncestorAssignment("same_direct_selected", start, 0, 1)

    frontier = {int(value) for value in parents[start]}
    visited = {start}
    depth = 1
    while frontier:
        candidates = sorted(frontier & selected_indices)
        if len(candidates) == 1:
            return AncestorAssignment("promoted_unique_ancestor", candidates[0], depth, 1)
        if len(candidates) > 1:
            return AncestorAssignment("ancestor_orphan_ambiguous", None, depth, len(candidates))
        visited.update(frontier)
        frontier = {
            int(parent)
            for index in frontier
            for parent in parents[index]
            if int(parent) not in visited
        }
        depth += 1
    return AncestorAssignment("ancestor_no_selected_ancestor", None, None, 0)
