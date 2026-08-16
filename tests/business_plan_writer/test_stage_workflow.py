from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SETUP = (
    ROOT
    / "plugins"
    / "business-plan-writer"
    / "skills"
    / "setup-business-plan-project"
    / "scripts"
)
CREATE = SETUP / "create_project.py"
ADVANCE = SETUP / "advance_stage.py"
TOP_LEVEL = {
    "00. 시작하기",
    "01. 사업정보",
    "02. 목적 및 요구사항",
    "03. 사업계획서양식",
    "04. 조사자료",
    "05. 작성초안",
    "06. 검토결과",
    "07. 최종본",
    "08. 발표덱",
    "99. 원본백업",
}
STAGES = [
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


def run(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=environment,
        check=False,
    )


def create(project: Path, mode: str = "DEMO") -> None:
    result = run(
        CREATE,
        "--path",
        str(project),
        "--purpose",
        "지원사업",
        "--mode",
        mode,
    )
    if result.returncode != 0:
        raise AssertionError(result.stdout + result.stderr)


class StageWorkflowTests(unittest.TestCase):
    def test_generator_creates_exact_required_top_level_and_stage_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            create(project)
            actual = {path.name for path in project.iterdir() if path.is_dir()}
            self.assertEqual(actual, TOP_LEVEL)
            state = json.loads(
                (project / "00. 시작하기" / "단계상태.json").read_text(encoding="utf-8")
            )
            self.assertEqual([record["name"] for record in state["stages"]], STAGES)
            self.assertEqual([record["status"] for record in state["stages"]], ["NOT_STARTED"] * 10)
            self.assertEqual(state["interactionMode"], "DEMO")
            self.assertTrue(
                (project / "00. 시작하기" / "사용자협업상태.json").is_file()
            )
            self.assertTrue((project / "08. 발표덱" / "발표자료상태.md").is_file())
            self.assertTrue((project / "99. 원본백업" / "README.md").is_file())
            self.assertTrue((project / "06. 검토결과" / "문안승인.md").is_file())
            self.assertFalse((project / "05. 작성초안" / "문안승인.md").exists())

    def test_next_stage_and_pass_without_evidence_are_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            create(project)
            blocked = run(ADVANCE, "start", str(project), "2")
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("blocked by stage 1", blocked.stdout)

            started = run(ADVANCE, "start", str(project), "1")
            self.assertEqual(started.returncode, 0, started.stdout + started.stderr)
            no_evidence = run(ADVANCE, "complete", str(project), "1", "--status", "PASS")
            self.assertNotEqual(no_evidence.returncode, 0)
            self.assertIn("PASS requires", no_evidence.stdout)

            evidence = project / "02. 목적 및 요구사항" / "stage1.md"
            evidence.write_text("stage 1 evidence\n", encoding="utf-8")
            passed = run(
                ADVANCE,
                "complete",
                str(project),
                "1",
                "--status",
                "PASS",
                "--evidence",
                evidence.relative_to(project).as_posix(),
            )
            self.assertEqual(passed.returncode, 0, passed.stdout + passed.stderr)
            stage_two = run(ADVANCE, "start", str(project), "2")
            self.assertEqual(stage_two.returncode, 0, stage_two.stdout + stage_two.stderr)

    def test_mandatory_stages_cannot_be_skipped_and_optional_sequence_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            create(project)
            evidence = project / "00. 시작하기" / "evidence.md"
            evidence.write_text("verified\n", encoding="utf-8")
            relative = evidence.relative_to(project).as_posix()

            for stage in range(1, 8):
                started = run(ADVANCE, "start", str(project), str(stage))
                self.assertEqual(started.returncode, 0, started.stdout + started.stderr)
                if stage == 1:
                    skipped = run(
                        ADVANCE,
                        "complete",
                        str(project),
                        str(stage),
                        "--status",
                        "NOT_REQUESTED",
                    )
                    self.assertNotEqual(skipped.returncode, 0)
                    self.assertIn("mandatory", skipped.stdout)
                passed = run(
                    ADVANCE,
                    "complete",
                    str(project),
                    str(stage),
                    "--status",
                    "PASS",
                    "--evidence",
                    relative,
                )
                self.assertEqual(passed.returncode, 0, passed.stdout + passed.stderr)

            for stage in (8, 9):
                self.assertEqual(run(ADVANCE, "start", str(project), str(stage)).returncode, 0)
                skipped = run(
                    ADVANCE,
                    "complete",
                    str(project),
                    str(stage),
                    "--status",
                    "NOT_REQUESTED",
                )
                self.assertEqual(skipped.returncode, 0, skipped.stdout + skipped.stderr)

            self.assertEqual(run(ADVANCE, "start", str(project), "10").returncode, 0)
            presentation = project / "08. 발표덱" / "deck-receipt.md"
            presentation.write_text("pptx pdf script q&a\n", encoding="utf-8")
            finished = run(
                ADVANCE,
                "complete",
                str(project),
                "10",
                "--status",
                "PASS",
                "--evidence",
                presentation.relative_to(project).as_posix(),
            )
            self.assertEqual(finished.returncode, 0, finished.stdout + finished.stderr)
            receipt = json.loads(finished.stdout)
            self.assertIsNone(receipt["currentStage"])

    def test_missing_required_folder_blocks_check(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            create(project)
            (project / "08. 발표덱" / "발표자료상태.md").unlink()
            (project / "08. 발표덱").rmdir()
            result = run(ADVANCE, "check", str(project))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("missing required project folders", result.stdout)

    def test_real_mode_requires_recorded_user_collaboration_gates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            create(project, mode="REAL")
            evidence = project / "00. 시작하기" / "evidence.md"
            evidence.write_text("verified\n", encoding="utf-8")
            relative = evidence.relative_to(project).as_posix()
            collaboration_path = project / "00. 시작하기" / "사용자협업상태.json"

            def start(stage: int) -> None:
                result = run(ADVANCE, "start", str(project), str(stage))
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            def complete(stage: int) -> subprocess.CompletedProcess[str]:
                return run(
                    ADVANCE,
                    "complete",
                    str(project),
                    str(stage),
                    "--status",
                    "PASS",
                    "--evidence",
                    relative,
                )

            for stage in (1, 2):
                start(stage)
                self.assertEqual(complete(stage).returncode, 0)

            start(3)
            blocked = complete(3)
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("question round status CONFIRMED", blocked.stdout)

            collaboration = json.loads(collaboration_path.read_text(encoding="utf-8"))
            collaboration["questionRound"] = {
                "status": "CONFIRMED",
                "answers": [{"question": "첫 고객", "answer": "인터뷰 후 확정"}],
                "confirmedBy": "owner",
                "confirmedAt": "2026-08-16T12:00:00+09:00",
                "sourceQuote": "질문을 확인했고 이 답으로 진행해줘",
            }
            collaboration_path.write_text(
                json.dumps(collaboration, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            self.assertEqual(complete(3).returncode, 0)

            start(4)
            self.assertEqual(complete(4).returncode, 0)
            start(5)
            blocked = complete(5)
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("strategy decision status CONFIRMED", blocked.stdout)

            collaboration = json.loads(collaboration_path.read_text(encoding="utf-8"))
            collaboration["strategyDecision"] = {
                "status": "CONFIRMED",
                "selectedOption": "검증 우선",
                "confirmedBy": "owner",
                "confirmedAt": "2026-08-16T12:10:00+09:00",
                "sourceQuote": "검증 우선안으로 잡아줘",
            }
            collaboration_path.write_text(
                json.dumps(collaboration, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            self.assertEqual(complete(5).returncode, 0)

            start(6)
            self.assertEqual(complete(6).returncode, 0)
            start(7)
            blocked = complete(7)
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("content approval status APPROVED", blocked.stdout)

            approved = project / "05. 작성초안" / "approved.md"
            approved.write_text("approved text\n", encoding="utf-8")
            collaboration = json.loads(collaboration_path.read_text(encoding="utf-8"))
            collaboration["contentApproval"] = {
                "status": "APPROVED",
                "approvedFile": approved.relative_to(project).as_posix(),
                "approvedBy": "owner",
                "approvedAt": "2026-08-16T12:20:00+09:00",
                "sourceQuote": "이 문안을 승인해",
            }
            collaboration_path.write_text(
                json.dumps(collaboration, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            self.assertEqual(complete(7).returncode, 0)


if __name__ == "__main__":
    unittest.main()
