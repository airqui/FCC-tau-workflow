import yaml

from fcc_tau_workflow.product_manifest import load_product_manifest


def manifest():
    return {
        "schema_version": "fcc_tau_workflow_product_manifest_v1",
        "association_contract": "fcc_tau_association_v1",
        "sample": "W",
        "products": [{
            "source_file_id": "033851393",
            "source_rec": "/data/smoke.root",
            "direct_assignment": "/data/direct.parquet",
            "ancestor_assignment": "/data/ancestor.parquet",
            "truth_definition_version": "selected_truth_v1",
            "input_provenance": "/data/summary.json",
        }],
    }


def test_product_manifest_parses_without_opening_external_products(tmp_path):
    path = tmp_path / "products.yaml"
    path.write_text(yaml.safe_dump(manifest()))
    assert load_product_manifest(path)["sample"] == "W"


def test_duplicate_source_id_is_rejected(tmp_path):
    data = manifest()
    data["products"].append(dict(data["products"][0]))
    path = tmp_path / "products.yaml"
    path.write_text(yaml.safe_dump(data))
    try:
        load_product_manifest(path)
    except ValueError as error:
        assert "duplicate" in str(error)
    else:
        raise AssertionError("duplicate source ID accepted")
