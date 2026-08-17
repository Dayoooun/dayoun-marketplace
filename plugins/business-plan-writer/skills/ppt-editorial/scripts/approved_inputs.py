from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import rfc8785

DIGEST_PREFIX = "sha256:"
NORMALIZER_VERSION = "dayoun-visible-text-v1"
MAPPER_VERSION = "dayoun-region-map-v1"
SCENE_RENDERER_VERSION = "scene-deck-v3"
IMAGE_RENDERER_VERSION = "image-first-v1"


class ApprovalError(ValueError):
    pass


def _strict_object(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ApprovalError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: str | Path) -> Any:
    try:
        return json.loads(
            Path(path).read_text(encoding="utf-8"),
            object_pairs_hook=_strict_object,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ApprovalError(f"non-finite value: {value}")
            ),
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise ApprovalError(f"cannot load approved JSON {path}: {exc}") from exc


def canonical_bytes(value: Any) -> bytes:
    try:
        return rfc8785.dumps(value)
    except Exception as exc:
        raise ApprovalError(f"RFC 8785 canonicalization failed: {exc}") from exc


def digest_value(value: Any) -> str:
    return DIGEST_PREFIX + hashlib.sha256(canonical_bytes(value)).hexdigest()


def digest_bytes(data: bytes) -> str:
    return DIGEST_PREFIX + hashlib.sha256(data).hexdigest()


def store_value(store: Path, value: Any) -> str:
    canonical = canonical_bytes(value)
    digest = digest_bytes(canonical)
    target = store / digest.removeprefix(DIGEST_PREFIX)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.read_bytes() != canonical:
        raise ApprovalError(f"content-address collision: {digest}")
    target.write_bytes(canonical)
    return digest


def resolve_value(store: Path, digest: str) -> Any:
    if not digest.startswith(DIGEST_PREFIX) or len(digest) != 71:
        raise ApprovalError(f"invalid digest: {digest}")
    path = store / digest.removeprefix(DIGEST_PREFIX)
    if not path.is_file():
        raise ApprovalError(f"approved input unavailable: {digest}")
    data = path.read_bytes()
    if digest_bytes(data) != digest:
        raise ApprovalError(f"approved input digest mismatch: {digest}")
    return json.loads(data.decode("utf-8"))


def build_approval_envelope(
    *,
    payload: dict[str, Any],
    deck_briefs: list[dict[str, Any]],
    visible_manifest: dict[str, Any] | None,
    renderer_mode: str | None,
    approved_by: str,
    approval_revision: int,
    cycle_id: str,
    renderer_version: str,
) -> dict[str, Any]:
    if renderer_mode not in {None, "scene-deck", "image-first"}:
        raise ApprovalError(f"unsupported renderer mode: {renderer_mode}")
    ppt_selected = payload.get("outputs", {}).get("ppt") is True
    if ppt_selected != (renderer_mode is not None):
        raise ApprovalError("renderer mode must exactly match the canonical PPT selection")
    if not ppt_selected and (deck_briefs or visible_manifest is not None):
        raise ApprovalError("non-PPT approval must not contain deck briefs or visible text")
    if renderer_mode is not None and not deck_briefs:
        raise ApprovalError("a PPT renderer requires at least one ordered deck brief")
    if renderer_mode == "image-first" and visible_manifest is None:
        raise ApprovalError("image-first requires a visible-text manifest")
    return {
        "schemaVersion": "1.0.0",
        "payloadDigest": digest_value(payload),
        "selectedOutputs": payload["outputs"],
        "deckBriefDigests": [digest_value(brief) for brief in deck_briefs],
        "visibleTextManifestDigest": digest_value(visible_manifest) if visible_manifest else None,
        "rendererMode": renderer_mode,
        "canonicalization": "RFC8785-JCS",
        "normalizerVersion": NORMALIZER_VERSION,
        "rendererVersion": renderer_version,
        "mapperVersion": MAPPER_VERSION,
        "approvedBy": approved_by,
        "approvedAt": datetime.now(timezone.utc).isoformat(),
        "approvalRevision": approval_revision,
        "cycleId": cycle_id,
    }


def verify_approval_bundle(
    envelope: dict[str, Any],
    *,
    payload: dict[str, Any],
    deck_briefs: list[dict[str, Any]],
    visible_manifest: dict[str, Any] | None,
    expected_mode: str | None,
) -> None:
    if expected_mode == "image-first":
        if visible_manifest is None:
            raise ApprovalError("image-first approval requires visible-text manifest")
        from build_visible_text_manifest import ManifestError, build_manifest

        try:
            derived_manifest = build_manifest(payload, deck_briefs)
        except ManifestError as exc:
            raise ApprovalError(f"visible-text manifest inputs are invalid: {exc}") from exc
        if digest_value(derived_manifest) != digest_value(visible_manifest):
            raise ApprovalError("STALE_APPROVAL: visible-text manifest is not derived from approved briefs")
    actual = {
        "payloadDigest": digest_value(payload),
        "selectedOutputs": payload["outputs"],
        "deckBriefDigests": [digest_value(brief) for brief in deck_briefs],
        "visibleTextManifestDigest": digest_value(visible_manifest) if visible_manifest else None,
        "rendererMode": expected_mode,
        "normalizerVersion": NORMALIZER_VERSION,
        "mapperVersion": MAPPER_VERSION,
    }
    for key, value in actual.items():
        if envelope.get(key) != value:
            raise ApprovalError(f"STALE_APPROVAL: {key} does not match approved value")


