# 참가자 사전 준비 안내

수업 48시간 전에 아래 항목을 확인합니다.

## 필수

- 개인 노트북, 충전기, 마우스
- ChatGPT 계정 로그인
- Codex를 사용할 수 있는 ChatGPT 데스크톱 앱 또는 Codex CLI
- 제공된 설치 확인용 프로젝트에서 간단한 요청 1회 성공
- 공유 가능한 회사·아이템 소개자료
- 공고문, 평가지표, 작성요령
- 원본 HWP와 한글에서 다른 이름으로 저장한 HWPX 작업본

## 보안

- 주민등록번호, 계좌번호, 신분증, 고객명단, 비공개 계약서는 넣지 않습니다.
- 고객명·회사명은 필요하면 A사, B고객처럼 마스킹합니다.
- 원본은 99_원본백업에 보관하고 수정하지 않습니다.

## 설치 확인

~~~powershell
codex --version
codex login status
codex plugin marketplace add <배포받은-dayoun-마켓플레이스-경로>
codex plugin list --marketplace dayoun --available --json
codex plugin add modoo-startup-plan@dayoun
~~~

설치가 어렵다면 수업용 프로젝트에 포함된 로컬 스킬로 전환합니다. 설치 문제로 12분 이상 수업을 중단하지 않습니다.
