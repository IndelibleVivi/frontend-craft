#!/usr/bin/env node
// Explicit, local preparation of the audio entries in Side A's rights manifest.
import { readFile, lstat, realpath, mkdir, mkdtemp, rm, link } from 'node:fs/promises';
import { createWriteStream } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawn } from 'node:child_process';
import { pipeline } from 'node:stream/promises';

const defaultRoot = fileURLToPath(new URL('../music-library/', import.meta.url));
const usage = 'Usage: node scripts/prepare-media.mjs (--check | --fetch) [--id TRACK_ID]';

export function parseArgs(args) {
  let mode, id;
  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === '--help') return { help: true };
    if (arg === '--check' || arg === '--fetch') {
      if (mode) throw new Error(usage);
      mode = arg.slice(2);
    } else if (arg === '--id' && !id && args[i + 1] && !args[i + 1].startsWith('--')) id = args[++i];
    else throw new Error(usage);
  }
  if (!mode) throw new Error(usage);
  return { mode, id };
}

export function runTool(command, args) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { stdio: ['ignore', 'pipe', 'pipe'] });
    let stdout = '', stderr = '';
    child.stdout.on('data', chunk => { stdout = (stdout + chunk).slice(-65536); });
    child.stderr.on('data', chunk => { stderr = (stderr + chunk).slice(-65536); });
    child.on('error', error => reject(new Error(`${command}: ${error.message}`)));
    child.on('close', code => code === 0 ? resolve(stdout) : reject(new Error(`${command} exited ${code}: ${stderr.trim()}`)));
  });
}

function officialUrl(value) {
  const url = new URL(value);
  if (url.protocol !== 'https:' || url.hostname !== 'incompetech.com' || url.port || url.username || url.password ||
      !url.pathname.startsWith('/music/royalty-free/mp3-royaltyfree/') || !url.pathname.endsWith('.mp3') || url.search || url.hash) {
    throw new Error(`Unsupported audio source: ${value}`);
  }
  return url.href;
}

async function safeTarget(root, entry) {
  if (!/^[a-z0-9-]+$/.test(entry.id) || entry.localPath !== `public/assets/audio/${entry.id}.m4a`) {
    throw new Error(`Unsafe audio target for ${entry.id}`);
  }
  const target = path.join(root, entry.localPath);
  // Refuse symlinks in every existing ancestor, including the final file.
  let current = root;
  for (const part of entry.localPath.split('/')) {
    current = path.join(current, part);
    try {
      const stat = await lstat(current);
      if (stat.isSymbolicLink()) throw new Error(`Refusing symlink: ${current}`);
      if (current !== target && !stat.isDirectory()) throw new Error(`Not a directory: ${current}`);
      if (current === target && !stat.isFile()) throw new Error(`Not a regular file: ${current}`);
    } catch (error) { if (error.code !== 'ENOENT') throw error; }
  }
  return target;
}

async function inspectAudio(target, run, expectedDuration) {
  try { await lstat(target); } catch (error) { if (error.code === 'ENOENT') return 'missing'; throw error; }
  try {
    const metadata = JSON.parse(await run('ffprobe', ['-v', 'error', '-show_entries', 'stream=codec_type,codec_name:format=duration', '-of', 'json', target]));
    if (!metadata.streams?.some(stream => stream.codec_type === 'audio' && stream.codec_name === 'aac') || !(Number(metadata.format?.duration) > 0) || Math.abs(Number(metadata.format.duration) - expectedDuration) > 1) return 'invalid';
    return 'ready';
  } catch { return 'invalid'; }
}

export async function prepareMedia({ mode, id, root = defaultRoot, run = runTool, fetcher = globalThis.fetch, log = console.log }) {
  if (!['check', 'fetch'].includes(mode)) throw new Error(usage);
  root = await realpath(root);
  const manifest = JSON.parse(await readFile(path.join(root, 'ASSETS.json'), 'utf8'));
  if (!Array.isArray(manifest)) throw new Error('ASSETS.json must be an array');
  const audio = manifest.filter(entry => entry.role === 'audio');
  if (!audio.length) throw new Error('ASSETS.json has no audio entries');
  const selected = audio.filter(entry => !id || entry.id === id);
  if (!selected.length) throw new Error(`Unknown audio id: ${id}`);
  const ids = new Set();
  const entries = [];
  for (const entry of selected) {
    if (ids.has(entry.id)) throw new Error(`Duplicate audio id: ${entry.id}`);
    ids.add(entry.id);
    if (!Number.isFinite(entry.dimensionsOrDuration) || entry.dimensionsOrDuration <= 0) throw new Error(`Invalid duration for ${entry.id}`);
    entries.push({ entry, url: officialUrl(entry.sourceUrl), target: await safeTarget(root, entry) });
  }
  // No network call until both required tools have passed preflight.
  await run('ffprobe', ['-version']);
  if (mode === 'fetch') await run('ffmpeg', ['-version']);
  const results = [];
  for (const { entry, url, target } of entries) {
    let status = await inspectAudio(target, run, entry.dimensionsOrDuration);
    if (mode === 'fetch' && status === 'invalid') throw new Error(`${entry.id}: existing audio is invalid; move it aside before retrying (preserved: ${target})`);
    if (mode === 'fetch' && status === 'missing') {
      await safeTarget(root, entry);
      await mkdir(path.dirname(target), { recursive: true });
      const temporary = await mkdtemp(path.join(path.dirname(target), '.prepare-media-'));
      try {
        const response = await fetcher(url, { redirect: 'error', signal: AbortSignal.timeout(120000) });
        if (!response.ok) throw new Error(`Download failed: HTTP ${response.status} ${response.statusText ?? ''} (${url})`);
        if (!response.body) throw new Error(`Download has no body: ${url}`);
        const source = path.join(temporary, 'source.mp3');
        const output = path.join(temporary, 'audio.m4a');
        await pipeline(response.body, createWriteStream(source, { flags: 'wx' }));
        await run('ffmpeg', ['-nostdin', '-v', 'error', '-n', '-protocol_whitelist', 'file,pipe', '-i', source, '-map', '0:a:0', '-vn', '-c:a', 'aac', '-b:a', '96k', '-movflags', '+faststart', output]);
        if (await inspectAudio(output, run, entry.dimensionsOrDuration) !== 'ready') throw new Error(`${entry.id}: transcoded output is not valid AAC audio`);
        await safeTarget(root, entry);
        // Same-filesystem hard link is atomic and refuses concurrent/user files.
        await link(output, target);
        status = 'prepared';
      } finally { await rm(temporary, { recursive: true, force: true }); }
    }
    log(`${entry.id}: ${status}`);
    results.push({ id: entry.id, status });
  }
  return results;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const options = parseArgs(process.argv.slice(2));
    if (options.help) console.log(usage);
    else {
      const results = await prepareMedia(options);
      if (results.some(result => !['ready', 'prepared'].includes(result.status))) process.exitCode = 1;
    }
  } catch (error) { console.error(error.message); process.exitCode = 1; }
}
