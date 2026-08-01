# 검증 기록

검증일: 2026-08-02
대상 버전: 0.4.0

## 강의 과정과 웹

- 과정 전용 테스트: 3개 통과
- 전체 프로젝트 테스트: 34개 통과
- 변경 TS/TSX 대상 ESLint: 통과
- Next.js 프로덕션 빌드: 통과
- 120분 합계: 핵심 실습 110분 + 보호 버퍼 10분
- 필수 결과물: 공백진단표, 검증·활동 기록, 멘토링 변화기록, 다음 공식 마감 실행카드
- 일반 채팅형 AI 공통, Codex·Claude Code·Antigravity 확장, Green·Yellow·Red 전환 문구와 실제 폴더명 일치 확인
- 이전 증거 ID `E-001`과 0.1.0 ZIP 링크가 새 과정에 남지 않도록 회귀 테스트 추가

빌드 중 여러 lockfile로 인한 Next.js workspace-root 경고가 표시되지만 컴파일과 TypeScript 검사는 통과했습니다. 이번 과정 변경과 무관한 저장소 설정 경고입니다.

## dayoun 플러그인

- Codex 플러그인 검증기: 통과
- Claude Code 플러그인·마켓플레이스 검증기: 경고 없이 각각 통과
- Antigravity 1.104.0: 루트 `plugin.json`, `skills/`, 워크스페이스 `.agents/skills` 구조 확인
- 6개 스킬 × 원본·`.agents`·`.claude` 3개 트리 구조 검증: 18개 모두 통과
- 공개 저장소 자동 테스트: 20개 통과
- 프로젝트 생성 모드: 프로그램프로필을 포함한 27개 템플릿 생성
- 폴더 생성 재실행: 기존 파일 보존
- `--force` 실행: 사용자 수정 파일을 PROTECTED_MODIFIED로 보호
- 정식 플러그인과 스타터의 `.agents/skills`·`.claude/skills`: 바이트 단위 자동 동기화 검사 통과
- 스타터 프로젝트: 두 프로바이더 경로에 같은 로컬 스킬 6개 포함, `.pyc` 제외
- HWPX 주석 양식 검색: 플레이스홀더 4개 확인
- 승인 JSON 치환: BLOCK 0, 미해결 0
- 치환 결과 ZIP/XML 구조검증: 통과
- 플레이스홀더 0개 자동치환: 종료코드 2로 차단
- 플레이스홀더 0개 수동 매핑 전환: 정상 허용

## 안전·일관성 규칙

- 회사 입력 F001과 검증 주장 C001을 분리하고 네 결과물에서 같은 C001 사용
- 검토 범위와 범위 내 분모를 표시하며 범위 밖 항목은 NOT_REVIEWED로 기록
- 특정 기관·날짜는 공통 기준에서 분리하고 프로그램팩으로만 선택
- HWPX는 수정 허용·실제 양식 수령·복사본 사전검증이 확인된 경우에만 선택
- 콘텐츠 검토 → 사용자 승인 → 조건부 HWPX → 산출물·한글 육안검토 순서 적용
- `NOT_RUN`을 PASS 또는 BLOCK 0으로 해석하지 않음
- 일반 양식에 중괄호가 0개이면 자동치환하지 않고 `MANUAL_MAPPING` 사용
- 오프라인 근거팩과 완성 예시는 교육용 가상자료로 명시
- 특정 제품의 `$스킬명` 호출 문법을 공통 SKILL.md에서 제거하고 자연어 스킬 호출로 통일
- Windows는 `python`, macOS/Linux는 `python3` 실행 예시를 제공
- 일반 채팅형 AI는 프롬프트·워크시트 경로로만 안내하며 파일 자동화를 동일 기능으로 표현하지 않음

Windows에서 스킬 검증기를 기본 인코딩으로 실행하면 UTF-8 한국어를 cp949로 읽어 실패하므로 `PYTHONUTF8=1`을 적용해 검증했다. 적용 후 18개 스킬이 모두 통과했다.

## 공개 경로

- 공개 원본: `https://github.com/Dayoooun/dayoun-marketplace`
- 전체 과정: `/courses/practice/12-modoo-startup-plan`
- 자료공유: `/resources`
- 공개 ZIP: `/files/dayoun-marketplace-v0.4.0.zip`
- 참가자 빠른 시작: `course/06-participant-quick-start.md`
- 멀티 프로바이더 안내: `course/07-multi-provider-guide.md`
- 설치 없는 스타터: `fallback/starter-project`
- 완성 예시: `fallback/completed-project`
- 오프라인 근거팩: `fallback/offline-evidence-pack`
