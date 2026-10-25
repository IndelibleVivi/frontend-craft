# Side A — observed evidence

## Current continuation — 2026-10-25

The existing product candidate now supports a complete JSON export/preview/merge/
restore path. The 25 domain/controller tests and 8 offline media-preparation tests
passed, along with typecheck and the production build. Production Chromium
journeys passed all 20 interaction cases across 1440 × 1000 and 390 × 844:
browsing while listening, queue/list editing, reopen paused, error/retry, storage
protection, JSON download/upload, continuous merge, explicit paused replacement,
Cancel/focus return, and a Chinese missing-track preview. These are synthetic
personal libraries; the actual music remains the attributed recordings.

The 24 complete local AAC recordings separately decoded, retained distinct sampled
PCM, nonzero signal and manifest duration within one second. This took about
90 seconds on this host; the recording test now has its own 180-second budget.
The general interaction timeout stays 45 seconds. It is not an audio-quality
assessment or a performance guarantee. The same files need not decode twice for
wide and narrow layouts.

Tracing affected observation: the new wide transfer journey twice showed a
playing element at zero time with trace recording; the identical untraced test
passed, and standalone wide/narrow probes observed HTTP 206 and advancing time.
That supports an instrumentation-related explanation on this host, not a general
browser diagnosis. The default suite uses one managed Chromium worker without
trace recording. `SIDE_A_TRACE=1` opts into traces for diagnosis; failed tests
still capture screenshots. No playback assertion was removed. The final production build also passed all
20 interaction cases under `/music-library/`; the identical static recordings
were not decoded again for this path-only check.

The importer also rejects a combined library over the 2 MiB recovery limit before
writing; two individually valid files must not create an unreadable next save.
Malformed data, duplicate occurrence IDs, missing catalog items, normalized view
values and quota failure have independent regression cases. The original save
is preserved when its recovery has not been explicitly resolved.

Audio preparation has 8 offline boundary checks: explicit mode, prerequisite
failure before network, official source/path constraints, no-clobber publication,
interruption cleanup, existing files, and full-duration validation. This host
lacks ffmpeg/ffprobe on PATH, so **actual download/transcode through the new command
is unverified**. Its existing local recordings were exercised in Chromium; that
does not validate reconstruction from a fresh clone.

New captures retain the older images and use an explicit revision prefix:

| Current state | English | 中文 |
| --- | --- | --- |
| Browsing while listening | [View](evidence/20261025-browse-and-listen-wide.en.png) | [查看](evidence/20261025-browse-and-listen-wide.zh-CN.png) |
| File preview, wide | [View](evidence/20261025-transfer-wide.en.png) | [查看](evidence/20261025-transfer-wide.zh-CN.png) |
| File preview, narrow | [View](evidence/20261025-transfer-narrow.en.png) | [查看](evidence/20261025-transfer-narrow.zh-CN.png) |
| Explicit restoration, narrow | [View](evidence/20261025-restore-narrow.en.png) | [查看](evidence/20261025-restore-narrow.zh-CN.png) |

The source, font, eight authored covers, these captured states and the observed
use resolve through [catalog.json](catalog.json). The catalog's current source
assets carry byte digests; editing a source deliberately makes that captured
identity stale until a new catalog revision records it. Gallery output is derived.
This is a practiced candidate; no owner aesthetic acceptance, second host,
public deployment or autonomous FC improvement is established.

## Earlier observation — 2026-10-02

Checked on 2026-10-02 using the local production build and Playwright-managed
headless Chromium. This document records behavior and inspected pixels;
it does not award visual acceptance or establish FC's general effectiveness.

## Reproduction

Commands run from `examples/products/`:

```bash
npm run typecheck
npm test
npm run build
npm run preview
node scripts/capture.mjs
```

For the subdirectory production check, a second terminal used:

```bash
npm run preview -- --base=/music-library/ --port=4218
SIDE_A_URL=http://127.0.0.1:4218/music-library/ npm run test:e2e
```

The resulting suite passed 15 cases with one intentional skip: the exact same
24 static audio files are decoded once in the wide project, rather than again
in the narrow project. The 14 unit cases passed separately. Typecheck and
production build completed. These counts describe this run, not quality scores.

## What was observed

