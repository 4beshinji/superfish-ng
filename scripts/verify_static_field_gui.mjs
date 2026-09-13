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
    "Usage: node scripts/verify_static_field_gui.mjs --url-file LAUNCH_URL_FILE --cases CASES_JSON --workspace WORKSPACE --out NEW_DIRECTORY",
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

  const launch = new URL(args['--url']); launch.pathname = '/static.html';
  const cases = JSON.parse(await readFile(args['--cases'], 'utf8'));
  const restored = args['--restore'] ? JSON.parse(await readFile(args['--restore'], 'utf8')) : null;
  const check = async (operation, expression) => { if (!await ev(expression)) throw Error(operation); report.checks.push({operation,passed:true}); };
  const download = async name => { for(let i=0;i<600;i++){try{return await readFile(out+'/downloads/'+name);}catch{}await sleep(100);}throw Error('missing download '+name); };
  const navigate = async id => {const url=new URL(launch);if(id)url.searchParams.set('job',id);await call('Page.navigate',{url:url.href},sessionId);await wait('typeof selected!=="undefined" && document.querySelector("#document")');};
  const ready = async () => await wait('typeof selected!=="undefined" && selected!==null && rendered===selected && !document.querySelector("#result-view").hidden',300000);
  const loadProject = async file => {
    await ev('document.querySelector("#document").value="";document.querySelector("#input-file").value=""');
    const {root}=await call('DOM.getDocument',{},sessionId);const {nodeId}=await call('DOM.querySelector',{nodeId:root.nodeId,selector:'#input-file'},sessionId);
    await call('DOM.setFileInputFiles',{nodeId,files:[file]},sessionId);await wait('document.querySelector("#document").value.length>0',120000);
    const expected=JSON.parse(await readFile(file,'utf8')),actual=JSON.parse(await ev('document.querySelector("#document").value'));
    if(!isDeepStrictEqual(actual,expected))throw Error('file input changed the Project or SI Case');
  };
  const solve = async file => {await loadProject(file);const old=await ev('selected');await click('#solve');await wait(`selected!==${JSON.stringify(old)}`,120000);await ready();return await ev('selected');};
  await navigate(); report.records=[];
  for(const [index,value] of cases.entries()){
    const expected=JSON.parse(await readFile(value.expected_view_file,'utf8')),project=expected.project;
    let job;
    if(restored){job=restored.records[index].id;await navigate(job);await ready();}
    else{
      await loadProject(value.project_file);
      const alternate=project.display_length_unit==='m'?'mm':'m';
      for(const unit of [alternate,project.display_length_unit]){
        await ev(`document.querySelector('#length-unit').value=${JSON.stringify(unit)};document.querySelector('#input-status').textContent=''`);await click('#validate');await wait('document.querySelector("#input-status").textContent.length>0',120000);
        const actual=JSON.parse(await ev('document.querySelector("#document").value'));
        if(!isDeepStrictEqual(actual,{...project,display_length_unit:unit}))throw Error('display unit switch changed SI Case');
      }
      if(index===0){
        await ev(`(()=>{const p=JSON.parse(document.querySelector('#document').value);p.case.name+=' GUI編集';document.querySelector('#document').value=jsonText(p);document.querySelector('#input-status').textContent=''})()`);
        await click('#validate');await wait('document.querySelector("#input-status").textContent.length>0');
        const actual=JSON.parse(await ev('document.querySelector("#document").value'));
        if(!isDeepStrictEqual(actual,{...project,case:{...project.case,name:project.case.name+' GUI編集'}}))throw Error('JSON editor changed unrelated fields');
        await fill('#document',await readFile(value.project_file,'utf8'));
        await ev('document.querySelector("#input-status").textContent=""');await click('#validate');await wait('document.querySelector("#input-status").textContent.length>0');
        report.checks.push({operation:'strict JSON editing retains every other SI/material/initial-value field',passed:true});
      }
      await click('#save-project');const saved=await download('static-project.json');if(!saved.equals(await readFile(value.project_file)))throw Error('Project download bytes changed');await rename(out+'/downloads/static-project.json',out+'/downloads/'+index+'-edited-project.json');
      const old=await ev('selected');await click('#solve');await wait(`selected!==${JSON.stringify(old)}`,120000);await ready();job=await ev('selected');
    }
    if(!isDeepStrictEqual(JSON.parse(await ev('document.querySelector("#project-json").textContent')),project))throw Error('displayed Project changed');
    if(!isDeepStrictEqual(JSON.parse(await ev('document.querySelector("#outcome-json").textContent')),expected.outcome))throw Error('displayed original quantities or failure history changed');
    if(await ev('document.querySelector("#solver-status").dataset.status')!==expected.solver_status)throw Error('success/failure status changed');
    if(await ev('document.querySelector("#field-view").hidden')!==value.failed)throw Error('failure plot visibility incorrect');
    if(!await ev('document.querySelector("#rf-na").textContent.includes("N/A") && document.querySelector("#rf-na").textContent.includes("circuit / accelerator")'))throw Error('RF N/A definitions missing');
    let plots=0;
    if(!value.failed){
      if(!isDeepStrictEqual(JSON.parse(await ev('document.querySelector("#probe-json").textContent')),expected.plot.cell_center_probe))throw Error('original cell-center field samples or materials changed');
      const rows=await ev('Array.from(document.querySelectorAll("#quantity-table tbody tr")).map(r=>Array.from(r.cells).map(c=>c.textContent))');
      const wanted=Object.entries(expected.outcome.quantities).filter(([,v])=>typeof v==='number').map(([k,v])=>[k,Object.is(v,-0)?'-0':String(v)]);
      if(!isDeepStrictEqual(rows,wanted))throw Error('quantity table changed SI numbers');
      for(const [field,unit] of Object.entries(expected.plot.field_units)){
        await ev(`document.querySelector('#field').value=${JSON.stringify(field)};document.querySelector('#field').dispatchEvent(new Event('change'))`);
        const values=expected.plot.cell_center_probe.fields[field],lo=Math.min(...values),hi=Math.max(...values),caption=await ev('document.querySelector("#field-caption").textContent');
        for(const text of [field,`[${unit}]`,String(values.length),lo.toPrecision(8),hi.toPrecision(8),project.display_length_unit])if(!caption.includes(text))throw Error('field component, SI unit or sample extrema missing '+text);
        const limit=Math.max(Math.abs(lo),Math.abs(hi));
        if(!await ev(`document.querySelector('#field-canvas').dataset.rangeMin===${JSON.stringify(String(-limit))}&&document.querySelector('#field-canvas').dataset.rangeMax===${JSON.stringify(String(limit))}`))throw Error('component color scale must be explicitly symmetric about zero');
        if(!await ev(`(()=>{const c=document.querySelector('#field-canvas'),p=c.getContext('2d').getImageData(0,0,c.width,c.height).data;return c.dataset.field===${JSON.stringify(field)}&&Array.from(p).some((v,i)=>i%4===3&&v>0)})()`))throw Error('field canvas did not render');plots++;
      }
    }else if(!(await ev('document.querySelector("#failure-reason").textContent')).includes(expected.outcome.reason))throw Error('actual failure reason missing');
    const files=['project.json',...(value.failed?['case.json','failure.json','manifest.json']:['case.json','fields.npz','manifest.json','mesh.npz','results.json']).map(n=>'solution/'+n)];
    for(const file of files){await click(`#downloads button[data-file="${file}"]`);const name=file.replaceAll('/','-'),bytes=await download(name);if(!bytes.equals(await readFile(resolve(value.source_job,file)))||!bytes.equals(await readFile(resolve(args['--workspace'],job,file))))throw Error('native download differs '+file);await rename(out+'/downloads/'+name,out+'/downloads/'+index+'-'+name);}
    if([0,4,13,16,28,33].includes(index)){await ev('document.querySelector("#field-canvas").scrollIntoView({block:"center"})');const shot=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false},sessionId);await writeFile(out+'/case-'+index+'.png',Buffer.from(shot.data,'base64'));}
    report.records.push({name:value.name,id:job,failed:value.failed,plots,downloads:files.length,project_download:!restored,original_case_quantities_fields_and_units_identical:true});report.checks.push({operation:(restored?'restart/replay/display ':'input/edit/solve/display ')+value.name,passed:true});console.log('DONE',index,value.name);
  }
  await check('HTTP rejects missing token',`(async()=>{const r=await fetch('/api',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'static-field-jobs'})});return r.status===403})()`);
  await check('HTTP rejects extra action fields',`(async()=>{const r=await fetch('/api',{method:'POST',headers:{'Content-Type':'application/json','X-NG-Token':token},body:JSON.stringify({action:'static-field-jobs',extra:1})});return r.status===400})()`);
  if(!restored){
    const original=await readFile(cases[0].project_file,'utf8'),duplicate=original.replace('"project_version": 1','"project_version": 1, "project_version": 1');
    await fill('#document',duplicate);await click('#solve');await wait('!document.querySelector("#error").hidden && document.querySelector("#error").textContent.includes("duplicate") && document.querySelector("#result-view").hidden');
    report.checks.push({operation:'duplicate JSON keys reject through actual editor/solve HTTP action',passed:true});
    const extra=await solve(cases[0].project_file);report.changed_owned_job=extra;const changed=resolve(args['--workspace'],extra,'solution/results.json');await writeFile(changed,Buffer.concat([await readFile(changed),Buffer.from('\n')]));
    await wait('!document.querySelector("#error").hidden && document.querySelector("#result-view").hidden && document.querySelector("#field-view").hidden');
    await check('changed owned native removes plot/quantities and rejects download',`(async()=>{try{await api('static-field-download',{id:selected,file:'solution/results.json'},true);return false;}catch{return true;}})()`);
    await click(`.job[data-job="${report.records[0].id}"] button`);await ready();await check('selecting a valid result clears previous changed-file error',`document.querySelector('#error').hidden`);
    const cancelProject=resolve(args['--cases'],'../cancel-project.json');
    for(const operation of ['cancel','kill']){
      await loadProject(cancelProject);const old=await ev('selected');await click('#solve');await wait(`selected!==${JSON.stringify(old)}`,120000);const id=await ev('selected');
      await wait(`(async()=>{const j=(await api('static-field-jobs')).find(j=>j.id===${JSON.stringify(id)});return j?.status==='running'})()`,120000);
      if(operation==='cancel')await click(`.job[data-job="${id}"] button`);
      else{const directory=resolve(args['--workspace'],id),state=JSON.parse(await readFile(directory+'/job.json','utf8')),pid=Number((await readFile(directory+'/worker.claim','utf8')).trim());if(state.status!=='running'||!Number.isSafeInteger(pid)||pid<=1)throw Error('cannot identify live owned worker');process.kill(pid,'SIGKILL');}
      const expected=operation==='cancel'?'cancelled':'failed';await wait(`(async()=>{const j=(await api('static-field-jobs')).find(j=>j.id===${JSON.stringify(id)});return j?.status===${JSON.stringify(expected)}})()`,30000);
      await wait('document.querySelector("#result-view").hidden && document.querySelector("#field-view").hidden');report[operation+'_job']=id;report.checks.push({operation:'real static GUI worker '+operation+' leaves no success field',passed:true});
    }
  }
  for(const index of [0,33]){
    await call('Page.navigate',{url:launch.origin+'/'},sessionId);await wait('typeof currentJob!=="undefined" && document.querySelector("#run")');const job=report.records[index].id;
    await wait(`document.querySelector('.job[data-job="${job}"] button') && !document.querySelector('.job[data-job="${job}"] button').disabled`);await click(`.job[data-job="${job}"] button`);await ready();
    if(await ev('location.pathname')!=='/static.html'||await ev('selected')!==job)throw Error('main history misroutes static success/failure');
    report.checks.push({operation:'main history opens static '+(index?'saved failure':'success')+' in dedicated page',passed:true});
  }
  await call('Page.navigate',{url:launch.origin+'/'},sessionId);await wait('typeof currentJob!=="undefined" && document.querySelector("#run")');
  const rfProject=resolve(args['--cases'],'../rf-project.json');
  if(!restored){
    const {root}=await call('DOM.getDocument',{},sessionId);const {nodeId}=await call('DOM.querySelector',{nodeId:root.nodeId,selector:'#open'},sessionId);await call('DOM.setFileInputFiles',{nodeId,files:[rfProject]},sessionId);await wait('document.querySelector("#nr").value==="8" && document.querySelector("#nz").value==="10"');
    const old=await ev('document.querySelector("#jobs .job")?.dataset.job');await click('#run');await wait(`document.querySelector('#jobs .job')?.dataset.job!==${JSON.stringify(old)} && document.querySelector('#jobs .job button')?.textContent==='結果を開く' && !document.querySelector('#jobs .job button').disabled`,180000);report.rf_job=await ev('document.querySelector("#jobs .job").dataset.job');
  }else report.rf_job=restored.rf_job;
  await wait(`document.querySelector('.job[data-job="${report.rf_job}"] button')`);await click(`.job[data-job="${report.rf_job}"] button`);await wait(`currentJob===${JSON.stringify(report.rf_job)} && currentResult!==null`,90000);
  const actualRF=await ev('currentResult.result'),nativeRF=JSON.parse(await readFile(resolve(args['--workspace'],report.rf_job,'solution/results.json'),'utf8'));
  if(!isDeepStrictEqual(actualRF,nativeRF)||Math.abs(actualRF.modes[0].frequency_hz/(299792458*2.404825557695773/(2*Math.PI*.1))-1)>1e-3)throw Error('existing RF FEM/native regression');
  report.checks.push({operation:'existing RF file input, actual pillbox FEM and full native quantities retained',passed:true});
  for(const [page,selector] of [['/planar.html','#width'],['/hphi.html','#inner-radius'],['/magnetic.html','#source-path']]){await call('Page.navigate',{url:launch.origin+page},sessionId);await wait(`document.querySelector(${JSON.stringify(selector)})`);await check('existing '+page+' retains static navigation',`document.querySelector('a[href="/static.html"]')!==null`);}
  report.source_changed_during_run=!isDeepStrictEqual(report.source_sha256,await sourceHashes());report.passed=!report.source_changed_during_run&&report.external_requests.length===0;
  if(!report.passed)throw Error('source or external HTTP changed');console.log(JSON.stringify({passed:true,checks:report.checks.length}));
}catch(error){report.error=String(error);process.exitCode=1;console.error(error);}
finally{await writeFile(out+'/report.json',JSON.stringify(report,null,2));ws?.close();if(browser.exitCode===null){browser.kill();await new Promise(done=>browser.once('exit',done));}}

