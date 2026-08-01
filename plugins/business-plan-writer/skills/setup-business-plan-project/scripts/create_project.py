#!/usr/bin/env python3
"""Create a safe, reusable business-plan project folder."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


FOLDERS = (
    "00. 시작하기",
    "01. 사업정보/공유가능 원본",
    "02. 목적 및 요구사항/원본",
    "03. 사업계획서양식/원본",
    "03. 사업계획서양식/작업용 HWPX",
    "04. 조사자료/출처원문",
    "05. 작성초안",
    "06. 검토결과",
    "07. 최종본",
    "99. 원본백업",
)


TEMPLATES = {
    "00. 시작하기/프로젝트상태.md": """# 프로젝트 상태

- 사용 목적: {purpose}
- 자료 사용 모드: {mode}
- 문서 독자: {확인필요}
- 문서에서 내려야 할 결정: {확인필요}
- 현재 단계: 자료 준비

## 진행 확인

- [ ] 사용 목적과 독자 확인
- [ ] 공유 가능한 사업 정보 정리
- [ ] 공식 요구사항 또는 필요한 장·절 정리
- [ ] 원본과 작업 사본 분리
- [ ] 가장 중요한 보완점 선택
- [ ] 필요한 조사와 출처 확인
- [ ] 초안 작성
- [ ] 범위에 맞는 검토와 사용자 승인
- [ ] 다음 행동 정리
- [ ] HWPX 사용 시 구조검사와 한글 화면 확인

## 다음 행동

1. 사업 아이디어의 고객·사용 상황·문제를 한 문장으로 기록
2. 사용할 수 있는 원본 자료 배치
3. 공식 공고·평가표·양식이 있으면 원본 폴더에 복사
4. QUICK / SECTION / FULL 중 작업 범위 선택
""",
    "00. 시작하기/계획프로필.json": """{
  "purpose": {purpose_json},
  "reader": "",
  "decision": "",
  "document_name": "",
  "deadline": "",
  "official_program": {
    "name": "",
    "track": {track_json}
  },
  "requirements_source": "",
  "requirements_status": "unknown",
  "required_sections": [],
  "template_received": false,
  "notes": "확인한 정보만 입력하고 모르면 빈 값 또는 unknown으로 유지"
}
""",
    "00. 시작하기/입력자료목록.csv": "file_id,file_name,document_type,version_or_date,owner,sharing_level,masked,read_status,notes\n",
    "00. 시작하기/작업범위.md": """# 작업 범위

- 범위: {확인필요: QUICK / SECTION / FULL}
- 대상 장·절: {확인필요}
- 가장 중요한 보완점: {확인필요}
- 확인할 질문: {확인필요}
- 사용할 근거: {확인필요}
- HWPX 사용: {확인필요: 사용 안 함 / 자동 치환 / 수동 반영}
""",
    "00. 시작하기/근거목록.csv": "evidence_id,related_section,statement,source_name,source_path_or_url,published_or_recorded_date,base_date,unit,checked_on,status,limitations,notes\n",
    "00. 시작하기/요구사항추적표.csv": "requirement_id,official_or_internal_requirement,source_location,required_or_optional,length_limit,draft_file,evidence_ids,status\n",
    "01. 사업정보/사업정보표.md": """# 사업정보표

사용자가 제공한 내용도 아직 확인하지 않았다면 `사용자 제공·미확인`으로 표시합니다. 사실, 가정, 앞으로 할 계획을 구분합니다.

| 구분 | 내용 | 근거 파일·위치 | 상태 |
|---|---|---|---|
| 문제를 발견한 배경 |  |  | 확인필요 |
| 제품·서비스 한 문장 |  |  | 확인필요 |
| 목표고객과 사용 상황 |  |  | 확인필요 |
| 현재 보유 기술·자원 |  |  | 확인필요 |
| 확인된 실적 |  |  | 확인필요 |
| 앞으로 할 계획 |  |  | 계획 |
""",
    "01. 사업정보/누락정보.md": "# 누락정보\n\n- [ ] {확인필요}\n",
    "02. 목적 및 요구사항/목적과요구사항.md": """# 목적과 요구사항

