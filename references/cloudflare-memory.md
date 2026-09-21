# Cloudflare memory (semantic retrieval)

Optional layer that adds semantic recall to the local case store: Cloudflare
Workers AI (`@cf/baai/bge-m3`) embeds a small allowlisted slice of each case and
Vectorize stores the vectors plus opaque scope/revision metadata. The canonical
records stay local and remain the only source of truth. Lexical `--term` queries
stay fully offline; this layer reaches paraphrased or cross-language queries the
lexical path misses.

Everything below is portable: no personal account ids, tokens, or absolute
paths appear as literals. Substitute your own values.

Model and geometry are fixed: `@cf/baai/bge-m3`, 1024 dimensions, cosine. The
config cannot promise another model.

## 1. Prerequisites

- Python 3.9+ (stdlib only; no pip installs).
- A Cloudflare account id and an API token with Workers AI + Vectorize access.
- Node/Wrangler only for `auth: "wrangler"` or one-time index provisioning.

## 2. Initialize the local store

```bash
export FC_ROOT="<an explicitly authorized directory>"
python3 scripts/fc_memory.py init --root "$FC_ROOT" --mkdir \
  --project "<project-slug>" --surface "<surface-name>"
```

`--mkdir` creates a missing root; `init` never overwrites an existing
`context.md`/`cases.json`. The template has both **Current aims** and **Current
boundaries** because positive intent matters as much as prohibitions.

## 3. Configure the target

Create `"$FC_ROOT/cloudflare.json"`:

```json
{
  "version": 1,
  "account_id": "<32-hex account id>",
  "index_name": "frontend-craft-memory",
  "namespace": "fc-<stable-random-id>",
  "model": "@cf/baai/bge-m3",
  "dimensions": 1024,
  "metric": "cosine",
  "auth": "env"
}
```

- `model`/`dimensions`/`metric` are validated to the fixed values above.
- `auth: "env"` reads `CLOUDFLARE_API_TOKEN`. `auth: "wrangler"` captures the
  token from `npx --yes wrangler@4.135.0 auth token --json`. Tokens are never
  written to disk or printed, and provider error text is never echoed.

## 4. Provision the index (runbook step; not automated by the CLI)

Create the index and two metadata indexes once. `namespace` is a native
Vectorize vector attribute, not a metadata property, so it does **not** need a
metadata index. Confirm the exact flag spelling with
`npx --yes wrangler@4.135.0 vectorize create-metadata-index --help`; the
installed CLI uses `--propertyName` (no hyphen, camelCase):

```bash
npx --yes wrangler@4.135.0 vectorize create frontend-craft-memory \
  --dimensions=1024 --metric=cosine

npx --yes wrangler@4.135.0 vectorize create-metadata-index frontend-craft-memory \
  --propertyName=project_key --type=string
npx --yes wrangler@4.135.0 vectorize create-metadata-index frontend-craft-memory \
  --propertyName=surface_key --type=string
```

Metadata indexes must exist before sync. `sync --apply` refuses to embed until
it has verified them, because records inserted before the indexes cannot be
scope-filtered. The list endpoint reports `indexType` as `String` (capital S);
the check is case-insensitive.

## 5. Verify with doctor

```bash
python3 scripts/fc_memory.py doctor --root "$FC_ROOT"
```

Checks config, local `context.md`/`cases.json` (separately), auth, the remote
index **config** (`GET .../indexes/{index}` → `result.config.dimensions` and
`result.config.metric`) and **info** (`GET .../indexes/{index}/info` →
`result.dimensions`, `result.vectorCount`, `result.processedUpToMutation`), and
the metadata index list
(`GET .../indexes/{index}/metadata_index/list` → `result.metadataIndexes[]`).
`doctor` is a readiness check; it does not prove a data query works. Exit 0 =
ready; 6 = remote/auth problem; 5 = invalid config.

## 6. Sync (dry-run first)

```bash
python3 scripts/fc_memory.py sync --root "$FC_ROOT"           # dry-run
python3 scripts/fc_memory.py sync --root "$FC_ROOT" --apply   # network writes
python3 scripts/fc_memory.py sync --root "$FC_ROOT" --apply --wait
python3 scripts/fc_memory.py sync --root "$FC_ROOT" --verify  # re-check pending only
```

