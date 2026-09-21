#!/usr/bin/env python3
"""Optional Cloudflare Workers AI + Vectorize memory layer for Frontend Craft.

Imported by ``scripts/fc_memory.py`` (the single canonical CLI). Stdlib only:
JSON config in the operator's authorized root, ``urllib.request`` for REST, no
service framework, no daemon, no persisted credential.

Fixed contract (see ``references/cloudflare-memory.md``):

- Model/geometry are fixed: ``@cf/baai/bge-m3`` / 1024 dims / cosine. The config
  cannot promise an arbitrary model while ``doctor`` hard-checks another.
- Two independent metadata indexes, ``project_key`` and ``surface_key``, each a
  hash of ``namespace`` plus one axis. Default scope is
  ``project_key $in [h(project), h(*)]`` AND ``surface_key $in [h(surface), h(*)]``.
  ``--transfer`` drops the project filter but keeps surface.
- Vector id is ``sha256(namespace + "\x1f" + case_id)`` hex (deterministic, <=64
  bytes). A remote hit is mapped back through a local id map; an unknown id is
  rejected, never coerced to a same-named case.
- ``revision`` covers embedded text AND scope AND model, so a scope or embedded-text
  change triggers a re-sync and a stale cross-scope candidate cannot be returned.
- Vectorize requests carry the native ``namespace`` field; queries filter on it.
- Embeddings send only an allowlist: title/statement/next_action/keywords/limits.
  ``context.md`` and the ``evidence`` field are not sent. Operators review
  allowlisted field contents; field selection does not redact their text.
- Tokens come from ``CLOUDFLARE_API_TOKEN`` or ``wrangler auth token --json``;
  they are never persisted and never echoed (provider messages are not echoed
  verbatim because they may reflect the token).
- ``sync`` is dry-run by default; only ``--apply`` writes. Every accepted
  mutation id is persisted immediately so an interrupted run stays resumable.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

CONFIG_NAME = "cloudflare.json"
SYNC_STATE_NAME = ".fc-sync-state.json"
MODEL = "@cf/baai/bge-m3"
DIMENSIONS = 1024
METRIC = "cosine"
WRANGLER_SPEC = "wrangler@4.135.0"
SYNC_STATE_VERSION = 2

# Vectorize topK limits: returning values or metadata caps topK at 50; returning
# neither caps it at 100. Queries here request returnMetadata="all" (needed for
# local revision/scope validation), so the binding limit is 50.
MAX_TOPK = 50
DEFAULT_TOP_K = 20
EMBED_BATCH = 64
UPSERT_BATCH = 64
DELETE_BATCH = 64
GET_BY_IDS_BATCH = 100

EXIT_REMOTE = 6
EXIT_PENDING = 7

API_BASE = "https://api.cloudflare.com/client/v4"
EMBED_PATH = "/accounts/{account_id}/ai/run/{model}"

# The ONLY case fields ever embedded. Order is the join order; keep it stable.
EMBED_FIELDS = ("title", "statement", "next_action", "keywords", "limits")

# The metadata indexes that must exist before sync (propertyName -> indexType).
# `namespace` is a native Vectorize vector attribute, not a metadata property,
# so it is NOT required as an index. The live API reports indexType as
# ``String`` (capital S) even though the create parameter uses ``string``;
# comparisons are casefolded.
REQUIRED_METADATA_INDEXES = (
    ("project_key", "string"),
    ("surface_key", "string"),
)


def metadata_type_matches(actual: Any, expected: str) -> bool:
    return isinstance(actual, str) and actual.casefold() == expected.casefold()


class CloudError(Exception):
    """A remote or auth failure. Never carries a token in its message."""


class ConfigError(Exception):
    """A malformed ``cloudflare.json`` or invalid target configuration."""


class PendingError(Exception):
    """Mutations are still queued; caller reports ``pending``, not ``ready``."""


# ---------------------------------------------------------------------------
# Hashing / ids / scope keys / revisions
# ---------------------------------------------------------------------------


def digest(value: str) -> str:
    """Full SHA-256 hex (64 chars) of a UTF-8 string."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def remote_id(config: Dict[str, Any], case_id: str) -> str:
    """Deterministic opaque id: sha256(namespace + \\x1f + case_id), 64 hex."""
    return digest(f"{config['namespace']}\x1f{case_id}")


def axis_key(config: Dict[str, Any], axis: str, value: str) -> str:
    """Hash one scope axis with the namespace so names don't leak or truncate."""
    return digest(f"{config['namespace']}\x1f{axis}\x1f{value}")


def project_key(config: Dict[str, Any], project: str) -> str:
    return axis_key(config, "project", project)


