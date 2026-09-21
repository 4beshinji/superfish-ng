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
    "Usage: node scripts/verify_gui_material_hphi_rejections.mjs --url LAUNCH_URL --out NEW_DIRECTORY --request REQUEST_JSON",
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
  const wait = async (expression, ms = 15000, allowExpectedError = false) => {
    const start = performance.now();
    while (performance.now() - start < ms) {
      const error = await ev('document.querySelector("#error")?.hidden ? "" : document.querySelector("#error")?.textContent');
      if (error && !allowExpectedError) throw Error(`GUI rejected operation: ${error}`);
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
  await wait('typeof project !== "undefined" && project !== null && document.querySelector("#hphi-tune-apply")');
  const request=JSON.parse(await readFile(args['--request'],'utf8'));
  if(request.format!=='superfish_ng_material_hphi_tune'||request.schema_version!==1)throw Error('material request required');
  const check=async(operation,expression)=>{if(!await ev(expression))throw Error(operation);report.checks.push({operation,passed:true});console.log('PASS',operation);};
  const loadFile=async(selector,filename)=>{const {root}=await call('DOM.getDocument',{},sessionId);const {nodeId}=await call('DOM.querySelector',{nodeId:root.nodeId,selector},sessionId);await call('DOM.setFileInputFiles',{nodeId,files:[resolve(filename)]},sessionId);};
  const launch=async selector=>{const old=await ev('$("hphi-tune-dirty").textContent');await click(selector);await wait(`$("hphi-tune-dirty").textContent!==${JSON.stringify(old)} && $("hphi-tune-dirty").textContent.includes('投入済み')`,resultTimeout);return await ev('$("hphi-tune-dirty").textContent.split(": ").at(-1)');};
  report.job_ids=[];
  await loadFile('#hphi-tune-open',args['--request']);
  await wait('!$("hphi-tune-start").disabled');
  const before=await ev('api("jobs")');
  for(const kind of ['nonvacuum-axis','loss-tangent']){
    const bad=structuredClone(request);
    if(kind==='nonvacuum-axis')bad.project.case.acceleration.z_end_m=.1;
    else bad.project.case.partition.materials[0].loss_tangent=.01;
    const reason=kind==='nonvacuum-axis'?'vacuum':'loss_tangent';
    await fill('#hphi-tune-document',JSON.stringify(bad));await click('#hphi-tune-apply');
    await wait(`!$('error').hidden && $('error').textContent.includes(${JSON.stringify(reason)})`,15000,true);
    await check(kind+' rejected during request normalization',`!$('error').hidden`);
    await click('#hphi-tune-start');
    await wait(`!$('error').hidden && $('error').textContent.includes(${JSON.stringify(reason)})`,15000,true);
    if(!isDeepStrictEqual(await ev('api("jobs")'),before))throw Error('invalid physics allocated a job');
    report.checks.push({operation:kind+' rejected at start without allocating a job',passed:true});
  }
  await fill('#hphi-tune-document',JSON.stringify(request));await click('#hphi-tune-apply');
  await wait(`$('error').hidden && $('hphi-tune-dirty').textContent===''`);
  if(!isDeepStrictEqual(await ev('JSON.parse($("hphi-tune-document").value)'),request))throw Error('valid request was not restored');
  report.checks.push({operation:'valid material and vacuum-axis request restored intact',passed:true});
  report.source_changed_during_run=!isDeepStrictEqual(report.source_sha256,await sourceHashes());
  report.passed=!report.source_changed_during_run && report.external_requests.length===0;
  if(!report.passed)throw Error('source changed or external request');
  console.log(JSON.stringify({passed:report.passed,checks:report.checks,job_ids:report.job_ids}));
}catch(e){report.error=String(e);process.exitCode=1;console.error(e);}
finally{await writeFile(out+'/report.json',JSON.stringify(report,null,2));for(const entry of pending.values())clearTimeout(entry.timer);ws?.close();browser.kill();browser.stdout?.destroy();browser.stderr?.destroy();browser.unref();}
