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
if (!args["--url"] || !args["--out"] || !args["--sources"])
  throw Error(
    "Usage: node scripts/verify_gui_curved_piecewise_remesh.mjs --url LAUNCH_URL --out NEW_DIRECTORY --sources CURVED_COMPARISON_VALIDATION_DIRECTORY",
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
  let uiWaitMs=15000;
  const wait = async (expression, ms = uiWaitMs) => {
    const start = performance.now();
    while (performance.now() - start < ms) {
      if (await ev(expression)) return;
      await sleep(100);
    }
    throw Error(
      `UI timeout: ${expression}; ${JSON.stringify(await ev('({busy:trackingBusy,errorHidden:$("error").hidden,error:$("error").textContent})'))}`,
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
  const check = async (name, expression) => {
    if (!await ev(expression)) throw Error(name);
    report.checks.push({operation:name,passed:true});
  };
  const select = async (id,value) => ev(`(()=>{const e=document.getElementById(${JSON.stringify(id)});e.value=${JSON.stringify(value)};e.dispatchEvent(new Event("change",{bubbles:true}))})()`);
  const loadFile = async filename => {
    const {root}=await call("DOM.getDocument",{},sessionId);
    const {nodeId}=await call("DOM.querySelector",{nodeId:root.nodeId,selector:"#tracking-open"},sessionId);
    await call("DOM.setFileInputFiles",{nodeId,files:[resolve(filename)]},sessionId);
  };
  await ev('document.querySelector("#import-path").closest("details").open=true');

  await ev('refreshJobs()');
  const imported={},known=new Set(await ev('[...$("tracking-current").options].map(x=>x.value).filter(Boolean)'));
  for (const stage of ['old','new']) {
    await fill('#import-path',resolve(args['--sources'],`scale-1-${stage}`));await click('#import-result');
    await wait(`document.querySelector('#tracking-current').options.length===${known.size+2}`);
    const ids=await ev('[...$("tracking-current").options].map(x=>x.value).filter(Boolean)');
    imported[stage]=ids.find(id=>!known.has(id));known.add(imported[stage]);
  }
  const meshes=JSON.parse(await readFile(resolve(args['--sources'],'scale-1-comparison-meshes.json'),'utf8'));
  // Full version-4 history replay reconstructs multiple common partitions;
  // the measured native reverse/replay takes more than the old 15-second wait.
  if(meshes[0].schema_version===4)uiWaitMs=60000;
  report.ui_wait_ms=uiWaitMs;
  await select('tracking-previous',imported.old);await select('tracking-current',imported.new);
  await select('tracking-mapping','piecewise_remesh');
  await fill('#tracking-ids','["fundamental"]');await fill('#tracking-order',8);
  await fill('#tracking-overlap',.9);await fill('#tracking-margin',.05);await fill('#tracking-gap',1e-6);await fill('#tracking-rank',1e-8);
  await fill('#tracking-comparison-json',JSON.stringify(meshes));await click('#tracking-compare');
  await wait('trackingResult?.document.status==="PASS" && !trackingBusy');
  await check('GUI uses curved comparison declarations with independent native meshes',
    'trackingResult.document.tracking.physical_mapping.comparison_geometry_order===2 && trackingResult.document.tracking.physical_mapping.solver_triangle_counts[1]===4*trackingResult.document.tracking.physical_mapping.solver_triangle_counts[0] && !$("tracking-comparison").hidden');
  const pair=await ev('trackingResult.document');
  await writeFile(out+'/pair.json',JSON.stringify(pair,null,2));
  const expected=JSON.parse(await readFile(resolve(args['--sources'],'scale-1-order-8-pair.json'),'utf8'));
  // Browser JSON writes 0 for 0.0. Declaration byte hashes legitimately differ;
  // replay below verifies each against its own request. Compare all other data.
  const actualTracking=structuredClone(pair.tracking),expectedTracking=structuredClone(expected.tracking);
  delete actualTracking.physical_mapping.comparison_mesh_sha256;
  delete expectedTracking.physical_mapping.comparison_mesh_sha256;
  if(!isDeepStrictEqual(actualTracking,expectedTracking))throw Error('GUI tracking differs from independent Python/CLI report');
  report.checks.push({operation:'GUI numerical tracking report equals Python/CLI',passed:true});
  if(meshes[0].schema_version===4) {
    await check('the complete common integration partition and both history sizes are visible',
      '$("tracking-status").textContent.includes("共通積分分割") && $("tracking-status").textContent.includes("曲線上の節点順") && trackingResult.document.tracking.physical_mapping.common_reference_partition.final_cell_counts.join(",")==="111,112"');
    const limited=structuredClone(meshes);for(const m of limited)m.max_pair_tests=1;
    await fill('#tracking-comparison-json',JSON.stringify(limited));await click('#tracking-compare');
    await wait('!$("error").hidden && !trackingBusy && $("error").textContent.includes("max_pair_tests")');
    if(!isDeepStrictEqual(await ev('trackingResult.document'),pair))throw Error('Failed common partition budget replaced verified pair');
    report.checks.push({operation:'common partition pair budget rejects before replacing the verified result',passed:true});
    await fill('#tracking-comparison-json',JSON.stringify(meshes));
  }
  if(meshes[0].schema_version===3) {
    await check('automatic correspondence and the explicit boundary policy are visible',
      '$("tracking-status").textContent.includes("曲線上の節点順") && trackingResult.document.tracking.physical_mapping.numbering_correspondence.current_cell_for_previous.length===26');
    const strict=structuredClone(meshes);
    for(const m of strict)m.boundary_pairing='same_curve_fractions';
    await fill('#tracking-comparison-json',JSON.stringify(strict));await click('#tracking-compare');
    await wait('!$("error").hidden && !trackingBusy && $("error").textContent.includes("fractions")');
    if(!isDeepStrictEqual(await ev('trackingResult.document'),pair))throw Error('Failed correspondence policy replaced verified pair');
    report.checks.push({operation:'incompatible fraction policy fails without replacing verified pair',passed:true});
    await fill('#tracking-comparison-json',JSON.stringify(meshes));
  }
  await click('#tracking-start');await wait('trackingResult?.document.document_type==="mode_tracking_history" && !trackingBusy');
  const one=await ev('trackingResult.document');
  await select('tracking-current',imported.old);await click('#tracking-extend');
  await wait('!$("error").hidden && !trackingBusy');
  if(!isDeepStrictEqual(await ev('trackingResult.document'),one))throw Error('wrong-direction failure changed verified history');
  report.checks.push({operation:'unswapped curved maps fail reverse extension without replacing history',passed:true});
  await click('#tracking-comparison-swap');await click('#tracking-extend');
  await wait('trackingResult?.document.steps?.length===2 && !trackingBusy');
  await check('explicitly swapped nonlinear maps retain the mode ID on return',
    `trackingResult.document.status==="PASS" && trackingResult.document.current_mode_ids[0]==="fundamental" && trackingResult.document.steps[1].request.controls.comparison_meshes[0].schema_version===${meshes[0].schema_version}`);
  await click('#tracking-save');
  let saved;
  for(let n=0;n<100;n++){try{saved=JSON.parse(await readFile(out+'/downloads/mode-tracking-history.json','utf8'));break;}catch{}await sleep(100);}
  if(!isDeepStrictEqual(saved,await ev('trackingResult.document')))throw Error('download differs from verified nonlinear history');
  report.checks.push({operation:'download retains the complete nested geometry declarations and verified history',passed:true});
  await click('#tracking-reset');await loadFile(out+'/downloads/mode-tracking-history.json');
  await wait('trackingResult?.document.steps?.length===2 && !trackingBusy');
  await check('saved replay restores both curved comparison meshes and mapping choice',
    '$("tracking-mapping").value==="piecewise_remesh" && JSON.stringify(JSON.parse($("tracking-comparison-json").value))===JSON.stringify(trackingResult.document.steps.at(-1).request.controls.comparison_meshes)');
  const confirmed=await ev('trackingResult.document');
  const bad=structuredClone(saved);bad.steps[0].request.controls.comparison_meshes[0].source_mesh.points[0][0]+=.001;
  await writeFile(out+'/changed-history.json',JSON.stringify(bad));await loadFile(out+'/changed-history.json');
  await wait('!$("error").hidden && !trackingBusy');
  if(!isDeepStrictEqual(await ev('trackingResult.document'),confirmed))throw Error('modified source declaration replaced the verified history');
  report.checks.push({operation:'modified nested source geometry is rejected during replay and history is retained',passed:true});
  await fill('#tracking-comparison-json','[{},{}]');await click('#tracking-extend');
  await wait('!$("error").hidden && !trackingBusy');
  if(!isDeepStrictEqual(await ev('trackingResult.document'),confirmed))throw Error('invalid nested controls changed history');
  report.checks.push({operation:'invalid comparison geometry input cannot partially change history',passed:true});
  await loadFile(out+'/downloads/mode-tracking-history.json');
  await wait('$("error").hidden && !trackingBusy && JSON.stringify(JSON.parse($("tracking-comparison-json").value))===JSON.stringify(trackingResult.document.steps.at(-1).request.controls.comparison_meshes)');
  const rect=await ev('(()=>{const r=$("mode-tracking").getBoundingClientRect();return {x:r.x+scrollX,y:r.y+scrollY,width:r.width,height:r.height,scale:1}})()');
  const shot=await call('Page.captureScreenshot',{captureBeyondViewport:true,clip:rect},sessionId);
  await writeFile(out+'/tracking.png',Buffer.from(shot.data,'base64'));
  report.source_changed_during_run=!isDeepStrictEqual(report.source_sha256,await sourceHashes());
  report.passed=!report.source_changed_during_run && report.external_requests.length===0 && report.checks.every(c=>c.passed);
  if (!report.passed) throw Error("mode tracking GUI checks failed");
  console.log(JSON.stringify({passed:report.passed,checks:report.checks,external_requests:report.external_requests}));
} catch (e) {
  report.error=String(e);process.exitCode=1;console.error(e);
} finally {
  await writeFile(out+"/report.json",JSON.stringify(report,null,2));ws?.close();browser.kill();
}
