import catalog from "../fixtures/catalog.json";

export const tracks = catalog.tracks;
export const releases = catalog.releases;
export type Track = (typeof tracks)[number];
export type Release = (typeof releases)[number];
export type Entry = { id: string; trackId: string; releaseId?: string };
export type Playlist = { id: string; name: string; entries: Entry[] };
export type Mode = "sequence" | "repeat-all" | "repeat-one";
export type ImportMode = "merge" | "replace";
export type Saved = {
  schemaVersion: 1;
  language: "en" | "zh";
  queue: Entry[];
  currentId: string | null;
  position: number;
  mode: Mode;
  volume: number;
  likes: string[];
  albumLikes: string[];
  playlists: Playlist[];
  route: string;
  scroll: Record<string, number>;
  sort: string;
};
export const trackById = new Map(tracks.map((t) => [t.id, t]));
export const releaseById = new Map(releases.map((r) => [r.id, r]));
export const releaseFor = (id: string) =>
  releases.find((r) => r.trackIds.includes(id))!;
export const entry = (trackId: string): Entry => ({
  id: crypto.randomUUID(),
  trackId,
  releaseId: releaseFor(trackId).id,
});
export function initial(): Saved {
  return {
    schemaVersion: 1,
    language: "en",
    queue: [],
    currentId: null,
    position: 0,
    mode: "sequence",
    volume: 0.65,
    likes: [],
    albumLikes: [],
    playlists: [],
    route: "/library",
    scroll: {},
    sort: "collection",
  };
}
export const currentIndex = (s: Saved) =>
  s.queue.findIndex((e) => e.id === s.currentId);
export const currentEntry = (s: Saved) => s.queue[currentIndex(s)];
export const currentTrack = (s: Saved) =>
  trackById.get(currentEntry(s)?.trackId);
export const MAX_IMPORT_TEXT = 2 * 1024 * 1024;
export const duration = (ids: string[]) =>
  ids.reduce((sum, id) => sum + (trackById.get(id)?.duration ?? 0), 0);
export function time(seconds: number) {
  const value = Math.max(0, Math.floor(Number.isFinite(seconds) ? seconds : 0));
  return `${Math.floor(value / 60)}:${String(value % 60).padStart(2, "0")}`;
}
export function insert(s: Saved, trackId: string, next: boolean): Saved {
  const queue = [...s.queue];
  queue.splice(
    next ? Math.max(0, currentIndex(s) + 1) : queue.length,
    0,
    entry(trackId),
  );
  return {
    ...s,
    queue,
    currentId: s.currentId ?? queue[0].id,
    position: s.currentId ? s.position : 0,
  };
}
export function moveUpcoming(s: Saved, id: string, direction: -1 | 1): Saved {
  const index = s.queue.findIndex((e) => e.id === id),
    next = index + direction;
  if (
    index <= currentIndex(s) ||
    next <= currentIndex(s) ||
    next >= s.queue.length
  )
    return s;
  const queue = [...s.queue];
  [queue[index], queue[next]] = [queue[next], queue[index]];
  return { ...s, queue };
}
export function nextIndex(s: Saved, natural: boolean): number | null {
  const index = currentIndex(s);
  if (index < 0) return null;
  if (natural && s.mode === "repeat-one") return index;
  if (index + 1 < s.queue.length) return index + 1;
  return s.mode === "repeat-all" ? 0 : null;
}
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
function isSafeId(value: unknown): value is string {
  return typeof value === "string" && value.length > 0 && value.length <= 200;
}
function validStringList(
  values: unknown,
  known: ReadonlyMap<string, unknown>,
): string[] {
  if (!Array.isArray(values) || !values.every(isSafeId))
    throw new Error("likes");
  return [...new Set(values)].filter((id) => known.has(id));
}

