from __future__ import annotations

import csv
import os
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "business-plan-writer"
SCRIPT = (
    PLUGIN
    / "skills"
    / "fill-hwpx-template"
    / "scripts"
    / "hwpx_placeholders.py"
)
DEMO = PLUGIN / "assets" / "demo" / "demo-business-plan.hwpx"


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def text_of(node: ET.Element) -> str:
    return "".join(
        item.text or "" for item in node.iter() if local_name(item.tag) == "t"
    ).strip()


def attributes(node: ET.Element) -> dict[str, str]:
    return {local_name(key): value for key, value in node.attrib.items()}


def approved_values(problem: str) -> dict[str, object]:
    return {
        "_approval": {
            "status": "APPROVED",
            "approved_by": "outline test",
            "approved_at": "2026-08-16T00:00:00Z",
            "source_draft": "test fixture",
        },
        "_claim_free": {
            "{회사명}": "회사명 식별값",
        },
        "values": {
            "{30일실행계획}": "1주차 확인, 2주차 제작, 3주차 검증, 4주차 개선 [P001 | 실행계획]",
            "{문제정의}": problem,
            "{시장근거}": "공식 출처와 기준일을 확인한다. [E001 | 공식자료]",
            "{회사명}": "모두랩",
        },
    }


def write_test_registry(path: Path) -> None:
    fieldnames = [
        "evidence_id",
        "evidence_type",
        "inline_citation",
        "related_section",
        "statement",
        "source_name",
        "source_path_or_url",
        "published_or_recorded_date",
        "base_date",
        "unit",
        "checked_on",
        "status",
        "limitations",
        "notes",
    ]
    rows = [
        ("E001", "external", "공식자료", "공식 근거", "기관", "https://example.com/e1", "PASS"),
        ("E002", "external", "보조자료", "보조 근거", "기관", "https://example.com/e2", "PASS"),
        ("U001", "user", "사용자 자료", "사용자 제공 사실", "사용자", "inputs/user-note.txt", "CONFIRMED"),
        ("H001", "hypothesis", "검증가설", "검증가설", "", "", "HYPOTHESIS"),
        ("P001", "plan", "실행계획", "실행계획", "", "", "PLAN"),
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for evidence_id, evidence_type, inline_citation, statement, source_name, source_path, status in rows:
            writer.writerow(
                {
                    "evidence_id": evidence_id,
                    "evidence_type": evidence_type,
                    "inline_citation": inline_citation,
                    "related_section": "test",
                    "statement": statement,
                    "source_name": source_name,
                    "source_path_or_url": source_path,
                    "published_or_recorded_date": "",
                    "base_date": "",
                    "unit": "",
                    "checked_on": "2026-08-16" if evidence_id[0] in {"E", "U"} else "",
                    "status": status,
                    "limitations": "",
                    "notes": "",
                }
            )


def run_fill_source(
    source: Path,
    values: Path,
    output: Path,
    *extra: str,
) -> subprocess.CompletedProcess[str]:
    registry = values.with_name(values.stem + "-evidence.csv")
    if not registry.exists():
        write_test_registry(registry)
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "fill",
            str(source),
            "--values",
            str(values),
            "--output",
            str(output),
            "--evidence-registry",
            str(registry),
            *extra,
        ],
        cwd=ROOT,
        env={**os.environ, "PYTHONIOENCODING": "cp1252"},
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )


def run_fill(
    values: Path,
    output: Path,
    *extra: str,
) -> subprocess.CompletedProcess[str]:
    return run_fill_source(DEMO, values, output, *extra)


def write_approved_values(path: Path, mapping: dict[str, str]) -> None:
    document = {
        "_approval": {
            "status": "APPROVED",
            "approved_by": "outline test",
            "approved_at": "2026-08-16T00:00:00Z",
            "source_draft": "test fixture",
        },
        "_claim_free": {
            marker: "식별·라벨 값"
            for marker in mapping
            if marker == "{회사명}"
        },
        "values": mapping,
    }
    path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_archive_with_section(
    source: Path,
    output: Path,
    section_text: str,
) -> None:
    with zipfile.ZipFile(source) as archive:
        with zipfile.ZipFile(output, "w") as target:
            for name in archive.namelist():
                info = archive.getinfo(name)
                data = (
                    section_text.encode("utf-8")
                    if name == "Contents/section0.xml"
                    else archive.read(name)
                )
                target.writestr(info, data)


