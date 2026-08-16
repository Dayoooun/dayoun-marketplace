from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


DESIGN_DELEGATION = ("알아서", "전문적으로", "보기 좋게", "보기좋게", "디자인해")


def _contains(text: str, values: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(value.lower() in lowered for value in values)


def build_brief(request: str, *, mode: str = "REAL") -> dict[str, Any]:
    text = request.strip()
    if not text:
        raise ValueError("request must not be empty")
    if mode not in {"REAL", "DEMO"}:
        raise ValueError("mode must be REAL or DEMO")

    design_delegated = _contains(text, DESIGN_DELEGATION)
    outputs: list[str] = ["TEXT_DRAFT"]
    if _contains(text, ("hwpx", "한글 양식", "한글파일", "한글 파일")):
        outputs.append("HWPX")
    if _contains(text, ("ppt", "발표자료", "발표 자료", "발표덱")):
        outputs.append("PPT")

    fixed_constraints: list[dict[str, str]] = []
    if _contains(text, ("내용은 바꾸지", "내용 바꾸지", "문안은 바꾸지")):
        fixed_constraints.append(
            {"constraint": "preserve-approved-content", "source": "user-request"}
        )
    if _contains(text, ("원본 보존", "원본은 보존", "원본을 보존")):
        fixed_constraints.append(
            {"constraint": "preserve-source-file", "source": "user-request"}
        )
    for color in sorted(set(re.findall(r"#[0-9A-Fa-f]{6}(?![0-9A-Fa-f])", text))):
        fixed_constraints.append(
            {"constraint": f"brand-color:{color.upper()}", "source": "user-request"}
        )
    if design_delegated:
        fixed_constraints.append(
            {"constraint": "design-delegated-within-evidence", "source": "user-request"}
        )

    autonomous_actions = [
        "inventory-provided-files-and-existing-project",
        "lock-official-form-and-user-constraints",
        "preserve-source-and-create-working-copy",
        "map-requirements-to-evidence-and-sections",
    ]
    if "HWPX" in outputs:
        autonomous_actions.extend(
            [
                "inventory-hwpx-page-table-paragraph-and-style-structure",
                "create-hwpx-design-decision-table",
                "apply-approved-content-and-delegated-design-to-working-copy",
                "validate-source-structure-and-hwpx-package",
                "render-pdf-and-page-pngs-for-full-page-100-percent-and-zoom-qa",
            ]
        )
    if "PPT" in outputs:
        autonomous_actions.append("create-and-render-approved-presentation")

    material_decisions = [
        {
            "decision": "question-round",
            "requiredWhen": "customer-use-case-or-problem-remains-unknown",
            "agentBehavior": "recommend-one-evidence-based-framing-and-ask-once",
        },
        {
            "decision": "strategy",
            "requiredWhen": "multiple-material-strategies-remain",
            "agentBehavior": "recommend-one-option-with-tradeoffs",
        },
        {
            "decision": "content-approval",
            "requiredWhen": "before-final-hwpx-or-ppt",
            "agentBehavior": "never-infer-or-self-approve",
        },
        {
            "decision": "publication-approval",
            "requiredWhen": "before-submit-publish-or-send",
            "agentBehavior": "never-infer-or-self-approve",
        },
    ]

    return {
        "schemaVersion": "1.0.0",
        "entrySkill": "complete-business-plan",
        "interactionMode": mode,
        "request": text,
        "requestedOutputs": outputs,
        "designDelegated": design_delegated,
        "fixedConstraints": fixed_constraints,
        "status": "READY_FOR_REVERSIBLE_WORK",
        "nextAction": autonomous_actions[0],
        "autonomousActions": autonomous_actions,
        "materialDecisions": material_decisions,
        "approvalGates": {
            "questionRound": mode == "REAL",
            "strategyDecision": mode == "REAL",
            "contentApproval": mode == "REAL",
            "designChoice": mode == "REAL" and "HWPX" in outputs and not design_delegated,
            "hwpxChoice": False,
            "presentationChoice": False,
            "publicationApproval": mode == "REAL",
        },
        "recommendedAction": (
            "Preserve the official form and approved content, then apply one semantic "
            "information-design direction to a working copy before render QA."
            if "HWPX" in outputs
            else "Inspect the supplied evidence and official requirements before drafting."
        ),
        "completionRequirements": {
            "noFabricatedFactsOrApprovals": True,
            "resultHwpxRequired": "HWPX" in outputs,
            "sourceStructureIntegrityRequired": "HWPX" in outputs,
            "pdfAndPagePngRenderReceiptRequired": "HWPX" in outputs,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalize a natural-language business-plan request into a lead brief."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--request")
    group.add_argument("--request-file", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--mode", choices=("REAL", "DEMO"), default="REAL")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    request = (
        args.request_file.read_text(encoding="utf-8")
        if args.request_file is not None
        else args.request
    )
    brief = build_brief(request, mode=args.mode)
    serialized = json.dumps(brief, ensure_ascii=False, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8", newline="\n")
    print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
