#!/usr/bin/env node
/*
 * Regression checks for examples/workflow/app.js — the real demo source.
 *
 * The demo is a classic browser script with no bundler. These dependency-free
 * checks run the *actual* file body through
 * Node's `vm`, with a small hand-written double standing in for the DOM the
 * demo talks to and for `localStorage`.
 *
 * What that proves: the demo's real storage/state logic, executed verbatim.
 * What that does NOT prove: rendering, CSS, focus order, screen-reader
 * output, or that a browser parses the page — see the note at the bottom.
 *
 * Run:  node tests/test_workflow_app.js
 */
"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");

const APP = path.join(__dirname, "..", "examples", "workflow", "app.js");
const KEY = "fc.workflow.demoNote.v1";

const EXAMPLE_TITLE = "Studio notes — letterpress proof";

/* --- a minimal element stand-in ------------------------------------------ */

function el(tag, attrs = {}) {
  const node = {
    tagName: tag.toUpperCase(),
    children: [],
    _attrs: { ...attrs },
    value: attrs.value ?? "",
    textContent: "",
    hidden: false,
    listeners: {},
    setAttribute(k, v) { this._attrs[k] = String(v); },
    getAttribute(k) { return Object.prototype.hasOwnProperty.call(this._attrs, k) ? this._attrs[k] : null; },
    addEventListener(type, fn) { (this.listeners[type] = this.listeners[type] || []).push(fn); },
    appendChild(child) { this.children.push(child); return child; },
    focus() {},
    querySelector() { return null; },
    querySelectorAll() { return []; },
    dispatch(type, extra = {}) {
      (this.listeners[type] || []).forEach((fn) =>
        fn.call(this, { target: this, preventDefault() {}, ...extra }));
    },
  };
  return node;
}

/* --- a scripted localStorage double ------------------------------------- *
 * `plan(kind, callIndex)` decides, per call, one of:
 *   "ok" | "absent" | "throw"   (reads)   — "absent" returns null
 *   "ok" | "throw"              (writes)
 * Call order is recorded so tests can assert that later calls really reached
 * the store again (the "no permanent fallback" promise).
 */
function makeStorage(records = {}, plan = () => "ok") {
  return {
    calls: [],
    records: new Map(Object.entries(records)),
    getItem(k) {
      const mode = plan("getItem", this.calls.length);
      this.calls.push(["getItem", k, mode]);
      if (mode === "throw") throw new Error("SecurityError: storage read blocked");
      if (mode === "absent") return null;
      return this.records.has(k) ? this.records.get(k) : null;
    },
    setItem(k, v) {
      const mode = plan("setItem", this.calls.length);
      this.calls.push(["setItem", k, mode]);
      if (mode === "throw") throw new Error("QuotaExceededError");
      this.records.set(k, v);
    },
  };
}

/* --- build the DOM the demo expects and run the real source -------------- */

