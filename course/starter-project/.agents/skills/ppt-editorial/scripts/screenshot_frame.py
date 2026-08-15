# -*- coding: utf-8 -*-
"""[S] 실증 스크린샷 임베드 슬라이드 렌더러 (범용).

하이브리드 보고서용: codex가 못 그리는 실제 화면(대시보드·매출표·시트·앱 스크린샷)을
모던플랫 프레임(eyebrow+제목+라운드 카드+그림자+캡션 pill+은은한 데코)에 임베드한다.
강조색은 파라미터(브라운 고정 금지). Pretendard 폰트 우선, 없으면 Malgun 폴백.

사용:
  python screenshot_frame.py spec.json OUT_DIR --accent 503020
spec.json = [{num, tab, eyebrow, title, images:[png...], caption, layout:"one"|"two"}, ...]
또는 import 해서 render(spec, out_dir, accent=(80,48,32)).
"""
import os, sys, json
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from platform_support import default_font, find_font

FW, FH = 1920, 1080

def _font(w, s):
    name = {"xb": "Pretendard-ExtraBold.otf", "b": "Pretendard-Bold.otf",
            "bl": "Pretendard-Black.otf", "l": "Pretendard-Light.otf"}.get(
                w, "Pretendard-Bold.otf")
    bold = w in ("b", "xb", "bl")
    return ImageFont.truetype(find_font(name) or default_font(bold=bold), s)

def _rounded(img, rad):
    m = Image.new("L", img.size, 0); ImageDraw.Draw(m).rounded_rectangle([0,0,img.size[0],img.size[1]], rad, fill=255)
    out = Image.new("RGBA", img.size); out.paste(img, (0,0)); out.putalpha(m); return out

def _place(canvas, path, box, rad=16):
    x, y, w, h = box
    im = Image.open(path).convert("RGB")
    r = min(w/im.width, h/im.height); nw, nh = int(im.width*r), int(im.height*r)
    im = im.resize((nw, nh), Image.LANCZOS); px, py = x+(w-nw)//2, y+(h-nh)//2
    sh = Image.new("RGBA", canvas.size, (0,0,0,0))
    ImageDraw.Draw(sh).rounded_rectangle([px+6, py+10, px+nw+6, py+nh+10], rad, fill=(50,40,30,60))
    canvas.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)))
    b = Image.new("RGBA", canvas.size, (0,0,0,0))
    ImageDraw.Draw(b).rounded_rectangle([px-2, py-2, px+nw+2, py+nh+2], rad+2, fill=(255,255,255,255), outline=(220,214,208,255), width=2)
    canvas.alpha_composite(b)
    canvas.paste(_rounded(im, rad), (px, py), _rounded(im, rad))

def render(spec, out_dir, accent=(80,48,32)):
    os.makedirs(out_dir, exist_ok=True)
    A2 = tuple(min(255, c+55) for c in accent)   # 밝은 강조
    INK, BG, TINT = (43,43,43), (250,248,246), tuple(min(255, c+185) for c in accent)
    for s in spec:
        c = Image.new("RGBA", (FW, FH), BG+(255,)); d = ImageDraw.Draw(c)
        # decor
        o = Image.new("RGBA", c.size, (0,0,0,0)); od = ImageDraw.Draw(o)
        od.ellipse([1680,-120,2060,260], fill=accent+(20,)); od.ellipse([1780,60,1980,260], fill=accent+(14,))
        c.alpha_composite(o)
        # header
        x = 110
        d.text((x,70), s.get("tab",""), font=_font("b",20), fill=A2)
        d.text((x,104), s.get("eyebrow",""), font=_font("b",24), fill=accent)
        d.text((x,138), s["title"], font=_font("xb",54), fill=INK)
        d.line([x,214,x+60,214], fill=accent, width=4)
        # images
        imgs = s["images"]; layout = s.get("layout", "one" if len(imgs)==1 else "two")
        top, bh = 250, 700
        if layout == "one": _place(c, imgs[0], (250, top, 1420, bh))
        else:
            _place(c, imgs[0], (110, top, 850, bh)); _place(c, imgs[1], (990, top, 820, bh))
        # caption pill
        cap = s.get("caption")
        if cap:
            tw = d.textlength(cap, font=_font("b",26))
            d.rounded_rectangle([x,998,x+tw+64,1052], 27, fill=TINT)
            d.ellipse([x+22,1017,x+38,1033], fill=accent)
            d.text((x+52,1010), cap, font=_font("b",26), fill=accent)
        c.convert("RGB").save(os.path.join(out_dir, "slide_%s.png" % s["num"]))
        print("  [S] slide_%s  %s" % (s["num"], s["title"]))

if __name__ == "__main__":
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    out = sys.argv[2]
    acc = (80,48,32)
    if "--accent" in sys.argv:
        h = sys.argv[sys.argv.index("--accent")+1].lstrip("#")
        acc = tuple(int(h[i:i+2], 16) for i in (0,2,4))
    render(spec, out, acc)
    print("[S] %d장 완료 (accent=%s)" % (len(spec), acc))
