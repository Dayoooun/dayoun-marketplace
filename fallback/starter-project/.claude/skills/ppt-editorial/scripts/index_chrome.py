# -*- coding: utf-8 -*-
"""상단 인덱스(탭) 크롬 — 프로파일별 스타일로 PIL 일괄 합성 (2026-07-21)

배경: 탭을 이미지 모델이 그리면 장마다 모양·위치·룰 길이가 흔들림(에코에듀 덱 실측:
10장 중 4종 변형). 로고·쪽번호와 마찬가지로 탭도 '고정 크롬' → 코드 합성이 정답.

사용:
    from index_chrome import IndexChrome
    ic = IndexChrome(style="folder-tab", accent=(47,107,63))
    ic.apply(src_png, out_png, label="문제 정의")   # 표지는 label=None로 스킵

스타일(컨셉별):
    folder-tab   : 모던플랫(Toss) — 사선 폴더탭 + 우측 끝까지 헤어라인
    eyebrow-rule : 에디토리얼 — 작은 라벨 + 얇은 룰 (박스 없음)
    number-dash  : 미니멀 — "02 — 라벨" 텍스트만
프롬프트 쪽 대응: 모델에는 "상단 좌측에 탭/인덱스를 그리지 말고 상단 스트립을 비워라"
(DO NOT draw any tab/index label at the top; leave the top strip empty) 지시.
기존 덱 보정: cover=True면 상단 스트립을 배경색으로 덮고 다시 그림(모델이 그린 탭 제거).
"""
from PIL import Image, ImageDraw, ImageFont
import os

FONT_KR = r"C:\Windows\Fonts\malgun.ttf"
FONT_KR_BOLD = r"C:\Windows\Fonts\malgunbd.ttf"


class IndexChrome:
    def __init__(self, style="folder-tab", accent=(47, 107, 63), font=None):
        self.style = style
        self.accent = tuple(accent)
        self.font_path = font or (FONT_KR_BOLD if style == "folder-tab" else FONT_KR)

    @staticmethod
    def _tracked(d, xy, text, font, fill, track):
        """자간(letter-spacing)을 준 텍스트 렌더 — 모델이 장마다 다르게 그리는 것을 코드로 통일."""
        x, y = xy
        for ch in text:
            d.text((x, y), ch, font=font, fill=fill)
            x += d.textlength(ch, font=font) + track
        return x

    def _bg_color(self, im, band_h):
        # 상단 스트립 좌우 끝 픽셀 중앙값 = 배경색 (페이퍼톤 슬라이드 전제)
        px = [im.getpixel((x, y)) for x in (5, im.width - 6) for y in range(3, band_h, 7)]
        px.sort()
        return px[len(px) // 2]

    def apply(self, src, out, label, page=None, cover=False):
        im = Image.open(src).convert("RGB")
        W, H = im.size
        d = ImageDraw.Draw(im)
        band_h = int(H * 0.105)          # 상단 스트립(탭 영역)
        if cover:
            d.rectangle([0, 0, W, band_h], fill=self._bg_color(im, band_h))
        if label:
            fs = max(18, int(H * 0.028))
            font = ImageFont.truetype(self.font_path, fs)
            x0 = int(W * 0.045)
            yt = int(H * 0.038)           # 탭 상단
            yb = yt + int(fs * 1.9)       # 탭 하단(=헤어라인 y)
            lw = max(2, H // 480)
            tw = d.textlength(label, font=font)

            if self.style == "folder-tab":
                xt = x0 + int(tw) + int(fs * 1.4)      # 탭 우상단
                s = int(fs * 1.1)                      # 사선 폭
                d.line([(x0, yb), (x0, yt), (xt, yt), (xt + s, yb)],
                       fill=self.accent, width=lw, joint="curve")
                d.line([(xt + s, yb), (W - int(W * 0.04), yb)], fill=self.accent, width=max(1, lw - 1))
                d.text((x0 + int(fs * 0.7), yt + int(fs * 0.35)), label, font=font, fill=self.accent)
            elif self.style == "eyebrow-rule":
                # 영문 아이브로우: 넓은 자간으로 전 슬라이드 균일 (크리틱 지적 — 자간 3종 혼재)
                self._tracked(d, (x0, yt), label, font, self.accent, max(2, int(fs * 0.22)))
            elif self.style == "eyebrow-only":
                self._tracked(d, (x0, yt), label, font, self.accent, max(2, int(fs * 0.22)))
            elif self.style == "number-dash":
                txt = f"{page}  —  {label}" if page else label
                d.text((x0, yt), txt, font=font, fill=self.accent)
        if page and self.style != "number-dash":
            f2 = ImageFont.truetype(self.font_path, max(16, int(H * 0.022)))
            d.text((W - int(W * 0.055), H - int(H * 0.06)), page, font=f2, fill=self.accent)
        im.save(out, optimize=True)
        return out


if __name__ == "__main__":
    import sys, json
    # python index_chrome.py plan.json  → [{"src","out","label","page"}] + {"style","accent"}
    conf = json.load(open(sys.argv[1], encoding="utf-8"))
    ic = IndexChrome(style=conf.get("style", "folder-tab"), accent=conf.get("accent", (47, 107, 63)))
    for j in conf["slides"]:
        ic.apply(j["src"], j["out"], j.get("label"), j.get("page"), cover=conf.get("cover", False))
        print("OK", j["out"])
