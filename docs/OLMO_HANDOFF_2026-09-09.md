# OLMO_HANDOFF

**Date:** 2026-09-09

This document is the entry point for reproducing the FCC-ee tau simulation,
reconstruction, truth association and analysis workflow used in the current
FCC-tau studies.

The workflow is split between two repositories:

```text
FCC-tau-workflow
    simulation / reconstruction / TruthLinkV1
    L_direct / L_ancestor
    production provenance and validation

TausFCCee
    analysis
    G association
    MC comparisons
    plots and tables
```

Maintained repository branches:

```text
FCC-tau-workflow
    branch: consolidation/20260901

TausFCCee
    branch: consolidation/20260901
```

Use each repository's Git history for the exact revision associated with this
handoff; do not copy commit identifiers from an external status snapshot.

The main rule is:

> Do not change software release, detector model, truth definitions or
> association rules when attempting to reproduce the existing results.

---

# 1. Software and detector provenance

The recommended software baseline for new FCC-tau work is Key4hep stable
2026-04-08.  Source the exact validated stack with:

```bash
source /cvmfs/sw.hsf.org/key4hep/releases/2026-04-08/x86_64-almalinux9-gcc14.2.0-opt/key4hep-stack/2026-04-08-i6h4f2/setup.sh
```

The equivalent convenience command is:

```bash
source /cvmfs/sw.hsf.org/key4hep/setup.sh -r 2026-04-08
```

Resolved components include:

```text
Marlin:      1.19.6
MarlinReco:  1.38
k4geo:       00-24
DD4hep:      1.36
```

The frozen local ILDConfig checkout used in this study is:

```text
/lhome/ific/a/airqui/FCC/fcc-tau-dependencies/ILDConfig

commit:
279b180a88597e45dfaf84f35d1b8b5358300079
```

Detector:

```text
ILD_FCCee_v01
```

Geometry SHA256:

```text
ab48a78ef69f6ee417233e34cffa75a0fd41742fb02130c57303f402abd87e29
```

The detector compact file can normally be obtained after sourcing Key4hep as:

```bash
export COMPACT_FILE="$k4geo_DIR/FCCee/ILD_FCCee/compact/ILD_FCCee_v01/ILD_FCCee_v01.xml"
```

## Historical nightly provenance

The old reference and Talk2 results retain the following production
provenance:

```bash
source /cvmfs/sw-nightlies.hsf.org/key4hep/releases/2026-08-21/x86_64-almalinux9-gcc14.2.0-opt/key4hep-stack/2026-08-21-5qmpe6/setup.sh
```

MarlinReco provenance relevant for the truth linker:

```text
MarlinReco version:
1.38.1

commit:
fe8e9e2d08b47048e639c072b7bce97f9847f7d1

processor:
RecoMCTruthLinker

library:
libMarlinReco.so
```

The exact nightly CVMFS stack is no longer available.  It remains the
provenance of the old results because it was the environment used to produce
them, not because the study identified a nightly-only reconstruction feature.
New work should use stable 2026-04-08 unless a study explicitly requires and
validates another release.  Do not rewrite the provenance of old results.

---

# 2. Generator input -> SIM

The generator input can be, for example:

```text
STDHEP
HepMC3 ASCII
```

The detector simulation is run with `ddsim`.

The frozen steering is:

```text
fcc-tau-dependencies/ILDConfig/StandardConfig/production/ddsim_steer.py
```

Its SHA256 in the frozen setup is:

```text
fdaa1a29fcf9ac704e18df5c69e7813abf7389b4a082991c337615778bce4cfd
```

The effective simulation configuration is:

```text
physics list:          QGSP_BERT
range cut:             0.1 mm
minimum kinetic E:     1 MeV
Geant4 decays:         disabled
saved process:         Decay
crossing-angle boost:  15 mrad
```

There is an important detail concerning the crossing angle. The steering file
contains internally `crossingAngleBoost = 7 mrad`, but the FCC-tau production
overrides it explicitly on the command line with:

```text
--crossingAngleBoost 15.e-3
```

Therefore the effective production value is **15 mrad**.

A canonical command is:

