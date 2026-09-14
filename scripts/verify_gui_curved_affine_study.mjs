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
if (!args['--url'] || !args['--out'] || !args['--study']) throw Error('Require --url --out --study');
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
  scope: args['--layout-only'] ? 'definition roundtrip and layout only; no new Study worker' : 'definition, real Study worker, tracking and stale response checks',
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




  const expected=JSON.parse(await readFile(args['--study'],'utf8'));
  await writeFile(out+'/source-project.json',JSON.stringify(expected.project));
  const loadFile=async(selector,path)=>{const {root}=await call('DOM.getDocument',{},sessionId);const {nodeId}=await call('DOM.querySelector',{nodeId:root.nodeId,selector},sessionId);await call('DOM.setFileInputFiles',{nodeId,files:[resolve(path)]},sessionId);};
  const select=async(id,value)=>ev(`(()=>{const e=$(${JSON.stringify(id)});e.value=${JSON.stringify(value)};e.dispatchEvent(new Event('change',{bubbles:true}))})()`);
  await loadFile('#open',out+'/source-project.json');
  const expectedHistory=expected.project.case.mesh.curved_refinement_steps || [];
  const splitCount=expectedHistory.filter(s=>s.split_pattern).length;
  await wait(`curvedHistoryRows().filter(r=>r._splitPattern).length===${splitCount} && (collect().case.model?.polarization ?? "tm")===${JSON.stringify(expected.project.case.model.polarization)}`);
  await select('study-kind','curved_affine_sweep');await wait('!$("study-affine").hidden && $("study-parameter").options.length===1');
  await fill('#study-affine-parameter',expected.parameter);await select('study-affine-unit',expected.parameter_unit);
  await select('study-affine-rf',expected.rf_coordinates);await fill('#study-affine-coefficients',JSON.stringify(expected.affine_coefficients));
  await fill('#study-values',expected.values.join(', '));
  await click('#save-study');
  let saved;for(let n=0;n<150;n++){try{saved=JSON.parse(await readFile(out+'/downloads/study.json','utf8'));break;}catch{}await sleep(100);}
  if(!saved || !isDeepStrictEqual(saved,expected))throw Error('Saved GUI affine Study differs from native declaration');
  report.checks.push({operation:'GUI creates the exact native affine Study, frozen mesh and ordered history',passed:true});
  await fill('#study-affine-parameter','changed');await fill('#study-values','7, 8');await select('study-affine-unit','m');
  await loadFile('#open-study',out+'/downloads/study.json');
  await wait(`$("study-affine-parameter").value===${JSON.stringify(expected.parameter)} && $("study-values").value==="1, 2" && $("study-affine-unit").value==="1"`);
  if(!isDeepStrictEqual(await ev('studyDefinition()'),expected))throw Error('Reload lost affine settings or frozen history');
  report.checks.push({operation:'definition reload restores laws, units, RF coordinates and all frozen choices',passed:true});
  if(!args['--layout-only']) {
  await fill('#study-affine-coefficients','{"radial_scale":[1],"axial_scale":[1],"axial_shear":[0]}');
  await click('#save-study');await wait('!$("error").hidden && $("error").textContent.includes("nonconstant")');
  report.checks.push({operation:'invalid constant shape law is rejected before download',passed:true});
  await fill('#study-affine-coefficients',JSON.stringify(expected.affine_coefficients));
  await ev('window.__baseApi=api;window.__studyJob=null;api=async(...args)=>{const result=await __baseApi(...args);if(args[0]==="start-study")window.__studyJob=result.id;return result}');
  await click('#start-study');await wait('!!window.__studyJob');
  const job=await ev('__studyJob'),jobSelector=`#jobs .job[data-job="${job}"]`;
  await wait(`document.querySelector(${JSON.stringify(jobSelector+' strong')})?.textContent.startsWith("計算完了")`,180000);
  await click(jobSelector+' button');await wait('activeStudy?.study.kind==="curved_affine_sweep"',180000);
  await check('independent spectra display does not claim fixed-domain convergence','activeStudy.comparisons.length===0 && activeStudy.numerical_status==="UNVERIFIED" && $("study-report").textContent.includes("独立したスペクトル")');
  const native=await ev('activeStudy');await writeFile(out+'/study-result.json',JSON.stringify(native,null,2));
  if(!isDeepStrictEqual(native.study,expected) || native.points.length!==2)throw Error('Worker result changed the affine declaration');
  const a=native.points[0].modes[0],b=native.points[1].modes[0];
  if(Math.abs(2*b.frequency_hz/a.frequency_hz-1)>1e-10)throw Error('GUI FEM violates Maxwell frequency scaling');
  if(expected.project.case.model?.polarization==='te') {
    if([a,b].some(m=>m.r_over_q_accelerator_ohm!==null || m.r_over_q_circuit_ohm!==null) || Math.abs(b.geometry_factor_ohm/a.geometry_factor_ohm-1)>1e-9)throw Error('TE GUI Study loses N/A or geometry-factor scaling');
    report.checks.push({operation:'TE Study preserves independent spectra, Maxwell frequency/G scaling and accelerating quantities N/A',passed:true});
  } else {
    if(!Number.isFinite(b.r_over_q_accelerator_ohm/a.r_over_q_accelerator_ohm) || Math.abs(b.r_over_q_accelerator_ohm/a.r_over_q_accelerator_ohm-1)>1e-9)throw Error('TM GUI Study violates R/Q scaling');
    report.checks.push({operation:'actual GUI Study worker preserves the declaration and Maxwell frequency/RQ scaling',passed:true});
  }
  await ev('$("tracking-study-panel").open=true;$("tracking-study").value=__studyJob');
  await fill('#tracking-study-ids','["A"]');await fill('#tracking-study-controls','');await fill('#tracking-order',5);await fill('#tracking-overlap',.8);
  await click('#tracking-study-run');await wait('trackingResult?.document.document_type==="study_mode_tracking" && !trackingBusy',180000);
  await check('completed Study tracking derives the relative map and preserves independent spectra','trackingResult.document.status==="PASS" && trackingResult.document.history.steps[0].request.controls.affine_map.radial_scale===2 && !Object.hasOwn(trackingResult.document.request.step_controls[0],"affine_map") && activeStudy.mode_tracking==="not performed; independent spectra"');
  if(expected.project.case.model?.polarization==='te') await check('completed TE Study tracking uses the electric field',`trackingResult.document.history.steps[0].tracking.physical_mapping.field==='Ephi_V_per_m'`);
  await click('#tracking-save');let tracking;
  for(let n=0;n<150;n++){try{tracking=JSON.parse(await readFile(out+'/downloads/study-mode-tracking.json','utf8'));break;}catch{}await sleep(100);}
  if(!tracking || !isDeepStrictEqual(tracking,await ev('trackingResult.document')))throw Error('Tracking download differs');
  await click('#tracking-reset');await loadFile('#tracking-open',out+'/downloads/study-mode-tracking.json');
  await wait('trackingResult?.document.document_type==="study_mode_tracking" && !trackingBusy',180000);
  report.checks.push({operation:'tracking download and complete saved replay retain the derived map',passed:true});
  await fill('#tracking-study-controls','');await click('#tracked-execution-prepare');
  await wait('$("tracked-execution-request").value.trim().startsWith("{")',60000);
  await check('sequential/adaptive request preparation retains affine laws and derives controls','(()=>{const r=JSON.parse($("tracked-execution-request").value);return r.study.study_version===2 && r.study.kind==="curved_affine_sweep" && r.step_controls.every(c=>c.mapping==="affine_remesh" && !Object.hasOwn(c,"affine_map"))})()');
  await ev('window.__release=null;api=async(...args)=>{const r=await __baseApi(...args);if(args[0]==="normalize-study")await new Promise(resolve=>window.__release=resolve);return r}');
  await click('#save-study');await wait('!!window.__release');await fill('#study-values','1, 1.5');await ev('__release()');
  await wait('!$("error").hidden && $("error").textContent.includes("入力が変わりました")');
  report.checks.push({operation:'in-flight validation refuses a stale shape Study definition',passed:true});
  await ev('api=__baseApi');await fill('#study-values','1, 2');
  await select('study-kind','fixed_geometry_convergence');await wait(`$("study-parameter").value===${JSON.stringify(expectedHistory.length ? 'additional_uniform_refinements' : '/case/mesh/curved_refinement_levels')}`);
  await check('switching to existing fixed-domain Study omits affine-only fields',`(async()=>{const r=await studyDefinition();return r.study_version===1 && r.kind==="fixed_geometry_convergence" && !Object.hasOwn(r,"affine_coefficients") && (r.project.case.mesh.curved_refinement_steps || []).length===${expectedHistory.length}})()`);
  }
  await loadFile('#open-study',out+'/downloads/study.json');await wait('!$("study-affine").hidden && $("study-values").value==="1, 2"');
  await check('multiline affine laws occupy the available form width','$("study-affine-coefficients").getBoundingClientRect().width > .9*$("study-affine").getBoundingClientRect().width');
  const rect=await ev('(()=>{const r=$("studies").getBoundingClientRect();return {x:r.x+scrollX,y:r.y+scrollY,width:r.width,height:r.height,scale:1}})()');
  const shot=await call('Page.captureScreenshot',{captureBeyondViewport:true,clip:rect},sessionId);await writeFile(out+'/affine-study.png',Buffer.from(shot.data,'base64'));
  report.source_changed_during_run=!isDeepStrictEqual(report.source_sha256,await sourceHashes());
  report.passed=!report.source_changed_during_run && report.external_requests.length===0 && report.checks.every(c=>c.passed);
  if(!report.passed)throw Error('Affine Study browser checks failed');console.log(JSON.stringify({passed:report.passed,checks:report.checks}));
} catch(e){report.error=String(e);process.exitCode=1;console.error(e);}
finally{await writeFile(out+'/report.json',JSON.stringify(report,null,2));ws?.close();browser.kill();}
