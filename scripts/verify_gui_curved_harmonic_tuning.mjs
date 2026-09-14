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
    "Usage: node scripts/verify_gui_curved_harmonic_tuning.mjs --url LAUNCH_URL --out NEW_DIRECTORY --request REQUEST_JSON",
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
  const wait = async (expression, ms = 60000) => {
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
  const request=JSON.parse(await readFile(args['--request'],'utf8')),harmonic=request.schema_version===5;
  report.scope='form generation and strict input, real worker pause/resume, exact download/replay and final native field';
  const set=async(id,value)=>ev(`(()=>{const e=document.querySelector('#'+${JSON.stringify(id)});e.value=${JSON.stringify(String(value))};e.dispatchEvent(new Event('change'))})()`);
  const loadFile=async filename=>{const {root}=await call('DOM.getDocument',{},sessionId);const {nodeId}=await call('DOM.querySelector',{nodeId:root.nodeId,selector:'#tune-open'},sessionId);await call('DOM.setFileInputFiles',{nodeId,files:[resolve(filename)]},sessionId);};
  await ev(`applyProject(${JSON.stringify(request.project)})`);
  if(harmonic) {
    await ev(`document.querySelector('#tune-coupled').checked=true`);await set('tune-binding-law','harmonic');
    await click('#tune-harmonic-template');await wait(`document.querySelector('#tune-geometry-coefficients').value.includes('/curves/')`);
    await check('template exposes numeric leaves and units',`Object.keys(JSON.parse(document.querySelector('#tune-geometry-coefficients').value)).length>6 && !document.querySelector('#tune-harmonic-settings').hidden && document.querySelector('#tune-profile-bindings').hidden`);
    await fill('#tune-geometry-coefficients',JSON.stringify(request.geometry_coefficients));
    await fill('#tune-parameter-name',request.parameter);await set('tune-parameter-unit',request.parameter_unit);
    await set('tune-harmonic-rf',request.rf_coordinates);await fill('#tune-harmonic-angle',request.minimum_corner_angle_deg);
    for(const [id,key] of [['target','target_hz'],['frequency-tolerance','frequency_tolerance_hz'],['parameter-tolerance','parameter_tolerance'],['max-trials','max_trials'],['refinement','refinement_scale'],['mesh-tolerance','mesh_frequency_tolerance_hz']])await fill('#tune-'+id,request[key]/(key==='target_hz'?1e6:1));
    await fill('#tune-low',request.bounds[0]);await fill('#tune-high',request.bounds[1]);await fill('#tune-ids',JSON.stringify(request.initial_ids));await fill('#tune-mode-id',request.mode_id);
    for(const [id,key] of [['order','sample_order'],['overlap','minimum_overlap'],['margin','minimum_assignment_margin'],['gap','relative_cluster_gap'],['rank','minimum_relative_singular_value']])await fill('#tracking-'+id,request.controls[key]);
    await click('#tune-prepare');await wait(`document.querySelector('#tune-request').value.includes('geometry_coefficients')`);
    const built=await ev(`JSON.parse(document.querySelector('#tune-request').value)`);
    if(!isDeepStrictEqual(built,request)) {await writeFile(out+'/generated.json',JSON.stringify(built,null,2));throw Error('generated request differs from original');}
    report.checks.push({operation:'form preserves original project, frozen history, units, laws and derived controls',passed:true});
    await fill('#tune-geometry-coefficients','{"/curves/1/semiaxes_m/1":[0.08,0.01],"/curves/1/semiaxes_m/1":[0.08,0.02]}');
    await click('#tune-prepare');await wait(`document.querySelector('#tune-request').value.includes('0.02')`);
    const oldJob=await ev(`document.querySelector('#tune-job').textContent`);await click('#tune-start');await wait(`!tuningBusy && !document.querySelector('#error').hidden`);
    await check('duplicate curve laws fail before launching a worker',`document.querySelector('#error').textContent.includes('duplicate') && document.querySelector('#tune-job').textContent===${JSON.stringify(oldJob)}`);
    await fill('#tune-geometry-coefficients',JSON.stringify(request.geometry_coefficients));await click('#tune-prepare');
    await wait(`JSON.stringify(JSON.parse(document.querySelector('#tune-request').value).geometry_coefficients)===JSON.stringify(${JSON.stringify(request.geometry_coefficients)})`);
    await ev(`window.tunePreviewOriginal=preview;preview=async()=>{const p=await window.tunePreviewOriginal();await new Promise(r=>setTimeout(r,500));return p};window.beforeTunePreparation=document.querySelector('#tune-request').value`);
    await click('#tune-prepare');await fill('#tune-parameter-name','changed_during_preview');await wait(`!document.querySelector('#error').hidden && document.querySelector('#error').textContent.includes('入力が変わりました')`);
    await check('changed input cannot publish a stale prepared request',`document.querySelector('#tune-request').value===window.beforeTunePreparation`);
    await ev('preview=window.tunePreviewOriginal');
    const clip=await ev(`(()=>{const r=document.querySelector('#tune-binding-settings').getBoundingClientRect();return {x:r.x+scrollX,y:r.y+scrollY,width:r.width,height:r.height,scale:1}})()`);
    const shot=await call('Page.captureScreenshot',{captureBeyondViewport:true,clip},sessionId);await writeFile(out+'/form.png',Buffer.from(shot.data,'base64'));
  } else {
    await click('#tune-prepare');await wait(`document.querySelector('#tune-request').value.includes('target_hz')`);
    await check('previous scalar form still prepares schema one',`JSON.parse(document.querySelector('#tune-request').value).schema_version===1`);
  }
  await fill('#tune-request',JSON.stringify(request));await fill('#tune-limit','2');
  const launch=async selector=>{const old=await ev(`document.querySelector('#tune-job').textContent`);await click(selector);await wait(`!tuningBusy && document.querySelector('#tune-job').textContent!==${JSON.stringify(old)}`,120000);return ev(`document.querySelector('#tune-job').textContent.match(/開始しました: ([a-zA-Z0-9-]+)/)[1]`);};
  const openJob=async(id,status)=>{await wait(`document.querySelector('[data-job="${id}"] strong')?.textContent.includes('${status}')`,900000);await click(`[data-job="${id}"] button`);await wait(`!tuningBusy && tuningResult?.document.status==='${status}'`,300000);};
  const first=await launch('#tune-start');await openJob(first,'PAUSED');
  await check('real worker publishes two verified trials and enables resume',`tuningResult.document.trials.length===2 && !document.querySelector('#tune-resume').disabled`);
  if(harmonic) await check('checkpoint restores nonlinear laws and RF policy',`document.querySelector('#tune-binding-law').value==='harmonic' && document.querySelector('#tune-harmonic-rf').value===${JSON.stringify(request.rf_coordinates)} && JSON.stringify(JSON.parse(document.querySelector('#tune-geometry-coefficients').value))===JSON.stringify(${JSON.stringify(request.geometry_coefficients)})`);
  await click('#tune-save');let downloaded;
  for(let n=0;n<100;n++){try{downloaded=await readFile(out+'/downloads/tune-checkpoint.json','utf8');break;}catch{}await sleep(100);}
  if(downloaded!==await ev('tuningResult.serialized'))throw Error('download differs from verified text');
  report.checks.push({operation:'download preserves exact server-verified JSON',passed:true});
  await fill('#tune-request','{}');await loadFile(out+'/downloads/tune-checkpoint.json');await wait(`!tuningBusy && JSON.parse(document.querySelector('#tune-request').value).schema_version===${request.schema_version}`,300000);
  await check('saved request replay restores the original version',`tuningResult.document.request.schema_version===${request.schema_version}`);
  const bad=JSON.parse(downloaded);bad.trials[0].value+=.001;await writeFile(out+'/modified.json',JSON.stringify(bad));await loadFile(out+'/modified.json');await wait(`!tuningBusy && !document.querySelector('#error').hidden`,300000);
  await check('forged trial cannot replace verified state',`document.querySelector('#error').textContent.includes('replay') && tuningResult.document.trials[0].value===${request.bounds[0]}`);
  await fill('#tune-request','{}');await fill('#tune-limit','');const last=await launch('#tune-resume');await openJob(last,'TUNED');
  await check('resume uses saved laws and passes a separate final refinement gate',`tuningResult.document.request.schema_version===${request.schema_version} && tuningResult.document.decision.mesh_difference_met && tuningResult.document.decision.refined_target_met && tuningResult.document.trials.at(-1).phase==='refinement'`);
  await writeFile(out+'/final-checkpoint.json',await ev('tuningResult.serialized'));
  const clip=await ev(`(()=>{const a=document.querySelector('#tune-status').getBoundingClientRect(),b=document.querySelector('#tune-trials').getBoundingClientRect();return {x:a.x+scrollX,y:a.y+scrollY,width:a.width,height:b.bottom-a.top,scale:1}})()`);
  const shot=await call('Page.captureScreenshot',{captureBeyondViewport:true,clip},sessionId);await writeFile(out+'/result.png',Buffer.from(shot.data,'base64'));
  const old=await ev('currentJob');await click('#tune-open-field');await wait(`currentJob!==${JSON.stringify(old)} && currentResult && !document.querySelector('#field-image').hidden`,300000);
  await check('final field selects the tracked identity',`Number(document.querySelector('#mode').value)===tuningResult.document.trials.at(-1).current_mode_ids.indexOf(tuningResult.document.request.mode_id)+1`);
  if(harmonic)await check('final field retains frozen source history plus one uniform step',`currentResult.result.case.mesh.curved_refinement_steps.length===${request.project.case.mesh.curved_refinement_steps.length+1} && currentResult.result.case.mesh.curved_refinement_steps.at(-1).kind==='uniform'`);
  report.job_ids={first,last};report.new_fem_solves=await ev('tuningResult.document.trials.length');
  report.source_changed_during_run=!isDeepStrictEqual(report.source_sha256,await sourceHashes());report.passed=!report.source_changed_during_run && report.external_requests.length===0 && report.checks.every(c=>c.passed);
  if(!report.passed)throw Error('GUI checks failed');console.log(JSON.stringify({passed:report.passed,checks:report.checks,external_requests:report.external_requests}));
} catch(e){report.error=String(e);process.exitCode=1;console.error(e);}
finally{await writeFile(out+'/report.json',JSON.stringify(report,null,2));ws?.close();browser.kill();}