```bash
cd /path/to/ILDConfig/StandardConfig/production

ddsim \
  --steeringFile ddsim_steer.py \
  --compactFile "$COMPACT_FILE" \
  --inputFiles "$GEN_INPUT" \
  --outputFile "$SIM_FILE" \
  --numberOfEvents "$N_EVENTS" \
  --crossingAngleBoost 15.e-3
```

For compressed STDHEP input, validate/decompress the input before handing the
actual STDHEP stream to `ddsim`.

For HepMC3 ASCII, the HepMC file can be passed directly as input.

Example KKMCee input used in the current study:

```text
/lustre/ific.uv.es/prj/gl/abehep.flc/FCC/KKMCee/kk_ee_Ztautau_4991.hepmc
```

This contains 2000 HepMC3 events.

---

# 3. SIM -> REC

The standard reconstruction is run with:

```bash
cd /path/to/ILDConfig/StandardConfig/production

k4run ILDReconstruction.py \
  --detectorModel=ILD_FCCee_v01 \
  --inputFiles="$SIM_FILE" \
  --outputFileBase="$OUTPUT_BASE" \
  --num-events=-1
```

This is not a traditional `Marlin steering.xml` execution. Instead the
reconstruction is run through:

```text
k4run / Gaudi
    |
    v
k4MarlinWrapper
    |
    v
Marlin processors
```

The processors themselves are still standard Marlin processors.

---

# 4. Tracking used by Pandora

The FCC-ee MDI tracking sequence runs both:

```text
Clupatra
    -> MarlinTrkTracks

ConformalTracking
    -> SiTracksCT
```

Both collections can be present in the REC file.

However Pandora is configured with:

```text
TrackCollections = ["MarlinTrkTracks"]
```

Therefore the tracking input used by the standard Pandora PFA reconstruction
in this production is `MarlinTrkTracks`, not `SiTracksCT`.

Pandora produces:

```text
PandoraPFOs
```

---

# 5. PID used in the analysis

The PID used in the current FCC-tau plots is the particle hypothesis stored
directly in `PandoraPFOs`, i.e. the reconstructed-particle PDG/type produced by
Pandora.

No additional dedicated high-level PID processor is used in this analysis.

Collections such as:

```text
PandoraPFOs_PID_dEdxPID
PandoraPFOs_PID_LikelihoodPID
PandoraPFOs_PID_ShowerShapesPID
...
```

exist in the REC schema but are empty in the reconstruction used here.

Thus:

> current FCC-tau PID = Pandora PFO particle hypothesis.

---

# 6. Stable reconstruction with integrated TruthLinkV1

On stable Key4hep 2026-04-08, do not run TruthLinkV1 as a second-pass Marlin
job.  A standalone pass fails before linking while converting the previously
written REC from EDM4hep to LCIO:

```text
REC -> k4MarlinWrapper -> EDM4hep-to-LCIO conversion -> failure
```

This was reproduced with a harmless one-event `Statusmonitor` pass containing
neither `RecoMCTruthLinker` nor an output writer.  It is therefore a stable
release I/O/conversion workflow constraint, not evidence of a
`RecoMCTruthLinker` physics or algorithm problem.

The validated stable workflow is:

```text
SIM
 -> reconstruction
 -> RecoMCTruthLinker in the same k4run process
 -> REC + TruthLinkV1
 -> L_direct
 -> L_ancestor
```

The standard processor `RecoMCTruthLinker` is used unmodified from
`MarlinReco`. FCC-tau only configures it.

Important configuration:

```text
RecoParticleCollection = PandoraPFOs
TrackCollection        = MarlinTrkTracks
ClusterCollection      = PandoraClusters
FullRecoRelation       = true
```

The processor writes the FCC-tau-namespaced collections:

```text
RecoMCTruthLinkTruthlinkV1
MCTruthRecoLinkTruthlinkV1
MarlinTrkTracksMCTruthLinkTruthlinkV1
ClusterMCTruthLinkTruthlinkV1
```

`TruthlinkV1` is a provenance/name-space convention used by FCC-tau. It does
**not** mean that `RecoMCTruthLinker` itself has been modified.

---

# 7. Stable workflow constraints and reproducibility

Use the standard unmodified `RecoMCTruthLinker` configuration above inside the
reconstruction process, after Pandora PFO production and before final REC
writing.  Do not strip ParticleID collections or alter Pandora as a workaround,
and do not reopen the stable REC in a second-pass Marlin job.

