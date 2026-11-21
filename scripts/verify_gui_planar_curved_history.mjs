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
  const fixture=JSON.parse(await readFile(args['--request'],'utf8'));
  const snapshot=async(directory)=>{const result={};for(const entry of await readdir(directory,{withFileTypes:true})){if(entry.name==='worker.log')continue;const path=directory+'/'+entry.name;if(entry.isDirectory())for(const [k,v] of Object.entries(await snapshot(path)))result[entry.name+'/'+k]=v;else if(entry.isFile())result[entry.name]=createHash('sha256').update(await readFile(path)).digest('hex');}return result;};
  const workspace=resolve(args['--workspace']);
  const jobState=async(id)=>JSON.parse(await readFile(workspace+'/'+id+'/job.json','utf8'));
  const poll=async(fn,label,ms=240000)=>{const start=performance.now();while(performance.now()-start<ms){if(await fn())return;await sleep(100);}throw Error('file-state timeout: '+label);};
  const selectValue=async(selector,value)=>ev(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});e.value=${JSON.stringify(value)};e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));})()`);
  const openJob=async(id,type)=>{const selector=`[data-job="${id}"] button`;await wait(`document.querySelector(${JSON.stringify(selector)})?.textContent==='結果を開く'`,240000);await click(selector);await wait(`document.querySelector('#${type}-selection').textContent.includes(${JSON.stringify(id)}) && !document.querySelector('#${type}-result').hidden`,240000);};
  const submitted=async(prefix)=>{await wait(`document.querySelector('#dirty').textContent.startsWith(${JSON.stringify(prefix)})`,240000);return (await ev('document.querySelector("#dirty").textContent')).split(': ').at(-1);};
  const pairStart=async(index,prev,next)=>{await fill('#comparison',JSON.stringify(fixture.requests[index]));await selectValue('#previous',fixture.native_ids[prev]);await selectValue('#current',fixture.native_ids[next]);await click('#comparison-start');return submitted('比較投入済み: ');};
  if(args['--history-render-only']){
    await openJob(args['--extended-history'],'history');
    await ev('document.querySelector("#history-details").parentElement.open=true');
    await check('unresolved historical IDs are explicit and complete expanded diagnostics remain scrollable','document.querySelector("#history-steps").textContent.includes("未確定, 未確定") && historyResult.result.steps[0].current_mode_ids.every(v=>v===null) && document.querySelector("#history-details").getBoundingClientRect().height<=parseFloat(getComputedStyle(document.querySelector("#history-details")).maxHeight)+1 && getComputedStyle(document.querySelector("#history-details")).overflowY==="auto"');
    await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true},sessionId).then(r=>writeFile(out+'/curved-history.png',Buffer.from(r.data,'base64')));
  }else{
  let extended;
  if(!args['--extended-history']){
  await wait(`document.querySelector('#previous option[value="${fixture.native_ids[0]}"]')`,240000);
  if(!args['--direct-pair']){
  await fill('#comparison',JSON.stringify(fixture.requests[0]));await click('#comparison-save');
  if(!isDeepStrictEqual(JSON.parse(await saved('planar-curved-tracking-request.json')),fixture.requests[0]))throw Error('comparison request save differs');
  await loadFile('#comparison-open',out+'/downloads/planar-curved-tracking-request.json');await wait('document.querySelector("#dirty").textContent==="条件を復元しました"');
  await check('real comparison request save and file reload preserve quadratic charts, E/H controls and original IDs',`JSON.stringify(JSON.parse(document.querySelector('#comparison').value))===${JSON.stringify(JSON.stringify(fixture.requests[0]))}`);
  const cancelled=await pairStart(0,0,2);report.cancelled_job=cancelled;
  await poll(async()=>{const state=await jobState(cancelled);return state.status==='running';},'actual running comparison');
  const claim=JSON.parse(await readFile(workspace+'/'+cancelled+'/worker.claim','utf8'));report.cancelled_worker_claim=claim;
  await click(`[data-job="${cancelled}"] button`);
  await poll(async()=> (await jobState(cancelled)).status==='cancelled','cancelled comparison');
  report.checks.push({operation:'real GUI cancels an actual running curved comparison worker',passed:true});
  }
  const direct=args['--direct-pair']||await pairStart(0,0,2);report.direct_pair=direct;await openJob(direct,'comparison');
  if(!args['--resume-after-pair']){
  await check('new comparison after cancellation retains real TE parity rank exchange and separate E/H assignment','pair.result.status==="PASS" && pair.result.individual_ids_complete && pair.result.current_mode_ids[0]==="even-x" && pair.result.current_mode_ids[1]==="odd-x" && document.querySelector("#comparison-matches").textContent.includes("even-x")');
  }
  const pairBytes=await snapshot(workspace+'/'+direct);
  if(!args['--resume-after-pair']){
  await click('#comparison-result-save');const downloadedPair=JSON.parse(await saved('planar-curved-tracking-results.json'));
  const originalPair=JSON.parse(await readFile(workspace+'/'+direct+'/execution/tracking-results.json','utf8'));
  if(!isDeepStrictEqual(downloadedPair,originalPair))throw Error('pair result download differs');
  report.checks.push({operation:'real comparison result download preserves full original E/H, guard and phase diagnostics',passed:true});
  }
  for(const [side,index] of [['previous',0],['current',2]]){
    const previousHref=await ev('document.querySelector("#field-link").href');
    await click('#'+side+'-field');await wait(`document.querySelector('#field-link').href.includes('?job=') && document.querySelector('#field-link').href!==${JSON.stringify(previousHref)}`,240000);
    const id=new URL(await ev('document.querySelector("#field-link").href')).searchParams.get('job');
    const files=await snapshot(workspace+'/'+id+'/solution');if(!isDeepStrictEqual(files,fixture.original_native_sha256[index]))throw Error('original native differs: '+side);
  }
  if(!isDeepStrictEqual(pairBytes,await snapshot(workspace+'/'+direct)))throw Error('pair parent changed during original imports');
  report.checks.push({operation:'both GUI comparison source imports preserve all original five native bytes and immutable parent',passed:true});
  const p0=await pairStart(1,0,1);await openJob(p0,'comparison');
  await check('true circle doublet continues the inherited set while keeping individual identities unresolved','pair.result.status==="PASS" && !pair.result.individual_ids_complete && pair.result.current_mode_ids.every(v=>v===null)');
  const p1=await pairStart(2,1,2);await openJob(p1,'comparison');report.history_pairs=[p0,p1];
  await fill('#history-request',JSON.stringify(fixture.history));await click('#history-save');
  if(!isDeepStrictEqual(JSON.parse(await saved('planar-curved-history-request.json')),fixture.history))throw Error('history request download differs');
  await loadFile('#history-open',out+'/downloads/planar-curved-history-request.json');await wait('document.querySelector("#dirty").textContent==="条件を復元しました"');
  await fill('#history-ids',JSON.stringify([p0,p1]));await click('#history-start');const history=await submitted('履歴投入済み: ');report.unresolved_history=history;await openJob(history,'history');
  await check('actual GUI builds ordered native-continuous history without inventing individual IDs','historyResult.result.status==="PASS" && historyResult.result.steps.length===2 && historyResult.result.current_mode_ids.every(v=>v===null) && !document.querySelector("#history-recover").disabled');
  const historyBytes=await snapshot(workspace+'/'+history);
  await fill('#recovery',JSON.stringify(fixture.recovery));await click('#recovery-save');
  if(!isDeepStrictEqual(JSON.parse(await saved('planar-curved-recovery-request.json')),fixture.recovery))throw Error('recovery request download differs');
  await loadFile('#recovery-open',out+'/downloads/planar-curved-recovery-request.json');await wait('document.querySelector("#dirty").textContent==="条件を復元しました"');
  await click('#history-recover');const recovered=await submitted('回復履歴投入済み: ');report.recovered_history=recovered;await openJob(recovered,'history');
  await check('actual GUI recovers rank-exchanged individual IDs from the declared real past anchor','historyResult.result.status==="PASS" && historyResult.result.individual_ids_complete && historyResult.result.current_mode_ids[0]==="even-x" && historyResult.result.current_mode_ids[1]==="odd-x" && historyResult.result.identity_recoveries.length===1 && document.querySelector("#history-recover").disabled');
  if(!isDeepStrictEqual(historyBytes,await snapshot(workspace+'/'+history)))throw Error('unresolved parent history changed');
  const p2=await pairStart(3,2,3);report.next_pair=p2;await openJob(p2,'comparison');
  await openJob(recovered,'history');await selectValue('#next-pair',p2);await click('#history-extend');extended=await submitted('延長履歴投入済み: ');report.extended_history=extended;await openJob(extended,'history');
  await check('actual GUI extends recovered identity chain and stops at explicit max_steps','historyResult.result.steps.length===3 && historyResult.result.individual_ids_complete && !historyResult.result.can_extend && document.querySelector("#history-extend").disabled');
  await click('#history-result-save');const historyFile=JSON.parse(await saved('planar-curved-history-results.json'));
  const originalHistory=JSON.parse(await readFile(workspace+'/'+extended+'/execution/history-results.json','utf8'));
  if(!isDeepStrictEqual(historyFile,originalHistory))throw Error('history result download differs');
  report.checks.push({operation:'GUI history download preserves inherited original comparisons, anchor recovery and all IDs',passed:true});
  }else{extended=args['--extended-history'];report.extended_history=extended;report.reused_actual_extended_history=true;await openJob(extended,'history');}
  const extendedBytes=await snapshot(workspace+'/'+extended);
  const oldFieldHref=await ev('document.querySelector("#field-link").href');
  await click('#history-field');await wait(`document.querySelector('#field-link').href.includes('?job=') && document.querySelector('#field-link').href!==${JSON.stringify(oldFieldHref)}`,240000);
  const imported=new URL(await ev('document.querySelector("#field-link").href')).searchParams.get('job');report.imported_last_source=imported;
  if(!isDeepStrictEqual(await snapshot(workspace+'/'+imported+'/solution'),fixture.original_native_sha256[3]))throw Error('last history native import differs');
  if(!isDeepStrictEqual(extendedBytes,await snapshot(workspace+'/'+extended)))throw Error('extended parent changed');
  await ev('document.querySelector("#history-details").parentElement.open=true');
  const diagnosticBounds=await ev('(()=>{const e=document.querySelector("#history-details"),s=getComputedStyle(e);return {height:e.getBoundingClientRect().height,maxHeight:parseFloat(s.maxHeight),overflow:s.overflowY,scrollHeight:e.scrollHeight}})()');
  if(!Number.isFinite(diagnosticBounds.maxHeight)||diagnosticBounds.height>diagnosticBounds.maxHeight+1||diagnosticBounds.overflow!=="auto")throw Error('expanded complete history diagnostics have no bounded scroll area');
  report.diagnostic_bounds=diagnosticBounds;
  await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true},sessionId).then(r=>writeFile(out+'/curved-history.png',Buffer.from(r.data,'base64')));
  report.checks.push({operation:'history source field import preserves actual final native and all parent bytes',passed:true});
  await click('#field-link');await wait(`typeof selected!=='undefined' && selected===${JSON.stringify(imported)}`,240000);
  await check('history original source opens native Cartesian RF with SI per-length conventions and two named R/Q N/A','project.case.schema_version===3 && document.querySelector("#quantities").textContent.includes("J/m") && document.querySelector("#na").textContent.includes("加速器定義・回路定義")');
  await click('#plot');await wait('!document.querySelector("#image").hidden && document.querySelector("#image").naturalWidth>0',240000);
  await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true},sessionId).then(r=>writeFile(out+'/original-history-field.png',Buffer.from(r.data,'base64')));
  report.checks.push({operation:'actual final original history field renders after real GUI recovery and extension',passed:true});
  }
  report.source_changed_during_run=!isDeepStrictEqual(report.source_sha256,await sourceHashes());report.passed=!report.source_changed_during_run&&report.external_requests.length===0;
  if(!report.passed)throw Error('source or external request guard failed');console.log(JSON.stringify({passed:report.passed,checks:report.checks}));
}catch(e){report.error=String(e);process.exitCode=1;console.error(e);}
finally{try{await writeFile(out+'/report.json',JSON.stringify(report,null,2));}finally{for(const entry of pending.values())clearTimeout(entry.timer);try{ws?.close();}finally{await dispose();}}}
