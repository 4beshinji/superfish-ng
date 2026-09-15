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
  scope: 'harmonic shape Study definition/strict laws, real worker, derived tracking/replay, request preparation and stale response checks',
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




  const expected=JSON.parse(await readFile(args['--study'],'utf8')),remesh=expected.kind==='curved_remesh_sweep';
  if(remesh && !args['--remesh-plan'])throw Error('Study v4 requires --remesh-plan for plan-import checks');
  report.study_kind=expected.kind;
  await writeFile(out+'/source-project.json',JSON.stringify(expected.project));
  const loadFile=async(selector,path)=>{const {root}=await call('DOM.getDocument',{},sessionId);const {nodeId}=await call('DOM.querySelector',{nodeId:root.nodeId,selector},sessionId);await call('DOM.setFileInputFiles',{nodeId,files:[resolve(path)]},sessionId);};
  const select=async(id,value)=>ev(`(()=>{const e=$(${JSON.stringify(id)});e.value=${JSON.stringify(value)};e.dispatchEvent(new Event('change',{bubbles:true}))})()`);
  await ev('window.__importedProject=null;window.__importApplyProject=applyProject;applyProject=p=>{const result=__importApplyProject(p);window.__importedProject=p;return result}');
  await loadFile('#open',out+'/source-project.json');await wait('!!window.__importedProject');await ev('applyProject=__importApplyProject');
  await select('study-kind',expected.kind);await wait('!$("study-harmonic").hidden && $("study-parameter").options.length===1');
  const templatePath=Object.keys(expected.geometry_coefficients)[0];
  const templateValue=templatePath.split('/').slice(1).reduce((value,key)=>value[key],expected.project.case.geometry);
  await click('#study-harmonic-template');await wait(`$("study-harmonic-coefficients").value.includes(${JSON.stringify(templatePath)})`);
  await check('template uses current curve values and continuous numeric fields',`(()=>{const d=JSON.parse($("study-harmonic-coefficients").value);return d[${JSON.stringify(templatePath)}][0]===${templateValue} && Object.values(d).every(c=>c.length===1) && !Object.keys(d).some(k=>k.endsWith("/branch"))})()`);
  await click('#save-study');await wait('!$("error").hidden && $("error").textContent.includes("nonconstant")');
  report.checks.push({operation:'constant template requires a varying term before a Study can be saved',passed:true});
  await fill('#study-harmonic-parameter',expected.parameter);await select('study-harmonic-unit',expected.parameter_unit);
  await select('study-harmonic-rf',expected.rf_coordinates);await fill('#study-harmonic-angle',expected.minimum_corner_angle_deg);
  await fill('#study-harmonic-coefficients',JSON.stringify(expected.geometry_coefficients));await fill('#study-values',expected.values.join(', '));
  if(remesh) {
    await fill('#study-remesh-cutover',expected.mesh_schedule.breakpoints[0]);
    await loadFile('#study-remesh-import',args['--remesh-plan']);
    await wait('$("study-remesh-schedule").value.includes("source_mesh")');
    if(!isDeepStrictEqual(await ev('JSON.parse($("study-remesh-schedule").value)'),expected.mesh_schedule))throw Error('Plan import changed explicit schedule');
    report.checks.push({operation:'plan import declares right-hand cutover and complete new mesh/history',passed:true});
  }
  if(args['--generation-settings']) {
    const settings=JSON.parse(await readFile(args['--generation-settings'],'utf8'));
    await ev('$("study-remesh-generation-settings").closest("details").open=true');
    await fill('#study-remesh-generation-settings',JSON.stringify(settings));await fill('#study-remesh-schedule','');
    await click('#study-remesh-generate');await wait('$("study-remesh-schedule").value.includes("source_mesh")',60000);
    if(!isDeepStrictEqual(await ev('JSON.parse($("study-remesh-schedule").value)'),expected.mesh_schedule))throw Error('GUI generation differs from CLI complete plan');
    if(!isDeepStrictEqual(await ev('preview()'),expected.project))throw Error('Generation changed source Project');
    report.checks.push({operation:'automatic generation exactly matches the CLI plan and preserves source Project',passed:true});
    const retained=await ev('$("study-remesh-schedule").value');
    const duplicate=JSON.stringify(settings).replace('"schema_version":1','"schema_version":1,"schema_version":1');
    await fill('#study-remesh-generation-settings',duplicate);await click('#study-remesh-generate');
    await wait('!$("error").hidden && $("error").textContent.includes("duplicate JSON key")');
    if(await ev('$("study-remesh-schedule").value')!==retained)throw Error('Rejected generation lost current schedule');
    report.checks.push({operation:'duplicate generation settings are rejected without replacing the plan',passed:true});
    await fill('#study-remesh-generation-settings',JSON.stringify({...settings,max_chord_edge_m:.001}));await click('#study-remesh-generate');
    await wait('!$("error").hidden && $("error").textContent.includes("fixed quadratic boundary")');
    if(await ev('$("study-remesh-schedule").value')!==retained)throw Error('Infeasible generation lost current schedule');
    report.checks.push({operation:'incompatible size is rejected and preserves current schedule',passed:true});
    await fill('#study-remesh-generation-settings',JSON.stringify(settings));
    await ev('window.__generationApi=api;window.__releaseGeneration=null;api=async(...args)=>{const r=await __generationApi(...args);if(args[0]==="generate-curved-remesh-plan")await new Promise(done=>window.__releaseGeneration=done);return r}');
    await click('#study-remesh-generate');await wait('!!window.__releaseGeneration');
    await fill('#study-remesh-generation-settings',JSON.stringify({...settings,max_rounds:21}));await ev('__releaseGeneration()');
    await wait('!$("error").hidden && $("error").textContent.includes("メッシュ生成中に入力が変わりました")');
    if(await ev('$("study-remesh-schedule").value')!==retained)throw Error('Stale generation changed schedule');
    report.checks.push({operation:'changed generation settings reject an in-flight completed plan',passed:true});
    await ev('api=__generationApi');await fill('#study-remesh-generation-settings',JSON.stringify(settings));
  }
  await click('#save-study');let saved;
  for(let n=0;n<300;n++){try{saved=JSON.parse(await readFile(out+'/downloads/study.json','utf8'));break;}catch{}await sleep(100);}
  if(!isDeepStrictEqual(saved,expected))throw Error('GUI harmonic Study differs from native declaration');
  report.checks.push({operation:`GUI creates the exact version-${expected.study_version} declaration and preserves frozen source mesh`,passed:true});
  await fill('#study-harmonic-parameter','changed');await fill('#study-values','7, 8');await select('study-harmonic-unit','m');await fill('#study-harmonic-angle',5);
  await loadFile('#open-study',out+'/downloads/study.json');
  await wait(`$("study-harmonic-parameter").value===${JSON.stringify(expected.parameter)} && $("study-values").value===${JSON.stringify(expected.values.join(', '))} && $("study-harmonic-unit").value===${JSON.stringify(expected.parameter_unit)}`);
  if(!isDeepStrictEqual(await ev('studyDefinition()'),expected))throw Error('Reload changed harmonic laws or controls');
  report.checks.push({operation:'definition reload restores laws, units, RF coordinates, quality and history',passed:true});
  await fill('#study-harmonic-coefficients','{"/curves/1/semiaxes_m/1":[.08,.01],"/curves/1/semiaxes_m/1":[.08,.02]}'.replaceAll('[.08,.','[0.08,0.'));
  await click('#save-study');await wait('!$("error").hidden && $("error").textContent.includes("duplicate JSON key")');
  report.checks.push({operation:'duplicate law paths reach the strict reader and are rejected',passed:true});
  await fill('#study-harmonic-coefficients',JSON.stringify(expected.geometry_coefficients));
  if(remesh) {
    const duplicate=JSON.stringify(expected.mesh_schedule).replace('"schema_version":1','"schema_version":1,"schema_version":1');
    await fill('#study-remesh-schedule',duplicate);await click('#save-study');
    await wait('!$("error").hidden && $("error").textContent.includes("duplicate JSON key")');
    report.checks.push({operation:'duplicate mesh schedule keys reach the strict server reader',passed:true});
    await fill('#study-remesh-schedule',JSON.stringify(expected.mesh_schedule));
    await ev('window.__oldFileText=File.prototype.text;window.__importRelease=null;File.prototype.text=async function(){const text=await __oldFileText.call(this);await new Promise(resolve=>window.__importRelease=resolve);return text}');
    await loadFile('#study-remesh-import',args['--remesh-plan']);await wait('!!window.__importRelease');
    await fill('#study-remesh-cutover',.6);await ev('__importRelease()');
    await wait('!$("error").hidden && $("error").textContent.includes("読込中に入力が変わりました")');
    await ev('File.prototype.text=__oldFileText');await fill('#study-remesh-cutover',expected.mesh_schedule.breakpoints[0]);
    if(!isDeepStrictEqual(await ev('JSON.parse($("study-remesh-schedule").value)'),expected.mesh_schedule))throw Error('Stale import changed schedule');
    report.checks.push({operation:'stale file import preserves the current schedule',passed:true});
  }
  await ev('window.__baseApi=api;window.__studyJob=null;api=async(...args)=>{const r=await __baseApi(...args);if(args[0]==="start-study")window.__studyJob=r.id;return r}');
  await click('#start-study');await wait('!!window.__studyJob');const job=await ev('__studyJob'),selector=`#jobs .job[data-job="${job}"]`;
  await wait(`document.querySelector(${JSON.stringify(selector+' strong')})?.textContent.startsWith("計算完了")`,240000);
  await click(selector+' button');await wait(`activeStudy?.study.kind===${JSON.stringify(expected.kind)}`,240000);
  await check('actual worker displays independent spectra without a convergence claim',`activeStudy.points.length===${expected.values.length} && activeStudy.comparisons.length===0 && activeStudy.numerical_status==="UNVERIFIED" && $("study-report").textContent.includes("独立したスペクトル")`);
  const result=await ev('activeStudy');await writeFile(out+'/study-result.json',JSON.stringify(result,null,2));
  if(!isDeepStrictEqual(result.study,expected))throw Error('Actual worker lost shape laws');
  if(args['--native-study']) {
    const reference=JSON.parse(await readFile(args['--native-study'],'utf8'));
    if(!isDeepStrictEqual(result.study,reference.study))throw Error('CLI and GUI input declarations differ');
    for(let i=0;i<expected.values.length;i++)for(const k of ['frequency_hz','r_over_q_accelerator_ohm','r_over_q_circuit_ohm','geometry_factor_ohm','transit_time_factor_abs']){
      const actual=result.points[i].modes[0][k],baseline=reference.points[i].modes[0][k];
      if(actual===null || baseline===null){if(actual!==baseline)throw Error('CLI/GUI applicability differs: '+k);}
      else if(!Number.isFinite(actual) || !Number.isFinite(baseline) || (baseline===0 ? actual!==0 : Math.abs(actual/baseline-1)>1e-12))throw Error('CLI/GUI field quantity differs: '+k);
    }
    report.checks.push({operation:'CLI and GUI native input and frequency/RF quantities agree',passed:true});
  }
  await ev('$("tracking-study-panel").open=true;$("tracking-study").value=__studyJob');
  await fill('#tracking-study-ids','["A"]');await fill('#tracking-study-controls','');await fill('#tracking-order',5);await fill('#tracking-overlap',.8);
  await click('#tracking-study-run');await wait('trackingResult?.document.document_type==="study_mode_tracking" && !trackingBusy',240000);
  const sourceMesh=expected.project.case.mesh;
  await check('completed Study tracking derives actual curved comparison meshes',`(()=>{const d=trackingResult.document,c=d.history.steps[0].request.controls;return d.status==="PASS" && c.mapping==="piecewise_remesh" && c.comparison_meshes.every(m=>m.schema_version===2 && JSON.stringify(m.curved_refinement_steps??[])===JSON.stringify(${JSON.stringify(sourceMesh.curved_refinement_steps??[])}) && (m.curved_refinement_levels??0)===${sourceMesh.curved_refinement_levels??0}) && !Object.hasOwn(d.request.step_controls[0],"comparison_meshes")})()`);
  if(expected.project.case.model?.polarization==='te'){
    const sector=expected.project.case.geometry.edge_tags.some(t=>['electric_symmetry','magnetic_symmetry'].includes(t));
    await check('generated TE Study tracks actual electric fields and retains source sector',`trackingResult.document.history.steps.every(s=>s.tracking.physical_mapping.field==='Ephi_V_per_m' && ${sector ? `s.tracking.physical_mapping.symmetry_sector.reflected===${!!expected.project.reflect_full}` : '!s.tracking.physical_mapping.symmetry_sector'})`);
  }
  await click('#tracking-save');let tracking;
  for(let n=0;n<300;n++){try{tracking=JSON.parse(await readFile(out+'/downloads/study-mode-tracking.json','utf8'));break;}catch{}await sleep(100);}
  if(!isDeepStrictEqual(tracking,await ev('trackingResult.document')))throw Error('Tracking download changed');
  await click('#tracking-reset');await loadFile('#tracking-open',out+'/downloads/study-mode-tracking.json');
  await wait('trackingResult?.document.document_type==="study_mode_tracking" && !trackingBusy',240000);
  report.checks.push({operation:'saved tracking downloads and completely replays original fields and derived meshes',passed:true});
  for(const adaptive of [false,true]) {
    await fill('#tracking-study-controls','');await ev(`$("tracked-execution-adaptive").checked=${adaptive};$("tracked-execution-request").value=""`);
    await click('#tracked-execution-prepare');await wait('$("tracked-execution-request").value.trim().startsWith("{")',60000);
    const request=await ev('JSON.parse($("tracked-execution-request").value)');
    if(!isDeepStrictEqual(request.study,expected) || Boolean(request.adaptive)!==adaptive || request.step_controls.some(c=>c.mapping!=="piecewise_remesh" || Object.hasOwn(c,"comparison_meshes")))throw Error('Prepared tracking request changed declaration');
    report.checks.push({operation:adaptive?'adaptive request preserves geometry laws and derived pair controls':'sequential request preserves geometry laws and derived pair controls',passed:true});
  }
  await ev('window.__release=null;api=async(...args)=>{const r=await __baseApi(...args);if(args[0]==="normalize-study")await new Promise(resolve=>window.__release=resolve);return r}');
  await click('#save-study');await wait('!!window.__release');await fill('#study-harmonic-angle',2);await ev('__release()');
  await wait('!$("error").hidden && $("error").textContent.includes("入力が変わりました")');
  report.checks.push({operation:'in-flight validation rejects a changed quality declaration',passed:true});await ev('api=__baseApi');
  if(remesh) {
    await fill('#study-harmonic-angle',1);
    await ev('window.__release=null;api=async(...args)=>{const r=await __baseApi(...args);if(args[0]==="normalize-study")await new Promise(resolve=>window.__release=resolve);return r}');
    await click('#save-study');await wait('!!window.__release');
    const changed=structuredClone(expected.mesh_schedule);changed.breakpoints=[.6];
    await fill('#study-remesh-schedule',JSON.stringify(changed));await ev('__release()');
    await wait('!$("error").hidden && $("error").textContent.includes("入力が変わりました")');
    report.checks.push({operation:'in-flight normalization rejects a changed mesh schedule',passed:true});await ev('api=__baseApi');
  }
  await select('study-kind','fixed_geometry_convergence');await wait(`$("study-parameter").value===${JSON.stringify(expected.project.case.mesh.curved_refinement_steps?.length ? 'additional_uniform_refinements' : '/case/mesh/curved_refinement_levels')}`);
  await check('old fixed-domain Study omits new shape fields','(async()=>{const d=await studyDefinition();return d.study_version===1 && !Object.hasOwn(d,"geometry_coefficients") && !Object.hasOwn(d,"minimum_corner_angle_deg")})()');
  await loadFile('#open-study',out+'/downloads/study.json');await wait(`!$("study-harmonic").hidden && $("study-harmonic-angle").value===${JSON.stringify(String(expected.minimum_corner_angle_deg))} && $("study-values").value===${JSON.stringify(expected.values.join(', '))}`);
  await check('shape law editor occupies available width','$("study-harmonic-coefficients").getBoundingClientRect().width>.9*$("study-harmonic").getBoundingClientRect().width');
  const rect=await ev('(()=>{const r=$("studies").getBoundingClientRect();return {x:r.x+scrollX,y:r.y+scrollY,width:r.width,height:r.height,scale:1}})()');
  const shot=await call('Page.captureScreenshot',{captureBeyondViewport:true,clip:rect},sessionId);await writeFile(out+'/shape-study.png',Buffer.from(shot.data,'base64'));
  report.source_changed_during_run=!isDeepStrictEqual(report.source_sha256,await sourceHashes());
  report.passed=!report.source_changed_during_run && report.external_requests.length===0;
  if(!report.passed)throw Error('Source changed or external HTTP occurred');console.log(JSON.stringify({passed:report.passed,checks:report.checks}));
} catch(e){report.error=String(e);process.exitCode=1;console.error(e);}
finally{await writeFile(out+'/report.json',JSON.stringify(report,null,2));ws?.close();browser.kill();}
