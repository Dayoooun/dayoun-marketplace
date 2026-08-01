# 출처와 증거 정책

## 우선순위

1. 정부·지자체·공공기관·법령·국가통계
2. 학술논문·표준·공식 기술문서
3. 기업 공시·공식 가격·공식 제품문서
4. 신뢰할 수 있는 산업보고서
5. 보조 근거로만 쓰는 기사·블로그·커뮤니티

## 증거원장 열

- claim_id
- section
- claim
- claim_type: 회사사실 / 외부근거 / 가정 / 향후계획
- source_name
- source_path_or_url
- page_or_location
- published_date
- accessed_date
- unit_and_base_date
- verification_status: 확인 / 확인필요 / 사용금지
- approved_wording
- notes

회사 내부 입력은 회사사실표에서 F001 계열 fact_id로 관리한다. 증거원장의 C001 계열은 외부 출처 또는 고객 근거로 검증할 주장에만 사용한다. 교육 경로의 선택 주장은 네 결과물 전체에서 C001로 고정한다.

## 작성 규칙

- 같은 수치라도 기준연도와 단위가 다르면 별도 주장으로 관리한다.
- 회사 내부 자료는 파일명과 페이지를 기록하되 공개 URL을 요구하지 않는다.
- 가정과 향후 계획은 외부 사실처럼 인용하지 않는다.
- 민감자료는 마스킹본만 사용한다.
