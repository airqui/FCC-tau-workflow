# Workflow quick start

This is the one-file golden path. L_direct selects one immediate MC contributor
per PFO when the frozen rule is unambiguous; L_ancestor maps that result to the
nearest unique selected generator-level ancestry. Commands below that run
simulation, reconstruction, truth linking, or assignment perform real
processing and write outputs. Use writable external output directories and run
them only after the preceding checks pass.

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
python -m venv --system-site-packages "$FCC_TAU_DEPENDENCY_ROOT/venv"
source "$FCC_TAU_DEPENDENCY_ROOT/venv/bin/activate"
python -m pip install --no-build-isolation -e .
```

`env.sh` checks the ILDConfig commit and geometry hash. At IFIC its default is
the frozen Key4hep `2026-08-21` CVMFS setup. At another site, set
`KEY4HEP_SETUP` and `COMPACT_FILE` explicitly; that is an override, not a claim
that another stack has been validated. The virtual environment inherits the
read-only Key4hep packages while keeping the editable installation in the
external dependency directory.
`env.sh` is idempotent for the same repository clone, so maintained wrappers
can validate the environment without duplicating Key4hep library paths.

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
export INPUT=/path/to/events_033851393.stdhep.gz
export FILE_STEM=$(basename "$INPUT" .gz)
export FILE_STEM=${FILE_STEM%.stdhep}
export SAMPLE_LABEL=W
export SOURCE_ID=033851393
export FCC_TAU_PRODUCTION=/path/to/writable/campaign
export FCC_TAU_OUTPUT="$FCC_TAU_PRODUCTION/outputs"
export FCC_TAU_TMP="$FCC_TAU_PRODUCTION/tmp"
mkdir -p "$FCC_TAU_PRODUCTION" "$FCC_TAU_OUTPUT" "$FCC_TAU_TMP"
```

For a one-event smoke job:

```bash
scripts/workflow/run_chain.sh "$INPUT" 1
```

`run_chain.sh` performs real simulation and reconstruction: it runs the
maintained `ddsim` command followed by `k4run ILDReconstruction.py`. It refuses
pre-existing SIM/REC outputs unless `--force` is explicitly supplied. Verify
the input and output paths before running it, and do not use `--force` without
reviewing the target files.

The outputs are:

```text
$FCC_TAU_OUTPUT/<FILE_STEM>/<FILE_STEM>_SIM.edm4hep.root
$FCC_TAU_OUTPUT/<FILE_STEM>/<FILE_STEM>_REC.edm4hep.root
```

## 5. Inspect SIM and REC

```bash
export SIM="$FCC_TAU_OUTPUT/$FILE_STEM/${FILE_STEM}_SIM.edm4hep.root"
export REC="$FCC_TAU_OUTPUT/$FILE_STEM/${FILE_STEM}_REC.edm4hep.root"
test -s "$SIM" && test -s "$REC"
podio-dump -e 0 "$SIM"
podio-dump -e 0 "$REC"
```

Confirm the expected event count and the collections listed in
[Reconstruction chain](RECONSTRUCTION_CHAIN.md#validation-after-each-stage).

`FILE_STEM` is the filename-derived stem used by `run_chain.sh` for output
paths. `SAMPLE_LABEL` is the physics/campaign label passed to association
products, such as `W` or `P8O`; it is not a filename. For a W-style
`events_033851393...` source, use `SOURCE_ID=033851393`. Reuse that exact
stable ID for every REC, L_direct, L_ancestor, summary, and manifest entry
derived from the source file. Other datasets must define an equally
deterministic stable identifier compatible with their campaign contract.

If you already have a SIM named `out_sim_edm4hep_N.root`, the maintained
SIM-to-REC-only command is:

```bash
export FCC_TAU_PYTHIA_SIM_ROOT=/path/to/sim
export FCC_TAU_PYTHIA_RECO_ROOT=/path/to/writable/reconstruction
scripts/workflow/run_pythia_reco_job.sh \
  "$FCC_TAU_PYTHIA_SIM_ROOT/out_sim_edm4hep_1.root" 0.0
```

This command performs real reconstruction, requires the exact filename
pattern, and preserves the SIM event count with `--num-events=-1`. Verify its
input and new output location before running it.

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

This command performs real REC-only truth linking and assignment. Replace the
final `1` with the exact REC event count. Passing `-` means the temporary
truth-linked REC is not retained; pass a non-existing target path there only
when the augmented REC must be preserved.

## 7. Build L_ancestor

```bash
mkdir -p "$PRODUCTS/ancestor" "$PRODUCTS/ancestor_summaries"
condor/wrappers/run_lancestor_job.sh \
  "$SAMPLE_LABEL" "$SOURCE_ID" "$REC" \
  "$PRODUCTS/direct/${SOURCE_ID}_Ldirect.parquet" \
  "$PRODUCTS/ancestor/${SOURCE_ID}_Lancestor.parquet" \
  "$PRODUCTS/ancestor_summaries/${SOURCE_ID}_Lancestor.json" 1
```

This command performs real ancestry assignment and writes outputs. Use the
same exact event count and `SOURCE_ID` as L_direct.

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

The workflow owns both `fcc_tau_association_v1` and
`fcc_tau_workflow_product_manifest_v1`. Copy the maintained example and replace
its data paths with the products created above:

```bash
cp configs/examples/workflow_product_manifest_v1.example.yaml \
  /path/to/writable/products.yaml
```

The complete example names the sample label, stable `source_file_id`, source
REC, L_direct Parquet, L_ancestor Parquet, truth-definition version, and
provenance summary. The authoritative event identity is
`(sample, source_file_id, event_in_file)`; add `pfo_index` or `mc_index` for
object identity. Transfer the data or make those paths visible to the analysis
job; never add a Python import or clone-relative absolute path.

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

## 11. Consume a completed externally produced TruthlinkV1 REC

For the KKMCee 2k campaign, first run the all-event stability/collection
preflight documented in [Datasets and provenance](DATASETS_AND_PROVENANCE.md).
Only after it passes, create new local output directories and invoke the
generic maintained extractors; no linker rerun is needed:

```bash
export LINKED_REC=/path/to/completed_2k_REC_TruthlinkV1.edm4hep.root
export PRODUCTS=/path/to/new/kkmcee_material/derived
mkdir -p "$PRODUCTS"
python scripts/workflow/extract_truthlink_assignments.py \
  --linked-rec "$LINKED_REC" --source-rec "$LINKED_REC" \
  --source-file-id 700000001 --expected-events 2000 \
  --assignment-output "$PRODUCTS/KKMCee_2k_pfo_assignment.parquet" \
  --candidate-output "$PRODUCTS/KKMCee_2k_candidate_relations.parquet" \
  --summary-output "$PRODUCTS/KKMCee_2k_direct_summary.json"
python scripts/workflow/extract_lancestor_assignments.py \
  --sample KKMCee --source-file-id 700000001 \
  --source-rec "$LINKED_REC" \
  --direct-assignment "$PRODUCTS/KKMCee_2k_pfo_assignment.parquet" \
  --ancestor-output "$PRODUCTS/KKMCee_2k_ancestor_assignment.parquet" \
  --summary-output "$PRODUCTS/KKMCee_2k_ancestor_summary.json" \
  --expected-events 2000
```

These commands perform L_direct reduction and L_ancestor promotion with the
frozen implementations. They refuse existing outputs. The two repositories
remain data-coupled only: transfer the resulting manifest/paths to TausFCCee;
do not import code between clones.
