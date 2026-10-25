import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, writeFile, mkdir, readFile, readdir, rm, symlink } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { prepareMedia, parseArgs } from '../scripts/prepare-media.mjs';

const item = { id: 'track-one', role: 'audio', dimensionsOrDuration: 12.5, localPath: 'public/assets/audio/track-one.m4a', sourceUrl: 'https://incompetech.com/music/royalty-free/mp3-royaltyfree/Test.mp3' };
async function fixture(t, entries = [item]) {
  const root = await mkdtemp(path.join(os.tmpdir(), 'side-a-media-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  await writeFile(path.join(root, 'ASSETS.json'), JSON.stringify(entries));
  return root;
}
function fakeRun(calls = []) {
  return async (command, args) => {
    calls.push([command, args]);
    if (args[0] === '-version') return 'version';
    if (command === 'ffmpeg') { await writeFile(args.at(-1), 'AAC'); return ''; }
    if (await readFile(args.at(-1), 'utf8') !== 'AAC') throw new Error('Invalid audio');
    return JSON.stringify({ streams: [{ codec_type: 'audio', codec_name: 'aac' }], format: { duration: '12.5' } });
  };
}
const options = root => ({ root, log() {}, run: fakeRun(), fetcher() { throw new Error('Unexpected network'); } });

test('CLI requires explicit mode and a complete id', () => {
  for (const args of [[], ['--id', 'one'], ['--check', '--fetch'], ['--fetch', '--id'], ['--wat']]) assert.throws(() => parseArgs(args));
  assert.deepEqual(parseArgs(['--fetch', '--id', 'track-one']), { mode: 'fetch', id: 'track-one' });
  const result = spawnSync(process.execPath, [new URL('../scripts/prepare-media.mjs', import.meta.url).pathname], { encoding: 'utf8' });
  assert.equal(result.status, 1);
  assert.match(result.stderr, /Usage:/);
});
test('check is offline and reports missing, ready, invalid; only audio role is selected', async t => {
  const root = await fixture(t, [item, { role: 'cover', id: 'cover' }]);
  assert.deepEqual(await prepareMedia({ ...options(root), mode: 'check' }), [{ id: item.id, status: 'missing' }]);
  await mkdir(path.join(root, 'public/assets/audio'), { recursive: true });
  const target = path.join(root, item.localPath);
  await writeFile(target, 'AAC');
  assert.equal((await prepareMedia({ ...options(root), mode: 'check' }))[0].status, 'ready');
  await writeFile(target, 'user file');
  assert.equal((await prepareMedia({ ...options(root), mode: 'check' }))[0].status, 'invalid');
  await assert.rejects(prepareMedia({ ...options(root), mode: 'fetch' }), /move it aside/);
  assert.equal(await readFile(target, 'utf8'), 'user file');
});
test('preflight failure occurs before fetch', async t => {
  const root = await fixture(t);
  let fetched = false;
  await assert.rejects(prepareMedia({ ...options(root), mode: 'fetch', run: async command => { if (command === 'ffmpeg') throw new Error('ffmpeg unavailable'); }, fetcher() { fetched = true; } }), /ffmpeg unavailable/);
  assert.equal(fetched, false);
});
test('fetch transcodes using argument arrays, publishes atomically, skips ready files and cleans temp files', async t => {
  const root = await fixture(t);
  const calls = [];
  let downloads = 0;
  const opts = { ...options(root), mode: 'fetch', run: fakeRun(calls), fetcher: async (url, init) => { downloads++; assert.equal(url, item.sourceUrl); assert.equal(init.redirect, 'error'); return new Response('MP3'); } };
  assert.equal((await prepareMedia(opts))[0].status, 'prepared');
  assert.equal(await readFile(path.join(root, item.localPath), 'utf8'), 'AAC');
  assert.equal((await prepareMedia(opts))[0].status, 'ready');
  assert.equal(downloads, 1);
  const args = calls.find(([command, args]) => command === 'ffmpeg' && args[0] !== '-version')[1];
  assert.ok(args.includes('96k'));
  assert.deepEqual(await readdir(path.dirname(path.join(root, item.localPath))), ['track-one.m4a']);
});
test('HTTP and transcode failures leave no output or temporary partials', async t => {
  for (const failure of ['http', 'transcode']) {
    const root = await fixture(t);
    const run = fakeRun();
    await assert.rejects(prepareMedia({ ...options(root), mode: 'fetch', run: async (command, args) => {
      if (failure === 'transcode' && command === 'ffmpeg' && args[0] !== '-version') throw new Error('decode failed');
      return run(command, args);
    }, fetcher: async () => failure === 'http' ? new Response('missing', { status: 404 }) : new Response('MP3') }), failure === 'http' ? /HTTP 404/ : /decode failed/);
    assert.deepEqual(await readdir(path.join(root, 'public/assets/audio')), []);
  }
});
test('rejects escaped paths, unapproved sources, unknown ids, and symlink destinations before network', async t => {
  for (const changed of [{ localPath: '../outside.m4a' }, { sourceUrl: 'https://example.com/test.mp3' }, { sourceUrl: 'http://incompetech.com/music/royalty-free/mp3-royaltyfree/Test.mp3' }]) {
    const root = await fixture(t, [{ ...item, ...changed }]);
    await assert.rejects(prepareMedia({ ...options(root), mode: 'fetch' }), /Unsafe|Unsupported/);
  }
  const root = await fixture(t);
  await assert.rejects(prepareMedia({ ...options(root), mode: 'fetch', id: 'unknown' }), /Unknown audio id/);
  await mkdir(path.join(root, 'public/assets'), { recursive: true });
  await symlink(os.tmpdir(), path.join(root, 'public/assets/audio'));
  await assert.rejects(prepareMedia({ ...options(root), mode: 'fetch' }), /Refusing symlink/);
});
test('concurrent destination creation is preserved and partials are cleaned', async t => {
  const root = await fixture(t);
  const run = fakeRun();
  await assert.rejects(prepareMedia({ ...options(root), mode: 'fetch', fetcher: async () => new Response('MP3'), run: async (command, args) => {
    const result = await run(command, args);
    if (command === 'ffmpeg' && args[0] !== '-version') await writeFile(path.join(root, item.localPath), 'concurrent user file');
    return result;
  } }), /EEXIST/);
  assert.equal(await readFile(path.join(root, item.localPath), 'utf8'), 'concurrent user file');
  assert.deepEqual(await readdir(path.join(root, 'public/assets/audio')), ['track-one.m4a']);
});

test('a playable but truncated recording is not ready', async t => {
  const root = await fixture(t, [{ ...item, dimensionsOrDuration: 300 }]);
  await mkdir(path.join(root, 'public/assets/audio'), { recursive: true });
  await writeFile(path.join(root, item.localPath), 'AAC');
  assert.equal((await prepareMedia({ ...options(root), mode: 'check' }))[0].status, 'invalid');
});
