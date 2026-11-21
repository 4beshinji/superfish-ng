// SPDX-License-Identifier: Apache-2.0
// Real local browser input and computation. Requires a running GUI and Chrome.
import { launchBrowser } from "./browser-session.mjs";
import { readFile, writeFile, mkdir, readdir, rename } from "node:fs/promises";
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
if (!args["--server-log"] || !args["--out"] || !args["--request"] || !args["--workspace"])
  throw Error(
    "Usage: node scripts/verify_gui_planar_curved_tuning.mjs --server-log LOG --out NEW_DIRECTORY --request REQUEST --workspace GUI_WORKSPACE",
  );
args['--url']=(await readFile(args['--server-log'],'utf8')).match(/http:\/\/127\.0\.0\.1:[0-9]+\/#\S+/)?.[0];
if(!args['--url'])throw Error('local server launch URL absent');
const out = resolve(args["--out"]);
await mkdir(out, { recursive: false });
const { profile, browser, dispose } = await launchBrowser();
let stderr = "",
  ws,
  id = 0;
const pending = new Map(),
  sleep = (ms) => new Promise((r) => setTimeout(r, ms));
browser.stderr.on("data", (b) => (stderr = (stderr + b).slice(-65536)));
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
      if (await ev(expression)) return;
      if(await ev('document.querySelector("#error") && !document.querySelector("#error").hidden'))throw Error(await ev('document.querySelector("#error").textContent'));
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

  const launch=new URL(args['--url']);launch.pathname='/planar-curved.html';
  await call('Page.navigate',{url:launch.href},sessionId);
  await wait('document.querySelector("#tune-request") && typeof api==="function"');
  const check=async(operation,expression)=>{if(!await ev(expression))throw Error(operation);report.checks.push({operation,passed:true});};
  const loadFile=async(selector,filename)=>{const {root}=await call('DOM.getDocument',{},sessionId);const {nodeId}=await call('DOM.querySelector',{nodeId:root.nodeId,selector},sessionId);await call('DOM.setFileInputFiles',{nodeId,files:[resolve(filename)]},sessionId);};
  const saved=async(name)=>{for(let n=0;n<300;n++){try{return await readFile(out+'/downloads/'+name);}catch{}await sleep(100);}throw Error('download absent: '+name);};
  if(args['--render-only']){
    await fill('#tune-request',await readFile(args['--request'],'utf8'));
    const widths=await ev('[...document.querySelectorAll("#planar-curved-workspace textarea")].map(e=>({id:e.id,width:e.getBoundingClientRect().width,parent:e.parentElement.getBoundingClientRect().width}))');
    if(widths.some(e=>e.width<.9*e.parent))throw Error('curve JSON editor does not fit its panel');
    report.editor_widths=widths;report.checks.push({operation:'all curved JSON editors use panel width and render readable controls',passed:true});
    await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true},sessionId).then(r=>writeFile(out+'/curved-workspace.png',Buffer.from(r.data,'base64')));
  }else{
  const openLatest=async()=>{await wait('document.querySelector("#jobs .job button")?.textContent==="結果を開く"',180000);const identifier=await ev('document.querySelector("#jobs .job").dataset.job');await click('#jobs .job button');await wait(`typeof tune!=="undefined" && tune!==null && document.querySelector('#tune-selection').textContent.includes(${JSON.stringify(identifier)})`,180000);return identifier;};
  if(!args['--resume-selection']){
  const request=JSON.parse(await readFile(args['--request'],'utf8'));
  await fill('#tune-request',JSON.stringify(request));
  await click('#tune-save');
  if(!isDeepStrictEqual(JSON.parse(await saved('planar-curved-tune-request.json')),request))throw Error('saved curved request changed');
  await loadFile('#tune-open',out+'/downloads/planar-curved-tune-request.json');
  await wait('document.querySelector("#dirty").textContent==="条件を復元しました"');
  report.checks.push({operation:'real curved request save and file reload preserve all original nodes, controls and units',passed:true});
  await click('#tune-start');report.first_job=await openLatest();
  await check('actual curved FEM worker publishes verified PAUSED prefix with original target rank','tune.document.status==="PAUSED" && tune.document.trials.length===1 && tune.document.trials[0].current_mode_ids[0]===tune.document.request.mode_id && !document.querySelector("#tune-resume").disabled');
  await click('#checkpoint-save');const checkpoint=await saved('planar-curved-tune-checkpoint.json');
  const document=JSON.parse(checkpoint);if(document.format!=='superfish_ng_planar_curved_tune_selection'||document.checkpoint.trials.length!==1)throw Error('checkpoint selection format');
  await loadFile('#checkpoint-open',out+'/downloads/planar-curved-tune-checkpoint.json');
  await wait('document.querySelector("#tune-selection").textContent.includes("planar-curved-tune-checkpoint.json")',180000);
  const once=await ev('tune.serialized');
  const repeatVersion=await ev('inputVersion');
  await loadFile('#checkpoint-open',out+'/downloads/planar-curved-tune-checkpoint.json');
  await wait(`inputVersion>${repeatVersion+1}`,180000);
  await wait('document.querySelector("#error").hidden');
  if(await ev('tune.serialized')!==once)throw Error('same saved selection changed');
  report.checks.push({operation:'real checkpoint download and repeated same-file physics replay remain bound to stopped job',passed:true});
  await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true},sessionId).then(r=>writeFile(out+'/curved-tune.png',Buffer.from(r.data,'base64')));
  await click('[data-trial="1"]');await wait('document.querySelector("#field-link").href.includes("?job=")',180000);
  const href=await ev('document.querySelector("#field-link").href');report.imported_job=new URL(href).searchParams.get('job');
  await click('#field-link');await wait(`typeof selected!=='undefined' && selected===${JSON.stringify(report.imported_job)}`,180000);
  await check('native field page opens the actual selected mode with per-length RF and both R/Q N/A','project.case.schema_version===3 && document.querySelector("#mode").value==="1" && document.querySelector("#quantities").textContent.includes("J/m") && document.querySelector("#na").textContent.includes("加速器定義・回路定義")');
  const names=await ev('[...document.querySelectorAll("#files button")].map(e=>e.textContent)');
  for(let i=0;i<names.length;i++){await click(`#files button:nth-child(${i+1})`);if(!(await saved(names[i])).equals(await readFile(args['--workspace']+'/'+report.first_job+'/execution/trial-001/solution/'+names[i])))throw Error('native original bytes changed: '+names[i]);}
  report.checks.push({operation:'real native download preserves all original five files including all field/RF arrays',passed:true});
  await click('#plot');await wait('!document.querySelector("#image").hidden && document.querySelector("#image").naturalWidth>0',180000);
  await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true},sessionId).then(r=>writeFile(out+'/original-field.png',Buffer.from(r.data,'base64')));
  report.checks.push({operation:'actual original curved field image renders in native RF page',passed:true});
  }else{
    const bytes=await readFile(args['--resume-selection']);await writeFile(out+'/downloads/planar-curved-tune-checkpoint.json',bytes);
    report.first_job=JSON.parse(bytes).owner_job_directory.split('/').at(-1);
    report.resumed_saved_selection=true;
  }
  await call('Page.navigate',{url:launch.href},sessionId);await wait('typeof tune!=="undefined" && document.querySelector("#checkpoint-open")');
  await loadFile('#checkpoint-open',out+'/downloads/planar-curved-tune-checkpoint.json');await wait('typeof tune!=="undefined" && tune!==null',180000);
  const selectedPrefix=JSON.parse(await readFile(out+'/downloads/planar-curved-tune-checkpoint.json'));
  if(args['--existing-resumed-job']){
    report.resumed_job=args['--existing-resumed-job'];const selector=`[data-job="${report.resumed_job}"] button`;
    await wait(`document.querySelector(${JSON.stringify(selector)})?.textContent==='結果を開く'`,180000);await click(selector);
    await wait(`tune.document.trials.length===2 && document.querySelector('#tune-selection').textContent.includes(${JSON.stringify(report.resumed_job)})`,180000);
    report.reused_actual_resumed_job=true;
  }else{await click('#tune-resume');await wait(`document.querySelector('#jobs .job')?.dataset.job!==${JSON.stringify(report.first_job)}`,180000);report.resumed_job=await openLatest();}
  await check('actual GUI resume creates new worker with byte-identical inherited prefix and inverse frequency scale','tune.document.status==="PAUSED" && tune.document.trials.length===2 && Math.abs(tune.document.trials[0].frequency_hz/tune.document.trials[1].frequency_hz-1.4)<1e-10');
  for(const [name,hash] of Object.entries(selectedPrefix.checkpoint.trial_sources_sha256[0]))if(createHash('sha256').update(await readFile(args['--workspace']+'/'+report.resumed_job+'/execution/trial-001/'+name)).digest('hex')!==hash)throw Error('GUI resumed prefix original bytes changed');
  }
  report.source_changed_during_run=!isDeepStrictEqual(report.source_sha256,await sourceHashes());report.passed=!report.source_changed_during_run&&report.external_requests.length===0;
  if(!report.passed)throw Error('source or external request guard failed');console.log(JSON.stringify({passed:report.passed,checks:report.checks}));
}catch(e){report.error=String(e);process.exitCode=1;console.error(e);}
finally{try{await writeFile(out+'/report.json',JSON.stringify(report,null,2));}finally{for(const entry of pending.values())clearTimeout(entry.timer);try{ws?.close();}finally{await dispose();}}}
