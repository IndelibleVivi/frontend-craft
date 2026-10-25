import { test, expect, type Page } from "@playwright/test";
import { readFile } from "node:fs/promises";
const key = "fc.side-a.v1";
async function about(page: Page) {
  const menu = page.getByRole("button", { name: "Open navigation", exact: true });
  if (await menu.isVisible()) await menu.click();
  await page.getByRole("button", { name: "About & credits", exact: true }).click();
}
async function choose(page: Page, value: string) {
  await page.getByLabel("Choose a library file").setInputFiles({ name: "night-walk.json", mimeType: "application/json", buffer: Buffer.from(value) });
}
async function snapshot(page: Page) {
  return page.evaluate(k => JSON.parse(localStorage.getItem(k)!), key);
}
test("export / preview / merge while listening / replace / reopen paused", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", e => errors.push(e.message));
  await page.goto("./");
  await page.getByRole("link", { name: "Open Blue Hour", exact: true }).click();
  await page.getByRole("button", { name: "Play I Knew a Guy", exact: true }).click();
  await expect.poll(() => page.locator("audio").evaluate((a: HTMLAudioElement) => !a.paused && a.currentTime > 0)).toBe(true);
  await page.getByRole("button", { name: "More for I Knew a Guy", exact: true }).click();
  await page.getByRole("button", { name: "New playlist", exact: true }).click();
  await page.getByLabel("Playlist name").fill("Night walk / 夜行");
  await page.getByRole("button", { name: "Save playlist", exact: true }).click();
  await about(page);
  const before = await snapshot(page);
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export my data", exact: true }).click();
  const file = await download;
  const raw = await readFile((await file.path())!, "utf8");
  expect(JSON.parse(raw).playlists[0].name).toBe("Night walk / 夜行");
  const audioBefore = await page.locator("audio").evaluate((a: HTMLAudioElement) => ({ src: a.currentSrc, time: a.currentTime }));
  await page.getByRole("button", { name: "Import library", exact: true }).click();
  await choose(page, raw);
  await expect(page.getByRole("dialog")).toContainText("night-walk.json");
  expect((await snapshot(page)).playlists).toEqual(before.playlists);
  await page.getByRole("button", { name: "Add to my library", exact: true }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  const merged = await snapshot(page);
  expect(merged.playlists).toHaveLength(2);
  expect(new Set(merged.playlists.map((p: {id:string}) => p.id)).size).toBe(2);
  expect(merged.queue).toEqual(before.queue);
  expect(await page.locator("audio").evaluate((a: HTMLAudioElement) => a.currentSrc)).toBe(audioBefore.src);
  await expect.poll(() => page.locator("audio").evaluate((a: HTMLAudioElement) => a.currentTime)).toBeGreaterThan(audioBefore.time);
  await page.getByRole("button", { name: "Import library", exact: true }).click();
  await choose(page, raw);
  await page.getByRole("radio", { name: "Restore this library", exact: false }).check();
  const apply = page.getByRole("button", { name: "Replace and reopen paused", exact: true });
  await expect(apply).toBeDisabled();
  await page.getByRole("checkbox", { name: "Replace my current Side A library with this file.", exact: true }).check();
  await apply.click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect.poll(() => page.locator("audio").evaluate((a: HTMLAudioElement) => a.paused)).toBe(true);
  expect((await snapshot(page)).playlists).toEqual(before.playlists);
  await page.reload();
  expect((await snapshot(page)).playlists).toEqual(before.playlists);
  expect(await page.locator("audio").evaluate((a: HTMLAudioElement) => a.paused)).toBe(true);
  expect(errors).toEqual([]);
});

test("invalid file and failed import preserve current data; cancel restores focus", async ({ page }) => {
  await page.goto("./");
  await about(page);
  const raw = JSON.stringify(await snapshot(page));
  const trigger = page.getByRole("button", { name: "Import library", exact: true });
  await trigger.click();
  await choose(page, '{"schemaVersion":999}');
  await expect(page.getByRole("alert")).toContainText("not a supported Side A library");
  await expect(page.getByRole("button", { name: "Add to my library", exact: true })).toHaveCount(0);
  await choose(page, raw);
  await page.evaluate(() => { Storage.prototype.setItem = () => { throw new DOMException("full", "QuotaExceededError"); }; });
  const original = await snapshot(page);
  await page.getByRole("button", { name: "Add to my library", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("could not save this import");
  expect(await snapshot(page)).toEqual(original);
  await page.keyboard.press("Escape");
  await expect(trigger).toBeFocused();
});

test("Chinese preview reports missing tracks and remains usable at narrow widths", async ({ page }) => {
  await page.goto("./");
  await about(page);
  const value = await snapshot(page);
  value.likes = ["not-in-this-catalog"];
  await page.getByRole("button", { name: "中文", exact: true }).click();
  await page.getByRole("button", { name: "导入音乐库", exact: true }).click();
  await page.getByLabel("选择音乐库文件").setInputFiles({ name: "夜行与清晨的很长音乐收藏备份.json", mimeType: "application/json", buffer: Buffer.from(JSON.stringify(value)) });
  await expect(page.getByRole("status")).toContainText("部分曲目");
  const dialog = page.getByRole("dialog");
  expect(await dialog.evaluate(el => el.scrollWidth <= el.clientWidth + 1)).toBe(true);
  await page.getByRole("button", { name: "加入当前音乐库", exact: true }).click();
  await expect(dialog).toHaveCount(0);
  expect((await snapshot(page)).likes).toEqual([]);
});
