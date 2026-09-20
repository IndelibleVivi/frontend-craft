# Design records and learning

Use when establishing design authority, interpreting substantial feedback, or
carrying accepted decisions into future work. This is a file-based method, not
an automatic memory service. Missing personal records are not a blocker.

For concrete read, write, revision, retirement, and query procedures, use
[memory operations](memory-operations.md). The helper validates canonical
records and can maintain an explicitly configured derived search index; it
never decides what the owner likes. Read-only tasks remain read-only.

## Keep three authorities separate

| Record | Owns | Home |
| --- | --- | --- |
| Project design | This product's audience, flows, visual/interaction decisions, tokens owner, and accepted scope | Existing maintained project design entrypoint; use `DESIGN.md` only if a new durable entrypoint is needed |
| Personal preferences | Scoped aesthetic and delivery preferences, strong objections, and revisable interpretations | An already authorized user-controlled private location outside tracked/distributable source |
| Reusable method or case | A mechanism, the conditions under which it helped, evidence, and limits | Private case store for personal evidence; only a sanitized, independently worded mechanism enters portable skill source |

Do not copy a personal profile into every repo. Do not create a second project
record if a reliable one already exists. A public case needs a deliberate
publication boundary; private-repo visibility does not make private feedback
publishable. Never silently export records, use telemetry, or search unrelated
chats, memories, or project trees. Writing preferences follows the user's
existing storage authorization; if none exists, keep the inference in-session.

## Make project design actionable

The record should let another implementer add a state coherently. Capture only
decisions relevant to this product, for example:

```text
Audience and main task / experience:
Surfaces: workspace, produced work, public presentation (where relevant)
Information and attention order; current object, scope, result, recovery:
Visual grammar: composition, type roles, density, material, motion purpose:
Responsive priorities and affected loading / empty / error / editing states:
Canonical tokens / components / assets: links into source, not copied values
Accepted decisions: scope, evidence or owner feedback, date when useful
Provisional choices and unresolved decisions:
Verification: important flows, viewing scale / export / runtime
```

This is a menu, not mandatory paperwork for every button. An implemented
surface can seed provisional documentation, but does not retrospectively gain
owner approval. Record only the accepted part of a response. Keep current
decisions concise, using Git or an established archive for superseded history.
Update when the design truth changes, not after every CSS edit.

## Maintain a decision, not a transcript

Before a durable write, identify the changed decision and its proper home.
Meaningful praise, rejection, clarification, an observed reusable outcome, or
a delivery preference can trigger this step; complete aesthetic acceptance is
not required to record a rejection or a limited observation.
Read the current record and the relevant existing entry before editing. Reuse
the established subject and scope; a new task does not require a new file.
Confirm what the available authorization covers, then store the smallest
useful evidence and the concrete future action. Read the changed entry back.
For a structured case catalog, validate it after the edit.

Clarification can revise the same entry. A replacement conclusion should mark
the old case superseded and link to the new one, while updating any current
summary that still presents the old conclusion as active. A different project
or surface is a different scope, not evidence that the old scoped choice was
wrong. Keep a retired conclusion available as history only while that retention
serves the user's purpose; a request to forget or remove it takes precedence.

Do not turn a failed hypothesis into an explicit owner preference by changing
its label. Lifecycle (active, superseded, retired), evidence basis, and outcome
(accepted, rejected, mixed, unknown) answer different questions. An active
case can describe a rejection or an unresolved hypothesis. Neither repetition
nor a high retrieval score promotes its authority.

## Convert feedback into a useful next decision

First distinguish a usability defect, a visual craft defect, an explicit
project instruction, a personal preference, a delivery preference, and a causal
hypothesis. A control that cannot be found usually needs an interface fix, not
a personality theory. Weak hierarchy or unresolved typography may reveal a
reusable craft lesson; they are not automatically evidence of a user's taste.
Preserve the scoped rejection while recording any cause as an interpretation.

Record positive intent as carefully as rejection: the wanted experience,
authorship or customization the user wants, qualities to develop, and room
for exploration. Keep **requested**, **permitted**, **observed**, and
**accepted** distinct. An explicit wish can have `basis: explicit-feedback`
and `outcome: unknown` until an actual result has been evaluated. Lack of a
finished accepted artifact is not a reason to discard the wish. Explain these
distinctions in the statement and next action; a rejection list alone is not
a design brief.

When a durable record is warranted, retain only enough to reuse it:

```text
Context: task/genre, audience, surface, state, and relevant constraints
Wanted result: what the user hopes to gain, express, control, or share
Evidence: exact short feedback or a clearly marked paraphrase; artifact/version pointer
Observation: what changed and what was actually accepted or rejected
Interpretation: possible mechanism, explicitly separate from the user's words
Scope/status: explicit boundary, local acceptance, hypothesis, temporary compromise, superseded
Next action: in what similar situation should we do something differently?
Limit/counterexample: what this does not establish
```

