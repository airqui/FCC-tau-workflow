# Stage 2 core workflow port

## Scope and result

Stage 2 ports only the maintained workflow from generator input through frozen
truth association:

1. STDHEP to SIM with `ddsim` and `crossingAngleBoost=15.e-3`.
2. SIM to REC with `k4run ILDReconstruction.py`.
3. REC-only `RecoMCTruthLinker`, writing a separate augmented REC.
4. Frozen L_direct assignment.
5. Frozen nearest-selected-ancestor L_ancestor assignment.

The package, scripts, configurations, Condor templates, contracts, provenance
and tests reside in this repository. Data, production outputs and the 1.4-GB
ILDConfig checkout remain external.

## Source-to-target map

`provenance/source_port_manifest.csv` is the authoritative map. It records 48
files inspected and 27 port origins. The principal moves are:

| Source role | Maintained target |
|---|---|
| `modules/truthlink_assignment.py` | `src/fcc_tau_workflow/truthlink_assignment.py` |
| `modules/truthlink_ancestor_assignment.py` | `src/fcc_tau_workflow/truthlink_ancestor_assignment.py` |
| REC-only linker steering | `scripts/workflow/run_truthlink_linker_v1.py` |
| assignment extractors | `scripts/workflow/extract_truthlink_assignments*.py` |
| frozen YAML rules | `configs/truthlink/` |
| production wrappers | `scripts/workflow/` and `condor/wrappers/` |
| submit descriptions | `condor/templates/` |

The `COPIED_UNCHANGED` files are byte-identical. `PORTED_WITH_PATH_REFACTOR`
means repository/import/path portability; any larger wrapper refactor is
explicitly identified in `PROVENANCE.md`.

## Frozen commands and configuration

Simulation retains `ddsim --steeringFile ddsim_steer.py`, detector compact,
input/output, event limit and `--crossingAngleBoost 15.e-3`. The referenced
steering supplies `QGSP_BERT`, 0.1-mm range cut, 1-MeV minimum kinetic energy,
disabled Geant4 decays and saved `Decay` process.

Reconstruction retains `k4run ILDReconstruction.py`,
`--detectorModel=ILD_FCCee_v01`, input SIM, output base and `--num-events=-1`.
The external steering files are pinned by ILDConfig commit and verified by the
bootstrap/environment scripts.

The linker is REC-only, has `FullRecoRelation=true`, reads `PandoraPFOs`,
`MarlinTrkTracks` and `PandoraClusters`, emits
`RecoMCTruthLinkTruthlinkV1`, and keeps all collections. The processor option
is named `MCParticle`; the EDM collection is named `MCParticles`. This is an
upstream interface distinction, not a local schema inconsistency.

## Portability and runtime convention

Shell code derives the repository from `BASH_SOURCE`; Python code uses package
imports and `Path(__file__)` where needed. No runtime source/config imports the
historical ild-tau or TausFCCee workspaces. The IFIC CVMFS path is the validated
site default. IFIC Lustre roots occur only in the explicitly site-specific
campaign record; reusable scripts receive roots as arguments or environment
variables.

Production manifests are external runtime inputs. Version-controlled campaign
YAML documents validated counts, resources, site references and the required
environment variables. Tiny non-sensitive examples are under
`tests/fixtures/manifests/`.

## Validation performed

- Stage-0 snapshot validation: PASS, zero mismatches.
- Exact-copy comparison: PASS for both scientific modules, linker steering,
  assignment contracts and ILDConfig pin.
- Semantic diff: extractor/test changes are import-only; SIM/REC command lines
  are unchanged; remaining changes are portability and core-only orchestration.
- Unit tests in frozen Key4hep environment: 22 passed.
- Python compilation: PASS.
- `bash -n` over every shell script: PASS.
- YAML parsing: PASS for eight files.
- Contract validation: PASS.
- Runtime historical-workspace dependency scan: PASS.

No production data were read or written for this port. No external one-event
Key4hep smoke job was run; Stage 2 validates source, contracts and unit-level
behavior, not a new campaign execution. No commit, remote or push is created.

## Stage boundary

Stage 3 analysis consolidation has not started. G, HitAnalysis and all
high-level scientific/audit products remain deliberately outside this core
repository until separately authorized.
