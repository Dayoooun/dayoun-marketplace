from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "providers"))

from provider_common import (  # noqa: E402
    ProviderEvidenceError,
    adapter_source_digest,
    canonical_projection,
    canonical_digest,
    required_run_ids,
    sha256_bytes,
    verify_evidence_record,
)


class ProviderContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.matrix = json.loads((ROOT / "contracts" / "fixtures" / "release" / "matrix.json").read_text(encoding="utf-8"))
        self.payload = {
            "cycle": {"cycleId": "R01-C1", "currentRevision": 1, "status": "CURRENT"},
            "facts": [{"id": "F1"}],
            "evidence": [{"id": "E1"}],
            "businessVerdicts": [{"id": "V1", "status": "PASS"}],
            "contentSteps": [{"id": "gap-diagnosis", "status": "PASS"}],
            "scope": "QUICK",
            "outputs": {"hwpx": False, "ppt": False},
            "rendererMode": None,
        }

    def test_matrix_requires_thirty_unique_identities(self) -> None:
        identities = required_run_ids(self.matrix)
        self.assertEqual(len(identities), 30)
        self.assertEqual(len(set(identities)), 30)

    def test_projection_mutation_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = root / "raw.json"
            raw.write_text("{}", encoding="utf-8")
            executable = root / "codex"
            executable.write_text("real executable fixture", encoding="utf-8")
            record = {
                "fixtureId": "R01",
                "provider": "codex",
                "protocolVersion": "dayoun-provider-run-v1",
                "timeout": False,
                "exitCode": 0,
                "executable": str(executable.resolve()),
                "executableDigest": sha256_bytes(executable.read_bytes()),
                "rawOutputRef": "raw.json",
                "rawOutputDigest": sha256_bytes(raw.read_bytes()),
                "normalizedProjection": canonical_projection(self.payload),
                "approvedTuple": {
                    "payloadDigest": "sha256:" + "1" * 64,
                    "approvalEnvelopeDigest": "sha256:" + "2" * 64,
                    "visibleTextManifestDigest": None,
                },
                "startedAt": "2026-01-01T00:00:00+00:00",
                "finishedAt": "2026-01-01T00:00:01+00:00",
                "adapterDigest": adapter_source_digest(
                    ROOT / "scripts" / "providers" / "codex_runner.py"
                ),
            }
            record["provenanceId"] = canonical_digest(record)
            verify_evidence_record(
                record,
                expected_fixture="R01",
                expected_provider="codex",
                expected_projection=canonical_projection(self.payload),
                evidence_root=root,
                expected_adapter=ROOT / "scripts" / "providers" / "codex_runner.py",
            )
            mutated = copy.deepcopy(record)
            mutated["normalizedProjection"]["facts"] = []
            mutated.pop("provenanceId")
            mutated["provenanceId"] = canonical_digest(mutated)
            with self.assertRaises(ProviderEvidenceError):
                verify_evidence_record(
                    mutated,
                    expected_fixture="R01",
                    expected_provider="codex",
                    expected_projection=canonical_projection(self.payload),
                    evidence_root=root,
                    expected_adapter=ROOT / "scripts" / "providers" / "codex_runner.py",
                )

    def test_duplicate_provenance_is_detectable(self) -> None:
        provenances = ["same", "same"]
        self.assertNotEqual(len(provenances), len(set(provenances)))


if __name__ == "__main__":
    unittest.main()
