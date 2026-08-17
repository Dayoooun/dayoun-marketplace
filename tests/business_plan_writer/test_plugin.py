from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "business-plan-writer"
SKILLS = PLUGIN / "skills"
STARTER_SKILLS = ROOT / "course" / "starter-project" / ".agents" / "skills"
CLAUDE_STARTER_SKILLS = ROOT / "course" / "starter-project" / ".claude" / "skills"
VERSION = "0.12.3"
CORE_SKILLS = {
    "complete-business-plan",
    "draft-business-plan",
    "fill-hwpx-template",
    "research-business-evidence",
    "review-business-plan",
    "setup-business-plan-project",
    "ppt-editorial",
}
ALL_SKILLS = CORE_SKILLS


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
        self.assertEqual(antigravity["version"], VERSION)

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
        self.assertEqual([item["name"] for item in agents["plugins"]], ["business-plan-writer", "business-documents"])
        self.assertEqual([item["name"] for item in claude["plugins"]], ["business-plan-writer", "business-documents"])

    def test_expected_skills_have_metadata(self) -> None:
        skill_dirs = sorted(path.parent for path in SKILLS.glob("*/SKILL.md"))
        self.assertEqual({path.name for path in skill_dirs}, ALL_SKILLS)
        self.assertEqual(len(CORE_SKILLS), 7)
        self.assertNotIn("create-business-documents", ALL_SKILLS)
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
        source_policy = (
            SKILLS
            / "research-business-evidence"
            / "references"
            / "source-policy.md"
        ).read_text(encoding="utf-8")
        complete = (SKILLS / "complete-business-plan" / "SKILL.md").read_text(
            encoding="utf-8"
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
            "개조식",
            "내어쓰기",
            "o 핵심항목",
            "- 세부내용",
            "주장과 출처 추적",
            "근거목록.csv",
            "[E001 |",
        ):
            self.assertIn(requirement, guide)
        self.assertIn("| 서식 |", rubric)
        self.assertIn("들여쓰기", rubric)
        self.assertIn("번호 체계", rubric)
        self.assertIn("o 핵심항목", rubric)
        self.assertIn("실제 내어쓰기", rubric)
        for content in (draft, review, source_policy, complete):
            self.assertIn("[E001 |", content)
            self.assertIn("[U001 |", content)
            self.assertIn("[H001 |", content)
            self.assertIn("[P001 |", content)
            self.assertIn("근거목록.csv", content)
        self.assertIn("출처 추적률 100%", draft)
        self.assertIn("출처 추적률이 100%", review)

    def test_script_skills_explain_windows_and_mac_linux_launchers(self) -> None:
        for skill_name in ("complete-business-plan", "setup-business-plan-project", "fill-hwpx-template"):
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
        starter = ROOT / "course" / "starter-project"
        for relative, template in module.TEMPLATES.items():
            expected = module.render_template(template, "교육", "unknown", "DEMO")
            target = starter / relative
            self.assertTrue(target.is_file(), relative)
            self.assertEqual(target.read_text(encoding="utf-8-sig"), expected, relative)

        expected_paths = {Path(relative).as_posix() for relative in module.TEMPLATES}
        expected_roots = {Path(relative).parts[0] for relative in module.TEMPLATES}
        actual_paths = {
            path.relative_to(starter).as_posix()
            for path in starter.rglob("*")
            if path.is_file()
            and path.relative_to(starter).parts[0] in expected_roots
        }
        self.assertEqual(actual_paths, expected_paths)

    def test_official_inputs_and_beginner_intake_precede_project_generation(self) -> None:
        content = (SKILLS / "complete-business-plan" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        official_at = content.index("먼저 공식 입력을 잠근다")
        intake_at = content.index("핵심 정보가 비어 있으면 하나만 묻기")
        setup_at = content.index("`setup-business-plan-project`")
        self.assertLess(official_at, intake_at)
        self.assertLess(intake_at, setup_at)
        self.assertIn("질문 하나만", content)
        self.assertIn("답을 기다린다", content)

    def test_installed_agent_leads_natural_language_and_hwpx_design(self) -> None:
        complete = (SKILLS / "complete-business-plan" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        fill = (SKILLS / "fill-hwpx-template" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        design = (
            SKILLS
            / "fill-hwpx-template"
            / "references"
            / "visual-design-system.md"
        ).read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertLess(
            complete.index("설치 후 기본 리드 계약"),
            complete.index("먼저 공식 입력을 잠근다"),
        )
        for requirement in (
            "스킬 이름",
            "고정 조건",
            "되돌릴 수 있는 일은 질문을 기다리지 않고 진행",
            "권장안과 대안",
            "사용자의 명시적 지시는 공통 기본값보다 항상 우선",
            "`알아서 보기 좋게`",
            "PDF/PNG 렌더",
        ):
            self.assertIn(requirement, complete)

        for requirement in (
            "`알아서 보기 좋게` 실행 계약",
            "디자인 결정표",
            "사용자가 지정한 브랜드·폰트·색·톤·참고 이미지",
            "결과 HWPX와",
            "검증 기록까지 만든다",
        ):
            self.assertIn(requirement, fill)

        for requirement in (
            "에이전트 자동 선택표",
            "문서 디자인 품질 gate",
            "본문만으로 판단이 가능하면 0개가 정답",
            "구조검사 PASS는 디자인 PASS가 아니다",
        ):
            self.assertIn(requirement, design)

        self.assertIn("설치 후에는 자연어로 지시합니다", readme)
        self.assertIn("스킬 이름이나 10단계를 외울 필요가 없습니다", readme)

    def test_natural_language_lead_brief_is_behavioral_and_fail_closed(self) -> None:
        script = (
            SKILLS
            / "complete-business-plan"
            / "scripts"
            / "lead_request.py"
        )
        request = (
            "이 HWPX 내용은 바꾸지 말고 브랜드 색 #0057B8로 알아서 보기 좋게 "
            "디자인해줘. 원본은 보존하고 PDF 확대검수까지 해줘."
        )
        completed = subprocess.run(
            [
                sys.executable,
                str(script),
                "--request",
                request,
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        brief = json.loads(completed.stdout)

        self.assertEqual(brief["entrySkill"], "complete-business-plan")
        self.assertEqual(brief["interactionMode"], "REAL")
        self.assertEqual(brief["status"], "READY_FOR_REVERSIBLE_WORK")
        self.assertIn("HWPX", brief["requestedOutputs"])
        self.assertTrue(brief["designDelegated"])
        constraints = {
            item["constraint"] for item in brief["fixedConstraints"]
        }
        self.assertIn("preserve-approved-content", constraints)
        self.assertIn("preserve-source-file", constraints)
        self.assertIn("brand-color:#0057B8", constraints)
        self.assertIn("design-delegated-within-evidence", constraints)

        actions = brief["autonomousActions"]
        self.assertEqual(
            brief["nextAction"],
            "inventory-provided-files-and-existing-project",
        )
        self.assertIn("create-hwpx-design-decision-table", actions)
        self.assertIn(
            "apply-approved-content-and-delegated-design-to-working-copy",
            actions,
        )
        self.assertIn(
            "assign-inline-source-status-markers-and-evidence-registry",
            actions,
        )
        self.assertIn(
            "render-pdf-and-page-pngs-for-full-page-100-percent-and-zoom-qa",
            actions,
        )
        self.assertTrue(brief["approvalGates"]["contentApproval"])
        self.assertEqual(
            brief["materialDecisions"][2]["agentBehavior"],
            "never-infer-or-self-approve",
        )
        self.assertFalse(brief["approvalGates"]["designChoice"])
        self.assertFalse(brief["approvalGates"]["hwpxChoice"])
        self.assertTrue(brief["approvalGates"]["publicationApproval"])
        self.assertTrue(
            brief["completionRequirements"]["sourceStructureIntegrityRequired"]
        )
        self.assertTrue(
            brief["completionRequirements"]["claimSourceTraceabilityRequired"]
        )
        self.assertTrue(
            brief["completionRequirements"]["pdfAndPagePngRenderReceiptRequired"]
        )

        for phrase in (
            "PPT",
            "PPTX",
            "PowerPoint",
            "파워포인트",
            "슬라이드",
            "발표자료",
            "발표 덱",
            "피치덱",
            "IR 덱",
            "제안서",
            "강의자료",
            "교육자료",
        ):
            with self.subTest(ppt_trigger=phrase):
                routed = subprocess.run(
                    [
                        sys.executable,
                        str(script),
                        "--request",
                        f"{phrase} 만들어줘",
                    ],
                    cwd=ROOT,
                    text=True,
                    encoding="utf-8",
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(
                    routed.returncode,
                    0,
                    routed.stdout + routed.stderr,
                )
                routed_brief = json.loads(routed.stdout)
                self.assertEqual(
                    routed_brief["entrySkill"],
                    "ppt-editorial",
                )
                self.assertEqual(
                    routed_brief["nextAction"],
                    "invoke-ppt-editorial-immediately",
                )
                self.assertTrue(
                    routed_brief["completionRequirements"][
                        "presentationHumanizationRequired"
                    ]
                )
                self.assertEqual(
                    routed_brief["completionRequirements"][
                        "presentationHumanizationScope"
                    ],
                    "titles-body-captions-script-and-qa",
                )
                self.assertIn(
                    "protect-facts-and-humanize-all-presentation-prose",
                    routed_brief["autonomousActions"],
                )

        demo_day = subprocess.run(
            [
                sys.executable,
                str(script),
                "--request",
                "데모데이 제출용 HWPX를 전문적으로 디자인해줘.",
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )
        self.assertEqual(demo_day.returncode, 0, demo_day.stdout + demo_day.stderr)
        demo_day_brief = json.loads(demo_day.stdout)
        self.assertEqual(demo_day_brief["interactionMode"], "REAL")
        self.assertTrue(demo_day_brief["approvalGates"]["contentApproval"])
        self.assertTrue(demo_day_brief["approvalGates"]["publicationApproval"])

        explicit_demo = subprocess.run(
            [
                sys.executable,
                str(script),
                "--request",
                "강의시연용 HWPX 흐름을 검증해줘.",
                "--mode",
                "DEMO",
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )
        self.assertEqual(
            explicit_demo.returncode,
            0,
            explicit_demo.stdout + explicit_demo.stderr,
        )
        explicit_demo_brief = json.loads(explicit_demo.stdout)
        self.assertEqual(explicit_demo_brief["interactionMode"], "DEMO")
        self.assertFalse(explicit_demo_brief["approvalGates"]["contentApproval"])
        self.assertFalse(
            explicit_demo_brief["approvalGates"]["publicationApproval"]
        )

        nondelegated = subprocess.run(
            [
                sys.executable,
                str(script),
                "--request",
                "이 HWPX 양식을 승인 문안으로 채워줘.",
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )
        self.assertEqual(
            nondelegated.returncode,
            0,
            nondelegated.stdout + nondelegated.stderr,
        )
        nondelegated_brief = json.loads(nondelegated.stdout)
        self.assertFalse(nondelegated_brief["designDelegated"])
        self.assertTrue(nondelegated_brief["approvalGates"]["designChoice"])

    def test_end_to_end_pipeline_and_skill_handoffs_are_documented(self) -> None:
        complete = (SKILLS / "complete-business-plan" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        workflow = (
            SKILLS
            / "complete-business-plan"
            / "references"
            / "workflow.md"
        ).read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        stages = [
            "공고문·평가지표·작성지침·사업계획서 양식 분석",
            "회사·사업 현황·아이디어 분석",
            "부족한 근거와 확인 질문 도출",
            "시장·고객·경쟁·가격·규제 조사",
            "사업전략·실행계획·수익구조 설계",
            "평가지표와 양식에 맞춰 텍스트 초안 작성",
            "검토·수정·사용자 승인",
            "선택한 경우 승인 내용을 HWPX 양식에 반영",
            "선택한 HWPX 구조·화면검사",
            "선택한 PPT·대본·예상 Q&A 제작",
        ]
        positions = [complete.index(stage) for stage in stages]
        self.assertEqual(positions, sorted(positions))
        for stage in stages:
            self.assertIn(stage, readme)
        self.assertIn("단계 게이트와 되돌아가기", workflow)

        for skill_name in (
            "setup-business-plan-project",
            "research-business-evidence",
            "draft-business-plan",
            "review-business-plan",
            "fill-hwpx-template",
            "ppt-editorial",
        ):
            content = (SKILLS / skill_name / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("파이프라인 위치", content, skill_name)

        ppt = (SKILLS / "ppt-editorial" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("HWPX 파일·경로·검사기록을 요구하거나 조회하면 안 된다", ppt)
        self.assertIn("대본", ppt)
        self.assertIn("예상 Q&A", ppt)
    def test_ppt_harness_interview_macos_and_regressions(self) -> None:
        ppt = SKILLS / "ppt-editorial"
        skill = (ppt / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("요구사항 확인 게이트", skill)
        self.assertIn("Windows와 macOS", skill)
        self.assertIn("PowerPoint 내부 텍스트 편집", skill)
        frontmatter = skill.split("---", 2)[1]
        for trigger in (
            "PPT",
            "PPTX",
            "파워포인트",
            "슬라이드",
            "발표자료",
            "피치덱",
            "IR덱",
            "제안서",
            "강의자료",
            "리디자인",
            "대본",
            "예상 Q&A",
        ):
            self.assertIn(trigger, frontmatter)
        self.assertIn("스킬명을 말하지 않아도 즉시", frontmatter)
        self.assertIn("한국어 윤문을 반드시", frontmatter)
        humanization = (
            ppt / "references" / "korean-prose-humanization.md"
        ).read_text(encoding="utf-8")
        for contract in (
            "Document prose mode",
            "보호 목록",
            "kill-ai-slop",
            "humanize-korean",
            "대본과 예상 Q&A 작성 뒤 다시 윤문",
        ):
            self.assertIn(contract, humanization)
        self.assertIn("필수 한국어 윤문 gate", skill)
        self.assertIn("윤문: PASS", skill)
        for contract in (
            'sceneMode: "cutout"',
            'sceneMode: "canvas"',
            "contentBBox",
            "alpha 0~255",
            "체크무늬",
            "minOccupancy",
            "scene-placement-receipt.json",
            "원본 16:9 크기",
        ):
            self.assertIn(contract, skill)
        self.assertTrue((ROOT / "tests" / "ppt" / "test_scene_cutout.py").is_file())
        self.assertTrue((ROOT / "tests" / "ppt" / "test_scene_occupancy.py").is_file())

        for relative in (
            "scripts/intake.py",
            "scripts/platform_support.py",
            "scripts/approved_inputs.py",
            "scripts/build_visible_text_manifest.py",
            "scripts/ocr/map_ocr_regions.py",
            "scripts/ocr/validate_visible_text.py",
            "scripts/scene-deck/info_layouts.py",
            "scripts/scene-deck/cutout.py",
        ):
            self.assertTrue((ppt / relative).is_file(), relative)
        self.assertTrue(
            (ppt / "references" / "korean-prose-humanization.md").is_file()
        )
        self.assertTrue((ROOT / "tests" / "ppt" / "test_harness.py").is_file())

        brief = (ppt / "templates" / "deck_brief.md").read_text(encoding="utf-8")
        self.assertIn("```json", brief)
        self.assertIn('"requirements_confirmed": false', brief)

        for relative in (
            "scripts/scene-deck/fonts.py",
            "scripts/chrome.py",
            "scripts/index_chrome.py",
            "scripts/screenshot_frame.py",
        ):
            source = (ppt / relative).read_text(encoding="utf-8")
            self.assertNotIn("C:\\\\Windows\\\\Fonts", source, relative)
            self.assertNotIn("C:/Windows/Fonts", source, relative)

        unit = run_python(ROOT / "tests" / "ppt" / "test_harness.py")
        self.assertEqual(unit.returncode, 0, unit.stdout + unit.stderr)
        smoke = run_python(ppt / "scripts" / "harness_smoke.py", "--quiet")
        self.assertEqual(smoke.returncode, 0, smoke.stdout + smoke.stderr)

        workflow = (ROOT / ".github" / "workflows" / "validate.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("windows-latest", workflow)
        self.assertIn("macos-latest", workflow)
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

    def test_visual_design_defaults_and_hwpx_invariants_are_shared(self) -> None:
        complete = (SKILLS / "complete-business-plan" / "SKILL.md").read_text(encoding="utf-8")
        draft = (SKILLS / "draft-business-plan" / "SKILL.md").read_text(encoding="utf-8")
        fill_root = SKILLS / "fill-hwpx-template"
        fill = (fill_root / "SKILL.md").read_text(encoding="utf-8")
        review = (SKILLS / "review-business-plan" / "SKILL.md").read_text(encoding="utf-8")
        ppt_root = SKILLS / "ppt-editorial"
        ppt = (ppt_root / "SKILL.md").read_text(encoding="utf-8")
        style = (ppt_root / "references" / "style-system.md").read_text(encoding="utf-8")
        fonts = (ppt_root / "scripts" / "scene-deck" / "fonts.py").read_text(encoding="utf-8")
        visual = (fill_root / "references" / "visual-design-system.md").read_text(encoding="utf-8")
        css = (fill_root / "assets" / "visual-default.css").read_text(encoding="utf-8")

        self.assertTrue((fill_root / "scripts" / "hwpx_visuals.py").is_file())
        for script_name in (
            "hwpx_revision.py",
            "hwpx_style_integrity.py",
            "hwpx_preview_sync.py",
            "install_bundled_fonts.py",
        ):
            self.assertTrue((fill_root / "scripts" / script_name).is_file())
        font_roots = (
            PLUGIN / "assets" / "fonts" / "pretendard",
            STARTER_SKILLS.parent / "assets" / "fonts" / "pretendard",
            CLAUDE_STARTER_SKILLS.parent / "assets" / "fonts" / "pretendard",
        )
        for font_name in (
            "Pretendard-Regular.otf",
            "Pretendard-Medium.otf",
            "Pretendard-SemiBold.otf",
            "Pretendard-Bold.otf",
            "LICENSE.txt",
            "manifest.json",
        ):
            for font_root in font_roots:
                self.assertTrue((font_root / font_name).is_file(), f"{font_root}: {font_name}")
        for content in (complete, draft, fill, review):
            self.assertIn("visual-design-system.md", content)
        for content in (style, fonts, ppt, visual, css):
            self.assertIn("Pretendard", content)

        for field in (
            "시각자료 종류",
            "핵심 메시지",
            "근거",
            "삽입할 표 셀",
            "앞 문단",
            "뒤 문단",
            "짧은 캡션",
        ):
            self.assertIn(field, draft)
        for invariant in (
            "tc → subList → p → run → tbl",
            "45,900 HWPUNIT",
            "39,982 HWPUNIT",
            "510 HWPUNIT",
            "220 HWPUNIT",
            "1,200 HWPUNIT",
            "borderFill",
            "#F2F2F2",
            "binaryItemIDRef",
            "content.hpf",
            "BinData",
            "secPr",
            "그림 N. 핵심 그림명",
        ):
            self.assertIn(invariant, visual)
        self.assertIn("답변 셀 마지막 일괄 배치는 금지", complete)
        self.assertIn("답변 셀 마지막에 일괄 배치하지 않는다", fill)
        self.assertIn("원본 쪽 여백", complete)
        self.assertIn("다른 양식에 강제로 덮어쓰지 않는다", visual)
        self.assertIn("user direction, brand system, or official template", style)
        self.assertIn("장식 이미지보다", ppt)
        for weight in range(100, 1000, 100):
            self.assertIn(f"font-weight: {weight}", css)
        self.assertIn("--visual-accent: #3182f6", css)
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
                "--evidence-registry",
                str(demo / "demo-evidence.csv"),
                "--output",
                str(temp / "filled.hwpx"),
            )
            self.assertEqual(fill.returncode, 0, fill.stdout + fill.stderr)
            validate = run_python(script, "validate", str(temp / "filled.hwpx"))
            self.assertEqual(validate.returncode, 0, validate.stdout + validate.stderr)


if __name__ == "__main__":
    unittest.main()