def resolve_approved_bundle(
    store: Path,
    envelope: dict[str, Any],
    *,
    expected_mode: str | None = None,
    expected_renderer_version: str | None = None,
) -> tuple[Any, list[Any], Any | None]:
    payload = resolve_value(store, envelope["payloadDigest"])
    briefs = [resolve_value(store, digest) for digest in envelope["deckBriefDigests"]]
    manifest_digest = envelope.get("visibleTextManifestDigest")
    manifest = resolve_value(store, manifest_digest) if manifest_digest else None
    verify_approval_bundle(
        envelope,
        payload=payload,
        deck_briefs=briefs,
        visible_manifest=manifest,
        expected_mode=expected_mode if expected_mode is not None else envelope.get("rendererMode"),
    )
    if (
        expected_renderer_version is not None
        and envelope.get("rendererVersion") != expected_renderer_version
    ):
        raise ApprovalError("STALE_APPROVAL: rendererVersion does not match current renderer")
    return payload, briefs, manifest


def sha256_file(path: Path) -> str:
    return DIGEST_PREFIX + hashlib.sha256(path.read_bytes()).hexdigest()


def build_image_render_receipt(
    *,
    store: Path,
    approval_digest: str,
    png_dir: Path,
) -> dict[str, Any]:
    envelope = resolve_value(store, approval_digest)
    _payload, briefs, _manifest = resolve_approved_bundle(
        store,
        envelope,
        expected_mode="image-first",
        expected_renderer_version=IMAGE_RENDERER_VERSION,
    )
    slide_ids = [
        f"{brief_index}:{slide['slide']}"
        for brief_index, brief in enumerate(briefs, 1)
        for slide in brief.get("slides", [])
    ]
    pngs = sorted(png_dir.resolve().glob("*.png"))
    if len(slide_ids) != len(pngs):
        raise ApprovalError("rendered image count does not match approved ordered slides")
    return {
        "schemaVersion": "1.0.0",
        "receiptVersion": "dayoun-image-render-receipt-v1",
        "approvalEnvelopeDigest": approval_digest,
        "rendererMode": "image-first",
        "rendererVersion": IMAGE_RENDERER_VERSION,
        "slides": [
            {
                "slideIdentity": slide_id,
                "fileName": path.name,
                "sha256": sha256_file(path),
            }
            for slide_id, path in zip(slide_ids, pngs, strict=True)
        ],
    }


def verify_image_render_receipt(
    receipt: dict[str, Any],
    *,
    approval_digest: str,
    png_dir: Path,
    expected_slide_ids: list[str] | None = None,
) -> None:
    if (
        receipt.get("receiptVersion") != "dayoun-image-render-receipt-v1"
        or receipt.get("approvalEnvelopeDigest") != approval_digest
        or receipt.get("rendererMode") != "image-first"
        or receipt.get("rendererVersion") != IMAGE_RENDERER_VERSION
    ):
        raise ApprovalError("render receipt is stale or belongs to another renderer")
    pngs = sorted(png_dir.resolve().glob("*.png"))
    slides = receipt.get("slides")
    if not isinstance(slides, list) or len(slides) != len(pngs):
        raise ApprovalError("render receipt slide set does not match rendered images")
    if expected_slide_ids is not None and [
        str(record.get("slideIdentity")) for record in slides
    ] != expected_slide_ids:
        raise ApprovalError("render receipt slide identities do not match approved order")
    for record, path in zip(slides, pngs, strict=True):
        if record.get("fileName") != path.name or record.get("sha256") != sha256_file(path):
            raise ApprovalError(f"rendered image changed after receipt: {path.name}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or verify immutable PPT approval inputs")
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build")
    build.add_argument("--payload", type=Path, required=True)
    build.add_argument("--brief", type=Path, action="append", default=[])
    build.add_argument("--manifest", type=Path)
    build.add_argument("--mode", choices=("scene-deck", "image-first"))
    build.add_argument("--approved-by", required=True)
    build.add_argument("--revision", type=int, required=True)
    build.add_argument("--cycle-id", required=True)
    build.add_argument("--renderer-version", required=True)
    build.add_argument("--store", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    verify = subparsers.add_parser("verify")
    verify.add_argument("--approval-digest", required=True)
    verify.add_argument("--store", type=Path, required=True)
    render = subparsers.add_parser("record-render")
    render.add_argument("--approval-digest", required=True)
    render.add_argument("--store", type=Path, required=True)
    render.add_argument("--png-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "build":
            payload = load_json(args.payload)
            briefs = [load_json(path) for path in args.brief]
            manifest = load_json(args.manifest) if args.manifest else None
            envelope = build_approval_envelope(
                payload=payload,
                deck_briefs=briefs,
                visible_manifest=manifest,
                renderer_mode=args.mode,
                approved_by=args.approved_by,
                approval_revision=args.revision,
                cycle_id=args.cycle_id,
                renderer_version=args.renderer_version,
            )
            verify_approval_bundle(
                envelope,
                payload=payload,
                deck_briefs=briefs,
                visible_manifest=manifest,
                expected_mode=args.mode,
            )
            store_value(args.store, payload)
            for brief in briefs:
                store_value(args.store, brief)
            if manifest is not None:
                store_value(args.store, manifest)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            envelope_digest = store_value(args.store, envelope)
            print(envelope_digest)
        elif args.command == "verify":
            envelope = resolve_value(args.store, args.approval_digest)
            resolve_approved_bundle(args.store, envelope)
            print("PASS")
        else:
            receipt = build_image_render_receipt(
                store=args.store,
                approval_digest=args.approval_digest,
                png_dir=args.png_dir,
            )
            print(store_value(args.store, receipt))
    except ApprovalError as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
