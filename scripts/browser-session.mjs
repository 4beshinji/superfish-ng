// SPDX-License-Identifier: Apache-2.0
// Linux-only lifecycle for disposable verification browsers; no npm dependencies.
import { fork, spawn } from 'node:child_process';
import {
  lstatSync, mkdirSync, readFileSync, readdirSync, renameSync, rmSync,
  statfsSync, writeFileSync,
} from 'node:fs';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export const BROWSER_LIMITS = Object.freeze({
  slots: 2, timeoutMs: 30 * 60_000, maxBytes: 512 * 1024 ** 2,
  minFreeBytes: 1024 ** 3, pollMs: 5000, graceMs: 5000,
});
export const BROWSER_STATE_ROOT = `/tmp/superfish-ng-browser-${process.getuid()}`;
const modulePath = fileURLToPath(import.meta.url);
const sleep = ms => new Promise(done => setTimeout(done, ms));

function privateDirectory(path, create = false) {
  if (create) {
    try { mkdirSync(path, { mode: 0o700 }); }
    catch (error) { if (error.code !== 'EEXIST') throw error; }
  }
  const info = lstatSync(path);
  if (!info.isDirectory() || info.uid !== process.getuid() || (info.mode & 0o077)) {
    throw new Error(`unsafe browser state directory: ${path}`);
  }
  return info;
}

function processInfo(pid) {
  try {
    const path = `/proc/${pid}`;
    const fields = readFileSync(`${path}/stat`, 'utf8').split(/\) /).at(-1).split(' ');
    return { pid: Number(pid), start: fields[19], group: Number(fields[2]),
      live: !['Z', 'X'].includes(fields[0]), uid: lstatSync(path).uid };
  } catch (error) {
    if (['ENOENT', 'ESRCH'].includes(error.code)) return null;
    throw error;
  }
}

function sameLiveProcess(identity) {
  if (!identity || !Number.isSafeInteger(identity.pid) || identity.pid <= 0 ||
      typeof identity.start !== 'string' || !/^\d+$/.test(identity.start)) {
    throw new Error('invalid browser owner identity');
  }
  const current = processInfo(identity.pid);
  return current?.live && current.start === identity.start;
}

function ownedProcesses(slot, group) {
  const result = [];
  for (const name of readdirSync('/proc')) {
    if (!/^\d+$/.test(name)) continue;
    let info;
    try { info = processInfo(Number(name)); }
    catch (error) { if (error.code === 'EACCES') continue; throw error; }
    if (!info?.live || info.uid !== process.getuid()) continue;
    let owned = group !== null && info.group === group;
    if (!owned) {
      try {
        const args = readFileSync(`/proc/${name}/cmdline`, 'utf8').split('\0');
        owned = args.includes(`--user-data-dir=${slot}/profile`) ||
          args.some(arg => arg.startsWith(`--database=${slot}/config/`));
      } catch (error) {
        if (!['ENOENT', 'ESRCH', 'EACCES'].includes(error.code)) throw error;
      }
    }
    if (owned) result.push(info);
  }
  return result;
}

function saveOwner(slot, owner) {
  writeFileSync(join(slot, 'owner.next'), JSON.stringify(owner), { mode: 0o600 });
  renameSync(join(slot, 'owner.next'), join(slot, 'owner.json'));
}

function reapSlot(slot) {
  // Unknown/incomplete ownership and live browsers consume a slot, never a deletion guess.
  try {
    const original = privateDirectory(slot);
    const file = join(slot, 'owner.json');
    const info = lstatSync(file);
    if (!info.isFile() || info.uid !== process.getuid()) return;
    const source = readFileSync(file, 'utf8');
    const owner = JSON.parse(source);
    if (owner.version !== 1 || !['allocated', 'ready'].includes(owner.phase) ||
        sameLiveProcess(owner.guardian)) return;
    if (owner.phase === 'ready' && !owner.chrome) return;
    if (owner.chrome && sameLiveProcess(owner.chrome)) return;
    if (ownedProcesses(slot, owner.chrome?.pid ?? null).length) return;
    const lock = join(slot, 'reaping');
    try { mkdirSync(lock, { mode: 0o700 }); }
    catch (error) { if (['EEXIST', 'ENOENT'].includes(error.code)) return; throw error; }
    try {
      if (privateDirectory(slot).ino !== original.ino || readFileSync(file, 'utf8') !== source) return;
      rmSync(slot, { recursive: true });
    } finally {
      // Do not remove a successor's reaper lock after the old slot was retired.
      try { if (lstatSync(slot).ino === original.ino) rmSync(lock, { recursive: true }); }
      catch (error) { if (error.code !== 'ENOENT') throw error; }
    }
  } catch (error) {
    if (!['ENOENT', 'EEXIST'].includes(error.code) && !(error instanceof SyntaxError)) {
      process.stderr.write(`preserving browser slot: ${error.message}\n`);
    }
  }
}