// Reject unknown/damaged saves before writing anything. Missing catalog objects
// are a recoverable, explicit repair; the original export remains available.
export function restore(raw: string): { value: Saved; repaired: boolean } {
  if (
    typeof raw !== "string" ||
    raw.length > MAX_IMPORT_TEXT ||
    new TextEncoder().encode(raw).byteLength > MAX_IMPORT_TEXT
  )
    throw new Error("size");
  const parsed: unknown = JSON.parse(raw);
  if (!isRecord(parsed) || parsed.schemaVersion !== 1)
    throw new Error("version");
  const d = parsed;
  const ids = new Set<string>();
  const validEntries = (items: unknown): Entry[] => {
    if (!Array.isArray(items)) throw new Error("queue");
    return items
      .filter((e) => {
        if (!isRecord(e) || !isSafeId(e.id) || !isSafeId(e.trackId))
          throw new Error("entry");
        if (ids.has(e.id)) throw new Error("entry");
        ids.add(e.id);
        return trackById.has(e.trackId);
      })
      .map((e) => ({
        id: e.id,
        trackId: e.trackId,
        releaseId: releaseFor(e.trackId).id,
      }));
  };
  if (
    !Array.isArray(d.queue) ||
    !Array.isArray(d.likes) ||
    !Array.isArray(d.albumLikes) ||
    !Array.isArray(d.playlists) ||
    (d.language !== "en" && d.language !== "zh") ||
    (d.mode !== "sequence" &&
      d.mode !== "repeat-all" &&
      d.mode !== "repeat-one") ||
    typeof d.position !== "number" ||
    !Number.isFinite(d.position) ||
    typeof d.volume !== "number" ||
    !Number.isFinite(d.volume) ||
    typeof d.route !== "string" ||
    !isRecord(d.scroll) ||
    (d.sort !== undefined && typeof d.sort !== "string") ||
    (d.currentId !== undefined && d.currentId !== null && !isSafeId(d.currentId))
  )
    throw new Error("shape");
  const rawQueue = d.queue;
  const rawPlaylists = d.playlists;
  const queue = validEntries(rawQueue);
  const playlistIds = new Set<string>();
  const playlists = rawPlaylists.map((p: unknown): Playlist => {
    if (
      !isRecord(p) ||
      !isSafeId(p.id) ||
      playlistIds.has(p.id) ||
      typeof p.name !== "string" ||
      p.name.length > 120
    )
      throw new Error("playlist");
    playlistIds.add(p.id);
    return { id: p.id, name: p.name, entries: validEntries(p.entries) };
  });
  const id = typeof d.currentId === "string" && queue.some((e) => e.id === d.currentId)
    ? d.currentId
    : (queue[0]?.id ?? null);
  const track = trackById.get(queue.find((e) => e.id === id)?.trackId ?? "");
  const value: Saved = {
    schemaVersion: 1,
    language: d.language,
    queue,
    currentId: id,
    position:
      id === d.currentId
        ? Math.max(0, Math.min(d.position, track?.duration ?? 0))
        : 0,
    volume: Math.max(0, Math.min(1, d.volume)),
    mode: d.mode,
    likes: validStringList(d.likes, trackById),
    albumLikes: validStringList(d.albumLikes, releaseById),
    playlists,
    route: d.route.startsWith("/") ? d.route : "/library",
    scroll: Object.fromEntries(
      Object.entries(d.scroll).filter(
        (pair): pair is [string, number] =>
          typeof pair[1] === "number" &&
          Number.isFinite(pair[1]) &&
          pair[1] >= 0,
      ),
    ),
    sort: typeof d.sort === "string" && ["collection", "title", "artist"].includes(d.sort)
      ? d.sort
      : "collection",
  };
  return {
    value,
    repaired:
      queue.length !== rawQueue.length ||
      value.likes.length !== d.likes.length ||
      value.albumLikes.length !== d.albumLikes.length ||
      playlists.some(
        (p: Playlist, i: number) =>
          p.entries.length !==
          ((rawPlaylists[i] as Record<string, unknown>).entries as unknown[]).length,
      ) ||
      id !== d.currentId ||
      value.position !== d.position ||
      value.volume !== d.volume ||
      value.route !== d.route ||
      value.sort !== d.sort ||
      Object.keys(value.scroll).length !== Object.keys(d.scroll).length,
  };
}
