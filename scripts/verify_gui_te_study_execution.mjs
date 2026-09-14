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
    "Usage: node scripts/verify_gui_te_study_execution.mjs --url LAUNCH_URL --out NEW_DIRECTORY --request REQUEST_JSON",
  );
const resultTimeout = Number(args["--result-timeout-ms"] ?? 180000);
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
  const request=JSON.parse(await readFile(args["--request"],"utf8"));
  if(request.study.project.case.model?.polarization!=='te')throw Error('TE request required');
  const adaptive=Object.hasOwn(request,'adaptive');
  const acceptedSweep=!!args['--accepted-sweep'];
  if(acceptedSweep && (!adaptive || request.study.values.length!==3))throw Error('accepted sweep requires three adaptive target values');
  const savedName=adaptive ? 'adaptive-study-checkpoint.json' : 'tracked-study-checkpoint.json';
  report.kind=adaptive?'adaptive':'sequential';report.job_ids=[];
  const loadFile=async filename=>{const {root}=await call('DOM.getDocument',{},sessionId);const {nodeId}=await call('DOM.querySelector',{nodeId:root.nodeId,selector:'#tracked-execution-open'},sessionId);await call('DOM.setFileInputFiles',{nodeId,files:[resolve(filename)]},sessionId);};
  const launch=async selector=>{
    const previous=await ev('$("tracked-execution-job").textContent');await click(selector);
    await wait(`!trackedExecutionBusy && $("tracked-execution-job").textContent!==${JSON.stringify(previous)}`,resultTimeout);
    const id=await ev('$("tracked-execution-job").textContent.match(/開始しました: ([a-zA-Z0-9-]+)/)[1]');report.job_ids.push(id);return id;
  };
  const openJob=async(id,status,count)=>{
    await wait(`document.querySelector('[data-job="${id}"] strong')?.textContent.includes(${JSON.stringify(status)})`,600000);
    await click(`[data-job="${id}"] button`);
    await wait(`!trackedExecutionBusy && trackedExecutionResult?.document.status===${JSON.stringify(status)} && (trackedExecutionResult.document.attempts?.length ?? trackedExecutionResult.document.point_runs.length)===${count}`,resultTimeout);
  };
  const capture=async name=>{const rect=await ev('(()=>{const r=$("tracked-execution").getBoundingClientRect();return {x:r.x+scrollX,y:r.y+scrollY,width:r.width,height:r.height,scale:1}})()');const shot=await call('Page.captureScreenshot',{captureBeyondViewport:true,clip:rect},sessionId);await writeFile(out+'/'+name,Buffer.from(shot.data,'base64'));};
  if(args['--replay-only']){
    const expected=await readFile(args['--replay-only'],'utf8');
    const saved=JSON.parse(expected);
    if(!isDeepStrictEqual(saved.request,request) || saved.document_type!==(adaptive?'adaptive_tracked_study':'tracked_study_checkpoint'))throw Error('replay file differs from declared request or kind');
    await fill('#tracked-execution-request','{}');await loadFile(args['--replay-only']);
    await wait('!trackedExecutionBusy && trackedExecutionResult?.document.status==="COMPLETE" && JSON.parse($("tracked-execution-request").value).initial_ids?.[0]==="TE-fundamental"',resultTimeout);
    if(await ev('trackedExecutionResult.serialized')!==expected)throw Error('completed replay differs');
    await check('fresh browser replays complete TE evidence and restores electric identity','trackedExecutionResult.document.history.current_mode_ids.join(",")==="TE-fundamental" && trackedExecutionResult.document.history.steps.every(s=>s.tracking.physical_mapping.field==="Ephi_V_per_m") && $("tracked-execution-resume").disabled');
    await capture('replayed-complete.png');
  }else{
  await fill('#tracked-execution-request',JSON.stringify(request).replace('"schema_version":1','"schema_version":1,"schema_version":1'));
  const original=await ev('$("tracked-execution-job").textContent');await click('#tracked-execution-start');
  await wait('!trackedExecutionBusy && !$("error").hidden');
  await check('duplicate TE request keys fail before worker creation',`$("error").textContent.includes('duplicate JSON key') && $("tracked-execution-job").textContent===${JSON.stringify(original)}`);
  await fill('#tracked-execution-request',JSON.stringify(request));await fill('#tracked-execution-limit','1');
  const first=await launch('#tracked-execution-start');await openJob(first,'PAUSED',1);
  if(!isDeepStrictEqual(await ev('trackedExecutionResult.document.request'),request))throw Error('GUI changed TE request');
  report.checks.push({operation:'native TE request preserved exactly through worker execution',passed:true});
  if(acceptedSweep)await check('accepted first interval pauses before the third target','trackedExecutionResult.document.points.length===2 && trackedExecutionResult.document.accepted_point_indices.join(",")==="0,1" && trackedExecutionResult.document.attempts[0].decision==="ACCEPT"');
  else if(adaptive)await check('failed coarse comparison and pending midpoint are visible','trackedExecutionResult.document.points.length===2 && trackedExecutionResult.document.accepted_point_indices.length===1 && $("tracked-adaptive-attempts").textContent.includes("二分") && $("tracked-adaptive-pending").textContent.includes("1.0625")');
  else await check('first TE point pauses and later point remains uncomputed','trackedExecutionResult.document.history===null && $("tracked-execution-points").textContent.includes("未計算")');
  await click('#tracked-execution-save');let downloaded;
  for(let n=0;n<100;n++){try{downloaded=await readFile(out+'/downloads/'+savedName,'utf8');break;}catch{}await sleep(100);}
  if(downloaded!==await ev('trackedExecutionResult.serialized'))throw Error('download changed checkpoint text');
  report.checks.push({operation:'checkpoint download preserves exact native text',passed:true});
  await fill('#tracked-execution-request','{}');await loadFile(out+'/downloads/'+savedName);
  await wait('!trackedExecutionBusy && JSON.parse($("tracked-execution-request").value).initial_ids?.[0]==="TE-fundamental"',resultTimeout);
  await check('file replay restores TE request and enables resume','!$("tracked-execution-resume").disabled && JSON.parse($("tracked-execution-request").value).study.project.case.model.polarization==="te"');
  const forged=JSON.parse(downloaded);
  if(adaptive)forged.attempts[0].decision=acceptedSweep?'BISECT':'ACCEPT';else forged.point_results[0].value=-1;
  await writeFile(out+'/forged.json',JSON.stringify(forged));await loadFile(out+'/forged.json');
  await wait('!trackedExecutionBusy && !$("error").hidden',resultTimeout);
  await check('forged evidence cannot replace the verified checkpoint','$("error").textContent.includes("replay") && !$("tracked-execution-resume").disabled');
  if(await ev('trackedExecutionResult.serialized')!==downloaded)throw Error('forged replay replaced result');
  await fill('#tracked-execution-request','{}');
  if(adaptive && !acceptedSweep){
    const second=await launch('#tracked-execution-resume');await openJob(second,'PAUSED',2);
    await check('adaptive resume inserts only midpoint and retains original endpoints','trackedExecutionResult.document.points.length===3 && trackedExecutionResult.document.accepted_point_indices.join(",")==="0,2" && $("tracked-adaptive-points").textContent.includes("追加点")');
  }
  await fill('#tracked-execution-limit','');const complete=await launch('#tracked-execution-resume');await openJob(complete,'COMPLETE',adaptive ? (acceptedSweep?2:3) : request.study.values.length);
  await check('completed TE history retains electric-field identity and disables resume','trackedExecutionResult.document.history.current_mode_ids.join(",")==="TE-fundamental" && trackedExecutionResult.document.history.steps.every(s=>s.tracking.physical_mapping.field==="Ephi_V_per_m") && !$("tracked-execution-save").disabled && $("tracked-execution-resume").disabled');
  if(acceptedSweep)await check('all declared intervals complete without inserted points','trackedExecutionResult.document.accepted_point_indices.join(",")==="0,1,2" && trackedExecutionResult.document.attempts.every(a=>a.decision==="ACCEPT")');
  else if(adaptive)await check('adaptive completion keeps failed comparison and accepted order','trackedExecutionResult.document.accepted_point_indices.join(",")==="0,2,1" && trackedExecutionResult.document.attempts[0].decision==="BISECT" && $("tracked-adaptive-attempts").textContent.includes("UNVERIFIED")');
  const completeText=await ev('trackedExecutionResult.serialized');await writeFile(out+'/complete.json',completeText);
  await capture('complete.png');await fill('#tracked-execution-request','{}');await loadFile(out+'/complete.json');
  await wait('!trackedExecutionBusy && trackedExecutionResult?.document.status==="COMPLETE" && JSON.parse($("tracked-execution-request").value).initial_ids?.[0]==="TE-fundamental"',resultTimeout);
  if(completeText!==await ev('trackedExecutionResult.serialized'))throw Error('complete replay changed text');
  report.checks.push({operation:'completed TE file replays without changing evidence',passed:true});
  if(adaptive){
    const stopped=args['--stopped-request'] ? JSON.parse(await readFile(args['--stopped-request'],'utf8')) : structuredClone(request);stopped.adaptive.max_depth=0;
    if(acceptedSweep && !args['--stopped-request']){stopped.study.affine_coefficients.axial_scale=[1.];stopped.step_controls.forEach(c=>c.minimum_overlap=.999999);}
    await fill('#tracked-execution-request',JSON.stringify(stopped));const id=await launch('#tracked-execution-start');await openJob(id,'UNVERIFIED',1);
    await check('depth limit leaves original target unreached and prohibits resume',`trackedExecutionResult.document.unreached_target_indices.join(",")===${JSON.stringify(acceptedSweep?'1,2':'1')} && $("tracked-execution-status").textContent.includes("二分深さの上限") && $("tracked-execution-resume").disabled && !$("tracked-execution-save").disabled`);
    await writeFile(out+'/stopped.json',await ev('trackedExecutionResult.serialized'));await capture('stopped.png');
  }
  }
  report.source_changed_during_run=!isDeepStrictEqual(report.source_sha256,await sourceHashes());
  report.passed=!report.source_changed_during_run && report.external_requests.length===0 && report.checks.every(c=>c.passed);
  if(!report.passed)throw Error('TE Study GUI verification failed');console.log(JSON.stringify({passed:report.passed,checks:report.checks,job_ids:report.job_ids}));
}catch(e){report.error=String(e);process.exitCode=1;console.error(e);}
finally{await writeFile(out+'/report.json',JSON.stringify(report,null,2));ws?.close();browser.kill();}
