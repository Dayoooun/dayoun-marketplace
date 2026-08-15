# 공문·안내문 모듈

## kind와 style

- `official`: 공문. style은 생략하거나 `official`
- `notice`: 안내문. style은 생략하거나 `notice`
- `poster`: 게시용 안내. style은 생략하거나 `poster`

이 모듈은 kind가 서식을 직접 고릅니다. 다른 값이나 서로 다른 kind/style 조합은 오류로 중단합니다.

## 입력 스키마

- `org`, `title`, `subtitle`, `to`, `via`
- `date`: `YYYY-MM-DD`
- `body`: `text`, `children`으로 중첩한 항목 배열
- `attach`: 붙임 이름 배열
- `seal_path`: 사용자가 제공한 직인 경로
- `accent`: 선택 색상. `#`과 여섯 자리 16진수 형식이며 **style이 아닙니다.**

번호는 코드가 `1. → 가. → 1) → 가) → (1) → (가) → ① → ㉮` 순서로 붙입니다. 날짜는 `YYYY. M. D.`로 표시합니다. `끝.`은 `official`에만 자동으로 붙고 `notice`와 `poster`에는 붙지 않습니다. `attach`는 본문이 아니라 별도 붙임 block으로 렌더링합니다.

기관명·날짜·금액·연락처와 법령·규정 번호를 만들지 않습니다. 모르는 값은 `[기관명 입력]`, `[일시 입력]`처럼 남깁니다. 직인은 사용자가 제공한 파일만 사용하고, 없으면 `(직인)`을 표시합니다.
