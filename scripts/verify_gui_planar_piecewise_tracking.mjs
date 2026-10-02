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
if (!args["--url"] || !args["--out"])
  throw Error(
    "Usage: node scripts/verify_gui_planar_piecewise_tracking.mjs --url LAUNCH_URL --out NEW_DIRECTORY --fixture FIXTURE_JSON; or --resume-report PRIOR_REPORT",
  );
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
    const priorError=await ev('document.querySelector("#error")?.hidden ? "" : document.querySelector("#error")?.textContent');
    let cleared=!priorError;
    while (performance.now() - start < ms) {
      if (await ev(expression)) return;
      const error=await ev('document.querySelector("#error")?.hidden ? "" : document.querySelector("#error")?.textContent');
      if(!error)cleared=true;
      if(error&&(cleared||error!==priorError))throw Error(`UI error: ${error}`);
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
    if(await ev(`document.querySelector(${JSON.stringify(selector)}).closest('details')?.open===false`))
      await click(`details:has(${selector}) > summary`);
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


  const launch=new URL(args['--url']);launch.pathname='/planar.html';
  await call('Page.navigate',{url:launch.href},sessionId);
  await wait('document.querySelector("#width")?.value==="310"');
  const check=async(operation,expression)=>{
    if(!await ev(expression))throw Error(operation);
    report.checks.push({operation,passed:true});console.log('PASS '+operation);
  };
  const instrument=async()=>ev(`if(typeof window.__trackingLoads==='undefined'){
    window.__trackingLoads=0;window.__startedPair=null;window.__startedHistory=null;
    const originalAPI=api;api=async(action,...rest)=>{const value=await originalAPI(action,...rest);
      if(action==='planar-normalize-tracking')window.__trackingLoads++;
      if(action==='planar-start-tracking')window.__startedPair=value.id;
      if(action==='planar-start-history'||action==='planar-extend-history')window.__startedHistory=value.id;
      return value;};}`);
  const loadFile=async(filename)=>{
    await instrument();const before=await ev('__trackingLoads');
    await ev('$("tracking-open").value=""');
    const {root}=await call('DOM.getDocument',{},sessionId);
    const {nodeId}=await call('DOM.querySelector',{nodeId:root.nodeId,selector:'#tracking-open'},sessionId);
    await call('DOM.setFileInputFiles',{nodeId,files:[]},sessionId);
    await call('DOM.setFileInputFiles',{nodeId,files:[resolve(filename)]},sessionId);
    await wait(`__trackingLoads>${before}`,120000);
  };
  const download=async(name)=>{for(let n=0;n<300;n++){try{return await readFile(out+'/downloads/'+name);}catch{}await sleep(100);}throw Error('missing download '+name);};
  const saveRequest=async(name)=>{
    await click('#tracking-save');const file=await download('planar-tracking-request.json');
    const value=JSON.parse(file);await rename(out+'/downloads/planar-tracking-request.json',out+'/'+name);
    return value;
  };
  const execute=async(button,history=false)=>{
    await instrument();const variable=history?'__startedHistory':'__startedPair';
    await ev(`${variable}=null`);await click(button);await wait(`${variable}!==null`,180000);
    const identifier=await ev(variable);
    await wait(`document.querySelector('[data-job="${identifier}"] strong')?.textContent.startsWith('complete')`,600000);
    await click(`[data-job="${identifier}"] > button`);
    await wait(`${history?'selectedHistory':'selectedTracking'}===${JSON.stringify(identifier)}`,600000);
    return identifier;
  };
  const screenshot=async(selector,name)=>{
    await ev(`document.querySelector(${JSON.stringify(selector)}).scrollIntoView({block:'start',behavior:'instant'})`);
    const shot=await call('Page.captureScreenshot',{format:'png'},sessionId);
    await writeFile(out+'/'+name,Buffer.from(shot.data,'base64'));
  };
  const render=async()=>{
    await click('#history-source');await wait('selected!==null && project.case.schema_version===2',180000);
    report.imported_job=await ev('selected');
    await click('#plot');await wait('!$("image").hidden && $("image").naturalWidth>100',180000);
    await check('owned final original field retains per-length RF and renders',
      '$("quantities").textContent.includes("J/m") && $("na").textContent.includes("N/A")');
    await screenshot('#result','history-field.png');
  };
  if(args['--resume-report']){
    const previous=JSON.parse(await readFile(args['--resume-report'],'utf8'));
    report.final_history=previous.final_history;
    await call('Page.navigate',{url:launch.origin+'/planar.html?job='+report.final_history},sessionId);
    await wait(`typeof selectedHistory!=='undefined' && selectedHistory===${JSON.stringify(report.final_history)}`,600000);
    await check('new server physically replays all three owned newer pairs',
      'currentHistory.result.status==="PASS" && currentHistory.result.steps.length===3 && JSON.stringify(currentHistory.result.steps.map(s=>s.request.tracking_version))==="[9,10,10]" && currentHistory.result.current_mode_ids[0]==="first"');
    await check('compact chart summaries retain all rows without page overflow',
      '$("history-steps").classList.contains("planar-history-steps") && getComputedStyle($("history-steps").querySelector("table")).tableLayout==="fixed" && $("history-steps").querySelectorAll("details").length===3 && [...$("history-steps").querySelectorAll("details")].every(d=>!d.open) && document.documentElement.scrollWidth<=innerWidth');
    await screenshot('#history-result','compact-history.png');
    await click('#history-steps details summary');
    if(!isDeepStrictEqual(await ev('JSON.parse($("history-steps").querySelector("pre").textContent)'),await ev('currentHistory.result.steps[0].request.mapping')))throw Error('expanded declaration differs');
    await check('expanded declaration preserves every SI point and remains within viewport',
      '$("history-steps").querySelector("details").open && document.documentElement.scrollWidth<=innerWidth');
    await screenshot('#history-result','expanded-chart.png');
    await click('#history-steps details summary');
    if(!args['--layout-only']){
    await render();
    await click('#history-use-groups');await wait('$("tracking-ids").value==="null"');
    await check('new server preserves original law when inheriting final ID groups',
      'trackingFromForm().tracking_version===10 && trackingFromForm().mapping.name==="polynomial_piecewise_xy_reference" && trackingFromForm().mapping.current_refinements===1 && trackingFromForm().previous_identity_groups[0].ids[0]==="first"');
    await screenshot('#tracking-mapping','restored-law.png');
    }
  }else{
    const fixture=JSON.parse(await readFile(args['--fixture'],'utf8'));
    const fixtureRoot=resolve(args['--fixture'],'..');
    if(args['--continue-report']){
      const previous=JSON.parse(await readFile(args['--continue-report'],'utf8'));
      if(!previous.error?.includes('anchor must declare resolved individual IDs')||previous.source_changed_during_run)throw Error('unexpected prior failure');
      if(!isDeepStrictEqual(previous.source_sha256,report.source_sha256))throw Error('continuation source changed');
      report.prior_report=resolve(args['--continue-report']);report.prior_successful_checks=previous.checks;
      for(const key of ['pair9','pair10','first_history','second_history'])report[key]=previous[key];
      await call('Page.navigate',{url:launch.origin+'/planar.html?job='+report.second_history},sessionId);
      await wait(`typeof selectedHistory!=='undefined' && selectedHistory===${JSON.stringify(report.second_history)}`,600000);
      await check('saved partial history replays newer requests and final individual ID',
        'currentHistory.result.steps.length===2 && JSON.stringify(currentHistory.result.steps.map(s=>s.request.tracking_version))==="[9,10]" && currentHistory.result.current_mode_ids[0]==="first"');
    }else{
    await loadFile(fixtureRoot+'/request9.json');
    if(!isDeepStrictEqual(await ev('trackingFromForm()'),fixture.request9))throw Error('request9 form loses declaration');
    if(!isDeepStrictEqual(await saveRequest('request9-saved.json'),fixture.request9))throw Error('request9 save differs');
    await fill('#tracking-ids','["changed"]');await loadFile(out+'/request9-saved.json');
    await check('explicit piecewise request9 keeps SI partitions through save and reload',
      `trackingFromForm().tracking_version===9 && !$("tracking-polynomial-options").hidden && $("tracking-polygon-options").hidden && $("tracking-ids").value==='["first"]'`);
    const before=await ev('document.querySelector("#jobs .job")?.dataset.job');
    const mapping=JSON.stringify(fixture.request9.mapping);
    await fill('#tracking-polynomial-mapping',mapping.replace('"mapping_version":1','"mapping_version":1,"mapping_version":1'));
    await click('#tracking-save');await wait('!$("error").hidden && $("error").textContent.includes("duplicate")');
    await check('raw duplicate declaration reaches strict server without allocating job',
      `document.querySelector('#jobs .job')?.dataset.job===${JSON.stringify(before)}`);
    await loadFile(out+'/request9-saved.json');
    await ev(`$('tracking-previous').value=${JSON.stringify(fixture.ids[0])};$('tracking-current').value=${JSON.stringify(fixture.ids[1])}`);
    report.pair9=await execute('#tracking-start');
    await check('actual owned request9 pair follows the original electric field',
      'currentTracking.request.tracking_version===9 && currentTracking.result.status==="PASS" && currentTracking.result.current_mode_ids[0]==="first"');
    await click('#history-select-tracking');report.first_history=await execute('#history-start',true);
    await check('history owns the complete explicit chart and original ID',
      'currentHistory.result.status==="PASS" && currentHistory.result.steps[0].request.tracking_version===9 && currentHistory.result.current_mode_ids[0]==="first"');
    await click('#tracking-use-groups');await wait('$("tracking-ids").value==="null"');
    await check('pair continuation retains chart and ID group',
      'trackingFromForm().tracking_version===9 && trackingFromForm().previous_identity_groups[0].ids[0]==="first"');
    const previous=await ev('$("tracking-previous").value');
    await loadFile(fixtureRoot+'/grouped-request10.json');
    if(!isDeepStrictEqual(await saveRequest('request10-saved.json'),fixture.request10))throw Error('request10 save differs');
    await loadFile(out+'/request10-saved.json');
    await check('original piecewise law and both trial values survive request10 roundtrip',
      'trackingFromForm().tracking_version===10 && trackingFromForm().mapping.previous_value===1 && trackingFromForm().mapping.current_value===.5 && trackingFromForm().previous_identity_groups[0].ids[0]==="first"');
    await ev(`$('tracking-previous').value=${JSON.stringify(previous)};$('tracking-current').value=${JSON.stringify(fixture.ids[2])}`);
    report.pair10=await execute('#tracking-start');
    await check('actual original-reference pair10 preserves inherited individual ID',
      'currentTracking.request.tracking_version===10 && currentTracking.result.status==="PASS" && currentTracking.result.current_mode_ids[0]==="first"');
    await ev(`$('history-next').value=${JSON.stringify(report.pair10)}`);
    report.second_history=await execute('#history-extend',true);
    await check('owned history preserves explicit and original-reference charts in order',
      'currentHistory.result.steps.length===2 && JSON.stringify(currentHistory.result.steps.map(s=>s.request.tracking_version))==="[9,10]" && currentHistory.result.current_mode_ids[0]==="first"');
    }
    await click('#history-use-groups');await wait('$("tracking-ids").value==="null"');
    await check('history continuation retains original Project law and ID group',
      'trackingFromForm().tracking_version===10 && trackingFromForm().mapping.current_value===.5 && trackingFromForm().previous_identity_groups[0].ids[0]==="first"');
    await fill('#tracking-polynomial-mapping',JSON.stringify(fixture.final_request10.mapping));
    await ev(`$('tracking-current').value=${JSON.stringify(fixture.ids[3])}`);
    await fill('#tracking-ids','["first"]');await fill('#tracking-groups','null');
    await click('#history-result > details > summary');
    await fill('#history-recovery-anchor',2);
    await click('#history-recovery-from-tracking');
    await wait('JSON.parse($("history-recovery-request").value)?.comparison?.mapping?.current_refinements===1',120000);
    await check('explicit recovery form preserves request10 declarations',
      'JSON.parse($("history-recovery-request").value).comparison.tracking_version===10 && JSON.parse($("history-recovery-request").value).anchor_snapshot_index===2');
    await fill('#tracking-ids','null');await fill('#tracking-groups',JSON.stringify(fixture.final_request10.previous_identity_groups));
    report.final_pair=await execute('#tracking-start');
    await check('original-reference fine-mesh continuation verifies the inherited ID',
      'currentTracking.result.status==="PASS" && currentTracking.result.current_mode_ids[0]==="first" && currentTracking.request.mapping.current_refinements===1');
    await ev(`$('history-next').value=${JSON.stringify(report.final_pair)}`);
    report.final_history=await execute('#history-extend',true);
    await check('three-step owned history retains requests and final individual ID',
      'currentHistory.result.status==="PASS" && currentHistory.result.steps.length===3 && currentHistory.result.individual_ids_complete');
    await click('#history-result-save');const history=JSON.parse(await download('planar-history-results.json'));
    if(!isDeepStrictEqual(history,await ev('currentHistory.result')))throw Error('history result export differs');
    await writeFile(out+'/history-result.json',JSON.stringify(history,null,2)+'\n');
    await screenshot('#history-result','history-result.png');await render();
    await call('Page.navigate',{url:launch.origin+'/planar.html?job='+report.final_history},sessionId);
    await wait(`typeof selectedHistory!=='undefined' && selectedHistory===${JSON.stringify(report.final_history)}`,600000);
    await check('URL restoration replays every owned chart and final ID',
      'currentHistory.result.steps.length===3 && currentHistory.result.current_mode_ids[0]==="first"');
  }
  report.source_changed_during_run=!isDeepStrictEqual(report.source_sha256,await sourceHashes());
  report.passed=!report.source_changed_during_run&&report.external_requests.length===0;
  if(!report.passed)throw Error('source or external HTTP changed');
  console.log(JSON.stringify({passed:true,checks:report.checks}));
} catch(e){report.error=String(e);process.exitCode=1;console.error(e);}
finally {
  try {
    await writeFile(out + "/report.json", JSON.stringify(report, null, 2));
  } finally {
    for (const entry of pending.values()) clearTimeout(entry.timer);
    try { ws?.close(); } finally { await dispose(); }
  }
}
