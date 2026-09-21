# Frontend Craft maintenance

This independent repository owns the canonical Frontend Craft skill source.
Make accepted source and documentation changes here. The repository root is
the installable skill package; installed copies and discovery links are
separate layers, not alternative source owners.

## Source and data boundaries

- `SKILL.md` owns routing and the shared method. `references/` owns focused
  methods and runbooks; load them only when they affect the current task.
- `scripts/fc_memory.py` owns the local record CLI. `scripts/fc_cloudflare.py`
  owns the optional Cloudflare transport and synchronization implementation.
- Personal context, case catalogs, credentials, configuration, sync state,
  raw sessions, and evaluation traces stay outside this repository. Use only
  synthetic records in tests and portable placeholders in documentation.
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
- Update README for supported behavior, installation, ownership, or data-flow
  changes, and the relevant method/runbook for operational changes. Keep dated
  provenance in `references/lineage.md` distinct from current instructions.
- Report source, published commit, installation, actual execution, and owner
  acceptance separately. Package validity and test counts do not prove design
  quality or that a host delivered the updated instructions.
