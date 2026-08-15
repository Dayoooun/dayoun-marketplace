from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


class FixtureError(ValueError):
    pass


def validate_matrix() -> dict[str, object]:
    matrix = json.loads(
        (REPO_ROOT / "contracts" / "fixtures" / "release" / "matrix.json").read_text(encoding="utf-8")
    )
    cases = {item["id"]: item for item in matrix["cases"]}
    if len(cases) != 10 or matrix.get("expectedRunCount") != 30:
        raise FixtureError("approved matrix must contain ten unique cases and 30 runs")
    for image_case in ("R04-I", "R07-I"):
        case = cases.get(image_case)
        if not case or case.get("rendererMode") != "image-first" or case.get("visual") != ["PPTX", "PDF"]:
            raise FixtureError(f"{image_case} does not carry image-first OCR and dual visual gates")
    r02 = cases.get("R02")
    if not r02 or set(r02.get("visual", [])) != {"HWPX", "PPTX", "PDF"}:
        raise FixtureError("R02 must require both selected-output visual gates")
    return matrix


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the locked 1.0 release fixture contract")
    parser.add_argument("--require-ppt-modes", default="scene-deck,image-first")
    parser.add_argument("--require-ocr-association", default="R04-I,R07-I")
    parser.add_argument("--require-original-oracle-negatives", action="store_true")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    if not args.strict or not args.require_original_oracle_negatives:
        print("BLOCK: strict original-oracle negative validation is mandatory", file=sys.stderr)
        return 2
    try:
        matrix = validate_matrix()
        modes = {case.get("rendererMode") for case in matrix["cases"] if case.get("rendererMode")}
        if modes != set(args.require_ppt_modes.split(",")):
            raise FixtureError(f"renderer mode coverage mismatch: {sorted(modes)}")
        required_ocr = set(args.require_ocr_association.split(","))
        actual_ocr = {case["id"] for case in matrix["cases"] if case.get("ocrSuite")}
        if required_ocr != actual_ocr:
            raise FixtureError(f"OCR association coverage mismatch: {sorted(actual_ocr)}")
    except (OSError, json.JSONDecodeError, KeyError, FixtureError) as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"status": "PASS", "cases": 10, "runs": 30}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
