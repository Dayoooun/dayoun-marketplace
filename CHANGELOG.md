# 변경 기록

## Unreleased

### business-plan-writer 0.12.9 RC

- `deck_brief → content_report → design_spec → slide_blueprint` 네 기획 원문과 승인 상태를 강제하는 production plan 도입
- 장별 visualRole·layout·styleVariant·3D 자산 의존성을 compiler가 fail-closed 검증
- 승인 후 1차 Codex 3D·사진·재질 에셋 병렬생성, 2차 HTML 슬라이드 병렬렌더를 순서대로 실행
- plan 및 기획 원문 digest, 장별 renderer 결정, assembly 순서를 `design-execution-plan.json`에 결속
- draft·누락 기획서·중복 slide ID·레이아웃 충돌·없는 참조 자산은 제작 전 차단

### business-plan-writer 0.12.8 RC

- HTML 슬라이드를 2배 supersampling한 뒤 1920×1080으로 내보내 작은 글자와 선명도를 개선
- 프로세스 rail과 모든 dot 중심을 같은 좌표로 고정하고 receipt에서 최대 1px 오차를 검증
- 그래프 viewBox를 실제 와이드 캔버스 비율에 맞춰 노드·엣지가 가로로 늘어나 보이던 문제 수정
- 긴 한글 표의 어절 분리 방지, 그래프·overview 글자 크기 상향, 3D 자산 점유율 개선
- 데이터 막대의 장식적 그라데이션을 제거하고 단일 강조색으로 통일

### business-plan-writer 0.12.7 RC

- PPT 기본 디자인을 `toss-data-unified`로 통합하고 콘텐츠 역할에 따라 Toss 3D·아이콘 에디토리얼·데이터 에디토리얼로 자동 라우팅
- 표·KPI·차트·프로세스·모듈·로드맵·엔티티 그래프는 Playwright HTML로, 3D·사진 자산은 Codex로 생성하는 하이브리드 렌더 계약 도입
- 12개 실제 시나리오를 PNG·PPTX·PDF·콘택트시트로 조립하고 layout receipt, source·asset·output digest, 페이지 수를 fail-closed 검증
- 그래프 endpoint·direction·label·고립 노드·엣지 가시성 검증과 topology 기반 자동 배치 추가
- `NaN`·`Infinity` 입력 및 receipt 내부 비유한값을 재귀 차단하고 모든 JSON 출력에 strict serialization 적용
- 전역 정본·marketplace plugin·Claude/Codex course 복사본을 동일 파일 집합으로 생성·검증

### business-plan-writer 0.12.6 RC

- Codex 이미지 생성을 항상 병렬로 강제. 잡이 2개 이상이면 `--cap` 1·2 를 줘도 최소 4로 상향한다. 슬라이드 1장에 수 분이 걸려 순차 실행은 23장 덱에서 70분을 넘겨 수업·납품 일정에서 실패한다
- 강제된 동시성은 잡 수를 넘지 않고, 잡 1개일 때만 순차로 남는다

### business-plan-writer 0.12.5 RC

- 최종 HWPX 본문에 외부 공개자료 `(기관명, 연도)`만 남기고 `(사용자 제공자료, 연도)`·`(검증가설)`·`(실행계획)` 노출을 중단
- `(검증가설)`은 심사에서 사업자가 스스로 근거 없음을 선언한 것으로 읽히고 `(사용자 제공자료)`는 출처가 아니라 자기 진술이므로 심사 문서의 근거 표기로 쓰지 않음
- 주장 추적은 그대로 유지. `[E/U/H/P]` 표지·근거목록.csv 대조는 치환 전에 동일하게 BLOCK 판정하고 문장별 ID는 `근거목록.csv`가 보관
- PPT 스타일 프로파일을 `style_profiles.json` 단일 출처로 옮기고 기본값을 `modern-flat`(모던 플랫 / Toss·Naver flat)으로 고정. 산문 설명만 두면 실행 경로가 읽지 못해 매 실행 다른 룩이 나왔다
- 슬라이드 생성 프롬프트에 이미지생성 강제 문구를 항상 주입. codex 가 Python/PIL/matplotlib/SVG 로 그리면 CJK 글리프가 없어 한글이 "?" 로 깨진다
- 스타일 앵커(`refs`) 없는 잡을 차단. 앵커 없이 프롬프트만 주면 룩이 재현되지 않는다. 부트스트랩 1장만 `allowNoStyleAnchor` 로 예외 허용
- 코드드로잉 폴백 검출 임계값을 30KB → 60KB 로 상향. 실측 드로잉 산출물이 18~50KB 라 30KB 기준은 50KB 짜리를 통과시켰다
- 브랜드 강조색 미지정 시 임의 블루로 대체하지 않고 중립 잉크그레이를 쓰도록 명시
- 버전 상수를 테스트·재현 스크립트에서 하드코딩 대신 `plugin.json` 에서 읽도록 변경

### business-plan-writer 0.12.4 RC