The integrated workflow was repeated on the same ten P8O SIM events.  Event 2
had 20 versus 18 `MarlinTrkTracks`; no interpretation is assigned to that
low-level difference.  The analysis-level products were identical:

- PandoraPFO multiplicities and total (86 versus 86);
- PFO type/PDG, momentum, energy, and charge;
- all 86 L_direct assignments;
- all 86 L_ancestor assignments.

Conclusion: **ANALYSIS-LEVEL REPRODUCIBLE**.

## 7.1 Stable P8O/P8H 10k campaign

The controlled campaign is stored under:

```text
/lustre/ific.uv.es/prj/gl/abehep.flc/FCC/P8_stable20260408_AB_10k/
```

P8O starts from historical existing SIM; P8H starts from PYTHIA 20260909
HepMC and stable simulation.  Both then use stable reconstruction with
integrated TruthLinkV1 and the same L_direct and L_ancestor definitions.

| Quantity | P8O | P8H |
|---|---:|---:|
| Events | 10,000 | 10,000 |
| MCParticles | 1,224,250 | 977,321 |
| PandoraPFOs | 61,326 | 61,009 |
| L_direct assigned | 61,323 | 61,006 |
| L_direct ambiguous | 3 | 3 |
| L_ancestor direct | 48,795 | 49,117 |
| L_ancestor promoted | 12,476 | 11,871 |
| No qualifying analysis-truth ancestor | 52 | 18 |
| Direct unassigned | 3 | 3 |

The raw MC bookkeeping differs substantially, but the maintained
analysis-truth populations are very similar.  Analysis-truth photons number
53,718 for P8O and 53,988 for P8H; neither sample has parentless
analysis-truth photons.  Raw L_direct unique assignment is approximately
99.995% in both samples.  This raw PFO-to-any-MC success must not be confused
with truth-species association efficiency.

## 7.2 Photon residual headline

For L_ancestor-associated photons:

| Sample | N | p median | p h68 | theta median [mrad] | theta h68 [mrad] |
|---|---:|---:|---:|---:|---:|
| Historical P8O/nightly | 40,627 | -0.01102 | 0.13986 | 0.2457 | 12.2535 |
| P8O stable | 22,496 | -0.01104 | 0.13909 | 0.3293 | 12.2486 |
| P8H stable | 22,904 | -0.01027 | 0.14164 | 0.1767 | 12.1975 |

The broad photon theta component is robust.  Neither P8O-to-P8H nor
stable-to-historical-nightly changes its width materially, and the raw
generator-bookkeeping difference does not propagate into a materially
different selected photon response.  This observation does not motivate a
further generator campaign.  A future photon-specific reconstruction or
association study may investigate the absolute approximately 12 mrad width,
but it should not be framed as a PYTHIA or Key4hep-release regression.

Terminology remains deliberately limited by stored genealogy:

```text
tau-origin photon != FSR
non-tau photon    != ISR
parentless photon != ISR
```

---

# 8. `RecoMCTruthLinkTruthlinkV1`

The main collection used by the FCC-tau assignment workflow is:

```text
RecoMCTruthLinkTruthlinkV1
```

It contains relations of the form:

```text
PandoraPFO -> MCParticle
```

A PFO can have more than one MC candidate.

Each relation carries a packed integer-like weight containing separately:

```text
T = tracking contribution
C = cluster/calorimeter contribution
```

The packed representation used by the standard linker is decoded as:

```text
W = 10000*C + T

T = int(W) % 10000
C = int(W) // 10000
```

The FCC-tau code does **not** redefine those weights. It reads the output of
the standard `RecoMCTruthLinker` processor.

---

# 9. `L_direct`

`L_direct` converts the possibly many `PFO -> MC candidate` relations into at
most one direct MC assignment per PFO.

Authoritative implementation:

```text
FCC-tau-workflow/
  src/fcc_tau_workflow/truthlink_assignment.py
  scripts/workflow/extract_truthlink_assignments.py
  configs/truthlink/assignment_v1.yaml
```

The scientific rule is frozen.

## 9.1 What `L_direct` does and does not require

