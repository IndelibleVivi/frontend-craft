# Catalogue operations

Use when registering, validating, resolving, querying, or rendering the Frontend
Craft visual catalogue: the public positive-instance library, a project's
reference collection, and a cross-project materials collection. The helper is
`scripts/fc_catalog.py` and uses only the Python standard library. It never
fetches or uploads anything, never executes a recorded command, and never scans
a root you did not name.

This runbook owns the operational contract of the helper: the accepted JSON
payloads, the CLI verbs, the root-binding rules, and the failure semantics.
`references/style-slots.md` owns what makes a style, palette, or combination;
`references/design-learning.md` owns feedback and cases; `references/build.md`
and `references/state-contracts.md` own how chosen relations reach a real
project. The catalogue only records identity, provenance, materials, and uses.

## One document, three collections

Every collection is one JSON file with the same top-level shape:

```json
{
  "version": 1,
  "id": "fc-library",
  "revision": 7,
  "items": [],
  "uses": []
}
```

- `version` is the **format** version and must be the integer `1`. Any other
  value is a hard error; the helper never guesses at another format.
- `id` is the stable collection id (for example `fc-library`,
  `sample-reader-project`, `shared-materials`). It is the identity used by every
  cross-collection reference.
- `revision` is the whole-file monotonic revision. It increases by one on every
  successful `register` that actually writes.
- `items` holds item versions; `uses` holds project adoption relations. Both are
  keyed by `(id, revision)` and must be unique. The **highest** revision of an id
  is the current version; older versions are history and never expire.
- An optional `archived: true` on an item version removes it from default
  discovery without invalidating an exact historical reference to it.

Suggested locations: `examples/library/catalog.json` for the public library,
`<project>/.frontend-craft/catalog.json` for a project's own collection, and an
already-authorized private FC location for cross-project materials. Personal
screenshots, cases, and credentials stay outside the public repository.

## Root bindings and locators

A `locator` is always `{"root": <alias>, "path": <relative path>}`. The path is
relative and must not be absolute, must not contain `..`, and the resolved real
path (following symlinks) must stay inside the bound root.

- The alias `catalog` always means "the directory holding this catalogue file".
  It cannot be rebound.
- Every other alias must be bound explicitly with a repeatable
  `--root <catalog-id>:<alias>=<path>`. The `<catalog-id>` scopes the binding to
  one collection, so two projects can each bind their own `project` root without
  collision. A binding whose id was not supplied (neither the primary catalogue
  nor a `--with-catalog`) is a usage error.
- The alias `project` conventionally points at the project root; `materials`,
  `captures`, and similar names are free-form.

`catalog` and `project` are the only aliases with conventional meaning, and only
`catalog` is fixed.

## Commands

```text
python3 scripts/fc_catalog.py query   --catalog <path> [--with-catalog <dep>]...
          [--root <id>:<alias>=<path>]... [--role <role>] [--task <t>]
          [--language <tag>] [--medium <m>] [--source <kind>] [--term <text>]...
          [--limit <n>] [--cursor <token> | --offset <n>] [--include-archived]
python3 scripts/fc_catalog.py show    --catalog <path> --id <id> [--revision <n>] [...]
python3 scripts/fc_catalog.py resolve --catalog <path> --id <id> [--revision <n>] [...]
python3 scripts/fc_catalog.py register --catalog <path> --record-file <json>
          --expect-revision <n> [--lock-timeout <seconds>] [...]
python3 scripts/fc_catalog.py validate --catalog <path> [...]
python3 scripts/fc_catalog.py gallery --catalog <path> --out <path>
          [--view-bindings <json>] [...]
```

All verbs accept repeatable `--with-catalog <path>` (read-only dependency) and
`--root <id>:<alias>=<path>`. `query`, `show`, `resolve`, and `validate` are
read-only. `register` writes only the primary catalogue. `gallery` writes only
its `--out` directory.

- **query** searches the primary catalogue and its dependencies. It filters on
  `role`, `task`, `language`, `medium`, `source` kind (authored/external/generated),
  and casefolded `--term` substrings over
  id/title/summary/tags. Results are ordered deterministically (items referenced
  by current uses first, then by collection id, then item id). It returns
  `matched`, `returned`, `truncated`, and the `revisions` map.
  - Continuation has two modes. `--offset` is **unguarded manual paging**: it
    slices the current result list and makes no stale-safe claim (`guarded:
    false`). `--cursor <token>` uses the opaque `next_cursor` from a previous
    page and is **stale-safe**: the token binds the filters, the exact catalogue
    set, each collection's whole-file revision, and the next offset. A
    continuation is rejected with `conflict` (exit 2) if a catalogue revision
    changed, and with `usage_error` if the filters differ or the token is
    malformed. Pass `--cursor` and `--offset` at most one at a time.
