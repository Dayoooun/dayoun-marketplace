# 씬 덱 (Scene Deck) — 고품질 프로파일 ★기본

> 2026-08-01 확정. 실제 납품 승인본(납품처 기술해자·납품처 결과보고) 수준을 재현하는 표준.
> **고객 납품·피칭·제안 덱은 이 프로파일로 시작한다.**

## 1. 이게 왜 기본인가

이전 시도들이 반려된 이유를 그대로 뒤집은 것이다.

| 반려된 접근 | 이 프로파일 |
|---|---|
| 아이콘 10개 만들어 카드에 나열 | **씬 일러스트 1장이 슬라이드를 지배** |
| 카드 3~4개 균등 배치 | 좌 대형타이포 / 우 씬 **2단 그리드** |
| 파란 풀블리드 밴드 | **미니멀 크롬** — 대시+영문라벨 / 얇은 하단 라인 |
| 5장 전부 같은 구도 | **내용이 구도를 결정** — § 8 구도 10종 |

### ★ 아이콘 ≠ 일러스트 ≠ 씬
- **아이콘**: 80px 타일. 카드 안 보조 요소. 키우면 "커진 아이콘"으로 보여 싸구려가 된다.
- **씬**: 메시지를 담은 한 장면. 갈라진 플랫폼, 다리를 건너는 사람, 교집합에 선 사람.
  **슬라이드 하나당 씬 하나**가 원칙.

## 2. 씬 프롬프트 규격

`presets.style_block(domain)`이 도메인별로 만들어 준다. **직접 쓰지 마라.**
`deck.py`를 쓰면 이 블록이 자동으로 프롬프트에 들어간다. 구성 요소:

```
RENDER STYLE — High-end 3D render, soft studio lighting, matte surfaces,
  rounded tactile geometry, soft contact shadows, subtle depth of field.
  NOT flat vector, NOT cartoon, NOT clay-toy, NOT line icons.
  Apple-keynote / fintech quality.

PALETTE — primary #2B6EF2 · lighter #6FA0FA · pale #DCE7FD
  white · grey #F1F3F6 · ink #161D2B   (blue is the hero)

BACKGROUND — pure white, generous empty space.
```

### ★ 씬 안에 라벨을 박아라
기준 덱은 그림 안에 한글 라벨이 들어간다(빙산의 `원고/조판/품질검증`, 벤의 `둘 다`).
라벨 없는 씬은 정보량이 부족하다.

```
TEXT LABELS rendered in the image (bold Korean gothic, ink colour, small):
  above the left platform:  "경영"
  above the right platform: "기술"
```


## 3. 실행 순서

**`deck.py`를 쓴다.** 아래는 그 내부 동작이며, 직접 호출할 일은 없다.

```python
from deck import Deck
d = Deck(domain="식음료", foot="OO식품", title="사업소개")
d.cover(...); d.agenda([...]); d.slide("L", ...); d.closing(...)
d.generate()                   # 씬 생성 (없는 것만)
d.build(pdf=True, pptx=True)   # 조립 + 출력
```

`generate()`가 내부적으로 하는 일:
1. `presets.style_block(domain)` + 씬 서술 + 라벨 + SAFE ZONE + PIL금지 지시로 프롬프트 조립
2. 구도별 비율 결정 (W/F는 `16:9 wide`, 나머지 `4:3 landscape`)
3. `jobs.json` 기록 후 `codex_parallel_gen.py --effort high` 실행
4. 산출물 확인 — 없거나 100KB 미만이면 실패로 경고

검수는 `python ../deck_qc.py <out폴더> --cover 01`.


## 4. 그리드 규격 (실측 기반)

캔버스 **2560×1440**, 좌우 여백 `M = W*0.030`

