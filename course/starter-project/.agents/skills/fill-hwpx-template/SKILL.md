---
name: fill-hwpx-template
description: "승인된 내용을 원본 보존 작업용 HWPX에 반영하고, 사용자의 디자인 지시 또는 '알아서 보기 좋게' 요청에 맞춰 표·문단·시각자료·타이포·여백을 주도적으로 설계할 때 사용한다. HWP→HWPX 준비, 중괄호 치환, 의미 기반 시각자료 배치, 구조검사, PDF/PNG 화면검수까지 수행한다."
---

# HWPX 양식 안전하게 채우기

## 먼저 확인

- `.hwp`는 직접 처리하지 않는다. 한글에서 **다른 이름으로 저장 → HWPX**로 준비한다.
- 최초 원본은 보존한다. 사용자가 자동 생성본을 한글에서 수정해 다시 올리면 그 최신 업로드본을 새 `user-edited-canonical`로 잠그고, 이후 작업용 HWPX는 반드시 그 파일에서 복사한다. 과거 원본·과거 자동 생성본으로 되돌아가 재생성하지 않는다.
- `_approval.status=APPROVED`, 승인자·시각·source_draft가 모두 있는 `placeholder-values.approved.json`만 입력으로 사용한다. 승인 우회 옵션은 없다.
- 중괄호 항목이 0개면 자동 입력 성공이 아니라 BLOCK이다.
- 구조검사와 실제 렌더 검사는 서로 다른 검사이며 둘 다 필요하다. 실제 렌더러가 만든 PDF·페이지별 PNG와 전체·100%·확대 검수 기록이 없으면 BLOCK이다.
- 공식 고정 구조·고정 문구와 사용자가 지정하지 않은 문단·글자·목록·표 스타일은 유지한다. 공식 지시, 사용자 지시, 디자인 결정표가 지정한 속성만 작업용 복사본에서 변경하고 변경 속성을 로그에 남긴다.
- 시각자료가 있으면 `references/visual-design-system.md`와 승인된 `앞 문단 / 뒤 문단 / 짧은 캡션` 명세를 먼저 확인한다.
- 원본의 섹션 순서, 공식 질문·제목·안내문, 최상위 표 topology, 고정 셀 텍스트를 source integrity receipt로 잠근다. 승인된 답변 셀·치환값·디자인 삽입영역 밖의 변경은 BLOCK이다.
- 비어 있지 않은 답변 플레이스홀더는 길이와 관계없이 `o 대항목 → - 핵심항목 → · 세부내용` 개조식으로 반영한다. 식별 라벨만 `_claim_free`로 제외한다.
- filler는 답변 셀의 기준 스타일을 복제해 `o` 1,200/-1,200 굵게, `-` 2,400/-1,200 보통, `·` 3,600/-800 보통의 실제 내어쓰기를 적용한다. 공백·탭으로 모양을 만들지 않는다.
- 승인값이 산문이면 중단하지 않고 `o 핵심내용 → - 주장`으로 자동 정규화한 뒤 `AUTO_OUTLINED`와 대상 플레이스홀더를 사용자에게 알린다. `--allow-prose-values` 예외는 없다.
- 초안·승인 JSON에는 각 주장 끝에 `[E001 | 기관명, {발표연도}]`·`[U001 | 사용자 제공자료, {기록연도}]`·`[H001 | 검증가설]`·`[P001 | 실행계획]` 표지를 둔다. E/U의 `inline_citation`은 `출처명, YYYY` 형식이며 근거목록 날짜의 연도와 같아야 한다.
- 최종 HWPX에는 외부 공개자료만 `(기관명, 연도)`로 남긴다. 근거가 여러 개면 `(기관명, 연도; 기관명, 연도)`처럼 한 괄호에 묶는다.
- `[U001 | 사용자 제공자료]`·`[H001 | 검증가설]`·`[P001 | 실행계획]`은 내부 추적 표지이므로 최종 문서 본문에 노출하지 않는다. `(검증가설)`은 심사에서 사업자가 스스로 근거 없음을 선언한 것으로 읽히고, `(사용자 제공자료)`는 출처가 아니라 자기 진술이라 근거로 기능하지 않는다. 추적은 `근거목록.csv`가 문장별 ID로 보관한다.
- 주장 ID는 `--evidence-registry 근거목록.csv`로 검증한다. E/U 행에 출처명·경로 또는 URL·확인일이 없거나, 표지와 `inline_citation`이 다르면 BLOCK한다.
- 회사명·성명·날짜처럼 주장하지 않는 식별 라벨만 승인 JSON의 `_claim_free` 객체에 `"{회사명}": "회사명 식별값"`처럼 키와 사유를 명시해 제외한다.
- 주장 플레이스홀더는 한 개의 문단과 한 개의 텍스트 run을 단독 점유해야 한다. 뒤에 고정 문구가 붙거나 여러 run으로 쪼개졌으면 최종 문단 끝 표지를 보장할 수 없으므로 BLOCK한다.
- `paraProperties`, `charProperties`, `borderFills`는 ID 존재 여부뿐 아니라 XML 배열 위치·연속성·`itemCnt`까지 검사한다. 문단 스타일을 추가하면 숫자 ID 순서로 재정렬하며 `·` 본문은 LEFT, 이미지 문단만 CENTER여야 한다.
- 사용자가 삭제한 문단·시각자료·`o 근거 원문` 블록은 deletion receipt에 기록하고 명시적 복원 승인 없이 다시 만들지 않는다.
- 사용자 확정 시각자료는 table/image width, 두 셀 borderFill, 테두리, 배경, 캡션, 행 높이, 여백을 profile로 잠근다. 새 시각자료는 전역 기본값이 아니라 최신 canonical의 확정 skeleton을 복제한다.
- 최종 `Preview/PrvText.txt`는 section 본문에서 다시 만들고 정확히 대조한다. 같은 파일명을 교체하지 않고 새 버전 파일명을 사용한다.

