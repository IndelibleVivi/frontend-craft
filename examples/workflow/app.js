/* ==========================================================================
   A request, made visible — behavior

   Two independent pieces of state are kept apart on purpose:

     view state : language and active step. It never touches persistence and
                  never resets the note.
     note state : the example, the working draft, and the last stored copy.
                  Only an explicit Save writes to localStorage.

   The editor is authored once in <template id="editor-template"> and cloned
   into a visible slot, so the page never holds a hidden duplicate input. At
   most one editable note exists at a time.

   This is a classic script (no modules) so it runs from file:// and from a
   local http server alike.
   ========================================================================== */

(function () {
  "use strict";

  /* The single storage key this demo is allowed to touch. */
  var KEY = "fc.workflow.demoNote.v1";

  /* The synthetic example. The page shows this until the visitor saves. */
  var EXAMPLE = {
    title: "Studio notes — letterpress proof",
    body: "Proof 3: the registration mark drifts about 2 mm on the fold.\n" +
          "Ink sits evenly on the uncoated sheet. Keep the paper, tighten the trim."
  };

  var root = document.documentElement;
  var liveRegion = document.getElementById("status-live");
  var editorTpl = document.getElementById("editor-template");
  var langToggle = document.getElementById("lang-toggle");
  var stepButtons = Array.prototype.slice.call(document.querySelectorAll("[data-step]"));
  var stepPanels = Array.prototype.slice.call(document.querySelectorAll("[data-step-panel]"));
  var host1 = document.getElementById("host-1");

  var editor = null;       /* the single live .editor element */
  var refs = null;         /* its inner elements */

  var storage = probeStorage();

  /* `saved`  — last copy written to this browser, or null when none exists.
     `draft`  — what the editor currently shows.
     `baseline` — where Discard sends the editor: the stored copy when one
                  exists, otherwise the example note. */
  var saved = storage.available ? readRecord() : null;
  var baseline = saved ? copyOf(saved) : copyOf(EXAMPLE);
  var draft = copyOf(baseline);

  /* == Storage ============================================================
     localStorage can be unavailable (some file:// policies, private windows)
     or refuse a write (quota). Both cases degrade to an honest in-memory
     session instead of a false "saved" claim. */

  function probeStorage() {
    try {
      window.localStorage.getItem(KEY);
    } catch (err) {
      return { available: false, read: function () { return null; },
               write: function () { return false; } };
    }
    return {
      available: true,
      read: function () {
        try { return window.localStorage.getItem(KEY); } catch (err) { return null; }
      },
      write: function (text) {
        try { window.localStorage.setItem(KEY, text); return true; }
        catch (err) { return false; }
      }
    };
  }

  function readRecord() {
    var raw = storage.read();
    if (!raw) return null;
    try {
      var parsed = JSON.parse(raw);
      if (!parsed || typeof parsed.title !== "string" || typeof parsed.body !== "string") {
        return null;
      }
      return {
        title: parsed.title,
        body: parsed.body,
        at: typeof parsed.at === "string" ? parsed.at : ""
      };
    } catch (err) {
      return null;
    }
  }

  function copyOf(record) {
    return { title: record.title, body: record.body };
  }

  function sameNote(a, b) {
    return a.title === b.title && a.body === b.body;
  }

  /* == Copy ==============================================================
     Every dynamic string carries both editions. Only the visitor's own note
     text is ever left untranslated. */

  function isZh() {
    return root.getAttribute("lang") === "zh-CN";
  }

  function t(en, zh) {
    return isZh() ? zh : en;
  }

  function timeText(iso) {
    var date = iso ? new Date(iso) : new Date();
    if (isNaN(date.getTime())) date = new Date();
    try {
      return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    } catch (err) {
      var minutes = date.getMinutes();
      return date.getHours() + ":" + (minutes < 10 ? "0" : "") + minutes;
    }
  }

  /* == Editor construction (exactly once) ================================ */

  function buildEditor() {
    editor = document.importNode(editorTpl.content, true).querySelector(".editor");

    host1.appendChild(editor);

    refs = {
      stateLabel: editor.querySelector("#note-state"),
      stateMeta: editor.querySelector("#note-count"),
      title: editor.querySelector("#note-title"),
      body: editor.querySelector("#note-body"),
      save: editor.querySelector('[data-act="save"]'),
      reopen: editor.querySelector('[data-act="reopen"]'),
      discard: editor.querySelector('[data-act="discard"]')
    };

    refs.title.addEventListener("input", onInput);
    refs.body.addEventListener("input", onInput);
    refs.save.addEventListener("click", saveNote);
    refs.reopen.addEventListener("click", reopenNote);
    refs.discard.addEventListener("click", discardDraft);
  }

  /* == Note state ======================================================== */

  function currentDraft() {
    return { title: refs.title.value, body: refs.body.value };
  }

  function writeDraft(note) {
    refs.title.value = note.title;
    refs.body.value = note.body;
  }

  /* The status line is derived by comparison every time, never asserted. */
  function updateState() {
    var state, label, meta = "";

    if (!storage.available) {
      state = "session";
      label = saved && sameNote(draft, saved)
        ? t("Saved for this page only — reload will lose it", "仅保存到当前页面 —— 刷新后会丢失")
        : t("Unsaved draft — browser storage unavailable", "未保存的草稿 —— 浏览器存储不可用");
    } else if (saved && sameNote(draft, saved)) {
      state = "saved";
      label = t("Saved in this browser", "已保存在本浏览器");
      if (saved.at) meta = timeText(saved.at);
    } else if (!saved && sameNote(draft, EXAMPLE)) {
      state = "example";
      label = t("Example note — not saved yet", "示例笔记 —— 尚未保存");
    } else {
      state = "draft";
      label = saved
        ? t("Draft — differs from the saved note", "草稿 —— 与已保存的笔记不同")
        : t("Draft — not saved yet", "草稿 —— 尚未保存");
    }

    editor.setAttribute("data-state", state);
    refs.stateLabel.textContent = label;
    refs.stateMeta.textContent = meta;
  }

  function updateCount() {
    var total = refs.title.value.length + refs.body.value.length;
    var stamp = storage.available && saved && sameNote(draft, saved) && saved.at
      ? timeText(saved.at) + " · " : "";
    refs.stateMeta.textContent = stamp + t(total + " characters", total + " 个字符");
  }

  function onInput() {
    draft = currentDraft();
    updateState();
    updateCount();
  }

  /* == Actions ===========================================================
     Save is the only path that writes. If the browser refuses the write, the
     note is kept as an in-memory session copy so the work is not lost, and
     the interface says exactly that. */

  function commit(note, at) {
    saved = { title: note.title, body: note.body, at: at };
    baseline = copyOf(note);
    draft = copyOf(note);
  }

  function saveNote() {
    var note = currentDraft();
    var at = new Date().toISOString();

    if (!storage.available) {
      commit(note, at);
      updateState();
      updateCount();
      announce(t("Saved for this session only. It will be lost when the page reloads.",
                 "仅保存到本次会话，刷新页面后会丢失。"));
      return;
    }

    if (storage.write(JSON.stringify({ title: note.title, body: note.body, at: at }))) {
      commit(note, at);
      updateState();
      updateCount();
      announce(t("Note saved in this browser.", "笔记已保存在本浏览器。"));
      return;
    }

    /* Refused write: keep the work in memory and disclose the limit. */
    commit(note, at);
    storage.available = false;
    updateState();
    updateCount();
    announce(t("This browser refused to save. The note is kept for this session only.",
               "浏览器拒绝保存。笔记仅保留在本次会话中。"));
  }

  function reopenNote() {
    /* Read persistence again when it is available, so another tab or a
       previous visit is honoured rather than a stale in-memory cache. */
    var source = storage.available ? readRecord() : saved;
    if (!source) {
      announce(t("No saved note exists yet. Save one first.",
                 "还没有已保存的笔记，请先保存。"));
      return;
    }
    saved = source;
    baseline = copyOf(source);
    draft = copyOf(source);
    writeDraft(draft);
    updateState();
    updateCount();
    announce(storage.available
      ? t("Reopened the saved note.", "已重新打开保存的笔记。")
      : t("Reopened the copy kept for this session.", "已重新打开本次会话保留的副本。"));
  }

  function discardDraft() {
    draft = copyOf(baseline);
    writeDraft(draft);
    updateState();
    updateCount();
    announce(saved
      ? t("Draft discarded. The editor shows the last saved copy again.",
          "已放弃草稿，编辑器重新显示最近保存的副本。")
      : t("Draft discarded. The editor shows the example note again.",
          "已放弃草稿，编辑器重新显示示例笔记。"));
  }

  function announce(message) {
    if (!liveRegion) return;
    liveRegion.textContent = "";
    /* Re-set on a fresh task so a repeated message still announces. */
    window.setTimeout(function () { liveRegion.textContent = message; }, 30);
  }

  /* == Step navigation ===================================================
     Switching steps only changes visibility. It never rewrites the note. */

  function setStep(step, options) {
    if (step < 1 || step > 3) return;

    stepPanels.forEach(function (panel) {
      panel.hidden = Number(panel.getAttribute("data-step-panel")) !== step;
    });
    stepButtons.forEach(function (button) {
      var on = Number(button.getAttribute("data-step")) === step;
      button.setAttribute("aria-selected", on ? "true" : "false");
      button.tabIndex = on ? 0 : -1;
    });

    var opts = options || {};
    if (opts.focusPanel === false) return;
    var panel = document.getElementById("step-" + step);
    if (panel) panel.focus({ preventScroll: true });
  }

  function wireTabs() {
    stepButtons.forEach(function (button) {
      button.addEventListener("click", function () {
        setStep(Number(button.getAttribute("data-step")));
      });
      /* Roving tablist: arrows and Home/End move the selection. */
      button.addEventListener("keydown", function (event) {
        var deltas = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 };
        var move = deltas[event.key];
        var home = event.key === "Home";
        var end = event.key === "End";
        if (!move && !home && !end) return;
        event.preventDefault();
        var next = home ? 1 : end ? 3 : Number(button.getAttribute("data-step")) + move;
        next = Math.min(3, Math.max(1, next));
        var target = document.getElementById("tab-" + next);
        if (target) {
          setStep(next, { focusPanel: false });
          target.focus();
        }
      });
    });
  }

  /* == Language ==========================================================
     The switch changes <html lang> only. It never reads or writes the note,
     so a draft in progress survives every switch. */

  function setLanguage(code) {
    var zh = code === "zh-CN";
    liveRegion.textContent = "";
    root.setAttribute("lang", zh ? "zh-CN" : "en");
    langToggle.setAttribute("aria-pressed", zh ? "true" : "false");
    langToggle.setAttribute(
      "aria-label",
      zh ? "Switch the interface to English" : "切换到中文界面"
    );
    document.getElementById("stepper").setAttribute("aria-label", t("Walkthrough steps", "演示步骤"));
    editor.querySelector(".editor__bar").setAttribute("aria-label", t("Note actions", "笔记操作"));
    editor.querySelector(".help").setAttribute("aria-label", t("What the actions do", "操作说明"));
    updateState();
    updateCount();
  }

  function wireLanguage() {
    langToggle.addEventListener("click", function () {
      setLanguage(isZh() ? "en" : "zh-CN");
    });
  }

  /* == Start ============================================================= */

  function init() {
    buildEditor();
    draft = copyOf(baseline);
    writeDraft(draft);
    wireTabs();
    wireLanguage();
    setLanguage("en");
    setStep(1, { focusPanel: false });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
