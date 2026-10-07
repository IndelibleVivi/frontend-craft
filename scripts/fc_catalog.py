#!/usr/bin/env python3
"""Frontend Craft visual catalogue CLI.

This helper owns one file format and one set of verbs for three collections:

- the public positive-instance library (``examples/library/``),
- a project's own reference collection (``<project>/.frontend-craft/catalog.json``),
- a cross-project materials collection in an authorized private location.

The catalogue records identity, visual originals, material locations, making
relations, versions, and provenance. A separate ``uses`` ledger records which
relation a project actually selected and whether it was verified to appear in
the real project. Decisions, preferences, feedback text, and current project
implementation stay in their existing owners; this file only points at them.

Verb scope:

- ``query`` / ``show`` / ``resolve`` / ``validate`` are read-only.
- ``register`` is the only writing verb; it also retains referenced media.
- ``gallery`` renders a static, disposable HTML read of the catalogue.

Boundaries that this code enforces rather than assumes:

- No command scans unknown roots. Every non-``catalog`` root is bound
  explicitly with ``--root <catalog-id>:<alias>=<path>``.
- Resolved paths must stay inside their bound root; absolute paths in a
  locator, traversal, and escaping symlinks are rejected.
- Recorded commands are never executed and remote files are never fetched.
- ``resolve`` reports each asset independently; it never turns a missing file
  or an unresolved reference into an unconditional success.
- Exact derivation references (``derivation``) must be acyclic; general
  ``references``/``materials`` relations may cycle.

See ``references/catalog-operations.md`` for the exact accepted JSON payloads
and the view-bindings file. See
``docs/specs/2026-10-08-visual-library-and-project-gallery.md`` sections 6-9
for the product behaviour this implements.
"""

from __future__ import annotations

import argparse
import base64
import errno
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import quote

try:  # POSIX advisory lock; the fallback is a bounded exclusive lock directory.
    import fcntl as _fcntl
except ImportError:  # pragma: no cover - non-POSIX platform
    _fcntl = None  # type: ignore[assignment]

SUPPORTED_VERSION = 1

ROLES = ("reference", "material", "style", "palette", "combination")
SOURCE_KINDS = ("authored", "external", "generated")
USE_STATUSES = ("selected", "in-use", "past")
USE_FIELDS = {
    "id", "revision", "target", "references", "relation", "status",
    "observed_at", "evidence",
}
PALETTE_ROLES = (
    "base", "raised", "text-primary", "text-secondary", "accent",
    "accent-foreground", "selected", "feedback",
)
PREVIEW_KINDS = (
    "screenshot", "image", "video", "audio", "keyframes", "type-specimen",
    "palette", "source",
)
ASSET_STATUSES = ("available", "missing", "changed", "remote-only", "unavailable")
MEDIA_SUFFIX_KINDS = {
    ".png": "image", ".jpg": "image", ".jpeg": "image", ".gif": "image",
    ".webp": "image", ".avif": "image", ".bmp": "image", ".svg": "image",
    ".mp4": "video", ".webm": "video", ".mov": "video",
    ".mp3": "audio", ".wav": "audio", ".ogg": "audio", ".m4a": "audio",
}
ACTIVE_SCHEME_RE = re.compile(r"^[a-z][a-z0-9+.\-]*:", re.IGNORECASE)
CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_CONFLICT = 2
EXIT_NOT_FOUND = 3
EXIT_MISSING = 4
EXIT_INVALID = 5
EXIT_BUSY = 6


class DataError(Exception):
    """A malformed input file or an invalid catalogue payload."""


class MissingError(Exception):
    """A required file is absent."""



class ConflictError(Exception):
    """The caller's expected revision does not match the file on disk."""


class LockBusyError(Exception):
    """The catalogue lock could not be acquired within the bounded wait."""


class UsageError(Exception):
    """An invalid command-line argument combination."""


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str):  # pragma: no cover - exercised via CLI
        self.print_usage(sys.stderr)
        self.exit(EXIT_USAGE, f"{self.prog}: error: {message}\n")


# ---------------------------------------------------------------------------
# Small typed helpers (validation uses these so wrong types fail loudly)
# ---------------------------------------------------------------------------

def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _require_int(container: Dict[str, Any], field: str, where: str, *, minimum: int = 1) -> int:
    value = container.get(field)
    if not _is_int(value) or value < minimum:
        raise DataError(f"{where}: '{field}' must be an integer >= {minimum}")
    return value


def _require_str(container: Dict[str, Any], field: str, where: str) -> str:
    value = container.get(field)
    if not isinstance(value, str) or not value.strip():
        raise DataError(f"{where}: '{field}' must be a non-empty string")
    return value


def _require_list(container: Dict[str, Any], field: str, where: str, *, nonempty: bool = True) -> List[Any]:
    value = container.get(field)
    if not isinstance(value, list) or (nonempty and not value):
        suffix = "non-empty " if nonempty else ""
        raise DataError(f"{where}: '{field}' must be a {suffix}list")
    return value


def _reject_unknown(container: Dict[str, Any], allowed: Iterable[str], where: str) -> None:
    extra = set(container) - set(allowed)
    if extra:
        raise DataError(f"{where}: unknown keys {sorted(extra)}")


def _check_metadata(value: str, where: str) -> None:
    if CONTROL_CHAR_RE.search(value):
        raise DataError(f"{where}: control characters are not allowed in metadata")
    if value.strip().lower().startswith(("javascript:", "vbscript:")):
        raise DataError(f"{where}: active URL scheme is not allowed in metadata")


def _validate_tag_list(container: Dict[str, Any], field: str, where: str) -> List[str]:
    value = container.get(field)
    if value is None:
        return []
    if not isinstance(value, list):
        raise DataError(f"{where}: '{field}' must be a list of strings")
    for entry in value:
        if not isinstance(entry, str) or not entry.strip():
            raise DataError(f"{where}: '{field}' entries must be non-empty strings")
        _check_metadata(entry, f"{where}.{field}")
    return list(value)


def _validate_tags(tags: Any, where: str) -> Dict[str, List[str]]:
    if tags is None:
        return {}
    if not isinstance(tags, dict):
        raise DataError(f"{where}: 'tags' must be an object")
    allowed = {"tasks", "languages", "media", "scales", "terms"}
    _reject_unknown(tags, allowed, f"{where}.tags")
    return {key: _validate_tag_list(tags, key, f"{where}.tags") for key in tags}


# ---------------------------------------------------------------------------
# URL / protocol safety
# ---------------------------------------------------------------------------

def _classify_url(url: str) -> Tuple[bool, str]:
    """Return (is_safe_link, scheme). Only http/https are treated as links."""
    match = ACTIVE_SCHEME_RE.match(url.strip())
    if not match:
        return False, ""
    scheme = match.group(0)[:-1].lower()
    return scheme in ("http", "https"), scheme


def _validate_url(url: Any, where: str) -> str:
    if not isinstance(url, str) or not url.strip():
        raise DataError(f"{where}: URL must be a non-empty string")
    safe, scheme = _classify_url(url)
    if not safe:
        raise DataError(f"{where}: only http/https links are allowed, got scheme {scheme!r}")
    if CONTROL_CHAR_RE.search(url):
        raise DataError(f"{where}: URL contains control characters")
    return url


# ---------------------------------------------------------------------------
# Locators and root binding
# ---------------------------------------------------------------------------

class RootBindings:
    """Bindings from locator ``root`` names to real directories.

    ``catalog`` is always the catalogue file's own directory and cannot be
    rebound. Every other non-``catalog`` root must be bound explicitly; an
    unbound root is refused rather than guessed at.
    """

    def __init__(self, catalog_id: str, catalog_dir: Path,
                 bindings: Optional[Dict[Tuple[str, str], Path]] = None) -> None:
        self.catalog_id = catalog_id
        self.catalog_dir = Path(catalog_dir)
        self.explicit: Dict[str, Path] = dict(bindings or {})

    def add_explicit(self, alias: str, path: Path) -> None:
        if not alias:
            raise UsageError("root alias must not be empty")
        self.explicit[alias] = Path(path)

    def resolve_root(self, root: str, *, where: str) -> Path:
        if root == "catalog":
            return self.catalog_dir
        if root in self.explicit:
            return self.explicit[root]
        raise MissingError(
            f"{where}: root '{root}' is not bound; pass "
            f"--root {self.catalog_id}:{root}=<path>"
        )


def _parse_root_arg(catalog_id: str, spec: str) -> Tuple[str, str, Path]:
    if "=" not in spec:
        raise UsageError(f"--root must be <catalog-id>:<alias>=<path>, got {spec!r}")
    head, _, path = spec.partition("=")
    owner, sep, alias = head.partition(":")
    if not sep or not owner or not alias or not path:
        raise UsageError(f"--root must be <catalog-id>:<alias>=<path>, got {spec!r}")
    if owner == "catalog":
        raise UsageError(f"--root {spec!r}: the 'catalog' root is fixed and cannot be rebound")
    return owner, alias, Path(path)


def _safe_under(root: Path, path: str, where: str) -> Path:
    """Join ``path`` under ``root`` and forbid traversal/absolute/symlink escape.

    ``path`` is always a relative POSIX-style path. The resolved real path must
    stay inside the resolved real root. A symlink whose target leaves the root
    is rejected even when the immediate entry is inside.
    """
    if not isinstance(path, str) or not path:
        raise DataError(f"{where}: locator 'path' must be a non-empty string")
    if path.startswith("/") or (len(path) > 1 and path[1] == ":"):
        raise DataError(f"{where}: locator 'path' must be relative, got {path!r}")
    parts = [p for p in path.split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts):
        raise DataError(f"{where}: locator 'path' must not traverse ('..'): {path!r}")
    root_real = root.resolve()
    candidate = root.joinpath(*parts)
    return _assert_inside(root_real, candidate, where, path)


def _assert_inside(root_real: Path, candidate: Path, where: str, label: str) -> Path:
    # Resolve as far as the path exists so symlinked components are checked too,
    # then re-attach the not-yet-existing suffix.
    probe = candidate
    suffix: List[str] = []
    while not os.path.lexists(probe):
        if probe == probe.parent:
            break
        suffix.append(probe.name)
        probe = probe.parent
    if os.path.lexists(probe):
        resolved = probe.resolve()
        for name in reversed(suffix):
            resolved = resolved / name
    else:  # pragma: no cover - defensive; root always exists
        resolved = candidate.resolve()
    if resolved != root_real and root_real not in resolved.parents:
        raise DataError(f"{where}: locator resolves outside its root ({label!r})")
    return candidate


def _validate_locator(locator: Any, where: str) -> Dict[str, str]:
    if not isinstance(locator, dict):
        raise DataError(f"{where}: 'locator' must be an object")
    _reject_unknown(locator, {"root", "path"}, where)
    root = _require_str(locator, "root", where)
    path = _require_str(locator, "path", where)
    if path.startswith("/") or any(p == ".." for p in path.split("/")):
        raise DataError(f"{where}: 'locator.path' must be a relative, non-traversing path")
    return {"root": root, "path": path}


# ---------------------------------------------------------------------------
# Content addressing
# ---------------------------------------------------------------------------

def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _looks_like_digest(value: Any) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[0-9a-f]{64}", value))


# ---------------------------------------------------------------------------
# Document loading & structural validation
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> Any:
    if not os.path.lexists(path):
        raise MissingError(f"file does not exist: {path}")
    if path.is_symlink():
        raise DataError(f"{path} must not be a symlink")
    if not path.is_file():
        raise DataError(f"{path} is not a regular file")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise MissingError(f"cannot read {path}: {exc}") from exc
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DataError(f"{path} is not valid UTF-8: {exc}") from exc
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise DataError(f"{path} is not valid JSON: {exc}") from exc


def _new_document(catalog_id: str) -> Dict[str, Any]:
    return {"version": SUPPORTED_VERSION, "id": catalog_id, "revision": 0, "items": [], "uses": []}


