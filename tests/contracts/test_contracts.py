from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from contract_utils import (  # noqa: E402
    ContractError,
    aggregate_validation,
    assert_declared_aggregate,
    canonical_digest,
    load_json,
    validate_schema,
)


class ContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = load_json(ROOT / "contracts" / "schemas" / "canonical.schema.json")
        self.payload = {
            "schemaVersion": "1.0.0",
            "projectId": "demo",
            "cycle": {"cycleId": "demo-C1", "currentRevision": 1, "status": "CURRENT"},
            "facts": [{"id": "F1", "claim": "매출은 10원", "value": 10, "unit": "KRW", "evidenceRefs": ["E1"]}],
            "evidence": [{"id": "E1", "source": "ledger", "locator": "row:1"}],
            "requirements": [{"id": "Q1", "text": "근거 필수", "sourceRef": "E1", "status": "REQUIRED"}],
            "decisions": [{"id": "D1", "value": "진행", "approvedBy": "owner"}],
            "businessVerdicts": [{"id": "V1", "status": "PASS", "reason": "근거 확인", "evidenceRefs": ["E1"]}],
            "contentSteps": [
                {"id": step, "status": "PASS", "evidenceRefs": ["E1"]}
                for step in ("gap-diagnosis", "evidence-record", "change-record", "action-card")
            ],
            "scope": "QUICK",
            "outputs": {"hwpx": False, "ppt": True},
            "rendererMode": "image-first",
        }

    def test_payload_validates_and_jcs_ignores_key_order(self) -> None:
        validate_schema(self.payload, self.schema, label="payload")
        reversed_payload = dict(reversed(list(self.payload.items())))
        self.assertEqual(canonical_digest(self.payload), canonical_digest(reversed_payload))

    def test_unknown_field_and_missing_evidence_fail(self) -> None:
        unknown = copy.deepcopy(self.payload)
        unknown["invented"] = True
        with self.assertRaises(ContractError):
            validate_schema(unknown, self.schema, label="payload")
        missing = copy.deepcopy(self.payload)
        missing["facts"][0]["evidenceRefs"] = []
        with self.assertRaises(ContractError):
            validate_schema(missing, self.schema, label="payload")

    def test_strict_aggregate_cannot_be_overridden(self) -> None:
        record = {
            "validators": {
                "fact": {"status": "PASS"},
                "structure": {"status": "BLOCK"},
                "contract": {"status": "PASS"},
            },
            "outputs": {
                "hwpx": {"requested": False, "automationStatus": "NOT_REQUESTED", "visualStatus": "NOT_REQUESTED"},
                "ppt": {"requested": True, "automationStatus": "PASS", "visualStatus": "PASS"},
            },
            "attempt": 1,
            "approvalStatus": "CURRENT",
            "aggregateStatus": "PASS",
        }
        self.assertEqual(aggregate_validation(record), "BLOCK")
        with self.assertRaises(ContractError):
            assert_declared_aggregate(record)

    def test_release_matrix_is_exactly_thirty_real_run_identities(self) -> None:
        matrix = json.loads((ROOT / "contracts" / "fixtures" / "release" / "matrix.json").read_text(encoding="utf-8"))
        identities = {(case["id"], provider) for case in matrix["cases"] for provider in matrix["providers"]}
        self.assertEqual(len(matrix["cases"]), 10)
        self.assertEqual(len(identities), 30)
        self.assertEqual(matrix["expectedRunCount"], 30)


if __name__ == "__main__":
    unittest.main()