function makeEnv({ records = {}, plan } = {}) {
  const live = el("p");
  const langToggle = el("button");
  const stepper = el("ol");
  const host = el("div");
  const panels = [1, 2, 3].map((i) => { const p = el("section"); p.setAttribute("data-step-panel", String(i)); return p; });
  const tabs = [1, 2, 3].map((i) => { const b = el("button"); b.setAttribute("data-step", String(i)); return b; });
  const rootEl = el("html");

  const title = el("input");
  const body = el("textarea");
  const stateLabel = el("span");
  const stateMeta = el("span");
  const save = el("button");
  const reopen = el("button");
  const discard = el("button");
  const editor = el("article");
  const bar = el("div");
  const help = el("ul");
  editor.querySelector = (sel) => ({
    "#note-state": stateLabel,
    "#note-count": stateMeta,
    "#note-title": title,
    "#note-body": body,
    '[data-act="save"]': save,
    '[data-act="reopen"]': reopen,
    '[data-act="discard"]': discard,
    ".editor__bar": bar,
    ".help": help,
  })[sel] ?? null;

  const template = { content: { childNodes: [editor] } };
  const byId = {
    "status-live": live,
    "lang-toggle": langToggle,
    "editor-template": template,
    "host-1": host,
    stepper,
    "step-1": panels[0],
    "step-2": panels[1],
    "step-3": panels[2],
    "tab-1": tabs[0],
    "tab-2": tabs[1],
    "tab-3": tabs[2],
  };

  const doc = {
    readyState: "complete",
    documentElement: rootEl,
    listeners: {},
    addEventListener(t, f) { (this.listeners[t] = this.listeners[t] || []).push(f); },
    getElementById: (id) => byId[id] ?? null,
    querySelectorAll: (sel) =>
      sel === "[data-step]" ? tabs : sel === "[data-step-panel]" ? panels : [],
    importNode: () => ({ querySelector: () => editor }),
    createElement: el,
  };

  const storage = makeStorage(records, plan);
  const win = {
    localStorage: storage,
    setTimeout: (fn) => { fn(); return 0; },
    clearTimeout: () => {},
  };

  const ctx = {
    window: win,
    document: doc,
    console,
    JSON, Date, isNaN, Number, Math, Array, Object, String,
    setTimeout: win.setTimeout,
  };
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync(APP, "utf8"), ctx, { filename: APP });

  return {
    storage, doc, win, rootEl,
    title, body, stateLabel, stateMeta, save, reopen, discard, live, langToggle,
    setTitle(v) { title.value = v; title.dispatch("input"); },
    setBody(v) { body.value = v; body.dispatch("input"); },
    clickReopen() { reopen.dispatch("click"); },
    clickSave() { save.dispatch("click"); },
    clickDiscard() { discard.dispatch("click"); },
    clickLang() { langToggle.dispatch("click"); },
  };
}

const record = (title, body, at = "2026-09-01T10:00:00.000Z") => JSON.stringify({ title, body, at });

/* --- tiny assertion helpers ---------------------------------------------- */

const checks = [];
function check(name, fn) { checks.push({ name, fn }); }
function eq(actual, expected, msg) {
  const a = JSON.stringify(actual);
  const b = JSON.stringify(expected);
  if (a !== b) throw new Error(`${msg || "mismatch"}: expected ${b}, got ${a}`);
}
function ok(cond, msg) { if (!cond) throw new Error(msg || "expected truthy"); }
function notEq(a, b, msg) { if (a === b) throw new Error(msg || `expected different values, both "${a}"`); }

/* ========================================================================
 * 1. The reported scenario: a confirmed save, a draft, then Reopen fails.
 * ====================================================================== */