| Claim | Evidence and scope |
| --- | --- |
| Listen to A while browsing B | Real `HTMLAudioElement` source and advancing currentTime remained A while search, B's detail, menus, queue and listening view changed. The full path ran at 1440 × 1000 and 390 × 844. |
| Queue identity and controls | Duplicate songs kept separate occurrence IDs; move/remove affected the chosen upcoming occurrence. Album playback replaced the queue; empty-queue additions remained paused. Unit cases also cover previous, repeat-one versus manual Next, repeat-all and stopping at the end. |
| Continuous browsing | Search groups returned all 24 tracks for the artist query; no-result and clear-search restored origin/scroll. Browser Back restored the search; listening/return preserved the album and position. Focus survived media updates and modal Escape returned to its trigger. |
| Durable user work | Likes, album saves, named playlists, duplicate playlist entries, ordering, queue/current occurrence and seek position survived reload. Reload remained paused; an explicit Play resumed. Language switching preserved identity and saved content. |
| Media failures | An injected `NotAllowedError` left a Play/retry state; an intercepted 404 retained song identity and recovered after retry. A unit case verifies late rejection of an old play promise cannot override the new track. |
| Storage failures | Browser-injected quota failure kept a playlist in the tab and saved it after retry. Corrupt raw data remained unchanged and its downloaded export matched the original. Reset preserved another app's key. Unit cases additionally cover unknown schema, explicit missing-track repair and position clamping. |
| Real local content | All 24 AAC recordings decoded in Chromium; durations agreed with the catalog within one second; each had nonzero PCM signal and a different sampled signal. The 8 cover images loaded. This is not subjective audition. |
| Responsive use | The complete journey ran at wide/narrow sizes, plus 1024 × 800 and 720 × 500 reflow checks. The latter models a 1440 × 1000 viewport at 200% CSS reflow; actual browser zoom was not tested. Reduced-motion media was set and modal keyboard exit was exercised. |
| Production paths | The same built output passed the suite under `/music-library/`, including direct hash routes, audio, fonts and images. No source-dev URL was used by that run. |

An initial parallel browser run stalled media time on the host; serialized
real-media journeys passed. Browser checks use one worker. This observation
does not establish a product concurrency defect or cross-device performance.
A development log also exposed missing React keys on dynamic playlist navigation;
route keys were added, both playlist journeys were rerun in development with
a console-warning assertion, and the production build was refreshed.

The first subdirectory probe used Python's basic static server. Its AAC
`seekable` range stayed `[0, 0]` despite a fully buffered recording, so seek
checks correctly failed. Vite preview served the required byte ranges and the
complete production suite passed. The [run instructions](../README.md) now
state this media-serving requirement.

## Rendered views

Captures come from the actual build. Their library data is synthetic; no
personal listening data or external product screenshot is included.

| View | English | 中文 |
| --- | --- | --- |
| Collection, 1440 × 1000 | [View](evidence/library-wide.en.png) | [查看](evidence/library-wide.zh-CN.png) |
| Browsing B, playing A, queue open | [View](evidence/browse-and-listen-wide.en.png) | [查看](evidence/browse-and-listen-wide.zh-CN.png) |
| Listening view | [View](evidence/listening-wide.en.png) | [查看](evidence/listening-wide.zh-CN.png) |
| Collection, 390 × 844 | [View](evidence/library-narrow.en.png) | [查看](evidence/library-narrow.zh-CN.png) |
| Album, 390 × 844 | [View](evidence/album-narrow.en.png) | [查看](evidence/album-narrow.zh-CN.png) |

Visual inspection checked the full compositions, relative emphasis of
browsing/playback/queue, real titles, Chinese wrapping, artwork cropping,
secondary text and controls. Internal revisions increased small text contrast
and size, retained sleeve notes on mobile, and reduced the mobile album image
so a real track appears earlier. These are specific maker judgments, not an
owner-approved style slot.

## Not established

- Subjective audio audition or a listener's assessment of the selections.
- Real phone hardware, Safari/Firefox, screen-reader output, or comprehensive WCAG conformance.
- Public deployment, streaming/account integration, imported personal music, or cross-browser synchronization.
- Owner aesthetic acceptance, autonomous first-draft quality, fewer future interventions, or a model ranking.

The local product is runnable and its named checks pass. Those boundaries
remain separate from whether someone finds the experience beautiful.