- **show** reads one item or use, its bounded direct relations, its history, and
  the uses that reference it. It never claims a file was viewed.
- **resolve** checks each recorded asset and preview independently against the
  real file and recorded digest. Statuses are `available`, `missing`, `changed`,
  `remote-only`, and `unavailable`. It reports `partial` and a non-zero exit
  when anything is missing, changed, or unavailable — a missing derivative never
  hides an available original. It also returns a bounded `bundle` with the exact
  files needed to resume: the `source` metadata, the `specimen` (`entry`,
  `source`, `notes`, and its `media` locator resolution), the `making` notes, the
  `derivation` (`script` locator resolution and each `sources` entry resolved to
  its exact asset/preview), and the `materials` entries. A reference with an
  `asset_id` selects that asset only; with a `preview_id` that preview only;
  with neither, all of the target item's assets and previews. Unbound roots,
  missing files, and not-recorded locators are explicit (`unavailable`,
  `missing`, `not-recorded`); no source or recipe is ever executed.
- **register** validates, retains media, and atomically appends a version. See
  below.
- **validate** checks the format, role-required payloads, and unique `(id,
  revision)` pairs, then checks **every preserved revision** (not only the
  current one) of every item and use: bounded references, `use.evidence.previews`
  references, the `specimen` and `derivation.script` locators, and each item's
  own assets and previews. It reports structural `errors` (invalid references or
  payloads) separately from `missing_media` (absent, changed, remote-only, or
  unbound files), each labelled with the exact `item 'id'@revision` / `use
  'id'@revision` and location, so a missing file never masquerades as a clean
  pass and a missing file is never reported as an invalid reference. Cross-
  collection derivation acyclicity and exact derivation sources are checked
  across all supplied collections.
- **gallery** renders a static page. See below.

## Item payload (for `register` and the file)

An item requires `id`, `revision`, `title`, and `roles`. `roles` is a non-empty
list drawn from `reference`, `material`, `style`, `palette`, `combination` and
may overlap. Role-required payloads:

- `style` and `combination` describe a positive instance that a reader can
  actually look at, so each requires a `making` block, at least one `previews`
  entry, and a `specimen` block (entry point and making notes).
- `palette` requires a `making` block and a real `palette` block (roles, values,
  and an `instance` reference). A palette is viewable through its role values
  and instance relation, so it does not additionally require a `specimen`.

Optional fields, validated when present:

| Field | Shape |
| --- | --- |
| `source` | `{"kind": "authored"\|"external"\|"generated", "url"?, "author"?, "version"?, "ref"?, "note"?}`; `external` requires a URL |
| `tags` | `{"tasks"?: [...], "languages"?: [...], "media"?: [...], "scales"?: [...], "terms"?: [...]}` |
| `previews` | list of `{"id", "kind", "locator", "digest"?, "capture"?, "label"?, "url"?}` |
| `assets` | list of `{"id", "locator"?, "url"?, "file_type"?, "sha256"?, "version"?, "axes"?, "note"?}` |
| `specimen` | `{"entry"?, "source"?, "notes"?, "locator"?, "url"?}`; `entry` is how to run/open it (`"open index.html"`), `locator` is `{root, path}` to the runnable source file |
| `making` | `{"effect", "carry": [...], "vary": [...], "limits"}` — all strings; copied as notes, never executed |
| `palette` | `{"roles": {<role>: {"value", "foreground"?, "background"?, "area"?, "note"?}}, "instance": <ref>, "state"?}` |
| `materials` | list of references; each may select one `asset_id` or one `preview_id` |
| `derivation` | `{"sources": [<ref>...], "script"?: {root, path}, "steps"?: [str...], "inputs"?, "outputs"?}`; `script` is a locator only, never executed |
| `rights` | `{"status": "known"\|"unknown", "license"?, "url"?, "terms"?, "note"?}` |
| `evidence` | `{"rendered"?: bool, "operated"?: bool, "observed"?: <UTC timestamp>, "source"?: object, "previews"?: [<ref>...], "case"?: object}` |
| `summary` | short display string |

A **reference** is `{"catalog_id", "item_id", "revision"}` plus at most one of
`asset_id` or `preview_id` (they are mutually exclusive).

`previews[].kind` is one of `screenshot`, `image`, `video`, `audio`,
`keyframes`, `type-specimen`, `palette`, `source`. A `capture` block may carry
`viewport` (`[w, h]`), `coverage` (`surface`/`full`/`clip`/`sequence`), `state`,
`taken_at`, `clip`, `sequence`, or `note`.