class HwpxOutlineFormattingTests(unittest.TestCase):
    def test_outline_lines_receive_role_styles_and_hanging_indents(self) -> None:
        outline = "\n".join(
            [
                "o 문제와 검증 원칙",
                "- 공개자료와 사용자 자료를 분리하고 확인되지 않은 수치는 가설로 둔다. [H001 | 검증가설]",
                "o 실행 판단 기준",
                "- 원료·안전성·제조·고객 행동지표가 확인될 때만 다음 단계로 진행한다. [P001 | 실행계획]",
            ]
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            values = root / "values.json"
            output = root / "outlined.hwpx"
            values.write_text(
                json.dumps(approved_values(outline), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            completed = run_fill(values, output)
            self.assertEqual(
                completed.returncode,
                0,
                completed.stdout + completed.stderr,
            )

            with zipfile.ZipFile(output) as archive:
                header = ET.fromstring(archive.read("Contents/header.xml"))
                section = ET.fromstring(archive.read("Contents/section0.xml"))

            expected = outline.splitlines()
            paragraphs = [
                node for node in section.iter() if local_name(node.tag) == "p"
            ]
            records = []
            for index, paragraph in enumerate(paragraphs):
                text = text_of(paragraph)
                if text not in expected:
                    continue
                paragraph_attrs = attributes(paragraph)
                run = next(
                    node for node in paragraph.iter() if local_name(node.tag) == "run"
                )
                records.append(
                    {
                        "index": index,
                        "text": text,
                        "para": paragraph_attrs["paraPrIDRef"],
                        "char": attributes(run)["charPrIDRef"],
                    }
                )

            self.assertEqual([record["text"] for record in records], expected)
            self.assertEqual(
                [record["index"] for record in records],
                list(range(records[0]["index"], records[0]["index"] + 4)),
            )
            heading_para = {records[0]["para"], records[2]["para"]}
            detail_para = {records[1]["para"], records[3]["para"]}
            heading_char = {records[0]["char"], records[2]["char"]}
            detail_char = {records[1]["char"], records[3]["char"]}
            self.assertEqual(len(heading_para), 1)
            self.assertEqual(len(detail_para), 1)
            self.assertNotEqual(heading_para, detail_para)
            self.assertEqual(len(heading_char), 1)
            self.assertEqual(len(detail_char), 1)

            para_defs = {
                attributes(node).get("id"): node
                for node in header.iter()
                if local_name(node.tag) == "paraPr"
            }
            heading_def = para_defs[next(iter(heading_para))]
            detail_def = para_defs[next(iter(detail_para))]
            self.assertEqual(
                {attributes(node).get("value") for node in heading_def.iter() if local_name(node.tag) == "left"},
                {"1200"},
            )
            self.assertEqual(
                {attributes(node).get("value") for node in detail_def.iter() if local_name(node.tag) == "left"},
                {"2400"},
            )
            for definition in (heading_def, detail_def):
                self.assertEqual(
                    {attributes(node).get("value") for node in definition.iter() if local_name(node.tag) == "intent"},
                    {"-1200"},
                )

            char_defs = {
                attributes(node).get("id"): node
                for node in header.iter()
                if local_name(node.tag) == "charPr"
            }
            heading_definition = char_defs[next(iter(heading_char))]
            detail_definition = char_defs[next(iter(detail_char))]
            self.assertTrue(
                any(local_name(node.tag) == "bold" for node in heading_definition)
            )
            self.assertFalse(
                any(local_name(node.tag) == "bold" for node in detail_definition)
            )

            para_container = next(
                node for node in header.iter() if local_name(node.tag) == "paraProperties"
            )
            self.assertEqual(
                int(attributes(para_container)["itemCnt"]),
                sum(local_name(node.tag) == "paraPr" for node in list(para_container)),
            )
            char_container = next(
                node for node in header.iter() if local_name(node.tag) == "charProperties"
            )
            self.assertEqual(
                int(attributes(char_container)["itemCnt"]),
                sum(local_name(node.tag) == "charPr" for node in list(char_container)),
            )

    def test_long_prose_blocks_by_default_and_requires_explicit_override(self) -> None:
        prose = " ".join(["근거를 확인하지 않은 장문 서술형 문단이다."] * 20)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            values = root / "values.json"
            output = root / "prose.hwpx"
            values.write_text(
                json.dumps(approved_values(prose), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            blocked = run_fill(values, output)
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("근거 또는 상태 표지가 필요합니다", blocked.stdout)
            self.assertFalse(output.exists())
            untraced_override = run_fill(
                values,
                root / "untraced-prose.hwpx",
                "--allow-prose-values",
            )
            self.assertNotEqual(untraced_override.returncode, 0)
            self.assertIn("근거 또는 상태 표지가 필요합니다", untraced_override.stdout)
            values.write_text(
                json.dumps(
                    approved_values(prose + " [E001 | 공식자료]"),
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            layout_blocked = run_fill(values, output)
            self.assertNotEqual(layout_blocked.returncode, 0)
            self.assertIn(
                "장문 HWPX 답변은 기본 개조식이어야 합니다",
                layout_blocked.stdout,
            )
            self.assertFalse(output.exists())

            allowed = run_fill(values, output, "--allow-prose-values")
            self.assertEqual(allowed.returncode, 0, allowed.stdout + allowed.stderr)
            self.assertTrue(output.is_file())

    def test_detail_claims_require_trace_ids(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            missing_values = root / "missing.json"
            valid_values = root / "valid.json"
            write_approved_values(
                missing_values,
                {
                    "{문제정의}": "o 핵심항목\n- 근거 ID가 없는 주장",
                    "{회사명}": "모두랩",
                    "{시장근거}": "확인 [E001 | 공식자료]",
                    "{30일실행계획}": "실행 [P001 | 실행계획]",
                },
            )
            valid_outline = "\n".join(
                [
                    "o 외부 근거",
                    "- 공식 통계로 확인한다. [E001 | 공식자료]",
                    "o 사용자 제공",
                    "- 대표자 경력은 사용자 자료에서 확인한다. [U001 | 사용자 자료]",
                    "o 검증가설",
                    "- 고객군은 아직 검증할 가설이다. [H001 | 검증가설]",
                    "o 실행계획",
                    "- 다음 단계에서 인터뷰를 진행한다. [P001 | 실행계획]",
                ]
            )
            write_approved_values(
                valid_values,
                {
                    "{문제정의}": valid_outline,
                    "{회사명}": "모두랩",
                    "{시장근거}": "확인 [E001 | 공식자료]",
                    "{30일실행계획}": "실행 [P001 | 실행계획]",
                },
            )
            missing = run_fill(missing_values, root / "missing.hwpx")
            valid = run_fill(valid_values, root / "valid.hwpx")
            self.assertNotEqual(missing.returncode, 0)
            self.assertIn("근거 또는 상태 표지가 필요합니다", missing.stdout)
            self.assertEqual(valid.returncode, 0, valid.stdout + valid.stderr)

    def test_claim_ids_require_matching_evidence_registry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            values = root / "values.json"
            output = root / "without-registry.hwpx"
            values.write_text(
                json.dumps(
                    approved_values("o 핵심항목\n- 공식 근거 주장 [E001 | 공식자료]"),
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            missing_registry = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "fill",
                    str(DEMO),
                    "--values",
                    str(values),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                env={**os.environ, "PYTHONIOENCODING": "cp1252"},
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(missing_registry.returncode, 0)
            self.assertIn("--evidence-registry", missing_registry.stdout)

            registry = values.with_name(values.stem + "-evidence.csv")
            write_test_registry(registry)
            registry_text = registry.read_text(encoding="utf-8-sig")
            registry.write_text(
                registry_text.replace("E001,external", "E001,plan", 1),
                encoding="utf-8-sig",
            )
            mismatched = run_fill(values, root / "mismatched.hwpx")
            self.assertNotEqual(mismatched.returncode, 0)
            self.assertIn("evidence_type은 external", mismatched.stdout)

    def test_registry_rows_labels_and_required_fields_fail_closed(self) -> None:
        cases = {
            "missing_id": (
                "근거목록.csv에 없는 주장 ID",
                lambda rows: [
                    row for row in rows if row["evidence_id"] != "E001"
                ],
            ),
            "duplicate_id": (
                "중복 evidence_id",
                lambda rows: rows
                + [
                    dict(
                        next(
                            row
                            for row in rows
                            if row["evidence_id"] == "E001"
                        )
                    )
                ],
            ),
            "missing_statement": (
                "E001 statement 값이 필요합니다",
                lambda rows: [
                    {**row, "statement": ""}
                    if row["evidence_id"] == "E001"
                    else row
                    for row in rows
                ],
            ),
            "missing_status": (
                "E001 status 값이 필요합니다",
                lambda rows: [
                    {**row, "status": ""}
                    if row["evidence_id"] == "E001"
                    else row
                    for row in rows
                ],
            ),
            "missing_source_name": (
                "E001 source_name 값이 필요합니다",
                lambda rows: [
                    {**row, "source_name": ""}
                    if row["evidence_id"] == "E001"
                    else row
                    for row in rows
                ],
            ),
            "missing_source_path": (
                "E001 source_path_or_url 값이 필요합니다",
                lambda rows: [
                    {**row, "source_path_or_url": ""}
                    if row["evidence_id"] == "E001"
                    else row
                    for row in rows
                ],
            ),
            "missing_checked_on": (
                "E001 checked_on 값이 필요합니다",
                lambda rows: [
                    {**row, "checked_on": ""}
                    if row["evidence_id"] == "E001"
                    else row
                    for row in rows
                ],
            ),
            "label_mismatch": (
                "inline_citation",
                lambda rows: [
                    {**row, "inline_citation": "다른자료"}
                    if row["evidence_id"] == "E001"
                    else row
                    for row in rows
                ],
            ),
            "citation_whitespace": (
                "앞뒤 공백",
                lambda rows: [
                    {**row, "inline_citation": " 공식자료 "}
                    if row["evidence_id"] == "E001"
                    else row
                    for row in rows
                ],
            ),
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, (message, mutate) in cases.items():
                with self.subTest(name=name):
                    values = root / f"{name}.json"
                    output = root / f"{name}.hwpx"
                    values.write_text(
                        json.dumps(
                            approved_values(
                                "o 핵심항목\n- 공식 주장 [E001 | 공식자료]"
                            ),
                            ensure_ascii=False,
                            indent=2,
                        ),
                        encoding="utf-8",
                    )
                    registry = values.with_name(
                        values.stem + "-evidence.csv"
                    )
                    write_test_registry(registry)
                    with registry.open(
                        "r",
                        encoding="utf-8-sig",
                        newline="",
                    ) as handle:
                        reader = csv.DictReader(handle)
                        fieldnames = list(reader.fieldnames or [])
                        rows = list(reader)
                    with registry.open(
                        "w",
                        encoding="utf-8",
                        newline="",
                    ) as handle:
                        writer = csv.DictWriter(
                            handle,
                            fieldnames=fieldnames,
                        )
                        writer.writeheader()
                        writer.writerows(mutate(rows))
                    completed = run_fill(values, output)
                    self.assertNotEqual(completed.returncode, 0)
                    self.assertIn(message, completed.stdout)

    def test_strict_marker_parser_and_multiple_markers(self) -> None:
        malformed = {
            "id_only": "o 핵심항목\n- 주장 [E001]",
            "blank_label": "o 핵심항목\n- 주장 [E001 |   ]",
            "nested": "o 핵심항목\n- 주장 [E001 | x [U999 | y]",
            "extra_pipe": "o 핵심항목\n- 주장 [E001 | 기관 | 2025]",
            "malformed_before_valid": (
                "o 핵심항목\n- 주장 "
                "[E999 | 기관 | 2025][E001 | 공식자료]"
            ),
            "nested_before_valid": (
                "o 핵심항목\n- 주장 "
                "[E999 | x [U999 | y][E001 | 공식자료]"
            ),
            "unregistered_before_valid": (
                "o 핵심항목\n- 주장 "
                "[E999 | 미등록자료][E001 | 공식자료]"
            ),
            "del_control": "o 핵심항목\n- 주장 [E001 | 공식\u007f자료]",
            "c1_control": "o 핵심항목\n- 주장 [E001 | 공식\u0085자료]",
            "bidi_control": "o 핵심항목\n- 주장 [E001 | 공식\u202e자료]",
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, problem in malformed.items():
                with self.subTest(name=name):
                    values = root / f"{name}.json"
                    values.write_text(
                        json.dumps(
                            approved_values(problem),
                            ensure_ascii=False,
                            indent=2,
                        ),
                        encoding="utf-8",
                    )
                    completed = run_fill(
                        values,
                        root / f"{name}.hwpx",
                    )
                    self.assertNotEqual(completed.returncode, 0)

            valid_values = root / "multiple.json"
            valid_values.write_text(
                json.dumps(
                    approved_values(
                        "o 핵심항목\n- 복수 근거 주장 "
                        "[E001 | 공식자료][E002 | 보조자료]"
                    ),
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            valid_registry = valid_values.with_name(
                valid_values.stem + "-evidence.csv"
            )
            write_test_registry(valid_registry)
            registry_text = valid_registry.read_text(
                encoding="utf-8-sig"
            )
            valid_registry.write_text(
                registry_text,
                encoding="utf-8",
            )
            valid = run_fill(valid_values, root / "multiple.hwpx")
            self.assertEqual(
                valid.returncode,
                0,
                valid.stdout + valid.stderr,
            )

            missing_values = root / "missing-followup.json"
            missing_values.write_text(
                json.dumps(
                    approved_values(
                        "o 핵심항목\n- 누락 근거 주장 "
                        "[E001 | 공식자료][E003 | 누락자료]"
                    ),
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            missing = run_fill(
                missing_values,
                root / "missing-followup.hwpx",
            )
            self.assertNotEqual(missing.returncode, 0)
            self.assertIn("E003", missing.stdout)

    def test_claim_free_is_explicit_and_inline_suffix_cannot_hide_marker(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            values = root / "values.json"
            document = approved_values(
                "짧은 주장 [H001 | 검증가설]"
            )
            document.pop("_claim_free")
            values.write_text(
                json.dumps(
                    document,
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            default_claim = run_fill(
                values,
                root / "default-claim.hwpx",
            )
            self.assertNotEqual(default_claim.returncode, 0)
            self.assertIn("{회사명}", default_claim.stdout)

            with zipfile.ZipFile(DEMO) as archive:
                section_text = archive.read(
                    "Contents/section0.xml"
                ).decode("utf-8")
            source = root / "inline-suffix.hwpx"
            write_archive_with_section(
                DEMO,
                source,
                section_text.replace(
                    "{문제정의}",
                    "{문제정의} 고정문구",
                    1,
                ),
            )
            source_values = root / "source-values.json"
            source_values.write_text(
                json.dumps(
                    approved_values(
                        "짧은 주장 [H001 | 검증가설]"
                    ),
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            blocked = run_fill_source(
                source,
                source_values,
                root / "inline-suffix-result.hwpx",
            )
            self.assertNotEqual(blocked.returncode, 0)
            log = (root / "inline-suffix-result-replacement-log.csv").read_text(
                encoding="utf-8-sig"
            )
            self.assertIn("문단에 단독", log)

    def test_identical_outline_fills_are_byte_deterministic(self) -> None:
        outline = "o 핵심항목\n- 결정적 문단 식별자를 사용한다. [P001 | 실행계획]"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            values = root / "values.json"
            first = root / "first.hwpx"
            second = root / "second.hwpx"
            values.write_text(
                json.dumps(approved_values(outline), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            first_run = run_fill(values, first)
            second_run = run_fill(values, second)
            self.assertEqual(first_run.returncode, 0, first_run.stdout + first_run.stderr)
            self.assertEqual(second_run.returncode, 0, second_run.stdout + second_run.stderr)
            self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_long_prose_gate_uses_exact_200_character_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            short_values = root / "short.json"
            blocked_values = root / "blocked.json"
            trace = " [H001 | 검증가설]"
            short_problem = "가" * (199 - len(trace)) + trace
            blocked_problem = "가" * (200 - len(trace)) + trace
            self.assertEqual(len(short_problem), 199)
            self.assertEqual(len(blocked_problem), 200)
            write_approved_values(
                short_values,
                {
                    "{문제정의}": short_problem,
                    "{회사명}": "모두랩",
                    "{시장근거}": "확인 [E001 | 공식자료]",
                    "{30일실행계획}": "실행 [P001 | 실행계획]",
                },
            )
            write_approved_values(
                blocked_values,
                {
                    "{문제정의}": blocked_problem,
                    "{회사명}": "모두랩",
                    "{시장근거}": "확인 [E001 | 공식자료]",
                    "{30일실행계획}": "실행 [P001 | 실행계획]",
                },
            )
            allowed = run_fill(short_values, root / "short.hwpx")
            blocked = run_fill(blocked_values, root / "blocked.hwpx")
            self.assertEqual(allowed.returncode, 0, allowed.stdout + allowed.stderr)
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("장문 HWPX 답변은 기본 개조식이어야 합니다", blocked.stdout)

    def test_mixed_or_malformed_outline_values_block(self) -> None:
        invalid_values = {
            "mixed": "o 핵심항목\n표시 없는 장문\n- 세부내용 [E001 | 공식자료]",
            "detail_first": "- 세부내용 [E001 | 공식자료]\no 핵심항목\n- 다음 세부내용 [E002 | 보조자료]",
            "heading_without_detail": "o 핵심항목",
            "consecutive_headings": "o 첫 항목\no 둘째 항목\n- 세부내용 [E001 | 공식자료]",
            "orphan_last_heading": "o 핵심항목\n- 세부내용 [E001 | 공식자료]\no 마지막 항목",
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, invalid in invalid_values.items():
                with self.subTest(name=name):
                    values = root / f"{name}.json"
                    output = root / f"{name}.hwpx"
                    values.write_text(
                        json.dumps(
                            approved_values(invalid),
                            ensure_ascii=False,
                            indent=2,
                        ),
                        encoding="utf-8",
                    )
                    completed = run_fill(
                        values,
                        output,
                        "--allow-prose-values",
                    )
                    self.assertNotEqual(completed.returncode, 0)
                    self.assertFalse(output.exists())

    def test_all_outline_prefixes_and_blank_line_removal(self) -> None:
        outline = "\n".join(
            [
                "  ○ 첫 핵심항목  ",
                "",
                "  • 첫 세부내용 [E001 | 공식자료]  ",
                "\t□ 둘째 핵심항목",
                "",
                "  ▪ 둘째 세부내용 [P001 | 실행계획]",
            ]
        )
        expected = [
            "○ 첫 핵심항목",
            "• 첫 세부내용 [E001 | 공식자료]",
            "□ 둘째 핵심항목",
            "▪ 둘째 세부내용 [P001 | 실행계획]",
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            values = root / "values.json"
            output = root / "prefixes.hwpx"
            values.write_text(
                json.dumps(approved_values(outline), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            completed = run_fill(values, output)
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            with zipfile.ZipFile(output) as archive:
                section = ET.fromstring(archive.read("Contents/section0.xml"))
            paragraphs = [
                text_of(node)
                for node in section.iter()
                if local_name(node.tag) == "p" and text_of(node) in expected
            ]
            self.assertEqual(paragraphs, expected)

    def test_each_placeholder_preserves_its_own_base_character_style(self) -> None:
        mapping = {
            "{문제정의}": "o 문제 핵심\n- 문제 세부 [E001 | 공식자료]",
            "{시장근거}": "o 시장 핵심\n- 시장 세부 [E002 | 보조자료]",
            "{30일실행계획}": "실행 [P001 | 실행계획]",
            "{회사명}": "모두랩",
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            values = root / "values.json"
            output = root / "heterogeneous.hwpx"
            write_approved_values(values, mapping)
            completed = run_fill(values, output)
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            with zipfile.ZipFile(output) as archive:
                header = ET.fromstring(archive.read("Contents/header.xml"))
                section = ET.fromstring(archive.read("Contents/section0.xml"))
            char_defs = {
                attributes(node).get("id"): node
                for node in header.iter()
                if local_name(node.tag) == "charPr"
            }
            text_to_height = {}
            for paragraph in section.iter():
                if local_name(paragraph.tag) != "p":
                    continue
                text = text_of(paragraph)
                if text not in {"o 문제 핵심", "- 문제 세부 [E001 | 공식자료]", "o 시장 핵심", "- 시장 세부 [E002 | 보조자료]"}:
                    continue
                run = next(
                    node for node in paragraph.iter() if local_name(node.tag) == "run"
                )
                char_id = attributes(run)["charPrIDRef"]
                text_to_height[text] = attributes(char_defs[char_id])["height"]
            self.assertEqual(text_to_height["o 문제 핵심"], "1400")
            self.assertEqual(text_to_height["- 문제 세부 [E001 | 공식자료]"], "1400")
            self.assertEqual(text_to_height["o 시장 핵심"], "1100")
            self.assertEqual(text_to_height["- 시장 세부 [E002 | 보조자료]"], "1100")

    def test_marker_run_is_styled_without_changing_leading_control_run(self) -> None:
        with zipfile.ZipFile(DEMO) as archive:
            section_text = archive.read("Contents/section0.xml").decode("utf-8")
        marker = "{문제정의}"
        marker_at = section_text.index(marker)
        paragraph_start = section_text.rfind("<hp:p", 0, marker_at)
        paragraph_open_end = section_text.index(">", paragraph_start) + 1
        control_run = '<hp:run charPrIDRef="0"><hp:t></hp:t></hp:run>'
        section_with_control = (
            section_text[:paragraph_open_end]
            + control_run
            + section_text[paragraph_open_end:]
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "control-run.hwpx"
            values = root / "values.json"
            output = root / "filled.hwpx"
            write_archive_with_section(DEMO, source, section_with_control)
            values.write_text(
                json.dumps(
                    approved_values("o 핵심항목\n- 세부내용 [E001 | 공식자료]"),
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            completed = run_fill_source(source, values, output)
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            with zipfile.ZipFile(output) as archive:
                section = ET.fromstring(archive.read("Contents/section0.xml"))
            heading = next(
                node
                for node in section.iter()
                if local_name(node.tag) == "p" and text_of(node) == "o 핵심항목"
            )
            runs = [
                node for node in heading.iter() if local_name(node.tag) == "run"
            ]
            self.assertEqual(attributes(runs[0])["charPrIDRef"], "0")
            self.assertNotEqual(attributes(runs[-1])["charPrIDRef"], "0")

            split_source = root / "split-run.hwpx"
            split_output = root / "split-output.hwpx"
            split_marker = (
                "{문제</hp:t></hp:run>"
                '<hp:run charPrIDRef="8"><hp:t>정의}'
            )
            write_archive_with_section(
                DEMO,
                split_source,
                section_text.replace(marker, split_marker, 1),
            )
            blocked = run_fill_source(split_source, values, split_output)
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("BLOCKS: 1", blocked.stdout)


if __name__ == "__main__":
    unittest.main()
