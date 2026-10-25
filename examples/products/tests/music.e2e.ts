import { test, expect, type Page } from "@playwright/test";
import catalog from "../music-library/fixtures/catalog.json" with { type: "json" };
const { tracks } = catalog;

const key = "fc.side-a.v1";
async function state(page: Page) {
  return page.evaluate(
    (k) => JSON.parse(localStorage.getItem(k) || "null"),
    key,
  );
}
async function nav(page: Page, name: RegExp) {
  const opener = page.getByRole("button", {
    name: "Open navigation",
    exact: true,
  });
  if (await opener.isVisible()) await opener.click();
  await page.getByRole("button", { name }).click();
}
async function more(page: Page, title: string, action: string) {
  await page
    .getByRole("button", { name: `More for ${title}`, exact: true })
    .first()
    .click();
  await page.getByRole("button", { name: action, exact: true }).click();
}
async function playing(page: Page) {
  await expect
    .poll(() =>
      page
        .locator("audio")
        .evaluate((el: HTMLAudioElement) => !el.paused && el.currentTime > 0),
    )
    .toBe(true);
}
async function noOverflow(page: Page) {
  await expect
    .poll(() =>
      page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
    )
    .toBe(true);
  await expect
    .poll(() =>
      page
        .locator("main")
        .evaluate((el) => el.scrollWidth <= el.clientWidth + 1),
    )
    .toBe(true);
}

test("listen A / browse B / arrange / return / save / reopen paused", async ({
  page,
}) => {
  await page.goto("./");
  await expect(
    page.getByRole("heading", { name: "Your collection" }),
  ).toBeVisible();
  expect(
    await page.locator("audio").evaluate((a: HTMLAudioElement) => a.paused),
  ).toBe(true);
  await page.getByRole("link", { name: "Open Blue Hour", exact: true }).click();
  await page
    .getByRole("button", { name: "Play I Knew a Guy", exact: true })
    .click();
  await playing(page);
  const originalSource = await page
    .locator("audio")
    .evaluate((a: HTMLAudioElement) => a.currentSrc);
  await page
    .getByRole("button", { name: "Back to browsing", exact: true })
    .click();
  await page.getByRole("textbox", { name: "Search music" }).fill("Soft");
  await page
    .getByRole("link", { name: "Open Soft Focus", exact: true })
    .click();
  await more(page, "Dream Culture", "Play next");
  await more(page, "Evening Fall (Piano)", "Add to end of queue");
  await more(page, "Dream Culture", "Add to end of queue");
  await page.locator("#queue-toggle").click();
  const items = page.locator(".queue-item");
  await expect(items).toHaveCount(4);
  const occurrences = await items.evaluateAll((els) =>
    els.map((el) => el.getAttribute("data-entry")),
  );
  expect(new Set(occurrences).size).toBe(4);
  await page
    .getByRole("button", { name: "Move up Evening Fall (Piano)", exact: true })
    .click();
  await expect(items.nth(1)).toContainText("Evening Fall (Piano)");
  await items
    .last()
    .getByRole("button", { name: "Remove queued Dream Culture" })
    .click();
  await expect(items).toHaveCount(3);
  await page.getByRole("button", { name: "Close queue", exact: true }).click();
  expect(
    await page.locator("audio").evaluate((a: HTMLAudioElement) => a.currentSrc),
  ).toBe(originalSource);
  await expect(page.locator(".playing-identity")).toContainText("I Knew a Guy");
  const scroll = await page.locator("main").evaluate((el) => {
    el.scrollTop = 320;
    return el.scrollTop;
  });
  await page
    .getByRole("button", { name: "Open listening view", exact: true })
    .click();
  await expect(
    page.getByRole("dialog", { name: "Listening room" }),
  ).toContainText("I Knew a Guy");
  await page
    .getByRole("button", { name: "Back to where you were", exact: true })
    .click();
  await expect(page).toHaveURL(/album\/soft-focus/);
  expect(await page.locator("main").evaluate((el) => el.scrollTop)).toBe(
    scroll,
  );
  await page.getByRole("button", { name: "Save album", exact: true }).click();
  await page
    .getByRole("button", { name: "Like Dream Culture", exact: true })
    .click();
  await more(page, "Dream Culture", "New playlist");
  await page
    .getByRole("textbox", { name: "Playlist name" })
    .fill("Night walk / 夜行");
  await page
    .getByRole("button", { name: "Save playlist", exact: true })
    .click();
  await page.getByRole("button", { name: "中文", exact: true }).click();
  await expect(page.locator(".playing-identity")).toContainText("I Knew a Guy");
  await expect(
    page.getByRole("button", { name: "已收藏", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "EN", exact: true }).click();
  await page.getByRole("button", { name: "Pause", exact: true }).click();
  const slider = page.getByRole("slider", {
    name: "Playback position",
    exact: true,
  });
  await slider.focus();
  await slider.press("Home");
  for (let i = 0; i < 12; i++) await slider.press("ArrowRight");
  const before = await state(page);
  expect(before.position).toBeGreaterThanOrEqual(11);
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Play", exact: true }),
  ).toBeVisible();
  await expect
    .poll(() =>
      page.locator("audio").evaluate((a: HTMLAudioElement) => a.currentTime),
    )
    .toBeGreaterThanOrEqual(11);
  expect(
    await page.locator("audio").evaluate((a: HTMLAudioElement) => a.paused),
  ).toBe(true);
  const after = await state(page);
  expect(after.queue).toEqual(before.queue);
  expect(after.currentId).toBe(before.currentId);
  expect(after.likes).toEqual(before.likes);
  expect(after.playlists).toEqual(before.playlists);
  await page.getByRole("button", { name: "Play", exact: true }).click();
  await playing(page);
  await noOverflow(page);
});

