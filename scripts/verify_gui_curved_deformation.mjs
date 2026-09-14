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
if (!args['--url'] || !args['--out'] || !args['--case'] || !args['--geometry'] || !args['--target'] || !args['--native-result']) throw Error('Require --url --out --case --geometry --target --native-result');
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




  const {root}=await call('DOM.getDocument',{},sessionId);
  const {nodeId}=await call('DOM.querySelector',{nodeId:root.nodeId,selector:'#open'},sessionId);
  const open=async(path)=>{
    await ev('window.__opened=false;window.__apply=applyProject;applyProject=p=>{__apply(p);window.__opened=true;applyProject=__apply}');
    await call('DOM.setFileInputFiles',{nodeId,files:[resolve(path)]},sessionId);await wait('__opened');
  };
  const loadFile=async(selector,path)=>{
    const {nodeId}=await call('DOM.querySelector',{nodeId:root.nodeId,selector},sessionId);
    await call('DOM.setFileInputFiles',{nodeId,files:[resolve(path)]},sessionId);
  };
  const select=async(id,value)=>ev(`(()=>{const e=$(${JSON.stringify(id)});e.value=${JSON.stringify(value)};e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}))})()`);
  const expected=JSON.parse(await readFile(args['--target'],'utf8'));
  const geometryText=await readFile(args['--geometry'],'utf8');
  const startPreview=async()=>{
    await click('#deformation-preview');
    await wait('!$("deformation-preview").disabled',120000);
  };
  const prepare=async()=>{
    await open(args['--case']);await ev('$("deformation-panel").open=true');
    await fill('#deformation-geometry',geometryText);await select('deformation-rf','fixed');await fill('#deformation-angle',1);
  };
  if(args['--additional-only']) {
    const folder=resolve(args['--additional-only']);
    await open(folder+'/rf-source.json');await ev('$(' + JSON.stringify('deformation-panel') + ').open=true');
    await loadFile('#deformation-open',folder+'/rf-target.json');await wait('$("deformation-geometry").value.includes("0.25")');
    await select('deformation-rf','axis_fraction');await startPreview();
    await check('axis-fraction selector scales all explicit RF coordinates',
      '(()=>{const r=deformationResult.response.target.rf_coordinates;return Math.abs(r.active_length_m/.1875-1)<1e-14 && Math.abs(r.voltage_interval_m[0]/.025-1)<1e-14 && Math.abs(r.voltage_interval_m[1]/.225-1)<1e-14 && Math.abs(r.phase_origin_m/.0375-1)<1e-14 && r.phase_origin_explicit && $("deformation-rf-info").textContent.includes("187.500")})()');
    const scaled=await ev('deformationResult.response.target.project');await writeFile(out+'/rf-scaled.json',JSON.stringify(scaled,null,2));
    await select('deformation-rf','fixed');await startPreview();
    await check('fixed selector preserves all explicit RF coordinates',
      '(()=>{const r=deformationResult.response.target.rf_coordinates;return r.active_length_m===.15 && r.voltage_interval_m[0]===.02 && r.voltage_interval_m[1]===.18 && r.phase_origin_m===.03 && r.phase_origin_explicit})()');
    await fill('#deformation-angle',60);await startPreview();
    await check('invalid quality floor clears any previous candidate','!deformationResult && $("deformation-apply").disabled && $("error").textContent.includes("strictly between") && $("deformation-status").textContent.includes("準備できません")');
    await open(folder+'/folded-source.json');await loadFile('#deformation-open',folder+'/folded-target.json');
    await wait('$("deformation-geometry").value.includes("0.04")');await fill('#deformation-angle',1);await startPreview();
    await check('a valid concave target with an actually folded mesh is refused','!deformationResult && $("deformation-apply").disabled && $("error").textContent.includes("Jacobian")');
    await prepare();await ev('window.__baseApi=api;window.__release=null;api=async(...args)=>{const r=await __baseApi(...args);if(args[0]==="preview-curved-deformation")await new Promise(resolve=>window.__release=resolve);return r}');
    await click('#deformation-preview');await wait('!!window.__release',120000);await fill('#beta',.9);await fill('#beta',1);await ev('__release()');await wait('!$("deformation-preview").disabled');
    await check('change and restoration of identical values still invalidates an in-flight response','!deformationResult && $("deformation-apply").disabled && $("error").textContent.includes("入力が変わりました")');await ev('api=__baseApi');
    await prepare();await startPreview();
    await check('preview label remains readable in the narrow editor',
      'parseFloat(getComputedStyle(document.querySelector("#deformation-boundary text")).fontSize)===26 && $("deformation-geometry").getBoundingClientRect().width>.9*$("deformation-panel").getBoundingClientRect().width');
    const rect=await ev('(()=>{const r=$("deformation-panel").getBoundingClientRect();return {x:r.x+scrollX,y:r.y+scrollY,width:r.width,height:r.height,scale:1}})()');
    const shot=await call('Page.captureScreenshot',{captureBeyondViewport:true,clip:rect},sessionId);await writeFile(out+'/deformation-preview.png',Buffer.from(shot.data,'base64'));
  } else {
  await open(args['--case']);await ev('$("deformation-panel").open=true');
  const original=await ev('collect()');
  await click('#deformation-template');await wait('!$("deformation-template").disabled && $("deformation-geometry").value.startsWith("{")');
  await check('template copies current native SI geometry without changing the Project','JSON.stringify(JSON.parse($("deformation-geometry").value))===JSON.stringify(geometry()) && !dirty');
  await loadFile('#deformation-open',args['--geometry']);await wait('$("deformation-geometry").value.includes("0.09")');
  if(await ev('$("deformation-geometry").value')!==geometryText)throw Error('Target file text changed');
  report.checks.push({operation:'target geometry file preserves raw JSON and SI values',passed:true});
  await fill('#deformation-geometry','{"type":"curved_contour","type":"curved_contour"}');await startPreview();
  await check('duplicate geometry fields reach strict server reader and cannot apply','$("error").textContent.includes("duplicate JSON key") && $("deformation-apply").disabled && $("deformation-view").hidden');
  await fill('#deformation-geometry',geometryText);await startPreview();
  await check('valid preview is separate from current Project and exposes native P2 boundary','!!deformationResult && !$("deformation-view").hidden && document.querySelectorAll("#deformation-boundary path").length===2 && [...document.querySelectorAll("#deformation-boundary path")].every(p=>p.getAttribute("d").includes(" Q "))');
  const response=await ev('deformationResult.response');
  if(!isDeepStrictEqual(response.target.project,expected) || !isDeepStrictEqual(await ev('collect()'),original))throw Error('Preview differs from CLI or changed source');
  await writeFile(out+'/preview.json',JSON.stringify(response,null,2));
  report.checks.push({operation:'full preview Project equals CLI deformation and source remains unchanged',passed:true});
  await click('#deformation-save');let raw;
  for(let n=0;n<200;n++){try{raw=await readFile(out+'/downloads/deformed-project.json','utf8');break;}catch{}await sleep(100);}
  if(raw!==response.serialized)throw Error('Prepared Project download changed exact serialization');
  report.checks.push({operation:'candidate download preserves exact native serialization before apply',passed:true});
  const rect=await ev('(()=>{const r=$("deformation-panel").getBoundingClientRect();return {x:r.x+scrollX,y:r.y+scrollY,width:r.width,height:r.height,scale:1}})()');
  const shot=await call('Page.captureScreenshot',{captureBeyondViewport:true,clip:rect},sessionId);await writeFile(out+'/deformation-preview.png',Buffer.from(shot.data,'base64'));
  await click('#deformation-apply');
  await check('apply keeps frozen history and activates guarded Undo','!$("deformation-undo").disabled && explicitProjectMesh!==null && curvedHistoryRows().filter(r=>r._splitPattern).length===2 && dirty');
  if(!isDeepStrictEqual((await ev('api("normalize",{document:collect()})')).project,expected))throw Error('Applied Project differs from candidate');
  await click('#deformation-undo');
  if(!isDeepStrictEqual(await ev('collect()'),original))throw Error('Undo failed to restore exact editor source');
  report.checks.push({operation:'Undo restores source geometry, source mesh, complete history and RF controls',passed:true});
  await startPreview();await click('#deformation-apply');await fill('#beta',.9);
  await check('later RF edits invalidate Undo without overwriting the edit','$("deformation-undo").disabled && !deformationUndo && $("beta").value==="0.9"');
  await prepare();await startPreview();await click('#deformation-apply');await click('#save');
  let saved;
  for(let n=0;n<200;n++){try{saved=JSON.parse(await readFile(out+'/downloads/cavity-project.json','utf8'));break;}catch{}await sleep(100);}
  if(!isDeepStrictEqual(saved,expected))throw Error('Normal Project save differs from candidate');
  await open(out+'/downloads/cavity-project.json');
  if(!isDeepStrictEqual((await ev('api("normalize",{document:collect()})')).project,expected))throw Error('Reload changes candidate');
  await check('normal Project save/reload retains exact case and numbered mesh and clears old Undo','$("deformation-undo").disabled && !deformationUndo');
  await ev('window.__baseApi=api;window.__job=null;api=async(...args)=>{const r=await __baseApi(...args);if(args[0]==="start")window.__job=r.id;return r}');
  await click('#run');await wait('!!window.__job');const job=await ev('__job'),selector=`#jobs .job[data-job="${job}"]`;
  await wait(`document.querySelector(${JSON.stringify(selector+' strong')})?.textContent.startsWith("計算完了")`,240000);
  await click(selector+' button');await wait('currentJob===window.__job && $("field-image").naturalWidth>0',240000);
  const result=await ev('currentResult');await writeFile(out+'/result.json',JSON.stringify(result,null,2));
  const native=JSON.parse(await readFile(args['--native-result'],'utf8'));
  if(!isDeepStrictEqual(result.result.case,expected.case))throw Error('Native solve changed saved Case');
  for(let i=0;i<native.modes.length;i++)for(const k of ['frequency_hz','r_over_q_accelerator_ohm','r_over_q_circuit_ohm','geometry_factor_ohm','transit_time_factor_abs'])
    if(Math.abs(result.result.modes[i][k]/native.modes[i][k]-1)>1e-12)throw Error('CLI/GUI native RF differs: '+k);
  report.checks.push({operation:'actual GUI worker and native field display equal CLI Case and separate frequency/RF quantities',passed:true});
  await ev('api=__baseApi');
  for(const [field,value] of [['beta',.9],['deformation-angle',2],['deformation-geometry',geometryText+'\n']]) {
    await prepare();await ev('window.__release=null;api=async(...args)=>{const r=await __baseApi(...args);if(args[0]==="preview-curved-deformation")await new Promise(resolve=>window.__release=resolve);return r}');
    await click('#deformation-preview');await wait('!!window.__release',120000);
    await fill('#'+field,value);await ev('__release()');await wait('!$("deformation-preview").disabled');
    await check(`in-flight ${field} change refuses stale candidate`,'!deformationResult && $("deformation-apply").disabled && $("deformation-view").hidden && $("error").textContent.includes("入力が変わりました")');
    await ev('api=__baseApi');
  }
  await prepare();await startPreview();await fill('#deformation-angle',2);
  await check('editing a prepared request removes candidate, overlay and download','!deformationResult && $("deformation-save").disabled && $("deformation-apply").disabled && $("deformation-view").hidden');
  await fill('#deformation-angle',1);await startPreview();
  await ev('$("beta").value="0.9"');await click('#deformation-apply');
  await check('apply checks current values even without an input event','!deformationResult && $("error").textContent.includes("入力が変わりました") && $("beta").value==="0.9"');
  await prepare();await startPreview();await click('#deformation-apply');await ev('$("beta").value="0.9"');await click('#deformation-undo');
  await check('Undo checks current values even without an input event','!deformationUndo && $("error").textContent.includes("Projectが変わりました") && $("beta").value==="0.9"');
  await prepare();await ev('window.__release=null;api=async(...args)=>{const r=await __baseApi(...args);if(args[0]==="normalize")await new Promise(resolve=>window.__release=resolve);return r}');
  await click('#deformation-template');await wait('!!window.__release');await fill('#beta',.9);await ev('__release()');await wait('!$("deformation-template").disabled');
  await check('template generation also rejects a stale source','$("error").textContent.includes("入力が変わりました") && $("beta").value==="0.9"');await ev('api=__baseApi');
  await prepare();const unfrozen=structuredClone(original);for(const step of unfrozen.case.mesh.curved_refinement_steps)delete step.split_pattern;
  await writeFile(out+'/unfrozen.json',JSON.stringify(unfrozen));await open(out+'/unfrozen.json');await startPreview();
  await check('unfrozen history is refused with an actionable freeze instruction','$("error").textContent.includes("freeze-curved-refinement") && $("deformation-apply").disabled');
  await prepare();await startPreview();await open(out+'/downloads/deformed-project.json');
  await check('replacing Project clears any earlier prepared candidate','!deformationResult && !deformationUndo && $("deformation-apply").disabled && $("deformation-view").hidden');
  await prepare();await startPreview();
  await check('SI editor uses available panel width','$("deformation-geometry").getBoundingClientRect().width>.9*$("deformation-panel").getBoundingClientRect().width');
  }
  report.source_changed_during_run=!isDeepStrictEqual(report.source_sha256,await sourceHashes());
  report.passed=!report.source_changed_during_run && report.external_requests.length===0;
  if(!report.passed)throw Error('Source changed or external HTTP occurred');console.log(JSON.stringify({passed:report.passed,checks:report.checks}));
} catch(e){report.error=String(e);process.exitCode=1;console.error(e);}
finally{await writeFile(out+'/report.json',JSON.stringify(report,null,2));ws?.close();browser.kill();}
