# 보안 정책

공개 Issue에는 API 키, 개인정보, 회사 내부자료, 제출 전 사업계획서, 참가자 원자료, raw provider/OCR 로그를 첨부하지 마세요.

보안 취약점이나 민감정보 노출을 발견했다면 GitHub 저장소의 **Security → Report a vulnerability** 기능으로 비공개 제보해 주세요. 재현 방법, 영향 범위, 문제가 있는 파일 경로를 함께 알려주시면 확인에 도움이 됩니다.

이미 공개된 비밀키는 저장소에서 파일만 지워도 안전해지지 않습니다. 해당 서비스에서 키를 즉시 폐기하고 새 키를 발급한 뒤 비공개로 제보해 주세요.

승인 envelope·canonical payload·visible-text manifest·artifact·toolchain digest의 불일치, content-addressed store 우회, renderer가 승인되지 않은 경로를 읽는 문제, 검증 BLOCK을 PASS로 덮는 문제는 보안 취약점으로 다룹니다. 공개 가능한 재현 fixture에는 가상 정보만 사용하고 민감한 원본은 비공개 제보에만 첨부하세요.
