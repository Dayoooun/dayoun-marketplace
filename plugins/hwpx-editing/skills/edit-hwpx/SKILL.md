---
name: edit-hwpx
description: HWPX(한글) 문서를 XML 수준에서 편집합니다. 부동 개체(서명·직인) 배치, 이미지 교체, 표 셀 수정, 다른 문서를 도너로 삼은 교차 빌드, 빌드 후 무결성 검증을 다룹니다. 'hwpx', '한글 문서', '서명 위치', '직인', '그림이 검게 나옴', '표 셀 편집', '도너' 키워드에 사용합니다.
---

# HWPX XML 편집

HWPX 는 ZIP + XML 이라 파이썬 표준 라이브러리만으로 편집할 수 있습니다. 다만 한글 고유의
좌표계·캐시·매니페스트 규칙을 모르면 **열리기는 하는데 화면이 깨진** 문서가 나옵니다.

이 스킬은 한컴 공식 OWPML 모델 소스(`github.com/hancom-io/hwpx-owpml-model`, Apache-2.0)와
실무 문서 43개 / `<hp:pic>` 276개 전수 실측으로 확인한 규칙만 담았습니다.

상세는 **`references/hwpx-structure.md`** 를 읽으세요. 아래는 가장 자주 사고가 나는 4가지입니다.

## 0. 그림이 틀어지거나 표가 잘리면 — **`treatAsChar`** 를 보세요

표와 그림에 각각 규칙이 있습니다. 하나로 통일하면 안 됩니다.

**표**

| 표 | 값 |
|---|---|
| 제목·헤더·업체정보 | `1` (글자처럼) — 부동이면 서명이 엉뚱한 칸으로 |
| **본문 서술(2행1열)·증빙자료** | **`0` (부동)** — 길어서 페이지를 넘겨야 함 |

**그림**

| 그림 | 값 |
|---|---|
| **표 안 사진** | **`1`** — 부동이면 셀을 벗어나 표가 깨집니다 |
| 서명·직인 | `0` — 앵커 문단 기준 자유 배치 |

실측: 표 안 사진은 정상본 9/9 전부 `1`.

부동 서명·직인은 **앵커 문단이 제목 문단(idx 0)** 이어야 합니다.
`treatAsChar=0` 이고 표 밖에 있어도 앵커가 표 안 문단이면 그 셀을 밀어내 표가 늘어납니다(§11).

 상세는 `references/hwpx-structure.md` §10.

사진 정렬은 `hp:pic` 이 아니라 **담긴 문단의 `paraPr`** 이 결정합니다.
표 앵커를 바꾸면 **서명 좌표를 다시 잡아야 합니다.**

## 1. 그림 위치는 `hp:pos` 가 결정합니다

`<hp:pic>` 안에 좌표계가 둘 있는데 역할이 다릅니다.

| 요소 | OWPML 클래스 | 언제 쓰이나 |
|---|---|---|
| `<hp:offset x y>` | `CASCOffset` (**ASC = As-Character**) | `treatAsChar="1"` (글자처럼 배치)일 때만 |
| `<hp:pos vertOffset horzOffset>` | `CPos` | `treatAsChar="0"` (부동)일 때 **유일한 결정자** |

부동 개체에서 `hp:offset` 을 아무리 고쳐도 화면은 안 움직입니다.
(검증: offset y 를 9종으로 바꿔 렌더 → md5 전부 동일)

`vertRelTo="PARA"` 는 앵커 문단이 기준입니다. **양식이 다르면 좌표를 이식하지 마세요.**
앵커 문단이 다르면 같은 값이 다른 위치를 가리킵니다.

## 2. `orgSz` 는 건드리지 않습니다

- `<hp:curSz>` = 표시 크기 → 여기만 조정
- `<hp:orgSz>` = 원본 기준 크기(예: `485040x159960`) → **수정 금지**

`orgSz` 에 픽셀값을 넣으면 배율이 26배로 튀어 그림이 페이지를 덮습니다.

