#!/usr/bin/env python3
"""Tests for the Frontend Craft read-only design-record helper.

All data here is synthetic and invented (projects ``lumen-notes``, ``orchard``,
``tessera``; topics such as inline-help visibility). No real project names,
personal preferences, transcripts, or private receipts are used.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "fc_memory.py"

SPEC = importlib.util.spec_from_file_location("fc_memory", SCRIPT)
assert SPEC and SPEC.loader
MEM = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MEM)

CONTEXT_TEXT = "# Synthetic design context\n\nSmall record; read whole.\n"


def run_cli(*args: str) -> tuple[int, dict]:
    """Invoke main() in-process and capture the JSON it prints."""
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        try:
            code = MEM.main(list(args))
        except SystemExit as exc:  # argparse usage exit
            code = int(exc.code or 0)
    out = stream.getvalue().strip()
    payload = json.loads(out) if out else {}
    return code, payload


def case(**overrides):
    base = {
        "id": "case-1",
        "title": "Sample",
        "updated": "2026-09-21",
        "scope": {"project": "alpha", "surface": "*"},
        "status": "active",
        "basis": "observed-result",
        "outcome": "mixed",
        "statement": "A short statement.",
        "next_action": "Do the thing next time.",
        "limits": "Only within this project.",
        "evidence": ["pointer-1"],
        "keywords": ["help"],
    }
    base.update(overrides)
    return base


class HelperFixture(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="fc-memory-test-")
        self.root = Path(self._tmp.name)
        self.write_context(CONTEXT_TEXT)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write_context(self, text: str) -> None:
        (self.root / "context.md").write_text(text, encoding="utf-8")

    def write_cases(self, data) -> None:
        (self.root / "cases.json").write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8"
        )

    def write_cases_raw(self, data: bytes) -> None:
        (self.root / "cases.json").write_bytes(data)

    def snapshot(self) -> dict:
        result = {}
        for name in ("context.md", "cases.json"):
            path = self.root / name
            result[name] = path.read_bytes() if path.exists() else None
        return result

    def q(self, *extra: str, project: str = "alpha", surface: str = "editor") -> tuple[int, dict]:
        return run_cli(
            "query", "--root", str(self.root), "--project", project,
            "--surface", surface, *extra,
        )


class QueryTests(HelperFixture):
    def setUp(self) -> None:
        super().setUp()
        self.write_cases(
            {
                "version": 1,
                "cases": [
                    case(
                        id="fc-help-cue",
                        title="Inline help must stay visible",
                        scope={"project": "lumen-notes", "surface": "*"},
                        basis="explicit-feedback",
                        outcome="rejected",
                        statement="The inline help cue read as missing when it was hover-only.",
                        next_action="Keep the primary inline help visible near the control.",
                        limits="Not a global ban on tooltips.",
                        keywords=["help", "inline help", "提示", "可见"],
                    ),
                    case(
                        id="fc-help-old",
                        title="Older help placement guess",
                        scope={"project": "lumen-notes", "surface": "*"},
                        status="superseded",
                        basis="hypothesis",
                        outcome="unknown",
                        statement="Early guess about help placement.",
                        next_action="n/a",
                        limits="superseded",
                        keywords=["help"],
                        superseded_by="fc-help-cue",
                    ),
                    case(
                        id="fc-orchard-identity",
                        title="Orchard identity note",
                        scope={"project": "orchard", "surface": "*"},
                        basis="observed-result",
                        outcome="mixed",
                        statement="Different product identity.",
                        next_action="Keep identity; generic polish is not lossless.",
                        limits="Project only.",
                        keywords=["identity", "身份"],
                    ),
                ],
            }
        )

    def test_chinese_english_alias_and_casefold(self) -> None:
        for term in ("提示", "inline help", "INLINE HELP"):
            code, payload = self.q("--term", term, project="lumen-notes")
            self.assertEqual(code, MEM.EXIT_OK, payload)
            ids = [item["case"]["id"] for item in payload["cases"]]
            self.assertEqual(ids, ["fc-help-cue"], term)
            self.assertIn(term, payload["cases"][0]["matched_terms"])

    def test_duplicate_terms_dedupe_by_casefold(self) -> None:
        code, payload = self.q("--term", "help", "--term", "HELP", "--term", "help",
                               project="lumen-notes")
        self.assertEqual(code, MEM.EXIT_OK)
        self.assertEqual(payload["terms"], ["help"])
        self.assertEqual(payload["cases"][0]["matched_terms"], ["help"])

    def test_blank_term_is_a_usage_error(self) -> None:
        code, payload = self.q("--term", "   ")
        self.assertEqual(code, MEM.EXIT_USAGE)
        self.assertEqual(payload["status"], "usage_error")

    def test_scope_project_and_surface_axes_and_wildcards(self) -> None:
        self.write_cases(
            {
                "version": 1,
                "cases": [
                    case(id="p-s", scope={"project": "lumen-notes", "surface": "editor"},
                         keywords=["axis"]),
                    case(id="p-star", scope={"project": "lumen-notes", "surface": "*"},
                         keywords=["axis"]),
                    case(id="star-s", scope={"project": "*", "surface": "editor"},
                         keywords=["axis"]),
                    case(id="star-star", scope={"project": "*", "surface": "*"},
                         keywords=["axis"]),
                ],
            }
        )
        code, payload = self.q("--term", "axis", project="lumen-notes", surface="editor")
        self.assertEqual(
            sorted(item["case"]["id"] for item in payload["cases"]),
            ["p-s", "p-star", "star-s", "star-star"],
        )
        code, payload = self.q("--term", "axis", project="lumen-notes", surface="*")
        self.assertEqual(
            sorted(item["case"]["id"] for item in payload["cases"]),
            ["p-star", "star-star"],
        )
        code, payload = self.q("--term", "axis", project="*", surface="*")
        self.assertEqual([item["case"]["id"] for item in payload["cases"]], ["star-star"])
        code, payload = self.q("--term", "axis", project="unrelated", surface="editor")
        self.assertEqual(
            sorted(item["case"]["id"] for item in payload["cases"]),
            ["star-s", "star-star"],
        )

    def test_match_ranks_by_distinct_term_count(self) -> None:
        self.write_cases(
            {
                "version": 1,
                "cases": [
                    case(id="two", title="two hits", statement="dense inline help",
                         keywords=["dense", "help"]),
                    case(id="one", title="one hit", statement="dense surface", keywords=["dense"]),
                    case(id="zero", title="none", statement="unrelated", keywords=["unrelated"]),
                ],
            }
        )
        code, payload = self.q("--term", "dense", "--term", "help")
        ids = [item["case"]["id"] for item in payload["cases"]]
        self.assertEqual(ids[0], "two")
        self.assertEqual(payload["cases"][0]["matched_terms"], ["dense", "help"])
        self.assertNotIn("zero", ids)

    def test_default_limit_is_eight_and_cli_limit_overrides(self) -> None:
        cases = [
            case(id=f"c{i:03d}", title="repeated topic", keywords=["topic"])
            for i in range(20)
        ]
        self.write_cases({"version": 1, "cases": cases})
        code, payload = self.q("--term", "topic")
        self.assertEqual(code, MEM.EXIT_OK)
        self.assertEqual(payload["matched"], 20)
        self.assertEqual(payload["returned"], 8)
        self.assertTrue(payload["truncated"])
        self.assertEqual([item["case"]["id"] for item in payload["cases"]],
                         [f"c{i:03d}" for i in range(8)])
        code, payload = self.q("--term", "topic", "--limit", "3")
        self.assertEqual(payload["returned"], 3)
        self.assertEqual([item["case"]["id"] for item in payload["cases"]],
                         ["c000", "c001", "c002"])

    def test_scope_only_browse_without_terms(self) -> None:
        code, payload = self.q(project="lumen-notes")
        self.assertEqual(code, MEM.EXIT_OK)
        self.assertEqual(payload["mode"], "scope_only")
        self.assertEqual(payload["status"], "matched")
        ids = {item["case"]["id"] for item in payload["cases"]}
        self.assertIn("fc-help-cue", ids)
        self.assertNotIn("fc-help-old", ids)
        self.assertNotIn("fc-orchard-identity", ids)

    def test_retired_excluded_from_query_but_visible_via_show(self) -> None:
        self.write_cases(
            {
                "version": 1,
                "cases": [
                    case(id="live", keywords=["cue"]),
                    case(id="gone", status="retired", keywords=["cue"]),
                ],
            }
        )
        code, payload = self.q("--term", "cue")
        self.assertEqual([item["case"]["id"] for item in payload["cases"]], ["live"])
        code, payload = run_cli("show", "--root", str(self.root), "--id", "gone")
        self.assertEqual(code, MEM.EXIT_OK)
        self.assertEqual(payload["case"]["status"], "retired")

    def test_superseded_excluded_from_query_but_visible_via_show(self) -> None:
        code, payload = self.q("--term", "help", project="lumen-notes")
        self.assertEqual([item["case"]["id"] for item in payload["cases"]], ["fc-help-cue"])
        code, payload = run_cli("show", "--root", str(self.root), "--id", "fc-help-old")
        self.assertEqual(code, MEM.EXIT_OK)
        self.assertEqual(payload["case"]["status"], "superseded")
        self.assertEqual(payload["case"]["basis"], "hypothesis")

    def test_hypothesis_keeps_its_basis_label(self) -> None:
        self.write_cases(
            {"version": 1, "cases": [case(id="h", basis="hypothesis", keywords=["guess"])]}
        )
        code, payload = self.q("--term", "guess")
        self.assertEqual(payload["cases"][0]["case"]["basis"], "hypothesis")
        self.assertEqual(payload["cases"][0]["case"]["status"], "active")

    def test_similar_but_opposite_both_surface_with_outcomes(self) -> None:
        self.write_cases(
            {
                "version": 1,
                "cases": [
                    case(id="like", title="likes density", outcome="accepted",
                         statement="Enjoys dense comparison here.", keywords=["density"]),
                    case(id="dislike", title="dislikes density", outcome="rejected",
                         statement="Rejects dense tables here.", keywords=["density"]),
                ],
            }
        )
        code, payload = self.q("--term", "density")
        found = {item["case"]["id"]: item["case"]["outcome"] for item in payload["cases"]}
        self.assertEqual(found, {"like": "accepted", "dislike": "rejected"})

    def test_zero_match_is_explicit_not_a_preference_claim(self) -> None:
        code, payload = self.q("--term", "zzzznomatch")
        self.assertEqual(code, MEM.EXIT_OK)
        self.assertEqual(payload["status"], "no_match")
        self.assertEqual(payload["matched"], 0)
        self.assertEqual(payload["cases"], [])

    def test_lexical_miss_on_paraphrase_keeps_context(self) -> None:
        # Chinese paraphrases of hover-only help; neither is a stored alias.
        # The target is available by ID, but literal retrieval cannot infer it.
        code, payload = self.q(
            "--term", "悬停", "--term", "隐藏指引", project="lumen-notes"
        )
        self.assertEqual(code, MEM.EXIT_OK)
        self.assertEqual(payload["status"], "no_match")
        self.assertEqual(payload["matched"], 0)
        self.assertEqual(payload["cases"], [])
        self.assertEqual(payload["context"]["text"], CONTEXT_TEXT)
        code, target = run_cli(
            "show", "--root", str(self.root), "--id", "fc-help-cue"
        )
        self.assertEqual(code, MEM.EXIT_OK)
        self.assertIn("hover-only", target["case"]["statement"])

    def test_missing_store_is_distinct_from_no_match(self) -> None:
        self.root.joinpath("cases.json").unlink()
        code, payload = self.q("--term", "x")
        self.assertEqual(code, MEM.EXIT_OK)
        self.assertEqual(payload["status"], "store_missing")
        self.assertEqual(payload["case_store"]["state"], "missing")

    def test_context_returned_whole_even_when_truncated(self) -> None:
        code, payload = self.q("--term", "help", project="lumen-notes")
        self.assertTrue(payload["context"]["available"])
        self.assertEqual(payload["context"]["text"], CONTEXT_TEXT)

    def test_missing_context_reported_but_query_still_works(self) -> None:
        self.root.joinpath("context.md").unlink()
        code, payload = self.q("--term", "help", project="lumen-notes")
        self.assertEqual(code, MEM.EXIT_OK)
        self.assertFalse(payload["context"]["available"])
        self.assertEqual(payload["context"]["state"], "missing")
        self.assertEqual(payload["status"], "matched")


class ShowTests(HelperFixture):
    def test_unknown_id_is_not_found(self) -> None:
        self.write_cases({"version": 1, "cases": [case(id="only")]})
        code, payload = run_cli("show", "--root", str(self.root), "--id", "missing")
        self.assertEqual(code, MEM.EXIT_NOT_FOUND)
        self.assertEqual(payload["status"], "not_found")
        self.assertNotIn("case", payload)


class ValidateTests(HelperFixture):
    def test_validate_ok(self) -> None:
        self.write_cases({"version": 1, "cases": [case()]})
        code, payload = run_cli("validate", "--root", str(self.root))
        self.assertEqual(code, MEM.EXIT_OK)
        self.assertEqual(payload["status"], "valid")
        self.assertEqual(payload["case_store"]["case_count"], 1)

    def test_validate_rejects_non_integer_version(self) -> None:
        for version in (2, "1", True, 1.0, None):
            self.write_cases({"version": version, "cases": []})
            code, payload = run_cli("validate", "--root", str(self.root))
            self.assertEqual(code, MEM.EXIT_INVALID, version)
            self.assertEqual(payload["status"], "invalid", version)

    def test_validate_rejects_bad_enum(self) -> None:
        self.write_cases({"version": 1, "cases": [case(status="blessed")]})
        code, _ = run_cli("validate", "--root", str(self.root))
        self.assertEqual(code, MEM.EXIT_INVALID)

    def test_validate_rejects_bad_updated_date(self) -> None:
        for value in ("2026-13-01", "2026-09-31", "21-09-2026", "2026/09/21", "yesterday"):
            self.write_cases({"version": 1, "cases": [case(updated=value)]})
            code, _ = run_cli("validate", "--root", str(self.root))
            self.assertEqual(code, MEM.EXIT_INVALID, value)

    def test_validate_accepts_real_date(self) -> None:
        self.write_cases({"version": 1, "cases": [case(updated="2024-02-29")]})
        code, _ = run_cli("validate", "--root", str(self.root))
        self.assertEqual(code, MEM.EXIT_OK)

    def test_validate_separates_missing_from_invalid(self) -> None:
        self.root.joinpath("context.md").unlink()
        self.write_cases({"version": 1, "cases": []})
        code, payload = run_cli("validate", "--root", str(self.root))
        self.assertEqual(code, MEM.EXIT_MISSING)
        self.assertEqual(payload["context"]["state"], "missing")

        self.write_context(CONTEXT_TEXT)
        self.write_cases_raw(b'{ not json')
        code, payload = run_cli("validate", "--root", str(self.root))
        self.assertEqual(code, MEM.EXIT_INVALID)
        self.assertEqual(payload["case_store"]["state"], "invalid")

    def test_malformed_utf8_is_a_clean_error(self) -> None:
        self.write_cases_raw(b'{"version": 1, "cases": []}\xff\xfe')
        code, payload = run_cli("validate", "--root", str(self.root))
        self.assertEqual(code, MEM.EXIT_INVALID)
        self.assertIn("UTF-8", payload["errors"][0])
        code, payload = self.q("--term", "x")
        self.assertEqual(code, MEM.EXIT_INVALID)
        self.assertEqual(payload["error"], "invalid_case_store")

    def test_bad_json_is_a_clear_error_not_silent_skip(self) -> None:
        self.write_cases_raw(b'{"version": 1, "cases": [}')
        code, payload = self.q("--term", "x")
        self.assertEqual(code, MEM.EXIT_INVALID)
        self.assertEqual(payload["error"], "invalid_case_store")


class SupersessionTests(HelperFixture):
    def test_superseded_requires_superseded_by(self) -> None:
        self.write_cases({"version": 1, "cases": [case(id="x", status="superseded")]})
        code, _ = run_cli("validate", "--root", str(self.root))
        self.assertEqual(code, MEM.EXIT_INVALID)

    def test_self_reference_rejected(self) -> None:
        self.write_cases(
            {"version": 1, "cases": [case(id="x", status="superseded", superseded_by="x")]}
        )
        code, _ = run_cli("validate", "--root", str(self.root))
        self.assertEqual(code, MEM.EXIT_INVALID)

    def test_cross_scope_supersession_rejected(self) -> None:
        self.write_cases(
            {
                "version": 1,
                "cases": [
                    case(id="a", status="superseded", scope={"project": "p", "surface": "*"},
                         superseded_by="b"),
                    case(id="b", scope={"project": "q", "surface": "*"}),
                ],
            }
        )
        code, payload = run_cli("validate", "--root", str(self.root))
        self.assertEqual(code, MEM.EXIT_INVALID)
        self.assertIn("same scope", payload["errors"][0])

    def test_dangling_supersession_rejected(self) -> None:
        self.write_cases(
            {"version": 1, "cases": [case(id="a", status="superseded", superseded_by="ghost")]}
        )
        code, _ = run_cli("validate", "--root", str(self.root))
        self.assertEqual(code, MEM.EXIT_INVALID)

    def test_cycle_rejected(self) -> None:
        self.write_cases(
            {
                "version": 1,
                "cases": [
                    case(id="a", status="superseded", superseded_by="b"),
                    case(id="b", status="superseded", superseded_by="a"),
                ],
            }
        )
        code, payload = run_cli("validate", "--root", str(self.root))
        self.assertEqual(code, MEM.EXIT_INVALID)
        self.assertIn("cycle", payload["errors"][0])

    def test_long_valid_chain_is_accepted(self) -> None:
        # Beyond Python's default recursion limit; this is not a timing assertion.
        length = 2000
        cases = []
        for i in range(length):
            overrides = {"id": f"c{i:04d}"}
            if i < length - 1:
                overrides.update(status="superseded", superseded_by=f"c{i + 1:04d}")
            cases.append(case(**overrides))
        self.write_cases({"version": 1, "cases": cases})
        code, payload = run_cli("validate", "--root", str(self.root))
        self.assertEqual(code, MEM.EXIT_OK, payload)

    def test_valid_supersession_accepted(self) -> None:
        self.write_cases(
            {
                "version": 1,
                "cases": [
                    case(id="old", status="superseded", superseded_by="new"),
                    case(id="new", title="revised", statement="Replaced default."),
                ],
            }
        )
        code, payload = run_cli("validate", "--root", str(self.root))
        self.assertEqual(code, MEM.EXIT_OK, payload)


class BoundaryTests(HelperFixture):
    def test_symlinked_case_file_is_refused(self) -> None:
        outside = self.root.parent / (self.root.name + "-outside.json")
        outside.write_text(json.dumps({"version": 1, "cases": []}), encoding="utf-8")
        try:
            (self.root / "cases.json").symlink_to(outside)
            code, payload = run_cli("validate", "--root", str(self.root))
            self.assertEqual(code, MEM.EXIT_INVALID)
            self.assertEqual(payload["case_store"]["state"], "invalid")
        finally:
            outside.unlink()

    def test_symlinked_context_is_refused(self) -> None:
        outside = self.root.parent / (self.root.name + "-ctx.md")
        outside.write_text("# external\n", encoding="utf-8")
        try:
            (self.root / "context.md").unlink()
            (self.root / "context.md").symlink_to(outside)
            code, _ = run_cli("validate", "--root", str(self.root))
            self.assertEqual(code, MEM.EXIT_INVALID)
        finally:
            outside.unlink()

    def test_files_unchanged_before_and_after(self) -> None:
        self.write_cases({"version": 1, "cases": [case(id="x", keywords=["help"])]})
        before = self.snapshot()
        run_cli("query", "--root", str(self.root), "--project", "alpha",
                "--surface", "editor", "--term", "help")
        run_cli("show", "--root", str(self.root), "--id", "x")
        run_cli("validate", "--root", str(self.root))
        self.assertEqual(before, self.snapshot())

    def test_limit_must_be_positive(self) -> None:
        self.write_cases({"version": 1, "cases": [case()]})
        code, _ = self.q("--term", "help", "--limit", "0")
        self.assertEqual(code, MEM.EXIT_USAGE)

    def test_root_must_exist(self) -> None:
        code, payload = run_cli("validate", "--root", str(self.root / "does-not-exist"))
        self.assertEqual(code, MEM.EXIT_MISSING)
        self.assertEqual(payload["status"], "missing")


class GrowthTests(HelperFixture):
    """A generated ~2000-case store: bounded, deterministic, scope-correct."""

    def _build(self, count: int = 2000) -> dict:
        projects = ["lumen-notes", "orchard", "tessera", "*"]
        surfaces = ["editor", "reader", "*"]
        statuses = ["active", "active", "active", "superseded", "retired"]
        cases = []
        for i in range(count):
            scope = {"project": projects[i % len(projects)],
                     "surface": surfaces[i % len(surfaces)]}
            status = statuses[i % len(statuses)]
            overrides = {
                "id": f"gen-{i:05d}",
                "title": f"Case {i} about density",
                "scope": scope,
                "status": status,
                "keywords": ["density", f"tag{i % 7}"],
            }
            if status == "superseded":
                # point to a same-scope active neighbour that exists later
                overrides["superseded_by"] = f"gen-{min(i + 1, count - 1):05d}"
            cases.append(case(**overrides))
        # Repair any superseded target that itself is non-active or cross-scope.
        by_id = {c["id"]: c for c in cases}
        for c in cases:
            if c["status"] != "superseded":
                continue
            target = by_id[c["superseded_by"]]
            if target["status"] != "active" or target["scope"] != c["scope"]:
                replacement = next(
                    g for g in cases
                    if g["status"] == "active" and g["scope"] == c["scope"]
                )
                c["superseded_by"] = replacement["id"]
        return {"version": 1, "cases": cases}

    def test_growth_store_validate_ok(self) -> None:
        document = self._build()
        self.write_cases(document)
        code, payload = run_cli("validate", "--root", str(self.root))
        self.assertEqual(code, MEM.EXIT_OK, payload)
        self.assertEqual(payload["case_store"]["case_count"], 2000)

    def test_growth_query_returns_only_eligible_subset(self) -> None:
        document = self._build()
        self.write_cases(document)
        expected = [
            c["id"] for c in document["cases"]
            if c["status"] == "active"
            and c["scope"]["project"] in ("lumen-notes", "*")
            and c["scope"]["surface"] in ("editor", "*")
        ]
        code, payload = self.q(
            "--term", "density", "--limit", "100000",
            project="lumen-notes", surface="editor",
        )
        self.assertEqual(code, MEM.EXIT_OK)
        returned = [item["case"]["id"] for item in payload["cases"]]
        self.assertEqual(returned, expected)
        self.assertEqual(payload["matched"], len(expected))
        self.assertEqual(payload["returned"], len(expected))
        self.assertFalse(payload["truncated"])
        # No leaks from other scopes or non-active statuses.
        for item in payload["cases"]:
            self.assertEqual(item["case"]["status"], "active")
            self.assertIn(item["case"]["scope"]["project"], ("lumen-notes", "*"))
            self.assertIn(item["case"]["scope"]["surface"], ("editor", "*"))

    def test_growth_default_limit_is_bounded_and_deterministic(self) -> None:
        self.write_cases(self._build())
        code, first = self.q("--term", "density", project="lumen-notes", surface="editor")
        self.assertEqual(first["returned"], 8)
        self.assertTrue(first["truncated"])
        self.assertGreater(first["matched"], 8)
        # ordering stable by matched-term count then id, and repeatable
        ids = [item["case"]["id"] for item in first["cases"]]
        self.assertEqual(ids, sorted(ids))
        code, second = self.q("--term", "density", project="lumen-notes", surface="editor")
        self.assertEqual(ids, [item["case"]["id"] for item in second["cases"]])
        self.assertEqual(first["context"]["text"], CONTEXT_TEXT)


if __name__ == "__main__":
    unittest.main()
