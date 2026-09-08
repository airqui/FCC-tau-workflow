#!/usr/bin/env python3
"""Static consistency checks for the frozen Stage-2 YAML contracts."""
from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from fcc_tau_workflow.product_manifest import load_product_manifest
from fcc_tau_workflow.truthlinked_preflight import REQUIRED_COLLECTIONS


def load(path: Path):
    with path.open() as stream:
        return yaml.safe_load(stream)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--product-manifest", type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    assignment = load(repo / "configs/truthlink/assignment_v1.yaml")
    ancestor = load(repo / "configs/truthlink/ancestor_assignment_v1.yaml")
    linker = load(repo / "configs/truthlink/linker_collections_v1.yaml")
    detector = load(repo / "configs/detector/ild_fccee_v01.yaml")
    environment = load(repo / "configs/environments/key4hep_2026-08-21.yaml")
    kkmcee = load(repo / "configs/campaigns/kkmcee_2k.yaml")
    contract = load(repo / "src/fcc_tau_workflow/contracts/association_v1.yaml")
    assert assignment["packed_weight"]["formula"] == "W = 10000 * clusterPermille + trackPermille"
    assert assignment["assignment"]["track_branch"]["condition"] == "any_candidate_track_permille_gt_0"
    assert assignment["event_identity"]["primary_key"] == ["source_file_id", "event_in_file", "pfo_index"]
    assert ancestor["ancestor_rule"]["selection"] == "nearest_depth"
    assert ancestor["ancestor_rule"]["cycles"] == "fatal"
    assert linker["full_reco_relation"] is True and linker["input_mode"] == "REC_only"
    assert linker["outputs"]["reco_mc_relation"] == "RecoMCTruthLinkTruthlinkV1"
    assert detector["simulation"]["crossing_angle_boost_rad"] == 0.015
    assert detector["simulation"]["physics_list"] == "QGSP_BERT"
    assert detector["reconstruction"]["num_events"] == -1
    assert environment["external_software"]["ildconfig_commit"] == "279b180a88597e45dfaf84f35d1b8b5358300079"
    assert kkmcee["generator"]["events"] == 2000
    assert kkmcee["generator"]["comparison_weight_policy"] == "unweighted"
    assert kkmcee["simulation"]["detector"] == detector["detector_model"]
    assert kkmcee["simulation"]["crossing_angle_boost_rad"] == detector["simulation"]["crossing_angle_boost_rad"]
    assert kkmcee["truthlink"]["full_reco_relation"] is True
    assert kkmcee["truthlink"]["required_collections"] == list(REQUIRED_COLLECTIONS)
    assert contract["authoritative_event_identity"]["fields"] == ["sample", "source_file_id", "event_in_file"]
    if args.product_manifest:
        product = load_product_manifest(args.product_manifest, check_products=True)
        assert product["association_contract"] == contract["contract"]
    print("contract_validation=PASS")


if __name__ == "__main__":
    main()