이미지를 교체할 때는 **폭은 유지하고 높이만 새 이미지 비율로 재계산**합니다.

```python
cw = 기존_curSz_width
ch = round(cw * new_img_h / new_img_w)
```

## 3. 셀 좌표는 표마다 리셋됩니다

`<hp:cellAddr colAddr rowAddr>` 은 `<hp:tbl>` 마다 0부터 다시 시작합니다.
문서에 `c1 r0` 이 여러 개라 좌표로 찍으면 첫 번째 표가 걸립니다.

**좌표 대신 기존 값을 지문으로 삼아 치환하세요.**

```python
x = x.replace("<hp:t>%s</hp:t>" % esc(old), "<hp:t>%s</hp:t>" % esc(new), 1)
```

## 4. BinData 는 텍스트 치환과 무관합니다

다른 문서를 도너로 삼아 빌드할 때 **텍스트만 바꾸면 사진·서명이 도너 것으로 남습니다.**
이미지를 지웠다면 `Contents/content.hpf` 의 `<opf:item>` 도 반드시 함께 지웁니다.

매니페스트에 파일 없는 항목이 남으면 한글이 **그림 영역을 통째로 검게** 그립니다.

```python
# ✗ [^/]* 는 href="BinData/..." 의 슬래시에서 끊깁니다
re.sub(r'<opf:item id="%s"[^/]*/>' % iid, '', manifest)
# ✓
re.sub(r'<opf:item id="%s"[^>]*/>' % iid, '', manifest)
```

## Receipt-authoritative 편집 절차

직접 `hwpx_hanging.py`·`hwpx_verify.py`에 원본·출력 경로를 넘기는 것은 **권한 있는 완료
경로가 아닙니다.** 설치본의 이 스킬 루트에서 `scripts/hwpx_edit_driver.py`만 실행합니다.
각 material stage는 독립적으로 인가된 `ref`와 expected `sha256:<64-lowerhex>`을 받고,
receipt와 artifact를 verified snapshot으로 소비합니다. 이전 receipt, 인접 digest, `latest`,
프로젝트 scripts 또는 도너 파일을 자동 발견하지 않습니다.
각 stage는 typed immutable receipt를 정확히 하나만 쓰고, 저장 직후 자신의 expected SHA로
다시 소비하여 self-validation합니다. 이 검증에 실패하면 handoff를 내보내지 않습니다.

원본은 절대 덮어쓰지 않습니다. `--output-ref`는 input과 다른, 아직 존재하지 않는
프로젝트 상대 ref여야 합니다. 도너·asset·도구 source SHA도 호출자가 독립적으로 공급합니다.
`--claimed-at`은 `2026-08-31T03:26:00+09:00`처럼 offset을 포함해야 합니다. 아래의
`<...>`는 실제 ref/SHA/식별자로 각각 교체하며, SHA를 같은 mutable 경로에서 계산해
권한값으로 삼지 않습니다.

공통 인자는 모든 호출에 정확히 같습니다:
`--project-root <trusted-project-root> --receipt-store <receipt-store> --workflow-id <workflow-id>
--cycle-id <cycle-id> --attempt <attempt> --claimed-at <timestamp-with-offset>
--root-sha256 sha256:<root> --receipt-ref <new-receipt-ref> --payload-ref <new-payload-ref>`.
설치 artifact는 bundled `_contracts`와 `_dependencies`를 사용합니다. 개발 저장소에서만
명시적 trusted `--contracts-root <contracts-root>`를 추가합니다.

1. **init** — input·선택 도너·asset·요청 operation을 각각 snapshot으로 검증해
   `hwpx-edit-init-payload` receipt 하나를 씁니다.

   ```bash
   python3 "<skill-root>/scripts/hwpx_edit_driver.py" init <공통-인자> \
     --input-ref "<input.hwpx-ref>" --input-sha256 "sha256:<input>" \
     --donor-ref "<donor.hwpx-ref>" --donor-sha256 "sha256:<donor>" \
     --asset "<asset-ref>@sha256:<asset>" --operation hanging-indent \
     --parameters-json '{"markers":["□"],"rounds":3}'
   ```

   도너가 없으면 `--donor-ref`와 `--donor-sha256`을 둘 다 생략합니다. 도너가 있으면
   둘 중 하나만 주는 호출은 BLOCK입니다.

