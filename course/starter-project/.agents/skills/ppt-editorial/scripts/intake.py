# -*- coding: utf-8 -*-
"""PPT 요구사항 명확화 인터뷰와 확인 게이트.

에이전트가 긴 설문을 한 번에 던지지 않도록 한 라운드에 최대 세 질문만 제시한다.
핵심 정보가 모이면 먼저 기준 판단을 보여 주고 사용자가 확인하거나 고친 뒤에만
덱 생성 단계로 넘어간다.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import re
from typing import Any


class IntakeBlocked(RuntimeError):
    """요구사항이 덜 채워졌거나 사용자 확인이 끝나지 않았을 때 발생한다."""

    def __init__(self, assessment: dict[str, Any]):
        self.assessment = assessment
        if assessment["phase"] == "intake":
            detail = " / ".join(q["text"] for q in assessment["questions"])
        else:
            detail = assessment.get("confirmation_prompt", "요구사항 확인이 필요합니다.")
        super().__init__(detail)


QUESTION_BANK = [
    {
        "id": "purpose",
        "text": "이 PPT로 최종적으로 얻어야 하는 결과는 무엇인가요?",
        "examples": ["제안 승인", "발표 심사", "교육", "결과 보고", "제품 소개"],
    },
    {
        "id": "audience",
        "text": "누가 보고 무엇을 판단하게 되나요?",
        "examples": ["고객", "투자자", "심사위원", "상사", "수강생"],
    },
    {
        "id": "delivery_context",
        "text": "어디서 어떤 방식으로 전달하나요?",
        "examples": ["10분 대면 발표", "이메일 제출", "강의", "회의 브리핑"],
    },
    {
        "id": "length",
        "text": "발표 시간이나 원하는 장수 중 하나를 알려주세요.",
        "examples": ["10분", "12장", "제한 없음"],
    },
    {
        "id": "source_materials",
        "text": "원고·보고서·사진·표·기존 PPT 중 사용할 자료가 있나요? 없으면 없다고 적어주세요.",
        "examples": ["사업계획서.hwpx", "제품 사진 폴더", "없음"],
    },
    {
        "id": "identity_anchors",
        "text": "반드시 유지할 회사명·제품명·로고·기관명 같은 식별 기준이 있나요?",
        "examples": ["회사명과 로고", "제품명", "없음"],
    },
    {
        "id": "output_editability",
        "text": "현재 하네스의 PPTX는 슬라이드가 한 장 이미지라 글자를 직접 편집할 수 없습니다. 이 형식으로 진행할까요?",
        "examples": ["이미지형 PPTX로 진행", "텍스트 편집형 제작 경로로 변경"],
    },
]

_PURPOSE_SPINES = {
    "proposal": "현황과 문제 → 제안 해법 → 실행 범위 → 기대 결과 → 다음 결정",
    "report": "목표와 기준 → 수행 내용 → 결과와 근거 → 한계 → 후속 조치",
    "lecture": "학습 목표 → 핵심 개념 → 사례 → 적용 절차 → 확인 문제",
    "pitch": "문제 → 고객과 시장 → 해법 → 검증 → 실행 계획 → 요청",
    "briefing": "결론 → 판단 근거 → 선택지 → 위험 → 요청 사항",
    "redesign": "기존 메시지 진단 → 유지 요소 → 재구성 원칙 → 새 흐름",
}


def _present(value: Any) -> bool:
    return value is not None and (not isinstance(value, str) or bool(value.strip()))


def normalize(brief: dict[str, Any]) -> dict[str, Any]:
    """입력값을 복사하고 안전한 기본값만 채운다."""
    data = copy.deepcopy(brief)
    data.setdefault("language", "ko")
    data.setdefault("mode", "auto")
    data.setdefault("editable_text_required", False)
    data.setdefault("must_include", [])
    data.setdefault("must_avoid", [])
    data.setdefault("assumptions", [])
    data.setdefault("open_questions", [])
    output = data.setdefault("output", {})
    output.setdefault("primary", "pptx")
    output.setdefault("secondary", "pdf")
    return data


def _missing_ids(data: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for key in ("purpose", "audience", "delivery_context"):
        if not _present(data.get(key)):
            missing.append(key)
    if not (_present(data.get("duration_minutes")) or _present(data.get("slide_count"))):
        missing.append("length")
    # 빈 목록은 "자료 없음" 또는 "식별 기준 없음"을 명시한 유효 답변이다.
    for key in ("source_materials", "identity_anchors"):
        if key not in data or data[key] is None:
            missing.append(key)
    if data.get("editable_text_required") and not data.get("flattened_pptx_accepted"):
        missing.append("output_editability")
    return missing


def _recommended_mode(data: dict[str, Any]) -> str:
    requested = str(data.get("mode", "auto")).lower()
    if requested in {"scene", "scene-deck", "image-first"}:
        return "scene-deck" if requested in {"scene", "scene-deck"} else "image-first"
    if data.get("visual_first") and not data.get("editable_text_required"):
        return "image-first"
    return "scene-deck"


def _page_range(data: dict[str, Any]) -> str:
    if _present(data.get("slide_count")):
        count = max(1, int(data["slide_count"]))
        return f"{count}장"
    minutes = max(1, int(data.get("duration_minutes", 10)))
    center = max(5, min(30, round(minutes / 1.3)))
    return f"{max(4, center - 2)}~{center + 2}장"


def _baseline(data: dict[str, Any]) -> dict[str, Any]:
    purpose = str(data.get("purpose", "other")).lower()
    return {
        "deck_goal": data.get("purpose"),
        "target_audience": data.get("audience"),
        "delivery_context": data.get("delivery_context"),
        "recommended_mode": _recommended_mode(data),
        "recommended_page_range": _page_range(data),
        "narrative_spine": _PURPOSE_SPINES.get(
            purpose, "목표와 배경 → 핵심 메시지 → 근거 → 실행 또는 요청"
        ),
        "usable_identity_anchors": data.get("identity_anchors", []),
        "material_status": "제공 자료 있음" if data.get("source_materials") else "제공 자료 없음",
        "assumptions": data.get("assumptions", []),
        "output_caveat": (
            "PPTX는 슬라이드 전면 이미지 방식이라 내부 텍스트를 직접 편집할 수 없습니다."
        ),
    }


def assess(brief: dict[str, Any], max_questions: int = 3) -> dict[str, Any]:
    """현재 인터뷰 단계, 다음 질문, 기준 판단과 진행 가능 여부를 반환한다."""
    data = normalize(brief)
    missing = _missing_ids(data)
    if missing:
        by_id = {q["id"]: q for q in QUESTION_BANK}
        questions = [copy.deepcopy(by_id[key]) for key in missing[:max(1, max_questions)]]
        return {
            "phase": "intake",
            "ready": False,
            "normalized": data,
            "missing": missing,
            "questions": questions,
            "rule": "한 라운드 최대 3개만 묻고 답을 반영한 뒤 다시 평가합니다.",
        }

    baseline = _baseline(data)
    if not data.get("requirements_confirmed"):
        return {
            "phase": "confirmation",
            "ready": False,
            "normalized": data,
            "missing": [],
            "questions": [],
            "baseline": baseline,
            "confirmation_prompt": (
                "위 요구사항 기준 판단이 맞는지 확인해 주세요. 틀린 항목은 고쳐 적고, "
                "맞으면 requirements_confirmed=true로 승인합니다."
            ),
        }

    return {
        "phase": "ready",
        "ready": True,
        "normalized": data,
        "missing": [],
        "questions": [],
        "baseline": baseline,
    }


def apply_answers(brief: dict[str, Any], answers: dict[str, Any],
                  confirm: bool = False) -> dict[str, Any]:
    """사용자 답변과 정정을 기존 브리프에 반영한다."""
    data = copy.deepcopy(brief)
    for key, value in answers.items():
        if key == "length":
            if isinstance(value, (int, float)):
                data["duration_minutes"] = value
            continue
        if key == "output_editability":
            data["flattened_pptx_accepted"] = bool(value)
            continue
        data[key] = copy.deepcopy(value)
    if confirm:
        data["requirements_confirmed"] = True
    elif answers:
        # 확인 뒤 요구사항이 바뀌면 이전 승인을 자동 무효화한다.
        data["requirements_confirmed"] = False
    return normalize(data)


def require_confirmed(brief: dict[str, Any]) -> dict[str, Any]:
    """확정된 브리프만 반환하고 그 외에는 다음 질문이 포함된 예외를 낸다."""
    result = assess(brief)
    if not result["ready"]:
        raise IntakeBlocked(result)
    return result["normalized"]


def load_brief(path: str | os.PathLike) -> dict[str, Any]:
    """JSON 파일 또는 Markdown의 ```json 펜스에서 브리프를 읽는다."""
    file_path = os.path.abspath(os.fspath(path))
    with open(file_path, encoding="utf-8") as handle:
        text = handle.read()
    if file_path.lower().endswith(".md"):
        match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
        if not match:
            raise ValueError("deck_brief.md에 ```json 객체가 없습니다.")
        return json.loads(match.group(1))
    return json.loads(text)


