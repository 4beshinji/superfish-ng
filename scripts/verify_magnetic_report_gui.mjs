// SPDX-License-Identifier: Apache-2.0
// Real local browser input and computation. Requires a running GUI and Chrome.
import { spawn } from "node:child_process";
import { mkdtemp, readFile, writeFile, mkdir, readdir, rename } from "node:fs/promises";
import { resolve } from "node:path";
import { createHash } from "node:crypto";
import { isDeepStrictEqual } from "node:util";
async function sourceHashes(directory = new URL("../src/superfish_ng", import.meta.url).pathname) {
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
if (args["--url-file"]) args["--url"] = (await readFile(args["--url-file"], "utf8")).trim();
if (!args["--url"] || !args["--out"] || !args["--cases"] || !args["--workspace"])
  throw Error(
    "Usage: node scripts/verify_gui_te.mjs --url LAUNCH_URL --out NEW_DIRECTORY",
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
      }, 180000);
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
      try { if (await ev(expression)) return; }
      catch (error) { if (!String(error).includes('ReferenceError')) throw error; }
      await sleep(100);
    }
    throw Error(
      `UI timeout: ${expression}; ${await ev('document.querySelector("#error")?.textContent')}; state=${await ev('JSON.stringify({width:document.querySelector("#width")?.value,unit:document.querySelector("#unit")?.value,project:typeof project!=="undefined"?project:null})')}`,
    );
  };
  const click = async (selector) => {
    const rect = await ev(
      `(async()=>{let e=document.querySelector(${JSON.stringify(selector)});e.scrollIntoView({block:'center',behavior:'instant'});await new Promise(done=>requestAnimationFrame(()=>requestAnimationFrame(done)));e=document.querySelector(${JSON.stringify(selector)});const r=e.getBoundingClientRect(),x=r.x+r.width/2,y=r.y+r.height/2;if(!e.contains(document.elementFromPoint(x,y)))throw Error('click target is obscured: '+JSON.stringify({target:e.outerHTML,rect:r.toJSON(),cover:document.elementFromPoint(x,y)?.tagName}));return {x,y}})()`,
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



  const launch = new URL(args['--url']); launch.pathname = '/magnetic.html';
  await call('Page.navigate', {url:launch.href}, sessionId);
  await wait('typeof selected!=="undefined" && document.querySelector("#source-path")');
  const cases = JSON.parse(await readFile(args['--cases'], 'utf8'));
  const restored = args['--restore'] ? JSON.parse(await readFile(args['--restore'], 'utf8')) : null;
  const check = async (operation, expression) => { if (!await ev(expression)) throw Error(operation); report.checks.push({operation, passed:true}); };
  const rows = async selector => await ev(`Array.from(document.querySelectorAll(${JSON.stringify(selector)}+' tr')).slice(1).map(row=>Array.from(row.querySelectorAll('td')).map(cell=>cell.textContent))`);
  const download = async name => { for(let i=0;i<600;i++){try{return await readFile(out+'/downloads/'+name);}catch{}await sleep(100);}throw Error('missing download '+name); };
  const ready = async () => await wait('typeof selected!=="undefined" && selected!==null && rendered===selected && !document.querySelector("#report-view").hidden',300000);
  const importCase = async value => {const old=await ev('selected');await fill('#source-path',value.source);await fill('#report-path',value.report);await click('#import');await wait(`selected!==${JSON.stringify(old)}`,30000);await ready();return await ev('selected');};
  report.records = [];
  for (const [index, value] of cases.entries()) {
    const expected = JSON.parse(await readFile(value.report, 'utf8'));
    let job;
    if (restored) {job=restored.records[index].id;const url=new URL(launch);url.searchParams.set('job',job);await call('Page.navigate',{url:url.href},sessionId);await ready();}
    else job=await importCase(value);
    if ('extraction' in expected) {
      const e=expected.extraction, series=e.series;
      const actual=await rows('#coefficients');
      const wanted=series.normal_t.map((n,i)=>[String(i+1),String(n),String(series.skew_t[i])]);
      if(!isDeepStrictEqual(actual,wanted))throw Error('displayed multipole coefficients differ: '+value.name);
      const frame=await ev('document.querySelector("#frame").textContent');
      for(const item of [JSON.stringify(series.frame.center_xy_m),String(series.frame.reference_radius_m),String(series.frame.rotation_rad)])if(!frame.includes(item))throw Error('missing explicit multipole frame '+item);
      const traces=await rows('#traces');
      const expectedTraces=e.traces.map(t=>[t.sample_count,t.radius_m,t.field_rms_t,t.truncated_field_rms_error_t,t.truncated_field_relative_error,t.negative_harmonic_rms_t,t.discarded_positive_harmonic_rms_t].map(String));
      if(!isDeepStrictEqual(traces,expectedTraces))throw Error('four original trace diagnostics differ');
    } else {
      const f=expected.force, axial='force_z_n' in f, actual=await rows('#quantities');
      const wanted=axial?[['軸方向力 Fz',String(f.force_z_n),'N']]:[['力 Fx',String(f.force_xy_n_per_m[0]),'N/m'],['力 Fy',String(f.force_xy_n_per_m[1]),'N/m'],['重み付き応力トルク τz',String(f.torque_z_nm_per_m),'N m/m'],['節点回転の応力トルク τz',String(f.nodal_rotation_stress_torque_z_nm_per_m),'N m/m']];
      if(!isDeepStrictEqual(actual,wanted))throw Error('displayed force/torque values or units differ: '+value.name);
      const status=expected.virtual_work===null?'not_performed':expected.status==='virtual_work_failed'?'failed':'complete';
      if(await ev('document.querySelector("#work-status").dataset.status')!==status)throw Error('null/failure/work status confused');
      const actualWork=await rows('#work-comparison');
      const show=v=>v===null?'未計算':String(v);
      const expectedWork=(expected.stress_virtual_work_comparison||[]).map(row=>axial?['z',row.step_m,'m',row.stress_force_z_n,row.virtual_force_z_n,row.difference_n,'N'].map(show):[row.kind==='rotation'?'節点回転':row.kind,row.step,row.kind==='rotation'?'rad':'m',row.stress_value,row.virtual_work_value,row.difference,row.unit].map(show));
      if(!isDeepStrictEqual(actualWork,expectedWork))throw Error('displayed work differences or nulls differ');
      if(expected.virtual_work!==null && !isDeepStrictEqual(JSON.parse(await ev('document.querySelector("#work-json").textContent')),expected.virtual_work))throw Error('full work Cases, potential or iteration history lost');
    }
    if(await ev('document.querySelector("#convention").textContent')!==(expected.extraction?.series.convention||expected.force.conventions))throw Error('convention changed');
    const nativeCase=JSON.parse(await readFile(value.source+'/case.json','utf8'));
    if(!isDeepStrictEqual(JSON.parse(await ev('document.querySelector("#source-case").textContent')),nativeCase))throw Error('source Case or material provenance lost');
    const files=['report.json','request.json',...Object.keys(expected.source_native_sha256).map(n=>'source/'+n)];
    for(const file of files){
      await click(`#downloads button[data-file="${file}"]`);const name=file.replaceAll('/','-'),bytes=await download(name);
      const owned=await readFile(resolve(args['--workspace'],job,file));if(!bytes.equals(owned))throw Error('download differs from owned file '+file);
      if(file==='report.json' && !bytes.equals(await readFile(value.report)))throw Error('report bytes changed');
      if(file.startsWith('source/') && !bytes.equals(await readFile(value.source+'/'+file.slice(7))))throw Error('source bytes changed');
      await rename(out+'/downloads/'+name,out+'/downloads/'+index+'-'+name);
    }
    if([0,6,13,14,16].includes(index)){await ev('window.scrollTo(0,0)');const shot=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true},sessionId);await writeFile(out+'/case-'+index+'.png',Buffer.from(shot.data,'base64'));}
    report.records.push({name:value.name,id:job,displayed_numbers_and_units_identical:true,full_source_and_work_preserved:true,downloads:7});
    report.checks.push({operation:(restored?'restart and reverify ':'import, reverify and display ')+value.name,passed:true});
    console.log('DONE',index,value.name);
  }
  await check('HTTP rejects missing session token',`(async()=>{const r=await fetch('/api',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'magnetic-report-jobs'})});return r.status===403})()`);
  await check('HTTP strict action rejects an extra field',`(async()=>{const r=await fetch('/api',{method:'POST',headers:{'Content-Type':'application/json','X-NG-Token':token},body:JSON.stringify({action:'magnetic-report-jobs',extra:1})});return r.status===400})()`);
  if(!restored){
    const extra=await importCase(cases[6]);report.changed_owned_job=extra;
    const changed=resolve(args['--workspace'],extra,'report.json');await writeFile(changed,Buffer.concat([await readFile(changed),Buffer.from('\n')]));
    await wait('!document.querySelector("#error").hidden && document.querySelector("#report-view").hidden',15000);
    report.checks.push({operation:'changed owned report removes displayed quantities before download',passed:true});
    const invalid=JSON.parse(await readFile(cases[6].report,'utf8'));invalid.force.force_xy_n_per_m[0]+=1;
    await writeFile(out+'/invalid-report.json',JSON.stringify(invalid));await fill('#source-path',cases[6].source);await fill('#report-path',out+'/invalid-report.json');const old=await ev('selected');await click('#import');
    await wait(`selected!==${JSON.stringify(old)} && !document.querySelector('#error').hidden && document.querySelector('#report-view').hidden`,90000);report.invalid_job=await ev('selected');
    report.checks.push({operation:'actual worker rejects numerically modified imported report',passed:true});
  }
  await call('Page.navigate',{url:launch.origin+'/'},sessionId);await wait('typeof currentJob!=="undefined" && document.querySelector("#run")');
  const magneticJob=report.records[0].id;await wait(`document.querySelector('[data-job="${magneticJob}"] button')`);await click(`[data-job="${magneticJob}"] button`);await wait(`location.pathname==='/magnetic.html' && selected===${JSON.stringify(magneticJob)} && rendered===selected`,300000);
  report.checks.push({operation:'main history routes magnetic job to its dedicated report page',passed:true});
  await call('Page.navigate',{url:launch.origin+'/'},sessionId);await wait('typeof currentJob!=="undefined" && document.querySelector("#run")');
  const rfProject=resolve(args['--cases'],'../rf-project.json');
  if(!restored){
    const {root}=await call('DOM.getDocument',{},sessionId);const {nodeId}=await call('DOM.querySelector',{nodeId:root.nodeId,selector:'#open'},sessionId);await call('DOM.setFileInputFiles',{nodeId,files:[rfProject]},sessionId);
    await wait('document.querySelector("#nr").value==="8" && document.querySelector("#nz").value==="10"');
    const old=await ev('document.querySelector("#jobs .job")?.dataset.job');await click('#run');
    await wait(`document.querySelector('#jobs .job')?.dataset.job!==${JSON.stringify(old)} && document.querySelector('#jobs .job button')?.textContent==='結果を開く' && !document.querySelector('#jobs .job button').disabled`,180000);
    report.rf_job=await ev('document.querySelector("#jobs .job").dataset.job');
  }else report.rf_job=restored.rf_job;
  await wait(`document.querySelector('[data-job="${report.rf_job}"] button')`);await click(`[data-job="${report.rf_job}"] button`);await wait(`currentJob===${JSON.stringify(report.rf_job)} && currentResult!==null`,90000);
  const actualRF=await ev('currentResult.result'),nativeRF=JSON.parse(await readFile(resolve(args['--workspace'],report.rf_job,'solution/results.json'),'utf8'));
  if(!isDeepStrictEqual(actualRF,nativeRF))throw Error('RF GUI no longer preserves full native results');
  const frequency=299792458*2.404825557695773/(2*Math.PI*.1);if(Math.abs(actualRF.modes[0].frequency_hz/frequency-1)>1e-3)throw Error('RF pillbox frequency regression');
  report.rf_result=actualRF;report.checks.push({operation:'existing RF file input, real pillbox FEM, complete native RF values and history retained',passed:true});
  for(const [page,selector] of [['/planar.html','#width'],['/hphi.html','#inner-radius']]){await call('Page.navigate',{url:launch.origin+page},sessionId);await wait(`document.querySelector(${JSON.stringify(selector)})`);await check('existing '+page+' loads',`document.querySelector('a[href="/magnetic.html"]')!==null`);}
  report.source_changed_during_run=!isDeepStrictEqual(report.source_sha256,await sourceHashes());report.passed=!report.source_changed_during_run&&report.external_requests.length===0;
  if(!report.passed)throw Error('source or external HTTP changed');console.log(JSON.stringify({passed:true,checks:report.checks}));
} catch(e){report.error=String(e);process.exitCode=1;console.error(e);}
finally{await writeFile(out+'/report.json',JSON.stringify(report,null,2));ws?.close();if(browser.exitCode===null){browser.kill();await new Promise(resolve=>browser.once('exit',resolve));}}
