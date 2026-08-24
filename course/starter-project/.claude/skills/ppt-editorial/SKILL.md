---
name: ppt-editorial
description: "PPT·PPTX·파워포인트·슬라이드·발표자료·발표덱·피치덱·IR덱·제안서·강의자료를 새로 만들거나 수정·리디자인·PDF 변환·대본·예상 Q&A까지 요청하면 스킬명을 말하지 않아도 즉시 사용하는 통합 하네스. scene-deck과 image-first를 지원하고, 모든 제목·본문·캡션·대본·Q&A는 사실·수치·고유명사·URL·명령을 보호한 한국어 윤문을 반드시 거친 뒤 PPTX/PDF로 렌더한다. Windows와 macOS 지원."
---


## 호출 조건 — PPT 이야기면 즉시 사용

사용자가 스킬명을 몰라도 다음 표현 중 하나를 말하면 이 스킬을 바로 적용한다.

- `PPT`, `pptx`, `파워포인트`, `슬라이드`, `발표자료`, `발표 덱`
- `피치덱`, `IR 덱`, `제안서`, `강의자료`, `교육자료`
- 기존 PPT의 `수정`, `리디자인`, `다듬기`, `PDF 변환`, `대본`, `예상 Q&A`

단순히 PPT 파일 내용을 조회하는 정보 질문만 read-only로 답한다. 생성·수정·변환 의도가
있으면 `ppt-editorial`이라는 이름을 다시 말하게 하지 않고 이 하네스를 시작한다.

## 필수 한국어 윤문 gate

`references/korean-prose-humanization.md`를 모든 모드에서 반드시 적용한다. 윤문은 선택
옵션이 아니다.

1. `content_report`의 사실·수치·고유명사·기관명·날짜·단위·URL·명령·복사용 프롬프트를
   보호 목록으로 먼저 잠근다.
2. 제목·본문·캡션·전환문·발표 대본·예상 Q&A의 한국어 산문을 Document prose mode로
   윤문한다. `kill-ai-slop`이 설치돼 있으면 그 스킬을 사용해 `humanize-korean`에
   위임하고, 없으면 이 플러그인에 포함된 로컬 reference 규칙을 그대로 적용한다.
3. 복사용 명령·코드·URL·정확한 제품명은 윤문하지 않는다.
4. 윤문 전후 보호 목록이 글자 단위로 같지 않으면 BLOCK하고 문구를 되돌린다.
5. 윤문 완료 전에는 `slide_blueprint`, 씬 프롬프트, PPTX/PDF 조립으로 넘어가지 않는다.
6. 대본·예상 Q&A를 만든 뒤에도 같은 gate를 한 번 더 적용한다.

완료 보고에는 `윤문: PASS`, 적용 범위, 보호한 사실과 실행한 방식
(`kill-ai-slop` 또는 bundled local rules)을 남긴다.
# 슬라이드 덱 하네스 — 씬 덱 방식

## 파이프라인 위치: 10단계 발표 PPT·대본·예상 Q&A

사업계획서 흐름에서는 `review-business-plan`에서 승인된 canonical payload와
approval envelope를 입력으로 받는다. HWPX는 독립 선택 산출물이므로 PPT-only 실행에
HWPX 파일·경로·검사기록을 요구하거나 조회하면 안 된다. 발표 청중·발표시간·평가항목을
함께 확인하고 `deck_brief → content_report → slide_blueprint`로 압축·재구성한다.
PPT의 수치·고유명사·주장·근거는 승인 bundle과 다시 대조한다.

**완료 조건**: PDF/PPTX 렌더 육안검사, 수치 원문 대조, 발표시간에 맞춘 대본,
평가지표 기반 예상 질문과 근거가 있는 답변이 모두 있어야 한다.


> ## 먼저 렌더 경로를 고른다
>
> | | **A. HTML 구조 렌더** | **B. Codex 이미지 생성** | **C. 하이브리드** (전역 기본값) |
> |---|---|---|---|
> | 그리는 것 | 표·차트·KPI·응답자 개요·아이콘·프로세스·모듈·로드맵·휴식 안내 | 3D 씬·사진·질감 일러스트 | 슬라이드 역할별로 A/B 자동 선택 |
> | 텍스트 | Chromium이 렌더. 한글·정렬·폰트 고정 | 이미지 안에 생성 | 구조 페이지는 HTML, 3D 페이지만 Codex |
> | 문구 수정 | HTML 스펙만 다시 렌더. 수초 | 해당 장 재생성 | 바뀐 경로만 재실행 |
> | 산출 | PNG + 이미지형 PPTX/PDF | PNG + 이미지형 PPTX/PDF | 같은 크기의 PNG 세트로 통합 |
> | 적합 | 보고서·표·설문·수치·아이콘 도식 | 표지·제품·개념·공간·감성 비주얼 | 제안서·결과보고·IR·강의 |
> | PowerPoint 내부 텍스트 편집 | 불가. JSON 스펙에서 수정 | 불가. 해당 장 재생성 | 불가. 경로별 원본에서 수정 |
>
> **판단 기준:** 브라우저가 정확히 그릴 수 있는 것은 HTML로 만든다. 표·차트·KPI·
> 아이콘·프로세스·모듈·로드맵을 Codex에 통째로 그리게 하지 않는다. 3D 오브젝트,
> 사진, 재질과 조명이 필요한 장면만 Codex 이미지 생성을 쓴다.
>
> `codex_parallel_gen.py`는 `layout`이 `cover|table|kpi|bars|process|modules|overview|roadmap|break|network|image`이면
> Playwright HTML 렌더러로 보내고, 그 외 3D·생성 이미지 잡은 Codex로 보낸다.
> 한 덱 안에서 두 경로를 섞되 HTML 산출은 2배 supersampling 뒤 1920×1080 PNG로 내보내고, Codex 산출도 조립 전에 같은 Full HD 캔버스로 정규화한다.

### 실전 시나리오 하네스

- `references/render_contract.json`은 `context.visualRole`에서 layout/renderer를 도출하고 수직·수평 균형·문체·그래프·품질 게이트를 묶는 단일 계약이다. catalog의 `spec.layout`이 맥락 결정과 다르면 렌더하지 않는다.
- `references/scenario_fewshots.json`은 맥락 → 렌더 결정 → 구조 → 불변조건을 보여주는 layout별 few-shot이다. 좌표나 특정 슬라이드 문구를 복제하지 않는다.
- `references/scenario_catalog.json`은 표·KPI·막대·도넛·프로세스·모듈·로드맵·긴 한글·엔티티 그래프·3D·사진 시나리오를 semantic data로 제공한다.
- `network` 노드는 `id|label|entityType`, 엣지는 `source|target|direction|label`이 필수다. 위치는 위상으로 계산하고 수동 `x/y`, 누락 endpoint, self-edge, 무라벨 edge, 고립 노드를 차단한다.
- 그래프 엣지는 노드 중심이 아니라 boundary port에서 끝난다. 우회 경로·marker·label·endpoint·노드 충돌을 `.layout.json`의 edge별 visibility receipt로 검증한다.
- `image`는 Codex가 만든 `3d-scene|photo|material-illustration` 자산을 HTML의 정확한 문구·정렬과 결합한다. 사진은 focal 위치와 crop scale을 명시한다.
- 모든 HTML 렌더는 body bbox, overflow, 내부 gap, 모듈 내부 여백, 그래프 관계, renderer/spec/asset digest를 receipt에 기록한다.

```bash
python scripts/scenario_harness.py --out-dir artifacts/scenario-harness
```

12개 시나리오 PNG, 콘택트시트, PPTX, PDF, `scenario-report.json`을 실제 생성한다. 보고서는 canonical input의 `sourceHash`, 모든 PNG/receipt와 조립 산출물 digest, PPTX/PDF page count를 결속한다. 하나라도 실패하면 exit 1이다.

### 씬 자산 모드 — `cutout`과 `canvas`

씬이 있다고 전부 같은 방식으로 배치하지 않는다.

- 원료·제품·기기·인물·3D 오브젝트는 `sceneMode: "cutout"`으로 지정한다.
- 환경·공간·전면 사진처럼 배경 자체가 디자인 자산이면 `sceneMode: "canvas"`로 지정한다.
- `cutout`은 실제 `contentBBox`로 전경을 크롭하고 alpha mask로 붙인다.
- `.safe.json`은 18% 생성 안전영역 증거일 뿐 전체 캔버스를 유지하라는 지시가 아니다.
  sidecar가 있어도 전경 크롭을 생략하지 않는다.
- 투명 배경을 요청한 결과는 실제 RGBA, alpha 0~255, 테두리 95% 이상 투명을
  확인한다. RGB, alpha 전부 255, 픽셀로 그린 체크무늬는 BLOCK한다.
- 불투명 흰색·아이보리 배경은 가장자리 연결영역만 제거한다. 접촉 그림자,
  반투명 젤·유리, 밝은 용기 내부는 전경으로 보존한다.

스펙 예시:

```json
{
  "sceneMode": "cutout",
  "sceneTransparent": false,
  "sceneTarget": {
    "slot": "right",
    "minOccupancy": 0.68,
    "maxOccupancy": 0.88,
    "allowAspectAdjusted": true
  }
}
```

기본 점유율은 COVER 70~88%, L/S 68~88%, W 72~92%, A 72~90%,
CLOSING 65~85%다. 면적과 폭·높이 점유율을 모두 receipt에 기록한다. 극단적인
가로·세로 전경은 승인 스펙의 `allowAspectAdjusted: true`가 있고 한 축 90% 이상·
다른 축 30% 이상일 때만 예외로 허용한다. 숨은 자동 예외는 없으며 이 조건도 못
채우면 작게 두지 말고 BLOCK한다. `canvas`도 명시된 점유율 범위를 그대로 검사한다.

조립 뒤 `scene-placement-receipt.json`에 source digest, mode, content bbox, slot,
placed bbox, 면적·폭·높이 점유율, 충돌 결과를 기록한다. 제목·본문·상단 chrome,
쪽번호·하단 헤어라인·발신주체와 겹치거나 슬롯을 벗어나면 납품하지 않는다.
콘택트시트만 보지 않고 COVER·L·S·W·A·CLOSING을 원본 16:9 크기로 각각 확인한다.

