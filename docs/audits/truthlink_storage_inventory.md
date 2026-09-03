# TruthLink / TruthLinkV1 Storage Inventory

Audit date: 2026-09-03

This is a read-only audit of real files under `/lustre/ific.uv.es/prj/gl/abehep.flc/FCC`.
No linker, assignment, reconstruction, Condor, or DDSim job was run. The audit
inspected ROOT keys and EDM4hep collection listings with ROOT and `podio-dump`.

This document is dated storage evidence, not a campaign-completeness contract.
Current code, machine-readable configuration, and the maintained workflow
documentation remain authoritative. The `TruthlinkV1` suffix below identifies
the maintained output collection namespace; it is not a different linker
algorithm.

## EXECUTIVE CONCLUSION

**Persistent TruthLinkV1 files already exist. Storage is mixed.**

The observed storage contains both:

- canonical files named `*_REC.edm4hep.root`; and
- retained files named `*_REC_truthlinked_v1.edm4hep.root` containing the four
  requested TruthLinkV1 relation families.

Therefore the maintained production model is not accurately described as
"only REC files, with TruthLink always regenerated on demand". Mode A remains
the documented regeneration path, but retained linked REC products are
physically present for W, P8C, and P8O.

**Classification: C - MIXED_STORAGE_MODEL**

## DATA SOURCES INSPECTED

Maintained documentation read before interpreting the files:

- `FCC-tau-workflow/docs/QUICKSTART.md`
- `FCC-tau-workflow/docs/RECONSTRUCTION_CHAIN.md`
- `FCC-tau-workflow/docs/TRUTH_LINKING_AND_ASSIGNMENT.md`
- `FCC-tau-workflow/docs/DATASETS_AND_PROVENANCE.md`

Real storage roots inspected:

- `/lustre/ific.uv.es/prj/gl/abehep.flc/FCC/ILD20260821_2k`
- `/lustre/ific.uv.es/prj/gl/abehep.flc/FCC/ILD20260730`
- `/lustre/ific.uv.es/prj/gl/abehep.flc/FCC/samples_pythia_20260821`

The inventory search found 2,012 REC-like ROOT files in these storage trees,
including 1,004 under `ILD20260821_2k`, 997 under `ILD20260730`, and 18 in the
Pythia storage tree. It found 7 files whose paths explicitly identify retained
TruthLinkV1 linked REC products: 5 W files, 1 P8C file, and 1 P8O file.

## ROOT FILE INVENTORY

| Path | Size | Mtime | Sample/campaign | Notes |
|---|---:|---|---|---|
| `/lustre/ific.uv.es/prj/gl/abehep.flc/FCC/ILD20260821_2k/outputs/events_000242385/events_000242385_REC.edm4hep.root` | 1,522,303,332 bytes | 2026-08-22 01:05:32 +0200 | W / ILD20260821_2k | Canonical REC; 2,000 ROOT event entries |
| `/lustre/ific.uv.es/prj/gl/abehep.flc/FCC/ILD20260821_2k/truthlink_assignment_v1/shareable_truthlinked_REC_10k/events_000242385_REC_truthlinked_v1.edm4hep.root` | 1,535,046,494 bytes | 2026-08-25 17:08:19 +0200 | W / ILD20260821_2k | Retained linked REC; 2,000 ROOT event entries |
| `/lustre/ific.uv.es/prj/gl/abehep.flc/FCC/samples_pythia_20260821/truthlink_assignment_v1_collab/retained_truthlinked_REC/P8C_suffix1_truthlinked_v1.edm4hep.root` | 755,168,485 bytes | 2026-08-26 12:48:26 +0200 | P8C / Pythia 20260821 | Retained linked REC; 1,000 ROOT event entries |
| `/lustre/ific.uv.es/prj/gl/abehep.flc/FCC/samples_pythia_20260821/truthlink_assignment_v1_ourReco/retained_truthlinked_REC/P8O_suffix1_truthlinked_v1.edm4hep.root` | 755,175,159 bytes | 2026-08-26 12:48:26 +0200 | P8O / Pythia 20260821 | Retained linked REC; 1,000 ROOT event entries |

Additional exact path evidence from the retained-file search:

- W retained files: 5 under `ILD20260821_2k/truthlink_assignment_v1/shareable_truthlinked_REC_10k/`.
- P8C retained files: `P8C_suffix1_truthlinked_v1.edm4hep.root`.
- P8O retained files: `P8O_suffix1_truthlinked_v1.edm4hep.root`.

## PARQUET INVENTORY

