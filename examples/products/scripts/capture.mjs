// Captures the actual application with a disposable synthetic browser library.
import { chromium } from "@playwright/test";
import { existsSync, mkdirSync } from "node:fs";
const directory = new URL("../music-library/evidence/", import.meta.url);
mkdirSync(directory, { recursive: true });
const revision = process.env.CAPTURE_REVISION || new Date().toISOString().replace(/[-:TZ.]/g, "");
if (!/^[a-z0-9-]+$/i.test(revision)) throw new Error("Invalid capture revision");
for (const language of ["en", "zh-CN"])
  for (const name of ["library-wide", "browse-and-listen-wide", "listening-wide", "album-narrow", "library-narrow", "transfer-wide", "transfer-narrow", "restore-narrow"])
    if (existsSync(new URL(`${revision}-${name}.${language}.png`, directory))) throw new Error("Capture revision already exists; choose a new CAPTURE_REVISION");
const browser = await chromium.launch();
try {
  for (const language of ["en", "zh-CN"]) {
    const context = await browser.newContext({
      viewport: { width: 1440, height: 1000 },
      reducedMotion: "reduce",
    });
    const page = await context.newPage();
    await page.goto(process.env.SIDE_A_URL || "http://127.0.0.1:4217/");
    await page.locator(".album-grid img").first().waitFor();
    if (language === "zh-CN")
      await page.getByRole("button", { name: "中文", exact: true }).click();
    const shot = async (name) => {
      await page.evaluate(() => document.fonts.ready);
      await page.screenshot({
        path: new URL(`${revision}-${name}.${language}.png`, directory).pathname,
        animations: "disabled",
      });
    };
    await shot("library-wide");
    await page.locator("#album-blue-hour").click();
    await page.locator(".track-number").nth(1).click();
    await page.waitForFunction(
      () =>
        !document.querySelector("audio").paused &&
        document.querySelector("audio").currentTime > 0,
    );
    await page.locator(".related-grid>button").first().click();
    await page.locator(".track-actions .icon-button").nth(1).click();
    await page.locator(".menu-actions>button").first().click();
    await page.locator("#queue-toggle").click();
    await page.locator(".toast").waitFor({ state: "hidden" });
    await shot("browse-and-listen-wide");
    await page.locator(".playing-identity").click();
    await shot("listening-wide");
    await page.locator(".return-browsing").click();
    await page.locator(".queue-head .icon-button").click();
    await page.setViewportSize({ width: 390, height: 844 });
    await page.locator(".album-music-column h1").scrollIntoViewIfNeeded();
    await shot("album-narrow");
    await page.locator(".topbar>.icon-button").first().click();
    await page.locator(".nav-dialog .nav-item").first().click();
    await page.locator("main").evaluate((el) => {
      el.scrollTop = 0;
    });
    await shot("library-narrow");
    await page.locator(".topbar>.icon-button").first().click();
    await page.locator(".nav-dialog .nav-item").last().click();
    await page.getByRole("button", { name: language === "en" ? "Import library" : "导入音乐库", exact: true }).click();
    const saved = await page.evaluate(() => JSON.parse(localStorage.getItem("fc.side-a.v1")));
    const trackId = saved.queue[0].trackId;
    saved.playlists = [{ id: "captured-mix", name: "Night walk / 夜行", entries: [{id:"capture-one",trackId}, {id:"capture-two",trackId}] }];
    await page.locator('input[type="file"]').setInputFiles({ name: "night-walk.json", mimeType: "application/json", buffer: Buffer.from(JSON.stringify(saved)) });
    await page.locator(".transfer-preview").waitFor();
    await page.setViewportSize({ width: 1440, height: 1000 });
    await shot("transfer-wide");
    await page.setViewportSize({ width: 390, height: 844 });
    await page.locator(".transfer-dialog").evaluate(el => { el.scrollTop = 0; });
    await shot("transfer-narrow");
    await page.getByRole("radio", { name: language === "en" ? "Restore this library" : "恢复此音乐库", exact: false }).check();
    await page.getByRole("checkbox").check();
    await page.keyboard.press("Tab");
    await shot("restore-narrow");
    if (!(await page.locator(".transfer-dialog").evaluate(el => el.scrollWidth <= el.clientWidth + 1))) throw new Error("Transfer dialog overflow");
    await context.close();
  }
} finally {
  await browser.close();
}

console.log(`Captured bilingual product and transfer states: ${revision}`);
