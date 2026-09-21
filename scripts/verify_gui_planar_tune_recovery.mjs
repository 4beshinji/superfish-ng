// SPDX-License-Identifier: Apache-2.0
// Real local browser input and computation. Requires a running GUI and Chrome.
import { spawn } from "node:child_process";
import { mkdtemp, readFile, writeFile, mkdir, readdir, rename } from "node:fs/promises";
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
if (!args["--url"] || !args["--out"])
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
      if (await ev(expression)) return;
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


  const launch=new URL(args['--url']);launch.pathname='/planar.html';await call('Page.navigate',{url:launch.href},sessionId);
  await wait('document.querySelector("#width")?.value==="310"');
  const check=async(operation,expression)=>{if(!await ev(`(async()=>(${expression}))()`))throw Error(operation);report.checks.push({operation,passed:true});};
  const loadFile=async(selector,filename)=>{const {root}=await call('DOM.getDocument',{},sessionId);const {nodeId}=await call('DOM.querySelector',{nodeId:root.nodeId,selector},sessionId);await call('DOM.setFileInputFiles',{nodeId,files:[]},sessionId);await call('DOM.setFileInputFiles',{nodeId,files:[resolve(filename)]},sessionId);};
  const download=async(name)=>{for(let i=0;i<300;i++){try{return await readFile(out+'/downloads/'+name);}catch{}await sleep(100);}throw Error('missing download '+name);};
  if(args['--resume-report']){
    const prior=JSON.parse(await readFile(args['--resume-report'],'utf8'));report.prior_report=resolve(args['--resume-report']);report.unverified_job=prior.unverified_job;
    await call('Page.navigate',{url:launch.origin+'/planar.html?job='+prior.resumed_job},sessionId);
    await wait(`typeof tuneSelection!=='undefined' && tuneSelection===${JSON.stringify(prior.resumed_job)}`,180000);
    await check('new server replays successful recovery and final refinement','currentTune.document.status==="TUNED" && currentTune.document.trials[2].identity_recovery.status==="PASS"');
    await click('#tune-trials [data-tune-trial="3"]');await wait('selected!==null && $("mode").value==="1"');
    await click('#plot');await wait('!$("image").hidden && $("image").naturalWidth>100',120000);
    report.checks.push({operation:'new server restores and renders recovered native field',passed:true});
    await call('Page.navigate',{url:launch.origin+'/planar.html?job='+report.unverified_job},sessionId);
    await wait(`typeof tuneSelection!=='undefined' && tuneSelection===${JSON.stringify(report.unverified_job)}`,120000);
  }else{
  const expected=JSON.parse(await readFile(args['--request'],'utf8'));
  await loadFile('#tune-open',args['--request']);await wait('project.case.mesh.nx===6 && $("tune-mode-id").value==="x"');
  if(!isDeepStrictEqual(JSON.parse(await ev('tuneRequestText()')),expected))throw Error('loaded request differs');
  await click('#tune-save');const saved=await download('planar-tune.json');if(!isDeepStrictEqual(JSON.parse(saved),expected))throw Error('saved request differs');
  report.checks.push({operation:'dedicated request and Project roundtrip with SI units',passed:true});
  await ev('document.querySelector("#tune-controls").closest("details").open=true');
  await fill('#tune-controls',JSON.stringify(expected.controls).replace('"minimum_overlap":0.9','"minimum_overlap":0.9,"minimum_overlap":0.8'));
  await click('#tune-start');await wait('!$("error").hidden && $("error").textContent.includes("duplicate")');
  await check('duplicate tracking controls rejected before allocation','(await api("jobs")).every(j=>j.kind!=="planar_tune")');
  await loadFile('#tune-open',args['--request']);await wait('JSON.parse($("tune-controls").value).minimum_overlap===.9');
  await ev('window.__baseApi=api;api=async(action,...rest)=>{const value=await __baseApi(action,...rest);if(["planar-start-tune","planar-resume-tune"].includes(action))window.__tuneJob=value.id;return value;}');
  const complete=async(id)=>{await wait(`document.querySelector('[data-job="${id}"] strong')?.textContent.startsWith('complete')`,120000);await click(`[data-job="${id}"] > button`);await wait(`tuneSelection===${JSON.stringify(id)}`,120000);};
  await click('#tune-start');await wait('!!window.__tuneJob');report.first_job=await ev('__tuneJob');await complete(report.first_job);
  await check('actual worker pauses at two trials with source identities','currentTune.document.status==="PAUSED" && currentTune.document.trials.length===2 && !$("tune-resume").disabled');
  await click('#tune-checkpoint-save');const checkpoint=await download('planar-tune-checkpoint.json');await writeFile(out+'/paused-checkpoint.json',checkpoint);
  await loadFile('#tune-checkpoint-open',out+'/paused-checkpoint.json');await wait('tuneSelection==="paused-checkpoint.json"');
  await check('saved checkpoint fully replays before resume','currentTune.document.status==="PAUSED" && currentTune.document.trials.length===2');
  await fill('#tune-new-trials','');await ev('window.__tuneJob=null');await click('#tune-resume');await wait('!!window.__tuneJob');report.resumed_job=await ev('__tuneJob');await complete(report.resumed_job);
  await check('resumed bisection and final refinement meet separate gates','currentTune.document.status==="TUNED" && currentTune.document.trials.length===3 && currentTune.document.decision.refined_target_met && currentTune.document.decision.mesh_difference_met && $("tune-resume").disabled && $("tune-decision").textContent.includes("粗細差")');
  await check('search and refinement preserve raw unresolved IDs and explicitly recover the target','currentTune.document.trials.slice(1).every(t=>t.identity_recovery.status==="PASS" && t.tracking.current_mode_ids.every(x=>x===null) && JSON.stringify(t.current_mode_ids)===JSON.stringify(["x","y"])) && $("tune-identities").textContent.includes("anchor_trial_index")');
  await writeFile(out+'/final-checkpoint.json',await ev('currentTune.serialized'));
  await click('#tune-trials [data-tune-trial="3"]');await wait('selected!==null && $("mode").value==="1"');report.imported_job=await ev('selected');
  await check('target trial opens the verified native mode and per-length RF','result.case.geometry.width_m===.214 && $("quantities").textContent.includes("J/m") && $("na").textContent.includes("N/A")');
  await click('#plot');await wait('!$("image").hidden && $("image").naturalWidth>100',120000);
  await ev('$("result").scrollIntoView({block:"start"})');let shot=await call('Page.captureScreenshot',{format:'png'},sessionId);await writeFile(out+'/target-field.png',Buffer.from(shot.data,'base64'));
  await call('Page.navigate',{url:launch.origin+'/planar.html?job='+report.resumed_job},sessionId);await wait(`typeof tuneSelection!=='undefined' && tuneSelection===${JSON.stringify(report.resumed_job)}`,120000);
  await check('page reload reopens persistent tuning result','currentTune.document.status==="TUNED" && $("tune-resume").disabled');
  await ev('$("tune-result").scrollIntoView({block:"start"})');shot=await call('Page.captureScreenshot',{format:'png'},sessionId);await writeFile(out+'/tune-result.png',Buffer.from(shot.data,'base64'));
  // A delayed server normalization must not overwrite edits made meanwhile.
  await ev('window.__baseApi=api;api=async(action,...rest)=>{const value=await __baseApi(action,...rest);if(action==="planar-normalize-tune")await new Promise(done=>setTimeout(done,1000));return value;}');
  await click('#tune-save');await fill('#tune-target',123456789);await wait('!$("error").hidden && $("error").textContent.includes("入力が変わりました")');
  await check('stale normalization preserves edited input','$("tune-target").value==="123456789"');await ev('api=__baseApi');
  const cancel=structuredClone(expected);cancel.frequency_tolerance_hz=1e-5;cancel.parameter_tolerance=1e-15;cancel.max_trials=60;cancel.target_hz=299792458/(2*.2112);
  await writeFile(out+'/cancel-request.json',JSON.stringify(cancel));await loadFile('#tune-open',out+'/cancel-request.json');await wait('$("tune-max-trials").value==="60"');await fill('#tune-new-trials','');
  await ev('window.__baseApi=api;window.__tuneJob=null;api=async(action,...rest)=>{const value=await __baseApi(action,...rest);if(["planar-start-tune","planar-resume-tune"].includes(action))window.__tuneJob=value.id;return value;}');
  await click('#tune-start');await wait('!!window.__tuneJob');report.cancelled_job=await ev('__tuneJob');
  const cp=resolve(args['--workspace'],report.cancelled_job,'execution/checkpoint-001.json');let found=false;
  for(let i=0;i<600;i++){try{JSON.parse(await readFile(cp,'utf8'));found=true;break;}catch{}await sleep(50);}if(!found)throw Error('no completed checkpoint before cancel');
  await wait(`document.querySelector('[data-job="${report.cancelled_job}"] > button')?.textContent==='中止'`);await click(`[data-job="${report.cancelled_job}"] > button`);
  await wait(`document.querySelector('[data-job="${report.cancelled_job}"] strong')?.textContent.startsWith('cancelled')`,30000);
  await click(`[data-tune-checkpoints="${report.cancelled_job}"]`);await wait(`!!document.querySelector('[data-job="${report.cancelled_job}"] [data-checkpoint="1"]')`);
  await click(`[data-job="${report.cancelled_job}"] [data-checkpoint="1"]`);await wait(`tuneSelection===${JSON.stringify(report.cancelled_job+' / 試行 1')}`,120000);
  await check('actual cancellation exposes and revalidates completed checkpoint','currentTune.document.status==="PAUSED" && currentTune.document.trials.length===1');
  await fill('#tune-new-trials',1);await ev('window.__tuneJob=null');await click('#tune-resume');await wait('!!window.__tuneJob');report.cancel_resume_job=await ev('__tuneJob');await complete(report.cancel_resume_job);
  await check('cancelled job resumes into a new job without losing ancestry','currentTune.document.status==="PAUSED" && currentTune.document.trials.length===2');
  const unverified=structuredClone(expected);unverified.project.case.geometry.width_m=.18;unverified.project.case.geometry.height_m=.2;unverified.bounds=[.18,.2];unverified.initial_ids=['y','x'];
  await writeFile(out+'/unverified-request.json',JSON.stringify(unverified));await loadFile('#tune-open',out+'/unverified-request.json');await wait('$("tune-bounds").value==="[0.18,0.2]"');await fill('#tune-new-trials','');await ev('window.__tuneJob=null');await click('#tune-start');await wait('!!window.__tuneJob');report.unverified_job=await ev('__tuneJob');await complete(report.unverified_job);
  }
  await check('ambiguous target is unevaluated and cannot open a fabricated mode','currentTune.document.status==="UNVERIFIED" && $("tune-trials").textContent.includes("未評価") && document.querySelectorAll("[data-tune-trial]")[1].disabled && $("tune-resume").disabled');
  await click('#tune-trials [data-tune-trial="1"]');await wait('$("mode").value==="2"');report.imported_rank2_job=await ev('selected');
  await check('source target ID opens rank two rather than default rank one','result.case.geometry.width_m===.18 && $("mode").value==="2"');
  await click('#study-save');const legacy=JSON.parse(await download('planar-study.json'));
  if(legacy.format!=='superfish_ng_planar_study'||legacy.kind!=='sweep')throw Error('legacy independent Study changed');
  report.checks.push({operation:'existing independent Study definition still saves',passed:true});
  report.source_changed_during_run=!isDeepStrictEqual(report.source_sha256,await sourceHashes());report.passed=!report.source_changed_during_run&&report.external_requests.length===0;
  if(!report.passed)throw Error('source or external HTTP changed');console.log(JSON.stringify({passed:true,checks:report.checks}));
} catch(e){report.error=String(e);process.exitCode=1;console.error(e);}
finally{await writeFile(out+'/report.json',JSON.stringify(report,null,2));ws?.close();if(browser.exitCode===null){browser.kill();await new Promise(resolve=>browser.once('exit',resolve));}}
