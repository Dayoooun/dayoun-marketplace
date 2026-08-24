from __future__ import annotations

import json
import sys
from pathlib import Path


SKILL = (
    Path(__file__).resolve().parents[2]
    / "plugins"
    / "business-plan-writer"
    / "skills"
    / "ppt-editorial"
)
SCRIPTS = SKILL / "scripts"
sys.path.insert(0, str(SCRIPTS))

import design_plan  # noqa: E402


def _plan(tmp_path: Path, approval: str = "approved") -> Path:
    for name in (
        "deck_brief.md",
        "content_report.md",
        "design_spec.md",
        "slide_blueprint.md",
    ):
        (tmp_path / name).write_text(f"# {name}\n", encoding="utf-8")
    payload = {
        "schemaVersion": 1,
        "approvalStatus": approval,
        "planningSources": {
            "deckBrief": "deck_brief.md",
            "contentReport": "content_report.md",
            "designSpec": "design_spec.md",
            "slideBlueprint": "slide_blueprint.md",
        },
        "designSystem": {
            "styleProfile": "toss-data-unified",
            "accentColor": "#246BFD",
        },
        "slides": [
            {
                "id": "S01",
                "pageRole": "cover",
                "visualRole": "cover",
                "title": "고품질 3D 제품",
                "coreMessage": "제품 개념을 정확한 정보 구조에 결합합니다",
                "asset": {
                    "mode": "generate",
                    "role": "3d-scene",
                    "prompt": "Premium 3D clay automation product on white",
                    "refs": [],
                    "out": "assets/S01.png",
                },
                "htmlSpec": {
                    "layout": "cover",
                    "title": [{"text": "제품", "weight": "bold"}],
                    "callout": "3D는 자산만 담당합니다",
                    "facts": ["Codex asset", "HTML copy"],
                },
                "out": "slides/S01.png",
            },
            {
                "id": "S02",
                "pageRole": "workflow",
                "visualRole": "process",
                "title": "다섯 단계",
                "coreMessage": "단계 연결을 보여줍니다",
                "htmlSpec": {
                    "layout": "process",
                    "title": [{"text": "과정", "weight": "bold"}],
                    "items": [
                        {"label": "진단", "detail": "확인", "icon": "search"},
                        {"label": "설계", "detail": "정의", "icon": "nodes"},
                    ],
                },
                "out": "slides/S02.png",
            },
        ],
    }
    path = tmp_path / "design-production-plan.json"
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def test_approved_plan_compiles_dependency_safe_parallel_batches(tmp_path: Path) -> None:
    plan_path = _plan(tmp_path)
    out_dir = tmp_path / "production"

    receipt = design_plan.compile_plan(plan_path, out_dir)
    asset_jobs = json.loads((out_dir / "asset-jobs.json").read_text(encoding="utf-8"))
    slide_jobs = json.loads((out_dir / "slide-jobs.json").read_text(encoding="utf-8"))

    assert receipt["status"] == "COMPILED"
    assert receipt["slideCount"] == 2
    assert receipt["assetJobCount"] == 1
    assert [batch["kind"] for batch in receipt["batches"]] == [
        "codex-assets",
        "html-slides",
    ]
    assert asset_jobs[0]["renderer"] == "codex"
    assert asset_jobs[0]["styleVariant"] == "toss-3d"
    assert slide_jobs[0]["renderer"] == "html"
    assert slide_jobs[0]["htmlSpec"]["imagePath"] == "assets/S01.png"
    assert slide_jobs[0]["layout"] == "cover"
    assert slide_jobs[1]["styleVariant"] == "icon-editorial"
    assert receipt["assemblyOrder"][1]["image"] == "slides/S02.png"
    assert all(source["digest"].startswith("sha256:") for source in receipt["planningSources"])
    assert receipt["palettePreset"] == "editorial-blue"


def test_draft_plan_is_blocked_before_jobs_are_written(tmp_path: Path) -> None:
    plan_path = _plan(tmp_path, approval="draft")
    out_dir = tmp_path / "production"

    try:
        design_plan.compile_plan(plan_path, out_dir)
    except design_plan.DesignPlanError as error:
        assert "approvalStatus='approved'" in str(error)
    else:
        raise AssertionError("draft design plan was compiled")

    assert not out_dir.exists()
def test_cover_plan_blocks_generic_ai_headline(tmp_path: Path) -> None:
    plan_path = _plan(tmp_path)
    payload = json.loads(plan_path.read_text(encoding="utf-8"))
    payload["slides"][0]["title"] = "도구 도입을 넘어 운영 기준을 설계합니다"
    plan_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    try:
        design_plan.compile_plan(plan_path, tmp_path / "production")
    except design_plan.DesignPlanError as error:
        assert "generic AI phrase" in str(error)
    else:
        raise AssertionError("generic AI headline was compiled")
def test_palette_preset_applies_primary_and_secondary_roles(tmp_path: Path) -> None:
    plan_path = _plan(tmp_path)
    payload = json.loads(plan_path.read_text(encoding="utf-8"))
    payload["designSystem"].pop("accentColor", None)
    payload["designSystem"]["palettePreset"] = "ink-coral"
    payload["slides"][1]["colorRole"] = "secondary"
    plan_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    out_dir = tmp_path / "production"
    receipt = design_plan.compile_plan(plan_path, out_dir)
    jobs = json.loads((out_dir / "slide-jobs.json").read_text(encoding="utf-8"))

    assert receipt["palettePreset"] == "ink-coral"
    assert jobs[0]["htmlSpec"]["accent"] == "#D45745"
    assert jobs[1]["htmlSpec"]["accent"] == "#20242A"


def test_three_consecutive_same_layouts_are_blocked(tmp_path: Path) -> None:
    plan_path = _plan(tmp_path)
    payload = json.loads(plan_path.read_text(encoding="utf-8"))
    process = payload["slides"][1]
    payload["slides"].extend(
        [
            {**process, "id": "S03", "out": "slides/S03.png"},
            {**process, "id": "S04", "out": "slides/S04.png"},
        ]
    )
    plan_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    try:
        design_plan.compile_plan(plan_path, tmp_path / "production")
    except design_plan.DesignPlanError as error:
        assert "repeats layout 'process'" in str(error)
    else:
        raise AssertionError("three consecutive process layouts were compiled")
