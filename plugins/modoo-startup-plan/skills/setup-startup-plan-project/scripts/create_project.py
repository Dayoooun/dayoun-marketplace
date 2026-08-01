#!/usr/bin/env python3
"""Create a safe, repeatable startup-plan project folder."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

FOLDERS = (
    "00. 시작하기",
    "01. 회사내용/공유가능 원본",
    "02. 공고문 및 평가지표/원본",
    "03. 사업계획서양식/원본 HWP 보관",
    "03. 사업계획서양식/작업용 HWPX",
    "04. 시장조사 리서치/출처원문",
    "05. 작성초안",
    "06. 검토결과",
    "07. 최종본",
    "99. 원본백업",
)

TEMPLATES = {
    "00. 시작하기/프로젝트상태.md": """# 프로젝트 상태

- 트랙: {track}
- 작업 모드: {mode}
- 완료 수준: {확인필요: FALLBACK / DRY_RUN / FULL}
- 제출물 명칭: {확인필요}
- 제출 마감: {확인필요}
- 제출 후 수정 가능 여부: {확인필요}
- 현재 단계: 자료 준비

## 완료

- [ ] 회사자료 배치
- [ ] 공고·평가기준 배치
- [ ] 제출본 원본과 작업 사본 분리
- [ ] 공백진단표 작성
- [ ] 검증·활동 기록 작성
- [ ] 멘토링 변화기록 작성
- [ ] 다음 공식 마감 실행카드와 1분 IR 작성
- [ ] 콘텐츠 검토 실행
- [ ] 대표자 문안 승인
- [ ] 조건부 HWPX 경로 사용 여부 확인
- [ ] HWPX 사용 시 구조·산출물·한글 육안검수 완료

## 다음 행동

1. 실제 트랙과 제출물 명칭 확인
2. 공유 가능한 회사자료 배치
3. 제출본 사본과 공고문·평가표 배치
4. Green / Yellow / Red 실습 경로 결정
""",
    "00. 시작하기/프로그램프로필.json": """{
  "program_name": "",
  "program_pack": "generic",
  "track": {track_json},
  "submission_name": "",
  "deadline": "",
  "post_submission_edit": "unknown",
  "criteria_source": "",
  "criteria_status": "unknown",
  "criteria": [],
  "form_received": false,
  "user_provided_summary": "",
  "notes": "공식 원문에서 확인한 값만 입력"
}
""",
    "00. 시작하기/제출요건.md": """# 제출요건

| 항목 | 공식 요구 | 원문 위치 | 상태 |
|---|---|---|---|
| 제출물 명칭 | {확인필요} |  | 확인필요 |
| 마감 | {확인필요} |  | 확인필요 |
| 파일 형식 | {확인필요} |  | 확인필요 |
| 페이지·용량 | {확인필요} |  | 확인필요 |
| 제출 후 수정 | {확인필요} |  | 확인필요 |
""",
    "00. 시작하기/입력자료목록.csv": "file_id,file_name,document_type,version_or_date,owner,sharing_level,masked,read_status,notes\n",
    "00. 시작하기/사전점검.md": """# 사전점검

- 실습 경로: {확인필요: Green / Yellow / Red}
- 작업 모드: {확인필요: DEMO / PARTIAL / REAL}
- Codex 실행: {확인필요}
- Python 실행: {확인필요}
- 웹 접근: {확인필요}
- 한글에서 HWPX 열기: {확인필요}
- 실제 양식에 플레이스홀더 존재: {확인필요}
- 누락 자료: {확인필요}
""",
    "00. 시작하기/실습범위카드.md": """# 실습범위 카드

- 제출본 기준점: {확인필요}
- 우선 보완할 평가 공백 1개: {확인필요}
- 확인 질문: {확인필요}
- 검증할 핵심 주장 C001: {확인필요}
- 사용할 공식 출처 또는 기존 고객 근거 1개: {확인필요}
- 다음 공식 마감: {확인필요}
- 콘텐츠 검토 범위: EDUCATION_SINGLE_CLAIM
- HWPX 선택 트랙 사용 여부: {확인필요: 사용 안 함 / ANNOTATED_TEMPLATE / MANUAL_MAPPING}
""",
    "00. 시작하기/증거원장.csv": "claim_id,criterion_id,form_field_id,section,claim,claim_type,source_name,source_path_or_url,page_or_location,published_date,accessed_date,unit_and_base_date,verification_status,approved_wording,notes\n",
    "00. 시작하기/요구사항추적표.csv": "criterion_id,form_field_id,official_prompt,source_page,required_or_optional,length_limit,claim_ids,draft_file,placeholder,approval_status,hwpx_status\n",
    "01. 회사내용/회사사실표.md": """# 회사사실표

