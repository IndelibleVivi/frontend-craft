# Frontend QA Contract

Read this reference when preparing or executing rendered QA, investigating a
frontend defect, or finalizing a user-visible frontend change. Scale the checks
to the actual blast radius; do not turn a one-control fix into a whole-product
audit.

This file supplies the detailed Web checks. For native UI, canvas internals,
installed shells, or exported works, also select the appropriate evidence in
[platform evidence](platform-evidence.md). Do not relabel browser proof as
device proof.

## Define the target

Write down the target flow before testing:

```text
[exact route and runtime] -> [user action or state] -> [expected visible result]
```

Confirm that the browser is serving the intended checkout/build. Record the
actual URL, port/host, relevant data or fixture, and viewport. A running process
or HTTP 200 does not prove the intended page, assets, or code are active.

## Choose evidence-bearing viewports

Start with the viewport the user or product actually prioritizes, then add one
materially different layout. When no stronger contract exists, useful defaults
are:

- desktop: about `1440 x 900`;
- mobile: `390 x 844`.

Add tablet, small laptop, wide desktop, installed PWA, or another browser only
when the changed layout, product contract, or observed defect makes it useful.
Do not run a ritual viewport matrix whose result cannot change the decision.

## Baseline browser checks

For the exact target:

- URL, title, route, and primary content identify the intended page.
- The app is not blank and shows no framework/build error overlay.
- Relevant assets load from their real served URLs, not an HTML fallback.
- Console and network evidence contain no relevant unexplained errors.
- Loading, empty, error, dense/long-content, and success states touched by the
  change remain honest and readable.
- The primary workflow reaches its expected visible state through real
  controls, not direct DOM manipulation or a screenshot.

## Layout and responsive checks

Inspect the first meaningful viewport before scrolling, then the full touched
surface.

- No clipped primary content, accidental overlap, hidden controls, broken
  sticky layers, scroll traps, or unintended horizontal page scroll.
- Long words, paths, tokens, translated text, and user content wrap or truncate
  according to the product contract.
- Grids, tables, forms, sidebars, drawers, dialogs, media, and navigation retain
  usable geometry at both viewports.
- Touch targets and controls remain reachable without decoration covering them.
- Images preserve intended crop, aspect ratio, resolution, and contrast.
- Layout shifts do not move the active control or obscure feedback.

Pair screenshots with DOM/layout evidence when a compositor, device-pixel
ratio, font load, or capture crop could mislead. Useful geometry includes
`scrollWidth`, `clientWidth`, bounding boxes, computed overflow, and visibility.

## Interaction and state checks

Exercise the exact changed flow plus the nearest regression-prone transition:

- click/tap and keyboard activation;
- hover, focus-visible, active, selected, disabled, and pending state where
  relevant;
- open/close, submit/cancel, validation, retry, navigation, or state persistence;
- one realistic long/dense value when content geometry can change;
- reduced-motion behavior when motion was added or changed.

Verify the resulting visible state, URL, focus target, data/state change, or
feedback. A successful click command without a checked result is not
interaction proof.

For stateful App work, apply the relevant boundaries from
[app interaction](app-interaction.md): inspection versus mutation, draft versus
commit, gesture completion/cancel, meaningful undo, and reopen/save state. Check
the state as well as its appearance. Exercise native text composition when it
is part of the changed contract; a synthetic fill does not establish IME behavior.

After navigation or a render that replaces nodes, refresh the DOM snapshot or
reacquire locators before asserting the next state. A stale automation handle is
test-harness evidence, not a product defect.

## Task comprehension

For a changed workflow or information hierarchy, choose a realistic goal
without encoding the click path: for example, “move the photo left while
keeping its crop window fixed.” Inspect the cues that let a person identify:

- their location and the object currently affected;
- the available action and its scope;
- pending work and the result of the action;
- how to exit, cancel, correct, or recover when the task requires it.

Trace where each clue is visible before the action is taken. Hiding controls
can make a screen quieter while making the task harder to discover. Check
whether emphasis, grouping, wording, depth, and feedback match the user's job.
Color or motion alone must not carry essential meaning.

Judge those cues at the actual scroll/window position where the task occurs,
not merely somewhere on the page. When a workflow alternates between a work
and its controls, inspect the travel required and whether object/scope context
survives. A responsive stack can pass overflow checks while making repeated
editing cumbersome.

Label an agent's inspection a cognitive walkthrough, not a user study. A
maintainer who knows the implementation cannot stand in for a first-time user.
Owner aesthetic approval, scripted task success, and observed comprehension
are separate observations. Real user testing is required only when the task
calls for it; report the evidence actually available.

## Positive quality and revision preservation