`L_direct` chooses among the MCParticle candidates already provided by
`RecoMCTruthLinker`.

Our `L_direct` reduction does **not** require:

```text
generatorStatus == 1
zero daughters
a particular PDG
a particular ancestry
```

The chosen direct MCParticle may therefore have `generatorStatus == 1` or a
different generator status.

This point is important when interpreting the efficiencies shown in the
analysis plots: the `L_direct` algorithm can successfully assign a unique
MCParticle even when that MCParticle is not itself a `generatorStatus == 1`
analysis truth particle.

## 9.2 Charged / track-supported branch

If at least one candidate has `T > 0`, then only track-supported candidates
participate.

Choose `maximum T`. If several candidates have the same maximum `T`, use
`maximum C` among those candidates. If an exact tie still remains, mark the
assignment ambiguous.

Therefore:

```text
max T
then max C
then ambiguity
```

There is no arbitrary final tiebreak.

## 9.3 Cluster-only branch

If all candidates have `T = 0`, choose `maximum C`.

If several candidates have exactly the same maximum `C`:

- if exactly one of them is neutral, choose the neutral candidate;
- otherwise mark the assignment ambiguous.

Therefore:

```text
max C
then unique-neutral priority
then ambiguity
```

## 9.4 What is explicitly NOT done

FCC-tau does not use `T + C` as a score.

It also does not resolve exact ties using:

```text
MC index
PDG
collection order
floating tolerance
```

A persisted relation with packed weight zero is still considered a relation.

No relation at all is a different status.

Typical direct-assignment outcomes include:

```text
assigned
truthlink_orphan_ambiguous
truthlink_orphan_no_relation
```

---

# 10. `L_direct` output and the meaning of the reported coverage

The extractor writes a compact Parquet product containing one row per PFO.

Among other fields it stores:

```text
source_file_id
event_in_file
pfo_index

truthlink_status
assigned_mc_index

track_permille
cluster_permille

decision_branch
```

The maintained extractor is:

```text
scripts/workflow/extract_truthlink_assignments.py
```

The Pythia-compatible entry point currently has the same maintained logic:

```text
scripts/workflow/extract_truthlink_assignments_pythia.py
```

## Assignment success is not the same as analysis coverage

This distinction is essential.

`L_direct` itself attempts to assign a unique MCParticle to each PFO, without
requiring a particular `generatorStatus`.

In the analysis plots, however, the quoted `L_direct` PFO coverage asks a more
restrictive question:

> Does the PFO have a unique `L_direct` assignment whose assigned MCParticle is
> one of the analysis truth particles?

For the current analysis, an analysis truth particle is defined as:

```text
generatorStatus == 1
non-zero momentum
not a neutrino
```

with neutrinos defined by:

```text
abs(PDG) in {12, 14, 16}
```

In the code/configuration this analysis set is named `selected_truth_v1`, but
that name is internal FCC-tau jargon.

Therefore a reported value such as approximately `79%` for `L_direct`
coverage must **not** be read as "`L_direct` only finds a MCParticle for 79% of
PFOs".

The typical situation is instead:

```text
PFO
 |
 v
L_direct
 |
 v
unique direct MCParticle X
generatorStatus != 1
```

The direct assignment exists, but it does not yet point to a
`generatorStatus == 1` analysis truth particle.

That is the case `L_ancestor` is designed to address.

---

# 11. `L_ancestor`

`L_ancestor` is a separate operation performed **after** `L_direct`.

It does not rerun `RecoMCTruthLinker`.

It does not recompute or reinterpret the track/cluster weights.

The starting point is always:

```text
PFO
 |
 v
L_direct
 |
 v
direct MCParticle
```

`L_ancestor` requires a unique direct MCParticle assignment from `L_direct`.

There are then three cases:

```text
PFO
 |
 v
L_direct
 |
 +-- no unique direct MC ------------------------> stop
 |
 +-- unique direct MC X
        |
        +-- X satisfies the analysis truth definition
        |       generatorStatus == 1
        |       non-zero momentum
        |       not a neutrino
        |
        |       -> L_ancestor = X
        |          depth = 0
        |
        +-- X does NOT satisfy that definition
                |
                v
          traverse stored parents
                |
                v
          nearest unique ancestor
          satisfying the same definition
                |
                v
          L_ancestor = that ancestor
```