근거가 없으면 내용을 만들지 말고 {확인필요}로 남깁니다. 회사 내부 입력은 F001 형식의 fact_id를 사용하고, 외부·고객 근거로 검증할 핵심 주장은 증거원장에서 C001로 관리합니다.

| fact_id | 구분 | 내용 | 근거 파일·위치 | 상태 |
|---|---|---|---|---|
| F001 | 대표자 문제 발견 경험 |  |  | 확인필요 |
| F002 | 아이템 한 문장 |  |  | 확인필요 |
| F003 | 목표고객 |  |  | 확인필요 |
| F004 | 현재 보유 기술·자원 |  |  | 확인필요 |
| F005 | 확인된 실적 |  |  | 확인필요 |
| F006 | 향후 계획 |  |  | 계획 |
""",
    "01. 회사내용/누락정보.md": "# 누락정보\n\n- [ ] {확인필요}\n",
    "02. 공고문 및 평가지표/평가기준표.md": """# 평가기준표

프로그램프로필에 기록한 실제 공고·평가표가 모든 일반 참조보다 우선합니다. 공식 배점이 없으면 임의 점수를 공식처럼 표시하지 않습니다.

| criterion_id | 평가영역 | 공식 문구 | 원문 위치 | 필요한 근거 | 상태 |
|---|---|---|---|---|---|
| R001 | {확인필요} |  |  |  | 확인필요 |
""",
    "02. 공고문 및 평가지표/공백진단표.md": """# 공백진단표

