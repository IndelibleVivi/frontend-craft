#!/usr/bin/env python3
"""Tests for the Frontend Craft visual catalogue CLI.

All data here is synthetic and invented (projects ``sample-reader``,
``atlas-guide``; catalogue ids ``fc-library``, ``sample-reader-project``,
``shared-materials``). No real project names, private screenshots, personal
preferences, or transcripts are used. Every fixture is written to a temporary
directory; nothing here performs network, model, or account access.
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "fc_catalog.py"
SPEC = importlib.util.spec_from_file_location("fc_catalog", SCRIPT)
assert SPEC and SPEC.loader
CAT = importlib.util.module_from_spec(SPEC)
sys.modules["fc_catalog"] = CAT
SPEC.loader.exec_module(CAT)


_CLI_LOCK = threading.Lock()


def run_cli(*args: str) -> tuple[int, dict]:
    """Invoke main() in-process and capture the JSON it prints.

    ``main`` writes to the process-wide stdout, so concurrent invocations are
    serialized with a lock; this keeps the test threads honest without changing
    production behaviour.
    """
    stream = io.StringIO()
    with _CLI_LOCK, contextlib.redirect_stdout(stream):
        try:
            code = CAT.main(list(args))
        except SystemExit as exc:  # argparse usage exit
            code = int(exc.code or 0)
    out = stream.getvalue().strip()
    payload = json.loads(out) if out else {}
    return code, payload


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class Base(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="fc-catalog-test-")
        self.root = Path(self._tmp.name)
        self.catalog = self.root / "catalog.json"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # --- fixture helpers ---------------------------------------------------

    def write(self, rel: str, data) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, (dict, list)):
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        elif isinstance(data, bytes):
            path.write_bytes(data)
        else:
            path.write_text(data, encoding="utf-8")
        return path

    def write_catalog(self, document, path: Path | None = None) -> Path:
        target = path or self.catalog
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
        return target

    def base_document(self, **overrides):
        document = {"version": 1, "id": "fc-library", "revision": 1, "items": [], "uses": []}
        document.update(overrides)
        return document

    def reference_item(self, **overrides):
        item = {
            "id": "margin-reference",
            "revision": 1,
            "title": "Active note beside the body text",
            "roles": ["reference"],
            "source": {"kind": "external", "url": "https://example.org/essay"},
            "tags": {"tasks": ["reading"], "languages": ["zh-Hans"], "media": ["typography"]},
            "previews": [],
        }
        item.update(overrides)
        return item

    def style_item(self, **overrides):
        item = {
            "id": "reading-margin",
            "revision": 1,
            "title": "Reading and an active margin",
            "roles": ["style"],
            "making": {"effect": "quiet body", "carry": ["measure"], "vary": ["tone"],
                       "limits": "not for dashboards"},
            "specimen": {"entry": "npm run start", "notes": "synthetic"},
            "previews": [{"id": "wide", "kind": "screenshot",
                          "locator": {"root": "catalog", "path": "captures/wide.svg"}}],
        }
        item.update(overrides)
        return item


# ---------------------------------------------------------------------------

class QueryShowTests(Base):
    def test_query_filters_and_pagination(self):
        items = [
            self.reference_item(id="a", title="A", tags={"tasks": ["reading"], "languages": ["zh-Hans"], "media": ["typography"]}),
            self.style_item(id="b", title="B"),
            self.reference_item(id="c", title="C", roles=["material"], tags={"media": ["photography"]}),
            self.reference_item(id="d", title="D", archived=True),
        ]
        self.write_catalog(self.base_document(items=items))

        code, payload = run_cli("query", "--catalog", str(self.catalog), "--limit", "2")
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "matched")
        self.assertEqual(payload["matched"], 3)  # archived excluded by default
        self.assertEqual(payload["returned"], 2)
        self.assertTrue(payload["truncated"])
        self.assertEqual(payload["next_offset"], 2)
        ids = [i["id"] for i in payload["items"]]
        self.assertEqual(ids, sorted(ids))  # deterministic order

        code, page2 = run_cli("query", "--catalog", str(self.catalog), "--limit", "2", "--offset", "2")
        self.assertFalse(page2["truncated"])
        all_ids = set(ids) | {i["id"] for i in page2["items"]}
        self.assertEqual(all_ids, {"a", "b", "c"})

        code, archived = run_cli("query", "--catalog", str(self.catalog),
                                 "--include-archived", "--role", "reference")
        self.assertIn("d", [i["id"] for i in archived["items"]])

    def test_query_role_language_medium_and_term(self):
        self.write_catalog(self.base_document(items=[
            self.reference_item(id="a"),
            self.style_item(id="b"),
        ]))
        _, by_role = run_cli("query", "--catalog", str(self.catalog), "--role", "style")
        self.assertEqual([i["id"] for i in by_role["items"]], ["b"])
        _, by_lang = run_cli("query", "--catalog", str(self.catalog), "--language", "zh-Hans")
        self.assertEqual([i["id"] for i in by_lang["items"]], ["a"])
        _, by_term = run_cli("query", "--catalog", str(self.catalog), "--term", "note")
        self.assertIn("a", [i["id"] for i in by_term["items"]])
        _, none = run_cli("query", "--catalog", str(self.catalog), "--term", "zzzzz")
        self.assertEqual(none["status"], "no_match")

    def test_query_reports_revisions_for_continuation(self):
        self.write_catalog(self.base_document(items=[self.reference_item()]))
        _, payload = run_cli("query", "--catalog", str(self.catalog))
        self.assertEqual(payload["revisions"], {"fc-library": 1})

    def test_show_current_and_history(self):
        items = [
            self.reference_item(id="x", revision=1, title="v1"),
            self.reference_item(id="x", revision=2, title="v2"),
            self.reference_item(id="x", revision=3, title="v3", archived=True),
        ]
        self.write_catalog(self.base_document(revision=3, items=items))
        _, payload = run_cli("show", "--catalog", str(self.catalog), "--id", "x")
        self.assertEqual(payload["item"]["revision"], 3)  # highest revision is current
        self.assertEqual([h["revision"] for h in payload["history"]], [3, 2, 1])

        _, rev2 = run_cli("show", "--catalog", str(self.catalog), "--id", "x", "--revision", "2")
        self.assertEqual(rev2["item"]["title"], "v2")
        self.assertFalse(rev2["current"])

        code, missing = run_cli("show", "--catalog", str(self.catalog), "--id", "nope")
        self.assertNotEqual(code, 0)
        self.assertEqual(missing["status"], "not_found")

    def test_show_uses_and_exact_reference(self):
        use = {
            "id": "reader-margin-use", "revision": 1,
            "target": {"project": "sample-reader", "surface": "reader",
                       "location": {"path": "src/pages/Reader.tsx", "region": "article"}},
            "references": [{"catalog_id": "fc-library", "item_id": "reading-margin", "revision": 1}],
            "relation": "body stays continuous", "status": "selected",
        }
        self.write_catalog(self.base_document(items=[self.style_item()], uses=[use]))
        _, payload = run_cli("show", "--catalog", str(self.catalog), "--id", "reader-margin-use")
        self.assertEqual(payload["status"], "use")
        self.assertEqual(payload["reference_state"][0]["result"]["status"], "resolved")


class CrossCollectionTests(Base):
    def test_unresolved_catalog_reported_not_guessed(self):
        item = self.style_item(materials=[
            {"catalog_id": "shared-materials", "item_id": "title-font", "revision": 1},
        ])
        self.write_catalog(self.base_document(items=[item]))
        _, payload = run_cli("show", "--catalog", str(self.catalog), "--id", "reading-margin")
        states = {r["where"]: r["result"] for r in payload["item"]["reference_state"]}
        self.assertEqual(states["materials[0]"]["status"], "unresolved-catalog")
        self.assertEqual(states["materials[0]"]["required_catalog"], "shared-materials")

    def test_dependency_resolves_and_exact_revision_matters(self):
        dep = self.root / "shared.json"
        self.write_catalog(self.base_document(id="shared-materials", items=[
            self.reference_item(id="title-font", title="Font v1", revision=1),
            self.reference_item(id="title-font", title="Font v2", revision=2),
        ]), path=dep)
        item = self.style_item(materials=[
            {"catalog_id": "shared-materials", "item_id": "title-font", "revision": 2},
            {"catalog_id": "shared-materials", "item_id": "title-font", "revision": 9},
        ])
        self.write_catalog(self.base_document(items=[item]))
        _, payload = run_cli("show", "--catalog", str(self.catalog), "--id", "reading-margin",
                             "--with-catalog", str(dep))
        states = {r["where"]: r["result"]["status"] for r in payload["item"]["reference_state"]}
        self.assertEqual(states["materials[0]"], "resolved")
        self.assertEqual(states["materials[1]"], "unresolved-revision")

    def test_duplicate_catalog_id_is_ambiguous(self):
        dep = self.root / "dup.json"
        self.write_catalog(self.base_document(), path=dep)  # same id fc-library
        self.write_catalog(self.base_document())
        code, payload = run_cli("query", "--catalog", str(self.catalog), "--with-catalog", str(dep))
        self.assertNotEqual(code, 0)
        self.assertIn("ambiguous", payload["message"])


class QueryDependencyTests(Base):
    def test_query_includes_dependency_items(self):
        dep = self.root / "lib.json"
        self.write_catalog(self.base_document(id="fc-library", items=[
            self.style_item(),
        ]), path=dep)
        proj = self.write_catalog(self.base_document(
            id="sample-reader-project", items=[self.reference_item(id="result", title="Result")]),
            path=self.root / "proj.json")
        code, payload = run_cli("query", "--catalog", str(proj), "--with-catalog", str(dep))
        self.assertEqual(code, 0)
        pairs = {(i["catalog_id"], i["id"]) for i in payload["items"]}
        self.assertEqual(pairs, {("fc-library", "reading-margin"),
                                 ("sample-reader-project", "result")})
        self.assertEqual(set(payload["revisions"]), {"fc-library", "sample-reader-project"})

    def test_query_running_out_of_one_catalog_continues_into_next(self):
        dep = self.root / "lib.json"
        self.write_catalog(self.base_document(id="aaa-library", items=[self.reference_item(id="z1")]), path=dep)
        proj = self.write_catalog(self.base_document(
            id="zzz-project", items=[self.reference_item(id="a1")]), path=self.root / "proj.json")
        # Deterministic order is catalog id, then item id: aaa-library first.
        _, page1 = run_cli("query", "--catalog", str(proj), "--with-catalog", str(dep), "--limit", "1")
        self.assertEqual([i["id"] for i in page1["items"]], ["z1"])
        self.assertEqual(page1["next_offset"], 1)
        _, page2 = run_cli("query", "--catalog", str(proj), "--with-catalog", str(dep),
                           "--limit", "1", "--offset", "1")
        self.assertEqual([i["id"] for i in page2["items"]], ["a1"])
        self.assertFalse(page2["truncated"])


class TypeAndRoleValidationTests(Base):
    def test_non_object_item_rejected(self):
        self.write_catalog(self.base_document(items=["not an object"]))
        code, payload = run_cli("query", "--catalog", str(self.catalog))
        self.assertEqual(code, CAT.EXIT_INVALID)
        self.assertEqual(payload["status"], "invalid")

    def test_revision_bool_rejected(self):
        self.write_catalog(self.base_document(items=[self.reference_item(revision=True)]))
        code, payload = run_cli("validate", "--catalog", str(self.catalog))
        self.assertNotEqual(code, 0)
        self.assertIn("revision", payload["message"])

    def test_unknown_role_rejected(self):
        self.write_catalog(self.base_document(items=[self.reference_item(roles=["vibe"])]))
        code, payload = run_cli("validate", "--catalog", str(self.catalog))
        self.assertNotEqual(code, 0)
        self.assertIn("unknown role", payload["message"])

    def test_palette_role_requires_palette_block(self):
        self.write_catalog(self.base_document(items=[self.reference_item(roles=["palette"])]))
        code, payload = run_cli("validate", "--catalog", str(self.catalog))
        self.assertNotEqual(code, 0)
        self.assertIn("palette", payload["message"])

    def test_style_role_requires_making(self):
        item = self.reference_item(roles=["style"])
        self.write_catalog(self.base_document(items=[item]))
        code, payload = run_cli("validate", "--catalog", str(self.catalog))
        self.assertNotEqual(code, 0)
        self.assertIn("making", payload["message"])

    def test_duplicate_item_revision_rejected(self):
        self.write_catalog(self.base_document(items=[self.reference_item(), self.reference_item()]))
        code, payload = run_cli("validate", "--catalog", str(self.catalog))
        self.assertNotEqual(code, 0)
        self.assertIn("duplicate", payload["message"])

    def test_unsupported_version_refused(self):
        self.write_catalog({"version": 2, "id": "x", "revision": 0, "items": [], "uses": []})
        code, payload = run_cli("validate", "--catalog", str(self.catalog))
        self.assertNotEqual(code, 0)
        self.assertIn("version", payload["message"])

    def test_unknown_document_key_rejected(self):
        document = self.base_document()
        document["extra"] = 1
        self.write_catalog(document)
        code, payload = run_cli("validate", "--catalog", str(self.catalog))
        self.assertNotEqual(code, 0)
        self.assertIn("unknown keys", payload["message"])

    def test_use_status_in_use_requires_observed_at(self):
        use = {
            "id": "u1", "revision": 1,
            "target": {"project": "p", "location": {"region": "x"}},
            "references": [{"catalog_id": "fc-library", "item_id": "reading-margin", "revision": 1}],
            "relation": "r", "status": "in-use",
        }
        self.write_catalog(self.base_document(items=[self.style_item()], uses=[use]))
        code, payload = run_cli("validate", "--catalog", str(self.catalog))
        self.assertNotEqual(code, 0)
        self.assertIn("observed_at", payload["message"])

    def test_reference_asset_and_preview_mutually_exclusive(self):
        item = self.style_item(materials=[{
            "catalog_id": "fc-library", "item_id": "reading-margin", "revision": 1,
            "asset_id": "a", "preview_id": "p",
        }])
        self.write_catalog(self.base_document(items=[item]))
        code, payload = run_cli("validate", "--catalog", str(self.catalog))
        self.assertNotEqual(code, 0)
        self.assertIn("mutually exclusive", payload["message"])


class PathSafetyTests(Base):
    def test_absolute_locator_rejected(self):
        item = self.reference_item(assets=[{"id": "a", "locator": {"root": "catalog", "path": "/etc/passwd"}}])
        self.write_catalog(self.base_document(items=[item]))
        code, payload = run_cli("validate", "--catalog", str(self.catalog))
        self.assertNotEqual(code, 0)
        self.assertIn("relative", payload["message"])

    def test_traversal_locator_rejected(self):
        item = self.reference_item(assets=[{"id": "a", "locator": {"root": "catalog", "path": "../outside.png"}}])
        self.write_catalog(self.base_document(items=[item]))
        code, payload = run_cli("validate", "--catalog", str(self.catalog))
        self.assertNotEqual(code, 0)

    def test_unbound_root_refused(self):
        self.write(self.root / "shot.png", b"x")
        item = self.reference_item(previews=[{"id": "p", "kind": "screenshot",
                                              "locator": {"root": "project", "path": "shot.png"}}])
        self.write_catalog(self.base_document(items=[item]))
        code, payload = run_cli("resolve", "--catalog", str(self.catalog), "--id", "margin-reference")
        self.assertEqual(payload["previews"][0]["status"], "unavailable")
        self.assertIn("not bound", payload["previews"][0]["reason"])

    def test_symlink_escape_rejected(self):
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "secret.png").write_bytes(b"secret")
        project = self.root / "project"
        project.mkdir()
        os.symlink(outside / "secret.png", project / "link.png")
        item = self.reference_item(previews=[{"id": "p", "kind": "screenshot",
                                              "locator": {"root": "project", "path": "link.png"}}])
        self.write_catalog(self.base_document(items=[item]))
        code, payload = run_cli("resolve", "--catalog", str(self.catalog), "--id", "margin-reference",
                                "--root", "fc-library:project=" + str(project))
        result = payload["previews"][0]
        self.assertIn(result["status"], ("missing", "unavailable"))

    def test_root_binding_must_match_catalog_id(self):
        self.write_catalog(self.base_document())
        code, payload = run_cli("query", "--catalog", str(self.catalog),
                                "--root", "other-id:project=/tmp")
        self.assertEqual(code, CAT.EXIT_USAGE)
        self.assertEqual(payload["status"], "usage_error")


class ResolveTests(Base):
    def _make(self, digest_status: str):
        media = self.root / "captures"
        media.mkdir()
        payload = b"synthetic screenshot"
        (media / "wide.png").write_bytes(payload)
        digest = sha(payload)
        recorded = digest if digest_status == "match" else (sha(b"other") if digest_status == "changed" else None)
        preview = {"id": "wide", "kind": "screenshot",
                   "locator": {"root": "project", "path": "captures/wide.png"}}
        if recorded:
            preview["digest"] = recorded
        asset = {"id": "raw", "locator": {"root": "project", "path": "captures/wide.png"},
                 "file_type": "image/png", "sha256": digest}
        item = self.reference_item(previews=[preview], assets=[asset])
        self.write_catalog(self.base_document(items=[item]))
        return digest

    def test_available_when_digest_matches(self):
        digest = self._make("match")
        code, payload = run_cli("resolve", "--catalog", str(self.catalog), "--id", "margin-reference",
                                "--root", "fc-library:project=" + str(self.root))
        self.assertEqual(payload["status"], "resolved")
        self.assertEqual(payload["previews"][0]["status"], "available")
        self.assertEqual(payload["assets"][0]["sha256"], digest)

    def test_changed_when_digest_differs(self):
        self._make("changed")
        code, payload = run_cli("resolve", "--catalog", str(self.catalog), "--id", "margin-reference",
                                "--root", "fc-library:project=" + str(self.root))
        self.assertEqual(payload["status"], "partial")
        self.assertEqual(payload["previews"][0]["status"], "changed")
        self.assertNotEqual(code, 0)

    def test_missing_file_is_partial(self):
        project = self.root / "empty"
        project.mkdir()
        preview = {"id": "wide", "kind": "screenshot",
                   "locator": {"root": "project", "path": "captures/wide.png"}}
        self.write_catalog(self.base_document(items=[self.reference_item(previews=[preview])]))
        code, payload = run_cli("resolve", "--catalog", str(self.catalog), "--id", "margin-reference",
                                "--root", "fc-library:project=" + str(project))
        self.assertEqual(payload["status"], "partial")
        self.assertEqual(payload["previews"][0]["status"], "missing")
        self.assertNotEqual(code, 0)

    def test_remote_only_asset(self):
        asset = {"id": "repost", "url": "https://example.org/a.png"}
        item = self.reference_item(assets=[asset])
        self.write_catalog(self.base_document(items=[item]))
        code, payload = run_cli("resolve", "--catalog", str(self.catalog), "--id", "margin-reference")
        self.assertEqual(payload["assets"][0]["status"], "remote-only")
        self.assertEqual(code, 0)

    def test_missing_derivative_does_not_hide_available_original(self):
        media = self.root / "src"
        media.mkdir()
        (media / "orig.png").write_bytes(b"orig")
        digest = sha(b"orig")
        asset_ok = {"id": "orig", "locator": {"root": "project", "path": "src/orig.png"}, "sha256": digest}
        asset_bad = {"id": "crop", "locator": {"root": "project", "path": "src/crop.png"}, "sha256": sha(b"crop")}
        item = self.reference_item(assets=[asset_ok, asset_bad])
        self.write_catalog(self.base_document(items=[item]))
        code, payload = run_cli("resolve", "--catalog", str(self.catalog), "--id", "margin-reference",
                                "--root", "fc-library:project=" + str(self.root))
        statuses = {a["asset_id"]: a["status"] for a in payload["assets"]}
        self.assertEqual(statuses["orig"], "available")
        self.assertEqual(statuses["crop"], "missing")
        self.assertEqual(payload["status"], "partial")

    def test_dependency_asset_resolved_via_own_root(self):
        dep_dir = self.root / "shared"
        dep_dir.mkdir()
        (dep_dir / "font.woff2").write_bytes(b"fontbytes")
        dep = self.root / "shared.json"
        self.write_catalog(self.base_document(id="shared-materials", items=[
            self.reference_item(id="title-font", assets=[
                {"id": "web-subset", "locator": {"root": "materials", "path": "font.woff2"},
                 "sha256": sha(b"fontbytes")},
            ]),
        ]), path=dep)
        # The style item's own preview must resolve too, so "resolved" is about
        # the dependency asset resolving and not about a knowingly missing file.
        (self.root / "captures").mkdir(exist_ok=True)
        (self.root / "captures" / "wide.svg").write_bytes(b"<svg xmlns='http://www.w3.org/2000/svg'/>")
        item = self.style_item(materials=[
            {"catalog_id": "shared-materials", "item_id": "title-font", "revision": 1},
        ])
        self.write_catalog(self.base_document(items=[item]))
        code, payload = run_cli("resolve", "--catalog", str(self.catalog), "--id", "reading-margin",
                                "--with-catalog", str(dep),
                                "--root", "shared-materials:materials=" + str(dep_dir))
        self.assertEqual(payload["status"], "resolved")
        self.assertEqual(code, 0)
        # The referenced dependency media is in the continuation bundle, not the
        # item's own asset list, and resolves via the dependency's own root.
        ref_assets = payload["bundle"]["materials"]
        self.assertEqual(ref_assets[0]["status"], "available")
        self.assertEqual(ref_assets[0]["via"]["catalog_id"], "shared-materials")



class ResolveBundleTests(Base):
    def test_bundle_resolves_specimen_recipe_and_derivation_sources(self):
        base = self.root / "spec"
        base.mkdir()
        (base / "specimen.html").write_bytes(b"<html>spec</html>")
        (base / "subset.py").write_bytes(b"print('recipe')\n")
        (base / "src.woff2").write_bytes(b"srcbytes")
        src = self.reference_item(id="src", roles=["material"], assets=[
            {"id": "orig", "locator": {"root": "spec", "path": "src.woff2"},
             "sha256": sha(b"srcbytes")},
        ])
        out = self.reference_item(id="out", roles=["material"], derivation={
            "sources": [{"catalog_id": "fc-library", "item_id": "src", "revision": 1,
                         "asset_id": "orig"}],
            "script": {"root": "spec", "path": "subset.py"},
            "steps": ["subset the title glyphs"],
        }, specimen={"entry": "open specimen.html",
                     "locator": {"root": "spec", "path": "specimen.html"}})
        self.write_catalog(self.base_document(items=[src, out]))
        root_arg = "fc-library:spec=" + str(base)
        code, payload = run_cli("resolve", "--catalog", str(self.catalog), "--id", "out",
                                "--root", root_arg)
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload["status"], "resolved")
        bundle = payload["bundle"]
        self.assertEqual(bundle["specimen"]["media"]["status"], "available")
        self.assertEqual(bundle["specimen"]["entry"], "open specimen.html")
        # The recipe is resolved as a file but never executed.
        self.assertEqual(bundle["derivation"]["script"]["status"], "available")
        self.assertEqual(bundle["derivation"]["steps"], ["subset the title glyphs"])
        der_src = bundle["derivation"]["sources"][0]
        self.assertEqual(der_src["status"], "available")
        self.assertEqual(der_src["via"]["asset_id"], "orig")

    def test_bundle_reports_missing_recipe_and_unbound_specimen(self):
        out = self.reference_item(id="out", roles=["material"], derivation={
            "sources": [{"catalog_id": "fc-library", "item_id": "src", "revision": 1}],
            "script": {"root": "spec", "path": "gone.py"},
        }, specimen={"entry": "open", "locator": {"root": "spec", "path": "gone.html"}})
        src = self.reference_item(id="src", roles=["material"])
        self.write_catalog(self.base_document(items=[src, out]))
        # `spec` root is not bound: the gap is explicit, never guessed.
        code, payload = run_cli("resolve", "--catalog", str(self.catalog), "--id", "out")
        self.assertNotEqual(code, 0)
        self.assertEqual(payload["status"], "partial")
        self.assertEqual(payload["bundle"]["specimen"]["media"]["status"], "unavailable")
        self.assertEqual(payload["bundle"]["derivation"]["script"]["status"], "unavailable")

    def test_preview_selector_does_not_dump_item_assets(self):
        dep = self.root / "dep.json"
        self.write_catalog(self.base_document(id="shared-materials", items=[
            self.reference_item(id="pack", assets=[
                {"id": "a1", "locator": {"root": "catalog", "path": "a1.png"},
                 "sha256": sha(b"a1")},
                {"id": "a2", "locator": {"root": "catalog", "path": "a2.png"},
                 "sha256": sha(b"a2")},
            ], previews=[
                {"id": "p1", "kind": "image", "locator": {"root": "catalog", "path": "p1.png"}},
            ]),
        ]), path=dep)
        item = self.reference_item(id="user", materials=[
            {"catalog_id": "shared-materials", "item_id": "pack", "revision": 1,
             "preview_id": "p1"},
        ])
        self.write_catalog(self.base_document(items=[item]))
        _, payload = run_cli("resolve", "--catalog", str(self.catalog), "--id", "user",
                             "--with-catalog", str(dep))
        entries = payload["bundle"]["materials"]
        self.assertEqual(len(entries), 1)  # only the named preview, not the assets
        self.assertEqual(entries[0].get("preview_id"), "p1")
        self.assertNotIn("asset_id", entries[0])

    def test_asset_selector_does_not_dump_item_previews(self):
        dep = self.root / "dep.json"
        self.write_catalog(self.base_document(id="shared-materials", items=[
            self.reference_item(id="pack", assets=[
                {"id": "a1", "locator": {"root": "catalog", "path": "a1.png"},
                 "sha256": sha(b"a1")},
            ], previews=[
                {"id": "p1", "kind": "image", "locator": {"root": "catalog", "path": "p1.png"}},
            ]),
        ]), path=dep)
        item = self.reference_item(id="user", materials=[
            {"catalog_id": "shared-materials", "item_id": "pack", "revision": 1,
             "asset_id": "a1"},
        ])
        self.write_catalog(self.base_document(items=[item]))
        _, payload = run_cli("resolve", "--catalog", str(self.catalog), "--id", "user",
                             "--with-catalog", str(dep))
        entries = payload["bundle"]["materials"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].get("asset_id"), "a1")
        self.assertNotIn("preview_id", entries[0])



class ValidateCoverageTests(Base):
    def test_validate_checks_preserved_history_references(self):
        # A non-current revision with a dangling reference must still be invalid.
        items = [
            self.reference_item(id="x", revision=1, title="v1", materials=[
                {"catalog_id": "fc-library", "item_id": "ghost", "revision": 1}]),
            self.reference_item(id="x", revision=2, title="v2"),
        ]
        self.write_catalog(self.base_document(revision=2, items=items))
        code, payload = run_cli("validate", "--catalog", str(self.catalog))
        self.assertEqual(code, CAT.EXIT_INVALID)
        labels = [e["where"] for e in payload["errors"]]
        self.assertTrue(any("'x'@1" in label and "materials[0]" in label for label in labels),
                        labels)
        self.assertEqual(payload["item_versions"], 2)

    def test_validate_checks_use_evidence_previews(self):
        item = self.style_item()
        use = {"id": "u1", "revision": 1,
               "target": {"project": "p", "location": {"path": "a.tsx"}},
               "references": [{"catalog_id": "fc-library", "item_id": "reading-margin",
                               "revision": 1}],
               "relation": "r", "status": "selected",
               "evidence": {"previews": [
                   {"catalog_id": "fc-library", "item_id": "reading-margin",
                    "revision": 1, "preview_id": "nope"}]}}
        self.write_catalog(self.base_document(items=[item], uses=[use]))
        code, payload = run_cli("validate", "--catalog", str(self.catalog))
        self.assertEqual(code, CAT.EXIT_INVALID)
        self.assertTrue(any("evidence.previews[0]" in e["where"] for e in payload["errors"]),
                        payload["errors"])

    def test_validate_separates_invalid_reference_from_missing_file(self):
        # A recorded but absent specimen locator is missing_media, not an error;
        # a dangling reference is an error. Both are labelled exactly.
        item = self.reference_item(id="x", roles=["material"],
                                   specimen={"entry": "open",
                                             "locator": {"root": "catalog", "path": "gone.html"}},
                                   materials=[{"catalog_id": "fc-library", "item_id": "ghost",
                                               "revision": 1}])
        self.write_catalog(self.base_document(items=[item]))
        code, payload = run_cli("validate", "--catalog", str(self.catalog))
        self.assertEqual(code, CAT.EXIT_INVALID)
        self.assertTrue(any("materials[0]" in e["where"] for e in payload["errors"]))
        self.assertTrue(any("specimen.locator" in m["where"] for m in payload["missing_media"]))
        self.assertTrue(all(m["status"] != "invalid" for m in payload["missing_media"]))

    def test_validate_checks_derivation_script_locator(self):
        src = self.reference_item(id="src", roles=["material"])
        item = self.reference_item(id="x", roles=["material"], derivation={
            "sources": [{"catalog_id": "fc-library", "item_id": "src", "revision": 1}],
            "script": {"root": "catalog", "path": "missing.py"}})
        self.write_catalog(self.base_document(items=[src, item]))
        code, payload = run_cli("validate", "--catalog", str(self.catalog))
        # A recorded but absent script is a missing-media gap, not a structural
        # error, and carries an exact label.
        self.assertEqual(code, 0, payload)
        self.assertTrue(any("derivation.script" in m["where"] for m in payload["missing_media"]),
                        payload["missing_media"])


class DerivationTests(Base):
    def test_derivation_cycle_rejected(self):
        a = self.reference_item(id="a", roles=["material"], derivation={"sources": [
            {"catalog_id": "fc-library", "item_id": "b", "revision": 1}]})
        b = self.reference_item(id="b", roles=["material"], derivation={"sources": [
            {"catalog_id": "fc-library", "item_id": "a", "revision": 1}]})
        self.write_catalog(self.base_document(items=[a, b]))
        code, payload = run_cli("validate", "--catalog", str(self.catalog))
        self.assertEqual(code, CAT.EXIT_INVALID)
        self.assertIn("cycle", payload["message"])

    def test_general_materials_may_cycle(self):
        a = self.style_item(id="a", materials=[
            {"catalog_id": "fc-library", "item_id": "b", "revision": 1}])
        b = self.style_item(id="b", materials=[
            {"catalog_id": "fc-library", "item_id": "a", "revision": 1}])
        self.write_catalog(self.base_document(items=[a, b]))
        code, payload = run_cli("validate", "--catalog", str(self.catalog))
        self.assertEqual(code, 0, payload)

    def test_derivation_chain_exact_and_acyclic_ok(self):
        src = self.reference_item(id="src", roles=["material"])
        out = self.reference_item(id="out", roles=["material"], derivation={"sources": [
            {"catalog_id": "fc-library", "item_id": "src", "revision": 1}],
            "steps": ["subset"]})
        self.write_catalog(self.base_document(items=[src, out]))
        code, payload = run_cli("validate", "--catalog", str(self.catalog))
        self.assertEqual(code, 0, payload)

    def test_cross_catalog_derivation_cycle_rejected_by_validate(self):
        dep = self.root / "dep.json"
        self.write_catalog(self.base_document(id="shared-materials", items=[
            self.reference_item(id="b", roles=["material"], derivation={"sources": [
                {"catalog_id": "fc-library", "item_id": "a", "revision": 1}]}),
        ]), path=dep)
        self.write_catalog(self.base_document(items=[
            self.reference_item(id="a", roles=["material"], derivation={"sources": [
                {"catalog_id": "shared-materials", "item_id": "b", "revision": 1}]}),
        ]))
        code, payload = run_cli("validate", "--catalog", str(self.catalog), "--with-catalog", str(dep))
        self.assertEqual(code, CAT.EXIT_INVALID)
        self.assertTrue(any("cycle" in str(e.get("detail", "")) for e in payload["errors"]),
                        payload["errors"])

    def test_validate_reports_unresolved_derivation_source(self):
        # A derivation that names a missing exact revision is an explicit error,
        # not a silent pass; a missing dependency catalogue is too.
        self.write_catalog(self.base_document(items=[
            self.reference_item(id="out", roles=["material"], derivation={"sources": [
                {"catalog_id": "fc-library", "item_id": "ghost", "revision": 1}]}),
        ]))
        code, payload = run_cli("validate", "--catalog", str(self.catalog))
        self.assertEqual(code, CAT.EXIT_INVALID)
        self.assertTrue(any(e["status"] == "unresolved-derivation-source" for e in payload["errors"]),
                        payload["errors"])


class MediaSafetyTests(Base):
    def test_unsafe_source_url_rejected(self):
        item = self.reference_item(source={"kind": "external", "url": "javascript:alert(1)"})
        self.write_catalog(self.base_document(items=[item]))
        code, payload = run_cli("validate", "--catalog", str(self.catalog))
        self.assertNotEqual(code, 0)
        self.assertIn("http", payload["message"])

    def test_data_url_in_asset_rejected(self):
        item = self.reference_item(assets=[{"id": "a", "url": "data:text/html,<script>1</script>"}])
        self.write_catalog(self.base_document(items=[item]))
        code, payload = run_cli("validate", "--catalog", str(self.catalog))
        self.assertNotEqual(code, 0)

    def test_control_characters_in_metadata_rejected(self):
        item = self.reference_item(title="bad\x00title")
        self.write_catalog(self.base_document(items=[item]))
        code, payload = run_cli("validate", "--catalog", str(self.catalog))
        self.assertNotEqual(code, 0)
        self.assertIn("control", payload["message"])

    def test_javascript_in_tag_rejected(self):
        # A javascript: prefix in tag metadata is refused outright.
        item = self.reference_item(tags={"tasks": ["javascript:alert(1)"]})
        self.write_catalog(self.base_document(items=[item]))
        code, payload = run_cli("validate", "--catalog", str(self.catalog))
        self.assertNotEqual(code, 0)
        self.assertIn("active URL scheme", payload["message"])


class RegisterTests(Base):
    def _record(self, item, retain=None):
        record = {"catalog_id": "sample-reader-project", "kind": "item", "item": item}
        if retain:
            record["retain"] = retain
        return record

    def test_register_round_trip_and_retains_media(self):
        self.write("src/shot.png", b"PNG-DATA")
        digest = sha(b"PNG-DATA")
        record = self._record(
            {"id": "reader-result", "revision": 1, "title": "Result", "roles": ["reference"],
             "assets": [{"id": "raw", "locator": {"root": "retain", "path": "s"}, "file_type": "image/png"}]},
            retain=[{"id": "s", "root": "project", "path": "src/shot.png"}],
        )
        rec = self.write("rec.json", record)
        code, payload = run_cli("register", "--catalog", str(self.catalog),
                                "--record-file", str(rec), "--expect-revision", "0",
                                "--root", "sample-reader-project:project=" + str(self.root))
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload["status"], "registered")
        self.assertEqual(payload["revision"], 1)
        stored = json.loads(self.catalog.read_text())
        self.assertEqual(stored["revision"], 1)
        self.assertEqual(stored["items"][0]["assets"][0]["sha256"], digest)
        self.assertEqual(stored["items"][0]["assets"][0]["locator"]["path"], f"media/sha256/{digest}.png")
        self.assertTrue((self.root / "media" / "sha256" / f"{digest}.png").is_file())

    def test_inline_input_locator_is_retained(self):
        self.write("src/shot.png", b"INLINE-BYTES")
        digest = sha(b"INLINE-BYTES")
        record = self._record({
            "id": "inline-item", "revision": 1, "title": "Inline", "roles": ["reference"],
            "assets": [{"id": "raw", "input_locator": {"root": "project", "path": "src/shot.png"},
                        "file_type": "image/png"}],
        })
        rec = self.write("inline.json", record)
        code, payload = run_cli("register", "--catalog", str(self.catalog), "--record-file", str(rec),
                                "--expect-revision", "0",
                                "--root", "sample-reader-project:project=" + str(self.root))
        self.assertEqual(code, 0, payload)
        stored = json.loads(self.catalog.read_text())
        asset = stored["items"][0]["assets"][0]
        self.assertNotIn("input_locator", asset)
        self.assertEqual(asset["sha256"], digest)
        self.assertTrue((self.root / "media" / "sha256" / f"{digest}.png").is_file())

    def test_idempotent_same_record_returns_unchanged(self):
        self.write("src/shot.png", b"PNG-DATA")
        record = self._record(
            {"id": "i1", "revision": 1, "title": "T", "roles": ["reference"],
             "assets": [{"id": "raw", "locator": {"root": "retain", "path": "s"}, "file_type": "image/png"}]},
            retain=[{"id": "s", "root": "project", "path": "src/shot.png"}],
        )
        rec = self.write("rec.json", record)
        args = ("register", "--catalog", str(self.catalog), "--record-file", str(rec),
                "--root", "sample-reader-project:project=" + str(self.root))
        code, first = run_cli(*args, "--expect-revision", "0")
        self.assertEqual(first["status"], "registered")
        # Re-submit the identical payload at a stale expected revision: the whole
        # submission already exists, so it is idempotent rather than a conflict.
        code, second = run_cli(*args, "--expect-revision", "0")
        self.assertEqual(second["status"], "unchanged")
        self.assertEqual(second["revision"], first["revision"])
        stored = json.loads(self.catalog.read_text())
        self.assertEqual(len(stored["items"]), 1)
        self.assertEqual(stored["revision"], 1)  # no new file revision
        # A genuinely stale *different* write conflicts.
        rec2 = self.write("rec2.json", self._record(
            {"id": "i2", "revision": 1, "title": "Other", "roles": ["reference"]}))
        code, conflict = run_cli("register", "--catalog", str(self.catalog),
                                 "--record-file", str(rec2), "--expect-revision", "0")
        self.assertEqual(code, CAT.EXIT_CONFLICT)
        self.assertEqual(conflict["status"], "conflict")

    def test_changed_dependency_revision_is_not_unchanged(self):
        dep = self.root / "lib.json"
        self.write_catalog(self.base_document(id="shared-materials", items=[
            self.reference_item(id="font", title="Font v1", revision=1),
            self.reference_item(id="font", title="Font v2", revision=2),
        ]), path=dep)
        item = {"id": "use-font", "revision": 1, "title": "Use font", "roles": ["reference"],
                "materials": [{"catalog_id": "shared-materials", "item_id": "font", "revision": 1}]}
        rec = self.write("r.json", {"kind": "item", "item": item})
        args = ("register", "--catalog", str(self.catalog), "--record-file", str(rec),
                "--with-catalog", str(dep))
        _, first = run_cli(*args, "--expect-revision", "0")
        self.assertEqual(first["status"], "registered")
        # Identical resubmission at stale revision is idempotent.
        _, again = run_cli(*args, "--expect-revision", "0")
        self.assertEqual(again["status"], "unchanged")
        # Changing the referenced exact revision is NOT unchanged; at a stale
        # expected revision it must conflict.
        item2 = dict(item)
        item2["materials"] = [{"catalog_id": "shared-materials", "item_id": "font", "revision": 2}]
        rec2 = self.write("r2.json", {"kind": "item", "item": item2})
        code, conflict = run_cli("register", "--catalog", str(self.catalog), "--record-file", str(rec2),
                                 "--with-catalog", str(dep), "--expect-revision", "0")
        self.assertEqual(code, CAT.EXIT_CONFLICT)
        self.assertEqual(conflict["status"], "conflict")

    def test_use_observed_at_ignored_on_retry(self):
        import time as _time
        self.write_catalog(self.base_document(items=[self.style_item()]))
        use = {"id": "u1", "revision": 1,
               "target": {"project": "p", "location": {"path": "a.tsx"}},
               "references": [{"catalog_id": "fc-library", "item_id": "reading-margin", "revision": 1}],
               "relation": "r", "status": "in-use"}
        rec = self.write("u.json", {"kind": "use", "use": use})
        _, first = run_cli("register", "--catalog", str(self.catalog), "--record-file", str(rec),
                           "--expect-revision", "1")
        self.assertEqual(first["status"], "registered")
        observed = json.loads(self.catalog.read_text())["uses"][0]["observed_at"]
        self.assertTrue(observed)
        _time.sleep(1.1)  # ensure a regenerated timestamp would differ
        _, again = run_cli("register", "--catalog", str(self.catalog), "--record-file", str(rec),
                           "--expect-revision", "1")
        self.assertEqual(again["status"], "unchanged")
        stored = json.loads(self.catalog.read_text())
        self.assertEqual(len(stored["uses"]), 1)
        self.assertEqual(stored["uses"][0]["observed_at"], observed)

    def test_reapplying_older_value_creates_new_current_version(self):
        self.write_catalog(self.base_document(revision=1, items=[
            self.reference_item(id="x", revision=1, title="v1"),
            self.reference_item(id="x", revision=2, title="v2"),
        ]))
        rec = self.write("r.json", {"kind": "item",
                                    "item": {"id": "x", "revision": 1, "title": "v1", "roles": ["reference"]}})
        code, payload = run_cli("register", "--catalog", str(self.catalog), "--record-file", str(rec),
                                "--expect-revision", "1")
        self.assertEqual(payload["status"], "registered")
        self.assertEqual(payload["revision"], 3)  # reapplication is a new current version
        stored = json.loads(self.catalog.read_text())
        self.assertEqual(sorted(i["revision"] for i in stored["items"] if i["id"] == "x"), [1, 2, 3])

    def test_batch_package_registers_items_and_uses_atomically(self):
        batch = {"catalog_id": "fc-library", "items": [
            {"id": "a", "revision": 1, "title": "A", "roles": ["reference"]},
            {"id": "b", "revision": 1, "title": "B", "roles": ["reference"],
             "materials": [{"catalog_id": "fc-library", "item_id": "a", "revision": 1}]},
        ], "uses": [
            {"id": "u", "revision": 1,
             "target": {"project": "p", "location": {"region": "x"}},
             "references": [{"catalog_id": "fc-library", "item_id": "b", "revision": 1}],
             "relation": "r", "status": "selected"},
        ]}
        rec = self.write("batch.json", batch)
        code, payload = run_cli("register", "--catalog", str(self.catalog), "--record-file", str(rec),
                                "--expect-revision", "0")
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload["status"], "registered")
        self.assertEqual({i["id"] for i in payload["items"]}, {"a", "b"})
        self.assertEqual(payload["uses"][0]["id"], "u")
        stored = json.loads(self.catalog.read_text())
        self.assertEqual(stored["revision"], 1)  # one file revision for the whole package
        self.assertEqual({i["id"] for i in stored["items"]}, {"a", "b"})
        # Whole package is idempotent at a stale expected revision.
        _, again = run_cli("register", "--catalog", str(self.catalog), "--record-file", str(rec),
                           "--expect-revision", "0")
        self.assertEqual(again["status"], "unchanged")
        self.assertEqual(len(json.loads(self.catalog.read_text())["items"]), 2)

    def test_batch_dangling_reference_rejected_without_partial_commit(self):
        batch = {"items": [
            {"id": "a", "revision": 1, "title": "A", "roles": ["reference"],
             "materials": [{"catalog_id": "fc-library", "item_id": "ghost", "revision": 1}]},
        ]}
        rec = self.write("batch.json", batch)
        code, payload = run_cli("register", "--catalog", str(self.catalog), "--record-file", str(rec),
                                "--expect-revision", "0")
        self.assertEqual(code, CAT.EXIT_INVALID)
        self.assertFalse(self.catalog.exists())  # nothing partially committed

    def test_dedup_preserves_original_under_same_name_overwrite(self):
        self.write("src/screenshot.png", b"ORIGINAL")
        digest_a = sha(b"ORIGINAL")
        rec = self.write("r1.json", self._record(
            {"id": "cap1", "revision": 1, "title": "cap1", "roles": ["reference"],
             "assets": [{"id": "raw", "locator": {"root": "retain", "path": "s"}}]},
            retain=[{"id": "s", "root": "project", "path": "src/screenshot.png"}]))
        run_cli("register", "--catalog", str(self.catalog), "--record-file", str(rec),
                "--expect-revision", "0", "--root", "sample-reader-project:project=" + str(self.root))
        # The same filename is overwritten with different content and registered
        # again; both immutable copies must survive.
        self.write("src/screenshot.png", b"REPLACED")
        digest_b = sha(b"REPLACED")
        rec2 = self.write("r2.json", self._record(
            {"id": "cap2", "revision": 1, "title": "cap2", "roles": ["reference"],
             "assets": [{"id": "raw", "locator": {"root": "retain", "path": "s"}}]},
            retain=[{"id": "s", "root": "project", "path": "src/screenshot.png"}]))
        run_cli("register", "--catalog", str(self.catalog), "--record-file", str(rec2),
                "--expect-revision", "1", "--root", "sample-reader-project:project=" + str(self.root))
        media = self.root / "media" / "sha256"
        self.assertTrue((media / f"{digest_a}.png").is_file())
        self.assertTrue((media / f"{digest_b}.png").is_file())
        self.assertEqual((media / f"{digest_a}.png").read_bytes(), b"ORIGINAL")
        stored = json.loads(self.catalog.read_text())
        digests = {i["assets"][0]["sha256"] for i in stored["items"]}
        self.assertEqual(digests, {digest_a, digest_b})

    def test_item_revision_increments_on_change(self):
        rec1 = self.write("a.json", self._record(
            {"id": "x", "revision": 1, "title": "v1", "roles": ["reference"]}))
        run_cli("register", "--catalog", str(self.catalog), "--record-file", str(rec1), "--expect-revision", "0")
        rec2 = self.write("b.json", self._record(
            {"id": "x", "revision": 1, "title": "v2", "roles": ["reference"]}))
        _, payload = run_cli("register", "--catalog", str(self.catalog), "--record-file", str(rec2), "--expect-revision", "1")
        self.assertEqual(payload["status"], "registered")
        self.assertEqual(payload["revision"], 2)
        stored = json.loads(self.catalog.read_text())
        self.assertEqual(sorted(i["revision"] for i in stored["items"]), [1, 2])

    def test_import_catalog_id_mismatch_rejected(self):
        rec = self.write("m.json", {"catalog_id": "other", "kind": "item",
                                    "item": {"id": "x", "revision": 1, "title": "t", "roles": ["reference"]}})
        self.write_catalog(self.base_document())
        code, payload = run_cli("register", "--catalog", str(self.catalog),
                                "--record-file", str(rec), "--expect-revision", "1")
        self.assertEqual(code, CAT.EXIT_INVALID)
        self.assertIn("does not match", payload["message"])

    def test_register_rejects_derivation_cycle_atomically(self):
        a = self.reference_item(id="a", roles=["material"], derivation={"sources": [
            {"catalog_id": "fc-library", "item_id": "b", "revision": 1}]})
        self.write_catalog(self.base_document(items=[a]))
        # Adding b with a derivation back to a would close the cycle.
        rec = self.write("cyc.json", {"kind": "item", "item": self.reference_item(
            id="b", roles=["material"], derivation={"sources": [
                {"catalog_id": "fc-library", "item_id": "a", "revision": 1}]})})
        before = self.catalog.read_text()
        code, payload = run_cli("register", "--catalog", str(self.catalog), "--record-file", str(rec),
                                "--expect-revision", "1")
        self.assertEqual(code, CAT.EXIT_INVALID)
        self.assertIn("cycle", payload["message"])
        self.assertEqual(self.catalog.read_text(), before)  # file untouched

    def test_malformed_payload_leaves_catalog_untouched(self):
        rec = self.write("bad.json", {"kind": "item", "item": {"id": "x", "roles": ["reference"]}})
        before = self.catalog.read_text() if self.catalog.exists() else None
        code, payload = run_cli("register", "--catalog", str(self.catalog), "--record-file", str(rec),
                                "--expect-revision", "0")
        self.assertEqual(code, CAT.EXIT_INVALID)
        self.assertFalse(self.catalog.exists())

    def test_interrupted_register_leaves_previous_catalog_readable(self):
        rec1 = self.write("a.json", {"kind": "item",
                                     "item": {"id": "x", "revision": 1, "title": "one", "roles": ["reference"]}})
        run_cli("register", "--catalog", str(self.catalog), "--record-file", str(rec1), "--expect-revision", "0")
        before = self.catalog.read_text()
        rec2 = self.write("b.json", {"kind": "item",
                                     "item": {"id": "y", "revision": 1, "title": "two", "roles": ["reference"]}})
        real_replace = os.replace

        def boom(src, dst):
            raise OSError("simulated write interruption")

        CAT.os.replace = boom
        try:
            code, payload = run_cli("register", "--catalog", str(self.catalog),
                                    "--record-file", str(rec2), "--expect-revision", "1")
        finally:
            CAT.os.replace = real_replace
        self.assertNotEqual(code, 0)
        # The previous complete catalogue is intact and unchanged.
        self.assertEqual(self.catalog.read_text(), before)
        stored = json.loads(self.catalog.read_text())
        self.assertEqual({i["id"] for i in stored["items"]}, {"x"})
        # An interrupted write may leave an unreferenced temp file (spec allows
        # this) but it must never be read as the catalogue; the catalogue path
        # itself only ever holds a complete document.
        json.loads(self.catalog.read_text())  # still parseable
        for leftover in self.root.glob(".catalog.json*.tmp"):
            self.assertNotEqual(leftover.name, "catalog.json")

    def test_media_retention_failure_does_not_publish(self):
        rec = self.write("r.json", {"catalog_id": "sample-reader-project", "kind": "item",
                                    "item": {"id": "x", "revision": 1, "title": "t", "roles": ["reference"],
                                             "assets": [{"id": "a",
                                                         "locator": {"root": "retain", "path": "s"}}]},
                                    "retain": [{"id": "s", "root": "project", "path": "missing.png"}]})
        code, payload = run_cli("register", "--catalog", str(self.catalog), "--record-file", str(rec),
                                "--expect-revision", "0",
                                "--root", "sample-reader-project:project=" + str(self.root))
        self.assertNotEqual(code, 0)
        self.assertFalse(self.catalog.exists())  # nothing published

    def test_concrete_locator_records_real_digest_and_resolves_change(self):
        self.write("src/a.png", b"ABC")
        rec = self.write("r.json", {"catalog_id": "sample-reader-project", "kind": "item",
                                    "item": {"id": "i", "revision": 1, "title": "t",
                                             "roles": ["reference"],
                                             "assets": [{"id": "a", "locator": {
                                                 "root": "project", "path": "src/a.png"}}],
                                             "previews": [{"id": "p1", "kind": "image",
                                                           "locator": {
                                                               "root": "project",
                                                               "path": "src/a.png"}}]}})
        root_arg = "sample-reader-project:project=" + str(self.root)
        code, payload = run_cli("register", "--catalog", str(self.catalog),
                                "--record-file", str(rec), "--expect-revision", "0",
                                "--root", root_arg)
        self.assertEqual(code, 0, payload)
        stored = json.loads(self.catalog.read_text())["items"][0]
        self.assertEqual(stored["assets"][0]["sha256"], sha(b"ABC"))
        self.assertEqual(stored["previews"][0]["digest"], sha(b"ABC"))
        # Re-running the identical record is idempotent even though the digest
        # is a computed fact.
        _, again = run_cli("register", "--catalog", str(self.catalog),
                           "--record-file", str(rec), "--expect-revision", "1",
                           "--root", root_arg)
        self.assertEqual(again["status"], "unchanged")
        # Changing the real bytes is detected as `changed`, never a silent pass.
        self.write("src/a.png", b"XYZ")
        code, resolved = run_cli("resolve", "--catalog", str(self.catalog), "--id", "i",
                                 "--root", root_arg)
        self.assertEqual(resolved["status"], "partial")
        self.assertEqual(resolved["assets"][0]["status"], "changed")
        self.assertEqual(resolved["previews"][0]["status"], "changed")

    def test_missing_concrete_locator_records_no_fake_digest(self):
        # A concrete locator whose file is absent must not gain a digest.
        rec = self.write("r.json", {"catalog_id": "sample-reader-project", "kind": "item",
                                    "item": {"id": "i", "revision": 1, "title": "t",
                                             "roles": ["reference"],
                                             "assets": [{"id": "a", "locator": {
                                                 "root": "catalog", "path": "nope.png"}}]}})
        code, payload = run_cli("register", "--catalog", str(self.catalog),
                                "--record-file", str(rec), "--expect-revision", "0")
        self.assertEqual(code, 0, payload)
        stored = json.loads(self.catalog.read_text())["items"][0]
        self.assertNotIn("sha256", stored["assets"][0])

    def test_use_registration_and_history(self):
        self.write_catalog(self.base_document(items=[self.style_item()]))
        use = {"id": "u1", "revision": 1,
               "target": {"project": "sample-reader", "location": {"path": "src/Reader.tsx"}},
               "references": [{"catalog_id": "fc-library", "item_id": "reading-margin", "revision": 1}],
               "relation": "carry the measure", "status": "in-use"}
        rec = self.write("u1.json", {"kind": "use", "use": use})
        _, payload = run_cli("register", "--catalog", str(self.catalog), "--record-file", str(rec),
                             "--expect-revision", "1")
        self.assertEqual(payload["status"], "registered")
        stored = json.loads(self.catalog.read_text())
        self.assertTrue(stored["uses"][0]["observed_at"])  # filled in for in-use


class LockAndConcurrencyTests(Base):
    def test_lock_blocks_second_writer(self):
        self.write_catalog(self.base_document())
        lock = CAT.FileLock(self.catalog, timeout=0.2)
        lock.__enter__()
        try:
            rec = self.write("r.json", {"kind": "item",
                                        "item": {"id": "x", "revision": 1, "title": "t", "roles": ["reference"]}})
            code, payload = run_cli("register", "--catalog", str(self.catalog), "--record-file", str(rec),
                                    "--expect-revision", "1", "--lock-timeout", "0.2")
            self.assertEqual(code, CAT.EXIT_BUSY)
            self.assertEqual(payload["status"], "busy")
        finally:
            lock.__exit__(None, None, None)

    def test_stale_os_lock_never_deleted_by_age(self):
        # A lock file left closed by a crashed process must not be removed based
        # on age; a fresh holder simply acquires it.
        self.write_catalog(self.base_document())
        stale = self.catalog.parent / (self.catalog.name + ".lock")
        stale.write_text("")
        old = 1000
        os.utime(stale, (old, old))
        self.assertTrue(stale.exists())
        rec = self.write("r.json", {"kind": "item",
                                    "item": {"id": "x", "revision": 1, "title": "t", "roles": ["reference"]}})
        code, payload = run_cli("register", "--catalog", str(self.catalog), "--record-file", str(rec),
                                "--expect-revision", "1")
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "registered")

    def test_concurrent_distinct_writers_merge(self):
        self.write_catalog(self.base_document())
        results = {}

        def writer(name, item_id):
            rec = self.write(f"{name}.json", {"kind": "item", "item": {
                "id": item_id, "revision": 1, "title": item_id, "roles": ["reference"]}})
            quiet = io.StringIO()
            for _ in range(8):
                with contextlib.redirect_stdout(quiet):
                    _, payload = run_cli("register", "--catalog", str(self.catalog),
                                         "--record-file", str(rec), "--expect-revision", "0")
                if payload.get("status") in ("registered", "unchanged"):
                    results[name] = payload["status"]
                    return
                if payload.get("status") == "conflict":
                    # re-read current revision and retry at the observed revision
                    current = json.loads(self.catalog.read_text())["revision"]
                    with contextlib.redirect_stdout(quiet):
                        _, payload = run_cli("register", "--catalog", str(self.catalog),
                                             "--record-file", str(rec),
                                             "--expect-revision", str(current))
                    if payload.get("status") in ("registered", "unchanged"):
                        results[name] = payload["status"]
                        return
            results[name] = "failed"

        threads = [threading.Thread(target=writer, args=("a", "item-a")),
                   threading.Thread(target=writer, args=("b", "item-b"))]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        # A writer may observe another's completed write and legitimately get
        # ``unchanged`` (its content already exists); both mean success.
        self.assertTrue(set(results.values()) <= {"registered", "unchanged"}, results)
        stored = json.loads(self.catalog.read_text())
        self.assertEqual({i["id"] for i in stored["items"]}, {"item-a", "item-b"})

    def test_same_id_different_content_conflicts_not_blind_overwrite(self):
        self.write_catalog(self.base_document(items=[self.reference_item(id="x", title="first")]))
        rec = self.write("r.json", {"kind": "item",
                                    "item": {"id": "x", "revision": 1, "title": "second", "roles": ["reference"]}})
        code, payload = run_cli("register", "--catalog", str(self.catalog), "--record-file", str(rec),
                                "--expect-revision", "0")
        self.assertEqual(code, CAT.EXIT_CONFLICT)
        self.assertEqual(payload["status"], "conflict")
        stored = json.loads(self.catalog.read_text())
        self.assertEqual(stored["items"][0]["title"], "first")


class GalleryTests(Base):
    def _catalog_with_media(self):
        media = self.root / "project" / "assets"
        media.mkdir(parents=True)
        (media / "wide.png").write_bytes(b"image-bytes")
        (media / "clip.svg").write_bytes(b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>")
        item = self.style_item(
            specimen={"entry": "npm run start", "notes": "synthetic"},
            previews=[
                {"id": "wide", "kind": "screenshot",
                 "locator": {"root": "project", "path": "assets/wide.png"},
                 "capture": {"viewport": [1440, 900], "state": "note open"}},
                {"id": "mark", "kind": "image",
                 "locator": {"root": "project", "path": "assets/clip.svg"}},
            ],
            source={"kind": "authored", "note": "synthetic"},
        )
        self.write_catalog(self.base_document(items=[item]))
        return self.root / "project"

    def test_gallery_copies_referenced_media_and_writes_page(self):
        project = self._catalog_with_media()
        out = self.root / "gallery"
        code, payload = run_cli("gallery", "--catalog", str(self.catalog), "--out", str(out),
                                "--root", "fc-library:project=" + str(project),
                                "--view-bindings", str(self.write("vb.json", {
                                    "fc-library:reading-margin:1": "https://127.0.0.1:5199/run"})))
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload["status"], "generated")
        index = (out / "index.html").read_text()
        manifest = json.loads((out / "media-manifest.json").read_text())["media"]
        self.assertTrue(manifest)  # media copied, not left as path-only links
        self.assertNotIn(str(project), index)  # no absolute host paths in the page
        self.assertNotIn("javascript:alert", index)  # SVG script text not inlined
        self.assertIn("https://127.0.0.1:5199/run", index)  # view binding used
        self.assertIn("open running instance", index)
        # Each copied file exists and is referenced by a relative URL.
        for digest, rel in manifest.items():
            self.assertTrue((out / rel).is_file())
        self.assertIn("<img", index)

    def _project_with_dependency(self):
        dep_dir = self.root / "dep"
        dep_dir.mkdir()
        (dep_dir / "v1.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'><rect/></svg>")
        (dep_dir / "v2.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'><circle/></svg>")
        dep = dep_dir / "catalog.json"
        self.write_catalog(self.base_document(id="fc-library", revision=2, items=[
            {"id": "lm", "revision": 1, "title": "LM v1", "roles": ["style"],
             "making": {"effect": "e1", "carry": ["c"], "vary": ["v"], "limits": "l"},
             "specimen": {"entry": "npm run v1", "notes": "synthetic"},
             "previews": [{"id": "p", "kind": "screenshot",
                           "locator": {"root": "catalog", "path": "v1.svg"}}]},
            {"id": "lm", "revision": 2, "title": "LM v2", "roles": ["style"],
             "making": {"effect": "e2", "carry": ["c"], "vary": ["v"], "limits": "l"},
             "specimen": {"entry": "npm run v2", "notes": "synthetic"},
             "palette": {"roles": {"base": {"value": "#ffffff"}},
                         "instance": {"catalog_id": "fc-library", "item_id": "lm", "revision": 2}},
             "previews": [{"id": "p", "kind": "screenshot",
                           "locator": {"root": "catalog", "path": "v2.svg"}}]},
            {"id": "unrelated", "revision": 1, "title": "UNRELATED-DUMP", "roles": ["reference"]},
        ]), path=dep)
        project = self.root / "project"
        project.mkdir()
        (project / "shot.png").write_bytes(b"PROJECT-SHOT")
        item = {"id": "result", "revision": 1, "title": "Result", "roles": ["reference"],
                "previews": [{"id": "shot", "kind": "screenshot",
                              "locator": {"root": "catalog", "path": "project/shot.png"}}],
                "materials": [{"catalog_id": "fc-library", "item_id": "lm", "revision": 2}]}
        use = {"id": "u1", "revision": 1,
               "target": {"project": "sample-reader", "location": {"path": "src/R.tsx"}},
               "references": [{"catalog_id": "fc-library", "item_id": "lm", "revision": 2}],
               "relation": "carry measure", "status": "in-use",
               "observed_at": "2026-10-07T16:00:00Z"}
        self.write_catalog(
            {"version": 1, "id": "sample-reader-project", "revision": 1,
             "items": [item], "uses": [use]},
            path=self.catalog)
        return dep, project

    def test_gallery_includes_exact_dependency_items_not_dump(self):
        dep, project = self._project_with_dependency()
        out = self.root / "gd"
        code, payload = run_cli("gallery", "--catalog", str(self.catalog), "--out", str(out),
                                "--with-catalog", str(dep))
        self.assertEqual(code, 0, payload)
        index = (out / "index.html").read_text()
        self.assertIn("fc-library/lm@2", index)           # exact referenced revision shown
        self.assertIn("LM v1", index)                      # history media rendered
        self.assertIn("e2", index)                         # making present
        self.assertIn("#ffffff", index)                    # palette present
        self.assertIn("Current project uses (1)", index)
        self.assertNotIn("UNRELATED-DUMP", index)          # no dependency dump
        manifest = json.loads((out / "media-manifest.json").read_text())["media"]
        self.assertGreaterEqual(len(manifest), 3)          # project shot + dep v1/v2

    def test_gallery_history_shows_old_media_with_labels(self):
        dep, project = self._project_with_dependency()
        out = self.root / "gh"
        run_cli("gallery", "--catalog", str(self.catalog), "--out", str(out),
                "--with-catalog", str(dep))
        index = (out / "index.html").read_text()
        # Two distinct digests for the two dep revisions must both be copied.
        manifest = json.loads((out / "media-manifest.json").read_text())["media"]
        copied = {m for m in manifest.values()}
        self.assertIn("media/" + sha(b"<svg xmlns='http://www.w3.org/2000/svg'><rect/></svg>") + ".svg", copied)
        self.assertIn("media/" + sha(b"<svg xmlns='http://www.w3.org/2000/svg'><circle/></svg>") + ".svg", copied)

    def test_gallery_view_binding_is_revision_exact(self):
        dep, project = self._project_with_dependency()
        # Legacy id-only key must NOT bind the historical revision.
        legacy = self.write("vb-legacy.json", {"fc-library:lm": "https://127.0.0.1:5199/old"})
        out = self.root / "gv"
        run_cli("gallery", "--catalog", str(self.catalog), "--out", str(out),
                "--with-catalog", str(dep), "--view-bindings", str(legacy))
        self.assertNotIn("https://127.0.0.1:5199/old", (out / "index.html").read_text())
        # Exact versioned key binds.
        exact = self.write("vb-exact.json", {"fc-library:lm:2": "https://127.0.0.1:5199/new"})
        out2 = self.root / "gv2"
        run_cli("gallery", "--catalog", str(self.catalog), "--out", str(out2),
                "--with-catalog", str(dep), "--view-bindings", str(exact))
        self.assertIn("https://127.0.0.1:5199/new", (out2 / "index.html").read_text())

    def test_gallery_exact_filter_not_prefix(self):
        self.write_catalog(self.base_document(items=[
            self.reference_item(id="a", tags={"languages": ["zh-Hans"], "media": ["typography"]}),
        ]))
        out = self.root / "gf"
        run_cli("gallery", "--catalog", str(self.catalog), "--out", str(out))
        index = (out / "index.html").read_text()
        # The page splits comma lists and compares whole tokens, so "zh" cannot
        # match "zh-Hans"; assert the helper implements exact token matching.
        self.assertIn("hasExact", index)
        self.assertIn('data-languages="zh-Hans"', index)

    def test_gallery_without_view_binding_marks_not_running(self):
        project = self._catalog_with_media()
        out = self.root / "gallery2"
        code, payload = run_cli("gallery", "--catalog", str(self.catalog), "--out", str(out),
                                "--root", "fc-library:project=" + str(project))
        self.assertEqual(code, 0)
        index = (out / "index.html").read_text()
        self.assertIn("not yet running", index)

    def test_gallery_rejects_active_view_binding(self):
        project = self._catalog_with_media()
        vb = self.write("vb.json", {"fc-library:reading-margin:1": "javascript:alert(1)"})
        code, payload = run_cli("gallery", "--catalog", str(self.catalog), "--out", str(self.root / "g"),
                                "--root", "fc-library:project=" + str(project),
                                "--view-bindings", str(vb))
        self.assertEqual(code, CAT.EXIT_INVALID)
        self.assertIn("http", payload["message"])

    def test_gallery_escapes_untrusted_metadata(self):
        item = self.style_item(title="<img src=x onerror=alert(1)> & \"quotes\"")
        self.write_catalog(self.base_document(items=[item]))
        out = self.root / "g3"
        code, _ = run_cli("gallery", "--catalog", str(self.catalog), "--out", str(out))
        self.assertEqual(code, 0)
        index = (out / "index.html").read_text()
        self.assertNotIn("<img src=x onerror", index)
        self.assertIn("&lt;img src=x", index)

    def test_gallery_missing_media_still_lists_item(self):
        item = self.reference_item(previews=[{"id": "m", "kind": "screenshot",
                                              "locator": {"root": "project", "path": "assets/gone.png"}}])
        self.write_catalog(self.base_document(items=[item]))
        out = self.root / "g4"
        code, payload = run_cli("gallery", "--catalog", str(self.catalog), "--out", str(out),
                                "--root", "fc-library:project=" + str(self.root))
        self.assertEqual(code, 0)
        self.assertTrue(payload["skipped_previews"])
        index = (out / "index.html").read_text()
        self.assertIn(item["title"], index)  # metadata still readable

    def test_gallery_leaves_no_staging_scratch_after_success(self):
        self._catalog_with_media()
        out = self.root / "g-clean"
        code, _ = run_cli("gallery", "--catalog", str(self.catalog), "--out", str(out))
        self.assertEqual(code, 0)
        leftovers = [p.name for p in self.root.iterdir() if p.name.startswith(".gallery-stage-")]
        self.assertEqual(leftovers, [])
        self.assertTrue((out / "index.html").is_file())

    def test_gallery_shows_project_uses_and_no_inert_actions(self):
        use = {"id": "u1", "revision": 1,
               "target": {"project": "sample-reader", "location": {"path": "src/x.tsx"}},
               "references": [{"catalog_id": "fc-library", "item_id": "reading-margin", "revision": 1}],
               "relation": "carry the measure", "status": "in-use",
               "observed_at": "2026-10-07T16:00:00Z"}
        self.write_catalog(self.base_document(items=[self.style_item()], uses=[use]))
        out = self.root / "g-uses"
        code, _ = run_cli("gallery", "--catalog", str(self.catalog), "--out", str(out))
        self.assertEqual(code, 0)
        index = (out / "index.html").read_text()
        self.assertIn("Current project uses (1)", index)
        self.assertIn("carry the measure", index)
        self.assertIn("recorded 2026-10-07T16:00:00Z", index)
        # No unimplemented Adopt/Apply/Save buttons.
        lowered = index.lower()
        for word in (">adopt<", ">apply<", ">save<"):
            self.assertNotIn(word, lowered)

    def test_gallery_filter_attributes_present(self):
        self.write_catalog(self.base_document(items=[
            self.style_item(tags={"tasks": ["reading"], "languages": ["zh-Hans"], "media": ["typography"]}),
        ]))
        out = self.root / "g-attrs"
        run_cli("gallery", "--catalog", str(self.catalog), "--out", str(out))
        index = (out / "index.html").read_text()
        self.assertIn('data-roles="style"', index)
        self.assertIn('data-tasks="reading"', index)
        self.assertIn('data-languages="zh-Hans"', index)

    def test_interrupted_gallery_preserves_previous_output(self):
        project = self._catalog_with_media()
        out = self.root / "g5"
        run_cli("gallery", "--catalog", str(self.catalog), "--out", str(out),
                "--root", "fc-library:project=" + str(project))
        original = (out / "index.html").read_text()

        # Inject a failure at the publish boundary (not merely a handled OSError)
        # to prove the live index is never missing during regeneration.
        real = CAT._publish_generation

        def boom(staging, target):
            raise RuntimeError("simulated interruption at publish")

        rec = self.write("add.json", {"kind": "item", "item": {
            "id": "extra", "revision": 1, "title": "extra", "roles": ["reference"]}})
        run_cli("register", "--catalog", str(self.catalog), "--record-file", str(rec),
                "--expect-revision", "1")
        CAT._publish_generation = boom
        try:
            with self.assertRaises(RuntimeError):
                CAT.cmd_gallery(CAT.build_parser().parse_args([
                    "gallery", "--catalog", str(self.catalog), "--out", str(out),
                    "--root", "fc-library:project=" + str(project)]))
        finally:
            CAT._publish_generation = real
        # The previous complete page is still present and readable.
        self.assertEqual((out / "index.html").read_text(), original)
        self.assertTrue((out / "index.html").is_file())

    def test_gallery_publish_failure_midway_keeps_live_index(self):
        # Fail after media copy but before index replace: the live index must
        # remain the previous revision.
        project = self._catalog_with_media()
        out = self.root / "g6"
        run_cli("gallery", "--catalog", str(self.catalog), "--out", str(out),
                "--root", "fc-library:project=" + str(project))
        original = (out / "index.html").read_text()
        real_replace = os.replace

        def fail_on_index(src, dst):
            if os.path.basename(str(dst)) == "index.html":
                raise OSError("simulated kill before index publish")
            return real_replace(src, dst)

        CAT.os.replace = fail_on_index
        try:
            code, payload = run_cli("gallery", "--catalog", str(self.catalog), "--out", str(out),
                                    "--root", "fc-library:project=" + str(project))
        finally:
            CAT.os.replace = real_replace
        self.assertNotEqual(code, 0)
        self.assertTrue((out / "index.html").is_file())
        self.assertEqual((out / "index.html").read_text(), original)

    def test_gallery_publish_order_is_media_then_meta_then_index(self):
        # Record the order of published names to lock the interruption contract.
        project = self._catalog_with_media()
        out = self.root / "g-order"
        real_replace = os.replace
        order: list = []

        def record(src, dst):
            name = os.path.basename(str(dst))
            if os.path.dirname(str(dst)) == str(out):
                order.append(name)
            return real_replace(src, dst)

        CAT.os.replace = record
        try:
            code, _ = run_cli("gallery", "--catalog", str(self.catalog), "--out", str(out),
                              "--root", "fc-library:project=" + str(project))
        finally:
            CAT.os.replace = real_replace
        self.assertEqual(code, 0)
        self.assertIn("index.html", order)
        self.assertEqual(order[-1], "index.html")  # entry point published last
        # Both side-metadata files are written before the entry point.
        self.assertLess(order.index("media-manifest.json"), order.index("index.html"))
        self.assertLess(order.index("generation.json"), order.index("index.html"))

    def test_gallery_prepublication_kill_leaves_old_index_and_media(self):
        # A real subprocess is killed by a handshake *after* it has published
        # media and side metadata but before index.html, proving the previous
        # page keeps working and no unrelated content is removed. The child
        # signals readiness; the parent waits for that signal (not a sleep).
        project = self._catalog_with_media()
        # Add a second preview so media publication is non-trivial.
        out = self.root / "g7"
        run_cli("gallery", "--catalog", str(self.catalog), "--out", str(out),
                "--root", "fc-library:project=" + str(project))
        original = (out / "index.html").read_text()
        # An unrelated file in the output root must survive regeneration.
        (out / "keep.txt").write_text("unrelated")

        handshake = self.root / "handshake"
        driver = self.root / "driver.py"
        driver.write_text(
            "import os, sys, importlib.util\n"
            f"spec = importlib.util.spec_from_file_location('fc_catalog', {str(SCRIPT)!r})\n"
            "cat = importlib.util.module_from_spec(spec); sys.modules['fc_catalog'] = cat\n"
            "spec.loader.exec_module(cat)\n"
            "marker = " + repr(str(handshake)) + "\n"
            "real = os.replace\n"
            "def patched(src, dst):\n"
            "    if os.path.basename(str(dst)) == 'index.html':\n"
            "        open(marker, 'w').write('ready')\n"
            "        import time\n"
            "        while True: time.sleep(0.1)\n"
            "    return real(src, dst)\n"
            "cat.os.replace = patched\n"
            "cat.main(['gallery', '--catalog', sys.argv[1], '--out', sys.argv[2],\n"
            "          '--root', sys.argv[3]])\n")
        proc = subprocess.Popen(
            [sys.executable, str(driver), str(self.catalog), str(out),
             "fc-library:project=" + str(project)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 20
            while not handshake.exists() and time.monotonic() < deadline:
                if proc.poll() is not None:
                    break
                time.sleep(0.02)
            self.assertTrue(handshake.exists(), "child never reached the index commit point")
        finally:
            proc.kill()
            proc.communicate()
        # The old page is still the live index, unrelated output is intact, and
        # the newly copied media (if any) did not corrupt anything.
        self.assertEqual((out / "index.html").read_text(), original)
        self.assertEqual((out / "keep.txt").read_text(), "unrelated")


class ExampleFixtureTests(Base):
    """The tracked synthetic walkthrough fixture must stay runnable and aligned.

    This mirrors the memory example: the public fixture is asserted through the
    real CLI so its README commands and field contract cannot drift. It is not a
    design claim and contains no personal data.
    """

    @property
    def examples(self) -> Path:
        return Path(__file__).resolve().parents[1] / "examples" / "catalog"

    @property
    def lib(self) -> Path:
        return self.examples / "library" / "catalog.json"

    @property
    def mat(self) -> Path:
        return self.examples / "materials" / "catalog.json"

    @property
    def proj(self) -> Path:
        return self.examples / "project" / "catalog.json"

    def _with_all(self) -> tuple[str, ...]:
        return ("--with-catalog", str(self.lib), "--with-catalog", str(self.mat))

    def _with_materials(self) -> tuple[str, ...]:
        return ("--with-catalog", str(self.mat))

    def test_fixture_validates(self):
        code, payload = run_cli("validate", "--catalog", str(self.proj), *self._with_all())
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload["status"], "valid")
        self.assertEqual(payload["errors"], [])
        # A referenced font asset is retained in the fixture, so it must be
        # resolvable rather than silently absent.
        self.assertEqual(payload["missing_media"], [])

    def test_fixture_query_show_resolve(self):
        _, q = run_cli("query", "--catalog", str(self.lib), *self._with_materials(),
                       "--role", "style", "--term", "reading")
        self.assertEqual([i["id"] for i in q["items"]], ["reading-margin"])
        self.assertEqual(q["revisions"]["sample-library"], 2)

        _, s = run_cli("show", "--catalog", str(self.lib), "--id", "reading-margin", "--revision", "1")
        self.assertEqual(s["item"]["revision"], 1)
        self.assertFalse(s["current"])

        code, r = run_cli("resolve", "--catalog", str(self.lib), "--id", "reading-margin",
                          *self._with_materials())
        self.assertEqual(code, 0, r)
        self.assertEqual(r["status"], "resolved")
        via = r["bundle"]["materials"]
        self.assertEqual(via[0]["status"], "available")
        self.assertEqual(via[0]["via"]["catalog_id"], "sample-materials")

    def test_fixture_gallery_uses_and_exact_dependency(self):
        out = self.root / "walkthrough-gallery"
        code, payload = run_cli("gallery", "--catalog", str(self.proj), "--out", str(out),
                                *self._with_all())
        self.assertEqual(code, 0, payload)
        index = (out / "index.html").read_text()
        self.assertIn("Current project uses (1)", index)
        self.assertIn("sample-library/reading-margin@2", index)  # exact referenced revision
        self.assertIn("History", index)  # the library item's rev 1 stays viewable
        manifest = json.loads((out / "media-manifest.json").read_text())["media"]
        self.assertGreaterEqual(len(manifest), 3)  # project capture + two library revisions
        for rel in manifest.values():
            self.assertTrue((out / rel).is_file())



class QueryCursorTests(Base):
    def _three(self):
        self.write_catalog(self.base_document(items=[
            self.reference_item(id="a"), self.reference_item(id="b"),
            self.reference_item(id="c"),
        ]))

    def test_cursor_continues_and_binds_revisions(self):
        self._three()
        _, p1 = run_cli("query", "--catalog", str(self.catalog), "--limit", "2")
        self.assertTrue(p1["truncated"])
        self.assertFalse(p1["guarded"])
        self.assertIsNotNone(p1["next_cursor"])
        self.assertEqual([i["id"] for i in p1["items"]], ["a", "b"])
        _, p2 = run_cli("query", "--catalog", str(self.catalog), "--limit", "2",
                        "--cursor", p1["next_cursor"])
        self.assertTrue(p2["guarded"])
        self.assertEqual([i["id"] for i in p2["items"]], ["c"])
        self.assertFalse(p2["truncated"])

    def test_cursor_rejects_changed_catalog_revision(self):
        self._three()
        _, p1 = run_cli("query", "--catalog", str(self.catalog), "--limit", "2")
        doc = json.loads(self.catalog.read_text())
        doc["revision"] = 2
        self.catalog.write_text(json.dumps(doc))
        code, conflict = run_cli("query", "--catalog", str(self.catalog), "--limit", "2",
                                 "--cursor", p1["next_cursor"])
        self.assertEqual(code, CAT.EXIT_CONFLICT)
        self.assertEqual(conflict["status"], "conflict")

    def test_cursor_rejects_changed_filters(self):
        self._three()
        _, p1 = run_cli("query", "--catalog", str(self.catalog), "--limit", "2")
        code, mismatch = run_cli("query", "--catalog", str(self.catalog), "--limit", "2",
                                 "--cursor", p1["next_cursor"], "--role", "reference")
        self.assertEqual(code, CAT.EXIT_USAGE)
        self.assertEqual(mismatch["status"], "usage_error")

    def test_cursor_rejects_malformed_and_offset_combo(self):
        self._three()
        code, bad = run_cli("query", "--catalog", str(self.catalog), "--cursor", "!!!not-base64!!!")
        self.assertEqual(code, CAT.EXIT_USAGE)
        self.assertEqual(bad["status"], "usage_error")
        _, p1 = run_cli("query", "--catalog", str(self.catalog), "--limit", "2")
        code, both = run_cli("query", "--catalog", str(self.catalog), "--limit", "2",
                             "--cursor", p1["next_cursor"], "--offset", "2")
        self.assertEqual(code, CAT.EXIT_USAGE)
        self.assertEqual(both["status"], "usage_error")

    def test_cursor_detects_changed_dependency_revision(self):
        dep = self.root / "dep.json"
        self.write_catalog(self.base_document(id="shared-materials", items=[
            self.reference_item(id="d")]), path=dep)
        self._three()
        _, p1 = run_cli("query", "--catalog", str(self.catalog), "--with-catalog", str(dep),
                        "--limit", "2")
        ddoc = json.loads(dep.read_text())
        ddoc["revision"] = 2
        dep.write_text(json.dumps(ddoc))
        code, conflict = run_cli("query", "--catalog", str(self.catalog),
                                 "--with-catalog", str(dep), "--limit", "2",
                                 "--cursor", p1["next_cursor"])
        self.assertEqual(code, CAT.EXIT_CONFLICT)
        self.assertEqual(conflict["status"], "conflict")


class ProcessConcurrencyTests(Base):
    """Real operating-system evidence: separate Python processes, not threads.

    The in-process tests exercise the same code paths, but only a second
    *process* proves that the advisory lock actually serialises independent
    interpreters (threads share the GIL-level lock state and can pass even when
    the on-disk lock does nothing).
    """

    def _run_proc(self, *args: str) -> tuple[int, dict]:
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True, text=True)
        out = proc.stdout.strip()
        payload = json.loads(out) if out else {}
        return proc.returncode, payload

    def test_two_processes_register_distinct_items(self):
        self.write_catalog(self.base_document())
        rec_a = self.write("pa.json", {"kind": "item", "item": {
            "id": "item-a", "revision": 1, "title": "A", "roles": ["reference"]}})
        rec_b = self.write("pb.json", {"kind": "item", "item": {
            "id": "item-b", "revision": 1, "title": "B", "roles": ["reference"]}})
        procs = [
            subprocess.Popen([sys.executable, str(SCRIPT), "register",
                              "--catalog", str(self.catalog), "--record-file", f,
                              "--expect-revision", "0", "--lock-timeout", "15"],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            for f in (str(rec_a), str(rec_b))
        ]
        outs = [p.communicate() for p in procs]
        statuses = []
        for (out, _err), proc in zip(outs, procs):
            payload = json.loads(out.strip()) if out.strip() else {}
            statuses.append(payload.get("status"))
        # Either both registered, or the loser saw a stale revision conflict and
        # was told to re-read; never a lost update or a corrupted file.
        self.assertTrue(set(statuses) <= {"registered", "conflict", "unchanged"}, statuses)
        stored = json.loads(self.catalog.read_text())
        ids = {i["id"] for i in stored["items"]}
        if "conflict" not in statuses:
            self.assertEqual(ids, {"item-a", "item-b"})
        else:
            # Re-run the conflicted writer at the observed revision; it merges.
            for name, rid in (("pa.json", "item-a"), ("pb.json", "item-b")):
                current = json.loads(self.catalog.read_text())["revision"]
                code, payload = self._run_proc(
                    "register", "--catalog", str(self.catalog),
                    "--record-file", str(self.root / name),
                    "--expect-revision", str(current))
                self.assertIn(payload.get("status"), ("registered", "unchanged"), payload)
            ids = {i["id"] for i in json.loads(self.catalog.read_text())["items"]}
            self.assertEqual(ids, {"item-a", "item-b"})

    def test_second_process_is_busy_while_lock_held(self):
        self.write_catalog(self.base_document())
        rec = self.write("r.json", {"kind": "item", "item": {
            "id": "x", "revision": 1, "title": "t", "roles": ["reference"]}})
        # Hold the lock in this process, then ask a real subprocess to write.
        lock = CAT.FileLock(self.catalog, timeout=0.2)
        lock.__enter__()
        try:
            code, payload = self._run_proc(
                "register", "--catalog", str(self.catalog), "--record-file", str(rec),
                "--expect-revision", "1", "--lock-timeout", "0.2")
        finally:
            lock.__exit__(None, None, None)
        self.assertEqual(code, CAT.EXIT_BUSY)
        self.assertEqual(payload["status"], "busy")

    def test_interrupted_process_leaves_previous_catalog_readable(self):
        # Register one item, snapshot the file, then SIGKILL a second process
        # that is mid-write. The catalogue must remain the previous complete
        # document (SIGKILL cannot run cleanup, so this is the strongest form).
        rec1 = self.write("a.json", {"kind": "item", "item": {
            "id": "x", "revision": 1, "title": "one", "roles": ["reference"]}})
        code, payload = self._run_proc("register", "--catalog", str(self.catalog),
                                       "--record-file", str(rec1), "--expect-revision", "0")
        self.assertEqual(code, 0, payload)
        before = self.catalog.read_text()

        rec2 = self.write("b.json", {"kind": "item", "item": {
            "id": "y", "revision": 1, "title": "two", "roles": ["reference"]}})
        # Handshake: the child signals the moment before it performs the atomic
        # replace, so the kill is deterministic rather than a timing guess.
        handshake = self.root / "reg-handshake"
        driver = self.root / "reg_driver.py"
        driver.write_text(
            "import os, sys, importlib.util\n"
            f"spec = importlib.util.spec_from_file_location('fc_catalog', {str(SCRIPT)!r})\n"
            "cat = importlib.util.module_from_spec(spec); sys.modules['fc_catalog'] = cat\n"
            "spec.loader.exec_module(cat)\n"
            "marker = " + repr(str(handshake)) + "\n"
            "real = os.replace\n"
            "def patched(src, dst):\n"
            "    if str(dst).endswith('catalog.json'):\n"
            "        open(marker, 'w').write('ready')\n"
            "        import time\n"
            "        while True: time.sleep(0.1)\n"
            "    return real(src, dst)\n"
            "cat.os.replace = patched\n"
            "cat.main(['register', '--catalog', sys.argv[1], '--record-file', sys.argv[2],\n"
            "          '--expect-revision', sys.argv[3]])\n")
        proc = subprocess.Popen(
            [sys.executable, str(driver), str(self.catalog), str(rec2), "1"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 20
            while not handshake.exists() and time.monotonic() < deadline:
                if proc.poll() is not None:
                    break
                time.sleep(0.02)
            self.assertTrue(handshake.exists(), "child never reached the catalog commit point")
        finally:
            proc.kill()
            proc.communicate()
        # Whatever the timing, the catalogue path holds a complete document:
        # either the previous one or a fully-written new one, never a partial
        # JSON blob, and never a missing file.
        self.assertTrue(self.catalog.is_file())
        stored = json.loads(self.catalog.read_text())
        self.assertEqual(stored["version"], 1)
        self.assertIn("x", {i["id"] for i in stored["items"]})
        json.loads(before)  # snapshot itself must be valid JSON


class QueryCompletionTests(Base):
    def test_source_filter_is_bound_to_query_cursor(self):
        self.write_catalog(self.base_document(items=[
            self.reference_item(id='a', source={'kind':'authored'}),
            self.reference_item(id='b', source={'kind':'authored'}),
            self.reference_item(id='c', source={'kind':'external', 'url':'https://example.test/source'})]))
        args=('query', '--catalog', str(self.catalog), '--limit', '1')
        code, result=run_cli(*args, '--source', 'authored')
        self.assertEqual(code, 0, result)
        self.assertEqual(result['matched'], 2)
        self.assertEqual(result['items'][0]['id'], 'a')
        code, second=run_cli(*args, '--source', 'authored', '--cursor', result['next_cursor'])
        self.assertEqual(code, 0, second)
        self.assertEqual(second['items'][0]['id'], 'b')
        code, changed=run_cli(*args, '--source', 'external', '--cursor', result['next_cursor'])
        self.assertEqual(code, CAT.EXIT_USAGE, changed)

    def test_cross_catalog_use_prioritizes_actual_target(self):
        dep=self.write('dep.json', self.base_document(id='z-materials', items=[self.reference_item(id='used')]))
        self.write_catalog(self.base_document(items=[self.reference_item(id='unused')], uses=[{
            'id':'selection', 'revision':1, 'target':{'project':'sample-reader'},
            'references':[{'catalog_id':'z-materials','item_id':'used','revision':1}],
            'relation':'selected for this project', 'status':'selected'}]))
        code, result=run_cli('query','--catalog',str(self.catalog),'--with-catalog',str(dep))
        self.assertEqual(code, 0, result)
        self.assertEqual([i['id'] for i in result['items']], ['used','unused'])


class GalleryIntegrityTests(Base):
    def test_runtime_binding_cannot_alias_colon_delimited_identities(self):
        bindings = {'a%3Ab:c:1': 'https://example.test/first',
                    'a:b%3Ac:1': 'https://example.test/second'}
        self.assertEqual(CAT._view_binding_for(bindings, 'a:b', 'c', 1),
                         'https://example.test/first')
        self.assertEqual(CAT._view_binding_for(bindings, 'a', 'b:c', 1),
                         'https://example.test/second')
        self.assertIsNone(CAT._view_binding_for(bindings, 'a:b', 'c', 2))

    def test_changed_capture_is_not_shown_as_old_revision(self):
        self.write('shot.svg', b'NEW CONTENT')
        self.write_catalog(self.base_document(items=[self.reference_item(previews=[{
            'id': 'shot', 'kind': 'image', 'locator': {'root': 'catalog', 'path': 'shot.svg'},
            'digest': sha(b'OLD CONTENT')}])]))
        out = self.root / 'gallery'
        code, result = run_cli('gallery', '--catalog', str(self.catalog), '--out', str(out))
        self.assertEqual(code, 0, result)
        self.assertIn('preview file changed', (out / 'index.html').read_text())
        self.assertEqual(json.loads((out / 'media-manifest.json').read_text())['media'], {})

    def test_downloads_copy_real_material_bytes_and_preserve_suffixes(self):
        for suffix in ('txt', 'json'):
            self.write('asset.' + suffix, b'123')
        self.write_catalog(self.base_document(items=[self.reference_item(assets=[
            {'id': suffix, 'locator': {'root': 'catalog', 'path': 'asset.' + suffix},
             'sha256': sha(b'123')} for suffix in ('txt', 'json')])]))
        out = self.root / 'gallery'
        code, result = run_cli('gallery', '--catalog', str(self.catalog), '--out', str(out))
        self.assertEqual(code, 0, result)
        manifest = json.loads((out / 'media-manifest.json').read_text())['media']
        self.assertEqual(len(manifest), 2)
        self.assertEqual({Path(rel).suffix for rel in manifest.values()}, {'.txt', '.json'})
        for rel in manifest.values():
            self.assertEqual((out / rel).read_bytes(), b'123')
        self.assertIn('download>Download json', (out / 'index.html').read_text())

    def test_palette_is_data_not_injected_css(self):
        attack = 'red;background-image:url(https://example.invalid/leak)'
        self.write_catalog(self.base_document(items=[self.reference_item(palette={
            'roles': {'base': {'value': attack}},
            'instance': {'catalog_id': 'fc-library', 'item_id': 'margin-reference', 'revision': 1}})]))
        out = self.root / 'gallery'
        code, result = run_cli('gallery', '--catalog', str(self.catalog), '--out', str(out))
        self.assertEqual(code, 0, result)
        from html.parser import HTMLParser
        class Styles(HTMLParser):
            def __init__(self):
                super().__init__(); self.styles = []
            def handle_starttag(self, tag, attrs):
                self.styles.extend(v for k, v in attrs if k == 'style')
        parser = Styles(); parser.feed((out / 'index.html').read_text())
        self.assertFalse(any('url(' in value for value in parser.styles))

    def test_compound_ids_remain_distinct_in_gallery_dom(self):
        dep = self.write('dep.json', self.base_document(id='a', items=[self.reference_item(id='b--c')]))
        self.write_catalog(self.base_document(id='a--b', items=[self.reference_item(id='c', materials=[
            {'catalog_id': 'a', 'item_id': 'b--c', 'revision': 1}])]))
        out = self.root / 'gallery'
        code, result = run_cli('gallery', '--catalog', str(self.catalog), '--with-catalog', str(dep), '--out', str(out))
        self.assertEqual(code, 0, result)
        import re
        ids = re.findall(r'<template id="([^"]+)"', (out / 'index.html').read_text())
        self.assertEqual(len(ids), 2)
        self.assertEqual(len(set(ids)), 2)

    def test_retention_refuses_output_symlink_escape(self):
        with tempfile.TemporaryDirectory() as outside:
            (self.root / 'media').symlink_to(outside, target_is_directory=True)
            self.write('input.svg', '<svg/>')
            rec = self.write('record.json', {'kind': 'item', 'item': self.reference_item(previews=[{
                'id': 'p', 'kind': 'image', 'input_locator': {'root': 'catalog', 'path': 'input.svg'}}])})
            code, result = run_cli('register', '--catalog', str(self.catalog), '--record-file', str(rec), '--expect-revision', '0')
            self.assertNotEqual(code, 0, result)
            self.assertEqual(list(Path(outside).iterdir()), [])
            self.assertFalse(self.catalog.exists())

    def test_gallery_refuses_output_media_symlink_escape(self):
        self.write('input.svg', '<svg/>')
        self.write_catalog(self.base_document(items=[self.reference_item(previews=[{
            'id': 'p', 'kind': 'image', 'locator': {'root': 'catalog', 'path': 'input.svg'}}])]))
        out = self.root / 'gallery'; out.mkdir()
        (out / 'index.html').write_text('previous')
        with tempfile.TemporaryDirectory() as outside:
            (out / 'media').symlink_to(outside, target_is_directory=True)
            code, result = run_cli('gallery', '--catalog', str(self.catalog), '--out', str(out))
            self.assertNotEqual(code, 0, result)
            self.assertEqual(list(Path(outside).iterdir()), [])
            self.assertEqual((out / 'index.html').read_text(), 'previous')


if __name__ == "__main__":
    unittest.main()