check("failed Reopen read is not reported as a confirmed absence", () => {
  let denyRead = false;
  const env = makeEnv({
    records: { [KEY]: record("Saved title", "Saved body") },
    plan: kind => kind === "getItem" && denyRead ? "throw" : "ok",
  });
  eq(env.stateLabel.textContent, "Saved in this browser", "load should show the stored copy");

  env.setTitle("Draft title");
  eq(env.title.value, "Draft title", "draft edit applies");
  eq(env.stateLabel.textContent, "Draft — differs from the saved note", "draft is distinguished from saved");

  denyRead = true;
  env.clickReopen();
  notEq(env.live.textContent, "No saved note exists yet. Save one first.",
        "a failed read must not be announced as a confirmed absence");
  ok(/Couldn't read/.test(env.live.textContent), "failure should be stated truthfully");
  ok(!/^Saved in this browser$/.test(env.stateLabel.textContent),
     "a failed read must not read as fully saved");
});

check("failed Reopen preserves the draft and the last confirmed copy", () => {
  let denyRead = false;
  const env = makeEnv({
    records: { [KEY]: record("Saved title", "Saved body") },
    plan: kind => kind === "getItem" && denyRead ? "throw" : "ok",
  });
  const initialReads = env.storage.calls.length;
  env.setTitle("Draft title");
  env.setBody("Draft body");
  denyRead = true;
  env.clickReopen();

  eq(env.title.value, "Draft title", "draft title must survive a failed read");
  eq(env.body.value, "Draft body", "draft body must survive a failed read");

  // Discard still returns to the last confirmed copy, not the example.
  env.clickDiscard();
  eq(env.title.value, "Saved title", "discard returns to the last confirmed copy");
  eq(env.body.value, "Saved body", "discard returns the last confirmed body");

  // After recovery, Reopen reads real storage again — nothing was stranded.
  env.storage.records.set(KEY, record("Recovered title", "Recovered body"));
  denyRead = false;
  env.clickReopen();
  eq(env.title.value, "Recovered title", "recovery must re-read storage");
  eq(env.body.value, "Recovered body", "recovery must re-read storage");
  const reads = env.storage.calls.filter((c) => c[0] === "getItem");
  eq(reads.length, initialReads + 2, "each Reopen reaches the real store");
  eq(reads[reads.length - 1][2], "ok", "the retry actually reached the store");
});

check("a failed read never sticks later reads in a fallback", () => {
  let denyRead = false;
  const env = makeEnv({
    records: { [KEY]: record("A", "body A") },
    plan: kind => kind === "getItem" && denyRead ? "throw" : "ok",
  });
  denyRead = true;
  env.clickReopen();
  env.storage.records.set(KEY, record("B", "body B"));
  denyRead = false;
  env.clickReopen();
  eq(env.title.value, "B", "a later successful read must win over the in-memory copy");
});

/* ========================================================================
 * 2. Confirmed absence stays distinguishable from failure.
 * ====================================================================== */

check("confirmed absence is still announced as absence", () => {
  const env = makeEnv({ records: {}, plan: () => "ok" });
  eq(env.stateLabel.textContent, "Example note — not saved yet", "fresh load shows the example");
  env.clickReopen();
  eq(env.live.textContent, "No saved note exists yet. Save one first.",
    "an empty store is honestly reported as empty");
});

check("a confirmed-absent read retains recovery without claiming browser storage", () => {
  // Load a real record, then have the store genuinely report nothing on Reopen
  // (another tab cleared it). The retained copy must not keep the status at
  // "Saved in this browser" while storage says otherwise.
  const env = makeEnv({
    records: { [KEY]: record("Saved title", "Saved body") },
  });
  eq(env.stateLabel.textContent, "Saved in this browser", "load reports the stored copy");

  env.storage.records.delete(KEY);
  env.clickReopen();
  ok(/No saved note|No note is currently stored/.test(env.live.textContent),
     "a confirmed absence is announced plainly");
  notEq(env.stateLabel.textContent, "Saved in this browser",
        "a confirmed-absent read must not still claim the note is saved");
  eq(env.title.value, "Saved title",
     "the draft in the editor is preserved, only the status is corrected");
  env.setTitle("Later draft");
  env.clickDiscard();
  eq(env.title.value, "Saved title", "absence must not erase the local recovery copy");
  notEq(env.stateLabel.textContent, "Saved in this browser", "discard does not restore a false storage claim");
});

check("quota refusal with readable empty storage preserves session-only reopen", () => {
  const env = makeEnv({plan: kind => kind === "setItem" ? "throw" : "ok"});
  env.setTitle("Page-held title");
  env.setBody("Page-held body");
  env.clickSave();
  env.setTitle("Unsaved draft");
  env.clickReopen();
  eq(env.title.value, "Page-held title", "an empty browser store does not erase the session copy");
  eq(env.body.value, "Page-held body", "the session body is retained");
  eq(env.stateLabel.textContent, "Saved for this page only — reload will lose it", "no persistence claim");
  env.setTitle("Another draft");
  env.clickDiscard();
  eq(env.title.value, "Page-held title", "the session baseline remains usable");
});

check("a session-only copy stays reopenable while storage stays blocked", () => {
  // Startup read fails, the write is refused, then the draft is edited and
  // Reopen is pressed with storage still inaccessible. The page-held copy must
  // come back and the status must stay truthfully session-only.
  const env = makeEnv({ records: {}, plan: () => "throw" });
  env.setTitle("Session title");
  env.setBody("Session body");
  env.clickSave();
  eq(env.stateLabel.textContent, "Saved for this page only — reload will lose it",
     "a refused write is session-only");

  env.setTitle("Session title edited");
  eq(env.stateLabel.textContent, "Unsaved draft — browser storage unavailable",
     "editing a session copy reads as an unsaved draft");

  env.clickReopen();
  eq(env.title.value, "Session title", "Reopen brings back the page-held copy");
  eq(env.body.value, "Session body", "Reopen restores the page-held body");
  eq(env.live.textContent, "Reopened the copy kept for this session.",
     "the session-only reopen is stated plainly");
  eq(env.stateLabel.textContent, "Saved for this page only — reload will lose it",
     "the status stays session-only, not a storage-failure message");
  notEq(env.live.textContent,
        "Couldn't read this browser's storage. Your note and the last confirmed copy are unchanged; try Reopen again.",
        "a page-held copy must not be reported as a failed read");
});

check("a transient read failure does not become a permanent session copy", () => {
  // A genuine persisted copy, one transient read failure, then recovery: the
  // session-copy shortcut must NOT swallow the recovered stored record.
  let denyRead = false;
  const env = makeEnv({
    records: { [KEY]: record("Stored", "Stored body") },
    plan: kind => kind === "getItem" && denyRead ? "throw" : "ok",
  });
  env.setTitle("In progress");
  denyRead = true;
  env.clickReopen();
  ok(!/^Saved for this page only/.test(env.stateLabel.textContent),
     "a failed read on a persisted copy is not session-only");
  eq(env.title.value, "In progress", "the draft survives the transient failure");

  env.storage.records.set(KEY, record("Recovered", "Recovered body"));
  denyRead = false;
  env.clickReopen();
  eq(env.title.value, "Recovered", "the real recovered record wins");
  eq(env.stateLabel.textContent, "Saved in this browser", "recovery returns to the saved status");
});

check("startup read failure is honest and does not fake the example", () => {
  const env = makeEnv({
    records: { [KEY]: record("Stored", "Stored body") },
    plan: (kind) => (kind === "getItem" ? "throw" : "ok"),
  });
  ok(/storage/i.test(env.stateLabel.textContent), "startup read failure must be disclosed");
  notEq(env.stateLabel.textContent, "Saved in this browser",
        "must not claim the stored copy was read");
  notEq(env.stateLabel.textContent, "Example note — not saved yet",
        "must not silently claim nothing is stored when the read failed");
});

/* ========================================================================
 * 3. Write failure and read failure are independent.
 * ====================================================================== */

check("a blocked write falls back to a session copy, truthfully", () => {
  const env = makeEnv({ records: {}, plan: (kind) => (kind === "setItem" ? "throw" : "ok") });
  env.setTitle("Session title");
  env.clickSave();
  ok(/refused to save|session/i.test(env.live.textContent), "blocked write must be disclosed");
  eq(env.stateLabel.textContent,
     "Saved for this page only — reload will lose it",
     "session-only save has its own status");
  eq(env.storage.records.size, 0, "a blocked write must not add a record");
});

check("a blocked write does not disable later reads of real storage", () => {
  const env = makeEnv({
    records: { [KEY]: record("Stored", "Stored body") },
    plan: (kind) => (kind === "setItem" ? "throw" : "ok"),
  });
  const initialReads = env.storage.calls.length;
  env.setTitle("Session title");
  env.clickSave();                  // write refused -> session copy
  env.clickReopen();                // must still read the real store
  const reads = env.storage.calls.filter((c) => c[0] === "getItem");
  eq(reads.length, initialReads + 1, "Reopen must read after a refused write");
  eq(reads[reads.length - 1][2], "ok", "the read reached the real store");
  eq(env.title.value, "Stored", "the real stored copy is what reopens");
});

check("save still writes to real storage after a failed read", () => {
  let denyRead = false;
  const env = makeEnv({
    records: { [KEY]: record("Stored", "Stored body") },
    plan: kind => kind === "getItem" && denyRead ? "throw" : "ok",
  });
  denyRead = true;
  env.clickReopen();                // read throws
  env.setTitle("New save");
  env.clickSave();                  // write must reach real storage
  const stored = JSON.parse(env.storage.records.get(KEY));
  eq(stored.title, "New save", "the new title is stored");
  eq(stored.body, "Stored body", "the untouched body is preserved on write");
  ok(typeof stored.at === "string" && stored.at.length > 0, "a timestamp is stored");
  eq(env.live.textContent, "Note saved in this browser.", "a real write is announced as saved");
});

/* ========================================================================
 * 4. Core promises: language, discard, save/reopen round trip.
 * ====================================================================== */

check("language switching never alters note text", () => {
  const env = makeEnv({ records: {}, plan: () => "ok" });
  env.setTitle("My title");
  env.setBody("My body");
  const before = { t: env.title.value, b: env.body.value };
  env.clickLang();
  eq(env.rootEl.getAttribute("lang"), "zh-CN", "switch goes to Chinese");
  eq({ t: env.title.value, b: env.body.value }, before, "note text is untouched by the switch");
  ok(/[\u4e00-\u9fff]/.test(env.stateLabel.textContent), "the status label is localized");
  env.clickLang();
  eq(env.rootEl.getAttribute("lang"), "en", "switch goes back to English");
  eq({ t: env.title.value, b: env.body.value }, before, "note text is untouched on the way back");
});

check("Discard writes nothing", () => {
  const env = makeEnv({ records: {}, plan: () => "ok" });
  env.setTitle("Draft");
  const before = env.storage.calls.length;
  env.clickDiscard();
  eq(env.storage.calls.length, before, "Discard must not call storage at all");
  eq(env.title.value, EXAMPLE_TITLE, "Discard restores the example before any save");
});

check("save then reopen round-trips the note and its timestamp", () => {
  const env = makeEnv({ records: {}, plan: () => "ok" });
  env.setTitle("Round trip");
  env.setBody("Round trip body");
  env.clickSave();
  eq(env.live.textContent, "Note saved in this browser.", "save is announced");
  env.setTitle("Unsaved change");
  env.clickReopen();
  eq(env.title.value, "Round trip", "Reopen restores the saved title");
  eq(env.body.value, "Round trip body", "Reopen restores the saved body");
  eq(env.live.textContent, "Reopened the saved note.", "Reopen is announced");
  ok(/^\d{1,2}:\d{2}(\s?[AP]M)? · /.test(env.stateMeta.textContent),
     "the saved timestamp is shown: " + env.stateMeta.textContent);
});

check("a malformed stored record is not mistaken for a failed read", () => {
  const env = makeEnv({ records: { [KEY]: "{ not json" }, plan: () => "ok" });
  // Parsing failed, but the read itself succeeded: the value is unusable. That
  // is its own fact — not "nothing is stored", not "the read failed".
  ok(!/Couldn't read/.test(env.stateLabel.textContent),
     "a parse failure must not be reported as a read failure");
  eq(env.stateLabel.textContent,
     "The saved note could not be read — try Save to replace it",
     "an unparsable record gets its own honest status");
  env.clickReopen();
  ok(!/Couldn't read this browser's storage/.test(env.live.textContent),
     "a parse failure is not announced as a read failure");
  ok(/couldn't be read/i.test(env.live.textContent),
     "a parse failure is announced truthfully: " + env.live.textContent);
  // Saving replaces the unusable copy with a real one.
  env.setTitle("Replacement");
  env.clickSave();
  eq(env.live.textContent, "Note saved in this browser.", "Save replaces the unusable copy");
});

/* --- run ----------------------------------------------------------------- */

let failed = 0;
for (const { name, fn } of checks) {
  try {
    fn();
    console.log(`ok   ${name}`);
  } catch (err) {
    failed += 1;
    console.log(`FAIL ${name}\n     ${err.message}`);
  }
}
console.log(`\n${checks.length - failed}/${checks.length} checks passed`);

/* Limits of this harness (kept with the test on purpose):
 * - This executes the app's logic against a hand-written double. It does not
 *   render, apply CSS, lay out, or run a browser event loop, so it cannot
 *   prove visual, focus, or screen-reader behavior. The demo README says the
 *   same thing about repository tests and browser verification.
 * - The double implements only the DOM surface app.js actually uses. If the
 *   app grows new DOM calls, extend the double rather than weakening a check.
 */
if (typeof process !== "undefined") process.exitCode = failed ? 1 : 0;