| 요소 | 위치 · 크기 |
|---|---|
| 상단 크롬 (대시+영문라벨 / 쪽번호) | `y = H*0.062` |
| 헤드라인 시작 | `y = H*0.245` (L/S) · `H*0.22` (A) · `H*0.16` (W) · `H*0.155` (C) |
| 헤드라인 크기 | **115px** (L/S/A) · 95px (W/C) — `fonts.TYPE_SCALE` 황금비 산출 |
| 표지 헤드라인 | **121px** (`display`). 텍스트 높이 실측 후 세로 중앙 배치 |
| 서브 텍스트 | 38px, grey, 행간 58px, 자간 −0.76 |
| 하단 구분선 | `y = H*0.889`, 1px |
| SAFE ZONE | `BODY_TOP = H*0.150` · `BODY_BOT = H*0.855` |
| 씬 영역 | L/S `W*0.40~0.42` · A `W*0.58` · C `W*0.56` · F `W*0.98` |
| 텍스트 최대 폭 | L 50% · S 42% · A 36% · T 30% · C 78% (오버플로우 방어) |

크기·행간·자간은 전부 `fonts.py`가 황금비(φ=1.618)로 산출한다. **하드코딩 금지.**

## 5. 함정

- **`trim_white()` 필수** — 씬 PNG는 흰 여백을 잔뜩 물고 온다. 그대로 붙이면 작아 보인다.
- **`--effort high` 없으면 품질이 무너진다.** 씬은 렌더 난이도가 높아 기본 effort로는 평면적으로 나온다.
- **씬 비율을 용도에 맞게 요청** — W 구도용은 `16:9 wide`, 나머지는 `4:3 landscape`.
- 헤드라인 2줄이 기본. 1줄이면 허전하고 3줄이면 씬이 눌린다.

## 6. 타이포그래피 — `fonts.py`

**폰트는 절대 하드코딩하지 말고 `fonts.py`를 import 한다.** 맑은 고딕은 사용 금지.

```python
import sys, os
sys.path.insert(0, os.path.join(SKILL_DIR, "scripts", "scene-deck"))
from fonts import font, metrics, draw_tracked, recommend

f = font("headline", family="pretendard")     # Pretendard Bold 115
m = metrics("headline", "pretendard")          # {size, leading, tracking_px}
draw_tracked(d, (x, y), "헤드라인", f, INK, m["tracking_px"])
```

### 폰트 풀 (11종 가용, `python fonts.py`로 점검)

| 계열 | 키 | 언제 |
|---|---|---|
| 모던 산세 | **`pretendard`** ★기본 | IT·핀테크·컨설팅. 중립적 |
| | `paperlogy` | 제조·건설·기술. 각지고 견고 |
| | `a2z` | 디자인·브랜딩. 기하학적 |
| | `noto` | 공공 제출물(폰트 미설치 대비) |
| 명조 | `serif_chosun` | 표지 헤드라인. 전통·권위 |
| | `serif_ridi` | 긴 문장·인용. 읽기 최적화 |
| | `serif_noto` | 결과보고서. 차분한 격식 |
| 디스플레이 | `gmarket` | 표지·섹션 **제목만**(본문 금지) |
| | `euljiro` | 레트로·로컬·전통시장 |
| 손글씨 | `hand_malang` | 교육·아동·복지의 **강조 문구만** |
| | `hand_letter` | 감사 인사·클로징 한 줄 |

`recommend("교육 복지")` → 주제에 맞는 조합을 자동 추천한다.

### 황금비 스케일 (φ=1.618, base 38px @2560×1440)

| 역할 | 크기 | 행간 | 자간 |
|---|---|---|---|
| display | 121 | 138 | −6.05 |
| **headline** | **115** | **140** | **−5.17** |
| title | 95 | 120 | −3.80 |
| num | 110 | 121 | −5.50 |
| sub | 38 | 58 | −0.76 |
| eyebrow | 30 | 36 | **+1.80** (영문 대문자는 벌림) |
| chrome | 28 | 36 | −0.28 |

**원칙**: 글자가 클수록 자간을 조이고 행간을 붙인다. 작을수록 벌린다.
영문 eyebrow만 자간을 크게 벌려(+0.08em) 라벨답게 만든다.


