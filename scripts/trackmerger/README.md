# Future TrackMerger B benchmark runner

This directory provides a small fail-closed driver for repeating the frozen
FCC-tau comparison with a new TrackMerger B. It does not reconstruct the
frozen A and does not generate or alter TrackMerger/ILDConfig steering.

The maintained scientific recipe is
[`docs/trackmerger/FUTURE_TRACKMERGER_BENCHMARK.md`](../../docs/trackmerger/FUTURE_TRACKMERGER_BENCHMARK.md).
The driver centralizes paths, provenance, dry-run commands and safety gates;
that document remains authoritative for the benchmark contract.

## What do I edit when a new TrackMerger arrives?

Copy the example to a campaign-owned location outside the repository:

```bash
cp scripts/trackmerger/config/future_benchmark.example.env \
  /path/to/new-campaign/trackmerger_future.env
```

Edit only that copy. Supply the new nightly/setup, pinned k4RecTracker and
ILDConfig checkouts/commits, `TrackMerger.cpp` hash, developer-designated
track and track-truth collection names, reviewed B steering bundle and a new
B-only output root.

The config is parsed as plain `KEY=VALUE` data. It is not sourced and cannot
execute shell code. Values are not expanded, so use complete paths rather
than `$VARIABLE` or `~`.

The steering bundle is deliberately not synthesized. For each new upstream
version, inspect whether native ILDConfig already supplies the requested
wiring. `B_PANDORA_CONFIG` and `B_HIGHLEVEL_CONFIG` must show that Pandora and
the primary `RecoMCTruthLinker` use the same configured B track collection.
The smoke/full steering must visibly limit their event counts, either through
their own `EvtMax` or through the configured event arguments.

## How do I run provenance/preflight?

First print the complete plan without checking or running anything:

```bash
python scripts/trackmerger/run_future_benchmark.py plan \
  --config /path/to/new-campaign/trackmerger_future.env
```

Then run the read-only preflight:

```bash
python scripts/trackmerger/run_future_benchmark.py preflight \
  --config /path/to/new-campaign/trackmerger_future.env \
  | tee /path/to/new-campaign/preflight.json
```

Preflight checks the configured Git commits and hashes, the frozen SIM and A
REC hashes, frozen TausFCCee identity, B-only output-root separation, static
Pandora/linker wiring, event limits and the path-limited Git sentinel. It
does not source software or run reconstruction.

## How do I dry-run the smoke?

```bash
python scripts/trackmerger/run_future_benchmark.py smoke \
  --config /path/to/new-campaign/trackmerger_future.env
```

This prints the resolved environment activation, working directory, steering,
frozen SIM and non-colliding B output base. Without `--execute-smoke`, it does
not create directories or run `k4run`.

## How do I execute the smoke?

Only after reviewing preflight and the dry-run:

```bash
python scripts/trackmerger/run_future_benchmark.py smoke \
  --config /path/to/new-campaign/trackmerger_future.env \
  --execute-smoke
```

The driver reruns preflight, refuses an existing output/log and records the
reconstruction log and exit code. It never retries or monitors in the
background.

Produce the frozen smoke assignments explicitly:

```bash
# dry-run
python scripts/trackmerger/run_future_benchmark.py assignments \
  --config /path/to/new-campaign/trackmerger_future.env --scope smoke

# execute L_direct then L_ancestor
python scripts/trackmerger/run_future_benchmark.py assignments \
  --config /path/to/new-campaign/trackmerger_future.env --scope smoke \
  --execute-assignments
```

The commands reuse the maintained extractors, `source_file_id=000242385`,
the integrated `RecoMCTruthLink` collection and the configured smoke event
count. No association rule is implemented in this driver.

## How do I validate it?

After smoke reconstruction and smoke assignments:

```bash
python scripts/trackmerger/run_future_benchmark.py validate-smoke \
  --config /path/to/new-campaign/trackmerger_future.env
```

The validator runs inside the configured Key4hep environment and checks:

- successful reconstruction exit and exact smoke event count;
- configured track collection, `PandoraPFOs`, `PandoraClusters`,
  `RecoMCTruthLink`, `MCTruthRecoLink` and track-truth relation presence;
- valid PFO track/cluster and forward/inverse truth references;
- every tracked PFO has usable configured-track truth;
- Pandora references only the configured track collection;
- L_direct has zero invalid references and `track_maxT > 0`;
- static Pandora and primary-linker wiring matches the config.

It writes `smoke/validation/smoke_gate.json`. Any failed check writes a FAIL
gate and reports exactly:

```text
STOP: full benchmark not authorized by smoke gate
```

The full stage also binds the PASS gate to the exact configuration SHA256, so
editing the config invalidates the authorization.

## How do I dry-run full B?

```bash
python scripts/trackmerger/run_future_benchmark.py full \
  --config /path/to/new-campaign/trackmerger_future.env
```

This prints only the 2000-event B command. There is no A reconstruction
command anywhere in the driver.

