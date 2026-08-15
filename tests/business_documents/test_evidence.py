from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from aggregate_documents_evidence import aggregate_documents  # noqa: E402

DIGEST = "sha256:" + "a" * 64


class DocumentsEvidenceTests(unittest.TestCase):
    def evidence(self) -> dict:
        return {
            "cases": [
                {
                    "kind": kind,
                    "rendererStatus": "PASS",
                    "browserVisualStatus": "PASS",
                    "inputEvidence": {
                        "evidenceRef": f"{kind}-input.json",
                        "evidenceDigest": DIGEST,
                    },
                    "artifactEvidence": {
                        "evidenceRef": f"{kind}-artifact.html",
                        "evidenceDigest": DIGEST,
                    },
                    "screenshotEvidence": {
                        "evidenceRef": f"{kind}-screenshot.png",
                        "evidenceDigest": DIGEST,
                    },
                    "remoteUrls": 0,
                    "privacyFindings": 0,
                }
                for kind in ("quote", "profile", "official", "notice", "poster")
            ],
            "criticalDefects": [],
        }

    def test_complete_documents_matrix_passes(self) -> None:
        self.assertEqual(aggregate_documents(self.evidence())["status"], "PASS")

    def test_missing_visual_or_kind_blocks(self) -> None:
        missing = self.evidence()
        missing["cases"].pop()
        self.assertEqual(aggregate_documents(missing)["status"], "BLOCK")
        visual = copy.deepcopy(self.evidence())
        visual["cases"][0]["browserVisualStatus"] = "BLOCK"
        self.assertEqual(aggregate_documents(visual)["status"], "BLOCK")


if __name__ == "__main__":
    unittest.main()
