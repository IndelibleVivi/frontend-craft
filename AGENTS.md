# Frontend Craft maintenance

This independent repository owns the canonical Frontend Craft skill source.
Make accepted source and documentation changes here. The repository root is
the installable skill package; installed copies and discovery links are
separate layers, not alternative source owners.

## Source and data boundaries

- `SKILL.md` owns routing and the shared method. `references/` owns focused
  methods and runbooks; load them only when they affect the current task.
  Build owns reference-to-product continuity; Evolve owns product change;
  App interaction owns the state-layer model; State and contracts owns tracing
  persistence boundaries; QA owns checks; Interface scenarios owns replay.
  Link these owners rather than copying their rules into new lifecycle leaves.
- `scripts/fc_memory.py` owns the local record CLI. `scripts/fc_cloudflare.py`
  owns the optional Cloudflare transport and synchronization implementation.
- Personal context, case catalogs, credentials, configuration, sync state,
  raw sessions, and evaluation traces stay outside this repository. Use only
  synthetic records in tests and portable placeholders in documentation.
- `examples/memory/` is a public synthetic fixture, not an operator record
  store. Keep its walkthrough and CLI assertions aligned; never put personal
  feedback or credentials into it.
- `examples/workflow/` owns the standalone, synthetic interactive demo. Keep
  its English and Chinese UI aligned and preserve draft/save/reopen behavior.
  It makes no model calls and is not evidence of an autonomous FC run.
- `examples/showcase/` owns the independent interactive style gallery. Its
  authored scenes demonstrate different compositions and controls, not an
  autonomous FC run or measured design-quality improvement.
- `scripts/render_banners.py` owns the hand-authored pixel glyphs, sprites,
  palettes, and scenes; `docs/visuals/banner-*.svg` are its derived exports.
  Re-render them after source changes. Do not replace these with ImageGen
  assets. The full project name is the title; FC is not a separate logo.
- `docs/visuals/architecture.*.svg` are directly editable diagram sources;
  the visual README maps claims to their method/helper owners. Preview PNGs
  are derived browser captures of the demos, not alternate UI sources.
  Refresh both language captures after visible demo changes.
- Local tests do not authorize external provisioning, writes, or private-data
  transfer. Preserve the caller's actual authorization for live operations.
- Do not replace current source with an older package or installation snapshot.
  Reconcile patches against this repository's current branch and history.

## Verification and documentation

- Run `python3 -m unittest discover -s tests -p 'test*.py'` for helper changes.
  For external API boundaries, assertions must encode the verified contract
  independently of the implementation constant they check.
- Run `skill-validate .` when available for skill/package changes, and inspect
  local reference links and `git diff --check` for changed documentation.
- For demo changes, verify the affected interactions in a browser: note
  editing/save/reopen/discard, shop selection/totals, article navigation, or
  line-field controls and reduced motion. Check language switching, keyboard
  focus, and wide/narrow layouts for the changed demo.
- For diagram changes, inspect both languages at full and intended embed
  sizes; keep live text, accessible descriptions, and source-backed
  relationships. Pixel banners use authored glyph paths with text equivalents.
- Update README for supported behavior, installation, ownership, or data-flow
  changes, and the relevant method/runbook for operational changes. Keep dated
  provenance in `references/lineage.md` distinct from current instructions.
- `README.md` is the canonical English reader entrance; `README.zh-CN.md`
  maintains the same capabilities, commands, boundaries, and rights in Chinese.
  Update both when their shared contract changes. Method references remain
  English and authoritative for their own instructions.
- `LICENSING.md` owns the path-level rights map. Functional instructions and
  helpers use SUL-1.0; the listed explanatory documents use CC BY-NC-SA 4.0.
  Classify new surfaces by role and preserve third-party terms and provenance.
- `.github/workflows/ci.yml` runs the offline helper and public-example tests
  on Python 3.13, without secrets or live Cloudflare calls. Its result does not
  establish skill activation, rendered design quality, or live service readiness.
- Report source, published commit, installation, actual execution, and owner
  acceptance separately. Package validity and test counts do not prove design
  quality or that a host delivered the updated instructions.