## 7. 도메인 프리셋 — `presets.py`

```python
from presets import preset, style_block
style_block("식음료")     # 그 도메인용 STYLE 블록 전체를 반환
```

9종: `it` `food` `manufacturing` `education` `welfare` `culture` `public` `medical` `retail`
별칭 해석 — "협동조합"→welfare, "AI 스타트업"→it, "공연 기획"→culture.
각 프리셋은 **팔레트 + 폰트조합 + 씬모티프 + 톤**을 함께 묶는다.

## 8. 구도 10종 — 내용이 결정한다

`layout_engine.LAY`. 슬라이드 성격에 맞춰 고른다.

### 본문 7종

| 코드 | 구도 | 언제 쓰나 |
|---|---|---|
| **L** | 좌 텍스트 / 우 씬 | 개념 설명. 텍스트가 주도 |
| **S** | 좌 씬 / 우 텍스트 | 리듬 전환. 수직 축적형 씬 |
| **W** | 상단 텍스트 / 하단 와이드 씬 | **순서·프로세스**. 가로로 흘러야 읽힘 |
| **C** | 중앙 대칭 | **비교·교집합**. 대칭이라야 의미가 산다 |
| **A** | 비대칭 대형(씬 58%) | 임팩트가 필요한 장 |
| **F** | 전면(full-bleed) | 분위기·규모 |
| **T** | 3분할(텍스트/씬/리스트) | 항목 나열. `items=[(제목,설명)]` 최대 3 |

### 실무 3종

| 코드 | 구도 | 전용 메서드 |
|---|---|---|
| **COVER** | 표지 — **크롬 없음** | `d.cover(eyebrow, head, sub, issuer, meta, scene)` |
| **AGENDA** | 목차 — 번호+제목+구분선 | `d.agenda([항목...], scene=)` 최대 6 |
| **CLOSING** | 클로징 — 중앙 엠블럼 | `d.closing(head, issuer=, scene=)` |

**연속 3장 이상 같은 구도 금지.** L→W→S→C→A 처럼 교차한다.
씬 비율은 `deck.py`가 자동 결정한다 — W/F는 `16:9 wide`, 나머지 `4:3 landscape`.


## 9. 수정 인터페이스 — `revise.py`

```python
from revise import Deck, apply_command
d = Deck.load("spec.json")
apply_command(d, "3번 헤드라인을 새 제목 로")   # 자연어
d.lay(2, "W"); d.scene(4, "저울 비교")          # API
print(d.plan())   # 무엇이 재생성되는지 미리보기
```

**TEXT 수정**(헤드라인·서브·구도·순서·색·폰트)은 재생성 없이 조립만 — 수초.
**SCENE 수정**(씬 내용·라벨·도메인)만 해당 장을 재생성 — 철칙 E를 코드로 강제.

### 지원하는 자연어 명령

| 명령 예시 | 분류 | 효과 |
|---|---|---|
| `3번 헤드라인을 새 제목 로` | TEXT | 헤드라인 교체 (`/`로 줄 분리) |
| `2번 서브를 부연 설명 로` | TEXT | 서브 교체 |
| `2번 구도를 W로` / `2번을 W 구도로` | TEXT | 구도 변경 (양쪽 어순 지원) |
| `5번을 2번으로 이동` | TEXT | 순서 변경 |
| `색을 navy로` / `폰트를 gmarket으로` | TEXT | 전체 팔레트·서체 |
| `1번 씬 다시` / `3번 씬 재생성` | SCENE | **프롬프트 유지하고 다시 뽑기** |

씬 내용을 바꾸려면 API를 쓴다: `d.scene(4, "저울 비교")`.
`d.scene(4)`처럼 본문을 생략하면 기존 프롬프트로 재생성한다.

⚠️ 슬라이드 번호는 **고정 ID(`_sid`)** 기준이다. `move()`로 순서를 바꿔도
"3번"은 계속 같은 슬라이드를 가리킨다. (순서 기준이면 move 뒤 명령이 엉뚱한 장에 적용됨 — 실측 버그)

