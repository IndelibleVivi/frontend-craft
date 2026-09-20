# Critique and revision

Use when an interface feels wrong, when inspecting design quality, or when
responding to visual/interaction feedback. Review-only remains read-only.
Precise bounded instructions do not need psychological interpretation.

## Observe before prescribing

Inspect the exact runtime, content, viewport, state, and region under discussion.
If the user reports no change, first verify the checkout/build/cache or installed
client they actually see. Do not compensate for stale runtime by increasing a
CSS adjustment.

Separate observation, cause hypothesis, and intended result. A useful revision
contract can be one sentence: “Regroup the competing inspector actions so the
selected object and its main operation read clearly; preserve the accepted
canvas composition and color.” It is a working judgment, not an approval form.

| Feedback | Discriminate using the current render | Possible cause-level move |
| --- | --- | --- |
| “Too empty” | Missing meaningful content, excessive container width, loose rhythm, or no focal anchor? | Restore missing content, rebalance region proportions, constrain line length, or strengthen the subject. |
| “Too busy” | Too many simultaneous groups, equal emphasis, irrelevant state, or decoration competing with controls? | Reorganize hierarchy, put state near its object, or reveal contextually; retain discoverable actions. |
| “Feels like a demo” | Fake data, generic copy, repeated identical cards, missing real workflow, or weak composition? | Make the real task and content primary; complete stateful behavior or give the content a deliberate structure. |
| “I don't know what I'm changing” | Is the selected object, editing scope, or result unclear? | Distinguish object and mode, connect control to result, provide exit/recovery cues. |
| “Still not right” | Same defect, mistaken diagnosis, implementation not active, or a new request? | Reinspect evidence and select a different causal explanation before changing more values. |

These are diagnostic forks, not automatic translations. “Busy” does not always
mean desaturate; “empty” does not always mean add cards. If observed evidence
cannot distinguish two materially different intents, ask one concrete question
with the affected region or alternatives. Continue independent clear fixes.

If the whole visual direction is rejected, record that rejection at its actual
scope. A named disliked detail is additional evidence, not permission to reduce
the complaint to that detail. Revisit composition, type relationships, palette,
material, control treatment, and fit to purpose together before choosing the
next intervention. Preserve real functionality; do not preserve an unaccepted
visual direction merely because a test fixture or the agent previously praised
it. Meeting requested ingredients is not the same as executing them well.

## Protect what already works

Identify accepted qualities at the level the user accepted: the composition,
type rhythm, object behavior, palette, or workspace/work boundary. “I love the
type” does not approve navigation. Preserve those qualities and required
functionality while making the smallest complete causal change. Several
coordinated layout/state edits may be more appropriate than one small number.

An accepted quality is not a ban on every pixel moving. Check that its effect
survives at the relevant size/state. Do not silently flatten a vivid artwork
because the surrounding tool UI was criticized, or change content to avoid
solving its layout.

## Compare the original problem

Use comparable content, dimensions, font availability, state, and environment.
For procedural work, reuse the input/seed when available; for motion, compare
the meaningful phase as well as the sequence. Pixel differences show change,
not improvement. Explain the result in terms of the defect, not just the edit.

After correction, revisit the reported region and the nearest likely regression:
the main task, accepted composition, adjacent responsive state, focus return,
or export as applicable. Record an unresolved cause honestly. Do not claim
human comprehension from your own successful click sequence.

If the same complaint returns, reopen the diagnosis. Repeating a stronger dose
of the previous adjustment needs new evidence. Stop when the requested change
is demonstrated and preserved qualities still hold; do not keep polishing
unrelated areas. New user ideas are not automatically failed revisions.

Meaningful acceptance or rejection can update the project's design entrypoint
or scoped experience using [design learning](design-learning.md). A concrete
defect can justify a regression case; no wording-only test can prove taste.
