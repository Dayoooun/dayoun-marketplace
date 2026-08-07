---
name: ppt-editorial
description: "발표 덱 제작 통합 하네스. 요구사항을 확인한 뒤 deck_brief·content_report·style_card·slide_blueprint로 정리하고 두 모드 중 하나로 생성한다 — (A) 씬 덱: 배경 일러스트만 모델이 그리고 텍스트는 코드가 렌더해 한글이 정확하며 원본 spec 수정이 빠른 이미지형 PPTX/PDF 산출. (B) 이미지 퍼스트: 슬라이드를 한 장 이미지로 통째 생성, 비주얼 자유도 최대. 제안서·결과보고·IR·강의자료·리디자인에 쓴다. Windows와 macOS 지원."
---

# 슬라이드 덱 하네스 — 씬 덱 방식

## 파이프라인 위치: 10단계 발표 PPT·대본·예상 Q&A

사업계획서 흐름에서 사용할 때는 `review-business-plan`에서 승인된 최종 문안과
HWPX 구조·화면검사 기록을 입력으로 받는다. 발표 청중·발표시간·평가항목을 함께 확인한다.

이 스킬은 HWPX 파일을 슬라이드로 직접 변환하지 않는다. 승인된 내용을
요구사항 확인 뒤 `deck_brief → content_report → slide_blueprint`로 압축·재구성한다.
PPT의 수치·고유명사·주장은 승인된 사업계획서와 다시 대조한다.

**완료 조건**: PDF/PPTX 렌더 육안검사, 수치 원문 대조, 발표시간에 맞춘 대본,
평가지표 기반 예상 질문과 근거가 있는 답변이 모두 있어야 한다.


> ## 먼저 모드를 고른다
>
> | | **A. 씬 덱** (기본값) | **B. 이미지 퍼스트** |
> |---|---|---|
> | 모델이 그리는 것 | 배경 씬·일러스트**만** | 슬라이드 **한 장 전체** |
> | 텍스트 | **코드가 렌더** — 한글 정확, 폰트 고정 | 이미지 안에 그려짐 |
> | 문구 수정 | 조립만 다시 — **수초** | 해당 장 재생성 |
> | 산출 | PDF + 이미지형 PPTX + 재조립 가능한 `spec.json` | 이미지형 PPTX |
> | 적합 | 제안서·결과보고·IR·강의 (텍스트가 계약·수치) | 콘셉트 제안·비주얼 우선 |
> | PowerPoint 내부 텍스트 편집 | 불가 — 문구는 `spec.json`에서 고쳐 재조립 | 불가 — 해당 장 재생성 |
>
> **판단 기준 한 줄**: 글자가 틀리면 안 되거나 나중에 고칠 일이 있으면 **A**,
> 그림이 전부이고 텍스트는 장식이면 **B**.
>
> 두 모드 모두 같은 이미지 생성 엔진을 쓴다. 차이는 **모델에게 무엇을 그리게 하느냐**다.

> ⚠️ 스킬명 `ppt-editorial`은 초기 이름이 남은 것이다. 현재는 씬 덱과 이미지 퍼스트 두 모드를 모두 제공한다.

레퍼런스(사용자가 원하는 룩을 보여주는 완성 덱 이미지)를 기준으로, **어떤 분야든** 잡지·갤러리 수준의 16:9 슬라이드를 codex(GPT Image)로 생성한다. 슬라이드의 모든 텍스트·아이콘·도식·사진을 이미지 안에 렌더하고, 로고·페이지번호 같은 고정 크롬만 PIL로 후합성한다.

## ★★★ 0. 실행 전제조건 (없으면 먼저 설치한다)

**에이전트 지시**: 이 스킬을 처음 쓰기 전에 아래를 점검하고, 빠진 것이 있으면
사용자에게 되묻지 말고 **바로 설치한 뒤** 작업을 이어간다. 설치가 실패할 때만 보고한다.

### 한 줄 점검

```bash
python -c "import PIL,cv2,fitz,numpy,pptx,shutil,sys;print('codex:',shutil.which('codex'),'| py:',sys.version.split()[0])"
```

`codex: None`이거나 `ModuleNotFoundError`가 나면 해당 항목을 설치한다.

### 파이썬 패키지

```bash
pip install pillow opencv-python pymupdf numpy python-pptx
```

