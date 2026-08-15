# 격리된 자산

## scene_prompts.py (2026-08-01 격리)

v3 초기 스크립트. `deck.py` + `presets.py`가 전부 대체했다.

**격리 이유** — 그대로 두면 오답을 가르친다:
- `BASE_STYLE`이 하드코딩이라 도메인 프리셋(G001)을 우회한다
- CAMERA/LIGHTING/MATERIALS 정교화(G003)가 반영되지 않은 구버전이다
- README가 이 파일을 쓰라고 안내하고 있어 §14(deck.py 진입점)와 모순이었다

지금은 `presets.style_block(domain)`이 스타일 블록을 만들고
`deck.py`가 프롬프트 조립·생성·조립·출력을 전부 처리한다.
