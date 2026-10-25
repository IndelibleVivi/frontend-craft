import {
  MAX_IMPORT_TEXT,
  currentIndex,
  currentTrack,
  entry,
  initial,
  insert,
  moveUpcoming,
  nextIndex,
  restore,
  trackById,
  type ImportMode,
  type Saved,
  type Mode,
} from "./domain";
import { mergeLibrary, previewImport } from "./transfer";

export const STORAGE_KEY = "fc.side-a.v1";
export type PlayerSnapshot = {
  saved: Saved;
  status: "idle" | "loading" | "playing" | "paused" | "error";
  error: string | null;
  storage: "ok" | "write" | "read" | "damaged" | "repaired";
  raw: string | null;
  volumeSupported: boolean;
};
export class Player {
  audio: HTMLAudioElement;
  private listeners = new Set<() => void>();
  private snapshot: PlayerSnapshot;
  private request = 0;
  private pendingSeek: number | null = null;
  private lastSave = 0;
  private expectedSource = "";
  private wantPlay = false;
  private blockedSave = false;
  constructor(
    audio: HTMLAudioElement,
    private storage: Pick<Storage, "getItem" | "setItem" | "removeItem">,
  ) {
    this.audio = audio;
    let saved = initial(),
      issue: PlayerSnapshot["storage"] = "ok",
      raw: string | null = null;
    try {
      raw = storage.getItem(STORAGE_KEY);
      if (raw) {
        try {
          const result = restore(raw);
          saved = result.value;
          issue = result.repaired ? "repaired" : "ok";
        } catch {
          issue = "damaged";
        }
      }
    } catch {
      issue = "read";
    }
    this.blockedSave =
      issue === "damaged" || issue === "read" || issue === "repaired";
    audio.preload = "metadata";
    audio.volume = saved.volume;
    this.snapshot = {
      saved,
      status: saved.currentId ? "paused" : "idle",
      error: null,
      storage: issue,
      raw,
      volumeSupported: Math.abs(audio.volume - saved.volume) < 0.01,
    };
    audio.addEventListener("loadedmetadata", () => {
      if (!this.isCurrent()) return;
      if (this.pendingSeek !== null) {
        audio.currentTime = Math.min(
          this.pendingSeek,
          Number.isFinite(audio.duration) ? audio.duration : this.pendingSeek,
        );
        this.pendingSeek = null;
      }
    });
    audio.addEventListener("playing", () => {
      if (this.isCurrent() && this.wantPlay)
        this.emit({ status: "playing", error: null });
    });
    audio.addEventListener("waiting", () => {
      if (this.isCurrent() && this.wantPlay) this.emit({ status: "loading" });
    });
    audio.addEventListener("pause", () => {
      if (!this.wantPlay && this.snapshot.status !== "error")
        this.emit({
          status: currentTrack(this.snapshot.saved) ? "paused" : "idle",
        });
    });
    audio.addEventListener("error", () => {
      if (this.isCurrent()) {
        this.wantPlay = false;
        this.emit({ status: "error", error: "media" });
      }
    });
    audio.addEventListener("timeupdate", () => {
      if (!this.isCurrent() || this.pendingSeek !== null) return;
      this.emit({
        saved: { ...this.snapshot.saved, position: audio.currentTime },
      });
      if (Date.now() - this.lastSave > 2500) this.persist();
    });
    audio.addEventListener("ended", () => {
      if (this.isCurrent()) this.next(true);
    });
    if (saved.currentId) this.load();
  }
  subscribe = (fn: () => void) => {
    this.listeners.add(fn);
    return () => {
      this.listeners.delete(fn);
    };
  };
  getSnapshot = () => this.snapshot;
  private emit(patch: Partial<PlayerSnapshot>) {
    this.snapshot = { ...this.snapshot, ...patch };
    this.listeners.forEach((fn) => fn());
  }
  update(patch: Partial<Saved>) {
    this.emit({ saved: { ...this.snapshot.saved, ...patch } });
    this.persist();
  }
  persist = () => {
    if (this.blockedSave) return;
    try {
      this.storage.setItem(STORAGE_KEY, JSON.stringify(this.snapshot.saved));
      this.lastSave = Date.now();
      if (this.snapshot.storage !== "ok") this.emit({ storage: "ok" });
    } catch {
      this.emit({ storage: "write" });
    }
  };
  retrySave() {
    if (this.snapshot.storage === "write") this.persist();
  }
  acceptRepair() {
    this.blockedSave = false;
    this.persist();
  }
  importLibrary(
    raw: string,
    mode: ImportMode,
  ): { ok: boolean; error?: "invalid" | "storage" | "blocked" | "capacity" } {
    if (mode !== "merge" && mode !== "replace")
      return { ok: false, error: "invalid" };
    if (this.blockedSave) return { ok: false, error: "blocked" };
    let candidate: Saved;
    try {
      const imported = previewImport(raw).value;
      candidate =
        mode === "replace"
          ? imported
          : mergeLibrary(this.snapshot.saved, imported);
    } catch {
      return { ok: false, error: "invalid" };
    }
    const serialized = JSON.stringify(candidate);
    if (new TextEncoder().encode(serialized).byteLength > MAX_IMPORT_TEXT)
      return { ok: false, error: "capacity" };
    try {
      this.storage.setItem(STORAGE_KEY, serialized);
    } catch {
      return { ok: false, error: "storage" };
    }
    this.lastSave = Date.now();
    this.emit({ saved: candidate, storage: "ok", raw: null });
    if (mode === "replace") this.load();
    return { ok: true };
  }
  reset() {
    this.pause();
    try {
      this.storage.removeItem(STORAGE_KEY);
      this.blockedSave = false;
      this.snapshot.saved = initial();
      this.expectedSource = "";
      this.audio.removeAttribute("src");
      this.audio.load();
      this.emit({ status: "idle", storage: "ok", error: null, raw: null });
    } catch {
      this.emit({ storage: "write" });
    }
  }
  private isCurrent() {
    return (
      !!this.expectedSource && this.audio.currentSrc === this.expectedSource
    );
  }
  private load() {
    this.request++;
    this.wantPlay = false;
    this.audio.pause();
    const track = currentTrack(this.snapshot.saved);
    this.audio.volume = this.snapshot.saved.volume;
    if (!track) {
      this.expectedSource = "";
      this.pendingSeek = null;
      this.audio.removeAttribute("src");
      this.audio.load();
      this.emit({ status: "idle", error: null });
      return;
    }
    this.expectedSource = new URL(track.audio, document.baseURI).href;
    this.pendingSeek = this.snapshot.saved.position;
    this.audio.src = this.expectedSource;
    this.audio.load();
    this.emit({ status: "paused", error: null });
  }
  async play() {
    if (!currentTrack(this.snapshot.saved)) return;
    if (this.snapshot.status === "error") this.load();
    const request = ++this.request;
    this.wantPlay = true;
    this.emit({ status: "loading", error: null });
    try {
      await this.audio.play();
      if (request === this.request && this.wantPlay)
        this.emit({ status: "playing" });
    } catch (error) {
      if (request === this.request) {
        this.wantPlay = false;
        this.emit({
          status: "error",
          error:
            error instanceof DOMException && error.name === "NotAllowedError"
              ? "blocked"
              : "media",
        });
      }
    }
  }
  pause() {
    this.request++;
    this.wantPlay = false;
    this.audio.pause();
    this.emit({
      status: currentTrack(this.snapshot.saved) ? "paused" : "idle",
    });
    this.persist();
  }
  toggle() {
    if (this.wantPlay) this.pause();
    else void this.play();
  }
  playList(ids: string[], index = 0) {
    if (!ids.length) return;
    const queue = ids.map(entry);
    this.update({ queue, currentId: queue[index].id, position: 0 });
    this.load();
    void this.play();
  }
  playEntry(id: string) {
    if (!this.snapshot.saved.queue.some((e) => e.id === id)) return;
    this.update({ currentId: id, position: 0 });
    this.load();
    void this.play();
  }
  add(trackId: string, next: boolean) {
    const hadCurrent = !!this.snapshot.saved.currentId;
    this.emit({ saved: insert(this.snapshot.saved, trackId, next) });
    this.persist();
    if (!hadCurrent) this.load();
  }
  move(id: string, direction: -1 | 1) {
    this.emit({ saved: moveUpcoming(this.snapshot.saved, id, direction) });
    this.persist();
  }
  remove(id: string) {
    const s = this.snapshot.saved,
      index = s.queue.findIndex((e) => e.id === id);
    if (index <= currentIndex(s)) return;
    this.update({ queue: s.queue.filter((e) => e.id !== id) });
  }
  seek(position: number) {
    const track = currentTrack(this.snapshot.saved);
    if (!track) return;
    const value = Math.max(
      0,
      Math.min(
        position,
        Number.isFinite(this.audio.duration)
          ? this.audio.duration
          : track.duration,
      ),
    );
    if (this.audio.readyState >= 1) {
      this.pendingSeek = null;
      this.audio.currentTime = value;
    } else this.pendingSeek = value;
    this.update({ position: value });
  }
  next(natural = false) {
    const i = nextIndex(this.snapshot.saved, natural);
    if (i === null) {
      this.pause();
      return;
    }
    const id = this.snapshot.saved.queue[i].id;
    if (id === this.snapshot.saved.currentId) {
      this.seek(0);
      void this.play();
    } else this.playEntry(id);
  }
  previous() {
    const s = this.snapshot.saved,
      index = currentIndex(s);
    if (s.position > 3 || index <= 0) this.seek(0);
    else this.playEntry(s.queue[index - 1].id);
  }
  mode(mode: Mode) {
    this.update({ mode });
  }
  volume(volume: number) {
    this.audio.volume = volume;
    this.update({ volume });
  }
  like(id: string) {
    const likes = this.snapshot.saved.likes;
    this.update({
      likes: likes.includes(id)
        ? likes.filter((x) => x !== id)
        : [...likes, id],
    });
  }
  albumLike(id: string) {
    const values = this.snapshot.saved.albumLikes;
    this.update({
      albumLikes: values.includes(id)
        ? values.filter((x) => x !== id)
        : [...values, id],
    });
  }
  createPlaylist(name: string, trackId?: string) {
    const id = crypto.randomUUID();
    this.update({
      playlists: [
        ...this.snapshot.saved.playlists,
        { id, name: name.trim(), entries: trackId ? [entry(trackId)] : [] },
      ],
    });
    return id;
  }
  addToPlaylist(id: string, trackId: string) {
    this.update({
      playlists: this.snapshot.saved.playlists.map((p) =>
        p.id === id ? { ...p, entries: [...p.entries, entry(trackId)] } : p,
      ),
    });
  }
  renamePlaylist(id: string, name: string) {
    this.update({
      playlists: this.snapshot.saved.playlists.map((p) =>
        p.id === id ? { ...p, name: name.trim() } : p,
      ),
    });
  }
  editPlaylist(id: string, entryId: string, move: -1 | 1 | "remove") {
    this.update({
      playlists: this.snapshot.saved.playlists.map((p) => {
        if (p.id !== id) return p;
        const entries = [...p.entries],
          i = entries.findIndex((e) => e.id === entryId);
        if (move === "remove")
          return { ...p, entries: entries.filter((e) => e.id !== entryId) };
        const j = i + move;
        if (i < 0 || j < 0 || j >= entries.length) return p;
        [entries[i], entries[j]] = [entries[j], entries[i]];
        return { ...p, entries };
      }),
    });
  }
}