## `알아서 보기 좋게` 실행 계약

이 요청을 받으면 색상 취향을 되묻는 것으로 시작하지 않는다. 에이전트가 원본 HWPX와
승인 문안을 분석해 디자인 권장안을 만들고, 사용자 지정이 없는 항목만 공통 기본값으로
채운다.

1. 원본의 용지·여백·머리말·꼬리말·표·문단·글자 스타일을 inventory로 기록한다.
2. 각 답변의 평가 질문, 핵심 주장, 근거, 숫자, 순서를 읽고 시각화 필요성을 판정한다.
3. 문장만으로 충분하면 시각자료를 넣지 않는다. 판단이 빨라지는 항목만 표·비교·흐름·로드맵·KPI로 바꾼다.
4. `디자인 결정표`에 정보구조, 시각자료 종류, 삽입 위치, 크기, 타이포, 색상, 근거를 기록한다.
5. 사용자가 지정한 브랜드·폰트·색·톤·참고 이미지는 고정 조건으로 적용한다. 없을 때만 중립 기본값을 쓴다.
6. 승인 문안과 디자인 결정표를 작업용 복사본에 반영하고 새 버전으로 저장한다.
7. XML·ZIP·manifest·`secPr` 검사 뒤 PDF/PNG로 렌더해 100%와 확대 화면에서 잘림, 겹침, 빈 페이지, 과밀, 낮은 대비를 확인한다.
8. 결함이 있으면 사용자에게 위치를 찾아 달라고 하지 않고 원인을 고쳐 새 버전을 다시 검사한다.

진짜로 결정이 필요한 경우만 묻는다. 공식 양식이 여러 개라 대상이 불명확하거나,
사용자 디자인 지시가 서로 충돌하거나, 승인 문안·원본·렌더러가 없을 때는 권장안과
영향을 제시하고 확인받는다. 그 외에는 분석 보고서만 남기고 멈추지 말고 결과 HWPX와
검증 기록까지 만든다.
사용자의 `알아서·전문적으로·보기 좋게` 지시는 근거 범위 안 디자인 결정을 위임한
현재 요청의 승인으로 기록한다. 같은 디자인을 적용해도 되는지 다시 묻지 않는다.
문안·공개범위·제출 승인까지 대신하지 않으며, 위임 범위 밖의 중대한 변경만 확인받는다.

## 파이프라인 위치: 8단계 HWPX 반영 + 9단계 검사

이 스킬은 사업계획서를 새로 쓰는 도구가 아니다. `review-business-plan`에서
BLOCK이 없고 사용자가 승인한 문안만 최종 제출 양식의 작업용 복사본에 옮긴다.

**진입 조건**: 승인 대상 파일·버전·승인자·시각, 승인된 치환값 또는 위치표가 있다.

