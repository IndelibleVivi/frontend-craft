# Licensing and provenance

Frontend Craft is **source-available**, with separate terms for its functional
skill package and explanatory documentation. It is not offered under an
OSI-approved open-source license. Faye Fang offers these licenses for the
project-original material; the project's authorship credit is **Faye & Cove**.

## Which terms apply

| Material | Paths | License |
| --- | --- | --- |
| Functional skill instructions and method/runbook references | `SKILL.md`, `AGENTS.md`, `references/` except `references/lineage.md` | [SUL-1.0](LICENSE) |
| Host configuration, helpers, tests, CI, synthetic record data, artwork rendering scripts, functional demos and technical specimens | `agents/`, `scripts/`, `tests/`, `.github/`, `.gitignore`, `requirements-fonts.txt`, `examples/memory/`, `examples/catalog/`, `examples/materials/`, `examples/workflow/` and `examples/showcase/` except their `README.md` files and the third-party font below | [SUL-1.0](LICENSE) |
| Third-party Noto Sans SC font derivative | `examples/materials/noto-sans-sc-specimen.woff2` | [SIL Open Font License 1.1](examples/materials/OFL-NotoSansSC.txt); source, author notice and exact derivation in [ASSETS.json](examples/materials/ASSETS.json) |
| Explanatory documentation and visual assets, including banners, architecture diagrams, and demo screenshots | `README.md`, `README.zh-CN.md`, `examples/README.md`, `examples/workflow/README.md`, `examples/showcase/README.md`, `examples/showcase/**/README.md`, `docs/specs/`, `docs/visuals/`, `references/lineage.md`, `LICENSING.md`, `LICENSE-DOCUMENTATION.md` | [CC BY-NC-SA 4.0](LICENSE-DOCUMENTATION.md) |
| Product example code, configuration, tests, render/capture scripts and original compilation metadata | `examples/products/`, except the documentation and assets classified below | [SUL-1.0](LICENSE) |
| Product explanations, asset manifests, screenshots, original cover arrangements and mark | `examples/products/**/*.md`, `examples/products/**/ASSETS.json`, `examples/products/**/evidence/*.png`, `examples/products/music-library/public/assets/covers/`, `examples/products/music-library/public/assets/mark.svg` | [CC BY-NC-SA 4.0](LICENSE-DOCUMENTATION.md), excluding incorporated third-party material |
| Side A recordings, original source images, font and bundled runtime dependencies | `examples/products/music-library/public/assets/audio/`, `originals/` and `fonts/` under that same assets directory; `public/THIRD-PARTY-NOTICES.txt`; dependencies declared in `examples/products/package.json` | Individual terms in [ASSETS.json](examples/products/music-library/ASSETS.json), [OFL.txt](examples/products/music-library/public/assets/fonts/OFL.txt) and [runtime notices](examples/products/music-library/public/THIRD-PARTY-NOTICES.txt) |

The Markdown method and runbook references are part of the instructions an
agent executes, so their classification follows their functional role rather
than their file extension. The license texts themselves retain their original
terms. Classify new material in this table when adding a new kind of surface.
`examples/catalog/README.md` and `examples/materials/README.md` are explanatory
documentation under CC BY-NC-SA 4.0, like the other example READMEs.
`assets/catalog/` and `examples/reference-desk/catalog.json` are functional
source/data under SUL-1.0. `examples/reference-desk/README.md`, its `evidence/`
captures, and `examples/materials/previews/` are explanatory material under
CC BY-NC-SA 4.0. The Noto font retains its individual OFL terms; a specimen
capture does not relicense the font file.

Side A's Kevin MacLeod recordings retain CC BY 4.0. NASA and Library of Congress
source material retains the conditions stated in the asset manifest. Cover
arrangements do not replace those underlying rights, and no artist or
institution endorsement is implied. Dependency and font notices must travel
with redistributed builds.

SUL-1.0 permits personal, noncommercial, and internal business use and
modification. Distribution or provision to others must be free of charge and
for noncommercial purposes, with its notices and other conditions preserved.
CC BY-NC-SA 4.0 permits noncommercial sharing and adaptation with attribution
and requires the applicable ShareAlike terms when adaptations are shared.
Read the linked license texts for the complete conditions.

## Sources and earlier revisions

[Lineage](references/lineage.md) records dated sources, pinned revisions,
independently worded adaptations, and mechanisms deliberately not adopted.
The package does not vendor the external rule corpora discussed there. Links
and acknowledgements do not relicense those sources; their own rights holders
and licenses continue to govern them.

These project licenses were introduced on 2026-09-22. Earlier repository
revisions carried no project-wide public license grant. This notice does not
rewrite history or alter third-party permissions. Private records, credentials,
case catalogs, and evaluation traces are not part of this repository or grant.

For contributions, retain third-party attribution and identify any material
you cannot offer under the applicable terms. No copyright assignment is
implied. Do not add private examples, copied rule corpora, or assets without
the rights needed to distribute them.
