# 사업계획서 검토표

| 영역 | 확인 질문 | 상태 |
|---|---|---|
| 목적 | 독자와 의사결정 목적에 맞는 문서인가 | PASS/WARN/BLOCK/NOT_REVIEWED |
| 요구사항 | 공식 필수 항목과 형식 제한을 지켰는가 | PASS/WARN/BLOCK/NOT_REVIEWED |
| 문제·고객 | 고객, 사용 상황, 문제가 구체적인가 | PASS/WARN/BLOCK/NOT_REVIEWED |
| 해결·차별 | 해결 방식이 문제와 이어지고 비교 기준이 있는가 | PASS/WARN/BLOCK/NOT_REVIEWED |
| 시장·수익 | 시장 범위, 지불 주체, 가격·비용 가정이 분명한가 | PASS/WARN/BLOCK/NOT_REVIEWED |
| 실행·팀 | 담당, 일정, 자원, 완료 기준과 팀 역량이 있는가 | PASS/WARN/BLOCK/NOT_REVIEWED |
| 재무·위험 | 수치 가정과 위험 대응이 활동 계획과 연결되는가 | PASS/WARN/BLOCK/NOT_REVIEWED |
| 사실성 | 사실, 가정, 계획을 구분하고 근거를 연결했는가 | PASS/WARN/BLOCK |
| 일관성 | 수치, 날짜, 고유명사, 단위가 문서 전체에서 같은가 | PASS/WARN/BLOCK |
| 표현 | 과장, 모호한 수식어, 지나치게 긴 문장을 줄였는가 | PASS/WARN/BLOCK |
| 문체·문단 | 종결 문체가 같고 한 문단에 하나의 핵심을 담았는가 | PASS/WARN/BLOCK |
| 서식 | 공식 양식, 번호 체계, 목록 단계, 들여쓰기가 일관되는가 | PASS/WARN/BLOCK |
| 표 | 제목, 머릿글, 단위, 기준일, 출처와 열별 표기가 분명한가 | PASS/WARN/BLOCK |
| 보안 | 개인정보와 비공개 정보를 제거하거나 가렸는가 | PASS/WARN/BLOCK |

## HWPX 검토표

| 영역 | 확인 질문 | 상태 |
|---|---|---|
| 승인 | 사용자 승인본과 치환값이 같은가 | PASS/WARN/BLOCK |
| 치환 | 양식의 대상 위치와 실제 치환 횟수가 같은가 | PASS/WARN/BLOCK |
| 누락 | 미치환 중괄호, 빈 필수값, 찾지 못한 항목이 0건인가 | PASS/WARN/BLOCK |
| 구조 | HWPX ZIP·XML 구조검사를 통과했는가 | PASS/WARN/BLOCK |
| 시각 위치 | 시각자료가 승인한 앞 문단과 뒤 문단 사이에 있는가 | PASS/WARN/BLOCK |
| 중첩표 | `tc → subList → p → run → tbl`의 1열 2행 구조인가 | PASS/WARN/BLOCK |
| 참조·쪽 설정 | 이미지 참조 3요소가 일치하고 원본 `secPr`이 보존됐는가 | PASS/WARN/BLOCK |
| 캡션 | `그림 N. 핵심 그림명` 형식, 가운데 정렬, 승인 서식인가 | PASS/WARN/BLOCK |
| 화면 | 한글에서 실제 문맥 위치·비율·해상도·표·줄바꿈·글자 겹침·페이지 넘김을 확인했는가 | PASS/WARN/BLOCK |