**완료 조건**: 새 HWPX와 변경 로그가 있고 미치환·빈 값이 없으며, 원본 고정 구조와
패키지 구조검사 PASS, 실제 렌더러가 만든 PDF·페이지별 PNG, 전체 페이지·100%·확대
육안검수 기록 PASS가 모두 있어야 한다. 시각자료가 있으면 의미상 위치, 중첩표 계층,
이미지 참조, 캡션, 원본 `secPr` 보존도 PASS해야 한다. 렌더러나 렌더 산출물이 없으면
완료가 아니라 BLOCK이다.

**다음 단계**: PPT를 선택했다면 승인된 사업계획서 canonical 원문과 검토 결과를
`ppt-editorial`에 넘긴다. PPT는 HWPX 파일·검사기록을 요구하지 않고 발표 목적에 맞게
내용을 다시 구성한다.

## 실행 방법

### 0. 사용자 수정본을 최신 canonical로 잠그기

사용자가 한글에서 표·셀·테두리·배경·문단·캡션을 수정한 HWPX를 다시 올리면 먼저
해당 파일을 새 canonical source로 복사하고 digest·스타일·시각자료 profile·삭제 의도를
receipt에 결속한다.

```powershell
python "<이 SKILL.md가 있는 폴더>\scripts\hwpx_revision.py" lock "사용자수정본.hwpx" --canonical-output "03. 사업계획서양식\canonical\사용자수정본_v08.hwpx" --receipt "06. 검토결과\user-canonical-v08.json" --previous "07. 최종본\직전자동생성_v07.hwpx" --removed-blocks "03. 사업계획서양식\removed-blocks.approved.json"
```

후속 결과는 canonical profile과 삭제 receipt를 다시 검사한다.

```powershell
python "<이 SKILL.md가 있는 폴더>\scripts\hwpx_revision.py" validate "03. 사업계획서양식\canonical\사용자수정본_v08.hwpx" --receipt "06. 검토결과\user-canonical-v08.json" --candidate "07. 최종본\사업계획서_v09.hwpx"
```

사용자 수정본이 없으면 최초 원본을 canonical로 사용하되 `role`을 임의로
`user-edited-canonical`이라고 기록하지 않는다.

최신 user-edited canonical을 입력할 때는 이후 `fill` 명령에 같은 receipt를
`--canonical-receipt`로 전달한다. digest가 다르거나 receipt role/status가 다르면 BLOCK한다.

이 SKILL.md가 있는 폴더를 스킬 루트로 정하고 그 아래 `scripts/hwpx_placeholders.py`를 사용한다. 프로젝트 루트의 scripts로 해석하지 않는다.

Windows에서는 `python`, macOS/Linux에서는 `python3`를 사용한다.

### 1. 양식의 중괄호 항목 찾기

Windows:

```powershell
python "<이 SKILL.md가 있는 폴더>\scripts\hwpx_placeholders.py" scan "03. 사업계획서양식\작업용 HWPX\양식.hwpx" --map-out "03. 사업계획서양식\placeholder-values.draft.json"
```

macOS/Linux:

```bash
python3 "<이 SKILL.md가 있는 폴더>/scripts/hwpx_placeholders.py" scan "03. 사업계획서양식/작업용 HWPX/양식.hwpx" --map-out "03. 사업계획서양식/placeholder-values.draft.json"
```

찾은 항목이 0개면 실제 양식에 자동 입력 표시가 없는 것이다. 자동 치환을 중단하고 위치표를 만들어 사람이 반영한다.

### 2. 사용자 승인값으로 새 파일 만들기

```powershell
python "<이 SKILL.md가 있는 폴더>\scripts\hwpx_placeholders.py" fill "03. 사업계획서양식\canonical\사용자수정본_v08.hwpx" --canonical-receipt "06. 검토결과\user-canonical-v08.json" --values "03. 사업계획서양식\placeholder-values.approved.json" --evidence-registry "00. 시작하기\근거목록.csv" --output "07. 최종본\사업계획서_v09.hwpx"
```

macOS/Linux에서는 `python3`와 `/` 경로 구분자를 사용한다.

사용자 수정본이 없는 최초 실행은 `작업용 HWPX/양식.hwpx`를 입력하고
`--canonical-receipt`를 생략한다. 이후 source/style/visual 검사는 그때 선택한 동일 입력을
끝까지 `--source`로 사용한다.

### 3. 구조 다시 검사하기

```powershell
python "<이 SKILL.md가 있는 폴더>\scripts\hwpx_placeholders.py" validate "07. 최종본\사업계획서_v01.hwpx"
```

스타일 배열 순서·참조·정렬을 별도로 검사한다.

