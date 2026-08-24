#!/usr/bin/env python3
"""Deterministic HTML renderer for PPT slides that do not need generated art.

Tables, charts, KPI panels, icon diagrams, modules and roadmaps render in a real
Chromium browser. Codex remains responsible for 3D scenes and generated imagery.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import math
import mimetypes
import sys
from pathlib import Path
from typing import Any

def configure_utf8_output(stream) -> None:
    reconfigure = getattr(stream, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8")


WIDTH = 1672
HEIGHT = 941
OUTPUT_WIDTH = 1920
OUTPUT_HEIGHT = 1080
OUTPUT_SCALE = 2
GRAPH_WIDTH = 1480.0
GRAPH_HEIGHT = 500.0
SUPPORTED_LAYOUTS = {
    "table",
    "kpi",
    "bars",
    "process",
    "modules",
    "break",
    "cover",
    "overview",
    "image",
    "network",
    "roadmap",
}

ICON_PATHS = {
    "search": '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/><path d="M8 11h6M11 8v6"/>',
    "nodes": '<circle cx="12" cy="5" r="2.5"/><circle cx="5" cy="18" r="2.5"/><circle cx="19" cy="18" r="2.5"/><path d="m10.8 7.2-4.6 8.5M13.2 7.2l4.6 8.5M7.5 18h9"/>',
    "play": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="m10 9 5 3-5 3Z"/>',
    "chart": '<path d="M4 20V10M10 20V6M16 20V3M22 20H2"/>',
    "refresh": '<path d="M20 7a8 8 0 0 0-14-2L3 8M4 17a8 8 0 0 0 14 2l3-3"/><path d="M3 3v5h5M21 21v-5h-5"/>',
    "check": '<circle cx="12" cy="12" r="9"/><path d="m8 12 2.5 2.5L16.5 8"/>',
    "document": '<path d="M6 2h8l4 4v16H6Z"/><path d="M14 2v5h5M9 12h6M9 16h6"/>',
    "people": '<circle cx="9" cy="8" r="3"/><circle cx="17" cy="9" r="2.5"/><path d="M3 20c0-4 2-6 6-6s6 2 6 6M15 15c3 0 5 2 5 5"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v6l4 2"/>',
    "link": '<path d="M10 13a5 5 0 0 0 7 0l2-2a5 5 0 0 0-7-7l-1 1M14 11a5 5 0 0 0-7 0l-2 2a5 5 0 0 0 7 7l1-1"/>',
}

BASE_CSS = f"""
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; width: {WIDTH}px; height: {HEIGHT}px; overflow: hidden; }}
body {{ font-family: var(--font-family); color: var(--text); }}
#slide {{ position: relative; width: {WIDTH}px; height: {HEIGHT}px; padding: 58px 66px 48px; background: var(--background); overflow: hidden; }}
.eyebrow {{ color: var(--accent); font-size: 17px; font-weight: 700; letter-spacing: .04em; margin-bottom: 24px; }}
.title {{ display: flex; align-items: baseline; flex-wrap: wrap; gap: 14px; font-size: 58px; line-height: 1.12; letter-spacing: -.04em; }}
.title .light {{ font-weight: 300; }} .title .bold {{ font-weight: 760; }}
.subtitle {{ margin-top: 22px; color: var(--muted); font-size: 23px; line-height: 1.45; }}
#slide.header-center .eyebrow {{ text-align: center; }}
#slide.header-center .title {{ justify-content: center; text-align: center; }}
#slide.header-center .subtitle {{ text-align: center; }}
.content {{ margin-top: 52px; }}
#slide.layout-process .content {{ margin-top: 142px; }}
#slide.layout-process .content {{ min-height: 260px; }}
#slide.layout-process .rule-note {{ bottom: 185px; }}
#slide.layout-roadmap .rule-note {{ bottom: 120px; }}
#slide.layout-bars .content {{ margin-top: 78px; }}
.footer {{ position: absolute; right: 66px; bottom: 30px; color: #8b9099; font-size: 13px; letter-spacing: .02em; }}
.rule-note {{ position: absolute; left: 66px; bottom: 54px; display: flex; align-items: center; gap: 18px; font-size: 17px; color: #333842; }}
.rule-note::before {{ content: ''; width: 64px; height: 3px; background: var(--accent); }}
.title, .subtitle, .kpi-label, .kpi-detail, .bar-label, .process-label, .process-detail,
.module-feature h3, .module-feature p, .module-row h3, .module-row p,
.roadmap-step h3, .roadmap-step p, .break-action h3, .break-action p,
.break-purpose, .meta-row, .donut-label, .dist-row, .graph-node-label,
.graph-edge-label, .image-fact, table.report th, table.report td,
.cover-statement, .image-copy h3, .image-copy p {{
  word-break: keep-all;
  overflow-wrap: normal;
}}
.icon {{ display: inline-block; width: 44px; height: 44px; color: currentColor; }}
.icon svg {{ width: 100%; height: 100%; fill: none; stroke: currentColor; stroke-width: 1.7; stroke-linecap: round; stroke-linejoin: round; }}

.table-wrap {{ margin-top: 38px; width: 100%; }}
table.report {{ width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 21px; }}
table.report th {{ height: 76px; padding: 0 18px; background: var(--accent); color: white; text-align: left; font-weight: 700; border-right: 1px solid rgba(255,255,255,.4); }}
table.report th:last-child {{ border-right: 0; text-align: center; }}
table.report td {{ height: var(--row-height, 105px); padding: 0 18px; border-right: 1px solid #dfe3ea; border-bottom: 1px solid #edf0f4; vertical-align: middle; word-break: keep-all; overflow-wrap: normal; }}
table.report tr:nth-child(odd) td {{ background: #f5f6f9; }}
table.report tr:nth-child(even) td {{ background: white; }}
table.report td:last-child {{ border-right: 0; text-align: center; font-weight: 650; }}

.kpi-layout {{ min-height: 500px; display: flex; flex-direction: column; }}
.kpi-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; }}
.kpi-item {{ min-height: 230px; padding: 42px 28px 34px; text-align: center; background: #fff; border: 1px solid #eef0f4; box-shadow: 0 14px 34px rgba(24,35,55,.055); }}
.kpi-value {{ color: var(--accent); font-size: 67px; font-weight: 760; line-height: 1; }}
.kpi-label {{ margin-top: 25px; font-size: 20px; font-weight: 700; }}
.kpi-detail {{ margin-top: 12px; color: #858a93; font-size: 15px; }}
.interpretation {{ margin-top: auto; max-width: 1120px; padding: 30px 0 18px; border-top: 3px solid var(--accent); }}
.interpretation h3 {{ margin: 0; font-size: 26px; }}
.interpretation p {{ margin: 14px 0 0; color: #666c75; font-size: 17px; line-height: 1.55; }}

.bars-layout {{ min-height: 510px; display: grid; grid-template-columns: 68% 28%; gap: 4%; align-items: start; }}
.bar-row {{ display: grid; grid-template-columns: 255px 1fr; align-items: center; margin-bottom: 27px; }}
.bar-label {{ font-size: 18px; color: #30343b; }}
.bar-track {{ height: 48px; position: relative; }}
.bar-fill {{ position: relative; height: 100%; min-width: 48px; background: var(--accent); }}
.bar-fill.neutral {{ background: #e6e8ec; }}
.bar-value {{ position: absolute; right: 12px; top: 50%; transform: translateY(-50%); font-size: 17px; color: #222; }}
.bar-fill .bar-value {{ color: #fff; }}
.bar-fill.neutral .bar-value {{ color: #222; }}
.summary-stack {{ min-height: 495px; display: grid; grid-template-rows: repeat(2, 1fr); gap: 20px; }}
.summary-box {{ min-height: 0; display: grid; place-content: center; text-align: center; border: 1px solid #e7e9ee; box-shadow: 0 12px 28px rgba(24,35,55,.045); }}
.summary-value {{ color: var(--accent); font-size: 62px; font-weight: 760; }}
.summary-label {{ margin-top: 8px; font-size: 17px; }}
.annotation {{ margin: 18px 0 0 255px; color: #d9333f; font-size: 15px; max-width: 610px; line-height: 1.4; }}

.process {{ position: relative; display: grid; grid-template-columns: repeat(var(--process-count), minmax(0, 1fr)); margin-top: 100px; transform: translateY(15px); }}
.process::before {{ content: ''; position: absolute; left: calc(50% / var(--process-count)); right: calc(50% / var(--process-count)); top: 78px; height: 1px; background: #bfc4cc; }}
.process-step {{ position: relative; text-align: center; padding: 0 12px; }}
.process-icon {{ margin: 0 auto 23px; width: 46px; height: 46px; color: #20242a; }}
.process-dot {{ position: relative; z-index: 2; width: 18px; height: 18px; margin: 0 auto 25px; border: 2px solid #20242a; border-radius: 50%; background: white; }}
.process-step.active .process-dot {{ border-color: var(--accent); background: var(--accent); transform: scale(1.45); }}
.process-step.active .process-icon, .process-step.active .process-label {{ color: var(--accent); }}
.process-label {{ font-size: 25px; font-weight: 650; }}
.process-step.active .process-label {{ font-size: 35px; font-weight: 760; }}
.process-detail {{ margin-top: 13px; color: #676d76; font-size: 16px; }}

.modules {{ display: grid; grid-template-columns: 42% 1fr; gap: 72px; align-items: stretch; min-height: 530px; }}
.module-feature {{ position: relative; background: color-mix(in srgb, var(--accent) 9%, #fff); padding: 52px 55px; display: flex; flex-direction: column; justify-content: flex-start; }}
.module-feature > .icon {{ position: absolute; top: 52px; right: 55px; width: 52px; height: 52px; color: var(--accent); }}
.module-feature .number {{ color: var(--accent); font-size: 58px; font-weight: 650; }}
.module-feature h3 {{ margin: auto 0 12px; font-size: 39px; }}
.module-feature p {{ color: #5d636d; font-size: 18px; }}
.module-rows {{ display: grid; grid-template-rows: repeat(3, 1fr); }}
.module-row {{ display: grid; grid-template-columns: 55px 60px 210px 1fr; align-items: center; border-bottom: 1px solid #dfe3e9; }}
.module-row:last-child {{ border-bottom: 0; }}
.module-row .number {{ color: var(--accent); font-size: 27px; font-weight: 700; }}
.module-row h3 {{ margin: 0; font-size: 28px; }}
.module-row p {{ color: #666c75; font-size: 17px; }}
.modules-feature-right {{ grid-template-columns: 1fr 42%; }}
.modules-feature-right .module-feature {{ order: 2; }}
.modules-feature-right .module-rows {{ order: 1; }}
.modules-feature-top {{ grid-template-columns: 1fr; grid-template-rows: 42% 1fr; gap: 34px; }}
.modules-feature-top .module-feature {{ display: grid; grid-template-columns: 100px 1fr 2fr 80px; align-items: center; padding: 34px 42px; }}
.modules-feature-top .module-feature .number {{ grid-column: 1; grid-row: 1; }}
.modules-feature-top .module-feature h3 {{ grid-column: 2; grid-row: 1; margin: 0; }}
.modules-feature-top .module-feature p {{ grid-column: 3; grid-row: 1; margin: 0; }}
.modules-feature-top .module-feature > .icon {{ position: static; grid-column: 4; grid-row: 1; justify-self: end; }}
.modules-feature-top .module-rows {{ grid-template-columns: repeat(3, 1fr); grid-template-rows: 1fr; }}
.modules-feature-top .module-row {{ grid-template-columns: 42px 48px 1fr; grid-template-rows: auto auto; align-content: center; padding: 20px 28px; border-right: 1px solid #dfe3e9; border-bottom: 0; }}
.modules-feature-top .module-row:last-child {{ border-right: 0; }}
.modules-feature-top .module-row .icon {{ grid-column: 1; grid-row: 1 / span 2; }}
.modules-feature-top .module-row .number {{ grid-column: 2; grid-row: 1; }}
.modules-feature-top .module-row h3 {{ grid-column: 3; grid-row: 1; font-size: 24px; }}
.modules-feature-top .module-row p {{ grid-column: 2 / 4; grid-row: 2; margin-top: 10px; }}
.modules-ledger {{ grid-template-columns: 1fr; grid-template-rows: 1fr 3fr; gap: 0; border-top: 1px solid #dfe3e9; }}
.modules-ledger .module-feature {{ display: grid; grid-template-columns: 70px 70px 250px 1fr; align-items: center; padding: 24px 18px; background: color-mix(in srgb, var(--accent) 7%, #fff); border-bottom: 1px solid #dfe3e9; }}
.modules-ledger .module-feature > .icon {{ position: static; grid-column: 1; }}
.modules-ledger .module-feature .number {{ grid-column: 2; font-size: 32px; }}
.modules-ledger .module-feature h3 {{ grid-column: 3; margin: 0; font-size: 30px; }}
.modules-ledger .module-feature p {{ grid-column: 4; margin: 0; font-size: 18px; }}
.modules-ledger .module-rows {{ grid-template-rows: repeat(3, 1fr); }}
.modules-ledger .module-row {{ grid-template-columns: 70px 70px 250px 1fr; padding: 0 18px; }}

.roadmap {{ position: relative; height: 500px; margin-top: 14px; }}
.roadmap-step {{ position: absolute; width: 23%; min-height: 260px; padding: 34px 28px; background: #f3f4f7; }}
.roadmap-step:nth-child(1) {{ left: 0; bottom: 0; }}
.roadmap-step:nth-child(2) {{ left: 24%; bottom: 48px; }}
.roadmap-step:nth-child(3) {{ left: 49%; bottom: 96px; }}
.roadmap-step:nth-child(4) {{ left: 74%; bottom: 144px; }}
.roadmap-step.active {{ background: color-mix(in srgb, var(--accent) 11%, #fff); }}
.roadmap-week {{ color: #30343a; font-size: 50px; font-weight: 520; }}
.roadmap-step.active .roadmap-week {{ color: var(--accent); font-weight: 700; }}
.roadmap-step h3 {{ margin: 16px 0 11px; font-size: 27px; }}
.roadmap-step p {{ margin: 0; color: #535963; font-size: 17px; line-height: 1.45; }}
.roadmap-step .icon {{ margin-top: 24px; }}

.break-layout {{ min-height: 530px; display: grid; grid-template-columns: 40% 56%; gap: 4%; }}
.break-hero {{ padding: 34px 48px 34px 0; border-right: 1px solid #dfe3e9; display: flex; flex-direction: column; justify-content: space-between; }}
.break-duration {{ color: var(--accent); font-size: 92px; font-weight: 760; line-height: 1; }}
.break-window {{ margin-top: 18px; font-size: 28px; font-weight: 700; }}
.break-purpose {{ margin-top: auto; padding-top: 26px; border-top: 1px solid #dfe3e9; font-size: 20px; line-height: 1.5; color: #414751; }}
.break-actions {{ display: grid; grid-template-rows: repeat(var(--break-count), minmax(0, 1fr)); border-top: 1px solid #dfe3e9; }}
.break-action {{ display: grid; grid-template-columns: 112px 1fr; align-items: center; padding: 24px 30px; border-bottom: 1px solid #dfe3e9; }}
.break-action-time {{ color: var(--accent); font-size: 27px; font-weight: 760; }}
.break-action h3 {{ margin: 0; font-size: 28px; line-height: 1.25; }}
.break-action p {{ margin: 10px 0 0; color: #666c75; font-size: 17px; line-height: 1.45; }}
.overview {{ display: grid; grid-template-columns: 25% 34% 41%; min-height: 520px; border-top: 1px solid #e2e5ea; }}
.overview > section {{ padding: 30px 34px; border-right: 1px solid #e2e5ea; }}
.overview > section:first-child {{ padding-left: 0; }}
.overview > section:last-child {{ border-right: 0; padding-right: 0; }}
.meta-row {{ display: flex; justify-content: space-between; align-items: center; min-height: 66px; border-bottom: 1px solid #edf0f3; font-size: 16px; }}
.meta-row strong {{ font-size: 18px; }}
.donut-title, .dist-title {{ margin-bottom: 28px; font-size: 18px; font-weight: 700; }}
.donut-wrap {{ position: relative; width: 290px; height: 290px; margin: 22px auto 0; border-radius: 50%; background: var(--donut); }}
.donut-wrap::after {{ content: ''; position: absolute; inset: 73px; border-radius: 50%; background: white; }}
.donut-label {{ position: absolute; z-index: 2; font-size: 16px; line-height: 1.25; text-align: center; }}
.donut-label strong {{ display: block; font-size: 18px; }}
.donut-label:nth-child(1) {{ right: 26px; top: 104px; color: white; }}
.donut-label:nth-child(2) {{ left: 72px; bottom: 28px; }}
.donut-label:nth-child(3) {{ left: 30px; top: 52px; }}
.dist-group {{ margin-bottom: 31px; }}
.dist-group:last-child {{ margin-bottom: 0; }}
.dist-row {{ display: grid; grid-template-columns: 112px 1fr 52px; align-items: center; gap: 10px; margin: 10px 0; font-size: 15px; }}
.dist-track {{ height: 9px; background: #edf0f4; }}
.dist-fill {{ height: 100%; background: #cfd4dc; }}
.dist-row.primary .dist-fill {{ background: var(--accent); }}
.dist-value {{ text-align: right; color: #5c626b; }}

#slide.layout-cover {{ padding-top: 72px; }}
#slide.layout-cover .eyebrow {{ margin-bottom: 30px; }}
#slide.layout-cover .title {{ max-width: 1280px; font-size: 74px; line-height: 1.08; }}
#slide.layout-cover .subtitle {{ max-width: 980px; font-size: 25px; }}
#slide.layout-cover .content {{ margin-top: 48px; }}
.cover-layout {{ min-height: 450px; display: grid; grid-template-columns: 34% 62%; gap: 4%; }}
.cover-copy {{ padding: 36px 30px 24px 0; display: flex; flex-direction: column; justify-content: space-between; }}
.cover-statement {{ max-width: 500px; padding-left: 24px; border-left: 4px solid var(--accent); font-size: 24px; font-weight: 700; line-height: 1.5; word-break: keep-all; }}
.cover-meta {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 22px; }}
.cover-meta-row {{ display: block; padding-top: 14px; border-top: 1px solid #d9dde3; font-size: 15px; }}
.cover-meta-row span {{ display: block; margin-bottom: 8px; color: #737983; }}
.cover-meta-row strong {{ font-weight: 650; }}
.cover-visual {{ min-height: 450px; overflow: hidden; background: white; }}
.cover-visual img {{ width: 100%; height: 100%; object-fit: var(--image-fit, contain); object-position: var(--image-position, center); transform: scale(var(--image-scale, 1)); transform-origin: var(--image-position, center); display: block; }}
.image-layout {{ min-height: 520px; display: grid; grid-template-columns: 38% 58%; gap: 4%; }}
.image-copy {{ align-self: stretch; padding: 36px 40px 30px 0; border-right: 1px solid #dfe3e9; display: flex; flex-direction: column; justify-content: space-between; }}
.image-copy h3 {{ margin: 0; font-size: 35px; line-height: 1.25; letter-spacing: -.035em; word-break: keep-all; overflow-wrap: normal; }}
.image-copy p {{ margin: 18px 0 0; color: #5f6670; font-size: 19px; line-height: 1.55; }}
.image-facts {{ margin-top: auto; display: grid; gap: 13px; }}
.image-fact {{ padding-top: 13px; border-top: 1px solid #dce1e8; font-size: 16px; }}
.image-frame {{ min-height: 520px; overflow: hidden; background: #f7f8fa; }}
.image-frame img {{ width: 100%; height: 100%; object-fit: var(--image-fit, cover); object-position: var(--image-position, center); transform: scale(var(--image-scale, 1)); transform-origin: var(--image-position, center); display: block; }}

.graph-canvas {{ position: relative; min-height: 520px; background: #fafbfc; border-top: 1px solid #e1e5eb; border-bottom: 1px solid #e1e5eb; overflow: hidden; }}
.graph-canvas svg {{ position: absolute; inset: 0; width: 100%; height: 100%; }}
.graph-edge {{ stroke: #aeb6c2; stroke-width: 1.7; fill: none; }}
.graph-edge.primary {{ stroke: var(--accent); stroke-width: 2.4; }}
.graph-edge-label {{ fill: #666d77; font-size: 16px; text-anchor: middle; paint-order: stroke; stroke: #fafbfc; stroke-width: 5px; }}
.graph-node {{ position: absolute; width: 180px; min-height: 100px; transform: translate(-50%, -50%); padding: 17px 18px; background: white; border: 1px solid #dce1e8; box-shadow: 0 10px 24px rgba(31,44,68,.055); }}
.graph-node.primary {{ border-color: var(--accent); background: color-mix(in srgb, var(--accent) 7%, #fff); }}
.graph-node-type {{ color: var(--accent); font-size: 13px; font-weight: 700; letter-spacing: .04em; }}
.graph-node-label {{ margin-top: 8px; font-size: 20px; font-weight: 700; line-height: 1.25; }}
#slide.layout-cover.composition-hero-left .cover-layout {{ grid-template-columns: 62% 34%; }}
#slide.layout-cover.composition-hero-left .cover-visual {{ order: 1; }}
#slide.layout-cover.composition-hero-left .cover-copy {{ order: 2; padding: 36px 0 24px 30px; }}
#slide.layout-cover.composition-stacked .cover-layout {{ grid-template-columns: 1fr; grid-template-rows: 58% 1fr; gap: 24px; }}
#slide.layout-cover.composition-stacked .cover-visual {{ order: 1; min-height: 260px; }}
#slide.layout-cover.composition-stacked .cover-copy {{ order: 2; padding: 0; display: grid; grid-template-columns: 48% 1fr; gap: 5%; }}
#slide.layout-cover.composition-stacked .cover-meta {{ align-self: end; }}
#slide.layout-table.composition-entity-led .report col:nth-child(1) {{ width: 40% !important; }}
#slide.layout-table.composition-entity-led .report col:nth-child(2) {{ width: 40% !important; }}
#slide.layout-table.composition-entity-led .report col:nth-child(3) {{ width: 20% !important; }}
#slide.layout-table.composition-outcome-led .report col:nth-child(1) {{ width: 24% !important; }}
#slide.layout-table.composition-outcome-led .report col:nth-child(2) {{ width: 44% !important; }}
#slide.layout-table.composition-outcome-led .report col:nth-child(3) {{ width: 32% !important; }}
#slide.layout-kpi .kpi-item {{ background: transparent; box-shadow: none; border: 0; border-top: 1px solid #dfe3e9; }}
#slide.layout-kpi.composition-lead-left .kpi-grid,
#slide.layout-kpi.composition-lead-right .kpi-grid {{ grid-template-columns: 56% 1fr; grid-template-rows: repeat(2, 1fr); gap: 0; min-height: 300px; }}
#slide.layout-kpi.composition-lead-left .kpi-item:first-child,
#slide.layout-kpi.composition-lead-right .kpi-item:first-child {{ grid-row: 1 / 3; display: flex; flex-direction: column; justify-content: center; align-items: flex-start; text-align: left; border-right: 1px solid #dfe3e9; }}
#slide.layout-kpi.composition-lead-right .kpi-item:first-child {{ grid-column: 2; border-right: 0; border-left: 1px solid #dfe3e9; }}
#slide.layout-kpi.composition-lead-left .kpi-item:not(:first-child),
#slide.layout-kpi.composition-lead-right .kpi-item:not(:first-child) {{ min-height: 0; padding: 14px 24px; text-align: left; }}
#slide.layout-kpi:is(.composition-lead-left,.composition-lead-right) .kpi-item:not(:first-child) .kpi-value {{ font-size: 44px; }}
#slide.layout-kpi:is(.composition-lead-left,.composition-lead-right) .kpi-item:not(:first-child) .kpi-label {{ margin-top: 8px; font-size: 18px; }}
#slide.layout-kpi:is(.composition-lead-left,.composition-lead-right) .kpi-item:not(:first-child) .kpi-detail {{ margin-top: 6px; font-size: 14px; }}
#slide.layout-kpi.composition-lead-right .kpi-item:not(:first-child) {{ grid-column: 1; }}
#slide.layout-kpi.composition-lead-left .kpi-item:first-child .kpi-value,
#slide.layout-kpi.composition-lead-right .kpi-item:first-child .kpi-value {{ font-size: 88px; }}
#slide.layout-kpi.composition-interpretation-left .kpi-layout {{ display: grid; grid-template-columns: 34% 62%; gap: 4%; }}
#slide.layout-kpi.composition-interpretation-left .interpretation {{ order: 1; margin: 0; align-self: stretch; }}
#slide.layout-kpi.composition-interpretation-left .kpi-grid {{ order: 2; grid-template-columns: 1fr; gap: 0; border-bottom: 1px solid #dfe3e9; }}
#slide.layout-kpi.composition-interpretation-left .kpi-item {{ min-height: 0; display: grid; grid-template-columns: 170px 220px 1fr; align-items: center; text-align: left; padding: 24px 20px; }}
#slide.layout-kpi.composition-interpretation-left .kpi-value {{ font-size: 52px; }}
#slide.layout-kpi.composition-interpretation-left .kpi-label {{ margin: 0; }}
#slide.layout-bars.composition-plot-right .bars-layout {{ grid-template-columns: 28% 68%; }}
#slide.layout-bars.composition-plot-right .summary-stack {{ order: 1; }}
#slide.layout-bars.composition-plot-right .bars-layout > div:first-child {{ order: 2; }}
#slide.layout-bars.composition-summary-bottom .bars-layout {{ grid-template-columns: 1fr; grid-template-rows: 1fr auto; gap: 28px; }}
#slide.layout-bars.composition-summary-bottom .summary-stack {{ min-height: 0; grid-template-columns: repeat(2, 1fr); grid-template-rows: 1fr; gap: 22px; }}
#slide.layout-bars.composition-summary-bottom .summary-box {{ min-height: 112px; padding: 22px 28px; display: grid; grid-template-columns: 150px 1fr; align-items: center; text-align: left; }}
#slide.layout-overview.composition-donut-stage .overview {{ grid-template-columns: 42% 25% 33%; }}
#slide.layout-overview.composition-donut-stage .overview > section:nth-child(2) {{ order: 1; }}
#slide.layout-overview.composition-donut-stage .overview > section:nth-child(1) {{ order: 2; }}
#slide.layout-overview.composition-donut-stage .overview > section:nth-child(3) {{ order: 3; }}
#slide.layout-overview.composition-distribution-stage .overview {{ grid-template-columns: 48% 22% 30%; }}
#slide.layout-overview.composition-distribution-stage .overview > section:nth-child(3) {{ order: 1; }}
#slide.layout-overview.composition-distribution-stage .overview > section:nth-child(1) {{ order: 2; }}
#slide.layout-overview.composition-distribution-stage .overview > section:nth-child(2) {{ order: 3; }}
#slide.layout-process:is(.composition-vertical-ledger,.composition-vertical-focus) .process {{ grid-template-columns: 1fr; margin-top: 18px; transform: none; }}
#slide.layout-process:is(.composition-vertical-ledger,.composition-vertical-focus) .process::before {{ left: 97px; right: auto; top: 34px; bottom: 34px; width: 1px; height: auto; }}
#slide.layout-process:is(.composition-vertical-ledger,.composition-vertical-focus) .process-step {{ display: grid; grid-template-columns: 70px 18px 218px 1fr; column-gap: 18px; align-items: center; min-height: 72px; text-align: left; padding: 0; }}
#slide.layout-process:is(.composition-vertical-ledger,.composition-vertical-focus) .process-icon {{ margin: 0; width: 34px; height: 34px; }}
#slide.layout-process:is(.composition-vertical-ledger,.composition-vertical-focus) .process-dot {{ top: auto; left: auto; margin: 0; justify-self: center; }}
#slide.layout-process:is(.composition-vertical-ledger,.composition-vertical-focus) .process-label {{ margin: 0; font-size: 24px; }}
#slide.layout-process:is(.composition-vertical-ledger,.composition-vertical-focus) .process-detail {{ margin: 0; }}
#slide.layout-process.composition-vertical-focus .process-step.active {{ min-height: 112px; padding: 18px 0; background: color-mix(in srgb, var(--accent) 7%, #fff); }}
#slide.layout-process.composition-vertical-focus .process-step.active .process-label {{ color: var(--accent); font-size: 31px; }}
#slide.layout-process:is(.composition-vertical-ledger,.composition-vertical-focus) .rule-note {{ bottom: 120px; }}
#slide.layout-roadmap.composition-staircase-fall .roadmap-step:nth-child(1) {{ bottom: 144px; }}
#slide.layout-roadmap.composition-staircase-fall .roadmap-step:nth-child(2) {{ bottom: 96px; }}
#slide.layout-roadmap.composition-staircase-fall .roadmap-step:nth-child(3) {{ bottom: 48px; }}
#slide.layout-roadmap.composition-staircase-fall .roadmap-step:nth-child(4) {{ bottom: 0; }}
#slide.layout-roadmap.composition-phase-ledger .roadmap {{ display: grid; grid-template-rows: repeat(4, 1fr); height: 500px; margin-top: 0; border-top: 1px solid #dfe3e9; }}
#slide.layout-roadmap.composition-phase-ledger .roadmap-step {{ position: static; width: auto; min-height: 0; display: grid; grid-template-columns: 170px 240px 1fr 60px; align-items: center; padding: 18px 24px; background: transparent; border-bottom: 1px solid #dfe3e9; }}
#slide.layout-roadmap.composition-phase-ledger .roadmap-step h3,
#slide.layout-roadmap.composition-phase-ledger .roadmap-step p {{ margin: 0; }}
#slide.layout-roadmap.composition-phase-ledger .roadmap-step .icon {{ position: static; justify-self: end; }}
#slide.layout-break.composition-time-right .break-layout {{ grid-template-columns: 56% 40%; }}
#slide.layout-break.composition-time-right .break-actions {{ order: 1; }}
#slide.layout-break.composition-time-right .break-hero {{ order: 2; border-right: 0; border-left: 1px solid #dfe3e9; padding: 34px 0 34px 48px; }}
#slide.layout-break.composition-return-band .break-layout {{ grid-template-columns: 1fr; grid-template-rows: 42% 1fr; gap: 26px; }}
#slide.layout-break.composition-return-band .break-hero {{ padding: 18px 0 28px; border-right: 0; border-bottom: 1px solid #dfe3e9; display: grid; grid-template-columns: 36% 1fr; align-items: end; }}
#slide.layout-break.composition-return-band .break-purpose {{ margin: 0; }}
#slide.layout-break.composition-return-band .break-actions {{ grid-template-columns: repeat(var(--break-count), 1fr); grid-template-rows: 1fr; }}
#slide.layout-break.composition-return-band .break-action {{ grid-template-columns: 1fr; align-content: center; border-right: 1px solid #dfe3e9; }}
#slide.layout-network.composition-vertical-flow .graph-node {{ width: 160px; min-height: 62px; padding: 8px 12px; }}
#slide.layout-network.composition-vertical-flow .graph-node-label {{ margin-top: 4px; font-size: 17px; }}
#slide.layout-image.composition-copy-right .image-layout {{ grid-template-columns: 58% 38%; }}
#slide.layout-image.composition-copy-right .image-frame {{ order: 1; }}
#slide.layout-image.composition-copy-right .image-copy {{ order: 2; border-right: 0; border-left: 1px solid #dfe3e9; padding: 36px 0 30px 40px; }}
#slide.layout-image.composition-visual-top .image-layout {{ grid-template-columns: 1fr; grid-template-rows: 62% 1fr; gap: 26px; }}
#slide.layout-image.composition-visual-top .image-frame {{ order: 1; min-height: 300px; }}
#slide.layout-image.composition-visual-top .image-copy {{ order: 2; border-right: 0; border-top: 1px solid #dfe3e9; padding: 24px 0 0; display: grid; grid-template-columns: 42% 1fr; gap: 5%; }}
#slide.preset-modern-flat .title {{ font-size: 62px; }}
#slide.preset-modern-flat .eyebrow {{ padding: 6px 10px; width: fit-content; background: color-mix(in srgb, var(--accent) 10%, #fff); }}
#slide.preset-data-report-editorial .title {{ font-size: 54px; }}
#slide.preset-data-report-editorial .content {{ margin-top: 44px; }}
#slide.preset-paper-serif {{ background: #FBF8F1; color: #29241F; }}
#slide.preset-paper-serif .title,
#slide.preset-paper-serif .kpi-value,
#slide.preset-paper-serif .roadmap-week {{ font-family: 'Noto Serif KR', 'Batang', serif; letter-spacing: -.025em; }}
#slide.preset-paper-serif .eyebrow {{ color: #705C45; }}
#slide.preset-swiss-grid {{ border-top: 12px solid var(--accent); padding-top: 46px; }}
#slide.preset-swiss-grid .eyebrow {{ color: #111318; border-bottom: 2px solid #111318; padding-bottom: 12px; }}
#slide.preset-swiss-grid .title {{ font-size: 66px; letter-spacing: -.055em; }}
#slide.preset-swiss-grid .footer {{ color: #111318; }}
#slide.preset-swiss-grid .summary-box,
#slide.preset-swiss-grid .kpi-item,
#slide.preset-swiss-grid .graph-node {{ box-shadow: none; border-color: #111318; }}
#slide.preset-warm-editorial {{ background: #FCF7EF; color: #2E2723; }}
#slide.preset-warm-editorial .subtitle,
#slide.preset-warm-editorial .process-detail,
#slide.preset-warm-editorial .module-row p {{ color: #75685E; }}
#slide.preset-warm-editorial .title {{ max-width: 1320px; font-size: 61px; }}
#slide.preset-warm-editorial .image-frame,
#slide.preset-warm-editorial .graph-canvas {{ background: #F7EFE4; }}
#slide.preset-technical-blueprint {{ background: #F4F8FA; color: #102B3A; }}
#slide.preset-technical-blueprint .eyebrow {{ border-left: 4px solid var(--accent); padding-left: 12px; }}
#slide.preset-technical-blueprint .content {{ border-top: 1px solid color-mix(in srgb, var(--accent) 28%, #fff); padding-top: 24px; }}
#slide.preset-technical-blueprint .graph-canvas {{ background: #EDF5F8; border-color: color-mix(in srgb, var(--accent) 28%, #fff); }}
#slide.preset-photo-documentary .title {{ max-width: 1200px; font-size: 60px; }}
#slide.preset-photo-documentary .image-layout {{ grid-template-columns: 30% 66%; }}
#slide.preset-photo-documentary .image-frame {{ background: white; }}
#slide.preset-photo-documentary .image-copy {{ padding-right: 34px; }}
"""


def _e(value: Any) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def _icon(name: str | None) -> str:
    paths = ICON_PATHS.get(str(name or "check"), ICON_PATHS["check"])
    return f'<span class="icon"><svg viewBox="0 0 24 24" aria-hidden="true">{paths}</svg></span>'


def _title(spec: dict) -> str:
    title = spec.get("title", "")
    if isinstance(title, list):
        parts = []
        for item in title:
            if isinstance(item, dict):
                weight = "bold" if item.get("weight") == "bold" else "light"
                parts.append(f'<span class="{weight}">{_e(item.get("text"))}</span>')
            else:
                parts.append(f'<span class="bold">{_e(item)}</span>')
        return "".join(parts)
    return f'<span class="bold">{_e(title)}</span>'


def validate_graph(graph: dict) -> list[str]:
    """Validate semantic entities and edge integrity before layout."""
    errors: list[str] = []
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    ids = [str(node.get("id", "")).strip() for node in nodes]
    if any(not node_id for node_id in ids):
        errors.append("node id is required")
    if len(ids) != len(set(ids)):
        errors.append("node ids must be unique")
    node_ids = set(ids)
    connected = {node_id: 0 for node_id in node_ids}
    for node in nodes:
        if not str(node.get("label", "")).strip():
            errors.append(f"node {node.get('id')!r} requires label")
        if not str(node.get("entityType", "")).strip():
            errors.append(f"node {node.get('id')!r} requires entityType")
    for index, edge in enumerate(edges):
        source = str(edge.get("source", "")).strip()
        target = str(edge.get("target", "")).strip()
        if source not in node_ids:
            errors.append(f"edge {index} source {source!r} is missing")
        if target not in node_ids:
            errors.append(f"edge {index} target {target!r} is missing")
        if source == target:
            errors.append(f"edge {index} cannot self-connect")
        direction = edge.get("direction", "forward")
        if direction not in {"forward", "bidirectional"}:
            errors.append(f"edge {index} has invalid direction {direction!r}")
        if graph.get("requireEdgeLabels", True) and not str(edge.get("label", "")).strip():
            errors.append(f"edge {index} requires label")
        if source in connected:
            connected[source] += 1
        if target in connected:
            connected[target] += 1
    if graph.get("forbidIsolated", True):
        for node_id, degree in connected.items():
            if degree == 0:
                errors.append(f"isolated node {node_id!r} is forbidden")
    return errors


def _graph_positions(graph: dict) -> dict[str, tuple[float, float]]:
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    ids = [str(node["id"]) for node in nodes]
    outgoing = {node_id: [] for node_id in ids}
    indegree = {node_id: 0 for node_id in ids}
    for edge in edges:
        source = str(edge["source"])
        target = str(edge["target"])
        outgoing[source].append(target)
        indegree[target] += 1
        if edge.get("direction") == "bidirectional":
            outgoing[target].append(source)
    queue = [node_id for node_id in ids if indegree[node_id] == 0]
    layer = {node_id: 0 for node_id in queue}
    visited = []
    while queue:
        node_id = queue.pop(0)
        visited.append(node_id)
        for target in outgoing[node_id]:
            indegree[target] -= 1
            layer[target] = max(layer.get(target, 0), layer[node_id] + 1)
            if indegree[target] == 0:
                queue.append(target)
    if len(visited) != len(ids):
        ordered = []
        remaining = set(ids)
        current = min(remaining)
        while current in remaining:
            ordered.append(current)
            remaining.remove(current)
            candidates = sorted(
                target for target in outgoing[current]
                if target in remaining
            )
            if not candidates:
                break
            current = candidates[0]
        ordered.extend(sorted(remaining))
        count = max(1, len(ordered))
        return {
            node_id: (
                GRAPH_WIDTH / 2 + 520 * math.cos(2 * math.pi * index / count),
                GRAPH_HEIGHT / 2 + 170 * math.sin(2 * math.pi * index / count),
            )
            for index, node_id in enumerate(ordered)
        }
    max_layer = max(layer.values(), default=0)
    groups: dict[int, list[str]] = {}
    for node_id in ids:
        groups.setdefault(layer.get(node_id, 0), []).append(node_id)
    positions: dict[str, tuple[float, float]] = {}
    for layer_index, group in groups.items():
        x = 120.0 if max_layer == 0 else 120.0 + 1240.0 * layer_index / max_layer
        for row, node_id in enumerate(group):
            y = 250.0 if len(group) == 1 else 75.0 + 350.0 * row / (len(group) - 1)
            positions[node_id] = (x, y)
    return positions

def _table(spec: dict) -> str:
    columns = spec.get("columns", [])
    widths = [str(c.get("width", "auto")) for c in columns]
    colgroup = "".join(f'<col style="width:{_e(w)}">' for w in widths)
    head = "".join(f'<th>{_e(c.get("label"))}</th>' for c in columns)
    row_data = spec.get("rows", [])
    row_height = max(72, min(110, round(440 / max(1, len(row_data)))))
    rows = "".join(
        "<tr>" + "".join(f'<td>{_e(cell)}</td>' for cell in row) + "</tr>"
        for row in row_data
    )
    return f'<div class="table-wrap"><table class="report" style="--row-height:{row_height}px"><colgroup>{colgroup}</colgroup><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>'


def _kpi(spec: dict) -> str:
    cards = "".join(
        f'<div class="kpi-item"><div class="kpi-value" style="color:{_e(item.get("color", "var(--accent)"))}">{_e(item.get("value"))}</div><div class="kpi-label">{_e(item.get("label"))}</div><div class="kpi-detail">{_e(item.get("detail"))}</div></div>'
        for item in spec.get("items", [])
    )
    interp = spec.get("interpretation", {})
    return f'<div class="kpi-layout"><div class="kpi-grid">{cards}</div><div class="interpretation"><h3>{_e(interp.get("title"))}</h3><p>{_e(interp.get("body"))}</p></div></div>'


def _bars(spec: dict) -> str:
    bars = []
    items = spec.get("items", [])
    max_value = max((float(item.get("value", 0)) for item in items), default=1.0)
    for item in items:
        value = float(item.get("value", 0))
        highlighted = bool(item.get("highlight"))
        fill = "bar-fill" if highlighted else "bar-fill neutral"
        style = f'width:{max(5.0, min(100.0, value / max_value * 100.0))}%;'
        bars.append(f'<div class="bar-row"><div class="bar-label">{_e(item.get("label"))}</div><div class="bar-track"><div class="{fill}" style="{style}"><span class="bar-value">{_e(item.get("display", str(value)+"%"))}</span></div></div></div>')
    summaries = "".join(
        f'<div class="summary-box"><div class="summary-value" style="color:{_e(item.get("color", "var(--accent)"))}">{_e(item.get("value"))}</div><div class="summary-label">{_e(item.get("label"))}</div></div>'
        for item in spec.get("summaries", [])
    )
    annotation = f'<div class="annotation">{_e(spec.get("annotation"))}</div>' if spec.get("annotation") else ""
    return f'<div class="bars-layout"><div><div>{"".join(bars)}</div>{annotation}</div><div class="summary-stack">{summaries}</div></div>'


def _process(spec: dict) -> str:
    active = int(spec.get("active", 0))
    process_items = spec.get("items", [])
    items = "".join(
        f'<div class="process-step {"active" if index == active else ""}"><div class="process-icon">{_icon(item.get("icon"))}</div><div class="process-dot"></div><div class="process-label">{_e(item.get("label"))}</div><div class="process-detail">{_e(item.get("detail"))}</div></div>'
        for index, item in enumerate(process_items)
    )
    count = max(1, len(process_items))
    return f'<div class="process" style="--process-count:{count}">{items}</div>'


def _modules(spec: dict) -> str:
    items = spec.get("items", [])
    featured = int(spec.get("featured", 0))
    preset = _composition_preset(spec)
    hero = items[featured]
    rows = "".join(
        f'<div class="module-row">{_icon(item.get("icon"))}<div class="number">{index+1:02d}</div><h3>{_e(item.get("label"))}</h3><p>{_e(item.get("detail"))}</p></div>'
        for index, item in enumerate(items) if index != featured
    )
    return f'<div class="modules modules-{preset}"><div class="module-feature">{_icon(hero.get("icon"))}<div class="number">{featured+1:02d}</div><h3>{_e(hero.get("label"))}</h3><p>{_e(hero.get("detail"))}</p></div><div class="module-rows">{rows}</div></div>'


def _roadmap(spec: dict) -> str:
    active = int(spec.get("active", 0))
    items = "".join(
        f'<div class="roadmap-step {"active" if index == active else ""}"><div class="roadmap-week">{_e(item.get("week"))}</div><h3>{_e(item.get("label"))}</h3><p>{_e(item.get("detail"))}</p>{_icon(item.get("icon"))}</div>'
        for index, item in enumerate(spec.get("items", []))
    )
    return f'<div class="roadmap">{items}</div>'

def _break(spec: dict) -> str:
    actions = spec.get("actions", [])
    if not 2 <= len(actions) <= 3:
        raise ValueError("break layout requires 2 or 3 actions")
    rows = "".join(
        f'<div class="break-action"><div class="break-action-time">{_e(item.get("time"))}</div><div><h3>{_e(item.get("label"))}</h3><p>{_e(item.get("detail"))}</p></div></div>'
        for item in actions
    )
    return (
        '<div class="break-layout">'
        f'<section class="break-hero"><div><div class="break-duration">{_e(spec.get("duration"))}</div><div class="break-window">{_e(spec.get("window"))}</div></div><div class="break-purpose">{_e(spec.get("purpose"))}</div></section>'
        f'<section class="break-actions" style="--break-count:{len(actions)}">{rows}</section>'
        '</div>'
    )



def _overview(spec: dict) -> str:
    metadata = "".join(
        f'<div class="meta-row"><span>{_e(item.get("label"))}</span><strong>{_e(item.get("value"))}</strong></div>'
        for item in spec.get("metadata", [])
    )
    donut = spec.get("donut", [])
    total = sum(float(item.get("value", 0)) for item in donut) or 1.0
    cursor = 0.0
    stops = []
    labels = []
    default_colours = ["var(--accent)", "#9fc2f4", "#d9e5f6"]
    for index, item in enumerate(donut):
        portion = float(item.get("value", 0)) / total * 100.0
        colour = item.get("color", default_colours[index % len(default_colours)])
        stops.append(f"{colour} {cursor:.3f}% {cursor + portion:.3f}%")
        labels.append(
            f'<div class="donut-label"><span>{_e(item.get("label"))}</span><strong>{_e(item.get("display", str(item.get("value")) + "%"))}</strong></div>'
        )
        cursor += portion
    donut_style = "--donut:conic-gradient(" + ",".join(stops) + ")"
    groups = []
    for group in spec.get("distributions", []):
        items = group.get("items", [])
        maximum = max((float(item.get("value", 0)) for item in items), default=1.0)
        rows = "".join(
            f'<div class="dist-row {"primary" if index == 0 else ""}"><span>{_e(item.get("label"))}</span><div class="dist-track"><div class="dist-fill" style="width:{float(item.get("value", 0)) / maximum * 100:.3f}%"></div></div><span class="dist-value">{_e(item.get("display", str(item.get("value")) + "%"))}</span></div>'
            for index, item in enumerate(items)
        )
        groups.append(f'<div class="dist-group"><div class="dist-title">{_e(group.get("title"))}</div>{rows}</div>')
    return (
        '<div class="overview">'
        f'<section>{metadata}</section>'
        f'<section><div class="donut-title">{_e(spec.get("donutTitle", "조직 규모"))}</div><div class="donut-wrap" style="{donut_style}">{"".join(labels)}</div></section>'
        f'<section>{"".join(groups)}</section>'
        '</div>'
    )


def _cover(spec: dict) -> str:
    source = spec.get("imageData", "")
    if not source:
        raise ValueError("cover layout requires imagePath or imageData")
    meta = "".join(
        f'<div class="cover-meta-row"><span>{_e(item.get("label"))}</span><strong>{_e(item.get("value"))}</strong></div>'
        for item in spec.get("metadata", [])
    )
    fit = "cover" if spec.get("imageFit") == "cover" else "contain"
    return (
        '<div class="cover-layout">'
        f'<section class="cover-copy"><div class="cover-statement">{_e(spec.get("statement"))}</div><div class="cover-meta">{meta}</div></section>'
        f'<section class="cover-visual" style="--image-fit:{fit};--image-scale:{float(spec.get("imageScale", 1.0)):.3f};--image-position:{_e(spec.get("imagePosition", "center"))}"><img src="{source}" alt="{_e(spec.get("imageAlt", ""))}"></section>'
        '</div>'
    )

def _image(spec: dict) -> str:
    source = spec.get("imageData", "")
    if not source:
        raise ValueError("image layout requires imagePath or imageData")
    facts = "".join(
        f'<div class="image-fact">{_e(item)}</div>'
        for item in spec.get("facts", [])
    )
    fit = "contain" if spec.get("imageFit") == "contain" else "cover"
    return (
        '<div class="image-layout">'
        f'<div class="image-copy"><div><h3>{_e(spec.get("callout"))}</h3><p>{_e(spec.get("caption"))}</p></div><div class="image-facts">{facts}</div></div>'
        f'<div class="image-frame" style="--image-fit:{fit};--image-scale:{float(spec.get("imageScale", 1.0)):.3f};--image-position:{_e(spec.get("imagePosition", "center"))}"><img src="{source}" alt="{_e(spec.get("imageAlt", ""))}"></div>'
        '</div>'
    )


_NODE_HALF_X = 87.0
_NODE_HALF_Y = 50.0


def _node_boundary_points(
    source: tuple[float, float],
    target: tuple[float, float],
) -> tuple[tuple[float, float], tuple[float, float]]:
    dx = target[0] - source[0]
    dy = target[1] - source[1]
    scale = max(
        abs(dx) / _NODE_HALF_X if dx else 0,
        abs(dy) / _NODE_HALF_Y if dy else 0,
        1,
    )
    offset_x = dx / scale
    offset_y = dy / scale
    return (
        (source[0] + offset_x, source[1] + offset_y),
        (target[0] - offset_x, target[1] - offset_y),
    )


def _segment_hits_node(
    start: tuple[float, float],
    end: tuple[float, float],
    center: tuple[float, float],
) -> bool:
    for index in range(1, 20):
        ratio = index / 20
        x = start[0] + (end[0] - start[0]) * ratio
        y = start[1] + (end[1] - start[1]) * ratio
        if (
            abs(x - center[0]) < _NODE_HALF_X + 12
            and abs(y - center[1]) < _NODE_HALF_Y + 12
        ):
            return True
    return False


def _edge_route(
    source_id: str,
    target_id: str,
    positions: dict[str, tuple[float, float]],
    orientation: str = "horizontal",
) -> tuple[str, tuple[float, float]]:
    source = positions[source_id]
    target = positions[target_id]
    start, end = _node_boundary_points(source, target)
    if orientation == "vertical":
        direction = 1.0 if target[1] >= source[1] else -1.0
        start = (source[0], source[1] + direction * 31.0)
        end = (target[0], target[1] - direction * 31.0)
    blockers = [
        center
        for node_id, center in positions.items()
        if node_id not in {source_id, target_id}
        and _segment_hits_node(start, end, center)
    ]
    if not blockers:
        path = f"M {start[0]:.2f} {start[1]:.2f} L {end[0]:.2f} {end[1]:.2f}"
        if abs(end[0] - start[0]) >= abs(end[1] - start[1]):
            label = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2 - 72)
        else:
            label = (
                (start[0] + end[0]) / 2 + (120 if orientation == "vertical" else 24),
                (start[1] + end[1]) / 2,
            )
        return path, label
    if orientation == "vertical":
        centers = list(positions.values())
        candidates = [
            max(26.0, min(center[0] for center in centers) - 120.0),
            min(GRAPH_WIDTH - 26.0, max(center[0] for center in centers) + 120.0),
        ]
        lane = max(
            candidates,
            key=lambda value: min(
                abs(value - center[0]) - _NODE_HALF_X
                for center in centers
            ),
        )
        first_y = start[1] + (4.0 if end[1] >= start[1] else -4.0)
        last_y = end[1] - (4.0 if end[1] >= start[1] else -4.0)
        path = (
            f"M {start[0]:.2f} {start[1]:.2f} "
            f"L {start[0]:.2f} {first_y:.2f} "
            f"L {lane:.2f} {first_y:.2f} "
            f"L {lane:.2f} {last_y:.2f} "
            f"L {end[0]:.2f} {last_y:.2f} "
            f"L {end[0]:.2f} {end[1]:.2f}"
        )
        return path, (lane + 24, (first_y + last_y) / 2)
    centers = list(positions.values())
    candidates = [
        max(26.0, min(center[1] for center in centers) - 78.0),
        min(474.0, max(center[1] for center in centers) + 78.0),
    ]
    lane = max(
        candidates,
        key=lambda value: min(
            abs(value - center[1]) - _NODE_HALF_Y
            for center in centers
        ),
    )
    first_x = start[0] + (34.0 if end[0] >= start[0] else -34.0)
    last_x = end[0] - (34.0 if end[0] >= start[0] else -34.0)
    path = (
        f"M {start[0]:.2f} {start[1]:.2f} "
        f"L {first_x:.2f} {start[1]:.2f} "
        f"L {first_x:.2f} {lane:.2f} "
        f"L {last_x:.2f} {lane:.2f} "
        f"L {last_x:.2f} {end[1]:.2f} "
        f"L {end[0]:.2f} {end[1]:.2f}"
    )
    label = ((first_x + last_x) / 2, lane - 10)
    return path, label


def _network(spec: dict) -> str:
    graph = spec.get("graph", {})
    errors = validate_graph(graph)
    if errors:
        raise ValueError("invalid graph: " + "; ".join(errors))
    preset = _composition_preset(spec)
    if preset == "hub-spoke":
        primary_nodes = [
            str(node["id"])
            for node in graph.get("nodes", [])
            if node.get("primary")
        ]
        if len(primary_nodes) != 1:
            raise ValueError("hub-spoke requires exactly one primary hub node")
        hub = primary_nodes[0]
        edges = graph.get("edges", [])
        spokes = {str(node["id"]) for node in graph.get("nodes", []) if str(node["id"]) != hub}
        connected = set()
        for edge in edges:
            source = str(edge["source"])
            target = str(edge["target"])
            if hub not in {source, target}:
                raise ValueError("hub-spoke requires every edge to touch the primary hub")
            connected.add(target if source == hub else source)
        if connected != spokes or len(edges) != len(spokes):
            raise ValueError("hub-spoke requires one edge per spoke")
    positions = _graph_positions(graph)
    if preset == "vertical-flow":
        positions = {
            node_id: (
                120.0 + (y / GRAPH_HEIGHT) * 1240.0,
                45.0 + (x / GRAPH_WIDTH) * 410.0,
            )
            for node_id, (x, y) in positions.items()
        }
    elif preset == "hub-spoke":
        node_ids = [str(node["id"]) for node in graph.get("nodes", [])]
        primary = next(
            (
                str(node["id"])
                for node in graph.get("nodes", [])
                if node.get("primary")
            ),
            node_ids[0],
        )
        spokes = [node_id for node_id in node_ids if node_id != primary]
        positions = {primary: (GRAPH_WIDTH / 2, GRAPH_HEIGHT / 2)}
        for index, node_id in enumerate(spokes):
            angle = -math.pi / 2 + 2 * math.pi * index / max(1, len(spokes))
            positions[node_id] = (
                GRAPH_WIDTH / 2 + 520 * math.cos(angle),
                GRAPH_HEIGHT / 2 + 170 * math.sin(angle),
            )
    edges = []
    for index, edge in enumerate(graph.get("edges", [])):
        source_id = str(edge["source"])
        target_id = str(edge["target"])
        path, label_point = _edge_route(
            source_id,
            target_id,
            positions,
            orientation="vertical" if preset == "vertical-flow" else "horizontal",
        )
        marker_start = ' marker-start="url(#arrow-start)"' if edge.get("direction") == "bidirectional" else ""
        css_class = "graph-edge primary" if edge.get("primary") else "graph-edge"
        edge_id = f"edge-{index}-{source_id}-{target_id}"
        edges.append(
            f'<path id="{_e(edge_id)}" class="{css_class}" data-source="{_e(source_id)}" data-target="{_e(target_id)}" data-direction="{_e(edge.get("direction", "forward"))}" data-label="{_e(edge.get("label"))}" d="{path}" marker-end="url(#arrow-end)"{marker_start}/>'
            f'<text class="graph-edge-label" data-edge-id="{_e(edge_id)}" x="{label_point[0]:.2f}" y="{label_point[1]:.2f}">{_e(edge.get("label"))}</text>'
        )
    nodes = []
    for node in graph.get("nodes", []):
        x, y = positions[str(node["id"])]
        css_class = "graph-node primary" if node.get("primary") else "graph-node"
        nodes.append(
            f'<div class="{css_class}" data-node-id="{_e(node.get("id"))}" style="left:{x / GRAPH_WIDTH * 100:.3f}%;top:{y / GRAPH_HEIGHT * 100:.3f}%">'
            f'<div class="graph-node-type">{_e(node.get("entityType"))}</div>'
            f'<div class="graph-node-label">{_e(node.get("label"))}</div></div>'
        )
    return (
        '<div class="graph-canvas">'
        f'<svg viewBox="0 0 {GRAPH_WIDTH:.0f} {GRAPH_HEIGHT:.0f}" preserveAspectRatio="none" aria-hidden="true">'
        '<defs><marker id="arrow-end" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#8e98a6"/></marker>'
        '<marker id="arrow-start" markerWidth="8" markerHeight="8" refX="1" refY="4" orient="auto-start-reverse"><path d="M8,0 L0,4 L8,8 Z" fill="#8e98a6"/></marker></defs>'
        + "".join(edges)
        + '</svg>'
        + "".join(nodes)
        + '</div>'
    )


LAYOUT_RENDERERS = {
    "table": _table,
    "kpi": _kpi,
    "bars": _bars,
    "process": _process,
    "modules": _modules,
    "overview": _overview,
    "image": _image,
    "cover": _cover,
    "network": _network,
    "break": _break,
    "roadmap": _roadmap,
}
COMPOSITION_PRESETS = {
    "cover": ("hero-right", "hero-left", "stacked"),
    "table": ("evidence-wide", "entity-led", "outcome-led"),
    "kpi": ("lead-left", "lead-right", "interpretation-left"),
    "bars": ("plot-left", "plot-right", "summary-bottom"),
    "overview": ("metadata-rail", "donut-stage", "distribution-stage"),
    "process": ("horizontal-rail", "vertical-ledger", "vertical-focus"),
    "modules": ("feature-left", "feature-right", "feature-top", "ledger"),
    "roadmap": ("staircase-rise", "staircase-fall", "phase-ledger"),
    "break": ("time-left", "time-right", "return-band"),
    "network": ("horizontal-flow", "vertical-flow", "hub-spoke"),
    "image": ("copy-left", "copy-right", "visual-top"),
}


def _composition_preset(spec: dict) -> str:
    layout = str(spec.get("layout") or "")
    allowed = COMPOSITION_PRESETS.get(layout)
    if not allowed:
        raise ValueError(f"unsupported HTML slide layout: {layout!r}")
    if "modulePreset" in spec:
        raise ValueError("modulePreset is obsolete; use compositionPreset")
    preset = str(spec.get("compositionPreset") or allowed[0])
    if preset not in allowed:
        raise ValueError(f"unsupported compositionPreset for {layout}: {preset!r}")
    return preset


def supports(job: dict) -> bool:
    spec = job.get("htmlSpec", job)
    layout = spec.get("layout")
    explicit = job.get("renderer")
    if explicit == "codex":
        return False
    return layout in SUPPORTED_LAYOUTS and (explicit == "html" or "htmlSpec" in job or "layout" in job)


def _html_tokens() -> dict:
    defaults = {
        "fontFamily": "Pretendard, 'Noto Sans KR', 'Malgun Gothic', sans-serif",
        "accent": "#246BFD",
        "background": "#FFFFFF",
        "text": "#111318",
        "muted": "#6D727B",
    }
    profile_path = Path(__file__).resolve().parent.parent / "style_profiles.json"
    if not profile_path.is_file():
        return defaults
    payload = json.loads(profile_path.read_text(encoding="utf-8"))
    defaults.update(payload.get("renderPolicy", {}).get("htmlTokens", {}))
    return defaults


def build_html(spec: dict) -> str:
    layout = spec.get("layout")
    if layout not in LAYOUT_RENDERERS:
        raise ValueError(f"unsupported HTML slide layout: {layout!r}")
    spec = dict(spec)
    composition = _composition_preset(spec)
    spec["compositionPreset"] = composition
    tokens = _html_tokens()
    accent = _e(spec.get("accent", tokens["accent"]))
    note = f'<div class="rule-note">{_e(spec.get("note"))}</div>' if spec.get("note") else ""
    content = LAYOUT_RENDERERS[layout](spec)
    classes = [f"layout-{layout}", f"composition-{composition}"]
    preset = "".join(
        character
        for character in str(spec.get("designPreset") or "")
        if character.isalnum() or character == "-"
    )
    if preset:
        classes.append(f"preset-{preset}")
    if spec.get("headerAlign") == "center":
        classes.append("header-center")
    class_value = " ".join(classes)
    return f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><style>:root{{--accent:{accent};--font-family:{_e(tokens["fontFamily"])};--background:{_e(tokens["background"])};--text:{_e(tokens["text"])};--muted:{_e(tokens["muted"])};}}{BASE_CSS}</style></head><body><main id="slide" class="{class_value}"><div class="eyebrow">{_e(spec.get("eyebrow"))}</div><div class="title">{_title(spec)}</div><div class="subtitle">{_e(spec.get("subtitle"))}</div><section class="content">{content}</section>{note}<div class="footer">{_e(spec.get("footer"))}</div></main></body></html>'''


def _prepare_image_data(spec: dict, base: Path) -> None:
    if spec.get("layout") not in {"image", "cover"} or spec.get("imageData"):
        return
    raw_path = spec.get("imagePath")
    if not raw_path:
        raise ValueError(f"{spec.get('layout')} layout requires imagePath")
    path = Path(raw_path)
    if not path.is_absolute():
        path = (base / path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"image asset not found: {path}")
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    spec["imageData"] = f"data:{mime};base64,{encoded}"
    spec["_resolvedImagePath"] = str(path)


def _layout_receipt(page, spec: dict) -> dict:
    metrics = page.evaluate(
        """() => {
          const slide = document.querySelector('#slide');
          const box = (el) => {
            if (!el) return null;
            const r = el.getBoundingClientRect();
            return {left:r.left, top:r.top, right:r.right, bottom:r.bottom, width:r.width, height:r.height};
          };
          const union = (items) => {
            const boxes = items.map(box).filter(Boolean);
            if (!boxes.length) return null;
            return {
              left: Math.min(...boxes.map(b => b.left)),
              top: Math.min(...boxes.map(b => b.top)),
              right: Math.max(...boxes.map(b => b.right)),
              bottom: Math.max(...boxes.map(b => b.bottom))
            };
          };
          const surfaceStyle = (selector) => {
            const el = document.querySelector(selector);
            if (!el) return null;
            const style = getComputedStyle(el);
            return {
              backgroundColor: style.backgroundColor,
              borderTopWidth: style.borderTopWidth,
              borderRightWidth: style.borderRightWidth
            };
          };
          const koreanMidWordBreaks = [];
          const koreanTargets = document.querySelectorAll(
            '.title, .subtitle, .kpi-label, .kpi-detail, .bar-label, ' +
            '.process-label, .process-detail, .module-feature h3, .module-feature p, ' +
            '.module-row h3, .module-row p, .roadmap-step h3, .roadmap-step p, ' +
            '.break-action h3, .break-action p, .break-purpose, .meta-row, ' +
            '.donut-label, .dist-row, .graph-node-label, .graph-edge-label, ' +
            '.image-fact, table.report th, table.report td, .cover-statement, ' +
            '.image-copy h3, .image-copy p'
          );
          for (const el of koreanTargets) {
            const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
            while (walker.nextNode()) {
              const node = walker.currentNode;
              const text = node.nodeValue || '';
              for (const match of text.matchAll(/[가-힣]{2,}/g)) {
                const tops = new Set();
                for (let offset = match.index; offset < match.index + match[0].length; offset++) {
                  const range = document.createRange();
                  range.setStart(node, offset);
                  range.setEnd(node, offset + 1);
                  const rect = range.getBoundingClientRect();
                  if (rect.width || rect.height) {
                    tops.add(Math.round(rect.top * 10) / 10);
                  }
                }
                if (tops.size > 1) {
                  koreanMidWordBreaks.push({
                    selector: String(el.className || el.tagName).slice(0, 80),
                    word: match[0],
                    lines: tops.size
                  });
                }
              }
            }
          }
          const meaningful = [...document.querySelectorAll(
            'table.report, .kpi-item, .interpretation, .bar-fill, .summary-box, .annotation, ' +
            '.process-step, .module-feature, .module-row, .roadmap-step, .break-hero, .break-action, .overview > section, ' +
            '.image-copy, .image-frame, .cover-copy, .cover-visual, .graph-canvas, .rule-note'
          )].filter(el => getComputedStyle(el).display !== 'none');
          const overflow = [...document.querySelectorAll('#slide *')]
            .filter(el => {
              if (el instanceof SVGElement) return false;
              const style = getComputedStyle(el);
              const text = String(el.textContent || '').trim();
              if (style.display === 'none' || style.visibility === 'hidden' || !text) return false;
              return el.scrollWidth > el.clientWidth + 1 || el.scrollHeight > el.clientHeight + 7;
            })
            .map(el => ({
              tag: el.tagName.toLowerCase(),
              className: String(el.className || ''),
              text: String(el.textContent || '').trim().slice(0, 120),
              clientWidth: el.clientWidth,
              scrollWidth: el.scrollWidth,
              clientHeight: el.clientHeight,
              scrollHeight: el.scrollHeight
            }));
          const feature = document.querySelector('.module-feature');
          const featureBox = box(feature);
          const featureChildren = feature ? union([...feature.children]) : null;
          let moduleBalance = null;
          if (featureBox && featureChildren) {
            moduleBalance = {
              top: (featureChildren.top - featureBox.top) / featureBox.height,
              bottom: (featureBox.bottom - featureChildren.bottom) / featureBox.height,
              left: (featureChildren.left - featureBox.left) / featureBox.width,
              right: (featureBox.right - featureChildren.right) / featureBox.width
            };
          }
          const nodeRects = new Map(
            [...document.querySelectorAll('.graph-node')].map(node => [
              node.dataset.nodeId,
              node.getBoundingClientRect()
            ])
          );
          const pointInside = (point, rect, inset = 4) => Boolean(
            rect &&
            point.x > rect.left + inset &&
            point.x < rect.right - inset &&
            point.y > rect.top + inset &&
            point.y < rect.bottom - inset
          );
          const overlaps = (a, b) => Boolean(
            a && b &&
            a.left < b.right &&
            a.right > b.left &&
            a.top < b.bottom &&
            a.bottom > b.top
          );
          const screenPoint = (path, distance) => {
            const point = path.getPointAtLength(distance);
            const matrix = path.getScreenCTM();
            return matrix
              ? new DOMPoint(point.x, point.y).matrixTransform(matrix)
              : {x: point.x, y: point.y};
          };
          const graphEdges = [...document.querySelectorAll('.graph-edge')].map(path => {
            const length = path.getTotalLength();
            const source = path.dataset.source;
            const target = path.dataset.target;
            const direction = path.dataset.direction;
            const label = document.querySelector(
              `.graph-edge-label[data-edge-id="${path.id}"]`
            );
            const obstacles = [...nodeRects.entries()]
              .filter(([id]) => id !== source && id !== target);
            const sampledOcclusion = Array.from({length: 19}, (_, index) =>
              screenPoint(path, length * (index + 1) / 20)
            ).some(point => obstacles.some(([, rect]) => pointInside(point, rect, 0)));
            const labelRect = label ? label.getBoundingClientRect() : null;
            return {
              source,
              target,
              direction,
              label: path.dataset.label,
              length: Math.round(length * 100) / 100,
              hasMarkerEnd: path.getAttribute('marker-end') === 'url(#arrow-end)',
              hasMarkerStart: direction !== 'bidirectional' ||
                path.getAttribute('marker-start') === 'url(#arrow-start)',
              startOccluded: pointInside(screenPoint(path, 0), nodeRects.get(source)),
              endOccluded: pointInside(screenPoint(path, length), nodeRects.get(target)),
              pathOccluded: sampledOcclusion,
              labelOccluded: [...nodeRects.values()].some(rect => overlaps(labelRect, rect))
            };
          });
          const processSteps = union([...document.querySelectorAll('.process-step')]);
          const processNote = box(document.querySelector('#slide.layout-process .rule-note'));
          const processToNoteGap = processSteps && processNote
            ? (processNote.top - processSteps.bottom) / slide.getBoundingClientRect().height
            : null;
          const process = document.querySelector('.process');
          const processRect = process ? process.getBoundingClientRect() : null;
          const processLineTop = process
            ? parseFloat(getComputedStyle(process, '::before').top)
            : null;
          const processLineY = processRect && Number.isFinite(processLineTop)
            ? processRect.top + processLineTop
            : null;
          const processDotCenters = [...document.querySelectorAll('.process-dot')]
            .map(dot => {
              const rect = dot.getBoundingClientRect();
              return rect.top + rect.height / 2;
            });
          const processDotMaxDeviation = processLineY !== null && processDotCenters.length
            ? Math.max(...processDotCenters.map(center => Math.abs(center - processLineY)))
            : null;
          const processLineLeft = process
            ? parseFloat(getComputedStyle(process, '::before').left)
            : null;
          const processLineX = processRect && Number.isFinite(processLineLeft)
            ? processRect.left + processLineLeft
            : null;
          const processDotCenterXs = [...document.querySelectorAll('.process-dot')]
            .map(dot => {
              const rect = dot.getBoundingClientRect();
              return rect.left + rect.width / 2;
            });
          const processDotMaxDeviationX = processLineX !== null && processDotCenterXs.length
            ? Math.max(...processDotCenterXs.map(center => Math.abs(center - processLineX)))
            : null;
          const processDotToLabelGaps = [...document.querySelectorAll('.process-step')]
            .map(step => {
              const dot = step.querySelector('.process-dot')?.getBoundingClientRect();
              const label = step.querySelector('.process-label')?.getBoundingClientRect();
              return dot && label ? label.left - dot.right : null;
            })
            .filter(value => value !== null);
          const processDotToLabelMinGap = processDotToLabelGaps.length
            ? Math.min(...processDotToLabelGaps)
            : null;
          const compositionRegions = {};
          for (const selector of [
            '.cover-copy', '.cover-visual', '.table-wrap', '.kpi-grid',
            '.interpretation', '.bars-layout > div:first-child', '.summary-stack',
            '.overview > section:nth-child(1)', '.overview > section:nth-child(2)',
            '.overview > section:nth-child(3)', '.process', '.module-feature',
            '.module-rows', '.roadmap', '.break-hero', '.break-actions',
            '.graph-canvas', '.image-copy', '.image-frame'
          ]) {
            const rect = union([...document.querySelectorAll(selector)]);
            if (rect) compositionRegions[selector] = rect;
          }
          return {
            slide: box(slide),
            header: union([
              document.querySelector('.eyebrow'),
              document.querySelector('.title'),
              document.querySelector('.subtitle')
            ]),
            content: box(document.querySelector('.content')),
            meaningfulBody: union(meaningful),
            footer: box(document.querySelector('.footer')),
            moduleFeature: featureBox,
            moduleBalance,
            overflow,
            graphNodeCount: document.querySelectorAll('.graph-node').length,
            graphEdgeCount: document.querySelectorAll('.graph-edge').length,
            graphEdgeLabelCount: document.querySelectorAll('.graph-edge-label').length,
            graphEdges,
            processToNoteGap,
            processLineY,
            processDotCenters,
            processDotMaxDeviation,
            processLineX,
            processDotCenterXs,
            processDotMaxDeviationX,
            processDotToLabelMinGap,
            koreanMidWordBreaks,
            compositionRegions,
            surfaceStyles: {
              coverCopy: surfaceStyle('.cover-copy'),
              breakHero: surfaceStyle('.break-hero'),
              imageCopy: surfaceStyle('.image-copy'),
            }
          };
        }"""
    )
    slide = metrics.get("slide") or {"width": WIDTH, "height": HEIGHT}

    def normalize(rect):
        if rect is None:
            return None
        return {
            "left": round(rect["left"] / slide["width"], 4),
            "top": round(rect["top"] / slide["height"], 4),
            "right": round(rect["right"] / slide["width"], 4),
            "bottom": round(rect["bottom"] / slide["height"], 4),
            "width": round((rect["right"] - rect["left"]) / slide["width"], 4),
            "height": round((rect["bottom"] - rect["top"]) / slide["height"], 4),
        }

    receipt_spec = dict(spec)
    receipt_spec.pop("_imageData", None)
    spec_digest = "sha256:" + hashlib.sha256(
        json.dumps(
            receipt_spec,
            ensure_ascii=False,
            sort_keys=True,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    source_asset = spec.get("_resolvedImagePath")
    source_asset_digest = (
        "sha256:" + hashlib.sha256(Path(source_asset).read_bytes()).hexdigest()
        if source_asset and Path(source_asset).is_file()
        else None
    )
    process_gap = metrics.get("processToNoteGap")
    process_alignment = {
        "lineY": (
            round(float(metrics["processLineY"]) / slide["height"], 4)
            if metrics.get("processLineY") is not None
            else None
        ),
        "dotCenters": [
            round(float(value) / slide["height"], 4)
            for value in metrics.get("processDotCenters", [])
        ],
        "maxDeviationPx": (
            round(float(metrics["processDotMaxDeviation"]), 2)
            if metrics.get("processDotMaxDeviation") is not None
            else None
        ),
        "lineX": (
            round(float(metrics["processLineX"]) / slide["width"], 4)
            if metrics.get("processLineX") is not None
            else None
        ),
        "dotCenterXs": [
            round(float(value) / slide["width"], 4)
            for value in metrics.get("processDotCenterXs", [])
        ],
        "maxDeviationXPx": (
            round(float(metrics["processDotMaxDeviationX"]), 2)
            if metrics.get("processDotMaxDeviationX") is not None
            else None
        ),
        "dotToLabelMinGapPx": (
            round(float(metrics["processDotToLabelMinGap"]), 2)
            if metrics.get("processDotToLabelMinGap") is not None
            else None
        ),
    }
    if process_gap is not None and not math.isfinite(float(process_gap)):
        raise ValueError("layout receipt contains non-finite process gap")
    return {
        "schemaVersion": 1,
        "renderer": "html-playwright",
        "layout": spec.get("layout"),
        "size": [WIDTH, HEIGHT],
        "pixelSize": [OUTPUT_WIDTH, OUTPUT_HEIGHT],
        "header": normalize(metrics.get("header")),
        "content": normalize(metrics.get("content")),
        "meaningfulBody": normalize(metrics.get("meaningfulBody")),
        "footer": normalize(metrics.get("footer")),
        "moduleFeature": normalize(metrics.get("moduleFeature")),
        "moduleBalance": metrics.get("moduleBalance"),
        "overflow": metrics.get("overflow", []),
        "graph": {
            "nodes": metrics.get("graphNodeCount", 0),
            "edges": metrics.get("graphEdgeCount", 0),
            "edgeLabels": metrics.get("graphEdgeLabelCount", 0),
            "visibility": metrics.get("graphEdges", []),
        },
        "internalGaps": {
            "processToNote": (
                round(process_gap, 4)
                if process_gap is not None
                else None
            ),
        },
        "processAlignment": process_alignment,
        "surfaceStyles": metrics.get("surfaceStyles", {}),
        "koreanMidWordBreaks": metrics.get("koreanMidWordBreaks", []),
        "designPreset": spec.get("designPreset"),
        "compositionPreset": spec.get("compositionPreset"),
        "compositionRegions": {
            selector: normalize(rect)
            for selector, rect in metrics.get("compositionRegions", {}).items()
        },
        "rendererDigest": "sha256:" + hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "specDigest": spec_digest,
        "sourceAsset": source_asset,
        "assetRole": spec.get("assetRole"),
        "sourceAssetDigest": source_asset_digest,
    }

def render_job(job: dict, base_dir: str | Path) -> Path:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as error:
        raise RuntimeError("Playwright is required for HTML slide rendering") from error

    base = Path(base_dir).resolve()
    spec = dict(job.get("htmlSpec", job))
    if "accent" not in spec and job.get("accentColor"):
        spec["accent"] = job["accentColor"]
    if "designPreset" not in spec and job.get("styleProfile"):
        spec["designPreset"] = job["styleProfile"]
    spec["compositionPreset"] = _composition_preset(spec)
    _prepare_image_data(spec, base)
    out_value = job.get("out") or spec.get("out")
    if not out_value:
        raise ValueError("HTML slide job requires out")
    out = Path(out_value)
    if not out.is_absolute():
        out = base / out
    out.parent.mkdir(parents=True, exist_ok=True)

    markup = build_html(spec)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT}, device_scale_factor=OUTPUT_SCALE)
        page.set_content(markup, wait_until="load")
        page.evaluate("document.fonts.ready")
        receipt = _layout_receipt(page, spec)
        raw_out = out.with_name(out.stem + ".supersampled.png")
        page.locator("#slide").screenshot(path=str(raw_out))
        from PIL import Image
        with Image.open(raw_out) as image:
            image.convert("RGB").resize(
                (OUTPUT_WIDTH, OUTPUT_HEIGHT),
                Image.Resampling.LANCZOS,
            ).save(out)
        raw_out.unlink()
        receipt_path = out.with_suffix(".layout.json")
        receipt_path.write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        browser.close()
    return out


def main() -> int:
    configure_utf8_output(sys.stdout)
    parser = argparse.ArgumentParser(description="Render deterministic PPT slides with Chromium")
    parser.add_argument("spec_json", type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path("."))
    args = parser.parse_args()
    data = json.loads(args.spec_json.read_text(encoding="utf-8"))
    slides = data.get("slides", []) if isinstance(data, dict) else data
    for index, slide in enumerate(slides, 1):
        job = dict(slide)
        job.setdefault("out", f"slide_{index:02d}.png")
        out = render_job(job, args.out_dir)
        print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