Thus `L_ancestor` does **not** repair a missing or ambiguous direct assignment.

Its purpose is different: when `L_direct` has already found a unique MCParticle
but that particle is not a `generatorStatus == 1` analysis truth particle,
`L_ancestor` follows the stored genealogy towards its parents.

Authoritative implementation:

```text
FCC-tau-workflow/
  src/fcc_tau_workflow/truthlink_ancestor_assignment.py
  scripts/workflow/extract_lancestor_assignments.py
  configs/truthlink/ancestor_assignment_v1.yaml
```

---

# 12. Exact `L_ancestor` rule

The algorithm is:

```text
1. Start from the unique MCParticle assigned by L_direct.

2. If there is no unique direct MCParticle:
       stop
       no ancestry search is attempted.

3. Check whether the direct MCParticle satisfies:

       generatorStatus == 1
       non-zero momentum
       not a neutrino

4. If yes:
       L_ancestor = direct MCParticle
       ancestor depth = 0
       stop.

5. Otherwise perform a parent-only breadth-first search (BFS)
   through the stored MC genealogy.

6. At each increasing depth, look for particles satisfying:

       generatorStatus == 1
       non-zero momentum
       not a neutrino

7. Stop at the nearest depth containing such particles.

8. If exactly one such particle exists at that nearest depth:
       L_ancestor = that particle
       mark it as a unique promoted ancestor.

9. If more than one such particle exists at the same nearest depth:
       the ancestry result is ambiguous.

10. If no such ancestor is reachable:
       mark the result as no_selected_ancestor
       (implementation/status name retained for provenance).
```

Graphically:

```text
PFO
 |
 v
L_direct
 |
 v
MCParticle X
 |
 +-- generatorStatus == 1,
 |   p != 0,
 |   non-neutrino ?
 |      |
 |      yes
 |      |
 |      +--> L_ancestor = X
 |           depth = 0
 |
 no
 |
 v
parents at depth 1
 |
 +-- qualifying particle(s) found?
 |      |
 |      one
 |      +--> L_ancestor = that particle
 |
 |      more than one
 |      +--> ambiguous
 |
 none
 |
 v
parents at depth 2
 |
 ...
```

Cycles in the stored genealogy are treated as invalid/fatal conditions rather
than silently ignored.

An ambiguous or missing `L_direct` assignment is never repaired by ancestry.

---

# 13. Technical difference between `L_direct` and `L_ancestor`

A useful summary is:

```text
RecoMCTruthLinker
    |
    | PFO -> candidate MCParticles
    | with track/cluster weights T and C
    v
L_direct
    |
    | choose one immediate MC contributor
    | using T/C weights only
    v
direct MCParticle
    |
    | if generatorStatus != 1 analysis truth,
    | traverse stored parents
    v
L_ancestor
```

## `L_direct`

Answers approximately:

> Which stored MCParticle is the strongest immediate contributor to this PFO?

It uses the track/cluster weights produced by `RecoMCTruthLinker`.

It does not impose `generatorStatus == 1` or a zero-daughter requirement.

## `L_ancestor`

Answers approximately:

> Starting from the unique direct MC contributor, what is the nearest unique
> ancestor satisfying the analysis truth definition
> (`generatorStatus == 1`, non-neutrino, non-zero momentum)?

It uses genealogy only.

It does not use the T/C weights again.

## Relation to the coverage numbers shown in the slides

The analysis compares both association definitions against the same
`generatorStatus == 1` visible truth denominator.

Therefore:

```text
L_direct coverage
    = fraction of PFOs whose direct MC assignment is already
      a qualifying generatorStatus == 1 analysis truth particle

L_ancestor coverage
    = fraction of PFOs that can be connected, directly or through
      parent traversal, to a qualifying generatorStatus == 1
      analysis truth particle
```

This is why `L_ancestor` can have a coverage close to 100% while the reported
`L_direct` coverage is substantially lower, even though `L_direct` itself
produces a unique MC assignment for almost every PFO.

---

# 14. Why `L_ancestor` is useful

Detector simulation and generator records can contain MCParticles that are
descendants of the `generatorStatus == 1` particle used as the analysis truth
reference.

For example:

