# Future TrackMerger benchmark recipe

## Purpose

Use this recipe to compare a future TrackMerger revision with the frozen
FCC-tau benchmark:

```text
frozen A reference
  +-- B v1: trackmerger_pandora_tau_ab_2000evt_v1
  +-- B v2: future TrackMerger revision
  +-- B v3: later TrackMerger revision
```

Routine future studies rebuild only B. They do not repeat the original
campaign or reconstruct A unless repeatability is the explicit study target.
The benchmark registry is [trackmerger_benchmarks.csv](trackmerger_benchmarks.csv).

## Frozen input and A reference

```text
SIM path:
/lustre/ific.uv.es/prj/gl/abehep.flc/FCC/ILD20260821_2k/outputs/
events_000242385/events_000242385_SIM.edm4hep.root

SIM SHA256:
1f8adc41bf67f68cd981206abd23bf7d4b8e4a6d6aefa1d3ebb810f1215db5cc

events:       2000
detector:     ILD_FCCee_v01
cms energy:   91 GeV
```

The authoritative A chain is:

```text
MarlinTrkTracks
  -> Pandora
  -> primary RecoMCTruthLinker using MarlinTrkTracks
```

```text
A REC path:
/lustre/ific.uv.es/prj/gl/abehep.flc/FCC/TrackMerger_Pandora_AB/
nightly_20260916/benchmark2000/A/
events_000242385_A_MarlinTrkTracks_REC.edm4hep.root

A REC SHA256:
c86ac1eda781c206ee3ec29c0e37caf5d8c93d81a83b866db1860a61d433257d

A L_direct:
/lhome/ific/a/airqui/FCC/trackmerger_pandora_ab/audit/benchmark2000/A/direct.parquet

A L_ancestor:
/lhome/ific/a/airqui/FCC/trackmerger_pandora_ab/audit/benchmark2000/A/ancestor.parquet
```

These A products are frozen. Check their hashes and reuse them; do not
reconstruct A for a routine new-B comparison.

## Procedure for a new B

1. Pin the new dated Key4hep nightly. Record its resolved setup path.
2. Record the nightly identifier, k4RecTracker commit, `TrackMerger.cpp`
   SHA256 and ILDConfig commit.
3. Run the one-time, path-limited change sentinel below against the previous
   tested provenance.
4. Inspect only relevant TrackMerger and ILDConfig tracking, Pandora and
   truth-link changes. Do not open an algorithm-development study as part of
   this routine gate.
5. Produce a small B smoke with the developer-designated TrackMerger output
   feeding both Pandora and the primary `RecoMCTruthLinker`.
6. Apply the smoke gate below. Stop if any requirement fails.
7. If it passes, reconstruct only B for the same 2000 SIM events.
8. Produce frozen L_direct and L_ancestor assignments without changing their
   rules.
9. Run the exact frozen maintained analysis configuration and families.
10. Compare the new B with the frozen A and with earlier registered B
    versions.

The result must be described as `same A, same SIM, same analysis; B
software/version changed`.

## B reconstruction and truth-link wiring contract

Pandora and the primary `RecoMCTruthLinker` must consume the same B track
collection. For benchmark v1 this contract is:

```text
Pandora TrackCollections = RefittedGreedyMergedTracks

RecoMCTruthLinker:
  TrackCollection       = RefittedGreedyMergedTracks
  TrackMCTruthLinkName  = RefittedGreedyMergedTracksMCTruthLink
  RecoMCTruthLinkName   = RecoMCTruthLink
  MCTruthRecoLinkName   = MCTruthRecoLink
  FullRecoRelation      = true
```

If developers designate a successor collection, both consumers must use that
successor and the track-relation name must follow it consistently. If a future
ILDConfig provides this wiring natively, use and document the native
configuration. Inspect current ILDConfig first; do not blindly reapply the v1
adapter to changed upstream code.

## Minimum B smoke gate

Before processing 2000 events, require all of the following:

```text
job exit = 0
developer-designated merged/refitted track collection present
PandoraPFOs present
valid PFO track references
valid PFO cluster references
RecoMCTruthLink present
MCTruthRecoLink present
tracked PFOs have usable track truth
track_maxT > 0
invalid references = 0
Pandora track collection == primary RecoMCTruthLinker track collection
```

If any check fails, stop. Do not launch the 2000-event B run.

## Frozen scientific and analysis contract

Preserve without reinterpretation:

```text
G
L_direct
L_ancestor
TruthlinkV1
truthlink_assignment_v1
truthlink_ancestor_assignment_v1
truth selections
efficiency denominators
residual definitions
PID interpretation
analysis families
histogram binning
normalization
```

Do not modify a scientific definition to accommodate a TrackMerger revision.
The frozen analysis identity is:

```text
TausFCCee commit:
a85f4fae5666089562ca3dafe25a81d99381db93

analysis script SHA256:
c25254878e1d51c2b0835052aea621c83ddd02bc9f89fdaa88048f19aeba211e

benchmark-v1 config:
/lhome/ific/a/airqui/FCC/trackmerger_pandora_ab/analysis/benchmark2000/
comparison_config.yaml
```

For a future B, make an isolated config derived from this exact file by
changing only the B product/provenance entries required for the new version.
Do not rewrite its `scientific_contract`, performance bins or association
settings. The benchmark-v1 analysis command was:

