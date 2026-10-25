import { afterEach, describe, expect, it, vi } from "vitest";
import {
  entry,
  initial,
  insert,
  moveUpcoming,
  nextIndex,
  restore,
  tracks,
  releases,
  currentTrack,
  type Saved,
} from "../music-library/src/domain";
import { Player, STORAGE_KEY } from "../music-library/src/player";
import { previewImport } from "../music-library/src/transfer";

const [a, b, c] = tracks.map((t) => t.id);
class AudioDouble extends EventTarget {
  src = "";
  currentSrc = "";
  currentTime = 0;
  duration = 300;
  readyState = 1;
  preload = "";
  volume = 1;
  paused = true;
  play = vi.fn(async () => {
    this.paused = false;
    this.dispatchEvent(new Event("playing"));
  });
  pause() {
    this.paused = true;
    this.dispatchEvent(new Event("pause"));
  }
  load() {
    this.currentSrc = this.src;
    this.currentTime = 0;
  }
  removeAttribute() {
    this.src = "";
  }
  event(type: string) {
    this.dispatchEvent(new Event(type));
  }
}
function setup(raw?: string) {
  vi.stubGlobal("document", { baseURI: "http://localhost/" });
  const data = new Map<string, string>(raw ? [[STORAGE_KEY, raw]] : []);
  const storage = {
    getItem: (key: string) => data.get(key) ?? null,
    setItem: vi.fn((key: string, value: string) => {
      data.set(key, value);
    }),
    removeItem: (key: string) => {
      data.delete(key);
    },
  };
  const audio = new AudioDouble();
  const player = new Player(audio as unknown as HTMLAudioElement, storage);
  return { player, audio, storage, data };
}
afterEach(() => vi.unstubAllGlobals());

describe("queue occurrence identity and transport semantics", () => {
  it("keeps duplicate songs independent and only reorders upcoming entries", () => {
    let s = insert(initial(), a, false);
    s = insert(s, b, false);
    s = insert(s, b, false);
    expect(new Set(s.queue.map((e) => e.id)).size).toBe(3);
    const [current, one, two] = s.queue;
    expect(moveUpcoming(s, one.id, -1)).toBe(s);
    s = moveUpcoming(s, two.id, -1);
    expect(s.queue.map((e) => e.id)).toEqual([current.id, two.id, one.id]);
    expect(s.currentId).toBe(current.id);
  });
  it("single repeat applies only to natural ending; sequence stops and repeat-all wraps", () => {
    const queue = [entry(a), entry(b)],
      s: Saved = {
        ...initial(),
        queue,
        currentId: queue[0].id,
        mode: "repeat-one",
      };
    expect(nextIndex(s, true)).toBe(0);
    expect(nextIndex(s, false)).toBe(1);
    s.currentId = queue[1].id;
    s.mode = "sequence";
    expect(nextIndex(s, true)).toBeNull();
    s.mode = "repeat-all";
    expect(nextIndex(s, true)).toBe(0);
  });
  it("adding to an empty queue stays paused, next inserts after current, past/current cannot be removed", () => {
    const { player, audio } = setup();
    player.add(a, false);
    player.add(b, false);
    player.add(c, true);
    expect(audio.play).not.toHaveBeenCalled();
    expect(player.getSnapshot().status).toBe("paused");
    expect(player.getSnapshot().saved.queue.map((e) => e.trackId)).toEqual([
      a,
      c,
      b,
    ]);
    player.remove(player.getSnapshot().saved.currentId!);
    expect(player.getSnapshot().saved.queue).toHaveLength(3);
  });
  it("previous restarts after three seconds, then moves to the preceding occurrence", () => {
    const { player, audio } = setup();
    player.playList([a, b], 1);
    audio.event("loadedmetadata");
    player.seek(4);
    player.previous();
    expect(currentTrack(player.getSnapshot().saved)?.id).toBe(b);
    expect(audio.currentTime).toBe(0);
    player.previous();
    expect(currentTrack(player.getSnapshot().saved)?.id).toBe(a);
  });
});

