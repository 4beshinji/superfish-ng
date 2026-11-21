// SPDX-License-Identifier: Apache-2.0
// Real local browser input and computation. Requires a running GUI and Chrome.
import { launchBrowser } from "./browser-session.mjs";
import { readFile, writeFile, mkdir, readdir, rename } from "node:fs/promises";
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
if (!args["--url"] || !args["--out"])
  throw Error(
    "Usage: node scripts/verify_gui_planar_affine_tuning.mjs --url LAUNCH_URL --out NEW_DIRECTORY --workspace JOBS --request AFFINE_JSON",
  );
const out = resolve(args["--out"]);
await mkdir(out, { recursive: false });
const { profile, browser, dispose } = await launchBrowser();
let stderr = "",
  ws,
  id = 0;
const pending = new Map(),
  sleep = (ms) => new Promise((r) => setTimeout(r, ms));
browser.stderr.on("data", (b) => (stderr = (stderr + b).slice(-65536)));
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
      }, 180000);
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
    const priorError=await ev('document.querySelector("#error")?.hidden ? "" : document.querySelector("#error")?.textContent');
    let cleared=!priorError;
    while (performance.now() - start < ms) {
      if (await ev(expression)) return;
      const error=await ev('document.querySelector("#error")?.hidden ? "" : document.querySelector("#error")?.textContent');
      if(!error)cleared=true;
      if(error&&(cleared||error!==priorError))throw Error(`UI error: ${error}`);
      await sleep(100);
    }
    throw Error(
      `UI timeout: ${expression}; ${await ev('document.querySelector("#error")?.textContent')}; state=${await ev('JSON.stringify({width:document.querySelector("#width")?.value,unit:document.querySelector("#unit")?.value,project:typeof project!=="undefined"?project:null})')}`,
    );
  };
  const click = async (selector) => {
    const rect = await ev(
      `(async()=>{let e=document.querySelector(${JSON.stringify(selector)});e.scrollIntoView({block:'center',behavior:'instant'});await new Promise(done=>requestAnimationFrame(()=>requestAnimationFrame(done)));e=document.querySelector(${JSON.stringify(selector)});const r=e.getBoundingClientRect(),x=r.x+r.width/2,y=r.y+r.height/2;if(!e.contains(document.elementFromPoint(x,y)))throw Error('click target is obscured: '+JSON.stringify({target:e.outerHTML,rect:r.toJSON(),cover:document.elementFromPoint(x,y)?.tagName}));return {x,y}})()`,
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


  const launch=new URL(args['--url']);launch.pathname='/planar.html';await call('Page.navigate',{url:launch.href},sessionId);
  await wait('document.querySelector("#width")?.value==="310"');
  const check=async(operation,expression)=>{if(!await ev(`(async()=>(${expression}))()`))throw Error(operation);report.checks.push({operation,passed:true});console.log('PASS '+operation);};
  const expected=JSON.parse(await readFile(args['--request'],'utf8'));
  await ev('window.__loads=0;window.__baseApi=api;api=async(action,...rest)=>{const value=await __baseApi(action,...rest);if(action==="planar-normalize-tune")window.__loads++;if(["planar-start-tune","planar-resume-tune"].includes(action))window.__tuneJob=value.id;return value;}');
  const {root}=await call('DOM.getDocument',{},sessionId);
  const {nodeId}=await call('DOM.querySelector',{nodeId:root.nodeId,selector:'#tune-open'},sessionId);
  await call('DOM.setFileInputFiles',{nodeId,files:[resolve(args['--request'])]},sessionId);await wait('__loads===1',120000);
  if(!isDeepStrictEqual(JSON.parse(await ev('tuneRequestText()')),expected))throw Error('legacy affine request changed');
  await check('legacy affine law remains schema 2 and exact Project',
    '$("tune-shape-kind").value==="affine" && JSON.parse(tuneRequestText()).schema_version===2 && $("tune-recovery-selection").value==="none"');
  await click('#tune-save');let saved;
  for(let n=0;n<300;n++){try{saved=await readFile(out+'/downloads/planar-tune.json');break;}catch{}await sleep(100);}
  if(!saved||!isDeepStrictEqual(JSON.parse(saved),expected))throw Error('legacy affine saved request differs');
  report.checks.push({operation:'legacy affine request saves unchanged',passed:true});
  const complete=async(identifier)=>{
    await wait(`document.querySelector('[data-job="${identifier}"] strong')?.textContent.startsWith('complete')`,600000);
    await click(`[data-job="${identifier}"] > button`);await wait(`tuneSelection===${JSON.stringify(identifier)}`,600000);
  };
  await fill('#tune-new-trials',2);await click('#tune-start');await wait('!!window.__tuneJob',600000);report.first_job=await ev('__tuneJob');await complete(report.first_job);
  await check('legacy affine worker pauses with true rank crossing',
    'currentTune.document.status==="PAUSED" && currentTune.document.schema_version===1 && currentTune.document.trials.length===2 && JSON.stringify(currentTune.document.trials[1].current_mode_ids)===JSON.stringify(["x","y"])');
  await writeFile(out+'/paused-checkpoint.json',await ev('currentTune.serialized'));
  await fill('#tune-new-trials','');await ev('window.__tuneJob=null');await click('#tune-resume');await wait('!!window.__tuneJob',600000);report.resumed_job=await ev('__tuneJob');await complete(report.resumed_job);
  await check('legacy affine resume meets target and mesh gates',
    'currentTune.document.status==="TUNED" && currentTune.document.trials.length===3 && currentTune.document.decision.refined_target_met && currentTune.document.decision.mesh_difference_met');
  await writeFile(out+'/final-checkpoint.json',await ev('currentTune.serialized'));
  await click('#tune-trials [data-tune-trial="3"]');await wait('selected!==null && $("mode").value==="1"',180000);report.imported_job=await ev('selected');
  await check('legacy affine opens actual target native and per-length RF',
    'result.case.schema_version===2 && $("quantities").textContent.includes("J/m") && $("na").textContent.includes("N/A")');
  await click('#plot');await wait('!$("image").hidden && $("image").naturalWidth>100',180000);
  await ev('$("result").scrollIntoView({block:"start"})');const shot=await call('Page.captureScreenshot',{format:'png'},sessionId);await writeFile(out+'/legacy-affine-field.png',Buffer.from(shot.data,'base64'));
  report.source_changed_during_run=!isDeepStrictEqual(report.source_sha256,await sourceHashes());report.passed=!report.source_changed_during_run&&report.external_requests.length===0;
  if(!report.passed)throw Error('source or external HTTP changed');console.log(JSON.stringify({passed:true,checks:report.checks}));
} catch(e){report.error=String(e);process.exitCode=1;console.error(e);}
finally {
  try {
    await writeFile(out + "/report.json", JSON.stringify(report, null, 2));
  } finally {
    for (const entry of pending.values()) clearTimeout(entry.timer);
    try { ws?.close(); } finally { await dispose(); }
  }
}