하이브리드 모드에서는 구조화 가능한 페이지를 `html_slide_renderer.py`가 Chromium으로 렌더하고, 3D 씬·사진·질감 일러스트만 Codex가 생성한다. Codex가 만든 3D 자산과 HTML 페이지는 같은 PNG 세트에서 함께 조립할 수 있다. 전체 슬라이드를 Codex에 맡기는 경로는 사용자가 비주얼 전체 생성을 명시했거나 HTML로 표현할 수 없는 페이지에만 쓴다.

## ★★★ 0. 실행 전제조건 (없으면 먼저 설치한다)

**에이전트 지시**: 이 스킬을 처음 쓰기 전에 아래를 점검하고, 빠진 것이 있으면
사용자에게 되묻지 말고 **바로 설치한 뒤** 작업을 이어간다. 설치가 실패할 때만 보고한다.

### 한 줄 점검

```bash
python -c "import PIL,cv2,fitz,numpy,pptx,playwright,shutil,sys;print('codex:',shutil.which('codex'),'| py:',sys.version.split()[0])"
```

`codex: None`이거나 `ModuleNotFoundError`가 나면 해당 항목을 설치한다.

### 파이썬 패키지

```bash
pip install pillow opencv-python pymupdf numpy python-pptx playwright
python -m playwright install chromium
```

| import | 설치명 | 쓰는 곳 | 없으면 |
| --- | --- | --- | --- |
| `PIL` | `pillow` | 씬 합성·QC·폰트 측정 | 전 기능 정지 |
| `fitz` | `pymupdf` | PDF 생성·페이지 측정 | PDF 산출 불가 |
| `numpy` | `numpy` | 여백 검사·레이아웃 계산 | QC·레이아웃 정지 |
| `pptx` | `python-pptx` | 편집 가능 PPTX 출력 | PPTX만 불가 (PDF는 됨) |
| `cv2` | `opencv-python` | `photos.py` 사진 자동 크롭 | 사진 슬라이드만 불가 |
| `playwright` | `playwright` | HTML 표·차트·아이콘 렌더 | 구조 페이지 렌더 불가 |

파이썬은 **3.10 이상**을 쓴다.

### Windows와 macOS

하네스 코드는 두 운영체제를 같은 경로로 지원한다. Windows에서는 위 명령의
`python`·`pip`를 쓰고, macOS에서는 다음처럼 실행한다.

```bash
# Python 또는 Node가 없을 때만
brew install python node

python3 -m pip install pillow opencv-python pymupdf numpy python-pptx playwright
python3 -m playwright install chromium
npm i -g @openai/codex
codex login
python3 scripts/harness_smoke.py
```

이 플러그인은 Pretendard 1.3.9의 Regular·Medium·SemiBold·Bold와 SIL OFL 1.1
라이선스를 `assets/fonts/pretendard`에 포함한다. 렌더 전에 다음 명령으로 bundle과
사용자 범위 설치 상태를 검사하고, 없을 때만 설치한다.

```bash
python ../fill-hwpx-template/scripts/install_bundled_fonts.py verify-bundle
python ../fill-hwpx-template/scripts/install_bundled_fonts.py check
python ../fill-hwpx-template/scripts/install_bundled_fonts.py install
```

`platform_support.py`가 Windows의 사용자 폰트 폴더와 macOS의
`~/Library/Fonts`, `/Library/Fonts`, `/System/Library/Fonts`를 함께 탐색한다.
Pretendard가 없으면 Noto Sans KR 또는 Apple SD Gothic Neo로 폴백한다.
별도 폰트를 써야 하면 `PPT_EDITORIAL_FONT`에 파일 경로를 지정한다.

macOS에서 GUI 앱을 통해 실행해 Homebrew 경로가 `PATH`에서 빠져도
`/opt/homebrew/bin`과 `/usr/local/bin`의 `codex`를 다시 찾는다.
생성 종료도 Windows의 `taskkill` 또는 macOS의 POSIX 프로세스 그룹으로 자동 분기한다.

### codex CLI — 3D·생성 이미지 전용

```bash
npm i -g @openai/codex
codex login
codex --version
```

**Claude Code에서 실행하더라도 이 CLI는 따로 설치해야 한다.**
씬(배경 이미지) 생성은 codex를 통해 GPT-Image를 호출하기 때문이다.
`scripts/codex_parallel_gen.py`는 HTML로 처리할 수 없는 잡이 하나라도 있을 때만
`require_codex()`를 실행한다. HTML 전용 덱은 codex 없이 완성된다.

### codex 없이 되는 것

3D·사진·생성 일러스트를 뺀 나머지는 전부 동작한다. 표·차트·KPI·아이콘·
프로세스·모듈·로드맵은 Playwright Chromium이 렌더하므로 **구조 중심 덱은
codex 없이 완성된다.**

### 선택 사항

| 대상 | 용도 | 없을 때 |
| --- | --- | --- |
| 한글 폰트(Pretendard·G마켓산스 등) | 지정 서체 렌더 | `fonts.py`가 시스템 폰트로 자동 폴백 |
| Playwright Chromium | HTML 구조 슬라이드 렌더 | 구조 페이지 렌더 불가 |

## ★★★ 0-1. 요구사항 확인 게이트 (두 모드 공통)

바로 생성하지 않는다. 이미 사용자가 말한 내용은 다시 묻지 않고, 다음 핵심 정보에서
비어 있는 것만 **한 라운드 최대 3개**씩 확인한다.

1. PPT의 목적과 사용자가 얻어야 할 결과
2. 청중과 청중이 내려야 할 판단
3. 발표·제출·강의 등 전달 상황
4. 발표 시간 또는 장수
5. 사용할 원고·보고서·사진·표·기존 PPT
6. 반드시 유지할 회사명·제품명·로고·기관명

첫 질문에서 색상·무드까지 길게 묻지 않는다. 핵심 정보가 모이면 에이전트가 먼저
`목적 / 청중 / 권장 모드 / 권장 장수 / 서사축 / 식별 기준 / 부족한 정보`를 짧게
판단해 보여 준다. 사용자가 고치거나 승인하기 전에는 생성으로 넘어가지 않는다.

```bash
python scripts/intake.py deck_brief.md
# 누락이 없고 사용자가 위 판단을 승인한 뒤
python scripts/intake.py deck_brief.md --confirm
```

`Deck.from_brief()`는 이 확인 상태를 코드에서도 강제한다.

```python
from deck import Deck
d = Deck.from_brief("deck_brief.md", domain="it", out_dir="deck_out")
```

`requirements_confirmed`가 없거나 필수 정보가 비어 있으면 `IntakeBlocked`와 함께
다음 질문이 반환된다. 승인 뒤 요구사항을 수정하면 승인은 자동 무효화하고 다시 확인한다.
콘텐츠 근거를 정리한 다음에만 밝기·전문/스타일리시 노선·프리뷰 개수를 짧게 맞춘다.
상세 인터뷰 순서는 `references/image-first-workflow.md`의 Stage 1~1.5를 따른다.
사용자·브랜드·공식 양식의 스타일 요구가 없으면 `references/style-system.md`의 Pretendard와 밝고 절제된 중립 기본값을 사용한다. 장식 이미지보다 승인된 주장·구조를 설명하는 다이어그램, 비교, 타임라인, KPI, 프로세스를 우선한다.

**전역 모드 기본값:** 사용자가 편집 가능한 개별 도형·텍스트를 요구하지 않으면
`image-first`로 생성하고 `toss-data-unified`를 적용한다. 편집 가능성이 필수이면
`scene-deck`을 쓴다. 사용자가 모드를 직접 지정하면 그 선택이 최우선이다.

## ★★★ 1. 확인된 요구사항과 자료를 정리한다 (두 모드 공통)

바로 생성하지 마라. 무엇을 넣을지 정하지 않은 채 그리면 재생성만 반복한다.
`templates/`의 서식을 채워 근거를 고정한 뒤 생성으로 넘어간다.

| 산출물 | 서식 | 채우는 것 |
|---|---|---|
| `deck_brief.md` | `templates/deck_brief.md` | 목적·청중·전달상황·장수·출력형식·사용자 확인 상태 |
| `content_report.md` | `templates/content_report.md` | 주장별 근거 상태 — `user_provided` / `source_supported` / `inferred` / `needs_confirmation` |
| `style_card.md` | `templates/style_card.md` | 레퍼런스에서 뽑은 팔레트·서체·리듬·금지요소 |
| `slide_blueprint.md` | `templates/slide_blueprint.md` | 장별 역할·핵심 메시지·필수 문구·에셋 바인딩 |

**`content_report.md`가 핵심이다.** 출처 없는 수치를 슬라이드에 넣으면
발표장에서 무너진다. `inferred`와 `needs_confirmation`은 생성 전에 사용자에게 확인한다.

자료가 적으면 서식을 다 채우려 하지 말고 **가장 중요한 공백 하나**를 질문한다.

### 레퍼런스 역할 분리

사용자가 준 이미지를 한 덩어리로 다루지 마라. 역할이 다르면 처리도 다르다.

| 역할 | 예 | 처리 |
|---|---|---|
| 스타일 레퍼런스 | 원하는 룩의 완성 덱 | 팔레트·타이포·리듬만 추출 (`style_card.md`) |
| 제품/공간 레퍼런스 | 제품 사진·매장 내부 | 모양을 정확히 유지해야 함 → 씬에 함께 전달 |
| 증거 레퍼런스 | 스크린샷·인증서·표 | **재생성 금지** — 코드로 후합성 (`screenshot_frame.py`) |

로고·인증서·작은 글자가 많은 표는 모델에게 다시 그리게 하면 반드시 깨진다.


## ★★★ 2. 기획서 승인 후 2단 병렬제작
**한 에이전트가 내용·디자인·생성·판단을 다 하면 깨진다.** 특히 "판단"에서 오케스트레이터의 자기 눈이 반복 실패한다(실측 3회 어긋남). 역할을 분리하라.