def _validate_timestamp(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DataError(f"{where}: timestamp must be an ISO-8601 string")
    candidate = value.strip().replace("Z", "+00:00")
    try:
        datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise DataError(f"{where}: timestamp must be ISO-8601 ({exc})") from exc
    return value


def _validate_reference(ref: Any, where: str) -> Dict[str, Any]:
    if not isinstance(ref, dict):
        raise DataError(f"{where}: reference must be an object")
    _reject_unknown(ref, {"catalog_id", "item_id", "revision", "asset_id", "preview_id"}, where)
    _require_str(ref, "catalog_id", where)
    _require_str(ref, "item_id", where)
    _require_int(ref, "revision", where, minimum=1)
    if ref.get("asset_id") is not None and ref.get("preview_id") is not None:
        raise DataError(f"{where}: 'asset_id' and 'preview_id' are mutually exclusive")
    for field in ("asset_id", "preview_id"):
        if ref.get(field) is not None:
            _require_str(ref, field, where)
    return ref


def _validate_source(source: Any, where: str) -> Dict[str, Any]:
    if not isinstance(source, dict):
        raise DataError(f"{where}: 'source' must be an object")
    _reject_unknown(source, {"kind", "url", "author", "version", "ref", "note"}, where)
    kind = source.get("kind")
    if kind not in SOURCE_KINDS:
        raise DataError(f"{where}: 'source.kind' must be one of {list(SOURCE_KINDS)}")
    if source.get("url") is not None:
        _validate_url(source["url"], f"{where}.source.url")
    if source.get("ref") is not None:
        _validate_reference(source["ref"], f"{where}.source.ref")
    for field in ("author", "version", "note"):
        if source.get(field) is not None:
            _check_metadata(_require_str(source, field, where), f"{where}.source.{field}")
    if kind == "external" and source.get("url") is None:
        raise DataError(f"{where}: source.kind 'external' requires a URL")
    return source


def _validate_capture(capture: Any, where: str) -> Dict[str, Any]:
    if not isinstance(capture, dict):
        raise DataError(f"{where}: 'capture' must be an object")
    _reject_unknown(capture, {"viewport", "coverage", "state", "taken_at", "clip", "sequence", "note"}, where)
    viewport = capture.get("viewport")
    if viewport is not None:
        if (not isinstance(viewport, list) or len(viewport) != 2
                or not all(_is_int(v) and v > 0 for v in viewport)):
            raise DataError(f"{where}: 'capture.viewport' must be [width, height]")
    if capture.get("taken_at") is not None:
        _validate_timestamp(capture["taken_at"], f"{where}.capture.taken_at")
    if capture.get("state") is not None:
        _check_metadata(_require_str(capture, "state", where), f"{where}.capture.state")
    if capture.get("coverage") is not None:
        if capture["coverage"] not in ("surface", "full", "clip", "sequence"):
            raise DataError(f"{where}: 'capture.coverage' must be surface/full/clip/sequence")
    return capture


def _validate_previews(previews: Any, where: str) -> List[Dict[str, Any]]:
    if previews is None:
        return []
    if not isinstance(previews, list):
        raise DataError(f"{where}: 'previews' must be a list")
    seen = set()
    for index, preview in enumerate(previews):
        pwhere = f"{where}.previews[{index}]"
        if not isinstance(preview, dict):
            raise DataError(f"{pwhere}: preview must be an object")
        _reject_unknown(preview, {"id", "kind", "locator", "digest", "capture", "label", "url",
                                  "input_locator"}, pwhere)
        pid = _require_str(preview, "id", pwhere)
        if pid in seen:
            raise DataError(f"{pwhere}: duplicate preview id '{pid}'")
        seen.add(pid)
        kind = preview.get("kind")
        if kind not in PREVIEW_KINDS:
            raise DataError(f"{pwhere}: 'kind' must be one of {list(PREVIEW_KINDS)}")
        if preview.get("locator") is not None:
            _validate_locator(preview["locator"], f"{pwhere}.locator")
        if preview.get("input_locator") is not None:
            _validate_locator(preview["input_locator"], f"{pwhere}.input_locator")
        if preview.get("locator") is None and preview.get("input_locator") is None:
            raise DataError(f"{pwhere}: a preview needs a 'locator' or an 'input_locator'")
        digest = preview.get("digest")
        if digest is not None and not _looks_like_digest(digest):
            raise DataError(f"{pwhere}: 'digest' must be a lowercase hex sha256")
        if preview.get("capture") is not None:
            _validate_capture(preview["capture"], pwhere)
        if preview.get("label") is not None:
            _check_metadata(_require_str(preview, "label", pwhere), f"{pwhere}.label")
        if preview.get("url") is not None:
            _validate_url(preview["url"], f"{pwhere}.url")
    return previews


def _validate_making(making: Any, where: str) -> Dict[str, Any]:
    if not isinstance(making, dict):
        raise DataError(f"{where}: 'making' must be an object")
    _reject_unknown(making, {"effect", "carry", "vary", "limits"}, where)
    out: Dict[str, Any] = {}
    for field in ("effect", "limits"):
        text = _require_str(making, field, where)
        _check_metadata(text, f"{where}.making.{field}")
        out[field] = text
    for field in ("carry", "vary"):
        value = making.get(field)
        if not isinstance(value, list) or not value:
            raise DataError(f"{where}: 'making.{field}' must be a non-empty list")
        for entry in value:
            if not isinstance(entry, str) or not entry.strip():
                raise DataError(f"{where}: 'making.{field}' entries must be non-empty strings")
        out[field] = list(value)
    return out


def _validate_palette(palette: Any, where: str) -> Dict[str, Any]:
    if not isinstance(palette, dict):
        raise DataError(f"{where}: 'palette' must be an object")
    _reject_unknown(palette, {"roles", "instance", "state"}, where)
    roles = palette.get("roles")
    if not isinstance(roles, dict) or not roles:
        raise DataError(f"{where}: 'palette.roles' must be a non-empty object")
    for role, entry in roles.items():
        rwhere = f"{where}.palette.roles.{role}"
        if role not in PALETTE_ROLES:
            raise DataError(f"{rwhere}: unknown palette role {role!r}")
        if not isinstance(entry, dict):
            raise DataError(f"{rwhere}: must be an object")
        _reject_unknown(entry, {"value", "foreground", "background", "area", "note"}, rwhere)
        _require_str(entry, "value", rwhere)
        for field in ("foreground", "background"):
            if entry.get(field) is not None:
                _require_str(entry, field, rwhere)
    _validate_reference(palette.get("instance"), f"{where}.palette.instance")
    if palette.get("state") is not None:
        _check_metadata(_require_str(palette, "state", where), f"{where}.palette.state")
    return palette


def _validate_assets(assets: Any, where: str) -> List[Dict[str, Any]]:
    if assets is None:
        return []
    if not isinstance(assets, list):
        raise DataError(f"{where}: 'assets' must be a list")
    seen = set()
    for index, asset in enumerate(assets):
        awhere = f"{where}.assets[{index}]"
        if not isinstance(asset, dict):
            raise DataError(f"{awhere}: asset must be an object")
        _reject_unknown(asset, {"id", "role", "locator", "url", "file_type", "sha256",
                                "version", "axes", "note", "input_locator"}, awhere)
        aid = _require_str(asset, "id", awhere)
        if aid in seen:
            raise DataError(f"{awhere}: duplicate asset id '{aid}'")
        seen.add(aid)
        locator = asset.get("locator")
        url = asset.get("url")
        if locator is None and url is None and asset.get("input_locator") is None:
            raise DataError(f"{awhere}: an asset needs a 'locator', an 'input_locator', or a 'url'")
        if locator is not None:
            _validate_locator(locator, f"{awhere}.locator")
        if asset.get("input_locator") is not None:
            _validate_locator(asset["input_locator"], f"{awhere}.input_locator")
        if url is not None:
            _validate_url(url, f"{awhere}.url")
        if asset.get("sha256") is not None and not _looks_like_digest(asset["sha256"]):
            raise DataError(f"{awhere}: 'sha256' must be a lowercase hex sha256")
        if locator is None and asset.get("sha256") is not None:
            raise DataError(f"{awhere}: a sha256 needs a local 'locator' to check")
        for field in ("file_type", "version", "note"):
            if asset.get(field) is not None:
                _check_metadata(_require_str(asset, field, awhere), f"{awhere}.{field}")
        if asset.get("axes") is not None and not isinstance(asset["axes"], dict):
            raise DataError(f"{awhere}: 'axes' must be an object when present")
    return assets


def _validate_derivation(derivation: Any, where: str) -> Dict[str, Any]:
    if not isinstance(derivation, dict):
        raise DataError(f"{where}: 'derivation' must be an object")
    _reject_unknown(derivation, {"sources", "script", "steps", "inputs", "outputs"}, where)
    sources = derivation.get("sources")
    if not isinstance(sources, list) or not sources:
        raise DataError(f"{where}: 'derivation.sources' must be a non-empty list")
    for index, ref in enumerate(sources):
        _validate_reference(ref, f"{where}.derivation.sources[{index}]")
    if derivation.get("script") is not None:
        _validate_locator(derivation["script"], f"{where}.derivation.script")
    if derivation.get("steps") is not None:
        steps = _require_list(derivation, "steps", where)
        for entry in steps:
            if not isinstance(entry, str) or not entry.strip():
                raise DataError(f"{where}: 'derivation.steps' entries must be strings")
    for field in ("inputs", "outputs"):
        if derivation.get(field) is not None and not isinstance(derivation[field], list):
            raise DataError(f"{where}: 'derivation.{field}' must be a list when present")
    return derivation


def _validate_rights(rights: Any, where: str) -> Dict[str, Any]:
    if rights is None:
        return {"status": "unknown"}
    if not isinstance(rights, dict):
        raise DataError(f"{where}: 'rights' must be an object")
    _reject_unknown(rights, {"status", "license", "url", "terms", "note"}, where)
    status = rights.get("status", "unknown")
    if status not in ("known", "unknown"):
        raise DataError(f"{where}: 'rights.status' must be 'known' or 'unknown'")
    if rights.get("url") is not None:
        _validate_url(rights["url"], f"{where}.rights.url")
    for field in ("license", "terms", "note"):
        if rights.get(field) is not None:
            _check_metadata(_require_str(rights, field, where), f"{where}.rights.{field}")
    return rights


def _validate_specimen(specimen: Any, where: str) -> Dict[str, Any]:
    if not isinstance(specimen, dict):
        raise DataError(f"{where}: 'specimen' must be an object")
    _reject_unknown(specimen, {"entry", "source", "notes", "locator", "url"}, where)
    for field in ("entry", "source", "notes"):
        if specimen.get(field) is not None:
            _check_metadata(_require_str(specimen, field, where), f"{where}.specimen.{field}")
    if specimen.get("locator") is not None:
        _validate_locator(specimen["locator"], f"{where}.specimen.locator")
    if specimen.get("url") is not None:
        _validate_url(specimen["url"], f"{where}.specimen.url")
    return specimen


def _validate_evidence(evidence: Any, where: str) -> Dict[str, Any]:
    if not isinstance(evidence, dict):
        raise DataError(f"{where}: 'evidence' must be an object")
    _reject_unknown(evidence, {"rendered", "operated", "observed", "source", "previews", "case"}, where)
    for field in ("rendered", "operated"):
        if evidence.get(field) is not None and not isinstance(evidence[field], bool):
            raise DataError(f"{where}: 'evidence.{field}' must be a boolean")
    if evidence.get("observed") is not None:
        _validate_timestamp(evidence["observed"], f"{where}.evidence.observed")
    for field in ("source", "case"):
        if evidence.get(field) is not None:
            if not isinstance(evidence[field], dict):
                raise DataError(f"{where}: 'evidence.{field}' must be an object")
            for value in evidence[field].values():
                if isinstance(value, str):
                    _check_metadata(value, f"{where}.evidence.{field}")
    if evidence.get("previews") is not None:
        if not isinstance(evidence["previews"], list):
            raise DataError(f"{where}: 'evidence.previews' must be a list")
        for index, ref in enumerate(evidence["previews"]):
            _validate_reference(ref, f"{where}.evidence.previews[{index}]")
    return evidence


def _validate_item(item: Any, where: str) -> Dict[str, Any]:
    if not isinstance(item, dict):
        raise DataError(f"{where}: item must be an object")
    _reject_unknown(item, {"id", "revision", "title", "roles", "source", "tags", "previews",
                           "specimen", "making", "palette", "assets", "materials",
                           "derivation", "rights", "evidence", "archived", "summary"}, where)
    item_id = _require_str(item, "id", where)
    where = f"item '{item_id}'"
    _require_int(item, "revision", where, minimum=1)
    _check_metadata(_require_str(item, "title", where), f"{where}.title")
    roles = item.get("roles")
    if not isinstance(roles, list) or not roles:
        raise DataError(f"{where}: 'roles' must be a non-empty list")
    for role in roles:
        if role not in ROLES:
            raise DataError(f"{where}: unknown role {role!r}; allowed {list(ROLES)}")
    if item.get("archived") is not None and not isinstance(item["archived"], bool):
        raise DataError(f"{where}: 'archived' must be a boolean when present")
    if item.get("summary") is not None:
        _check_metadata(_require_str(item, "summary", where), f"{where}.summary")
    if item.get("source") is not None:
        _validate_source(item["source"], where)
    _validate_tags(item.get("tags"), where)
    _validate_previews(item.get("previews"), where)
    if item.get("specimen") is not None:
        _validate_specimen(item["specimen"], where)
    if item.get("making") is not None:
        _validate_making(item["making"], where)
    if item.get("palette") is not None:
        _validate_palette(item["palette"], where)
    _validate_assets(item.get("assets"), where)
    if item.get("materials") is not None:
        if not isinstance(item["materials"], list):
            raise DataError(f"{where}: 'materials' must be a list")
        for index, ref in enumerate(item["materials"]):
            _validate_reference(ref, f"{where}.materials[{index}]")
    if item.get("derivation") is not None:
        _validate_derivation(item["derivation"], where)
    if item.get("rights") is not None:
        _validate_rights(item["rights"], where)
    if item.get("evidence") is not None:
        _validate_evidence(item["evidence"], where)
    if "palette" in roles and item.get("palette") is None:
        raise DataError(f"{where}: role 'palette' requires a 'palette' block")
    # A positive instance (style/combination) must be *viewable*: it needs a
    # making relation, at least one preview, and a specimen entry point. A
    # palette is viewable through its role values and its instance relation.
    for positive in ("style", "combination"):
        if positive in roles:
            if item.get("making") is None:
                raise DataError(
                    f"{where}: role {positive!r} requires a 'making' block "
                    "(effect/carry/vary/limits)")
            if not item.get("previews"):
                raise DataError(
                    f"{where}: role {positive!r} requires at least one preview "
                    "(a positive instance must be viewable)")
            if item.get("specimen") is None:
                raise DataError(
                    f"{where}: role {positive!r} requires a 'specimen' block "
                    "(entry point and making notes)")
    if "palette" in roles and item.get("making") is None:
        raise DataError(f"{where}: role 'palette' requires a 'making' block (effect/carry/vary/limits)")
    return item


def _validate_use(use: Any, where: str) -> Dict[str, Any]:
    if not isinstance(use, dict):
        raise DataError(f"{where}: use must be an object")
    _reject_unknown(use, USE_FIELDS, where)
    use_id = _require_str(use, "id", where)
    where = f"use '{use_id}'"
    _require_int(use, "revision", where, minimum=1)
    target = use.get("target")
    if not isinstance(target, dict) or not target:
        raise DataError(f"{where}: 'target' must be a non-empty object")
    _reject_unknown(target, {"project", "surface", "location"}, f"{where}.target")
    _require_str(target, "project", f"{where}.target")
    if target.get("surface") is not None:
        _check_metadata(_require_str(target, "surface", f"{where}.target"), f"{where}.target.surface")
    location = target.get("location")
    if location is not None:
        if not isinstance(location, dict):
            raise DataError(f"{where}.target: 'location' must be an object")
        _reject_unknown(location, {"path", "region"}, f"{where}.target.location")
        if location.get("path") is not None:
            path = _require_str(location, "path", f"{where}.target.location")
            if path.startswith("/") or any(p == ".." for p in path.split("/")):
                raise DataError(f"{where}.target.location.path must be a relative, non-traversing path")
        if location.get("region") is not None:
            _check_metadata(_require_str(location, "region", f"{where}.target.location"),
                            f"{where}.target.location.region")
        if location.get("path") is None and location.get("region") is None:
            raise DataError(f"{where}.target.location needs 'path' or 'region'")
    refs = use.get("references")
    if not isinstance(refs, list) or not refs:
        raise DataError(f"{where}: 'references' must be a non-empty list")
    for index, ref in enumerate(refs):
        _validate_reference(ref, f"{where}.references[{index}]")
    _require_str(use, "relation", where)
    status = use.get("status")
    if status not in USE_STATUSES:
        raise DataError(f"{where}: 'status' must be one of {list(USE_STATUSES)}")
    if status == "in-use" and use.get("observed_at") is None:
        raise DataError(f"{where}: status 'in-use' requires 'observed_at'")
    if use.get("observed_at") is not None:
        _validate_timestamp(use["observed_at"], f"{where}.observed_at")
    if use.get("evidence") is not None:
        _validate_evidence(use["evidence"], where)
    return use


def _validate_document(document: Any, *, path_label: str) -> Dict[str, Any]:
    if not isinstance(document, dict):
        raise DataError(f"{path_label}: root must be a JSON object")
    _reject_unknown(document, {"version", "id", "revision", "items", "uses"}, path_label)
    version = document.get("version")
    if not _is_int(version) or version != SUPPORTED_VERSION:
        raise DataError(
            f"{path_label}: 'version' must be the integer {SUPPORTED_VERSION}, got "
            f"{version!r}; this helper refuses to guess at other formats"
        )
    _require_str(document, "id", path_label)
    revision = document.get("revision")
    if not _is_int(revision) or revision < 0:
        raise DataError(f"{path_label}: 'revision' must be an integer >= 0")
    items = document.get("items")
    if not isinstance(items, list):
        raise DataError(f"{path_label}: 'items' must be a list")
    uses = document.get("uses")
    if not isinstance(uses, list):
        raise DataError(f"{path_label}: 'uses' must be a list")
    seen_item_rev: set = set()
    for index, item in enumerate(items):
        validated = _validate_item(item, f"{path_label}.items[{index}]")
        key = (validated["id"], validated["revision"])
        if key in seen_item_rev:
            raise DataError(f"{path_label}.items[{index}]: duplicate (item_id, revision) {key!r}")
        seen_item_rev.add(key)
    seen_use_rev: set = set()
    for index, use in enumerate(uses):
        validated = _validate_use(use, f"{path_label}.uses[{index}]")
        key = (validated["id"], validated["revision"])
        if key in seen_use_rev:
            raise DataError(f"{path_label}.uses[{index}]: duplicate (use_id, revision) {key!r}")
        seen_use_rev.add(key)
    _validate_derivation_acyclic(document)
    return {
        "version": SUPPORTED_VERSION, "id": document["id"], "revision": revision,
        "items": items, "uses": uses,
    }


# ---------------------------------------------------------------------------
# Current / history projection
# ---------------------------------------------------------------------------

def _current_items(document: Dict[str, Any]) -> List[Dict[str, Any]]:
    best: Dict[str, Dict[str, Any]] = {}
    for item in document["items"]:
        current = best.get(item["id"])
        if current is None or item["revision"] > current["revision"]:
            best[item["id"]] = item
    return list(best.values())


def _current_uses(document: Dict[str, Any]) -> List[Dict[str, Any]]:
    best: Dict[str, Dict[str, Any]] = {}
    for use in document["uses"]:
        current = best.get(use["id"])
        if current is None or use["revision"] > current["revision"]:
            best[use["id"]] = use
    return list(best.values())


def _find_item(document: Dict[str, Any], item_id: str, revision: Optional[int]) -> Optional[Dict[str, Any]]:
    matches = [i for i in document["items"] if i["id"] == item_id]
    if not matches:
        return None
    if revision is None:
        return max(matches, key=lambda i: i["revision"])
    for item in matches:
        if item["revision"] == revision:
            return item
    return None


def _find_use(document: Dict[str, Any], use_id: str, revision: Optional[int]) -> Optional[Dict[str, Any]]:
    matches = [u for u in document["uses"] if u["id"] == use_id]
    if not matches:
        return None
    if revision is None:
        return max(matches, key=lambda u: u["revision"])
    for use in matches:
        if use["revision"] == revision:
            return use
    return None


def _item_history(document: Dict[str, Any], item_id: str) -> List[Dict[str, Any]]:
    return sorted((i for i in document["items"] if i["id"] == item_id),
                  key=lambda i: i["revision"], reverse=True)


def _uses_for_item(document: Dict[str, Any], item_id: str) -> List[Dict[str, Any]]:
    out = []
    for use in _current_uses(document):
        if any(ref["item_id"] == item_id for ref in use["references"]):
            out.append(use)
    return sorted(out, key=lambda u: u["id"])


# ---------------------------------------------------------------------------
# Catalogue loading
# ---------------------------------------------------------------------------

class Catalog:
    def __init__(self, path: Path, document: Dict[str, Any], *, exists: bool) -> None:
        self.path = Path(path)
        self.document = document
        self.exists = exists
        self.revision = document["revision"]
        self.id = document["id"]


def _load_catalog(catalog_arg: str, *, allow_missing: bool = False) -> Catalog:
    path = Path(catalog_arg)
    if not os.path.lexists(path):
        if allow_missing:
            return Catalog(path, _new_document(path.stem), exists=False)
        raise MissingError(f"catalogue does not exist: {path}")
    document = _load_json(path)
    validated = _validate_document(document, path_label=str(path))
    return Catalog(path, validated, exists=True)


def _load_bindings(args: argparse.Namespace, catalog: Catalog,
                   extra_ids: Optional[Iterable[str]] = None) -> RootBindings:
    bindings = RootBindings(catalog.id, catalog.path.parent)
    # Bind the primary catalogue's own roots; a root scoped to a dependency id
    # is resolved separately for that dependency. A root scoped to some third,
    # unknown id is not silently ignored.
    known_ids = {catalog.id, *(extra_ids or [])}
    declared = set()
    for spec in getattr(args, "root", []) or []:
        owner, alias, path = _parse_root_arg(catalog.id, spec)
        declared.add(owner)
        if owner == catalog.id:
            bindings.add_explicit(alias, path)
    unknown = declared - known_ids
    if unknown:
        raise UsageError(
            f"--root: no catalogue with id {sorted(unknown)} was supplied "
            f"(pass it as --with-catalog)"
        )
    return bindings


def _build_index(catalogs: Sequence[Catalog]) -> Dict[str, Catalog]:
    index: Dict[str, Catalog] = {}
    for catalog in catalogs:
        if catalog.id in index:
            raise DataError(
                f"ambiguous catalogue id '{catalog.id}': supplied by both "
                f"{index[catalog.id].path} and {catalog.path}"
            )
        index[catalog.id] = catalog
    return index


def _dependency_bindings(
    catalog_id: str,
    primary_bindings: RootBindings,
    argv_roots: Sequence[str],
    index: Dict[str, Catalog],
) -> RootBindings:
    """Bindings for a dependency catalogue: its own ``catalog`` root, plus any
    explicit roots the caller scoped to that dependency id."""
    catalog = index[catalog_id]
    bound = RootBindings(catalog_id, catalog.path.parent)
    for spec in argv_roots or []:
        if "=" not in spec:
            continue
        head, _, path = spec.partition("=")
        owner, sep, alias = head.partition(":")
        if owner == catalog_id and sep and alias and path:
            bound.add_explicit(alias, Path(path))
    return bound


# ---------------------------------------------------------------------------
# Reference checking (structure vs. resolution are kept separate)
# ---------------------------------------------------------------------------

def _check_reference(ref: Dict[str, Any], index: Dict[str, Catalog]) -> Dict[str, Any]:
    catalog = index.get(ref["catalog_id"])
    if catalog is None:
        return {"reference": dict(ref), "status": "unresolved-catalog",
                "required_catalog": ref["catalog_id"]}
    item = _find_item(catalog.document, ref["item_id"], ref.get("revision"))
    if item is None:
        any_item = [i for i in catalog.document["items"] if i["id"] == ref["item_id"]]
        status = "unresolved-revision" if any_item else "unresolved-item"
        return {"reference": dict(ref), "status": status, "catalog": catalog.id}
    if ref.get("asset_id") is not None:
        if ref["asset_id"] not in {a["id"] for a in (item.get("assets") or [])}:
            return {"reference": dict(ref), "status": "unresolved-asset", "catalog": catalog.id}
    if ref.get("preview_id") is not None:
        if ref["preview_id"] not in {p["id"] for p in (item.get("previews") or [])}:
            return {"reference": dict(ref), "status": "unresolved-preview", "catalog": catalog.id}
    return {"reference": dict(ref), "status": "resolved", "catalog": catalog.id}


def _all_references(item: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
    out: List[Tuple[str, Dict[str, Any]]] = []
    src = item.get("source")
    if isinstance(src, dict) and src.get("ref") is not None:
        out.append(("source.ref", src["ref"]))
    for index, ref in enumerate(item.get("materials") or []):
        out.append((f"materials[{index}]", ref))
    palette = item.get("palette")
    if isinstance(palette, dict) and palette.get("instance") is not None:
        out.append(("palette.instance", palette["instance"]))
    deriv = item.get("derivation")
    if isinstance(deriv, dict):
        for index, ref in enumerate(deriv.get("sources") or []):
            out.append((f"derivation.sources[{index}]", ref))
    return out


# A derivation node identity is (catalog_id, item_id, revision, asset_id). The
# item-level node (asset_id None) is what a derivation edge points at unless the
# reference names a specific asset.
DerivationNode = Tuple[str, str, int, Optional[str]]


def _derivation_node(catalog_id: str, item_id: str, revision: int,
                     asset_id: Optional[str]) -> DerivationNode:
    return (catalog_id, item_id, revision, asset_id)


def _require_exact_derivation_assets(item: Dict[str, Any], index: Dict[str, "Catalog"]) -> None:
    """Derivation sources must name an exact revision, and an exact asset when
    the source item actually has assets (a bare item reference is not enough to
    reproduce a product derived from a specific original)."""
    deriv = item.get("derivation")
    if not isinstance(deriv, dict):
        return
    for index_i, ref in enumerate(deriv.get("sources") or []):
        catalog = index.get(ref["catalog_id"])
        if catalog is None:
            raise DataError(
                f"item '{item['id']}' derivation.sources[{index_i}] needs catalogue "
                f"'{ref['catalog_id']}' (pass --with-catalog)")
        target = _find_item(catalog.document, ref["item_id"], ref["revision"])
        if target is None:
            raise DataError(
                f"item '{item['id']}' derivation.sources[{index_i}] does not resolve to "
                f"{ref['catalog_id']}:{ref['item_id']}@{ref['revision']}")
        source_assets = target.get("assets") or []
        if source_assets and ref.get("asset_id") is None:
            raise DataError(
                f"item '{item['id']}' derivation.sources[{index_i}] must name an exact "
                f"'asset_id' of its source item (which has {len(source_assets)} assets)")
        if ref.get("asset_id") is not None and ref["asset_id"] not in {a["id"] for a in source_assets}:
            raise DataError(
                f"item '{item['id']}' derivation.sources[{index_i}] asset_id "
                f"'{ref['asset_id']}' is not an asset of {ref['item_id']}@{ref['revision']}")


def _derivation_edges(
    documents: Dict[str, Dict[str, Any]],
) -> Dict[DerivationNode, List[DerivationNode]]:
    """Edges for derivation dependency: output node -> exact source node.

    Nodes are keyed by full identity ``(catalog_id, item_id, revision,
    asset_id)`` across every supplied document. A source that resolves to an
    exact item (optionally an exact asset) in a supplied catalogue produces an
    edge; a reference to an unsupplied catalogue or a missing revision/asset
    stays unresolved and is reported, never guessed.
    """
    known: set = set()
    for catalog_id, document in documents.items():
        for item in document["items"]:
            known.add(_derivation_node(catalog_id, item["id"], item["revision"], None))
            for asset in item.get("assets") or []:
                known.add(_derivation_node(catalog_id, item["id"], item["revision"], asset["id"]))
    edges: Dict[DerivationNode, List[DerivationNode]] = {}
    unresolved: List[Dict[str, Any]] = []
    for catalog_id, document in documents.items():
        for item in document["items"]:
            node = _derivation_node(catalog_id, item["id"], item["revision"], None)
            edges.setdefault(node, [])
            deriv = item.get("derivation")
            if not isinstance(deriv, dict):
                continue
            for index, ref in enumerate(deriv.get("sources") or []):
                target = _derivation_node(ref["catalog_id"], ref["item_id"], ref["revision"],
                                          ref.get("asset_id"))
                if target in known:
                    edges[node].append(target)
                else:
                    unresolved.append({
                        "catalog_id": catalog_id, "item_id": item["id"],
                        "revision": item["revision"], "where": f"derivation.sources[{index}]",
                        "reference": dict(ref), "status": "unresolved-derivation-source",
                    })
    return edges, unresolved


def _find_derivation_cycle(
    edges: Dict[DerivationNode, List[DerivationNode]],
) -> Optional[List[DerivationNode]]:
    state: Dict[DerivationNode, int] = {}
    stack: List[DerivationNode] = []
    on_stack: Dict[DerivationNode, int] = {}

    def visit(node: DerivationNode) -> Optional[List[DerivationNode]]:
        state[node] = 1
        on_stack[node] = len(stack)
        stack.append(node)
        for nxt in edges.get(node, []):
            if state.get(nxt, 0) == 1:
                return stack[on_stack[nxt]:] + [nxt]
            if state.get(nxt, 0) == 0:
                found = visit(nxt)
                if found is not None:
                    return found
        stack.pop()
        on_stack.pop(node, None)
        state[node] = 2
        return None

    for node in edges:
        if state.get(node, 0) == 0:
            found = visit(node)
            if found is not None:
                return found
    return None


def _node_label(node: DerivationNode) -> str:
    catalog_id, item_id, revision, asset_id = node
    return f"{catalog_id}:{item_id}@{revision}" + (f"#{asset_id}" if asset_id else "")


def _validate_derivation_acyclic(
    document: Dict[str, Any], *, extra_documents: Optional[Dict[str, Dict[str, Any]]] = None,
) -> None:
    documents = {document["id"]: document}
    if extra_documents:
        documents.update(extra_documents)
    edges, _unresolved = _derivation_edges(documents)
    cycle = _find_derivation_cycle(edges)
    if cycle is not None:
        chain = " -> ".join(_node_label(node) for node in cycle)
        raise DataError(f"derivation cycle detected (must be acyclic): {chain}")


def _derivation_unresolved(
    document: Dict[str, Any], *, extra_documents: Optional[Dict[str, Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    documents = {document["id"]: document}
    if extra_documents:
        documents.update(extra_documents)
    _edges, unresolved = _derivation_edges(documents)
    return unresolved


def _active_schemes_in_strings(value: Any, path: str = "") -> List[str]:
    """Collect metadata strings that embed an active URL scheme (javascript: etc.)."""
    found: List[str] = []
    if isinstance(value, str):
        if value.strip().lower().startswith(("javascript:", "vbscript:")):
            found.append(path or "<root>")
    elif isinstance(value, dict):
        for key, item in value.items():
            found.extend(_active_schemes_in_strings(item, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(_active_schemes_in_strings(item, f"{path}[{index}]"))
    return found


# ---------------------------------------------------------------------------
# resolve
# ---------------------------------------------------------------------------

def _resolve_locator_file(
    locator: Dict[str, str], bindings: RootBindings, *, where: str,
    expected_digest: Optional[str],
) -> Dict[str, Any]:
    try:
        root = bindings.resolve_root(locator["root"], where=where)
    except MissingError as exc:
        return {"status": "unavailable", "reason": str(exc),
                "locator": {"root": locator["root"], "path": locator["path"]}}
    try:
        real = _safe_under(root, locator["path"], where)
    except DataError as exc:
        return {"status": "unavailable", "reason": str(exc),
                "locator": {"root": locator["root"], "path": locator["path"]}}
    out: Dict[str, Any] = {"locator": {"root": locator["root"], "path": locator["path"]},
                           "path": str(real)}
    if not os.path.lexists(real):
        out["status"] = "missing"
        return out
    if os.path.islink(real) or not real.is_file():
        out["status"] = "missing"
        out["reason"] = "not a regular file"
        return out
    actual = _file_sha256(real)
    out["sha256"] = actual
    if expected_digest is None:
        out["status"] = "available"
        out["digest_note"] = "no recorded digest; present but unverified"
    elif expected_digest == actual:
        out["status"] = "available"
    else:
        out["status"] = "changed"
        out["expected_sha256"] = expected_digest
    return out


def _resolve_asset(asset: Dict[str, Any], bindings: RootBindings, *, where: str) -> Dict[str, Any]:
    if asset.get("locator") is None:
        if asset.get("url"):
            return {"asset_id": asset.get("id"), "status": "remote-only", "url": asset["url"]}
        return {"asset_id": asset.get("id"), "status": "unavailable", "reason": "no locator and no url"}
    out = _resolve_locator_file(asset["locator"], bindings, where=where,
                                expected_digest=asset.get("sha256"))
    out["asset_id"] = asset.get("id")
    return out


def _resolve_preview(preview: Dict[str, Any], bindings: RootBindings, *, where: str) -> Dict[str, Any]:
    if preview.get("locator") is None:
        status = "remote-only" if preview.get("url") else "unavailable"
        return {"preview_id": preview.get("id"), "status": status}
    out = _resolve_locator_file(preview["locator"], bindings, where=where,
                                expected_digest=preview.get("digest"))
    out["preview_id"] = preview.get("id")
    return out


def _describe_item(item: Dict[str, Any], catalog: Catalog, index: Dict[str, Catalog],
                   *, simple: bool) -> Dict[str, Any]:
    entry: Dict[str, Any] = {
        "catalog_id": catalog.id,
        "id": item["id"],
        "revision": item["revision"],
        "title": item["title"],
        "roles": item.get("roles", []),
        "archived": bool(item.get("archived", False)),
        "tags": item.get("tags", {}),
        "reference": {"catalog_id": catalog.id, "item_id": item["id"], "revision": item["revision"]},
    }
    if item.get("summary"):
        entry["summary"] = item["summary"]
    entry["preview_entries"] = [
        {"catalog_id": catalog.id, "item_id": item["id"], "revision": item["revision"], "preview_id": p["id"]}
        for p in (item.get("previews") or [])
    ]
    entry["asset_entries"] = [
        {"catalog_id": catalog.id, "item_id": item["id"], "revision": item["revision"], "asset_id": a["id"]}
        for a in (item.get("assets") or [])
    ]
    if not simple:
        for field in ("source", "specimen", "making", "palette", "derivation", "rights", "evidence"):
            if item.get(field) is not None:
                entry[field] = item[field]
        entry["previews"] = item.get("previews", [])
        entry["assets"] = item.get("assets", [])
        if item.get("materials"):
            entry["materials"] = item["materials"]
        entry["reference_state"] = [
            {"where": where, "result": _check_reference(ref, index)}
            for where, ref in _all_references(item)
        ]
    return entry


_CURSOR_VERSION = 1

def _query_filters(args: argparse.Namespace) -> Dict[str, Any]:
    return {
        "role": args.role, "task": args.task, "language": args.language,
        "medium": args.medium, "source": args.source, "terms": list(args.term or []),
        "include_archived": bool(args.include_archived),
    }

def _make_cursor(args: argparse.Namespace, revisions: Dict[str, int], offset: int) -> str:
    """Opaque, bounded continuation token for a query page.

    Binds the result filters, the exact catalogue set with each collection's
    whole-file revision, and the next offset. It is a stable serialization of
    those facts, not a hidden store: a continuation is accepted only with the same
    filters and unchanged revisions, so a stale page is
    rejected instead of silently stitched.
    """
    payload = {
        "v": _CURSOR_VERSION,
        "filters": _query_filters(args),
        "revisions": dict(sorted(revisions.items())),
        "offset": offset,
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return base64.urlsafe_b64encode(blob.encode("utf-8")).decode("ascii")

def _decode_cursor(token: str) -> Dict[str, Any]:
    try:
        raw = base64.urlsafe_b64decode(token.encode("ascii"))
        payload = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        raise UsageError("--cursor is malformed; re-run the query without --cursor")
    if not isinstance(payload, dict) or payload.get("v") != _CURSOR_VERSION:
        raise UsageError("--cursor has an unsupported version; re-run the query without --cursor")
    if not isinstance(payload.get("filters"), dict) or not isinstance(payload.get("revisions"), dict) \
            or not isinstance(payload.get("offset"), int) or payload["offset"] < 0:
        raise UsageError("--cursor is malformed; re-run the query without --cursor")
    return payload

def cmd_query(args: argparse.Namespace) -> Tuple[int, Dict[str, Any]]:
    catalog = _load_catalog(args.catalog)
    dependencies = [_load_catalog(p) for p in (args.with_catalog or [])]
    bindings = _load_bindings(args, catalog, [d.id for d in dependencies])
    catalogs = [catalog] + dependencies
    index = _build_index(catalogs)

    # Resolve the page position. A --cursor is a stale-safe continuation bound
    # to the filters and catalogue revisions; --offset is unguarded manual
    # paging and makes no stale-safe claim. The two are mutually exclusive.
    if getattr(args, "cursor", None) is not None:
        if args.offset:
            raise UsageError("--cursor and --offset are mutually exclusive")
        payload = _decode_cursor(args.cursor)
        if payload["filters"] != _query_filters(args):
            raise UsageError(
                "--cursor does not match the supplied filters; re-run the query")
        revisions_now = {source.id: source.revision for source in catalogs}
        if payload["revisions"] != dict(sorted(revisions_now.items())):
            raise ConflictError(
                "a catalogue changed since this cursor was issued; re-run the query")
        offset = payload["offset"]
        guarded = True
    else:
        offset = args.offset
        guarded = False

    candidates: List[Dict[str, Any]] = []
    for source in catalogs:
        for item in _current_items(source.document):
            ok, terms = _matches_item(item, args)
            if ok:
                candidates.append({"catalog": source, "item": item, "matched_terms": terms})

    used_pairs = {
        (ref["catalog_id"], ref["item_id"])
        for source in catalogs
        for use in _current_uses(source.document)
        for ref in use["references"]
    }
    candidates.sort(key=lambda c: (
        0 if (c["catalog"].id, c["item"]["id"]) in used_pairs else 1,
        c["catalog"].id, c["item"]["id"],
    ))
    revisions = {source.id: source.revision for source in catalogs}
    page = candidates[offset:offset + args.limit]
    next_offset = offset + len(page)
    truncated = next_offset < len(candidates)
    return EXIT_OK, {
        "ok": True,
        "status": "matched" if candidates else "no_match",
        "mode": "lexical" if args.term else "browse",
        "terms": list(args.term or []),
        "filters": {"role": args.role, "task": args.task, "language": args.language,
                    "medium": args.medium, "source": args.source,
                    "include_archived": args.include_archived},
        "revisions": revisions,
        "offset": offset,
        "limit": args.limit,
        "guarded": guarded,
        "matched": len(candidates),
        "returned": len(page),
        "next_offset": next_offset if truncated else None,
        "next_cursor": _make_cursor(args, revisions, next_offset) if truncated else None,
        "truncated": truncated,
        "items": [_describe_item(c["item"], c["catalog"], index, simple=True) for c in page],
    }


def _matches_item(item: Dict[str, Any], args: argparse.Namespace) -> Tuple[bool, List[str]]:
    if args.role and args.role not in (item.get("roles") or []):
        return False, []
    tags = item.get("tags") or {}
    if args.task and args.task not in (tags.get("tasks") or []):
        return False, []
    if args.language and args.language not in (tags.get("languages") or []):
        return False, []
    if args.medium and args.medium not in (tags.get("media") or []):
        return False, []
    if args.source and args.source != (item.get("source") or {}).get("kind"):
        return False, []
    if item.get("archived") is True and not args.include_archived:
        return False, []
    matched_terms: List[str] = []
    if args.term:
        haystack: List[str] = [item.get("id", ""), item.get("title", "")]
        if item.get("summary"):
            haystack.append(item["summary"])
        for key in ("tasks", "languages", "media", "scales", "terms"):
            haystack.extend(tags.get(key, []) or [])
        for term in args.term:
            needle = term.casefold()
            if any(needle in value.casefold() for value in haystack):
                matched_terms.append(term)
        if not matched_terms:
            return False, []
    return True, matched_terms


def cmd_show(args: argparse.Namespace) -> Tuple[int, Dict[str, Any]]:
    catalog = _load_catalog(args.catalog)
    dependencies = [_load_catalog(p) for p in (args.with_catalog or [])]
    bindings = _load_bindings(args, catalog, [d.id for d in dependencies])
    index = _build_index([catalog] + dependencies)

    item = _find_item(catalog.document, args.id, args.revision)
    if item is None:
        use = _find_use(catalog.document, args.id, args.revision)
        if use is None:
            return EXIT_NOT_FOUND, {"ok": False, "status": "not_found",
                                    "catalog_id": catalog.id, "id": args.id, "revision": args.revision}
        return EXIT_OK, {
            "ok": True, "status": "use", "catalog_id": catalog.id, "use": use,
            "reference_state": [
                {"where": f"references[{i}]", "result": _check_reference(ref, index)}
                for i, ref in enumerate(use["references"])
            ],
        }

    current = _find_item(catalog.document, args.id, None)
    return EXIT_OK, {
        "ok": True,
        "status": "item",
        "catalog_id": catalog.id,
        "current": current["revision"] == item["revision"],
        "item": _describe_item(item, catalog, index, simple=False),
        "history": [{"revision": rev["revision"], "archived": bool(rev.get("archived", False))}
                    for rev in _item_history(catalog.document, args.id)],
        "uses": [{"id": u["id"], "revision": u["revision"], "status": u["status"], "target": u.get("target")}
                 for u in _uses_for_item(catalog.document, args.id)],
        "note": "show reads recorded structure; it does not claim any file was viewed",
    }


def _bindings_for_ref(ref: Dict[str, Any], catalog: Catalog, bindings: RootBindings,
                      argv_roots: Sequence[str], index: Dict[str, "Catalog"]) -> RootBindings:
    """Root bindings for the collection a reference names.

    A reference into another catalogue resolves against that catalogue's own
    ``catalog`` root plus any roots the caller scoped to its id. A reference
    into the primary catalogue uses the primary bindings.
    """
    if ref["catalog_id"] == catalog.id:
        return bindings
    return _dependency_bindings(ref["catalog_id"], bindings, argv_roots, index)


def _resolve_reference_media(ref: Dict[str, Any], catalog: Catalog, bindings: RootBindings,
                             argv_roots: Sequence[str], index: Dict[str, "Catalog"],
                             *, where: str) -> List[Dict[str, Any]]:
    """Resolve the exact media a reference names, honouring its selector.

    A reference with ``asset_id`` returns that one asset; with ``preview_id``
    that one preview; with neither, every asset and preview of the target item.
    This is why a preview reference must not dump the target's unrelated assets.
    """
    state = _check_reference(ref, index)
    if state["status"] != "resolved":
        return [{"where": where, "reference": dict(ref), "status": state["status"],
                 "required_catalog": state.get("required_catalog")}]
    target_catalog = index[ref["catalog_id"]]
    target = _find_item(target_catalog.document, ref["item_id"], ref.get("revision"))
    bound = _bindings_for_ref(ref, catalog, bindings, argv_roots, index)
    via = {"catalog_id": ref["catalog_id"], "item_id": ref["item_id"],
           "revision": ref.get("revision")}
    out: List[Dict[str, Any]] = []
    for asset in target.get("assets") or []:
        if ref.get("asset_id") is not None and asset["id"] != ref["asset_id"]:
            continue
        if ref.get("preview_id") is not None:
            continue  # a preview selector does not pull this item's assets
        resolved = _resolve_asset(asset, bound, where=where)
        resolved["via"] = {**via, "asset_id": asset["id"]}
        out.append(resolved)
    for preview in target.get("previews") or []:
        if ref.get("preview_id") is not None and preview["id"] != ref["preview_id"]:
            continue
        if ref.get("asset_id") is not None:
            continue  # an asset selector does not pull this item's previews
        resolved = _resolve_preview(preview, bound, where=where)
        resolved["via"] = {**via, "preview_id": preview["id"]}
        out.append(resolved)
    if not out and (target.get("assets") or target.get("previews")):
        out.append({"where": where, "reference": dict(ref), "status": "unresolved-selector",
                    "reason": "selector matches no asset/preview of the referenced item"})
    return out


def _resolve_locator_entry(locator: Any, bindings: RootBindings, *, where: str,
                           kind: str) -> Dict[str, Any]:
    """Resolve a bare locator (specimen, derivation script) the same way as media."""
    if locator is None:
        return {"where": where, "status": "unavailable", "reason": "no locator recorded"}
    resolved = _resolve_locator_file(locator, bindings, where=where, expected_digest=None)
    resolved["where"] = where
    resolved["kind"] = kind
    return resolved


def cmd_resolve(args: argparse.Namespace) -> Tuple[int, Dict[str, Any]]:
    catalog = _load_catalog(args.catalog)
    dependencies = [_load_catalog(p) for p in (args.with_catalog or [])]
    bindings = _load_bindings(args, catalog, [d.id for d in dependencies])
    index = _build_index([catalog] + dependencies)

    item = _find_item(catalog.document, args.id, args.revision)
    if item is None:
        return EXIT_NOT_FOUND, {"ok": False, "status": "not_found",
                                "catalog_id": catalog.id, "id": args.id, "revision": args.revision}

    reference_state = [
        {"where": where, "result": _check_reference(ref, index)}
        for where, ref in _all_references(item)
    ]
    unresolved = [r for r in reference_state if r["result"]["status"] != "resolved"]

    assets_out: List[Dict[str, Any]] = []
    previews_out: List[Dict[str, Any]] = []
    for asset in item.get("assets") or []:
        assets_out.append(_resolve_asset(asset, bindings, where=f"assets.{asset['id']}"))
    for preview in item.get("previews") or []:
        previews_out.append(_resolve_preview(preview, bindings, where=f"previews.{preview['id']}"))

    # A bounded continuation bundle: the exact files and notes a later worker
    # needs to resume, resolved with the same locator rules and never executed.
    specimen = item.get("specimen") or {}
    specimen_out: Optional[Dict[str, Any]] = None
    if item.get("specimen") is not None:
        specimen_out = {
            "entry": specimen.get("entry"),
            "source": specimen.get("source"),
            "notes": specimen.get("notes"),
            "url": specimen.get("url"),
        }
        if specimen.get("locator") is not None:
            specimen_out["media"] = _resolve_locator_entry(
                specimen["locator"], bindings, where="specimen.locator", kind="specimen")
        else:
            # A specimen may legitimately record only an entry command and notes.
            # "not-recorded" is an explicit gap, not a broken file, so it does
            # not by itself make the whole resolution partial.
            specimen_out["media"] = {"where": "specimen.locator", "status": "not-recorded",
                                     "reason": "no specimen locator recorded"}

    making = item.get("making") or {}
    making_out = None
    if item.get("making") is not None:
        # Making notes are data copied verbatim; the helper never runs them.
        making_out = {k: making[k] for k in ("effect", "carry", "vary", "limits")
                      if k in making}

    derivation = item.get("derivation") or {}
    derivation_out: Optional[Dict[str, Any]] = None
    if item.get("derivation") is not None:
        derivation_out = {
            "steps": derivation.get("steps"),
            "inputs": derivation.get("inputs"),
            "outputs": derivation.get("outputs"),
        }
        if derivation.get("script") is not None:
            derivation_out["script"] = _resolve_locator_entry(
                derivation["script"], bindings, where="derivation.script", kind="recipe")
        else:
            derivation_out["script"] = {"where": "derivation.script", "status": "not-recorded",
                                        "reason": "no script locator recorded"}
        derivation_out["sources"] = []
        for i, ref in enumerate(derivation.get("sources") or []):
            derivation_out["sources"].extend(_resolve_reference_media(
                ref, catalog, bindings, args.root, index, where=f"derivation.sources[{i}]"))

    materials_out: List[Dict[str, Any]] = []
    for i, ref in enumerate(item.get("materials") or []):
        materials_out.extend(_resolve_reference_media(
            ref, catalog, bindings, args.root, index, where=f"materials[{i}]"))

    bundle = {
        "source": item.get("source"),
        "specimen": specimen_out,
        "making": making_out,
        "derivation": derivation_out,
        "materials": materials_out,
    }

    summary = {status: sum(1 for a in assets_out if a["status"] == status) for status in ASSET_STATUSES}
    bundle_entries = []
    for section in ("specimen", "derivation"):
        data = bundle.get(section)
        if isinstance(data, dict):
            if isinstance(data.get("media"), dict):
                bundle_entries.append(data["media"])
            if isinstance(data.get("script"), dict):
                bundle_entries.append(data["script"])
            for source in data.get("sources") or []:
                if isinstance(source, dict) and "status" in source:
                    bundle_entries.append(source)
    bundle_entries.extend(e for e in materials_out if isinstance(e, dict) and "status" in e)
    bundle_ok = all(
        e.get("status") in ("available", "remote-only", "not-recorded")
        for e in (assets_out + previews_out + bundle_entries)
    )
    fully_ok = not unresolved and bundle_ok
    payload = {
        "ok": True,
        "status": "resolved" if fully_ok else "partial",
        "catalog_id": catalog.id,
        "id": item["id"],
        "revision": item["revision"],
        "reference_state": reference_state,
        "unresolved_references": [r["result"] for r in unresolved],
        "assets": assets_out,
        "asset_summary": summary,
        "previews": previews_out,
        "source": item.get("source"),
        "bundle": bundle,
        "note": ("resolve checks local files against recorded digests and returns the exact "
                 "specimen/recipe/material files needed to resume; it never downloads, uploads, "
                 "or executes a recorded script"),
    }
    return (EXIT_OK if fully_ok else EXIT_MISSING), payload


# ---------------------------------------------------------------------------
# Atomic writes, locks, media retention
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _write_temp(target: Path, data: bytes) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=str(target.parent))
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    return Path(tmp_name)


def _atomic_write_json(path: Path, document: Dict[str, Any]) -> None:
    data = json.dumps(document, ensure_ascii=False, indent=2).encode("utf-8")
    tmp = _write_temp(path, data)
    os.replace(tmp, path)
    _fsync_dir(path.parent)


def _fsync_dir(path: Path) -> None:
    try:
        fd = os.open(str(path), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


class FileLock:
    """Bounded OS advisory lock spanning read-check-write.

    Uses ``fcntl.flock`` where available and an exclusive lock directory
    otherwise. A held lock is never removed based on its age; a stale lock left
    by a crashed process is reported as ``busy`` rather than guessed at.
    """

    def __init__(self, target: Path, timeout: float = 5.0, poll: float = 0.02) -> None:
        self.lock_path = target.parent / (target.name + ".lock")
        self.timeout = timeout
        self.poll = poll
        self._handle = None
        self._dir_locked = False

    def __enter__(self) -> "FileLock":
        import time
        deadline = time.monotonic() + self.timeout
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        while True:
            if _fcntl is not None:
                handle = open(self.lock_path, "a+")
                try:
                    _fcntl.flock(handle.fileno(), _fcntl.LOCK_EX | _fcntl.LOCK_NB)
                    self._handle = handle
                    return self
                except OSError as exc:
                    handle.close()
                    if exc.errno not in (errno.EACCES, errno.EAGAIN, errno.EWOULDBLOCK):
                        raise
            else:  # pragma: no cover - non-POSIX fallback
                try:
                    os.mkdir(self.lock_path)
                    self._dir_locked = True
                    return self
                except FileExistsError:
                    pass
            if time.monotonic() >= deadline:
                raise LockBusyError(f"catalogue is locked by another writer: {self.lock_path}")
            time.sleep(self.poll)

    def __exit__(self, *exc: Any) -> None:
        if self._handle is not None:
            try:
                if _fcntl is not None:
                    _fcntl.flock(self._handle.fileno(), _fcntl.LOCK_UN)
            finally:
                self._handle.close()
                self._handle = None
        if self._dir_locked:  # pragma: no cover - non-POSIX fallback
            try:
                os.rmdir(self.lock_path)
            except OSError:
                pass
            self._dir_locked = False



def _retain_file(source_root: Path, path: str, target_dir: Path, *, where: str,
                 commit: bool = True) -> Dict[str, str]:
    """Copy one real file into the immutable media store.

    The immutable name is ``media/sha256/<digest><suffix>``. An existing file
    with the same digest is reused; a different file is never overwritten. When
    ``commit`` is False the digest and canonical locator are computed but nothing
    is written, so an idempotency check never mutates the store.
    """
    source = _safe_under(source_root, path, where)
    if not os.path.lexists(source) or os.path.islink(source) or not source.is_file():
        raise MissingError(f"{where}: retain file is not a readable regular file: {path}")
    data = source.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    suffix = source.suffix.lower()
    if not commit:
        return {"digest": digest,
                "locator": {"root": "catalog", "path": f"media/sha256/{digest}{suffix}"}}
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{digest}{suffix}"
    if os.path.lexists(target):
        if target.is_symlink() or _file_sha256(target) != digest:
            raise DataError(f"immutable media collision for {digest}: existing file differs")
    else:
        tmp = _write_temp(target, data)
        os.replace(tmp, target)
    return {"digest": digest,
            "locator": {"root": "catalog", "path": f"media/sha256/{digest}{suffix}"}}


def _retain_media(catalog: Catalog, bindings: RootBindings,
                  record: Dict[str, Any]) -> List[Dict[str, str]]:
    """Retain files named in the record's ``retain`` list.

    Each entry is ``{"id", "root", "path"}``; the returned entries carry the
    retain id, the content digest, and the canonical locator.
    """
    retained: List[Dict[str, str]] = []
    target_dir = _safe_under(catalog.path.parent, "media/sha256", "retained media")
    for entry in record.get("retain", []) or []:
        source_root = bindings.resolve_root(entry["root"], where="retain.root")
        result = _retain_file(source_root, entry["path"], target_dir, where="retain.path")
        retained.append({"retain_id": entry.get("id"), **result})
    return retained


def _validate_retain(record: Dict[str, Any], where: str) -> None:
    retain = record.get("retain")
    if retain is None:
        return
    if not isinstance(retain, list):
        raise DataError(f"{where}: 'retain' must be a list")
    seen = set()
    for index, entry in enumerate(retain):
        ewhere = f"{where}.retain[{index}]"
        if not isinstance(entry, dict):
            raise DataError(f"{ewhere}: must be an object")
        _reject_unknown(entry, {"id", "root", "path", "kind"}, ewhere)
        rid = _require_str(entry, "id", ewhere)
        if rid in seen:
            raise DataError(f"{ewhere}: duplicate retain id {rid!r}")
        seen.add(rid)
        _require_str(entry, "root", ewhere)
        _require_str(entry, "path", ewhere)
        if entry["path"].startswith("/") or any(p == ".." for p in entry["path"].split("/")):
            raise DataError(f"{ewhere}: 'path' must be a relative, non-traversing path")


def _observed_digest(locator: Any, bindings: RootBindings, *, where: str) -> Optional[str]:
    """SHA-256 of a local file a concrete locator points at, or None.

    Used to record the real content identity of a linked (not retained) file.
    A locator whose root is unbound or whose file is absent/irregular returns
    None: the helper never fabricates a digest it did not read.
    """
    if not isinstance(locator, dict):
        return None
    try:
        root = bindings.resolve_root(locator["root"], where=where)
        real = _safe_under(root, locator["path"], where)
    except (MissingError, DataError, KeyError):
        return None
    if not os.path.lexists(real) or os.path.islink(real) or not real.is_file():
        return None
    return _file_sha256(real)

def _materialize_item(
    record: Dict[str, Any],
    media: List[Dict[str, str]],
    bindings: RootBindings,
    catalog: Catalog,
    *,
    commit: bool = True,
) -> Dict[str, Any]:
    """Copy an item payload, retaining inline ``input_locator`` media.

    Two ways to retain media are supported: a top-level ``retain`` list whose
    entries are referenced by ``{"root": "retain", "path": "<retain id>"}``, and
    an inline ``input_locator`` on an asset or preview. In both cases the helper
    copies the real file, records its digest, and rewrites the locator to the
    immutable ``catalog`` path.
    """
    target_dir = _safe_under(catalog.path.parent, "media/sha256", "retained media")

    def resolve(value: Any) -> Any:
        if isinstance(value, dict):
            if value.get("root") == "retain":
                key = value.get("path")
                match = next((m for m in media
                              if m["retain_id"] == key or m["digest"] == key), None)
                if match is None:
                    raise DataError(f"locator references unknown retain id {key!r}")
                return dict(match["locator"])
            return {k: resolve(v) for k, v in value.items()}
        if isinstance(value, list):
            return [resolve(v) for v in value]
        return value

    item = resolve(record["item"])
    for asset in item.get("assets", []) or []:
        inline = asset.pop("input_locator", None)
        if inline is not None:
            root = bindings.resolve_root(inline["root"], where="asset.input_locator")
            result = _retain_file(root, inline["path"], target_dir,
                                  where="asset.input_locator", commit=commit)
            asset["locator"] = result["locator"]
            asset["sha256"] = result["digest"]
        locator = asset.get("locator")
        if isinstance(locator, dict) and locator.get("root") == "catalog" \
                and str(locator.get("path", "")).startswith("media/sha256/"):
            asset.setdefault("sha256", Path(locator["path"]).stem)
        elif locator is not None and asset.get("sha256") is None:
            # A concrete local locator (not retained) records the real digest of
            # the file it currently points at, so `resolve` can detect change.
            # A missing or unbound file simply keeps no digest; nothing is faked.
            got = _observed_digest(locator, bindings, where=f"assets.{asset.get('id')}")
            if got is not None:
                asset["sha256"] = got
    for preview in item.get("previews", []) or []:
        inline = preview.pop("input_locator", None)
        if inline is not None:
            root = bindings.resolve_root(inline["root"], where="preview.input_locator")
            result = _retain_file(root, inline["path"], target_dir,
                                  where="preview.input_locator", commit=commit)
            preview["locator"] = result["locator"]
            preview["digest"] = result["digest"]
        locator = preview.get("locator")
        if isinstance(locator, dict) and locator.get("root") == "catalog" \
                and str(locator.get("path", "")).startswith("media/sha256/"):
            preview.setdefault("digest", Path(locator["path"]).stem)
        elif locator is not None and preview.get("digest") is None:
            got = _observed_digest(locator, bindings, where=f"previews.{preview.get('id')}")
            if got is not None:
                preview["digest"] = got
    return item


# Fields the helper generates and therefore ignores when deciding whether a
# submission is *already present unchanged*. Only the top-level object of an
# item/use is normalised this way; ``revision`` inside any reference is part of
# that reference's identity and is compared exactly.
_GENERATED_TOP_LEVEL = ("revision",)
_GENERATED_USE_TOP_LEVEL = ("revision", "observed_at")


def _canonicalise_retained(value: Any) -> Any:
    """Canonicalise any object that carries a retained-media locator.

    A retained asset/preview identifies content by the digest embedded in its
    immutable ``catalog`` path, not by the input path it was copied from. The
    digest field (``sha256``/``digest``) is a generated fact, so it is dropped
    when it already appears in the locator path. Dispatch is by *shape* (does
    the dict carry a retained ``locator``?), not by nesting depth, so it reaches
    ``assets``/``previews`` list elements as well as a direct ``locator``,
    without mangling a locator that is not itself retained media.
    """
    if isinstance(value, dict):
        locator = value.get("locator")
        retained = (isinstance(locator, dict) and locator.get("root") == "catalog"
                    and str(locator.get("path", "")).startswith("media/sha256/"))
        out = {key: _canonicalise_retained(item) for key, item in value.items()}
        if retained:
            digest = Path(str(locator["path"])).stem
            out["locator"] = {"root": "catalog", "path": f"media/sha256/{digest}"}
            out.pop("sha256", None)
            out.pop("digest", None)
        return out
    if isinstance(value, list):
        return [_canonicalise_retained(item) for item in value]
    return value

def _compare_shape(value: Any, *, top_level: bool, kind: Optional[str]) -> Any:
    """Drop generated top-level fields; preserve every nested identity exactly."""
    if isinstance(value, dict):
        generated = _GENERATED_USE_TOP_LEVEL if kind == "use" else _GENERATED_TOP_LEVEL
        out = {}
        for key, item in value.items():
            if top_level and key in generated:
                continue
            out[key] = _compare_shape(item, top_level=False, kind=kind)
        return out
    if isinstance(value, list):
        return [_compare_shape(item, top_level=False, kind=kind) for item in value]
    return value

def _normalise_for_compare(value: Any, *, kind: str) -> Any:
    """Normalise an item/use for semantic idempotency.

    Only the top-level generated fields are dropped. Identity inside any
    reference (``revision``, ``asset_id``, ``preview_id``) and inside nested
    structures is preserved, so a changed exact dependency is never mistaken for
    an unchanged submission. Retained-media locators are canonicalised wherever
    they appear, so re-copying an identical file is not seen as a change.
    """
    return _canonicalise_retained(_compare_shape(value, top_level=True, kind=kind))


def _current_item(document: Dict[str, Any], item_id: str) -> Optional[Dict[str, Any]]:
    return _find_item(document, item_id, None)


def _current_use(document: Dict[str, Any], use_id: str) -> Optional[Dict[str, Any]]:
    return _find_use(document, use_id, None)


def _next_item_revision(document: Dict[str, Any], item_id: str) -> int:
    revisions = [i["revision"] for i in document["items"] if i["id"] == item_id]
    return (max(revisions) + 1) if revisions else 1


def _next_use_revision(document: Dict[str, Any], use_id: str) -> int:
    revisions = [u["revision"] for u in document["uses"] if u["id"] == use_id]
    return (max(revisions) + 1) if revisions else 1


# ---------------------------------------------------------------------------
# Register: payload parsing (single form and batch/package form)
# ---------------------------------------------------------------------------

def _parse_record(record: Any) -> Dict[str, Any]:
    """Validate and normalise a ``--record-file`` payload.

    Accepted shapes:

    - Single legacy form: ``{"catalog_id"?, "kind": "item"|"use",
      "item"|"use": {...}, "retain"?: [...]}``.
    - Batch/package form: ``{"catalog_id"?, "items": [...],
      "uses": [...]?, "retain"?: [...]}`` where each element is a full item/use
      payload (no wrapper). ``items`` and ``uses`` may be given together; they
      are committed atomically as one new file revision.
    - Full-version import: the batch form with explicit ``revision`` values on
      each element; those are verified, not recomputed.
    """
    if not isinstance(record, dict):
        raise DataError("record-file root must be a JSON object")
    if "kind" in record:
        _reject_unknown(record, {"catalog_id", "kind", "item", "use", "retain"}, "record-file")
        kind = record.get("kind")
        if kind not in ("item", "use"):
            raise DataError("record-file: 'kind' must be 'item' or 'use'")
        if kind == "item" and not isinstance(record.get("item"), dict):
            raise DataError("record-file: 'item' must be an object for kind 'item'")
        if kind == "use" and not isinstance(record.get("use"), dict):
            raise DataError("record-file: 'use' must be an object for kind 'use'")
        items = [record["item"]] if kind == "item" else []
        uses = [record["use"]] if kind == "use" else []
        if kind == "item" and record.get("use") is not None:
            raise DataError("record-file: a 'use' payload needs kind 'use'")
        if kind == "use" and record.get("item") is not None:
            raise DataError("record-file: an 'item' payload needs kind 'item'")
        exact_versions = False
    else:
        _reject_unknown(record, {"catalog_id", "items", "uses", "retain"}, "record-file")
        raw_items = record.get("items", [])
        raw_uses = record.get("uses", [])
        if not isinstance(raw_items, list):
            raise DataError("record-file: 'items' must be a list")
        if not isinstance(raw_uses, list):
            raise DataError("record-file: 'uses' must be a list")
        if not raw_items and not raw_uses:
            raise DataError("record-file: provide at least one item or use")
        if any(not isinstance(i, dict) for i in raw_items):
            raise DataError("record-file: every entry in 'items' must be an object")
        if any(not isinstance(u, dict) for u in raw_uses):
            raise DataError("record-file: every entry in 'uses' must be an object")
        items, uses = list(raw_items), list(raw_uses)
        # The batch/package form is the full-version import shape: its explicit
        # ``revision`` values are a claim about the exact version being written
        # and are verified against the next free revision, never silently
        # rewritten. The single ``kind`` form appends and assigns revisions.
        exact_versions = True

    _validate_retain(record, "record-file")
    catalog_id = record.get("catalog_id")
    if catalog_id is not None and (not isinstance(catalog_id, str) or not catalog_id.strip()):
        raise DataError("record-file: 'catalog_id' must be a non-empty string")

    # Generated facts the helper owns are filled before validation, so a caller
    # never hand-writes a revision or an in-use timestamp.
    for use in uses:
        if use.get("status") == "in-use" and use.get("observed_at") is None:
            use["observed_at"] = _now_iso()
    for item in items:
        _validate_item(item, "record-file.items")
    for use in uses:
        _validate_use(use, "record-file.uses")
    if len({i["id"] for i in items}) != len(items):
        raise DataError("record-file: duplicate item ids in one submission")
    if len({u["id"] for u in uses}) != len(uses):
        raise DataError("record-file: duplicate use ids in one submission")
    return {"catalog_id": catalog_id, "items": items, "uses": uses,
            "retain": record.get("retain") or [], "exact_versions": exact_versions}



def _preview_retain(parsed: Dict[str, Any], bindings: RootBindings,
                    catalog: Catalog) -> List[Dict[str, str]]:
    """Resolve the ``retain`` list to digests/locators without writing files."""
    target_dir = _safe_under(catalog.path.parent, "media/sha256", "retained media")
    out: List[Dict[str, str]] = []
    for entry in parsed["retain"]:
        root = bindings.resolve_root(entry["root"], where="retain.root")
        result = _retain_file(root, entry["path"], target_dir, where="retain.path", commit=False)
        out.append({"retain_id": entry["id"], **result})
    return out


def _submission_present(parsed: Dict[str, Any], document: Dict[str, Any], *,
                        bindings: RootBindings, catalog: Catalog) -> bool:
    """True when every element of the submission already exists unchanged.

    Compares against **current** versions only: re-applying an older value is a
    new version, not an unchanged submission. Read-only: it computes digests for
    retained media but writes nothing.
    """
    preview_media = _preview_retain(parsed, bindings, catalog)
    for raw_item in parsed["items"]:
        candidate = _materialize_item(
            {"item": raw_item, "retain": parsed["retain"]}, preview_media, bindings, catalog,
            commit=False)
        current = _current_item(document, candidate["id"])
        if current is None:
            return False
        if _normalise_for_compare(current, kind="item") != _normalise_for_compare(candidate, kind="item"):
            return False
    for raw_use in parsed["uses"]:
        current = _current_use(document, raw_use["id"])
        if current is None:
            return False
        if _normalise_for_compare(current, kind="use") != _normalise_for_compare(raw_use, kind="use"):
            return False
    return True


def cmd_register(args: argparse.Namespace) -> Tuple[int, Dict[str, Any]]:
    parsed = _parse_record(_load_json(Path(args.record_file)))

    target = Path(args.catalog)
    target.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(target, timeout=args.lock_timeout):
        if os.path.lexists(target):
            document = _validate_document(_load_json(target), path_label=str(target))
            exists = True
        else:
            document = _new_document(parsed["catalog_id"] or target.stem)
            exists = False
        if parsed["catalog_id"] is not None and parsed["catalog_id"] != document["id"]:
            raise DataError(
                f"record-file.catalog_id '{parsed['catalog_id']}' does not match "
                f"catalogue id '{document['id']}'"
            )

        catalog = Catalog(target, document, exists=exists)
        dep_ids = [d.id for d in (_load_catalog(p) for p in (args.with_catalog or []))]
        bindings = _load_bindings(args, catalog, dep_ids)
        bindings.catalog_id = document["id"]

        # Idempotency is decided before the revision gate: a whole submission
        # whose content already exists is ``unchanged`` even at a stale expected
        # revision. A stale submission with new/changed content conflicts below.
        if _submission_present(parsed, document, bindings=bindings, catalog=catalog):
            first_item = parsed["items"][0]["id"] if parsed["items"] else None
            first_use = parsed["uses"][0]["id"] if parsed["uses"] else None
            # Report the current revisions of the matching objects so a caller
            # can confirm what already exists.
            revisions: Dict[str, Any] = {}
            for raw_item in parsed["items"]:
                current = _current_item(document, raw_item["id"])
                if current is not None:
                    revisions.setdefault("items", {})[current["id"]] = current["revision"]
            for raw_use in parsed["uses"]:
                current = _current_use(document, raw_use["id"])
                if current is not None:
                    revisions.setdefault("uses", {})[current["id"]] = current["revision"]
            payload = {
                "ok": True, "status": "unchanged", "catalog_id": document["id"],
                "id": first_item or first_use, "item": first_item, "use": first_use,
                "file_revision": document["revision"], "retained": [],
                "items": [{"id": k, "revision": v} for k, v in revisions.get("items", {}).items()],
                "uses": [{"id": k, "revision": v} for k, v in revisions.get("uses", {}).items()],
            }
            if len(parsed["items"]) + len(parsed["uses"]) == 1:
                obj = (parsed["items"] or parsed["uses"])[0]
                payload["revision"] = revisions.get("items", {}).get(obj["id"],
                                    revisions.get("uses", {}).get(obj["id"]))
                payload["kind"] = "item" if parsed["items"] else "use"
            return EXIT_OK, payload

        if document["revision"] != args.expect_revision:
            raise ConflictError(
                f"revision conflict for {target}: expected {args.expect_revision}, file is at "
                f"{document['revision']}"
            )

        media = _retain_media(catalog, bindings, parsed)
        items = [_materialize_item({"item": raw, "retain": parsed["retain"]}, media, bindings, catalog)
                 for raw in parsed["items"]]

        # Assign revisions in submission order, and validate every reference
        # (including references to items in this same batch) before any write.
        # The batch/package form imports exact versions: a supplied ``revision``
        # that disagrees with the next free revision is a hard error, never a
        # silent renumber. The single ``kind`` form appends and assigns.
        exact = parsed["exact_versions"]
        probe = {"version": SUPPORTED_VERSION, "id": document["id"],
                 "revision": document["revision"],
                 "items": list(document["items"]), "uses": list(document["uses"])}
        registered_items: List[Dict[str, Any]] = []
        for item in items:
            obj = dict(item)
            expected = _next_item_revision(probe, obj["id"])
            if exact and obj["revision"] != expected:
                raise DataError(
                    f"register: item '{obj['id']}' imports revision {obj['revision']} "
                    f"but the next free revision is {expected}"
                )
            obj["revision"] = expected
            probe["items"].append(obj)
            registered_items.append(obj)
        registered_uses: List[Dict[str, Any]] = []
        for raw in parsed["uses"]:
            obj = dict(raw)
            expected = _next_use_revision(probe, obj["id"])
            if exact and obj["revision"] != expected:
                raise DataError(
                    f"register: use '{obj['id']}' imports revision {obj['revision']} "
                    f"but the next free revision is {expected}"
                )
            obj["revision"] = expected
            probe["uses"].append(obj)
            registered_uses.append(obj)

        # Validate refs within this batch against the prospective document plus
        # any supplied dependency catalogues.
        probe_catalog = Catalog(target, probe, exists=True)
        index = _build_index([probe_catalog] + [_load_catalog(p) for p in (args.with_catalog or [])])
        for item in registered_items:
            for where, ref in _all_references(item):
                state = _check_reference(ref, index)
                if state["status"] in ("unresolved-catalog", "unresolved-revision",
                                       "unresolved-item", "unresolved-asset", "unresolved-preview"):
                    raise DataError(
                        f"register: item '{item['id']}' {where} does not resolve "
                        f"({state['status']}); supply --with-catalog or fix the reference"
                    )
        for use in registered_uses:
            for idx, ref in enumerate(use["references"]):
                state = _check_reference(ref, index)
                if state["status"] in ("unresolved-catalog", "unresolved-revision",
                                       "unresolved-item", "unresolved-asset", "unresolved-preview"):
                    raise DataError(
                        f"register: use '{use['id']}' references[{idx}] does not resolve "
                        f"({state['status']})"
                    )

        # Derivation sources must be exact assets where the source item has
        # assets, and the whole derivation graph (including dependencies) must
        # stay acyclic and fully resolved across all preserved versions.
        for item in registered_items:
            _require_exact_derivation_assets(item, index)

        document["items"].extend(registered_items)
        document["uses"].extend(registered_uses)
        new_revision = document["revision"] + 1
        document["revision"] = new_revision
        # Full-document re-validation (format, uniqueness) plus derivation
        # acyclicity across all preserved versions of every supplied catalogue.
        _validate_document(document, path_label=str(target))
        extra_docs = {c.id: c.document for c in (_load_catalog(p) for p in (args.with_catalog or []))}
        unresolved_deriv = _derivation_unresolved(document, extra_documents=extra_docs)
        if unresolved_deriv:
            first = unresolved_deriv[0]
            raise DataError(
                f"register: derivation source {first['reference']} does not resolve to an "
                f"exact asset/revision in a supplied catalogue")
        _validate_derivation_acyclic(document, extra_documents=extra_docs)
        _atomic_write_json(target, document)

        payload = {
            "ok": True, "status": "registered", "catalog_id": document["id"],
            "file_revision": new_revision, "retained": media,
            "items": [{"id": i["id"], "revision": i["revision"]} for i in registered_items],
            "uses": [{"id": u["id"], "revision": u["revision"]} for u in registered_uses],
        }
        # Backward-compatible convenience fields for the single submit form.
        if len(registered_items) + len(registered_uses) == 1:
            obj = (registered_items or registered_uses)[0]
            payload["id"] = obj["id"]
            payload["revision"] = obj["revision"]
            payload["kind"] = "item" if registered_items else "use"
        return EXIT_OK, payload

# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------

def cmd_validate(args: argparse.Namespace) -> Tuple[int, Dict[str, Any]]:
    catalog = _load_catalog(args.catalog)
    dependencies = [_load_catalog(p) for p in (args.with_catalog or [])]
    bindings = _load_bindings(args, catalog, [d.id for d in dependencies])
    index = _build_index([catalog] + dependencies)

    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    missing_media: List[Dict[str, Any]] = []

    # Every *invalid* reference is a structural error; every file that is simply
    # absent/changed/remote/unbound is a `missing_media` entry. The two are never
    # conflated, and both are labelled with the exact item/use revision and the
    # exact location (including use evidence.previews and specimen/script
    # locators), for every preserved revision -- not just the current one.
    def check_ref(label: str, ref: Any, *, argv_roots: Sequence[str]) -> None:
        """Classify one reference: a structural error, or a media gap, or ok.

        An unresolvable reference is an `error`; a resolvable one whose files are
        absent/changed/remote/unbound is a `missing_media` entry. The two are
        never conflated, and both carry the exact `label`.
        """
        state = _check_reference(ref, index)
        if state["status"] != "resolved":
            errors.append({"where": label, "status": state["status"],
                           "reference": state["reference"],
                           "required_catalog": state.get("required_catalog")})
            return
        for entry in _resolve_reference_media(ref, catalog, bindings, argv_roots, index,
                                              where=label):
            if "status" in entry and entry["status"] not in ("available", "remote-only"):
                missing_media.append({"where": label, "status": entry["status"],
                                      "via": entry.get("via"), "locator": entry.get("locator")})

    def check_item(item: Dict[str, Any], *, argv_roots: Sequence[str]) -> None:
        label = f"item '{item['id']}'@{item['revision']}"
        for where, ref in _all_references(item):
            check_ref(f"{label} {where}", ref, argv_roots=argv_roots)
        for path in _active_schemes_in_strings(item):
            warnings.append({"where": label, "issue": path,
                             "note": "active URL scheme in metadata; gallery will refuse to link it"})
        # The item's own assets and previews (real files) for this exact revision.
        for asset in item.get("assets") or []:
            resolved = _resolve_asset(asset, bindings, where=f"{label} assets.{asset['id']}")
            if resolved["status"] != "available":
                missing_media.append({"where": f"{label} assets.{asset['id']}",
                                      "status": resolved["status"], "via": None,
                                      "locator": asset.get("locator"),
                                      "path": resolved.get("path")})
        for preview in item.get("previews") or []:
            resolved = _resolve_preview(preview, bindings, where=f"{label} previews.{preview['id']}")
            if resolved["status"] != "available":
                missing_media.append({"where": f"{label} previews.{preview['id']}",
                                      "status": resolved["status"], "via": None,
                                      "locator": preview.get("locator"),
                                      "path": resolved.get("path")})
        # Bare locators carried by specimen and derivation script.
        specimen = item.get("specimen") or {}
        if specimen.get("locator") is not None:
            resolved = _resolve_locator_entry(specimen["locator"], bindings,
                                              where=f"{label} specimen.locator", kind="specimen")
            if resolved["status"] != "available":
                missing_media.append({"where": f"{label} specimen.locator",
                                      "status": resolved["status"], "via": None,
                                      "locator": specimen["locator"], "path": resolved.get("path")})
        deriv = item.get("derivation") or {}
        if deriv.get("script") is not None:
            resolved = _resolve_locator_entry(deriv["script"], bindings,
                                              where=f"{label} derivation.script", kind="recipe")
            if resolved["status"] != "available":
                missing_media.append({"where": f"{label} derivation.script",
                                      "status": resolved["status"], "via": None,
                                      "locator": deriv["script"], "path": resolved.get("path")})

    def check_use(use: Dict[str, Any], *, argv_roots: Sequence[str]) -> None:
        label = f"use '{use['id']}'@{use['revision']}"
        for i, ref in enumerate(use["references"]):
            check_ref(f"{label} references[{i}]", ref, argv_roots=argv_roots)
        evidence = use.get("evidence") or {}
        for i, ref in enumerate(evidence.get("previews") or []):
            check_ref(f"{label} evidence.previews[{i}]", ref, argv_roots=argv_roots)

    # Validate every preserved revision of every item and use, not only current.
    for item in catalog.document["items"]:
        check_item(item, argv_roots=args.root)
    for use in catalog.document["uses"]:
        check_use(use, argv_roots=args.root)

    # Derivation is the one relation that must be acyclic and exact across
    # every supplied collection. Check the whole graph (all preserved versions,
    # primary plus dependencies) and report unresolved exact assets.
    extra_docs = {c.id: c.document for c in dependencies}
    unresolved_derivation = _derivation_unresolved(catalog.document, extra_documents=extra_docs)
    for entry in unresolved_derivation:
        errors.append({"where": f"item '{entry['item_id']}'@{entry['revision']} {entry['where']}",
                       "status": entry["status"], "reference": entry["reference"]})
    try:
        _validate_derivation_acyclic(catalog.document, extra_documents=extra_docs)
    except DataError as exc:
        errors.append({"where": "derivation", "status": "unresolved-derivation-cycle",
                       "detail": str(exc)})
    for item in catalog.document["items"]:
        try:
            _require_exact_derivation_assets(item, index)
        except DataError as exc:
            errors.append({"where": f"item '{item['id']}'@{item['revision']} derivation",
                           "status": "unresolved-derivation-source", "detail": str(exc)})

    return (EXIT_OK if not errors else EXIT_INVALID), {
        "ok": not errors,
        "status": "valid" if not errors else "invalid",
        "catalog_id": catalog.id,
        "revision": catalog.revision,
        "items": len(_current_items(catalog.document)),
        "item_versions": len(catalog.document["items"]),
        "uses": len(_current_uses(catalog.document)),
        "use_versions": len(catalog.document["uses"]),
        "errors": errors,
        "missing_media": missing_media,
        "warnings": warnings,
        "note": ("errors are structural (invalid references/payloads); missing_media lists "
                 "absent, changed, remote, or unbound files for every preserved revision"),
    }


# ---------------------------------------------------------------------------
# gallery
# ---------------------------------------------------------------------------

_HTML_HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root { --bg:#f2f4f7; --surface:#fff; --ink:#1c2432; --muted:#586477; --line:#cbd2dc;
        --accent:#305994; --chip:#e8edf3; }
@media (prefers-color-scheme:dark) { :root { --bg:#17181a; --surface:#202225; --ink:#f1efe9;
        --muted:#b6afa4; --line:#34373b; --accent:#7fc2ad; --chip:#2a2d31; } }
* { box-sizing:border-box; }
html, body { margin:0; }
body { background:var(--bg); color:var(--ink); font:16px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif; }
a { color:var(--accent); }
header { padding:1.25rem clamp(1rem,4vw,2.5rem) .75rem; border-bottom:1px solid var(--line); }
header h1 { margin:0 0 .25rem; font-size:clamp(1.3rem,2.6vw,1.9rem); overflow-wrap:anywhere; }
header p { margin:0; color:var(--muted); }
.controls { display:flex; flex-wrap:wrap; gap:.6rem; padding:.9rem clamp(1rem,4vw,2.5rem); align-items:flex-end; }
.controls label { display:flex; flex-direction:column; font-size:.78rem; color:var(--muted); gap:.2rem; }
.controls input, .controls select { padding:.4rem .5rem; border:1px solid var(--line); border-radius:.4rem;
        background:var(--surface); color:inherit; font:inherit; max-width:12rem; }
main { padding:0 clamp(1rem,4vw,2.5rem) 3rem; }
.grid { display:grid; gap:1rem; grid-template-columns:repeat(auto-fill,minmax(240px,1fr)); }
.card { background:var(--surface); border:1px solid var(--line); border-radius:.6rem; overflow:hidden;
        display:flex; flex-direction:column; }
.card[hidden] { display:none; }
.card .thumb { aspect-ratio:4/3; background:var(--chip); display:flex; align-items:center;
        justify-content:center; overflow:hidden; }
.card .thumb img { width:100%; height:100%; object-fit:cover; display:block; }
.card .thumb.missing { color:var(--muted); font-size:.8rem; text-align:center; padding:.5rem; }
.card .body { padding:.7rem .8rem .9rem; }
.card h2 { font-size:1rem; margin:0 0 .3rem; overflow-wrap:anywhere; }
.meta { color:var(--muted); font-size:.8rem; display:flex; flex-wrap:wrap; gap:.35rem; }
.chip { background:var(--chip); border-radius:999px; padding:.1rem .5rem; }
.card a.open { display:inline-block; margin-top:.5rem; font-size:.85rem; }
.detail { background:var(--surface); border:1px solid var(--line); border-radius:.6rem; padding:1rem; margin-top:1rem; }
.detail img.preview { max-width:100%; height:auto; border:1px solid var(--line); border-radius:.4rem; background:var(--chip); }
.detail video.preview, .detail audio.preview { max-width:100%; }
.preview-viewport { overflow:auto; max-height:80vh; }
.preview-viewport.original img.preview { max-width:none; }
.zoom { font:inherit; color:var(--accent); background:var(--surface); border:1px solid var(--line); padding:.35rem .6rem; margin-top:.5rem; }
.detail { overflow-wrap:anywhere; }
.detail[hidden] { display:none; }
.miss { color:var(--muted); }
ul.meta-list { margin:.3rem 0; }
li.ok::marker, li.gap::marker { color:var(--muted); }
li.gap { color:#a0452f; }
.detail figure { margin:.6rem 0; }
.detail figcaption, .cap { color:var(--muted); font-size:.82rem; }
.detail .making, .detail .palette, .detail .materials, .detail .refs, .detail .history { margin-top:.8rem; }
.detail h3 { font-size:.92rem; margin:.6rem 0 .3rem; }
.swatches { list-style:none; padding:0; display:flex; flex-wrap:wrap; gap:.5rem; }
.swatch { display:flex; align-items:center; gap:.35rem; font-size:.82rem; }
.swatch .dot { width:1rem; height:1rem; border-radius:50%; border:1px solid var(--line); display:inline-block; }
.history-entry { border-top:1px solid var(--line); padding:.4rem 0; }
.uses-list { margin:.3rem 0; }
#empty { padding:1rem 0; }
ul { overflow-wrap:anywhere; }
footer { padding:1rem clamp(1rem,4vw,2.5rem) 2rem; color:var(--muted); font-size:.8rem; }
:focus-visible { outline:2px solid var(--accent); outline-offset:2px; }
[hidden] { display:none !important; }
</style>
</head>
<body>
"""

_HTML_SCRIPT = """<script>
(function () {
  var search = document.getElementById('search');
  var role = document.getElementById('role');
  var task = document.getElementById('task');
  var language = document.getElementById('language');
  var medium = document.getElementById('medium');
  var source = document.getElementById('source');
  var cards = Array.prototype.slice.call(document.querySelectorAll('.card'));
  var detail = document.getElementById('detail');
  var list = document.getElementById('list');
  var empty = document.getElementById('empty');
  var currentId = '';
  var savedScroll = 0;
  function tokens(value) {
    return (value || '').split(',').filter(function (v) { return v.length > 0; });
  }
  function hasExact(value, wanted) {
    if (!wanted) { return true; }
    return tokens(value).indexOf(wanted) !== -1;
  }
  function apply() {
    var needle = (search.value || '').trim().toLowerCase();
    var visible = 0;
    cards.forEach(function (card) {
      var hay = (card.dataset.search || '').toLowerCase();
      var ok = !needle || hay.indexOf(needle) !== -1;
      if (ok) { ok = hasExact(card.dataset.roles, role.value); }
      if (ok) { ok = hasExact(card.dataset.tasks, task.value); }
      if (ok) { ok = hasExact(card.dataset.languages, language.value); }
      if (ok) { ok = hasExact(card.dataset.media, medium.value); }
      if (ok && source.value) { ok = card.dataset.source === source.value; }
      card.hidden = !ok;
      if (ok) { visible += 1; }
    });
    empty.hidden = visible !== 0;
  }
  [search, role, task, language, medium, source].forEach(function (el) {
    if (el) { el.addEventListener('input', apply); el.addEventListener('change', apply); }
  });
  function openDetail(card) {
    currentId = card.dataset.card;
    savedScroll = window.scrollY || window.pageYOffset || 0;
    list.hidden = true;
    empty.hidden = true;
    detail.hidden = false;
    detail.innerHTML = '';
    var tpl = document.getElementById('tpl-' + card.dataset.card);
    if (tpl) { detail.appendChild(tpl.content.cloneNode(true)); }
    detail.querySelectorAll('[data-color]').forEach(function (dot) {
      // Setting one color property rejects URLs and declaration injection.
      dot.style.backgroundColor = dot.dataset.color;
    });
    var wrap = document.createElement('p');
    var link = document.createElement('a');
    link.href = '#';
    link.setAttribute('data-back', '');
    link.textContent = 'Back to list';
    link.addEventListener('click', function (ev) { ev.preventDefault(); closeDetail(currentId); });
    wrap.appendChild(link);
    detail.prepend(wrap);
    link.focus({preventScroll:true});
    detail.scrollIntoView({block:'start'});
  }
  function closeDetail(id) {
    detail.hidden = true;
    list.hidden = false;
    apply();
    var card = cards.find(function (candidate) { return candidate.dataset.card === id; });
    window.scrollTo(0, savedScroll);
    if (card && !card.hidden) {
      var opener = card.querySelector('a.open');
      if (opener) { opener.focus({preventScroll:true}); }
    } else if (search) {
      search.focus({preventScroll:true});
    }
  }
  document.addEventListener('click', function (ev) {
    var zoom = ev.target.closest && ev.target.closest('button.zoom');
    if (zoom) {
      var viewport = zoom.closest('figure').querySelector('.preview-viewport');
      var original = viewport.classList.toggle('original');
      zoom.setAttribute('aria-pressed', String(original));
      zoom.textContent = original ? 'Fit to view' : 'View at original size';
      return;
    }
    var opener = ev.target.closest && ev.target.closest('a.open');
    if (opener) {
      ev.preventDefault();
      var card = opener.closest('.card');
      if (card) { openDetail(card); }
    }
  });
  document.addEventListener('keydown', function (ev) {
    if (ev.key === 'Escape' && !detail.hidden) { closeDetail(currentId); }
  });
  apply();
})();
</script>
"""

_HTML_TAIL = ('<footer>Static catalogue read. Regenerate after source changes; this page never '
              'executes source HTML, script strings, or SVG documents.</footer>\n</body>\n</html>\n')


def _media_kind_for(path: str) -> str:
    return MEDIA_SUFFIX_KINDS.get(Path(path).suffix.lower(), "file")


def _copy_media(locator: Dict[str, str], root: Path, out_media: Path,
                manifest: Dict[str, str], expected_digest: Optional[str] = None) -> Optional[str]:
    """Copy a referenced media file into the output, returning its relative URL.

    Deduplicates by content digest and never copies a symlink target that
    resolves outside the root. Returns ``None`` when the file is absent.
    """
    try:
        real = _safe_under(root, locator["path"], "gallery media")
    except DataError:
        return None
    if not os.path.lexists(real) or os.path.islink(real) or not real.is_file():
        return None
    data = real.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if expected_digest is not None and expected_digest != digest:
        return None
    suffix = real.suffix.lower()
    rel = f"media/{digest}{suffix}"
    target = out_media / f"{digest}{suffix}"
    name = f"{digest}{suffix}"
    if name in manifest:
        return rel
    out_media.mkdir(parents=True, exist_ok=True)
    if not os.path.lexists(target):
        tmp = _write_temp(target, data)
        os.replace(tmp, target)
    manifest[name] = rel
    return rel


def _copy_media_for(locator: Dict[str, str], bindings: RootBindings, out_media: Path,
                    manifest: Dict[str, str], expected_digest: Optional[str] = None) -> Optional[str]:
    try:
        root = bindings.resolve_root(locator["root"], where="gallery media")
    except MissingError:
        return None
    return _copy_media(locator, root, out_media, manifest, expected_digest)


def _html_escape(value: Any) -> str:
    text = "" if value is None else str(value)
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&#39;"))


def _evidence_summary(evidence: Dict[str, Any]) -> str:
    evidence = evidence or {}
    bits = []
    if evidence.get("rendered"):
        bits.append("rendered")
    if evidence.get("operated"):
        bits.append("operated")
    if evidence.get("observed"):
        bits.append("observed " + str(evidence["observed"]))
    return ", ".join(bits) if bits else "not yet verified"


def _render_media(preview: Dict[str, Any], bindings: RootBindings, out_media: Path,
                  manifest: Dict[str, str], *, title: str,
                  label_prefix: str = "") -> Tuple[str, Optional[str], bool]:
    """Render one preview as safe HTML.

    Returns (html, first_local_rel, copied). An unsafe or missing media becomes
    an explicit gap; a remote preview is only linked when its scheme is safe.
    """
    locator = preview.get("locator")
    rel = None
    state = _resolve_preview(preview, bindings, where="gallery preview")
    if locator is not None and state["status"] == "available":
        rel = _copy_media_for(locator, bindings, out_media, manifest, preview.get("digest"))
    label = _html_escape((label_prefix + (preview.get("label") or title)))
    if rel is None:
        if preview.get("url") and _classify_url(preview["url"])[0]:
            html = (f'<p class="miss">[gap] remote preview only: '
                    f'<a href="{_html_escape(preview["url"])}" rel="noreferrer noopener" '
                    f'target="_blank">{_html_escape(preview["url"])}</a></p>')
        else:
            html = f'<p class="miss">[gap] preview file {_html_escape(state["status"])}: {label}</p>'
        return html, None, False
    kind = _media_kind_for(locator["path"]) if locator else "file"
    if kind == "video":
        return (f'<figure><video class="preview" controls preload="metadata" src="{rel}"></video>'
                f'<figcaption>{label}</figcaption></figure>'), rel, True
    if kind == "audio":
        return (f'<figure><audio class="preview" controls preload="metadata" src="{rel}"></audio>'
                f'<figcaption>{label}</figcaption></figure>'), rel, True
    # Always <img>: an SVG is displayed as an image resource, so any active
    # content inside it never executes as a document.
    return (f'<figure><div class="preview-viewport" tabindex="0" role="region" aria-label="{label}">'
            f'<img class="preview" src="{rel}" alt="{label}" loading="lazy"></div>'
            f'<figcaption>{label}</figcaption>'
            '<button type="button" class="zoom" aria-pressed="false">View at original size</button></figure>'), rel, True


def _capture_note(preview: Dict[str, Any]) -> str:
    capture = preview.get("capture") or {}
    bits = []
    if capture.get("viewport"):
        bits.append("viewport " + "x".join(str(v) for v in capture["viewport"]))
    if capture.get("coverage"):
        bits.append(str(capture["coverage"]))
    if capture.get("state"):
        bits.append(str(capture["state"]))
    if capture.get("taken_at"):
        bits.append("taken " + str(capture["taken_at"]))
    return ", ".join(bits)


def _render_making(making: Dict[str, Any]) -> str:
    if not isinstance(making, dict):
        return ""
    carry = "".join(f"<li>{_html_escape(c)}</li>" for c in making.get("carry", []))
    vary = "".join(f"<li>{_html_escape(v)}</li>" for v in making.get("vary", []))
    return (
        '<section class="making"><h3>Making</h3>'
        f'<p><strong>Effect:</strong> {_html_escape(making.get("effect"))}</p>'
        f'<details><summary>Carry (fixed)</summary><ul>{carry}</ul></details>'
        f'<details><summary>Vary (variable)</summary><ul>{vary}</ul></details>'
        f'<p><strong>Limits:</strong> {_html_escape(making.get("limits"))}</p></section>'
    )


def _render_palette(palette: Dict[str, Any]) -> str:
    if not isinstance(palette, dict):
        return ""
    swatches = "".join(
        '<li class="swatch"><span class="dot" data-color="'
        f'{_html_escape(entry.get("value"))}"></span>'
        f'<code>{_html_escape(role)}</code> {_html_escape(entry.get("value"))}'
        + (f' · on {_html_escape(entry.get("foreground") or entry.get("background"))}'
           if entry.get("foreground") or entry.get("background") else "")
        + (f' · {_html_escape(entry.get("area"))}' if entry.get("area") else "")
        + "</li>"
        for role, entry in (palette.get("roles") or {}).items()
    )
    instance = palette.get("instance") or {}
    return (
        '<section class="palette"><h3>Palette</h3>'
        f'<ul class="swatches">{swatches}</ul>'
        + (f'<p class="miss">instance: {_html_escape(instance.get("catalog_id"))}'
           f'/{_html_escape(instance.get("item_id"))}@{_html_escape(instance.get("revision"))}</p>'
           if instance else "")
        + (f'<p>State: {_html_escape(palette.get("state"))}</p>' if palette.get("state") else "")
        + "</section>"
    )


def _render_references(item: Dict[str, Any], index: Dict[str, "Catalog"],
                       primary_id: str) -> str:
    rows = []
    for where, ref in _all_references(item):
        state = _check_reference(ref, index)
        label = (f'{ref["catalog_id"]}/{ref["item_id"]}@{ref["revision"]}'
                 + (f'#{ref["asset_id"]}' if ref.get("asset_id") else "")
                 + (f'#{ref["preview_id"]}' if ref.get("preview_id") else ""))
        status = state["status"]
        cls = "ok" if status == "resolved" else "gap"
        rows.append(f'<li class="{cls}">{_html_escape(where)}: {_html_escape(label)} — '
                    f'{_html_escape(status)}'
                    + (f' (needs catalogue {_html_escape(state.get("required_catalog") or "")})'
                       if status == "unresolved-catalog" else "")
                    + "</li>")
    if not rows:
        return ""
    return ('<section class="refs"><h3>References</h3>'
            f'<ul class="meta-list">{"".join(rows)}</ul></section>')


def _render_materials(item: Dict[str, Any], bindings: RootBindings,
                      out_media: Path, manifest: Dict[str, str]) -> str:
    assets = item.get("assets") or []
    if not assets:
        return ""
    rows = []
    for asset in assets:
        digest = asset.get("sha256")
        state = _resolve_asset(asset, bindings, where="gallery asset")
        rel = (_copy_media_for(asset["locator"], bindings, out_media, manifest, digest)
               if state["status"] == "available" else None)
        link = (f' — <a href="{rel}" download>Download {_html_escape(asset["id"])}</a>'
                if rel else f' — <span class="miss">{_html_escape(state["status"])}</span>')
        rows.append(
            f'<li>{_html_escape(asset.get("id"))} — '
            f'{_html_escape(asset.get("file_type") or "file")}'
            + (f' — sha256 {_html_escape(digest[:12])}…' if digest else " — no digest")
            + link
            + (f' — <span class="miss">remote-only {_html_escape(asset.get("url"))}</span>'
               if asset.get("url") and not asset.get("locator") else "")
            + "</li>"
        )
    return ('<section class="materials"><h3>Materials</h3>'
            f'<ul class="meta-list">{"".join(rows)}</ul></section>')


def _render_item_view(item: Dict[str, Any], catalog: Catalog, index: Dict[str, "Catalog"],
                      bindings: RootBindings, out_media: Path, manifest: Dict[str, str],
                      view_bindings: Dict[str, str], *,
                      title_prefix: str = "") -> Tuple[str, Optional[str], List[Dict[str, Any]]]:
    """Return (html, first_thumb_rel, skipped_previews) for one item revision."""
    skipped: List[Dict[str, Any]] = []
    previews_html: List[str] = []
    thumb: Optional[str] = None
    for preview in item.get("previews") or []:
        html, rel, copied = _render_media(preview, bindings, out_media, manifest,
                                          title=item["title"])
        note = _capture_note(preview)
        if note:
            html += f'<p class="cap">{_html_escape(preview.get("id"))}: {_html_escape(note)}</p>'
        previews_html.append(html)
        if not copied:
            skipped.append({"item": item["id"], "revision": item["revision"],
                            "preview": preview["id"], "reason": "no local file"})
        if thumb is None and rel is not None:
            thumb = rel

    specimen = item.get("specimen") or {}
    source = item.get("source") or {}
    links: List[str] = []
    url = _view_binding_for(view_bindings, catalog.id, item["id"], item["revision"])
    if url:
        links.append(f'<p>Specimen: <a href="{_html_escape(url)}" rel="noreferrer noopener" '
                     f'target="_blank">open running instance</a> '
                     f'<span class="chip">{_html_escape(catalog.id)}/{_html_escape(item["id"])}@'
                     f'{item["revision"]}</span></p>')
    else:
        entry = specimen.get("entry") or "no entry recorded"
        links.append(f'<p class="miss">Specimen not yet running '
                     f'(expected binding {quote(catalog.id, safe="")}:{quote(item["id"], safe="")}:'
                     f'{item["revision"]}): {_html_escape(entry)}</p>')
    if specimen.get("source"):
        links.append(f'<p>Specimen source: {_html_escape(specimen["source"])}</p>')
    if specimen.get("notes"):
        links.append(f'<p>{_html_escape(specimen["notes"])}</p>')
    if specimen.get("locator"):
        links.append('<p>Specimen source locator: '
                     f'{_html_escape(specimen["locator"]["root"])}:'
                     f'{_html_escape(specimen["locator"]["path"])}</p>')
    if source.get("url") and _classify_url(source["url"])[0]:
        links.append(f'<p>Source: <a href="{_html_escape(source["url"])}" '
                     'rel="noreferrer noopener" target="_blank">original</a></p>')
    elif source.get("note"):
        links.append(f'<p>Source: {_html_escape(source["note"])}</p>')

    making_html = _render_making(item.get("making"))
    palette_html = _render_palette(item.get("palette"))
    refs_html = _render_references(item, index, catalog.id)
    materials_html = _render_materials(item, bindings, out_media, manifest)
    evidence = f'<p>Evidence: {_html_escape(_evidence_summary(item.get("evidence")))}</p>'

    body = (
        f'<h2>{_html_escape(title_prefix + item["title"])}</h2>'
        f'<div class="meta">'
        + "".join(f'<span class="chip">{_html_escape(r)}</span>' for r in item.get("roles", []))
        + f'<span class="chip">{_html_escape(catalog.id)}/{_html_escape(item["id"])}@'
          f'{item["revision"]}</span></div>'
        + (f'<p>{_html_escape(item.get("summary"))}</p>' if item.get("summary") else "")
        + evidence
        + "".join(previews_html)
        + making_html + palette_html
        + "".join(links)
        + materials_html + refs_html
    )
    return body, thumb, skipped


def _view_binding_for(view_bindings: Dict[str, str], catalog_id: str, ref_id: str,
                      revision: int) -> Optional[str]:
    """Resolve a running-instance URL for an *exact* item/use revision.

    The key is ``<encoded catalog_id>:<encoded ref_id>:<revision>``. Encoding
    each identity separately prevents delimiters inside an id from colliding.
    An id-only key never binds:
    a running instance for revision 1 must not be presented as the instance for
    revision 2, and the page must never fabricate a link for a revision nobody
    started.
    """
    return view_bindings.get(f"{quote(catalog_id, safe='')}:{quote(ref_id, safe='')}:{revision}")


def _gallery_items(catalog: Catalog, dependencies: List["Catalog"]) -> List[Tuple[Catalog, Dict[str, Any]]]:
    """Primary current items plus exactly the dependency items they reference.

    Referenced dependency items are included at the exact revision named by a
    primary item/use reference. No unrelated dependency catalogue dump.
    """
    index = _build_index([catalog] + dependencies)
    selected: List[Tuple[Catalog, Dict[str, Any]]] = []
    seen: set = set()
    for item in sorted((i for i in _current_items(catalog.document) if not i.get("archived")),
                       key=lambda i: (i["id"], i["revision"])):
        selected.append((catalog, item))
        seen.add((catalog.id, item["id"], item["revision"]))
    wanted: List[Tuple[str, str, int]] = []
    for item in _current_items(catalog.document):
        for _where, ref in _all_references(item):
            wanted.append((ref["catalog_id"], ref["item_id"], ref["revision"]))
    for use in _current_uses(catalog.document):
        for ref in use["references"]:
            wanted.append((ref["catalog_id"], ref["item_id"], ref["revision"]))
    for catalog_id, item_id, revision in wanted:
        key = (catalog_id, item_id, revision)
        if key in seen or catalog_id == catalog.id:
            continue
        dep = index.get(catalog_id)
        if dep is None:
            continue
        target = _find_item(dep.document, item_id, revision)
        if target is None:
            continue
        seen.add(key)
        selected.append((dep, target))
    return sorted(selected, key=lambda pair: (pair[0].id, pair[1]["id"], pair[1]["revision"]))


def _render_gallery(catalog: Catalog, bindings: RootBindings, dependencies: List["Catalog"],
                    out_dir: Path, *, view_bindings: Dict[str, str],
                    argv_roots: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    """Render the static page into staging, then publish atomically.

    Media and the final page are prepared in a staging directory; publishing
    makes the new media visible first and then atomically replaces the page
    entry, so an interrupted generation always leaves the previous page
    readable at ``out_dir`` (no window where the live path is missing).
    """
    out_dir = Path(out_dir)
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    index = _build_index([catalog] + dependencies)
    bindings_by_id = {catalog.id: bindings}
    for dep in dependencies:
        # Each dependency resolves its media under its own ``catalog`` root plus
        # any roots the caller scoped to that dependency id.
        bindings_by_id[dep.id] = _dependency_bindings(dep.id, bindings, argv_roots or [], index)

    staging = Path(tempfile.mkdtemp(prefix=".gallery-stage-", dir=str(out_dir.parent)))
    manifest: Dict[str, str] = {}
    skipped: List[Dict[str, Any]] = []
    try:
        out_media = staging / "media"
        selected = _gallery_items(catalog, dependencies)
        by_id = {(c.id, i["id"], i["revision"]): (c, i) for c, i in selected}

        cards: List[str] = []
        templates: List[str] = []
        for cat, item in selected:
            used_bindings = bindings_by_id.get(cat.id, bindings)
            body, thumb, item_skipped = _render_item_view(
                item, cat, index, used_bindings, out_media, manifest, view_bindings)
            skipped.extend(item_skipped)
            card_id = base64.urlsafe_b64encode(json.dumps(
                [cat.id, item["id"], item["revision"]], ensure_ascii=False).encode()).decode().rstrip("=")
            if thumb and _media_kind_for(thumb) == "image":
                thumb_html = (f'<div class="thumb"><img src="{thumb}" alt="{_html_escape(item["title"])}" '
                              'loading="lazy"></div>')
            elif thumb:
                thumb_html = f'<div class="thumb missing">{_html_escape(_media_kind_for(thumb))} · open details to play</div>'
            else:
                thumb_html = '<div class="thumb missing">no preview media</div>'
            tags = item.get("tags") or {}
            search_bits = " ".join([item["id"], item["title"], item.get("summary") or "",
                                    cat.id] + tags.get("tasks", []) + tags.get("languages", [])
                                   + tags.get("media", []) + tags.get("terms", []))
            cards.append(
                f'<article class="card" id="card-{_html_escape(card_id)}" data-card="{_html_escape(card_id)}" '
                f'data-roles="{_html_escape(",".join(item.get("roles", [])))}" '
                f'data-tasks="{_html_escape(",".join(tags.get("tasks", [])))}" '
                f'data-languages="{_html_escape(",".join(tags.get("languages", [])))}" '
                f'data-media="{_html_escape(",".join(tags.get("media", [])))}" '
                f'data-source="{_html_escape((item.get("source") or {}).get("kind", ""))}" '
                f'data-search="{_html_escape(search_bits)}">'
                f'{thumb_html}<div class="body"><h2>{_html_escape(item["title"])}</h2>'
                f'<div class="meta"><span class="chip">{_html_escape(cat.id)}</span>'
                f'<span class="chip">rev {item["revision"]}</span>'
                + "".join(f'<span class="chip">{_html_escape(r)}</span>' for r in item.get("roles", []))
                + "</div>"
                + f'<a class="open" href="#{_html_escape(card_id)}">Open details</a>'
                "</div></article>"
            )
            templates.append(f'<template id="tpl-{_html_escape(card_id)}">{body}'
                             + _render_history(cat, item["id"], index, bindings_by_id,
                                               out_media, manifest, view_bindings, skipped)
                             + "</template>")

        # Project uses belong at the top: current surface and adopted relations.
        uses_section = _render_uses_section(catalog, index, view_bindings)

        def options(values: Iterable[str]) -> str:
            return "".join(f'<option value="{_html_escape(v)}">{_html_escape(v)}</option>'
                           for v in sorted(set(values)))

        role_options = options(ROLES)
        task_options = options(t for _c, i in selected for t in (i.get("tags") or {}).get("tasks", []))
        lang_options = options(t for _c, i in selected for t in (i.get("tags") or {}).get("languages", []))
        media_options = options(t for _c, i in selected for t in (i.get("tags") or {}).get("media", []))

        html = [
            _HTML_HEAD.replace("__TITLE__", _html_escape(f"FC catalogue — {catalog.id}")),
            f'<header><h1>{_html_escape(catalog.id)}</h1>'
            f'<p>{len(catalog_items(selected, catalog.id))} project items · '
            f'{len(selected)} shown (including exact referenced materials) · '
            f'catalogue revision {catalog.revision}</p></header>',
            '<section class="controls" aria-label="Filters">'
            '<label>Search<input id="search" type="search" autocomplete="off"></label>'
            f'<label>Role<select id="role"><option value="">any</option>{role_options}</select></label>'
            f'<label>Task<select id="task"><option value="">any</option>{task_options}</select></label>'
            f'<label>Language<select id="language"><option value="">any</option>{lang_options}</select></label>'
            f'<label>Medium<select id="medium"><option value="">any</option>{media_options}</select></label>'
            f'<label>Source<select id="source"><option value="">any</option>{options(SOURCE_KINDS)}</select></label>'
            '</section>',
            uses_section,
            '<main><p id="empty" class="miss" hidden>No items match the current filters.</p>'
            '<div class="grid" id="list">' + "".join(cards) + '</div>',
            '<section class="detail" id="detail" hidden aria-live="polite"></section></main>',
            '<div id="templates" hidden>' + "".join(templates) + '</div>',
            _HTML_TAIL,
            _HTML_SCRIPT,
        ]
        (staging / "index.html").write_text("".join(html), encoding="utf-8")
        (staging / "media-manifest.json").write_text(
            json.dumps({"media": manifest}, ensure_ascii=False, indent=2), encoding="utf-8")
        generation = {"catalog_id": catalog.id, "catalog_revision": catalog.revision,
                      "items": len(selected), "media": len(manifest),
                      "catalogs": sorted({c.id for c, _ in selected})}
        (staging / "generation.json").write_text(
            json.dumps(generation, ensure_ascii=False, indent=2), encoding="utf-8")

        previous_generation = None
        if os.path.lexists(out_dir / "generation.json"):
            try:
                previous_generation = _load_json(out_dir / "generation.json")
            except (DataError, MissingError):
                previous_generation = None

        _publish_generation(staging, out_dir)
        result = {"generation": generation, "skipped_previews": skipped,
                  "media_manifest": manifest, "previous_generation": previous_generation}
    except BaseException:
        _remove_tree(staging)
        raise
    # The staging tree has been published (or was never reached); drop it so
    # repeated generations do not accumulate sibling scratch directories.
    _remove_tree(staging)
    return result


def catalog_items(selected: List[Tuple["Catalog", Dict[str, Any]]], catalog_id: str) -> List[Any]:
    return [i for c, i in selected if c.id == catalog_id]


def _render_history(cat: "Catalog", item_id: str, index: Dict[str, "Catalog"],
                    bindings_by_id: Dict[str, "RootBindings"], out_media: Path,
                    manifest: Dict[str, str], view_bindings: Dict[str, str],
                    skipped: List[Dict[str, Any]]) -> str:
    history = _item_history(cat.document, item_id)
    if len(history) <= 1:
        return ""
    rows = []
    for rev in history:
        body, _thumb, item_skipped = _render_item_view(
            rev, cat, index, bindings_by_id.get(cat.id, RootBindings(cat.id, cat.path.parent)),
            out_media, manifest, view_bindings)
        skipped.extend(item_skipped)
        rows.append(f'<details class="history-entry"><summary>rev {rev["revision"]}'
                    + (" (archived)" if rev.get("archived") else "")
                    + f' — {_html_escape(rev["title"])}</summary>{body}</details>')
    return f'<section class="history"><h3>History ({len(history)})</h3>{"".join(rows)}</section>'


def _render_uses_section(catalog: "Catalog", index: Dict[str, "Catalog"],
                         view_bindings: Dict[str, str]) -> str:
    uses = _current_uses(catalog.document)
    if not uses:
        return '<section class="detail uses" aria-label="Current project uses">' \
               '<h2>Current project uses (0)</h2><p class="miss">No adoption relations recorded yet.</p></section>'
    rows = []
    for use in sorted(uses, key=lambda u: u["id"]):
        refs = []
        for ref in use["references"]:
            state = _check_reference(ref, index)
            refs.append(
                f'<li class="{"ok" if state["status"] == "resolved" else "gap"}">'
                f'{_html_escape(ref["catalog_id"])}/{_html_escape(ref["item_id"])}'
                f'@{ref["revision"]}'
                + (f'#{_html_escape(ref["asset_id"])}' if ref.get("asset_id") else "")
                + f' — {_html_escape(state["status"])}</li>'
            )
        loc = (use.get("target") or {}).get("location") or {}
        where = loc.get("path") or loc.get("region") or ""
        url = _view_binding_for(view_bindings, catalog.id, use["id"], use["revision"])
        rows.append(
            f'<li><strong>{_html_escape(use["status"])}</strong> — '
            f'{_html_escape(use.get("relation") or "")} '
            f'<span class="miss">({_html_escape((use.get("target") or {}).get("project", ""))}'
            + (f' · {_html_escape(where)}' if where else "")
            + (f' · recorded {_html_escape(use.get("observed_at"))}' if use.get("observed_at") else "")
            + ")</span>"
            + (f' <a href="{_html_escape(url)}" rel="noreferrer noopener" target="_blank">open</a>'
               if url else "")
            + f'<ul class="meta-list">{"".join(refs)}</ul></li>'
        )
    return ('<section class="detail uses" aria-label="Current project uses">'
            f'<h2>Current project uses ({len(uses)})</h2>'
            f'<ul class="uses-list">{"".join(rows)}</ul></section>')


def _publish_generation(staging: Path, target: Path) -> None:
    """Publish a generated gallery without ever renaming away the live page.

    Publication order is deliberate and is the interruption contract:

    1. immutable, content-addressed media (idempotent and additive),
    2. the side metadata (``media-manifest.json``, ``generation.json``),
    3. ``index.html`` **last**, as the single commit point.

    Every file is written to a sibling temp file and ``os.replace``d over the
    target (a rename, never a move-away), so the live entry point is at every
    instant either the previous complete page or the new one. If anything fails
    before step 3, the previous ``index.html`` still points at media that the
    additive step either kept or already had; the new page has not gone live.
    """
    target.mkdir(parents=True, exist_ok=True)
    # 1. Media: content-addressed, so copying is idempotent and additive.
    src_media = staging / "media"
    if src_media.is_dir():
        dst_media = _safe_under(target, "media", "gallery output media")
        dst_media.mkdir(parents=True, exist_ok=True)
        for entry in src_media.iterdir():
            if not entry.is_file():
                continue
            dst = dst_media / entry.name
            if os.path.lexists(dst):
                if _file_sha256(dst) == _file_sha256(entry):
                    continue
                raise DataError(f"gallery media collision for {entry.name}: existing file differs")
            tmp = _write_temp(dst, entry.read_bytes())
            os.replace(tmp, dst)
    # 2. Side metadata, written before the entry point that may reference it.
    for name in ("media-manifest.json", "generation.json"):
        src = staging / name
        if src.is_file():
            tmp = _write_temp(target / name, src.read_bytes())
            os.replace(tmp, target / name)
    # 3. The entry point is the commit point.
    index_src = staging / "index.html"
    if index_src.is_file():
        tmp = _write_temp(target / "index.html", index_src.read_bytes())
        os.replace(tmp, target / "index.html")
    _fsync_dir(target)


def _remove_tree(path: Path) -> None:
    import shutil
    try:
        shutil.rmtree(path)
    except OSError:
        pass


def _load_view_bindings(path: Optional[str]) -> Dict[str, str]:
    if not path:
        return {}
    document = _load_json(Path(path))
    if not isinstance(document, dict):
        raise DataError("view-bindings must be a JSON object")
    if "bindings" in document:
        document = document["bindings"]
        if not isinstance(document, dict):
            raise DataError("view-bindings 'bindings' must be an object")
    out: Dict[str, str] = {}
    for key, value in document.items():
        if not isinstance(key, str) or not key.strip():
            raise DataError("view-bindings keys must be non-empty strings")
        if not isinstance(value, str):
            raise DataError(f"view-bindings['{key}'] must be a string URL")
        safe, scheme = _classify_url(value)
        if not safe:
            raise DataError(f"view-bindings['{key}'] must be an http/https URL, got scheme {scheme!r}")
        out[key] = value
    return out


def cmd_gallery(args: argparse.Namespace) -> Tuple[int, Dict[str, Any]]:
    catalog = _load_catalog(args.catalog)
    dependencies = [_load_catalog(p) for p in (args.with_catalog or [])]
    bindings = _load_bindings(args, catalog, [d.id for d in dependencies])
    view_bindings = _load_view_bindings(args.view_bindings)
    result = _render_gallery(catalog, bindings, dependencies, Path(args.out),
                             view_bindings=view_bindings, argv_roots=args.root)
    return EXIT_OK, {"ok": True, "status": "generated", "out": args.out,
                     "catalog_id": catalog.id, **result}


# ---------------------------------------------------------------------------
# Parser / dispatch
# ---------------------------------------------------------------------------

def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--with-catalog", action="append", default=[],
                        help="read-only dependency catalogue (repeatable)")
    parser.add_argument("--root", action="append", default=[],
                        help="<catalog-id>:<alias>=<path> root binding (repeatable)")


def build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="fc_catalog", description="Frontend Craft visual catalogue CLI.")
    sub = parser.add_subparsers(dest="command", required=True)

    def add(name: str, help_text: str) -> argparse.ArgumentParser:
        child = sub.add_parser(name, help=help_text)
        child.add_argument("--catalog", required=True)
        _add_common(child)
        return child

    query = add("query", "bounded, deterministic catalogue search")
    query.add_argument("--role", choices=ROLES)
    query.add_argument("--task")
    query.add_argument("--language")
    query.add_argument("--medium")
    query.add_argument("--source", choices=SOURCE_KINDS)
    query.add_argument("--term", action="append", default=[])
    query.add_argument("--limit", type=int, default=12)
    query.add_argument("--offset", type=int, default=0,
                       help="unguarded manual page start (no stale-safe claim)")
    query.add_argument("--cursor", help="stale-safe continuation token from a prior next_cursor")
    query.add_argument("--include-archived", action="store_true")
    query.set_defaults(func=cmd_query)

    show = add("show", "show one item/use and its bounded direct relations")
    show.add_argument("--id", required=True)
    show.add_argument("--revision", type=int)
    show.set_defaults(func=cmd_show)

    resolve = add("resolve", "check each recorded asset/preview independently")
    resolve.add_argument("--id", required=True)
    resolve.add_argument("--revision", type=int)
    resolve.set_defaults(func=cmd_resolve)

    register = add("register", "validate, retain media, and atomically append a version")
    register.add_argument("--record-file", required=True)
    register.add_argument("--expect-revision", type=int, required=True)
    register.add_argument("--lock-timeout", type=float, default=5.0)
    register.set_defaults(func=cmd_register)

    validate = add("validate", "check structure, references, and current media")
    validate.set_defaults(func=cmd_validate)

    gallery = add("gallery", "generate a static, local-browsable HTML read")
    gallery.add_argument("--out", required=True)
    gallery.add_argument("--view-bindings")
    gallery.set_defaults(func=cmd_gallery)

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
    if getattr(args, "offset", None) is not None and args.offset < 0:
        parser.error("--offset must be >= 0")
    if getattr(args, "revision", None) is not None and args.revision < 1:
        parser.error("--revision must be >= 1")

    try:
        code, payload = args.func(args)
    except UsageError as exc:
        return _emit({"ok": False, "status": "usage_error", "error": "usage_error", "message": str(exc)}, EXIT_USAGE)
    except LockBusyError as exc:
        return _emit({"ok": False, "status": "busy", "error": "busy", "message": str(exc)}, EXIT_BUSY)
    except ConflictError as exc:
        return _emit({"ok": False, "status": "conflict", "error": "conflict", "message": str(exc)}, EXIT_CONFLICT)
    except MissingError as exc:
        return _emit({"ok": False, "status": "missing", "error": "missing", "message": str(exc)}, EXIT_MISSING)
    except DataError as exc:
        return _emit({"ok": False, "status": "invalid", "error": "invalid", "message": str(exc)}, EXIT_INVALID)
    except OSError as exc:
        # A filesystem failure (for example a write/rename that cannot complete)
        # is reported as a stable, machine-readable error; the previous complete
        # file is left in place by the atomic-write helpers.
        return _emit({"ok": False, "status": "write_failed", "error": "write_failed",
                      "message": str(exc)}, EXIT_MISSING)
    return _emit(payload, code)


if __name__ == "__main__":
    sys.exit(main())