Dry-run prints the exact upload fields, counts, and deletion ids. `--apply`
embeds only **new or changed active** cases and deletes vectors for
retired/superseded/removed ones. `--wait` requires `--apply` and runs a bounded
resume loop over the canonical readback verification (below); without it, a
queued write is reported `pending`, never `ready`. `--verify` re-checks the
persisted pending state with no re-embedding and exits 7 while it is still
pending. `--wait` and `--verify` use the same evidence rule.

Only these fields are embedded: `title`, `statement`, `next_action`,
`keywords`, `limits`. The helper does not send `context.md` or the `evidence`
field. Review the selected text before authorizing sync: allowlisting field
names is not automatic redaction of private details written inside them.

## 7. Sync state

`.fc-sync-state.json` records the target fingerprint, each vector's
revision/scope, `pending_mutations` (with the ids each covers and their
expected revisions and scope keys), and `pending_deletions`. Writes are atomic;
both the file and its `.tmp` path are refused if they are symlinks. The pending
state describes the **latest acknowledged operation per id**, so an earlier
pending upload is replaced when the id changes revision or is deleted, and an
obsolete pending deletion is dropped when the id is re-added and that operation
is accepted. Each acknowledged batch is persisted before the next one. A
failed or unattempted batch stays in the next sync plan; an accepted pending
batch is checked by readback without re-embedding. If the network or process
fails after the server accepts a request but before its receipt is saved, a
retry may repeat that idempotent upsert/delete; do not claim atomicity across
the local file and the remote service.

Because the index may be shared by several catalog namespaces,
`processedUpToMutation` can advance past our ids without our write being done.
So `sync --verify` clears a pending upload only when `get_by_ids` returns the
vector with **our namespace, the current revision, and the expected scope
keys**, and clears a pending deletion only when the id is absent. The mutation
pointer is never evidence. A malformed `get_by_ids` result is an explicit remote
error, never treated as "all ids absent". A manifest for a different target is
refused, so a changed config cannot drive deletions of vectors this catalog did
not write, and `--verify` cannot clear pending state against another target.

`--wait` and `--verify` share this one rule; `--wait` only retries it a bounded
number of times. `--verify` reports local write/delete state only. It is **not**
a claim about query recall quality; that is observed by an actual query.

## 8. Query

```bash
# lexical, offline
python3 scripts/fc_memory.py query --root "$FC_ROOT" \
  --project "<project-slug>" --surface "<surface>" --term "<keyword>"

# semantic, natural language (aims and boundaries both)
python3 scripts/fc_memory.py query --root "$FC_ROOT" \
  --project "<project-slug>" --surface "<surface>" \
  --query "make the reading surface calmer and keep help discoverable"

# cross-project mechanism candidates
python3 scripts/fc_memory.py query --root "$FC_ROOT" \
  --project "<project-slug>" --surface "<surface>" \
  --term "grouping" --transfer
```

- Scope is exact project/surface plus the global `*` value on each axis. A user
  request for `*` is not "the whole store". The query carries the native
  `namespace` and filters on the `project_key`/`surface_key` metadata indexes;
  each returned hit is re-checked against the local record (scope, status,
  revision), so the remote filter is never trusted alone.
- `--transfer` drops the project filter but keeps surface, so another project's
  mechanism case can match. Each hit is labeled `analogy` with its origin
  `current_scope`; it is never promoted to a current preference.
- Candidate count is bounded (`topK` capped at 50 with `returnMetadata: all`,
  the platform limit when metadata or values are returned), so it is not the
  count of all relevant records.
- A remote/auth failure is a transparent `remote_error`/`auth_error`; it is
  **never** silently downgraded to a lexical result.

## Boundaries and limits

- Optional: missing config, missing token, or no network degrades to clear
  errors while the offline verbs keep working.
- Vectorize stores vectors and opaque metadata only; no body text. Scope keys
  and ids are SHA-256 hex so names do not leak and long names cannot truncate.
- Cost: each `--apply` embeds only changed actives; each semantic query embeds
  one query string. Large-store latency has not been measured.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | success (including dry-run and no_match) |
| 2 | usage error |
| 3 | `show` unknown id |
| 4 | required file/root absent |
| 5 | invalid config or local store |
| 6 | remote or auth error |
| 7 | mutation still pending |
