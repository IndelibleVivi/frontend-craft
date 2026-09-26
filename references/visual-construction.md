# Construct visual relationships

Use when composing a first result or when diagnosis identifies a relationship
that needs to be remade. [Design direction](design-direction.md) chooses the
goal; [critique](critique-revision.md) locates failures. This method supplies
making moves to test in the renderer, not a style preset or ingredient list.

## Establish the subject and its supporting roles

Place representative content before designing its containers. Identify the
main subject, related facts, next action, and secondary explanation. Sketch
their spatial relationships directly in the target renderer when practical.
Use real type, content lengths, images, and active controls early enough that
they can change the composition.

Repeated outlines can make tiny pieces of content compete with the subject.
Group by meaning first: shared alignment and proximity may carry a relationship
with less visual weight than nested boxes. Keep enclosures where they explain
selection, input, separation, or character. Cards and pills can work well;
replacing their shape without changing the relationships does little.

## Choose a making move with a visible consequence

These are examples of construction reasoning. Apply the row that explains the
current work, then inspect the result; they are not mandatory steps.

| Relationship to build | Concrete implementation move | What could show the move was wrong |
| --- | --- | --- |
| Related values should read as one observation | Align their labels and values, group shared context once, and let the group own its heading rather than boxing each value equally | Scanning loses units or independent edit targets; a group is mistaken for one value |
| A reading surface needs breathing room | Set a deliberate text measure, closer within-group spacing and larger between-group intervals; move secondary controls out of the reading line while keeping them discoverable | Extra scrolling separates facts needed together, or whitespace simply pushes the subject off screen |
| A rich composition needs an operable foreground | Give imagery/texture a bounded role and quiet enough local contrast behind text; organize one dominant mass with subordinate ornaments | Decorative contrast wins over labels, controls blend into material, or expression has been stripped out instead of composed |
| A dense workspace needs simultaneous comparison | Align comparable values, reduce repeated labels, use compact type roles and meaningful separators; keep relevant columns in view | Compression makes labels unreadable or responsive reflow breaks cross-row comparison |
| Typography should distinguish reading from measurement | Use roles for prose, short labels, values, and units; tune measure, leading, numeral alignment, wrapping, and mixed-script fallback at actual size | Enlarged headlines dominate the task, numbers lose their units, or the fallback font changes line breaks unexpectedly |
| Images should carry subject rather than fill a slot | Choose aspect ratio, crop, focal position, and text relationship together; inspect the real asset and replacement content | A crop removes the meaningful subject, a mask hides detail, or a sample-specific image dictates every future record |
| Motion should explain a change or express a work | Tie duration and sequencing to entry, response, continuity, or rest; keep the action result clear in reduced motion too | Repeated use requires waiting, motion obscures state, or removing it erases essential feedback |

Build a coherent grammar from these decisions. Use canonical tokens where
repetition warrants them, but do not create a theme engine for every style the
skill might encounter. Two separate products can be beautifully different
without either supporting the other's visual system.

## Choose controls and graphic means

Choose the means of expression from the job before tuning the existing widget.
If a few meaningful choices need comparison, visible semantic options may serve
better than a collapsed menu; if a long option set needs compact selection, the
menu may be right. [App interaction](app-interaction.md) owns that control decision.
Likewise, a typographic composition, an authored SVG, a real image crop, or a
procedural field can establish different subjects and rhythms. Use the product's
available visual language and the actual content to choose; the user need not
name a drawing technique before the agent can use it.

A graphic earns its place through the relationship it creates: orienting a
section, expressing character, connecting related content, or providing a focal
subject. Adding an illustration beside an unchanged weak form may leave the
complaint intact. Recompose the graphic, text, controls, and responsive behavior
together where needed. Code-native graphics stay within the task's scope;
[ImageGen remains opt-in](../SKILL.md#image-policy-opt-in-never-prerequisite).

When a few options need comparison and their effects are hard to connect, open
the [choice-and-result making study](../examples/showcase/README.md#making-study-choice-and-result).
It isolates the visible-choice → immediate-result relationship from Soft Scoop
and lets the reader change content length and option count. Inspect the working
state at the intended width before borrowing the mechanism; the example's
styling is not a prescription. Its source and counterexample belong with the
study, rather than in a new general control rule.

## Make information-bearing graphics truthful

Decide whether a mark conveys data, operation, identity, or decoration.
Aggregated durations can support totals or proportions; they cannot establish
the ordering of events. Start/end timestamps show an interval, not necessarily
continuous activity. A circle may suggest progress or a whole: use it only
when that meaning is supported, or make its decorative role unambiguous.
The same applies to text labels: do not infer confidence, completion, or
activity status from unrelated note wording or the newest date unless the
product actually defines that derivation. A plausible annotation can invent
a fact just as readily as a plausible chart.

Distinguish input from display. A graphic that explains a range may be poor at
entering a precise value. Keep a clear semantic control, units, and accessible
alternative where needed; [App interaction](app-interaction.md) owns control
selection. Hand-drawn SVG, CSS, canvas, and other code-native graphics can carry
expression without inventing measurements or replacing usable controls.

## Adapt the relationship to the working viewport

Decide what must remain together when space changes. A desktop side panel can
become a long trip away from the active object on a phone. Recompose grouping,
position, or disclosure around the action and result; scaling down everything
or stacking it blindly may preserve pixels while losing the experience.

For repeated-use surfaces, inspect the distance from opening the product to
its useful subject and action. Large introductions, summary statistics, and
one-chip-per-record navigation can consume the phone's first screen before
any actual work appears. Recompose or compress that preliminary material when
it displaces the daily task; preserve a deliberate introduction where first-use
orientation or the product's expressive purpose calls for it.

Check representative long content and the actual working state, not only an
empty or resting screen. Touch, focus, selection, validation, and keyboard
occlusion can change visual weight and reachability. Use the available runtime
evidence honestly; a short browser viewport is not a physical-keyboard test.

## Inspect the before and after, then retain the useful mechanism

Hold content, state, fonts, and viewing scale sufficiently steady to explain
the change. Name the prior relationship, the implementation move, the observed
result, and its cost. “Less cluttered” needs visible support, such as a clear
reading sequence without losing the next action. Do not equate fewer controls,
more whitespace, or more decoration with better quality.

If the move fails, change the relationship rather than intensifying the same
effect. Unknown preferences still require a considered craft judgment. Explicit
richness, playfulness, restraint, or ritual should each be made to work; none is
noise to normalize away.

A reusable making case needs the actual before/after artifact, representative
input, mechanism, observation, and limit. Keep private evidence in its proper
home through [design learning](design-learning.md); examples in this table are
reasoning aids, not measured success cases or owner-approved designs.
