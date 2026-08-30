---
name: frontend-craft
description: "Build, redesign, repair, or review real frontend interfaces from repository, product, design, reference, and runtime evidence. Use for frontend applications, pages, components, responsive UI, interaction work, or rendered browser QA. ImageGen is never a default step; generated imagery enters only when the user explicitly requests or approves it for a real deliverable asset."
---

# Frontend Craft

Build the interface the product actually needs, in the system that actually
owns it, and verify the result in the runtime a person will use.

This is a design-engineering skill. It covers greenfield UI, existing-product
work, reference-led implementation, redesign, targeted repair, and frontend
review. It does not turn every frontend task into a concept-art workflow.

## Core contract

- Start from current authority: the user's request, accepted product/design
  material, the canonical repo, supplied references and assets, and the exact
  rendered runtime.
- Preserve product meaning and behavior. Do not invent routes, metrics, copy,
  data, permissions, states, or interactions merely to make a screen look full.
- Deliver the complete requested surface. A hero, shell, static mock, scaffold,
  or collection of inert controls is not a finished app unless that is the
  explicit deliverable.
- Use the existing framework, package manager, component system, router, state
  model, styling conventions, and accessibility semantics unless the user has
  authorized a replacement.
- Treat source, build, rendered behavior, deployment, and owner acceptance as
  separate evidence layers.

## Image policy: opt in, never prerequisite

Do not call ImageGen to begin frontend work, establish taste, make a ritual
moodboard, or satisfy a workflow gate.

Prefer, in order, the assets and media that belong to the product:

1. supplied brand, product, content, screenshot, or reference assets;
2. existing repo assets and design tokens;
3. real content or licensed/public assets whose use is authorized;
4. code-native HTML/CSS, SVG, canvas, charts, diagrams, or procedural visuals.

ImageGen is an adjacent, opt-in asset route. Use it only when the user
explicitly asks for generated imagery, or after a concrete required raster-asset
gap is identified and the user explicitly approves generation for that asset.
Its output must enter the real deliverable and still pass the same provenance,
asset, layout, and browser checks. The absence of supplied imagery is not, by
itself, a reason to generate any.

## Resolve the work mode

Choose the mode from evidence before changing code.

### Existing product or targeted repair

The current product architecture and accepted visual system remain authority.
Inspect the affected route, components, data/state path, styles, and rendered
failure. Make the smallest coherent change that completes the requested
behavior; do not smuggle in a redesign.

### Reference-led implementation

The declared reference is visual authority for its stated scope; the current
app is behavior authority. Preserve real controls, data, routes, handlers,
semantics, and states while matching measured layout, typography, color,
assets, density, and responsive behavior.

When `$pixel-perfect-reference-ui` is installed and the user wants strict
replication from a total screenshot, mockup, Figma export, or reference-image
set, use it as the specialized method. Do not replace functional UI with a
screenshot or invent substitute visuals when the reference is exact.

### Net-new or visually unlocked design

Inspect product purpose, audience, content, workflows, data, constraints, and
platform before choosing visual language. Form one compact direction:

- subject and primary user job;
- information hierarchy and first meaningful action;
- layout/container model and responsive priority;
- typography and color character;
- one or two signature visual or interaction ideas that belong to the product.

Critique generic defaults before coding. Avoid automatic bento grids, card
stacks, pills, gradients, floating orbs, fake metrics, dashboard chrome, and
decorative labels unless the product or accepted direction calls for them.

If a genuinely open identity or product-direction choice would materially
change the result, present a small decision surface and stop only at that human
judgment boundary. Otherwise proceed in code; a generated concept is not
required.

### Review only

Inspect current source and rendered behavior. Report concrete findings with
file, route, state, viewport, reproduction, and impact. Do not mutate the repo
unless the user asked for fixes.

## Working method

### 1. Establish the real target

- Resolve the physical repo root, current Git state, and applicable
  instructions before edits.
