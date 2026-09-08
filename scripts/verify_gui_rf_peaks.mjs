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
    "Usage: node scripts/verify_gui_rf_peaks.mjs --url LAUNCH_URL --out NEW_DIRECTORY --request REQUEST_JSON",
  );
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
      }, 30000);
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
  const begin = performance.now();
  await call("Page.navigate", { url: args["--url"] }, sessionId);
  await wait('document.querySelector("#shape polygon")');
  report.startup_ms = performance.now() - begin;
  const check=async (operation,expression)=>{if (!await ev(expression)) throw Error(operation);report.checks.push({operation,passed:true});};
  const fixtures=JSON.parse(await readFile(args['--request'],'utf8'));
  const loadFile=async filename=>{const {root}=await call('DOM.getDocument',{},sessionId);const {nodeId}=await call('DOM.querySelector',{nodeId:root.nodeId,selector:'#rf-peaks-open'},sessionId);await call('DOM.setFileInputFiles',{nodeId,files:[resolve(filename)]},sessionId);};
  const importResult=async path=>{if(!await ev('document.querySelector("#import-path").closest("details").open'))await click('details:has(#import-path)>summary');const previous=await ev('currentJob');await fill('#import-path',path);await click('#import-result');await wait(`currentJob!==${JSON.stringify(previous)} && rfPeakReady && !document.querySelector('#field-image').hidden`,60000);return await ev('currentJob');};
  const selectMode=async mode=>{await ev(`(()=>{const e=document.querySelector('#mode');e.value=${JSON.stringify(String(mode))};e.dispatchEvent(new Event('change',{bubbles:true}))})()`);};
  const assess=async mode=>{await click('#rf-peaks-assess');await wait(`!rfPeakBusy && rfPeakResult?.document.mode_index===${mode-1}`,60000);};
  await check('peak controls start disabled without a native result','document.querySelector("#rf-peaks-assess").disabled');
  const affineJob=await importResult(fixtures.affine);await assess(1);
  await check('ordinary RF view shows five bounded quantities without claiming mesh convergence','document.querySelector("#rf-peaks-values tbody").rows.length===5 && rfPeakResult.document.status==="DISCRETE_BOUNDS_ONLY" && document.querySelector("#rf-peaks-status").textContent.includes("メッシュ収束: 未評価") && document.querySelector("#rf-peaks-status").textContent.includes("物理誤差上界: なし")');
  await check('original RF data and peak-phasor normalization are preserved','JSON.stringify(rfPeakResult.document.rf)===JSON.stringify(currentResult.result.modes[0]) && rfPeakResult.document.rf.stored_energy_j>0 && Object.keys(rfPeakResult.document.conventions).length>0');
  await selectMode(2);await check('switching rank clears the previous assessment','rfPeakResult===null && document.querySelector("#rf-peaks-values tbody").rows.length===0 && document.querySelector("#rf-peaks-save").disabled');await assess(2);
  await check('assessment follows selected frequency rank','rfPeakResult.document.mode_index===1 && document.querySelector("#rf-peaks-status").textContent.includes("順位 2")');
  const expected=await ev('rfPeakResult.serialized');await click('#rf-peaks-save');const file=out+'/downloads/rf-discrete-peaks.json';let downloaded;
  for(let i=0;i<100;i++){try{downloaded=await readFile(file,'utf8');if(downloaded===expected)break;}catch{}await sleep(100);}
  if(downloaded!==expected)throw Error('saved RF peak JSON differs');report.checks.push({operation:'download preserves exact verified assessment',passed:true});
  const bad=JSON.parse(downloaded);bad.intervals.epk_v_per_m[0]*=.5;await writeFile(out+'/changed.json',JSON.stringify(bad));await loadFile(out+'/changed.json');await wait('!rfPeakBusy && !document.querySelector("#error").hidden',60000);
  await check('altered bounds preserve the last verified assessment','rfPeakResult.document.mode_index===1 && document.querySelector("#error").textContent.includes("replay")');
  await call('Page.reload',{},sessionId);await wait('typeof currentJob!=="undefined" && document.querySelector("#shape polygon")');await wait(`document.querySelector('[data-job="${affineJob}"] button')`,60000);await click(`[data-job="${affineJob}"] button`);await wait('rfPeakReady',60000);await selectMode(2);await loadFile(file);await wait('!rfPeakBusy && rfPeakResult?.document.mode_index===1',60000);
  await check('saved assessment reopens for its original result and rank after reload',`rfPeakResult.serialized===${JSON.stringify(expected)}`);
  await selectMode(1);await assess(1);await loadFile(file);await wait('!rfPeakBusy && !document.querySelector("#error").hidden',60000);
  await check('a document for another rank is rejected without replacing current evidence','rfPeakResult.document.mode_index===0 && document.querySelector("#error").textContent.includes("result and mode")');
  // Delay delivery of an actual verified server response to exercise stale-request handling.
  await ev('window.originalRFPeakApi=api;api=async(...args)=>{const r=await window.originalRFPeakApi(...args);if(args[0]==="assess-rf-peaks")await new Promise(done=>window.releaseRFPeak=done);return r;}');
  await click('#rf-peaks-assess');await wait('typeof window.releaseRFPeak==="function"',60000);await selectMode(2);await ev('window.releaseRFPeak();api=window.originalRFPeakApi');await sleep(200);
  await check('late server response cannot attach previous rank peaks to the new selection','rfPeakResult===null && document.querySelector("#rf-peaks-values tbody").rows.length===0 && !rfPeakBusy');
  await importResult(fixtures.curve);await assess(1);
  await check('curved native fields use the same RF assessment with geometry approximation unassessed','rfPeakResult.document.geometry_order===2 && rfPeakResult.document.geometry_approximation_assessed===false && rfPeakResult.document.intervals.epk_v_per_m[1]===currentResult.result.modes[0].epk_discrete_upper_bound_v_per_m');
  const rect=await ev('(()=>{const a=document.querySelector("#rf-peaks").getBoundingClientRect();return {x:a.x+scrollX,y:a.y+scrollY,width:a.width,height:a.height,scale:1}})()');const shot=await call('Page.captureScreenshot',{captureBeyondViewport:true,clip:rect},sessionId);await writeFile(out+'/rf-curved-peaks.png',Buffer.from(shot.data,'base64'));
  await importResult(fixtures.neck);await assess(1);
  await check('reentrant corners retain their singular-geometry warning','rfPeakResult.document.geometry_diagnostic.status==="SINGULAR_GEOMETRY" && document.querySelector("#rf-peaks-status").textContent.includes("SINGULAR_GEOMETRY") && rfPeakResult.document.status==="DISCRETE_BOUNDS_ONLY"');
  const source=await ev('rfPeakResult.document.run+"/case.json"'),original=await readFile(source,'utf8'),previous=await ev('rfPeakResult.serialized');
  try {await writeFile(source,original+'\n');await click('#rf-peaks-replay');await wait('!rfPeakBusy && !document.querySelector("#error").hidden',60000);await check('modified native fields are rejected without replacing verified evidence',`rfPeakResult.serialized===${JSON.stringify(previous)}`);}
  finally {await writeFile(source,original);}
  await click('#rf-peaks-replay');await wait('!rfPeakBusy && document.querySelector("#error").hidden',60000);
  report.source_changed_during_run=!isDeepStrictEqual(report.source_sha256,await sourceHashes());
  report.passed=!report.source_changed_during_run && report.external_requests.length===0 && report.checks.every(c=>c.passed);
  if(!report.passed)throw Error('affine surface GUI checks failed');
  console.log(JSON.stringify({passed:report.passed,checks:report.checks,external_requests:report.external_requests}));
} catch(e){report.error=String(e);process.exitCode=1;console.error(e);}
finally{await writeFile(out+'/report.json',JSON.stringify(report,null,2));ws?.close();browser.kill();}
