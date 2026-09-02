# Reconstruction chain

## Purpose and frozen configuration

The maintained production path converts generator STDHEP input into an
EDM4hep simulation file (SIM), then reconstructs that SIM into an EDM4hep REC.
RecoMCTruthLinker later records PFO-to-MC candidate contributors; L_direct
selects an immediate contributor and L_ancestor maps it to nearest unique
selected generator-level ancestry.
The configuration validated for this repository is:

| Item | Frozen value |
|---|---|
| Key4hep | `2026-08-21` |
| Detector | `ILD_FCCee_v01` |
| ILDConfig | `279b180a88597e45dfaf84f35d1b8b5358300079` |
| Geometry SHA-256 | `ab48a78ef69f6ee417233e34cffa75a0fd41742fb02130c57303f402abd87e29` |
| Physics list | `QGSP_BERT` |
| Range cut | `0.1 mm` |
| Minimum kinetic energy | `1 MeV` |
| Geant4 decays | disabled |
| Saved process | `Decay` |
| Crossing-angle boost | `15e-3 rad` |

The machine-readable authorities are
`configs/detector/ild_fccee_v01.yaml`,
`configs/environments/key4hep_2026-08-21.yaml`, and
`configs/detector/ILDConfig.commit`.

## Environment

```bash
export FCC_TAU_DEPENDENCY_ROOT="$PWD/../fcc-tau-dependencies"
scripts/workflow/bootstrap_ildconfig.sh
source scripts/workflow/env.sh
python scripts/validation/validate_contracts.py
```

Key4hep, ROOT, podio, EDM4hep, DD4hep, `ddsim`, `k4run`, and the ILD software
stack are external dependencies. The editable package is installed in the
`--system-site-packages` virtual environment shown in the quick start; pip
cannot install the validated Key4hep stack, and the CVMFS Python prefix is
read-only.

## STDHEP to SIM

`scripts/workflow/run_chain.sh` executes these maintained SIM semantics from
the ILDConfig production directory:

```bash
ddsim --steeringFile ddsim_steer.py \
  --compactFile "$COMPACT_FILE" \
  --inputFiles "$LOCAL_INPUT" \
  --outputFile "$SIM_FILE" \
  --numberOfEvents "$N_EVENTS" \
  --crossingAngleBoost 15.e-3
```

**NOT EXECUTED IN STAGE 4.** Compressed STDHEP is first checked with `gzip -t`
and decompressed into the configured temporary area. The steering file pins
the physics list, range cut, kinetic-energy threshold, Geant4-decay behavior,
and saved process listed above.

## SIM to REC

The same wrapper executes:

```bash
k4run ILDReconstruction.py \
  --detectorModel=ILD_FCCee_v01 \
  --inputFiles="$SIM_FILE" \
  --outputFileBase="$OUTPUT_BASE" \
  --num-events=-1
```

**NOT EXECUTED IN STAGE 4.** In reconstruction, `--num-events=-1` means
process every event already present in the SIM; it does not request a new
generator event count. The SIM-to-REC-only wrapper for Pythia input executes
the same command and verifies that the SIM and REC event counts agree.

## Validation after each stage

### SIM

WHAT: confirm a non-empty, readable EDM4hep file with the requested number of
events.

```bash
test -s "$SIM_FILE"
podio-dump -e 0 "$SIM_FILE"
```

Check the command exit code and `ddsim.log`/`metrics.txt`, then confirm
`MCParticles` and the expected simulated tracker/calorimeter hit collections.
The campaign wrapper records the requested event count and SIM size. A missing
collection is a failed input for reconstruction, not a reason to rename the
collection in the workflow.

### REC

```bash
test -s "$REC_FILE"
podio-dump -e 0 "$REC_FILE"
```

Confirm readability, event-count preservation, `MCParticles`, `PandoraPFOs`,
`MarlinTrkTracks`, and `PandoraClusters`. The REC-only linker also needs the
simulated-hit and tracker-hit relation collections declared in
`scripts/workflow/run_truthlink_linker_v1.py`. For a campaign inventory:

```bash
scripts/validation/validate_outputs.sh "$DATA_ROOT" "$OUTPUT_ROOT"
```

This inventory check reports non-empty REC, partial SIM/REC, and missing
outputs. It does not replace `podio-dump` or the per-job event-count checks.

## Truth-link production modes

### Mode A — current validated mode

**Status: VALIDATED / SUPPORTED**

```text
SIM
 -> REC
 -> REC-only RecoMCTruthLinker
 -> REC with RecoMCTruthLinkTruthlinkV1
 -> L_direct
 -> L_ancestor
```

The validated `ILD_FCCee_v01` REC production did not contain useful populated
`RecoMCTruthLink` relations. Existing REC files do contain the MCParticles,
PFOs, tracks, clusters, simulated hits, and relations needed to run the linker
after reconstruction. Historical REC therefore does not require another
`ddsim` or reconstruction pass. The maintained Mode-A entry point is
`condor/wrappers/run_truthlink_assignment_job.sh`; it creates a temporary
truth-linked REC and extracts L_direct. L_ancestor is then produced by
`condor/wrappers/run_lancestor_job.sh`.

### Mode B — future integrated mode

**Status: SUPPORTED DESIGN / NOT YET REGRESSION-VALIDATED**

```text
SIM
 -> ILD reconstruction including RecoMCTruthLinker in the same job
 -> REC already containing RecoMCTruthLinkTruthlinkV1
 -> L_direct
 -> L_ancestor
```

This mode has not passed the required A/B regression and must not be advertised
as validated production. L_direct and L_ancestor semantics must remain
identical.

The promotion gate starts from the same SIM and compares standard REC plus the
post-linker against an integrated-linker REC. It requires:

- the same event count;
- unchanged pre-existing REC content;
- identical `PandoraPFOs`, tracks, and clusters;
- identical `RecoMCTruthLinkTruthlinkV1` candidate relations;
- identical packed weights;
- identical L_direct output;
- identical L_ancestor output.

Only a passing A/B validation can promote Mode B to `VALIDATED`.

### Desired future workflow behavior

**DESIRED FUTURE WORKFLOW BEHAVIOR — not currently implemented:** if
`RecoMCTruthLinkTruthlinkV1` exists and is non-empty, downstream orchestration
should skip the REC-only linker. If the collection is missing or empty, it
should run the REC-only linker. Current users must inspect the collection and
choose Mode A explicitly.

For the relation and assignment semantics, continue with
[Truth linking and assignment](TRUTH_LINKING_AND_ASSIGNMENT.md).
