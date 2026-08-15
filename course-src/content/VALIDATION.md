# 검증 계약과 현재 상태

- 대상 개발선: `business-plan-writer 0.10.x`, `business-documents 0.1.x`, `course-kit 0.1.x`
- 제품 원본: `plugins/business-plan-writer`, `plugins/business-documents`, `course-src`, `contracts`
- 공개 강의 `course/`는 `python scripts/generate_course.py --clean`으로 생성합니다.

## 자동 검증

```powershell
python -m pip install -r requirements.txt
python scripts/validate_contracts.py contracts
python scripts/generate_course.py --check
python scripts/check_generated.py --forbid-internal
python scripts/validate_release_fixtures.py --require-ppt-modes scene-deck,image-first --require-ocr-association R04-I,R07-I --require-original-oracle-negatives --strict
python -m unittest discover -s tests -v
python scripts/build_release_artifacts.py --all --health-only --output-dir dist/health
```

CI는 Ubuntu·Windows·macOS에서 같은 계약·생성물·단위 테스트를 실행합니다. `business-plan-writer` 공개 산출물에는 일곱 핵심 스킬과 immutable `_contracts` snapshot만 들어가며 `business-documents`, test harness, 저장소 상대경로 의존성은 들어가지 않습니다. 기본 강의에는 generated `.agents/skills`와 `.claude/skills`가 들어가지만 수작업 원본은 `course-src`에 두지 않습니다.

## 1.0에서 별도로 필요한 실제 증거

자동 테스트 통과는 1.0 PASS가 아닙니다. 다음은 실제 사람이 참가하거나 잠긴 외부 앱을 실행해야 하므로 결과를 만들지 않습니다.

- 10개 fixture × Codex·Claude Code·Antigravity 실제 CLI = 30개 고유 provenance run
- Windows 11 x64, Hancom Office 2024 Hangeul, PowerPoint 2024 x64, Edge Stable의 exact build 화면검수
- 고정 Pretendard·rasterizer·OCR executable/model/한국어 pack·normalizer·mapper digest
- 유효 시작자 N≥10 강의, 2인 블라인드 calibration, 110분 완주·향상·안전 지표
- ITT 외부 베타 10명, provider 4/3/3, QUICK/SECTION 5/5, C1–C6 중대 결함 0

현재 `release/toolchains.lock.json`은 의도적으로 `UNLOCKED`입니다. 외부 증거와 공개 가능한 집계본이 없으면 `scripts/release_dry_run.py --strict-evidence`가 BLOCK하고, 사람이나 다른 검사기가 이를 PASS로 덮을 수 없습니다.

## 안전 경계

- 사실·가정·계획·미검토는 canonical 계약에서 분리합니다.
- QUICK·SECTION·FULL 범위 밖은 `NOT_REVIEWED`, 선택하지 않은 HWPX·PPT는 `NOT_REQUESTED`입니다.
- HWPX와 PPT는 독립 선택 산출물이며 PPT-only 경로는 HWPX를 읽지 않습니다.
- image-first는 승인 전 visible-text manifest를 digest에 묶고 전달 PPTX·PDF pixels를 각각 OCR 검증합니다.
- 참가자 원자료·개인정보·raw provider/OCR 로그는 공개 저장소에 커밋하지 않습니다.
