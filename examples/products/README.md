# Product examples

[Frontend Craft](../../README.md) · [中文入口](../../README.zh-CN.md)

This package contains **[Side A](music-library/README.md)**, a complete local
music-library example. Browse a compilation while another song keeps playing,
arrange what comes next, make a playlist, and return to the same listening place.
Its eight authored compilations contain 24 complete, attributed recordings.

The product has its own React/TypeScript/Vite package. It is separate from the
dependency-free [mechanism studies](../showcase/README.md) and
[note-editing workflow](../workflow/README.md). It does not call a model or
demonstrate an autonomous FC execution, measured improvement, or accepted style.

## Run locally

Use Node.js 22.12+ (or 20.19+ as supported by Vite) and npm. From this directory:

```bash
npm ci
# Install FFmpeg (including ffprobe) separately, then explicitly fetch the music.
npm run media:fetch
npm run media:check
npm run dev
```

Open [Side A](http://127.0.0.1:4216/). The port is fixed; a busy port fails
explicitly. The page loads its fonts, artwork and prepared music from local files.
Audio binaries are deliberately excluded from Git. `media:fetch` downloads the
24 official MP3 recordings and creates full AAC 96 kb/s derivatives with FFmpeg;
`media:check` checks each local AAC duration against the manifest within one second.
Use `npm run media:fetch -- --id usuan1100137` for one recording. Existing valid
files are reused; invalid existing files are preserved with a move-aside error.
Interrupted preparation leaves completed tracks reusable and removes temporary
partials. Neither command uploads data. Install dependencies and fetch media
explicitly; ordinary use needs no network. FFmpeg/ffprobe must be on PATH.

```bash
npm run typecheck
npm test
npm run test:media
npm run build
npm run preview
```

The production preview is [port 4217](http://127.0.0.1:4217/). The generated
`dist/music-library/` directory is self-contained and can be served under a
subdirectory. Routes use a hash, so opening an album directly needs no server
rewrite. Serve over HTTP, rather than opening `index.html` through `file:`.
Build output, dependencies and test traces are ignored.

The media server must support HTTP byte-range requests for AAC seeking. Vite
dev/preview do. Python's basic `http.server` is unsuitable for this product:
the observed Chromium runtime plays the file there but reports a zero-length
seekable range. A working subdirectory preview is:

```bash
npm run preview -- --base=/music-library/ --port=4218
```

Then open `http://127.0.0.1:4218/music-library/`.

```bash
# Install a Playwright-managed Chromium if it is not already available.
npx playwright install chromium
npm run test:e2e

# Exercise a separately running production preview or subdirectory server.
SIDE_A_URL=http://127.0.0.1:4217/ npm run test:e2e
```

Browser tests use one headless Chromium worker. They exercise real local audio,
and inject specified media/storage failures in isolated browser contexts.
Set `SIDE_A_TRACE=1` only when tracing is needed; on this host trace snapshots
can disturb the real media clock. Failed cases still capture screenshots.
Audio decoding runs once with a separate 180-second budget; responsive workflows run at both sizes. This is
product verification, not a live model evaluation. See
[evidence and limits](music-library/EVIDENCE.md).

## Sources and generated files

- `music-library/src/`: UI, queue semantics, the single audio controller, persistence.
- `music-library/fixtures/catalog.json`: real recording identity and authored compilation metadata.
- `music-library/public/`: artwork, font and notices; prepared local recordings add approximately 56 MiB and stay ignored.
- `music-library/ASSETS.json`: each asset's origin, rights, modification and local path.
- `scripts/render-covers.mjs`: canonical authored cover arrangements; run
  `node scripts/render-covers.mjs` to regenerate the eight cover SVGs and mark.
- `scripts/capture.mjs`: actual-browser captures, using a disposable library.
  After starting the production preview, run
  `CAPTURE_REVISION=my-revision node scripts/capture.mjs`. The prefix must be new;
  existing captures are never overwritten.
  It writes paired English/Chinese images to `music-library/evidence/`.
- `tests/`: queue/persistence regressions and complete browser journeys.

No original MP3 downloads, private logs, account data or credentials belong here.
The AAC recordings are full-length transcodes. Their original download URLs
and measured durations remain in the asset manifest and catalog.

## 中文

这里目前是一件完整产品：**Side A 音乐库**。先把这一件做完整并实际评审，再推进
灯具商店与创作工作台；本包没有用空页面占据后两件的位置。

运行与验证命令见上方。界面可切换中英文，曲目原题和作者保持原样。核心片段是：
播放 A 的第二首 → 浏览 B → 安排下一首和队尾 → 进入聆听空间 → 返回 B → 收藏并建歌单
→ 刷新，恢复队列与位置但保持暂停 → 导出 JSON → 在另一浏览器预览后导入。所有已准备资源本地加载；JSON 导入恢复收藏与列表，不导入私人音频，不连接流媒体账号。fresh clone 不含录音，须先自行安装 FFmpeg／ffprobe，再明确执行 `npm run media:fetch`；不会在 build 或 dev 时静默下载。
请使用支持 HTTP byte-range 的媒体服务器；已验证 Vite dev/preview。普通 Python
`http.server` 下音频可播放却无法正确定位进度，因此不适用于本产品。

这件产品有自己的依赖与资源，并非旧 Python 静态示例的另一个主题。源码、浏览器验证、
作品接受度以及发布是不同状态，不能相互代替。

Rights follow the [repository rights map](../../LICENSING.md), with third-party
assets retaining their own terms.

## Library transfer

In **About & credits**, export a healthy library, then choose **Import library**
to preview a Side A JSON file (up to 2 MiB). **Add to my library** preserves
playback, the current queue, settings and existing playlists; it unions likes
and creates independently editable copies of imported playlists. Importing the
same file again deliberately adds another copy of each playlist. **Restore this
library** requires explicit confirmation and replaces this app's saved state;
export the current library first if needed. It always restores paused.

Preview and Cancel never import. Unavailable catalog tracks are omitted only
with a repair warning. Invalid/unknown formats are rejected. The complete
candidate must save before the live library or audio changes; quota failure
leaves both unchanged and allows retry. A damaged original must be explicitly
resolved through the existing recovery controls before import can replace it.
A merge over the 2 MiB reopen limit is rejected before saving. No data leaves
the browser. This is portable JSON backup, not cloud sync or
concurrent-tab coordination.

关于页可导出并导入 Side A JSON。预览与取消不会改音乐库；“加入当前音乐库”保留
当前聆听和已有歌单，导入歌单成为独立副本；“恢复此音乐库”需要确认，会替换
当前应用数据，恢复后始终暂停。保存失败时保留导入前的数据与播放；缺失曲目会
明确提示修复。文件留在浏览器，不上传。
