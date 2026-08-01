---
name: fill-hwpx-template
description: "한글 HWP를 HWPX로 저장하도록 안내하고, HWPX의 중괄호 플레이스홀더를 스캔해 JSON 치환표를 만든 뒤 원본을 보존한 새 HWPX 파일과 변경 로그를 생성·검증한다. 사용자가 한글 양식, HWPX 치환, 사업계획서 양식 채우기, 중괄호 항목 자동 입력을 요청할 때 사용한다."
---

# HWPX 양식 채우기

## 안전 규칙

- .hwp 파일은 직접 처리하지 않는다. 한글에서 다른 이름으로 저장하여 .hwpx로 만든다.
- 원본과 같은 경로로 출력하지 않는다.
- 정확히 발견된 중괄호 항목만 치환한다.
- 미치환 항목과 구조검증 결과를 반드시 보고한다.
- 구조검증 통과는 한글에서의 육안검수를 대신하지 않는다.

## 절차

1. 작업용 HWPX를 스캔한다.

~~~powershell
python scripts/hwpx_placeholders.py scan "03. 사업계획서양식\작업용 HWPX\양식.hwpx" --map-out "03. 사업계획서양식\placeholder-values.json"
~~~

2. placeholder-values.json의 빈 값만 검증된 내용으로 채운다.
3. 새 파일을 생성한다.

~~~powershell
python scripts/hwpx_placeholders.py fill "03. 사업계획서양식\작업용 HWPX\양식.hwpx" --values "03. 사업계획서양식\placeholder-values.json" --output "05. 작성초안\사업계획서_v01.hwpx"
~~~

4. 구조를 다시 검증한다.

~~~powershell
python scripts/hwpx_placeholders.py validate "05. 작성초안\사업계획서_v01.hwpx"
~~~

5. replacement-log.csv와 남은 플레이스홀더를 확인한다.
6. 가능하면 한글에서 열어 표, 줄바꿈, 글자 겹침, 페이지 넘김을 육안 확인한다.

HWP에서 HWPX로 저장하는 방법과 제한사항은 references/hwp-to-hwpx.md를 읽는다.