2. **operation** — init handoff의 `receiptRef`·`receiptSha256`을 그대로 expected parent로
   전달합니다. runtime은 input과 donor snapshot만 읽고 새 output을 만들며,
   `hwpx_hanging.py` source가 independently authorized `--tool-source-sha256`과 일치할 때만
   실행합니다. `hwpx-edit-operation-payload` receipt에는 input/donor snapshot과 tool binding이 남습니다.

   ```bash
   python3 "<skill-root>/scripts/hwpx_edit_driver.py" operation <새-공통-인자> \
     --init-receipt-ref "<init-receipt-ref>" --init-receipt-sha256 "sha256:<init-receipt>" \
     --output-ref "<new-output.hwpx-ref>" --tool-source-sha256 "sha256:<hwpx-hanging-source>"
   ```

3. **validation** — operation handoff의 ref/SHA를 다시 검증하고 output·donor snapshot으로
   XML, manifest, placeholder, mimetype, floating `pos`, `orgSz`/`curSz`, donor 잔존을
   검사해 `hwpx-edit-validation-payload` 하나를 씁니다. `BLOCK` receipt도 immutable
   결과이며 PASS로 바꾸거나 재사용하지 않습니다.

   ```bash
   python3 "<skill-root>/scripts/hwpx_edit_driver.py" validation <새-공통-인자> \
     --operation-receipt-ref "<operation-receipt-ref>" \
     --operation-receipt-sha256 "sha256:<operation-receipt>"
   ```

모든 성공 또는 receipt-terminal 호출의 stdout은 정확히 한 줄인 canonical
`dayoun-handoff-v1` JSON입니다. 그 `receiptRef`·`receiptSha256`을 다음 호출에만 전달하고,
진단은 stderr에서 읽습니다. 변조·stale parent·누락 expected SHA·원본과 같은 output·도구
불일치·검증 FAIL은 성공 handoff가 아닌 stable nonzero exit/BLOCK으로 fail-closed 처리합니다.

## PDF 변환

**rhwp CLI** (Rust, MIT, ★3.7k) 로 한글 없이 변환합니다. macOS aarch64 네이티브 바이너리 제공.

```bash
rhwp export-pdf input.hwpx -o output.pdf --profile print
```

- **CLI 를 쓰세요.** `rhwp-python` 바인딩은 같은 코어지만 `<hp:checkBtn>` 을 안 그립니다
- 다운로드 후 `xattr -dr com.apple.quarantine` 필수 — 안 하면 실행이 무한 대기합니다
- 상류 코어가 stdout 으로 진단 로그를 쏟습니다 → `grep -vE "DEBUG_TAB_POS|LAYOUT_OVERFLOW"`

CUPS 가상 프린터(SIP 차단)·LibreOffice(`.hwpx` 필터 없음)는 검증 후 배제했습니다.
상세는 `references/hwpx-to-pdf.md`.

## 표 셀 내어쓰기 — 한글 COM 없이 됩니다

접힌 줄이 왼쪽 끝으로 붙는 문제는 **맥에서 코드로 잡힙니다.** rhwp 는 표 셀 문단의
`paraPr` margin `intent` 를 렌더에 반영합니다. "표 셀은 intent 가 무시된다"는 통설은
오진이었습니다 (2026-08-27 실측).

내어쓰기는 위 `init`의 `--parameters-json`에 `markers`, `rounds`, 필요하면 `noMeasure`를
명시하고, 이어지는 receipt-authoritative `operation`과 `validation`으로만 실행합니다.
직접 mutable input/output CLI 호출이나 path-only `--check` 결과는 PASS 권한이 아닙니다.

