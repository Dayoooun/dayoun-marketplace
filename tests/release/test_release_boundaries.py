from __future__ import annotations
import io
import hashlib

import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from build_release_artifacts import build_target, configure_utf8_output  # noqa: E402
from compare_release_builds import digest  # noqa: E402
from release_dry_run import (  # noqa: E402
    ReleaseGateError,
    _validate_toolchain_lock,
    validate_release,
)
from rollback_rehearsal import load as load_rollback, rehearse  # noqa: E402
from test_release_independence import evaluate  # noqa: E402


class ReleaseBoundaryTests(unittest.TestCase):
    def test_windows_console_output_is_reconfigured_to_utf8(self) -> None:
        buffer = io.BytesIO()
        stream = io.TextIOWrapper(buffer, encoding="cp1252")
        configure_utf8_output(stream)

        self.assertEqual(stream.encoding.lower().replace("-", ""), "utf8")
        stream.write("한글 파일")
        stream.flush()
        self.assertEqual(buffer.getvalue().decode("utf-8"), "한글 파일")
        stream.detach()

    def test_release_publish_steps_bind_the_repository(self) -> None:
        workflows = [
            ROOT / ".github" / "workflows" / "release-contracts.yml",
            ROOT / ".github" / "workflows" / "release-business-plan-writer.yml",
            ROOT / ".github" / "workflows" / "release-business-documents.yml",
            ROOT / ".github" / "workflows" / "release-course-kit.yml",
        ]
        for workflow in workflows:
            text = workflow.read_text(encoding="utf-8")
            release_job = text.split("\n  release:\n", 1)[1]
            self.assertIn("actions/checkout@v5", release_job, workflow.name)
            self.assertIn('--repo "$GITHUB_REPOSITORY"', release_job, workflow.name)
    def test_writer_build_is_reproducible_and_excludes_documents_and_tests(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            left = Path(directory) / "left"
            right = Path(directory) / "right"
            build_target("business-plan-writer", "0.12.4", left)
            build_target("business-plan-writer", "0.12.4", right)
            left_zip = next(left.glob("*.zip"))
            right_zip = next(right.glob("*.zip"))
            self.assertEqual(digest(left_zip), digest(right_zip))
            with zipfile.ZipFile(left_zip) as archive:
                names = archive.namelist()
            self.assertFalse(any("create-business-documents" in name for name in names))
            self.assertFalse(any(name.endswith("test_harness.py") for name in names))
            self.assertIn("_contracts/schemas/canonical.schema.json", names)
            self.assertIn("requirements.txt", names)
            self.assertFalse(any("__pycache__" in name or name.endswith(".pyc") for name in names))

    def test_bootstrap_rollback_install_smoke_remove(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            artifacts = Path(directory)
            build_target("contracts", "1.0.0", artifacts)
            result = rehearse(
                load_rollback(ROOT / "release" / "last-verified" / "contracts.json"),
                target="contracts",
                candidate=artifacts,
            )
            self.assertEqual(result["status"], "PASS")
            self.assertTrue(result["cleanHomeRemoved"])
    def test_member_manifest_blocks_archive_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            artifacts = Path(directory)
            build_target("contracts", "1.0.0", artifacts)
            archive = next(artifacts.glob("*.zip"))
            with zipfile.ZipFile(archive, "a") as mutated:
                mutated.writestr("tampered.txt", b"tampered")
            with self.assertRaises(ReleaseGateError):
                validate_release(
                    target="contracts",
                    closure_path=ROOT / "release" / "manifests" / "contracts.json",
                    artifacts=artifacts,
                    evidence=None,
                    strict=False,
                )
    def test_source_digest_record_cannot_be_rewritten(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            artifacts = Path(directory)
            build_target("contracts", "1.0.0", artifacts)
            manifest_path = next(artifacts.glob("*.members.json"))
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["sourceRecords"][0]["sha256"] = "sha256:" + "0" * 64
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(ReleaseGateError):
                validate_release(
                    target="contracts",
                    closure_path=ROOT / "release" / "manifests" / "contracts.json",
                    artifacts=artifacts,
                    evidence=None,
                    strict=True,
                )
    def test_unlocked_or_incomplete_toolchain_never_qualifies(self) -> None:
        lock = json.loads(
            (ROOT / "release" / "toolchains.lock.json").read_text(encoding="utf-8")
        )
        with self.assertRaises(ReleaseGateError):
            _validate_toolchain_lock(lock)
        forged = json.loads(json.dumps(lock))
        forged["status"] = "LOCKED"
        for value in forged.values():
            if isinstance(value, dict):
                value["verified"] = True
        with self.assertRaises(ReleaseGateError):
            _validate_toolchain_lock(forged)
    def test_writer_one_dot_zero_is_blocked_while_exact_toolchain_is_unlocked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifacts = root / "artifacts"
            evidence = root / "evidence"
            build_target("business-plan-writer", "0.12.4", artifacts)
            evidence.mkdir()
            lock_path = ROOT / "release" / "toolchains.lock.json"
            lock_digest = "sha256:" + hashlib.sha256(lock_path.read_bytes()).hexdigest()
            records = {
                "provider-summary.json": {
                    "status": "PASS",
                    "runCount": 30,
                    "provenanceCount": 30,
                    "runIdCount": 30,
                    "providers": ["codex", "claude-code", "antigravity"],
                },
                "course-summary.json": {
                    "status": "PASS",
                    "validStarters": 10,
                    "complete": 8,
                    "requiredComplete": 8,
                    "improved": 7,
                    "requiredImproved": 7,
                    "blockers": [],
                },
                "beta-summary.json": {
                    "status": "PASS",
                    "participants": 10,
                    "providerAllocation": {"codex": 4, "claude-code": 3, "antigravity": 3},
                    "scopeAllocation": {"QUICK": 5, "SECTION": 5},
                    "complete": 8,
                    "completedByProvider": {"codex": 3, "claude-code": 3, "antigravity": 2},
                    "blockers": [],
                },
                "visual-summary.json": {
                    "status": "PASS",
                    "rendererModes": ["scene-deck", "image-first"],
                    "caseCount": 10,
                    "imageFirstCases": ["R04-I", "R07-I"],
                    "externalVisualPass": True,
                    "criticalDefects": 0,
                    "toolchainLockDigest": lock_digest,
                },
            }
            for name, record in records.items():
                record["sourceEvidenceDigest"] = "sha256:" + "a" * 64
                (evidence / name).write_text(json.dumps(record), encoding="utf-8")
            with self.assertRaises(ReleaseGateError):
                validate_release(
                    target="business-plan-writer",
                    closure_path=ROOT / "release" / "manifests" / "business-plan-writer.json",
                    artifacts=artifacts,
                    evidence=evidence,
                    strict=True,
                )

    def test_evidence_targets_never_qualify_in_non_strict_mode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            artifacts = Path(directory)
            build_target("course-kit", "0.1.0", artifacts)
            with self.assertRaises(ReleaseGateError):
                validate_release(
                    target="course-kit",
                    closure_path=ROOT / "release" / "manifests" / "course-kit.json",
                    artifacts=artifacts,
                    evidence=None,
                    strict=False,
                )

    def test_cross_target_artifact_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            artifacts = Path(directory)
            build_target("contracts", "1.0.0", artifacts)
            with self.assertRaises(ReleaseGateError):
                validate_release(
                    target="course-kit",
                    closure_path=ROOT / "release" / "manifests" / "course-kit.json",
                    artifacts=artifacts,
                    evidence=Path(directory),
                    strict=True,
                )
    def test_target_closure_ignores_unrelated_failure(self) -> None:
        writer = evaluate("business-plan-writer", {"business-documents"}, {"business-documents"})
        self.assertEqual(writer["status"], "PASS")
        self.assertNotIn("business-documents", writer["accessLog"])
        blocked = evaluate("business-plan-writer", set(), {"contracts"})
        self.assertEqual(blocked["status"], "BLOCK")
        documents = evaluate("business-documents", {"business-plan-writer", "course-kit"}, set())
        self.assertEqual(documents["status"], "PASS")

    def test_all_closure_manifests_forbid_unrelated_reads(self) -> None:
        for path in (ROOT / "release" / "manifests").glob("*.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertFalse(set(data["required"]) & set(data["forbiddenReads"]), path.name)


if __name__ == "__main__":
    unittest.main()
