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
    "Usage: node scripts/verify_gui_planar_curved.mjs --url LAUNCH_URL --out NEW_DIRECTORY --fixtures REFERENCES --workspace GUI_WORKSPACE",
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

  const launch=new URL(args['--url']);launch.pathname='/planar.html';
  const fixtures=resolve(args['--fixtures']),workspace=resolve(args['--workspace']);
  await call('Page.navigate',{url:launch.href},sessionId);
  await wait('document.querySelector("#width")?.value==="310"');
  const check=async(operation,expression)=>{if(!await ev(expression))throw Error(operation);report.checks.push({operation,passed:true});};
  const loadFile=async(selector,filename)=>{const {root}=await call('DOM.getDocument',{},sessionId);const {nodeId}=await call('DOM.querySelector',{nodeId:root.nodeId,selector},sessionId);await call('DOM.setFileInputFiles',{nodeId,files:[resolve(filename)]},sessionId);};
  let downloadRoot;
  const readDownload=async(name)=>{for(let n=0;n<300;n++){try{return await readFile(downloadRoot+'/'+name);}catch{}await sleep(100);}throw Error('download absent: '+name);};
  const runAndOpen=async()=>{const previous=await ev('document.querySelector("#jobs .job")?.dataset.job');await click('#start');await wait(`document.querySelector('#jobs .job')?.dataset.job!==${JSON.stringify(previous)} && document.querySelector('#jobs .job button')?.textContent==='結果を開く' && !document.querySelector('#jobs .job button').disabled`,90000);const next=await ev('document.querySelector("#jobs .job").dataset.job');await click('#jobs .job button');await wait(`selected===${JSON.stringify(next)} && !document.querySelector('#result').hidden`);return next;};
  report.curved_jobs={};report.reference_native_sha256={};
  for(const pol of ['te','tm']){
    const expected=JSON.parse(await readFile(fixtures+'/'+pol+'-reference.json','utf8'));
    const input=JSON.parse(await readFile(fixtures+'/'+pol+'-project.json','utf8'));
    const native=fixtures+'/'+pol+'-native';
    const before={};for(const name of await readdir(native))before[name]=createHash('sha256').update(await readFile(native+'/'+name)).digest('hex');
    report.reference_native_sha256[pol]=before;
    downloadRoot=out+'/'+pol+'-downloads';await mkdir(downloadRoot);
    await call('Browser.setDownloadBehavior',{behavior:'allow',downloadPath:downloadRoot});
    await loadFile('#open',fixtures+'/'+pol+'-project.json');
    await wait(`project.case.schema_version===3 && project.case.model.polarization===${JSON.stringify(pol)}`);
    await check('curved '+pol+' form retains original map and fixed P2 choice', 'document.querySelector("#rectangle").hidden && document.querySelector("#polygon-note").hidden && !document.querySelector("#curved-note").hidden && document.querySelector("#order").disabled && document.querySelector("#order").value==="2" && JSON.stringify(documentFromForm())===JSON.stringify(project)');
    await ev('document.querySelector("#unit").value="m";document.querySelector("#unit").dispatchEvent(new Event("change"))');
    await wait('project.display_length_unit==="m"');
    if(!isDeepStrictEqual(await ev('documentFromForm().case'),input.case))throw Error('display unit changed original curved map or numerics');
    await click('#save');const saved=JSON.parse(await readDownload('planar-project.json'));
    if(!isDeepStrictEqual(saved,{...input,display_length_unit:'m'}))throw Error('curved Project save changed inputs');
    await click('#new');await wait('project.case.schema_version===1');
    await loadFile('#open',downloadRoot+'/planar-project.json');await wait('project.case.schema_version===3');
    report.curved_jobs[pol]=await runAndOpen();
    if(!isDeepStrictEqual(await ev('result'),expected.result))throw Error(pol+' GUI RF differs from independent original API');
    await check(pol+' per-length units and both R/Q N/A','document.querySelector("#quantities").textContent.includes("J/m") && document.querySelector("#quantities").textContent.includes("W/m") && document.querySelector("#na").textContent.includes("加速器定義・回路定義")');
    const names=await ev('[...document.querySelectorAll("#files button")].map(b=>b.textContent)');
    for(let i=0;i<names.length;i++){await click(`#files button:nth-child(${i+1})`);const raw=await readDownload(names[i]);if(!raw.equals(await readFile(native+'/'+names[i])))throw Error('GUI native bytes differ: '+pol+'/'+names[i]);}
    report.checks.push({operation:pol+' GUI native all five files exactly match independent API',passed:true});
    await ev('document.querySelector("#mode").value="2";document.querySelector("#mode").dispatchEvent(new Event("change"))');
    await fill('#points',JSON.stringify(expected.points_xy_m));await click('#probe');await click('#probe-meta');
    const csv=(await readDownload('planar-probe.csv')).toString(),lines=csv.trim().split(/\r?\n/),headers=lines[0].split(','),rows=lines.slice(1).map(line=>line.split(',').map(Number));
    for(const [name,values] of Object.entries(expected.fields))if(!isDeepStrictEqual(rows.map(row=>row[headers.indexOf(name)]),values))throw Error('GUI signed original field differs: '+name);
    const metadata=JSON.parse(await readDownload('planar-probe.csv.json'));
    if(!isDeepStrictEqual(metadata.quantities,expected.result.modes[1])||!isDeepStrictEqual(metadata.native_sha256,before))throw Error('probe RF/native binding differs');
    report.checks.push({operation:pol+' GUI original-point all 12 signed SI components and full RF binding',passed:true});
    await click('#plot');await wait('!document.querySelector("#image").hidden && document.querySelector("#image").naturalWidth>100',90000);
    await ev('document.querySelector("#image").scrollIntoView({block:"center"})');const screenshot=await call('Page.captureScreenshot',{format:'png'},sessionId);await writeFile(out+'/'+pol+'-fields.png',Buffer.from(screenshot.data,'base64'));
    await fill('#points','[[1,1]]');await click('#probe');await wait('!document.querySelector("#error").hidden');
    report.checks.push({operation:pol+' curved-wall original field plot and exterior probe rejection',passed:true});
    // Imports preserve source coefficients; rerun is a separate new worker.
    for(const source of [native,workspace+'/'+report.curved_jobs[pol]]){
      const previous=await ev('selected');await fill('#import-path',source);await click('#import');await wait(`selected!==${JSON.stringify(previous)} && project.case.schema_version===3 && document.querySelector('#error').hidden`,30000);
      if(!isDeepStrictEqual(await ev('result'),expected.result))throw Error('curved import changed RF');
    }
    report.rerun_job=await runAndOpen();if(!isDeepStrictEqual(await ev('result'),expected.result))throw Error('curved rerun changed RF');
    for(const [name,hash] of Object.entries(before))if(createHash('sha256').update(await readFile(native+'/'+name)).digest('hex')!==hash)throw Error('reference native changed');
    report.checks.push({operation:pol+' direct/managed import, new rerun and original native preservation',passed:true});
  }
  await fill('#study-values','[1,2]');await ev('document.querySelector("#study-parameter").value="uniform_scale"');
  const beforeStudy=await ev('document.querySelector("#jobs .job")?.dataset.job');
  await click('#study-start');await wait(`document.querySelector('#jobs .job')?.dataset.job!==${JSON.stringify(beforeStudy)} && document.querySelector('#jobs .job button')?.textContent==='結果を開く' && !document.querySelector('#jobs .job button').disabled`,90000);report.study_job=await ev('document.querySelector("#jobs .job").dataset.job');await click('#jobs .job button');await wait('currentStudy!==null && !document.querySelector("#study-result").hidden');
  const sweep=await ev('currentStudy.result');
  for(let i=0;i<sweep.points[0].modes.length;i++){const a=sweep.points[0].modes[i],b=sweep.points[1].modes[i];if(Math.abs(b.frequency_hz*2/a.frequency_hz-1)>1e-10||Math.abs(b.geometry_factor_ohm/a.geometry_factor_ohm-1)>1e-10||Math.abs(b.q0/a.q0/Math.sqrt(2)-1)>1e-10)throw Error('GUI sweep scale invariant');}
  report.checks.push({operation:'curved independent Study actual two-scale f/Q/G invariants',passed:true});
  await loadFile('#open',fixtures+'/cancel-project.json');await wait('project.case.geometry.domain.cell_nodes.length===1024');
  await click('#start');await wait('document.querySelector("#jobs .job button")?.textContent==="中止"');report.cancelled_job=await ev('document.querySelector("#jobs .job").dataset.job');await click('#jobs .job button');await wait('document.querySelector("#jobs .job strong")?.textContent.startsWith("cancelled")',30000);
  await loadFile('#open',fixtures+'/tm-project.json');await wait('project.case.geometry.domain.cell_nodes.length===16');report.after_cancel_job=await runAndOpen();
  report.checks.push({operation:'actual curved worker cancellation and new-job restart',passed:true});
  await call('Page.navigate',{url:launch.origin+'/planar.html?job='+report.curved_jobs.tm},sessionId);await wait(`typeof selected!=='undefined' && selected===${JSON.stringify(report.curved_jobs.tm)}`);
  await check('persistent curve Project/result page reload','project.case.schema_version===3 && document.querySelector("#order").disabled && result.modes.length===4');
  report.source_changed_during_run=!isDeepStrictEqual(report.source_sha256,await sourceHashes());report.passed=!report.source_changed_during_run&&report.external_requests.length===0;
  if(!report.passed)throw Error('source/external request check failed');console.log(JSON.stringify({passed:report.passed,checks:report.checks}));
} catch(e){report.error=String(e);process.exitCode=1;console.error(e);}
finally {
  try {
    await writeFile(out + "/report.json", JSON.stringify(report, null, 2));
  } finally {
    for (const entry of pending.values()) clearTimeout(entry.timer);
    try { ws?.close(); } finally { await dispose(); }
  }
}