**단일 intent 를 쓰면 안 됩니다.** 접힌 줄은 그 문단 **첫 글자 x** 에 맞아야 하는데
접두사 폭이 패턴마다 다릅니다 (HWPUNIT = pt × 100):

| 문단 | 필요한 `intent` | 문서 |
|---|---|---|
| `□ 1. …` / `○ (라벨) …` | **-1350** | 부산신보 2회차 |
| `　- …` (전각공백+대시) | **-1725** | 부산신보 2회차 |
| `   - (목표) …` (반각 3칸) | **-3086** | 경남신보 중간결과보고서 |

스크립트가 원본을 렌더해 실측하고, **결과를 다시 렌더해 남은 오차만큼 보정**합니다
(기본 3회). 값을 손으로 넣지 마세요. 1패스로는 원본이 이미 intent 를 가진 문서에서
틀립니다 — 경남신보 paraPr 20 은 `-3660` 이 이미 들어 있는데도 5.7pt 어긋나 있었습니다.

- **`left` 는 0 으로 둡니다.** `intent` 단독으로 완성됩니다. `left=W` 를 주면 한/글이 문단
  전체(마커 포함)를 W 만큼 밉니다 (2026-09-03 한컴 저작 원본 대조 실측)
- **`linesegarray` 는 내어쓰기를 건 문단만 지웁니다** (기본 `strip_lineseg=True`, 표·부동
  개체를 품은 문단은 제외). 안 지우면 한/글이 저장된 줄 나눔(후속 줄 `flags` 에 내어쓰기
  비트 `0x100000` 없음)을 믿어 **접힘을 0 으로 그립니다** — rhwp 는 lineseg 를 무시해 맥에서
  는 보이지 않습니다. 문서 전체를 지우면 `vertRelTo="PARA"` 부동 서명이 앵커를 잃고 떠오릅니다
- **rhwp 는 한/글의 오라클이 아닙니다.** 제출 전 렌더는 윈도우 한/글로 뽑습니다
  (`consulting-report/scripts/hwpx_cli.py pdf … --win`). `rhwp verify --check-hanging` 이 stale
  lineseg·분기 불일치를 exit 3 으로 잡습니다
- 공유 paraPr 는 수정하지 않고 (원본 paraPr × 접두사 패턴) 조합마다 전용 사본을 만듭니다
- **불릿 문단에만 겁니다.** 서술문에 걸면 접힌 줄이 첫 글자로 당겨져 오히려 어긋납니다
- **번호 제목(`2. …`)은 내용으로 거릅니다.** 불릿 좌측에서 정확히 글자 한 칸 왼쪽이라
  좌표로는 분리되지 않습니다. 단 한 자리 번호만 — `16. 완납` 은 진짜 접힌 줄입니다
- **JUSTIFY 문서는 허용치를 넓힙니다**(1.5 → 2.0pt). 양쪽 정렬은 자간을 늘려 줄 끝을
  맞추므로 접힌 줄에 반올림이 최대 1.72pt 남습니다. `--check` 가 원본 HWPX 를 읽어 자동 판정

⚠️ **rhwp 는 `<hp:switch>` 의 `hp:case`(HwpUnitChar) 만 읽고 `hp:default` 는 무시합니다.**
6종 변형 렌더 대조로 확정했습니다. 두 분기 값이 다른 문서가 실제로 있으므로
(경남신보 case=-3660 / default=-7320) 양쪽을 같은 값으로 맞춰 써야 합니다.

⚠️ 측정 함정: 전각·반각 공백은 렌더 시 여백으로 흡수돼 **PDF 텍스트에 남지 않습니다.**
기준점은 줄 시작 x 가 아니라 **셀 좌측**(페이지 내 마커 줄 최소 x)이고, 값 조회는
선행공백을 뺀 **마커만으로 폴백**해야 들여쓴 불릿이 보정에서 빠지지 않습니다.
상세는 `references/hwpx-to-pdf.md` §7.

## 하지 않는 것

- `.hwp`(구 바이너리 포맷) 편집. 이 스킬은 `.hwpx`(OWPML) 전용입니다.
