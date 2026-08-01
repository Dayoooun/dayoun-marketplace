#!/usr/bin/env python3
"""Create a safe, repeatable startup-plan project folder."""

from __future__ import annotations

import argparse
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
- 제출물 명칭: {확인필요}
- 제출 마감: {확인필요}
- 제출 후 수정 가능 여부: {확인필요}
- 현재 단계: 자료 준비

## 완료

- [ ] 회사자료 배치
- [ ] 공고·평가기준 배치
- [ ] 작업용 HWPX 배치
- [ ] 증거원장 작성
- [ ] 핵심초안 작성
- [ ] BLOCK 0건
- [ ] HWPX 구조 검증
- [ ] 한글에서 열기 확인

## 다음 행동

1. 실제 트랙과 제출물 명칭 확인
2. 공유 가능한 회사자료 배치
3. 공고문·평가표·HWPX 양식 배치
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
    "00. 시작하기/증거원장.csv": "claim_id,section,claim,claim_type,source_name,source_path_or_url,page_or_location,published_date,accessed_date,unit_and_base_date,verification_status,approved_wording,notes\n",
    "01. 회사내용/회사사실표.md": """# 회사사실표

근거가 없으면 내용을 만들지 말고 {확인필요}로 남깁니다.

| 구분 | 내용 | 근거 파일·위치 | 상태 |
|---|---|---|---|
| 대표자 문제 발견 경험 |  |  | 확인필요 |
| 아이템 한 문장 |  |  | 확인필요 |
| 목표고객 |  |  | 확인필요 |
| 현재 보유 기술·자원 |  |  | 확인필요 |
| 확인된 실적 |  |  | 확인필요 |
| 향후 계획 |  |  | 계획 |
""",
    "01. 회사내용/누락정보.md": "# 누락정보\n\n- [ ] {확인필요}\n",
    "02. 공고문 및 평가지표/평가기준표.md": """# 평가기준표

실제 공고·부산대 내부 평가표가 일반 참조보다 우선합니다. 공식 배점이 없으면 임의 점수를 공식처럼 표시하지 않습니다.

| 평가영역 | 공식 문구 | 원문 위치 | 필요한 근거 | 상태 |
|---|---|---|---|---|
| 도전의 진정성 |  |  | 문제 발견 경험·신청 배경 | 확인필요 |
| 사회적 가치 |  |  | 차별성·기대효과 | 확인필요 |
| 아이디어 구체성 |  |  | 시장성·실현 가능성 | 확인필요 |
""",
    "03. 사업계획서양식/placeholder-values.json": "{}\n",
    "04. 시장조사 리서치/조사질문.md": """# 조사질문

1. 목표고객은 어떤 상황에서 이 문제를 경험하는가?
2. 현재 어떤 대안을 사용하고 무엇이 부족한가?
3. 시장성 주장을 뒷받침할 1차 자료는 무엇인가?
4. 구현·사업화 가능성을 검증할 가장 작은 실험은 무엇인가?
""",
    "04. 시장조사 리서치/시장조사.md": "# 시장조사\n\n출처·발표일·기준연도·단위를 함께 기록합니다.\n",
    "04. 시장조사 리서치/경쟁사비교.csv": "대상,고객,핵심기능,가격,강점,한계,출처,조회일\n",
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
    "06. 검토결과/최종검토.md": "# 최종검토\n\n- PASS: 0\n- WARN: 0\n- BLOCK: 0\n",
    "07. 최종본/제출전확인.md": """# 제출 전 확인

- [ ] BLOCK 0건
- [ ] 미치환 중괄호 0건
- [ ] HWPX 구조검증 통과
- [ ] 한글에서 열기·표·줄바꿈 육안 확인
- [ ] 파일명·용량·페이지 제한 확인
""",
}


def safe_write(path: Path, content: str, force: bool) -> str:
    if path.exists() and not force:
        return "SKIP"
    path.write_text(content, encoding="utf-8", newline="\n")
    return "WRITE"


def main() -> int:
    parser = argparse.ArgumentParser(description="사업계획서 프로젝트 폴더 생성")
    parser.add_argument("--path", required=True, help="생성할 프로젝트 폴더")
    parser.add_argument(
        "--track",
        choices=("general-tech", "local", "unknown"),
        default="unknown",
        help="모두의 창업 트랙",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="도구가 관리하는 빈 템플릿만 덮어쓰기",
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
    for relative, template in TEMPLATES.items():
        target = project / relative
        result = safe_write(target, template.replace("{track}", args.track), args.force)
        (written if result == "WRITE" else skipped).append(relative)

    print(f"PROJECT: {project}")
    print(f"CREATED_OR_UPDATED: {len(written)}")
    for item in written:
        print(f"  + {item}")
    print(f"PRESERVED_EXISTING: {len(skipped)}")
    for item in skipped:
        print(f"  = {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
