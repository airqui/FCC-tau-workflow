# FCC-tau TrackMerger study

## Purpose

This directory records the first FCC-tau TrackMerger campaign and its frozen
2000-event Pandora/tau benchmark. The campaign tested whether the current
TrackMerger prototype can be carried through the existing FCC-tau chain and
measured its downstream performance relative to the `MarlinTrkTracks`
baseline.

The definitive campaign status is:

```text
PASS WITH UNDERSTOOD WIP LIMITATIONS
```

The B chain works technically end to end:

```text
RefittedGreedyMergedTracks
  -> Pandora
  -> equivalent RecoMCTruthLink wiring
  -> frozen L_direct
  -> frozen L_ancestor
  -> maintained FCC-tau comparison analysis
```

Its charged-particle reconstruction performance is nevertheless substantially
worse than the current `MarlinTrkTracks` baseline. See
[BENCHMARK_V1.md](BENCHMARK_V1.md) for the fixed identity and headline
results.

## Campaign history

- **TM-0:** preflight and architecture audit.
- **TM-0.5:** stable-compatible TrackMerger backport validation.
- **TM-1 / TM-1b:** three-event and ten-event tracking-only smoke tests.
- **TM-1c:** read-only diagnosis; severe refit hit loss correlated strongly
  with incompatible helix parameters whose matching tolerances were disabled.
- **TM-2P:** official-nightly provenance gate.
- **TM-2A:** 100-event official-nightly audit; 130/237 greedy candidates had
  severe refit hit loss.
- **TM-3A:** attempted parent-truth diagnostic; persisted REC provided
  `NO_DEFENSIBLE_PARENT_TRUTH_PATH`. Parent-truth debugging was not required
  for the primary benchmark.
- **Pandora smoke:** Pandora accepted `RefittedGreedyMergedTracks`.
- **Truth-link smoke and repair:** the initial B primary linker remained
  Marlin-based; equivalent B-specific wiring to the greedy-refitted track
  collection passed the technical gate.
- **benchmark2000:** definitive downstream A/B performance benchmark on 2000
  identical SIM events.

Developer feedback identifies `RefittedGreedyMergedTracks` as the collection
to use. It is therefore the primary TrackMerger benchmark collection;
`RefittedAmbiguousMergedTracks` is not the primary performance target.

## Current status

Benchmark v1 establishes that the prototype is executable through
reconstruction, Pandora, truth linking, L_direct, L_ancestor and the
maintained analysis. It also establishes a material loss of charged-particle
efficiency and resolution, including inside the 10--170 degree TPC-covered
proxy. The degradation must not be attributed solely to the known
forward/SET limitation.

This is a frozen descriptive benchmark. It does not claim a cause and does
not define optimized TrackMerger settings.

## Known limitations and current implementation

- **Known WIP limitation:** SET is not included.
- **Known WIP limitation:** forward completion is incomplete.
- **Known WIP limitation:** unmatched tracks are omitted from the greedy
  merged collection.
- **Known current implementation:** matching uses d0/z0 only; phi, omega and
  tanLambda tolerances are disabled.
- **TM-2 observation:** 130/237 greedy candidates showed severe refit hit
  loss.

Secondary diagnostics support further study of the d0/z0-only matching:

- severe loss: 130/237 (54.85%);
- opposite omega sign: 103/130 severe candidates (79.23%) versus 5/91 full
  candidates (5.49%);
- median absolute wrapped delta-phi: 3.014 severe versus 0.00734 full;
- median absolute delta-tanLambda: 0.878 severe versus 0.000389 full.

These observations are diagnostic context only. They do not establish parent
MC truth and are not proposed optimized cuts.

## What is frozen

- benchmark identity and the A/B reconstruction products listed in
  [BENCHMARK_V1.md](BENCHMARK_V1.md);
- the 2000-event SIM input and existing A REC;
- A uses `MarlinTrkTracks` for both Pandora and the primary
  `RecoMCTruthLinker`;
- B uses `RefittedGreedyMergedTracks` for both Pandora and the primary
  `RecoMCTruthLinker`;
- `FullRecoRelation = true` and the B track relation
  `RefittedGreedyMergedTracksMCTruthLink`;
- the scientific definitions `G`, `L_direct`, `L_ancestor`, `TruthlinkV1`,
  `truthlink_assignment_v1` and `truthlink_ancestor_assignment_v1`;
- the maintained analysis implementation at commit
  `a85f4fae5666089562ca3dafe25a81d99381db93`.

## Parked / not required for benchmark v1

- parent truth for `SiTracksCT` / `ClupatraTracks`;
- optimization of phi/omega/tanLambda matching;
- omega-sign compatibility study;
- greedy first-match optimization;
- ambiguous-mode performance optimization;
- SET completion;
- forward completion;
- unmatched-track arbitration;
- TrackMerger algorithm modifications.

These questions do not block rerunning the frozen comparison with a future
TrackMerger revision.

## Future TrackMerger revisions

For future revisions:

1. Reuse the same SIM.
2. Reuse the existing A REC; do not reconstruct A unless an explicit
   repeatability study is authorized.
3. Build only a new B with the new TrackMerger revision.
4. Preserve equivalent Pandora and primary `RecoMCTruthLinker` wiring to the
   B track collection.
5. Run exactly the same maintained FCC-tau analysis.
6. Compare the result against benchmark v1.

Detailed external artifacts and machine-readable summaries are indexed in
[BENCHMARK_V1.md](BENCHMARK_V1.md).

Future benchmark reruns should follow [FUTURE_TRACKMERGER_BENCHMARK.md](FUTURE_TRACKMERGER_BENCHMARK.md).