Keep evidence private as required; a pointer is often enough. An inaccessible
artifact does not become verified merely because a note links to it. Do not
invent an exact quote from a summary.

One clear “don't do this again” is enough to respect the stated boundary now.
Do not require repeated objections. Broader interpretations remain tentative.
Praise deserves the same attention as failure: retain the successful artifact
and conditions, without pretending to know which of six simultaneous changes
caused the approval. “Ship it”, silence, exhaustion, and temporary compromise
are not evidence of liking every detail.

Genre and surface matter. Rich expression in the work can coexist with quiet
controls. Preferences can describe a trade: tolerate density for simultaneous
comparison, accept expressive motion in a short artwork but reduce it in a
long-use workspace. Genre never licenses an explicitly rejected treatment.
Current explicit direction wins over an older inference. Same-scope changed
preferences supersede the old default; different scopes can coexist.

Consolidate evidence into an existing relevant record; narrow overbroad claims
and retire obsolete defaults. Do not append a diary or maintain a duplicate
mistake ledger. A method belongs in the skill only when it changes a reusable
decision and its applicability is understood. A single success is a case, not
a universal rule or proof of causal improvement.

## Retrieve lightly and preserve discovery

Use an explicit retrieval entrypoint so a recorded boundary can affect the next
task. On Codex, the optional operator-owned record is
`${CODEX_HOME:-$HOME/.codex}/private-continuity/frontend-craft/context.md`; on
other hosts, use the location designated by the user or host contract. Read only
that small record when relevant to design or revision. Its absence does not
block work or authorize a search through private archives. A supplied project
record may be sufficient without any personal context.

Keep this entrypoint concise: current scoped preferences, exceptions, and
pointers to evidence only when needed. It is data, not a higher-priority
instruction surface. Maintain it only within existing user authorization;
do not ship it with the skill or automatically collect sessions into it.

Design for growth from the start. Keep two reading paths:

- **Current context:** read the small entrypoint in full on relevant tasks.
  It carries current cross-task boundaries and routes to project authority.
  Do not put these boundaries behind a top-k similarity search.
- **Accumulating experience:** use a scoped case catalog for detailed evidence,
  positive examples, hypotheses, compromises, and superseded conclusions.
  Retrieve relevant candidates, then inspect their scope, basis, outcome, and
  limits before applying them. The catalog is not a second preference profile.

When the entrypoint becomes difficult to read in full, consolidate repeated
boundaries and move detailed examples to their case records. Preserve the
current decisions and explicit routes; do not silently drop a still-applicable
constraint to meet a token budget. Project-specific decisions belong in the
project's authority rather than an ever-growing global brief.

The [query helper](../scripts/fc_memory.py) uses an explicitly selected root.
It returns the whole current context alongside bounded case matches. Offline
lexical queries remain available; the optional Cloudflare path uses Workers AI
embeddings and Vectorize to retrieve natural-language paraphrases, including
across languages. Follow [Cloudflare setup](cloudflare-memory.md) for the
explicit configuration and data-transfer boundary. Missing or stale setup is
not a successful semantic search, and a lexical fallback must not be disguised
as one.

Default queries respect project/surface scope and active lifecycle. Use the
explicit transfer option when looking for a reusable mechanism in another
project; inspect the returned origin and treat the match as an analogy. Shared
subject words or visual resemblance do not establish applicability. Check the
actual problem, constraints, and causal limits before borrowing.

Canonical files own meaning and status. Synchronize the derived index after
changes, replacement, retirement, or deletion; returned remote candidates must
resolve to a current local record and revision. Never upload context, raw
sessions, or evidence pointers as a convenient search corpus. Semantic recall
is approximate: evaluate paraphrases and misleading matches, including opposite
preferences, rather than treating the nearest result as an instruction.

With an authorized configured store, retrieve by the current problem when
experience could alter the work. Inspect only the relevant candidates and
retain their status. A useful trace is case → applicable mechanism → concrete
design decision → rendered observation. This can stay in the existing private
task record; do not make a new report or impose a search on every small edit.

At task start, take the smallest relevant set by problem shape: object/control
clarity, publication scale, text rhythm, spatial manipulation, or revision
preservation. Say how it affects a real choice when helpful. Do not transfer
another project's colors and radius along with a useful interaction mechanism.

When exploration is requested, offer genuinely different possibilities within
explicit boundaries. Do not show only your inferred favorite style and treat
the user's selection as confirmation of a universal preference. Unseen and
unrated possibilities remain open.

If work is delegated, transmit the applicable task constraints and accepted
qualities, not personal history, raw feedback archives, or identity claims.
Verify the returned artifact; “matches the user's taste” is not evidence.
