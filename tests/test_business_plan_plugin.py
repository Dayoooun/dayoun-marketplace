from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "business-plan-writer"
SKILLS = PLUGIN / "skills"
STARTER_SKILLS = ROOT / "fallback" / "starter-project" / ".agents" / "skills"
CLAUDE_STARTER_SKILLS = ROOT / "fallback" / "starter-project" / ".claude" / "skills"
VERSION = "0.6.0"


def run_python(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    return subprocess.run(
        [sys.executable, str(script), *args],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def skill_files(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    }


def load_create_project_module():
    path = SKILLS / "setup-business-plan-project" / "scripts" / "create_project.py"
    spec = importlib.util.spec_from_file_location("create_project", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BusinessPlanPluginTests(unittest.TestCase):
    def test_plugin_uses_generic_name_and_current_version(self) -> None:
        codex = json.loads(
            (PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        claude = json.loads(
            (PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        antigravity = json.loads((PLUGIN / "plugin.json").read_text(encoding="utf-8"))

        self.assertEqual(codex["name"], "business-plan-writer")
        self.assertEqual(codex["version"], VERSION)
        self.assertEqual(codex["interface"]["displayName"], "AI 사업계획서 작성 도우미")
        self.assertEqual(claude["name"], codex["name"])
        self.assertEqual(claude["version"], VERSION)
        self.assertEqual(antigravity["name"], codex["name"])

    def test_both_marketplaces_point_to_the_generic_plugin(self) -> None:
        agents = json.loads(
            (ROOT / ".agents" / "plugins" / "marketplace.json").read_text(
                encoding="utf-8"
            )
        )
        claude = json.loads(
            (ROOT / ".claude-plugin" / "marketplace.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(agents["name"], "dayoun")
        self.assertEqual(claude["name"], "dayoun")
        self.assertEqual(agents["plugins"][0]["name"], "business-plan-writer")
        self.assertEqual(claude["plugins"][0]["name"], "business-plan-writer")
        self.assertEqual(claude["plugins"][0]["version"], VERSION)

    def test_expected_six_skills_have_metadata(self) -> None:
        expected = {
            "complete-business-plan",
            "draft-business-plan",
            "fill-hwpx-template",
            "research-business-evidence",
            "review-business-plan",
            "setup-business-plan-project",
        }
        skill_dirs = sorted(path.parent for path in SKILLS.glob("*/SKILL.md"))
        self.assertEqual({path.name for path in skill_dirs}, expected)
        for skill_dir in skill_dirs:
            content = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
            self.assertTrue(content.startswith("---\n"), skill_dir.name)
            frontmatter = content.split("---", 2)[1]
            self.assertIn(f"name: {skill_dir.name}", frontmatter)
            self.assertIn("description:", frontmatter)
            self.assertTrue((skill_dir / "agents" / "openai.yaml").is_file())

    def test_starter_skills_exactly_match_plugin_skills(self) -> None:
        self.assertEqual(skill_files(SKILLS), skill_files(STARTER_SKILLS))
        self.assertEqual(skill_files(SKILLS), skill_files(CLAUDE_STARTER_SKILLS))

    def test_core_skills_are_generic_and_provider_neutral(self) -> None:
        forbidden = (
            "모두의 창업",
            "부산대학교",
            "pnu-modoo",
            "도전의 진정성",
            "사회적 가치",
            "아이디어 구체성",
        )
        for skill_file in sorted(SKILLS.glob("*/SKILL.md")):
            content = skill_file.read_text(encoding="utf-8")
            self.assertNotRegex(content, r"\$[a-z][a-z0-9-]+")
            self.assertNotIn("Codex 실행", content)
            for term in forbidden:
                self.assertNotIn(term, content)
        self.assertTrue(
            (
                SKILLS
                / "draft-business-plan"
                / "references"
                / "program-profiles"
                / "pnu-modoo.md"
            ).is_file()
        )

    def test_complete_skill_supports_general_use_cases_in_plain_language(self) -> None:
        content = (SKILLS / "complete-business-plan" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        for use_case in (
            "새로 작성",
            "기존 문서 보완",
            "공고·평가기준 맞춤",
            "자율 사업계획",
            "투자·IR",
            "사내 검토",
            "대출·제안",
        ):
            self.assertIn(use_case, content)
        self.assertIn("내가 알고 있는 정보", content)
        self.assertIn("확인이 필요한 내용", content)
        self.assertNotIn("F001", content)
        self.assertNotIn("C001", content)

    def test_writing_style_and_formatting_are_shared_by_draft_and_review(self) -> None:
        draft = (SKILLS / "draft-business-plan" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        review = (SKILLS / "review-business-plan" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        rubric = (
            SKILLS
            / "review-business-plan"
            / "references"
            / "review-rubric.md"
        ).read_text(encoding="utf-8")
        guide_path = (
            SKILLS
            / "draft-business-plan"
            / "references"
            / "writing-style.md"
        )

        self.assertTrue(guide_path.is_file())
        guide = guide_path.read_text(encoding="utf-8")
        self.assertIn("references/writing-style.md", draft)
        self.assertIn("references/writing-style.md", review)
        for requirement in (
            "문체",
            "한 문단에 하나의 핵심",
            "들여쓰기",
            "번호 체계",
            "표",
            "공식 양식",
        ):
            self.assertIn(requirement, guide)
        self.assertIn("| 서식 |", rubric)
        self.assertIn("들여쓰기", rubric)
        self.assertIn("번호 체계", rubric)

    def test_script_skills_explain_windows_and_mac_linux_launchers(self) -> None:
        for skill_name in ("setup-business-plan-project", "fill-hwpx-template"):
            content = (SKILLS / skill_name / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("Windows", content)
            self.assertIn("macOS/Linux", content)
            self.assertIn("python", content)
            self.assertIn("python3", content)
            self.assertIn("이 SKILL.md가 있는 폴더", content)
            self.assertIn("프로젝트 루트의 scripts로 해석하지 않는다", content)

    def test_provider_guide_uses_generic_installation(self) -> None:
        guide = (ROOT / "course" / "07-multi-provider-guide.md").read_text(
            encoding="utf-8"
        )
        for provider in ("Codex", "Claude Code", "Antigravity"):
            self.assertIn(provider, guide)
        self.assertIn("business-plan-writer@dayoun", guide)
        self.assertIn("complete-business-plan", guide)
        self.assertIn("특정 지원사업에 묶이지", guide)
        self.assertIn("설치 방법은 서로 다릅니다", guide)

    def test_starter_project_templates_match_generator(self) -> None:
        module = load_create_project_module()
        starter = ROOT / "fallback" / "starter-project"
        for relative, template in module.TEMPLATES.items():
            expected = module.render_template(template, "교육", "unknown", "DEMO")
            target = starter / relative
            self.assertTrue(target.is_file(), relative)
            self.assertEqual(target.read_text(encoding="utf-8-sig"), expected, relative)

        expected_paths = {Path(relative).as_posix() for relative in module.TEMPLATES}
        actual_paths = {
            path.relative_to(starter).as_posix()
            for path in starter.rglob("*")
            if path.is_file()
            and path.relative_to(starter).parts[0].startswith(
                tuple(f"{index:02d}." for index in range(8))
            )
        }
        self.assertEqual(actual_paths, expected_paths)

    def test_beginner_intake_happens_before_project_generation(self) -> None:
        content = (SKILLS / "complete-business-plan" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        intake_at = content.index("먼저 하나만 묻기")
        setup_at = content.index("`setup-business-plan-project`")
        self.assertLess(intake_at, setup_at)
        self.assertIn("질문 하나만", content)
        self.assertIn("답을 기다린다", content)

    def test_project_profile_is_generic_and_uses_plain_labels(self) -> None:
        script = SKILLS / "setup-business-plan-project" / "scripts" / "create_project.py"
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "project"
            result = run_python(
                script,
                "--path",
                str(project),
                "--purpose",
                "투자·IR",
                "--track",
                "unknown",
                "--mode",
                "PARTIAL",
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            profile = json.loads(
                (project / "00. 시작하기" / "계획프로필.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(profile["purpose"], "투자·IR")
            self.assertEqual(profile["requirements_status"], "unknown")
            info = (project / "01. 사업정보" / "사업정보표.md").read_text(
                encoding="utf-8"
            )
            research = (project / "04. 조사자료" / "조사기록.md").read_text(
                encoding="utf-8"
            )
            self.assertNotIn("F001", info)
            self.assertNotIn("C001", research)

    def test_force_never_overwrites_user_content(self) -> None:
        script = SKILLS / "setup-business-plan-project" / "scripts" / "create_project.py"
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "project"
            first = run_python(script, "--path", str(project))
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            draft = project / "05. 작성초안" / "사업계획서초안.md"
            draft.write_text(
                draft.read_text(encoding="utf-8") + "\n사용자 작성 문장\n",
                encoding="utf-8",
            )
            second = run_python(script, "--path", str(project), "--force")
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            self.assertIn("사용자 작성 문장", draft.read_text(encoding="utf-8"))
            self.assertIn("PROTECTED_MODIFIED", second.stdout)

    def test_non_utf8_user_file_is_preserved(self) -> None:
        script = SKILLS / "setup-business-plan-project" / "scripts" / "create_project.py"
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "project"
            first = run_python(script, "--path", str(project))
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            draft = project / "05. 작성초안" / "사업계획서초안.md"
            cp949_content = "사용자가 한글에서 저장한 문장\n".encode("cp949")
            draft.write_bytes(cp949_content)
            second = run_python(script, "--path", str(project), "--force")
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            self.assertEqual(draft.read_bytes(), cp949_content)
            self.assertIn("PROTECTED_MODIFIED", second.stdout)

    def test_track_name_is_valid_json_even_with_quotes(self) -> None:
        script = SKILLS / "setup-business-plan-project" / "scripts" / "create_project.py"
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "project"
            track = '일반 "기술" 트랙'
            result = run_python(script, "--path", str(project), "--track", track)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            profile = json.loads(
                (project / "00. 시작하기" / "계획프로필.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(profile["official_program"]["track"], track)

    def test_hwpx_demo_scan_fill_and_validate(self) -> None:
        script = SKILLS / "fill-hwpx-template" / "scripts" / "hwpx_placeholders.py"
        demo = PLUGIN / "assets" / "demo"
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            scan = run_python(
                script,
                "scan",
                str(demo / "demo-business-plan.hwpx"),
                "--map-out",
                str(temp / "draft.json"),
            )
            self.assertEqual(scan.returncode, 0, scan.stdout + scan.stderr)
            self.assertIn("PLACEHOLDERS: 4", scan.stdout)
            fill = run_python(
                script,
                "fill",
                str(demo / "demo-business-plan.hwpx"),
                "--values",
                str(demo / "demo-values.json"),
                "--output",
                str(temp / "filled.hwpx"),
            )
            self.assertEqual(fill.returncode, 0, fill.stdout + fill.stderr)
            validate = run_python(script, "validate", str(temp / "filled.hwpx"))
            self.assertEqual(validate.returncode, 0, validate.stdout + validate.stderr)


if __name__ == "__main__":
    unittest.main()
