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
if (!args["--url"] || !args["--out"] || !args["--request"] || !args["--workspace"])
  throw Error(
    "Usage: node scripts/verify_gui_adaptive_refinement.mjs --url LAUNCH_URL --out NEW_DIRECTORY --request REQUEST_JSON --workspace GUI_WORKSPACE",
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
  const request=JSON.parse(await readFile(args['--request'],'utf8'));request.mode_id=request.initial_ids[1];
  const loadFile=async filename=>{const {root}=await call('DOM.getDocument',{},sessionId);const {nodeId}=await call('DOM.querySelector',{nodeId:root.nodeId,selector:'#refine-open'},sessionId);await call('DOM.setFileInputFiles',{nodeId,files:[resolve(filename)]},sessionId);};
  const launch=async selector=>{
    const old=await ev('document.querySelector("#refine-job").textContent');await click(selector);
    await wait(`!refinementBusy && document.querySelector('#refine-job').textContent!==${JSON.stringify(old)}`);
    return await ev('document.querySelector("#refine-job").textContent.match(/開始しました: ([a-zA-Z0-9-]+)/)[1]');
  };
  const openJob=async(id,status,count)=>{
    await wait(`document.querySelector('[data-job="${id}"] strong')?.textContent.includes(${JSON.stringify(status)})`,60000);
    await click(`[data-job="${id}"] button`);
    await wait(`!refinementBusy && refinementResult?.document.status===${JSON.stringify(status)} && refinementResult.document.levels.length===${count}`,60000);
  };
  await click('#refine-prepare');await wait('document.querySelector("#refine-request").value.includes("uniform_two_steps")');
  await check('form creates explicit version 2 and dedicated tracking settings','JSON.parse(document.querySelector("#refine-request").value).controls.mapping==="nested_affine" && !("sample_order" in JSON.parse(document.querySelector("#refine-request").value).controls) && JSON.parse(document.querySelector("#refine-request").value).relative_tolerances.frequency_hz===.0001');
  await check('request editor uses panel width','document.querySelector("#refine-request").getBoundingClientRect().width>.8*document.querySelector("#adaptive-refinement").getBoundingClientRect().width');
  await ev('document.querySelector("#refine-version").value="1";document.querySelector("#refine-version").dispatchEvent(new Event("change"))');
  await click('#refine-prepare');await wait('JSON.parse(document.querySelector("#refine-request").value).schema_version===1');
  await check('version 1 form explicitly uses sampled tracking','JSON.parse(document.querySelector("#refine-request").value).controls.sample_order===3 && JSON.parse(document.querySelector("#refine-request").value).controls.mapping==="same_domain" && !("confirmation" in JSON.parse(document.querySelector("#refine-request").value))');
  const beforeInvalid=await ev('document.querySelectorAll("#jobs .job").length');
  await fill('#refine-request',JSON.stringify(request).replace('"mapping":"nested_affine"','"mapping":"same_domain","mapping":"nested_affine"'));
  await click('#refine-start');await wait('!refinementBusy && !document.querySelector("#error").hidden');
  await check('raw request rejects duplicate nested keys before reserving a job',`document.querySelector('#error').textContent.includes('duplicate JSON key') && document.querySelectorAll('#jobs .job').length===${beforeInvalid}`);
  await fill('#refine-request',JSON.stringify(request));await fill('#refine-limit','4');
  const first=await launch('#refine-start');await openJob(first,'PAUSED',4);
  await check('one uniform confirmation is paused despite small changes','document.querySelector("#refine-confirmation").textContent.includes("全域確認 1 回") && document.querySelector("#refine-levels tbody").rows[3].cells[1].textContent==="全域確認" && !document.querySelector("#refine-resume").disabled');
  await check('adaptive jobs are excluded from individual result selectors',`![...document.querySelector('#tracking-current').options].some(o=>o.value===${JSON.stringify(first)})`);
  await click('#refine-save');let downloaded;
  const file=out+'/downloads/adaptive-refinement-checkpoint.json';
  for(let n=0;n<100;n++){try{downloaded=await readFile(file,'utf8');break;}catch{}await sleep(100);}
  if(downloaded!==await ev('refinementResult.serialized'))throw Error('download differs from verified JSON');
  report.checks.push({operation:'download preserves the complete verified checkpoint',passed:true});
  await call('Page.reload',{},sessionId);await wait('typeof refinementResult!=="undefined" && refinementResult===null && document.querySelector("#shape polygon")');
  await check('page reload clears in-memory refinement state','refinementResult===null');
  await loadFile(file);await wait('!refinementBusy && refinementResult?.document.levels.length===4',60000);
  await check('saved version and controls restore after reload','document.querySelector("#refine-version").value==="2" && document.querySelector("#refine-order").disabled && JSON.parse(document.querySelector("#refine-request").value).mode_id==="second"');
  const changed=JSON.parse(downloaded);changed.levels[3].refinement_kind='residual';await writeFile(out+'/changed.json',JSON.stringify(changed));
  await loadFile(out+'/changed.json');await wait('!refinementBusy && !document.querySelector("#error").hidden');
  await check('altered confirmation cannot replace verified state','refinementResult.document.levels[3].refinement_kind==="uniform_confirmation" && document.querySelector("#error").textContent.includes("replay")');
  await fill('#refine-request','{}');await fill('#refine-mode-id','edited');await fill('#refine-limit','');
  const second=await launch('#refine-resume');await openJob(second,'TARGETS_MET',5);
  const final=await ev('refinementResult.document');
  if(!isDeepStrictEqual(final.level_runs.slice(0,4),JSON.parse(downloaded).level_runs))throw Error('resume replaced ancestry');
  if((await readdir(resolve(args['--workspace'],second,'execution'))).includes('level-001'))throw Error('resume recomputed first level');
  await check('resume uses saved request and executes only the new confirmation','refinementResult.document.request.mode_id==="second" && document.querySelector("#refine-confirmation").textContent.includes("全域確認 2 回") && document.querySelector("#refine-resume").disabled');
  await check('frequency and RF show both intervals without claiming a physical error bound','document.querySelector("#refine-gates tbody").rows.length===3 && [...document.querySelector("#refine-gates tbody").rows].every(r=>r.cells[1].textContent!=="—" && r.cells[2].textContent!=="—" && r.cells[4].textContent==="条件内") && document.querySelector("#refine-confirmation").textContent.includes("表面ピーク: 未評価。物理誤差上界: なし")');
  const rect=await ev('(()=>{const a=document.querySelector("#refine-status").getBoundingClientRect(),b=document.querySelector("#refine-levels").getBoundingClientRect();return {x:a.x+scrollX,y:a.y+scrollY,width:Math.max(a.width,b.width),height:b.bottom-a.top,scale:1}})()');
  const shot=await call('Page.captureScreenshot',{captureBeyondViewport:true,clip:rect},sessionId);await writeFile(out+'/refinement-result.png',Buffer.from(shot.data,'base64'));
  await click('#refine-open-field');await wait('document.querySelector("#mode").value==="2" && !document.querySelector("#field-image").hidden',60000);
  await check('field opens the tracked second mode','Number(document.querySelector("#mode").value)===refinementResult.document.levels.at(-1).mode_index+1');
  const unresolved=structuredClone(request);unresolved.controls.relative_cluster_gap=.9;
  await fill('#refine-request',JSON.stringify(unresolved));const third=await launch('#refine-start');await openJob(third,'UNVERIFIED',2);
  await check('unresolved identity disables field and resume but retains evidence','document.querySelector("#refine-open-field").disabled && document.querySelector("#refine-resume").disabled && !document.querySelector("#refine-save").disabled && document.querySelector("#refine-levels tbody").rows[1].textContent.includes("評価不可")');
  const limited=structuredClone(request);for(const key in limited.relative_tolerances)limited.relative_tolerances[key]=1e-14;
  await fill('#refine-request',JSON.stringify(limited));const fourth=await launch('#refine-start');await openJob(fourth,'LEVEL_LIMIT',5);
  await check('level limit is not treated as convergence','document.querySelector("#refine-status").textContent.includes("水準上限で停止") && [...document.querySelector("#refine-gates tbody").rows].some(r=>r.cells[4].textContent==="未達") && document.querySelector("#refine-resume").disabled');
  const large=structuredClone(limited);large.case.mesh.nr=30;large.case.mesh.nz=36;large.max_levels=20;large.max_triangles=200000;
  await fill('#refine-request',JSON.stringify(large));const fifth=await launch('#refine-start');
  const partial=resolve(args['--workspace'],fifth,'execution/checkpoint-001.json');let prefix;
  for(let n=0;n<300;n++){try{prefix=JSON.parse(await readFile(partial,'utf8'));break;}catch{}await sleep(100);}
  if(!prefix)throw Error('first checkpoint not saved before cancellation');
  await click(`[data-job="${fifth}"] button`);await wait(`document.querySelector('[data-job="${fifth}"] strong')?.textContent.startsWith('中止')`);
  await check('active cancellation does not publish a completed result',`document.querySelector('[data-job="${fifth}"] button').disabled`);
  await loadFile(partial);await wait('!refinementBusy && refinementResult?.document.levels.length===1 && refinementResult.document.request.max_levels===20',60000);
  await check('cancelled job checkpoint can be reverified and resumed','refinementResult.document.status==="PAUSED" && !document.querySelector("#refine-resume").disabled');
  await fill('#refine-limit','1');const sixth=await launch('#refine-resume');await openJob(sixth,'PAUSED',2);
  await check('cancelled execution resumes with its original first level',`refinementResult.document.level_runs[0]===${JSON.stringify(prefix.level_runs[0])}`);
  const legacy=structuredClone(request);legacy.schema_version=1;delete legacy.confirmation;legacy.controls.mapping='same_domain';legacy.controls.sample_order=3;
  await fill('#refine-request',JSON.stringify(legacy));await fill('#refine-limit','');const seventh=await launch('#refine-start');await openJob(seventh,'TARGETS_MET',3);
  await check('version 1 remains explicitly local-only','document.querySelector("#refine-confirmation").textContent.includes("局所差のみ・全域確認なし") && document.querySelector("#refine-version").value==="1" && !document.querySelector("#refine-order").disabled');
  report.job_ids={first,second,third,fourth,fifth,sixth,seventh};
  report.source_changed_during_run=!isDeepStrictEqual(report.source_sha256,await sourceHashes());
  report.passed=!report.source_changed_during_run && report.external_requests.length===0 && report.checks.every(c=>c.passed);
  if(!report.passed)throw Error('adaptive refinement GUI checks failed');
  console.log(JSON.stringify({passed:report.passed,checks:report.checks,external_requests:report.external_requests}));
} catch(e){report.error=String(e);process.exitCode=1;console.error(e);}
finally{await writeFile(out+'/report.json',JSON.stringify(report,null,2));ws?.close();browser.kill();}
