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
    "Usage: node scripts/verify_gui_material_hphi_tracking.mjs --url LAUNCH_URL --out NEW_DIRECTORY --request REQUEST_JSON",
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
      }, 600000);
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
  await call('Page.navigate',{url:args['--url']},sessionId);


  await wait('typeof trackingRequest !== "undefined" && $("jobs").dataset.signature');
  const input=JSON.parse(await readFile(args['--request'],'utf8')),request=input.request;
  const check=async(operation,expression)=>{if(!await ev(expression))throw Error(operation);report.checks.push({operation,passed:true});console.log('PASS',operation);};
  await ev(`document.querySelector('#tracking-document').closest('details').open=true`);
  await fill('#tracking-document',JSON.stringify(request));await click('#tracking-apply');
  await wait('!$("tracking-start").disabled');
  if(!isDeepStrictEqual(await ev('trackingFromForm()'),request))throw Error('material request changed');
  await check('complete fixed-material comparison preview and material native choices',`$('tracking-preview').textContent.includes('三角形') && Array.from($('tracking-previous').options).some(o=>o.value===${JSON.stringify(input.source_ids[0])})`);
  for(const [side,id] of [['previous',input.source_ids[0]],['current',input.source_ids[1]]])await ev(`$('tracking-${side}').value=${JSON.stringify(id)}`);
  await click('#tracking-start');
  await wait(`$('tracking-dirty').textContent.includes('追跡投入済み: ')`,resultTimeout);
  const pairId=await ev(`$('tracking-dirty').textContent.split(': ')[1]`);
  await wait(`document.querySelector('[data-job="${pairId}"] strong')?.textContent.startsWith('complete')`,resultTimeout);
  await click(`[data-job="${pairId}"] > button`);
  await wait('currentTracking?.result.status === "PASS"',resultTimeout);
  if(!isDeepStrictEqual(await ev('currentTracking.request'),request))throw Error('saved comparison request changed');
  await check('material E/H result displays identity and finite comparison diagnostics',`$('tracking-current-ids').textContent.includes('TEM') && $('tracking-resolution').textContent.includes('比較三角形')`);
  const historyRequest={format:'superfish_ng_material_hphi_tracking_history_request',history_version:1,step_count:1,max_steps:3};
  const historyFile=out+'/history-request.json';await writeFile(historyFile,JSON.stringify(historyRequest));
  const {root}=await call('DOM.getDocument',{},sessionId);
  const {nodeId}=await call('DOM.querySelector',{nodeId:root.nodeId,selector:'#history-open'},sessionId);
  await call('DOM.setFileInputFiles',{nodeId,files:[historyFile]},sessionId);
  await wait(`hphiHistoryRequest?.format===${JSON.stringify(historyRequest.format)}`,resultTimeout);
  await fill('#history-step-ids',JSON.stringify([pairId]));await click('#history-start');
  await wait(`$('history-note').textContent.includes('履歴を投入済み: ')`,resultTimeout);
  const historyId=await ev(`$('history-note').textContent.split(': ')[1]`);
  await wait(`document.querySelector('[data-job="${historyId}"] strong')?.textContent.startsWith('complete')`,resultTimeout);
  await click(`[data-job="${historyId}"] > button`);
  await wait(`currentHphiHistory?.id===${JSON.stringify(historyId)}`,resultTimeout);
  await check('material ordered history retains request, original IDs and step request',`currentHphiHistory.result.status==='PASS' && currentHphiHistory.result.current_mode_ids[0]==='TEM' && JSON.stringify(currentHphiHistory.step_requests[0])===JSON.stringify(currentTracking.request)`);
  const saved=await ev('currentHphiHistory');report.pair_id=pairId;report.history_id=historyId;
  const nativePath=resolve(input.workspace,historyId,'step-0000/previous/solution/results.json');
  const native=JSON.parse(await readFile(nativePath,'utf8'));
  const nativeHashes=async()=>{const hashes={};for(const side of ['previous','current']){const dir=resolve(input.workspace,historyId,'step-0000',side);for(const name of ['project.json',...(await readdir(dir+'/solution')).map(n=>'solution/'+n)]){const path=resolve(dir,name);hashes[path]=createHash('sha256').update(await readFile(path)).digest('hex');}}return hashes;};
  report.native_sha256=await nativeHashes();
  await click('[data-history-source="0-previous"]');
  await wait('selected!==null && result!==null',resultTimeout);
  if(!isDeepStrictEqual(await ev('result'),native))throw Error('history original native/RF differ');
  await check('history opens original material Project display unit and N/A axial RF',`$('unit').value==='m' && $('result').textContent.includes('N/A')`);
  await click('#plot');await wait('!$("image").hidden && $("image").naturalWidth>0',resultTimeout);
  const shot=await call('Page.captureScreenshot',{captureBeyondViewport:false},sessionId);await writeFile(out+'/native-field.png',Buffer.from(shot.data,'base64'));
  report.source_changed_during_run=!isDeepStrictEqual(report.source_sha256,await sourceHashes());
  report.native_unchanged=isDeepStrictEqual(report.native_sha256,await nativeHashes());
  report.passed=report.native_unchanged&&!report.source_changed_during_run&&report.external_requests.length===0;
  if(!report.passed)throw Error('source changed or external request');
}catch(e){report.error=String(e);process.exitCode=1;console.error(e);}
finally{await writeFile(out+'/report.json',JSON.stringify(report,null,2));for(const entry of pending.values())clearTimeout(entry.timer);ws?.close();browser.kill();browser.stdout?.destroy();browser.stderr?.destroy();browser.unref();}