| import | 설치명 | 쓰는 곳 | 없으면 |
| --- | --- | --- | --- |
| `PIL` | `pillow` | 씬 합성·QC·폰트 측정 | 전 기능 정지 |
| `fitz` | `pymupdf` | PDF 생성·페이지 측정 | PDF 산출 불가 |
| `numpy` | `numpy` | 여백 검사·레이아웃 계산 | QC·레이아웃 정지 |
| `pptx` | `python-pptx` | 편집 가능 PPTX 출력 | PPTX만 불가 (PDF는 됨) |
| `cv2` | `opencv-python` | `photos.py` 사진 자동 크롭 | 사진 슬라이드만 불가 |

파이썬은 **3.10 이상**을 쓴다.

### Windows와 macOS

하네스 코드는 두 운영체제를 같은 경로로 지원한다. Windows에서는 위 명령의
`python`·`pip`를 쓰고, macOS에서는 다음처럼 실행한다.

```bash
# Python 또는 Node가 없을 때만
brew install python node

python3 -m pip install pillow opencv-python pymupdf numpy python-pptx
npm i -g @openai/codex
codex login
python3 scripts/harness_smoke.py
```

`platform_support.py`가 Windows의 사용자 폰트 폴더와 macOS의
`~/Library/Fonts`, `/Library/Fonts`, `/System/Library/Fonts`를 함께 탐색한다.
Pretendard가 없으면 Noto Sans KR 또는 Apple SD Gothic Neo로 폴백한다.
별도 폰트를 써야 하면 `PPT_EDITORIAL_FONT`에 파일 경로를 지정한다.

macOS에서 GUI 앱을 통해 실행해 Homebrew 경로가 `PATH`에서 빠져도
`/opt/homebrew/bin`과 `/usr/local/bin`의 `codex`를 다시 찾는다.
생성 종료도 Windows의 `taskkill` 또는 macOS의 POSIX 프로세스 그룹으로 자동 분기한다.

### codex CLI — 씬 생성 전용

```bash
npm i -g @openai/codex
codex login
codex --version
```

**Claude Code에서 실행하더라도 이 CLI는 따로 설치해야 한다.**
씬(배경 이미지) 생성은 codex를 통해 GPT-Image를 호출하기 때문이다.
`scripts/codex_parallel_gen.py`의 `require_codex()`가 시작 시 검사하고,
없으면 위 설치 명령을 출력하며 중단한다 — 원인 불명의 `FileNotFoundError`는 나지 않는다.

### codex 없이 되는 것

씬을 뺀 나머지는 전부 동작한다. 이미지 생성이 불가능한 환경이면
`scene=` 인자를 비우고 진행한다. 레이아웃·타이포·표·차트·PDF·PPTX는
모두 코드가 처리하므로 **글자 중심 덱은 codex 없이 완성된다.**

### 선택 사항

| 대상 | 용도 | 없을 때 |
| --- | --- | --- |
| 한글 폰트(Pretendard·G마켓산스 등) | 지정 서체 렌더 | `fonts.py`가 시스템 폰트로 자동 폴백 |
| Chrome/Chromium | 일부 합성 경로 | 기본 경로는 Pillow만 쓰므로 불필요 |

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


## ★★★ 2. 모드 A — 씬 덱 실행 (기본값 · 4단계 파이프라인)
**한 에이전트가 내용·디자인·생성·판단을 다 하면 깨진다.** 특히 "판단"에서 오케스트레이터의 자기 눈이 반복 실패한다(실측 3회 어긋남). 역할을 분리하라.

| 단계 | 주체 | 산출물 |
|------|------|--------|
| 1. 입력 | 사용자 | 슬라이드별 내용 + 레퍼런스 이미지(원하는 룩) + 취향/톤 |
| 2. **디자인 디렉터** | `Agent`(general-purpose) — `prompts/director.md` | 슬라이드별 codex 프롬프트 = `jobs.json` |
| 3. **codex 병렬 생성** | `scripts/…/codex_parallel_gen.py` | 슬라이드 이미지 N장 |
| 4. **디자인 크리틱** | `Agent`(general-purpose) — `prompts/critic.md` | 슬라이드별 PASS/FIX + 구체 수정지침 |
| 5. 조립 | 오케스트레이터 | 크롬 합성 → 통합 PDF |

