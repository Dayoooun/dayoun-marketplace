# Release evidence

`1.0` 태그는 코드 테스트만으로 만들 수 없습니다. 대상별 `release_dry_run.py`가 아래 공개 가능한 집계 JSON을 읽어 모두 `status: PASS`인지 확인합니다.

- `business-plan-writer/provider-summary.json`: 실제 Codex·Claude Code·Antigravity 30회, distinct provenance, approved tuple digest
- `business-plan-writer/visual-summary.json`: 잠긴 Windows·한컴·PowerPoint·Edge·폰트·OCR 환경과 선택 산출물 PASS
- `business-plan-writer/course-summary.json`: 유효 시작자 N≥10, 80% 완주, 70% 향상, 안전사고 0, 5분 전환
- `business-plan-writer/beta-summary.json`: ITT 10명, provider 4/3/3, QUICK/SECTION 5/5, 8명 이상 완주, C1–C6 0
- `course-kit/course-summary.json`: 같은 강의 게이트의 집계본
- `business-documents/documents-summary.json`: renderer·브라우저 화면검수 집계본

참가자 식별정보, 개인정보, 비공개 사업자료와 실고객 raw 로그는 커밋하지 않습니다. `.gitignore`의 `raw/`, `participants/`, `*-identifiable.json` 규칙이 이를 차단합니다. 릴리스 source bundle은 공개 가상 fixture와 비식별 기록만 포함하고 입력·산출물·도구 digest와 판정을 보존합니다.

각 `*-summary.json`은 같은 디렉터리의 raw source JSON을 `sourceEvidenceRef`로 가리키고 그 실제 file SHA-256을 `sourceEvidenceDigest`에 기록해야 합니다. release gate는 course·beta·documents raw record를 다시 집계하고 provider의 30 complete run envelope/provenance/raw-output digest 및 visual 10-case ledger를 재검증합니다. 요약 숫자만 손으로 작성하면 PASS하지 않습니다.

`visual-source.json`의 각 case는 matrix의 `rendererMode`·`expectedVisual`을 그대로 기록하고, mode automation과 fact/structure/contract 세 validator의 PASS를 포함합니다. `evidence[]`의 각 `{kind, ref, digest}`는 같은 evidence 디렉터리의 실제 파일을 가리켜야 합니다. scene-deck은 scene/deck receipt와 각 output ZIP bundle, image-first는 canonical visible-text manifest·render receipt·rendered PNG ZIP bundle·PPTX/PDF OCR을 포함하며, release gate는 approval·renderer version·ordered slide identity·실제 bundle member digest·PPTX/PDF 페이지와 OCR mapping까지 다시 결속합니다.

`release/toolchains.lock.json`의 모든 구성요소는 실제 RC 환경에서 full build와 digest를 채우고 `verified: true`, 최상위 `status: LOCKED`로 바꿔야 합니다. 현재 `UNLOCKED` 상태는 의도적으로 writer 1.0을 BLOCK합니다. 사람이 이 BLOCK을 면제할 수 없습니다.
