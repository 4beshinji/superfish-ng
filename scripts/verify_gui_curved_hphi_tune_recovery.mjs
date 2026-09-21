// SPDX-License-Identifier: Apache-2.0
// Real local browser input and computation. Requires a running GUI and Chrome.
import { spawn } from "node:child_process";
import { mkdtemp, readFile, writeFile, mkdir, readdir } from "node:fs/promises";
import { resolve } from "node:path";
import { createHash } from "node:crypto";
import { isDeepStrictEqual } from "node:util";
async function sourceHashes(directory = "src/superfish_ng") {
  const result = {};
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const path = `${directory}/${entry.name}`;
    if (entry.isDirectory() && entry.name !== "__pycache__")
      Object.assign(result, await sourceHashes(path));
    else if (entry.isFile() && /\.(py|html|js|css)$/.test(entry.name))
      result[path] = createHash("sha256")
        .update(await readFile(path))
        .digest("hex");
  }
  return result;
}
const args = Object.fromEntries(
  process.argv
    .slice(2)
    .reduce((a, v, i, s) => (i % 2 ? a : [...a, [v, s[i + 1]]]), []),
);
if (!args["--url"] || !args["--out"] || !args["--request"])
  throw Error(
    "Usage: node scripts/verify_gui_curved_hphi_tune_recovery.mjs --url LAUNCH_URL --out NEW_DIRECTORY --request REQUEST_JSON",
  );
const resultTimeout = Number(args["--result-timeout-ms"] ?? 600000);
if (!Number.isSafeInteger(resultTimeout) || resultTimeout <= 0)
  throw Error("--result-timeout-ms must be a positive integer");
const out = resolve(args["--out"]);
await mkdir(out, { recursive: false });
const profile = await mkdtemp("/tmp/ng-gui-chrome-");
const browser = spawn("/usr/bin/google-chrome", [
  "--headless",
  "--remote-debugging-port=0",
  `--user-data-dir=${profile}`,
  "--disable-background-networking",
  "--no-first-run",
  "about:blank",
]);
let stderr = "",
  ws,
  id = 0;
const pending = new Map(),
  sleep = (ms) => new Promise((r) => setTimeout(r, ms));
