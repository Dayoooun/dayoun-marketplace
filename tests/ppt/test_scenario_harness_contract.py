from __future__ import annotations

import json
import sys
from pathlib import Path
import pytest


SKILL = (
    Path(__file__).resolve().parents[2]
    / "plugins"
    / "business-plan-writer"
    / "skills"
    / "ppt-editorial"
)
SCRIPTS = SKILL / "scripts"
REFERENCES = SKILL / "references"
sys.path.insert(0, str(SCRIPTS))

import html_slide_renderer as renderer  # noqa: E402
import scenario_harness as harness  # noqa: E402


def _load(name: str) -> dict:
    return json.loads((REFERENCES / name).read_text(encoding="utf-8"))


def test_scenario_catalog_is_context_driven_and_coordinate_free() -> None:
    contract = _load("render_contract.json")
    catalog = _load("scenario_catalog.json")
    fewshots = _load("scenario_fewshots.json")

    assert contract["rendererDecision"]["rule"]
    assert len(fewshots["fewShots"]) >= 9
    assert len(catalog["scenarios"]) >= 12

    required_context = set(contract["context"]["required"])
    layouts = set(contract["rendererDecision"]["htmlLayouts"])
    for scenario in catalog["scenarios"]:
        assert required_context <= set(scenario["context"])
        assert scenario["spec"]["layout"] in layouts
        decision, decision_errors = harness._resolve_context_decision(
            scenario,
            contract,
            fewshots,
        )
        assert decision_errors == []
        assert decision["layout"] == scenario["spec"]["layout"]
        assert decision["fewShotIds"]
        assert harness._validate_semantics(scenario, contract, decision) == []
        graph = scenario["spec"].get("graph")
        if graph:
            assert renderer.validate_graph(graph) == []
            assert all("x" not in node and "y" not in node for node in graph["nodes"])
        if scenario["spec"].get("assetRole") == "photo":
            assert scenario["spec"]["imagePosition"]
            assert scenario["spec"]["imageScale"] >= 1.05


def test_context_route_rejects_conflicting_fixture_layout() -> None:
    contract = _load("render_contract.json")
    fewshots = _load("scenario_fewshots.json")
    scenario = {
        "context": {
            "audience": "reviewer",
            "message": "관계",
            "evidenceType": "relationships",
            "density": "medium",
            "visualRole": "entity-flow",
        },
        "spec": {"layout": "table", "columns": []},
    }
    decision, decision_errors = harness._resolve_context_decision(
        scenario,
        contract,
        fewshots,
    )

    assert decision_errors == []
    assert decision["layout"] == "network"
    errors = harness._validate_semantics(scenario, contract, decision)
    assert any("context derives layout 'network'" in error for error in errors)


def test_graph_contract_rejects_missing_labels_endpoints_and_isolates() -> None:
    graph = {
        "forbidIsolated": True,
        "requireEdgeLabels": True,
        "nodes": [
            {"id": "a", "label": "요청", "entityType": "INPUT"},
            {"id": "b", "label": "", "entityType": "ROLE"},
            {"id": "orphan", "label": "고립", "entityType": "SYSTEM"},
        ],
        "edges": [
            {"source": "a", "target": "missing", "direction": "forward", "label": ""}
        ],
    }

    errors = renderer.validate_graph(graph)

    assert any("requires label" in error for error in errors)
    assert any("target 'missing' is missing" in error for error in errors)
    assert any("isolated node 'orphan'" in error for error in errors)


def test_network_render_receipt_binds_nodes_edges_and_labels(tmp_path: Path) -> None:
    graph = {
        "forbidIsolated": True,
        "requireEdgeLabels": True,
        "nodes": [
            {"id": "request", "label": "업무 요청", "entityType": "INPUT"},
            {"id": "owner", "label": "책임자", "entityType": "ROLE", "primary": True},
            {"id": "record", "label": "실행 기록", "entityType": "EVIDENCE"},
        ],
        "edges": [
            {"source": "request", "target": "owner", "direction": "forward", "label": "할당"},
            {"source": "owner", "target": "record", "direction": "forward", "label": "기록"},
        ],
    }
    out = renderer.render_job(
        {
            "renderer": "html",
            "layout": "network",
            "out": "network.png",
            "eyebrow": "ENTITY FLOW",
            "title": "엔티티 연결 검증",
            "subtitle": "위상 기반 자동 배치",
            "graph": graph,
        },
        tmp_path,
    )
    receipt = json.loads(out.with_suffix(".layout.json").read_text(encoding="utf-8"))

    assert receipt["graph"]["nodes"] == 3
    assert receipt["graph"]["edges"] == 2
    assert receipt["graph"]["edgeLabels"] == 2
    assert all(edge["hasMarkerEnd"] for edge in receipt["graph"]["visibility"])
    assert all(
        not edge[field]
        for edge in receipt["graph"]["visibility"]
        for field in ("startOccluded", "endOccluded", "pathOccluded", "labelOccluded")
    )
    assert receipt["rendererDigest"].startswith("sha256:")
    assert receipt["specDigest"].startswith("sha256:")
    assert receipt["overflow"] == []
    assert 0.80 <= receipt["meaningfulBody"]["bottom"] <= 0.88


def test_source_manifest_binds_contract_code_style_and_assets() -> None:
    catalog_path = REFERENCES / "scenario_catalog.json"
    contract_path = REFERENCES / "render_contract.json"
    fewshots_path = REFERENCES / "scenario_fewshots.json"
    manifest = harness._source_manifest(
        catalog_path,
        contract_path,
        fewshots_path,
        _load("scenario_catalog.json"),
    )
    names = {Path(row["path"]).name for row in manifest["files"]}

    assert manifest["sourceHash"].startswith("sha256:")
    assert {
        "SKILL.md",
        "style_profiles.json",
        "html_slide_renderer.py",
        "scenario_harness.py",
        "render_contract.json",
        "scenario_fewshots.json",
        "scenario_catalog.json",
        "automation-3d-asset.png",
        "team-workflow-photo.png",
    } <= names


def test_process_gap_rejects_non_finite_receipt() -> None:
    contract = _load("render_contract.json")
    scenario = next(
        item
        for item in _load("scenario_catalog.json")["scenarios"]
        if item["id"] == "S005-process"
    )
    receipt = {
        "size": contract["qualityGate"]["size"],
        "overflow": [],
        "rendererDigest": harness._digest(SCRIPTS / "html_slide_renderer.py"),
        "specDigest": "sha256:test",
        "content": {"top": 0.35},
        "meaningfulBody": {"bottom": 0.82},
        "internalGaps": {"processToNote": 0.1},
        "footer": {"left": float("nan")},
    }

    errors = harness._validate_receipt(scenario, receipt, contract)

    assert any("receipt contains non-finite values at $.footer.left" in error for error in errors)


def test_strict_json_reader_rejects_nan_constant(tmp_path: Path) -> None:
    path = tmp_path / "nan.json"
    path.write_text('{"root": NaN}', encoding="utf-8")

    with pytest.raises(harness.ScenarioHarnessError, match="non-finite JSON constant"):
        harness._read_json(path)