describe("media results are subordinate to the active request", () => {
  it("a rejected play is an error, not playing, and retry can recover", async () => {
    const { player, audio } = setup();
    player.add(a, false);
    audio.play.mockRejectedValueOnce(
      new DOMException("gesture", "NotAllowedError"),
    );
    await player.play();
    expect(player.getSnapshot()).toMatchObject({
      status: "error",
      error: "blocked",
    });
    await player.play();
    expect(player.getSnapshot()).toMatchObject({
      status: "playing",
      error: null,
    });
  });
  it("late rejection from A cannot replace successful B", async () => {
    const { player, audio } = setup();
    let reject!: (e: Error) => void;
    audio.play.mockImplementationOnce(
      () =>
        new Promise<void>((_, r) => {
          reject = r;
        }),
    );
    player.playList([a]);
    player.playList([b]);
    await Promise.resolve();
    reject(new Error("stale"));
    await Promise.resolve();
    expect(currentTrack(player.getSnapshot().saved)?.id).toBe(b);
    expect(player.getSnapshot()).toMatchObject({
      status: "playing",
      error: null,
    });
  });
  it("natural queue ending stops on its last item without escaping the queue", async () => {
    const { player, audio } = setup();
    player.playList([a, b], 1);
    await Promise.resolve();
    audio.event("ended");
    expect(currentTrack(player.getSnapshot().saved)?.id).toBe(b);
    expect(player.getSnapshot().status).toBe("paused");
  });
});