| 단계 | 주체 | 산출물 |
|------|------|--------|
| 1. 내용 기획 | 오케스트레이터 | `deck_brief.md` → `content_report.md` → `design_spec.md` → `slide_blueprint.md` |
| 2. **디자인 디렉터** | `prompts/director.md` | 승인 전 `design-production-plan.json` (`approvalStatus: draft`) |
| 3. **계획 compiler** | `scripts/design_plan.py` | 역할·레이아웃·렌더러·에셋 의존성을 잠근 `design-execution-plan.json` |
| 4-A. **Codex 병렬제작** | `codex_parallel_gen.py` | 고품질 3D·사진·재질 에셋을 동시 생성 |
| 4-B. **HTML 병렬제작** | 같은 생성기 | 에셋 완료 후 표·차트·아이콘·정확한 한글을 동시 렌더 |
| 5. **디자인 크리틱·조립** | 독립 크리틱 + 오케스트레이터 | PASS/FIX 판정 → PNG/PPTX/PDF |

**루프**: 크리틱이 FIX한 슬라이드만 → 2단계 디렉터가 피드백을 반영해 plan을 수정 → 3단계 compiler 재실행 → 4단계 해당 잡만 재생성 → 5단계 재판정한다. 슬라이드별 최대 2회까지만 재생성하며, 시간·usage 컷오프에 닿거나 그 뒤에도 BLOCK이면 미검증 결과를 납품하지 않는다. 선택 PPT는 BLOCK으로 남기고 코드 전용 덱 또는 사전 생성본으로 설명한다.
- **오케스트레이터는 미적 판단을 하지 않는다.** "예쁘다/괜찮다" 자평 금지 → 크리틱 에이전트에 위임.
- 디렉터·크리틱은 반드시 **레퍼런스와 (있으면) 현재 결과물을 Read로 직접 보게** 하고, 취향을 판정 기준으로 넘긴다.
- 실증(고객사 Q): 크리틱이 "하단 앵커 부재/세로중앙 부유 띠"를 systemic 문제로 한 번에 잡음 — 오케스트레이터 혼자선 3라운드 놓친 것.

**실행 게이트:** 기획서가 네 planning source를 모두 가리키고
`approvalStatus: "approved"`일 때만 compiler가 실행된다. draft, 누락 파일, 중복 slide ID,
visualRole/layout 충돌, 참조 없는 생성 에셋은 `BLOCK`한다.

```bash
python scripts/design_plan.py design-production-plan.json --out-dir production
# 승인된 계획을 실제로 제작할 때만:
python scripts/design_plan.py design-production-plan.json --out-dir production --execute --cap 6 --effort high
```

`production/design-execution-plan.json`은 `planDigest`, 네 기획 원문 digest, 장별 renderer,
`styleVariant`, asset dependency와 최종 assembly 순서를 기록한다. 실행은 반드시
**1차 Codex 에셋 병렬 → 2차 HTML 슬라이드 병렬** 순서다. 3D 자산을 기다리지 않고
이미지 슬라이드를 먼저 렌더하는 race를 허용하지 않는다. 시작 파일은
`templates/design-production-plan.example.json`을 복사해 쓴다.

## ★★★ 3. 모드 B — 이미지 퍼스트 실행

슬라이드 한 장을 통째로 생성하지만 한글 깨짐·줄바꿈 오류를 허용하지 않는다.
생성 전에 canonical payload와 순서가 고정된 deck brief에서
`visible-text-manifest.json`을 만들고 payload·brief·manifest digest를 한 approval
envelope에 고정한다. 결과 PPTX와 PDF의 실제 픽셀을 고정된 rasterizer·OCR·region
mapper로 검사하며, 한 글자·수치·날짜·고유명사·근거 관계가 다르면 `AUTO_BLOCK`이다.

### 생성 패킷 — 한 번에 묶어 보낸다

레퍼런스를 나중에 덧입히지 마라. 첫 생성에 전부 넣어야 품질이 나온다.

```
ROLE / DECK PURPOSE / AUDIENCE
STYLE SYSTEM          style_card.md 에서
CONTENT LOCK          정확히 들어갈 텍스트 (한 글자도 바꾸지 말 것)
REFERENCE INPUTS      스타일·제품·증거 레퍼런스 경로
IMAGE FIDELITY RULES  어떤 요소를 정확히 유지할지
COMPOSITION TASK      구도 목표
FORBIDDEN             금지 요소
OUTPUT                크기·형식
```

### 규칙

- **쪽번호를 생성 프롬프트에 넣지 마라.** 조립 단계에서 코드로 찍는다.
- 로고·스크린샷·인증서·작은 글자 표는 생성 대상에서 빼고 후합성하되, 후합성 텍스트도
  승인 manifest에 포함한다.
- 모든 표시 문구는 stable `text_id`, slide, occurrence, mandatory normalized region을
  가진다. label/value·evidence/claim·date/event 관계는 relation edge와 geometry로 고정한다.
- `scripts/build_visible_text_manifest.py`로 oracle을 만들고
  `scripts/approved_inputs.py build`로 payload·ordered briefs·manifest와 envelope를
  content-addressed store에 넣는다. renderer와 validator에는 이때 출력된 approval
  digest와 store만 전달한다.
- 렌더 직후 `scripts/approved_inputs.py record-render`로 ordered slide identity·filename·PNG
  digest receipt를 store에 기록한다.
- `scripts/assemble_pptx.py ... --approval-digest <digest> --approval-store <store>
  --render-receipt-digest <receipt> --pdf`로 조립한다. 같은 장수의 PNG로 바꾸어도 BLOCK이며
  loose payload·brief·manifest·HWPX path는 받지 않는다.
- 전달된 PPTX/PDF를 각각 rasterize/OCR한 뒤
  `scripts/ocr/validate_visible_text.py --approval-digest <digest> --approval-store <store> ...`
  로 검사한다. `map_ocr_regions.py`는 validator 내부의 저수준 mapper다.
- confidence 0.99 미만, alternatives, ambiguous/no/multiple region, missing/extra text,
  clip/tofu, PPTX/PDF 불일치, toolchain 또는 승인 digest 불일치는 모두 BLOCK이다.
- fact·structure·contract 검증자 전원 PASS와 PPTX/PDF 외부 화면 PASS가 모두 필요하다.
  OCR·검증자·화면검수·사람은 서로의 BLOCK을 덮을 수 없다.
- 상세 워크플로는 `references/image-first-workflow.md`를 읽는다.


## 3-1. 스타일 프로파일 (모드 공통 · 검증된 디자인 DNA — 골라서 앵커로 먹임)
원하는 룩을 **레퍼런스 세트 + 스타일 블록 + 승인된 예시 슬라이드**로 고정한다. "이 DNA 항상 잘 나오게"의 메커니즘 = 아래 3종을 `-i`로 먹이는 것.

### ★★★ 0. 씬 덱 (Scene Deck) — **편집 가능한 도형·텍스트가 필수일 때 사용**

승인 기준본 = 납품처 기술해자 덱 · 납품처 결과보고.
**사용법·규격·함정은 `scripts/scene-deck/README.md`(19절)에 전부 있다. 반드시 먼저 읽어라.**

#### ★ 진입점은 `Deck` 클래스다 — build.py를 새로 쓰지 마라

```python
import sys, os
SKILL = os.path.dirname(os.path.abspath("SKILL.md"))   # 이 SKILL.md가 있는 폴더
sys.path.insert(0, os.path.join(SKILL, "scripts", "scene-deck"))
from deck import Deck

d = Deck(domain="제조", foot="OO정밀", title="스마트공장_제안")
d.cover("SMART FACTORY PROPOSAL", ["사람이 못 보는 불량을", "기계가 잡습니다"],
 ["설비 데이터 기반 실시간 품질 검사"], issuer="(주)OO정밀",
 meta=["제조혁신 컨설팅 · 2026"], scene="a precision inspection module ...")
d.agenda(["현황 진단", "불량 발생 구조", "검사 자동화 설계", "도입 로드맵"], scene="...")
d.slide("L", "THE PROBLEM", ["눈으로 검사하면", "반드시 놓칩니다"], ["..."],
 scene="...", labels=["육안 검사"])
d.slide("C", "RESULT", ["불량 유출이 줄어듭니다"], ["..."], scene="...",
 num=["0.3", "%", "목표 유출률"], chips=["24시간 검사", "로트 이력 추적"])
d.photos(["a.jpg", "b.jpg"], "ON SITE", ["현장에서 함께합니다"], ["..."])
d.closing(["함께 만드는 무결점 라인"], issuer="(주)OO정밀", scene="...")

# d.slides와 d.approval_config()를 deck_brief의 sceneDeckSlides/sceneDeckConfig로 기록하고
# approved_inputs.py build --renderer-version scene-deck-v3 으로 승인한다.

APPROVAL_DIGEST = "sha256:..."  # approved_inputs.py build 출력
APPROVAL_STORE = "approval-store"
d.generate(APPROVAL_DIGEST, APPROVAL_STORE) # 씬 생성 (있으면 생략 — 철칙 E)
d.build(APPROVAL_DIGEST, APPROVAL_STORE, pdf=True, pptx=True) # 조립 + PDF/PPTX
```

`domain` 한 줄로 팔레트·폰트·씬모티프·톤이 잡히고, 씬 비율·SAFE ZONE·PIL금지 지시·
재생성 방지가 자동이다. `build()` 시 `spec.json`이 저장돼 수정에 재사용된다.

#### 핵심 자산