## 10. 사용자 실사진 — `photos.py`

```python
from photos import plan, prep, prompt_block
ready = prep(paths, "photos_ready")        # 리사이즈 + (옵션)얼굴 블러
pl = plan(ready)                            # 성격 판정 + 배치 결정
prompt = style_block(dom) + body + prompt_block(pl, labels)
job = {"refs": ready, "prompt": prompt}    # ★ refs로 codex에 전달
```

**철칙 D**: 코드 후합성 금지. `refs`로 넘겨 codex가 씬 안에서 함께 그리게 한다.
그래야 사진이 3D 프레임에 담기고 조명·그림자·팔레트가 씬과 일치한다.

| 장수 | 모드 | 배치 |
|---|---|---|
| 1 | hero | L/A 구도, 씬 중심 |
| 2 | compare | S/C 구도, 좌우 대칭 |
| 3 | sequence | W 구도, 가로 흐름 + 화살표 |
| 4 | grid | F/T 구도, 2×2 격자 |

얼굴이 검출되면 개인정보 지시가 자동 삽입된다.

## 11. 성능 (2026-08-01 실측)

동일 파이프라인에서 최적화 전후를 측정한 값이다.

| 실행 | 장수 | 소요 | 장당 |
|---|---|---|---|
| 최적화 **전** | 9장 | 397초 (6.6분) | 44.1초 |
| 최적화 **후** | 10장 | 343초 (5.7분) | **34.3초** |

**장당 22% 단축.** effort high 유지 — 품질 타협 없음.

개선 3건:
- 적응형 폴링 — 고정 3초 → 0.6/1.5/3초 (초반 촘촘히 회수)
- 캐시 확보 후 `__out.png` 대기 45초 → 12초
- 동시성 자동화 — `--cap` 생략 시 `min(잡수, 코어//2, 10)`

⚠️ 자동 cap은 `all_jobs` 로드 **뒤에** 계산해야 한다.
앞에 두면 `args.cap=0`이 그대로 `ThreadPoolExecutor(max_workers=0)`로 가서
`ValueError`로 즉시 죽는다(실측 버그).


## 12. 강조 요소 사용법 (2026-08-01)

슬라이드 스펙에 필드를 넣으면 **자동으로 렌더된다.** 별도 호출 불필요.

```python
{"lay": "L", "head": [...], "sub": [...],
 "num":   ["2,800", "회", "연간 커밋"],        # 대형 수치 + 단위 + 캡션
 "chips": ["키워드1", "키워드2", "키워드3"],      # 키워드 칩
 "items": [("경영 진단", "사업성 분석"), ...]}   # T 구도 전용 리스트(최대 3)
```

| 필드 | 렌더 | 지원 구도 |
|---|---|---|
| `num` | 대형 수치(hero색) + 단위 + 회색 캡션 | L S W A |
| `chips` | 라운드 칩, 배경은 hero에서 자동 파생 | L S W A |
| `items` | 우측 카드 리스트 | T |

칩 배경색은 `_pale()`이 hero 색에서 계산하므로 도메인을 바꿔도 자동으로 어울린다.

⚠️ `lay_W`는 씬 영역을 **고정하지 않는다.** 텍스트+강조가 실제로 차지한 높이 아래
`BODY_BOT`까지 남은 공간을 전부 쓴다. 고정값(`H*0.40`)이면 텍스트가 짧을 때
상단이 비고 씬이 하단으로 쏠린다(실측 수정).


## 13. ★ 단일 진입점 — `deck.py` (여기서 시작하라)

덱 하나를 만들 때 `build.py`를 새로 쓰지 마라. `Deck` 클래스가 전부 처리한다.