browser.stderr.on("data", (b) => (stderr += b));
const report = {
  passed: false,
  node: process.version,
  checks: [],
  external_requests: [],
  source_sha256: await sourceHashes(),
};
try {
  let info;
  for (let n = 0; n < 100; n++) {
    try {
      info = await readFile(profile + "/DevToolsActivePort", "utf8");
      break;
    } catch {}
    await sleep(100);
  }
  if (!info) throw Error(stderr);
  const [port, path] = info.trim().split("\n");
  ws = new WebSocket(`ws://127.0.0.1:${port}${path}`);
  await new Promise((r, j) => {
    ws.onopen = r;
    ws.onerror = j;
  });
  ws.onmessage = (e) => {
    const m = JSON.parse(e.data);
    if (m.method === "Fetch.requestPaused") {
      const external =
        new URL(m.params.request.url).origin !== new URL(args["--url"]).origin;
      call(
        external ? "Fetch.failRequest" : "Fetch.continueRequest",
        {
          requestId: m.params.requestId,
          ...(external ? { errorReason: "InternetDisconnected" } : {}),
        },
        m.sessionId,
      ).catch(() => {});
    }
    if (m.method === "Page.javascriptDialogOpening")
      call("Page.handleJavaScriptDialog", { accept: true }, m.sessionId).catch(
        () => {},
      );
    if (m.method === "Network.requestWillBeSent") {
      const url = m.params.request.url;
      if (
        /^https?:/.test(url) &&
        new URL(url).origin !== new URL(args["--url"]).origin
      )
        report.external_requests.push(url);
    }
    if (pending.has(m.id)) {
      const { done, fail, timer } = pending.get(m.id);
      pending.delete(m.id);
      clearTimeout(timer);
      m.error ? fail(Error(JSON.stringify(m.error))) : done(m.result);
    }
  };
  const call = (method, params = {}, sessionId) =>
    new Promise((done, fail) => {
      const n = ++id;
      const timer = setTimeout(() => {
        pending.delete(n);
        fail(Error(`timeout ${method}`));
      }, resultTimeout);
      pending.set(n, { done, fail, timer });
      ws.send(JSON.stringify({ id: n, method, params, sessionId }));
    });
  report.browser = await call("Browser.getVersion");
  const { targetId } = await call("Target.createTarget", {
    url: "about:blank",
  });
  const { sessionId } = await call("Target.attachToTarget", {
    targetId,
    flatten: true,
  });
  const ev = async (expression) => {
    const r = await call(
      "Runtime.evaluate",
      { expression, awaitPromise: true, returnByValue: true },
      sessionId,
    );
    if (r.exceptionDetails) throw Error(JSON.stringify(r.exceptionDetails));
    return r.result.value;
  };
  const wait = async (expression, ms = 15000) => {
    const start = performance.now();
    while (performance.now() - start < ms) {
      const error = await ev('document.querySelector("#error")?.textContent');
      if (error) throw Error(`GUI rejected operation: ${error}`);
      if (await ev(expression)) return;
      await sleep(100);
    }
    throw Error(
      `UI timeout: ${expression}; ${await ev('document.querySelector("#error")?.textContent')}`,
    );
  };
  const click = async (selector) => {
    const rect = await ev(
      `(async()=>{const e=document.querySelector(${JSON.stringify(selector)});e.scrollIntoView({block:'center',behavior:'instant'});await new Promise(done=>requestAnimationFrame(()=>requestAnimationFrame(done)));const r=e.getBoundingClientRect(),x=r.x+r.width/2,y=r.y+r.height/2;if(!e.contains(document.elementFromPoint(x,y)))throw Error('click target is obscured');return {x,y}})()`,
    );
    for (const type of ["mousePressed", "mouseReleased"])
      await call(
        "Input.dispatchMouseEvent",
        { type, ...rect, button: "left", clickCount: 1 },
        sessionId,
      );
  };
  const fill = async (selector, value) => {
    await ev(
      `(()=>{const e=document.querySelector(${JSON.stringify(selector)});e.focus();e.select()})()`,
    );
    await call("Input.insertText", { text: String(value) }, sessionId);
    await call(
      "Input.dispatchKeyEvent",
      { type: "keyDown", key: "Tab", code: "Tab", windowsVirtualKeyCode: 9 },
      sessionId,
    );
    await call(
      "Input.dispatchKeyEvent",
      { type: "keyUp", key: "Tab", code: "Tab", windowsVirtualKeyCode: 9 },
      sessionId,
    );
  };
  await mkdir(out + "/downloads");
  await call("Browser.setDownloadBehavior", {
    behavior: "allow",
    downloadPath: out + "/downloads",
  });
  await call("Page.enable", {}, sessionId);
  await call("Network.enable", {}, sessionId);
  await call(
    "Fetch.enable",
    { patterns: [{ urlPattern: "http://*" }, { urlPattern: "https://*" }] },
    sessionId,
  );
  await call(
    "Emulation.setDeviceMetricsOverride",
    { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false },
    sessionId,
  );
  await call('Page.navigate',{url:args['--url']},sessionId);
  if(args['--checkpoint']){
    await wait('typeof currentHphiTune !== "undefined"');
    const {root}=await call('DOM.getDocument',{},sessionId);
    const {nodeId}=await call('DOM.querySelector',{nodeId:root.nodeId,selector:'#hphi-tune-checkpoint-open'},sessionId);
    await call('DOM.setFileInputFiles',{nodeId,files:[resolve(args['--checkpoint'])]},sessionId);
  }
  await wait('typeof currentHphiTune !== "undefined" && currentHphiTune?.document.status === "TUNED"',resultTimeout);
  const request=JSON.parse(await readFile(args['--request'],'utf8'));
  if(request.format!=='superfish_ng_curved_hphi_tune'||request.schema_version!==1)throw Error('curved recovery request required');
  const check=async(operation,expression)=>{if(!await ev(expression))throw Error(operation);report.checks.push({operation,passed:true});console.log('PASS',operation);};
  const final=await ev('currentHphiTune.document');
  if(!isDeepStrictEqual(final.request,request))throw Error('request changed');
  const nativeHashes=async()=>{const hashes={};for(const run of final.trial_runs){const walk=async dir=>{for(const entry of await readdir(dir,{withFileTypes:true})){const p=dir+'/'+entry.name;if(entry.isDirectory())await walk(p);else hashes[p]=createHash('sha256').update(await readFile(p)).digest('hex');}};await walk(run);}return hashes;};
  report.native_sha256=await nativeHashes();
  await check('search and refinement preserve raw inherited groups and recovered individual IDs',`currentHphiTune.document.trials.length===4 && currentHphiTune.document.trials.slice(2).every(t=>t.tracking.current_mode_ids.every(id=>id===null)&&t.current_mode_ids.join(',')==='radial,TEM'&&t.identity_recovery.status==='PASS')`);
  await check('comparison parent and anchor are shown separately',`$('hphi-tune-trials').textContent.includes('比較親の試行 1 / anchor試行 2') && $('hphi-tune-trials').textContent.includes('比較親の試行 3 / anchor試行 3')`);
  await click('#hphi-tune-save-request');
  const readDownload=async name=>{for(let n=0;n<100;n++){try{return await readFile(out+'/downloads/'+name,'utf8');}catch{}await sleep(100);}throw Error('download missing '+name);};
  if(!isDeepStrictEqual(JSON.parse(await readDownload('hphi-tune-request.json')),request))throw Error('download request changed');
  await click('#hphi-tune-checkpoint-save');
  const text=await readDownload('hphi-tune-checkpoint.json');
  if(text!==await ev('currentHphiTune.serialized'))throw Error('checkpoint changed');
  for(let n=0;n<2;n++){
    await fill('#hphi-tune-document','{}');
    const {root}=await call('DOM.getDocument',{},sessionId);
    const {nodeId}=await call('DOM.querySelector',{nodeId:root.nodeId,selector:'#hphi-tune-checkpoint-open'},sessionId);
    await call('DOM.setFileInputFiles',{nodeId,files:[out+'/downloads/hphi-tune-checkpoint.json']},sessionId);
    await wait(`JSON.parse($('hphi-tune-document').value).format==='superfish_ng_curved_hphi_tune'`,resultTimeout);
    if(await ev('currentHphiTune.serialized')!==text)throw Error('same-file replay changed checkpoint');
  }
  report.checks.push({operation:'complete recovery request downloaded and same owned checkpoint replayed twice',passed:true});
  await click('[data-hphi-tune-trial="4"]');
  await wait(`selected!==null && $('hphi-tune-status').textContent.includes('元場を表示中')`,resultTimeout);
  const rank=final.trials[3].current_mode_ids.indexOf(request.mode_id)+1;
  await check('recovered target opens actual native rank with unavailable axial RF',`Number($('mode').value)===${rank} && $('result').textContent.includes('N/A')`);
  const native=JSON.parse(await readFile(resolve(final.trial_runs[3],'solution/results.json'),'utf8'));
  if(!isDeepStrictEqual(await ev('result'),native))throw Error('GUI native results/RF differ');
  await click('#plot');await wait('!$("image").hidden && $("image").naturalWidth>0',resultTimeout);
  const shot=await call('Page.captureScreenshot',{captureBeyondViewport:false},sessionId);await writeFile(out+'/native-field.png',Buffer.from(shot.data,'base64'));
  report.native_unchanged=isDeepStrictEqual(report.native_sha256,await nativeHashes());
  report.source_changed_during_run=!isDeepStrictEqual(report.source_sha256,await sourceHashes());
  report.passed=report.native_unchanged&&!report.source_changed_during_run&&report.external_requests.length===0;
  if(!report.passed)throw Error('native/source changed or external request');
  console.log(JSON.stringify({passed:report.passed,checks:report.checks}));
}catch(e){report.error=String(e);process.exitCode=1;console.error(e);}
finally{await writeFile(out+'/report.json',JSON.stringify(report,null,2));for(const entry of pending.values())clearTimeout(entry.timer);ws?.close();browser.kill();browser.stdout?.destroy();browser.stderr?.destroy();browser.unref();}