```powershell
python "<이 SKILL.md가 있는 폴더>\scripts\hwpx_style_integrity.py" validate "07. 최종본\사업계획서_v09.hwpx" --output "06. 검토결과\hwpx-style-integrity.json"
```

4. 변경 로그에서 찾지 못한 항목, 빈 값, 미치환 중괄호가 없는지 확인한다.
5. 한글에서 결과 파일을 열어 표 너비·행 높이, 문단·자동 줄 바꿈, 번호 체계·목록 단계·들여쓰기, 글자 겹침, 페이지 넘김을 직접 확인한다. 시각자료는 실제 문맥 위치, 1열 2행 중첩표, 이미지 비율·해상도, 짧고 가운데 정렬된 캡션을 함께 확인한다.
6. 오류가 있으면 원본을 덮어쓰지 말고 승인값 또는 위치표를 고친 뒤 새 버전을 만든다.

### 4. 원본 고정 구조 검사

원본의 플레이스홀더가 아닌 문단, 섹션 순서, 최상위 표 topology, `secPr`을 결과와
대조한다. 승인된 기존 답변 문단을 바꾸는 작업이면
`editable-zones.approved.json`의 `editableParagraphExact` 배열에 원본 문단 전체를
정확히 기록한다. 각 anchor는 원본에서 정확히 한 번만 일치해야 하며, 짧은 공통 단어,
부분 문자열, 중복 문단은 BLOCK이다. `사업명: {사업명}`처럼 플레이스홀더가 있는 문단도
플레이스홀더 바깥의 `사업명:` 고정 문구는 자동 보존한다.

```powershell
python "<이 SKILL.md가 있는 폴더>\scripts\hwpx_source_integrity.py" "07. 최종본\사업계획서_v09.hwpx" --source "03. 사업계획서양식\canonical\사용자수정본_v08.hwpx" --editable-spec "03. 사업계획서양식\editable-zones.approved.json" --output "06. 검토결과\hwpx-source-integrity.json"
```

editable spec이 필요 없는 빈 양식은 `--editable-spec`만 생략한다. macOS/Linux에서는
`python3`와 `/` 경로를 사용한다. 결과가 BLOCK이면 HWPX를 완료로 표시하지 않는다.

### 5. 시각자료 구조와 위치 검사

시각자료는 답변 셀 마지막에 일괄 배치하지 않는다. 승인 명세의 설명 문단 직후,
다음 항목 직전에 `tc → subList → p → run → tbl` 계층의 1열 2행 중첩표로
삽입한다. 위 행은 이미지, 아래 행은 `그림 N. 핵심 그림명` 캡션이다.

현재 결과 설정을 먼저 확인한다.

```powershell
python "<이 SKILL.md가 있는 폴더>\scripts\hwpx_visuals.py" inspect "07. 최종본\사업계획서_v01.hwpx"
```

승인된 위치 명세와 원본 HWPX를 기준으로 재현 검증한다.

```powershell
python "<이 SKILL.md가 있는 폴더>\scripts\hwpx_visuals.py" validate "07. 최종본\사업계획서_v09.hwpx" --source "03. 사업계획서양식\canonical\사용자수정본_v08.hwpx" --spec "03. 사업계획서양식\visual-placement.approved.json"
```

macOS/Linux에서는 `python3`와 `/` 경로 구분자를 사용한다. 검사는 다음을 모두
fail-closed로 확인한다.

- `앞 문단 / 뒤 문단` 사이의 의미상 위치
- `tc → subList → p → run → tbl` 계층과 1열 2행 구조
- `<img binaryItemIDRef>`·`Contents/content.hpf`·실제 `BinData` member 일치
- 짧은 캡션, 가운데 정렬, 행 높이, 배경, 이미지·캡션 셀의 borderFill ID와 canonical digest
- 원본과 결과의 `secPr` canonical digest 일치
- `--source`는 필수다. 원본 없이 `secPrPreserved`를 PASS로 만들 수 없다.
- manifest ID와 ZIP member가 중복되거나 href가 절대경로·역슬래시·`.`·`..` segment를 포함하거나 이미지가 `BinData/` 밖을 가리키면 BLOCK
- 시각표 후보 수와 승인 명세 수가 정확히 같고 캡션도 중복되지 않음
- 사용자 확정 시각자료 profile과 같은 table/image width·셀 여백·테두리·배경·캡션 설정

### 6. 실제 렌더와 확대 검수

