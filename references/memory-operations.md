# Memory operations

Use when reading, recording, revising, or retiring Frontend Craft design
records, or when querying reusable experience cases. This is a small file-based
method; it is not an automatic memory service. Missing records are never a
blocker.

Verb scope: `query`, `show`, and `validate` are read-only and never modify
records. `init` creates the first records if absent and never overwrites.
`sync`/`doctor` are network verbs; `sync` is dry-run unless `--apply`. Editing
records themselves always goes through your normal file tools.

## Two files, two jobs

Both files live directly inside one caller-authorized root (for Codex, the
operator's designated private FC directory). The canonical read path opens only
`context.md` and `cases.json` in that root; it does not recurse, follow
references, or follow symlinks to those files.

The optional Cloudflare path also reads `cloudflare.json`; sync maintains its
derived `.fc-sync-state.json` in the same root.

| File | Owns | Read policy |
| --- | --- | --- |
| `context.md` | The small, human-maintained **current** aims, preferences, and boundaries | Read **whole** on relevant design/revision work. Returned whole by every query |
| `cases.json` | A growing, human-reviewed ledger of **reusable experience cases** | Reconciled and queried by scope/status, then literal terms or configured semantic recall |

Do not copy `context.md` into `cases.json` or build a second preference
profile. `context.md` remains the authority for current preferences; the case
store is evidence you may reuse, not a parallel profile.

Growth is expected. The ledger is meant to accumulate cases over time; the
helper stays bounded and honest about its own limits (see *Growth and the
lexical ceiling* below).

## When to read which

- A relevant design or revision task: read `context.md` whole. It is short.
- A task where a past case could change a concrete choice: query `cases.json`
  by scope and relevant terms or a natural-language `--query` when configured.
- You need a bounded listing of the current scope: query with no terms for a
  paged-by-`--limit` `scope_only` listing (not an exhaustive dump).
- No `cases.json`: query reports `store_missing`; continue with `context.md`,
  project `DESIGN.md`, and the current request.

## The case store

`cases.json` is a single JSON object:

```json
{
  "version": 1,
  "cases": [
    {
      "id": "fc-inline-help-2026-09-21",
      "title": "Inline help must stay visible",
      "updated": "2026-09-21",
      "scope": { "project": "lumen-notes", "surface": "*" },
      "status": "active",
      "basis": "explicit-feedback",
      "outcome": "rejected",
      "statement": "A hover-only help cue read as missing during testing.",
      "next_action": "Keep the primary inline help visible near the control.",
      "limits": "Not a global ban on tooltips or secondary hints.",
      "evidence": ["pointer to the feedback receipt; do not open automatically"],
      "keywords": ["help", "inline help", "提示", "可见"]
    }
  ]
}
```

Field rules:

- `version` must be the JSON integer `1` (`true`, `1.0`, and strings are
  rejected).
- `updated` is a real `YYYY-MM-DD` date.
- `scope` is a single value per axis; `*` means cross-project or cross-surface.
- `status`, `basis`, and `outcome` are independent:
  - `status`: `active` | `superseded` | `retired`;
  - `basis`: `explicit-feedback` | `observed-result` | `hypothesis` |
    `temporary-compromise`;
  - `outcome`: `accepted` | `rejected` | `mixed` | `unknown`.
- **`active` is a lifecycle, not owner approval.** Keep `basis` visible: an
  `active` case with `basis: hypothesis` is still only a hypothesis. Agent
  judgment must never promote an inference into an explicit preference.
- `evidence` entries are pointers; the helper does not open them, and a link is
  not proof that an artifact is verified.
- `superseded_by` is **required** when `status` is `superseded`. It must name
  another case in the same store with the **same scope**, not point at itself,
  and not form a cycle. A changed scope is a coexisting case, not a global
  replacement.

## Write, revise, retire (with existing file tools, not this helper)

Existing canonical records are edited through your normal file-editing tools:
read the current file first, make the minimal change, read it back, and run
`validate`. The helper does not infer or rewrite their meaning. Synchronize an
authorized configured index after a change; see the Cloudflare section below.

To create the first `context.md`/`cases.json` in an authorized root, use the
offline `init` verb (it never overwrites existing files):

```bash
python3 scripts/fc_memory.py init --root "<authorized-root>" \
  --project lumen-notes --surface editor
```

- **Write** within existing task/storage authorization. Worth recording:
  positive wishes, praise, objections, clarification, a clearly observed result,
  or a hypothesis/temporary compromise you
  want to keep honestly labeled. State the true `basis` and `outcome`, and do
  not raise an observation, hypothesis, or temporary compromise to an owner
  preference. One clear "don't do this again" is enough to affect the next task
  in its scope. If there is no write authorization, keep the observation
  in-session.
- **Clarify**: if the same case still holds but is worded better, keep its
  stable `id` and update `updated` to the revision date.
- **Replace**: if a same-scope fact changed, give the replacement a new `id` and
  mark the old case `superseded` with `superseded_by` pointing to it. Then
  reconcile any `context.md` text that still presents the prior conclusion. A
  different scope coexists.
- **Reuse the established vocabulary.** Scopes use exact case-sensitive slugs
  (`project`, `surface`); do not silently rename one, which would break recall.
- **Retire**: set `status: retired` and keep the record (and any
  counterexamples). Retirement is not permanent deletion. When the user
  explicitly asks to forget or delete a case, carry that out as an authorized
  edit that also reconciles the affected `context.md` and any in-store
  `superseded_by` references, so no dangling links remain within the authorized
  scope. Deletion is not a promise to erase unrelated archives.
- Preserve the minimum evidence needed; a pointer is often enough. Never invent
  an exact quote from a summary.

## Query: read and apply

```bash
python3 scripts/fc_memory.py query \
  --root "<authorized-root>" --project lumen-notes --surface editor \
  --term "inline help" --term 提示 --limit 5
```

- `--project` and `--surface` are required. Passing `*` selects only the global
  value on that axis; it does not widen to every project or surface.
- `--term` is optional and repeatable. Omit it for a bounded `scope_only`
  listing of the current scope. Terms are short keywords, not natural language:
  they are stripped, blank terms are a usage error, and duplicates are
  collapsed by casefold (`FOCUS` and `focus` count once). Matching is casefolded
  substring over `title`, `keywords`, `statement`, and `next_action` only (not
  `limits`). Multiple terms are ORed and ranked by the number of distinct terms
  hit, with stable ties by `id`. `matched_terms` echoes the canonical terms
  that matched. This is **not** a semantic rank.
- `--limit` default is **8**. The response reports `matched` (all eligible),
  `returned`, and `truncated`, so a bounded answer is never mistaken for the
  whole store. `context.md` is always returned whole regardless of the limit.
- Output fields: `status` (`matched` | `no_match` | `store_missing`), `mode`
  (`lexical` | `scope_only`), `context` (complete text plus
  `available`/`state`), `case_store` (`available` | `missing` | `invalid`),
  `requested_scope`, `terms`, `matched`/`returned`/`truncated`, and the full
  candidate records with `matched_terms`.
- A `no_match` result means only "no recorded case matched". Never report it as
  the user having no preference.
- Bad JSON, invalid UTF-8, or an invalid record is a clear error with a
  non-zero exit; it is never silently skipped into a success. A missing file
  and a zero match carry different fields.
- Cases outside the requested scope are not returned, and are never described
  as a partial result.

Cost model: each query loads and validates the whole `cases.json` catalog into
memory, then filters it. Bounded results and the `--limit` cap mean the *response*
is bounded, not that lookup is indexed or constant-cost; a larger store means
more work per query. Large production-store latency has not been measured.

Then **apply with judgment**: check each case against the current task and its
`scope`, `basis`, `limits`, and `outcome`. A similar case is candidate evidence,
not instruction authority; it never overrides the live request or the project's
accepted design. Current explicit direction wins over an older inference.

Show any case, including superseded and retired ones, by id:

```bash
python3 scripts/fc_memory.py show --root "<authorized-root>" --id fc-inline-help-2026-09-21
```

Validate the store (context presence plus case schema and supersession links):

```bash
python3 scripts/fc_memory.py validate --root "<authorized-root>"
```

Exit codes (matching the helper's actual behavior):

| Code | Meaning |
| --- | --- |
| 0 | Success: query valid match, `no_match`, or `store_missing` |
| 2 | Usage error (e.g. blank `--term`, non-positive `--limit`) |
| 3 | `show` requested an unknown id (`not_found`) |
| 4 | A required root/file is absent (`missing`) |
| 5 | Invalid input: bad JSON, invalid UTF-8, or schema/version/supersession error |

## Growth and the lexical ceiling

The ledger will grow, so the baseline needs to stay correct and bounded rather
than permanently small:

- Selection is exact-scope, `active`-only, literal-keyword, and capped by
  `--limit`. Eligible results, ordering, and truncation counts stay correct and
  deterministic as the store grows.
- The ceiling is real: matching is lexical. A paraphrased or cross-language
  query with no shared keyword returns `no_match` even when a relevant case
  exists. That is honest, not a preference claim; `context.md` is still
  returned.

Semantic retrieval now ships as an optional Cloudflare layer (Workers AI
embeddings + Vectorize). It is for the paraphrased/cross-language misses the
lexical path cannot reach. It is opt-in and additive: `--term` stays lexical and
offline, and the local records remain the only source of truth. See
[Cloudflare memory](cloudflare-memory.md) for setup, sync, and the semantic
query. The gate below is still the reason the semantic path exists, and still
governs whether to extend it further:

1. Collect real query-to-id pairs — the query a user actually asked and the
   case id that should have matched.
2. Measure the lexical baseline first, so the semantic layer has a comparison.
3. Keep scope/status filtering and canonical-record resolution ahead of any
   scored candidate (the shipped path already does this).
4. Any derived index must be rebuilt or invalidated on every edit, replacement,
   retirement, or deletion, and re-verify the same contracts (scope
   correctness, `active`-only recall, honest `no_match`, whole context).

Do not add a second index field or local cache before it serves a real
implementation.

## Boundaries and limits

- The helper uses the given root and does not infer, extract, or promote
  preferences. It does not touch project `DESIGN.md` or install anything into
  a global skill. `init` creates absent files; sync maintains derived state.
- Lexical queries, show, validate, and init are offline. Configured semantic
  queries, doctor, sync application, and pending verification contact
  Cloudflare; see its runbook for the exact data boundary. There is no daemon,
  background collection, or guarantee of automatic execution: the method works
  when the skill is loaded and the agent applies it.
