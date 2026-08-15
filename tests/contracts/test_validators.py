from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VALIDATORS = ROOT / "plugins" / "business-plan-writer" / "validators"
sys.path.insert(0, str(VALIDATORS))

from aggregate_validators import aggregate  # noqa: E402
from contract_validator import validate_contract  # noqa: E402
from fact_validator import validate_facts  # noqa: E402
from structure_validator import validate_structure  # noqa: E402

DIGEST = "sha256:" + "a" * 64


class IndependentValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = json.loads(
            (ROOT / "contracts" / "fixtures" / "release" / "R01" / "canonical.json").read_text(
                encoding="utf-8"
            )
        )
        self.policy = json.loads(
            (ROOT / "contracts" / "policies" / "scope-steps.json").read_text(encoding="utf-8")
        )

    def test_three_validators_pass_valid_fixture(self) -> None:
        self.assertEqual(validate_facts(self.payload), [])
        self.assertEqual(validate_structure(self.payload, self.policy), [])
        self.assertEqual(
            validate_contract(
                self.payload,
                contracts_root=ROOT / "contracts",
                approval_digest=None,
                approval_store=None,
                require_approval=False,
            ),
            [],
        )

    def test_fact_and_scope_bypasses_block(self) -> None:
        missing = copy.deepcopy(self.payload)
        missing["facts"][0]["evidenceRefs"] = ["UNKNOWN"]
        self.assertTrue(validate_facts(missing))
        scope = copy.deepcopy(self.payload)
        scope["contentSteps"][0]["status"] = "NOT_REVIEWED"
        self.assertIn("required-step-not-pass:gap-diagnosis", validate_structure(scope, self.policy))

    def test_no_override_aggregate_rejects_second_failed_attempt(self) -> None:
        records = {
            role: {
                "status": "PASS",
                "validatorId": f"{role}-validator",
                "validatorVersion": "v1",
                "evidenceRefs": [DIGEST],
                "artifactDigest": DIGEST,
                "reason": "pass",
            }
            for role in ("fact", "structure", "contract")
        }
        outputs = {
            "hwpx": {"requested": False, "automationStatus": "NOT_REQUESTED", "visualStatus": "NOT_REQUESTED"},
            "ppt": {"requested": False, "automationStatus": "NOT_REQUESTED", "visualStatus": "NOT_REQUESTED"},
        }
        passed = aggregate(
            records,
            outputs,
            cycle_id="cycle",
            approval_revision=1,
            approval_digest=DIGEST,
            attempt=1,
        )
        self.assertEqual(passed["aggregateStatus"], "PASS")
        records["fact"]["status"] = "BLOCK"
        rejected = aggregate(
            records,
            outputs,
            cycle_id="cycle",
            approval_revision=2,
            approval_digest=DIGEST,
            attempt=2,
        )
        self.assertEqual(rejected["aggregateStatus"], "REJECTED")


if __name__ == "__main__":
    unittest.main()
