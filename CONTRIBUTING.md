# 기여 안내

오타, 수업 흐름 개선, 새로운 평가표 예시, HWPX 호환성 개선을 환영합니다.

1. 변경 목적을 한 가지로 좁힙니다.
2. 실제 회사의 개인정보, 영업비밀, 비공개 공고문, 참가자 raw evidence는 포함하지 않습니다.
3. canonical·approval·validation 구조를 바꾸면 `contracts/` schema와 policy부터 수정합니다.
4. 스킬을 수정했다면 해당 `SKILL.md`와 참조 문서가 서로 일치하는지 확인합니다.
5. `course/`와 starter의 스킬 snapshot은 직접 수정하지 않습니다. `course-src/` 또는 plugin 원본을 바꾸고 `python scripts/generate_course.py --clean`으로 생성합니다.
6. HWPX 스크립트를 수정했다면 데모 파일의 검색·치환·구조검증을 모두 실행합니다.
7. PPT renderer·OCR을 수정했다면 승인 전 oracle, region relation, PPTX/PDF delivered-pixel negative를 실행합니다.
8. Pull Request에 변경 이유, 실행한 명령, 실제 결과와 외부 검증 BLOCK을 구분해 적습니다.

기본 검증은 `python scripts/validate_contracts.py contracts`, `python scripts/generate_course.py --check`, `python -m unittest discover -s tests -v`입니다. `scripts/build_release_artifacts.py --all --health-only`는 전체 건강검사일 뿐 target release PASS가 아닙니다.

공식 양식과 평가기준은 기관·회차마다 다를 수 있으므로 특정 기관의 비공개 자료를 범용 규칙으로 고정하지 않습니다.