```python
import sys, os
sys.path.insert(0, os.path.join(SKILL_DIR, "scripts", "scene-deck"))
from deck import Deck

d = Deck(domain="교육", foot="OO아카데미", title="교육사업_소개")

d.slide("L", "THE PROBLEM", ["배우고 나면", "잊어버립니다"],
        ["일회성 특강은 현장에 남지 않는다"],
        scene="a lone lecture podium on an isolated platform, knowledge particles drifting away",
        labels=["1회성 특강"])

d.slide("W", "OUR PROGRAM", ["4단계로 정착시킵니다"], ["진단 · 학습 · 실습 · 코칭"],
        scene="four rounded pedestals in a row carrying a clipboard, a book, a workbench, a speech bubble",
        labels=["진단", "학습", "실습", "코칭"])

d.slide("L", "TRACK RECORD", ["숫자로", "증명합니다"], ["수료 후 현장 적용률"],
        scene="a tall stack of layered plates with a graduation cap at the summit",
        num=["1,240", "명", "누적 수료"], chips=["현장 적용 82%", "재수강 3회+"])

d.photos(["a.jpg","b.jpg","c.jpg"], "ON SITE", ["현장에서 함께합니다"], ["3회차 밀착"])

d.summary()      # 구성 미리보기
d.generate()     # 씬 생성 (이미 있으면 생략 — 철칙 E)
d.build()        # 조립 + PDF
```

`Deck`이 자동으로 처리하는 것:

| 항목 | 동작 |
|---|---|
| 팔레트·폰트 | `domain`에서 프리셋 적용 |
| 씬 비율 | W/F는 `16:9 wide`, 나머지 `4:3 landscape` |
| SAFE ZONE·PIL금지 지시 | 모든 프롬프트에 자동 삽입 |
| 사진 | `photos()`가 성격 판정 → 구도 자동 선택 → refs 전달 |
| 재생성 | 이미 있는 씬은 건너뜀 |
| 저장 | `build()` 시 `spec.json` 기록 → `revise.py`로 수정 가능 |

**수정은 재생성하지 말고** `Deck.load("spec.json")` 후 `revise.py`를 쓴다.


## 14. 텍스트 오버플로우 방어 (2026-08-01)

긴 헤드라인·서브가 들어와도 화면을 넘지 않는다. `typo()`가 자동 처리한다.

1. **어절 단위 줄바꿈** — 공백 기준. 한 어절이 폭을 넘으면 그 어절만 글자 단위로 자른다.
2. **폰트 자동 축소** — 3줄을 넘으면 6px씩 줄인다. 하한은 원래 크기의 62%.
3. **구도별 텍스트 폭** — 씬이 옆에 있으면 그만큼 좁힌다.

| 구도 | 텍스트 최대 폭 |
|---|---|
| L | 50% |
| S | 42% |
| A | 36% (씬이 가장 큼) |
| T | 30% (중앙 씬 + 우측 리스트) |
| C | 78% (중앙 정렬) |
| W/F | 전폭 |

⚠️ `lay_C`는 반드시 `typo()`를 써야 한다. 자체 렌더하면 이 보호가 빠져
중앙 정렬 긴 제목이 좌우로 넘친다(실측 버그).

스트레스 8케이스(긴헤드라인/긴서브/칩6개/중앙긴제목/W·S·A 긴제목/T항목5개)
전건 통과 — 우측 여백·하단 크롬 침범 0건.


## 15. QC 게이트 정합 (2026-08-01)

`deck_qc.py`는 씬덱 규격과 **같은 여백 상수**를 쓴다.

```python
SCENE_DECK_MARGIN = 0.030          # layout_engine.M = W * 0.030
RIGHT_LIMIT = 1.0 - 0.030 + 0.004  # 0.974
LEFT_LIMIT  = 0.030 - 0.004        # 0.026
```

예전 `LEFT_LIMIT 0.035`는 하네스 여백(0.030)보다 넓어 **설계값에 정확히 맞은
슬라이드를 FAIL로 찍었다**(실측 좌 0.031). 안티에일리어싱 여유 0.004만 준다.