| 파일 | 역할 |
|---|---|
| **`scripts/intake.py`** | 필수 정보 질문·기준 판단·사용자 확인 게이트 |
| **`scripts/platform_support.py`** | Windows/macOS 폰트·CLI·프로세스 공통 처리 |
| **`scripts/scene-deck/deck.py`** | 진입점. `from_brief → cover/agenda/slide/photos/closing → generate → build` |
| `scripts/scene-deck/presets.py` | 도메인 10종 — it/food/manufacturing/education/welfare/culture/public/medical/retail/beauty |
| `scripts/scene-deck/layout_engine.py` | 씬 구도 10종 + 강조요소 + 오버플로우 방어 |
| `scripts/scene-deck/info_layouts.py` | TABLE·EXAMPLE·MATRIX·BAR·FLOW·GENEALOGY·PROMPT 정보 레이아웃 7종 |
| `scripts/scene-deck/fonts.py` | 폰트 풀 11종 + 황금비 스케일 + 운영체제 폴백 |
| `scripts/scene-deck/revise.py` | 수정 인터페이스 (자연어 + API, 재생성 자동 판별) |
| `scripts/scene-deck/photos.py` | 실사진 4모드 (hero/compare/sequence/grid) |

#### 핵심 규칙

- **씬 일러스트 1장이 슬라이드를 지배한다.** 고급 3D 렌더(Apple keynote 급), 흰 배경.
 팔레트·모티프·톤은 `presets.py`가 도메인별로 준다.
- **씬 안에 한글 라벨을 박는다**(`labels=[...]`). 라벨 없는 씬은 정보량이 부족하다.
- **구도 10종** — 본문 `L`(좌텍/우씬) `S`(반전) `W`(프로세스) `C`(비교·교집합)
 `A`(비대칭대형) `F`(전면) `T`(3분할) / 실무 `COVER` `AGENDA` `CLOSING`.
 **연속 3장 이상 같은 구도 금지.**
- **정보 레이아웃 7종** — 순서·의존관계는 `FLOW`, 개념 확장 관계는 `GENEALOGY`, 복사용 요청문은 `PROMPT`를 쓴다. `GENEALOGY` 번호 timeline은 카드 밖 gutter에 둔다. 표·흐름·계보·프롬프트가 24px 이상 투사용 글자 크기에서 body/footer 경계에 맞지 않으면 축소하지 말고 BLOCK한 뒤 슬라이드를 나눈다. 투사용 표는 `font_sizes=[...]`로 후보 크기를 지정한다.
- **씬 안전여백** — 모든 화면·카드·버튼·연결선·라벨·그림자는 상하좌우 18%를 비우고 중앙 64% 안에 완전히 들어와야 한다. `codex_parallel_gen.py`가 생성본을 중앙 64%로 framing하고 실제 foreground bbox를 검사해 `.safe.json`과 scene receipt에 결속한다. receipt가 없거나 이미지 digest가 바뀌면 재생성·조립을 BLOCK한다.
- 크롬은 미니멀: 상단 파란 대시 + 영문 eyebrow / 우측 쪽번호, 하단 얇은 라인 + 회사명.
 **파란 풀블리드 밴드 금지**(촌스러움, 실측 반려). 표지는 크롬 없음.
- 헤드라인 **115px**(2560 캔버스). 씬 생성은 **`--effort high` 필수**.
- 필수 게이트: `python scripts/deck_qc.py <out폴더> --cover 01`
- 코드를 고쳤으면: `python scripts/harness_smoke.py`, `python -m unittest tests.ppt.test_harness -v`, `python -m unittest tests.ppt.test_information_layouts -v`
- 디스크: 씬 생성 시 `.cxwork` 격리 홈이 덱당 300~700MB 생긴다. 시작·종료 시 자동 정리(`--keep-work`로 보존). 상세는 scene-deck README §20

> ⚠️ **아이콘 ≠ 씬.** 아이콘(80px 타일)을 키워 큰 영역에 쓰면 "커진 아이콘"으로 보여 싸구려가 된다.
> 아이콘 나열로 슬라이드를 채우려는 시도는 2026-08-01 실측에서 전부 반려됐다.

> **표지 디자인:** 표지는 `visualRole: "cover"`와 `layout: "cover"`를 쓴다. 제목은 2줄 이내, 정확한 제목·부제·메타데이터는 HTML로 유지한다. 우측 62%에는 고품질 3D 또는 사진 자산 하나만 두고 자산은 프레임 폭의 65~80%를 차지하게 한다. 좌측 34%는 박스 없이 캔버스 위에 포지셔닝 문장과 대상·형식·버전 메타스트립만 정렬한다. 옅은 회색 큰 카드, 카드 상단 강조선, 중앙 부유 제목, 작은 아이콘 콜라주, 본문용 카드 그리드, 푸터 크롬, 의미 없는 장식은 금지한다.
> **휴식 안내:** 작은 타이머 카드 하나와 멀리 떨어진 하단 문장으로 여백을 메우지 않는다. 좌측 40%에는 박스 없이 시간·구간·휴식 목적을 타이포그래피와 헤어라인으로 묶고, 우측 56%에는 복귀 안내·재개 활동 2~3개를 배치한다. 본문은 29~84%를 사용하며 하단 25%가 비면 실패다. `visualRole: "break"`와 `layout: "break"`를 쓴다.
> **AI 카드 금지:** 평범한 문장을 큰 옅은 회색·옅은 브랜드색 직사각형 안에 넣고, 상단에 강조색 선을 붙이고, 남은 공간을 비운 채 메타데이터를 카드 하단으로 미는 구성을 금지한다. 카드가 허용되는 경우는 표·경고·선택된 모듈·이미지 크롭처럼 실제 의미 경계가 있을 때뿐이다. 기본 문법은 naked typography, 비대칭 열, 1px 헤어라인, 메타스트립과 단일 시각 앵커다.
> **헤드라인 문체:** 일정·휴식·목차·안내·상태 페이지는 결론형 문장을 만들지 말고 명사형 또는 `시간 + 행동` 형식으로 쓴다. 짧게 쓸 수 있는데 `합니다/입니다`를 붙이지 않는다. 사용자가 직접 준 문구가 아니라면 `~를 넘어/~을 넘어`, `~가 아니라`, `함께 만듭니다`, `다시 시작합니다`, `연결됩니다`, `새로운 가능성`을 금지한다. Light 전제 + Bold 결론 구문은 데이터 해석처럼 실제 결론이 있을 때만 쓴다. 예: `15분 휴식 · 10:25 팀별 활동 재개`, `이번 주 실행 항목`, `업무 자동화 운영 기준 설계`.
> ⚠️ **수정은 재생성이 아니다.** `Deck.load(spec).revise()` + `apply_command()`로 고친다.
> 텍스트·구도·순서·색·폰트는 조립만 하고(수초), 씬 내용을 바꿀 때만 그 장을 재생성한다.

### ★★★ 전역 기본값: Toss 3D + 데이터 리포트 통합

> **줄내림:** 한글 어절 내부 줄내림을 금지한다. `검수 요청`은 `검수`와 `요청` 사이에서만, `존재하지 않는 노드`는 공백에서만 줄을 바꾼다. 제목·설명·프로세스·모듈·로드맵은 `word-break: keep-all; overflow-wrap: normal`을 사용한다. 긴 코드 경로는 `/`, `.`, `_`, `(` 같은 기술 구분자에서만 나누며, 공간이 부족하면 어절을 쪼개지 말고 열 폭·글자 크기·슬라이드 수를 조정한다. receipt에서 한글 단어의 글자들이 서로 다른 line box에 놓이면 실패한다.

> **디자인 루틴 수:** 스타일 프로파일 4종, 기본 통합 프로파일 내부 변형 3종, HTML 역할 레이아웃 11종, 검증 시나리오 14종, few-shot 11종이다. 그러나 기본값이 `toss-data-unified` 하나라 명시적 기획 없이 실행하면 같은 흰 배경·같은 강조색으로 수렴한다.

> **팔레트:** 미지정 기본은 `editorial-blue`이며 초록은 자동 기본값이 아니다. 기획서에서 `palettePreset`을 `editorial-blue`, `navy-cyan`, `ink-coral`, `violet-slate`, `forest-sand`, `mono-red` 중 하나로 잠근다. `forest-sand`는 환경·지역·식품 맥락에서만 사용한다. 장별 `colorRole`은 `primary|secondary`이며, 같은 layout은 3장 연속 사용할 수 없다. 8장 이상 덱은 최소 2개, 12장 이상은 최소 3개, 16장 이상은 최소 4개 layout을 사용한다.
`styleProfile`을 생략하면 `toss-data-unified`를 쓴다. 한 덱 안에서 표지·개념·제품·
프로세스·여정·로드맵은 `toss-3d`, 기능·단계·역할·체크리스트는 `icon-editorial`,
설문·KPI·수치·통계·분포·차트·표·성과 페이지는 `data-editorial`로 자동 전환한다.
세 변형은 Pretendard 계열 고딕, 흰 배경, 같은 강조색, 작은 eyebrow, 넓은 여백,
얇은 구분선과 절제된 그림자를 공유한다.

- **자동 판정:** `scripts/style_profile.py::select_variant()`가 슬라이드 프롬프트의 역할어를 센다.
- **명시 우선:** 자동 판정이 맞지 않으면 잡에 `"styleVariant": "toss-3d"`, `"icon-editorial"` 또는 `"data-editorial"`을 적는다.
- **혼합 금지:** 한 슬라이드 안에 큰 3D 히어로와 촘촘한 차트 대시보드를 함께 넣지 않는다. 슬라이드 단위로 변형을 고른다.
- **검증된 앵커 7종:** Toss 3D의 개념·프로세스·제품 3장, 데이터 에디토리얼의 KPI·응답자 개요·막대 차트 3장, 승인된 표 1장을 형식별로 자동 주입한다. 아이콘 페이지는 데이터 에디토리얼 3장을 기준으로 삼고 아이콘은 작은 의미 라벨로만 쓴다. 표 페이지는 승인된 표 1장만 단독 주입해 헤더·지브라 행·열 비율을 고정한다.
- **기간 로드맵:** 일자형 수평 타임라인을 금지한다. 4개 기간은 좌하단에서 우상단으로 올라가는 계단형 phase slab으로 배치하고, 기간 숫자·짧은 제목·작은 아이콘만 남긴다.
### A. 페이퍼화이트 명조
- 페이퍼화이트 + **명조(serif)** + 미니멀 + 강조 1색 + 얇은 헤어라인 + (선택)수묵/잉크 모티프. 실물 사진 크게.
- 톤: 차분·고급·정제된 여백. 결과보고·컨설팅·전통/식음 브랜드에 적합.
- 실전: 고객사 Q 덱 · 고객사 P 오디션 덱.

