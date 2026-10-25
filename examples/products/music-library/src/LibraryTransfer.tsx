import { useEffect, useRef, useState } from "react";
import { ArrowRight, Download, Upload } from "lucide-react";
import { previewImport, type ImportMode } from "./transfer";
import type { Saved } from "./domain";
import type { Player } from "./player";

export function LibraryTransfer({ player, zh, download, imported }: {
  player: Player;
  zh: boolean;
  download: (value: string, filename: string) => void;
  imported: (mode: ImportMode) => void;
}) {
  const t = (en: string, cn: string) => zh ? cn : en;
  const [source, setSource] = useState<{ raw: string; name: string; value: Saved; repaired: boolean } | null>(null);
  const [mode, setMode] = useState<ImportMode>("merge");
  const [confirmed, setConfirmed] = useState(false);
  const [error, setError] = useState<"invalid" | "size" | "read" | "storage" | "blocked" | "capacity" | null>(null);
  const [reading, setReading] = useState(false);
  const generation = useRef(0);
  useEffect(() => () => { generation.current++; }, []);
  const current = player.getSnapshot().saved;
  const read = async (file: File | undefined) => {
    const token = ++generation.current;
    setSource(null); setError(null); setConfirmed(false);
    if (!file) { setReading(false); return; }
    if (file.size > 2 * 1024 * 1024) { setError("size"); setReading(false); return; }
    setReading(true);
    try {
      const raw = await file.text();
      if (token !== generation.current) return;
      try {
        const preview = previewImport(raw);
        setSource({ raw, name: file.name, ...preview });
      } catch { setError("invalid"); }
    } catch { if (token === generation.current) setError("read"); }
    finally { if (token === generation.current) setReading(false); }
  };
  const summary = (value: Saved) => (
    <dl className="transfer-counts">
      <div><dt>{t("Playlists", "歌单")}</dt><dd>{value.playlists.length}</dd></div>
      <div><dt>{t("Liked songs", "喜欢的歌曲")}</dt><dd>{value.likes.length}</dd></div>
      <div><dt>{t("Saved albums", "收藏的合辑")}</dt><dd>{value.albumLikes.length}</dd></div>
      <div><dt>{t("Queue entries", "队列曲目")}</dt><dd>{value.queue.length}</dd></div>
    </dl>
  );
  return <div className="library-transfer">
    <p>{t("Take your listening space with you. Choose a Side A library export to review before making any changes.", "把聆听空间带走。选择 Side A 导出的音乐库，先查看内容，再决定怎样导入。")}</p>
    <label className="transfer-file">
      <Upload size={20} aria-hidden="true" />
      <span>{t("Choose a library file", "选择音乐库文件")}</span>
      <input type="file" accept=".json,application/json" onChange={e => void read(e.target.files?.[0])} />
    </label>
    {reading && <p role="status">{t("Reading your file…", "正在读取文件…")}</p>}
    {error && <p className="transfer-error" role="alert">{({
      capacity: t("These libraries together exceed the 2 MiB backup limit. Export your current library, then restore the file instead, or choose a smaller library.", "合并后的音乐库超出 2 MiB 备份上限。可先导出当前音乐库，再恢复此文件，或选择较小的音乐库。"),
      invalid: t("This is not a supported Side A library. Nothing has changed.", "这不是受支持的 Side A 音乐库，当前数据未改变。"),
      size: t("Choose a library smaller than 2 MiB. Audio files are not library exports.", "请选择不超过 2 MiB 的音乐库文件。音频文件不是音乐库导出。"),
      read: t("This file could not be read. Choose it again or use another copy.", "无法读取此文件，请重新选择或换一个副本。"),
      storage: t("The browser could not save this import. Your current library and playback are unchanged. Free some space and try again.", "浏览器无法保存此次导入，当前音乐库与播放未改变。请释放空间后重试。"),
      blocked: t("Resolve the saved-data warning first. Your original save has not been overwritten.", "请先处理已保存数据的警告，原始记录未被覆盖。"),
    })[error]}</p>}
    {source && <>
      <div className="transfer-preview">
        <section><span className="eyebrow">{t("FROM FILE", "来自文件")}</span><h3>{source.name}</h3>{summary(source.value)}
          <ul className="transfer-names">{source.value.playlists.slice(0, 3).map(p => <li key={p.id}>{p.name} <span>· {p.entries.length} {t("songs", "首")}</span></li>)}</ul>
          {source.value.playlists.length > 3 && <p>{t(`And ${source.value.playlists.length - 3} more playlists`, `另有 ${source.value.playlists.length - 3} 张歌单`)}</p>}
        </section>
        <ArrowRight className="transfer-arrow" aria-hidden="true" />
        <section><span className="eyebrow">{t("IN THIS BROWSER", "当前浏览器")}</span><h3>{t("Your listening space", "你的聆听空间")}</h3>{summary(current)}</section>
      </div>
      {source.repaired && <p className="transfer-warning" role="status">{t("Some catalog items or saved values need repair. Only available songs will be imported. Your original file stays untouched.", "部分曲目或保存值需要修复，只会导入仍可用的曲目。原始文件不会改变。")}</p>}
      <fieldset className="transfer-modes"><legend>{t("How would you like to bring it in?", "怎样导入？")}</legend>
        <label><input type="radio" name="import-mode" value="merge" checked={mode === "merge"} onChange={() => { setMode("merge"); setConfirmed(false); }} /><span><strong>{t("Add to my library", "加入当前音乐库")}</strong><small>{t("Keep listening. Add likes and new copies of the file’s playlists; keep your current playlists, queue and settings.", "继续聆听，合并喜欢与收藏，新增文件中的歌单副本；保留当前歌单、队列和设置。")}</small></span></label>
        <label><input type="radio" name="import-mode" value="replace" checked={mode === "replace"} onChange={() => { setMode("replace"); setConfirmed(false); }} /><span><strong>{t("Restore this library", "恢复此音乐库")}</strong><small>{t("Replace this browser’s Side A data with the file, including its queue and position. Reopen paused.", "用文件替换当前浏览器的 Side A 数据，包括队列与进度。恢复后暂停。")}</small></span></label>
      </fieldset>
      {mode === "replace" && <div className="transfer-replace">
        <button className="quiet-button" onClick={() => download(JSON.stringify(player.getSnapshot().saved, null, 2), "side-a-before-restore.json")}><Download size={16} />{t("Export my current library first", "先导出当前音乐库")}</button>
        <label><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)} /><span>{t("Replace my current Side A library with this file.", "确认用此文件替换当前 Side A 音乐库。")}</span></label>
      </div>}
      <button className="solid-button" disabled={mode === "replace" && !confirmed} onClick={() => {
        const result = player.importLibrary(source.raw, mode);
        if (!result.ok) setError(result.error || "invalid");
        else imported(mode);
      }}>{mode === "merge" ? t("Add to my library", "加入当前音乐库") : t("Replace and reopen paused", "替换并暂停恢复")}</button>
    </>}
  </div>;
}
