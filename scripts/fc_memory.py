#!/usr/bin/env python3
"""Frontend Craft design-record CLI: local record store plus optional Cloudflare
semantic retrieval.

Frontend Craft keeps two separate files inside one explicitly authorized root:

- ``context.md``: the small, human-maintained current aims-and-boundaries record.
  Every query returns it whole; it is never trimmed by terms, scope, or
  ``--limit``.
- ``cases.json``: a growing, human-reviewed ledger of reusable experience cases.

Verb scope:

- ``query`` / ``show`` / ``validate`` are read-only and never modify records.
- ``init`` creates the first records if absent and never overwrites.
- ``sync``/``doctor`` are network verbs; ``sync`` is dry-run unless ``--apply``.

``query --term`` is lexical (casefolded substring) and works fully offline;
``query --query`` is the optional Cloudflare Workers AI + Vectorize semantic
path. A lexical miss reports ``no_match`` rather than guessing, and a semantic
remote/auth failure is reported as an error, never silently downgraded to a
lexical result. Selection is candidate evidence for an agent to judge, not an
instruction authority. Records stay local; the cloud layer stores vectors and
opaque scope/revision metadata only. See ``references/memory-operations.md`` and
``references/cloudflare-memory.md``.

The ``--root`` is the caller-authorized directory; this is not an OS sandbox.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:  # Support both direct CLI use and path-based module loading.
    import fc_cloudflare as fccloud
except ImportError:  # pragma: no cover - import path bootstrap
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import fc_cloudflare as fccloud

SUPPORTED_VERSION = 1
CONTEXT_NAME = "context.md"
CASES_NAME = "cases.json"
DEFAULT_LIMIT = 8

STATUSES = ("active", "superseded", "retired")
BASES = ("explicit-feedback", "observed-result", "hypothesis", "temporary-compromise")
OUTCOMES = ("accepted", "rejected", "mixed", "unknown")

EXIT_OK = 0
EXIT_NOT_FOUND = 3
EXIT_MISSING = 4
EXIT_INVALID = 5
EXIT_REMOTE = 6
EXIT_PENDING = 7
EXIT_USAGE = 2


class DataError(Exception):
    """A malformed or invalid input file."""


class InvalidError(DataError):
    """The store exists but does not satisfy the contract."""


class MissingError(Exception):
    """A required file is absent."""


class UsageError(Exception):
    """An invalid command-line argument combination."""


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str):  # pragma: no cover - exercised via CLI
        self.print_usage(sys.stderr)
        self.exit(EXIT_USAGE, f"{self.prog}: error: {message}\n")


# ---------------------------------------------------------------------------
# File loading (read-only, no symlink following, no recursion)
# ---------------------------------------------------------------------------


def _resolve_root(root_arg: str) -> Path:
    root = Path(root_arg)
    if not os.path.lexists(root):
        raise MissingError(f"root does not exist: {root}")
    if not root.is_dir():
        raise InvalidError(f"root is not a directory: {root}")
    return root


def load_context(root: Path) -> Dict[str, Any]:
    """Read ``context.md`` whole. Returns availability plus text or an error."""
    path = root / CONTEXT_NAME
    if not os.path.lexists(path):
        return {"available": False, "status": "missing", "path": str(path), "text": None}
    if path.is_symlink():
        raise InvalidError(f"{CONTEXT_NAME} must not be a symlink")
    if not path.is_file():
        raise InvalidError(f"{CONTEXT_NAME} is not a regular file")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise MissingError(f"cannot read {CONTEXT_NAME}: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise InvalidError(f"{CONTEXT_NAME} is not valid UTF-8: {exc}") from exc
    return {"available": True, "status": "available", "path": str(path), "text": text}


def load_cases(root: Path) -> Tuple[str, List[Dict[str, Any]]]:
    """Read and structurally validate ``cases.json``. Returns (path, records)."""
    path = root / CASES_NAME
    if not os.path.lexists(path):
        raise MissingError(f"{CASES_NAME} is missing")
    if path.is_symlink():
        raise InvalidError(f"{CASES_NAME} must not be a symlink")
    if not path.is_file():
        raise InvalidError(f"{CASES_NAME} is not a regular file")
    try:
        raw_bytes = path.read_bytes()
    except OSError as exc:
        raise MissingError(f"cannot read {CASES_NAME}: {exc}") from exc
    try:
        raw = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise InvalidError(f"{CASES_NAME} is not valid UTF-8: {exc}") from exc
    try:
        document = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise InvalidError(f"{CASES_NAME} is not valid JSON: {exc}") from exc
    return str(path), validate_case_document(document)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _require_str(container: Dict[str, Any], field: str, where: str) -> str:
    value = container.get(field)
    if not isinstance(value, str) or not value.strip():
        raise InvalidError(f"{where}: '{field}' must be a non-empty string")
    return value


def _require_str_list(container: Dict[str, Any], field: str, where: str) -> List[str]:
    value = container.get(field)
    if not isinstance(value, list) or not value:
        raise InvalidError(f"{where}: '{field}' must be a non-empty list of strings")
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise InvalidError(f"{where}: '{field}' entries must be non-empty strings")
    return value


def _validate_updated(value: Any, where: str) -> str:
    text = _require_str({"updated": value}, "updated", where)
    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise InvalidError(
            f"{where}: 'updated' must be an ISO YYYY-MM-DD date ({exc})"
        ) from exc
    if parsed.isoformat() != text:
        raise InvalidError(f"{where}: 'updated' must be in canonical YYYY-MM-DD form")
    return text


def _validate_scope(scope: Any, where: str) -> Dict[str, str]:
    if not isinstance(scope, dict):
        raise InvalidError(f"{where}: 'scope' must be an object")
    extra = set(scope) - {"project", "surface"}
    if extra:
        raise InvalidError(f"{where}: 'scope' has unknown keys: {sorted(extra)}")
    for axis in ("project", "surface"):
        value = scope.get(axis)
        if not isinstance(value, str) or not value.strip():
            raise InvalidError(f"{where}: 'scope.{axis}' must be a non-empty string")
    return {"project": scope["project"], "surface": scope["surface"]}


def _validate_case(case: Any, index: int, seen_ids: set) -> Dict[str, Any]:
    where = f"cases[{index}]"
    if not isinstance(case, dict):
        raise InvalidError(f"{where}: case must be an object")
    case_id = case.get("id")
    if not isinstance(case_id, str) or not case_id.strip():
        raise InvalidError(f"{where}: 'id' must be a non-empty string")
    if case_id in seen_ids:
        raise InvalidError(f"{where}: duplicate id '{case_id}'")
    seen_ids.add(case_id)
    where = f"case '{case_id}'"

    for field in ("title", "statement", "next_action", "limits"):
        _require_str(case, field, where)

    _validate_updated(case.get("updated"), where)

    _validate_scope(case.get("scope"), where)

    if case.get("status") not in STATUSES:
        raise InvalidError(f"{where}: 'status' must be one of {list(STATUSES)}")
    if case.get("basis") not in BASES:
        raise InvalidError(f"{where}: 'basis' must be one of {list(BASES)}")
    if case.get("outcome") not in OUTCOMES:
        raise InvalidError(f"{where}: 'outcome' must be one of {list(OUTCOMES)}")

    _require_str_list(case, "evidence", where)
    _require_str_list(case, "keywords", where)
    return dict(case)


def _validate_supersession(cases: List[Dict[str, Any]]) -> None:
    index = {case["id"]: case for case in cases}
    for case in cases:
        ref = case.get("superseded_by")
        where = f"case '{case['id']}'"
        if case["status"] == "superseded":
            if ref is None:
                raise InvalidError(
                    f"{where}: status 'superseded' requires a 'superseded_by' id"
                )
        elif ref is not None:
            raise InvalidError(
                f"{where}: 'superseded_by' is only valid when status is 'superseded'"
            )
        else:
            continue
        if not isinstance(ref, str) or not ref.strip():
            raise InvalidError(f"{where}: 'superseded_by' must be a non-empty string")
        if ref == case["id"]:
            raise InvalidError(f"{where}: 'superseded_by' must not point at itself")
        if ref not in index:
            raise InvalidError(f"{where}: 'superseded_by' -> '{ref}' is not in this store")
        if case["scope"] != index[ref]["scope"]:
            raise InvalidError(
                f"{where}: 'superseded_by' -> '{ref}' must share the same scope "
                f"(a different scope is a coexisting case, not a global supersession)"
            )
    _validate_supersession_acyclic(cases, index)


def _validate_supersession_acyclic(
    cases: List[Dict[str, Any]], index: Dict[str, Dict[str, Any]]
) -> None:
    """Iterative cycle check; each node is walked once across the whole check.

    A ``completed`` set records nodes whose chain is already known to terminate,
    so a long linear history is validated in one pass per node instead of
    restarting from every suffix (which would be quadratic). Long valid chains
    must not hit recursion limits either, hence the explicit stack-free walk.
    """
    completed: set = set()
    for case in cases:
        if case["id"] in completed:
            continue
        seen = {case["id"]}
        current = case
        while True:
            ref = current.get("superseded_by")
            if ref is None:
                break
            if ref in seen:
                raise InvalidError(
                    f"case '{case['id']}': 'superseded_by' chain forms a cycle via '{ref}'"
                )
            if ref in completed:
                break
            seen.add(ref)
            current = index[ref]
        completed.update(seen)


def validate_case_document(document: Any) -> List[Dict[str, Any]]:
    if not isinstance(document, dict):
        raise InvalidError(f"{CASES_NAME} root must be a JSON object")
    version = document.get("version")
    if isinstance(version, bool) or not isinstance(version, int):
        raise InvalidError(f"{CASES_NAME}: 'version' must be the JSON integer 1")
    if version != SUPPORTED_VERSION:
        raise InvalidError(
            f"{CASES_NAME}: unsupported version {version!r}; this helper supports "
            f"version {SUPPORTED_VERSION}"
        )
    cases = document.get("cases")
    if not isinstance(cases, list):
        raise InvalidError(f"{CASES_NAME}: 'cases' must be a list")
    seen_ids: set = set()
    validated = [_validate_case(case, index, seen_ids) for index, case in enumerate(cases)]
    _validate_supersession(validated)
    return validated


# ---------------------------------------------------------------------------
# Matching (literal, casefolded substring; not semantic)
# ---------------------------------------------------------------------------


def match_case(case: Dict[str, Any], terms: List[str]) -> List[str]:
    """Return the distinct, canonical input terms matching this case.

    Matching uses casefolded substring search over ``title``, ``keywords``,
    ``statement``, and ``next_action`` only (not ``limits``). Returned terms are
    the stripped originals, deduplicated by casefold, so ``FOCUS`` and ``focus``
    count once and appear in the input as written, first occurrence first.
    """
    if not terms:
        return []
    haystack = [case["title"], case["statement"], case["next_action"]]
    haystack.extend(case["keywords"])
    folded = [value.casefold() for value in haystack]
    matched: List[str] = []
    for term in terms:
        needle = term.casefold()
        if not needle or any(existing.casefold() == needle for existing in matched):
            continue
        if any(needle in value for value in folded):
            matched.append(term)
    return matched


def canonicalize_terms(terms: List[str]) -> List[str]:
    """Strip terms, reject blanks, and deduplicate by casefold (first wins).

    Raises ``UsageError`` on an explicitly blank term so the CLI can report a
    usage error rather than silently dropping it.
    """
    canonical: List[str] = []
    seen = set()
    for term in terms:
        stripped = term.strip()
        if not stripped:
            raise UsageError(f"empty --term is not allowed: {term!r}")
        key = stripped.casefold()
        if key in seen:
            continue
        seen.add(key)
        canonical.append(stripped)
    return canonical


def scope_matches(case: Dict[str, Any], project: str, surface: str) -> bool:
    """Exact-axis scope filtering. ``*`` selects only the global value on a axis."""
    case_scope = case["scope"]
    if project == "*":
        project_ok = case_scope["project"] == "*"
    else:
        project_ok = case_scope["project"] in ("*", project)
    if surface == "*":
        surface_ok = case_scope["surface"] == "*"
    else:
        surface_ok = case_scope["surface"] in ("*", surface)
    return project_ok and surface_ok


def transfer_scope_matches(case: Dict[str, Any], project: str, surface: str) -> bool:
    """Widened scope for ``--transfer``: reach other projects' mechanism cases.

    Surface filtering is preserved (an editor mechanism is not a dashboard
    mechanism), but the project axis no longer excludes a different project's
    case. The caller labels each hit with its origin scope so it stays candidate
    analogy evidence, never a promotion to preference.
    """
    case_scope = case["scope"]
    if surface == "*":
        return case_scope["surface"] == "*"
    return case_scope["surface"] in ("*", surface)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def _context_section(root: Path) -> Dict[str, Any]:
    context = load_context(root)
    return {
        "available": context["available"],
        "state": context["status"],
        "text": context["text"],
    }


def cmd_query(args: argparse.Namespace) -> Tuple[int, Dict[str, Any]]:
    root = _resolve_root(args.root)
    context_section = _context_section(root)

    terms = canonicalize_terms(list(args.term))
    transfer = bool(getattr(args, "transfer", False))

    if getattr(args, "query", None):
        return _semantic_query(args, root, context_section, transfer)

    try:
        path, cases = load_cases(root)
        store_state, store_error = "available", None
    except InvalidError as exc:
        return EXIT_INVALID, {
            "ok": False,
            "error": "invalid_case_store",
            "message": str(exc),
            "context": context_section,
            "case_store": {"state": "invalid", "path": str(root / CASES_NAME)},
        }
    except MissingError as exc:
        path, cases, store_state, store_error = str(root / CASES_NAME), [], "missing", str(exc)

    matcher = transfer_scope_matches if transfer else scope_matches
    in_scope = [case for case in cases if matcher(case, args.project, args.surface)]
    active = [case for case in in_scope if case["status"] == "active"]

    if terms:
        matched: List[Dict[str, Any]] = []
        for case in active:
            hits = match_case(case, terms)
            if hits:
                matched.append({"case": case, "matched_terms": hits})
        matched.sort(key=lambda item: (-len(item["matched_terms"]), item["case"]["id"]))
        mode = "lexical"
    else:
        matched = [{"case": case, "matched_terms": []} for case in active]
        matched.sort(key=lambda item: item["case"]["id"])
        mode = "scope_only"

    limit = args.limit if args.limit is not None else DEFAULT_LIMIT
    limited = matched[:limit]

    if store_state == "missing":
        status = "store_missing"
    elif matched:
        status = "matched"
    else:
        status = "no_match"

    payload: Dict[str, Any] = {
        "ok": True,
        "status": status,
        "mode": mode,
        "error": store_error,
        "context": context_section,
        "case_store": {"state": store_state, "path": path},
        "requested_scope": {"project": args.project, "surface": args.surface},
        "terms": terms,
        "transfer": transfer,
        "matched": len(matched),
        "returned": len(limited),
        "truncated": len(matched) > len(limited),
        "cases": [_present(item, transfer=transfer, project=args.project)
                  for item in limited],
    }
    return EXIT_OK, payload


def _present(item: Dict[str, Any], *, transfer: bool, project: str) -> Dict[str, Any]:
    """Render a candidate. With ``--transfer``, mark cross-project analogies and
    label their origin scope so they cannot be mistaken for current prefs."""
    case = item["case"]
    entry: Dict[str, Any] = {"case": case, "matched_terms": item.get("matched_terms", [])}
    if "score" in item:
        entry["score"] = item["score"]
    if transfer:
        cross = case["scope"]["project"] not in ("*", project)
        entry["analogy"] = cross
        entry["current_scope"] = {
            "project": case["scope"]["project"],
            "surface": case["scope"]["surface"],
        }
    return entry


def _semantic_query(
    args: argparse.Namespace,
    root: Path,
    context_section: Dict[str, Any],
    transfer: bool,
) -> Tuple[int, Dict[str, Any]]:
    """Natural-language path. A remote/auth failure is a transparent failure and
    is never silently downgraded to a lexical result."""
    try:
        config = fccloud.load_config(root)
    except fccloud.ConfigError as exc:
        return EXIT_INVALID, {
            "ok": False,
            "status": "invalid_config",
            "error": "invalid_config",
            "message": str(exc),
            "context": context_section,
            "mode": "semantic",
        }
    try:
        path, cases = load_cases(root)
    except MissingError as exc:
        return EXIT_MISSING, {
            "ok": False, "status": "missing", "error": "missing", "message": str(exc),
            "context": context_section, "mode": "semantic",
        }
    except InvalidError as exc:
        return EXIT_INVALID, {
            "ok": False, "status": "invalid_case_store", "error": "invalid_case_store",
            "message": str(exc), "context": context_section, "mode": "semantic",
        }

    try:
        token = fccloud.resolve_token(config)
    except fccloud.CloudError as exc:
        return EXIT_REMOTE, {
            "ok": False, "status": "auth_error", "error": "auth_error",
            "message": str(exc), "context": context_section, "mode": "semantic",
            "case_store": {"state": "available", "path": path},
        }

    transport = fccloud.Transport(config["account_id"], token)
    project, surface = args.project, args.surface
    project_keys, surface_keys = fccloud.scope_filter_keys(
        config, project, surface, transfer=transfer
    )

    limit = args.limit if args.limit is not None else DEFAULT_LIMIT
    try:
        embedded = fccloud.embed_texts(transport, [args.query])
        hits_payload = fccloud.query_vectors(
            transport, config, embedded[0], project_keys, surface_keys, limit
        )
    except fccloud.CloudError as exc:
        return EXIT_REMOTE, {
            "ok": False, "status": "remote_error", "error": "remote_error",
            "message": str(exc), "context": context_section, "mode": "semantic",
            "case_store": {"state": "available", "path": path},
        }

    hits = (hits_payload.get("result") or {}).get("matches") or []
    cases_by_id = fccloud.normalize_cases(cases)
    reverse_ids = fccloud.reverse_id_map(config, cases)
    accepted, rejected = fccloud.resolve_hits(
        config, hits, cases_by_id, reverse_ids,
        project=project, surface=surface, transfer=transfer,
    )
    hit_count = len(accepted)
    accepted = accepted[:limit]

    return EXIT_OK, {
        "ok": True,
        "status": "matched" if accepted else "no_match",
        "mode": "semantic",
        "error": None,
        "context": context_section,
        "case_store": {"state": "available", "path": path},
        "requested_scope": {"project": project, "surface": surface},
        "query": args.query,
        "project_keys": project_keys,
        "surface_keys": surface_keys,
        "namespace": config["namespace"],
        "transfer": transfer,
        "matched": hit_count,
        "returned": len(accepted),
        "candidate_count_is_bounded": True,
        "top_k_cap": fccloud.MAX_TOPK,
        "rejected": rejected,
        "cases": [_present(hit, transfer=transfer, project=project) for hit in accepted],
    }


def cmd_show(args: argparse.Namespace) -> Tuple[int, Dict[str, Any]]:
    root = _resolve_root(args.root)
    path, cases = load_cases(root)
    for case in cases:
        if case["id"] == args.id:
            return EXIT_OK, {
                "ok": True,
                "status": "found",
                "case_store": {"state": "available", "path": path},
                "case": case,
            }
    return EXIT_NOT_FOUND, {
        "ok": False,
        "status": "not_found",
        "error": "not_found",
        "message": f"no case with id '{args.id}' in this store",
        "case_store": {"state": "available", "path": path},
    }


def cmd_validate(args: argparse.Namespace) -> Tuple[int, Dict[str, Any]]:
    root = _resolve_root(args.root)
    errors: List[str] = []
    exit_code = EXIT_OK

    context = load_context(root)
    context_state = "available" if context["available"] else "missing"
    if not context["available"]:
        errors.append(f"{CONTEXT_NAME} is missing")
        exit_code = EXIT_MISSING

    try:
        path, cases = load_cases(root)
        store_section = {"state": "available", "path": path, "case_count": len(cases)}
    except MissingError as exc:
        store_section = {"state": "missing", "path": str(root / CASES_NAME)}
        errors.append(str(exc))
        if exit_code == EXIT_OK:
            exit_code = EXIT_MISSING
    except InvalidError as exc:
        store_section = {"state": "invalid", "path": str(root / CASES_NAME)}
        errors.append(str(exc))
        exit_code = EXIT_INVALID

    return exit_code, {
        "ok": exit_code == EXIT_OK,
        "status": "valid" if exit_code == EXIT_OK else ("invalid" if exit_code == EXIT_INVALID else "missing"),
        "context": {"state": context_state, "path": context["path"]},
        "case_store": store_section,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

CONTEXT_TEMPLATE = """# Frontend Craft current context

