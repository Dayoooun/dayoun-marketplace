# HWPX → PDF 변환 규칙

> 2026-08-27 확정. 실측 근거만 담았다. 추측 없음.
> 재단 제출본은 PDF 합본이 필수라 이 경로가 막히면 업무가 멈춘다.

## 1. 결론 — 플랫폼별 도구가 다르다

| 플랫폼 | 도구 | 명령 |
|---|---|---|
| **macOS** | **rhwp CLI** (`bin/rhwp`, 동봉) | `python scripts/hwpx2pdf_mac.py <대상>` |
| Windows | 한글 Office COM | `python scripts/hwpx2pdf.py <대상>` |

맥에서 `hwpx2pdf.py` 를 부르면 안 된다. `win32com` 은 Windows COM 바인딩이라 import 자체가 실패한다.

```bash
# 단일 파일
python scripts/hwpx2pdf_mac.py "…/2회차_방문후_제출서류_신디필라테스.hwpx"

# 업체 폴더 일괄 (00.제출·.bak·작업본·템플릿은 자동 제외)
python scripts/hwpx2pdf_mac.py "…/06.(2차)신디필라테스스튜디오_신은미_교육(필라테스)"
```

---

## 2. rhwp 를 쓰는 이유

[edwardkim/rhwp](https://github.com/edwardkim/rhwp) — Rust 기반 HWP/HWPX 파서·렌더러, MIT, ★3.7k.

- **한글 설치 불필요.** 포맷을 직접 파싱해 렌더한다
- macOS aarch64 네이티브 바이너리 제공 → `bin/rhwp` 에 동봉 (v0.8.4, 16MB)
- `export-pdf --profile print` 로 인쇄 프로파일 PDF 생성

### ★ CLI 를 쓴다 — Python 바인딩이 아니라

같은 rhwp 코어인데 **체크박스 렌더가 다르다.**

| | `<hp:checkBtn>` | 판정 |
|---|---|---|
| `rhwp-python` (PyO3) `export_pdf` | **안 그림** — 빈 네모로 나옴 | 제출 불가 |
| **`rhwp` CLI `export-pdf`** | **정상 렌더** | **채택** |

재단 제출본은 `☑ 정상영업`, `☑ 결과보고`, `☑ 다시서기 플랜` 이 필수다.
체크가 빠지면 반려된다. 편의보다 렌더 정확도가 우선이다.

---

## 3. 검증한 실패 경로 — 다시 시도하지 말 것

| 방법 | 왜 안 되나 |
|---|---|
| **CUPS 가상 프린터** | **macOS SIP 가 막는다.** `cups-files.conf` 에 `FileDevice Yes` 를 넣고 cupsd 를 재시작해도 `file://` 백엔드는 거부된다. `raw` 대기열은 "macOS에서 더 이상 지원되지 않습니다" |
| **LibreOffice** | 설치·작동은 되지만 필터가 `writer_MIZI_Hwp_97`(확장자 `hwp`)뿐. **`.hwpx` 필터가 아예 없다** (`registry/writer.xcd` 직접 확인) |
| `python-hwpx` | 한글 없이 HWPX 를 읽지만 HTML 변환 시 `<img>` 태그 **0개** — 증빙 사진 전부 소실 |
| `pyhwpx` | `Requires-Dist: pywin32` — Windows 전용 |
| 한컴 맥 AppleScript | `.sdef` 없음. `print` 이벤트는 받지만 프린터가 없으면 조용히 무시 |
| 한컴 맥 CLI | 실행 인자 없음 (바이너리 문자열 전수 조사) |
| 한컴 맥 GUI 자동화 | 대화상자까지는 열리나 저장 버튼 제어가 불안정. 화면을 점유해 사용자 작업을 방해한다 |

**LibreOffice 는 지웠다.** 되지도 않고, 된다 해도 한글 native 렌더가 아니라 제출용으로 부적합하다.

---

## 4. 설치·검증

```bash
# 바이너리 확인
$SKILL/bin/rhwp -V          # → rhwp v0.8.4

# 재설치가 필요하면 (릴리즈 교체 시)
curl -sL -o rhwp.tar.gz \
  "https://github.com/edwardkim/rhwp/releases/download/v0.8.4/rhwp-v0.8.4-macos-aarch64.tar.gz"
curl -sL "https://github.com/edwardkim/rhwp/releases/download/v0.8.4/SHA256SUMS.txt" | grep macos-aarch64
shasum -a 256 rhwp.tar.gz    # ★ 반드시 대조
tar xzf rhwp.tar.gz && xattr -dr com.apple.quarantine rhwp/
```

**격리 속성 제거 필수.** GitHub 에서 받은 바이너리는 `com.apple.quarantine` 이 붙어
실행이 무한 대기한다. LibreOffice 도 같은 이유로 "멈춘다"고 오판했었다.

---

## 5. 알려진 특성

### stdout 진단 로그

상류 rhwp 코어가 `[DEBUG_TAB_POS]` / `LAYOUT_OVERFLOW` 를 stdout 으로 쏟는다.
`hwpx2pdf_mac.py` 가 걸러내지만 CLI 를 직접 부를 때는 파이프로 거른다.

```bash
rhwp export-pdf a.hwpx -o a.pdf 2>&1 | grep -vE "DEBUG_TAB_POS|LAYOUT_OVERFLOW"
```

### 텍스트 추출과 렌더는 별개

CLI PDF 에서 `☑` 를 텍스트로 추출하면 안 잡힌다(경로로 그려서). **렌더는 정상**이다.
검증할 때 텍스트 추출만 보고 "체크가 없다"고 판단하면 안 된다 — 렌더 이미지로 확인한다.

```python
import pymupdf
doc = pymupdf.open("out.pdf")
doc[0].get_pixmap(dpi=110).save("check.png")   # 눈으로 본다
```

### 변환 제외 대상

`hwpx2pdf_mac.py` 가 자동으로 건너뛴다: `00.제출`, `000.제출`, `.bak`, `작업본`, `템플릿`, `양식`, `_tmp`

---

## 6. 실측 결과 (2026-08-27)

| 업체 | 페이지 | 크기 | 이미지 | 텍스트 |
|---|---|---|---|---|
| 신디필라테스 2회차 | 5쪽 | 26.5MB | 16개 | 2,298자 |
| 쇼미더브이알 2회차 | 3쪽 | 2.2MB | 4개 | 2,652자 |

신디는 증빙 사진 14장이 들어가 용량이 크다. 쇼미는 기존 한컴 변환본과 **페이지 수가 일치**한다.

---

## 7. 내어쓰기 — rhwp 는 `paraPr` intent 를 렌더에 반영한다 (2026-08-27)

표 셀 문단의 내어쓰기는 **한글 COM 없이 맥에서 적용된다.** 이전 기록의
"`<hh:margin>` intent 가 렌더링에서 무시됨 → 한글 COM 후처리 필수"는 오진이었다.

신디필라테스 2회차(5쪽)로 검증: paraPr 24 의 margin intent 를 0 → -2600 으로 바꾸면
p1·p2 픽스맵 md5 가 바뀌고 접힌 줄이 들여쓰기된다. 반대로 `hp:offset` 을 9종으로
스윕해도 md5 는 전부 같다(§ hwpx-structure 의 부동 개체 규칙과 동일한 결론).

### ⛔ rhwp 는 `hp:case` 만 읽는다 — `hp:default` 는 무시한다

`<hh:margin>` 은 `<hp:switch>` 안에 두 벌 있다. 어느 쪽이 유효한지 6종 변형을 렌더해
md5 로 대조했다 (경남신보 중간결과보고서, paraPr 20):

| 변형 | 렌더 |
|---|---|
| `case` 만 0 으로 | **DIFF** |
| `case` 만 -20000 으로 | **DIFF** |
| `default` 만 0 으로 | SAME |
| `default` 만 -20000 으로 | SAME |

→ **`hp:case`(`required-namespace=…/HwpUnitChar`) 만 렌더에 반영된다.**
두 분기 값이 다른 문서가 실제로 있으므로(경남신보 case=-3660 / default=-7320)
양쪽을 같은 값으로 맞춰 써야 한글과 rhwp 가 같은 결과를 낸다.

단위는 이름과 달리 HWPUNIT 그대로다. case 값을 훑으면 정확히 선형이다:

```
case=0     → 접힌 줄 x=152.5      case=-2000 → x=172.5
case=-1000 → x=162.5              case=-3660 → x=189.1
```
1pt = 100 unit.

### 접힌 줄은 그 문단 **첫 글자 x** 에 맞춘다 — 단일 intent 금지

접두사 폭이 문서·패턴마다 달라 값 하나로는 전부 어긋난다:

| 문단 | 필요한 `intent` | 문서 |
|---|---|---|
| `□ 1. …` / `○ (라벨) …` | **-1350** | 부산신보 2회차 |
| `　- …` (전각공백+대시) | **-1725** | 부산신보 2회차 |
| `   - (목표) …` (반각 3칸) | **-3086** | 경남신보 중간결과보고서 |

**1패스로는 안 된다.** 원본이 이미 intent 를 갖고 있으면 접두사 폭을 재도 그 폭 자체가
기존 intent 로 이동한 뒤의 값이다. 경남신보 paraPr 20 은 `-3660` 이 들어 있는데도
접힌 줄이 본문보다 5.7pt 더 들어가 있었다.

→ **적용 → 렌더 → 남은 오차(pt×100)만큼 intent 보정**을 오차가 허용치 안에 들 때까지
반복한다(기본 3회). `intent` 가 음수일수록 접힌 줄이 오른쪽으로 가므로, 접힌 줄이
목표보다 왼쪽이면 보정값도 음수다.

- **`left` 는 건드리지 않는다.** `intent` 단독으로 내어쓰기가 완성된다
- **`linesegarray` 를 지우지 않는다.** 지우면 `vertRelTo="PARA"` 부동 서명이 앵커 기준을
  잃고 떠오른다. rhwp 는 lineseg 가 남아 있어도 intent 를 반영한다
- 공유 paraPr 는 수정하지 않고 (원본 paraPr × 접두사 패턴) 조합마다 전용 사본을 주입한다
- **불릿 문단에만 건다.** 실무 문서 493건 스캔 기준 불릿은 `□ ○ - ● ▪ · ※ ◦` 8종.
  서술문에 걸면 접힌 줄이 첫 글자로 당겨져 오히려 어긋난다

### 측정 함정 — PDF 에 전각·반각 공백은 없다

`　- …` 의 선행 공백은 렌더 시 글자가 아니라 여백으로 흡수돼 PDF 텍스트에 남지 않는다.
그 줄의 `chars[0]` 은 이미 밀린 위치(70.79pt)로 나온다.

- ❌ 줄 시작 x 기준 → 1350 이 나오고 접힌 줄이 마커 위치에 걸린다
- ✅ **셀 좌측(페이지 내 마커 줄 최소 x)** 기준 → 1725
- rhwp 는 문단마다 별도 블록을 만들어 **블록 bbox 는 기준으로 못 쓴다**(자기 들여쓰기와 같음)
- XML 키 `('\u3000','-')` 와 측정 키 `('','-')` 가 어긋나므로 조회는 **마커만으로 폴백**한다.
  폴백이 없으면 들여쓴 불릿이 통째로 보정에서 빠진다

### 접힌 줄 판정 — 오탐 4종

보정과 검증이 같은 기준을 써야 "게이트는 통과인데 눈으로 보면 안 맞는" 상태가 없다.
네 조건을 모두 만족해야 접힌 줄이다:

| 조건 | 안 걸면 |
|---|---|
| 직전이 불릿 줄 | — |
| **번호 제목이 아닐 것** (`^\s*[(\[]?\d[.)\]]`) | 아래 ★ 참조 |
| y 간격 ≤ 글자높이 × 1.2 | 고정 pt 로는 못 쓴다. 행간이 문서마다 다르다(0 ~ 7.2pt) |
| 불릿 좌측 −1글자 ~ 본문 x +1글자 | 아래 3종이 오탐으로 잡힌다 |

- 이웃 표의 **가운데 정렬 제목** (부산신보 「증빙자료(사진 등)」 x=257.7 vs 앵커 x=70.8)
- 같은 셀의 **다음 항목 제목** (경남신보 `1.`·`2.` 번호 문단, −30.9pt)
- 좌우로 나란한 **라벨 셀** (경남신보 「이행정도」 x=56.8 vs 본문 셀 x=165.4)

**★ 번호 제목은 좌표로 못 거른다.** 비지단 결과보고서의 `2. …` 제목은 불릿 좌측에서
정확히 글자 한 칸(−10pt) 왼쪽이라 어떤 x 창을 잡아도 경계에 걸린다. 내용으로 판정한다.
단 **한 자리 번호만** 본다 — 부산신보 `16. 완납` 은 진짜 접힌 줄이고, 이 서식들의
목차는 최대 6항목이라 두 자리 번호가 제목일 일이 없다.

### 허용치 — JUSTIFY 문서는 넓힌다

기본 1.5pt. 완전히 맞은 줄은 0.00~0.08pt 로 떨어지지만 글자폭 반올림으로
1.0pt 남는 문단이 섞인다 — 8pt 본문 한 글자의 1/7 로 육안 구분이 안 되는 폭이다.

**`horizontal="JUSTIFY"` 문단이 있으면 2.0pt 로 완화한다.** 양쪽 정렬은 자간을 늘려
줄 끝을 맞추므로 접힌 줄 첫 글자 x 에 반올림이 누적된다(거제 멘토링보고서 실측 최대
1.72pt — 전 문단이 JUSTIFY). 이걸 안 넓히면 정상 렌더가 MISS 로 잡힌다.

판정은 **PDF 가 아니라 원본 HWPX 의 header.xml** 을 읽어서 한다. `--check` 는 PDF 옆의
같은 이름 `.hwpx` 를 자동으로 찾고, 없으면 기본 허용치를 쓴다.

### 폐기된 접근 (재시도 금지)

| 시도 | 결과 | 원인 |
|---|---|---|
| lineseg 에 horzsize/flags 직접 계산 | 자간 겹침 | 값이 실제 텍스트 폭과 불일치 |
| linesegarray 문서 전체 제거 | 부동 서명 부양 | 앵커 문단 lineseg 소실 |
| 단일 `intent=-2600` 일괄 적용 | 접힌 줄이 첫 글자와 안 맞음 | 접두사 폭이 패턴마다 다름 |
| 1패스 실측만 | 기존 intent 문서에서 어긋남 | 측정값이 이미 이동한 뒤의 위치 |
| 마커 필터 없이 전 문단 적용 | 서술문이 망가짐 | 본문 첫 글자를 마커로 오인 |
| 번호 제목을 x 창으로 거르기 | 못 거르거나 진짜 접힌 줄까지 제외 | 불릿 좌측 −1글자에 정확히 걸침 |
| 전 문서 동일 허용치 | JUSTIFY 문서가 MISS 로 잡힘 | 자간 조정 반올림이 최대 1.72pt |
| pyhwpx `Run('TableCellBlock')` | 맥에서 실행 불가 | 한글 COM = Windows 전용 |

---

## 8. 빌드 → 검증 → 변환 순서

```bash
SKILL="$HOME/.claude/skills/consulting-report"
PY="$SKILL/.venv/bin/python"
CO="…/06.(2차)신디필라테스스튜디오_신은미_교육(필라테스)"

# ① HWPX 무결성 검증 (표·그림 treatAsChar, 매니페스트, 도너 잔존 …)
"$PY" "$SKILL/scripts/hwpx_verify.py" \
      "$CO/2회차_방문후_제출서류_신디필라테스.hwpx"

# ② PDF 변환
"$PY" "$SKILL/scripts/hwpx2pdf_mac.py" "$CO"

# ③ 내어쓰기 게이트 — 접힌 줄이 첫 글자에 붙었는지 PDF 좌표로 대조
"$PY" "$SKILL/scripts/hanging_check.py" "$CO/2회차_방문후_제출서류_신디필라테스.pdf"

# ④ 렌더 육안 확인 (체크박스·서명·사진)
"$PY" -c "import pymupdf; pymupdf.open('$CO/2회차_방문후_제출서류_신디필라테스.pdf')[0].get_pixmap(dpi=110).save('/tmp/chk.png')"
```

**검증(①)을 건너뛰지 않는다.** 표 앵커가 틀리면 PDF 에서 내용이 잘리거나
서명이 엉뚱한 칸에 찍힌다. 상세는 `references/hwpx-structure.md` §10.