Name the quality promised by this task and observe it in the actual medium:
clear comparison in a dense tool, sustained reading rhythm, a distinctive
composition, convincing material, or an expressive temporal sequence. Explain
what in the render supports the judgment; avoid ungrounded “premium” scores.

For an explicit reference or aesthetic goal, use the goal loop in
[design direction](design-direction.md). Compare the intended relationships,
not only the presence of recognizable colors or motifs. Keep the original
target visible when choosing the next implementation change.

Keep functional correctness, task usability, and visual quality as separate
results. Passing many interaction/layout checks does not increase the evidence
for taste. An agent-authored brief, simulated praise, or preservation of a
baseline cannot establish owner acceptance. When actual owner feedback rejects
the visual result, update its current case status; retain technical evidence
without continuing to present the artifact as an aesthetic success.

After feedback-driven edits, recheck the original defect and the accepted
qualities exposed to regression. Compare with equivalent content, dimensions,
fonts, state, and environment; align procedural inputs and meaningful animation
phases where possible. A pixel diff detects change, not aesthetic merit.

For visual works, follow [visual works](visual-works.md): inspect real exports
and viewing scale, and observe motion across time rather than selecting one
flattering frame. Do not replace the artwork's purpose with control QA alone.

## Accessibility checks

Keep the pass proportional, but always inspect the semantics touched by the
change:

- interactive elements use the correct native role or an equivalent complete
  keyboard contract;
- controls have accessible names and form fields retain labels, instructions,
  and errors;
- focus is visible and follows a sensible order;
- dialogs, menus, popovers, drawers, and overlays handle focus entry/return,
  Escape, outside interaction, and stacking as their contract requires;
- when an overlay action re-renders or replaces its trigger, closing the
  overlay still returns focus to the live replacement control;
- color is not the only carrier of state, and text/controls remain legible;
- live updates announce themselves when users otherwise cannot perceive them.

Design and inspect the active states as part of the visual system: text editing,
object selection, validation, hover, and keyboard focus. A clean unfocused
screenshot can conceal a visually disruptive working state. Focus visibility
does not prescribe a dark, thick outer ring. Choose a clearly perceivable
indicator that fits the component and its surroundings, keeping keyboard
location distinguishable from selection or error. Do not solve a disliked
indicator by removing focus visibility. On Web, `:focus-visible` follows browser
heuristics; text inputs may match after a pointer click too. Inspect actual
pointer and keyboard behavior rather than equating the selector with
"keyboard only". Relevant primary sources are recorded in [lineage](lineage.md).

For changed motion, test reduced-motion behavior and preserve clear state
feedback. Distinguish interaction-triggered motion from automatic animation;
the applicable controls differ. This focused check is not a claim of complete
WCAG conformance. See the primary-source notes in [lineage](lineage.md) when
changing the accessibility contract.

Use automated accessibility tooling when it is already available or the blast
radius warrants it, then inspect the affected interaction manually. A clean
scanner does not prove usability.

## Visual authority and fidelity

When an accepted design or total visual reference exists, compare at equivalent
dimensions and use this order:

1. page/container width, gutters, section heights, and major regions;
2. content hierarchy, density, and text wrapping;
3. asset bounds, crop, layering, and interaction clearance;
4. typography, color, border, radius, shadow, and icon treatment;
5. motion and micro-detail.

Keep a short mismatch ledger while fixing: reference evidence, rendered
evidence, repair, or a concrete intentional deviation. Do not reinterpret an
accepted reference to satisfy generic taste rules.

For net-new design, judge the render against the brief rather than an invented
concept image: subject, audience, primary job, information hierarchy, visual
direction, signature idea, real content, and responsive priority.

For authoring products, inspect both the workspace and the work at its intended
reading size. When comparing visual languages, hold content and palette steady
so the graphic differences can be judged. When comparing palettes, verify that
the color control does not also change structure or typography. Exercise
interface and work languages independently when both are supported.

## Framework and performance routing

Run project checks that exist and cover the change: typecheck, lint, unit/
component tests, build, and configured end-to-end tests. Do not install a new
browser or test stack merely to make the report longer.

Investigate performance when it is part of the task, a meaningful regression is
observed, or a substantial new surface changes data loading/rendering. Route to
the current framework-specific guidance and inspect the relevant high-impact
category first: request waterfalls, bundle/load cost, server/client boundary,
rerender churn, or expensive rendering. Do not preload a complete framework
rulebook for unrelated CSS or content work.

## Evidence and handoff

Store temporary screenshots, traces, and scripts outside the repo unless the
user asked for committed artifacts. Before handoff, state:

- target flow, runtime, and viewport(s);
- checks run and their fresh results;
- interaction and visible-state evidence;
- remaining untested flows or intentional deviations;
- whether the claim is source-complete, build-verified, browser-verified,
  deployed/activated, or owner/device accepted.

Never collapse those claim levels into a single "done".
