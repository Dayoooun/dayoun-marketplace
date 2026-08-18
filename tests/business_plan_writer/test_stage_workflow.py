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
    "방향 인터뷰·부족한 근거·확인 질문 도출",
    "시장·고객·경쟁·가격·규제 독립 조사",
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



def stage_evidence(project: Path, stage: int) -> str:
    locations = {
        1: "02. 목적 및 요구사항/stage1.md",
        2: "01. 사업정보/stage2.md",
        3: "04. 조사자료/stage3.md",
        4: "04. 조사자료/stage4.md",
        5: "05. 작성초안/stage5.md",
        6: "05. 작성초안/stage6.md",
        7: "06. 검토결과/stage7.md",
        8: "07. 최종본/stage8.hwpx",
        9: "06. 검토결과/stage9.json",
        10: "08. 발표덱/stage10.md",
    }
    relative = locations[stage]
    target = project / relative
    target.write_text(f"stage {stage} evidence\n", encoding="utf-8")
    return relative

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

    def test_live_education_project_defaults_to_real_mode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "live-education"
            result = run(
                CREATE,
                "--path",
                str(project),
                "--purpose",
                "교육",
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            state = json.loads(
                (project / "00. 시작하기" / "단계상태.json").read_text(
                    encoding="utf-8"
                )
            )
            collaboration = json.loads(
                (project / "00. 시작하기" / "사용자협업상태.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(state["interactionMode"], "REAL")
            self.assertEqual(collaboration["interactionMode"], "REAL")
            self.assertTrue(
                (project / "04. 조사자료" / "독립조사" / "worker-01.md").is_file()
            )

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

    def test_demo_mode_stops_at_review_block_and_never_simulates_approval(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            create(project)

            for stage in range(1, 7):
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
                    stage_evidence(project, stage),
                )
                self.assertEqual(passed.returncode, 0, passed.stdout + passed.stderr)

            self.assertEqual(run(ADVANCE, "start", str(project), "7").returncode, 0)
            simulated = run(
                ADVANCE,
                "complete",
                str(project),
                "7",
                "--status",
                "PASS",
                "--evidence",
                stage_evidence(project, 7),
            )
            self.assertNotEqual(simulated.returncode, 0)
            self.assertIn("DEMO mode cannot approve", simulated.stdout)

            blocked = run(
                ADVANCE,
                "complete",
                str(project),
                "7",
                "--status",
                "BLOCK",
                "--evidence",
                stage_evidence(project, 7),
            )
            self.assertEqual(blocked.returncode, 0, blocked.stdout + blocked.stderr)
            next_stage = run(ADVANCE, "start", str(project), "8")
            self.assertNotEqual(next_stage.returncode, 0)
            self.assertIn("stage 7 status BLOCK", next_stage.stdout)

    def test_missing_required_folder_blocks_check(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            create(project)
            (project / "08. 발표덱" / "발표자료상태.md").unlink()
            (project / "08. 발표덱").rmdir()
            result = run(ADVANCE, "check", str(project))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("missing required project folders", result.stdout)

    def test_unexpected_top_level_folder_blocks_but_metadata_is_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            create(project)
            (project / ".dayoun").mkdir()
            allowed = run(ADVANCE, "check", str(project))
            self.assertEqual(allowed.returncode, 0, allowed.stdout + allowed.stderr)
            (project / "09. 임의폴더").mkdir()
            blocked = run(ADVANCE, "check", str(project))
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("unexpected top-level project folders", blocked.stdout)

    def test_evidence_must_be_stage_local_file_and_cannot_be_reused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            create(project)
            self.assertEqual(run(ADVANCE, "start", str(project), "1").returncode, 0)

            directory_evidence = run(
                ADVANCE,
                "complete",
                str(project),
                "1",
                "--status",
                "PASS",
                "--evidence",
                "02. 목적 및 요구사항",
            )
            self.assertNotEqual(directory_evidence.returncode, 0)
            self.assertIn("existing file", directory_evidence.stdout)

            wrong = project / "01. 사업정보" / "wrong-stage.md"
            wrong.write_text("wrong\n", encoding="utf-8")
            wrong_folder = run(
                ADVANCE,
                "complete",
                str(project),
                "1",
                "--status",
                "PASS",
                "--evidence",
                wrong.relative_to(project).as_posix(),
            )
            self.assertNotEqual(wrong_folder.returncode, 0)
            self.assertIn("outside its output folders", wrong_folder.stdout)

            passed = run(
                ADVANCE,
                "complete",
                str(project),
                "1",
                "--status",
                "PASS",
                "--evidence",
                stage_evidence(project, 1),
            )
            self.assertEqual(passed.returncode, 0, passed.stdout + passed.stderr)
            self.assertEqual(run(ADVANCE, "start", str(project), "2").returncode, 0)
            passed = run(
                ADVANCE,
                "complete",
                str(project),
                "2",
                "--status",
                "PASS",
                "--evidence",
                stage_evidence(project, 2),
            )
            self.assertEqual(passed.returncode, 0, passed.stdout + passed.stderr)

            self.assertEqual(run(ADVANCE, "start", str(project), "3").returncode, 0)
            shared = project / "04. 조사자료" / "shared.md"
            shared.write_text("stage 3\n", encoding="utf-8")
            relative = shared.relative_to(project).as_posix()
            passed = run(
                ADVANCE,
                "complete",
                str(project),
                "3",
                "--status",
                "PASS",
                "--evidence",
                relative,
            )
            self.assertEqual(passed.returncode, 0, passed.stdout + passed.stderr)

            self.assertEqual(run(ADVANCE, "start", str(project), "4").returncode, 0)
            reused = run(
                ADVANCE,
                "complete",
                str(project),
                "4",
                "--status",
                "PASS",
                "--evidence",
                relative,
            )
            self.assertNotEqual(reused.returncode, 0)
            self.assertIn("already used by a prior stage", reused.stdout)

    def test_real_mode_requires_recorded_user_collaboration_gates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            create(project, mode="REAL")
            collaboration_path = project / "00. 시작하기" / "사용자협업상태.json"

            def start(stage: int) -> None:
                result = run(ADVANCE, "start", str(project), str(stage))
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            def complete(
                stage: int,
                status: str = "PASS",
            ) -> subprocess.CompletedProcess[str]:
                args = [
                    "complete",
                    str(project),
                    str(stage),
                    "--status",
                    status,
                ]
                if status != "NOT_REQUESTED":
                    args.extend(["--evidence", stage_evidence(project, stage)])
                return run(ADVANCE, *args)

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

            start(8)
            blocked = complete(8, "NOT_REQUESTED")
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("HWPX choice status NOT_REQUESTED", blocked.stdout)
            collaboration = json.loads(collaboration_path.read_text(encoding="utf-8"))
            collaboration["hwpxChoice"] = {
                "status": "NOT_REQUESTED",
                "confirmedBy": "owner",
                "confirmedAt": "2026-08-16T12:30:00+09:00",
                "sourceQuote": "HWPX는 이번 범위에서 만들지 마",
            }
            collaboration_path.write_text(
                json.dumps(collaboration, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            self.assertEqual(complete(8, "NOT_REQUESTED").returncode, 0)

            start(9)
            self.assertEqual(complete(9, "NOT_REQUESTED").returncode, 0)
            start(10)
            blocked = complete(10)
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("presentation choice status REQUESTED", blocked.stdout)
            collaboration = json.loads(collaboration_path.read_text(encoding="utf-8"))
            collaboration["presentationChoice"] = {
                "status": "REQUESTED",
                "confirmedBy": "owner",
                "confirmedAt": "2026-08-16T12:40:00+09:00",
                "sourceQuote": "PPT와 대본, 예상 Q&A를 만들어",
            }
            collaboration_path.write_text(
                json.dumps(collaboration, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            finished = complete(10)
            self.assertEqual(finished.returncode, 0, finished.stdout + finished.stderr)
            self.assertIsNone(json.loads(finished.stdout)["currentStage"])


if __name__ == "__main__":
    unittest.main()
