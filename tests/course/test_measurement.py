from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from aggregate_beta_evidence import BetaEvidenceError, aggregate_beta  # noqa: E402
from aggregate_course_evidence import CourseEvidenceError, aggregate_course  # noqa: E402
from contract_utils import canonical_digest  # noqa: E402


class MeasurementTests(unittest.TestCase):
    def course_evidence(self, n: int = 10) -> dict:
        rubric_pre = {"gapDiagnosis": 0, "evidenceRecord": 1, "changeRecord": 1, "actionCard": 0}
        rubric_post = {"gapDiagnosis": 2, "evidenceRecord": 2, "changeRecord": 2, "actionCard": 2}
        calibration_path = ROOT / "contracts" / "fixtures" / "course-calibration.json"
        calibration = json.loads(calibration_path.read_text(encoding="utf-8"))
        golden_scores = {
            item["artifactId"]: item["rubric"]
            for item in calibration["goldenArtifacts"]
        }
        safety_answers = {
            item["caseId"]: item["expected"]
            for item in calibration["safetyCases"]
        }
        roster = [
            {"participantId": f"P{index:02d}"}
            for index in range(1, n + 1)
        ]
        return {
            "calibrationFixtureDigest": (
                "sha256:" + hashlib.sha256(calibration_path.read_bytes()).hexdigest()
            ),
            "assessors": [
                {
                    "id": assessor,
                    "blind": True,
                    "artifactScores": copy.deepcopy(golden_scores),
                    "safetyClassifications": copy.deepcopy(safety_answers),
                }
                for assessor in ("A1", "A2")
            ],
            "roster": copy.deepcopy(roster),
            "rosterDigest": canonical_digest(roster),
            "rosterFrozenAt": "2026-01-01T00:00:00+00:00",
            "participants": [
                {
                    "participantId": f"P{index:02d}",
                    "startedAt": "2026-01-01T00:01:00+00:00",
                    "consent": True,
                    "firstActionSeconds": 300,
                    "completedAtSeconds": 6500,
                    "preRubric": rubric_pre,
                    "postRubric": rubric_post,
                    "artifactRubric": rubric_post,
                }
                for index in range(1, n + 1)
            ],
            "safetyIncidents": [],
            "fallbackTransitions": [{"id": "T1", "durationSeconds": 300}],
        }

    def test_course_n10_boundaries_pass(self) -> None:
        result = aggregate_course(self.course_evidence())
        self.assertEqual(result["status"], "PASS")
        self.assertEqual((result["requiredComplete"], result["requiredImproved"]), (8, 7))

    def test_course_duplicate_identity_and_coerced_score_are_rejected(self) -> None:
        duplicate = self.course_evidence()
        duplicate["participants"][1]["participantId"] = "P01"
        with self.assertRaises(CourseEvidenceError):
            aggregate_course(duplicate)
        coerced = self.course_evidence()
        coerced["participants"][0]["preRubric"]["gapDiagnosis"] = "0"
        with self.assertRaises(CourseEvidenceError):
            aggregate_course(coerced)
    def test_claimed_calibration_cannot_replace_exact_scores(self) -> None:
        evidence = self.course_evidence()
        evidence["assessors"][0]["artifactScores"]["G1"]["gapDiagnosis"] = 3
        result = aggregate_course(evidence)
        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("assessor-calibration", result["blockers"])

    def test_course_n9_missing_and_301_second_fallback_block(self) -> None:
        result = aggregate_course(self.course_evidence(9))
        self.assertEqual(result["status"], "BLOCK")
        evidence = self.course_evidence()
        evidence["participants"][0]["postRubric"] = None
        evidence["fallbackTransitions"][0]["durationSeconds"] = 301
        result = aggregate_course(evidence)
        self.assertEqual(result["status"], "BLOCK")
        self.assertTrue(any(item.startswith("fallback-over-300s") for item in result["blockers"]))

    def beta_evidence(self) -> dict:
        providers = ["codex"] * 4 + ["claude-code"] * 3 + ["antigravity"] * 3
        scopes = ["QUICK"] * 5 + ["SECTION"] * 5
        digest = "sha256:" + "a" * 64
        roster = [
            {
                "participantId": f"P{index + 1:02d}",
                "provider": providers[index],
                "scope": scopes[index],
            }
            for index in range(10)
        ]
        return {
            "roster": copy.deepcopy(roster),
            "rosterDigest": canonical_digest(roster),
            "rosterFrozenAt": "2026-01-01T00:00:00+00:00",
            "participants": [
                {
                    **assignment,
                    "startedAt": "2026-01-01T00:01:00+00:00",
                    "consent": True,
                    "preRecord": True,
                    "attempts": [
                        {
                            "scopeComplete": True,
                            "validators": {
                                role: {
                                    "status": "PASS",
                                    "evidenceDigest": digest,
                                    "evidenceRef": f"{assignment['participantId']}-{role}.json",
                                }
                                for role in ("fact", "structure", "contract")
                            },
                            "selectedOutputs": {"hwpx": False, "ppt": True},
                            "outputAutomation": {
                                "ppt": {
                                    "status": "PASS",
                                    "evidenceDigest": digest,
                                    "evidenceRef": f"{assignment['participantId']}-ppt-automation.json",
                                }
                            },
                            "outputVisual": {
                                "ppt": {
                                    "status": "PASS",
                                    "evidenceDigest": digest,
                                    "evidenceRef": f"{assignment['participantId']}-ppt-visual.json",
                                }
                            },
                        }
                    ],
                }
                for assignment in roster
            ],
            "criticalDefects": [],
        }

    def test_beta_locked_assignment_passes(self) -> None:
        result = aggregate_beta(self.beta_evidence())
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["complete"], 10)

    def test_beta_duplicate_identity_is_rejected(self) -> None:
        evidence = self.beta_evidence()
        evidence["participants"][1]["participantId"] = "P01"
        with self.assertRaises(BetaEvidenceError):
            aggregate_beta(evidence)

    def test_beta_non_infra_retry_and_critical_defect_block(self) -> None:
        evidence = self.beta_evidence()
        participant = evidence["participants"][0]
        participant["attempts"] = [
            {"failureClass": "PRODUCT"},
            copy.deepcopy(participant["attempts"][0]),
        ]
        evidence["criticalDefects"] = [
            {"code": "C1", "qaLeadDecision": "critical", "releaseOwnerRecord": "BLOCK"}
        ]
        result = aggregate_beta(evidence)
        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("non-infrastructure-retry:P01", result["blockers"])
        self.assertIn("critical-defect:C1", result["blockers"])


