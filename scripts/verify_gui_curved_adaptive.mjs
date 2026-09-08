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
if (!args["--url"] || !args["--out"] || !args["--request"] || !args["--old-checkpoint"])
  throw Error(
    "Usage: node scripts/verify_gui_curved_adaptive.mjs --url LAUNCH_URL --out NEW_DIRECTORY --request REQUEST_JSON --old-checkpoint VERSION_3_CHECKPOINT",
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
  const openJob=async(id,status,count)=>{
    await wait(`document.querySelector('[data-job="${id}"] strong')?.textContent.includes(${JSON.stringify(status)})`,600000);
    await click(`[data-job="${id}"] button`);
    await wait(`!refinementBusy && refinementResult?.document.status===${JSON.stringify(status)} && refinementResult.document.levels.length===${count}`,600000);
  };
  await writeFile(out+'/case.json',JSON.stringify(request.case));
  await loadFile('#open',out+'/case.json');await wait('document.querySelector("#geometry-type").value==="curved_contour"');
  await ev('(()=>{const e=document.querySelector("#refine-version");e.value="4";e.dispatchEvent(new Event("change",{bubbles:true}))})()');
  for(const [id,value] of [['bulk',request.bulk_fraction],['max-levels',request.max_levels],['max-triangles',request.max_triangles],['angle',request.minimum_corner_angle_deg],['ids',JSON.stringify(request.initial_ids)],['mode-id',request.mode_id],['quadrature-order',request.quadrature_check_order],['quadrature-tolerance',request.quadrature_relative_tolerance]])await fill('#refine-'+id,value);
  await check('version 4 exposes peak and quadrature controls with mapped corner angle definition','!document.querySelector("#refine-epk").disabled && !document.querySelector("#refine-quadrature-order").disabled && document.querySelector("#refine-order").disabled && document.querySelector("#refine-angle-label").textContent.includes("頂点接線")');
  await click('#refine-prepare');await wait('document.querySelector("#refine-request").value.includes("nested_curved")');
  await check('form builds strict curved request with separate corner and quadrature controls',`(()=>{const r=JSON.parse(document.querySelector('#refine-request').value);return r.schema_version===4 && r.case.mesh.geometry_order===2 && r.confirmation==='uniform_two_steps' && r.controls.mapping==='nested_curved' && r.minimum_corner_angle_deg===${request.minimum_corner_angle_deg} && !('minimum_angle_deg' in r) && r.quadrature_check_order===${request.quadrature_check_order} && r.quadrature_relative_tolerance===${request.quadrature_relative_tolerance}})()`);
  // Run the request made by the actual form, rather than substitute the fixture JSON.
  const built=await ev('JSON.parse(document.querySelector("#refine-request").value)');await writeFile(out+'/built-request.json',JSON.stringify(built,null,2));
  await fill('#refine-limit','4');const first=await launch('#refine-start');await openJob(first,'PAUSED',4);
  await check('four computed levels expose five gates and all quadrature comparisons','document.querySelector("#refine-gates tbody").rows.length===5 && document.querySelector("#refine-peaks tbody").rows.length===4 && document.querySelector("#refine-quadrature tbody").rows.length===4 && !document.querySelector("#refine-quadrature").hidden && [...document.querySelector("#refine-quadrature tbody").rows].every(r=>r.cells[9].textContent==="条件内")');
  await fill('#refine-quadrature-order','25');await fill('#refine-angle','9');await fill('#refine-limit','');const second=await launch('#refine-resume');await openJob(second,'TARGETS_MET',5);
  await check('resume restores saved quadrature and quality settings',`refinementResult.document.request.quadrature_check_order===${request.quadrature_check_order} && Number(document.querySelector('#refine-quadrature-order').value)===${request.quadrature_check_order} && Number(document.querySelector('#refine-angle').value)===${request.minimum_corner_angle_deg}`);
  await check('confirmed five quantities retain smooth geometry and two uniform steps','[...document.querySelector("#refine-gates tbody").rows].every(r=>r.cells[4].textContent==="条件内") && [...document.querySelector("#refine-peaks tbody").rows].every(r=>r.cells[5].textContent==="SMOOTH_WITHIN_TOLERANCE") && document.querySelector("#refine-confirmation").textContent.includes("全域確認 2 回") && document.querySelector("#refine-confirmation").textContent.includes("物理誤差上界: なし") && document.querySelector("#affine-surface-assess").disabled');
  const expected=await ev('refinementResult.serialized');await click('#refine-save');
  const file=out+'/downloads/adaptive-refinement-checkpoint.json';let downloaded;
  for(let i=0;i<100;i++){try{downloaded=await readFile(file,'utf8');if(downloaded===expected)break;}catch{}await sleep(100);}
  if(downloaded!==expected)throw Error('saved checkpoint differs from server JSON');report.checks.push({operation:'download preserves exact verified checkpoint',passed:true});
  const bad=JSON.parse(downloaded);bad.levels[0].quadrature_check.relative_differences.mass_form=1;await writeFile(out+'/changed.json',JSON.stringify(bad));
  await loadFile('#refine-open',out+'/changed.json');await wait('!refinementBusy && !document.querySelector("#error").hidden',600000);
  await check('changed quadrature result is rejected without replacing verified data','refinementResult.document.status==="TARGETS_MET" && document.querySelector("#error").textContent.includes("replay")');
  await call('Page.reload',{},sessionId);await wait('typeof refinementResult!=="undefined" && refinementResult===null && document.querySelector("#shape polygon")');
  await loadFile('#refine-open',file);await wait('!refinementBusy && refinementResult?.document.status==="TARGETS_MET"',600000);
  await check('saved checkpoint restores version 4 and every per-level table','document.querySelector("#refine-version").value==="4" && document.querySelector("#refine-quadrature tbody").rows.length===5 && document.querySelector("#refine-peaks tbody").rows.length===5 && !document.querySelector("#refine-quadrature-order").disabled');
  const rect=await ev('(()=>{const a=document.querySelector("#refine-status").getBoundingClientRect(),b=document.querySelector("#refine-quadrature").getBoundingClientRect();return {x:a.x+scrollX,y:a.y+scrollY,width:Math.max(a.width,b.width),height:b.bottom-a.top,scale:1}})()');
  const shot=await call('Page.captureScreenshot',{captureBeyondViewport:true,clip:rect},sessionId);await writeFile(out+'/curved-confirmed.png',Buffer.from(shot.data,'base64'));
  await click('#refine-open-field');await wait('document.querySelector("#mode").value==="1" && !document.querySelector("#field-image").hidden',600000);
  await check('target field opens the verified curved mode','Number(document.querySelector("#mode").value)===refinementResult.document.levels.at(-1).mode_index+1');
  const limited=structuredClone(built);limited.quadrature_relative_tolerance=1e-30;await fill('#refine-request',JSON.stringify(limited));const third=await launch('#refine-start');await openJob(third,'QUADRATURE_UNVERIFIED',1);
  await check('failed integration comparison is visible and cannot resume','document.querySelector("#refine-status").textContent.includes("高次積分との比較を確認できず停止") && document.querySelector("#refine-quadrature tbody").rows[0].cells[9].textContent==="未達" && document.querySelector("#refine-resume").disabled && refinementResult.document.surface_status==="UNVERIFIED"');
  await loadFile('#refine-open',args['--old-checkpoint']);await wait('!refinementBusy && refinementResult?.document.request.schema_version===3',600000);
  await check('opening version 3 clears curved integration results and restores affine angle','document.querySelector("#refine-quadrature").hidden && document.querySelector("#refine-quadrature tbody").rows.length===0 && document.querySelector("#refine-quadrature-order").disabled && document.querySelector("#refine-angle-label").textContent.includes("直線三角形") && document.querySelector("#refine-gates tbody").rows.length===5');
  report.source_changed_during_run=!isDeepStrictEqual(report.source_sha256,await sourceHashes());
  report.passed=!report.source_changed_during_run && report.external_requests.length===0 && report.checks.every(c=>c.passed);
  if(!report.passed)throw Error('curved adaptive GUI checks failed');
  console.log(JSON.stringify({passed:report.passed,checks:report.checks,external_requests:report.external_requests}));
} catch(e){report.error=String(e);process.exitCode=1;console.error(e);}
finally{await writeFile(out+'/report.json',JSON.stringify(report,null,2));ws?.close();browser.kill();}
