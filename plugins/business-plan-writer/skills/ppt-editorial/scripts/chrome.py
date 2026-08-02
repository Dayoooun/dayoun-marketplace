# -*- coding: utf-8 -*-
"""에디토리얼 덱 균일 크롬 합성 (재사용 모듈, 2026-07-05 실전검증).

원칙: 모델=아트만 / PIL=고정 반복요소(로고 좌상단 · 하단 푸터 · 페이지번호)를 전 슬라이드
동일 상대좌표로 1회 균일 합성. 모델이 매장 그리게 하면 글자 깨짐·장별 흔들림 발생.

사용:
    from chrome import Chrome
    ch = Chrome(logo="logo_final.png", footer="브랜드 · 부제", accent=(78,104,85))
    ch.apply("raw/slide_02.png", "final/slide_02.png", "02")
    ch.apply("raw/cover.png",    "final/slide_01.png", "01", cover=True)  # cover=베이크드 푸터 미디언 소거

config 값은 덱마다 다르니 생성자 인자로 주입. 서체는 로컬 폰트 경로.
"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

DEFAULT_SERIF = r"C:\Windows\Fonts\NotoSerifKR-VF.ttf"


class Chrome:
    def __init__(self, logo, footer, accent=(78, 104, 85), serif=DEFAULT_SERIF,
                 ink=(26, 26, 26), gray=(120, 116, 108), logo_w=0.150,
                 cover_erase=(0.040, 0.900, 0.42, 0.945)):
        self.logo = logo
        self.footer = footer
        self.accent = accent
        self.serif = serif
        self.ink = ink
        self.gray = gray
        self.logo_w = logo_w              # 로고 폭(슬라이드 폭 비율)
        self.cover_erase = cover_erase    # 표지 베이크드 푸터 소거 bbox(비율)

    @staticmethod
    def _spaced(draw, xy, text, font, fill, tracking=0):
        x, y = xy
        for ch in text:
            draw.text((x, y), ch, font=font, fill=fill)
            x += draw.textlength(ch, font=font) + tracking
        return x

    def apply(self, path, out, page_label, cover=False):
        im = Image.open(path).convert("RGB")
        W, H = im.size
        d = ImageDraw.Draw(im)

        if cover:
            # 배경(그라데이션/수묵) 위 옛 푸터 소거: 단색 덮기는 seam → 미디언 필터로 글자획만 소거
            l, t, r, b = self.cover_erase
            bx = (int(W*l), int(H*t), int(W*r), int(H*b))
            region = im.crop(bx)
            for _ in range(2):
                region = region.filter(ImageFilter.MedianFilter(size=21))
            im.paste(region, bx[:2])

        # 로고 (좌상단)
        if self.logo and os.path.exists(self.logo):
            lg = Image.open(self.logo).convert("RGBA")
            lw = int(W * self.logo_w)
            lh = int(lw * lg.height / lg.width)
            lg = lg.resize((lw, lh), Image.LANCZOS)
            im.paste(lg, (int(W*0.055), int(H*0.058)), lg)

        # 푸터 헤어라인 틱 + 텍스트 + 페이지번호
        fy = int(H * 0.935)
        d.line([(int(W*0.055), fy+int(H*0.028)), (int(W*0.055)+int(W*0.022), fy+int(H*0.028))],
               fill=self.accent, width=2)
        ff = ImageFont.truetype(self.serif, max(15, int(H*0.019)))
        self._spaced(d, (int(W*0.055), fy), self.footer, ff, self.gray, tracking=1)
        pf = ImageFont.truetype(self.serif, max(16, int(H*0.021)))
        pw = d.textlength(page_label, font=pf)
        d.text((int(W*0.945)-pw, fy-2), page_label, font=pf, fill=self.accent)

        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        im.save(out)
        return im.size
