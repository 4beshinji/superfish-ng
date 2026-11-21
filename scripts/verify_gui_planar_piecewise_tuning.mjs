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
    "Usage: node scripts/verify_gui_planar_piecewise_tuning.mjs --url LAUNCH_URL --out NEW_DIRECTORY --workspace JOBS --request SUCCESS_JSON --cancel-request CANCEL_JSON --unverified-request UNVERIFIED_JSON; or --resume-report PRIOR_REPORT",
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


  const launch=new URL(args['--url']);launch.pathname='/planar.html';
  await call('Page.navigate',{url:launch.href},sessionId);
  await wait('document.querySelector("#width")?.value==="310"');
  const check=async(operation,expression)=>{
    if(!await ev(`(async()=>(${expression}))()`))throw Error(operation);
    report.checks.push({operation,passed:true});console.log('PASS '+operation);
  };
  const loadFile=async(selector,filename)=>{
    await ev('if(typeof window.__tuneLoadCount==="undefined"){window.__tuneLoadCount=0;window.__tuneReplayCount=0;const originalAPI=api;api=async(action,...rest)=>{const value=await originalAPI(action,...rest);if(action==="planar-normalize-tune")window.__tuneLoadCount++;if(action==="planar-replay-tune")window.__tuneReplayCount++;return value;};}');
    const counter=selector==='#tune-open'?'__tuneLoadCount':'__tuneReplayCount';
    const before=await ev(counter);
    const {root}=await call('DOM.getDocument',{},sessionId);
    const {nodeId}=await call('DOM.querySelector',{nodeId:root.nodeId,selector},sessionId);
    await call('DOM.setFileInputFiles',{nodeId,files:[]},sessionId);
    await call('DOM.setFileInputFiles',{nodeId,files:[resolve(filename)]},sessionId);
    await wait(`${counter}>${before}`,600000);
  };
  const download=async(name)=>{
    for(let n=0;n<300;n++){try{return await readFile(out+'/downloads/'+name);}catch{}await sleep(100);}
    throw Error('missing download '+name);
  };
  const complete=async(identifier)=>{
    await wait(`document.querySelector('[data-job="${identifier}"] strong')?.textContent.startsWith('complete')`,600000);
    await click(`[data-job="${identifier}"] > button`);
    await wait(`tuneSelection===${JSON.stringify(identifier)}`,600000);
  };
  const openSaved=async(identifier,index)=>{
    await click(`[data-tune-checkpoints="${identifier}"]`);
    await wait(`!!document.querySelector('[data-job="${identifier}"] [data-checkpoint="${index}"]')`);
    await click(`[data-job="${identifier}"] [data-checkpoint="${index}"]`);
    await wait(`tuneSelection===${JSON.stringify(identifier+' / 試行 '+index)}`,600000);
  };
  const renderTarget=async(index,filename)=>{
    await click(`#tune-trials [data-tune-trial="${index}"]`);
    await wait('selected!==null && $("mode").value==="1"',180000);
    report.imported_job=await ev('selected');
    await check('native target retains explicit polygon and per-length RF',
      'result.case.schema_version===2 && $("quantities").textContent.includes("J/m") && $("na").textContent.includes("N/A")');
    await click('#plot');await wait('!$("image").hidden && $("image").naturalWidth>100',180000);
    await ev('$("result").scrollIntoView({block:"start"})');
    const shot=await call('Page.captureScreenshot',{format:'png'},sessionId);
    await writeFile(out+'/'+filename,Buffer.from(shot.data,'base64'));
  };
  if(args['--resume-report']){
    const prior=JSON.parse(await readFile(args['--resume-report'],'utf8'));
    report.prior_report=resolve(args['--resume-report']);
    for(const key of ['resumed_job','unverified_job','cancel_resume_job'])report[key]=prior[key];
    await call('Page.navigate',{url:launch.origin+'/planar.html?job='+report.resumed_job},sessionId);
    await wait(`typeof tuneSelection!=='undefined' && tuneSelection===${JSON.stringify(report.resumed_job)}`,600000);
    await check('new server replays owned successful final refinement',
      'currentTune.document.status==="TUNED" && currentTune.document.schema_version===2 && currentTune.document.request.schema_version===4 && currentTune.document.decision.refined_target_met && currentTune.document.decision.mesh_difference_met');
    await writeFile(out+'/final-checkpoint.json',await ev('currentTune.serialized'));
    await renderTarget(4,'restored-field.png');
    await call('Page.navigate',{url:launch.origin+'/planar.html?job='+report.cancel_resume_job},sessionId);
    await wait(`typeof tuneSelection!=='undefined' && tuneSelection===${JSON.stringify(report.cancel_resume_job)}`,600000);
    await openSaved(report.cancel_resume_job,1);
    await check('new server opens inherited owned prefix',
      'currentTune.document.status==="PAUSED" && currentTune.document.trials.length===1');
    await call('Page.navigate',{url:launch.origin+'/planar.html?job='+report.unverified_job},sessionId);
    await wait(`typeof tuneSelection!=='undefined' && tuneSelection===${JSON.stringify(report.unverified_job)}`,600000);
  }else{
    const expected=JSON.parse(await readFile(args['--request'],'utf8'));
    await loadFile('#tune-open',args['--request']);
    await wait('project.case.schema_version===2 && $("tune-shape-kind").value==="piecewise"');
    if(!isDeepStrictEqual(JSON.parse(await ev('tuneRequestText()')),expected))throw Error('loaded piecewise request differs');
    await click('#tune-save');const saved=await download('planar-tune.json');
    if(!isDeepStrictEqual(JSON.parse(saved),expected))throw Error('saved piecewise request differs');
    await loadFile('#tune-open',out+'/downloads/planar-tune.json');
    await wait('$("tune-shape-kind").value==="piecewise"');
    await check('piecewise law Project and recovery request roundtrip with SI units',
      'JSON.parse(tuneRequestText()).schema_version===4 && JSON.parse(tuneRequestText()).shape_law.kind==="polynomial_piecewise_xy" && JSON.parse(tuneRequestText()).identity_recovery.anchor_selection==="latest_resolved_trial"');
    await ev('$("tune-recovery-selection").value="none"');await click('#tune-start');
    await wait('!$("error").hidden && $("error").textContent.includes("回復方法")');
    await check('missing piecewise recovery policy refuses allocation',
      '(await api("jobs")).every(j=>j.kind!=="planar_tune")');
    await loadFile('#tune-open',args['--request']);
    await wait('$("tune-recovery-selection").value==="latest_resolved_trial"');
    await ev('$("tune-shape-law").closest("details").open=true');
    const duplicated=JSON.stringify(expected.shape_law).replace('"parameter_unit":"dimensionless"','"parameter_unit":"dimensionless","parameter_unit":"dimensionless"');
    await fill('#tune-shape-law',duplicated);await click('#tune-start');
    await wait('!$("error").hidden && $("error").textContent.includes("duplicate")');
    await check('duplicate shape-law key rejected without replacing raw JSON',
      '(await api("jobs")).every(j=>j.kind!=="planar_tune")');
    await loadFile('#tune-open',args['--request']);await wait('!$("error").hidden===false');
    await ev('window.__baseApi=api;api=async(action,...rest)=>{const value=await __baseApi(action,...rest);if(["planar-start-tune","planar-resume-tune"].includes(action))window.__tuneJob=value.id;return value;}');
    await fill('#tune-new-trials',2);await click('#tune-start');await wait('!!window.__tuneJob',600000);
    report.first_job=await ev('__tuneJob');await complete(report.first_job);
    await check('actual piecewise worker pauses at two search trials',
      'currentTune.document.status==="PAUSED" && currentTune.document.trials.length===2 && currentTune.document.request.schema_version===4');
    await click('#tune-checkpoint-save');await writeFile(out+'/paused-checkpoint.json',await download('planar-tune-checkpoint.json'));
    await loadFile('#tune-checkpoint-open',out+'/paused-checkpoint.json');await wait('tuneSelection==="paused-checkpoint.json"',600000);
    await loadFile('#tune-checkpoint-open',out+'/paused-checkpoint.json');await wait('tuneSelection==="paused-checkpoint.json"',600000);
    await check('same checkpoint file can be reloaded and physically replayed',
      'currentTune.document.status==="PAUSED" && currentTune.document.trials.length===2');
    await fill('#tune-new-trials','');await ev('window.__tuneJob=null');await click('#tune-resume');await wait('!!window.__tuneJob',600000);
    report.resumed_job=await ev('__tuneJob');await complete(report.resumed_job);
    await check('nonaffine search and final refinement meet both gates',
      'currentTune.document.status==="TUNED" && currentTune.document.trials.length===4 && currentTune.document.decision.refined_target_met && currentTune.document.decision.mesh_difference_met && $("tune-resume").disabled');
    await writeFile(out+'/final-checkpoint.json',await ev('currentTune.serialized'));
    await renderTarget(4,'target-field.png');
    await call('Page.navigate',{url:launch.origin+'/planar.html?job='+report.resumed_job},sessionId);
    await wait(`typeof tuneSelection!=='undefined' && tuneSelection===${JSON.stringify(report.resumed_job)}`,600000);
    await openSaved(report.resumed_job,2);
    await check('resumed job opens its owned inherited checkpoint',
      'currentTune.document.status==="PAUSED" && currentTune.document.trials.length===2');
    await call('Page.navigate',{url:launch.origin+'/planar.html?job='+report.resumed_job},sessionId);
    await wait(`typeof tuneSelection!=='undefined' && tuneSelection===${JSON.stringify(report.resumed_job)}`,600000);
    await ev('$("tune-result").scrollIntoView({block:"start"})');
    const shot=await call('Page.captureScreenshot',{format:'png'},sessionId);
    await writeFile(out+'/tune-result.png',Buffer.from(shot.data,'base64'));
    await ev('window.__baseApi=api;api=async(action,...rest)=>{const value=await __baseApi(action,...rest);if(["planar-start-tune","planar-resume-tune"].includes(action))window.__tuneJob=value.id;return value;}');
    await loadFile('#tune-open',args['--cancel-request']);await wait('$("tune-max-trials").value==="60"');
    await fill('#tune-new-trials','');await ev('window.__tuneJob=null');await click('#tune-start');await wait('!!window.__tuneJob',600000);
    report.cancelled_job=await ev('__tuneJob');
    const cp=resolve(args['--workspace'],report.cancelled_job,'execution/checkpoint-001.json');let found=false;
    for(let i=0;i<2400;i++){try{JSON.parse(await readFile(cp,'utf8'));found=true;break;}catch{}await sleep(50);}
    if(!found)throw Error('no complete owned checkpoint before cancellation');
    await wait(`document.querySelector('[data-job="${report.cancelled_job}"] > button')?.textContent==='中止'`);
    await click(`[data-job="${report.cancelled_job}"] > button`);
    await wait(`document.querySelector('[data-job="${report.cancelled_job}"] strong')?.textContent.startsWith('cancelled')`,30000);
    await openSaved(report.cancelled_job,1);
    await check('real cancellation exposes verified owned initial checkpoint',
      'currentTune.document.status==="PAUSED" && currentTune.document.trials.length===1');
    await writeFile(out+'/cancelled-checkpoint.json',await ev('currentTune.serialized'));
    await fill('#tune-new-trials',1);await ev('window.__tuneJob=null');await click('#tune-resume');await wait('!!window.__tuneJob',600000);
    report.cancel_resume_job=await ev('__tuneJob');await complete(report.cancel_resume_job);
    await check('cancelled piecewise prefix resumes into new owned job',
      'currentTune.document.status==="PAUSED" && currentTune.document.trials.length===2');
    await writeFile(out+'/cancel-resumed-checkpoint.json',await ev('currentTune.serialized'));
    await loadFile('#tune-open',args['--unverified-request']);await wait('$("tune-mode-id").value==="x"');
    await fill('#tune-new-trials','');await ev('window.__tuneJob=null');await click('#tune-start');await wait('!!window.__tuneJob',600000);
    report.unverified_job=await ev('__tuneJob');await complete(report.unverified_job);
    await writeFile(out+'/unverified-checkpoint.json',await ev('currentTune.serialized'));
  }
  await check('true degeneracy remains unevaluated and disables fabricated target',
    'currentTune.document.status==="UNVERIFIED" && currentTune.document.trials.at(-1).frequency_hz===null && currentTune.document.trials.at(-1).target_error_hz===null && $("tune-trials").textContent.includes("未評価") && document.querySelectorAll("[data-tune-trial]")[1].disabled && $("tune-resume").disabled');
  report.source_changed_during_run=!isDeepStrictEqual(report.source_sha256,await sourceHashes());
  report.passed=!report.source_changed_during_run&&report.external_requests.length===0;
  if(!report.passed)throw Error('source or external HTTP changed');
  console.log(JSON.stringify({passed:true,checks:report.checks}));
} catch(e){report.error=String(e);process.exitCode=1;console.error(e);}
finally {
  try {
    await writeFile(out + "/report.json", JSON.stringify(report, null, 2));
  } finally {
    for (const entry of pending.values()) clearTimeout(entry.timer);
    try { ws?.close(); } finally { await dispose(); }
  }
}