### B. 모던 플랫 (Toss/Naver flat)
- **Pretendard류 고딕**(명조 아님) · 흰/옅은웜그레이 배경 · **3D 아이소메트릭·클레이 일러스트 + 플랫 아이콘**(브랜드색 톤) · **큰 볼드 숫자** · 둥근 소프트카드·알약(pill) · 얇은 그레이 구분선 · 좌상단 **탭 라벨** + 영문 eyebrow + 큰 볼드 고딕 헤드라인.
- 강조색은 브랜드색(파라미터). 레퍼런스가 블루여도 "브랜드색으로, 블루 금지" 강하게 지시.
- ★ **내용에 맞는 아이콘/일러스트**: 슬라이드 의미에 매칭(자사몰=가게, 광고=확성기, CRM=순환, 성과=오르는 막대+브랜드 모티프). 제네릭 금지.
- ★ **정제된 작은 스케일이 기본값**([[ppt-taste-minimal-airy]]): 헤드라인 modest·일러스트 작게 코너로·숫자/아이콘 작게·여백 넉넉. "크고 빽빽" 금지. 프롬프트에 "REFINED & SMALL, modest headline, small tucked illustration, generous airy whitespace, NOT big/heavy" 명시.
- ★★ **데코 오브제 관리 (은은 + 의미연결)**: 정제 스케일에서 생기는 dead zone은 **은은한(저대비·1~2개·과하지 않게) 데코**로만 균형 — 채움/클러터 금지. ★데코는 반드시 **슬라이드 주제와 의미 연결**(전략=성장 화살표/계단, 고객=사람/연결, 로드맵=경로, 성과=차트 힌트, 브랜드=브랜드 모티프, 주제 3D클레이를 빈 코너에). **무의미한 기하 필러 금지**. 옅은 배경도형·점선호·도트그리드는 주제를 echo할 때만.
- 톤: 밝고 모던·친근·테크. 스타트업 IR·SaaS·이커머스·데이터 성과에 적합. 실전: 납품 덱.

### C. 데이터 리포트 에디토리얼

- **핵심 인상:** 순백 배경, Pretendard 계열 고딕, 넓은 바깥 여백, 작은 섹션 eyebrow, 한 줄 안에서 Light 전제와 Bold 결론을 나누는 헤드라인.
- **정보가 장식이다:** 가로 막대·도넛·직접 라벨·1px 구분선·짧은 주석으로 설명한다. 3D 일러스트와 제네릭 아이콘은 넣지 않는다.
- **강조 규칙:** 결정적인 값 1~2개만 브랜드색과 같은 hue의 밝은 틴트로 만든 짧은 tonal gradient를 쓴다. 나머지는 차콜과 3단계 쿨그레이로 낮춘다. 적색은 실제 경고·격차·부정 결과 주석에만 허용한다.
- **대표 구도:** `65/35 막대+KPI 카드`, `KPI 3개+하단 해석문`, `메타데이터+도넛+분포 차트 2단`. 카드보다 차트와 결론형 문장이 먼저 보이게 한다.
- **막대 균형:** 막대 최댓값을 plot 폭 100%로 정규화하고 다른 값은 그에 비례시킨다. `31%`를 가용 폭의 31%로 바로 쓰지 않는다. 막대 영역 `68%`, KPI 영역 `28%`, 간격 `4%`를 기본으로 하고 두 열의 상·하단 시각 높이를 맞춘다. 경고 주석은 막대 영역 바로 아래에 붙이며 차트와 KPI 사이에 띄우지 않는다.
- **수직 점유율:** 표지·클로징을 제외한 구조 페이지는 본문을 높이 `28~34%`에서 시작하고 마지막 의미 요소를 `78~84%`에 둔다. 하단 `10~14%`만 푸터 밴드로 남긴다. 본문이 `68%` 이전에 끝나거나 하단 25%가 통째로 비면 실패다. 내용이 적으면 글자를 키우기보다 행 높이·차트 높이·해석 블록 간격으로 점유율을 회복한다.
- **표 규칙:** 사용자가 승인한 표 문법을 그대로 쓴다. 브랜드 블루 직사각 헤더와 흰 글자, 흰색/아주 옅은 쿨그레이 지브라 행, 각진 모서리, 넉넉한 행 높이, 1px 열 구분선이 기본이다. 3열은 `28/52/20`, 설명은 좌측 정렬, 짧은 산출물·상태 열은 가운데 정렬한다. 표 전체 카드·행별 라운드 카드·그림자는 금지한다.
- **표면 처리:** 카드 모서리는 작게, 그림자는 넓고 아주 흐리게, 테두리는 거의 보이지 않게 한다. 배경 전체 그라데이션·네온 글로우·두꺼운 테두리·과도한 라운드는 금지한다.
- 단독 실행 프로파일은 `data-report-editorial`이다. 전역 기본 통합 프로파일에서는 검증된 3페이지를 슬라이드 역할에 맞는 기준 세트로 자동 주입한다.

→ 프로파일 정의의 단일 출처는 `style_profiles.json`이다. 전역 기본값은 `toss-data-unified`이며 `scripts/style_profile.py`가 변형을 고르고, `codex_parallel_gen.py`가 해당 프롬프트와 기준 이미지를 주입한다.

```powershell
python "<스킬 루트>\scripts\style_profile.py" --list
python "<스킬 루트>\scripts\style_profile.py" --prompt "응답자 설문 KPI 58.4% 분포 차트" --accent "#0B5FFF"
python "<스킬 루트>\scripts\style_profile.py" --variant "toss-3d" --accent "#0B5FFF"
```

기본 통합 동작은 `styleProfile`을 생략해도 적용된다. 자동 판정을 덮어쓸 때만 `jobs.json`에 `"styleVariant": "toss-3d"`, `"icon-editorial"` 또는 `"data-editorial"`을 넣는다. 완전히 다른 룩이 필요할 때는 `"styleProfile": "paper-serif"` 같은 단독 프로파일을 지정한다.

### ★★★ 강조색·서체는 고정하지 않는다 (2026-07-06 지시)

**강조색과 서체를 하네스가 임의로 가정하지 말 것.** 브랜드 로고에서 색을 뽑을 수 있어도 **반드시 사용자에게 확인**한다("강조색 이걸로 할까요?"). 색을 못 받았으면 임의 블루로 튀지 말고 중립 잉크그레이를 쓴다.

이는 **룩 자체를 매번 흔들라는 뜻이 아니다.** 스타일 프로파일은 `style_profiles.json` 기본값으로 고정하고, 브랜드색만 파라미터로 받는다. 사용자가 다른 프로파일을 원하거나 레퍼런스를 주면 그때 바꾼다. 덱 시작 시 ①강조색 ②(선택)프로파일 변경 ③(선택)레퍼런스를 확인한다.


## ★★★ 4. 3대 철칙 (도메인 무관 · 어기면 깨짐)

### 철칙 A — Codex 잡 안에서 코드 드로잉 금지

Codex가 담당하는 3D·사진·생성 이미지 잡에서만 적용한다. 프롬프트에 이미지생성 강제가
없으면 Codex가 Python/PIL/matplotlib로 그려 한글이 깨질 수 있다.
`codex_parallel_gen.py`는 Codex 잡에만 `IMAGE_GEN_MANDATE`를 자동 주입하고,
60KB 미만 결과를 `code-drawing-fallback`으로 불합격 처리한다. HTML 잡은
`html_slide_renderer.py`가 Playwright Chromium으로 렌더하므로 이 금지 대상이 아니다.

### ★★★ 병렬 생성 강제 — 순차 실행 금지

슬라이드 1장 생성에 수 분이 걸린다. 순차로 돌리면 23장 덱이 70분을 넘겨 수업·납품 일정에서 그대로 실패한다. 격리 `CODEX_HOME`으로 상태를 분리하므로 고병렬이 안전하다.

- 잡이 2개 이상이면 `--cap`을 1이나 2로 줘도 **최소 4로 자동 상향**한다(`MIN_PARALLEL_CAP`).
- 강제된 cap은 잡 수를 넘지 않는다. 잡 3개면 3.
- 잡 1개일 때만 순차다.
- `--cap 0`(기본)은 `min(잡수, 코어//2, 10)`으로 자동 결정한다.

### 철칙 B — 레퍼런스 덱을 `-i` 스타일 앵커로 반드시 먹여라
품질 격차의 근본원인 = 레퍼런스 없이 "미니멀·여백" 규칙대로 앙상하게 만든 것. **다른 완성 덱(원하는 룩)을 `-i`로 먹이는 게 리치 룩 재현의 최대 동력.**
- **draft-anchor(금지) vs style-anchor(필수)**: 같은 슬라이드 내용의 레이아웃 초안을 먹이는 건 금지(템플릿 채운 느낌). 원하는 룩을 보여주는 **다른** 완성 덱을 먹이는 건 필수.
- 레퍼런스가 여러 장이면 슬라이드 타입별 최적 1장 배정(카드형↔카드 레퍼런스, Before/After↔B/A 레퍼런스).
- 레퍼런스가 없으면? 표지 등 1장을 여러 변형으로 뽑아 사용자가 고른 것을 이후 슬라이드의 앵커로 재사용(부트스트랩).

### 철칙 C — 콘텐츠는 모델, 고정 크롬은 PIL
로고·페이지번호·푸터를 매 슬라이드 모델이 그리게 하면 장마다 흔들리고 글자 깨진다(실측: 표지 푸터 "AI MARKeting").
→ 프롬프트에서 **네 모서리 비우게** 하고, 로고·페이지번호는 `scripts/chrome.py`로 전 슬라이드 동일 상대좌표 1회 합성. 단, **슬라이드가 자체 하단 레지스터(스탯바/요약)를 가지면 하단 푸터는 생략**(충돌). 표지만 로고/푸터, 콘텐츠는 크롬 최소화가 안전.

### ★★★ 철칙 C 완성형 — SAFE ZONE 방식 (2026-07-23 납품 덱에서 확립, 이게 최종 표준)