## How do I explicitly execute full B?

```bash
python scripts/trackmerger/run_future_benchmark.py full \
  --config /path/to/new-campaign/trackmerger_future.env \
  --execute-full
```

Execution requires preflight PASS, a matching smoke-gate PASS and no existing
full-B REC/log. Missing or failed smoke authorization stops before `k4run`.

## How do I run frozen assignments and analysis?

Assignments use the maintained `truthlink_assignment_v1` and
`truthlink_ancestor_assignment_v1` extractors:

```bash
# inspect commands
python scripts/trackmerger/run_future_benchmark.py assignments \
  --config /path/to/new-campaign/trackmerger_future.env --scope full

# execute explicitly
python scripts/trackmerger/run_future_benchmark.py assignments \
  --config /path/to/new-campaign/trackmerger_future.env --scope full \
  --execute-assignments
```

Prepare a candidate analysis config from the frozen v1 config:

```bash
python scripts/trackmerger/run_future_benchmark.py prepare-analysis \
  --config /path/to/new-campaign/trackmerger_future.env
```

The generator preserves everything before the `comparisons:` block and
changes only the comparison key plus B name, label, REC, direct, ancestor and
provenance fields. Review the candidate manually against the frozen config.
The driver will reject any later analysis config whose scientific/performance
prefix differs or whose frozen A products are absent.

Dry-run analysis with the reviewed config:

```bash
python scripts/trackmerger/run_future_benchmark.py analysis \
  --config /path/to/new-campaign/trackmerger_future.env \
  --reviewed-config /new/B/root/analysis/comparison_config.candidate.yaml
```

Execute only after review:

```bash
python scripts/trackmerger/run_future_benchmark.py analysis \
  --config /path/to/new-campaign/trackmerger_future.env \
  --reviewed-config /new/B/root/analysis/comparison_config.candidate.yaml \
  --execute-analysis --confirm-reviewed-config
```

This reuses `scripts/analysis/build_mc_comparison.py` at the frozen TausFCCee
commit with exactly:

```text
part12 part3 part3b part4 photon_diagnostic performance
```

## Where are the outputs?

All new products are below the configured `B_OUTPUT_ROOT`:

```text
smoke/
  *_REC.edm4hep.root
  logs/
  assignments/
  validation/smoke_gate.json
full/
  *_REC.edm4hep.root
  logs/
  assignments/
analysis/
  comparison_config.candidate.yaml
  results/
summary/
  trackmerger_benchmark_candidate.csv
```

The driver refuses to overwrite outputs and rejects a B root that overlaps
the frozen A location.

## How do I compare with benchmark v1?

The analysis always uses the frozen A REC/L_direct/L_ancestor and the new B.
Its standard results contain the maintained comparison families. After
reviewing those results, prepare—but do not append—a registry candidate:

```bash
python scripts/trackmerger/run_future_benchmark.py registry-candidate \
  --config /path/to/new-campaign/trackmerger_future.env
```

The candidate is marked `CANDIDATE_REVIEW_REQUIRED`; its two headline
efficiency fields remain `REVIEW_REQUIRED`. Fill and validate them from the
reviewed analysis summary before any separately authorized registry edit.
The driver never modifies `docs/trackmerger/trackmerger_benchmarks.csv`.

## Complete placeholder example

```bash
cp scripts/trackmerger/config/future_benchmark.example.env \
  /work/TM-next/trackmerger_future.env

# Edit /work/TM-next/trackmerger_future.env with the actual future pins.
python scripts/trackmerger/run_future_benchmark.py plan \
  --config /work/TM-next/trackmerger_future.env
python scripts/trackmerger/run_future_benchmark.py preflight \
  --config /work/TM-next/trackmerger_future.env
python scripts/trackmerger/run_future_benchmark.py smoke \
  --config /work/TM-next/trackmerger_future.env
# Only after review, repeat smoke with --execute-smoke.
# Then execute smoke assignments and validate-smoke.
# Only a PASS smoke gate permits full --execute-full.
# Execute full assignments, prepare/review the analysis config, then use
# --execute-analysis --confirm-reviewed-config.
```

No future nightly is implied by this example.

## What must never be changed?

- Never reconstruct or overwrite frozen A.
- Never change the frozen SIM, detector, 2000-event scope or source identity.
- Never change G, L_direct, L_ancestor, TruthlinkV1,
  `truthlink_assignment_v1`, `truthlink_ancestor_assignment_v1`, truth
  selections, denominators, residuals, PID interpretation, families, binning
  or normalization merely to accommodate a new TrackMerger.
- Never let Pandora and the primary `RecoMCTruthLinker` use different B track
  collections.
- Never carry a v1 adapter blindly into changed ILDConfig; inspect native
  upstream wiring first.
- Never treat a generated registry row as accepted without review and
  separate authorization.
- Never infer algorithmic causes or optimize matching as part of the routine
  rerun workflow.
