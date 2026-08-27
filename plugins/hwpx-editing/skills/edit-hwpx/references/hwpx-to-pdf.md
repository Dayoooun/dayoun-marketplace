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

## 7. 빌드 → 검증 → 변환 순서

```bash
SKILL="$HOME/.claude/skills/consulting-report"
PY="$SKILL/.venv/bin/python"
CO="…/06.(2차)신디필라테스스튜디오_신은미_교육(필라테스)"

# ① HWPX 무결성 검증 (표·그림 treatAsChar, 매니페스트, 도너 잔존 …)
"$PY" ~/dev/dayoun-marketplace/plugins/hwpx-editing/skills/edit-hwpx/scripts/hwpx_verify.py \
      "$CO/2회차_방문후_제출서류_신디필라테스.hwpx"

# ② PDF 변환
"$PY" "$SKILL/scripts/hwpx2pdf_mac.py" "$CO"

# ③ 렌더 육안 확인 (체크박스·서명·사진)
"$PY" -c "import pymupdf; pymupdf.open('$CO/2회차_방문후_제출서류_신디필라테스.pdf')[0].get_pixmap(dpi=110).save('/tmp/chk.png')"
```

**검증(①)을 건너뛰지 않는다.** 표 앵커가 틀리면 PDF 에서 내용이 잘리거나
서명이 엉뚱한 칸에 찍힌다. 상세는 `references/hwpx-structure.md` §10.
