# A request, made visible

[Repository README](../../README.md) · [中文说明](#中文说明) ·
[Other examples](../README.md) · [License map](../../LICENSING.md)

A small, self-contained Frontend Craft walkthrough. It shows one concrete
interface request, the inline help it produced, and the working note editor
that resulted — so the change is something you can use, not just read about.

The example, the note text, and the "before" picture are **synthetic and
manually authored** for this repository. Nothing here is a recording of an
automated Frontend Craft run, a benchmark, or a quality score.

## Open it

From the repository root:

```bash
python3 -m http.server 4182 --bind 127.0.0.1
```

Then open <http://127.0.0.1:4182/examples/workflow/>.

Directly opening `examples/workflow/index.html` depends on your browser's
`file://` policy. The loopback HTTP route above is the verified preview path.
The page is plain HTML, CSS, and JavaScript with no build step, no
dependencies, no bundled or downloaded fonts, no external assets, and no
external network requests.

## What the walkthrough shows

Three steps sit above one working editor, and the editor stays visible
throughout.

1. **The brief** — the request is spelled out simply. The request used for
   this example is:

   > “Make essential toolbar help visible on narrow screens. Preserve the note
   > text, controls and artwork.”

   It names the object (the editor's toolbar), the condition (narrow screens,
   without depending on hover), and the boundary (keep the note text, controls,
   and artwork).

2. **The change** — the previous toolbar and the delivered one side by side.
   The left picture is a labelled illustration, not a screenshot: help there
   existed only on hover. The right side is the live editor.

3. **Try it** — the editor at full size, where you do the work below.

The editor is authored once and stays mounted beside the story on wide screens
and below it on narrow screens. Switching steps never creates a second copy.

## What you can do

Everything happens in the editor. Its toolbar holds the three actions below; a
recovery strip appears only when a refused save left a page-only copy worth
getting back.

| Action | What it actually does |
| --- | --- |
| **Save** | Writes the current title and body to this browser. A real write settles the note and clears any page-only recovery copy. |
| **Reopen** | Loads the last stored copy back into the editor — the way to check what was really kept. |
| **Discard draft** | Returns the editor to the last saved copy (or the page-only copy when that is the last confirmed one). Nothing is written and nothing is deleted; before the first save, restores the example. |
| **Restore page copy** | Shown only when a refused save left a page-only copy that differs from what the editor shows. Puts that copy back into the editor and writes nothing. |

A status line beside the fields always states the truth, derived by comparing
the editor against what is actually stored:

- **Example note — not saved yet** — the page just loaded and nothing is stored.
- **Draft — not saved yet** / **Draft — differs from the saved note** — you have
  changed something that is not stored.
- **Saved in this browser** — the editor matches the stored copy; the time shown
  is when it was written.
- **Unsaved draft — browser storage unavailable** / **Saved for this page only —
  reload will lose it** — persistence is unavailable, so the note lives in this
  page only.
- **Couldn't read this browser's storage — …** — a read of this browser's
  storage failed, so whether anything is stored is *unknown*. Your draft and the
  last confirmed copy are kept; press **Reopen** again to retry the real storage.
- **The saved note could not be read — try Save to replace it** — a value is
  stored but is not a note this demo can use.

A failed read is never treated as evidence that nothing is stored. **Reopen**
always retries real storage; when it returns a usable note, that note is loaded.

A refused write is kept as an independent page-only copy, so a later read cannot
erase it. Suppose this browser already holds a note, you edit it into a new
version, and the write is refused: a later **Reopen** loads the older saved note,
while the refused version stays reachable through **Restore page copy**.
Identical copies raise no conflict, and a successful **Save** is the one action
that settles the note and ends the recovery.

There is no background autosave: a reload shows exactly what was last saved.
Actions are announced to screen readers, and the editor is
fully keyboard operable.

## Storage boundary

Only one key is used, and only when you press **Save**:

```text
fc.workflow.demoNote.v1
```

Its value is a small JSON object with the note's `title`, `body`, and the
`at` timestamp of the write. The demo never writes anything else, never reads
other keys, and never deletes your note. Opening, refreshing, or closing the
page does not remove a previously saved note.

If the browser blocks local storage (some `file://` policies and private
windows) or refuses a write, the demo does not pretend to save. It keeps your
note in memory for the current page, says so plainly, and shows
a session-only status. Reloading after that will not restore the note — which
is exactly what the status says.

Two different failures are kept apart, because they mean different things:

- **A refused write** (quota, blocked storage) retains a page-only copy, held
  apart from the browser's record. **Reopen** loads a usable browser-saved note
  if one is available; otherwise it brings back the page-held copy and says it
  is session-only. This works even when reads succeed but storage is empty after
  a refused write. When the browser does hold a different note, that note loads
  while the page-only copy stays available behind **Restore page copy**.
- **A failed read without a page-only save** leaves the draft and last confirmed
  copy untouched. The status says storage could not be read; a later
  **Reopen** can retry. Failure does not establish whether a note is stored.

If the store is confirmed empty (for example another tab cleared it), **Reopen**
reports that plainly without erasing the draft or the last confirmed copy.
**Discard draft** returns to that copy, and the status makes clear it is no
longer confirmed in browser storage.

The recovery state is shown in real browser captures: [English, wide](../../docs/visuals/workflow-recovery.en.png) and [Chinese, narrow](../../docs/visuals/workflow-recovery.zh-CN.png). The note text is synthetic; interface language switching preserves it.

## Files

`index.html`, `styles.css`, and `app.js` in this directory are the single
source of truth for the demo. There is no second implementation and no
generated copy. The interface switch at the top right toggles every label,
heading, help sentence, status message, and announced message between English
and Chinese; it never alters your note text. Previews elsewhere in the
repository are captures of this page and should be refreshed after any visible
change.

The demo's storage and state behavior is covered by an offline regression check
that runs the real `app.js`. Run from the repository root with Node.js:

```bash
node tests/test_workflow_app.js
```

It exits non-zero when a stored/absent/failed-read distinction is broken. It
drives the app's logic directly, so it does **not** render the page or prove
visual, focus, or screen-reader behavior.

## Scope and limits

- **Synthetic and manual.** The scenario, the note, and the "before"
  illustration were written by hand for this repository.
- **No model calls.** The page runs entirely in your browser. No Frontend Craft
  method executes here, and nothing is sent anywhere.
- **Not a quality claim.** The demo illustrates a workflow; it does not measure
  design quality, agent performance, or user satisfaction.
- **Local browser verification is separate.** Package validity and passing
  repository tests do not establish that this page renders or behaves correctly
  in your browser.

## 中文说明

这是一个自带完整、可独立运行的 Frontend Craft 走查示例：展示一个具体的界面请求、它带来的行内帮助，以及最终可用的笔记编辑器 —— 让你能真正上手使用，而不只是阅读。

示例本身、笔记内容以及“改动前”的画面都是为本仓库**人工编写的合成内容**，不是自动化 FC 执行的录像，也不是评测或质量评分。

**打开方式**：在仓库根目录运行 `python3 -m http.server 4182 --bind 127.0.0.1`，然后访问 <http://127.0.0.1:4182/examples/workflow/>。直接打开 `examples/workflow/index.html` 取决于浏览器的 `file://` 策略；已经验证的是上述本机 HTTP 预览路径。页面只用原生 HTML、CSS 和 JavaScript，无需构建、无依赖、无自带或下载字体、无外部资源，也不发起外部网络请求。

**可以做什么**：编辑器的工具栏自带三个操作 —— **保存**（把标题和正文写入本浏览器；真正写入即确认本次保存，并清除页内恢复副本）、**重新打开**（把最近保存的副本读回编辑器）、**放弃草稿**（退回最近保存的副本；当最近确认的就是页内副本时，则退回该副本；不写入也不删除任何内容）。当一次被拒绝的保存留下了与编辑器当前内容不同的页内副本时，会出现**恢复页内副本**操作，它把那份副本放回编辑器，不写入任何内容。字段旁的状态行会如实显示当前是示例、草稿、已保存，还是仅限本次会话。

**存储边界**：只使用一个键 `fc.workflow.demoNote.v1`，且只在你点击“保存”时写入；值为包含 `title`、`body` 和写入时间 `at` 的小型 JSON。示例不会读写其他键，也不会删除你的笔记。若浏览器阻止本地存储（部分 `file://` 策略与隐私窗口）或拒绝写入，示例不会假装保存成功：它把笔记保留在当前页面内存中，明确显示“仅限本次会话”，此时刷新页面不会恢复笔记 —— 与状态说明完全一致。

两种失败分别处理：**写入被拒绝**（配额、存储被阻止）时保留页面内副本，它与浏览器里的记录分开保存。“重新打开”始终重试真实存储；有可用的浏览器已存笔记就读取它，否则取回页面内副本并注明“仅限本次会话”，包括写入失败后仍可读取、但存储为空的情况。当浏览器里确实存着另一份笔记时，读取的是那份笔记，而页内副本仍可通过“恢复页内副本”取回；两份副本相同则不会制造无意义冲突。真正的“保存”会确认本次保存，并结束这次恢复。**没有页面内保存副本时的读取失败**会保留草稿与最近确认的副本，并说明无法读取存储；下次“重新打开”仍可重试。读取失败不能证明没有记录。若确认存储为空（例如其他标签页已清除），示例会如实说明，但仍保留草稿和最近确认的副本；“放弃草稿”可返回该副本，状态不会把它误称为仍在浏览器存储中。

**恢复状态截图**：[英文宽屏](../../docs/visuals/workflow-recovery.en.png)与[中文窄屏](../../docs/visuals/workflow-recovery.zh-CN.png)均来自真实浏览器。笔记为合成内容，切换界面语言时保持原文。

**文件**：本目录下的 `index.html`、`styles.css`、`app.js` 是演示的唯一权威来源，不存在第二份实现或生成副本。右上角的界面开关会在中英文之间切换所有标签、标题、帮助句、状态与朗读文案，但不会改动你的笔记正文。演示的存储与状态行为有一项离线回归检查，直接运行真实的 `app.js`：在仓库根目录使用 Node.js 执行 `node tests/test_workflow_app.js`；当“已存储 / 为空 / 读取失败”的区分被破坏时，它以非零状态码退出。它直接驱动应用逻辑，因此**不会**渲染页面，也不证明视觉、焦点或屏幕阅读器行为。

**范围与限制**：场景与插图均为人工编写的合成内容；页面不进行模型调用，也不把任何内容发送出去；它演示的是流程，不构成设计质量、智能体表现或用户满意度的证明。浏览器内的真实验证与仓库测试结论是相互独立的。
