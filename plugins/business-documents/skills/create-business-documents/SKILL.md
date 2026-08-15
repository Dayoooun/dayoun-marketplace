---
name: create-business-documents
description: 사용자 사실을 바탕으로 견적서, 프로필·이력서, 공문·안내문을 A4 HTML로 만듭니다.
---

# 실무 문서 만들기

이 스킬은 **사업계획서 10단계의 일부가 아닙니다.** 독립 `business-documents` 플러그인으로만 설치·버전·릴리스하며 `business-plan-writer`나 기본 강의 배포판에서 호출·복제하지 않습니다. 승인된 사업정보를 견적서·프로필·공문으로 정리할 때 사용하고, 강의 커리큘럼에는 포함하지 않습니다.

## 모듈 선택

| 요청 | kind | style | 상세 규칙 |
|---|---|---|---|
| 견적서 | `quote` | `clean`, `office`, `brand` | `references/quote.md` |
| 프로필·이력서 | `profile` | `clean`, `sidebar`, `editorial` | `references/profile.md` |
| 공문 | `official` | 생략 또는 `official` | `references/official-notice.md` |
| 안내문 | `notice` | 생략 또는 `notice` | `references/official-notice.md` |
| 게시용 안내 | `poster` | 생략 또는 `poster` | `references/official-notice.md` |

공문·안내문 모듈은 `kind`가 서식을 직접 고릅니다. `clean` 같은 다른 모듈의 style을 섞지 않습니다.

## 작업 순서

1. 사용자 요청에 맞는 모듈을 하나 고릅니다.
2. 해당 reference의 JSON 스키마에서 사용자가 실제로 준 값만 채웁니다.
3. 필수값이 비어 있으면 누락 항목을 한 번에 묶어 질문합니다. 사용자가 모르는 값은 대괄호 placeholder로 남깁니다.
4. 이 `SKILL.md`가 있는 폴더를 기준으로 아래 스크립트를 실행합니다. 프로젝트 루트의 scripts로 해석하지 않습니다.

Windows:

```powershell
python scripts/render_cli.py --kind quote --style clean --input references/examples/quote.json --output-dir output
```

macOS/Linux:

```bash
python3 scripts/render_cli.py --kind quote --style clean --input references/examples/quote.json --output-dir output
```

5. 생성된 HTML 파일을 내려받아 브라우저에서 엽니다. 미리보기 창은 인쇄를 막을 수 있으므로 원본 파일을 직접 연 뒤 상단 **PDF로 저장 / 인쇄** 버튼을 누릅니다. Print-to-PDF는 사용자가 브라우저에서 수행하는 단계입니다.
6. 답변에는 전체 HTML을 붙이지 않고 생성 파일 경로와 확인할 placeholder만 알려줍니다.

## 공통 안전 규칙

- 기관명, 사람 이름, 금액, 연락처, 주소, 날짜, 법령을 만들지 않습니다.
- 모르는 값은 `[사업자등록번호 입력]`, `[일시 입력]`처럼 표시합니다.
- HTML·CSS를 손으로 새로 쓰지 않고 JSON을 수정한 뒤 renderer를 다시 실행합니다.
- 합계와 한글 금액을 손으로 계산하지 않습니다.
- 로고·인장·사진은 사용자가 제공한 로컬 경로만 사용하며 새로 생성하지 않습니다.
- 이미지 처리 라이브러리가 없거나 경로를 열 수 없으면 문서 유형별 placeholder를 유지합니다.
- 이 스킬의 출력은 HTML과 브라우저 Print-to-PDF뿐입니다. HWPX와 DOCX는 만들지 않습니다.
- 이모지를 쓰지 않습니다.