```text
generatorStatus == 1 analysis particle
              |
              v
       stored descendant(s)
              |
              v
   detector interaction / conversion product
              |
              v
             PFO
```

A direct truth link can legitimately point to one of those descendant
MCParticles rather than directly to the `generatorStatus == 1` particle.

For performance studies defined relative to the `generatorStatus == 1`
analysis truth population, `L_ancestor` relates the PFO back to the nearest
unique qualifying ancestor.

This is particularly useful when comparing samples whose stored MC genealogies
or bookkeeping conventions differ.

---

# 15. Important ancestry terminology

FCC-tau defines tau origin using the **stored MC genealogy** only.

A particle is tau-origin if recursively following stored parents reaches a
particle with:

```text
abs(PDG) == 15
```

This must not be overinterpreted. In particular:

```text
tau-origin photon != automatically FSR
non-tau photon    != automatically ISR
parentless photon != automatically ISR
```

These are statements about the stored generator record, not necessarily unique
physical radiation classifications.

---

# 16. How the assignments are used in analysis

`L_direct` and `L_ancestor` products are naturally:

```text
PFO -> MC
```

The efficiency/resolution analyses are defined relative to the analysis truth
population:

```text
generatorStatus == 1
non-zero momentum
not a neutrino
```

For truth-level efficiencies the analysis therefore needs the inverse point of
view:

```text
analysis-truth MC -> PFO candidate(s)
```

More than one PFO may point to the same MC particle.

When exactly one representative PFO is required, FCC-tau uses the frozen
representative-PFO ranking based on the underlying direct-link strengths.

The rule is again:

```text
if there are track-supported candidates:
    max T
    then max C
else:
    max C
```

An exact remaining tie is:

```text
ambiguous_multiple_pfo
```

The representative PFO is **not** chosen using:

```text
PID
reconstructed energy
fiducial cuts
PFO index
```

This keeps association independent of the performance quantity being measured.

---

# 17. `G` geometric association

The analysis also contains an independent geometric association `G`.

It is defined as:

```text
sqrt(
    (delta theta)^2
    +
    wrap(delta phi)^2
) < 0.1
```

with reco-side deduplication.

This is a `theta-phi` distance. It is **not** the standard eta-phi `DeltaR`.

`G` belongs to the analysis code in `TausFCCee`, not to the truth-link workflow.

---

# 18. Residual definitions

For uniquely associated truth/PFO pairs the current analysis uses:

Momentum residual:

```text
(reco_p - truth_p) / truth_p
```

Polar-angle residual:

```text
(reco_theta - truth_theta) * pi/180 * 1000
```

in mrad.

Resolution summaries are:

```text
median
central68 halfwidth = (q84 - q16)/2
```

RMS is not used as the default summary.

---

# 19. PID denominator

PID performance is conditional on a valid unique truth/PFO association.

Therefore unmatched truth and ambiguous truth/PFO associations are excluded
from the PID denominator. They are association failures, not PID failures.

---

# 20. Maintained plotting / comparison code

The maintained plotting pipeline is in `TausFCCee`.

Entry point:

```text
scripts/analysis/build_mc_comparison.py
```

Configuration:

```text
configs/analysis/fcc_mc_comparisons_v1.yaml
```

Main implementation:

```text
modules/fcc_mc_comparison.py
modules/fcc_mc_comparison_outputs.py
```

Documentation:

```text
docs/MC_COMPARISON_PIPELINE.md
docs/ANALYSIS_RECIPES.md
```

The configured analysis families are:

```text
part12
    tau decay modes
    terminal tau kinematics
    analysis-truth multiplicities
      (named selected_truth in the code/configuration)
    truth-particle kinematics

part3
    G / L_direct / L_ancestor efficiencies
    binned inefficiency
    PFO coverage

part3b
    PFO momentum residuals
    PFO theta residuals

part4
    conditional PID matrices
    conditional PID efficiency
```

---

# 21. Reproducing the W/PYTHIA8 talk plots

The frozen Talk-2 comparison is:

```text
WHIZARD vs PYTHIA8
18k vs 18k events
```

From `TausFCCee`:

```bash
python scripts/analysis/build_mc_comparison.py \
  --comparison whizard_p8o_18k \
  --output-root /tmp/fcc_tau_w_p8o_regression \
  --validation-mode
```

