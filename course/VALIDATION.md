# 검증 기록

- 검증일: 2026-08-07
- 대상 버전: 0.8.0
- 공개 플러그인: `business-plan-writer`

## 범용성

- 신규 작성, 기존 문서 보완, 공고·평가기준 맞춤, 자율 사업계획 지원
- 지원사업, 투자·IR, 사내 검토, 대출·제안, 교육 목적 지원
- 일곱 개 기본 SKILL.md에 특정 기관명·프로그램명·전용 평가영역이 없음을 자동 검사
- 특정 프로그램 참고자료는 `draft-business-plan/references/program-profiles/`에 분리
- 공식 자료가 없으면 일반 확인 관점을 질문 목록으로만 사용하고 임의 배점을 만들지 않음
- 초보자 기본 안내에서는 내부 관리번호 대신 `알고 있는 정보`와 `확인이 필요한 내용`을 사용

## 프로바이더와 설치자료

- Codex 매니페스트·스킬 자동 검사: 통과
- 일곱 개 스킬 공식 검증기: 모두 통과
- Codex·Claude Code·Antigravity용 매니페스트 이름과 버전 일치
- 원본 스킬과 스타터의 `.agents/skills`, `.claude/skills`: 55개 파일씩 바이트 단위 일치
- 프로젝트 생성기와 스타터 프로젝트: 25개 템플릿 일치
- 공개 마켓플레이스 자동 테스트: 18개 통과

## 안전과 일관성

- 기존 사용자 파일은 일반 재실행과 `--force` 재실행 모두 덮어쓰지 않음
- UTF-8이 아닌 사용자 파일도 그대로 보존
- 사실, 가정, 앞으로 할 계획을 구분
- 숫자·고유명사·날짜·단위와 출처를 범위별로 검토
- 원본, 작업 사본, 승인본을 구분
- HWPX 데모 검색 4개, 승인값 치환, ZIP·XML 구조검사 통과
- HWPX 자동 검사와 한글 화면 확인을 별도 필수 단계로 유지
- 공식 자료 분석부터 발표자료까지 10단계가 순서대로 연결됨
- 텍스트 초안 검토와 사용자 승인 전에는 HWPX에 반영하지 않음
- 발표 덱은 HWPX 직접 변환이 아니라 승인 내용을 발표시간·평가지표에 맞춰 재구성

## 공개 경로

- 공개 원본: `https://github.com/Dayoooun/dayoun-marketplace`
- 웹 과정: `/courses/practice/12-modoo-startup-plan`
- 공개 ZIP: `/files/dayoun-marketplace-v0.8.0.zip`
- 참가자 빠른 시작: `course/06-participant-quick-start.md`
- 멀티 프로바이더 안내: `course/07-multi-provider-guide.md`
- 설치 없는 스타터: `fallback/starter-project`
