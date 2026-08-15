"""ppt-hybrid — salvage_cache.py
codex no-output 플레이키 회수: 라이브/잔존 .cxwork의 격리홈 캐시(generated_images)에서
생성본을 찾아 theme.json 매핑대로 backgrounds/assets에 채운다 (이미 있으면 스킵).
사용: python scripts/salvage_cache.py
"""
import glob
import json
import os
import shutil


def main():
    """.cxwork 격리홈 캐시에서 생성본을 회수한다.

    ★ import만으로 실행되던 톱레벨 코드를 main()으로 감쌌다.
      스모크 테스트가 이 스크립트를 import하자 '회수: 0'을 출력했고,
      부작용 없이 import되어야 검증에 쓸 수 있다.
    """
    salvaged = []
    for tdir in glob.glob("themes/*/"):
        theme = os.path.basename(os.path.normpath(tdir))
        tj = os.path.join(tdir, "theme.json")
        if not os.path.exists(tj):
            continue
        meta = json.load(open(tj, encoding="utf-8"))
        outmap = {}
        for _, rel in list(meta.get("backgrounds", {}).items()) + list(meta.get("assets", {}).items()):
            outmap[os.path.splitext(os.path.basename(rel))[0]] = os.path.join(tdir, rel)
        for work in glob.glob(os.path.join(tdir, ".cxwork", "*")):
            slug = os.path.basename(work).rsplit("_", 1)[0]
            dest = outmap.get(slug)
            if not dest or os.path.exists(dest):
                continue
            cache = glob.glob(os.path.join(work, ".codexhome", "generated_images", "**", "*.png"), recursive=True)
            if not cache:
                continue
            src = max(cache, key=os.path.getmtime)
            if os.path.getsize(src) < 100_000:  # 미완성/깨진 파일 배제
                continue
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy(src, dest)
            salvaged.append(f"{theme}/{slug} <- {os.path.getsize(src)//1024}KB")

    print("회수:", len(salvaged))
    for s in salvaged:
        print(" ", s)


if __name__ == "__main__":
    main()
