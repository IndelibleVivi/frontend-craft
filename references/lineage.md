# Frontend Craft Lineage

This is maintainer provenance, not a daily runtime checklist. `frontend-craft`
uses original wording and a locally owned contract. External work supplies
contrast and narrow mechanisms; it does not become automatic authority.

Review date for the records below: 2026-08-30.

## Faye/Cove field practice

The local kernel comes from repeated frontend and PWA work across product,
reader, dashboard, and reference-led surfaces:

- accepted product/design material, current app behavior, runtime state, and
  owner judgment are different authorities;
- an exact reference governs visuals while the app continues to govern real
  behavior;
- source, build, server/runtime, installed client/PWA, and owner acceptance are
  separate gates;
- browser QA needs interaction, console, responsive layout, and DOM geometry;
  screenshots alone can misdiagnose overflow or compositor artifacts;
- fake data, screenshot-only mocks, and generated images cannot replace a
  canonical renderer or real product state;
- mobile-first is a product decision when adopted, not a universal styling
  slogan;
- formal visual direction may pause at an owner judgment boundary without
  freezing unrelated backend, protocol, or shared-renderer work.

These practices land in the runtime method and QA contract. Project-specific
names, release procedures, infrastructure, and private continuity do not.

## OpenAI Build Web Apps 0.1.2

Source
: Installed OpenAI remote plugin `build-web-apps@openai-curated-remote`, UI name
  `Build Web Apps`.

Pinned ref
: Version `0.1.2` as installed and inspected on 2026-08-30.

License / rights note
: No independent license grant was surfaced in the inspected bundle manifest or
  README. No plugin wording is copied into this skill; only high-level workflow
  behavior is compared and independently restated.

Reviewed files
: `skills/frontend-app-builder/SKILL.md`,
  `skills/frontend-testing-debugging/SKILL.md`, bundle `README.md`, and plugin
  manifest.

Distilled pattern
: Complete-surface implementation, design-system consistency, browser-backed
  interaction QA, and reference/render comparison can raise frontend quality.

Observed local problem
: The builder makes ImageGen-first concepting a hard default for broad new-app
  and redesign triggers, even when repo, product, reference, or runtime evidence
  is the more useful authority.

Landing plane
: Runtime method and QA.

Decision
: `ADAPT`

Accepted kernel
: Complete requested surface, coherent tokens/components, real browser loop,
  responsive/interaction checks, and faithful implementation after a concept or
  reference has actually been accepted.

Excluded machinery
: Mandatory ImageGen, a generated image per section, concept approval as a
  universal gate, forced React/Vite defaults, fixed agency-signoff rhetoric,
  and `view_image` as an unconditional completion blocker.

Verification if applied
: A behavioral forward-test must show that ordinary frontend work completes
  without ImageGen while preserving design authority and real browser QA.

Reopen condition
: Reassess if Codex gains a verified per-skill disable boundary or the upstream
  plugin removes its mandatory ImageGen contract.

## Anthropic frontend-design