### 우측 배치는 `place_right()`를 쓴다

`trim()`으로 흰 여백을 걷어낸 씬은 콘텐츠가 가장자리에 딱 붙는다.
그대로 우변에 맞추면 안티에일리어싱 픽셀이 여백선을 넘는다(실측 우 0.990).

```python
place_right(im, sc, W - M, top)    # 콘텐츠 폭의 1.2%를 패딩으로 확보
```

L·A 구도가 이 함수를 쓴다. C·F·T는 중앙 정렬이라 해당 없음.

**실행**: `python deck_qc.py <슬라이드폴더> --cover none`
검증 덱 5종(유통3·교육3·갭3·식음료5·의료5) 전건 PASS.


## 16. 실무 덱 구조 — 표지·목차·클로징 (2026-08-01)

기준 덱은 **표지 → 목차 → 본문 → 클로징** 구조다.
본문 구도만으로는 납품 덱이 되지 않는다.

```python
d = Deck(domain="제조", foot="OO정밀", title="스마트공장_제안")

d.cover("SMART FACTORY PROPOSAL",
        ["사람이 못 보는 불량을", "기계가 잡습니다"],
        ["설비 데이터 기반 실시간 품질 검사"],
        issuer="(주)OO정밀",
        meta=["제조혁신 컨설팅 · 2026", "사업자등록 000-00-00000"],
        scene="a precision inspection module scanning a metal part")

d.agenda(["현황 진단", "불량 발생 구조", "검사 자동화 설계", "도입 로드맵"],
         scene="four stacked document plates with a gear on top")

d.slide("L", ...)      # 본문
d.slide("W", ...)

d.closing(["함께 만드는 무결점 라인"], issuer="(주)OO정밀",
          scene="two robotic arms clasping like a handshake")
```

| 구도 | 특징 |
|---|---|
| `COVER` | **크롬 없음**(쪽번호·푸터 미표시). eyebrow → display 헤드 → 서브 → issuer → meta |
| `AGENDA` | 번호 + 제목 + 구분선, 우측 씬. 최대 6항목. eyebrow는 크롬이 그리므로 본문에서 생략 |
| `CLOSING` | 중앙 엠블럼 씬 + 중앙 정렬 헤드 + issuer |

표지는 `_nochrome: True`가 붙어 `build()`가 크롬을 건너뛴다.
QC 실행 시 표지는 `--cover 01`로 여백 검사에서 제외한다.


## 17. 출력 포맷 · 실패 가시화 (2026-08-01)

### PPTX 출력

```python
d.build(pdf=True, pptx=True)     # 둘 다
d.pptx()                          # PPTX만
```

슬라이드 전면에 PNG를 까는 방식이라 텍스트 편집은 안 되지만,
**발표 도구(슬라이드쇼·발표자 노트·인쇄 배포)를 그대로 쓸 수 있다.**
고객이 "PPT 파일로 달라"고 할 때 필요하다. 16:9(13.333×7.5in) 고정.

`python-pptx`가 없으면 안내만 출력하고 넘어간다(빌드는 중단되지 않는다).

### 실패를 조용히 넘기지 않는다

씬이 없으면 텍스트만 렌더되고 **겉보기엔 정상 종료**한다.
그대로 납품하면 빈 슬라이드가 섞인다. 두 지점에서 경고한다.

```
[생성] 6장 (effort=high)
  ⚠ 생성 실패 1장: s04 — 다시 generate() 하면 실패분만 재시도한다

[조립] 6장 (도메인=manufacturing 폰트=paperlogy)
  ⚠ 씬 누락 1장 — 텍스트만 렌더됨: 04(s04)
    → d.generate() 로 재생성하라
```

판정 기준은 **씬 파일 존재 + 100KB 초과**다(PIL 드로잉 산출물은 보통 50KB 미만이라
크기로도 걸러진다). 정상 덱에서는 아무 경고도 나오지 않는다.


## 18. 수정 워크플로우 연동 (2026-08-01)

