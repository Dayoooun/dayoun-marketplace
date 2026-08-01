from __future__ import annotations

import json
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "modoo-startup-plan"
SKILLS = PLUGIN / "skills"
STARTER_SKILLS = (
    ROOT / "fallback" / "starter-project" / ".agents" / "skills"
)
CLAUDE_STARTER_SKILLS = (
    ROOT / "fallback" / "starter-project" / ".claude" / "skills"
)


def run_python(script: Path, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def skill_files(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)).replace("\\", "/"): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    }


def load_create_project_module():
    path = (
        SKILLS
        / "setup-startup-plan-project"
        / "scripts"
        / "create_project.py"
    )
    spec = importlib.util.spec_from_file_location("create_project", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ModooPluginTests(unittest.TestCase):
    def test_plugin_version_is_0_4_0(self) -> None:
        manifest = json.loads(
            (PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["version"], "0.4.0")

    def test_each_agent_provider_has_a_native_manifest(self) -> None:
        codex = json.loads(
            (PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        claude = json.loads(
            (PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        antigravity = json.loads(
            (PLUGIN / "plugin.json").read_text(encoding="utf-8")
        )

        self.assertEqual(codex["name"], "modoo-startup-plan")
        self.assertEqual(claude["name"], codex["name"])
        self.assertEqual(claude["version"], codex["version"])
        self.assertEqual(antigravity["name"], codex["name"])

    def test_claude_marketplace_points_to_the_canonical_plugin(self) -> None:
        marketplace = json.loads(
            (ROOT / ".claude-plugin" / "marketplace.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(marketplace["name"], "dayoun")
        plugin = next(
            item
            for item in marketplace["plugins"]
            if item["name"] == "modoo-startup-plan"
        )
        self.assertEqual(plugin["source"], "./plugins/modoo-startup-plan")
        self.assertEqual(plugin["version"], "0.4.0")

    def test_all_skills_have_valid_frontmatter_and_ui_metadata(self) -> None:
        skill_dirs = sorted(path.parent for path in SKILLS.glob("*/SKILL.md"))
        self.assertEqual(len(skill_dirs), 6)
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

    def test_skill_instructions_are_provider_neutral(self) -> None:
        for skill_file in sorted(SKILLS.glob("*/SKILL.md")):
            content = skill_file.read_text(encoding="utf-8")
            self.assertNotRegex(content, r"\$[a-z][a-z0-9-]+")
            self.assertNotIn("Codex 실행", content)

    def test_script_skills_explain_windows_and_mac_linux_launchers(self) -> None:
        for skill_name in ("setup-startup-plan-project", "fill-hwpx-template"):
            content = (SKILLS / skill_name / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("Windows", content)
            self.assertIn("macOS/Linux", content)
            self.assertIn("python", content)
            self.assertIn("python3", content)

    def test_provider_guide_promises_one_workflow_not_identical_installation(self) -> None:
        guide = (ROOT / "course" / "07-multi-provider-guide.md").read_text(
            encoding="utf-8"
        )
        for provider in ("Codex", "Claude Code", "Antigravity"):
            self.assertIn(provider, guide)
        for output in ("공백진단표", "검증활동기록", "멘토링변화기록", "실행카드"):
            self.assertIn(output, guide)
        self.assertIn("설치 방법은 서로 다릅니다", guide)
        self.assertIn("일반 채팅형 AI", guide)
        self.assertIn("프롬프트", guide)

    def test_starter_project_templates_match_generator(self) -> None:
        module = load_create_project_module()
        starter = ROOT / "fallback" / "starter-project"
        for relative, template in module.TEMPLATES.items():
            expected = module.render_template(template, "unknown", "DEMO")
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
        content = (SKILLS / "complete-modoo-plan" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        intake_at = content.index("초보자 최소 입력")
        setup_at = content.index("`setup-startup-plan-project` 스킬")
        self.assertLess(intake_at, setup_at)
        self.assertIn("질문 하나만", content)
        self.assertIn("프로젝트를 생성하지 않는다", content)

    def test_project_uses_separate_fact_and_claim_ids_and_program_profile(self) -> None:
        create_script = (
            SKILLS
            / "setup-startup-plan-project"
            / "scripts"
            / "create_project.py"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "project"
            result = run_python(
                create_script,
                "--path",
                str(project),
                "--track",
                "unknown",
                "--mode",
                "PARTIAL",
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            profile = json.loads(
                (project / "00. 시작하기" / "프로그램프로필.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(profile["program_pack"], "generic")
            self.assertEqual(profile["criteria_status"], "unknown")
            facts = (project / "01. 회사내용" / "회사사실표.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("F001", facts)
            self.assertNotIn("| C001 |", facts)
            activity = (
                project / "04. 시장조사 리서치" / "검증활동기록.md"
            ).read_text(encoding="utf-8")
            self.assertIn("증거 ID: C001", activity)

    def test_force_never_overwrites_user_content(self) -> None:
        create_script = (
            SKILLS
            / "setup-startup-plan-project"
            / "scripts"
            / "create_project.py"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "project"
            first = run_python(create_script, "--path", str(project))
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            draft = project / "05. 작성초안" / "핵심초안.md"
            draft.write_text(
                draft.read_text(encoding="utf-8") + "\n사용자 작성 문장\n",
                encoding="utf-8",
            )
            second = run_python(create_script, "--path", str(project), "--force")
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            self.assertIn("사용자 작성 문장", draft.read_text(encoding="utf-8"))
            self.assertIn("PROTECTED_MODIFIED", second.stdout)

    def test_non_utf8_user_file_is_preserved(self) -> None:
        create_script = (
            SKILLS
            / "setup-startup-plan-project"
            / "scripts"
            / "create_project.py"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "project"
            first = run_python(create_script, "--path", str(project))
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            draft = project / "05. 작성초안" / "핵심초안.md"
            cp949_content = "사용자가 한글에서 저장한 문장\n".encode("cp949")
            draft.write_bytes(cp949_content)
            second = run_python(create_script, "--path", str(project), "--force")
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            self.assertEqual(draft.read_bytes(), cp949_content)
            self.assertIn("PROTECTED_MODIFIED", second.stdout)

    def test_track_name_is_valid_json_even_with_quotes(self) -> None:
        create_script = (
            SKILLS
            / "setup-startup-plan-project"
            / "scripts"
            / "create_project.py"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "project"
            track = '일반 "기술" 트랙'
            result = run_python(
                create_script, "--path", str(project), "--track", track
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            profile = json.loads(
                (project / "00. 시작하기" / "프로그램프로필.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(profile["track"], track)

    def test_setup_records_user_input_before_requesting_official_files(self) -> None:
        content = (SKILLS / "setup-startup-plan-project" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("USER_PROVIDED_UNVERIFIED", content)
        self.assertIn("사용자 제공·미검증", content)
        self.assertIn("전부 빈 템플릿으로 끝내지 않는다", content)

    def test_generic_reference_has_no_institution_or_session_dates(self) -> None:
        common_skill = (SKILLS / "draft-modoo-plan" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        generic = (
            SKILLS
            / "draft-modoo-plan"
            / "references"
            / "evaluation-map.md"
        ).read_text(encoding="utf-8")
        self.assertNotIn("부산대", generic)
        self.assertNotIn("8월 14일", generic)
        self.assertNotIn("8월 19일", generic)
        for institution_specific_criterion in (
            "도전의 진정성",
            "사회적 가치",
            "아이디어 구체성",
        ):
            self.assertNotIn(institution_specific_criterion, common_skill)
            self.assertNotIn(institution_specific_criterion, generic)
        pnu_pack = (
            SKILLS
            / "draft-modoo-plan"
            / "references"
            / "pnu-modoo-program-pack.md"
        )
        self.assertTrue(pnu_pack.is_file())

    def test_review_scope_defines_coverage_denominator(self) -> None:
        content = (SKILLS / "review-modoo-plan" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        for scope in ("EDUCATION_SINGLE_CLAIM", "SELECTED_SECTION", "FULL_DOCUMENT"):
            self.assertIn(scope, content)
        self.assertIn("범위 내 사실 주장", content)
        self.assertIn("NOT_REVIEWED", content)

    def test_script_paths_are_resolved_from_each_skill_directory(self) -> None:
        for skill_name in ("setup-startup-plan-project", "fill-hwpx-template"):
            content = (SKILLS / skill_name / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("이 SKILL.md가 있는 폴더", content)
            self.assertIn("프로젝트 루트의 scripts로 해석하지 않는다", content)

    def test_hwpx_demo_scan_fill_and_validate(self) -> None:
        script = (
            SKILLS / "fill-hwpx-template" / "scripts" / "hwpx_placeholders.py"
        )
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

    def test_completed_example_uses_one_consistent_core_claim(self) -> None:
        completed = ROOT / "fallback" / "completed-project"
        facts = (completed / "01. 회사내용" / "회사사실표.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("F001", facts)
        self.assertNotIn("| C001 |", facts)
        evidence = (completed / "00. 시작하기" / "증거원장.csv").read_text(
            encoding="utf-8"
        )
        self.assertIn("C001", evidence)
        self.assertNotIn("C002", evidence)
        lock = (completed / "05. 작성초안" / "content-lock.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("C001 확인", lock)
        self.assertNotIn("C002", lock)
        review = (completed / "06. 검토결과" / "콘텐츠검토.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("EDUCATION_SINGLE_CLAIM", review)
        self.assertIn("범위 내 사실 주장 분모: 1", review)
        profile = json.loads(
            (completed / "00. 시작하기" / "프로그램프로필.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(profile["program_pack"], "pnu-modoo")


if __name__ == "__main__":
    unittest.main()