This regenerates the maintained numerical products and checks them against the
frozen Talk-2 reference.

The original frozen Talk-2 output tree is:

```text
/lhome/ific/a/airqui/FCC/talk2_material
```

It should be treated as read-only reference material.

---

# 22. Reproducing the W/KKMCee comparison

The current maintained W/KKMCee comparison uses:

```text
WHIZARD:
source_file_id = 000242385
2000 events

KKMCee:
source_file_id = 700000001
2000 events
```

Set:

```bash
export FCC_TAU_KKMCEE_MATERIAL=/lhome/ific/a/airqui/FCC/kkmcee_material
```

Then:

```bash
cd /path/to/TausFCCee

python scripts/analysis/build_mc_comparison.py \
  --comparison whizard_kkmcee_2k \
  --output-root /path/to/output
```

The maintained local reference output is:

```text
/lhome/ific/a/airqui/FCC/kkmcee_material/comparison_W2k_KKMCee2k
```

The KKMCee assignment products are exposed to the analysis through:

```text
/lhome/ific/a/airqui/FCC/kkmcee_material/derived/
```

which currently contains symlinks to the canonical Lustre products.

---

# 23. Example complete chain

The conceptual chain is:

```text
generator
HepMC / STDHEP
      |
      | ddsim
      v
SIM
      |
      | k4run ILDReconstruction.py
      v
REC
      |
      | standard MarlinReco RecoMCTruthLinker
      | via k4MarlinWrapper
      v
REC_TruthlinkV1
      |
      | extract_truthlink_assignments.py
      v
L_direct.parquet
      |
      | extract_lancestor_assignments.py
      v
L_ancestor.parquet
      |
      v
TausFCCee analysis
      |
      +--> G
      +--> association efficiency
      +--> residuals
      +--> PID
      +--> plots/tables
```

---

# 24. Files to read first

For workflow/reconstruction:

```text
FCC-tau-workflow/README.md
FCC-tau-workflow/PROVENANCE.md
FCC-tau-workflow/docs/RECONSTRUCTION_CHAIN.md
FCC-tau-workflow/docs/TRUTH_LINKING_AND_ASSIGNMENT.md
FCC-tau-workflow/docs/DATASETS_AND_PROVENANCE.md
```

For analysis:

```text
TausFCCee/docs/ANALYSIS_RECIPES.md
TausFCCee/docs/MC_COMPARISON_PIPELINE.md
```

For the actual implementation of the truth assignment:

```text
FCC-tau-workflow/src/fcc_tau_workflow/truthlink_assignment.py
FCC-tau-workflow/src/fcc_tau_workflow/truthlink_ancestor_assignment.py
```

For the maintained MC-comparison plots:

```text
TausFCCee/scripts/analysis/build_mc_comparison.py
TausFCCee/modules/fcc_mc_comparison.py
TausFCCee/modules/fcc_mc_comparison_outputs.py
```

---

# 25. Scientific / technical boundaries

The following definitions are frozen for the current studies:

```text
analysis truth:
    generatorStatus == 1
    non-zero momentum
    non-neutrino
    (internal code/config name: selected_truth_v1)

G

truthlink_assignment_v1 = L_direct
truthlink_ancestor_assignment_v1 = L_ancestor

tau-origin definition
representative-PFO rule
PID denominator
momentum residual
theta residual
```

Do not change one of these silently when comparing against existing plots.

Likewise, do not interpret generator-record-dependent photon ancestry labels as
physical ISR/FSR categories unless that interpretation has been established
separately.

---

# 26. Minimal reproducibility checklist

Before accepting a reproduced result, record at least:

```text
Key4hep setup path
detector model
ILDConfig commit
geometry checksum
MarlinReco version/commit
generator input path/checksum
SIM path/checksum
REC path/checksum
TruthlinkV1 path/checksum
source_file_id
number of events
L_direct product
L_ancestor product
analysis configuration
Git commits of FCC-tau-workflow and TausFCCee
```

For the current handoff reference:

```text
FCC-tau-workflow:
82aa6a9

TausFCCee:
844cc76
```

This information is enough to distinguish software provenance, detector
reconstruction, truth association and downstream analysis.