describe("durable state and recoverable failures", () => {
  it("restores after metadata, clamps position, and never starts audio", () => {
    const q = [entry(a)],
      s = { ...initial(), queue: q, currentId: q[0].id, position: 9000 };
    const { player, audio } = setup(JSON.stringify(s));
    expect(audio.currentTime).toBe(0);
    audio.event("loadedmetadata");
    expect(audio.currentTime).toBe(tracks[0].duration);
    expect(audio.play).not.toHaveBeenCalled();
    expect(player.getSnapshot().status).toBe("paused");
  });
  it.each(["{bad", JSON.stringify({ ...initial(), schemaVersion: 999 })])(
    "does not overwrite damaged or unknown saves: %s",
    (raw) => {
      const { player, storage, data } = setup(raw);
      player.like(a);
      player.persist();
      expect(player.getSnapshot().storage).toBe("damaged");
      expect(storage.setItem).not.toHaveBeenCalled();
      expect(data.get(STORAGE_KEY)).toBe(raw);
    },
  );
  it("requires explicit acceptance before saving a catalog repair", () => {
    const q = [{ id: "missing", trackId: "unavailable" }, entry(b)],
      raw = JSON.stringify({
        ...initial(),
        queue: q,
        currentId: "missing",
        position: 45,
      });
    const { player, storage } = setup(raw);
    expect(player.getSnapshot().storage).toBe("repaired");
    expect(currentTrack(player.getSnapshot().saved)?.id).toBe(b);
    expect(player.getSnapshot().saved.position).toBe(0);
    player.like(a);
    expect(storage.setItem).not.toHaveBeenCalled();
    player.acceptRepair();
    expect(player.getSnapshot().storage).toBe("ok");
    expect(storage.setItem).toHaveBeenCalled();
  });
  it("retains in-tab work when writes fail, then retries the full state", () => {
    const { player, storage, data } = setup();
    storage.setItem.mockImplementationOnce(() => {
      throw new Error("quota");
    });
    player.createPlaylist("Sunday", a);
    expect(player.getSnapshot().storage).toBe("write");
    expect(player.getSnapshot().saved.playlists[0].entries[0].trackId).toBe(a);
    player.retrySave();
    expect(player.getSnapshot().storage).toBe("ok");
    expect(JSON.parse(data.get(STORAGE_KEY)!).playlists[0].name).toBe("Sunday");
  });
  it("playlist occurrences reorder/remove independently and survive validation", () => {
    const { player } = setup();
    const id = player.createPlaylist("Evening", a);
    player.addToPlaylist(id, a);
    player.addToPlaylist(id, b);
    const original = player.getSnapshot().saved.playlists[0].entries;
    player.editPlaylist(id, original[2].id, -1);
    player.editPlaylist(id, original[0].id, "remove");
    player.renamePlaylist(id, "Night");
    const value = restore(JSON.stringify(player.getSnapshot().saved)).value;
    expect(value.playlists[0].name).toBe("Night");
    expect(value.playlists[0].entries.map((e) => e.id)).toEqual([
      original[2].id,
      original[1].id,
    ]);
  });
  it("round-trips the existing saved export shape", () => {
    const q = [entry(a), entry(a)],
      saved: Saved = {
        ...initial(),
        queue: q,
        currentId: q[0].id,
        position: 5,
        likes: [a],
        albumLikes: [releases[0].id],
        playlists: [{ id: "p", name: "Two copies", entries: [entry(a), entry(a)] }],
      };
    expect(restore(JSON.stringify(saved))).toEqual({
      value: saved,
      repaired: false,
    });
  });
  it("rejects malformed structures and oversized text", () => {
    const valid = initial();
    expect(() =>
      previewImport(JSON.stringify(valid).padEnd(2 * 1024 * 1024 + 1)),
    ).toThrow("size");
    expect(() =>
      previewImport(JSON.stringify({ ...valid, likes: ["界".repeat(700_000)] })),
    ).toThrow("size");
    expect(() => restore(JSON.stringify({ ...valid, queue: [null] }))).toThrow();
    expect(() => restore(JSON.stringify({ ...valid, scroll: [] }))).toThrow();
    expect(() => restore(JSON.stringify({ ...valid, likes: [null] }))).toThrow();
    expect(() =>
      restore(
        JSON.stringify({
          ...valid,
          playlists: [{ id: "p", name: "Missing entries" }],
        }),
      ),
    ).toThrow();
  });
  it("reports missing catalog tracks in a repaired preview", () => {
    const q = [entry(a), { id: "gone", trackId: "unavailable" }],
      raw = JSON.stringify({
        ...initial(),
        queue: q,
        currentId: q[0].id,
        playlists: [
          {
            id: "partial",
            name: "Partial",
            entries: [{ id: "old", trackId: "also-gone" }],
          },
        ],
        likes: [a, "unavailable"],
        albumLikes: [releases[0].id, "unavailable"],
      });
    const preview = previewImport(raw);
    expect(preview.repaired).toBe(true);
    expect(preview.value.queue).toHaveLength(1);
    expect(preview.value.playlists[0].entries).toEqual([]);
    expect(preview.value.likes).toEqual([a]);
  });
  it("merges likes and fresh playlist occurrences without changing playback", async () => {
    const { player, audio } = setup();
    player.playList([a, b]);
    await Promise.resolve();
    const before = player.getSnapshot().saved,
      source = before.queue[0],
      imported: Saved = {
        ...initial(),
        queue: [{ ...source, id: "import-current" }],
        currentId: "import-current",
        likes: [b, a],
        albumLikes: [releases[0].id],
        playlists: [
          {
            id: "same-playlist-id",
            name: "Source",
            entries: [source, { ...source, id: "duplicate-entry" }],
          },
        ],
      };
    const src = audio.currentSrc;
    expect(player.importLibrary(JSON.stringify(imported), "merge")).toEqual({
      ok: true,
    });
    const after = player.getSnapshot().saved;
    expect(after.queue).toEqual(before.queue);
    expect(after.currentId).toBe(before.currentId);
    expect(after.position).toBe(before.position);
    expect(after.route).toBe(before.route);
    expect(after.mode).toBe(before.mode);
    expect(after.volume).toBe(before.volume);
    expect(after.likes.sort()).toEqual([a, b].sort());
    expect(after.albumLikes).toEqual([releases[0].id]);
    expect(after.playlists[0].id).not.toBe("same-playlist-id");
    expect(after.playlists[0].entries).toHaveLength(2);
    expect(new Set(after.playlists[0].entries.map((e) => e.id)).size).toBe(2);
    expect(after.playlists[0].entries.map((e) => e.trackId)).toEqual([a, a]);
    expect(audio.currentSrc).toBe(src);
    expect(audio.play).toHaveBeenCalledTimes(1);
    expect(audio.paused).toBe(false);
    expect(player.getSnapshot().status).toBe("playing");
  });
  it("merges a colliding playlist id without overwriting the existing playlist", () => {
    const { player } = setup();
    player.createPlaylist("Current", a);
    const current = player.getSnapshot().saved.playlists[0];
    const imported: Saved = {
      ...initial(),
      playlists: [{ id: current.id, name: "Imported", entries: [entry(b)] }],
    };
    player.importLibrary(JSON.stringify(imported), "merge");
    const playlists = player.getSnapshot().saved.playlists;
    expect(playlists).toHaveLength(2);
    expect(playlists[0]).toEqual(current);
    expect(playlists[1].id).not.toBe(current.id);
    expect(playlists[1].name).toBe("Imported");
  });
  it("replaces saved data, volume and position while staying paused", async () => {
    const { player, audio } = setup();
    player.playList([a, b]);
    await Promise.resolve();
    expect(audio.paused).toBe(false);
    const source = entry(b),
      imported: Saved = {
        ...initial(),
        queue: [source],
        currentId: source.id,
        position: 42,
        volume: 0.2,
        route: "/playlist/restored",
      };
    expect(player.importLibrary(JSON.stringify(imported), "replace")).toEqual({
      ok: true,
    });
    expect(player.getSnapshot().saved.queue.map((e) => e.id)).toEqual([
      source.id,
    ]);
    expect(player.getSnapshot().saved.position).toBe(42);
    expect(audio.currentSrc).toContain(tracks[1].audio);
    expect(audio.paused).toBe(true);
    expect(audio.volume).toBe(0.2);
    expect(player.getSnapshot().status).toBe("paused");
    audio.event("loadedmetadata");
    expect(audio.currentTime).toBe(42);
    expect(audio.play).toHaveBeenCalledTimes(1);
  });
  it("clears the old audio source when replacing with an empty queue", async () => {
    const { player, audio } = setup();
    player.playList([a]);
    await Promise.resolve();
    expect(player.importLibrary(JSON.stringify(initial()), "replace")).toEqual({
      ok: true,
    });
    expect(audio.paused).toBe(true);
    expect(audio.currentSrc).toBe("");
    expect(player.getSnapshot()).toMatchObject({
      status: "idle",
      error: null,
    });
  });
  it("keeps current state and audio when candidate storage fails", async () => {
    const { player, audio, storage, data } = setup();
    player.playList([a]);
    await Promise.resolve();
    const before = player.getSnapshot(),
      src = audio.currentSrc,
      oldTime = audio.currentTime,
      stored = data.get(STORAGE_KEY);
    storage.setItem.mockImplementationOnce(() => {
      throw new DOMException("full", "QuotaExceededError");
    });
    expect(
      player.importLibrary(JSON.stringify({ ...initial(), likes: [b] }), "merge"),
    ).toEqual({ ok: false, error: "storage" });
    expect(player.getSnapshot()).toBe(before);
    expect(audio.currentSrc).toBe(src);
    expect(audio.currentTime).toBe(oldTime);
    expect(audio.paused).toBe(false);
    expect(data.get(STORAGE_KEY)).toBe(stored);
  });
  it("blocks import over damaged or repaired original state", () => {
    for (const raw of [
      "{damaged",
      JSON.stringify({
        ...initial(),
        queue: [{ id: "gone", trackId: "unavailable" }],
        currentId: "gone",
      }),
    ]) {
      const { player, storage, data } = setup(raw);
      expect(player.importLibrary(JSON.stringify(initial()), "merge")).toEqual({
        ok: false,
        error: "blocked",
      });
      expect(storage.setItem).not.toHaveBeenCalled();
      expect(data.get(STORAGE_KEY)).toBe(raw);
    }
  });
  it("reset removes only this app key", () => {
    const { player, data } = setup();
    data.set("unrelated", "keep");
    player.add(a, false);
    player.reset();
    expect(data.has(STORAGE_KEY)).toBe(false);
    expect(data.get("unrelated")).toBe("keep");
    expect(player.getSnapshot().saved.queue).toEqual([]);
  });
});


describe("backup capacity and normalized recovery", () => {
  it("rejects a merge that would save a library too large to reopen", () => {
    const { player, data } = setup();
    const raw = JSON.stringify({ ...initial(), playlists: [{ id: "large", name: "Large mix", entries: Array.from({length: 14000}, () => entry(a)) }] });
    expect(new TextEncoder().encode(raw).byteLength).toBeLessThan(2 * 1024 * 1024);
    expect(player.importLibrary(raw, "merge")).toEqual({ ok: true });
    const before = player.getSnapshot(), stored = data.get(STORAGE_KEY);
    expect(player.importLibrary(raw, "merge")).toEqual({ ok: false, error: "capacity" });
    expect(player.getSnapshot()).toBe(before);
    expect(data.get(STORAGE_KEY)).toBe(stored);
    expect(restore(stored!).value.playlists).toHaveLength(1);
  });
  it("labels filtered view state as repaired and rejects duplicate occurrence identities", () => {
    expect(restore(JSON.stringify({ ...initial(), sort: "future", scroll: {"/library": -1} })).repaired).toBe(true);
    const duplicate = entry(a);
    expect(() => restore(JSON.stringify({...initial(), queue: [duplicate, duplicate]}))).toThrow("entry");
  });
});
