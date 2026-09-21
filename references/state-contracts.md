# State and persistence contracts

Use when a UI promise crosses a state boundary: a draft, an in-flight request,
a saved fact, a reopened view, a sync path, or a migration. This reference
traces an action through those layers and repairs the evidenced cause inside
the current task. It deepens the ownership model in
[app interaction](app-interaction.md); that table stays canonical, and this
file does not restate it. General debugging, Git, and delegation remain with
the host/repository method.

## Write the promise as a chain

For one consequential action, name each link in observable terms. Keep it to
the path under work; a repair does not need a whole-app contract.

```text
Cancel path (no write expected)
Action: drag the crop width, then Cancel
Draft: window width changed in the editor only
Commit rule: nothing is saved; Cancel restores the start
Saved fact: reopening later still shows the original width
Reopened view: the width control reads the original value, not the draft

Save path (write expected)
Action: Apply
Request: one update carrying the edited crop
Saved fact: reopening later shows the new width
Reopened view: the width control reads the saved value, not a default
```

This synthetic example assumes explicit Apply and discard-on-Cancel editing.
Use the product's actual commitment and draft-retention rules for other flows.
Identify the source of truth at each step.
Write the chain from the current code's actual route, then compare it with the
promise the interface makes. A cancel path that issues a write, or a save path
that never reaches storage, is the defect these two chains expose. A green
request does not prove the reopened view; a correct control reading does not
prove anything was saved.

## Trace the producer and consumer path

Follow the value in the current implementation instead of assuming a layer from
its name:

- find where the value is produced (input handler, draft reducer, form state,
  optimistic update, server response) and where it is consumed (render, save
  payload, export, cache read, reopen loader);
- note the serialization boundary and the unit/type at each side; a mismatch
  often appears as a default or `0`, not as an error;
- date/time, number, boolean, missing field, empty collection, and localized
  text all cross that boundary differently;
- check the read path separately from the write path. "Sent", "stored", and
  "reloaded" are different claims;
- use [platform evidence](platform-evidence.md) when the boundary is a native
  store, a shell bridge, or an export rather than the page itself.

## Keep, clear, and distinguish absent values

A field that is absent, `null`, empty, `false`, or `0` can carry several
different product facts. The contract in this product decides which of these
are actually distinct; do not impose one storage schema where the domain does
not distinguish:

- **Missing, unknown, and not applicable.** These may be one fact or several.
  Where the contract treats them as distinct — a value never provided, a value
  the person does not know, and a value that does not apply to this record —
  keep them distinct and show the matching state. Where it does not (for
  example, a plain required field that is merely blank), do not invent extra
  states. Do not send a fabricated `0`, `false`, `[]`, or empty string that
  asserts something the person never said.
- **Explicit zero or none.** A real chosen value that only needs separate
  treatment if the product's semantics say so; it must round-trip wherever a
  quantity is genuinely settable. An unset quantity must not render as a
  plausible number.
- **Explicit clear.** An intentional removal, only when the domain has one.
  Decide whether it deletes the record, blanks the field, or records
  "cleared", and make the reopen view show which one happened.

Choose per-field behavior from the value's semantic type and required
precision, not from a shared form default. Whatever the contract distinguishes,
verify that round trip: save, reload, and confirm a truthful display.

Trace the actual serializer and receiver for each intended operation. If the
server treats `null` as “keep”, sending `null` cannot implement “clear”, even
when the input becomes blank and the response succeeds. One valid partial
update contract is omitted = keep, explicit `null` = clear, `0` = recorded zero;
it is an example, not a universal wire format. Under that contract, changing
`{minutes: 30, note: "Keep this"}` with `{minutes: null}` must reopen as
`{minutes: null, note: "Keep this"}`. Exercise a previously populated value;
testing an already-empty field cannot expose a clear operation that does nothing.

## Single-field edits against whole-record writes

Whole-record updates lose untouched values when a read-modify-write step drops
fields, a partial form posts its own defaults, or a stale copy overwrites a
newer commit. Make the write preserve what the person did not change:

- keep the untouched values from the loaded record in the payload, or use a
  patch/merge that the server actually honors;
- check the optimistic or draft merge, not only the request body, so the local
  case does not diverge from the saved one;
- confirm the response that replaces local state still contains every field,
  including ones this action never touched;
- when the update touches an ordered list or collection, check the operations it
  actually supports; a merge that passes a single-field test can still
  duplicate or drop an item;
- when concurrent edits are actually possible, keep the current record and flag
  the conflict rather than silently clobbering it.

Apply these to the shape of the update under work. A single scalar field does
not require list-merge or conflict machinery that the product does not have.

## Failure, retry, and mixed outcomes

Feedback must say what is true about the stored state, not just about the call:

- an acknowledged save and an unconfirmed one must look different; do not show
  "saved" while a request is pending or after it failed;
- on failure, keep the person's work and offer a retry at the same scope, rather
  than discarding the draft or leaving an edit that looks committed;
- when a batch partly succeeds, report which parts saved and which did not;
  "Saved" over a partial failure is worse than an honest partial result;
- a retry must be idempotent enough not to create duplicates, double counts, or
  a second record on success;
- when the product already supports offline, timeout, or reconnect, those paths
  resolve to one of these states rather than a spinner that never settles.

## Correct the evidenced cause

Find the current pass that actually fails, then change the cause and verify the
original symptom. A bug in the running product is a defect to repair, not
frozen behavior to preserve. Useful order:

- fix the owner layer where the value is corrupted, not the display that
  reveals it; a formatting patch over a lost field hides the loss;
- separate behavior-preserving refactoring from a product or contract change.
  Refactoring around a boundary is ordinary engineering authority; changing
  what a field means, what the API returns, or who owns the data is a product
  decision that needs the caller's actual authority;
- a file, module, or layer boundary is not by itself an approval gate. Correct
  an evidenced root cause inside the requested task's scope even when it lives
  in another file of that scope;
- leave unrelated behavior, data, and other people's edits alone; do not
  generalize the fix past the observed failure.

## Work inside the authority already granted

Check the caller's existing authority before treating a boundary as a gate. A
file, module, or layer boundary is not an approval requirement, and covered
work — refactoring, correcting an evidenced defect, ordinary writes in the
environment the task already authorizes — does not need re-approval. Do not ask
again for scope that was already granted.

Ask only when the action actually needs what is missing: unclear product
meaning, or an external, destructive, or irreversible consequence the current
authorization does not cover — a real data migration that changes stored
meaning, an external-system write, or provisioning. Present the proposed
change, the affected records and their current meaning, the reversible path,
and the verification that would prove it, then proceed within the authority
that exists. A passing local test does not itself extend authorization to
external provisioning or private-data transfer.

## Verify across the boundary

Use representative records, not one happy value, and check each stage rather
than a single success signal. Match the checks to the semantics this change
actually touches or that the observed failure implicates:

- reload the exact route and confirm the reopened view shows the saved fact;
- exercise the value distinctions this field's contract defines, such as an
  explicit zero or none, an explicit clear, or a value that was never set;
- edit the touched value and confirm untouched values survive; for a
  list-shaped change, confirm nothing was dropped or duplicated;
- when the change alters failure or retry behavior, force a failure and a retry
  and confirm feedback and stored state agree;
- when a migration or schema change is in scope, verify old records still load,
  or state clearly which records the change does not cover.

Rendered checks belong to [QA](qa-contract.md); artifact outputs belong to
[visual works](visual-works.md). Report source, saved-state evidence, reopened
evidence, and any migration or external write separately, and name honestly
what was tested synthetically, what used real records, and what the owner has
accepted.
