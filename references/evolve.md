# Evolve an existing product

Use when adding a capability, accommodating meaningful content growth,
reorganizing journeys, or replacing a visual/interaction system. A specific
defect uses diagnosis and a focused repair; a label or spacing change does not
need this whole method.

## Establish what this change should preserve and replace

Inspect the affected journeys, accepted design decisions, and current source.
Distinguish four facts: the requested new behavior, existing promises that
remain, observed defects to fix, and implementation details that can change.
An accepted reading rhythm can survive replacement of its old container;
preservation does not give every component permanent ownership of the screen.

Make a small impact map in the existing task record when the change spans
surfaces. Record only the relevant relationship:

```text
New capability -> affected entry/working/return surfaces -> state or contract
that changes -> qualities and existing user work to preserve -> revealing check
```

For example, adding collections to a library affects finding, assigning, and
returning to an item. The mapping reveals whether navigation, saved filters,
direct links, or an open edit actually depend on the old structure. Inspect
those dependencies; do not invent a migration for every conceivable user state.

## Reorganize the task before adding another region

Growth can make a working layout cease to serve the job. Observe actual content
volume and the new action's frequency, scope, and relationship to existing work.
Decide whether it belongs inline, in navigation, near an object, in a dedicated
view, or in an already appropriate group. Appending a card to the bottom is a
choice to justify, not the default integration strategy.

Retain simultaneously needed information and the user's current context.
Progressive disclosure helps only if the hidden work can still be found when
needed. Deliberate full editing may need all fields visible. A dense comparison
may need more information at once, not a quieter screenshot.

Judge coherence without forcing uniformity. A welcome sequence, a daily
workspace, and a produced artwork may share identity while using different
density, scale, and motion. Trace a token's consumers before changing it globally;
a local hierarchy problem may need a local role rather than a global reduction.

## Choose a coherent change boundary

For an additive feature, integrate the complete entry -> action -> result ->
return path, including the real states it exposes. For a redesign, account for
the affected interior surfaces as well as the front door. For a repair, trace
the actual failure before reorganizing unrelated areas. Use
[Build](build.md) for making and [state and contracts](state-contracts.md) when
the proposed experience reveals a model or persistence problem.

Existing architecture is a starting point, not a veto on required change.
Restructure when it removes evidenced resistance or enables the requested
experience. Avoid a parallel implementation that leaves old routes, event
handlers, state owners, or defaults active. Check callers and retire the
superseded path in the same scope. Keep a compatibility path only for an
identified consumer or actual rollout requirement, with a removal condition.

Use staged delivery when the change needs it, not to hide incomplete requested
work. Each stage should have a coherent usable path and an explicit relation
to the remaining scope. Source-complete, locally integrated, deployed, and
adopted are different states. A plan does not authorize migration, live writes,
release, or new external dependencies; apply the caller's existing boundaries
without imposing a separate FC approval process.

## Carry old work through the new experience

Use an actual authorized sample or synthetic equivalent of pre-change content
to exercise the affected return path. Can a person still open the relevant
work, recognize what changed, continue editing, and recover from the failure
this change can cause? Check saved filters, route state, draft handling, and
exports only where the touched implementation affects them.

When semantics change, settle what old data means before presenting it as a
new fact. Do not reinterpret “unknown” as “none” or silently rewrite historical
content to make the new interface look complete. A current product decision
may already resolve the meaning; inspect it before asking again.

## Prove continuity through change

Replay the relevant [interface scenarios](interface-scenarios.md), adding or
revising only the states this feature creates. Compare the preserved quality
with equivalent content and viewing conditions. The new feature must work;
the old primary task must still work; the visual relationships must remain
coherent. These are separate observations, not one accumulated pass count.

Update the project's authoritative design and user/operator documentation
when its current truth changes. Record an intentional replacement as such;
do not retain an obsolete screenshot or contract as if it were still normative.
Carry explicit feedback at its actual scope using
[design learning](design-learning.md). Stop once the requested evolution and
affected regressions are covered, without turning a small follow-up into
another global redesign.
