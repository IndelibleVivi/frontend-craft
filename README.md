# Frontend Craft

Frontend Craft is Faye & Cove's evidence-led Codex skill for building,
redesigning, repairing, and reviewing real frontend interfaces. It starts from
the product, repository, accepted design or reference, and rendered runtime;
it does not make generated concept art a prerequisite for frontend work.

## What it protects

- ImageGen is opt-in. It is used only when generated imagery is explicitly
  requested or a concrete raster-asset gap is explicitly approved.
- Existing products keep their real architecture, behavior, data, routes,
  semantics, and accepted visual system unless a replacement is authorized.
- Reference-led work treats the reference as visual authority and the running
  product as behavior authority.
- Net-new design grows from the actual subject, audience, content, workflow,
  and constraints rather than a fashionable generic template.
- Completion requires browser-backed responsive, interaction, focus,
  accessibility, layout, and runtime evidence proportional to the change.
- Source, build, rendered runtime, deployment, and owner acceptance remain
  separate claims.

The full operating method is in [SKILL.md](SKILL.md). The rendered verification
contract is in [references/qa-contract.md](references/qa-contract.md), and the
field-practice and public-source provenance record is in
[references/lineage.md](references/lineage.md).

## Install for evaluation or authorized use

Ask Codex to install the skill from:

```text
https://github.com/IndelibleVivi/frontend-craft
```

Or use Codex's bundled skill installer:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-installer/scripts/install-skill-from-github.py" \
  --repo IndelibleVivi/frontend-craft \
  --path . \
  --name frontend-craft
```

The installer intentionally stops if `frontend-craft` already exists in the
destination. After installation, start a fresh Codex task or reload skill
discovery before evaluating activation.

## Use

```text
Use $frontend-craft to build this interface from the repo's real product,
design, and runtime authority. Do not use ImageGen unless I explicitly approve
a required generated asset.
```

The skill also routes targeted repairs, strict reference-led implementation,
visually unlocked net-new work, and review-only frontend audits without forcing
all of them through one design-generation flow.

## Repository shape

The repository root is the installable skill directory:

```text
README.md
SKILL.md
agents/openai.yaml
references/qa-contract.md
references/lineage.md
```

## Rights

Public visibility makes this source inspectable, but no copyright license has
been granted yet. The installation instructions document the package boundary;
they are not themselves permission to copy, redistribute, or publish modified
versions. A future LICENSE must be an explicit maintainer decision.