Small, human-maintained record of current scoped aims and boundaries.
Read whole on relevant design/revision work. Keep it short; move detailed
examples into cases.json. Positive aims matter as much as prohibitions.

## Current aims

- Project: <project-slug>
- Surface: <surface-name>
- <what the experience should achieve; the quality to strengthen>

## Current boundaries

- <one line per current, still-applicable boundary or objection>
"""

CASES_TEMPLATE = {"version": 1, "cases": []}


def cmd_init(args: argparse.Namespace) -> Tuple[int, Dict[str, Any]]:
    """Create the first ``context.md``/``cases.json``. Never overwrites."""
    root_path = Path(args.root)
    if not os.path.lexists(root_path):
        if not args.mkdir:
            raise MissingError(
                f"root does not exist: {root_path} (pass --mkdir to create it)"
            )
        root_path.mkdir(parents=True)
    root = _resolve_root(args.root)

    created: List[str] = []
    skipped: List[str] = []
    context_path = root / CONTEXT_NAME
    if os.path.lexists(context_path):
        skipped.append(CONTEXT_NAME)
    else:
        text = CONTEXT_TEMPLATE
        if args.project and args.surface:
            text = text.replace("<project-slug>", args.project).replace(
                "<surface-name>", args.surface
            )
        context_path.write_text(text, encoding="utf-8")
        created.append(CONTEXT_NAME)

    cases_path = root / CASES_NAME
    if os.path.lexists(cases_path):
        skipped.append(CASES_NAME)
    else:
        cases_path.write_text(
            json.dumps(CASES_TEMPLATE, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        created.append(CASES_NAME)

    return EXIT_OK, {
        "ok": True,
        "status": "initialized" if created else "already_initialized",
        "root": str(root),
        "created": created,
        "skipped_existing": skipped,
    }


def cmd_sync(args: argparse.Namespace) -> Tuple[int, Dict[str, Any]]:
    root = _resolve_root(args.root)
    config = fccloud.load_config(root)
    path, cases = load_cases(root)
    manifest = fccloud.load_manifest(root)

    if getattr(args, "verify", False):
        try:
            token = fccloud.resolve_token(config)
            transport = fccloud.Transport(config["account_id"], token)
            status = fccloud.verify_pending(transport, config, root)
        except fccloud.ConfigError as exc:
            return EXIT_INVALID, {
                "ok": False, "status": "invalid_config", "error": "invalid_config",
                "message": str(exc), "applied": None,
            }
        except fccloud.CloudError as exc:
            return EXIT_REMOTE, {
                "ok": False, "status": "remote_error", "error": "remote_error",
                "message": str(exc), "applied": None,
            }
        code = EXIT_OK if status["status"] in ("none", "ready") else EXIT_PENDING
        return code, {
            "ok": status["status"] != "pending",
            "status": status["status"],
            "mode": "verify",
            "applied": False,
            "pending": status["pending"],
            "verified_uploads": status.get("verified_uploads", []),
            "verified_deletions": status.get("verified_deletions", []),
            "unverified": status.get("unverified", []),
            "note": status.get("note"),
            "case_store": {"state": "available", "path": path},
        }

    plan = fccloud.plan_sync(config, cases, manifest)
    summary = fccloud.summarize_plan(plan)

    if not args.apply:
        if getattr(args, "wait", False):
            raise UsageError(
                "--wait requires --apply (it waits for mutations created by a "
                "write); use `sync --verify` to re-check persisted pending state"
            )
        summary.update(
            {
                "ok": True,
                "status": "dry_run",
                "mode": "dry_run",
                "applied": False,
                "case_store": {"state": "available", "path": path},
            }
        )
        return EXIT_OK, summary

    try:
        token = fccloud.resolve_token(config)
        transport = fccloud.Transport(config["account_id"], token)
        result = fccloud.apply_sync(
            transport, config, root, plan, wait=args.wait
        )
    except fccloud.CloudError as exc:
        return EXIT_REMOTE, {
            "ok": False, "status": "remote_error", "error": "remote_error",
            "message": str(exc), "applied": None,
            "note": "applied state is whatever was persisted; inspect "
                    f"{fccloud.SYNC_STATE_NAME} and re-run sync --apply",
        }
    except fccloud.PendingError as exc:
        return EXIT_PENDING, {
            "ok": True, "status": "pending", "error": "pending",
            "message": str(exc), "applied": True,
            "note": "pending state persisted; re-run `sync --verify` to check "
                    "readback without re-embedding",
        }

    summary.update(
        {
            "ok": True,
            "status": "applied" if result["mutation_state"] == "ready" else "pending",
            "mode": "apply",
            "applied": result["applied"],
            "mutation_state": result["mutation_state"],
            "uploaded": result["uploaded"],
            "deleted": result["deleted"],
            "verified_uploads": result.get("verified_uploads", []),
            "verified_deletions": result.get("verified_deletions", []),
            "unverified": result.get("unverified", []),
            "case_store": {"state": "available", "path": path},
        }
    )
    return EXIT_OK, summary


def cmd_doctor(args: argparse.Namespace) -> Tuple[int, Dict[str, Any]]:
    """Verify config, local records, auth, remote index info, and metadata
    indexes. Uses GET .../indexes/{index} (result.config.dimensions/metric),
    GET .../indexes/{index}/info, and GET .../metadata_index/list."""
    root = _resolve_root(args.root)
    checks: List[Dict[str, Any]] = []
    errors: List[str] = []

    try:
        config = fccloud.load_config(root)
        checks.append({"name": "config", "ok": True, "detail": config["index_name"]})
    except fccloud.ConfigError as exc:
        return EXIT_INVALID, {
            "ok": False, "status": "invalid_config", "error": "invalid_config",
            "message": str(exc), "checks": checks,
        }

    dims_ok = config["dimensions"] == fccloud.DIMENSIONS
    metric_ok = config["metric"] == fccloud.METRIC
    checks.append({"name": "dimensions", "ok": dims_ok, "detail": config["dimensions"]})
    checks.append({"name": "metric", "ok": metric_ok, "detail": config["metric"]})
    if not (dims_ok and metric_ok):
        errors.append("config must be 1024/cosine")

    context = load_context(root)
    checks.append({"name": "context", "ok": context["available"], "detail": context["status"]})
    if not context["available"]:
        errors.append(f"{CONTEXT_NAME} is missing")
    try:
        _, cases = load_cases(root)
        checks.append({"name": "case_store", "ok": True, "detail": {"count": len(cases)}})
    except (MissingError, InvalidError) as exc:
        checks.append({"name": "case_store", "ok": False, "detail": str(exc)})
        errors.append(f"case store: {exc}")

    try:
        token = fccloud.resolve_token(config)
        checks.append({"name": "auth", "ok": True, "detail": config["auth"]})
    except fccloud.CloudError as exc:
        checks.append({"name": "auth", "ok": False, "detail": str(exc)})
        errors.append(str(exc))
        return EXIT_REMOTE, {
            "ok": False, "status": "auth_error", "error": "auth_error",
            "checks": checks, "errors": errors,
        }

    transport = fccloud.Transport(config["account_id"], token)
    try:
        info = fccloud.get_index_info(transport, config)
        index_config = fccloud.get_index_config(transport, config)
    except fccloud.CloudError as exc:
        return EXIT_REMOTE, {
            "ok": False, "status": "remote_error", "error": "remote_error",
            "message": str(exc), "checks": checks, "errors": errors,
        }

    result = info.get("result") or {}
    remote_dims = result.get("dimensions")
    remote_vectors = result.get("vectorCount")
    processed = result.get("processedUpToMutation")
    # Real GET /indexes/{index} shape: result.config = {dimensions, metric}.
    geometry = index_config.get("config") if isinstance(index_config, dict) else None
    geometry = geometry if isinstance(geometry, dict) else {}
    remote_metric = geometry.get("metric")
    remote_cfg_dims = geometry.get("dimensions")
    checks.append(
        {
            "name": "remote_index_info",
            "ok": remote_cfg_dims == fccloud.DIMENSIONS
            and fccloud.metadata_type_matches(remote_metric, fccloud.METRIC),
            "detail": {"dimensions": remote_dims, "vectorCount": remote_vectors,
                       "metric": remote_metric, "configDimensions": remote_cfg_dims,
                       "processedUpToMutation": processed},
        }
    )
    if remote_cfg_dims != fccloud.DIMENSIONS:
        errors.append(
            f"remote index config dimensions are {remote_cfg_dims!r}, expected "
            f"{fccloud.DIMENSIONS}; recreate the index via the runbook"
        )
    if not fccloud.metadata_type_matches(remote_metric, fccloud.METRIC):
        errors.append(
            f"remote index metric is {remote_metric!r}, expected "
            f"{fccloud.METRIC!r}; recreate the index via the runbook"
        )
    if remote_dims is not None and remote_dims != fccloud.DIMENSIONS:
        errors.append(
            f"/info dimensions are {remote_dims!r}, expected {fccloud.DIMENSIONS}"
        )

    try:
        indexes = fccloud.list_metadata_indexes(transport, config)
    except fccloud.CloudError as exc:
        return EXIT_REMOTE, {
            "ok": False, "status": "remote_error", "error": "remote_error",
            "message": str(exc), "checks": checks, "errors": errors,
        }
    present = {
        item.get("propertyName"): item.get("indexType")
        for item in indexes
        if isinstance(item, dict)
    }
    missing = [
        name
        for name, kind in fccloud.REQUIRED_METADATA_INDEXES
        if not fccloud.metadata_type_matches(present.get(name), kind)
    ]
    checks.append(
        {
            "name": "metadata_indexes",
            "ok": not missing,
            "detail": {"present": present, "missing": missing},
        }
    )
    if missing:
        errors.append(
            "missing metadata indexes before sync: " + ", ".join(missing)
        )

    ok = not errors
    return (EXIT_OK if ok else EXIT_REMOTE), {
        "ok": ok,
        "status": "ready" if ok else "not_ready",
        "checks": checks,
        "errors": errors,
        "target_fingerprint": fccloud.target_fingerprint(config),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(
        prog="fc_memory",
        description=(
            "Frontend Craft design records: offline lexical query/show/validate "
            "(read-only), init, and optional Cloudflare sync/doctor/semantic query."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    query = subparsers.add_parser("query", help="select candidate cases for a scope")
    query.add_argument("--root", required=True, help="authorized directory holding the records")
    query.add_argument("--project", required=True, help="project slug, or * for cross-project only")
    query.add_argument("--surface", required=True, help="surface name, or * for cross-surface only")
    query.add_argument(
        "--term",
        action="append",
        default=[],
        help="literal keyword, repeatable; omitted => bounded scope browse (mode=scope_only)",
    )
    query.add_argument(
        "--limit",
        type=int,
        default=None,
        help=f"max cases to return, positive int (default {DEFAULT_LIMIT})",
    )
    query.add_argument(
        "--query",
        default=None,
        help="natural-language query routed to Workers AI + Vectorize (semantic mode)",
    )
    query.add_argument(
        "--transfer",
        action="store_true",
        help="widen project scope to other projects' mechanism cases (labeled analogies)",
    )
    query.set_defaults(func=cmd_query)

    show = subparsers.add_parser("show", help="show one case by id, including retired ones")
    show.add_argument("--root", required=True)
    show.add_argument("--id", required=True)
    show.set_defaults(func=cmd_show)

    validate = subparsers.add_parser("validate", help="check context presence and case schema")
    validate.add_argument("--root", required=True)
    validate.set_defaults(func=cmd_validate)

    init = subparsers.add_parser(
        "init", help="create first context.md/cases.json (never overwrites)"
    )
    init.add_argument("--root", required=True, help="authorized directory to initialize")
    init.add_argument("--project", default=None, help="optional project slug for the template")
    init.add_argument("--surface", default=None, help="optional surface name for the template")
    init.add_argument("--mkdir", action="store_true", help="create the root if missing")
    init.set_defaults(func=cmd_init)

    doctor = subparsers.add_parser(
        "doctor", help="verify config, 1024/cosine, metadata indexes, and auth"
    )
    doctor.add_argument("--root", required=True)
    doctor.set_defaults(func=cmd_doctor)

    sync = subparsers.add_parser(
        "sync", help="dry-run by default; --apply embeds changed actives and deletes removed"
    )
    sync.add_argument("--root", required=True)
    sync.add_argument("--apply", action="store_true", help="perform network writes")
    sync.add_argument(
        "--wait", action="store_true",
        help="bounded wait for queued mutations to reach ready",
    )
    sync.add_argument(
        "--verify", action="store_true",
        help="read back pending mutations and update local state; no embed or remote write",
    )
    sync.set_defaults(func=cmd_sync)

    return parser


def _emit(payload: Dict[str, Any], exit_code: int) -> int:
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return exit_code


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "limit", None) is not None and args.limit < 1:
        parser.error("--limit must be a positive integer")

    try:
        code, payload = args.func(args)
    except UsageError as exc:
        return _emit(
            {"ok": False, "status": "usage_error", "error": "usage_error", "message": str(exc)},
            EXIT_USAGE,
        )
    except MissingError as exc:
        return _emit({"ok": False, "status": "missing", "error": "missing", "message": str(exc)}, EXIT_MISSING)
    except InvalidError as exc:
        return _emit({"ok": False, "status": "invalid", "error": "invalid", "message": str(exc)}, EXIT_INVALID)
    except DataError as exc:
        return _emit({"ok": False, "status": "invalid", "error": "invalid", "message": str(exc)}, EXIT_INVALID)
    except fccloud.ConfigError as exc:
        return _emit(
            {"ok": False, "status": "invalid_config", "error": "invalid_config",
             "message": str(exc)},
            EXIT_INVALID,
        )
    except fccloud.CloudError as exc:
        return _emit(
            {"ok": False, "status": "remote_error", "error": "remote_error",
             "message": str(exc)},
            EXIT_REMOTE,
        )
    except fccloud.PendingError as exc:
        return _emit(
            {"ok": False, "status": "pending", "error": "pending",
             "message": str(exc)},
            EXIT_PENDING,
        )
    return _emit(payload, code)


if __name__ == "__main__":
    sys.exit(main())
