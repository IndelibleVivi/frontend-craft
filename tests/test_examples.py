"""Keep the public offline walkthrough reproducible through the real CLI."""

import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples" / "memory"


class PublicMemoryExampleTests(unittest.TestCase):
    def run_example(self, verb, *args):
        result = subprocess.run(
            [sys.executable, "scripts/fc_memory.py", verb,
             "--root", "examples/memory", *args],
            cwd=ROOT, text=True, capture_output=True, check=True,
        )
        return json.loads(result.stdout)

    def query(self, *extra, term="help"):
        return self.run_example(
            "query", "--project", "lumen-notes", "--surface", "editor",
            "--term", term, *extra,
        )

    def test_documented_validation_and_scoped_query(self):
        validation = self.run_example("validate")
        self.assertEqual(validation["status"], "valid")
        self.assertEqual(validation["case_store"]["case_count"], 2)
        result = self.query()
        self.assertEqual(result["mode"], "lexical")
        self.assertEqual(result["status"], "matched")
        self.assertEqual(result["returned"], 1)
        case = result["cases"][0]["case"]
        self.assertEqual(case["id"], "lumen-visible-help")
        self.assertEqual(case["basis"], "explicit-feedback")
        self.assertEqual(case["outcome"], "rejected")
        self.assertEqual(result["context"]["text"],
                         (FIXTURE / "context.md").read_text(encoding="utf-8"))

    def test_documented_transfer_retains_origin_and_uncertainty(self):
        result = self.query("--transfer")
        self.assertEqual(result["returned"], 2)
        cases = {item["case"]["id"]: item for item in result["cases"]}
        self.assertFalse(cases["lumen-visible-help"]["analogy"])
        analogy = cases["orchard-visible-help"]
        self.assertTrue(analogy["analogy"])
        self.assertEqual(analogy["current_scope"],
                         {"project": "orchard", "surface": "editor"})
        self.assertEqual(analogy["case"]["basis"], "hypothesis")
        self.assertEqual(analogy["case"]["outcome"], "unknown")

    def test_documented_miss_keeps_complete_context(self):
        result = self.query(term="absent-example-term")
        self.assertEqual(result["status"], "no_match")
        self.assertEqual(result["returned"], 0)
        self.assertEqual(result["cases"], [])
        self.assertEqual(result["context"]["text"],
                         (FIXTURE / "context.md").read_text(encoding="utf-8"))