def save_brief(path: str | os.PathLike, brief: dict[str, Any]) -> str:
    """브리프를 원래 JSON/Markdown 형식을 유지해 저장한다."""
    file_path = os.path.abspath(os.fspath(path))
    payload = json.dumps(normalize(brief), ensure_ascii=False, indent=2)
    if file_path.lower().endswith(".md"):
        if os.path.exists(file_path):
            with open(file_path, encoding="utf-8") as handle:
                text = handle.read()
        else:
            text = "# deck_brief.md\n\n```json\n{}\n```\n"
        pattern = re.compile(r"```json\s*\{.*?\}\s*```", re.DOTALL)
        replacement = "```json\n" + payload + "\n```"
        if not pattern.search(text):
            raise ValueError("deck_brief.md에 교체할 ```json 객체가 없습니다.")
        output = pattern.sub(lambda _: replacement, text, count=1)
    else:
        output = payload + "\n"
    with open(file_path, "w", encoding="utf-8") as handle:
        handle.write(output)
    return file_path


def main() -> int:
    parser = argparse.ArgumentParser(description="PPT 요구사항 인터뷰 상태 검사")
    parser.add_argument("brief_path")
    parser.add_argument("--confirm", action="store_true",
                        help="누락이 없으면 사용자 확인 상태를 파일에 기록")
    parser.add_argument("--max-questions", type=int, default=3)
    args = parser.parse_args()

    path = os.path.abspath(args.brief_path)
    brief = load_brief(path)
    result = assess(brief, args.max_questions)
    if args.confirm:
        if result["phase"] == "intake":
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 2
        brief["requirements_confirmed"] = True
        save_brief(path, brief)
        result = assess(brief)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
