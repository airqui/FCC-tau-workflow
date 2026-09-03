# Repository guardrails

`FCC-tau-workflow` owns FCC-ee tau simulation, reconstruction, REC-only
`RecoMCTruthLinker`, L_direct, L_ancestor, workflow contracts/manifests,
Condor support, provenance, and workflow validation.

Before changing maintained behavior, read `README.md` and the relevant pages
under `docs/`, especially `RECONSTRUCTION_CHAIN.md`,
`TRUTH_LINKING_AND_ASSIGNMENT.md`, and `DATASETS_AND_PROVENANCE.md`. Treat the
current repository, machine-readable configs/contracts, and tests as the
authority; do not rely on status snapshots from external handoffs.

Preserve these boundaries:

- the 2026-09-01 scientific freeze and validated reconstruction/linking setup;
- G belongs to `TausFCCee`; L_direct and L_ancestor belong here;
- cross-repository exchange is data-only, with no runtime imports or absolute
  clone dependencies;
- Mode A is validated/supported; Mode B is not regression-validated;
- `truthlink_assignment_v1` and `truthlink_ancestor_assignment_v1` semantics
  must not change as incidental cleanup.

Use the narrowest relevant validators and distinguish dry-runs from real
processing. Do not commit large event products or silently overwrite outputs.
Never claim an unrun test or production step passed.

Final pushes are manual unless the project owner explicitly authorizes one.
Avoid history rewriting and do not alter remotes without explicit approval.