**루프**: 크리틱이 FIX한 슬라이드만 → 2단계(디렉터, 크리틱 피드백 첨부)로 되돌려 프롬프트 재작성 → 3단계 재생성 → 4단계 재판정. 전체 PASS까지.
- **오케스트레이터는 미적 판단을 하지 않는다.** "예쁘다/괜찮다" 자평 금지 → 크리틱 에이전트에 위임.
- 디렉터·크리틱은 반드시 **레퍼런스와 (있으면) 현재 결과물을 Read로 직접 보게** 하고, 취향을 판정 기준으로 넘긴다.
- 실증(고객사 Q): 크리틱이 "하단 앵커 부재/세로중앙 부유 띠"를 systemic 문제로 한 번에 잡음 — 오케스트레이터 혼자선 3라운드 놓친 것.

## ★★★ 3. 모드 B — 이미지 퍼스트 실행

슬라이드 한 장을 통째로 생성한다. 텍스트도 이미지 안에 그려지므로
**한글 깨짐·줄바꿈 오류를 감수**해야 하고, 문구를 고치려면 그 장을 다시 뽑아야 한다.

콘셉트 제안처럼 비주얼이 전부이고 텍스트가 장식인 경우에만 고른다.

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
- 로고·스크린샷·인증서·작은 글자 표는 생성 대상에서 빼고 후합성한다.
- 기본 산출은 이미지형 PPTX다. 편집 가능한 PPTX는 부차적이며,
  PowerPoint에서 폰트·레이아웃이 달라질 수 있음을 사용자에게 알린다.
- 검수는 모드 A와 같은 게이트를 쓴다 — `scripts/deck_qc.py`로 여백·종횡비를 본다.

상세 워크플로는 `references/image-first-workflow.md`를 읽는다.


## 3-1. 스타일 프로파일 (모드 공통 · 검증된 디자인 DNA — 골라서 앵커로 먹임)
원하는 룩을 **레퍼런스 세트 + 스타일 블록 + 승인된 예시 슬라이드**로 고정한다. "이 DNA 항상 잘 나오게"의 메커니즘 = 아래 3종을 `-i`로 먹이는 것.

### ★★★ 0. 씬 덱 (Scene Deck) — **기본값. 고객 납품·피칭·제안은 여기서 시작** (2026-08-01 확정)

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

