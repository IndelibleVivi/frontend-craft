import {
  MAX_IMPORT_TEXT,
  entry,
  restore,
  type Entry,
  type ImportMode,
  type Saved,
} from "./domain";

export type { ImportMode };

function freshEntry(value: Entry): Entry {
  return entry(value.trackId);
}

function freshPlaylist(value: Saved["playlists"][number]) {
  return {
    id: crypto.randomUUID(),
    name: value.name,
    entries: value.entries.map(freshEntry),
  };
}

export function mergeLibrary(current: Saved, imported: Saved): Saved {
  return {
    ...current,
    likes: [...new Set([...current.likes, ...imported.likes])],
    albumLikes: [...new Set([...current.albumLikes, ...imported.albumLikes])],
    playlists: [
      ...current.playlists,
      ...imported.playlists.map(freshPlaylist),
    ],
  };
}

export function previewImport(raw: string): {
  value: Saved;
  repaired: boolean;
} {
  if (
    typeof raw !== "string" ||
    raw.length > MAX_IMPORT_TEXT ||
    new TextEncoder().encode(raw).byteLength > MAX_IMPORT_TEXT
  )
    throw new Error("size");
  return restore(raw);
}
