// SPDX-License-Identifier: Apache-2.0
// Headless integration test; Node 22 + an existing Chrome, no npm dependencies.
import { spawn } from 'node:child_process';
import { mkdir, mkdtemp, readFile, writeFile, access, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { resolve, join, dirname, relative } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createHash } from 'node:crypto';

const options = {};
for (let i = 2; i < process.argv.length; i += 2) {
  if (!['--html', '--out', '--chrome', '--mode'].includes(process.argv[i]) || !process.argv[i + 1]) {
    throw new Error('Usage: node scripts/verify_gallery.mjs --html INDEX_HTML --out NEW_DIRECTORY [--chrome EXECUTABLE] [--mode gallery|static]');
  }
  options[process.argv[i]] = process.argv[i + 1];
}
if (!options['--html'] || !options['--out']) throw new Error('--html and --out are required');
const scenario = options['--mode'] || 'gallery';
if (!['gallery', 'static'].includes(scenario)) throw new Error('--mode must be gallery or static');
const html = resolve(options['--html']);
const out = resolve(options['--out']);
await access(html);
await mkdir(dirname(out), { recursive: true });
await mkdir(out); // Never overwrite a prior test.
const profile = await mkdtemp(join(tmpdir(), 'superfish-browser-'));
const executable = options['--chrome'] || '/usr/bin/google-chrome';
const browser = spawn(executable, ['--headless', '--remote-debugging-port=0', '--remote-debugging-address=127.0.0.1',
  `--user-data-dir=${profile}`, '--no-first-run', '--no-default-browser-check', '--disable-background-networking',
  '--disable-component-update', '--disable-sync', 'about:blank'], { stdio: ['ignore', 'ignore', 'pipe'] });
let browserError, stderr = '', ws, sequence = 0;
browser.on('error', error => { browserError = error; });
browser.stderr.on('data', data => { stderr += data; });
const pending = new Map();
const report = { html, executable, mode: 'headless integration test; isolated temporary profile; no existing desktop session',
  scenario, node: process.version, selections: [], passed: false };
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const pause = ms => new Promise(done => setTimeout(done, ms));

function call(method, params = {}, sessionId) {
  return new Promise((done, fail) => {
    const id = ++sequence;
    const timer = setTimeout(() => { pending.delete(id); fail(new Error(`CDP timeout: ${method}`)); }, 20000);
    pending.set(id, { done, fail, timer });
    ws.send(JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) }));
  });
}