d.generate() # 씬 생성 (있으면 생략 — 철칙 E)
d.build(pdf=True, pptx=True) # 조립 + PDF/PPTX
```

`domain` 한 줄로 팔레트·폰트·씬모티프·톤이 잡히고, 씬 비율·SAFE ZONE·PIL금지 지시·
재생성 방지가 자동이다. `build()` 시 `spec.json`이 저장돼 수정에 재사용된다.

#### 핵심 자산

| 파일 | 역할 |
|---|---|
| **`scripts/intake.py`** | 필수 정보 질문·기준 판단·사용자 확인 게이트 |
| **`scripts/platform_support.py`** | Windows/macOS 폰트·CLI·프로세스 공통 처리 |
| **`scripts/scene-deck/deck.py`** | 진입점. `from_brief → cover/agenda/slide/photos/closing → generate → build` |
| `scripts/scene-deck/presets.py` | 도메인 9종 — it/food/manufacturing/education/welfare/culture/public/medical/retail |
| `scripts/scene-deck/layout_engine.py` | 씬 구도 10종 + 강조요소 + 오버플로우 방어 |
| `scripts/scene-deck/info_layouts.py` | 표·대비·2×2·막대 정보 레이아웃 네 가지 |
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
- 크롬은 미니멀: 상단 파란 대시 + 영문 eyebrow / 우측 쪽번호, 하단 얇은 라인 + 회사명.
 **파란 풀블리드 밴드 금지**(촌스러움, 실측 반려). 표지는 크롬 없음.
- 헤드라인 **115px**(2560 캔버스). 씬 생성은 **`--effort high` 필수**.
- 필수 게이트: `python scripts/deck_qc.py <out폴더> --cover 01`
- 코드를 고쳤으면: `python scripts/harness_smoke.py`와 `python -m unittest scripts/test_harness.py -v`
- 디스크: 씬 생성 시 `.cxwork` 격리 홈이 덱당 300~700MB 생긴다. 시작·종료 시 자동 정리(`--keep-work`로 보존). 상세는 scene-deck README §20

> ⚠️ **아이콘 ≠ 씬.** 아이콘(80px 타일)을 키워 큰 영역에 쓰면 "커진 아이콘"으로 보여 싸구려가 된다.
> 아이콘 나열로 슬라이드를 채우려는 시도는 2026-08-01 실측에서 전부 반려됐다.

> ⚠️ **수정은 재생성이 아니다.** `Deck.load(spec).revise()` + `apply_command()`로 고친다.
> 텍스트·구도·순서·색·폰트는 조립만 하고(수초), 씬 내용을 바꿀 때만 그 장을 재생성한다.

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

→ 새 덱 시작 시 사용자에게 프로파일 확인(또는 사용자가 레퍼런스를 주면 그걸 새 프로파일로 흡수).

### ★★★ 절대 고정 금지 — 매 덱 사용자에게 질문 (2026-07-06 지시)
**강조색·서체·스타일 프로파일·톤 등 핵심 디자인 선택을 하네스나 특정 값(예: 브라운)으로 고정/가정하지 말 것.** 브랜드 로고에서 색을 뽑을 수 있어도 **반드시 사용자에게 확인**한다("강조색 이걸로 할까요?"). 취향은 프로젝트마다 다르다 → 시작 시 ①스타일 프로파일 ②강조색 ③서체(명조/고딕) ④(선택)레퍼런스를 물어보고 진행. 사용자가 준 레퍼런스가 있으면 우선.


## ★★★ 4. 3대 철칙 (도메인 무관 · 어기면 깨짐)

### 철칙 A — PIL 드로잉 금지 (텍스트 "???" 깨짐의 진짜 원인)
프롬프트에 이미지생성 강제가 없으면 codex가 슬라이드를 **이미지 생성 대신 Python/PIL/matplotlib로 그려버린다**. PIL 기본 폰트엔 CJK 글리프가 없어 **모든 글자가 "?"로 렌더**된다(면도날 직선 헤어라인 = 드로잉 증거, 파일크기 18~50KB=드로잉 / 700KB~1MB=이미지생성).
→ **모든 프롬프트 말미에**: `Use ONLY the image-generation capability — ABSOLUTELY NO Python/PIL/matplotlib/code drawing (renders text as broken '?'). Every glyph perfectly correct, no '?'.` 실측: 동일 슬라이드 45KB"???" → 923KB 완벽.

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

### 철칙 D — 실사진은 **codex에 전달해 슬라이드 안에 함께 그리게 한다** (2026-07-27 최종)
> ⚠️ 제목 주의: 2026-07-23까지는 "코드 후합성"이 정답이었고 아래 초기 서술이 그 흔적이다.
> **현재 기본값은 codex 전달이다.** 실측 재발(2026-07-27 납품처 v2): 개정된 철칙을 잊고 후합성으로
> 만들었다가 사용자에게 지적받아 6장을 재생성했다. 사진이 있는 슬라이드를 만들 때는
> **먼저 이 문단 끝의 ★★ 반전을 읽고 시작할 것.**
GPT-Image는 입력 사진을 **재해석해서 다시 그린다** — 제품·작품·인물의 디테일이 결정적이면 치명적이다.
→ 프롬프트에서 사진 영역을 좌표로 지정해 **완전히 비우게** 하고(`Leave the region from x=NN% to x=NN%, y=NN% to y=NN% COMPLETELY EMPTY — no frame, no outline, no label, no placeholder. A real photograph will be composited there later.`), 원본을 PIL로 cover 합성한다.

**핵심 이점**: 위치가 틀려도 **재생성 없이 좌표만 5초 만에 수정**. (납품 덱에서 5건을 이 방식으로 처리 — 모델이 그렸다면 장당 2~3분씩 재생성해야 했다.)

**★★ 반전 (2026-07-23 최종 확정) — 후합성보다 "codex에 사진 전달"이 낫다.** 후합성은 사진은 정확하지만 **모델이 만든 레이아웃과 따로 놀아** 옆에 어색한 여백이 남는다(납품 시안2 실측: 정규화로 콘텐츠가 축소되며 우측 대형 공백 발생). 사진을 codex에 넘겨 **레이아웃 안에 직접 배치**시키면 여백이 사라지고 통합이 자연스럽다. 관건은 **재해석 억제 프롬프트**:
```
★★★ REAL PHOTOGRAPHS — MUST BE INCLUDED (highest priority):
FIRST open these actual photo file(s): "<절대경로>"
These are DOCUMENTARY EVIDENCE of a real site / installed artwork the founder presents to judges.
REPRODUCE THEM FAITHFULLY: same composition, objects, colours, lighting, background.
STRICTLY FORBIDDEN: stylising, illustration/3D/clipart conversion, stock/imagined replacement,
changing the flowers/branches/vessel/room, inventing a different arrangement.
If a detail can't be reproduced, keep it simple and faithful rather than invent.
PLACEMENT: integrate naturally at ~x NN%~NN%, y NN%~NN%, as a clean rounded photo block with subtle
shadow; balance the composition so no side is left noticeably empty.
```
실측: 카페 설치·설문 현장·완성작·Before/After 사진이 원본과 **거의 완전 일치**로 재현됐고(스톡화 안 됨), 여백도 해소. refs에 사진 경로를 넣어야 codex가 파일을 연다.
- **후합성이 나은 경우**: 픽셀 100% 보존이 계약·법적으로 결정적일 때(로고·서명·QR). 그 외 발표 증거 사진은 codex 전달이 낫다.
- 파이프라인: 사진은 codex 생성분을 쓰므로 **후합성 단계는 건너뛴다**. normalize → 크롬만.

**슬롯 자동 피팅 필수** — 모델이 비운 영역과 지정 좌표는 미묘하게 어긋난다(헤드라인이 예상보다 내려오거나 KPI 숫자가 슬롯을 침범). 하드코딩 대신 **빈 영역을 감지해 슬롯을 자동 축소**하라:
```python
def fit_empty(slide, px0, py0, px1, py1, pad=10, max_shrink=0.42):
 a = np.array(slide.convert("L")).astype(int)
 bg = int(np.bincount(a.ravel()).argmax()) # 배경 = 최빈값
 content = np.abs(a - bg) > 14
 # 슬롯의 각 변이 콘텐츠에 닿는 동안 안쪽으로 밀어넣는다 (max_shrink까지)
