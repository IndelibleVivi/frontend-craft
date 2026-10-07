# Produce and continue materials

Use when the composition needs actual materials, a generated sample must enter
production, or existing files need another crop, text coverage, or export.
[Visual construction](visual-construction.md) owns their compositional role;
[catalog operations](catalog-operations.md) owns registration and resolution.
This is a bridge to existing production tools, not a new generator or browser.

## Turn the design need into a usable brief

Choose the deliverable before choosing the tool:

| Deliverable | What to request | What remains code-native |
| --- | --- | --- |
| Direction or composition sample | A judgeable frame with the intended hierarchy and material relationships; label it as a concept | The complete working interface, real copy and responsive layout |
| Production image or layer | The subject, crop allowance, edge/alpha, lighting, required variants, and space that surrounding content needs | Buttons, navigation, editable text and state feedback |
| Texture or material map | Tile/scale, seams, channels, color-space expectations and the surface it will affect | Geometry, compositing, accessible foreground and lifecycle |
| Motion, scene or sound | Beginning, transition, resting/looping state, duration, camera/listener relation and actual controls | Interaction state, pause, reduced motion, media failure and return |

Write the brief from the current product: destination and role; actual subject;
material and color relationships; focal area and surrounding space; viewport or
aspect variants; required source/editable outputs; one decisive uncertainty to
inspect. Do not outsource these decisions to a user who only asked for a better
result. A resolved direction can go straight to production without sample voting.

Assign references separately: **identity/content**, **style/material**, and
**composition**. State which visible relationships each should preserve. A
rejected layout may still contain a needed object; attaching it as an unrestricted
composition reference can reproduce the rejected arrangement. Do not include
private or unrelated files just because a tool accepts multiple references.

## Use the installed production route

Read the applicable installed image, media or graphics skill and obey its actual
input/output and permission contract. Prefer the user's selected route. Do not
invent a model, account, fallback or command, and do not switch a failed web route
to a paid API silently. A material brief does not itself authorize generation,
uploads, cost or publishing; existing task authority may already cover them.

For a host with `image-use-chat`, follow that installed skill's `image-use`
workflow. Its `-i`, `--style-ref` and `--composition-ref` inputs have different
jobs: keep those meanings in the brief. Resolve its configured project through
that tool; FC stores no account/project defaults and reads no credentials.
Other hosts may provide a native image tool or another media skill. Use their
supported reference mechanism instead of pretending these CLI flags are portable.
If no suitable route exists, identify the missing output and continue independent
layout/material work; never report a prompt as a produced asset.

Keep the actual returned file and available provenance: source or tool, supplied
references, effective prompt/parameters when exposed, dimensions, alpha and
format. Record unknown settings as unknown. Inspect the pixels or playback,
then load the output at its real size in the product. Recut/re-export from the
original when the layout changes; a screenshot of the output is not its source.
When submission outcome is uncertain, recover the existing tool job before
resubmitting. On success, register actual files, not a predicted output path.

## Fonts: inspect, subset, and rebuild when text changes

Start with the exact licensed font file and its license, not a family name.
The optional [font helper](../scripts/fc_fonts.py) uses
[fontTools](https://fonttools.readthedocs.io/en/latest/subset/index.html) to inspect
family/version, variable axes and cmap, and make WOFF2 from explicit UTF-8 text.
It does not download fonts, choose a face, grant rights, or rewrite project CSS.
FontTools with WOFF2 support is optional; use the project's environment or an
isolated one. The following tested invocation keeps it out of system Python:

```bash
uv run --with 'fonttools[woff]==4.60.1' python scripts/fc_fonts.py inspect \
  --font /work/materials/title.ttf --text-file /work/project/title.txt
uv run --with 'fonttools[woff]==4.60.1' python scripts/fc_fonts.py subset \
  --font /work/materials/title.ttf --text-file /work/project/title.txt \
  --text-file /work/project/controls.txt --out /work/project/fonts/title-v1
```

Run from the FC package, or use its absolute helper path. Each subset creates a
new directory containing `font.woff2` and `manifest.json`; existing outputs are
refused. The original is untouched. The manifest records exact input/output
digests, relative source/text paths, requested/missing codepoints, font metadata,
and tool version. Digests identify the bytes used for this derivation. Keep the
original and text inputs with the project/material store; the manifest does not
embed them or make absent files recoverable. Do not publish private text paths.

Missing glyphs fail before output unless `--allow-missing` explicitly permits a
known fallback; those characters remain listed. Newline, carriage return and tab
are layout controls; other requested characters are checked without normalization.
Collections require `--font-index`. All layout features, font names, license
metadata and available variable axes are retained by this recipe. Cmap coverage
does not prove shaping, variation-sequence support, color-font fidelity or quality.
Keep the original font when subsetting would lose a feature the product needs.

On a text change, resolve the same original, update the real text input and write
a new revision directory. Register source and WOFF2 as separate assets linked by
derivation, with the manifest as the making recipe. Update the project's use to
the new asset only after loaded-font checks. Do not subset an old subset to add
glyphs it never contained. For open-ended user content, choose full coverage,
language ranges or an intentional fallback; finite title coverage is insufficient.

In the browser, await font loading and inspect actual mixed-script text,
punctuation, wrapping, weight/axis values and fallback. Compare the new content at
wide/narrow sizes. A declared CSS family or successful conversion proves neither
that it loaded nor that every glyph came from it.

## Retain materials for the next task

Use the project’s existing design entrypoint to locate its catalog and explicitly
named shared stores. Resolve exact assets with [catalog operations](catalog-operations.md)
before editing. Registration records acquisition; a project use records adoption
or application; scoped cases record feedback. None implies the others.

For an image crop, keep the original, crop/scale parameters and exported variant;
for a vector or procedural work, keep editable source and parameters; for 3D,
keep model, textures, environment and camera/material settings together; for media,
keep the source, edit/encoding recipe and playback conditions. The host's existing
tools perform the transformation. Catalog recipes are data, never auto-executed.

If a variant is missing, use an available original and its inspected recipe to
rebuild under the current task. If bytes changed, preserve that fact and record a
new revision; do not claim the new file reproduces the old capture. If an original
is missing too, report the specific dependency and use an authorized alternative.
Gallery copies are useful evidence, not automatically the editable production source.

Moving hosts requires the actual catalog, permitted materials and explicit root
bindings. Rebind portable roots, resolve, open the decisive material, then continue
one real edit. A cloud case hit or copied JSON alone does not move font/image bytes.
Keep private catalogs, generated galleries and intermediate manifests local unless
publication is actually authorized.