try {
  report.verifier_sha256 = hash(await readFile(fileURLToPath(import.meta.url)));
  report.html_sha256 = hash(await readFile(html));
  let portInfo;
  for (let attempt = 0; attempt < 200; attempt++) {
    if (browserError) throw browserError;
    if (browser.exitCode !== null) throw new Error(`Chrome exited ${browser.exitCode}: ${stderr}`);
    try { portInfo = await readFile(join(profile, 'DevToolsActivePort'), 'utf8'); break; } catch {}
    await pause(50);
  }
  if (!portInfo) throw new Error(`Chrome did not expose its local test endpoint: ${stderr}`);
  const [port, endpoint] = portInfo.trim().split('\n');
  ws = new WebSocket(`ws://127.0.0.1:${port}${endpoint}`);
  await new Promise((done, fail) => { ws.addEventListener('open', done, { once: true }); ws.addEventListener('error', fail, { once: true }); });
  ws.addEventListener('message', event => {
    const response = JSON.parse(event.data);
    if (!response.id || !pending.has(response.id)) return;
    const entry = pending.get(response.id);
    pending.delete(response.id);
    clearTimeout(entry.timer);
    if (response.error) entry.fail(new Error(JSON.stringify(response.error)));
    else entry.done(response.result);
  });
  report.browser = await call('Browser.getVersion');
  const { targetId } = await call('Target.createTarget', { url: 'about:blank' });
  const { sessionId } = await call('Target.attachToTarget', { targetId, flatten: true });
  const evaluate = async expression => {
    const response = await call('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true }, sessionId);
    if (response.exceptionDetails) throw new Error(JSON.stringify(response.exceptionDetails));
    return response.result.value;
  };
  await call('Page.enable', {}, sessionId);
  await call('Network.enable', {}, sessionId);
  await call('Network.setBlockedURLs', { urls: ['http://*', 'https://*'] }, sessionId);
  await call('Emulation.setDeviceMetricsOverride', { width: 1280, height: 960, deviceScaleFactor: 1, mobile: false }, sessionId);
  const navigation = await call('Page.navigate', { url: pathToFileURL(html).href }, sessionId);
  if (navigation.errorText) throw new Error(navigation.errorText);
  for (let attempt = 0; attempt < 200; attempt++) {
    if (await evaluate('document.readyState === "complete"'+(scenario === 'gallery' ? ' && document.querySelectorAll("select option").length > 0' : ''))) break;
    if (attempt === 199) throw new Error('gallery did not finish loading with a mode selector');
    await pause(50);
  }
  await evaluate('Promise.all([...document.images].map(image => image.decode())).then(() => true)');
  const values = scenario === 'gallery' ? await evaluate('[...document.querySelector("select").options].map(option => option.value)') : ['static'];
  const links = await evaluate('[...document.querySelectorAll("a[href], img[src]")].map(e => e.href || e.src)');
  report.link_sha256 = {};
  for (const link of links) {
    const url = new URL(link);
    if (url.protocol !== 'file:') throw new Error(`gallery unexpectedly depends on a non-local resource: ${link}`);
    const path = fileURLToPath(url);
    if (relative(dirname(html), path).split(/[\\/]/).includes('..')) throw new Error(`gallery link leaves its result directory: ${path}`);
    report.link_sha256[path] = hash(await readFile(path));
  }
  if (scenario === 'gallery') await evaluate('document.querySelector("select").focus()');
  const key = async (name, code) => {
    for (const type of ['keyDown', 'keyUp']) await call('Input.dispatchKeyEvent', { type, key: name, code: name, windowsVirtualKeyCode: code }, sessionId);
    await pause(60);
  };
  if (scenario === 'gallery') await key('Home', 36);
  for (let i = 0; i < values.length; i++) {
    if (i) await key('ArrowDown', 40);
    const state = scenario === 'static' ? await evaluate(`({ selected: 'static', visible: ['static'],
      images: [...document.images].map(image => ({ src: image.src, width: image.naturalWidth, height: image.naturalHeight })) })`) : await evaluate(`(() => {
      const visible = [...document.querySelectorAll('section.mode')].filter(e => !e.hidden && getComputedStyle(e).display !== 'none');
      return { selected: document.querySelector('select').value, visible: visible.map(e => e.id),
        images: visible.flatMap(e => [...e.querySelectorAll('img')].map(image => ({ src: image.src, width: image.naturalWidth, height: image.naturalHeight }))) };
    })()`);
    if (state.selected !== values[i] || state.visible.length !== 1 || state.visible[0] !== values[i] ||
        !state.images.length || state.images.some(image => image.width <= 0 || image.height <= 0)) {
      throw new Error(`keyboard mode selection failed: expected ${values[i]}, got ${JSON.stringify(state)}`);
    }
    report.selections.push(state);
    if (i === 0 || i === values.length - 1) {
      const { cssContentSize } = await call('Page.getLayoutMetrics', {}, sessionId);
      const screenshot = await call('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true,
        clip: { x: 0, y: 0, width: cssContentSize.width, height: Math.min(cssContentSize.height, 8000), scale: 1 } }, sessionId);
      await writeFile(join(out, `selection-${i}.png`), Buffer.from(screenshot.data, 'base64'));
    }
  }
  report.passed = hash(await readFile(html)) === report.html_sha256;
  if (!report.passed) throw new Error('gallery HTML changed during verification');
  console.log(`PASS: ${values.length} ${scenario === 'gallery' ? 'keyboard selections' : 'static pages'}, ${links.length} local links/images; ${out}`);
} catch (error) {
  report.error = String(error.stack || error);
  process.exitCode = 1;
  console.error(report.error);
} finally {
  await writeFile(join(out, 'verification.json'), JSON.stringify(report, null, 2) + '\n');
  await writeFile(join(out, 'chrome.log'), stderr);
  if (ws?.readyState === WebSocket.OPEN) {
    try { await call('Browser.close'); } catch {}
    ws.close();
  }
  if (browser.exitCode === null) {
    browser.kill('SIGTERM');
    for (let i = 0; i < 100 && browser.exitCode === null; i++) await pause(50);
    if (browser.exitCode === null) browser.kill('SIGKILL');
  }
  for (const entry of pending.values()) clearTimeout(entry.timer);
  await rm(profile, { recursive: true, force: true }); // Only this test's mkdtemp profile.
}
