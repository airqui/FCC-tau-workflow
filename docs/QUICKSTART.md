# Workflow quick start

This is the one-file golden path. L_direct selects one immediate MC contributor per PFO when the frozen rule is unambiguous; L_ancestor maps that result to nearest unique selected generator-level ancestry. Commands that run simulation,
reconstruction, truth linking, or assignment are labelled **NOT EXECUTED IN
STAGE 4**; run them only with writable external output directories and after
the checks immediately above them pass.

## 1. Clone

```bash
git clone YOUR_FCC_TAU_WORKFLOW_URL FCC-tau-workflow
cd FCC-tau-workflow
```

The editable install supplies `fcc_tau_workflow`. It does not install Key4hep.

## 2. Bootstrap ILDConfig and load the validated stack

Choose a dependency directory outside the clone:

```bash
export FCC_TAU_DEPENDENCY_ROOT="$PWD/../fcc-tau-dependencies"
scripts/workflow/bootstrap_ildconfig.sh
source scripts/workflow/env.sh
python -m pip install -e .
```

`env.sh` checks the ILDConfig commit and geometry hash. At IFIC its default is
the frozen Key4hep `2026-08-21` CVMFS setup. At another site, set
`KEY4HEP_SETUP` and `COMPACT_FILE` explicitly; that is an override, not a claim
that another stack has been validated.

## 3. Inspect the frozen configuration

```bash
python scripts/validation/validate_contracts.py
sha256sum "$COMPACT_FILE"
git -C "$ILDCONFIG_ROOT" rev-parse HEAD
```

Expected geometry SHA-256 is
`ab48a78ef69f6ee417233e34cffa75a0fd41742fb02130c57303f402abd87e29`;
expected ILDConfig commit is
`279b180a88597e45dfaf84f35d1b8b5358300079`.

## 4. Produce SIM and REC from one STDHEP file

Set portable external paths; do not put event data in the clone:

```bash
export INPUT=/path/to/events_XXXXXXXXX.stdhep.gz
export FCC_TAU_PRODUCTION=/path/to/writable/campaign
export FCC_TAU_OUTPUT="$FCC_TAU_PRODUCTION/outputs"
export FCC_TAU_TMP="$FCC_TAU_PRODUCTION/tmp"
mkdir -p "$FCC_TAU_PRODUCTION" "$FCC_TAU_OUTPUT" "$FCC_TAU_TMP"
```

For a one-event smoke job:

```bash
scripts/workflow/run_chain.sh "$INPUT" 1
```

**NOT EXECUTED IN STAGE 4.** `run_chain.sh` runs the maintained `ddsim` command
followed by `k4run ILDReconstruction.py`. It refuses pre-existing SIM/REC
outputs unless `--force` is explicitly supplied. Do not use `--force` without
reviewing the target files.

The outputs are:

```text
$FCC_TAU_OUTPUT/<sample>/<sample>_SIM.edm4hep.root
$FCC_TAU_OUTPUT/<sample>/<sample>_REC.edm4hep.root
```

## 5. Inspect SIM and REC

```bash
export SOURCE_ID=000000001
export SAMPLE=$(basename "$INPUT" .gz)
export SAMPLE=${SAMPLE%.stdhep}
export SIM="$FCC_TAU_OUTPUT/$SAMPLE/${SAMPLE}_SIM.edm4hep.root"
export REC="$FCC_TAU_OUTPUT/$SAMPLE/${SAMPLE}_REC.edm4hep.root"
test -s "$SIM" && test -s "$REC"
podio-dump -e 0 "$SIM"
podio-dump -e 0 "$REC"
```

