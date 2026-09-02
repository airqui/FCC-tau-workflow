#!/usr/bin/env python3
"""Association-only FCCee linker steering for truthlink_assignment_v1."""
from pathlib import Path
import os

from Configurables import EventDataSvc, MarlinProcessorWrapper
from Gaudi.Configuration import INFO
from k4FWCore import ApplicationMgr, IOSvc
from k4MarlinWrapper.io_helpers import IOHandlerHelper

INPUT_REC = Path(os.environ["TRUTHLINK_INPUT_REC"])
OUTPUT_REC = Path(os.environ["TRUTHLINK_OUTPUT_REC"])
EVENTS = int(os.environ.get("TRUTHLINK_EVTMAX", "2000"))
if not INPUT_REC.is_file():
    raise FileNotFoundError(f"input REC is missing: {INPUT_REC}")
if OUTPUT_REC.exists():
    raise FileExistsError(f"refusing to overwrite output: {OUTPUT_REC}")
if not OUTPUT_REC.parent.is_dir():
    raise FileNotFoundError(f"output directory is missing: {OUTPUT_REC.parent}")
if EVENTS <= 0:
    raise ValueError("TRUTHLINK_EVTMAX must be positive")

algorithms = []
services = [EventDataSvc("EventDataSvc")]
io_service = IOSvc()
io_handler = IOHandlerHelper(algorithms, io_service)
io_handler.add_reader([str(INPUT_REC)])

truth_linker = MarlinProcessorWrapper("RecoMCTruthLinkTruthlinkAssignmentV1")
truth_linker.ProcessorType = "RecoMCTruthLinker"
truth_linker.Parameters = {
    "CalohitMCTruthLinkName": ["CalohitMCTruthLinkTruthlinkV1"],
    "ClusterCollection": ["PandoraClusters"],
    "ClusterMCTruthLinkName": ["ClusterMCTruthLinkTruthlinkV1"],
    "FullRecoRelation": ["true"],
    "KeepDaughtersPDG": ["22", "111", "310", "13", "211", "321"],
    "MCParticleCollection": ["MCParticle"],
    "MCTruthClusterLinkName": ["MCTruthClusterLinkTruthlinkV1"],
    "MCTruthRecoLinkName": ["MCTruthRecoLinkTruthlinkV1"],
    "MCTruthTrackLinkName": ["MCTruthMarlinTrkTracksLinkTruthlinkV1"],
    "RecoMCTruthLinkName": ["RecoMCTruthLinkTruthlinkV1"],
    "RecoParticleCollection": ["PandoraPFOs"],
    "SimCaloHitCollections": [
        "ECalBarrelSiHitsEven", "ECalBarrelSiHitsOdd",
        "ECalEndcapSiHitsEven", "ECalEndcapSiHitsOdd",
        "EcalEndcapRingCollection", "HcalBarrelRegCollection",
        "HcalEndcapsCollection", "HcalEndcapRingCollection",
        "LumiCalCollection", "YokeBarrelCollection", "YokeEndcapsCollection",
    ],
    "SimCalorimeterHitRelationNames": [
        "EcalBarrelRelationsSimRec", "EcalEndcapsRelationsSimRec",
        "EcalEndcapRingRelationsSimRec", "HcalBarrelRelationsSimRec",
        "HcalEndcapsRelationsSimRec", "HcalEndcapRingRelationsSimRec",
        "RelationLcalHit", "RelationMuonHit",
    ],
    "SimTrackerHitCollections": [
        "VertexBarrelCollection", "VertexEndcapCollection",
        "InnerTrackerBarrelCollection", "InnerTrackerEndcapCollection",
        "TPCCollection", "SETCollection",
    ],
    "TrackCollection": ["MarlinTrkTracks"],
    "TrackMCTruthLinkName": ["MarlinTrkTracksMCTruthLinkTruthlinkV1"],
    "TrackerHitsRelInputCollections": [
        "VertexBarrelTrackerHitRelations", "VertexEndcapTrackerHitRelations",
        "InnerTrackerBarrelHitRelations", "InnerTrackerEndcapHitRelations",
        "TPCTrackerHitRelations", "SETSpacePointRelations",
    ],
    "UseTrackerHitRelations": ["true"],
    "UsingParticleGun": ["false"],
}
algorithms.append(truth_linker)
io_handler.add_edm4hep_writer(str(OUTPUT_REC), ["keep *"])
io_handler.finalize_converters()

app_mgr = ApplicationMgr(
    TopAlg=algorithms,
    EvtSel="NONE",
    EvtMax=EVENTS,
    ExtSvc=services,
    OutputLevel=INFO,
)