**판단 기준 한 줄: "장마다 같은 자리에 있어야 하는 것은 전부 코드가 그린다."**
모델에게 상단 제목바나 하단 요약밴드를 그리게 하면 반드시 흔들린다. 실측(납품 시안2 15장): 하단 네이비 밴드 상단이 **0.826~0.919로 9%p 편차**, 상단 라벨 y0가 **0~163px 편차**. 넘길 때 프레임이 떠는 게 눈에 보인다.

**절차**
1. **프롬프트에 SAFE ZONE을 최상위 우선순위로 주입** — 앞선 지시와 충돌하므로 "무시하라"까지 명시해야 먹는다:
```
★★ SAFE ZONES — THIS OVERRIDES ANY EARLIER INSTRUCTION IN THIS PROMPT:
1) TOP 15% must be COMPLETELY EMPTY — plain flat background. Do NOT draw the breadcrumb,
 numbered title, section label, vertical bar, rule or eyebrow. Composited by code afterwards.
2) BOTTOM 15% must be COMPLETELY EMPTY — plain flat background. Do NOT draw the summary band,
 summary sentence, footer, page number or rule. Composited by code afterwards.
3) Put ALL content strictly between 15% and 85% of slide height, and fill that middle area well.
4) Ignore every earlier sentence that told you to draw a breadcrumb, numbered title or bottom band.
```
2. **크롬 모듈이 상·하단을 균일 합성** — 덱별 `chrome_*.py`에 `SPEC = {sid: (번호, 제목, 하단요약)}`을 두고 고정 비율 좌표로 그린다(상단=브레드크럼+세로바+번호+제목 / 하단=밴드 y0.865 고정+요약 중앙정렬+쪽번호).
3. **제목까지 코드로 그리는 게 맞다.** 콘텐츠처럼 보이지만 위치·크기가 장마다 같아야 하므로 크롬이다. 한글은 맑은고딕 Bold(`malgunbd.ttf`)로 충분히 깨끗하게 렌더된다.
4. **검증은 픽셀 실측으로**: 밴드 상단 y·라벨 y0를 전 장 뽑아 편차 0인지 확인. 육안 판정 금지.

5. **★ SAFE ZONE 정규화는 필수다 — 모델은 여백 지시를 못 지킨다.** 실측(납품 시안2): SAFE ZONE을 명시해도 **14장 중 13장이 침범**(콘텐츠 top이 0.054~0.147로 산개). 재생성해도 반복되므로 **후처리로 확정**한다:
```python
def normalize(im, SAFE_TOP=0.163, SAFE_BOT=0.845):
 # ① 배경 최빈값으로 콘텐츠 bbox 감지 (행/열 합이 임계 초과하는 구간)
 # ② 안전 영역 높이에 맞춰 비율 유지 축소 (s = tgt_h / content_h, 최대 1.0)
 # ③ 배경색 캔버스에 중앙 정렬로 재배치
```
콘텐츠가 10~15% 작아지지만 **전 장 크롬 위치가 픽셀 단위로 일치**하는 값어치가 훨씬 크다. 파이프라인 순서: **생성 → normalize → 크롬 합성 → 사진 합성(fit_empty) → 2K/PPTX**. 크롬을 사진보다 먼저 얹어야 `fit_empty`가 크롬을 콘텐츠로 인식해 자동으로 피한다.

**부수 효과**: 모델이 상·하단을 안 그리니 중앙 콘텐츠에 집중해 본문 밀도가 올라간다. 그리고 문구 오타·수치 오류를 코드에서 즉시 고칠 수 있다(재생성 불필요).

---

**★ 상단 인덱스(탭 라벨)도 고정 크롬이다 (2026-07-21 에코에듀 실측으로 승격)**: 탭을 모델이 그리게 하면 10장 중 4종 변형(폴더탭/라운드박스/무테두리/위치 이탈)이 나오고, 크리틱 재생성 루프로도 완전 수렴 불가(확률적 재발).
→ ① 프롬프트에는 "DO NOT draw any tab/index label at the top; leave the top strip (top ~10%) empty except the eyebrow/headline" 지시(eyebrow·헤드라인은 콘텐츠라 모델 유지). ② 탭은 `scripts/index_chrome.py`로 전장 동일좌표 일괄 합성. ③ **인덱스 스타일은 컨셉(프로파일)별로 다르게**: 모던플랫=`folder-tab`(사선 폴더탭+풀폭 헤어라인) / 에디토리얼=`eyebrow-rule`(작은 라벨+얇은 룰) / 미니멀=`number-dash`("02 — 라벨"). 스타일·강조색은 덱 시작 시 사용자 확인(고정 금지 원칙과 동일). ④ 모델이 이미 탭을 그린 기존 덱은 `cover=True`(상단 스트립 배경색 덮기+재합성)로 보정 — 상단이 근단색 페이퍼톤일 때만 안전.

### 철칙 E — 납품 후 수정 요청은 **재생성이 아니라 image-to-image EDIT** (2026-07-27 사고로 확립)

> ⚠️ **이 철칙을 어기면 고객이 즉시 알아챈다.** 실측: 수정 요청 20여 건을 전면 재생성으로
> 처리했더니 "레이아웃이 바뀌고 없던 내용이 생겼어요 — 팀구성에서 팀원이 모두 빠지고 '1인 기업'이라는
> 문구가 생겼다"는 반려를 받았다. **원본 3인 팀(CEO/CFO/CSO)을 모델이 1인 기업으로 재해석**한 것.

**원칙: 이미 승인된 덱은 픽셀이 자산이다. 바뀌는 것만 말하고 나머지는 건드리지 마라.**

```
You are EDITING an existing finished presentation slide (image-to-image).
OPEN the base slide and keep it as the foundation:
 "<ASCII 절대경로 / 원본 본문 PNG>"

EDIT INSTRUCTIONS — change ONLY what is listed below.
Keep ALL other pixels, layout, grid, card shapes, fonts, font sizes, colours, icon style and
spacing EXACTLY identical to the base slide. Do NOT redesign, do NOT rearrange, do NOT add or
remove any element that is not explicitly listed. Do NOT invent new text.
The top 15% and bottom 15% must remain empty exactly as in the base.
 1) <수정 1>
 2) <수정 2>
```

**핵심 작성 요령**
- 수정 항목마다 **"나머지는 그대로"를 개별 문장으로 반복**한다. 예: *"The funnel graphic, the three
 isometric illustrations, card shapes and all other text stay identical."* 이 한 줄이 재해석을 막는다.
- 사진 교체는 **"같은 프레임 위치·크기에 끼워라"**(`fit each photo into the SAME frame position and
 size that the element it replaces occupied`)로 지시 — 안 그러면 레이아웃을 다시 짠다.
- 요소 **삭제**는 "무엇으로 대체하지 말 것"까지 써야 한다(`leaving that area as clean empty
 background of the same card colour. Do NOT replace them with anything else.`).
- 원본에 있던 **인물·조직 구성은 절대 임의로 줄이지 말 것**. 개인정보 때문에 이름을 빼야 하면
 **구조(3인 카드)는 유지하고 이름 줄만 제거**한다.
- base는 **크롬 합성 전 본문(raw)** 을 쓴다. 완성본을 base로 하면 제목바가 이중으로 얹힌다.
- **★★ EDIT 전에 "고객이 실제로 받은 파일"을 base로 특정하라 (2026-07-27 실측)**: 작업 폴더에 `raw_b`, `raw_b2`, `raw_b3`처럼 세대별 raw가 쌓여 있으면 **어느 것이 납품본인지 기억에 의존하면 반드시 틀린다.** 실측: raw_b2를 base로 edit했는데 실제 납품본은 **raw_b3**였고(전 15장이 서로 다름), 재사용 슬라이드에서 3D 아이콘이 통째로 사라져 "레이아웃이 바뀌었다"는 2차 반려로 이어졌다.
 → **판정 절차(필수)**: 고객이 준 납품 PDF를 `fitz`로 페이지 렌더 → 각 raw 폴더와 픽셀 MAE 비교 → 승수가 많은 폴더를 base로 확정.
 ```python
 o = np.array(Image.open(f"orig_pdf/p{sid}.png").convert("RGB").resize((400,225))).astype(int)
 b = np.array(Image.open(f"{cand}/slide_{sid}.png").convert("RGB").resize((400,225))).astype(int)
 score = np.abs(o-b).mean() # 낮을수록 일치. 납품본은 보통 MAE < 5 인 장이 섞여 나온다
 ```
- **★ 납품본에만 있는 "후합성 요소"를 먼저 목록화하라**: EDIT base(raw)에는 없고 완성본에만 있는 사진·로고·쪽번호는 *"그대로 두라"고 지시해도 되살아나지 않는다*(base에 없으니 유지할 대상이 없음). 실측: 좌측 실사진 3장이 통째로 소실. → EDIT 착수 전 **완성본 vs base를 나란히 비교해 후합성 요소를 목록화**하고, 빌드의 SLOTS에 반드시 복원할 것.

**실측 결과**: 팀구성 3인 카드·인용블록·아이콘이 픽셀 단위로 보존된 채 이름만 사라지고 사진 2장이
교체됨. 자금 슬라이드도 도넛·아이콘·패널을 유지한 채 수치 7개만 정확히 갱신됨. 재생성 대비
**레이아웃 리스크 0**.

**언제 재생성인가**: 신규 덱, 컨셉 자체 변경, 슬라이드 신설. 그 외 기존 덱 수정은 전부 EDIT.

### 철칙 D — 실사진은 원본 자산으로 보존하고 HTML이 배치한다

실사진은 증거다. Codex에 원본 사진을 다시 그리게 하지 않는다. 재해석 과정에서 인물·제품·
현장·색·로고·설치 상태가 달라질 수 있다. 현재 하이브리드 기본 경로는 다음과 같다.

1. 원본 사진 또는 Codex가 **새로 생성한 사진 자산**을 별도 PNG/JPEG로 준비한다.
2. 정확한 제목·설명·출처·캡션은 HTML이 렌더한다.
3. `image` 레이아웃에 `imagePath`, `assetRole: "photo"`, `imageFit`,
   필요하면 `imageScale`과 focal 위치를 구조화해 전달한다.
