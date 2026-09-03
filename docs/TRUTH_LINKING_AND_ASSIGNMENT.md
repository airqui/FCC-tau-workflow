# Truth linking and assignment

## 1. Overview

This document defines the validated path from reconstructed objects to
versioned association products. A reconstructed particle-flow object (PFO) can
have several MC contributors. `RecoMCTruthLinker` persists those candidate
relations; L_direct reduces them to at most one immediate contributor; and
L_ancestor optionally promotes that contributor to selected generator-level
provenance.

These definitions differ from G, the geometric association maintained in
TausFCCee:

- **G:** geometric selected-truth association.
- **L_direct:** immediate detector-level MC contributor.
- **L_ancestor:** selected generator-level provenance reached through stored
  MC parents.

They answer different questions, are complementary diagnostics, and are not
interchangeable definitions of truth.

## 2. What RecoMCTruthLinker provides

`RecoMCTruthLinker` does not choose one final truth particle per PFO. With
`FullRecoRelation=true`, it writes every persisted PFO-to-MC candidate
contributor and its packed track/cluster weight. L_direct makes the later,
explicit reduction.

`TruthlinkV1` is the maintained suffix used to keep these output collections
separate from pre-existing relation names. It is a collection-naming and
provenance convention, not a different `RecoMCTruthLinker` algorithm. The
configured flow is:

```text
RecoMCTruthLinker -> candidate relation collections -> RecoMCTruthLinkTruthlinkV1 -> L_direct -> L_ancestor
```

## 3. Running the REC-only linker

Two truth-link production modes are defined:

- **Mode A — VALIDATED / SUPPORTED:** `SIM -> REC -> REC-only
  RecoMCTruthLinker -> REC with RecoMCTruthLinkTruthlinkV1 -> L_direct ->
  L_ancestor`.
- **Mode B — SUPPORTED DESIGN / NOT YET REGRESSION-VALIDATED:** `SIM ->
  reconstruction with RecoMCTruthLinker in the same job -> REC already
  containing RecoMCTruthLinkTruthlinkV1 -> L_direct -> L_ancestor`.

