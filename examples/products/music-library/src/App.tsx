import {
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  useSyncExternalStore,
  type ReactNode,
  type CSSProperties,
} from "react";
import {
  ArrowDown,
  ArrowLeft,
  ArrowUp,
  Check,
  ChevronDown,
  ChevronRight,
  Disc3,
  Heart,
  Library,
  ListMusic,
  Maximize2,
  MoreHorizontal,
  Pause,
  Play,
  Plus,
  Repeat,
  Repeat1,
  Search,
  SkipBack,
  SkipForward,
  SlidersHorizontal,
  Volume2,
  X,
  Info,
  Music2,
  Clock3,
  ArrowUpRight,
  Download,
  Menu,
} from "lucide-react";
import {
  currentIndex,
  currentTrack,
  duration,
  releaseById,
  releaseFor,
  releases,
  time,
  trackById,
  tracks,
  type Entry,
  type Release,
  type Track,
} from "./domain";
import type { Player } from "./player";
import { LibraryTransfer } from "./LibraryTransfer";

function IconButton({
  label,
  children,
  onClick,
  active = false,
  disabled = false,
  className = "",
  id,
}: {
  label: string;
  children: ReactNode;
  onClick: () => void;
  active?: boolean;
  disabled?: boolean;
  className?: string;
  id?: string;
}) {
  return (
    <button
      id={id}
      className={`icon-button ${active ? "active" : ""} ${className}`}
      type="button"
      aria-label={label}
      title={label}
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </button>
  );
}
function Modal({
  title,
  children,
  close,
  className = "",
}: {
  title: string;
  children: ReactNode;
  close: () => void;
  className?: string;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const trigger = document.activeElement as HTMLElement;
    ref.current?.showModal();
    return () => {
      ref.current?.close();
      if (trigger?.isConnected) trigger.focus();
    };
  }, []);
  return (
    <dialog
      ref={ref}
      className={`dialog ${className}`}
      aria-label={title}
      onCancel={(e) => {
        e.preventDefault();
        close();
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) close();
      }}
    >
      <div className="dialog-heading">
        <h2>{title}</h2>
        <IconButton label="Close / 关闭" onClick={close}>
          <X />
        </IconButton>
      </div>
      {children}
    </dialog>
  );
}
function Artwork({
  release,
  className = "",
  eager = false,
}: {
  release: Release;
  className?: string;
  eager?: boolean;
}) {
  const [failed, setFailed] = useState(false);
  return failed ? (
    <div
      className={`art-fallback ${className}`}
      role="img"
      aria-label={release.title}
      style={{ background: release.color }}
    >
      <Disc3 />
      <span>{release.title}</span>
    </div>
  ) : (
    <img
      className={className}
      src={release.cover}
      width="600"
      height="600"
      alt={release.title}
      loading={eager ? "eager" : "lazy"}
      onError={() => setFailed(true)}
    />
  );
}
function download(value: string, filename: string) {
  const url = URL.createObjectURL(
    new Blob([value], { type: "application/json" }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function App({ player }: { player: Player }) {
  const snap = useSyncExternalStore(player.subscribe, player.getSnapshot);
  const s = snap.saved,
    zh = s.language === "zh",
    t = (en: string, cn: string) => (zh ? cn : en);
  const pane = useRef<HTMLElement>(null);
  const initialRoute = location.hash.slice(1) || s.route;
  const [route, setRoute] = useState(initialRoute);
  const routeRef = useRef(route);
  routeRef.current = route;
  const restoreFocus = useRef<Record<string, string>>({});
  const searchOrigin = useRef("/library");
  const [gridMode, setGridMode] = useState<"albums" | "tracks">("albums");
  const [queueOpen, setQueueOpen] = useState(false);
  const [listenOpen, setListenOpen] = useState(false);
  const [mobile, setMobile] = useState(
    matchMedia("(max-width: 760px)").matches,
  );
  const [menuOpen, setMenuOpen] = useState(false);
  const [trackMenu, setTrackMenu] = useState<string | null>(null);
  const [listDialog, setListDialog] = useState<{
    trackId?: string;
    id?: string;
  } | null>(null);
  const [listName, setListName] = useState("");
  const [resetOpen, setResetOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [toast, setToast] = useState("");
  const toastTimer = useRef<ReturnType<typeof setTimeout> | undefined>(
    undefined,
  );
  const current = currentTrack(s),
    playing = snap.status === "playing",
    busy = snap.status === "loading";
  const currentRelease = current ? releaseFor(current.id) : null;
  const upcoming = s.queue.slice(currentIndex(s) + 1);
  const query = route.startsWith("/search")
    ? new URLSearchParams(route.split("?")[1]).get("q") || ""
    : "";
  const album = route.startsWith("/album/")
    ? releaseById.get(route.split("/")[2])
    : undefined;
  const playlist = route.startsWith("/playlist/")
    ? s.playlists.find((p) => p.id === route.split("/")[2])
    : undefined;
  const notify = (message: string) => {
    setToast(message);
    clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(""), 2800);
  };
  const remember = () => {
    const focus = document.activeElement as HTMLElement;
    if (focus.id) restoreFocus.current[routeRef.current] = focus.id;
    player.update({
      route: routeRef.current,
      scroll: {
        ...player.getSnapshot().saved.scroll,
        [routeRef.current]: pane.current?.scrollTop || 0,
      },
    });
  };
  const navigate = (path: string, replace = false) => {
    clearTimeout(scrollTimer.current);
    remember();
    history[replace ? "replaceState" : "pushState"](
      { sideA: true },
      "",
      `#${path}`,
    );
    setRoute(path);
    player.update({ route: path });
    setMenuOpen(false);
  };
  const back = () => {
    remember();
    if (history.state?.sideA) history.back();
    else navigate("/library");
  };
  useEffect(() => {
    if (!location.hash) history.replaceState(null, "", `#${initialRoute}`);
    const pop = () => {
      clearTimeout(scrollTimer.current);
      remember();
      const path = location.hash.slice(1) || "/library";
      setRoute(path);
      player.update({ route: path });
    };
    window.addEventListener("popstate", pop);
    const media = matchMedia("(max-width: 760px)");
    const change = () => setMobile(media.matches);
    media.addEventListener("change", change);
    return () => {
      window.removeEventListener("popstate", pop);
      media.removeEventListener("change", change);
    };
  }, []);
  useLayoutEffect(() => {
    if (pane.current)
      pane.current.scrollTop = player.getSnapshot().saved.scroll[route] || 0;
    const id = restoreFocus.current[route];
    if (id) document.getElementById(id)?.focus({ preventScroll: true });
  }, [route]);
  useEffect(() => {
    document.documentElement.lang = zh ? "zh-CN" : "en";
    document.title = `${album?.title || playlist?.name || "Side A"} — ${t("Music library", "音乐库")}`;
  }, [zh, album, playlist]);
  const scrollTimer = useRef<ReturnType<typeof setTimeout> | undefined>(
    undefined,
  );
  const onScroll = () => {
    const path = routeRef.current,
      position = pane.current?.scrollTop || 0;
    clearTimeout(scrollTimer.current);
    scrollTimer.current = setTimeout(() => {
      player.update({
        scroll: { ...player.getSnapshot().saved.scroll, [path]: position },
      });
    }, 180);
  };
  const search = (value: string) => {
    if (!route.startsWith("/search")) searchOrigin.current = route;
    if (!value) navigate(searchOrigin.current, true);
    else
      navigate(
        `/search?q=${encodeURIComponent(value)}`,
        route.startsWith("/search"),
      );
  };
  const newList = (trackId?: string) => {
    setListName("");
    setListDialog({ trackId });
    setTrackMenu(null);
  };
  const openTrackMenu = (id: string) => setTrackMenu(id);
  const add = (id: string, next: boolean) => {
    player.add(id, next);
    notify(
      t(
        next ? "Added to play next" : "Added to the queue",
        next ? "已加入下一首" : "已加入队尾",
      ),
    );
    setTrackMenu(null);
  };
  const toggleLike = (track: Track) => {
    player.like(track.id);
  };
  const navItem = (
    path: string,
    name: string,
    icon: ReactNode,
    count?: number,
  ) => (
    <button
      key={path}
      className={`nav-item ${route === path ? "selected" : ""}`}
      onClick={() => navigate(path)}
      aria-current={route === path ? "page" : undefined}
    >
      {icon}
      <span>{name}</span>
      {count !== undefined && <small>{count}</small>}
    </button>
  );
  const navigation = (
    <>
      <button
        className="wordmark"
        onClick={() => navigate("/library")}
        aria-label="Side A"
      >
        <span className="brand-symbol">A</span>
        <span>
          side a<span className="brand-dot">.</span>
        </span>
      </button>
      <p className="side-caption">
        {t("A little room for your music.", "给音乐，留一点空间。")}
      </p>
      <nav aria-label={t("Your library", "你的音乐库")}>
        <span className="nav-label">{t("YOUR LIBRARY", "你的音乐")}</span>
        {navItem(
          "/library",
          t("Collection", "音乐收藏"),
          <Library />,
          releases.length,
        )}
        {navItem("/recent", t("Recently added", "最近加入"), <Clock3 />)}
        {navItem(
          "/liked",
          t("Liked songs", "喜欢的歌曲"),
          <Heart />,
          s.likes.length,
        )}
        {navItem(
          "/saved",
          t("Saved albums", "收藏的合辑"),
          <Disc3 />,
          s.albumLikes.length,
        )}
        <div className="nav-label list-label">
          <span>{t("YOUR PLAYLISTS", "我的列表")}</span>
          <IconButton
            label={t("Create playlist", "创建列表")}
            onClick={() => newList()}
          >
            <Plus />
          </IconButton>
        </div>
        {s.playlists.map((p) =>
          navItem(`/playlist/${p.id}`, p.name, <ListMusic />, p.entries.length),
        )}
        {!s.playlists.length && (
          <button className="create-list" onClick={() => newList()}>
            <Plus size={16} />
            {t("Make a little mix", "做一张自己的歌单")}
          </button>
        )}
      </nav>
      <div className="sidebar-bottom">
        <div className="local-indicator">
          <span />
          {t("Your own listening space", "属于你的聆听空间")}
        </div>
        {navItem("/about", t("About & credits", "关于与署名"), <Info />)}
      </div>
    </>
  );
  const likeButton = (track: Track) => (
    <IconButton
      label={t(
        `${s.likes.includes(track.id) ? "Unlike" : "Like"} ${track.title}`,
        `${s.likes.includes(track.id) ? "取消喜欢" : "喜欢"} ${track.title}`,
      )}
      active={s.likes.includes(track.id)}
      onClick={() => toggleLike(track)}
    >
      <Heart fill={s.likes.includes(track.id) ? "currentColor" : "none"} />
    </IconButton>
  );
  function TrackRows({
    ids,
    entries,
    listId,
  }: {
    ids: string[];
    entries?: Entry[];
    listId?: string;
  }) {
    return (
      <div className="track-table">
        <div className="track-head">
          <span>#</span>
          <span>{t("TRACK / ARTIST", "歌曲 / 作者")}</span>
          <span>{t("TIME", "时长")}</span>
          <span />
        </div>
        {ids.map((id, index) => {
          const track = trackById.get(id)!;
          const isCurrent = current?.id === id;
          return (
            <div
              className={`track-row ${isCurrent ? "is-current" : ""}`}
              key={entries?.[index]?.id || id}
              data-track={id}
            >
              <button
                className="track-number"
                onClick={() => player.playList(ids, index)}
                aria-label={t(`Play ${track.title}`, `播放 ${track.title}`)}
              >
                {isCurrent && playing ? (
                  <span className="equalizer">
                    <i />
                    <i />
                    <i />
                  </span>
                ) : (
                  <>
                    <span>{String(index + 1).padStart(2, "0")}</span>
                    <Play className="row-play" size={15} fill="currentColor" />
                  </>
                )}
              </button>
              <button
                className="track-title"
                onClick={() => player.playList(ids, index)}
              >
                <strong>{track.title}</strong>
                <span>
                  {track.artist}
                  {track.composer !== track.artist
                    ? ` · ${track.composer}`
                    : ""}
                </span>
              </button>
              <span className="track-time">{time(track.duration)}</span>
              <div className="track-actions">
                {likeButton(track)}
                <IconButton
                  label={t(
                    `More for ${track.title}`,
                    `${track.title} 的更多操作`,
                  )}
                  onClick={() => openTrackMenu(id)}
                >
                  <MoreHorizontal />
                </IconButton>
              </div>
              {listId && entries && (
                <div className="playlist-row-actions">
                  <IconButton
                    label={t(`Move up ${track.title}`, `上移 ${track.title}`)}
                    disabled={index === 0}
                    onClick={() =>
                      player.editPlaylist(listId, entries[index].id, -1)
                    }
                  >
                    <ArrowUp />
                  </IconButton>
                  <IconButton
                    label={t(`Move down ${track.title}`, `下移 ${track.title}`)}
                    disabled={index === ids.length - 1}
                    onClick={() =>
                      player.editPlaylist(listId, entries[index].id, 1)
                    }
                  >
                    <ArrowDown />
                  </IconButton>
                  <IconButton
                    label={t(`Remove ${track.title}`, `移除 ${track.title}`)}
                    onClick={() =>
                      player.editPlaylist(listId, entries[index].id, "remove")
                    }
                  >
                    <X />
                  </IconButton>
                </div>
              )}
            </div>
          );
        })}
      </div>
    );
  }
  function AlbumCards({ values }: { values: Release[] }) {
    return (
      <div className="album-grid">
        {values.map((release, index) => (
          <article className="album-card" key={release.id}>
            <div className="album-image">
              <a
                id={`album-${release.id}`}
                href={`#/album/${release.id}`}
                onClick={(e) => {
                  e.preventDefault();
                  navigate(`/album/${release.id}`);
                }}
                aria-label={t(`Open ${release.title}`, `打开 ${release.title}`)}
              >
                <Artwork release={release} eager={index < 4} />
              </a>
              <button
                className="cover-play"
                aria-label={t(`Play ${release.title}`, `播放 ${release.title}`)}
                onClick={() => player.playList(release.trackIds)}
              >
                <Play size={19} fill="currentColor" />
              </button>
            </div>
            <div className="album-caption">
              <a
                href={`#/album/${release.id}`}
                onClick={(e) => {
                  e.preventDefault();
                  navigate(`/album/${release.id}`);
                }}
              >
                <h2>{release.title}</h2>
                <span>{zh ? release.tagZh : release.tag}</span>
              </a>
              <span className="album-index">
                {String(release.number).padStart(2, "0")}
              </span>
            </div>
          </article>
        ))}
      </div>
    );
  }
  const queueContent = (
    <>
      <div className="queue-head">
        <div>
          <span className="eyebrow">
            {t("THE LISTENING LINE", "接下来的聆听")}
          </span>
          <h2>{t("Your queue", "播放队列")}</h2>
        </div>
        <IconButton
          label={t("Close queue", "关闭队列")}
          onClick={() => setQueueOpen(false)}
        >
          <X />
        </IconButton>
      </div>
      {current && currentRelease ? (
        <>
          <span className="queue-section">
            {playing
              ? t("NOW PLAYING", "正在播放")
              : t("CURRENT TRACK", "当前曲目")}
          </span>
          <button className="queue-current" onClick={() => setListenOpen(true)}>
            <Artwork release={currentRelease} />
            <span>
              <strong>{current.title}</strong>
              <small>{current.artist}</small>
            </span>
            {playing ? (
              <span className="equalizer">
                <i />
                <i />
                <i />
              </span>
            ) : (
              <Maximize2 size={16} />
            )}
          </button>
        </>
      ) : (
        <p className="muted">
          {t("Choose a song to begin.", "选一首歌，开始吧。")}
        </p>
      )}
      <div className="queue-section">
        <span>{t("UP NEXT", "接下来")}</span>
        <span>{upcoming.length}</span>
      </div>
      <div className="queue-items">
        {upcoming.map((e, i) => {
          const tr = trackById.get(e.trackId)!;
          return (
            <div className="queue-item" key={e.id} data-entry={e.id}>
              <Artwork release={releaseFor(e.trackId)} />
              <button
                className="queue-title"
                onClick={() => player.playEntry(e.id)}
                aria-label={t(
                  `Play queued ${tr.title}`,
                  `播放队列中的 ${tr.title}`,
                )}
              >
                <strong>{tr.title}</strong>
                <span>
                  {tr.artist} · {time(tr.duration)}
                </span>
              </button>
              <div className="queue-move">
                <IconButton
                  label={t(`Move up ${tr.title}`, `上移 ${tr.title}`)}
                  disabled={i === 0}
                  onClick={() => player.move(e.id, -1)}
                >
                  <ArrowUp />
                </IconButton>
                <IconButton
                  label={t(`Move down ${tr.title}`, `下移 ${tr.title}`)}
                  disabled={i === upcoming.length - 1}
                  onClick={() => player.move(e.id, 1)}
                >
                  <ArrowDown />
                </IconButton>
                <IconButton
                  label={t(
                    `Remove queued ${tr.title}`,
                    `从队列移除 ${tr.title}`,
                  )}
                  onClick={() => player.remove(e.id)}
                >
                  <X />
                </IconButton>
              </div>
            </div>
          );
        })}
      </div>
      {!upcoming.length && (
        <div className="queue-empty">
          <ListMusic />
          <p>
            {t(
              "Leave a little room for what comes next.",
              "为接下来的音乐，留一点位置。",
            )}
          </p>
          <small>
            {t(
              "Add songs from any album using its ••• menu.",
              "从任意歌曲的 ••• 菜单加入下一首。",
            )}
          </small>
        </div>
      )}
      <p className="queue-foot">
        {t(
          "Keep browsing. The music stays with you.",
          "继续翻看，音乐会一直在。",
        )}
      </p>
    </>
  );
  const modeText = {
    sequence: t("In order", "顺序播放"),
    "repeat-all": t("Repeat queue", "列表循环"),
    "repeat-one": t("Repeat track", "单曲循环"),
  };
  const cycleMode = () => {
    const modes = ["sequence", "repeat-all", "repeat-one"] as const;
    player.mode(modes[(modes.indexOf(s.mode) + 1) % 3]);
  };
  const transport = (
    <div className="transport">
      <IconButton
        label={t("Previous track", "上一首")}
        disabled={!current}
        onClick={() => player.previous()}
      >
        <SkipBack fill="currentColor" />
      </IconButton>
      <IconButton
        label={playing || busy ? t("Pause", "暂停") : t("Play", "播放")}
        className={`primary-play ${busy ? "loading" : ""}`}
        disabled={!current}
        onClick={() => player.toggle()}
      >
        {playing || busy ? (
          <Pause fill="currentColor" />
        ) : (
          <Play fill="currentColor" />
        )}
      </IconButton>
      <IconButton
        label={t("Next track", "下一首")}
        disabled={!current}
        onClick={() => player.next()}
      >
        <SkipForward fill="currentColor" />
      </IconButton>
    </div>
  );
  const seek = (
    <div className="seek">
      <span>{time(s.position)}</span>
      <input
        aria-label={t("Playback position", "播放进度")}
        type="range"
        min="0"
        max={current?.duration || 1}
        step="1"
        value={s.position}
        disabled={!current}
        onChange={(e) => player.seek(Number(e.target.value))}
        style={
          {
            "--progress": `${(s.position / (current?.duration || 1)) * 100}%`,
          } as CSSProperties
        }
      />
      <span>{time(current?.duration || 0)}</span>
    </div>
  );
  const sortedReleases = [...releases].sort((a, b) =>
    s.sort === "title"
      ? a.title.localeCompare(b.title)
      : s.sort === "artist"
        ? a.artist.localeCompare(b.artist) || a.title.localeCompare(b.title)
        : a.number - b.number,
  );
  const visibleReleases =
    route === "/saved"
      ? sortedReleases.filter((r) => s.albumLikes.includes(r.id))
      : route === "/recent" && s.sort === "collection"
        ? [...sortedReleases].reverse()
        : sortedReleases;
  const visibleTrackIds = visibleReleases
    .flatMap((r) => r.trackIds)
    .sort((a, b) =>
      s.sort === "title"
        ? trackById.get(a)!.title.localeCompare(trackById.get(b)!.title)
        : s.sort === "artist"
          ? trackById.get(a)!.artist.localeCompare(trackById.get(b)!.artist) ||
            trackById.get(a)!.title.localeCompare(trackById.get(b)!.title)
          : 0,
    );
  const lowerQuery = query.toLocaleLowerCase().trim();
  const matchingAlbums = releases.filter((r) =>
    `${r.title} ${r.titleZh} ${r.tag} ${r.tagZh}`
      .toLocaleLowerCase()
      .includes(lowerQuery),
  );
  const matchingTracks = tracks.filter((tr) =>
    `${tr.title} ${tr.artist} ${tr.composer}`
      .toLocaleLowerCase()
      .includes(lowerQuery),
  );
  const credits = route === "/about";
  return (
    <div className={`app ${queueOpen && !mobile ? "with-queue" : ""}`}>
      <a
        className="skip-link"
        href="#main"
        onClick={(e) => {
          e.preventDefault();
          pane.current?.focus();
        }}
      >
        {t("Skip to music", "跳到音乐内容")}
      </a>
      {!mobile && <aside className="sidebar">{navigation}</aside>}
      <div className="workspace">
        <header className="topbar">
          {mobile ? (
            <IconButton
              label={t("Open navigation", "打开导航")}
              onClick={() => setMenuOpen(true)}
            >
              <Menu />
            </IconButton>
          ) : (
            <IconButton
              label={t("Go back", "返回")}
              disabled={route === "/library"}
              onClick={back}
            >
              <ArrowLeft />
            </IconButton>
          )}
          <div className="search-box">
            <Search size={18} />
            <input
              aria-label={t("Search music", "搜索音乐")}
              placeholder={t("Find something good", "找一首想听的歌")}
              value={query}
              onChange={(e) => search(e.target.value)}
            />
            {query && (
              <IconButton
                label={t("Clear search", "清空搜索")}
                onClick={() => search("")}
              >
                <X size={16} />
              </IconButton>
            )}
          </div>
          <button
            className="language"
            onClick={() => player.update({ language: zh ? "en" : "zh" })}
            lang={zh ? "en" : "zh-CN"}
          >
            {zh ? "EN" : "中文"}
          </button>
          <span className="top-rule" />
          <IconButton
            id="queue-toggle"
            label={t("Open queue", "打开队列")}
            active={queueOpen}
            onClick={() => setQueueOpen(!queueOpen)}
          >
            <ListMusic />
          </IconButton>
        </header>
        {snap.storage !== "ok" && (
          <div className="storage-notice" role="alert">
            <span>
              {snap.storage === "write"
                ? t(
                    "Changes are only in this tab. Saving failed.",
                    "保存失败，更改仅在当前页面。",
                  )
                : snap.storage === "repaired"
                  ? t(
                      "Some saved tracks or values need repair. The original save is preserved.",
                      "部分已保存曲目或数值需要修复，原始记录已保留。",
                    )
                  : t(
                      "Your saved data could not be opened. It has not been overwritten.",
                      "无法打开已保存的数据，原始记录未被覆盖。",
                    )}
            </span>
            <button
              onClick={() =>
                download(
                  snap.storage === "write"
                    ? JSON.stringify(s)
                    : snap.raw || JSON.stringify(s),
                  "side-a-recovery.json",
                )
              }
            >
              {t("Export copy", "导出副本")}
            </button>
            {snap.storage === "write" && (
              <button onClick={() => player.retrySave()}>
                {t("Retry save", "重试保存")}
              </button>
            )}
            {snap.storage === "repaired" && (
              <button onClick={() => player.acceptRepair()}>
                {t("Use available tracks", "使用仍可用的曲目")}
              </button>
            )}
            <button onClick={() => setResetOpen(true)}>
              {t("Reset", "重置")}
            </button>
          </div>
        )}
        <main
          id="main"
          ref={pane}
          className={`main-content ${album ? "album-content" : ""}`}
          onScroll={onScroll}
          tabIndex={-1}
        >
          {album ? (
            <>
              <div className="breadcrumbs">
                <button onClick={back}>
                  <ArrowLeft size={15} />
                  {t("Back to browsing", "返回浏览")}
                </button>
                <span>
                  {t("DEMO COMPILATION", "示范合辑")} /{" "}
                  {String(album.number).padStart(2, "0")}
                </span>
              </div>
              <div
                className="album-spread"
                style={{ "--album-color": album.color } as CSSProperties}
              >
                <div className="album-art-column">
                  <Artwork release={album} eager />
                  <div className="sleeve-caption">
                    <span>SIDE A SELECTS</span>
                    <span>{String(album.number).padStart(2, "0")} / 08</span>
                  </div>
                  <div className="liner">
                    <span className="eyebrow">
                      {t("SLEEVE NOTES", "内页札记")}
                    </span>
                    <p>{zh ? album.noteZh : album.note}</p>
                    <small>
                      {t(
                        "Curated by Side A · Music by Kevin MacLeod",
                        "Side A 选曲 · 音乐：Kevin MacLeod",
                      )}
                      {album.id === "slow-motion" ? " · Erik Satie" : ""}
                    </small>
                  </div>
                </div>
                <div className="album-music-column">
                  <span className="eyebrow">
                    {zh ? album.tagZh : album.tag}
                  </span>
                  <h1>{album.title}</h1>
                  {zh && album.titleZh !== album.title && (
                    <p className="album-translation">{album.titleZh}</p>
                  )}
                  <p className="album-byline">
                    {album.artist}
                    <span>·</span>3 {t("tracks", "首")}
                    <span>·</span>
                    {time(duration(album.trackIds))}
                  </p>
                  <div className="album-buttons">
                    <button
                      className="solid-button"
                      onClick={() => player.playList(album.trackIds)}
                    >
                      <Play size={17} fill="currentColor" />
                      {t("Play album", "播放合辑")}
                    </button>
                    <button
                      className={`quiet-button ${s.albumLikes.includes(album.id) ? "liked" : ""}`}
                      aria-pressed={s.albumLikes.includes(album.id)}
                      onClick={() => player.albumLike(album.id)}
                    >
                      <Heart
                        size={18}
                        fill={
                          s.albumLikes.includes(album.id)
                            ? "currentColor"
                            : "none"
                        }
                      />
                      {s.albumLikes.includes(album.id)
                        ? t("Saved", "已收藏")
                        : t("Save album", "收藏合辑")}
                    </button>
                  </div>
                  {TrackRows({ ids: album.trackIds })}
                  <div className="record-note">
                    <span>℗</span>
                    <p>
                      {t(
                        "Original recordings, collected with care.",
                        "认真收集的原始录音。",
                      )}
                      <small>
                        {t(
                          "A demo compilation, not an official artist release.",
                          "本示范合辑并非艺术家的官方发行。",
                        )}{" "}
                        <button onClick={() => navigate("/about")}>
                          {t("Music credits ↗", "音乐署名 ↗")}
                        </button>
                      </small>
                    </p>
                  </div>
                </div>
              </div>
              <div className="section-heading">
                <h2>{t("Stay a little longer", "再听一会儿")}</h2>
                <span>{t("MORE FROM YOUR COLLECTION", "继续翻看收藏")}</span>
              </div>
              <div className="related-grid">
                {releases
                  .filter((r) => r.id !== album.id)
                  .slice(0, 3)
                  .map((r) => (
                    <button
                      key={r.id}
                      onClick={() => navigate(`/album/${r.id}`)}
                    >
                      <Artwork release={r} />
                      <span>
                        <strong>{r.title}</strong>
                        <small>{zh ? r.tagZh : r.tag}</small>
                      </span>
                      <ChevronRight size={18} />
                    </button>
                  ))}
              </div>
            </>
          ) : route.startsWith("/album/") ? (
            <div className="empty">
              <Disc3 />
              <h1>{t("Album not found", "找不到这张合辑")}</h1>
              <button
                className="solid-button"
                onClick={() => navigate("/library")}
              >
                {t("Back to collection", "回到音乐收藏")}
              </button>
            </div>
          ) : query ? (
            <>
              <div className="page-heading">
                <span className="eyebrow">
                  {t("IN YOUR LIBRARY", "在你的音乐库中")}
                </span>
                <h1>{t("Search results", "搜索结果")}</h1>
                <p>
                  {t("Finding", "正在查找")} “{query}”
                </p>
              </div>
              {matchingAlbums.length > 0 && (
                <>
                  <div className="section-heading">
                    <h2>{t("Albums", "合辑")}</h2>
                    <span>{matchingAlbums.length}</span>
                  </div>
                  {AlbumCards({ values: matchingAlbums })}
                </>
              )}
              {matchingTracks.length > 0 && (
                <>
                  <div className="section-heading">
                    <h2>
                      {matchingTracks.every((tr) =>
                        tr.artist.toLowerCase().includes(lowerQuery),
                      )
                        ? t("Artist · Kevin MacLeod", "作者 · Kevin MacLeod")
                        : t("Songs", "歌曲")}
                    </h2>
                    <span>{matchingTracks.length}</span>
                  </div>
                  {TrackRows({ ids: matchingTracks.map((tr) => tr.id) })}
                </>
              )}
              {!matchingAlbums.length && !matchingTracks.length && (
                <div className="empty">
                  <Search />
                  <h2>{t("Nothing here just yet", "还没有找到")}</h2>
                  <p>
                    {t(
                      "Try a song, an artist or an album title.",
                      "试试歌曲、作者或合辑名称。",
                    )}
                  </p>
                  <button className="quiet-button" onClick={() => search("")}>
                    {t("Clear search", "清空搜索")}
                  </button>
                </div>
              )}
            </>
          ) : credits ? (
            <section className="about">
              <span className="eyebrow">SIDE A / FRONTEND CRAFT</span>
              <h1>{t("A little room for music.", "给音乐，留一点空间。")}</h1>
              <p>
                {t(
                  "Side A is a local music-library demonstration. Eight original compilations bring together 24 complete recordings. Compilations and artwork were made for this example; they are not official releases by the musician.",
                  "Side A 是本地音乐库示例。八组原创示范合辑收录 24 首完整录音；合辑与封面专为此示例制作，并非音乐家的官方发行。",
                )}
              </p>
              <h2>{t("Your listening space", "你的聆听空间")}</h2>
              <p>
                {t(
                  "Likes, playlists, your queue and your place in a song stay in this browser. Reopening always starts paused. This app does not upload your library, use an account or contact a streaming service.",
                  "喜欢、列表、队列与播放位置保存在当前浏览器，重开时始终暂停。本应用不上传音乐库，不需要账号，也不连接流媒体服务。",
                )}
              </p>
              <div className="about-actions">
                <button
                  className="quiet-button"
                  onClick={() =>
                    download(JSON.stringify(s, null, 2), "side-a-library.json")
                  }
                >
                  <Download size={16} />
                  {t("Export my data", "导出我的数据")}
                </button>
                <button className="quiet-button" onClick={() => setImportOpen(true)}>
                  {t("Import library", "导入音乐库")}
                </button>
                <button
                  className="quiet-button"
                  onClick={() => setResetOpen(true)}
                >
                  {t("Reset Side A data", "重置 Side A 数据")}
                </button>
              </div>
              <h2>{t("Music & attribution", "音乐与署名")}</h2>
              <p>
                {t(
                  "All recordings by Kevin MacLeod (incompetech.com), licensed under Creative Commons Attribution 4.0. The three Gymnopédies were composed by Erik Satie. Full recordings are transcoded to AAC; original titles and credits are retained.",
                  "所有录音来自 Kevin MacLeod（incompetech.com），依 CC BY 4.0 使用。三首吉诺佩蒂的作曲者为 Erik Satie。完整录音转码为 AAC，保留原始题名与署名。",
                )}{" "}
                <a
                  href="https://creativecommons.org/licenses/by/4.0/"
                  target="_blank"
                  rel="noreferrer"
                >
                  CC BY 4.0 ↗
                </a>
              </p>
              <div className="credit-tracks">
                {tracks.map((tr) => (
                  <a
                    key={tr.id}
                    href={tr.sourceUrl}
                    target="_blank"
                    rel="noreferrer"
                  >
                    <span>
                      {tr.title}
                      <small>Kevin MacLeod · {tr.isrc}</small>
                    </span>
                    <ArrowUpRight size={15} />
                  </a>
                ))}
              </div>
              <h2>{t("Artwork & type", "图像与字体")}</h2>
              <p>
                {t(
                  "Cover arrangements: Faye & Cove. Blue Hour incorporates Joseph Pennell’s Night lights of Manhattan (c. 1921–1926), Library of Congress, no known restrictions on publication. Floating Cities incorporates the Apollo 17 Blue Marble photograph, NASA Johnson Space Center. No artist or institution endorsement is implied.",
                  "封面编排：Faye & Cove。Blue Hour 使用 Joseph Pennell《Night lights of Manhattan》（约 1921–1926），来自美国国会图书馆，无已知出版限制。Floating Cities 使用阿波罗 17 号蓝色弹珠照片，来自 NASA 约翰逊航天中心。不代表艺术家或机构认可本产品。",
                )}
              </p>
              <p>
                <a href="https://www.loc.gov/item/2003663794/">
                  Library of Congress ↗
                </a>{" "}
                · <a href="https://svs.gsfc.nasa.gov/30613/">NASA ↗</a> ·{" "}
                <a href="assets/fonts/OFL.txt">DM Sans / OFL-1.1 ↗</a>
              </p>
            </section>
          ) : playlist ? (
            <>
              <div className="page-heading playlist-heading">
                <span className="eyebrow">
                  {t("YOUR OWN MIX", "你的专属歌单")}
                </span>
                <h1>{playlist.name}</h1>
                <p>
                  {playlist.entries.length} {t("songs", "首歌曲")} ·{" "}
                  {time(duration(playlist.entries.map((e) => e.trackId)))}
                </p>
                <div className="album-buttons">
                  <button
                    className="solid-button"
                    disabled={!playlist.entries.length}
                    onClick={() =>
                      player.playList(playlist.entries.map((e) => e.trackId))
                    }
                  >
                    <Play size={16} fill="currentColor" />
                    {t("Play playlist", "播放列表")}
                  </button>
                  <button
                    className="quiet-button"
                    onClick={() => {
                      setListName(playlist.name);
                      setListDialog({ id: playlist.id });
                    }}
                  >
                    {t("Rename", "重命名")}
                  </button>
                </div>
              </div>
              {playlist.entries.length ? (
                TrackRows({
                  ids: playlist.entries.map((e) => e.trackId),
                  entries: playlist.entries,
                  listId: playlist.id,
                })
              ) : (
                <div className="empty">
                  <ListMusic />
                  <h2>
                    {t(
                      "Every mix starts somewhere.",
                      "每张歌单，都从一首歌开始。",
                    )}
                  </h2>
                  <p>
                    {t(
                      "Find a song, open its ••• menu and add it here.",
                      "找到一首歌，从它的 ••• 菜单加入这里。",
                    )}
                  </p>
                  <button
                    className="quiet-button"
                    onClick={() => navigate("/library")}
                  >
                    {t("Browse your music", "浏览音乐")}
                  </button>
                </div>
              )}
            </>
          ) : route.startsWith("/playlist/") ? (
            <div className="empty">
              <h1>{t("Playlist not found", "列表不存在")}</h1>
              <button onClick={() => navigate("/library")}>
                {t("Back to collection", "返回音乐收藏")}
              </button>
            </div>
          ) : route === "/liked" ? (
            <>
              <div className="page-heading">
                <span className="eyebrow">
                  {t("THE ONES YOU COME BACK TO", "总想再听一遍")}
                </span>
                <h1>
                  {t("Liked songs", "喜欢的歌曲")}
                  <Heart className="heading-heart" />
                </h1>
                <p>
                  {s.likes.length} {t("songs, kept close.", "首，放在心上。")}
                </p>
                {!!s.likes.length && (
                  <button
                    className="solid-button"
                    onClick={() => player.playList(s.likes)}
                  >
                    <Play size={16} />
                    {t("Play all", "播放全部")}
                  </button>
                )}
              </div>
              {s.likes.length ? (
                TrackRows({ ids: s.likes })
              ) : (
                <div className="empty">
                  <Heart />
                  <p>
                    {t(
                      "Tap a heart beside any song to keep it here.",
                      "点一下歌曲旁的爱心，就能把它留在这里。",
                    )}
                  </p>
                  <button
                    className="quiet-button"
                    onClick={() => navigate("/library")}
                  >
                    {t("Explore the collection", "去音乐库看看")}
                  </button>
                </div>
              )}
            </>
          ) : (
            <>
              <div className="page-heading collection-heading">
                <div>
                  <span className="eyebrow">
                    {t("GOOD MUSIC. YOUR PACE.", "好音乐，慢慢听。")}
                  </span>
                  <h1>
                    {route === "/saved"
                      ? t("Saved albums", "收藏的合辑")
                      : route === "/recent"
                        ? t("Fresh on the shelf", "最近加入")
                        : t("Your collection", "音乐收藏")}
                    <span className="heading-count">
                      {route === "/saved" ? s.albumLikes.length : "08"}
                    </span>
                  </h1>
                  <p>
                    {t(
                      "A few good records. An open afternoon.",
                      "几张好唱片，一个自在的午后。",
                    )}
                  </p>
                </div>
                <span className="collection-stamp">
                  <Disc3 size={24} />
                  <span>
                    {visibleTrackIds.length} {t("TRACKS", "首歌曲")}
                    <br />
                    {t("YOURS TO EXPLORE", "等待你发现")}
                  </span>
                </span>
              </div>
              <div className="collection-tools">
                <div className="view-tabs">
                  <button
                    className={gridMode === "albums" ? "selected" : ""}
                    onClick={() => setGridMode("albums")}
                    aria-pressed={gridMode === "albums"}
                  >
                    {t("Albums", "合辑")}
                  </button>
                  <button
                    className={gridMode === "tracks" ? "selected" : ""}
                    onClick={() => setGridMode("tracks")}
                    aria-pressed={gridMode === "tracks"}
                  >
                    {t("All songs", "全部歌曲")}
                  </button>
                </div>
                <label className="sort">
                  <SlidersHorizontal size={14} />
                  <select
                    aria-label={t("Sort collection", "排序音乐收藏")}
                    value={s.sort}
                    onChange={(e) => player.update({ sort: e.target.value })}
                  >
                    <option value="collection">
                      {t("Collection order", "收藏顺序")}
                    </option>
                    <option value="title">{t("Title A–Z", "按标题")}</option>
                    <option value="artist">{t("Artist A–Z", "按作者")}</option>
                  </select>
                </label>
              </div>
              {gridMode === "albums"
                ? AlbumCards({ values: visibleReleases })
                : TrackRows({ ids: visibleTrackIds })}
              {route === "/saved" && !s.albumLikes.length && (
                <div className="empty">
                  <Disc3 />
                  <p>
                    {t(
                      "Save an album from its sleeve page.",
                      "从合辑内页收藏你喜欢的一张。",
                    )}
                  </p>
                </div>
              )}
              <div className="collection-footer">
                <span>
                  {t(
                    "8 demo compilations · Music by Kevin MacLeod",
                    "8 组示范合辑 · 音乐：Kevin MacLeod",
                  )}
                </span>
                <button onClick={() => navigate("/about")}>
                  {t("Credits & notes", "署名与说明")}
                  <ArrowUpRight size={13} />
                </button>
              </div>
            </>
          )}
        </main>
      </div>
      {queueOpen && !mobile && (
        <aside
          className="queue-panel"
          aria-label={t("Playback queue", "播放队列")}
        >
          {queueContent}
        </aside>
      )}
      <footer
        className="player-bar"
        aria-label={t("Music player", "音乐播放器")}
      >
        <button
          className="playing-identity"
          disabled={!current}
          onClick={() => setListenOpen(true)}
          aria-label={t("Open listening view", "打开聆听视图")}
        >
          {currentRelease ? (
            <Artwork release={currentRelease} />
          ) : (
            <span className="empty-art">
              <Music2 />
            </span>
          )}
          <span>
            <strong>
              {current?.title ||
                t("Find your next favourite", "找到下一首喜欢的歌")}
            </strong>
            <small>
              {current
                ? `${current.artist} · ${currentRelease!.title}`
                : t(
                    "Pick a record. Make yourself at home.",
                    "选一张唱片，放松一点。",
                  )}
            </small>
          </span>
          {current && <Maximize2 size={15} />}
        </button>
        <div className="player-centre">
          {transport}
          {seek}
        </div>
        <div className="player-extras">
          <IconButton
            label={modeText[s.mode]}
            active={s.mode !== "sequence"}
            onClick={cycleMode}
          >
            {s.mode === "repeat-one" ? <Repeat1 /> : <Repeat />}
          </IconButton>
          {snap.volumeSupported && (
            <label className="volume">
              <Volume2 size={18} />
              <input
                type="range"
                min="0"
                max="1"
                step=".01"
                value={s.volume}
                aria-label={t("Volume", "音量")}
                onChange={(e) => player.volume(Number(e.target.value))}
              />
            </label>
          )}
          <IconButton
            label={t("Open queue", "打开队列")}
            active={queueOpen}
            onClick={() => setQueueOpen(!queueOpen)}
          >
            <ListMusic />
          </IconButton>
        </div>
        {snap.error && (
          <div className="media-error" role="alert">
            <span>
              {snap.error === "blocked"
                ? t(
                    "Playback was blocked. Press play to try again.",
                    "播放被浏览器阻止，请点播放重试。",
                  )
                : t(
                    "This recording could not play. Retry or choose another.",
                    "此录音无法播放，请重试或选择另一首。",
                  )}
            </span>
            <button onClick={() => void player.play()}>
              {t("Retry", "重试")}
            </button>
          </div>
        )}
      </footer>
      {toast && (
        <div className="toast" role="status">
          <Check size={16} />
          {toast}
        </div>
      )}
      {menuOpen && mobile && (
        <Modal
          title={t("Your music", "你的音乐")}
          close={() => setMenuOpen(false)}
          className="nav-dialog"
        >
          {navigation}
        </Modal>
      )}
      {queueOpen && mobile && (
        <Modal
          title={t("Playback queue", "播放队列")}
          close={() => setQueueOpen(false)}
          className="queue-dialog"
        >
          {queueContent}
        </Modal>
      )}
      {trackMenu && (
        <Modal
          title={trackById.get(trackMenu)!.title}
          close={() => setTrackMenu(null)}
          className="track-dialog"
        >
          <div className="menu-actions">
            <button onClick={() => add(trackMenu, true)}>
              <SkipForward />
              {t("Play next", "下一首播放")}
            </button>
            <button onClick={() => add(trackMenu, false)}>
              <ListMusic />
              {t("Add to end of queue", "加入队尾")}
            </button>
            <button
              onClick={() => {
                player.like(trackMenu);
                setTrackMenu(null);
              }}
            >
              <Heart />
              {s.likes.includes(trackMenu)
                ? t("Remove from liked songs", "取消喜欢")
                : t("Like this song", "喜欢这首歌")}
            </button>
          </div>
          <div className="playlist-picker">
            <span className="eyebrow">
              {t("ADD TO A PLAYLIST", "加入个人列表")}
            </span>
            {s.playlists.map((p) => (
              <button
                key={p.id}
                onClick={() => {
                  player.addToPlaylist(p.id, trackMenu);
                  notify(t(`Added to ${p.name}`, `已加入 ${p.name}`));
                  setTrackMenu(null);
                }}
              >
                <ListMusic size={17} />
                <span>{p.name}</span>
                <Plus size={15} />
              </button>
            ))}
            <button onClick={() => newList(trackMenu)}>
              <Plus size={17} />
              {t("New playlist", "新建列表")}
            </button>
          </div>
        </Modal>
      )}
      {listDialog && (
        <Modal
          title={
            listDialog.id
              ? t("Rename playlist", "重命名列表")
              : t("Make a little mix", "做一张自己的歌单")
          }
          close={() => setListDialog(null)}
        >
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (!listName.trim()) return;
              const id = listDialog.id;
              if (id) player.renamePlaylist(id, listName);
              else player.createPlaylist(listName, listDialog.trackId);
              setListDialog(null);
              notify(
                player.getSnapshot().storage === "ok"
                  ? t("Playlist saved", "列表已保存")
                  : t("Playlist updated in this tab", "列表仅在本页更新"),
              );
            }}
          >
            <label className="name-field">
              {t("Playlist name", "列表名称")}
              <input
                autoFocus
                value={listName}
                onChange={(e) => setListName(e.target.value)}
                maxLength={120}
                required
                placeholder={t("Sunday, no plans", "周日，没有计划")}
              />
            </label>
            <button
              className="solid-button"
              disabled={!listName.trim()}
              type="submit"
            >
              {t("Save playlist", "保存列表")}
            </button>
          </form>
        </Modal>
      )}
      {importOpen && (
        <Modal title={t("Bring your library", "带回你的音乐库")} close={() => setImportOpen(false)} className="transfer-dialog">
          <LibraryTransfer player={player} zh={zh} download={download} imported={mode => {
            clearTimeout(scrollTimer.current);
            if (mode === "replace") {
              const path = player.getSnapshot().saved.route;
              routeRef.current = path;
              history.replaceState(null, "", `#${path}`);
              setRoute(path);
              setQueueOpen(false);
              setListenOpen(false);
              requestAnimationFrame(() => pane.current?.focus({ preventScroll: true }));
            }
            setImportOpen(false);
            notify(mode === "merge" ? t("Library added. Keep listening.", "音乐库已加入，继续聆听。") : (player.getSnapshot().saved.language === "zh" ? "音乐库已恢复，当前暂停。" : "Library restored, paused."));
          }} />
        </Modal>
      )}
      {resetOpen && (
        <Modal
          title={t("Reset Side A?", "重置 Side A？")}
          close={() => setResetOpen(false)}
        >
          <p>
            {t(
              "This removes only Side A’s saved likes, playlists, queue and position from this browser. You can export a copy first.",
              "这只会移除当前浏览器中 Side A 的喜欢、列表、队列和进度。你可以先导出副本。",
            )}
          </p>
          <div className="about-actions">
            <button
              className="quiet-button"
              onClick={() =>
                download(
                  snap.storage === "write"
                    ? JSON.stringify(s, null, 2)
                    : snap.raw || JSON.stringify(s, null, 2),
                  "side-a-backup.json",
                )
              }
            >
              {t("Export a copy", "导出副本")}
            </button>
            <button
              className="solid-button"
              onClick={() => {
                player.reset();
                if (player.getSnapshot().storage === "ok") {
                  setResetOpen(false);
                  history.replaceState(null, "", "#/library");
                  setRoute("/library");
                }
              }}
            >
              {t("Reset this app", "重置此应用")}
            </button>
          </div>
        </Modal>
      )}
      {listenOpen && current && currentRelease && (
        <Modal
          title={t("Listening room", "聆听空间")}
          close={() => setListenOpen(false)}
          className="listening-dialog"
        >
          <div className="listening-spread">
            <div className="listening-cover">
              <Artwork release={currentRelease} eager />
              <div className="listening-edition">
                <span>
                  SIDE A SELECTS /{" "}
                  {String(currentRelease.number).padStart(2, "0")}
                </span>
                <span>{t("DEMO COMPILATION", "示范合辑")}</span>
              </div>
            </div>
            <div className="listening-information">
              <span className="eyebrow">
                {playing
                  ? t("NOW PLAYING", "正在播放")
                  : busy
                    ? t("LOADING", "正在载入")
                    : t("PAUSED", "已暂停")}
              </span>
              <h1>{current.title}</h1>
              <p>{current.artist}</p>
              <button
                className="listening-album"
                onClick={() => {
                  setListenOpen(false);
                  navigate(`/album/${currentRelease.id}`);
                }}
              >
                {currentRelease.title}
                <ArrowUpRight size={16} />
              </button>
              <div className="listening-controls">
                {transport}
                {seek}
                <button className="mode-text" onClick={cycleMode}>
                  {s.mode === "repeat-one" ? (
                    <Repeat1 size={16} />
                  ) : (
                    <Repeat size={16} />
                  )}{" "}
                  {modeText[s.mode]}
                </button>
                {snap.volumeSupported && (
                  <label className="listening-volume">
                    <Volume2 size={16} />
                    <input
                      aria-label={t("Volume", "音量")}
                      type="range"
                      min="0"
                      max="1"
                      step=".01"
                      value={s.volume}
                      onChange={(e) => player.volume(Number(e.target.value))}
                    />
                  </label>
                )}
              </div>
              <div className="album-journey">
                <span className="eyebrow">
                  {t("IN THIS COMPILATION", "在这张合辑里")}
                </span>
                {currentRelease.trackIds.map((id, i) => (
                  <button
                    key={id}
                    className={id === current.id ? "selected" : ""}
                    onClick={() => player.playList(currentRelease.trackIds, i)}
                  >
                    <span>{String(i + 1).padStart(2, "0")}</span>
                    <strong>{trackById.get(id)!.title}</strong>
                    {id === current.id ? (
                      <span>{playing ? "♫" : "Ⅱ"}</span>
                    ) : (
                      <span>{time(trackById.get(id)!.duration)}</span>
                    )}
                  </button>
                ))}
              </div>
              {snap.error && (
                <p role="alert">
                  {t(
                    "Audio unavailable. Return to the player to retry.",
                    "音频不可用，请返回播放器重试。",
                  )}
                </p>
              )}
              <button
                className="return-browsing"
                onClick={() => setListenOpen(false)}
              >
                <ArrowLeft size={16} />
                {t("Back to where you were", "回到刚才的位置")}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
