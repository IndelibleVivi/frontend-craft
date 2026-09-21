# Reopen meaningful interface states

Use when a state is difficult to reconstruct, when a feature will be revised
across sessions, or when a regression needs a repeatable path. A one-control
repair may need only an existing test or a short reproduction. This method
adds reusable evidence to the product's own tooling; it is not a new test
platform and does not require Storybook, a screenshot runner, or a fixed suite.

## Select the state that can disprove the result

Choose the user task and the affected condition together: reopening a long
record, cancelling a partial edit, saving after a recoverable failure, or
returning from a filtered library. Keep ordinary content as well as the input
that exposes the failure. Do not accumulate a universal edge-case gallery.

Use the project's existing story, component test, browser test, development
route, or fixture mechanism. If none is needed, a reproducible recipe next to
the relevant test/runbook is sufficient. A screenshot without its state and
entry path is an observation, not a replayable scenario.

```text
Purpose: amend one value while preserving the rest of a record
Entry: exact local route/build and the normal path to the record
Input: synthetic fixture or authorized test data; relevant clock/seed if needed
Setup: project's test-store reset/seed command, scoped to disposable data
Action: open the value, type, cancel; reopen, type, save; reopen again
Observe: displayed values, draft/committed state, request result, focus/feedback
Compare: same content, viewport, fonts and relevant renderer conditions
Evidence: test/run command and output; before/after captures when useful
Limits: local fixture behavior; no live service or owner acceptance claim
```

Adapt this recipe to the real task; do not create empty fields as paperwork.
Prefer synthetic fixtures over private production exports. A setup command
must target a known disposable store, never an ambiguous current database.
Synthetic content alone does not make the active working store disposable:
it may contain the edits a later revision must preserve. Give a resettable
test its own store/copy, or explicitly retain and restore the task-owned
fixture. A replay must not silently replace ongoing work with its seed.

## Exercise the canonical path

Enter through real controls for interaction claims. Fixture setup can prepare
content or a supported failure, but directly assigning application state does
not prove users can reach it. If a component story bypasses routing, persistence,
or an API, keep that limit explicit and check the relevant integrated path too.
For a persistence claim, a mock that reimplements the receiver proves only
the mock's contract. Exercise the actual serializer and receiver together.
Inspect the selected replay mode: a command that exits successfully after
skipping the browser or API checks is not a passing integrated run.

For a save defect, assert both the visible result and the retained facts. For
a cancellation defect, compare before editing with after reopening. For an
asynchronous issue, control the relevant response order or failure through the
existing test seam. Do not introduce a fake production success or unnecessary
provider dependency to make the test easier.

When a visual experiment lives in browser overrides or a temporary study,
apply the chosen change to its source owner, reopen the normal route without
the override, and repeat the relevant observation. Keep the experimental result
distinct until that replay succeeds.

## Compare in conditions that explain change

Hold browser/OS, fonts, viewport, data, and relevant motion/seed stable when
using pixel comparisons. Use a baseline only when its role is known: captured
prior behavior, an accepted reference, or an unaccepted candidate. Updating a
snapshot does not approve the design. Explain intentional differences and
inspect important regressions rather than regenerating all baselines to green.

Combine the checks in a useful render pass: inspect layout, active controls,
task feedback, and the promised quality in that state. Use geometry and stored
data where a screenshot cannot answer the question. [QA](qa-contract.md) owns
the detailed checks; this method owns getting back to the same meaningful state.

## Keep the scenario useful through evolution

When the product changes, update the setup and expectations that changed by
contract, retaining regression evidence for the promises that remain. Link the
scenario from the existing project design or test entrypoint when later work
needs it. Store distributable synthetic fixtures/tests with the project when
appropriate; keep temporary captures, private data, and evaluation traces
outside the distributable skill.

Record what actually ran and what remains untested. A replay can show preserved
data, reachable controls, or a restored visual relationship; it cannot prove a
first-time user's comprehension or aesthetic acceptance. A single successful
run is not a measured improvement in FC's overall quality.