```bash
cd /lhome/ific/a/airqui/FCC/TausFCCee
PYTHONPATH=$PWD/src:$PYTHONPATH \
python scripts/analysis/build_mc_comparison.py \
  --comparison trackmerger_pandora_ab_2000 \
  --config /lhome/ific/a/airqui/FCC/trackmerger_pandora_ab/analysis/benchmark2000/comparison_config.yaml \
  --output-root /lhome/ific/a/airqui/FCC/trackmerger_pandora_ab/analysis/benchmark2000/results \
  --families part12 part3 part3b part4 photon_diagnostic performance
```

A future run must use a new, non-colliding output root and the isolated
future-version config while retaining the same comparison implementation and
family list.

## Required headline report

Every new B comparison against frozen A must report at least:

- tracks entering Pandora;
- total, charged and neutral PFOs;
- combined charged association efficiency;
- electron, muon, charged-pion, charged-kaon and photon efficiencies;
- dp/p, delta-theta and delta-phi central-68 half-widths;
- combined charged efficiency in the descriptive 10--170 degree
  TPC-covered proxy;
- corresponding TPC-covered-proxy residual widths.

Use the maintained definitions, denominators and regional proxy. Do not turn
the proxy into a new acceptance definition.

## One-time provenance/change sentinel

Run this once before each campaign, after setting the source paths and new
commits explicitly. These commands inspect only relevant paths; they do not
source software, run reconstruction or modify either checkout.

The monitored paths below are the native paths in the pinned upstream
ILDConfig checkout; they are not FCC-tau-local reorganizations. Together they
cover overall reconstruction activation and sequencing (`ILDReconstruction.py`),
direct TrackMerger configuration (`Tracking/TrackMerging_FCCee.py`), the
FCC/MDI tracking approaches (`Tracking/TrackingReco_FCCeeMDI.py`), Pandora
track-input wiring (`ParticleFlow/PandoraPFA.py`) and RecoMCTruthLinker/
high-level truth wiring (`HighLevelReco/HighLevelReco_FCCee.py`). No single
file is treated as defining the complete TrackMerger workflow.

```bash
PREVIOUS_K4REC_SHA=5b048492ebd0a5b780c012854be14be79d497b2d
PREVIOUS_ILDCONFIG_SHA=a0b43f645e0c27f356d82a37ed0b3f67840f3895
NEW_K4REC_SHA=<new-pinned-k4RecTracker-commit>
NEW_ILDCONFIG_SHA=<new-pinned-ILDConfig-commit>
K4REC_SRC=<path-to-pinned-k4RecTracker-source>
ILDCONFIG_SRC=<path-to-pinned-ILDConfig-source>

git -C "$K4REC_SRC" log --oneline \
  "$PREVIOUS_K4REC_SHA..$NEW_K4REC_SHA" -- \
  Tracking/components/TrackMerger.cpp
git -C "$K4REC_SRC" diff --stat \
  "$PREVIOUS_K4REC_SHA..$NEW_K4REC_SHA" -- \
  Tracking/components/TrackMerger.cpp
sha256sum "$K4REC_SRC/Tracking/components/TrackMerger.cpp"

git -C "$ILDCONFIG_SRC" log --oneline \
  "$PREVIOUS_ILDCONFIG_SHA..$NEW_ILDCONFIG_SHA" -- \
  StandardConfig/production/ILDReconstruction.py \
  StandardConfig/production/Tracking/TrackMerging_FCCee.py \
  StandardConfig/production/Tracking/TrackingReco_FCCeeMDI.py \
  StandardConfig/production/ParticleFlow/PandoraPFA.py \
  StandardConfig/production/HighLevelReco/HighLevelReco_FCCee.py
git -C "$ILDCONFIG_SRC" diff --stat \
  "$PREVIOUS_ILDCONFIG_SHA..$NEW_ILDCONFIG_SHA" -- \
  StandardConfig/production/ILDReconstruction.py \
  StandardConfig/production/Tracking/TrackMerging_FCCee.py \
  StandardConfig/production/Tracking/TrackingReco_FCCeeMDI.py \
  StandardConfig/production/ParticleFlow/PandoraPFA.py \
  StandardConfig/production/HighLevelReco/HighLevelReco_FCCee.py
```

Record the output with the future benchmark provenance. Review actual diffs
only where this sentinel reports a relevant change. No helper script is
maintained because the commands require deliberate, explicit source paths and
revision pins.

## Historical v1 diagnostic context

TM-2 found severe post-refit hit loss for 130/237 greedy candidates. Opposite
omega sign occurred for 103/130 severe-loss and 5/91 full-retention
candidates. In v1, d0/z0 matching was active while phi, omega and tanLambda
tolerances were disabled.

These are historical diagnostics, not future pass/fail criteria and not
proposed matching cuts. The frozen downstream A/B result is the primary
performance reference.

## Outside routine benchmarking

Do not automatically reopen parent truth, omega-sign or other helix-threshold
optimization, greedy first-match optimization, ambiguous-mode performance,
SET/forward completion, unmatched-track arbitration or refitter internals.
Study them only when developers explicitly request algorithm feedback or a
future benchmark shows a new unexplained behavior.

## Versioning policy

Append each accepted result to the adjacent registry. Keep the frozen A, SIM
and analysis identity fixed across the series. If geometry, scientific
definitions or another reconstruction component must also change, the result
is not automatically part of this longitudinal series: give it a new
benchmark version/context and document the extra change explicitly.

The detailed benchmark-v1 result remains in [BENCHMARK_V1.md](BENCHMARK_V1.md);
do not duplicate its full product inventory here.
