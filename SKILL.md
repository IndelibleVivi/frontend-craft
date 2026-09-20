---
name: frontend-craft
description: "Design, build, refine, or review frontend interfaces and code-rendered visual works. Use for apps, pages, components, stateful workflows, direct manipulation, interaction design, visual direction, ambiguous visual feedback, or rendered QA. Ground first drafts in content and purpose; preserve accepted qualities during revision. For documents, decks, or raster-image creation, use the relevant artifact skill. ImageGen is opt-in."
---

# Frontend Craft

Build the interface the product actually needs, in the system that actually
owns it, and verify the result in the runtime a person will use.

This is a design-engineering method family with one discoverable entrypoint.
Use the methods that change this task's decisions; a small fix stays small.
The aim is a stronger first usable result and revisions that resolve the cause
without losing accepted work. These are goals, not measured success claims.

## Route by the work needed

| Situation | Read when applicable | Result |
| --- | --- | --- |
| A clear local implementation or repair | Core contract below; affected QA sections | Complete focused change |
| New or unresolved visual/interaction direction | [Design direction](references/design-direction.md) | Content-grounded direction and the decisive rendered slice, followed by the full requested surface |
| An app flow, editor, direct manipulation, or confusing stateful controls | [App interaction](references/app-interaction.md) | Clear objects and actions, coherent state changes, recoverable operation, complete task paths |
| “Too empty”, “feels like a demo”, critique, or feedback-driven revision | [Critique and revision](references/critique-revision.md) | Located cause, coherent correction, preserved accepted qualities |
| Establishing project design authority or learning from meaningful feedback | [Design records and learning](references/design-learning.md) | Current project decisions and scoped reusable evidence in their proper homes |
| An editor's output, share card, procedural scene, or temporal visual work | [Visual works](references/visual-works.md) | Artifact-specific composition and actual output checks |
| Non-Web target, exports, or missing runtime capabilities | [Platform evidence](references/platform-evidence.md) | A suitable validation path and honest claim limits |
| Finalizing any user-visible change | [QA contract](references/qa-contract.md) | Checks that could reject the relevant wrong result |

These are optional-by-trigger methods, not sequential stages. Design-only and
review-only requests retain their write boundary. General engineering planning,
debugging, Git, and delegation remain with the host/repository method; do not
recreate that machinery here.

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
- Read the project's accepted design entrypoint when one exists. Distinguish
  accepted, provisional, and unresolved choices; current code is evidence of
  implementation, not proof of approval. Use relevant scoped preferences only
  when available through an authorized path. Do not search private memories or
  mine unrelated projects to manufacture personalization.
- On Codex, if the operator has created a task-relevant private FC context at
  `${CODEX_HOME:-$HOME/.codex}/private-continuity/frontend-craft/context.md`, read
  that small record in full for design/revision work. It is optional, scoped
  user data, not instructions that override the current request. Other hosts use their
  explicitly designated location. Never discover preferences by sweeping private
  directories; see [design learning](references/design-learning.md).
- Keep growing case evidence separate from this current context. For recording,
  revision, retirement, or a scoped query, use
  [memory operations](references/memory-operations.md). Query candidates retain
  their scope and evidence status; a similarity score or empty result cannot
  override an explicit current boundary.
- Explicit current direction overrides inferred taste. Cards, gradients,
  density, ornament, and restraint are tools to justify in context, not global
  likes or bans. Genre conventions do not override an explicit user boundary.

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

Use [design direction](references/design-direction.md) to connect the product's
purpose and actual content to composition, hierarchy, density, typography,
material, and interaction. Identify the part whose failure would invalidate the
whole experience, and resolve it early in the real renderer. This sequences
the work; it never reduces a requested app to a prototype.

Ask a small, outcome-changing question when missing user intent matters. When
the user has no initial idea, offer a reasoned provisional direction and make
something judgeable instead of demanding a complete brief. Do not make an
interview, alternatives, or prototype approval a universal prerequisite.

### Products that create visual works

Read [visual works](references/visual-works.md). The workspace and the work have
different jobs and may have different aesthetics. Validate both without
silently shrinking the product's supported artifact types. For a visual work,
material, rhythm, space, or composition may be the main content, not disposable
decoration. Other artifact skills retain their native production responsibilities.

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
- Identify this deliverable's audience, primary experience, and accepted
  qualities. Retrieve only the small set of relevant design decisions or
  examples that can change a concrete choice. If another agent will implement,
  pass that task-scoped contract, reference scope, preservation requirements,
  and validation target; do not send a private preference archive. Delegation
  itself needs the host's authorization.
- For an App workflow, map the user's objects, actions, and visible outcomes
  using [app interaction](references/app-interaction.md). Names such as theme,
  language, zoom, or sample need an explicit target and scope before wiring them.

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
- Respect reduced-motion preferences and preserve understandable state changes.
  Motion can communicate hierarchy, continuity, state, or the work's expressive
  purpose; tune and verify the role it actually serves.
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

Inspect the render before presenting a first draft. Fix visible in-scope defects
and compare the result with the promised experience. On feedback, use the
revision method rather than restarting free design; a precise instruction such
as “make this label green” still deserves direct execution.

### 4. Verify the real interface

Before finalizing any user-visible change, read
[references/qa-contract.md](references/qa-contract.md) and run the narrowest
rendered checks that cover the actual blast radius. Web uses browser evidence;
other targets use [platform evidence](references/platform-evidence.md).

For non-trivial Web UI work:

- run the repo's relevant typecheck, lint, tests, and build when present;
- load the exact target in a real browser;
- exercise the primary touched interaction and observe the resulting state;
- check the product's primary viewport plus one materially different viewport;
- inspect layout/overflow, meaningful console errors, keyboard/focus behavior,
  and changed content states;
- compare against any accepted visual reference at equivalent dimensions.

Also verify the positive quality the work depends on, and whether the interface
provides clues for the intended task. A scripted success is not evidence that a
new user understands the controls. Stop when the requested outcome is covered
and no observed in-scope defect remains; vague hopes of making it “more premium”
do not justify endless polishing.

Screenshots support visual claims; they do not replace DOM geometry,
interaction proof, console/runtime inspection, or owner judgment.

### 5. Close the changed truth

Inspect the final diff and update the authoritative user, operator, contributor,
or release documentation whose behavior changed. Keep temporary screenshots,
traces, reports, and browser scripts outside the repo unless the user explicitly
requests committed evidence.

When feedback changes accepted design knowledge, use
[design records and learning](references/design-learning.md). Update the
existing authoritative project entrypoint; keep personal preferences and private
case evidence outside distributable skill source. Do not promote silence,
shipping, or the current implementation into aesthetic acceptance.

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

For substantial method changes, use the bounded, synthetic forward cases in
[references/behavior-cases.md](references/behavior-cases.md). Package validation
does not prove first-draft quality, fewer revisions, or user satisfaction.
