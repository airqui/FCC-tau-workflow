# TrackMerger Pandora/tau benchmark v1

## Status and scope

**Status: PASS WITH UNDERSTOOD WIP LIMITATIONS.**

`trackmerger_pandora_tau_ab_2000evt_v1` compares two reconstructions of the
same 2000-event SIM input:

- **A:** `MarlinTrkTracks -> Pandora`, with `MarlinTrkTracks` also used by the
  primary `RecoMCTruthLinker`;
- **B:** `RefittedGreedyMergedTracks -> Pandora`, with
  `RefittedGreedyMergedTracks` also used by the primary
  `RecoMCTruthLinker`.

Both primary linkers use `FullRecoRelation = true` and persist
`RecoMCTruthLink` and `MCTruthRecoLink`. B additionally persists
`RefittedGreedyMergedTracksMCTruthLink`. The B-specific wiring is required:
using a Marlin-based primary linker for B does not provide an equivalent
track branch for PFO truth assignment.

No definition of `G`, `L_direct`, `L_ancestor`, `TruthlinkV1`,
`truthlink_assignment_v1` or `truthlink_ancestor_assignment_v1` changed.

## Exact benchmark identity

```text
BENCHMARK_VERSION       trackmerger_pandora_tau_ab_2000evt_v1
SIM_SHA256              1f8adc41bf67f68cd981206abd23bf7d4b8e4a6d6aefa1d3ebb810f1215db5cc
NIGHTLY                 2026-09-16-ca7lev
K4RECTRACKER_SHA        5b048492ebd0a5b780c012854be14be79d497b2d
TRACKMERGER_CPP_SHA256  9f1ac1e1808e8819c4c9f7d3da55921718de0d9e956c89ab4c5b7b9ce457b20f
ILDCONFIG_SHA           a0b43f645e0c27f356d82a37ed0b3f67840f3895
A_STEERING_SHA256       c0e15624650e98c8f0857bcb56d22f8adf634c42dccca4a68f1402fb0552717b
B_STEERING_SHA256       e44c4775c19e937ef025e7bf8172a13e9149d8eeff4b461742f8f066eed21588
ANALYSIS_COMMIT         a85f4fae5666089562ca3dafe25a81d99381db93
ANALYSIS_SCRIPT_SHA256  c25254878e1d51c2b0835052aea621c83ddd02bc9f89fdaa88048f19aeba211e
A_REC_SHA256            c86ac1eda781c206ee3ec29c0e37caf5d8c93d81a83b866db1860a61d433257d
B_REC_SHA256            4a7a7f9e7b9122e4e0ae0dbf1390c352221dfe783e2b14fb28f4ce6a1881d677
```

## Headline results

| Quantity | A: MarlinTrkTracks | B: RefittedGreedyMergedTracks |
|---|---:|---:|
| tracks entering Pandora | 7806 | 4775 |
| total PFOs | 12443 | 12425 |
| charged PFOs | 5648 | 3252 |
| neutral PFOs | 6795 | 9173 |

Tau-origin selected-truth L_ancestor `associated_unique` efficiency:

| Species | A | B | Delta [percentage points] |
|---|---:|---:|---:|
| electron | 97.516% | 96.601% | -0.915 |
| muon | 98.580% | 89.205% | -9.375 |
| charged pion | 96.763% | 92.555% | -4.208 |
| charged kaon | 97.000% | 94.000% | -3.000 |
| combined charged | 5124/5276 = 97.119% | 4892/5276 = 92.722% | -4.397 |
| photon | 81.629% | 80.259% | -1.370 |

Charged kaons are included as a truth association/efficiency species. Kaon
PID performance is not evaluated because the maintained reconstructed-PID
categorization has no dedicated kaon category.

For the descriptive 10--170 degree TPC-covered proxy, combined charged
efficiency changes from 98.037% to 93.587%. Its central-68 widths change as
follows:

| Metric | A | B |
|---|---:|---:|
| dp/p | 0.00765 | 0.09854 |
| delta-theta | 0.480 mrad | 6.157 mrad |
| delta-phi | 2.278 mrad | 97.951 mrad |

The degradation is therefore not confined to the known forward/SET
limitation. This is a numerical observation, not a causal interpretation.

## Truth-assignment integrity

| Frozen result | A | B |
|---|---:|---:|
| L_direct assigned | 12443 | 12422 |
| L_direct ambiguous | 0 | 3 |
| L_direct no_relation | 0 | 0 |
| L_direct track branch | 5648 | 3252 |
| L_direct cluster branch | 6795 | 9173 |
| L_ancestor same/direct selected | 9775 | 9764 |
| L_ancestor promoted unique ancestor | 2630 | 2621 |
| L_ancestor no selected ancestor | 38 | 37 |
| L_ancestor direct unassigned | 0 | 3 |
| invalid references | 0 | 0 |

All 3252 B PFOs carrying greedy tracks have usable greedy-track truth. The
three B ambiguities are frozen exact-tie outcomes.

## Authoritative artifacts

Detailed human-readable report:

```text
/lhome/ific/a/airqui/FCC/TRACKMERGER_PANDORA_TAU_AB_2000EVT.md
```

Machine-readable benchmark summary:

```text
/lhome/ific/a/airqui/FCC/trackmerger_pandora_ab/analysis/benchmark2000/
results/summary/benchmark_summary.json
```

Compact machine-readable products in the same summary directory:

```text
headline_comparison.csv
regional_efficiency_summary.csv
regional_residual_summary.csv
```

The external report and JSON are authoritative for detailed counts,
constituent steering hashes, regional tables, warnings and generated-product
inventory. This repository page is the compact maintained index, not a copy
of the full campaign report.

## Comparison policy for future versions

A future TrackMerger benchmark must:

1. reuse the SIM identified above;
2. reuse the existing A REC and frozen A assignments;
3. avoid reconstructing A unless repeatability is the explicit study target;
4. reconstruct only a new B with the candidate TrackMerger revision;
5. make both Pandora and the primary `RecoMCTruthLinker` consume the new B
   benchmark track collection, preserving `FullRecoRelation = true`;
6. preserve the frozen L_direct and L_ancestor rules and collection semantics;
7. run the same maintained FCC-tau analysis implementation and families;
8. compare the resulting hashes, integrity counts and numerical outputs with
   `trackmerger_pandora_tau_ab_2000evt_v1`.

The following are parked and are not prerequisites for such a rerun: parent
truth for `SiTracksCT`/`ClupatraTracks`, matching optimization, omega-sign
studies, greedy first-match or ambiguous-mode optimization, SET/forward
completion, unmatched-track arbitration and TrackMerger algorithm changes.