- 제출본 기준 파일: {확인필요}
- 선택한 공개 평가영역: {확인필요}
- 가장 중요한 공백 1개: {확인필요}
- 확인 질문: {확인필요}
- 필요한 근거: {확인필요}
- 공백을 우선한 이유: {확인필요}
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
    "04. 시장조사 리서치/조사질문.md": """# 조사질문

1. 목표고객은 어떤 상황에서 이 문제를 경험하는가?
2. 현재 어떤 대안을 사용하고 무엇이 부족한가?
3. 시장성 주장을 뒷받침할 1차 자료는 무엇인가?
4. 구현·사업화 가능성을 검증할 가장 작은 실험은 무엇인가?
""",
    "04. 시장조사 리서치/시장조사.md": "# 시장조사\n\n출처·발표일·기준연도·단위를 함께 기록합니다.\n",
    "04. 시장조사 리서치/경쟁사비교.csv": "대상,고객,핵심기능,가격,강점,한계,출처,조회일\n",
    "04. 시장조사 리서치/검증활동기록.md": """# 검증·활동 기록

- 증거 ID: C001
- 확인할 주장: {확인필요}
- 공식 출처 또는 기존 고객 근거: {확인필요}
- 발행기관·기록 주체: {확인필요}
- 발행일·인터뷰일·기준일: {확인필요}
- 확인한 내용: {확인필요}
- 해석의 한계: {확인필요}
- 다음 검증 행동: {확인필요}
""",
    "05. 작성초안/핵심초안.md": """# 핵심초안

## 문제와 고객

{확인필요}

## 해결책과 차별성

{확인필요}

## 기대효과와 시장성

{확인필요}

## MVP와 30일 검증계획

{확인필요}
""",
    "05. 작성초안/content-lock.md": """# 대표자 문안 승인

- 승인 상태: NOT_APPROVED
- 승인 대상 초안: {확인필요}
- 승인 일시: {확인필요}
- 공개 가능한 내용 확인: {확인필요}
- 근거 ID 일치 확인: {확인필요}
- 확인필요 항목 처리: {확인필요}
""",
    "06. 검토결과/콘텐츠검토.md": """# 콘텐츠 검토

- 검토 상태: NOT_RUN
- 검토 범위: EDUCATION_SINGLE_CLAIM
- 검토 대상 버전: {확인필요}
- 범위 내 필수항목 분모: {확인필요}
- 범위 내 사실 주장 분모: {확인필요}
- 범위 밖 항목: NOT_REVIEWED
- PASS: -
- WARN: -
- BLOCK: -
- 범위 내 필수항목 커버리지: {확인필요}
- 범위 내 사실 주장 근거 커버리지: {확인필요}
""",
    "06. 검토결과/산출물검토.md": """# HWPX 산출물 검토

- 검토 상태: NOT_RUN
- 검토 대상 파일: {확인필요}
- 완료 수준: {확인필요: FALLBACK / DRY_RUN / FULL}
- 구조검증: {확인필요}
- 미치환 항목: {확인필요}
- 한글 육안검수: {확인필요}
""",
    "06. 검토결과/멘토링변화기록.md": """# 멘토링 변화기록

- 제출 당시 생각: {확인필요}
- 새 근거·멘토 의견: {확인필요}
- 결정: {확인필요: 유지 / 수정 / 보류}
- 결정 이유: {확인필요}
- 아직 확인할 질문: {확인필요}
- 다음 검증: {확인필요}
""",
    "07. 최종본/최종확인.md": """# 최종 확인

- [ ] 원래 제출본과 고도화본을 구분해 보관
- [ ] 콘텐츠 검토 실행 및 BLOCK 처리
- [ ] 대표자 승인 문안만 사용
- [ ] 미치환 중괄호 0건
- [ ] HWPX 구조검증 통과
- [ ] 한글에서 열기·표·줄바꿈 육안 확인
- [ ] 활동·변경 기록과 다음 공식 마감까지의 실행계획 확인
""",
    "07. 최종본/다음공식마감실행카드.md": """# 다음 공식 마감 실행카드

- 다음 공식 마감: {확인필요}
- 할 일 1개: {확인필요}
- 담당자: {확인필요}
- 기한: {확인필요}
- 완료 증거: {확인필요}
- 실패하면 바꿀 조건: {확인필요}

## 1분 IR 핵심 메시지

- 문제: {확인필요}
- 고객: {확인필요}
- 해결: {확인필요}
- 차별성: {확인필요}
- 다음 검증: {확인필요}
""",
    "07. 최종본/release-manifest.md": """# 결과물 상태

- 완료 수준: NOT_SET
- 허용값: FALLBACK / DRY_RUN / FULL
- 최종 파일: {확인필요}
- 승인한 초안 버전: {확인필요}
- 콘텐츠 검토 상태: NOT_RUN
- HWPX 산출물 검토 상태: NOT_RUN
- 한글 육안검수: NOT_RUN
""",
}


def render_template(template: str, track: str, mode: str) -> str:
    return (
        template.replace("{track_json}", json.dumps(track, ensure_ascii=False))
        .replace("{track}", track)
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
        "--track",
        default="unknown",
        help="공식 공고에서 확인한 트랙명. 모르면 unknown",
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
        help="호환성 옵션. 사용자 수정 파일은 덮어쓰지 않고 보호 상태로 보고",
    )
    args = parser.parse_args()

    project = Path(args.path).expanduser().resolve()
    if project == Path(project.anchor):
        parser.error("드라이브 루트에는 프로젝트를 만들 수 없습니다.")

    project.mkdir(parents=True, exist_ok=True)
    for folder in FOLDERS:
        (project / folder).mkdir(parents=True, exist_ok=True)

    written: list[str] = []
    skipped: list[str] = []
    protected: list[str] = []
    for relative, template in TEMPLATES.items():
        target = project / relative
        content = render_template(template, args.track, args.mode)
        result = safe_write(target, content, args.force)
        if result == "WRITE":
            written.append(relative)
        elif result == "PROTECTED_MODIFIED":
            protected.append(relative)
        else:
            skipped.append(relative)

    print(f"PROJECT: {project}")
    print(f"CREATED_OR_UPDATED: {len(written)}")
    for item in written:
        print(f"  + {item}")
    print(f"PRESERVED_EXISTING: {len(skipped)}")
    for item in skipped:
        print(f"  = {item}")
    print(f"PROTECTED_MODIFIED: {len(protected)}")
    for item in protected:
        print(f"  ! {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
