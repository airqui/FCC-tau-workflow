# FCC-ee ILD tau workflow

This repository provides the production and truth-association workflow for
FCC-ee tau samples reconstructed with ILD. Its validated chain is:

`STDHEP -> SIM -> REC -> RecoMCTruthLinkTruthlinkV1 -> L_direct -> L_ancestor -> versioned products`

The linker records candidate contributors; L_direct selects an immediate contributor and L_ancestor maps it to nearest unique selected generator provenance.

The validated environment is Key4hep `2026-08-21`, detector
`ILD_FCCee_v01`, and ILDConfig commit
`279b180a88597e45dfaf84f35d1b8b5358300079`.

## Start here

- [Quick start](docs/QUICKSTART.md): one-file golden path and safe checks.
- [Reconstruction chain](docs/RECONSTRUCTION_CHAIN.md): frozen SIM/REC setup,
  validation, and the two truth-link production modes.
- [Truth linking and assignment](docs/TRUTH_LINKING_AND_ASSIGNMENT.md):
  RecoMCTruthLinker, packed weights, L_direct, L_ancestor, and contracts.
- [Datasets and provenance](docs/DATASETS_AND_PROVENANCE.md): W, P8C, P8O,
  campaign inventory, storage, and reproducibility.
- [Troubleshooting](docs/TROUBLESHOOTING.md): known failure symptoms and fixes.
- [Stage-2 port record](docs/README_STAGE2_CORE.md): migration provenance and
  internal validation boundary.

## Repository structure

- `scripts/workflow/`: environment, SIM/REC, linker, and product extractors.
- `scripts/validation/`: maintained static and campaign-output checks.
- `src/fcc_tau_workflow/`: frozen L_direct/L_ancestor decision modules and the
  association contract.
- `configs/`: validated environment, detector, campaigns, and truth-link rules.
- `condor/templates/` and `condor/wrappers/`: batch descriptions and executable
  entry points.
- `tests/`: unit tests and small synthetic manifests.
- `provenance/`: source mapping and checksums.

## Boundary with TausFCCee

This repository does **not** contain high-level tau physics analysis, G
geometric matching, HitAnalysis, or scientific plots. Those live in the
separate `TausFCCee` analysis repository.

The interface between the repositories is data only: this workflow exports
REC files, manifests, and L_direct/L_ancestor Parquet products; TausFCCee reads
those products. There are no Python imports or absolute paths between clones.

## Dependencies and validation

Key4hep supplies ROOT, podio, EDM4hep, `ddsim`, `k4run`, and the ILD stack; pip
does not install them. The Key4hep Python prefix is read-only, so create the
documented external virtual environment after sourcing the stack, then install
only this package:

```bash
python -m venv --system-site-packages "$FCC_TAU_DEPENDENCY_ROOT/venv"
source "$FCC_TAU_DEPENDENCY_ROOT/venv/bin/activate"
python -m pip install --no-build-isolation -e .
```

For repository-only validation that does not run production:

```bash
python scripts/validation/validate_contracts.py
python -m pytest -q tests/unit
(cd "$(git rev-parse --show-toplevel)" && \
  sha256sum --check configs/truthlink/code_checksums.sha256)
```