PDF는 `scripts/export_hwpx_pdf.py`로 만든다. `rhwp` CLI가 HWPX를 직접 PDF로
변환하므로 한컴 한글 설치가 필요 없고 macOS·Linux에서도 같은 경로를 쓴다.
LibreOffice는 HWPX를 열지 못하므로 대체재가 아니다.

```bash
python scripts/export_hwpx_pdf.py "07. 최종본/사업계획서_v09.hwpx" \
  --output "06. 검토결과/render/사업계획서.pdf" \
  --baseline "03. 사업계획서양식/작업용 HWPX/원본.hwpx" \
  --report "06. 검토결과/render/overflow.json"
```

**`--baseline`에 원본 양식을 반드시 준다.** 이 스크립트는 렌더러가 stderr로
알리는 `LAYOUT_OVERFLOW`를 세어 게이트로 쓴다. 양식이 원래 갖고 있던 넘침까지
실패로 만들면 쓸 수 없으므로 원본 대비 **증가분**만 판정한다. 증가분이 0을
넘으면 exit 2로 BLOCK이다.

넘침이 늘었다면 치환값이 칸을 넘친 것이다. 플레이스홀더는 대개 표 셀 안에
있고 셀 높이는 고정이므로, 줄 수가 늘면 내용이 셀 밖으로 나간다. 실측
(2026-08-27): 데모 양식의 값 4개를 개조식으로 치환하자 넘침이 2건에서 41건이
됐고, 회사명처럼 주장이 아닌 값을 `_claim_free`로 선언해 개조식 변환에서 빼자
28건, 네 값 모두 짧은 한 줄로 바꾸자 9건이 됐다. **구조검사(`validate`·
`hwpx_source_integrity`)는 세 경우 모두 PASS였다.** 구조가 맞아도 렌더는 깨진다.

rhwp를 PATH에 두거나 `RHWP_BIN` 환경변수로 경로를 지정한다. 렌더러를 찾지
못하면 조용히 건너뛰지 않고 BLOCK한다 — 화면검수 없는 HWPX를 납품하지 않는다.

PDF를 모든 페이지 PNG와 검수 전 receipt로 바꾼다.

```powershell
python "<이 SKILL.md가 있는 폴더>/scripts/render_pdf_pages.py" "07. 최종본/사업계획서_v09.hwpx" "06. 검토결과/render/사업계획서.pdf" --output-dir "06. 검토결과/render/pages" --receipt "06. 검토결과/render-qa.json" --renderer-name rhwp --renderer-version "<rhwp -V 로 확인한 실제 버전>"
```

`render-qa.json`은 `NEEDS_REVIEW`, 각 결함 확인값 `null`, `zoomReviewed=false`로
생성된다. 전체 페이지·100%·확대 화면을 직접 확인한 뒤 각 페이지의 `clipping`,
`overlap`, `blankPage`, `lowContrast`, `orphanParagraph`, `captionSplit`을 모두
`false`, `zoomReviewed`를 `true`, 최상위 `status`를 `PASS`로 바꾼다. 결함을 발견하면
receipt를 통과시키지 말고 HWPX를 수정해 새 버전으로 다시 렌더한다.

```powershell
python "<이 SKILL.md가 있는 폴더>\scripts\verify_hwpx_render.py" "07. 최종본\사업계획서_v09.hwpx" --receipt "06. 검토결과\render-qa.json" --output "06. 검토결과\render-qa-verified.json"
```

PDF·페이지 PNG·렌더러 이름·버전·확대 검수 중 하나라도 없거나 digest가 바뀌면 BLOCK이다.

최종 파일의 미리보기 텍스트를 본문과 동기화한 새 버전을 만든 뒤 검증한다.

```powershell
python "<이 SKILL.md가 있는 폴더>\scripts\hwpx_preview_sync.py" sync "07. 최종본\사업계획서_v09.hwpx" --output "07. 최종본\사업계획서_v10.hwpx" --report "06. 검토결과\preview-sync.json"
python "<이 SKILL.md가 있는 폴더>\scripts\hwpx_preview_sync.py" validate "07. 최종본\사업계획서_v10.hwpx" --output "06. 검토결과\preview-validate.json"
```

1R 실측값과 다른 양식의 비례 조정 규칙은 `references/visual-design-system.md`를
따른다. 1R 수치를 다른 양식에 강제로 덮어쓰거나 시각자료 때문에 쪽 여백을 바꾸지 않는다.

HWP에서 HWPX로 저장하는 방법과 제한은 `references/hwp-to-hwpx.md`, 시각자료 배치·디자인·검증 기준은 `references/visual-design-system.md`를 읽는다.
