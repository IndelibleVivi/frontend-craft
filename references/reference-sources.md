# Reference sources and making recipes

Use when a concrete making decision lacks a convincing positive destination,
when the current technique cannot produce it, or when revisions converge on
the same weak result. Start with the recipe relevant to the task; inspect its
source when that evidence can change the choice. These are conditional craft
materials, not a compulsory reading list or a universal visual style.

## Find evidence at the scale of the problem

Describe the product posture, actual content, core use episode, platform, and
relationship to improve before searching for a component or style name.
A product's public introduction is not evidence of its populated daily UI.
Choose one main direction and name what each additional source contributes.

Use an available research tool or Soundings, when installed, for a bounded
question. For example:

> Find an inspectable reading/library experience that connects a search hit to
> its full context and returns to the same result set. Include real long text,
> navigation states, visual material, and implementation clues. Explain the
> relationships to borrow and the conditions that could break them. Return a
> viable direction for the current platform, not only links or component names.

Keep private context out of external queries. Observe the medium that matters:
screenshots for composition, actual states for interaction, time for motion,
and source for implementation. If a source cannot be inspected, use another or
label the missing evidence. Then continue the original making task. Available
knowledge does not require research for a clear local fix.

## Content recognition before container styling

**Use:** browsing records where title/subject lets the reader recognize an item.
Compose identity first, decision-helping context next, metadata last. Group
related values; combine a value with necessary units/context instead of giving
every database field an equally prominent label. Keep the item's real action
and enough context to distinguish similar items.

**Try:** render the same three uneven records before/after. Change hierarchy
and grouping while holding content steady; then repeat the row enough times
to reveal accumulated borders and visual weight. A label-led specification
comparison may need the opposite emphasis. Form labels and accessible control
names retain their own contracts.