공식 공고·평가표·작성요령이 있으면 그 원문을 우선합니다. 공식 기준이 없으면 독자와 의사결정 목적에 맞춰 필요한 장·절을 정합니다.

| 번호 | 요구사항 | 출처·위치 | 필요한 내용·근거 | 상태 |
|---|---|---|---|---|
| R001 | {확인필요} |  |  | 확인필요 |
""",
    "02. 목적 및 요구사항/보완점진단표.md": """# 보완점 진단표

- 기준 문서: {확인필요}
- 검토 범위: {확인필요}
- 가장 중요한 보완점: {확인필요}
- 왜 먼저 보완하는가: {확인필요}
- 확인할 질문: {확인필요}
- 필요한 정보 또는 근거: {확인필요}
""",
    "03. 사업계획서양식/template-field-map.csv": "field_id,official_prompt,page_or_location,length_limit,placeholder,insertion_mode,status\n",
    "03. 사업계획서양식/placeholder-values.draft.json": """{
  "_approval": {
    "status": "DRAFT",
    "approved_by": "",
    "approved_at": "",
    "source_draft": ""
  },
  "values": {}
}
""",
    "03. 사업계획서양식/placeholder-values.approved.json": """{
  "_approval": {
    "status": "NOT_APPROVED",
    "approved_by": "",
    "approved_at": "",
    "source_draft": ""
  },
  "values": {}
}
""",
    "04. 조사자료/조사질문.md": """# 조사질문

1. 목표고객은 어떤 상황에서 이 문제를 경험하는가?
2. 현재 어떤 대안을 사용하고 무엇이 부족한가?
3. 시장·가격·비용 관련 설명을 확인할 가장 믿을 만한 자료는 무엇인가?
4. 이 사업의 가장 큰 가정을 확인할 작은 실험은 무엇인가?
""",
    "04. 조사자료/조사기록.md": """# 조사기록

- 확인할 내용: {확인필요}
- 출처 또는 고객 기록: {확인필요}
- 작성 기관·기록 주체: {확인필요}
- 발표일·기준일·인터뷰일: {확인필요}
- 확인한 내용: {확인필요}
- 이 자료만으로 말할 수 없는 것: {확인필요}
- 다음 확인 행동: {확인필요}
""",
    "04. 조사자료/시장조사.md": "# 시장조사\n\n출처, 발표일, 기준연도, 단위를 함께 기록합니다.\n",
    "04. 조사자료/경쟁대안비교.csv": "대상,고객,사용상황,핵심기능,가격,강점,한계,출처,확인일\n",
    "05. 작성초안/사업계획서초안.md": """# 사업계획서 초안

## 목적과 한 문장 요약

{확인필요}

## 문제와 고객

{확인필요}

## 해결책과 차별점

{확인필요}

## 시장과 수익 구조

{확인필요}

## 실행계획과 팀

{확인필요}

## 비용·재원·성과지표

{확인필요}

## 위험과 다음 검증

{확인필요}
""",
    "05. 작성초안/문안승인.md": """# 문안 승인

- 승인 상태: NOT_APPROVED
- 승인 대상 파일·버전: {확인필요}
- 승인자: {확인필요}
- 승인 일시: {확인필요}
- 공개 가능한 내용 확인: {확인필요}
- 확인필요 항목 처리: {확인필요}
""",
    "06. 검토결과/내용검토.md": """# 내용 검토

- 검토 상태: NOT_RUN
- 검토 범위: {확인필요: QUICK / SECTION / FULL}
- 검토 대상 버전: {확인필요}
- 범위 안의 필수 항목 수: {확인필요}
- 범위 안의 확인 필요한 문장 수: {확인필요}
- 범위 밖 항목: NOT_REVIEWED
- PASS: -
- WARN: -
- BLOCK: -
""",
    "06. 검토결과/변경기록.md": """# 변경기록

| 위치 | 이전 내용 | 확인한 정보·의견 | 결정 | 바꾼 내용 | 남은 질문 |
|---|---|---|---|---|---|
|  |  |  | 유지/수정/보류 |  |  |
""",
    "06. 검토결과/HWPX검토.md": """# HWPX 검토