Source
: [`anthropics/claude-plugins-official`](https://github.com/anthropics/claude-plugins-official),
  `plugins/frontend-design/skills/frontend-design`.

Pinned ref
: Commit [`ed404106fcd80ba98ecb7c851e531dcb626d13b7`](https://github.com/anthropics/claude-plugins-official/commit/ed404106fcd80ba98ecb7c851e531dcb626d13b7)
  dated 2026-08-28.

License / rights note
: [Apache-2.0](https://github.com/anthropics/claude-plugins-official/blob/ed404106fcd80ba98ecb7c851e531dcb626d13b7/plugins/frontend-design/skills/frontend-design/LICENSE.txt).

Reviewed files
: [`SKILL.md`](https://github.com/anthropics/claude-plugins-official/blob/ed404106fcd80ba98ecb7c851e531dcb626d13b7/plugins/frontend-design/skills/frontend-design/SKILL.md),
  skill `LICENSE.txt`, and plugin `LICENSE`.

Distilled pattern
: Ground a compact visual direction in subject, audience, page job, color,
  typography, layout, and one signature idea; critique it before coding and
  inspect the render afterward.

Observed local problem
: Tool-first concepting can displace product judgment and make media generation
  look mandatory even when the interface can be designed directly from the
  brief and real content.

Landing plane
: Runtime method.

Decision
: `ADAPT`

Accepted kernel
: Brief-specific direction, one coherent visual thesis, self-critique before
  implementation, and render critique when the environment supports it.

Excluded machinery
: Persona wording, trend-sensitive aesthetic blacklists, and treating aesthetic
  risk-taking as a hard gate for routine maintenance.

Verification if applied
: Net-new design should be recognizably tied to its subject and primary job
  without requiring generated concept art.

Reopen condition
: Revisit when the upstream skill changes its direction-setting or verification
  method materially.

## Vercel React Best Practices

Source
: [`vercel-labs/agent-skills`](https://github.com/vercel-labs/agent-skills),
  `skills/react-best-practices`.

Pinned ref
: Commit [`063bee94c3f4df8453406c830b0a7df0f2860278`](https://github.com/vercel-labs/agent-skills/commit/063bee94c3f4df8453406c830b0a7df0f2860278)
  dated 2026-08-28.

License / rights note
: The pinned skill frontmatter declares `MIT`, but the reviewed pinned repo tree
  did not expose a root license file. Keep original wording, link provenance,
  and do not vendor its rule text without a separate rights check.

Reviewed files
: [`SKILL.md`](https://github.com/vercel-labs/agent-skills/blob/063bee94c3f4df8453406c830b0a7df0f2860278/skills/react-best-practices/SKILL.md),
  `metadata.json`, `rules/_sections.md`, and `rules/bundle-conditional.md`.

Distilled pattern
: A small impact-prioritized router can load only the framework guidance needed
  for the current problem.

Observed local problem
: A monolithic frontend workflow taxes CSS, content, and repair tasks with
  unrelated framework rules and tools.

Landing plane
: Runtime routing and progressive disclosure.

Decision
: `ADAPT`

Accepted kernel
: Load high-impact, stack-specific engineering references only when the current
  framework, feature, or performance evidence makes them relevant.

Excluded machinery
: Vendoring the full React/Next rule corpus, treating React/Next as universal,
  and loading a monolithic fallback file for every frontend task.

Verification if applied
: A non-React visual repair should not load React guidance; a material
  React/Next performance task should route to the relevant category.

Reopen condition
: Add a maintained local reference only after repeated work proves a stable
  subset is being rediscovered often enough to justify ownership.

## Vercel Web Interface Guidelines

Source
: [`vercel-labs/web-interface-guidelines`](https://github.com/vercel-labs/web-interface-guidelines).

Pinned ref
: Commit [`e3d624baaf29dc1fc645aff3e38f03e564d2d6b1`](https://github.com/vercel-labs/web-interface-guidelines/commit/e3d624baaf29dc1fc645aff3e38f03e564d2d6b1)
  dated 2026-08-18.

License / rights note
: [MIT](https://github.com/vercel-labs/web-interface-guidelines/blob/e3d624baaf29dc1fc645aff3e38f03e564d2d6b1/LICENSE).

Reviewed files
: [`command.md`](https://github.com/vercel-labs/web-interface-guidelines/blob/e3d624baaf29dc1fc645aff3e38f03e564d2d6b1/command.md),
  `README.md`, `LICENSE`, and the pinned `agent-skills` integration wrapper.

Distilled pattern
: Keep implementation and audit as distinct modes; inspect actual source and
  rendered states for accessibility, focus, forms, motion, layout, content, and
  performance, then report locatable findings.

Observed local problem
: Generated concept imagery cannot prove an existing interface is correct,
  usable, responsive, or accessible.

Landing plane
: QA reference and review mode.

Decision
: `ADAPT`

Accepted kernel
: Blast-radius-aware source/runtime review, stateful interaction checks, and
  findings tied to concrete locations and evidence.

Excluded machinery
: Fetching unpinned `main` on every run, auditing every rule regardless of task
  scope, and importing provider-specific style preferences as universal law.

Verification if applied
: Review-only tasks must produce evidence-backed findings without silently
  editing; implementation tasks must still verify the real rendered surface.

Reopen condition
: Re-pin and re-evaluate before adopting a newly added category or automated
  audit mechanism.
