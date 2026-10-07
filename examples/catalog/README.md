# Catalogue CLI walkthrough (synthetic)

This directory is a small, portable **synthetic** fixture for
`scripts/fc_catalog.py`. It demonstrates the storage and continuation shape of
one document format across three collections:

| Path | Collection id | Role |
| --- | --- | --- |
| `library/catalog.json` | `sample-library` | a public positive-instance library (a style with two revisions and a palette) |
| `materials/catalog.json` | `sample-materials` | a cross-project materials collection (a placeholder font asset) |
| `project/catalog.json` | `sample-reader-project` | a project collection whose use references both |

Everything here is invented: the scenes are placeholder SVGs, the font file is a
few synthetic bytes, and the project name `sample-reader` is fictional. This
fixture is for exercising the CLI and for checking that references, revisions,
root bindings, resolution, and gallery rendering behave; it is **not** a design
or style claim, not a measured quality improvement, and not evidence that any
Frontend Craft run happened. There are no personal records, credentials, or
machine-specific paths.

It also exercises the two continuation shapes: `query` returns a stale-safe
`next_cursor` (an opaque token bound to the filters and catalogue revisions)
alongside unguarded manual `--offset` paging, and `resolve` returns a bounded
`bundle` with the exact specimen/recipe/material files needed to resume.

Ordinary read-only examples, the full field contract, and the failure
semantics live in
[`references/catalog-operations.md`](../../references/catalog-operations.md).
Start there; the shortest version is:

```bash
python3 scripts/fc_catalog.py validate \
  --catalog examples/catalog/project/catalog.json \
  --with-catalog examples/catalog/library/catalog.json \
  --with-catalog examples/catalog/materials/catalog.json
```

The `gallery` example writes only to the `--out` directory you name. To try a
`register`, copy the fixture to a temporary directory first so the tracked
example stays unchanged.