- Identify the exact route, URL, port, host, or app shell the user sees.
- Map the owning components, styles, design tokens, assets, data/state path,
  interactions, and relevant loading/empty/error states.
- Inspect the current rendered surface when it exists. A stale dev server or a
  different localhost port is not evidence about the edited checkout.
- Name the behavior and design boundaries that must remain unchanged.

### 2. Shape the implementation

- Derive structure from product content and workflows, not from a fashionable
  template.
- Use a small coherent token and component system where repetition warrants
  it. Do not build an abstract design system before the surface needs one.
- Keep interactive UI code-native and semantic. Buttons, links, inputs,
  dialogs, tables, navigation, media controls, and state transitions must work.
- Implement required normal, hover, focus, active, disabled, loading, empty,
  error, and success states in proportion to the touched workflow.
- Prefer stable layout primitives such as grid, flex, `minmax()`, `clamp()`,
  container constraints, and deliberate overflow behavior over screenshot-tuned
  piles of magic numbers.
- Respect `prefers-reduced-motion`; motion should reveal hierarchy, continuity,
  or state rather than decorate every element.
- For a new repo with no stack decision, choose the smallest maintained stack
  that satisfies the product and delivery contract. Do not default to a
  framework merely because another skill preferred it.

Load framework- or provider-specific guidance only when the current stack or
feature needs it. React/Next performance work, payments, databases, component
registries, and deployment each have their own current primary sources and may
have dedicated installed skills; they are not mandatory phases of ordinary
frontend work.

### 3. Implement the complete slice

Work in coherent rendered slices, but retain the full requested scope. Connect
real data or an explicitly authorized deterministic fixture; do not present
invented state as product truth. Preserve adjacent behavior and retire any
superseded local path in the affected scope rather than layering a duplicate
implementation over it.

For reference work, compare progressively at the same viewport. Fix large
geometry and hierarchy before typography, color, shadow, and micro-detail.

### 4. Verify the real interface

Before finalizing any user-visible change, read
[references/qa-contract.md](references/qa-contract.md) and run the narrowest
browser-backed checks that cover the actual blast radius.

At minimum for non-trivial UI work:

- run the repo's relevant typecheck, lint, tests, and build when present;
- load the exact target in a real browser;
- exercise the primary touched interaction and observe the resulting state;
- check the product's primary viewport plus one materially different viewport;
- inspect layout/overflow, meaningful console errors, keyboard/focus behavior,
  and changed content states;
- compare against any accepted visual reference at equivalent dimensions.

Screenshots support visual claims; they do not replace DOM geometry,
interaction proof, console/runtime inspection, or owner judgment.

### 5. Close the changed truth

Inspect the final diff and update the authoritative user, operator, contributor,
or release documentation whose behavior changed. Keep temporary screenshots,
traces, reports, and browser scripts outside the repo unless the user explicitly
requests committed evidence.

Report separately:

- source behavior changed;
- focused checks and build passed or failed;
- rendered desktop/mobile and interaction checks passed or failed;
- deployment/runtime activation performed or not performed;
- owner/device/aesthetic acceptance confirmed or still open.

## Hard failures

Do not hand off as complete when any in-scope item remains:

- blank shell, framework error overlay, broken route, missing asset, or relevant
  console error;
- inert or fake primary controls;
- clipped primary content, unintended horizontal scroll, overlap, hidden focus,
  inaccessible modal/flyout behavior, or unreadable responsive collapse;
- placeholder copy/data presented as real product state;
- visual drift from an accepted reference that is still fixable;
- build-only or screenshot-only evidence presented as runtime or owner
  acceptance;
- ImageGen output used as a substitute for product reasoning, real UI, or
  runtime verification.

## Maintainer provenance

This method deliberately adapts a small number of external mechanisms and
Faye/Cove field practices without inheriting their whole workflows. Read
[references/lineage.md](references/lineage.md) only when revising the skill's
method, sources, or licensing/provenance boundary.