`digest` (previews) and `sha256` (assets) are lowercase hex SHA-256 values. A
SHA-256 is only meaningful next to a local `locator`; a remote-only asset must
not fabricate one.

`evidence` records what the caller actually did, and the helper never upgrades
it:

- `rendered` / `operated` are booleans: did the caller render this item, and did
  the caller operate the described interaction. A still screenshot is not
  `operated`.
- `observed` is a UTC timestamp (`...Z`) of the caller's observation. It is a
  caller record, **not** a helper-verified acceptance or quality check.
- `source` is a free-form object describing the working copy (for example
  `{"working_copy": "synthetic fixture after a reader revision"}`); `case` links
  a private case id. `previews` is a list of references to recorded captures.

## Use payload (adoption facts)

A use record requires `id`, `revision`, `target`, `references`, `relation`, and
`status`, and field set is closed:

```json
{
  "id": "reader-margin-use",
  "revision": 1,
  "target": {
    "project": "sample-reader",
    "surface": "reader",
    "location": {"path": "src/pages/Reader.tsx", "region": "article and note"}
  },
  "references": [
    {"catalog_id": "fc-library", "item_id": "reading-margin", "revision": 1},
    {"catalog_id": "shared-materials", "item_id": "sample-title-font",
     "revision": 2, "asset_id": "web-subset"}
  ],
  "relation": "Body stays continuous; the note sits near its anchor.",
  "status": "in-use",
  "observed_at": "2026-10-07T16:00:00Z",
  "evidence": {"previews": [{"catalog_id": "sample-reader-project",
    "item_id": "reader-result", "revision": 1, "preview_id": "wide-note-open"}]}
}
```

- `status` is `selected` (planned or trying), `in-use` (the caller checked it in
  real source/render), or `past` (replaced; history stays readable).
- `in-use` requires `observed_at`, a caller-recorded UTC observation time. The
  helper fills it with the registration time if you omit it, so it is a
  generated fact you never hand-write. `observed_at` records when the caller
  looked; it is **not** a helper-verified acceptance and does not assert that a
  design was seen, executed, or approved.
- `target.location.path` is relative to the project root and must not traverse.
  A region name alone (no path) is allowed.

Use facts, download facts, and preference facts are separate. "Downloaded but
unused", "used but the whole direction was rejected", "only the title was liked"
must remain expressible; do not compress them into a single linear status.

## Register input

`--record-file` is one JSON object:

```json
{
  "catalog_id": "sample-reader-project",
  "kind": "item",
  "item": { ...item payload... },
  "retain": [
    {"id": "s", "root": "project", "path": "assets/shot.png"}
  ]
}
```