4. `.layout.json`에 원본 절대경로와 digest를 기록한다.
5. 사진 피사체를 가리거나 자르지 않고, 중앙 공백·한쪽 쏠림은 focal/scale 검증으로 차단한다.

Codex에 사진을 전달해 **새 슬라이드 전체를 재생성하는 경로는 기본값이 아니다.**
사용자가 사진의 창의적 재해석을 명시한 경우에만 허용한다. 로고·서명·QR·계약 증거처럼
픽셀 보존이 중요한 자산은 변형 없이 HTML `img`로 배치한다.

## 5. 디자인 원칙 (크리틱이 검사하는 것 = 프롬프트에 넣을 것)
1. **프레임 채움 / 하단 앵커**: 콘텐츠가 세로 중앙 한 줄에만 뜨고 상·하단이 비면 "아마추어 미니멀"로 읽힌다. **모든 콘텐츠 슬라이드 하단에 레지스터**(스탯바/요약 한 줄+아이콘/이미지/그래픽)를 넣어 앵커. "정제된 여백" ≠ "빈 공간".
2. **부유 금지**: 사진·도식·수치를 좌우 컬럼과 baseline 정렬. 사진은 near-full-height로 통합.
3. **미완성 금지**: 빈 원/빈 노드/플레이스홀더 = broken. 모든 요소에 실제 라벨·아이콘.
4. **균일 그리드 = 싸구려("AI 슬롭")**: 똑같은 카드 N개 나열보다 위계·비대칭(히어로+서브, 2단, 메타스트립)으로 설계.
5. **리치 컴포넌트**(레퍼런스에서 추출): 둥근 카드(옅은 틴트+미세 그림자) / 원형 배지 안 라인아이콘 / 2단 텍스트(굵은 제목+회색 설명) / 알약 배지(Before·After·STEP) / 하단 메타스트립 / 인용 콜아웃 / KPI 타일(큰 숫자+아이콘+캡션). 취향이 미니멀이어도 이 구조는 유지하되 작고 airy하게.
6. **일관성**: 반복 컴포넌트(배지 채움/아웃라인, 아이콘, 하단바 스타일)를 전 슬라이드 통일.
7. **실물 충실도**: 제품/장소/로고 사진은 재질·색·시그니처 그대로. 더 깨끗/희게/스톡으로 변형 금지. 여러 장이면 다양한 장면.

## 6. 취향은 파라미터 (프로젝트마다 주입)
디렉터·크리틱에 취향을 명시적으로 넘긴다. 없으면 레퍼런스에서 추론. 예시 — 발신주체: **작은 글자·넓은 여백·얇은 헤어라인·작은 아이콘·낮은 밀도**(무거운 카드/솔리드 바 지양, 단 텅 빈 미니멀도 거부) → [[ppt-taste-minimal-airy]]. 다른 프로젝트는 볼드·하이컨트라스트·큰 타이포일 수도. **취향에 맞춰 프롬프트의 글자크기·여백·강조를 조절**.

### ★★ 차트는 반드시 비율을 %로 계산해 지시할 것 (2026-07-23 실측)
모델은 **숫자 텍스트는 정확히 쓰지만, 그 숫자를 길이로 옮길 때 눈대중**을 한다. 납품 덱 실측: 막대 0.588이어야 할 것이 0.785, 곡선 포인트가 40% 부풀음, 처리비용 막대 1.90배→2.16배(과장), 원가율 0.707→0.774(**자기 강점을 스스로 축소**). 방향이 제각각이라 의도적 왜곡이 아니라 순수 눈대중.
→ 프롬프트에 **상대 비율을 미리 계산해 명시**: "9,792 막대를 100%로 할 때 5,760은 59%, 4,320은 44%, 3,200은 33%". 공통 블록도 주입:
`CHART ACCURACY: every bar length / segment width / point height MUST be mathematically proportional to its value. Do not eyeball it. Use one fixed scale per chart.`
1회 지시로 **오차 40%→10%까지** 개선되지만 완전 비례는 안 된다. 정밀도가 결정적이면 ①PIL로 막대만 후합성 ②또는 **밀도 높은 리포트 스타일**을 쓸 것(실측상 모던플랫·공공보고서형이 에디토리얼보다 비례가 정확했다).
검증은 육안 말고 **픽셀 실측**(강조색 엔드캡을 색상 클러스터링으로 잡아 막대 끝 좌표 추출).

### ★★★ 레이아웃 지시가 화면 텍스트로 새어나온다 (2026-07-27 실측 — 위험도 최상)
비율을 명시하면 정확도는 올라가지만, **모델이 그 비율을 "표시할 데이터"로 오해해 슬라이드에 찍는다.** 실측(납품 S08 시장규모): 막대 높이를 `100 : 62 : 42`로 지시했더니 하단 밴드에 **"TAM 100% · SAM 62% · SOM 42%"** 를 렌더. 실제 SAM/TAM은 5.7%(4,000억/7조)라 **심사위원이 즉시 오류로 읽는 치명적 노출**.
→ 비율 지시는 반드시 3종 세트로:
```
LAYOUT-ONLY INSTRUCTION (a drawing instruction, NOT text to display):
draw the columns at relative heights of 100 : 62 : 42.
NEVER print these layout ratio numbers anywhere on the slide.
The ONLY numbers allowed on this slide are "7조 원", "4,000억 원", "40억 원", "9.38%", "32%", "1%".
```
①`LAYOUT-ONLY … NOT text to display` 라벨 ②`NEVER print these ratio numbers` 금지문 ③**허용 숫자 화이트리스트**. ③이 가장 강력 — 목록 밖 숫자를 아예 못 쓰게 막는다.
검수 시 **"내 프롬프트의 지시값이 슬라이드에 보이나"** 를 별도 항목으로 볼 것(내용 오류가 아니라 프롬프트 누출이라 크리틱이 놓치기 쉽다).

### ★★ 컬럼별 수치 바인딩은 "이 컬럼엔 숫자 없음"까지 명시 (2026-07-27 실측)
다단 구성에서 컬럼마다 숫자 개수가 다르면, **모델이 시각 균형을 맞추려 숫자를 옆 컬럼으로 옮기거나 라벨과 짝을 바꾼다.** 실측(납품 S02): 숫자 없어야 할 1열에 77.9%가 들어가고, 2열의 77.9%↔65.6% 라벨이 서로 뒤바뀜.
→ ①`CRITICAL DATA BINDING - each number must sit under its OWN label. Do NOT move numbers between columns, do NOT swap.` ②컬럼별 개수 못박기: `column 1 = zero numbers, column 2 = exactly two, column 3 = exactly two` ③빈 컬럼은 **대체 요소를 지정**(`fill with a small clay-3D illustration - NOT with a number`). 안 주면 모델이 숫자로 메운다.

## 7. 콘텐츠 정직성
"레퍼런스만큼"은 **구조·톤 매칭**이지 **수치 복제**가 아니다. 실측: 레퍼런스/GPTs가 넣은 수치가 원본에 없는 환각일 수 있음(500→1,700 유입). **모든 수치는 원본 파일로 대조**, 없으면 실제 하드데이터로 치환. 정량 약하면 "수치 상승" 대신 "채널 0→1 구축·자체 운영 역량"으로 프레이밍.

> **2026-08-01 통합 확정.** PPT 관련 스킬이 `ppt-hybrid`·`ppt-image-first`·`slide-maker`로 흩어져
> `CLAUDE.md`는 `ppt-hybrid`를 가리키는데 실무 축적은 여기에만 쌓이는 모순이 있었다.
> **고객 납품·심사 제출은 전부 이 스킬 하나로** 한다. `ppt-hybrid`의 유용한 조각(`assemble_pptx.py`,
> `salvage_cache.py`)은 흡수했고, `ppt-image-first`·`slide-maker`는 deprecated.
> (납품처 2R 15장 · 수정요청 3회 반영 완료본. fix_canvas→normalize→SLOTS 후합성→크롬→업스케일→PPTX/PDF).

## 8. 재사용 자산
- **파이프라인 프롬프트**: `prompts/director.md`(2단계) · `prompts/critic.md`(4단계) — `{...}` 채워 `Agent`로 스폰.
- **병렬 생성 + 격리홈 + 루프**: `<스킬 폴더>/scripts/codex_parallel_gen.py`
 `python codex_parallel_gen.py jobs.json --cap 6 --retry 1 --loop 1 --effort high`
 jobs.json = `[{"label","refs":[절대경로…],"out","prompt"}]`. ★잡별 CODEX_HOME 격리 내장(고병렬 오염 방지). dup-headline 검사는 기본 OFF(에디토리얼 덱 오탐).
- **균일 크롬**: `<스킬 폴더>/scripts/chrome.py` — `Chrome(logo, footer, accent).apply(raw, out, "02", cover=False, with_logo=None)`. 상대좌표라 해상도 무관. 표지 베이크드 푸터 소거는 미디언필터(단색 덮기는 seam).
- **★ 조립 전 검수 게이트**: `scripts/deck_qc.py <슬라이드폴더>` — ①종횡비 불일치 ②좌·우 여백 소실 ③SAFE ZONE 침범을 픽셀로 검출, FAIL이면 exit 1. `--body`는 크롬 합성 전 검사. **콘택트시트 육안 검수로는 못 잡는 결함 전용**이며, 패널 안 텍스트 잘림·한글 깨짐은 여전히 우측 확대 크롭으로 봐야 한다.
- **덱별 스크립트**(세션 스크래치에 매번): jobs 빌더 + assemble(정규화 1920×1080 → 크롬 → fitz로 PDF). PIL PDF는 JPEG 코덱 필요 → **fitz(PyMuPDF)로 PDF**.
- ★★ **하이브리드 보고서 모드 (실증 스크린샷 임베드)** — `scripts/screenshot_frame.py`: 결과보고·성과보고처럼 **실제 화면(대시보드·매출표·시트·앱)을 넣어야 하는 대형 덱**은 codex 전용으로 안 됨(codex는 실제 화면 못 그림). **[C] codex 내러티브 + [S] 스크린샷 프레임** 혼합. `render(spec, out_dir, accent)` 또는 CLI `python screenshot_frame.py spec.json OUT --accent 503020`. spec=`[{num,tab,eyebrow,title,images:[png],caption,layout:"one"|"two"}]`. 프레임=eyebrow+제목+라운드카드+그림자+캡션 pill+은은한 데코, **강조색 파라미터**(고정 금지). [C]/[S] 모두 slide_NN.png로 내고 assemble이 1..N 순서 병합. 실전: 납품처 신보 결과보고 41장([S]19+[C]21+종합1, 2026-07-19). 40장급 PPTX는 JPEG(q84) 재압축으로 <30MB(전송 한도).