class StarterExampleTests(unittest.TestCase):
    def test_beginner_idea_draft_is_generated_and_fail_closed(self) -> None:
        source = (
            ROOT
            / "course-src"
            / "offline-evidence-pack"
            / "00-beginner-idea-draft.md"
        )
        generated = (
            ROOT
            / "course"
            / "offline-evidence-pack"
            / "00-beginner-idea-draft.md"
        )
        self.assertEqual(source.read_bytes(), generated.read_bytes())
        content = source.read_text(encoding="utf-8")
        for required in (
            "교육용 가상 사례",
            "아이디어만 있는 초보자의 첫 메모",
            "| 가정 |",
            "| 확인 필요 |",
            "| 아이디어 |",
            "| 계획 |",
            "확인된 내용 없음",
            "지금 말할 수 없는 것",
            "가장 먼저 확인할 질문",
            "AI에게 줄 첫 요청",
            "내 아이디어로 바꾸는 빈 양식",
        ):
            self.assertIn(required, content)
        self.assertIn("확인되지 않은 고객 수, 시장규모, 성과, 가격을 만들지 마", content)

    def test_beginner_idea_draft_links_to_staged_evidence(self) -> None:
        evidence_root = ROOT / "course-src" / "offline-evidence-pack"
        self.assertTrue((evidence_root / "02-fictional-company-brief.md").is_file())
        self.assertTrue((evidence_root / "03-fictional-customer-notes.md").is_file())

if __name__ == "__main__":
    unittest.main()
