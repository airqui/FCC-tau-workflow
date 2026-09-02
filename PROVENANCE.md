# Provenance

## Consolidation source

- Stage: 2, core workflow port, 2026-09-02.
- Authoritative read-only snapshot:
  `/lhome/ific/a/airqui/FCC/archive/consolidation_20260901/snapshots/ild-tau_pre_consolidation_20260901`
- Source repository HEAD at validation: `59243f2e3069b5da5afa134a535d2d880a6a7027`.
- Stage-0 snapshot validation: PASS, zero mismatches.
- Per-file source hash, classification, destination and action:
  `provenance/source_port_manifest.csv`.

The manifest records 48 inspected authoritative or exclusion-relevant source
files, of which 27 are port origins. `REFERENCE_ONLY` and `NOT_PORTED` entries
are evidence, not runtime dependencies.

## Frozen software and detector

- Key4hep release: `2026-08-21`.
- Validated IFIC setup:
  `/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2026-08-21/x86_64-almalinux9-gcc14.2.0-opt/key4hep-stack/2026-08-21-5qmpe6/setup.sh`.
- Detector: `ILD_FCCee_v01`.
- Geometry SHA-256:
  `ab48a78ef69f6ee417233e34cffa75a0fd41742fb02130c57303f402abd87e29`.
- ILDConfig commit: `279b180a88597e45dfaf84f35d1b8b5358300079`.
- MarlinReco linker commit: `fe8e9e2d08b47048e639c072b7bce97f9847f7d1`.

The large ILDConfig checkout is deliberately not vendored. The bootstrap
script installs it into an external cache and checks out the exact commit.

## Scientific preservation

The authoritative `truthlink_assignment.py` and
`truthlink_ancestor_assignment.py` modules, the REC-only linker steering and
the two frozen YAML assignment contracts were copied byte-for-byte. Their
source hashes are recorded in the port manifest and their installed hashes are
frozen in `configs/truthlink/code_checksums.sha256`.

Extractor and unit-test changes are import-path-only. Shell and Condor changes
replace historical workspace paths with repository-derived paths and explicit
runtime configuration. The L_ancestor extractor is a core-only wrapper around
the unchanged frozen module and contract; analysis-only tau genealogy fields
were not imported. No assignment, detector, simulation or reconstruction
scientific rule was changed.

## Deliberate exclusions

The port excludes G/geometrical matching, HitAnalysis, migration matrices,
tau-topology, PID, PFO-efficiency, photon-origin audits, plots, PDFs, production
ROOT/Parquet outputs and historical pilot/trial submit files. The separately
consolidated TausFCCee checkout is not imported and is not a runtime dependency.