**See:** [Refactoring UI's public example](https://refactoringui.com/previews/labels-are-a-last-resort)
contains visible before/after images and the label-scanning exception. The
mechanism does not require removing cards, importing its brand, or buying a book.

## Type roles with the actual language

**Use:** reading, long titles, bilingual content, or dense labeled values.
Make a specimen containing the real scripts, punctuation, numerals, short and
long headings, paragraphs, and active controls. Resolve the reading body, then
assign distinct display, navigation, annotation, and numeric roles. Tune font,
size, weight, measure, leading, and paragraph intervals together. Inspect the
loaded face and actual fallback; an English font pairing cannot settle CJK.

**Try:** a narrow article with a quieter metadata line and a compact navigation
face. Increase paragraph leading only while retaining visual grouping; compare
a long heading and mixed-script paragraph at reading size. A measurement table
needs alignment and simultaneous comparison instead of prose rhythm.

**See:** [Butterick](https://practicaltypography.com/typography-in-ten-minutes.html)
connects body text, size, measure, and leading. Adapt those relationships; do
not inherit the author's font bans or numeric ranges as universal requirements.
[W3C CLReq](https://www.w3.org/TR/clreq/) addresses Chinese punctuation, line
breaking, and mixed scripts; the inspected 2026-09-01 publication is a Group
Note Draft, a work in progress, not a W3C Recommendation.

## Let content determine a layout change

**Use:** an auxiliary region next to a primary reading or working region.
Choose the minimum useful width of each from its content. Let the pair wrap
when both can no longer work, rather than shrinking the primary text to keep
a desktop arrangement. Keep DOM/focus order coherent with the action sequence.

**Try:** a wrapping flex pair: a bounded auxiliary basis, a flexible primary
region, and a primary minimum based on readable content. A viewport breakpoint
alone may miss a narrow embedded container. After reflow, inspect the distance
between a control and its result; if stacking separates them, change disclosure
or position. The same rule does not justify hiding simultaneous comparisons.

**See:** [Every Layout's Sidebar](https://every-layout.dev/layouts/sidebar/)
connects a width problem to an inspectable layout and CSS mechanism. Borrow the
relationship using the current project's primitives, not a new component system.

## Make a visual choice explain its result

**Use:** a small mutually exclusive set whose differences are visual.
Expose the differentiating feature in each named choice and show its effect
near the current object. Keep selected identity separate from keyboard focus;
keep preview separate from saving when the product distinguishes them. Provide
precise entry for an exact value, rather than forcing it through a swatch.

**Try:** [the local choice-and-result study](../examples/showcase/studies/choice-and-result/index.html)
with three versus twelve choices, long labels, both languages, and compact
versus visible presentation. Follow one selected ID into title, art, and result.
A large set may need a menu or search; a multiselect or continuous quantity
requires a different contract.

**See:** [Adobe ColorArea](https://react-spectrum.adobe.com/ColorArea) connects
visible color adjustment with keyboard and accessible values;
[W3C APG radio guidance](https://www.w3.org/WAI/ARIA/apg/patterns/radio/) describes
exclusive choice and keyboard expectations, including native/toolbar differences.
These references do not require replacing the project's framework.

## Compose a material rather than attach an ornament

**Use:** a distinctive, rich, playful, or atmospheric direction.
Choose what carries the subject: image crop, letterform, graphic mass, texture,
spatial effect, or motion. Assign secondary materials a supporting role and
compose text and controls against their actual weight. Check one filled working
state as well as the initial presentation. Richness may concentrate in the work
while its editing controls stay quiet.

**Try:** for a translucent surface, first supply something meaningful behind it;
then tune background detail, opacity, edge, and foreground contrast together.
For an illustrated cover, let the image's focal point and silhouette determine
the title's space. These are different directions, not effects to accumulate.
A plain background can make translucency pointless; an unavailable subject
image can make a photo-led composition incomplete.

**See:** [IBM illustration techniques](https://www.ibm.com/design/language/illustration/tips-and-techniques/)
connect focal area, format, and composition. Its proprietary brand language is
not a general style requirement. [Codrops tutorials](https://tympanus.net/codrops/hub/tutorials/)
are a discovery route from expressive work to demos and code; inspect the actual
demo and its state/rights limitations before adopting it.

## Continuity

**Use:** a selection, disclosure, navigation, or direct manipulation whose
origin and destination should remain understandable. Make the pre-action cue,
transition, and final state describe the same operation. Keep object identity
and a supported way back; repeated input should update the intended object
without waiting for a decorative transition to finish.

**Try:** open a result in context, inspect its neighbors, return to the same
query and location, then choose another result quickly. Preserve only the
product's promised view/draft/work state. For an anchored popover, derive motion
origin from actual placement, including flipped placement, and keep reduced
motion informative. An irreversible operation still needs its real commit
semantics; fluidity cannot fabricate cancellation.

**See:** [Apple's Designing Fluid Interfaces transcript](https://developer.apple.com/videos/play/wwdc2018/803/)
discusses redirection and spatial consistency in touch interfaces; translate to
the current platform. [Emil Kowalski's interactive examples](https://emilkowal.ski/ui/good-vs-great-animations)
connect origin and movement to CSS. Use their mechanism rather than one fixed
easing or duration for every action.

## Selective absorption from UI UX Pro Max

FC contains the following independently expressed adaptations from inspected
upstream material; using them does not require installing the upstream skill
or running its generator. Source records remain candidates, not standards.

| Inspected upstream material | Usable FC adaptation | Condition to check |
| --- | --- | --- |
| [Typography data](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/blob/main/src/ui-ux-pro-max/data/typography.csv): single-family weight roles and script-specific candidates | Try a single family with distinct reading/control weights before adding a second; Noto Sans SC is a candidate for simplified Chinese, Noto Serif TC / Noto Sans TC for traditional Chinese roles | Verify current font coverage, loading rights/network policy and actual mixed-script specimen; category names do not determine taste |
| [Style data](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/blob/main/src/ui-ux-pro-max/data/styles.csv): material/effect/implementation fields | Translate a proposed material into its visual cause, such as background detail + translucency + edge + readable foreground | The material recipe above; do not import industry exclusions, fixed values, or categorical performance claims |
| [Color data](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/blob/main/src/ui-ux-pro-max/data/colors.csv): background/foreground and on-color roles | Define colors in working pairs and semantic roles; test their area and adjacency in the actual screen | A supplied palette does not establish contrast in overlays, selection, or imagery |
| [App interface data](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/blob/main/src/ui-ux-pro-max/data/app-interface.csv): pending, success, and error feedback | Put progress and actionable failure at the affected object; keep work recoverable and success truthful | Inspected examples target iOS/Android/React Native; translate semantics, not native imports or a fixed delay |

The inspected [generator](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/blob/main/src/ui-ux-pro-max/scripts/design_system.py)
has a marketing-section fallback. FC chooses structure from the product's task.
No CSV corpus, scripts, framework, or font binaries are vendored here. The
upstream [MIT license](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/blob/main/LICENSE)
was checked on 2026-10-02; substantial source reuse would retain its notices,
and font/image rights must be checked separately.

## Whole works, discovery sources, and limits

[Atomic Design chapter 2](https://atomicdesign.bradfrost.com/chapter-2/)
supports moving between real pages and their parts instead of treating assembly
as a linear guarantee of quality. [IBM layout](https://www.ibm.com/design/language/layout/overview/)
offers spatial relationships to inspect; its brand's restraint is not a ban on
expressive work. [Norman on signifiers](https://jnd.org/signifiers-not-affordances/)
helps explain pre-action cues. [Apple audio](https://developer.apple.com/audio/)
distinguishes audio-centered experience and embellishment; listen to validate it.

[Component Gallery](https://component.gallery/components/color-picker/) can
locate original component systems. [Refero's public tool reference](https://github.com/referodesign/refero_skill/blob/master/skills/refero-design/references/mcp-tools.md)
separates styles, screens, and flows; its inspected style coverage emphasizes
marketing/product pages, so app investigations need actual screens and flows.
Refero or [Mobbin](https://mobbin.com/mcp) may be optional connected sources;
no account, paid access, installation, or fixed multi-variant process is required.

Maintainer inspection on 2026-10-02 covered the recipes' cited primary
text/code, the UI UX Pro Max files, Refero's tool reference, and Refactoring
UI's rendered examples. Other galleries are discovery pointers; their
inventory, visuals, motion, and connected access were not verified.
The older Codrops Grid Zoom article returned a generic page and its demo was
unavailable through the research tool; it is not used as observed behavior.
Private galleries were not connected. Inspect decisive live evidence for each
new task. Research pointers, redistributed assets, practiced mechanisms, and
owner-accepted results retain their different evidence and rights boundaries.