- 검토 상태: NOT_RUN
- 검토 대상 파일: {확인필요}
- 구조검사: {확인필요}
- 미치환 항목: {확인필요}
- 한글 화면 확인: {확인필요}
""",
    "07. 최종본/최종확인.md": """# 최종 확인

- [ ] 목적과 독자에 맞는 필수 항목 포함
- [ ] 사실, 가정, 계획 구분
- [ ] 숫자와 고유명사 일치
- [ ] 출처·날짜·단위·한계 확인
- [ ] 근거 없는 과장 표현 제거
- [ ] 개인정보와 비공개정보 확인
- [ ] 사용자 승인 문안만 사용
- [ ] 원본과 최종본을 구분해 보관
- [ ] HWPX 사용 시 구조검사와 한글 화면 확인
""",
    "07. 최종본/다음행동.md": """# 다음 행동

- 할 일: {확인필요}
- 담당자: {확인필요}
- 기한: {확인필요}
- 완료 기준: {확인필요}
- 결과를 반영할 문서 위치: {확인필요}
""",
    "07. 최종본/release-manifest.md": """# 결과물 상태

- 완료 범위: NOT_SET
- 허용값: QUICK / SECTION / FULL
- 최종 파일: {확인필요}
- 승인한 초안 버전: {확인필요}
- 내용 검토 상태: NOT_RUN
- HWPX 검토 상태: NOT_RUN
- 한글 화면 확인: NOT_RUN
""",
}


def render_template(template: str, purpose: str, track: str, mode: str) -> str:
    return (
        template.replace("{purpose_json}", json.dumps(purpose, ensure_ascii=False))
        .replace("{track_json}", json.dumps(track, ensure_ascii=False))
        .replace("{purpose}", purpose)
        .replace("{mode}", mode)
    )


def safe_write(path: Path, content: str, force: bool) -> str:
    if path.exists():
        try:
            current = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            return "PROTECTED_MODIFIED" if force else "SKIP"
        if current == content:
            return "SAME"
        return "PROTECTED_MODIFIED" if force else "SKIP"
    path.write_text(content, encoding="utf-8", newline="\n")
    return "WRITE"


def main() -> int:
    parser = argparse.ArgumentParser(description="사업계획서 프로젝트 폴더 생성")
    parser.add_argument("--path", required=True, help="생성할 프로젝트 폴더")
    parser.add_argument(
        "--purpose",
        default="unknown",
        help="지원사업, 투자·IR, 사내 검토, 대출·제안, 교육, 기타. 모르면 unknown",
    )
    parser.add_argument(
        "--track",
        default="unknown",
        help="공식 사업의 트랙명. 해당 없거나 모르면 unknown",
    )
    parser.add_argument(
        "--mode",
        choices=("DEMO", "PARTIAL", "REAL"),
        default="PARTIAL",
        help="입력자료 사용 모드",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="사용자 수정 파일은 덮어쓰지 않고 보호 상태로 보고",
    )
    args = parser.parse_args()

    project = Path(args.path).expanduser().resolve()
    if project == Path(project.anchor):
        parser.error("드라이브 또는 파일시스템 루트에는 프로젝트를 만들 수 없습니다.")

    project.mkdir(parents=True, exist_ok=True)
    for folder in FOLDERS:
        (project / folder).mkdir(parents=True, exist_ok=True)

    results: dict[str, list[str]] = {
        "WRITE": [],
        "SAME": [],
        "SKIP": [],
        "PROTECTED_MODIFIED": [],
    }
    for relative, template in TEMPLATES.items():
        target = project / relative
        content = render_template(template, args.purpose, args.track, args.mode)
        results[safe_write(target, content, args.force)].append(relative)

    print(f"PROJECT: {project}")
    print(f"CREATED: {len(results['WRITE'])}")
    print(f"UNCHANGED: {len(results['SAME'])}")
    print(f"PRESERVED_EXISTING: {len(results['SKIP'])}")
    print(f"PROTECTED_MODIFIED: {len(results['PROTECTED_MODIFIED'])}")
    for item in results["PROTECTED_MODIFIED"]:
        print(f"  ! {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