function allocateSlot(root, limits) {
  privateDirectory(root, true);
  for (let index = 0; index < BROWSER_LIMITS.slots; index++) reapSlot(join(root, `slot-${index}`));
  const disk = statfsSync(root);
  if (disk.bavail * disk.bsize < limits.minFreeBytes) throw new Error('less than 1 GiB free for browser verification');
  for (let index = 0; index < BROWSER_LIMITS.slots; index++) {
    const slot = join(root, `slot-${index}`);
    try { mkdirSync(slot, { mode: 0o700 }); return slot; }
    catch (error) { if (error.code !== 'EEXIST') throw error; }
  }
  throw new Error('both browser verification slots are occupied; finish active runs or inspect retained ownership records');
}

function diskBytes(path, limit) {
  const info = lstatSync(path);
  if (info.isSymbolicLink()) return 0;
  let bytes = info.blocks * 512;
  if (info.isDirectory()) {
    for (const entry of readdirSync(path)) {
      try { bytes += diskBytes(join(path, entry), limit - bytes); }
      catch (error) { if (error.code !== 'ENOENT') throw error; }
      if (bytes > limit) break;
    }
  }
  return bytes;
}

async function terminateBrowser(slot, chrome, graceMs) {
  for (const signal of ['SIGTERM', 'SIGKILL']) {
    const deadline = Date.now() + graceMs;
    do {
      const processes = ownedProcesses(slot, chrome?.pid ?? null);
      if (!processes.length) return;
      for (const info of processes) {
        if (sameLiveProcess(info)) {
          try { process.kill(info.pid, signal); }
          catch (error) { if (error.code !== 'ESRCH') throw error; }
        }
      }
      await sleep(50);
    } while (Date.now() < deadline);
  }
  throw new Error('browser processes survived cleanup; retaining their slot');
}

async function guardian(options) {
  const limits = { ...BROWSER_LIMITS, ...options.limits };
  let slot, chrome, owner, timer, monitor, stopping, requested, initialized = false;
  process.stderr.on('error', () => {}); // Parent SIGKILL closes the diagnostic pipe.
  const send = message => new Promise(done => {
    if (!process.connected) return done();
    process.send(message, () => done());
  });
  const finish = (code = 0, error = null) => stopping ??= (async () => {
    clearTimeout(timer); clearInterval(monitor);
    try {
      if (slot) {
        await terminateBrowser(slot, chrome, limits.graceMs);
        rmSync(slot, { recursive: true, maxRetries: 3, retryDelay: 100 });
      }
    } catch (failure) { code = 1; error = `${error ?? ''} cleanup: ${failure.message}`; }
    await send({ type: 'finished', code, error });
    process.exit(code);
  })();
  const stop = () => { requested = true; if (initialized) void finish(); };
  process.on('disconnect', stop);
  process.on('message', message => { if (message.type === 'stop') stop(); });
  process.on('SIGTERM', stop); process.on('SIGINT', stop);
  try {
    slot = allocateSlot(options.stateRoot, limits);
    owner = { version: 1, phase: 'allocated', guardian: processInfo(process.pid), chrome: null };
    saveOwner(slot, owner);
    for (const name of ['profile', 'cache', 'config', 'tmp']) privateDirectory(join(slot, name), true);
    owner.phase = 'launching'; saveOwner(slot, owner);
    chrome = spawn(options.executable, [...options.args,
      `--user-data-dir=${slot}/profile`, '--disk-cache-size=33554432', '--media-cache-size=16777216'], {
      detached: true, stdio: ['ignore', 'ignore', 'pipe'],
      env: { ...process.env, XDG_CACHE_HOME: join(slot, 'cache'),
        XDG_CONFIG_HOME: join(slot, 'config'), TMPDIR: join(slot, 'tmp') },
    });
    chrome.stderr.on('data', bytes => {
      if (process.connected && !process.stderr.write(bytes)) chrome.stderr.pause();
    });
    process.stderr.on('drain', () => chrome.stderr.resume());
    await new Promise((done, fail) => { chrome.once('spawn', done); chrome.once('error', fail); });
    owner.chrome = processInfo(chrome.pid);
    if (!owner.chrome) throw new Error('browser exited during startup');
    owner.phase = 'ready'; saveOwner(slot, owner);
    initialized = true;
    chrome.on('exit', (code, signal) => {
      if (!stopping) void finish(1, `browser exited before disposal (${code ?? signal})`);
    });
    if (requested || !process.connected) return await finish();
    if (chrome.exitCode !== null || chrome.signalCode !== null) throw new Error('browser exited during startup');
    timer = setTimeout(() => void finish(124, 'browser verification deadline exceeded'), limits.timeoutMs);
    monitor = setInterval(() => {
      try {
        if (diskBytes(slot, limits.maxBytes) > limits.maxBytes) {
          void finish(1, 'browser temporary state exceeded its byte budget');
        }
      } catch (error) { void finish(1, error.message); }
    }, limits.pollMs);
    await send({ type: 'ready', profile: join(slot, 'profile') });
  } catch (error) { await finish(1, error.message); }
}

