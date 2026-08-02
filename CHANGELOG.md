# 변경 기록

## 0.7.0 · 2026-08-02

### 추가

- `ppt-editorial` 스킬 — 발표용 16:9 슬라이드 덱 제작
  - 도메인 프리셋 9종(it/food/manufacturing/education/welfare/culture/public/medical/retail)
  - 구도 10종(본문 L/S/W/C/A/F/T + 실무 COVER/AGENDA/CLOSING)
  - `Deck` API: cover → slide/photos → generate → build(PDF·PPTX)
  - 자체 게이트 3종(deck_qc / harness_smoke / doc_consistency, 모두 self-test 포함)
  - 씬만 이미지 생성 모델이 그리고 텍스트·배치·타이포는 코드가 렌더 — 글자 깨짐 없음
  - `ppt-image-first` 하네스 통합 — 앞단 자료 정리(deck_brief/content_report/
    style_card/slide_blueprint)를 두 모드 공통 단계로 흡수하고, 생성은
    모드 A(씬 덱) / 모드 B(이미지 퍼스트) 중 선택하도록 일원화

## 0.6.0 · 2026-08-02

- 공식 양식을 우선하는 범용 문체·문단·번호·들여쓰기·표 서식 기준 추가
- 초안 작성과 최종 검토가 하나의 서식 기준을 사용하도록 연결
- HWPX 입력 후 목록 단계, 들여쓰기, 표 크기와 자동 줄 바꿈 확인 강화
- 문체와 서식 회귀 테스트 추가

## 0.5.0 · 2026-08-02

- 공개 플러그인을 `business-plan-writer`로 변경하고 특정 지원사업 이름을 기본 기능에서 제거
- 신규 작성, 기존 문서 보완, 공고 맞춤, 투자·IR, 사내 검토, 대출·제안, 자율 계획 지원
- 핵심 스킬 이름을 `complete-business-plan`, `draft-business-plan`, `review-business-plan` 등 범용 이름으로 통일
- 초보자 기본 안내에서 내부 관리번호를 숨기고 `알고 있는 정보`와 `확인이 필요한 내용`으로 표현
- 범용 폴더를 사업정보, 목적 및 요구사항, 조사자료 중심으로 재구성
- 특정 프로그램 기준은 최신 공식 원문이 있을 때만 읽는 선택 참고자료로 분리
- Codex·Claude Code·Antigravity용 스킬과 설치 자료를 0.5.0으로 동기화

## 0.4.0 · 2026-08-02

- Codex·Claude Code·Antigravity용 네이티브 매니페스트와 설치 경로 추가
- 여섯 스킬 본문에서 특정 제품의 호출 기호를 제거하고 자연어 호출로 통일
- Windows와 macOS/Linux에서 Python 보조 스크립트를 실행하는 방법 분리
- 스타터 프로젝트에 `.agents/skills`와 `.claude/skills`를 동일 원본으로 제공
- 일반 채팅형 AI의 프롬프트 경로와 파일 실행형 에이전트 경계를 명시
- 프로바이더와 관계없이 네 가지 기본 결과물 계약을 유지하는 자동 테스트 추가

## 0.3.0 · 2026-08-02

- 초보자는 프로젝트 생성 전에 고객·사용상황 질문 하나부터 시작
- 회사 내부 입력 F001과 검증 주장 C001을 분리하고 네 결과물의 C001 연결을 고정
- 범용 프로그램프로필과 부산대학교 모두의 창업 선택 기준팩 분리
- EDUCATION_SINGLE_CLAIM·SELECTED_SECTION·FULL_DOCUMENT 검토 범위와 분모 명시
- `--force`에서도 사용자 수정 파일을 덮어쓰지 않도록 보호
- 스크립트 경로를 각 SKILL.md 폴더 기준으로 해석하도록 수정
- 정식 플러그인·스타터 스킬·빈 프로젝트 자동 동기화와 CI 검사 추가
- 독립 실행·HWPX·완성 예시를 포함한 자동 테스트 추가

## 0.2.0 · 2026-08-01

- 제출 이후 수업 목적을 공백진단·근거검증·멘토링 변화·다음 공식 마감 준비로 수정
- GPT 공통 경로와 Codex 확장 경로의 필수 결과물을 동일하게 통일
- Green·Yellow·Red 대체 경로와 10분 보호 버퍼 추가
- DEMO·PARTIAL·REAL 작업 모드와 입력자료 사전점검 추가
- 콘텐츠 검토 → 사용자 승인 → 선택 HWPX → 산출물 검토 순서 적용
- 플레이스홀더 0개, 미승인 값, 빈 값의 자동치환 차단
- 로컬 스킬 포함 스타터 프로젝트, 완성 예시, 오프라인 근거팩 추가

## 0.1.0

- 최초 공개 버전