- 외부 조사 전에 목표고객·문제·첫 제품·판매 방식·조사 우선순위를 사용자와 확정
- FULL·교육 실습에서 서로 독립적인 조사 worker 3개 이상과 worker별 결과·실패 기록·종합본을 필수화
- 조사 worker가 실패하거나 시간·사용량 한도에 닿으면 미확인 범위를 남기고 전체 완료 선언을 차단
- 승인 우회 `--allow-unapproved-values`를 제거하고 user-edited canonical 입력을 receipt digest에 결속
- 한컴 한글 PDF 내보내기 뒤 페이지 PNG와 `NEEDS_REVIEW` receipt를 만드는 render QA 도구 추가
- Scene Deck과 image-first의 이미지·텍스트 책임을 분리하고 PPT 재생성 횟수·수업 컷오프를 제한
- 출처 예시의 고정 연도 `2025`를 실제 근거목록 연도 자리표시자로 교체

### business-plan-writer 0.12.3 RC

- HWPX 답변을 길이와 관계없이 `o 대항목 → - 핵심항목 → · 세부내용` 개조식으로 통일
- 산문 승인값은 `o 핵심내용 → - 주장`으로 자동 정규화하고 `AUTO_OUTLINED` 대상만 사용자에게 안내
- `o` 1,200/-1,200, `-` 2,400/-1,200, `·` 3,600/-800 HWPUNIT의 실제 내어쓰기 유지
- E/U 출처를 `출처명, YYYY`로 검증하고 최종 HWPX에는 내부 ID 대신 `(출처명, 연도)`로 표시
- 근거가 여러 개면 `(출처명, 연도; 출처명, 연도)`로 묶고 `근거목록.csv` 역추적 유지

- authored `contracts/`에 canonical payload, approval envelope, validation, provider-run, visible-text/OCR schemas와 QUICK·SECTION·FULL 상태기계를 추가
- `create-business-documents`를 독립 `business-documents` 플러그인과 SemVer/tag namespace로 분리
- HWPX와 PPT를 독립 선택 산출물로 변경하고 PPT-only 경로에서 HWPX 선행 의존성을 제거
- `scene-deck`과 `image-first`를 동등 1.0 후보로 유지하고 image-first 승인 digest·region mapping·PPTX/PDF OCR fail-closed 검증 추가
- `course-src` 원본에서 `course` 배포판과 스타터 스킬 snapshot을 생성하도록 변경하고 수작업 mirror·`fallback/` 제거
- 실제 3 provider 30회, N≥10 강의, 10명 외부 베타, exact Windows 시각 baseline을 별도 BLOCK 가능한 릴리스 증거로 고정
- contracts·writer·documents·course-kit의 target-scoped deterministic ZIP과 독립 tag workflow 추가

## 0.9.0 · 2026-08-08

- 사업계획서 10단계와 분리된 선택 스킬 `create-business-documents` 추가
- 견적서, 프로필·이력서, 공문·안내문·게시물용 JSON 입력과 A4 HTML 출력 지원
- 부가세 계산·한글 금액, 프로필 항목 순서, 공문 번호·날짜·붙임·`끝.` 규칙을 코드로 검증
- Windows·macOS·Linux 공통 경로와 오프라인 한글 시스템 글꼴 지원
- 실제 고객정보를 복사하지 않는 가상 예제 allowlist와 개인정보 형태 회귀 검사 추가
- 태그 푸시에서 검증 후 설치 ZIP을 게시하는 GitHub Actions 릴리스 자동화 추가

## 0.8.0 · 2026-08-07

- PPT 생성 전에 목적·청중·전달상황·시간/장수·자료·식별 기준을 묻는 요구사항 인터뷰 추가
- 한 라운드 최대 3개 질문, 기준 판단 선제시, 사용자 확인 전 생성 금지 게이트 추가
- `Deck.from_brief()`와 `IntakeBlocked`로 미확인 요구사항의 조기 생성을 코드에서도 차단
- Windows·macOS 공통 폰트 탐색, Homebrew `codex` 탐색, 운영체제별 프로세스 트리 종료 구현
- 이미지형 PPTX의 PowerPoint 내부 텍스트 편집 불가 조건을 인터뷰와 문서에 명시
- 인터뷰·macOS·폰트·프로세스·문서 정합을 포함한 단위 및 스모크 회귀 테스트 추가

## 0.7.1 · 2026-08-02

- 공고문·평가지표·작성지침·사업계획서 양식 분석부터 발표자료까지 10단계 파이프라인 명시
- 단계별 진입 조건·완료 조건·다음 스킬 계약 추가
- 공고 분석 필수 항목(자격·지원·일정·제출·평가·작성 제한·수정공고·근거 위치) 표준화
- 조사 전 근거 질문, 승인 전 HWPX 금지, 구조·화면검사 전 제출 완료 금지 게이트 추가
- `complete-business-plan`에서 `ppt-editorial`까지 연결하고 PPT 대본·예상 Q&A를 완료 범위에 포함
- HWPX 페이지 직접 변환이 아니라 승인된 내용을 발표용으로 재구성한다는 경계 명시

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