```
어두운 배경(네이비 표지 등)에 사진을 얹을 때는 **하드 엣지가 "붙여넣은 판"처럼 보인다** → `cover_blend()`: ①사진 전체에 배경색 20% 블렌드(색온도 정합) ②좌측 40% 페더 그라데이션 ③같은 곡선의 알파 dissolve.

하단 밴드가 있는 레이아웃은 **밴드 상단을 자동 감지해 사진 하단을 클램프**하되, ⚠️밴드 안 흰 글씨 때문에 중앙 열은 오검출된다 → **우측 끝(x 0.90~0.98)에서 스캔**.

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
4. **프로브**: 텍스트 최밀집 1~2장 먼저 생성 → **한글/글자 육안검증**(자동검증은 깨짐 못 잡음) → OK면 전량.
5. **3단계 배치 생성**: `codex_parallel_gen.py … --effort high`.
6. **4단계 크리틱 스폰**: `prompts/critic.md` 채워 `Agent` → PASS/FIX 판정.
7. **루프**: FIX 슬라이드만 3(→필요시 2)로 되돌려 재생성 → 재판정. 전체 PASS까지.
8. **조립**: 크롬 합성(표지만 로고/푸터) → fitz PDF → 사용자 전달.

## 10. 실전 교훈 (구체 함정)
- **로고 추출**: 슬라이드에서 잘라낸 로고는 주변 텍스트 아티팩트를 물고 옴 → 타이트 크롭+getbbox 오토크롭+고립 얼룩 수동 제거. 페이퍼 배경 키아웃=밝고(>188) 저채도(sat<42) 투명화. 초록 등 이질 잔여 색 제거.
- **배경 위 텍스트 소거**: 그라데이션/텍스처 위 단색 덮기는 사각 seam → `MedianFilter(size=21)` 2회(글자획만 소거, 배경 보존).
- **글자 검증 게이트**: 자동검증(크기·해시)은 글자 깨짐/오타 판정 불가. 유일 게이트 = **사람 눈 또는 크리틱 에이전트가 컨택트시트/개별 Read**. 오타도 크리틱이 잡음(실측: "증가"가 "종가"로 오렌더 → 크리틱이 검출 → 재생성).
- **codex 도구 선택 확률성**: 같은 프롬프트도 슬라이드마다 이미지생성 vs PIL을 확률적으로 고름 → 철칙 A로 강제. 깨진 장만 re-roll.
- **codex 사용량 한도**: 대량(수십 장) 생성 시 usage limit 도달 가능 → 계정 전환(`codex logout`→`codex login`, auth.json 자동반영). 배치는 순차(동시 2개 codex_parallel_gen 실행 시 뒤엣것 no-output).
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
