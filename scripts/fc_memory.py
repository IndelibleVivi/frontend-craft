#!/usr/bin/env python3
"""Read-only retrieval helper for Frontend Craft design records.

Frontend Craft keeps two separate files inside one explicitly authorized root:

- ``context.md``: the small, human-maintained current-preference record. Every
  query returns it whole; it is never trimmed by terms, scope, or ``--limit``.
- ``cases.json``: a growing, human-reviewed ledger of reusable experience cases.

This helper only reads. It never extracts, writes, ranks semantically, or
maintains a profile. It selects cases by exact scope, lifecycle status, and
literal term matching, and it reports honestly when nothing matched. Selection
is candidate evidence for an agent to judge, not an instruction authority.

Matching is deliberately lexical (casefolded substring). That is a real ceiling:
a paraphrased or cross-language query with no shared keyword will miss even when
a relevant case exists, and the helper reports that as ``no_match`` rather than
guessing. A semantic or hybrid layer is a future option to evaluate against real
query-to-id misses, not something this helper pretends to provide. See
``references/memory-operations.md``.

The ``--root`` is the caller-authorized directory; this is not an OS sandbox.
See ``references/memory-operations.md`` for the operating protocol.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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

    in_scope = [case for case in cases if scope_matches(case, args.project, args.surface)]
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
        "matched": len(matched),
        "returned": len(limited),
        "truncated": len(matched) > len(limited),
        "cases": [
            {"case": item["case"], "matched_terms": item["matched_terms"]}
            for item in limited
        ],
    }
    return EXIT_OK, payload


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


def build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(
        prog="fc_memory",
        description="Read-only Frontend Craft design-record retrieval.",
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
    query.set_defaults(func=cmd_query)

    show = subparsers.add_parser("show", help="show one case by id, including retired ones")
    show.add_argument("--root", required=True)
    show.add_argument("--id", required=True)
    show.set_defaults(func=cmd_show)

    validate = subparsers.add_parser("validate", help="check context presence and case schema")
    validate.add_argument("--root", required=True)
    validate.set_defaults(func=cmd_validate)

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
    return _emit(payload, code)


if __name__ == "__main__":
    sys.exit(main())
