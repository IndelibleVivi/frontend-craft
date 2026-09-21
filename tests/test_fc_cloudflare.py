#!/usr/bin/env python3
"""Tests for the Cloudflare Workers AI + Vectorize memory layer.

No network: every HTTP call goes through an injected ``sender``. All data is
synthetic (projects ``lumen-notes``/``orchard``); no real account ids or tokens.

These tests encode the corrected contract and will FAIL if the old behavior
returns (missing /accounts in URLs, composite ns: ids, scope_key metadata,
returning foreign same-named ids, silent fallback, lost mutation ids).
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import fc_cloudflare as FC  # noqa: E402

MEM_SPEC = importlib.util.spec_from_file_location("fc_memory", SCRIPTS / "fc_memory.py")
assert MEM_SPEC and MEM_SPEC.loader
MEM = importlib.util.module_from_spec(MEM_SPEC)
MEM_SPEC.loader.exec_module(MEM)

CLASSIC_REASON = "stale_revision"


def config(**overrides):
    base = {
        "version": 1,
        "account_id": "a" * 32,
        "index_name": "frontend-craft-memory",
        "namespace": "fc-test-ns-0001",
        "model": "@cf/baai/bge-m3",
        "dimensions": 1024,
        "metric": "cosine",
        "auth": "env",
    }
    base.update(overrides)
    return base


def case(**overrides):
    base = {
        "id": "fc-help-cue",
        "title": "Inline help must stay visible",
        "updated": "2026-09-21",
        "scope": {"project": "lumen-notes", "surface": "*"},
        "status": "active",
        "basis": "explicit-feedback",
        "outcome": "rejected",
        "statement": "A hover-only help cue read as missing.",
        "next_action": "Keep primary inline help visible near the control.",
        "limits": "Not a global ban on tooltips.",
        "evidence": ["/secret/path/receipt.json"],
        "keywords": ["help", "inline help"],
    }
    base.update(overrides)
    return base


class RecordingSender:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, method, url, body, headers):
        self.calls.append({"method": method, "url": url, "body": body, "headers": dict(headers)})
        if not self.responses:
            raise AssertionError(f"unexpected extra call: {method} {url}")
        status, payload = self.responses.pop(0)
        return status, json.dumps(payload).encode("utf-8")


def transport_with(sender):
    return FC.Transport("a" * 32, "test-token", sender=sender)


def ok_embed(rows=1):
    return (200, {"success": True, "result": {"data": [[0.0] * 1024 for _ in range(rows)]}})


def metadata_list(names=(("project_key", "String"), ("surface_key", "String"))):
    return (200, {"success": True, "result": {"metadataIndexes": [
        {"propertyName": n, "indexType": k} for n, k in names]}})


class UrlTests(unittest.TestCase):
    def test_no_vectorize_url_lacks_accounts_prefix(self) -> None:
        # Regression guard: the old bug omitted /accounts and produced
        # /<account>/vectorize/... paths.
        for suffix in (("upsert",), ("query",), ("delete_by_ids",), ("info",),
                       ("metadata_index", "list")):
            path = FC._index_path(config(), *suffix)
            self.assertTrue(path.startswith("/accounts/"), path)
            self.assertNotRegex(path, r"^/[0-9a-f]{32}/vectorize")

    def test_index_path_includes_accounts_and_v2(self) -> None:
        path = FC._index_path(config(), "info")
        self.assertTrue(path.startswith("/accounts/" + "a" * 32 + "/vectorize/v2/indexes/"))
        self.assertNotIn("://", path)

    def test_upsert_url_is_v2_and_has_accounts(self) -> None:
        sender = RecordingSender([(200, {"success": True, "result": {"mutationId": "m1"}})])
        vector = {"id": "x", "values": [0.0] * 1024, "namespace": "ns", "metadata": {}}
        FC.upsert_vectors(transport_with(sender), config(), [vector])
        self.assertIn("/accounts/" + "a" * 32 + "/vectorize/v2/indexes/frontend-craft-memory/upsert",
                      sender.calls[0]["url"])

    def test_info_and_metadata_list_hit_distinct_endpoints(self) -> None:
        sender = RecordingSender([
            (200, {"success": True, "result": {"dimensions": 1024}}),
            metadata_list(),
        ])
        FC.get_index_info(transport_with(sender), config())
        FC.list_metadata_indexes(transport_with(sender), config())
        self.assertTrue(sender.calls[0]["url"].endswith("/info"))
        self.assertTrue(sender.calls[1]["url"].endswith("/metadata_index/list"))

    def test_get_with_string_null_body_is_rejected(self) -> None:
        # A GET must send no body; transport must not send the literal "null".
        sender = RecordingSender([(200, {"success": True, "result": {}})])
        FC.get_index_info(transport_with(sender), config())
        self.assertIsNone(sender.calls[0]["body"])


class IdAndMetadataTests(unittest.TestCase):
    def test_remote_id_is_sha256_hex_and_opaque(self) -> None:
        rid = FC.remote_id(config(), "fc-help-cue")
        self.assertEqual(len(rid), 64)
        self.assertNotIn("lumen", rid)
        self.assertNotIn("help", rid)
        self.assertNotIn(":", rid)

    def test_remote_id_same_case_id_different_namespace_differs(self) -> None:
        a = FC.remote_id(config(namespace="ns-a"), "case-x")
        b = FC.remote_id(config(namespace="ns-b"), "case-x")
        self.assertNotEqual(a, b)

    def test_metadata_carries_scope_keys_and_revision(self) -> None:
        vector = next(iter(FC.desired_vectors(config(), [case()]).values()))
        self.assertIn("project_key", vector["metadata"])
        self.assertIn("surface_key", vector["metadata"])
        self.assertEqual(vector["metadata"]["revision"], vector["revision"])
        self.assertNotIn("hover-only", json.dumps(vector["metadata"]))

    def test_revision_covers_scope_model_and_text(self) -> None:
        base = case()
        self.assertNotEqual(FC.revision_of(base), FC.revision_of(case(scope={"project": "lumen-notes", "surface": "editor"})))
        self.assertNotEqual(FC.revision_of(base), FC.revision_of(case(statement="different body")))

    def test_ndjson_uses_native_namespace_field(self) -> None:
        vector = {"id": "x", "values": [0.0] * 1024, "namespace": "ns-1", "metadata": {"revision": "r"}}
        body = json.loads(FC.build_ndjson([vector]).decode("utf-8").strip())
        self.assertEqual(body["namespace"], "ns-1")
        self.assertEqual(body["id"], "x")
        self.assertNotIn("==", body["id"])


class ConfigTests(unittest.TestCase):
    def test_config_rejects_non_fixed_model_dimensions_metric(self) -> None:
        for bad in (
            config(model="@cf/other-model"),
            config(dimensions=768),
            config(metric="euclidean"),
        ):
            with self.assertRaises(FC.ConfigError):
                FC._validate_config(bad)

    def test_config_accepts_fixed_geometry(self) -> None:
        validated = FC._validate_config(config())
        self.assertEqual(validated["model"], "@cf/baai/bge-m3")
        self.assertEqual(validated["dimensions"], 1024)
        self.assertEqual(validated["metric"], "cosine")
        # scope_index_prefix must not survive from the old implementation.
        self.assertNotIn("scope_index_prefix", validated)


class EmbedTests(unittest.TestCase):
    def test_embed_sends_text_param_and_validates_dims(self) -> None:
        sender = RecordingSender([ok_embed(2)])
        rows = FC.embed_texts(transport_with(sender), ["a", "b"])
        self.assertEqual(len(rows), 2)
        sent = json.loads(sender.calls[0]["body"].decode("utf-8"))
        self.assertIn("text", sent)
        self.assertNotIn("contexts", sent)

    def test_embed_rejects_wrong_dimension_response(self) -> None:
        sender = RecordingSender([(200, {"success": True, "result": {"data": [[0.0] * 10]}})])
        with self.assertRaises(FC.CloudError):
            FC.embed_texts(transport_with(sender), ["a"])

    def test_token_sent_as_bearer_never_in_url(self) -> None:
        sender = RecordingSender([ok_embed(1)])
        FC.embed_texts(transport_with(sender), ["x"])
        call = sender.calls[0]
        self.assertEqual(call["headers"]["Authorization"], "Bearer test-token")
        self.assertNotIn("test-token", call["url"])


class QueryFilterTests(unittest.TestCase):
    def test_default_scope_filters_project_and_surface_including_global(self) -> None:
        cfg = config()
        projects, surfaces = FC.scope_filter_keys(cfg, "lumen-notes", "editor", transfer=False)
        self.assertEqual(
            sorted(projects),
            sorted([FC.project_key(cfg, "lumen-notes"), FC.project_key(cfg, "*")]),
        )
        self.assertEqual(
            sorted(surfaces),
            sorted([FC.surface_key(cfg, "editor"), FC.surface_key(cfg, "*")]),
        )

    def test_star_axis_selects_only_global(self) -> None:
        cfg = config()
        projects, surfaces = FC.scope_filter_keys(cfg, "*", "*", transfer=False)
        self.assertEqual(projects, [FC.project_key(cfg, "*")])
        self.assertEqual(surfaces, [FC.surface_key(cfg, "*")])

    def test_transfer_drops_project_keeps_surface(self) -> None:
        cfg = config()
        projects, surfaces = FC.scope_filter_keys(cfg, "lumen-notes", "editor", transfer=True)
        self.assertEqual(projects, [])
        self.assertEqual(
            sorted(surfaces),
            sorted([FC.surface_key(cfg, "editor"), FC.surface_key(cfg, "*")]),
        )

    def test_query_payload_has_namespace_filter_and_capped_topk(self) -> None:
        sender = RecordingSender([(200, {"success": True, "result": {"matches": []}})])
        FC.query_vectors(
            transport_with(sender), config(), [0.0] * 1024,
            [FC.project_key(config(), "lumen-notes")], [FC.surface_key(config(), "*")],
            top_k=500,
        )
        payload = json.loads(sender.calls[0]["body"].decode("utf-8"))
        self.assertEqual(payload["namespace"], config()["namespace"])
        self.assertEqual(payload["topK"], FC.MAX_TOPK)
        self.assertIn("project_key", payload["filter"])
        self.assertIn("surface_key", payload["filter"])

    def test_query_rejects_bad_vector_dimension(self) -> None:
        sender = RecordingSender([])
        with self.assertRaises(FC.CloudError):
            FC.query_vectors(transport_with(sender), config(), [0.0] * 10, [], [], 5)


class VectorizeTopKContractTests(unittest.TestCase):
    def test_metadata_query_obeys_platform_boundary(self) -> None:
        # https://developers.cloudflare.com/vectorize/platform/limits/
        # Metadata-returning queries cap at 50. Expectations must not depend on
        # FC.MAX_TOPK, or a wrong production constant would make the test pass.
        for requested, expected in [(3, 3), (50, 50), (51, 50), (100000, 50)]:
            with self.subTest(requested=requested):
                sender = RecordingSender([(200, {"success": True, "result": {"matches": []}})])
                FC.query_vectors(
                    transport_with(sender), config(), [0.0] * 1024,
                    [FC.project_key(config(), "lumen-notes")],
                    [FC.surface_key(config(), "*")], top_k=requested,
                )
                payload = json.loads(sender.calls[0]["body"].decode("utf-8"))
                self.assertEqual(payload["topK"], expected)
                self.assertEqual(payload["returnMetadata"], "all")
                self.assertFalse(payload["returnValues"])


class ResolveHitTests(unittest.TestCase):
    def _reverse(self, cfg, cases):
        return FC.reverse_id_map(cfg, cases)

    def test_unknown_remote_id_is_rejected_not_coerced(self) -> None:
        cfg = config()
        foreign = FC.digest("other\x1ffc-help-cue")  # same case id, different ns
        accepted, rejected = FC.resolve_hits(
            cfg, [{"id": foreign, "score": 0.9, "metadata": {"revision": "x"}}],
            {"fc-help-cue": case()}, self._reverse(cfg, [case()]),
            project="lumen-notes", surface="editor",
        )
        self.assertEqual(accepted, [])
        self.assertEqual(rejected[0]["reason"], "unknown_remote_id")

    def test_stale_status_and_scope_are_rejected(self) -> None:
        cfg = config()
        active = case()
        retired = case(id="fc-retired", status="retired")
        out_of_scope = case(id="fc-other", scope={"project": "other", "surface": "editor"})
        cases = [active, retired, out_of_scope]
        rev = {c["id"]: FC.revision_of(c) for c in cases}
        hits = [
            {"id": FC.remote_id(cfg, "fc-help-cue"), "score": 0.9, "metadata": {"revision": "deadbeef"}},
            {"id": FC.remote_id(cfg, "fc-retired"), "score": 0.8, "metadata": {"revision": rev["fc-retired"]}},
            {"id": FC.remote_id(cfg, "fc-other"), "score": 0.7, "metadata": {"revision": rev["fc-other"]}},
        ]
        accepted, rejected = FC.resolve_hits(
            cfg, hits, {c["id"]: c for c in cases}, self._reverse(cfg, cases),
            project="lumen-notes", surface="editor",
        )
        reasons = sorted(r["reason"] for r in rejected)
        self.assertEqual(accepted, [])
        self.assertEqual(reasons, ["out_of_scope", "stale_revision", "status:retired"])

    def test_transfer_accepts_other_project_and_labels_analogy(self) -> None:
        cfg = config()
        other = case(id="fc-orchard-mech", scope={"project": "orchard", "surface": "editor"})
        cases = {"fc-orchard-mech": other}
        hits = [{"id": FC.remote_id(cfg, "fc-orchard-mech"), "score": 0.7,
                 "metadata": {"revision": FC.revision_of(other)}}]
        accepted, _ = FC.resolve_hits(
            cfg, hits, cases, self._reverse(cfg, [other]),
            project="lumen-notes", surface="editor", transfer=True,
        )
        self.assertTrue(accepted[0]["analogy"])
        self.assertEqual(accepted[0]["current_scope"]["project"], "orchard")


class PlanAndStateTests(unittest.TestCase):
    def test_plan_uploads_active_skips_unchanged_and_deletes_removed(self) -> None:
        cfg = config()
        pointer = FC.remote_id(cfg, "fc-help-cue")
        manifest = {"version": FC.SYNC_STATE_VERSION, "target": FC.target_fingerprint(cfg),
                    "vectors": {pointer: {"revision": FC.revision_of(case())}},
                    "pending_mutations": []}
        plan = FC.plan_sync(cfg, [case(), case(id="r", status="retired")], manifest)
        self.assertEqual(plan["uploads"], [])
        self.assertEqual(plan["deletions"], [])
        plan2 = FC.plan_sync(cfg, [case(statement="changed")], manifest)
        self.assertEqual(len(plan2["uploads"]), 1)
        self.assertEqual(plan2["deletions"], [])  # same id, still present

        # A genuinely removed case plans a deletion of its old pointer.
        plan3 = FC.plan_sync(cfg, [case(id="unrelated-new")], manifest)
        self.assertEqual(plan3["deletions"], [pointer])

    def test_changed_scope_triggers_resync(self) -> None:
        cfg = config()
        moved = case(scope={"project": "lumen-notes", "surface": "editor"})
        manifest = {"version": FC.SYNC_STATE_VERSION, "target": FC.target_fingerprint(cfg),
                    "vectors": {FC.remote_id(cfg, "fc-help-cue"): {"revision": FC.revision_of(case())}},
                    "pending_mutations": []}
        plan = FC.plan_sync(cfg, [moved], manifest)
        self.assertEqual(len(plan["uploads"]), 1)

    def test_changed_target_is_refused(self) -> None:
        manifest = {"version": FC.SYNC_STATE_VERSION, "target": FC.target_fingerprint(config()),
                    "vectors": {"x": {"revision": "0"}}, "pending_mutations": []}
        with self.assertRaises(FC.ConfigError):
            FC.plan_sync(config(namespace="other-ns"), [case()], manifest)

    def test_manifest_symlink_is_refused(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        target = root / "real.json"
        target.write_text("{}")
        (root / FC.SYNC_STATE_NAME).symlink_to(target)
        with self.assertRaises(FC.ConfigError):
            FC.load_manifest(root)


class SyncApplyTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="fc-sync-")
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def _apply(self, responses, cases, *, wait=False):
        sender = RecordingSender(responses)
        plan = FC.plan_sync(config(), cases, FC.load_manifest(self.root))
        result = FC.apply_sync(transport_with(sender), config(), self.root, plan, wait=wait)
        return result, sender

    def test_requires_metadata_indexes_before_embed(self) -> None:
        # Missing surface_key -> refuse before any embed/upsert.
        sender = RecordingSender([metadata_list(names=(("project_key", "String"),))])
        plan = FC.plan_sync(config(), [case()], FC.load_manifest(self.root))
        with self.assertRaises(FC.CloudError):
            FC.apply_sync(transport_with(sender), config(), self.root, plan, wait=False)
        self.assertEqual(len(sender.calls), 1)

    def test_capital_string_index_type_is_accepted(self) -> None:
        # Regression: live API returns indexType 'String'; namespace is NOT needed.
        sender = RecordingSender([metadata_list()])
        FC.require_metadata_ready(transport_with(sender), config())  # must not raise

    def test_apply_embeds_upserts_and_persists_receipt(self) -> None:
        result, _ = self._apply(
            [metadata_list(), ok_embed(1), (200, {"success": True, "result": {"mutationId": "m1"}})],
            [case()],
        )
        self.assertTrue(result["applied"])
        self.assertEqual(result["mutation_state"], "pending")
        saved = FC.load_manifest(self.root)
        receipt = saved["pending_mutations"][0]
        self.assertEqual(receipt["mutation_ids"], ["m1"])
        self.assertEqual(list(receipt["expected"]), [FC.remote_id(config(), "fc-help-cue")])

    def test_pending_receipt_survives_error(self) -> None:
        self._apply(
            [metadata_list(), ok_embed(1), (200, {"success": True, "result": {"mutationId": "m1"}})],
            [case()],
        )
        # A newer revision of the same id (not a deletion) re-plans an upload;
        # the failed upsert must keep the id pending.
        plan = FC.plan_sync(config(), [case(statement="changed")], FC.load_manifest(self.root))
        sender = RecordingSender([metadata_list(), ok_embed(1), (500, {"success": False, "errors": [{"message": "no"}]})])
        with self.assertRaises(FC.CloudError):
            FC.apply_sync(transport_with(sender), config(), self.root, plan, wait=False)
        self.assertEqual(len(FC.load_manifest(self.root)["pending_mutations"]), 1)

    def test_verify_clears_when_readback_matches_and_deletion_absent(self) -> None:
        result, _ = self._apply(
            [metadata_list(), ok_embed(1), (200, {"success": True, "result": {"mutationId": "m1"}})],
            [case()],
        )
        rid = FC.remote_id(config(), "fc-help-cue")
        # get_by_ids returns the vector with our namespace + current revision
        # + the expected scope keys.
        scope = case()["scope"]
        vsender = RecordingSender([(200, {"success": True, "result": [
            {"id": rid, "namespace": config()["namespace"],
             "metadata": {
                 "revision": FC.revision_of(case()),
                 "project_key": FC.project_key(config(), scope["project"]),
                 "surface_key": FC.surface_key(config(), scope["surface"]),
             }}]})])
        status = FC.verify_pending(transport_with(vsender), config(), self.root)
        self.assertEqual(status["status"], "ready")
        self.assertEqual(status["verified_uploads"], [rid])
        self.assertEqual(FC.load_manifest(self.root)["pending_mutations"], [])

    def test_verify_pending_deletion_absent_clears_it(self) -> None:
        self._apply(
            [metadata_list(), ok_embed(1), (200, {"success": True, "result": {"mutationId": "m1"}})],
            [case()],
        )
        plan = FC.plan_sync(config(), [], FC.load_manifest(self.root))
        sender = RecordingSender([metadata_list(), (200, {"success": True, "result": {"mutationId": "m2"}})])
        FC.apply_sync(transport_with(sender), config(), self.root, plan, wait=False)
        saved = FC.load_manifest(self.root)
        self.assertEqual(len(saved["pending_deletions"]), 1)
        # get_by_ids returns nothing -> deletion verified.
        vsender = RecordingSender([(200, {"success": True, "result": []})])
        status = FC.verify_pending(transport_with(vsender), config(), self.root)
        self.assertEqual(status["verified_deletions"], saved["pending_deletions"])
        self.assertEqual(FC.load_manifest(self.root)["pending_deletions"], [])

    def test_verify_other_namespace_mutation_pointer_does_not_clear(self) -> None:
        # The index is shared; another namespace advances processedUpToMutation
        # past ours, but our vector is NOT read back -> stays pending.
        self._apply(
            [metadata_list(), ok_embed(1), (200, {"success": True, "result": {"mutationId": "m1"}})],
            [case()],
        )
        vsender = RecordingSender([(200, {"success": True, "result": []})])
        status = FC.verify_pending(transport_with(vsender), config(), self.root)
        self.assertEqual(status["status"], "pending")
        self.assertEqual(status["unverified"][0]["reason"], "not_read_back")
        self.assertEqual(len(FC.load_manifest(self.root)["pending_mutations"]), 1)

    def test_verify_wrong_namespace_or_revision_does_not_clear(self) -> None:
        self._apply(
            [metadata_list(), ok_embed(1), (200, {"success": True, "result": {"mutationId": "m1"}})],
            [case()],
        )
        rid = FC.remote_id(config(), "fc-help-cue")
        for vector, reason in (
            ({"id": rid, "namespace": "other-ns", "metadata": {"revision": FC.revision_of(case())}}, "wrong_namespace"),
            ({"id": rid, "namespace": config()["namespace"], "metadata": {"revision": "0" * 64}}, "wrong_revision"),
        ):
            vsender = RecordingSender([(200, {"success": True, "result": [vector]})])
            status = FC.verify_pending(transport_with(vsender), config(), self.root)
            self.assertEqual(status["status"], "pending", reason)
            self.assertEqual(status["unverified"][0]["reason"], reason)

    def test_verify_delete_still_present_does_not_clear(self) -> None:
        self._apply(
            [metadata_list(), ok_embed(1), (200, {"success": True, "result": {"mutationId": "m1"}})],
            [case()],
        )
        plan = FC.plan_sync(config(), [], FC.load_manifest(self.root))
        sender = RecordingSender([metadata_list(), (200, {"success": True, "result": {"mutationId": "m2"}})])
        FC.apply_sync(transport_with(sender), config(), self.root, plan, wait=False)
        rid = FC.remote_id(config(), "fc-help-cue")
        # Readback still returns the deleted vector -> not cleared.
        vsender = RecordingSender([(200, {"success": True, "result": [{"id": rid, "namespace": config()["namespace"]}]})])
        status = FC.verify_pending(transport_with(vsender), config(), self.root)
        self.assertIn(
            {"id": rid, "reason": "delete_still_present"}, status["unverified"]
        )

    def test_success_without_mutation_id_is_not_ready(self) -> None:
        result, _ = self._apply(
            [metadata_list(), ok_embed(1), (200, {"success": True, "result": {}})],
            [case()],
        )
        # No mutationId: receipt has no ids; must not be claimed ready by the
        # pointer alone (readback is still required, so state is pending).
        self.assertEqual(result["mutation_state"], "pending")

    def test_rerun_no_changes_does_not_reembed(self) -> None:
        self._apply(
            [metadata_list(), ok_embed(1), (200, {"success": True, "result": {"mutationId": "m1"}})],
            [case()],
        )
        plan = FC.plan_sync(config(), [case()], FC.load_manifest(self.root))
        self.assertEqual(plan["uploads"], [])
        self.assertEqual(plan["deletions"], [])
        # A rerun would touch only metadata readiness; no embed budget is spent.
        self.assertEqual(len(FC.load_manifest(self.root)["pending_mutations"]), 1)

    def test_verify_refuses_different_target(self) -> None:
        self._apply(
            [metadata_list(), ok_embed(1), (200, {"success": True, "result": {"mutationId": "m1"}})],
            [case()],
        )
        vsender = RecordingSender([])
        with self.assertRaises(FC.ConfigError):
            FC.verify_pending(transport_with(vsender), config(namespace="other-ns"), self.root)

    def _readback(self, *vectors):
        return (200, {"success": True, "result": list(vectors)})

    def _upload_response(self, c, rid=None):
        rid = rid or FC.remote_id(config(), c["id"])
        return {"id": rid, "namespace": config()["namespace"], "metadata": {
            "revision": FC.revision_of(c),
            "project_key": FC.project_key(config(), c["scope"]["project"]),
            "surface_key": FC.surface_key(config(), c["scope"]["surface"]),
        }}

    def test_wait_uses_readback_not_pointer(self) -> None:
        # The shared pointer is irrelevant; only the readback proves ours.
        responses = [
            metadata_list(),
            ok_embed(1),
            (200, {"success": True, "result": {"mutationId": "m1"}}),
            self._readback(self._upload_response(case())),
        ]
        result, _ = self._apply(responses, [case()], wait=True)
        self.assertEqual(result["mutation_state"], "ready")
        self.assertEqual(FC.load_manifest(self.root)["pending_mutations"], [])

    def test_wait_clears_pending_deletions(self) -> None:
        # Upload then delete; the deletion supersedes the upload receipt, and
        # --wait clears pending_deletions once the id is absent on readback.
        self._apply(
            [metadata_list(), ok_embed(1), (200, {"success": True, "result": {"mutationId": "m1"}})],
            [case()],
        )
        self.assertEqual(len(FC.load_manifest(self.root)["pending_mutations"]), 1)
        responses = [
            metadata_list(),
            (200, {"success": True, "result": {"mutationId": "m2"}}),
            self._readback(),  # nothing present -> deletion verified
        ]
        sender = RecordingSender(responses)
        plan = FC.plan_sync(config(), [], FC.load_manifest(self.root))
        result = FC.apply_sync(transport_with(sender), config(), self.root, plan,
                               wait=True, attempts=2, interval=0, sleeper=lambda _: None)
        self.assertEqual(result["mutation_state"], "ready")
        saved = FC.load_manifest(self.root)
        self.assertEqual(saved["pending_deletions"], [])
        self.assertEqual(saved["pending_mutations"], [])

    def test_wait_timeout_keeps_receipt(self) -> None:
        responses = [
            metadata_list(),
            ok_embed(1),
            (200, {"success": True, "result": {"mutationId": "m1"}}),
            self._readback(),  # not read back -> still pending
            self._readback(),
        ]
        sender = RecordingSender(responses)
        plan = FC.plan_sync(config(), [case()], FC.load_manifest(self.root))
        with self.assertRaises(FC.PendingError):
            FC.apply_sync(transport_with(sender), config(), self.root, plan,
                          wait=True, attempts=2, interval=0, sleeper=lambda _: None)
        self.assertEqual(len(FC.load_manifest(self.root)["pending_mutations"]), 1)

    def test_reconcile_accepted_revision_delete_and_readd(self) -> None:
        accepted = (200, {"success": True, "result": {"mutationId": "m"}})
        self._apply([metadata_list(), ok_embed(1), accepted], [case()])
        changed = case(statement="changed")
        self._apply([metadata_list(), ok_embed(1), accepted], [changed])
        saved = FC.load_manifest(self.root)
        rid = FC.remote_id(config(), changed["id"])
        self.assertEqual(saved["pending_mutations"][0]["expected"][rid]["revision"], FC.revision_of(changed))
        self._apply([metadata_list(), accepted], [])
        saved = FC.load_manifest(self.root)
        self.assertEqual(saved["pending_mutations"], [])
        self.assertEqual(saved["pending_deletions"], [rid])
        self._apply([metadata_list(), ok_embed(1), accepted], [changed])
        saved = FC.load_manifest(self.root)
        self.assertEqual(saved["pending_deletions"], [])
        self.assertIn(rid, saved["pending_mutations"][0]["expected"])

    def test_failed_revision_and_delete_stay_in_retry_plan(self) -> None:
        accepted = (200, {"success": True, "result": {"mutationId": "m"}})
        failed = (500, {"success": False})
        self._apply([metadata_list(), ok_embed(1), accepted], [case()])
        before = FC.load_manifest(self.root)
        changed = case(statement="changed")
        with self.assertRaises(FC.CloudError):
            self._apply([metadata_list(), ok_embed(1), failed], [changed])
        self.assertEqual(FC.load_manifest(self.root), before)
        plan = FC.plan_sync(config(), [changed], FC.load_manifest(self.root))
        self.assertEqual(len(plan["uploads"]), 1)
        with self.assertRaises(FC.CloudError):
            self._apply([metadata_list(), failed], [])
        self.assertEqual(FC.load_manifest(self.root), before)
        self.assertEqual(len(FC.plan_sync(config(), [], before)["deletions"]), 1)

    def test_partial_batch_failure_retries_only_unaccepted_vectors(self) -> None:
        records = [case(id="case-" + str(i)) for i in range(65)]
        responses = [metadata_list(), ok_embed(64), ok_embed(1),
                     (200, {"success": True, "result": {"mutationId": "m1"}}),
                     (500, {"success": False})]
        with self.assertRaises(FC.CloudError):
            self._apply(responses, records)
        saved = FC.load_manifest(self.root)
        self.assertEqual(len(saved["vectors"]), 64)
        plan = FC.plan_sync(config(), records, saved)
        self.assertEqual([v["case_id"] for v in plan["uploads"]], ["case-64"])
        accepted = (200, {"success": True, "result": {"mutationId": "m2"}})
        self._apply([metadata_list(), ok_embed(1), accepted], records)
        self.assertEqual(len(FC.load_manifest(self.root)["vectors"]), 65)
        self.assertEqual(FC.plan_sync(config(), records, FC.load_manifest(self.root))["uploads"], [])

    def test_get_by_ids_wrong_shape_is_explicit_error(self) -> None:
        self._apply(
            [metadata_list(), ok_embed(1), (200, {"success": True, "result": {"mutationId": "m1"}})],
            [case()],
        )
        vsender = RecordingSender([(200, {"success": True, "result": {"not": "a list"}})])
        with self.assertRaises(FC.CloudError):
            FC.verify_pending(transport_with(vsender), config(), self.root)
        # Pending state is untouched (no false "all absent").
        self.assertEqual(len(FC.load_manifest(self.root)["pending_mutations"]), 1)

    def test_manifest_tmp_symlink_is_refused(self) -> None:
        tmp = self.root / (FC.SYNC_STATE_NAME + ".tmp")
        target = self.root / "elsewhere.json"
        target.write_text("{}")
        tmp.symlink_to(target)
        with self.assertRaises(FC.ConfigError):
            FC.save_manifest_atomic(self.root, {"version": FC.SYNC_STATE_VERSION})


class AuthAndSecretTests(unittest.TestCase):
    def test_env_token_required(self) -> None:
        prev = os.environ.pop("CLOUDFLARE_API_TOKEN", None)
        try:
            with self.assertRaises(FC.CloudError):
                FC.resolve_token(config(auth="env"))
        finally:
            if prev is not None:
                os.environ["CLOUDFLARE_API_TOKEN"] = prev

    def test_wrangler_json_parsed(self) -> None:
        class Proc:
            returncode = 0
            stdout = json.dumps({"type": "token", "token": "secret-token-value"})
            stderr = ""
        self.assertEqual(FC.resolve_token(config(auth="wrangler"), runner=lambda: Proc()),
                         "secret-token-value")

    def test_error_never_echoes_provider_message_or_token(self) -> None:
        sender = RecordingSender([(403, {"success": False, "errors": [
            {"code": 10000, "message": "token secret-token-value is invalid"}]})])
        with self.assertRaises(FC.CloudError) as ctx:
            FC.embed_texts(transport_with(sender), ["x"])
        message = str(ctx.exception)
        self.assertNotIn("secret-token-value", message)
        self.assertNotIn("is invalid", message)
        self.assertIn("403", message)


class CliSemanticTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="fc-cloud-cli-")
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        (self.root / "context.md").write_text("# Context\n\n- Dense tables.\n", encoding="utf-8")
        (self.root / "cases.json").write_text(
            json.dumps({"version": 1, "cases": [case()]}), encoding="utf-8")
        (self.root / "cloudflare.json").write_text(json.dumps(config()), encoding="utf-8")
        self._orig = MEM.fccloud.Transport
        self._env = os.environ.get("CLOUDFLARE_API_TOKEN")
        os.environ["CLOUDFLARE_API_TOKEN"] = "test-token"

    def tearDown(self) -> None:
        MEM.fccloud.Transport = self._orig
        if self._env is None:
            os.environ.pop("CLOUDFLARE_API_TOKEN", None)
        else:
            os.environ["CLOUDFLARE_API_TOKEN"] = self._env

    def _patch(self, responses):
        sender = RecordingSender(responses)
        original = MEM.fccloud.Transport
        MEM.fccloud.Transport = lambda account_id, token, _s=None: original(
            account_id, token, sender=sender)
        return sender

    def _run(self, *args):
        import contextlib
        import io
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            try:
                code = MEM.main(list(args))
            except SystemExit as exc:
                code = int(exc.code or 0)
        out = stream.getvalue().strip()
        return code, (json.loads(out) if out else {})

    def _hit_rows(self):
        ns = config()
        accepted = case()
        return [{"id": FC.remote_id(ns, "fc-help-cue"), "score": 0.87,
                 "metadata": {"revision": FC.revision_of(accepted)}}]

    def test_natural_query_returns_resolved_candidate(self) -> None:
        self._patch([ok_embed(1), (200, {"success": True, "result": {"matches": self._hit_rows()}})])
        code, payload = self._run(
            "query", "--root", str(self.root), "--project", "lumen-notes",
            "--surface", "editor", "--query", "the help text keeps disappearing")
        self.assertEqual(code, MEM.EXIT_OK, payload)
        self.assertEqual(payload["mode"], "semantic")
        self.assertEqual(payload["cases"][0]["case"]["id"], "fc-help-cue")
        self.assertIn("Dense tables.", payload["context"]["text"])
        self.assertEqual(payload["namespace"], config()["namespace"])
        self.assertTrue(all("lumen" not in k for k in payload["project_keys"]))

    def test_cli_query_limit_reaches_capped_metadata_request(self) -> None:
        # Literal Vectorize metadata cap (independent of FC.MAX_TOPK).
        metadata_limit = 50
        sender = self._patch([
            ok_embed(1),
            (200, {"success": True, "result": {"matches": self._hit_rows()}}),
        ])
        code, payload = self._run(
            "query", "--root", str(self.root), "--project", "lumen-notes",
            "--surface", "editor", "--query", "help", "--limit", "500")
        self.assertEqual(code, MEM.EXIT_OK, payload)
        self.assertEqual(payload["mode"], "semantic")
        request = json.loads(sender.calls[1]["body"].decode("utf-8"))
        self.assertEqual(request["topK"], metadata_limit)
        self.assertEqual(request["returnMetadata"], "all")
        # Metadata-dependent local validation still runs and keeps the candidate.
        self.assertEqual(payload["cases"][0]["case"]["id"], "fc-help-cue")

    def test_cli_query_limit_at_metadata_boundary_is_unchanged(self) -> None:
        sender = self._patch([
            ok_embed(1),
            (200, {"success": True, "result": {"matches": self._hit_rows()}}),
        ])
        code, payload = self._run(
            "query", "--root", str(self.root), "--project", "lumen-notes",
            "--surface", "editor", "--query", "help", "--limit", "50")
        self.assertEqual(code, MEM.EXIT_OK, payload)
        request = json.loads(sender.calls[1]["body"].decode("utf-8"))
        self.assertEqual(request["topK"], 50)

    def test_stale_hit_reported_not_returned(self) -> None:
        rows = [{"id": FC.remote_id(config(), "fc-help-cue"), "score": 0.9,
                 "metadata": {"revision": "0" * 64}}]
        self._patch([ok_embed(1), (200, {"success": True, "result": {"matches": rows}})])
        code, payload = self._run(
            "query", "--root", str(self.root), "--project", "lumen-notes",
            "--surface", "editor", "--query", "help")
        self.assertEqual(payload["status"], "no_match")
        self.assertEqual(payload["rejected"][0]["reason"], "stale_revision")

    def test_remote_error_is_not_a_lexical_fallback(self) -> None:
        self._patch([(500, {"success": False, "errors": [{"message": "down"}]})])
        code, payload = self._run(
            "query", "--root", str(self.root), "--project", "lumen-notes",
            "--surface", "editor", "--query", "help")
        self.assertEqual(code, MEM.EXIT_REMOTE)
        self.assertEqual(payload["status"], "remote_error")
        self.assertNotIn("cases", payload)

    def test_plain_term_stays_offline_lexical(self) -> None:
        code, payload = self._run(
            "query", "--root", str(self.root), "--project", "lumen-notes",
            "--surface", "editor", "--term", "help")
        self.assertEqual(code, MEM.EXIT_OK)
        self.assertEqual(payload["mode"], "lexical")


class CliTransferTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="fc-transfer-")
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        (self.root / "context.md").write_text("# Context\n", encoding="utf-8")
        (self.root / "cases.json").write_text(json.dumps({
            "version": 1,
            "cases": [case(id="fc-mech", keywords=["grouping"],
                           scope={"project": "atria", "surface": "editor"},
                           statement="Co-locating the selected object's action removed mode confusion.")],
        }), encoding="utf-8")

    def _run(self, *args):
        import contextlib
        import io
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            try:
                code = MEM.main(list(args))
            except SystemExit as exc:
                code = int(exc.code or 0)
        out = stream.getvalue().strip()
        return code, (json.loads(out) if out else {})

    def test_default_hides_other_projects(self) -> None:
        _, payload = self._run("query", "--root", str(self.root), "--project", "lumen-notes",
                               "--surface", "editor", "--term", "grouping")
        self.assertEqual(payload["status"], "no_match")

    def test_transfer_surfaces_cross_project_analogy(self) -> None:
        _, payload = self._run("query", "--root", str(self.root), "--project", "lumen-notes",
                               "--surface", "editor", "--term", "grouping", "--transfer")
        self.assertEqual(payload["status"], "matched")
        self.assertTrue(payload["cases"][0]["analogy"])
        self.assertEqual(payload["cases"][0]["current_scope"]["project"], "atria")

    def test_transfer_still_respects_surface(self) -> None:
        _, payload = self._run("query", "--root", str(self.root), "--project", "lumen-notes",
                               "--surface", "dashboard", "--term", "grouping", "--transfer")
        self.assertEqual(payload["status"], "no_match")


class InitDoctorTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="fc-init-")
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "store"

    def _run(self, *args):
        import contextlib
        import io
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            try:
                code = MEM.main(list(args))
            except SystemExit as exc:
                code = int(exc.code or 0)
        out = stream.getvalue().strip()
        return code, (json.loads(out) if out else {})

    def test_init_requires_mkdir_for_new_root(self) -> None:
        code, payload = self._run("init", "--root", str(self.root))
        self.assertEqual(code, MEM.EXIT_MISSING)

    def test_init_template_has_aims_and_boundaries(self) -> None:
        code, payload = self._run("init", "--root", str(self.root), "--mkdir",
                                  "--project", "lumen-notes", "--surface", "editor")
        self.assertEqual(code, MEM.EXIT_OK)
        text = (self.root / "context.md").read_text(encoding="utf-8")
        self.assertIn("## Current aims", text)
        self.assertIn("## Current boundaries", text)

    def test_doctor_missing_context_is_not_ok(self) -> None:
        (self.root).mkdir(parents=True)
        (self.root / "cloudflare.json").write_text(json.dumps(config()), encoding="utf-8")
        (self.root / "cases.json").write_text(json.dumps({"version": 1, "cases": []}), encoding="utf-8")
        # No context.md, and auth will fail; assert the context check itself.
        code, payload = self._run("doctor", "--root", str(self.root))
        context_check = next(c for c in payload["checks"] if c["name"] == "context")
        self.assertFalse(context_check["ok"])


class DoctorRemoteTests(unittest.TestCase):
    """doctor must read the remote metric from the index config, not just local
    config + /info dimensions, and must use case-insensitive metadata types."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="fc-doctor-")
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        (self.root / "context.md").write_text("# Context\n", encoding="utf-8")
        (self.root / "cases.json").write_text(json.dumps({"version": 1, "cases": []}), encoding="utf-8")
        (self.root / "cloudflare.json").write_text(json.dumps(config()), encoding="utf-8")
        self._orig = MEM.fccloud.Transport
        self._env = os.environ.get("CLOUDFLARE_API_TOKEN")
        os.environ["CLOUDFLARE_API_TOKEN"] = "test-token"

    def tearDown(self) -> None:
        MEM.fccloud.Transport = self._orig
        if self._env is None:
            os.environ.pop("CLOUDFLARE_API_TOKEN", None)
        else:
            os.environ["CLOUDFLARE_API_TOKEN"] = self._env

    def _patch(self, responses):
        sender = RecordingSender(responses)
        original = MEM.fccloud.Transport
        MEM.fccloud.Transport = lambda account_id, token, _s=None: original(
            account_id, token, sender=sender)
        return sender

    def _run(self, *args):
        import contextlib
        import io
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            try:
                code = MEM.main(list(args))
            except SystemExit as exc:
                code = int(exc.code or 0)
        out = stream.getvalue().strip()
        return code, (json.loads(out) if out else {})

    def _responses(self, metric="cosine", index_type="String"):
        # Real shape: GET /indexes/{index} -> result.config = {dimensions, metric}.
        return [
            (200, {"success": True, "result": {"dimensions": 1024, "vectorCount": 0,
                                               "processedUpToMutation": "m1"}}),
            (200, {"success": True, "result": {
                "created_on": "2026-09-01T00:00:00Z",
                "modified_on": "2026-09-01T00:00:00Z",
                "name": "frontend-craft-memory",
                "description": "",
                "config": {"dimensions": 1024, "metric": metric},
            }}),
            metadata_list(names=(("project_key", index_type), ("surface_key", index_type))),
        ]

    def test_doctor_accepts_capital_string_and_cosine(self) -> None:
        self._patch(self._responses())
        code, payload = self._run("doctor", "--root", str(self.root))
        self.assertEqual(code, MEM.EXIT_OK, payload)
        idx = next(c for c in payload["checks"] if c["name"] == "metadata_indexes")
        self.assertTrue(idx["ok"])

    def test_doctor_fails_on_wrong_remote_metric(self) -> None:
        self._patch(self._responses(metric="euclidean"))
        code, payload = self._run("doctor", "--root", str(self.root))
        self.assertEqual(code, MEM.EXIT_REMOTE)
        self.assertTrue(any("metric" in e for e in payload["errors"]))


class SyncCliGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="fc-synccli-")
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        (self.root / "context.md").write_text("# Context\n", encoding="utf-8")
        (self.root / "cases.json").write_text(json.dumps({"version": 1, "cases": [case()]}), encoding="utf-8")
        (self.root / "cloudflare.json").write_text(json.dumps(config()), encoding="utf-8")
        self._orig = MEM.fccloud.Transport
        self._env = os.environ.get("CLOUDFLARE_API_TOKEN")
        os.environ["CLOUDFLARE_API_TOKEN"] = "test-token"

    def tearDown(self) -> None:
        MEM.fccloud.Transport = self._orig
        if self._env is None:
            os.environ.pop("CLOUDFLARE_API_TOKEN", None)
        else:
            os.environ["CLOUDFLARE_API_TOKEN"] = self._env

    def _run(self, *args):
        import contextlib
        import io
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            try:
                code = MEM.main(list(args))
            except SystemExit as exc:
                code = int(exc.code or 0)
        out = stream.getvalue().strip()
        return code, (json.loads(out) if out else {})

    def test_wait_without_apply_is_a_usage_error(self) -> None:
        code, payload = self._run("sync", "--root", str(self.root), "--wait")
        self.assertEqual(code, MEM.EXIT_USAGE)
        self.assertEqual(payload.get("status"), "usage_error")

    def test_verify_pending_returns_exit_7(self) -> None:
        # Seed a manifest with a pending upload receipt.
        rid = FC.remote_id(config(), "fc-help-cue")
        manifest = {
            "version": FC.SYNC_STATE_VERSION,
            "target": FC.target_fingerprint(config()),
            "vectors": {},
            "pending_mutations": [
                {"mutation_ids": ["m1"], "expected": {rid: {"revision": FC.revision_of(case())}}}
            ],
            "pending_deletions": [],
        }
        (self.root / FC.SYNC_STATE_NAME).write_text(json.dumps(manifest), encoding="utf-8")
        # Readback returns nothing -> still pending -> exit 7.
        original = MEM.fccloud.Transport

        def patch(responses):
            sender = RecordingSender(responses)
            MEM.fccloud.Transport = lambda account_id, token, _s=None: original(
                account_id, token, sender=sender)

        patch([(200, {"success": True, "result": []})])
        code, payload = self._run("sync", "--root", str(self.root), "--verify")
        self.assertEqual(code, MEM.EXIT_PENDING)
        self.assertEqual(payload["status"], "pending")

if __name__ == "__main__":
    unittest.main()