`Deck`과 `revise`가 이어진다. 덱을 다시 만들지 말고 고쳐 쓴다.

```python
d = Deck.load("deck_out/spec.json")
r = d.revise()                                  # revise.Deck 핸들
apply_command(r, "3번 헤드라인을 새 제목 로")     # 자연어
apply_command(r, "5번을 A 구도로")
r.scene(4, "a redesigned four-step line")       # 씬 교체
print(r.plan())                                  # 재생성 대상 미리보기
r.save()                                         # spec.json 갱신

Deck.load("deck_out/spec.json").generate().build()   # 바뀐 씬만 재생성
```

실측: 텍스트 수정 2건 + 씬 교체 1건 → **"조립만 2건 / 씬 재생성 1장(s04)"**
으로 정확히 분리. 전면 재생성(6장 540초) 대신 95초.

### 표지 수직 정렬

`lay_COVER`는 텍스트 블록 높이를 **먼저 계산해 세로 중앙**에 놓는다.
고정 y(0.26)를 쓰면 짧은 표지에서 하단이 크게 비고 상단으로 쏠린다(실측 수정).
검증: 텍스트 세로 범위 0.292~0.703, 중심 0.498.


## 19. 공개 저장소 동기화

스킬 원본을 `Dayoooun/ppt-editorial`(public)에 반영할 때 **`cp`를 직접 쓰지 마라.**

```bash
cd ~/.pdftool/ppt_repo
python scripts/sync_from_skill.py --dry   # 무엇이 바뀌는지
python scripts/sync_from_skill.py         # 복사 + 익명화 + 검사
git add -A && git commit && git push
```

`sync_from_skill.py`가 하는 일:
1. 12개 파일쌍을 md5 비교해 **변경분만** 복사
2. **복사 직후 익명화**(`anonymize_check --fix`) — 이 순서가 핵심
3. `anonymize_check` + `doc_consistency` 검사 실행

⚠️ 복사와 익명화를 따로 하면 **반드시 잊는다.** 실측으로 같은 사고가 2번 났다.
두 번째는 `doc_consistency.py`를 푸시하던 중 README를 복사하자마자 익명화가
풀려 고객 실명이 들어갔고, pre-push 훅이 막았다.

`.git/hooks/pre-push`가 두 검사를 순차 실행하므로 잊어도 푸시는 차단된다.


## 20. 디스크 — `.cxwork` 격리 홈

`codex_parallel_gen.py`는 잡마다 `.cxwork/<잡ID>_<시도>/`에 격리 홈을 만든다.
`CODEX_HOME`을 여기로 잡아 잡끼리 상태가 섞이지 않게 하는 장치다.

**덱 하나당 300~700MB**가 쌓인다. 생성 시작 시와 종료 시 자동으로 지운다.

```bash
# 디버깅으로 남기고 싶을 때
python codex_parallel_gen.py jobs.json --keep-work
```

### 왜 한때 안 지워졌나 (2026-08-02 실측)

`shutil.rmtree`가 `WinError 5`로 실패했다. 292건 전부
`.codexhome/.tmp/marketplace` 하위 — **codex가 마켓플레이스 캐시를 읽기 전용으로 만든다.**

```python
def _force(fn, path, exc):
    os.chmod(path, stat.S_IWRITE)
    fn(path)
shutil.rmtree(work, onerror=_force)
```

⚠️ 처음엔 "taskkill 후 핸들 점유"로 판단해 재시도 4회를 넣었다. 증상만 가려졌다.
`onerror`로 실제 예외를 찍고 나서야 원인이 파일 속성임이 드러났다.

누적분이 있다면(구버전으로 생성한 덱) 이렇게 회수한다:

```python
import shutil, os, stat, glob
def force(fn, path, exc):
    try: os.chmod(path, stat.S_IWRITE); fn(path)
    except OSError: pass
for d in glob.glob("**/.cxwork", recursive=True):
    shutil.rmtree(d, onerror=force)
```
