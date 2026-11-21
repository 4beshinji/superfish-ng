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
  ws.onerror=(e)=>{report.websocket_error={message:e.message,error:String(e.error),cause:String(e.error?.cause)};};
  browser.on("exit",(code,signal)=>{report.browser_exit={code,signal};});
  ws.onclose=(e)=>{report.unexpected_websocket_close={code:e.code,reason:e.reason};for(const item of pending.values())item.fail(Error("debugger socket closed"));};
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
    report.last_evaluation=expression.slice(0,240);
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
  await call("Network.enable", {maxTotalBufferSize:1048576,maxResourceBufferSize:1048576,maxPostDataSize:1}, sessionId);
  await call("Network.setBlockedURLs", {urlPatterns:[
    {urlPattern:new URL(args['--url']).origin+'/*',block:false},
    {urlPattern:'http://*:*/*',block:true},
    {urlPattern:'https://*:*/*',block:true},
  ]},sessionId);
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
  const saved=async(name)=>{for(let n=0;n<3000;n++){try{return await readFile(out+'/downloads/'+name);}catch{}await sleep(100);}throw Error('download absent: '+name);};
  const cases=JSON.parse(await readFile(args['--request'],'utf8'));
  const fixture=cases.find(c=>c.name===args['--case']);if(!fixture)throw Error('select circle or ellipse');report.case=fixture.name;
  const original=JSON.parse(await readFile(fixture.checkpoint,'utf8'));
  await ev(`(()=>{window.checkpointTransport=[];const nativeFetch=window.fetch;window.fetch=async(url,options)=>{let evidence;if(options?.headers?.['X-NG-Action']){evidence={action:options.headers['X-NG-Action'],body_bytes:new Blob([options.body]).size,started:performance.now()};checkpointTransport.push(evidence);}const r=await nativeFetch(url,options);if(evidence){evidence.status=r.status;evidence.elapsed_ms=performance.now()-evidence.started;}return r;};})()`);
  if(!args['--existing-native-job']){
  await loadFile('#checkpoint-open',fixture.checkpoint);
  await wait(`typeof tune!=='undefined' && tune!==null && document.querySelector('#tune-selection').textContent.includes(${JSON.stringify(fixture.name+'-owned-checkpoint.json')})`,1500000);
  await check('real '+fixture.name+' complete owned checkpoint physics replay retains all original trials and both separate frequency gates',`tune.document.status==='TUNED' && tune.document.trials.length===${fixture.trial_count} && tune.document.decision.refined_target_met===true && tune.document.decision.mesh_difference_met===true && document.querySelector('#tune-summary').textContent.includes('最終目標: 達成') && document.querySelector('#tune-summary').textContent.includes('粗細差の条件: 達成') && document.querySelector('#tune-resume').disabled`);
  console.log(JSON.stringify(report.checks.at(-1)));
  await check('real '+fixture.name+' original target ranks and recovery metadata remain distinct from mode IDs',`JSON.stringify(tune.document.trials.map(t=>t.current_mode_ids))===${JSON.stringify(JSON.stringify(fixture.current_mode_ids))} && tune.document.trials[${fixture.target_trial-1}].current_mode_ids.indexOf(tune.document.request.mode_id)+1===${fixture.expected_rank}`);
  if(fixture.name==='ellipse')await check('real noncircular TE final refinement uses actual earlier anchor zero and recovered individual identities','tune.document.trials[1].identity_recovery.anchor_trial_index===0 && tune.document.trials[2].identity_recovery.anchor_trial_index===0 && tune.document.trials[2].frequency_hz!==null');
  await click('#checkpoint-save');const selection=JSON.parse(await saved('planar-curved-tune-checkpoint.json'));
  if(selection.format!=='superfish_ng_planar_curved_tune_selection'||selection.owner_job_directory!==null||!isDeepStrictEqual(selection.checkpoint,original))throw Error('complete large scientific checkpoint changed during actual GUI save');
  report.saved_checkpoint_bytes=(await readFile(out+'/downloads/planar-curved-tune-checkpoint.json')).length;
  report.checks.push({operation:'actual '+fixture.name+' full checkpoint download preserves every original E/H chart, trial, RF binding and decision',passed:true});
  await ev('document.querySelector("#tune-details").parentElement.open=true');
  const bounds=await ev('(()=>{const e=document.querySelector("#tune-details"),s=getComputedStyle(e);return {height:e.getBoundingClientRect().height,maxHeight:parseFloat(s.maxHeight),overflow:s.overflowY,scrollHeight:e.scrollHeight}})()');
  if(!Number.isFinite(bounds.maxHeight)||bounds.height>bounds.maxHeight+1||bounds.overflow!=='auto')throw Error('large tune diagnostics not bounded');report.diagnostic_bounds=bounds;
  await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true},sessionId).then(r=>writeFile(out+'/large-tune.png',Buffer.from(r.data,'base64')));
  await click(`[data-trial="${fixture.target_trial}"]`);
  await wait('document.querySelector("#field-link").href.includes("?job=")',1500000);
  const href=await ev('document.querySelector("#field-link").href');report.imported_job=new URL(href).searchParams.get('job');
  if(Number(new URL(href).searchParams.get('mode'))!==fixture.expected_rank)throw Error('imported target actual rank differs');
  const trial=fixture.sources[fixture.target_trial-1];
  for(const file of ['case.json','fields.npz','mesh.npz','results.json','manifest.json'])if(!(await readFile(resolve(args['--workspace'])+'/'+report.imported_job+'/solution/'+file)).equals(await readFile(trial.path+'/solution/'+file)))throw Error('original native bytes differ: '+file);
  report.transport=await ev('checkpointTransport');
  if(report.transport.length!==2||report.transport.some(r=>r.status!==200||r.body_bytes>128*1024**2))throw Error('actual dedicated large checkpoint transport evidence differs');
  if(fixture.name==='ellipse'&&report.transport.some(r=>r.body_bytes<=64*1024**2))throw Error('ellipse did not exercise >64 MiB actual science body');
  report.checks.push({operation:'actual '+fixture.name+' target field import exercises complete dedicated HTTP checkpoint body and preserves all original five files',passed:true});console.log(JSON.stringify(report.checks.at(-1)));
  await click('#field-link');await wait(`typeof selected!=='undefined' && selected===${JSON.stringify(report.imported_job)} && document.querySelector('#mode').value===${JSON.stringify(String(fixture.expected_rank))}`,240000);
  await check('native '+fixture.name+' RF page selects actual rank '+fixture.expected_rank+' with SI per-length energy and both named R/Q N/A',`project.case.schema_version===3 && document.querySelector('#mode').value===${JSON.stringify(String(fixture.expected_rank))} && document.querySelector('#quantities').textContent.includes('J/m') && document.querySelector('#na').textContent.includes('加速器定義・回路定義')`);
  }else{
    report.imported_job=args['--existing-native-job'];report.reused_actual_imported_job=true;
    const url=new URL(launch.href);url.pathname='/planar.html';url.search='?job='+encodeURIComponent(report.imported_job)+'&mode='+fixture.expected_rank;
    await call('Page.navigate',{url:url.href},sessionId);
    await wait(`typeof selected!=='undefined' && selected===${JSON.stringify(report.imported_job)} && document.querySelector('#mode').value===${JSON.stringify(String(fixture.expected_rank))}`,240000);
  }
  const trial=fixture.sources[fixture.target_trial-1];
  const names=await ev('[...document.querySelectorAll("#files button")].map(e=>e.textContent)');
  for(let i=0;i<names.length;i++){
    let oldBytes;if(args['--reuse-downloads'])try{oldBytes=await readFile(resolve(args['--reuse-downloads'])+'/'+names[i]);}catch(error){if(error.code!=='ENOENT')throw error;}
    if(oldBytes){if(!oldBytes.equals(await readFile(trial.path+'/solution/'+names[i])))throw Error('prior real download differs: '+names[i]);await writeFile(out+'/downloads/'+names[i],oldBytes);}
    else{await click(`#files button:nth-child(${i+1})`);if(!(await saved(names[i])).equals(await readFile(trial.path+'/solution/'+names[i])))throw Error('actual native download differs: '+names[i]);}
  }
  report.checks.push({operation:'real '+fixture.name+' original native downloads preserve all field/RF arrays from the selected actual mode',passed:true});
  await click('#plot');await wait('!document.querySelector("#image").hidden && document.querySelector("#image").naturalWidth>0',240000);
  await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true},sessionId).then(r=>writeFile(out+'/original-large-field.png',Buffer.from(r.data,'base64')));
  report.checks.push({operation:'actual '+fixture.name+' original field image renders after full large checkpoint replay',passed:true});
  report.source_changed_during_run=!isDeepStrictEqual(report.source_sha256,await sourceHashes());report.passed=!report.source_changed_during_run&&report.external_requests.length===0;
  if(!report.passed)throw Error('source or external request guard failed');console.log(JSON.stringify({passed:report.passed,checks:report.checks}));
}catch(e){report.browser_stderr=stderr;report.error=String(e);process.exitCode=1;console.error(e);}
finally{try{await writeFile(out+'/report.json',JSON.stringify(report,null,2));}finally{for(const entry of pending.values())clearTimeout(entry.timer);try{ws?.close();}finally{await dispose();}}}
