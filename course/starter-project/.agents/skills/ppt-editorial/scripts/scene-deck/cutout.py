#!/usr/bin/env python3
"""Foreground analysis and background-safe cutouts for generated PPT scenes."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image


BACKGROUND_DISTANCE = 18.0
BORDER_UNIFORM_RATIO = 0.80
TRANSPARENT_BORDER_RATIO = 0.95


def sha256(path: str | Path) -> str:
    source = Path(path)
    return "sha256:" + hashlib.sha256(source.read_bytes()).hexdigest()


def _border_width(width: int, height: int) -> int:
    return max(2, min(width, height) // 80)


def _border_mask(width: int, height: int, thickness: int) -> np.ndarray:
    mask = np.zeros((height, width), dtype=bool)
    mask[:thickness, :] = True
    mask[-thickness:, :] = True
    mask[:, :thickness] = True
    mask[:, -thickness:] = True
    return mask


def _background_color(rgb: np.ndarray, border: np.ndarray) -> np.ndarray:
    return np.median(rgb[border], axis=0)


def _distance(rgb: np.ndarray, background: np.ndarray) -> np.ndarray:
    values = rgb.astype(np.float32) - background.astype(np.float32)
    return np.sqrt(np.sum(values * values, axis=2))


def _quantized_color(value: np.ndarray) -> tuple[int, int, int]:
    return tuple(int(channel // 16) for channel in value)


def checkerboard_detected(rgb: np.ndarray, region: np.ndarray) -> bool:
    values = rgb[region]
    if not len(values):
        return False
    colors = Counter(_quantized_color(value) for value in values)
    if len(colors) < 2:
        return False
    total = sum(colors.values())
    (first, first_count), (second, second_count) = colors.most_common(2)
    coverage = (first_count + second_count) / total
    balance = min(first_count, second_count) / max(first_count, second_count)
    separation = math.sqrt(sum((a - b) ** 2 for a, b in zip(first, second)))
    quantized = rgb // 16
    component_counts = []
    for color in (first, second):
        color_mask = (
            np.all(quantized == np.asarray(color, dtype=np.uint8), axis=2)
            & region
        ).astype(np.uint8)
        count, _labels = cv2.connectedComponents(color_mask, connectivity=4)
        component_counts.append(count - 1)
    return (
        coverage >= 0.45
        and balance >= 0.15
        and separation >= 1.5
        and min(component_counts) >= 4
    )


def _edge_connected_background(
    candidate: np.ndarray,
    border: np.ndarray,
) -> np.ndarray:
    _count, labels = cv2.connectedComponents(
        candidate.astype(np.uint8),
        connectivity=4,
    )
    edge_labels = set(int(value) for value in np.unique(labels[border]))
    edge_labels.discard(0)
    return np.isin(labels, list(edge_labels))


def _bbox(mask: np.ndarray) -> list[int] | None:
    ys, xs = np.nonzero(mask)
    if not len(xs):
        return None
    return [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]


def analyze_image(
    image: Image.Image,
    *,
    requested_transparent: bool = False,
) -> dict[str, Any]:
    rgba = np.asarray(image.convert("RGBA"))
    rgb = rgba[:, :, :3]
    alpha = rgba[:, :, 3]
    height, width = alpha.shape
    border = _border_mask(width, height, _border_width(width, height))
    alpha_min = int(alpha.min())
    alpha_max = int(alpha.max())
    alpha_present = image.mode in {"RGBA", "LA", "PA"} or (
        image.mode == "P" and "transparency" in image.info
    )
    transparent_border_ratio = float(np.mean(alpha[border] <= 8))
    fake_checkerboard = False
    residual_foreground_ratio = 0.0
    background_field_ambiguous = False
    errors: list[str] = []

    if alpha_min < 255:
        content_mask = alpha > 8
        background_mode = "transparent-alpha"
        fake_checkerboard = checkerboard_detected(rgb, content_mask)
        if alpha_min != 0 or alpha_max != 255:
            errors.append("alpha-bearing cutout must span 0 through 255")
        if transparent_border_ratio < TRANSPARENT_BORDER_RATIO:
            errors.append(
                "alpha-bearing cutout border must be at least 95% transparent"
            )
        if fake_checkerboard:
            errors.append("alpha-bearing cutout contains painted checkerboard pixels")
    else:
        background = _background_color(rgb, border)
        distance = _distance(rgb, background)
        border_uniform_ratio = float(
            np.mean(distance[border] <= BACKGROUND_DISTANCE)
        )
        background_mask = _edge_connected_background(
            distance <= BACKGROUND_DISTANCE,
            border,
        )
        content_mask = ~background_mask
        residual_foreground_ratio = float(np.mean(content_mask))
        fake_checkerboard = checkerboard_detected(rgb, border)
        background_mode = "opaque-uniform"
        if fake_checkerboard:
            background_mode = "opaque-checkerboard"
            errors.append("fake checkerboard transparency is not allowed")
        elif border_uniform_ratio < BORDER_UNIFORM_RATIO:
            background_mode = "opaque-nonuniform"
            errors.append("cutout background is not a uniform edge-connected field")

    box = _bbox(content_mask)
    if box is None:
        errors.append("scene contains no detectable foreground")
        coverage = 0.0
    else:
        left, top, right, bottom = box
        coverage = (right - left) * (bottom - top) / float(width * height)
        margins = (
            left / width,
            top / height,
            (width - right) / width,
            (height - bottom) / height,
        )
        bbox_mask = content_mask[top:bottom, left:right]
        bbox_fill_ratio = float(np.mean(bbox_mask))
        bbox_edge_fill = (
            float(np.mean(bbox_mask[0, :])),
            float(np.mean(bbox_mask[-1, :])),
            float(np.mean(bbox_mask[:, 0])),
            float(np.mean(bbox_mask[:, -1])),
        )
        background_field_ambiguous = (
            alpha_min == 255
            and coverage >= 0.15
            and bbox_fill_ratio >= 0.94
            and min(bbox_edge_fill) >= 0.85
        )
        if alpha_min == 255 and (
            residual_foreground_ratio > 0.55 or min(margins) < 0.05
        ):
            background_mode = "opaque-nonuniform"
            errors.append(
                "opaque cutout retains excessive interior background or texture"
            )
        if background_field_ambiguous:
            background_mode = "opaque-nonuniform"
            errors.append(
                "opaque cutout contains an ambiguous filled background field"
            )
    if requested_transparent and alpha_min == 255:
        if not alpha_present:
            errors.append("transparent scene must be stored with an alpha channel")
        errors.append("transparent scene alpha must span 0 through 255")
        errors.append("transparent scene border must be at least 95% transparent")

    background_color = _background_color(rgb, border)
    return {
        "status": "PASS" if not errors else "BLOCK",
        "generatedCanvas": [width, height],
        "contentBBox": box,
        "contentCoverage": round(coverage, 6),
        "backgroundMode": background_mode,
        "backgroundColor": [int(round(value)) for value in background_color],
        "alpha": {
            "present": alpha_present,
            "min": alpha_min,
            "max": alpha_max,
            "transparentBorderRatio": round(transparent_border_ratio, 6),
        },
        "checkerboardDetected": fake_checkerboard,
        "residualForegroundRatio": round(residual_foreground_ratio, 6),
        "backgroundFieldAmbiguous": background_field_ambiguous,
        "errors": errors,
    }


def analyze_scene(
    path: str | Path,
    *,
    requested_transparent: bool = False,
) -> dict[str, Any]:
    source = Path(path)
    with Image.open(source) as image:
        report = analyze_image(
            image.copy(),
            requested_transparent=requested_transparent,
        )
    report["sha256"] = sha256(source)
    return report


def load_scene_receipt(path: str | Path) -> dict[str, Any] | None:
    sidecar = Path(str(path) + ".safe.json")
    try:
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _opaque_cutout(image: Image.Image) -> Image.Image:
    rgb = np.asarray(image.convert("RGB"))
    height, width, _channels = rgb.shape
    border = _border_mask(width, height, _border_width(width, height))
    background = _background_color(rgb, border)
    distance = _distance(rgb, background)
    background_mask = _edge_connected_background(
        distance <= BACKGROUND_DISTANCE,
        border,
    )
    alpha = np.full((height, width), 255, dtype=np.uint8)
    alpha[background_mask] = 0
    rgba = np.dstack((rgb, alpha))
    return Image.fromarray(rgba, mode="RGBA")


def crop_with_padding(
    image: Image.Image,
    box: list[int] | tuple[int, int, int, int],
    *,
    padding_ratio: float = 0.025,
) -> Image.Image:
    left, top, right, bottom = (int(value) for value in box)
    pad = max(2, int(round(max(right - left, bottom - top) * padding_ratio)))
    return image.crop(
        (
            max(0, left - pad),
            max(0, top - pad),
            min(image.width, right + pad),
            min(image.height, bottom + pad),
        )
    )


def cutout_scene(
    path: str | Path,
    *,
    requested_transparent: bool = False,
    padding_ratio: float = 0.025,
) -> tuple[Image.Image, dict[str, Any]]:
    source = Path(path)
    with Image.open(source) as opened:
        image = opened.copy()
    report = analyze_image(
        image,
        requested_transparent=requested_transparent,
    )
    report["sha256"] = sha256(source)
    if report["status"] != "PASS" or report["contentBBox"] is None:
        raise ValueError("scene cutout validation failed: " + "; ".join(report["errors"]))
    if report["backgroundMode"] == "transparent-alpha":
        prepared = image.convert("RGBA")
    else:
        prepared = _opaque_cutout(image)
    return (
        crop_with_padding(
            prepared,
            report["contentBBox"],
            padding_ratio=padding_ratio,
        ),
        report,
    )
