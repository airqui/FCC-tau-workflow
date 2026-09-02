# Datasets and provenance

## Sample names

- **W:** WHIZARD generation plus our validated ILD reconstruction.
- **P8C:** PYTHIA8 generation plus collaborator reconstruction.
- **P8O:** PYTHIA8 generation plus our validated ILD reconstruction.

The names identify both generator and reconstruction provenance. Do not merge
P8C and P8O merely because their generator is the same.

## Validated W inventory

The frozen W campaign record is `configs/campaigns/ild20260821_2k.yaml`:

- historical generator inventory: 997 files;
- currently available/processed inputs: 996;
- REC files: 996;
- events per file: 2,000;
- total events: 1,992,000;
- known missing generator input: `events_090620005.stdhep.gz`.

The missing input was not invented, substituted, or silently omitted. If it
becomes available, it requires an explicit inventory extension and validation.

## Provenance to retain

For each source file retain, directly or through a versioned manifest:

- sample and `source_file_id`;
- generator/SIM/REC input path or stable dataset identifier;
- event count and input checksum or manifest reference;
- Key4hep release, detector model, ILDConfig commit, and geometry hash;
- assignment version and truth-definition version;
- output paths and output checksums;
- job exit status, runtime, peak memory, and worker when available.

The authoritative event identity is `(sample, source_file_id, event_in_file)`.
Add `pfo_index` or `mc_index` for object identity. Derived packed/Cantor event
integers are never cross-repository primary keys.

## Storage policy

Large generator, SIM, REC, linked REC, and stable shared production products
belong on managed bulk storage such as Lustre. Code, configs, documentation,
small manifests, contracts, and small validation summaries belong in the Git
clone. Do not commit ROOT/EDM4hep, large Parquet, logs, or generated plot trees.

All generic commands take paths through arguments or environment variables.
No personal historical path is a runtime requirement.

## IFIC example

The validated IFIC Key4hep setup is recorded in
`configs/environments/key4hep_2026-08-21.yaml`. The validated campaign YAML
also records the IFIC Lustre locations as provenance. These are site reference
paths, not generic defaults for another installation.

At IFIC, load the verified defaults after bootstrapping ILDConfig:

```bash
source scripts/workflow/env.sh
```

Override storage explicitly for a new campaign:

```bash
export FCC_TAU_DATA=/path/to/stdhep
export FCC_TAU_PRODUCTION=/path/to/writable/campaign
export FCC_TAU_OUTPUT="$FCC_TAU_PRODUCTION/outputs"
export FCC_TAU_TMP="$FCC_TAU_PRODUCTION/tmp"
```

## Input inventory

Preview pending STDHEP inputs without writing a manifest:

```bash
scripts/workflow/prepare_inputs.sh "$FCC_TAU_DATA" "$FCC_TAU_OUTPUT"
```

Write a new manifest only to a non-existing path:

```bash
scripts/workflow/prepare_inputs.sh --write "$MANIFEST" \
  "$FCC_TAU_DATA" "$FCC_TAU_OUTPUT"
```

The script excludes complete REC outputs and reports partial SIM/REC states for
manual review. It refuses to overwrite the manifest.

## Condor usage

Templates are in `condor/templates/`; repository-relative executables are in
`condor/wrappers/`. Templates receive `repo_root`, `log_dir`, and `manifest`
as submit macros. Manifests must match the `queue ... from` columns in the
chosen template, output directories must exist, and shared paths must be
visible on worker nodes because `should_transfer_files = NO`.

For truth-link production, first build a queue from a campaign CSV:

```bash
python scripts/workflow/build_truthlink_queue.py \
  --campaign-manifest "$CAMPAIGN_MANIFEST" \
  --queue-output "$QUEUE" \
  --expected-total "$EXPECTED_TOTAL" \
  --expected-remaining "$EXPECTED_REMAINING"
```

Test exactly one queue row without submission:

```bash
head -n 1 "$QUEUE" > "$ONE_JOB_QUEUE"
mkdir -p "$LOG_DIR"
condor_submit -dry-run /tmp/fcc-truthlink.job.ad \
  -append "repo_root=$PWD" \
  -append "log_dir=$LOG_DIR" \
  -append "queue_file=$ONE_JOB_QUEUE" \
  condor/templates/truthlink_assignment_v1.sub
```

This is a submit-description dry-run; it does not run the linker. After review,
the production form is:

```bash
condor_submit \
  -append "repo_root=$PWD" \
  -append "log_dir=$LOG_DIR" \
  -append "queue_file=$QUEUE" \
  condor/templates/truthlink_assignment_v1.sub
```

**NOT EXECUTED IN STAGE 4.** Apply the same macro pattern to
`tautau.sub`, `pythia_reco.sub`, `pythia_truthlink_assignment_v1.sub`, or
`lancestor_v1.sub`, using exactly the manifest columns declared at the bottom
of that template. Test one row first.

Inspect failures without continuous polling:

```bash
condor_q "$CLUSTER_ID" -nobatch
sed -n '1,200p' "$LOG_DIR"/*.err
sed -n '1,200p' "$LOG_DIR"/*.out
```

Check the Condor event log and wrapper-produced JSON/metrics before retrying.
Never overwrite a partial product set; quarantine or otherwise resolve it
explicitly first.

## Cross-repository product handoff

The workflow exports REC, direct assignment Parquet, ancestor assignment
Parquet, summaries, and a small versioned manifest. TausFCCee consumes those
paths as data. It does not import `fcc_tau_workflow`, and this repository does
not import TausFCCee. See
[Truth linking and assignment](TRUTH_LINKING_AND_ASSIGNMENT.md#9-output-contracts).
