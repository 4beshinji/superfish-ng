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
    "Usage: node scripts/verify_gui_affine_surface.mjs --url LAUNCH_URL --out NEW_DIRECTORY --request REQUEST_JSON",
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
    await wait(`!refinementBusy && document.querySelector('#refine-job').textContent!==${JSON.stringify(old)}`,60000);
    return await ev('document.querySelector("#refine-job").textContent.match(/開始しました: ([a-zA-Z0-9-]+)/)[1]');
  };
  const openJob=async(id,status,count)=>{
    await wait(`document.querySelector('[data-job="${id}"] strong')?.textContent.includes(${JSON.stringify(status)})`,60000);
    await click(`[data-job="${id}"] button`);
    await wait(`!refinementBusy && refinementResult?.document.status===${JSON.stringify(status)} && refinementResult.document.levels.length===${count}`,60000);
  };
  const assess=async(status,mode='second')=>{
    await fill('#affine-surface-mode-id',mode);await click('#affine-surface-assess');
    await wait(`!affineSurfaceBusy && affineSurfaceResult?.document.status===${JSON.stringify(status)} && affineSurfaceResult.document.mode_id===${JSON.stringify(mode)}`,60000);
  };
  await check('surface assessment requires a loaded sequence of at least three levels','document.querySelector("#affine-surface-assess").disabled');
  await fill('#refine-request',JSON.stringify(request));await fill('#refine-limit','1');
  const first=await launch('#refine-start');await openJob(first,'PAUSED',1);
  await check('one level remains ineligible for a two-interval assessment','document.querySelector("#affine-surface-assess").disabled');
  await fill('#refine-limit','3');const second=await launch('#refine-resume');await openJob(second,'PAUSED',4);
  await assess('CONFIRMATION_PENDING');
  await check('one uniform refinement cannot be presented as complete surface convergence','document.querySelector("#affine-surface-status").textContent.includes("全域確認待ち") && document.querySelector("#affine-surface-confirmation").textContent.includes("全域確認2水準 不足")');
  await check('surface assessment leaves original adaptive surface status unchanged','refinementResult.document.surface_status==="UNASSESSED" && refinementResult.document.status==="PAUSED"');
  await fill('#refine-limit','');const third=await launch('#refine-resume');await openJob(third,'TARGETS_MET',5);
  await check('new adaptive result does not overwrite the previous verified surface assessment','affineSurfaceResult.document.status==="CONFIRMATION_PENDING"');
  await assess('TARGETS_MET');
  await check('surface target can differ from the adaptive target while preserving rank','refinementResult.document.request.mode_id==="fundamental" && affineSurfaceResult.document.mode_id==="second" && [...document.querySelector("#affine-surface-values tbody").rows].every(r=>r.cells[2].textContent==="2")');
  await check('all five quantities have two independently displayed acceptance intervals','document.querySelector("#affine-surface-changes tbody").rows.length===20 && [...document.querySelector("#affine-surface-changes tbody").rows].filter(r=>r.cells[4].textContent==="対象").length===10');
  await check('peak intervals and unassessed physical error remain visible','document.querySelector("#affine-surface-peaks tbody").rows.length===5 && document.querySelector("#affine-surface-confirmation").textContent.includes("物理誤差上界: なし") && document.querySelector("#affine-surface-geometry").textContent.includes("再入角 0")');
  await click('#affine-surface-save');const file=out+'/downloads/affine-surface-convergence.json';let downloaded;
  for(let n=0;n<100;n++){try{downloaded=await readFile(file,'utf8');break;}catch{}await sleep(100);}
  if(downloaded!==await ev('affineSurfaceResult.serialized'))throw Error('download differs from verified text');
  report.checks.push({operation:'download preserves exact verified surface JSON',passed:true});
  const changed=JSON.parse(downloaded);changed.geometry_diagnostic.status='accepted';await writeFile(out+'/changed.json',JSON.stringify(changed));
  await loadFile('#affine-surface-open',out+'/changed.json');await wait('!affineSurfaceBusy && !document.querySelector("#error").hidden',60000);
  await check('altered geometry cannot replace the previous verified assessment','affineSurfaceResult.document.geometry_diagnostic.status==="NO_REENTRANT_CORNERS" && document.querySelector("#error").textContent.includes("replay")');
  await fill('#affine-surface-mode-id','missing');await click('#affine-surface-assess');await wait('!affineSurfaceBusy && !document.querySelector("#error").hidden',60000);
  await check('unresolved identity leaves the prior target and evaluation intact','affineSurfaceResult.document.mode_id==="second" && document.querySelector("#affine-surface-status").textContent.includes("対象ID: second")');
  await click('#affine-surface-replay');await wait('!affineSurfaceBusy && document.querySelector("#affine-surface-mode-id").value==="second"',60000);
  await call('Page.reload',{},sessionId);await wait('typeof affineSurfaceResult!=="undefined" && affineSurfaceResult===null && document.querySelector("#shape polygon")');
  await loadFile('#affine-surface-open',file);await wait('!affineSurfaceBusy && affineSurfaceResult?.document.status==="TARGETS_MET"',60000);
  await check('saved surface replay works after reload without an adaptive document loaded','refinementResult===null && affineSurfaceResult.document.mode_id==="second" && document.querySelector("#affine-surface-assess").disabled && !document.querySelector("#affine-surface-replay").disabled');
  const screenshot=async name=>{
    const rect=await ev('(()=>{const a=document.querySelector("#affine-surface-status").getBoundingClientRect(),b=document.querySelector("#affine-surface-peaks").getBoundingClientRect();return {x:a.x+scrollX,y:a.y+scrollY,width:Math.max(a.width,b.width),height:b.bottom-a.top,scale:1}})()');
    const shot=await call('Page.captureScreenshot',{captureBeyondViewport:true,clip:rect},sessionId);await writeFile(out+'/'+name+'.png',Buffer.from(shot.data,'base64'));
  };
  await screenshot('surface-met');
  await click('#affine-surface-open-field');await wait('document.querySelector("#mode").value==="2" && !document.querySelector("#field-image").hidden',60000);
  await check('field view opens the evaluated identity rather than the adaptive target','Number(document.querySelector("#mode").value)===affineSurfaceResult.document.rows.at(-1).mode_index+1');
  const neck=structuredClone(request);neck.case.geometry.points_zr_m=[[0,.1],[.1,.075],[.2,.1]];neck.minimum_angle_deg=1;neck.controls.minimum_overlap=.8;
  await fill('#refine-request',JSON.stringify(neck));await fill('#refine-limit','3');const fourth=await launch('#refine-start');await openJob(fourth,'PAUSED',3);
  await assess('SINGULAR_GEOMETRY','fundamental');
  await check('reentrant geometry is retained despite completed evaluation','document.querySelector("#affine-surface-status").textContent.includes("再入角：有限ピークは未認定") && document.querySelector("#affine-surface-geometry").textContent.includes("再入角 1") && !document.querySelector("#affine-surface-save").disabled');
  await screenshot('surface-reentrant');
  const unverified=structuredClone(request);unverified.case.geometry.points_zr_m=[[0,.1],[.2,.12]];unverified.case.boundaries={z_min:'electric_symmetry',z_max:'pec'};unverified.controls.minimum_overlap=.8;
  await fill('#refine-request',JSON.stringify(unverified));const fifth=await launch('#refine-start');await openJob(fifth,'PAUSED',3);
  await assess('UNVERIFIED_GEOMETRY','fundamental');
  await check('nonorthogonal symmetry join remains geometrically unverified','document.querySelector("#affine-surface-status").textContent.includes("形状未確認") && document.querySelector("#affine-surface-geometry").textContent.includes("UNVERIFIED_GEOMETRY")');
  const coarse=structuredClone(request);coarse.schema_version=1;delete coarse.confirmation;coarse.controls.mapping='same_domain';coarse.controls.sample_order=3;coarse.controls.minimum_overlap=.8;coarse.case.solver={element_order:1,modes:1};coarse.initial_ids=['fundamental'];coarse.case.mesh={nr:2,nz:2};coarse.max_levels=3;
  await fill('#refine-request',JSON.stringify(coarse));await fill('#refine-limit','');const sixth=await launch('#refine-start');
  await wait(`document.querySelector('[data-job="${sixth}"] strong')?.textContent.startsWith('計算完了')`,60000);await click(`[data-job="${sixth}"] button`);await wait('!refinementBusy && refinementResult?.document.request.schema_version===1',60000);
  await assess('NOT_CONVERGED','fundamental');
  await check('unmet differences are separated from local-only version 1 execution','document.querySelector("#affine-surface-status").textContent.includes("未収束") && document.querySelector("#affine-surface-confirmation").textContent.includes("版1：局所差のみ・全域確認なし") && [...document.querySelector("#affine-surface-changes tbody").rows].some(r=>r.cells[5].textContent==="未達")');
  report.job_ids={first,second,third,fourth,fifth,sixth};
  report.source_changed_during_run=!isDeepStrictEqual(report.source_sha256,await sourceHashes());
  report.passed=!report.source_changed_during_run && report.external_requests.length===0 && report.checks.every(c=>c.passed);
  if(!report.passed)throw Error('affine surface GUI checks failed');
  console.log(JSON.stringify({passed:report.passed,checks:report.checks,external_requests:report.external_requests}));
} catch(e){report.error=String(e);process.exitCode=1;console.error(e);}
finally{await writeFile(out+'/report.json',JSON.stringify(report,null,2));ws?.close();browser.kill();}