test("search restores the original scroll; browser back and keyboard focus survive playback", async ({
  page,
}) => {
  await page.goto("./");
  await page
    .getByRole("button", { name: "Play Blue Hour", exact: true })
    .click();
  await playing(page);
  await page.locator("main").evaluate((el) => {
    el.scrollTop = 250;
  });
  const position = await page.locator("main").evaluate((el) => el.scrollTop);
  await page.getByRole("textbox", { name: "Search music" }).fill("Kevin");
  await expect(
    page.getByRole("heading", { name: "Artist · Kevin MacLeod" }),
  ).toBeVisible();
  await expect(page.locator(".track-row")).toHaveCount(24);
  await page
    .getByRole("textbox", { name: "Search music" })
    .fill("definitely no song");
  await expect(
    page.getByRole("heading", { name: "Nothing here just yet" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Clear search", exact: true })
    .first()
    .click();
  expect(await page.locator("main").evaluate((el) => el.scrollTop)).toBe(
    position,
  );
  await page.getByRole("textbox", { name: "Search music" }).fill("Blue");
  await page.getByRole("link", { name: "Open Blue Hour", exact: true }).click();
  const heart = page.getByRole("button", {
    name: "Like I Knew a Guy",
    exact: true,
  });
  await heart.focus();
  await expect
    .poll(() =>
      page.locator("audio").evaluate((a: HTMLAudioElement) => a.currentTime),
    )
    .toBeGreaterThan(2);
  await expect(heart).toBeFocused();
  await heart.press("Enter");
  await expect(
    page.getByRole("button", { name: "Unlike I Knew a Guy", exact: true }),
  ).toBeFocused();
  await page.goBack();
  await expect(page.getByRole("textbox", { name: "Search music" })).toHaveValue(
    "Blue",
  );
  await page.getByRole("link", { name: "Skip to music" }).focus();
  await page.keyboard.press("Enter");
  await expect(page.locator("main")).toBeFocused();
  await expect(page).toHaveURL(/search/);
});

test("playlist editing preserves duplicate occurrences, ordering and bilingual long content", async ({
  page,
}) => {
  const keyWarnings: string[] = [];
  page.on("console", message => {
    if (message.text().includes('Each child in a list')) keyWarnings.push(message.text());
  });
  await page.goto("./#/album/blue-hour");
  await more(page, "I Knew a Guy", "New playlist");
  await page.getByRole("textbox", { name: "Playlist name" }).fill("Sunday");
  await page
    .getByRole("button", { name: "Save playlist", exact: true })
    .click();
  await more(page, "I Knew a Guy", "Sunday");
  await more(page, "Just As Soon", "Sunday");
  await nav(page, /^Sunday 3$/);
  await page
    .getByRole("button", { name: "Move up Just As Soon", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Remove I Knew a Guy", exact: true })
    .first()
    .click();
  await expect(page.locator(".track-row")).toHaveCount(2);
  await expect(page.locator(".track-row").first()).toContainText(
    "Just As Soon",
  );
  await page.getByRole("button", { name: "Rename", exact: true }).click();
  await page
    .getByRole("textbox", { name: "Playlist name" })
    .fill("给慢慢走回家的夜晚：没有截断的歌单名字");
  await page
    .getByRole("button", { name: "Save playlist", exact: true })
    .click();
  await page.reload();
  await expect(
    page.getByRole("heading", {
      name: "给慢慢走回家的夜晚：没有截断的歌单名字",
    }),
  ).toBeVisible();
  await page.getByRole("button", { name: "中文", exact: true }).click();
  await expect(page.locator(".track-row")).toHaveCount(2);
  await noOverflow(page);
  await page.goto("./#/album/slow-motion");
  await expect(
    page.getByRole("heading", {
      name: "慢下来，在最后一班车开走之前",
      exact: true,
    }),
  ).toBeVisible();
  await expect(page.locator(".liner")).toBeVisible();
  await noOverflow(page);
  expect(keyWarnings).toEqual([]);
});

test("play refusal and failed media retain identity and can retry", async ({
  page,
}) => {
  await page.addInitScript(() => {
    const real = HTMLMediaElement.prototype.play;
    let first = true;
    HTMLMediaElement.prototype.play = function () {
      if (first) {
        first = false;
        return Promise.reject(
          new DOMException("gesture required", "NotAllowedError"),
        );
      }
      return real.call(this);
    };
  });
  await page.goto("./#/album/blue-hour");
  await page.getByRole("button", { name: "Play album", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("Playback was blocked");
  await expect(
    page.getByRole("button", { name: "Play", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Retry", exact: true }).click();
  await playing(page);
  await page.route(`**/${tracks[1].audio}`, (route) =>
    route.fulfill({ status: 404, body: "unavailable" }),
  );
  await page
    .getByRole("button", { name: "Play I Knew a Guy", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText(
    "This recording could not play",
  );
  await expect(page.locator(".playing-identity")).toContainText("I Knew a Guy");
  await page.unroute(`**/${tracks[1].audio}`);
  await page.getByRole("button", { name: "Retry", exact: true }).click();
  await playing(page);
});

test("storage failures preserve raw data; scoped reset leaves other applications alone", async ({
  page,
}) => {
  await page.addInitScript(
    ({ key }) => {
      localStorage.setItem(key, "{broken");
      localStorage.setItem("other-app", "keep");
    },
    { key },
  );
  await page.goto("./");
  await expect(page.getByRole("alert")).toContainText(
    "has not been overwritten",
  );
  await page.getByRole("link", { name: "Open Blue Hour", exact: true }).click();
  await page
    .getByRole("button", { name: "Like I Knew a Guy", exact: true })
    .click();
  expect(await page.evaluate((k) => localStorage.getItem(k), key)).toBe(
    "{broken",
  );
  const downloaded = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export copy", exact: true }).click();
  const stream = await (await downloaded).createReadStream();
  const chunks: Buffer[] = [];
  for await (const chunk of stream!) chunks.push(chunk);
  expect(Buffer.concat(chunks).toString()).toBe("{broken");
  await page.getByRole("button", { name: "Reset", exact: true }).click();
  await page
    .getByRole("button", { name: "Reset this app", exact: true })
    .click();
  await expect(page.getByRole("alert")).toHaveCount(0);
  expect(await page.evaluate(() => localStorage.getItem("other-app"))).toBe(
    "keep",
  );
  expect((await state(page))?.likes || []).toEqual([]);
});

test("a failed save remains in this tab and is recoverable without losing the playlist", async ({
  page,
}) => {
  await page.addInitScript(
    ({ key }) => {
      const real = Storage.prototype.setItem;
      let blocked = true;
      Object.assign(window, {
        allowSideASave: () => {
          blocked = false;
        },
      });
      Storage.prototype.setItem = function (k, value) {
        if (k === key && blocked)
          throw new DOMException("full", "QuotaExceededError");
        return real.call(this, k, value);
      };
    },
    { key },
  );
  await page.goto("./#/album/blue-hour");
  await more(page, "I Knew a Guy", "New playlist");
  await page.getByRole("textbox", { name: "Playlist name" }).fill("Kept here");
  await page
    .getByRole("button", { name: "Save playlist", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText("Saving failed");
  await expect(page.getByRole("status")).toContainText("updated in this tab");
  await page.evaluate(() =>
    (window as unknown as { allowSideASave: () => void }).allowSideASave(),
  );
  await page.getByRole("button", { name: "Retry save", exact: true }).click();
  await expect(page.getByRole("alert")).toHaveCount(0);
  await page.reload();
  expect((await state(page)).playlists[0].name).toBe("Kept here");
});

test("all 24 local recordings decode with distinct content, actual duration and nonzero PCM signal", async ({
  page,
}, info) => {
  test.skip(info.project.name !== "wide", "Same static files for both widths.");
  test.setTimeout(180000); // Decode all 56 MiB sequentially; interaction checks retain 45 s.
  await page.goto("./");
  const result = await page.evaluate(async (tracks) => {
    const context = new AudioContext();
    const results = [];
    for (const track of tracks) {
      const response = await fetch(track.audio);
      if (!response.ok) throw new Error(track.title);
      const decoded = await context.decodeAudioData(
        await response.arrayBuffer(),
      );
      const data = decoded.getChannelData(0);
      let squares = 0;
      const samples: number[] = [];
      for (let i = 0; i < data.length; i += 200) {
        squares += data[i] ** 2;
      }
      for (let j = 1; j <= 8; j++)
        samples.push(
          Number(data[Math.floor((data.length * j) / 10)].toFixed(6)),
        );
      results.push({
        title: track.title,
        duration: decoded.duration,
        rms: Math.sqrt(squares / (data.length / 200)),
        samples,
      });
    }
    await context.close();
    return results;
  }, tracks);
  expect(result).toHaveLength(24);
  expect(new Set(result.map((r) => JSON.stringify(r.samples))).size).toBe(24);
  result.forEach((r, i) => {
    expect(Math.abs(r.duration - tracks[i].duration)).toBeLessThan(1);
    expect(r.rms).toBeGreaterThan(0.001);
  });
  await info.attach("decoded-audio.json", {
    body: JSON.stringify(result, null, 2),
    contentType: "application/json",
  });
});

test("covers render; intermediate width, 200% reflow, reduced motion and modal keyboard exit", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("./");
  await page.locator("main").evaluate((el) => {
    el.scrollTop = el.scrollHeight;
  });
  await expect
    .poll(() =>
      page
        .locator(".album-image img")
        .evaluateAll((imgs) =>
          imgs.every(
            (el) =>
              (el as HTMLImageElement).complete &&
              (el as HTMLImageElement).naturalWidth > 0,
          ),
        ),
    )
    .toBe(true);
  await page.setViewportSize({ width: 1024, height: 800 });
  await noOverflow(page);
  await page.setViewportSize({ width: 720, height: 500 }); // 1440x1000 at 200%: same CSS viewport/reflow.
  await noOverflow(page);
  await page.locator("#queue-toggle").click();
  await expect(
    page.getByRole("dialog", { name: "Playback queue" }),
  ).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.locator("#queue-toggle")).toBeFocused();
  await page.getByRole("textbox", { name: "Search music" }).fill("Gymnopedie");
  await expect(page.locator(".track-row")).toHaveCount(3);
  await noOverflow(page);
});