Mode B must not be presented as validated production until the documented A/B
gate demonstrates identical relation candidates and packed weights, unchanged
pre-existing REC content, and identical L_direct/L_ancestor outputs. The full
gate is in [Reconstruction chain](RECONSTRUCTION_CHAIN.md#mode-b--future-integrated-mode).

**DESIRED FUTURE WORKFLOW BEHAVIOR — not currently implemented:** skip the
REC-only linker when `RecoMCTruthLinkTruthlinkV1` already exists and is
non-empty; otherwise run it. Current operation uses Mode A explicitly.

For one file, the maintained wrapper runs both the REC-only linker and the
L_direct extractor:

```bash
export SOURCE_ID=033851393
export INPUT_REC=/data/events_033851393_REC.edm4hep.root
export ASSIGNMENT_PARQUET=/data/033851393_Ldirect.parquet
export CANDIDATE_PARQUET=/data/033851393_Ldirect_candidates.parquet
export SUMMARY_JSON=/data/033851393_Ldirect.json
export RETAINED_LINKED_REC_OR_DASH=-
export EXPECTED_EVENTS=2000
condor/wrappers/run_truthlink_assignment_job.sh \
  "$SOURCE_ID" "$INPUT_REC" \
  "$ASSIGNMENT_PARQUET" "$CANDIDATE_PARQUET" "$SUMMARY_JSON" \
  "$RETAINED_LINKED_REC_OR_DASH" "$EXPECTED_EVENTS"
```

This command performs real truth linking and assignment and writes outputs.
For this W-style wrapper, `SOURCE_ID` must be exactly nine decimal digits. For
`events_033851393...`, use `SOURCE_ID=033851393` and reuse it for every product
derived from that source. Other dataset wrappers must supply a deterministic
stable identifier compatible with their campaign contract. Output parents
must already exist and every output target must be absent. Use `-` for the
retained-REC argument to discard the temporary linked REC after successful
extraction.

The steering itself reads environment variables:

```bash
export LINKED_REC=/data/events_033851393_REC_truthlinked.edm4hep.root
export TRUTHLINK_INPUT_REC="$INPUT_REC"
export TRUTHLINK_OUTPUT_REC="$LINKED_REC"
export TRUTHLINK_EVTMAX="$EXPECTED_EVENTS"
k4run scripts/workflow/run_truthlink_linker_v1.py
```

The steering command performs real processing. Prefer the wrapper because it
verifies code checksums, constrains threading, manages scratch, and validates
the products.

## 4. Collections used

The validated configuration is `configs/truthlink/linker_collections_v1.yaml`:

| Role | Name |
|---|---|
| PFO | `PandoraPFOs` |
| Tracks | `MarlinTrkTracks` |
| Clusters | `PandoraClusters` |
| EDM MC collection | `MCParticles` |
| Processor MC parameter | `MCParticle` |
| PFO-to-MC output | `RecoMCTruthLinkTruthlinkV1` |
| MC-to-PFO output | `MCTruthRecoLinkTruthlinkV1` |
| Track-to-MC output | `MarlinTrkTracksMCTruthLinkTruthlinkV1` |
| Cluster-to-MC output | `ClusterMCTruthLinkTruthlinkV1` |

`MCParticle` is the Marlin processor parameter value; `MCParticles` is the EDM
collection exposed by podio. The singular/plural distinction is intentional,
not a typo. The steering also names the required tracker-hit and calorimeter-hit
relation inputs, writes the configured reverse and hit-level relation names,
and keeps every pre-existing collection in the output REC. The L_direct
extractor consumes `RecoMCTruthLinkTruthlinkV1`; the other collections remain
persisted supporting relations and are not alternate L_direct inputs.

## 5. FullRecoRelation

`FullRecoRelation=true` preserves the full candidate set. Setting it false
would change the input to L_direct and is not the validated contract. The
candidate Parquet therefore contains all persisted relations, while the
assignment Parquet has exactly one status row per `PandoraPFO`.

## 6. Packed weight encoding

For each relation:

```text
W = 10000 * clusterPermille + trackPermille
T = int(W) % 10000
C = int(W) // 10000
```

`T` and `C` are permille-like integer components. The reported fractional
components are `T/1000` and `C/1000`; L_direct compares the integers exactly.

Examples:

- `W=700` decodes to `T=700`, `C=0`.
- `W=2500400` decodes to `T=400`, `C=250` because
  `2500400 = 10000*250 + 400`.

A packed value of zero still represents an existing relation with `T=0` and
`C=0`. Non-integral, negative, or non-finite weights are rejected. No floating
tolerance participates in L_direct.

## 7. L_direct

L_direct (`truthlink_assignment_v1`) treats each PFO independently.

**Track branch.** If any candidate has `T>0`, only T-positive candidates
compete. Largest T wins. An exact T tie is reduced by largest C. If more than
one candidate still shares the exact maximum T and C, the status is
`truthlink_orphan_ambiguous`.

**Cluster branch.** If no candidate has `T>0`, largest C wins. On an exact
maximum-C tie, a unique candidate whose stored MCParticle charge is exactly
`0.0` wins. Zero or multiple neutral candidates leave
`truthlink_orphan_ambiguous`.

**Other cases.** No candidate relation gives
`truthlink_orphan_no_relation`. A packed-zero candidate is still a relation
and participates in the cluster branch. There is no MC-index, PDG,
collection-order, or floating-tolerance tie-break.

Small examples:

- Candidates `(MC 4,T=700,C=5)` and `(MC 9,T=600,C=900)` select MC 4: the
  track branch compares T first.
- `(MC 4,T=700,C=5)` and `(MC 9,T=700,C=8)` select MC 9 after the exact T tie.
- Two candidates with `T=0,C=500`, one charged and one neutral, select the
  unique stored-neutral candidate.
- Two neutral candidates with the same maximum `C` are ambiguous; their MC
  indices do not break the tie.

A *candidate contributor* is one linker relation. A *final L_direct
assignment* is the result of applying the frozen reducer to all candidates for
one PFO.

## 8. L_ancestor

L_ancestor (`truthlink_ancestor_assignment_v1`) takes L_direct as immutable
input. It does not re-read or re-rank packed relation weights.

1. If L_direct is unassigned, status is `direct_unassigned`.
2. If the direct MCParticle already satisfies selected truth, keep it at depth
   0 with status `same_direct_selected`.
3. Otherwise perform breadth-first search through stored parents.
4. At the nearest depth containing selected-truth ancestors, exactly one gives
   `promoted_unique_ancestor`; more than one gives
   `ancestor_orphan_ambiguous`.
5. If no selected ancestor exists, status is
   `ancestor_no_selected_ancestor`.
6. A cycle is fatal. No arbitrary tie-break is applied.

L_ancestor is useful for studying selected generator-level provenance. It is
not universally “the true association.”

Run it with:

```bash
export SAMPLE_LABEL=W
export SOURCE_REC="$INPUT_REC"
export ANCESTOR_PARQUET=/data/033851393_Lancestor.parquet
export ANCESTOR_SUMMARY=/data/033851393_Lancestor.json
condor/wrappers/run_lancestor_job.sh \
  "$SAMPLE_LABEL" "$SOURCE_ID" "$SOURCE_REC" "$ASSIGNMENT_PARQUET" \
  "$ANCESTOR_PARQUET" "$ANCESTOR_SUMMARY" "$EXPECTED_EVENTS"
```

This command performs real ancestry assignment and writes outputs. It must use
the same `SAMPLE_LABEL`, `SOURCE_ID`, source REC, and event count as L_direct.

## 9. Output contracts

`configs/truthlink/assignment_v1.yaml` preserves the validated W production
configuration and assignment provenance, including W-specific campaign counts.
It is not the universal cross-sample interface. The authoritative
machine-readable cross-sample contract is
`src/fcc_tau_workflow/contracts/association_v1.yaml`, named
`fcc_tau_association_v1`. The analysis consumer accepts the workflow-owned
`fcc_tau_workflow_product_manifest_v1` document. Identity fields are:

- event: `(sample, source_file_id, event_in_file)`;
- PFO: add `pfo_index`;
- truth: add `mc_index`.

`sample` identifies W/P8C/P8O, `source_file_id` identifies the source file,
`event_in_file` is its zero-based event position, and indices identify the PFO
or MCParticle within that event. Assignment status, truth-definition version,
source REC, event count, and input/checksum provenance must accompany the
products. Packed or Cantor integer event IDs are convenience fields only.

Maintained W-style manifest example (replace the data paths for a real run):

```yaml
schema_version: fcc_tau_workflow_product_manifest_v1
association_contract: fcc_tau_association_v1
sample: W
products:
  - source_file_id: "033851393"
    source_rec: /data/events_033851393_REC.edm4hep.root
    direct_assignment: /data/033851393_Ldirect.parquet
    ancestor_assignment: /data/033851393_Lancestor.parquet
    truth_definition_version: selected_truth_v1
    input_provenance: /data/033851393_Ldirect.json
```

The same example is available at
`configs/examples/workflow_product_manifest_v1.example.yaml`. The paths are
user-supplied data locations, not paths to either repository.

## 10. Validation

```bash
python scripts/validation/validate_contracts.py
python -m pytest -q tests/unit
(cd "$(git rev-parse --show-toplevel)" && \
  sha256sum --check configs/truthlink/code_checksums.sha256)
```

For produced files, require the exact event count, one assignment row per PFO,
zero invalid references and duplicate PFO keys, a complete status partition,
matching candidate counts, readable Parquet, and PASS summaries. L_ancestor
also requires a complete PFO join to L_direct and zero invalid genealogy
references.

## 11. Batch examples

See [Datasets and provenance](DATASETS_AND_PROVENANCE.md#condor-usage) for
template variables, a one-row dry-run, submission, and log inspection.

## 12. Common failure modes

Missing/empty relations usually mean the post-linker was not run or its input
collections are absent. Ambiguous L_direct or L_ancestor statuses are valid
scientific outcomes, not job failures. Missing products, schema mismatches,
cycles, invalid references, and event-count mismatches are failures. Detailed
symptom/cause/resolution entries are in [Troubleshooting](TROUBLESHOOTING.md).