The physical storage contains association Parquet products in addition to ROOT
files. Counts from the actual paths were:

| Storage area | Direct assignment | Ancestor assignment | Candidate relations |
|---|---:|---:|---:|
| W `ILD20260821_2k/truthlink_assignment_v1` | 997 | 0 in the inspected naming subset | 997 |
| Pythia `samples_pythia_20260821` | 118 | 118 | 118 |

Across the broader FCC storage search, filename-pattern counts were 1,114
`*_pfo_assignment.parquet`, 1,114 `*_ancestor_assignment.parquet`, and 1,114
`*_candidate_relations.parquet`. These counts are inventory counts, not claims
that every file belongs to one campaign or that every product is complete.

In particular, pathname counts in this audit do not replace the validated
996-input W campaign inventory. Historical, retained, partial, or differently
partitioned products can coexist under the broader storage roots.

Representative real Parquet paths include:

- `/lustre/ific.uv.es/prj/gl/abehep.flc/FCC/ILD20260821_2k/truthlink_assignment_v1/candidate_relations/events_000242385_candidate_relations.parquet`
- `/lustre/ific.uv.es/prj/gl/abehep.flc/FCC/samples_pythia_20260821/truthlink_assignment_v1_ourReco/P8O_suffix1_candidate_relations.parquet`
- `/lustre/ific.uv.es/prj/gl/abehep.flc/FCC/samples_pythia_20260821/truthlink_assignment_ancestor_v1_ourReco/P8O_suffix1_ancestor_assignment.parquet`

The last path preserves historical on-disk naming and must not be interpreted
as the canonical assignment identifier, which is
`truthlink_ancestor_assignment_v1`.

## EDM4HEP COLLECTION AUDIT

### Canonical W REC

Inspected file:

`/lustre/ific.uv.es/prj/gl/abehep.flc/FCC/ILD20260821_2k/outputs/events_000242385/events_000242385_REC.edm4hep.root`

ROOT reported 2,000 event entries. `podio-dump -e 0` reported:

| Collection | Event-zero object count | Observation |
|---|---:|---|
| `MCParticles` | 40 | Present |
| `PandoraPFOs` | 4 | Present |
| `MarlinTrkTracks` | 2 | Present |
| `PandoraClusters` | 4 | Present |
| `RecoMCTruthLink` | 0 | Legacy relation present, empty in event 0 |
| `MCTruthRecoLink` | 0 | Legacy relation present, empty in event 0 |
| `MarlinTrkTracksMCTruthLink` | 0 | Legacy relation present, empty in event 0 |
| `ClusterMCTruthLink` | 0 | Legacy relation present, empty in event 0 |
| `RecoMCTruthLinkTruthlinkV1` | absent | Not listed |
| `MCTruthRecoLinkTruthlinkV1` | absent | Not listed |
| `MarlinTrkTracksMCTruthLinkTruthlinkV1` | absent | Not listed |
| `ClusterMCTruthLinkTruthlinkV1` | absent | Not listed |

This is direct EDM4hep evidence that the inspected canonical REC does not
contain the requested V1 collections, despite containing legacy relation
collections.

### Retained W linked REC

Inspected file:

`/lustre/ific.uv.es/prj/gl/abehep.flc/FCC/ILD20260821_2k/truthlink_assignment_v1/shareable_truthlinked_REC_10k/events_000242385_REC_truthlinked_v1.edm4hep.root`

ROOT reported 2,000 event entries. The event tree listed all four requested
V1 collection names:

- `RecoMCTruthLinkTruthlinkV1`
- `MCTruthRecoLinkTruthlinkV1`
- `MarlinTrkTracksMCTruthLinkTruthlinkV1`
- `ClusterMCTruthLinkTruthlinkV1`

It also listed `MCParticles`, `PandoraPFOs`, `MarlinTrkTracks`, and
`PandoraClusters`, plus the corresponding legacy collections and the V1
calorimeter-hit truth-link collection. This is direct ROOT-key evidence that
the linked file is an augmented REC, not merely a renamed canonical REC.

### P8C and P8O retained linked REC

The event trees of both inspected files listed all four requested V1 names and
the four principal input collections:

- P8C: `/lustre/ific.uv.es/prj/gl/abehep.flc/FCC/samples_pythia_20260821/truthlink_assignment_v1_collab/retained_truthlinked_REC/P8C_suffix1_truthlinked_v1.edm4hep.root`, 1,000 event entries.
- P8O: `/lustre/ific.uv.es/prj/gl/abehep.flc/FCC/samples_pythia_20260821/truthlink_assignment_v1_ourReco/retained_truthlinked_REC/P8O_suffix1_truthlinked_v1.edm4hep.root`, 1,000 event entries.

