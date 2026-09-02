# Workflow troubleshooting

Each entry gives the observed symptom, likely cause, diagnostic, and safe
resolution. Do not weaken contracts or overwrite products to make a check pass.

## Key4hep setup missing or wrong

- **Symptom:** `env.sh` reports an unreadable setup, commands are missing, or
  versions differ.
- **Cause:** `KEY4HEP_SETUP` is absent/wrong or a non-validated stack was used.
- **Diagnostic:** `test -r "$KEY4HEP_SETUP"`; after sourcing, run
  `command -v ddsim k4run podio-dump`.
- **Resolution:** point `KEY4HEP_SETUP` to the recorded 2026-08-21 setup. A
  different site override needs separate validation.

## ILDConfig commit mismatch

- **Symptom:** `env.sh` says ILDConfig is unavailable or not at the validated
  commit.
- **Cause:** missing checkout, wrong checkout, or an altered dependency root.
- **Diagnostic:** `git -C "$ILDCONFIG_ROOT" rev-parse HEAD`.
- **Resolution:** set a clean dependency root and run
  `scripts/workflow/bootstrap_ildconfig.sh`; expected commit is
  `279b180a88597e45dfaf84f35d1b8b5358300079`.

## Geometry hash mismatch

- **Symptom:** `env.sh` reports an unexpected SHA-256.
- **Cause:** wrong compact geometry or software stack.
- **Diagnostic:** `sha256sum "$COMPACT_FILE"`.
- **Resolution:** use `ILD_FCCee_v01` from the validated stack; expected hash is
  `ab48a78ef69f6ee417233e34cffa75a0fd41742fb02130c57303f402abd87e29`.

## SIM unreadable

- **Symptom:** `podio-dump` fails, the file is empty, or reconstruction exits.
- **Cause:** failed/interrupted `ddsim`, corrupt input, or incomplete transfer.
- **Diagnostic:** `test -s "$SIM_FILE"`, inspect `ddsim.log` and run
  `podio-dump -e 0 "$SIM_FILE"`.
- **Resolution:** preserve the failed product for diagnosis, resolve input or
  storage failure, and rerun into a new clean target.

## REC lacks PandoraPFOs or required relations

- **Symptom:** reconstruction/linker reports a missing `PandoraPFOs`, track,
  cluster, simulated-hit, or hit-relation collection.
- **Cause:** incompatible reconstruction configuration or wrong input file.
- **Diagnostic:** `podio-dump -e 0 "$REC_FILE"` and compare with
  `scripts/workflow/run_truthlink_linker_v1.py`.
- **Resolution:** use a REC produced by the validated ILD chain. Do not rename
  collections in the contract.

## Truth-link relation missing or empty

- **Symptom:** `RecoMCTruthLinkTruthlinkV1` is absent/empty or every PFO has
  `truthlink_orphan_no_relation`.
- **Cause:** the validated post-linker has not run, or required inputs were
  empty/incompatible.
- **Diagnostic:** inspect the linked REC with `podio-dump`, then the direct
  summary's candidate counts.
- **Resolution:** run Mode A after verifying required collections. Automatic
  skip/run detection is desired future behavior and is not implemented.

## RecoMCTruthLinker collection mismatch

- **Symptom:** `k4run` reports an unknown input collection.
- **Cause:** REC schema differs from `linker_collections_v1`.
- **Diagnostic:** compare `podio-dump -e 0` output with the YAML and steering.
- **Resolution:** use a compatible REC or stop for a reviewed contract update;
  do not silently substitute a similar collection.

## Output relation collision

- **Symptom:** writer/processor reports an existing output collection or the
  steering refuses an existing linked REC.
- **Cause:** linker already ran or target path is reused.
- **Diagnostic:** inspect the input collection inventory and `test -e` on the
  target.
- **Resolution:** if the required relation is already populated, preserve it
  and assess whether it is validated; otherwise choose a new output. Do not
  overwrite.

## L_direct ambiguous or no relation

- **Symptom:** `truthlink_orphan_ambiguous` or
  `truthlink_orphan_no_relation` appears.
- **Cause:** an exact unresolved candidate tie, or no persisted relation.
- **Diagnostic:** inspect candidate rows, T/C integers, decision branch, and
  ambiguity reason.
- **Resolution:** retain the status as a valid outcome. Never introduce an
  MC-index, PDG, order, or floating-tolerance tie-break.

## L_ancestor has no selected ancestor

- **Symptom:** `ancestor_no_selected_ancestor`.
- **Cause:** no stored parent chain reaches selected truth.
- **Diagnostic:** inspect direct MC index and stored parents.
- **Resolution:** retain the status; it is not automatically a processing
  failure and must not be promoted arbitrarily.

## Ancestry cycle

- **Symptom:** fatal `cycle in MC ancestry`.
- **Cause:** malformed cyclic stored-parent graph.
- **Diagnostic:** isolate the event/source/PFO from the error and inspect its
  parent indices.
- **Resolution:** quarantine and report the input. Do not disable the cycle
  check.

## Manifest or schema mismatch

- **Symptom:** missing columns, unsupported contract/version, duplicate source
  ID, or queue-size assertion.
- **Cause:** wrong manifest type/version or incomplete product set.
- **Diagnostic:** run `python scripts/validation/validate_contracts.py` and
  compare headers with the chosen template/contract.
- **Resolution:** regenerate the manifest from authoritative inputs; do not
  edit counts or versions merely to satisfy the check.

## Event identity failure

- **Symptom:** duplicate PFO keys, invalid source ID, or cross-file joins fail.
- **Cause:** `source_file_id` is not the required nine digits, event positions
  were renumbered, or a derived integer was used as authority.
- **Diagnostic:** check `(sample, source_file_id, event_in_file, pfo_index)`.
- **Resolution:** restore source-local event positions and composite identity.

## Condor path or configuration failure

- **Symptom:** jobs are held, executable/input is missing, or logs cannot open.
- **Cause:** wrong `repo_root`, `manifest`, `log_dir`, invisible shared path, or
  missing environment variables on the worker.
- **Diagnostic:** use `condor_submit -dry-run`, inspect `.err`, `.out`, event
  log, and `HoldReason`.
- **Resolution:** fix macros/directories and validate one manifest row before
  submitting. Do not resubmit a partial output set.