- `kind` is `item` or `use`. `catalog_id` is optional for a new file (the helper
  uses the file's name) but must match an existing catalogue's `id`.
- **Batch / full-version import.** Instead of `kind`, pass `"items": [...]`
  and/or `"uses": [...]` (each element is a full item/use payload, no wrapper).
  The whole package is validated and committed atomically as one new file
  revision. In this form the explicit `revision` on each element is a claim
  about the exact version being written and is **verified** against the next
  free revision; a mismatch is a hard error (`invalid`), never a silent
  renumber. The single `kind` form appends and assigns the next revision, so a
  resubmitted older value becomes a new current version.
- `retain` lists real files, inside an explicitly bound root, to copy into the
  catalogue's immutable media store. Each entry needs a unique `id`; `root` and
  `path` locate the source.
- Inside the item payload you may reference a retained file with a placeholder
  locator `{"root": "retain", "path": "<retain id>"}`. The helper rewrites it to
  the real `{"root": "catalog", "path": "media/sha256/<digest><suffix>"}` and
  records the digest.
- Alternatively, an asset or preview may carry an inline
  `"input_locator": {"root": ..., "path": ...}`. The helper retains that file the
  same way and replaces `input_locator` with the immutable `locator` and digest.
- You may also give a concrete locator under any bound root and omit `sha256`
  (assets) or `digest` (previews); the helper computes the digest from the real
  file and records it. A remote-only asset should not carry a local digest.

`--expect-revision` is the file revision you last read (use `0` for a new
collection). Behaviour:

1. The helper holds a bounded OS advisory lock across read → check → validate →
   write → atomic replace. Locks are never removed based on age.
2. If your `--expect-revision` is stale **and** the submission adds genuinely new
   or changed content, it returns `conflict` with the current revision and
   leaves the file untouched. Re-read and merge.
3. If the whole submission already exists unchanged, it returns `unchanged`
   even at a stale expected revision — nothing would be written. Generated
   fields (revision numbers, `observed_at`, the registration timestamp, and
   derived digests) are ignored in this comparison, so re-running the same
   registration is idempotent.
4. Media is retained **before** the catalogue is published. An existing
   immutable file with the same digest is reused; a different file with the same
   name is never overwritten. A new `screenshot.png` produces a new digest and
   leaves the earlier capture intact.
5. The write goes to a temporary file and is `os.replace`d into place, so an
   interruption leaves the previous complete catalogue readable. A failure
   before publish leaves no half-written catalogue and no claimed new version.

Machine-readable results use a stable `ok`/`status` plus the object and reason.
A partial file result is reported as partial; a missing file may return a
readable partial result rather than a silent full success. Exit codes:
`0` ok, `2` conflict/usage, `3` not found, `4` missing/partial, `5` invalid,
`6` busy. A filesystem write failure is reported as `write_failed` with exit
`4`; the atomic-write helpers leave the previous complete file in place.

## Gallery

`gallery --catalog <project catalog> --out <dir>` renders a static, locally
browsable page. It presents the primary catalogue's own current (non-archived)
items and copies only the media they reference — not the whole library.

- Media is copied into `<out>/media/` under content-addressed names and
  referenced through relative URLs, so the page works even when the catalogue,
  source media, and output live under different authorized roots.
  The manifest maps each digest-plus-extension filename to its relative URL.
  A changed capture is an explicit gap, never substituted into an old revision.
  Available local assets have download links to their actual copied bytes;
  only assets belonging to the selected items are copied. Image previews can
  toggle between fit-to-view and original size, with a scrollable viewport.
- Items are rendered in escaped text; the page never executes source HTML,
  recorded script strings, or an SVG as a document. SVG previews are shown with
  `<img>`, so any script inside the SVG never runs. External links accept only
  `http`/`https`; `javascript:` and other active schemes are refused.
- No absolute host paths, private case bodies, or unrelated materials are
  copied into the page.
- `--view-bindings` maps an **exact revision** to a currently running specimen
  URL, for example
  `{"bindings": {"fc-library:reading-margin:2": "https://127.0.0.1:5199/run"}}`.
  Keys are `<catalog_id>:<ref_id>:<revision>` (an item or use id),
  formed by URL-encoding each id separately; for example `a:b` becomes `a%3Ab`.
  This prevents delimiters inside an identity from binding a different item.
  A binding is used only for the revision it names: an id-only or wrong-revision key never
  binds, so a running instance started for one version is never shown as the
  instance for another. Values must be `http`/`https`. When a revision has no
  binding the page shows a clear "not yet running" state and the recorded entry
  instead of a fabricated clickable link. This file is a local running binding;
  it does not replace the canonical locator.
- Output is staged in a scratch directory and published file by file, in a
  deliberate order: (1) immutable content-addressed media under `<out>/media/`,
  (2) the side metadata (`media-manifest.json`, `generation.json`), and (3)
  `index.html` **last**, as the single commit point. Every file is written to a
  sibling temp file and `os.replace`d over its target, so the live entry point
  is at every instant either the previous complete page or the new one — there
  is no window where `<out>/index.html` is missing, and a failure before step 3
  leaves the previous page usable. Unrelated files already in `<out>` are never
  deleted. A process killed mid-publication (for example `SIGKILL`) may leave
  unreferenced immutable media or `.tmp` files behind; that is expected, and
  they do not affect the live page. The page shows current items, roles
  (Styles/Palette/Combinations via `style`/`palette`/`combination`), history,
  materials, missing-media states, and exact source links. Filtering, scroll
  restoration on return, and keyboard/escape navigation are handled client-side
  with no external accounts.

Palette values are applied only as a CSS color property, never injected as
style declarations. Retained-media and output-media directories obey the same
root-containment rule; a symlink that escapes the designated root is refused.

Regenerating after a source change is expected; the output is disposable. The
page is a read of the catalogue, never a second source of truth.

## Failure semantics to keep honest

- A cross-collection reference whose collection was not supplied returns
  `unresolved-catalog` with the required id. The helper never probes arbitrary
  disk locations.
- `derivation.sources` must be acyclic; a cycle is a hard invalid. General
  `materials` and preview/reference relations **may** cycle.
- Unknown format versions, unknown keys, wrong types (for example a boolean
  where an integer revision is required), unknown roles, absolute or
  traversing locators, escaping symlinks, and active URL schemes in metadata are
  all invalid, each with a specific reason.
- `validate` success means the structure and resolvable references are sound.
  It does **not** mean every file is present and does not establish that any
  design was seen, executed, or accepted.

## Synthetic walkthrough

`examples/catalog/` is a small, portable, synthetic fixture: a public
`library/` collection, a cross-project `materials/` collection, and a
`project/` collection whose use references both. It exists to exercise the CLI
end to end and to show the storage and continuation shape. It is **not** a
design or style claim; the scenes and font bytes are invented placeholders.
Every command below is read-only except the last, which only writes into a
temporary output directory you name.

```bash
# Structure and resolvable references are sound.
python3 scripts/fc_catalog.py validate \
  --catalog examples/catalog/project/catalog.json \
  --with-catalog examples/catalog/library/catalog.json \
  --with-catalog examples/catalog/materials/catalog.json
# -> status "valid"

# Find a making relation; the library is the primary catalogue.
python3 scripts/fc_catalog.py query \
  --catalog examples/catalog/library/catalog.json \
  --with-catalog examples/catalog/materials/catalog.json \
  --role style --term reading
# -> status "matched", one current style item (`sample-library/reading-margin`),
#    and a `revisions` map for continuation

# Page deterministically with the stale-safe cursor. The first page returns a
# `next_cursor`; a continuation is rejected if any catalogue revision changed.
python3 scripts/fc_catalog.py query \
  --catalog examples/catalog/library/catalog.json \
  --with-catalog examples/catalog/materials/catalog.json --limit 1
# -> matched 2, returned 1, truncated true, next_cursor "<opaque token>"
python3 scripts/fc_catalog.py query \
  --catalog examples/catalog/library/catalog.json \
  --with-catalog examples/catalog/materials/catalog.json --limit 1 \
  --cursor '<paste next_cursor from the previous command>'
# -> the second item (`sample-materials/sample-title-font`); guarded true

# Read one exact revision and its bounded direct relations.
python3 scripts/fc_catalog.py show \
  --catalog examples/catalog/library/catalog.json \
  --id reading-margin --revision 2

# Check every recorded file against its digest. The referenced font asset
# resolves through the materials collection's own `catalog` root.
python3 scripts/fc_catalog.py resolve \
  --catalog examples/catalog/library/catalog.json \
  --id reading-margin \
  --with-catalog examples/catalog/materials/catalog.json
# -> status "resolved"; `bundle.materials[0]` is "available" with a `via`
#    reference to `sample-materials/sample-title-font`; `bundle.making` carries
#    the effect/carry/vary/limits notes; `bundle.specimen.media` is
#    "not-recorded" because the fixture records only an entry command

# Render the project gallery: its own items plus the exact dependency
# revisions it references, with media copied to a relative `media/` directory.
python3 scripts/fc_catalog.py gallery \
  --catalog examples/catalog/project/catalog.json \
  --out /tmp/fc-catalog-walkthrough \
  --with-catalog examples/catalog/library/catalog.json \
  --with-catalog examples/catalog/materials/catalog.json
# -> index.html, media/, media-manifest.json, generation.json
```

To bind a running specimen, write a small JSON file and pass
`--view-bindings bindings.json`; keys are `<catalog_id>:<ref_id>:<revision>`
and values must be `http`/`https` (see the Gallery section above). Without a
binding the page shows an honest "not yet running" state.

Register into a **copy** of the fixture if you want to see a write; do not
mutate the tracked example. A registration record that retains a real file, so
you can see the immutable media store and digest reuse, looks like this:

```json
{
  "catalog_id": "sample-reader-project",
  "kind": "item",
  "item": {
    "id": "new-capture",
    "revision": 1,
    "title": "A new capture",
    "roles": ["reference"],
    "previews": [
      {"id": "wide", "kind": "screenshot",
       "input_locator": {"root": "project", "path": "captures/reader-result.svg"}}
    ]
  }
}
```

Run it against a copy of the project collection (the `project` root is bound to
that copy so the synthetic capture is found):

```bash
cp -R examples/catalog/project /tmp/fc-catalog-register
python3 scripts/fc_catalog.py register \
  --catalog /tmp/fc-catalog-register/catalog.json \
  --record-file record.json --expect-revision 1 \
  --root sample-reader-project:project=/tmp/fc-catalog-register
```

The helper computes the digest, copies the file to
`media/sha256/<digest>.svg` inside the copied catalogue's directory, and returns
`status: "registered"` with the assigned `revision`. Re-running the same record
with a stale `--expect-revision` returns `unchanged` rather than creating a
duplicate.