/** Own a browser until dispose, parent exit (including SIGKILL), or a resource limit. */
export async function launchBrowser({ executable = '/usr/bin/google-chrome',
  args = ['--headless', '--remote-debugging-port=0', '--disable-background-networking', '--no-first-run', 'about:blank'],
  stateRoot = BROWSER_STATE_ROOT, limits = {} } = {}) {
  for (const [name, value] of Object.entries(limits)) {
    if (!(name in BROWSER_LIMITS) || name === 'slots' || !Number.isSafeInteger(value) || value <= 0 ||
        value > BROWSER_LIMITS[name]) throw new Error(`invalid browser limit: ${name}`);
  }
  if (args.some(arg => arg.startsWith('--user-data-dir'))) throw new Error('browser profiles are lifecycle-owned');
  const browser = fork(modulePath, ['--guardian'], {
    detached: true, stdio: ['ignore', 'ignore', 'pipe', 'ipc'], execArgv: [],
  });
  let tail = '', ready = false, disposing = false, finished, disposal;
  browser.stderr.on('data', bytes => { tail = (tail + bytes).slice(-65536); });
  const exited = new Promise(done => browser.once('exit', (code, signal) => done({ code, signal })));
  async function dispose() {
    disposing = true;
    return disposal ??= (async () => {
      if (browser.connected) browser.send({ type: 'stop' }, () => {});
      let timeout;
      try {
        const status = await Promise.race([exited, new Promise((_, reject) => {
          timeout = setTimeout(() => reject(new Error('browser guardian cleanup timed out')), 15000);
        })]);
        if (status.code !== 0) throw new Error(finished?.error ?? `browser guardian failed: ${status.code ?? status.signal}\n${tail}`);
      } finally { clearTimeout(timeout); }
    })();
  }
  const signals = { SIGINT: 130, SIGTERM: 143 };
  const handlers = Object.fromEntries(Object.entries(signals).map(([signal, code]) => [signal, () => {
    void dispose().catch(error => console.error(error.message)).finally(() => process.exit(code));
  }]));
  for (const [signal, handler] of Object.entries(handlers)) process.once(signal, handler);
  exited.then(status => {
    for (const [signal, handler] of Object.entries(handlers)) process.removeListener(signal, handler);
    if (ready && !disposing) {
      console.error(finished?.error ?? `browser guardian stopped unexpectedly (${status.code ?? status.signal})`);
      process.exit(finished?.code || 1);
    }
  });
  const readyProfile = new Promise((done, fail) => {
    browser.on('message', message => {
      if (message.type === 'ready') { ready = true; done(message.profile); }
      if (message.type === 'finished') { finished = message; if (!ready) fail(new Error(message.error ?? 'browser startup interrupted')); }
    });
    browser.once('error', fail);
    exited.then(status => { if (!ready) fail(new Error(finished?.error ?? `browser guardian startup failed (${status.code ?? status.signal})\n${tail}`)); });
  });
  browser.send({ executable, args, stateRoot: resolve(stateRoot), limits }, error => {
    if (error) browser.kill('SIGTERM');
  });
  const profile = await readyProfile;
  return { browser, profile, dispose };
}

if (process.argv[1] && resolve(process.argv[1]) === modulePath && process.argv[2] === '--guardian') {
  if (!process.send) throw new Error('browser guardian requires its parent IPC channel');
  // A parent can die before transmitting the initial request.
  const disconnected = () => process.exit(0);
  process.once('disconnect', disconnected);
  process.once('message', options => {
    process.removeListener('disconnect', disconnected);
    void guardian(options);
  });
}
