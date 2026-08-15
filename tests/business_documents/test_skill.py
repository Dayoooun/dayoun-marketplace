from __future__ import annotations

import ast
import importlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "plugins" / "business-documents" / "skills" / "create-business-documents"
SCRIPTS = SKILL / "scripts"
EXAMPLES = SKILL / "references" / "examples"


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "render_cli.py"), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        check=False,
    )


def load_renderers():
    sys.path.insert(0, str(SCRIPTS))
    try:
        common = importlib.import_module("common")
        quote = importlib.import_module("quote_render")
        profile = importlib.import_module("profile_render")
        notice = importlib.import_module("notice_render")
    finally:
        sys.path.pop(0)
    return common, quote, profile, notice


class BusinessDocumentsSkillTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.common, cls.quote, cls.profile, cls.notice = load_renderers()

    def test_skill_inventory_and_boundary_statement(self) -> None:
        self.assertTrue((SKILL / "SKILL.md").is_file())
        self.assertTrue((SKILL / "agents" / "openai.yaml").is_file())
        for relative in (
            "references/quote.md",
            "references/profile.md",
            "references/official-notice.md",
            "references/examples/quote.json",
            "references/examples/profile.json",
            "references/examples/official.json",
        ):
            self.assertTrue((SKILL / relative).is_file(), relative)
        router = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("사업계획서 10단계의 일부가 아닙니다", router)
        self.assertIn("독립 `business-documents` 플러그인", router)
        self.assertIn("강의 커리큘럼에는 포함하지 않습니다", router)
        self.assertIn("poster", router)
        self.assertIn("Print-to-PDF", router)

    def test_scripts_parse_with_python_311_grammar(self) -> None:
        for path in sorted(SCRIPTS.glob("*.py")):
            with self.subTest(path=path.name):
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path), feature_version=(3, 11))

    def test_quote_vat_and_korean_amount_boundaries(self) -> None:
        items = [{"qty": 3, "unit_price": 333}]
        self.assertEqual(self.quote.calculate_totals(items, "exclusive"), (999, 100, 1099))
        self.assertEqual(self.quote.calculate_totals(items, "inclusive"), (908, 91, 999))
        self.assertEqual(self.quote.kor_amount(0), "영원정")
        self.assertEqual(self.quote.kor_amount(1_650_000), "일백육십오만원정")
        self.assertEqual(self.quote.kor_amount(10_001), "일만일원정")
        self.assertEqual(self.quote.kor_amount(100_000_000), "일억원정")

    def test_quote_placeholders_and_escaping(self) -> None:
        html = self.quote.render(
            {
                "supplier": {},
                "customer": {},
                "title": '<script>alert("x") & test</script>',
                "items": [{"name": "(가상) 품목", "qty": 1, "unit_price": 1000}],
                "vat_mode": "exclusive",
            },
            "clean",
        )
        self.assertIn("[상호 입력]", html)
        self.assertIn("[사업자등록번호 입력]", html)
        self.assertIn(">-<", html)
        self.assertIn("(인)", html)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("&quot;x&quot;", html)
        self.assertIn("&amp;", html)

    def test_profile_order_omission_and_protected_fields(self) -> None:
        html = self.profile.render(
            {
                "name": "(가상) 윤하늘",
                "summary": "(가상) 실무형 기획자",
                "career": [{"org": "(가상) 새봄상사", "role": "기획"}],
                "edu": [{"org": "(가상) 해솔학교", "detail": "과정 수료"}],
                "cert": ["(가상) 실무 인증"],
                "skills": ["문서 기획"],
                "age": "출력되면 안 되는 값 A",
                "gender": "출력되면 안 되는 값 B",
                "marital_status": "출력되면 안 되는 값 C",
                "resident_number": "출력되면 안 되는 값 D",
            },
            "editorial",
        )
        positions = [html.index(label) for label in ("요약", "경력", "교육", "자격", "역량")]
        self.assertEqual(positions, sorted(positions))
        for marker in ("값 A", "값 B", "값 C", "값 D"):
            self.assertNotIn(marker, html)
        empty = self.profile.render({"name": "(가상) 윤하늘"}, "clean")
        for label in ("요약", "경력", "교육", "자격", "역량"):
            self.assertNotIn(f">{label}<", empty)
        self.assertIn("photo-placeholder", empty)

    def test_notice_numbering_date_attachments_and_end_marker(self) -> None:
        data = {
            "org": "(가상) 다온협회",
            "title": "(가상) 협업 안내",
            "date": "2026-08-08",
            "body": [
                {
                    "text": "첫 항목",
                    "children": [
                        {"text": "하위 항목", "children": [{"text": "세부 항목"}]}
                    ],
                }
            ],
            "attach": ["(가상) 일정표 1부"],
        }
        official = self.notice.render(data, "official")
        self.assertIn("1. 첫 항목", official)
        self.assertIn("가. 하위 항목", official)
        self.assertIn("1) 세부 항목", official)
        self.assertIn("2026. 8. 8.", official)
        self.assertIn("붙임", official)
        self.assertIn("끝.", official)
        self.assertIn("(직인)", official)
        self.assertNotIn("끝.", self.notice.render(data, "notice"))
        self.assertNotIn("끝.", self.notice.render(data, "poster"))

    def test_html_contract_and_image_backend_degradation(self) -> None:
        original = self.common.get_image_backend
        self.common.get_image_backend = lambda: None
        try:
            quote_html = self.quote.render(
                {"supplier": {"company": "(가상) 다온상사", "logo_path": "missing.png"}, "items": []},
                "office",
            )
            profile_html = self.profile.render(
                {"name": "(가상) 윤하늘", "photo_path": "missing.png"}, "sidebar"
            )
            notice_html = self.notice.render(
                {"org": "(가상) 다온협회", "seal_path": "missing.png"}, "official"
            )
        finally:
            self.common.get_image_backend = original
        self.assertIn("(가상) 다온상사", quote_html)
        self.assertIn("photo-placeholder", profile_html)
        self.assertIn("(직인)", notice_html)
        self.assertIn("[날짜 입력]", notice_html)
        for html in (quote_html, profile_html, notice_html):
            self.assertRegex(html, r"@page\s*\{[^}]*size:\s*A4")
            self.assertIn("PDF로 저장 / 인쇄", html)
            self.assertIn("@media print", html)

    def test_cli_smoke_and_kind_style_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            out = Path(temp_dir)
            cases = (
                ("quote", "clean", EXAMPLES / "quote.json"),
                ("profile", "sidebar", EXAMPLES / "profile.json"),
                ("official", "official", EXAMPLES / "official.json"),
                ("notice", "notice", EXAMPLES / "official.json"),
                ("poster", "poster", EXAMPLES / "official.json"),
            )
            for kind, style, source in cases:
                result = run_cli(
                    "--kind", kind, "--style", style, "--input", str(source), "--output-dir", str(out / kind)
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                files = list((out / kind).glob("*.html"))
                self.assertEqual(len(files), 1)
                text = files[0].read_text(encoding="utf-8")
                self.assertNotIn("/mnt/data", text)
                self.assertNotRegex(text, r"https?://")
            invalid = run_cli(
                "--kind", "official", "--style", "clean", "--input", str(EXAMPLES / "official.json"), "--output-dir", str(out / "bad")
            )
            self.assertNotEqual(invalid.returncode, 0)
            self.assertIn("style", invalid.stderr.lower())
            malformed = out / "malformed.json"
            malformed.write_text("{not json", encoding="utf-8")
            malformed_result = run_cli(
                "--kind", "quote", "--input", str(malformed), "--output-dir", str(out / "malformed")
            )
            self.assertNotEqual(malformed_result.returncode, 0)
            self.assertIn("JSON", malformed_result.stderr)
            malformed_shape = out / "malformed-shape.json"
            malformed_shape.write_text(
                json.dumps({"items": ["not-an-object"], "vat_mode": "exclusive"}),
                encoding="utf-8",
            )
            shape_result = run_cli(
                "--kind",
                "quote",
                "--input",
                str(malformed_shape),
                "--output-dir",
                str(out / "malformed-shape"),
            )
            self.assertEqual(shape_result.returncode, 2)
            self.assertIn("items[0] must be an object", shape_result.stderr)
            self.assertNotIn("Traceback", shape_result.stderr)

    def test_output_directory_relative_and_home_expansion(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            previous_cwd = Path.cwd()
            previous_env = {key: os.environ.get(key) for key in ("HOME", "USERPROFILE")}
            try:
                os.chdir(temp_dir)
                os.environ["HOME"] = temp_dir
                os.environ["USERPROFILE"] = temp_dir
                relative = self.common.save_html("relative", "sample", "relative-output")
                home = self.common.save_html("home", "sample", "~/home-output")
            finally:
                os.chdir(previous_cwd)
                for key, value in previous_env.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value
            self.assertEqual(relative.parent, Path(temp_dir, "relative-output").resolve())
            self.assertEqual(home.parent, Path(temp_dir, "home-output").resolve())

    def test_privacy_and_portability_gate(self) -> None:
        allowed_data = {
            "references/examples/quote.json",
            "references/examples/profile.json",
            "references/examples/official.json",
        }
        data_files = {
            path.relative_to(SKILL).as_posix()
            for path in SKILL.rglob("*")
            if path.is_file() and path.suffix.lower() in {".json", ".csv", ".html"}
        }
        self.assertEqual(data_files, allowed_data)
        sensitive_keys = {
            "company",
            "representative",
            "business_number",
            "address",
            "phone",
            "email",
            "contact",
            "location",
            "name",
            "org",
            "to",
            "via",
        }

        def assert_fictional_shape(value, key: str = "") -> None:
            if isinstance(value, dict):
                for child_key, child_value in value.items():
                    assert_fictional_shape(child_value, child_key)
            elif isinstance(value, list):
                for child_value in value:
                    assert_fictional_shape(child_value, key)
            elif key in sensitive_keys and str(value).strip():
                self.assertTrue(
                    str(value).startswith(("(가상)", "[")),
                    f"{key} must be fictional or a placeholder",
                )

        for relative in allowed_data:
            payload = json.loads((SKILL / relative).read_text(encoding="utf-8"))
            self.assertIn("(가상)", payload["_note"])
            assert_fictional_shape(payload)
        text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in SKILL.rglob("*")
            if path.is_file() and path.suffix.lower() in {".md", ".json", ".py", ".yaml", ".txt"}
        )
        self.assertNotIn("/mnt/data", text)
        self.assertNotRegex(text, r"https?://")
        self.assertNotRegex(text, r"[\w.+-]+@[\w-]+\.[A-Za-z]{2,}")
        self.assertNotRegex(text, r"\b0\d{1,2}[- ]?\d{3,4}[- ]?\d{4}\b")
        self.assertNotRegex(text, r"\b\d{3}-\d{2}-\d{5}\b")
        self.assertNotRegex(text, r"\b\d{6}-\d{7}\b")
        generated = [
            path
            for path in SKILL.rglob("*")
            if path.is_file() and path.suffix.lower() in {".html", ".png", ".jpg", ".jpeg"}
        ]
        self.assertEqual(generated, [])

    def test_skill_is_an_independent_plugin_and_release(self) -> None:
        self.assertFalse(
            (ROOT / "plugins" / "business-plan-writer" / "skills" / "create-business-documents").exists()
        )
        for relative in (
            "plugins/business-documents/plugin.json",
            "plugins/business-documents/.codex-plugin/plugin.json",
            "plugins/business-documents/.claude-plugin/plugin.json",
        ):
            payload = json.loads((ROOT / relative).read_text(encoding="utf-8"))
            self.assertEqual(payload["name"], "business-documents")
            self.assertEqual(payload["version"], "0.1.0")

        agents = json.loads(
            (ROOT / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8")
        )
        claude = json.loads(
            (ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            [plugin["name"] for plugin in agents["plugins"]],
            ["business-plan-writer", "business-documents"],
        )
        self.assertEqual(
            [plugin["name"] for plugin in claude["plugins"]],
            ["business-plan-writer", "business-documents"],
        )

        closure = json.loads(
            (ROOT / "release" / "manifests" / "business-documents.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(closure["required"], ["contracts", "business-documents"])
        self.assertIn("business-plan-writer", closure["forbiddenReads"])
        self.assertIn("course-kit", closure["forbiddenReads"])


if __name__ == "__main__":
    unittest.main()
