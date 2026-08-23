#!/usr/bin/env python3
"""Compile an approved deck design plan into dependency-safe parallel render batches."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
SKILL_ROOT = HERE.parent
CONTRACT_PATH = SKILL_ROOT / "references" / "render_contract.json"

sys.path.insert(0, str(HERE))
from style_profile import reference_assets, select_variant  # noqa: E402


class DesignPlanError(ValueError):
    pass


def _reject_constant(value: str):
    raise DesignPlanError(f"non-finite JSON constant {value!r} is not allowed")


def _read_json(path: Path) -> dict:
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=_reject_constant,
        )
    except (OSError, json.JSONDecodeError) as error:
        raise DesignPlanError(f"cannot read design plan {path}: {error}") from error
    if not isinstance(payload, dict):
        raise DesignPlanError("design plan root must be an object")
    return payload


def _digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _clean_rel(value: Any, field: str) -> str:
    text = str(value or "").strip().replace("\\", "/")
    if not text or text.startswith("/") or ":" in text.split("/")[0]:
        raise DesignPlanError(f"{field} must be a non-empty relative path")
    if ".." in Path(text).parts:
        raise DesignPlanError(f"{field} cannot escape the project directory")
    return text


def _required_text(payload: dict, field: str, scope: str) -> str:
    value = str(payload.get(field, "")).strip()
    if not value:
        raise DesignPlanError(f"{scope} requires {field}")
    return value


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def compile_plan(plan_path: Path, out_dir: Path) -> dict:
    plan_path = plan_path.resolve()
    project_dir = plan_path.parent
    payload = _read_json(plan_path)
    if payload.get("schemaVersion") != 1:
        raise DesignPlanError("schemaVersion must be 1")
    if payload.get("approvalStatus") != "approved":
        raise DesignPlanError("design plan must have approvalStatus='approved'")

    design = payload.get("designSystem")
    if not isinstance(design, dict):
        raise DesignPlanError("designSystem is required")
    profile = str(design.get("styleProfile") or "toss-data-unified")
    accent = _required_text(design, "accentColor", "designSystem")
    if not accent.startswith("#") or len(accent) not in {4, 7}:
        raise DesignPlanError("designSystem.accentColor must be a hex colour")
    sources = payload.get("planningSources")
    if not isinstance(sources, dict):
        raise DesignPlanError("planningSources is required")
    required_sources = ["deckBrief", "contentReport", "designSpec", "slideBlueprint"]
    source_manifest = []
    for field in required_sources:
        rel = _clean_rel(sources.get(field), f"planningSources.{field}")
        path = (project_dir / rel).resolve()
        if not path.is_file():
            raise DesignPlanError(f"planning source is missing: {rel}")
        source_manifest.append({"kind": field, "path": rel, "digest": _digest(path)})

    contract = _read_json(CONTRACT_PATH)
    layout_by_role = contract["contextRouting"]["visualRoleToLayout"]
    renderer_by_layout = contract["contextRouting"]["rendererByLayout"]
    asset_roles = set(contract["rendererDecision"]["codexAssetRoles"])
    slides = payload.get("slides")
    if not isinstance(slides, list) or not slides:
        raise DesignPlanError("slides must be a non-empty array")

    ids: set[str] = set()
    asset_jobs: list[dict] = []
    slide_jobs: list[dict] = []
    decisions: list[dict] = []
    assembly_order: list[dict] = []
    for index, slide in enumerate(slides, 1):
        if not isinstance(slide, dict):
            raise DesignPlanError(f"slide {index} must be an object")
        slide_id = _required_text(slide, "id", f"slide {index}")
        if slide_id in ids:
            raise DesignPlanError(f"duplicate slide id: {slide_id}")
        ids.add(slide_id)
        visual_role = _required_text(slide, "visualRole", slide_id)
        if visual_role not in layout_by_role:
            raise DesignPlanError(f"{slide_id} has unknown visualRole {visual_role!r}")
        expected_layout = layout_by_role[visual_role]
        html_spec = slide.get("htmlSpec")
        if not isinstance(html_spec, dict):
            raise DesignPlanError(f"{slide_id} requires htmlSpec")
        explicit_layout = html_spec.get("layout")
        if explicit_layout and explicit_layout != expected_layout:
            raise DesignPlanError(
                f"{slide_id} layout {explicit_layout!r} conflicts with {visual_role!r}"
            )
        html_spec = dict(html_spec)
        html_spec["layout"] = expected_layout
        html_spec.setdefault("accent", accent)
        title = _required_text(slide, "title", slide_id)
        core_message = _required_text(slide, "coreMessage", slide_id)
        routing_text = " ".join(
            [visual_role, str(slide.get("pageRole", "")), title, core_message]
        )
        variant = select_variant(
            profile,
            routing_text,
            requested=slide.get("styleVariant"),
        )

        asset = slide.get("asset")
        asset_label = None
        if asset is not None:
            if not isinstance(asset, dict):
                raise DesignPlanError(f"{slide_id}.asset must be an object")
            asset_role = _required_text(asset, "role", f"{slide_id}.asset")
            if asset_role not in asset_roles:
                raise DesignPlanError(f"{slide_id} has unsupported asset role {asset_role!r}")
            mode = str(asset.get("mode") or "generate")
            asset_out = _clean_rel(asset.get("out"), f"{slide_id}.asset.out")
            if mode == "generate":
                prompt = _required_text(asset, "prompt", f"{slide_id}.asset")
                supplied_refs = []
                for ref in asset.get("refs", []):
                    ref_rel = _clean_rel(ref, f"{slide_id}.asset.refs")
                    ref_path = (project_dir / ref_rel).resolve()
                    if not ref_path.is_file():
                        raise DesignPlanError(f"asset reference is missing: {ref_rel}")
                    supplied_refs.append(str(ref_path))
                automatic_refs = reference_assets(profile, variant, routing_text)
                refs = _unique(supplied_refs + automatic_refs)
                if not refs:
                    raise DesignPlanError(f"{slide_id} generated asset requires refs")
                asset_label = f"asset-{slide_id}"
                asset_jobs.append({
                    "label": asset_label,
                    "renderer": "codex",
                    "styleProfile": profile,
                    "styleVariant": variant,
                    "assetRole": asset_role,
                    "prompt": prompt,
                    "refs": refs,
                    "out": asset_out,
                })
            elif mode == "provided":
                source = (project_dir / asset_out).resolve()
                if not source.is_file():
                    raise DesignPlanError(f"provided asset is missing: {asset_out}")
            else:
                raise DesignPlanError(f"{slide_id}.asset.mode must be generate or provided")
            html_spec["imagePath"] = (
                asset_out
                if mode == "generate"
                else str((project_dir / asset_out).resolve())
            )
            html_spec["assetRole"] = asset_role

        out = _clean_rel(slide.get("out"), f"{slide_id}.out")
        slide_jobs.append({
            "label": slide_id,
            "renderer": "html",
            "layout": expected_layout,
            "styleProfile": profile,
            "styleVariant": variant,
            "htmlSpec": html_spec,
            "out": out,
        })
        decisions.append({
            "id": slide_id,
            "visualRole": visual_role,
            "layout": expected_layout,
            "renderer": renderer_by_layout[expected_layout],
            "styleVariant": variant,
            "assetDependency": asset_label,
        })
        assembly_order.append({"slide": index, "id": slide_id, "image": out})

    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    asset_jobs_path = out_dir / "asset-jobs.json"
    slide_jobs_path = out_dir / "slide-jobs.json"
    asset_jobs_path.write_text(
        json.dumps(asset_jobs, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    slide_jobs_path.write_text(
        json.dumps(slide_jobs, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    receipt = {
        "schemaVersion": 1,
        "status": "COMPILED",
        "plan": str(plan_path),
        "planDigest": _digest(plan_path),
        "planningSources": source_manifest,
        "styleProfile": profile,
        "accentColor": accent,
        "slideCount": len(slide_jobs),
        "assetJobCount": len(asset_jobs),
        "batches": [
            {"order": 1, "kind": "codex-assets", "parallel": True, "jobs": asset_jobs_path.name},
            {"order": 2, "kind": "html-slides", "parallel": True, "jobs": slide_jobs_path.name},
        ],
        "decisions": decisions,
        "assemblyOrder": assembly_order,
    }
    receipt_path = out_dir / "design-execution-plan.json"
    receipt_path.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return receipt


def execute_plan(out_dir: Path, cap: int, retry: int, effort: str) -> None:
    generator = HERE / "codex_parallel_gen.py"
    for jobs_name in ("asset-jobs.json", "slide-jobs.json"):
        jobs_path = out_dir / jobs_name
        jobs = json.loads(jobs_path.read_text(encoding="utf-8"))
        if not jobs:
            continue
        command = [
            sys.executable,
            str(generator),
            str(jobs_path),
            "--cap",
            str(cap),
            "--retry",
            str(retry),
            "--effort",
            effort,
        ]
        subprocess.run(command, check=True, cwd=out_dir)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compile an approved design plan, then run dependency-safe parallel production"
    )
    parser.add_argument("plan", type=Path)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--cap", type=int, default=6)
    parser.add_argument("--retry", type=int, default=1)
    parser.add_argument("--effort", default="high")
    args = parser.parse_args()
    try:
        receipt = compile_plan(args.plan, args.out_dir)
        if args.execute:
            execute_plan(args.out_dir.resolve(), args.cap, args.retry, args.effort)
            receipt["status"] = "EXECUTED"
            (args.out_dir.resolve() / "design-execution-plan.json").write_text(
                json.dumps(receipt, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                encoding="utf-8",
            )
    except (DesignPlanError, subprocess.CalledProcessError) as error:
        print(f"BLOCK: {error}", file=sys.stderr)
        return 1
    print(json.dumps(receipt, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