Confirm the expected event count and the collections listed in
[Reconstruction chain](RECONSTRUCTION_CHAIN.md#validation-after-each-stage).

If you already have a SIM named `out_sim_edm4hep_N.root`, the maintained
SIM-to-REC-only command is:

```bash
export FCC_TAU_PYTHIA_SIM_ROOT=/path/to/sim
export FCC_TAU_PYTHIA_RECO_ROOT=/path/to/writable/reconstruction
scripts/workflow/run_pythia_reco_job.sh \
  "$FCC_TAU_PYTHIA_SIM_ROOT/out_sim_edm4hep_1.root" 0.0
```

**NOT EXECUTED IN STAGE 4.** This command requires the exact filename pattern
and preserves the SIM event count with `--num-events=-1`.

## 6. Add truth links and build L_direct

The validated mode runs the linker over REC and immediately extracts L_direct.
Create empty output directories first:

```bash
export PRODUCTS=/path/to/writable/products
mkdir -p "$PRODUCTS/direct" "$PRODUCTS/candidates" "$PRODUCTS/summaries"
condor/wrappers/run_truthlink_assignment_job.sh \
  "$SOURCE_ID" "$REC" \
  "$PRODUCTS/direct/${SOURCE_ID}_Ldirect.parquet" \
  "$PRODUCTS/candidates/${SOURCE_ID}_candidates.parquet" \
  "$PRODUCTS/summaries/${SOURCE_ID}_Ldirect.json" \
  - 1
```

**NOT EXECUTED IN STAGE 4.** Replace the final `1` with the exact REC event
count. Passing `-` means the temporary truth-linked REC is not retained; pass a
non-existing target path there only when the augmented REC must be preserved.

## 7. Build L_ancestor

```bash
mkdir -p "$PRODUCTS/ancestor" "$PRODUCTS/ancestor_summaries"
condor/wrappers/run_lancestor_job.sh \
  W "$SOURCE_ID" "$REC" \
  "$PRODUCTS/direct/${SOURCE_ID}_Ldirect.parquet" \
  "$PRODUCTS/ancestor/${SOURCE_ID}_Lancestor.parquet" \
  "$PRODUCTS/ancestor_summaries/${SOURCE_ID}_Lancestor.json" 1
```

**NOT EXECUTED IN STAGE 4.** Use the same exact event count as L_direct.

## 8. Inspect the products

```bash
python -c 'import pyarrow.parquet as pq,sys; p=pq.ParquetFile(sys.argv[1]); print(p.schema_arrow); print(p.metadata.num_rows)' \
  "$PRODUCTS/direct/${SOURCE_ID}_Ldirect.parquet"
python -c 'import pyarrow.parquet as pq,sys; p=pq.ParquetFile(sys.argv[1]); print(p.schema_arrow); print(p.metadata.num_rows)' \
  "$PRODUCTS/ancestor/${SOURCE_ID}_Lancestor.parquet"
python -m json.tool "$PRODUCTS/summaries/${SOURCE_ID}_Ldirect.json"
python -m json.tool "$PRODUCTS/ancestor_summaries/${SOURCE_ID}_Lancestor.json"
```

The direct and ancestor summaries must report the requested event count and
zero invalid references. See [Truth linking and assignment](TRUTH_LINKING_AND_ASSIGNMENT.md)
for statuses and the versioned data contract.

## 9. Hand products to TausFCCee

Create a small `fcc_tau_workflow_product_manifest_v1` file using the schema in
the analysis repository's `configs/interfaces/example_workflow_product_manifest.yaml`.
It names the source REC, L_direct Parquet, L_ancestor Parquet, truth-definition
version, and provenance summary. Transfer the data or make those paths visible
to the analysis job; never add a Python import or clone-relative absolute path.

## 10. Run the maintained one-event regression smoke test

The IFIC fixture is a read-only one-event slice of an existing REC and has an
independently produced historical golden. Preview the exact input without
running the linker:

```bash
scripts/validation/run_smoke_test.sh \
  --fixture tests/fixtures/manifests/smoke_fixture_v1.yaml \
  --output-root /path/to/new/writable/smoke-output \
  --dry-run
```

To run the local regression, remove `--dry-run`. The output directory must not
already exist. The command runs REC-only truth linking, L_direct and
L_ancestor, verifies preservation of pre-existing REC content, compares with
the independent golden, and writes a data-only product manifest. It does not
run simulation, reconstruction, Condor, or analysis.

The fixture manifest contains site-specific read-only Lustre paths and is
therefore an IFIC regression fixture, not a portable production input.
