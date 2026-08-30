# Frontend QA Contract

Read this reference when preparing or executing rendered QA, investigating a
frontend defect, or finalizing a user-visible frontend change. Scale the checks
to the actual blast radius; do not turn a one-control fix into a whole-product
audit.

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

After navigation or a render that replaces nodes, refresh the DOM snapshot or
reacquire locators before asserting the next state. A stale automation handle is
test-harness evidence, not a product defect.

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
