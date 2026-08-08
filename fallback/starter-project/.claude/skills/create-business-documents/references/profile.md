# 프로필·이력서 모듈

## 입력 스키마

- `style`: `clean`, `sidebar`, `editorial`
- `name`, `headline`, `summary`
- `contact`: `phone`, `email`, `location`
- `photo_path`: 사용자가 제공한 사진 경로
- `career`: `org`, `role`, `period`, `description` 배열
- `edu`: `org`, `detail`, `period`, `description` 배열
- `cert`: 문자열 또는 항목 객체 배열
- `skills`: 문자열 또는 항목 객체 배열

본문 순서는 `summary → career → edu → cert → skills`로 고정합니다. 값이 없는 section은 제목까지 생략합니다. 사진을 새로 만들지 않으며, 사용자 경로가 없거나 열 수 없으면 빈 사진 프레임을 유지합니다.

나이, 성별, 결혼 여부, 주민등록번호는 입력 스키마에 두지 않고 렌더링하지 않습니다. 사용자가 준 성과를 부풀리거나 고용기관·수치·기간을 만들지 않습니다. 경력 공백을 숨기거나 날짜를 바꾸지 않습니다. 확인되지 않은 항목은 placeholder로 남깁니다.
