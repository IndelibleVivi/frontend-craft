# App interaction and working state

Use for stateful workflows, editors, direct manipulation, content libraries,
or an interface that technically works but feels baffling or tiring. This
method connects product meaning, state ownership, controls, and actual use;
it does not prescribe a framework or a universal screen layout.

## Start with the person's objects and task

Describe the task in domain terms before choosing controls. Identify what the
person acts on, what changes, what stays fixed, where the result appears, and
how they recover. A compact example is enough:

```text
Move the photo inside its crop window.
Target: image transform. Fixed: window shape and location.
Feedback: live crop. Finish: one undoable edit. Cancel: restore the start.
```

An image, its crop window, an independent foreground, and the viewport may
overlap on screen while remaining different objects. A message's body,
reasoning, and tool activity may share a conversation while requiring different
semantics and visual weight. Reflect these distinctions in labels, selection,
handles, grouping, and accessibility names; do not make users infer the data
model from a generic “edit” or “drag” command.

Resolve ambiguous nouns against the requested outcome. “Language” may mean
interface locale, authored text, or generated lettering. “Theme” may mean
palette or a different graphic language. A brief object-specific restatement
often resolves the ambiguity without an interview. A new interpretation must
not silently replace the product's central purpose.

## Match each control to a truthful contract

For each consequential action, establish:

| Question | Visible consequence |
| --- | --- |
| Which object and mode? | Selection and nearby context identify the target before action. |
| What can change? | The action name and controls match its actual behavior and range. |
| What else is affected? | Linked/shared changes show their scope before applying. |
| What cannot change here, and why? | Explain the constraint and expose an applicable action; don't fake movement by changing another object. |
| Where is the result? | Show meaningful feedback at the working location, not only a distant toast. |
| How can the person recover? | Provide the product's cancel, undo, retry, back, or reopen behavior. |

Distinguish finite presets from procedural variation. A control that cycles
three layouts should say so; a promised randomizer needs a meaningful variable
space and repeatable comparison. Preserve user-authored content and relationships
within its stated scope. Candidate browsing and choosing a result are different
actions. Make candidates large enough for the differences users must judge.

## Give each state change an owner

Map the relevant layers in the existing implementation; don't introduce a new
store or transaction framework just to match this table.

| Layer | Typical contents | Boundary to verify |
| --- | --- | --- |
| View | Selection, open inspector, zoom/pan, preview playback | Navigation or inspection must not silently rewrite the work. Persist view preferences only as the product intends. |
| In-progress edit | Current typing, slider/drag draft, candidate being compared | Give timely feedback; define when it becomes an accepted change and what cancel restores. |
| Committed work | Authored content, relationships, accepted parameters | Save and undo use meaningful user actions, not incidental renders or every pointer event. |
| Produced result | Rendered/exported/published artifact | Derive from the intended work state; keep workspace affordances out. |

For a continuous gesture, verify begin → live update → finish as well as the
supported cancellation path. A no-op should not create a misleading undo step.
Autosave, explicit Apply, immediate commit, and transactional editing are all
valid when their feedback and recovery match the product. Do not force Apply
onto every input or autosave onto every document.

Inspect both the visible result and what is saved. A preview can look correct
while accidentally adding history, changing a shared object, or resetting
authored geometry. When relationships are linked, test one change that should
propagate and one property that should remain independent.

## Make repeated operation feel continuous

Improve hierarchy through proximity, grouping, meaningful defaults, and
contextual controls while retaining requested creative power. Hiding important
actions or removing functionality is not a substitute for a comprehensible tool.

Try the action at a realistic pace and with real content:

- During text entry, preserve caret, selection, and input composition. In
  mixed-script products, exercise the actual IME/composition path when available;
  programmatic value filling alone does not verify it.
- During a drag, slider change, or live preview, observe feedback latency and
  layout stability. Investigate the relevant cause: rebuilding the inspector,
  invalidating unrelated caches, expensive rendering, or delayed commit events.
  Do not assert a frame-rate improvement from a code change alone.
- Distinguish scrolling, selecting/copying text, moving an object, and panning
  a canvas. Check the gesture transitions affected by the implementation,
  including keyboard/numeric access where the interaction requires it.
- Check the actual current values when reopening a tool. A default “1×” that
  disagrees with the selected object undermines trust even if the slider moves.
- On narrow screens, keep the current object, result, and exit reachable at the
  working scroll position. Short viewport checks do not prove soft-keyboard or
  physical-device behavior; use [platform evidence](platform-evidence.md).

Design focus, selection, editing, error, pending, and disabled states together.
They answer different questions and should not all become the same heavy box.
Use recognizable control shapes unless a custom form materially improves the
task. Verify the active state visually as well as the resting screenshot;
[QA](qa-contract.md) owns the focus visibility and keyboard checks.

## Close the whole requested task path

For an App-wide change, map the requested journeys to their touched surfaces
and states. A polished Home screen does not establish that search, conversation,
editing, library, or return navigation is complete. For a local repair, keep
this map local to its actual blast radius.

Use representative volume and content: a long conversation, many saved items,
long multilingual names, repeated collapsed auxiliary blocks. Repetition can
make a modest single component dominate the screen. Data type can justify a
different presentation; files and links need not become indistinguishable cards.

For products with saved works, distinguish source assets, examples, editable
projects, and exported files. A person should be able to find the claimed work,
open the right version, continue editing, and obtain the actual output through
the supported path. A screenshot in a delivery message or a hidden filesystem
export does not supply that product capability.

Keep evidence separate: inspect discoverability without giving away the click
path; exercise behavior through controls; inspect working-state visual quality;
record owner feedback at its actual scope. No one of these substitutes for the
others. Use [QA](qa-contract.md) for the concrete checks and
[visual works](visual-works.md) when the App creates artifacts.