The collection names were obtained from ROOT event-tree branches, not inferred
from the filenames.

## REC VS LINKED REC COMPARISON

For the W representative pair:

| Property | Canonical REC | Retained linked REC |
|---|---:|---:|
| ROOT event entries | 2,000 | 2,000 |
| File size | 1,522,303,332 | 1,535,046,494 |
| `MCParticles` | present, 40 in event 0 | present |
| `PandoraPFOs` | present, 4 in event 0 | present |
| `MarlinTrkTracks` | present, 2 in event 0 | present |
| `PandoraClusters` | present, 4 in event 0 | present |
| Four requested V1 families | absent | present |

The larger linked file and added V1 branches are consistent with an augmented
REC. The inspected pair has equal event counts and preserves the principal
pre-existing collections. A complete all-event object-by-object equality proof
was not performed in this audit.

## CAMPAIGN MATRIX

| Campaign | REC present in inspected storage | Linked REC present | L_direct present | L_ancestor present |
|---|---|---|---|---|
| W / ILD20260821_2k | Yes; 997 canonical REC files | Yes; 5 retained linked files found | Yes; 997 assignment products found | Not established from the W naming subset inspected |
| P8C / samples_pythia_20260821 | Yes; collaborator/source products are present in the Pythia tree | Yes; 1 retained linked file found | Yes; Pythia association products present | Yes; Pythia ancestor products present |
| P8O / samples_pythia_20260821 | Yes; 18 `*_REC.edm4hep.root` files in the our-reco tree | Yes; 1 retained linked file found | Yes; P8O assignment products present | Yes; P8O ancestor products present |
| ILD20260730 | Yes; 997 canonical REC files | No retained V1 linked file found by the explicit linked-name search | Not established | Not established |

The matrix is based on real filesystem entries and explicit product searches.
"Not established" means the audit did not claim absence where the inspected
naming/partition did not provide a complete product manifest.

## COUNTER-EVIDENCE

Evidence against `A - SINGLE_REC_ONLY`:

- Five W files physically exist under a retained linked REC directory and list
  all four requested V1 collection names.
- A P8C retained linked REC file lists all four requested V1 collection names.
- A P8O retained linked REC file lists all four requested V1 collection names.

Evidence against `B - PERSISTED_LINKED_REC` as a universal model:

- The inspected W canonical REC has no requested V1 collections, while its
  retained linked counterpart does.
- The storage contains large populations of canonical `*_REC.edm4hep.root`
  files separate from the retained linked products.
- The older `ILD20260730` tree contains 997 canonical REC files, and the
  explicit retained-linked filename search found no linked V1 file there.

These observations support campaign- and product-dependent persistence rather
than a uniform storage policy.

## LIMITATIONS

- ROOT and `podio-dump` inspection was performed on representative W, P8C, and
  P8O files, not every one of the 2,012 REC-like files.
- ROOT event-tree branch names establish collection presence; full event-wide
  relation cardinalities for every file were not computed.
- Event-zero object counts are reported where `podio-dump` output was captured;
  they must not be interpreted as whole-file relation counts.
- Some broad inventory commands were affected by an oversized inherited
  `PATH`; those failed commands were not used as evidence. The successful
  ROOT, `podio-dump`, `find`, `stat`, and direct linked-file searches provide
  the evidence used here.
- Product counts based on filename patterns may include partial or differently
  named outputs. They are inventory counts, not completeness certification.
- No claim is made that every retained linked file is from a complete or
  validated campaign solely because it contains the V1 collections.

## FINAL CLASSIFICATION

**C - MIXED_STORAGE_MODEL**

TruthLinkV1 is already stored in current FCC storage: at least the 7 retained
linked ROOT files identified above contain `RecoMCTruthLinkTruthlinkV1`,
`MCTruthRecoLinkTruthlinkV1`, `MarlinTrkTracksMCTruthLinkTruthlinkV1`, and
`ClusterMCTruthLinkTruthlinkV1`. Canonical REC files also coexist and, in the
inspected W example, lack those V1 collections. Consequently, some products
require REC-only regeneration while others already have persistent linked REC.

## RECOMMENDATION

For any new analysis, inspect the actual REC or linked REC event tree before
running the linker. Treat a file as already TruthLinkV1-linked only after
verifying the required collection names and nonzero relation counts with
EDM4hep tooling. Retain the linked REC when complete relation products are
needed; do not infer its existence from a campaign directory or filename.
