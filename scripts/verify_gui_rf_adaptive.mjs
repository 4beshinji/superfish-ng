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
if (!args["--url"] || !args["--out"] || !args["--request"] || !args["--old-checkpoint"] || !args["--workspace"])
  throw Error(
    "Usage: node scripts/verify_gui_curved_adaptive.mjs --url LAUNCH_URL --out NEW_DIRECTORY --request REQUEST_JSON --old-checkpoint VERSION_4_CHECKPOINT --workspace GUI_WORKSPACE",
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
  const request=JSON.parse(await readFile(args['--request'],'utf8'));
  const loadFile=async(selector,filename)=>{const {root}=await call('DOM.getDocument',{},sessionId);const {nodeId}=await call('DOM.querySelector',{nodeId:root.nodeId,selector},sessionId);await call('DOM.setFileInputFiles',{nodeId,files:[resolve(filename)]},sessionId);};
  const launch=async(selector)=>{
    const old=await ev('document.querySelector("#refine-job").textContent');await click(selector);
    await wait(`!refinementBusy && document.querySelector('#refine-job').textContent!==${JSON.stringify(old)}`,600000);
    return await ev('document.querySelector("#refine-job").textContent.match(/開始しました: ([a-zA-Z0-9-]+)/)[1]');
  };
  const openJob=async(jobId,status,count)=>{
    await wait(`document.querySelector('[data-job="${jobId}"] strong')?.textContent.includes(${JSON.stringify(status)})`,600000);
    await click(`[data-job="${jobId}"] button`);
    await wait(`!refinementBusy && refinementResult?.document.status===${JSON.stringify(status)} && refinementResult.document.levels.length===${count}`,600000);
  };
  await writeFile(out+'/case.json',JSON.stringify(request.case));
  await loadFile('#open',out+'/case.json');await wait('document.querySelector("#geometry-type").value==="curved_contour"');
  await ev('(()=>{const e=document.querySelector("#refine-version");e.value="5";e.dispatchEvent(new Event("change",{bubbles:true}))})()');
  for(const [id,value] of [['bulk',request.bulk_fraction],['max-levels',request.max_levels],['max-triangles',request.max_triangles],['angle',request.minimum_corner_angle_deg],['ids',JSON.stringify(request.initial_ids)],['mode-id',request.mode_id],['quadrature-order',request.quadrature_check_order],['quadrature-tolerance',request.quadrature_relative_tolerance],['frequency',request.relative_tolerances.frequency_hz],['rq',request.relative_tolerances.r_over_q_accelerator_ohm],['g',request.relative_tolerances.geometry_factor_ohm],['epk',request.surface_relative_tolerances.epk_over_eacc],['bpk',request.surface_relative_tolerances.bpk_over_eacc_mt_per_mv_per_m]])await fill('#refine-'+id,value);
  await check('version 5 exposes curved controls and total event budget','document.querySelector("#refine-version").value==="5" && !document.querySelector("#refine-quadrature-order").disabled && document.querySelector("#refine-max-levels-label").textContent.includes("未採用") && document.querySelector("#refine-bulk-label").textContent.includes("RF")');
  await click('#refine-prepare');await wait('document.querySelector("#refine-request").value.includes("nested_curved")');
  const built=await ev('JSON.parse(document.querySelector("#refine-request").value)');await writeFile(out+'/built-request.json',JSON.stringify(built,null,2));
  if(built.schema_version!==5 || built.minimum_corner_angle_deg!==request.minimum_corner_angle_deg || 'minimum_angle_deg' in built)throw Error('incorrect version 5 request');
  report.checks.push({operation:'form produces strict version 5 request',passed:true});
  await fill('#refine-limit','2');const first=await launch('#refine-start');await openJob(first,'PAUSED',2);
  await check('failed probe shows original parent and remains unaccepted','document.querySelector("#refine-levels tbody").rows[1].cells[9].textContent==="1" && document.querySelector("#refine-levels tbody").rows[1].cells[10].textContent==="未採用" && document.querySelector("#refine-field-event").value==="0" && document.querySelector("#refine-status").textContent.includes("未採用の確認も含む") && document.querySelector("#refine-confirmation").textContent.includes("親計算 1")');
  await ev('document.querySelector("#refine-field-event").value="1"');await click('#refine-open-field');
  await wait('currentResult?.result.mesh.triangles===40 && !document.querySelector("#field-image").hidden',600000);
  await check('explicit probe selection opens the unaccepted confirmation field','document.querySelector("#refine-field-event").value==="1" && currentResult.result.mesh.triangles===refinementResult.document.levels[1].triangles');
  await fill('#refine-limit','1');const local=await launch('#refine-resume');await openJob(local,'PAUSED',3);
  await check('local branch returns to original parent and becomes selected field','document.querySelector("#refine-levels tbody").rows[2].cells[9].textContent==="1" && document.querySelector("#refine-levels tbody").rows[2].cells[10].textContent==="採用" && document.querySelector("#refine-field-event").value==="2" && document.querySelector("#refine-confirmation").textContent.includes("1 → 3")');
  await fill('#refine-limit','');const final=await launch('#refine-resume');await openJob(final,'TARGETS_MET',5);
  const durations=await Promise.all([first,local,final].map(async identifier=>JSON.parse(await readFile(resolve(args['--workspace'],identifier,'job.json'),'utf8')).elapsed_seconds));
  const total=durations.reduce((a,b)=>a+b,0);
  await check('three ancestor job durations are counted once including the rejected probe',`refinementResult.execution_cost.all_event_owners_timed && refinementResult.execution_cost.jobs.length===3 && Math.abs(refinementResult.execution_cost.recorded_seconds-${total})<1e-9 && document.querySelector('#refine-cost').textContent.includes('時間記録あり 3 ジョブ') && document.querySelector('#refine-cost').textContent.includes('時間不明の計算 0 回')`);
  await check('two accepted comparisons populate all five gates and integration rows','[...document.querySelector("#refine-gates tbody").rows].length===5 && [...document.querySelector("#refine-gates tbody").rows].every(r=>r.cells[1].textContent!=="—" && r.cells[2].textContent!=="—" && r.cells[4].textContent==="条件内") && document.querySelector("#refine-quadrature tbody").rows.length===5 && !document.querySelector("#refine-quadrature").hidden && document.querySelector("#refine-confirmation").textContent.includes("最終連続確認 2 回") && document.querySelector("#affine-surface-assess").disabled');
  const expected=await ev('refinementResult.serialized');await click('#refine-save');
  const file=out+'/downloads/adaptive-refinement-checkpoint.json';let downloaded;
  for(let i=0;i<100;i++){try{downloaded=await readFile(file,'utf8');if(downloaded===expected)break;}catch{}await sleep(100);}
  if(downloaded!==expected)throw Error('download mismatch');report.checks.push({operation:'checkpoint download is exact',passed:true});
  await call('Page.reload',{},sessionId);await wait('typeof refinementResult!=="undefined" && refinementResult===null && document.querySelector("#shape polygon")');
  await loadFile('#refine-open',file);await wait('!refinementBusy && refinementResult?.document.status==="TARGETS_MET"',600000);
  await check('reopening restores branch state and final accepted field','document.querySelector("#refine-version").value==="5" && document.querySelector("#refine-field-event").value==="4" && document.querySelector("#refine-levels tbody").rows[1].cells[10].textContent==="未採用"');
  await check('reopening recomputes the same observed total from local jobs',`Math.abs(refinementResult.execution_cost.recorded_seconds-${total})<1e-9 && refinementResult.execution_cost.jobs.length===3`);
  const rect=await ev('(()=>{const a=document.querySelector("#refine-status").getBoundingClientRect(),b=document.querySelector("#refine-levels").getBoundingClientRect();return {x:a.x+scrollX,y:a.y+scrollY,width:Math.max(a.width,b.width),height:b.bottom-a.top,scale:1}})()');
  const shot=await call('Page.captureScreenshot',{captureBeyondViewport:true,clip:rect},sessionId);await writeFile(out+'/rf-branches.png',Buffer.from(shot.data,'base64'));
  const bad=JSON.parse(downloaded);bad.levels[2].parent_event_index=1;await writeFile(out+'/changed.json',JSON.stringify(bad));
  await loadFile('#refine-open',out+'/changed.json');await wait('!refinementBusy && !document.querySelector("#error").hidden',600000);
  await check('altered parent is rejected without replacing the verified checkpoint','refinementResult.document.status==="TARGETS_MET" && document.querySelector("#error").textContent.includes("replay")');
  const long=structuredClone(built);long.max_levels=100;for(const key of Object.keys(long.relative_tolerances))long.relative_tolerances[key]=1e-14;for(const key of Object.keys(long.surface_relative_tolerances))long.surface_relative_tolerances[key]=1e-14;
  await fill('#refine-request',JSON.stringify(long));const cancelled=await launch('#refine-start');
  const checkpoint=resolve(args['--workspace'],cancelled,'execution/checkpoint-001.json');
  let ready=false;for(let n=0;n<300;n++){try{await readFile(checkpoint);ready=true;break;}catch{}await sleep(100);}if(!ready)throw Error('no checkpoint before cancellation');
  await wait(`document.querySelector('[data-job="${cancelled}"] button')?.textContent==='中止'`,600000);await click(`[data-job="${cancelled}"] button`);
  await wait(`document.querySelector('[data-job="${cancelled}"] strong')?.textContent.includes('中止')`,600000);
  await loadFile('#refine-open',checkpoint);await wait('!refinementBusy && refinementResult?.document.status==="PAUSED" && refinementResult.document.levels.length===1',600000);
  await fill('#refine-limit','1');const resumed=await launch('#refine-resume');await openJob(resumed,'PAUSED',2);
  await check('cancelled job checkpoint resumes without discarding its parent source',`refinementResult.document.level_runs[0].includes(${JSON.stringify(cancelled)}) && refinementResult.document.levels[1].parent_event_index===0`);
  const resumedDurations=await Promise.all([cancelled,resumed].map(async identifier=>JSON.parse(await readFile(resolve(args['--workspace'],identifier,'job.json'),'utf8')).elapsed_seconds));
  if(!resumedDurations.every(value=>Number.isFinite(value)&&value>0))throw Error('cancelled/resumed time missing');
  await check('cancelled work remains in the resumed observed total',`refinementResult.execution_cost.all_event_owners_timed && refinementResult.execution_cost.jobs.length===2 && refinementResult.execution_cost.jobs[0].status==='cancelled' && Math.abs(refinementResult.execution_cost.recorded_seconds-${resumedDurations.reduce((a,b)=>a+b,0)})<1e-9`);
  await loadFile('#refine-open',args['--old-checkpoint']);await wait('!refinementBusy && refinementResult?.document.request.schema_version===4',600000);
  await check('version 4 replay hides branch-only columns and retains two gate intervals','[...document.querySelectorAll("[data-refine-branch]")].every(e=>e.hidden) && [...document.querySelector("#refine-gates tbody").rows].every(r=>r.cells[4].textContent==="条件内") && !document.querySelector("#refine-quadrature").hidden');
  await check('external checkpoint shows unknown time instead of a complete zero total','!refinementResult.execution_cost.all_event_owners_timed && refinementResult.execution_cost.unknown_event_indices.length===refinementResult.document.levels.length && document.querySelector("#refine-cost").textContent.includes("記録のある部分の合計")');
  report.source_changed_during_run=!isDeepStrictEqual(report.source_sha256,await sourceHashes());
  report.passed=!report.source_changed_during_run && report.external_requests.length===0 && report.checks.every(c=>c.passed);
  if(!report.passed)throw Error('RF adaptive GUI checks failed');
  console.log(JSON.stringify({passed:report.passed,checks:report.checks,external_requests:report.external_requests}));
} catch(e){report.error=String(e);process.exitCode=1;console.error(e);}
finally{await writeFile(out+'/report.json',JSON.stringify(report,null,2));ws?.close();browser.kill();}