## 9. E2E 런북 (명령 순서)
1. **입력**: 슬라이드별 내용(정확한 표시 텍스트, 수치는 원본 대조) + 레퍼런스 이미지 + 취향 확정.
2. **로고/강조색**: 정품 로고 크롭·키아웃(브랜드명 일치하는 마크만). 강조색 hex 확정.
3. **2단계 디렉터 스폰**: `prompts/director.md` 채워 `Agent` → `jobs.json` 산출.
4. **프로브**: 텍스트가 가장 많은 1장과 대표 씬 1장을 먼저 생성한다. 승인 계정 로그인·이미지 생성 권한·남은 usage·한글·수치·SAFE zone을 확인하고, 시작 시각·수업 종료 20분 전 컷오프·최대 재생성 2회를 `deck-output-receipt.json`에 기록한다.
5. **3단계 배치 생성**: 프로브가 PASS일 때만 `codex_parallel_gen.py … --effort high`를 실행한다.
6. **4단계 크리틱 스폰**: `prompts/critic.md`를 채워 `Agent`로 PASS/FIX를 판정한다.
7. **루프**: FIX 슬라이드만 최대 2회 재생성한다. 여전히 BLOCK이거나 usage·시간 컷오프에 닿으면 미검증 이미지를 납품하지 않는다. PPT가 선택 산출물이면 BLOCK으로 남기고, 수업에서는 HWPX 흐름을 우선한 뒤 `scene=` 없는 코드 전용 덱 데모 또는 사전 생성본으로 설명한다.
8. **조립**: 전 슬라이드 PASS일 때만 크롬 합성 → fitz PDF → 사용자 전달을 진행한다.

## 10. 실전 교훈 (구체 함정)
- **로고 추출**: 슬라이드에서 잘라낸 로고는 주변 텍스트 아티팩트를 물고 옴 → 타이트 크롭+getbbox 오토크롭+고립 얼룩 수동 제거. 페이퍼 배경 키아웃=밝고(>188) 저채도(sat<42) 투명화. 초록 등 이질 잔여 색 제거.
- **배경 위 텍스트 소거**: 그라데이션/텍스처 위 단색 덮기는 사각 seam → `MedianFilter(size=21)` 2회(글자획만 소거, 배경 보존).
- **글자 검증 게이트**: 자동검증(크기·해시)은 글자 깨짐/오타 판정 불가. 유일 게이트 = **사람 눈 또는 크리틱 에이전트가 컨택트시트/개별 Read**. 오타도 크리틱이 잡음(실측: "증가"가 "종가"로 오렌더 → 크리틱이 검출 → 재생성).
- **codex 도구 선택 확률성**: 같은 프롬프트도 슬라이드마다 이미지생성 vs PIL을 확률적으로 고름 → 철칙 A로 강제. 깨진 장만 re-roll.
- **codex 사용량 한도**: 대량 생성 전 승인된 계정으로 대표 1장 probe를 실행하고 남은 usage와 컷오프를 기록한다. 수업 중 한도에 닿으면 임의 계정으로 전환하지 않고 optional PPT 생성을 중단한다. 미검증 이미지는 납품하지 않는다.
- **upscayl 1장 실패가 전체 조립을 죽인다**(2026-07-27 실측): 대용량 다크 실사(클로징 등)에서 간헐 실패 → 다음 줄 `Image.open(out)`이 FileNotFoundError로 스크립트 전체 중단(앞 11장 업스케일 성과가 build로 못 넘어감). → upscale 루프는 **①2회 재시도 ②그래도 실패면 원본 복사 후 계속 ③말미에 FAIL 목록 보고** 구조로 짤 것. 단독 재실행하면 대부분 성공한다(동일 파일 2회차 성공 확인).
- **기존 덱 리디자인 시 원본 사진 회수**: 사용자가 PDF만 준 경우 페이지가 flatten된 단일 이미지라 개별 사진 추출 불가 → **좌표 크롭**으로 회수(`fitz`로 페이지 PNG 렌더 → PIL crop). 크롭 후 **콘택트시트로 텍스트 혼입 확인** 필수(표지·클로징 크롭은 헤드라인이 딸려온다 → 텍스트 없는 하단/측면만 재크롭). 로고도 같은 방식으로 회수하되 **좌우 여유를 넉넉히**(타이트하면 워드마크 앞글자가 잘림 — 실측: MANJOKDANG→OKDANG).
- **★ codex가 슬라이드마다 다른 종횡비로 뱉는다**(2026-07-27 실측): 같은 배치에서 14장은 1672×941(16:9)인데 1장만 **1774×887(2:1)** 로 나옴. 그대로 조립하면 그 장만 PPTX/PDF에서 찌그러진다(실측: 4K 업스케일 후 7096×3548 vs 6688×3764). → 파이프라인에 **`fix_canvas()` 선행 단계 필수**: 종횡비가 덱 기준과 0.02 이상 어긋나면 콘텐츠 bbox를 뽑아 기준 캔버스(예 1672×941)에 비율 유지로 재배치. normalize 앞에 두어야 안전. 조립 직전 `set(Image.open(f).size)`로 **크기 종류가 1개인지 검사**하는 게 가장 확실한 게이트.
- **부분 수정(개정) 작업은 "본문 재생성"과 "크롬 텍스트 교체"를 먼저 분류**(2026-07-27): 고객 수정 요청 20여 건 중 상단 카피·하단 요약·순서·섹션 제목은 전부 **코드(크롬 SPEC)에서 처리 가능** → 15장 중 11장만 재생성하고 4장은 기존 본문 재사용. 요청서를 받으면 ①본문 픽셀이 바뀌는가 ②크롬 텍스트만 바뀌는가로 나눈 뒤 재생성 범위를 최소화할 것. 순서 재배열은 `{신규sid: (구sid, 번호, 섹션명, 카피, 요약)}` 매핑 dict 하나로 본문 복사·크롬·쪽번호가 동시에 해결된다.
- **★★ 발표용 덱에 개인정보 금지 (2026-07-27 사용자 확정 — 전 덱 공통)**: 공모전·심사 발표는 프로젝터로 공개 상영되므로 **성명·휴대폰·이메일·주소·SNS 계정을 슬라이드에 넣지 않는다.** 실측(납품처 v2): 표지 "발표자 OOO", 팀 슬라이드에 "OOO / 010-… / …@naver.com"이 그대로 노출돼 지적받음. → 프롬프트 SYS에 **PRIVACY RULE 블록 상시 포함**: `NEVER render any personal name, mobile number, email address, address or SNS handle anywhere. Refer to the founder only by role ("대표", "창업자").` 인물 사진도 **얼굴이 식별되지 않게 크롭**하도록 지시. 연락처는 제출 서류에만 넣고 발표 슬라이드에서는 뺀다. (브랜드명·작품 태그는 개인정보가 아니므로 유지)
- **★ 상단 장표번호와 하단 쪽번호를 일치시킬 것 (2026-07-27 실측)**: 표지를 1페이지로 세면 본문 장표번호(01~14)와 물리 쪽번호(02~15)가 **계속 1씩 어긋나** 사용자가 바로 알아챈다. → 크롬에서 하단 쪽번호를 물리 sid가 아니라 **장표번호(num)** 로 출력하고 표지는 빈 문자열: `d.text(..., num or "", ...)`.
- **★ 텍스트가 패널·슬라이드 경계를 넘어 잘린다 (2026-07-27 실측)**: codex가 KPI 캡션을 자기 패널보다 넓게 그려 우측이 잘림(납품 S07 "설치 완료 공간" → "설치 완료 공간"의 끝 글자 소실). **normalize로는 못 고친다** — bbox 기준으로는 이미 안전 범위라 축소 대상이 아니기 때문. → ①프롬프트에 **TEXT CONTAINMENT 블록** 삽입: `EVERY caption must fit COMPLETELY INSIDE its own panel with padding on both sides. No text may touch, overflow or be clipped by a panel edge or the slide edge. If too wide, widen the column or shrink the caption — NEVER let a character be cut.` ②서브컬럼 x범위를 명시하고 우측에 4% 빈 여백 요구. ③검수는 **우측 1/3을 2배 확대 크롭**해서 육안 확인(콘택트시트로는 안 보임).
- **★ 크롬 헤드라인은 폭을 재서 자동 축소할 것 (2026-07-27)**: 제목 길이가 장마다 달라 고정 폰트로 그리면 긴 제목이 우측 끝까지 밀린다. → `avail = W*0.95 - (x + 번호폭)` 을 계산하고 `while size > 하한: if textlength(title, font) <= avail: break; size -= 2` 로 축소, 축소 시 번호와 baseline을 맞춘다(`base = ty + (기본크기-size)//2`).
- **★ normalize에 폭 제약도 넣을 것**: 높이만 기준으로 맞추면(`s = tgt_h/(b-t)`) 원본이 좌우 끝까지 찬 경우 여백이 안 생긴다. → `SAFE_W = 0.90` 을 두고 `s = min(1.0, tgt_h/(b-t), tgt_w/(r-l))`.

## 핵심 원칙 한 줄

---
*실전 사례: 고객사 Q AI마케팅 결과보고 10장(2026-07-06). 파이프라인으로 "하단 앵커 부재" systemic 문제·03 오타·무거운 하단바를 크리틱→디렉터→재생성 루프로 수렴, 레퍼런스 품질선 도달.*