def surface_key(config: Dict[str, Any], surface: str) -> str:
    return axis_key(config, "surface", surface)


def embed_text(case: Dict[str, Any]) -> str:
    """Allowlisted embedding text. Never includes evidence, context, or paths."""
    chunks: List[str] = []
    for field in EMBED_FIELDS:
        value = case.get(field)
        if isinstance(value, list):
            value = ", ".join(str(item) for item in value)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            chunks.append(f"{field}: {text}")
    return "\n".join(chunks)


def revision_of(case: Dict[str, Any]) -> str:
    """Content revision over embedded text AND scope AND model.

    Changing scope (or the fixed model/geometry) changes the revision, so a
    scope change triggers a re-sync and an old cross-scope vector cannot be
    returned. Date/basis/outcome changes that alter the embedded text also
    change it; the local record is always the returned truth.
    """
    scope = case.get("scope") or {}
    return digest(
        "rev\x1f"
        + MODEL
        + f"\x1f{DIMENSIONS}\x1f{METRIC}\x1f"
        + str(scope.get("project", ""))
        + "\x1f"
        + str(scope.get("surface", ""))
        + "\x1f"
        + embed_text(case)
    )


def normalize_cases(cases: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {case["id"]: case for case in cases}


def desired_vectors(
    config: Dict[str, Any], cases: List[Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    """Map remote_id -> vector plan for active cases.

    Keys: id, case_id, revision, text, project_key, surface_key, metadata.
    """
    out: Dict[str, Dict[str, Any]] = {}
    for case in cases:
        if case.get("status") != "active":
            continue
        rid = remote_id(config, case["id"])
        scope = case["scope"]
        pk = project_key(config, scope["project"])
        sk = surface_key(config, scope["surface"])
        out[rid] = {
            "id": rid,
            "case_id": case["id"],
            "revision": revision_of(case),
            "text": embed_text(case),
            "project_key": pk,
            "surface_key": sk,
            "metadata": {
                "revision": revision_of(case),
                "project_key": pk,
                "surface_key": sk,
                "updated": case.get("updated", ""),
            },
        }
    return out


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


def load_config(root: Path) -> Dict[str, Any]:
    path = root / CONFIG_NAME
    if not path.exists():
        raise ConfigError(
            f"{CONFIG_NAME} is missing; copy the template from "
            f"references/cloudflare-memory.md into the authorized root"
        )
    if path.is_symlink():
        raise ConfigError(f"{CONFIG_NAME} must not be a symlink")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConfigError(f"{CONFIG_NAME} is not valid JSON: {exc}") from exc
    return _validate_config(document)


def _validate_config(document: Any) -> Dict[str, Any]:
    if not isinstance(document, dict):
        raise ConfigError(f"{CONFIG_NAME} root must be a JSON object")
    version = document.get("version")
    if isinstance(version, bool) or not isinstance(version, int) or version != 1:
        raise ConfigError(f"{CONFIG_NAME}: 'version' must be the JSON integer 1")
    for field in ("account_id", "index_name", "namespace"):
        value = document.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ConfigError(f"{CONFIG_NAME}: '{field}' must be a non-empty string")
    # The model/geometry are fixed; a config that promises anything else is
    # rejected rather than silently disagreeing with doctor/runtime.
    model = document.get("model", MODEL)
    if model != MODEL:
        raise ConfigError(f"{CONFIG_NAME}: 'model' must be {MODEL!r}")
    dimensions = document.get("dimensions", DIMENSIONS)
    if isinstance(dimensions, bool) or dimensions != DIMENSIONS:
        raise ConfigError(f"{CONFIG_NAME}: 'dimensions' must be {DIMENSIONS}")
    metric = document.get("metric", METRIC)
    if metric != METRIC:
        raise ConfigError(f"{CONFIG_NAME}: 'metric' must be {METRIC!r}")
    auth = document.get("auth", "env")
    if auth not in ("env", "wrangler"):
        raise ConfigError(f"{CONFIG_NAME}: 'auth' must be 'env' or 'wrangler'")
    return {
        "version": 1,
        "account_id": document["account_id"].strip(),
        "index_name": document["index_name"].strip(),
        "namespace": document["namespace"].strip(),
        "model": MODEL,
        "dimensions": DIMENSIONS,
        "metric": METRIC,
        "auth": auth,
    }


def target_fingerprint(config: Dict[str, Any]) -> str:
    """Identity of the remote target so a changed config cannot reuse an old
    manifest to delete vectors it never wrote."""
    return digest(
        "\x1f".join(
            [
                "target",
                config["account_id"],
                config["index_name"],
                config["namespace"],
                MODEL,
                str(DIMENSIONS),
                METRIC,
            ]
        )
    )


# ---------------------------------------------------------------------------
# Auth (never persists or echoes the token)
# ---------------------------------------------------------------------------


def resolve_token(config: Dict[str, Any], runner=None) -> str:
    if config.get("auth") == "wrangler":
        return _token_from_wrangler(runner=runner)
    token = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
    if not token:
        raise CloudError(
            "CLOUDFLARE_API_TOKEN is not set (config auth='env'); set it or use "
            "auth='wrangler'"
        )
    return token


def _token_from_wrangler(runner=None) -> str:
    run = runner or (
        lambda: subprocess.run(
            ["npx", "--yes", WRANGLER_SPEC, "auth", "token", "--json"],
            capture_output=True,
            text=True,
            timeout=120,
        )
    )
    try:
        proc = run()
    except (OSError, subprocess.SubprocessError) as exc:
        raise CloudError(f"wrangler auth token failed: {type(exc).__name__}") from exc
    if proc.returncode != 0:
        # Never surface stderr verbatim: it may contain token fragments.
        raise CloudError("wrangler auth token returned a non-zero exit code")
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise CloudError("wrangler auth token did not return JSON") from exc
    token = ""
    if isinstance(payload, dict):
        token = str(payload.get("token", "") or "").strip()
    if not token:
        raise CloudError("wrangler auth token JSON had no 'token' field")
    return token


# ---------------------------------------------------------------------------
# HTTP transport (injectable for tests)
# ---------------------------------------------------------------------------


class Transport:
    """Thin urllib wrapper. ``sender`` is injectable so tests never hit the net."""

    def __init__(self, account_id: str, token: str, sender=None):
        self.account_id = account_id
        self._token = token
        self._sender = sender

    def _request(
        self, method: str, url: str, body: Optional[bytes], headers: Dict[str, str]
    ) -> Tuple[int, bytes]:
        if self._sender is not None:
            return self._sender(method, url, body, headers)
        req = urllib.request.Request(url, data=body, method=method)
        for key, value in headers.items():
            req.add_header(key, value)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as exc:
            # A provider message body may reflect the token; never re-raise it.
            return exc.code, b""
        except urllib.error.URLError as exc:
            raise CloudError(
                f"network error contacting Cloudflare: {type(exc.reason).__name__}"
            ) from exc

    def json_call(self, method: str, path: str, payload: Any) -> Dict[str, Any]:
        url = API_BASE + path
        headers = {"Authorization": f"Bearer {self._token}"}
        body: Optional[bytes] = None
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        status, raw = self._request(method, url, body, headers)
        return _decode(status, raw)

    def raw_call(
        self, method: str, path: str, body: bytes, content_type: str
    ) -> Dict[str, Any]:
        url = API_BASE + path
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": content_type,
        }
        status, raw = self._request(method, url, body, headers)
        return _decode(status, raw)


def _decode(status: int, raw: bytes) -> Dict[str, Any]:
    if not raw:
        raise CloudError(
            f"Cloudflare returned an empty response (HTTP {status})"
        )
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise CloudError(f"Cloudflare returned non-JSON (HTTP {status})")
    if not isinstance(payload, dict):
        raise CloudError(f"Cloudflare returned an unexpected JSON shape (HTTP {status})")
    if status >= 400 or payload.get("success") is False:
        # Do not echo provider text; it may reflect the token.
        codes = payload.get("errors") or []
        code = codes[0].get("code") if codes and isinstance(codes[0], dict) else None
        raise CloudError(
            f"Cloudflare API error (HTTP {status}, code {code if code is not None else 'unknown'})"
        )
    return payload


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------


def embed_texts(transport: Transport, texts: List[str]) -> List[List[float]]:
    """POST /ai/run/<model> with ``{"text": [...]}``; validate 1024-dim shape."""
    if not texts:
        return []
    path = EMBED_PATH.format(account_id=transport.account_id, model=MODEL)
    payload = transport.json_call("POST", path, {"text": texts})
    result = payload.get("result") or {}
    data = result.get("data")
    if not isinstance(data, list) or len(data) != len(texts):
        raise CloudError(
            f"embedding response shape mismatch: expected {len(texts)} rows"
        )
    for row in data:
        if not isinstance(row, list) or len(row) != DIMENSIONS:
            raise CloudError(
                f"embedding row is not {DIMENSIONS}-dimensional; refusing to send"
            )
    return data


def check_vector(vector: List[float]) -> None:
    if not isinstance(vector, list) or len(vector) != DIMENSIONS:
        raise CloudError(f"query vector must be {DIMENSIONS}-dimensional")


# ---------------------------------------------------------------------------
# Vectorize operations
# ---------------------------------------------------------------------------


def _index_path(config: Dict[str, Any], *suffix: str) -> str:
    parts = [
        "accounts",
        config["account_id"],
        "vectorize",
        "v2",
        "indexes",
        config["index_name"],
    ]
    parts.extend(suffix)
    return "/" + "/".join(parts)


def build_ndjson(vectors: List[Dict[str, Any]]) -> bytes:
    """Newline-delimited JSON for the upsert endpoint, using the native
    Vectorize ``namespace`` field plus metadata."""
    lines = []
    for vector in vectors:
        lines.append(
            json.dumps(
                {
                    "id": vector["id"],
                    "values": vector["values"],
                    "namespace": vector["namespace"],
                    "metadata": vector["metadata"],
                },
                ensure_ascii=False,
            )
        )
    return ("\n".join(lines) + "\n").encode("utf-8")


def upsert_vectors(
    transport: Transport, config: Dict[str, Any], vectors: List[Dict[str, Any]]
) -> Dict[str, Any]:
    if not vectors:
        return {"success": True, "result": {"mutationId": None}}
    body = build_ndjson(vectors)
    return transport.raw_call(
        "POST", _index_path(config, "upsert"), body, "application/x-ndjson"
    )


def delete_by_ids(
    transport: Transport, config: Dict[str, Any], ids: List[str]
) -> Dict[str, Any]:
    if not ids:
        return {"success": True, "result": {"mutationId": None}}
    return transport.json_call(
        "POST", _index_path(config, "delete_by_ids"), {"ids": ids}
    )


def get_index_info(transport: Transport, config: Dict[str, Any]) -> Dict[str, Any]:
    """GET .../indexes/{index}/info -> result {dimensions, vectorCount,
    processedUpToDatetime, processedUpToMutation}. Not the index config."""
    return transport.json_call("GET", _index_path(config, "info"), None)


def get_index_config(transport: Transport, config: Dict[str, Any]) -> Dict[str, Any]:
    """GET .../indexes/{index} -> ``result`` with keys ``created_on``,
    ``modified_on``, ``name``, ``description`` and ``config``, where
    ``result.config = {dimensions, metric}``.

    Distinct from ``/info``; used to confirm the remote geometry/metric.
    Returns the whole ``result`` dict (callers read ``result["config"]``).
    """
    payload = transport.json_call("GET", _index_path(config), None)
    result = payload.get("result")
    return result if isinstance(result, dict) else {}


def get_by_ids(
    transport: Transport, config: Dict[str, Any], ids: List[str]
) -> List[Dict[str, Any]]:
    """POST .../indexes/{index}/get_by_ids -> result is a LIST of vectors.

    Returns the raw list (possibly empty). A non-list ``result`` is an explicit
    remote error: treating it as "all requested ids absent" would let a
    malformed response falsely verify deletions. Batched within the cap.
    """
    if not ids:
        return []
    payload = transport.json_call(
        "POST", _index_path(config, "get_by_ids"), {"ids": ids}
    )
    result = payload.get("result")
    if not isinstance(result, list):
        raise CloudError(
            "get_by_ids returned a non-list result; refusing to infer absence"
        )
    return result

def list_metadata_indexes(
    transport: Transport, config: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """GET .../metadata_index/list -> result.metadataIndexes[...]."""
    payload = transport.json_call(
        "GET", _index_path(config, "metadata_index", "list"), None
    )
    result = payload.get("result") or {}
    indexes = result.get("metadataIndexes")
    return indexes if isinstance(indexes, list) else []


def query_vectors(
    transport: Transport,
    config: Dict[str, Any],
    vector: List[float],
    project_keys: List[str],
    surface_keys: List[str],
    top_k: int,
) -> Dict[str, Any]:
    """Query restricted by namespace AND project/surface filters.

    ``topK`` is capped at MAX_TOPK because ``returnMetadata="all"`` is bounded
    by the platform's metadata-returning limit (50), which is lower than the
    100 cap that applies only when neither values nor metadata are returned.
    """
    check_vector(vector)
    capped = max(1, min(int(top_k), MAX_TOPK))
    payload: Dict[str, Any] = {
        "namespace": config["namespace"],
        "vector": vector,
        "topK": capped,
        "returnValues": False,
        "returnMetadata": "all",
    }
    filters: Dict[str, Any] = {"surface_key": {"$in": surface_keys}}
    if project_keys:
        filters["project_key"] = {"$in": project_keys}
    payload["filter"] = filters
    return transport.json_call("POST", _index_path(config, "query"), payload)


# ---------------------------------------------------------------------------
# Sync manifest (atomic, resumable, idempotent)
# ---------------------------------------------------------------------------


def load_manifest(root: Path) -> Dict[str, Any]:
    path = root / SYNC_STATE_NAME
    if not os.path.lexists(path):
        return {
            "version": SYNC_STATE_VERSION,
            "target": None,
            "vectors": {},
            "pending_mutations": [],
            "pending_deletions": [],
        }
    if path.is_symlink():
        raise ConfigError(f"{SYNC_STATE_NAME} must not be a symlink")
    if not path.is_file():
        raise ConfigError(f"{SYNC_STATE_NAME} is not a regular file")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConfigError(f"{SYNC_STATE_NAME} is not valid JSON: {exc}") from exc
    if not isinstance(document, dict) or document.get("version") != SYNC_STATE_VERSION:
        raise ConfigError(
            f"{SYNC_STATE_NAME}: unsupported or missing version "
            f"(expected {SYNC_STATE_VERSION})"
        )
    document.setdefault("vectors", {})
    document.setdefault("target", None)
    document.setdefault("pending_mutations", [])
    document.setdefault("pending_deletions", [])
    return document


def save_manifest_atomic(root: Path, document: Dict[str, Any]) -> None:
    path = root / SYNC_STATE_NAME
    if os.path.lexists(path) and os.path.islink(path):
        raise ConfigError(f"{SYNC_STATE_NAME} must not be a symlink")
    tmp = path.with_suffix(path.suffix + ".tmp")
    if os.path.lexists(tmp) and os.path.islink(tmp):
        # The temp path must be a real file we replace, not a symlink an
        # attacker could redirect the atomic write through.
        raise ConfigError(f"{tmp.name} must not be a symlink")
    tmp.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    os.replace(tmp, path)


def plan_sync(
    config: Dict[str, Any],
    cases: List[Dict[str, Any]],
    manifest: Dict[str, Any],
) -> Dict[str, Any]:
    """Compute the exact uploads and deletions for the current catalog.

    A manifest written for a different target is refused rather than reused, so
    a changed config can never delete vectors this catalog did not write.
    """
    fingerprint = target_fingerprint(config)
    manifest_target = manifest.get("target")
    if manifest_target is not None and manifest_target != fingerprint:
        raise ConfigError(
            "sync manifest belongs to a different target "
            "(account/index/namespace/model changed); remove "
            f"{SYNC_STATE_NAME} deliberately after confirming the new target"
        )
    manifest_vectors = manifest.get("vectors") or {}
    desired = desired_vectors(config, cases)

    uploads: List[Dict[str, Any]] = []
    for rid, vector in desired.items():
        previous = manifest_vectors.get(rid)
        if not previous or previous.get("revision") != vector["revision"]:
            uploads.append(vector)

    deletions: List[str] = []
    for rid in manifest_vectors:
        if rid not in desired:
            deletions.append(rid)

    return {
        "fingerprint": fingerprint,
        "uploads": uploads,
        "deletions": sorted(deletions),
        "active_count": len(desired),
        "manifest_count": len(manifest_vectors),
    }


def summarize_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "target_fingerprint": plan["fingerprint"],
        "active_remote_records": plan["active_count"],
        "manifest_records": plan["manifest_count"],
        "uploads": [
            {
                "remote_id": vector["id"],
                "fields": list(EMBED_FIELDS),
                "revision": vector["revision"],
            }
            for vector in plan["uploads"]
        ],
        "deletions": plan["deletions"],
        "upload_count": len(plan["uploads"]),
        "delete_count": len(plan["deletions"]),
    }


def require_metadata_ready(transport: Transport, config: Dict[str, Any]) -> None:
    """Refuse to sync before the required metadata indexes exist.

    Records upserted before the indexes exist cannot be scope-filtered.
    ``indexType`` is compared case-insensitively (the API returns ``String``).
    """
    present = {
        item.get("propertyName"): item.get("indexType")
        for item in list_metadata_indexes(transport, config)
        if isinstance(item, dict)
    }
    missing = [
        name
        for name, kind in REQUIRED_METADATA_INDEXES
        if not metadata_type_matches(present.get(name), kind)
    ]
    if missing:
        raise CloudError(
            "metadata indexes missing before sync: " + ", ".join(missing)
        )


def _desired_uploads(plan: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """remote_id -> expected record for the plan's uploads."""
    desired: Dict[str, Dict[str, Any]] = {}
    for vector in plan["uploads"]:
        desired[vector["id"]] = {
            "revision": vector["revision"],
            "project_key": vector["project_key"],
            "surface_key": vector["surface_key"],
            "updated": vector["metadata"]["updated"],
        }
    return desired


def _set_pending(
    manifest: Dict[str, Any],
    uploads: Dict[str, Dict[str, Any]],
    deletions: List[str],
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Return the pending receipts/deletions to persist, keyed by latest op.

    Existing pending expectations are replaced by the accepted batch's
    expectation for the same id (new revision wins), dropped when the id is now
    deleted, and preserved for ids the batch does not mention. Pending deletions
    are dropped when the id is desired present again. This keeps the manifest
    describing the latest desired operation per owned id.
    """
    receipts: List[Dict[str, Any]] = []
    merged: Dict[str, Dict[str, Any]] = {}
    for receipt in manifest.get("pending_mutations") or []:
        for rid, record in (receipt.get("expected") or {}).items():
            merged[rid] = record
    for rid, record in uploads.items():
        merged[rid] = record
    for rid in deletions:
        merged.pop(rid, None)
    if merged:
        receipts.append(
            {
                "mutation_ids": [
                    mid
                    for receipt in (manifest.get("pending_mutations") or [])
                    for mid in (receipt.get("mutation_ids") or [])
                ],
                "expected": merged,
            }
        )
    pending_deletions = [
        rid
        for rid in (manifest.get("pending_deletions") or [])
        if rid not in uploads
    ]
    for rid in deletions:
        if rid not in pending_deletions:
            pending_deletions.append(rid)
    return receipts, sorted(pending_deletions)


def _persist(
    root: Path,
    fingerprint: str,
    applied: Dict[str, Dict[str, Any]],
    pending_receipts: List[Dict[str, Any]],
    pending_deletions: List[str],
) -> Dict[str, Any]:
    manifest = load_manifest(root)
    manifest["target"] = fingerprint
    vectors = manifest.setdefault("vectors", {})
    for rid, record in applied.items():
        vectors[rid] = record
    for rid in pending_deletions:
        vectors.pop(rid, None)
    manifest["pending_mutations"] = pending_receipts
    manifest["pending_deletions"] = pending_deletions
    save_manifest_atomic(root, manifest)
    return manifest


def _readback_by_id(
    transport: Transport, config: Dict[str, Any], ids: List[str]
) -> Dict[str, Dict[str, Any]]:
    """Read vectors back by id, batched within the platform cap."""
    found: Dict[str, Dict[str, Any]] = {}
    for start in range(0, len(ids), GET_BY_IDS_BATCH):
        for vector in get_by_ids(transport, config, ids[start : start + GET_BY_IDS_BATCH]):
            if isinstance(vector, dict) and vector.get("id") is not None:
                found[str(vector["id"])] = vector
    return found


def verify_pending(
    transport: Transport, config: Dict[str, Any], root: Path
) -> Dict[str, Any]:
    """The ONE canonical pending-verification path (readback evidence).

    A pending upload clears only when ``get_by_ids`` returns the vector with OUR
    namespace, the current revision, and the expected scope keys; a pending
    deletion clears only when the id is absent. The shared
    ``processedUpToMutation`` pointer is never used as evidence (another catalog
    namespace can advance it). A missing receipt is never treated as ready.
    Refuses to verify against a different target. ``sync --wait`` uses this same
    rule with a bounded retry.
    """
    manifest = load_manifest(root)
    fingerprint = target_fingerprint(config)
    if manifest.get("target") not in (None, fingerprint):
        raise ConfigError(
            "sync manifest belongs to a different target; refusing to verify or "
            "clear pending state against another target"
        )

    receipts: List[Dict[str, Any]] = list(manifest.get("pending_mutations") or [])
    deletions: List[str] = list(manifest.get("pending_deletions") or [])
    if not receipts and not deletions:
        return {"status": "none", "pending": [], "verified_uploads": [],
                "verified_deletions": [], "unverified": []}

    expected: Dict[str, Dict[str, Any]] = {}
    for receipt in receipts:
        for rid, record in (receipt.get("expected") or {}).items():
            expected[rid] = record

    found = _readback_by_id(transport, config, sorted(expected) + sorted(deletions))

    verified_uploads: List[str] = []
    unverified: List[Dict[str, Any]] = []
    for rid, record in expected.items():
        vector = found.get(rid)
        if vector is None:
            unverified.append({"id": rid, "reason": "not_read_back"})
            continue
        if vector.get("namespace") != config["namespace"]:
            unverified.append({"id": rid, "reason": "wrong_namespace"})
            continue
        metadata = vector.get("metadata") or {}
        if metadata.get("revision") != record.get("revision"):
            unverified.append({"id": rid, "reason": "wrong_revision"})
            continue
        if (
            record.get("project_key") is not None
            and metadata.get("project_key") != record.get("project_key")
        ):
            unverified.append({"id": rid, "reason": "wrong_project_key"})
            continue
        if (
            record.get("surface_key") is not None
            and metadata.get("surface_key") != record.get("surface_key")
        ):
            unverified.append({"id": rid, "reason": "wrong_surface_key"})
            continue
        verified_uploads.append(rid)

    verified_deletions: List[str] = []
    for rid in deletions:
        if rid in found:
            unverified.append({"id": rid, "reason": "delete_still_present"})
        else:
            verified_deletions.append(rid)

    upload_unresolved = any(
        item["reason"] in ("not_read_back", "wrong_namespace", "wrong_revision",
                           "wrong_project_key", "wrong_surface_key")
        for item in unverified
    )
    delete_unresolved = any(
        item["reason"] == "delete_still_present" for item in unverified
    )
    changed = False
    if not upload_unresolved and receipts:
        manifest["pending_mutations"] = []
        changed = True
    if not delete_unresolved and deletions:
        manifest["pending_deletions"] = []
        changed = True
    if changed:
        save_manifest_atomic(root, manifest)

    return {
        "status": "ready" if not unverified else "pending",
        "pending": [rid for rid in expected if rid not in verified_uploads]
        + [rid for rid in deletions if rid not in verified_deletions],
        "verified_uploads": verified_uploads,
        "verified_deletions": verified_deletions,
        "unverified": unverified,
        "note": "local write/delete state only; query recall quality is observed "
                "by an actual query, not claimed here",
    }


def wait_for_pending(
    transport: Transport,
    config: Dict[str, Any],
    root: Path,
    *,
    attempts: int = 6,
    interval: float = 5.0,
    sleeper=None,
) -> Dict[str, Any]:
    """Bounded resume loop over the canonical readback verification.

    Identical evidence rule to ``sync --verify``; it only retries. Raises
    ``PendingError`` if still pending after the bound, leaving state persisted.
    """
    sleep = sleeper or time.sleep
    status: Dict[str, Any] = {"status": "none"}
    for attempt in range(attempts):
        status = verify_pending(transport, config, root)
        if status["status"] in ("none", "ready"):
            return status
        if attempt < attempts - 1:
            sleep(interval)
    raise PendingError(
        "pending writes still unverified after bounded checks; state is "
        "persisted and can be re-checked with `sync --verify`"
    )


def apply_sync(
    transport: Transport,
    config: Dict[str, Any],
    root: Path,
    plan: Dict[str, Any],
    *,
    wait: bool = False,
    attempts: int = 6,
    interval: float = 5.0,
    sleeper=None,
) -> Dict[str, Any]:
    """Check metadata readiness, embed, upsert/delete, persist each acceptance.

    The manifest's pending state always describes the LATEST desired operation
    per owned id: an accepted new revision or deletion replaces an earlier
    pending upload, and a re-added id clears an obsolete pending deletion, so a
    removed old vector is never demanded forever. ``--wait`` uses the canonical
    readback verification, not the shared mutation pointer. A partial failure
    reports what was actually applied (never applied:false after remote writes).
    """
    require_metadata_ready(transport, config)

    uploads = plan["uploads"]
    deletions = plan["deletions"]
    fingerprint = plan["fingerprint"]

    texts = [vector["text"] for vector in uploads]
    values: List[List[float]] = []
    for start in range(0, len(texts), EMBED_BATCH):
        values.extend(embed_texts(transport, texts[start : start + EMBED_BATCH]))
    for vector, embedding in zip(uploads, values):
        vector["values"] = embedding
        vector["namespace"] = config["namespace"]

    desired_uploads = _desired_uploads(plan)
    manifest = load_manifest(root)
    pending_receipts = list(manifest.get("pending_mutations") or [])
    pending_deletions = list(manifest.get("pending_deletions") or [])
    result: Dict[str, Any] = {
        "applied": False,
        "uploaded": [],
        "deleted": [],
        "mutation_ids": [],
        "mutation_state": "pending" if pending_receipts or pending_deletions else "ready",
    }

    def record_accepted(applied: Dict[str, Dict[str, Any]], removed: List[str],
                        mutation_id: Optional[str]) -> None:
        nonlocal pending_receipts, pending_deletions
        current = load_manifest(root)
        pending_receipts, pending_deletions = _set_pending(current, applied, removed)
        if mutation_id:
            result["mutation_ids"].append(mutation_id)
            if pending_receipts:
                pending_receipts[0]["mutation_ids"].append(mutation_id)
        _persist(root, fingerprint, applied, pending_receipts, pending_deletions)

    # Only acknowledged batches enter the accepted-vector manifest. Failed or
    # unattempted batches remain in the next plan; pre-marking the whole plan
    # would turn retries into a no-op and leave pending records unrecoverable.
    for start in range(0, len(uploads), UPSERT_BATCH):
        chunk = uploads[start : start + UPSERT_BATCH]
        response = upsert_vectors(transport, config, chunk)
        mutation_id = (response.get("result") or {}).get("mutationId")
        accepted = {vector["id"]: desired_uploads[vector["id"]] for vector in chunk}
        record_accepted(accepted, [], mutation_id)
        result["uploaded"].extend(accepted)

    for start in range(0, len(deletions), DELETE_BATCH):
        chunk = deletions[start : start + DELETE_BATCH]
        response = delete_by_ids(transport, config, chunk)
        mutation_id = (response.get("result") or {}).get("mutationId")
        record_accepted({}, chunk, mutation_id)
        result["deleted"].extend(chunk)

    result["applied"] = bool(result["uploaded"] or result["deleted"])

    if wait and (pending_receipts or pending_deletions):
        status = wait_for_pending(
            transport, config, root,
            attempts=attempts, interval=interval, sleeper=sleeper,
        )
        result["mutation_state"] = status["status"]
        result["verified_uploads"] = status.get("verified_uploads", [])
        result["verified_deletions"] = status.get("verified_deletions", [])
        result["unverified"] = status.get("unverified", [])
    else:
        result["mutation_state"] = (
            "ready" if not pending_receipts and not pending_deletions else "pending"
        )
    return result

# ---------------------------------------------------------------------------
# Semantic query -> canonical record resolution
# ---------------------------------------------------------------------------


def scope_filter_keys(
    config: Dict[str, Any], project: str, surface: str, *, transfer: bool
) -> Tuple[List[str], List[str]]:
    """Return (project_keys, surface_keys) for the requested scope.

    Default: project_key in [h(project), h(*)] and surface_key in [h(surface),
    h(*)]. A `*` request axis selects only the global value. With ``transfer``
    the project axis is dropped so other projects' mechanism cases can match,
    while the surface axis is preserved.
    """
    if project == "*":
        projects = [project_key(config, "*")]
    else:
        projects = [project_key(config, project), project_key(config, "*")]
    if surface == "*":
        surfaces = [surface_key(config, "*")]
    else:
        surfaces = [surface_key(config, surface), surface_key(config, "*")]
    if transfer:
        projects = []
    return projects, surfaces


def local_scope_ok(
    case: Dict[str, Any], project: str, surface: str, *, transfer: bool
) -> bool:
    """Local re-check; never trust the remote filter alone."""
    scope = case.get("scope") or {}
    surface_ok = scope.get("surface") in ("*", surface) if surface != "*" else scope.get("surface") == "*"
    if not surface_ok:
        return False
    if transfer:
        return True
    project_ok = scope.get("project") in ("*", project) if project != "*" else scope.get("project") == "*"
    return project_ok


def resolve_hits(
    config: Dict[str, Any],
    hits: List[Dict[str, Any]],
    cases_by_id: Dict[str, Dict[str, Any]],
    reverse_ids: Dict[str, str],
    *,
    project: str,
    surface: str,
    transfer: bool = False,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Map Vectorize hits back to canonical CURRENT local records via the local
    id map. A hit whose id is unknown locally is rejected (never coerced to a
    same-named case). Stale revision / wrong scope / inactive are rejected.
    """
    accepted: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    for hit in hits:
        rid = str(hit.get("id", ""))
        case_id = reverse_ids.get(rid)
        if case_id is None:
            rejected.append({"remote_id": rid, "reason": "unknown_remote_id"})
            continue
        case = cases_by_id.get(case_id)
        if case is None:
            rejected.append({"remote_id": rid, "reason": "missing_local_record"})
            continue
        if case.get("status") != "active":
            rejected.append({"remote_id": rid, "reason": f"status:{case.get('status')}"})
            continue
        if revision_of(case) != (hit.get("metadata") or {}).get("revision"):
            rejected.append({"remote_id": rid, "reason": "stale_revision"})
            continue
        if not local_scope_ok(case, project, surface, transfer=transfer):
            rejected.append({"remote_id": rid, "reason": "out_of_scope"})
            continue
        entry = {"case": case, "score": hit.get("score"), "matched_terms": []}
        if transfer:
            entry["analogy"] = case["scope"]["project"] not in ("*", project)
            entry["current_scope"] = {
                "project": case["scope"]["project"],
                "surface": case["scope"]["surface"],
            }
        accepted.append(entry)
    return accepted, rejected


def reverse_id_map(config: Dict[str, Any], cases: List[Dict[str, Any]]) -> Dict[str, str]:
    """remote_id -> case_id, derived only from locally known cases."""
    return {remote_id(config, case["id"]): case["id"] for case in cases}
