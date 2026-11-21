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
    "Usage: node scripts/verify_gui_planar_curved_replay.mjs --url NEW_SERVER_URL --out NEW_DIRECTORY --fixtures REFERENCES --report FIRST_BROWSER_REPORT",
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
  const fixtures=resolve(args['--fixtures']),original=JSON.parse(await readFile(args['--report'],'utf8'));
  if(!original.passed)throw Error('original curved browser report must have passed');
  await call('Page.navigate',{url:launch.href},sessionId);await wait('document.querySelector("#width")?.value==="310"');
  const check=async(operation,expression)=>{if(!await ev(expression))throw Error(operation);report.checks.push({operation,passed:true});};
  const loadFile=async(filename)=>{const {root}=await call('DOM.getDocument',{},sessionId);const {nodeId}=await call('DOM.querySelector',{nodeId:root.nodeId,selector:'#open'},sessionId);await call('DOM.setFileInputFiles',{nodeId,files:[resolve(filename)]},sessionId);};
  let downloadRoot;
  const readDownload=async(name)=>{for(let n=0;n<300;n++){try{return await readFile(downloadRoot+'/'+name);}catch{}await sleep(100);}throw Error('download absent: '+name);};
  report.original_report_sha256=createHash('sha256').update(await readFile(args['--report'])).digest('hex');
  for(const pol of ['te','tm']){
    const expected=JSON.parse(await readFile(fixtures+'/'+pol+'-reference.json','utf8'));
    const id=original.curved_jobs[pol];
    await call('Page.navigate',{url:launch.origin+'/planar.html?job='+id},sessionId);
    await wait(`typeof selected!=='undefined' && selected===${JSON.stringify(id)} && !document.querySelector('#result').hidden`,60000);
    if(!isDeepStrictEqual(await ev('result'),expected.result))throw Error('restarted server changed original RF');
    await check(pol+' original curved Project and fixed P2 restored after server restart','project.case.schema_version===3 && document.querySelector("#order").disabled && documentFromForm().case.numerics.quadrature_order===project.case.numerics.quadrature_order');
    downloadRoot=out+'/'+pol+'-downloads';await mkdir(downloadRoot);await call('Browser.setDownloadBehavior',{behavior:'allow',downloadPath:downloadRoot});
    const names=await ev('[...document.querySelectorAll("#files button")].map(b=>b.textContent)');
    for(let i=0;i<names.length;i++){await click(`#files button:nth-child(${i+1})`);const raw=await readDownload(names[i]);if(!raw.equals(await readFile(fixtures+'/'+pol+'-native/'+names[i])))throw Error('native replay bytes differ');if(createHash('sha256').update(raw).digest('hex')!==original.reference_native_sha256[pol][names[i]])throw Error('original native binding differs');}
    report.checks.push({operation:pol+' original all five native bytes and full RF preserved after server restart',passed:true});
  }
  await call('Page.navigate',{url:launch.origin+'/planar.html?job='+original.study_job},sessionId);
  await wait(`typeof selectedStudy!=='undefined' && selectedStudy===${JSON.stringify(original.study_job)}`,60000);
  const sweep=await ev('currentStudy.result');
  for(let i=0;i<sweep.points[0].modes.length;i++){const a=sweep.points[0].modes[i],b=sweep.points[1].modes[i];if(Math.abs(b.frequency_hz*2/a.frequency_hz-1)>1e-10||Math.abs(b.geometry_factor_ohm/a.geometry_factor_ohm-1)>1e-10)throw Error('replayed Study covariance');}
  report.checks.push({operation:'owned curved Study fully replays after server restart',passed:true});
  await check('cancelled curved job stays cancelled after server restart',`[...document.querySelectorAll('#jobs .job')].some(row=>row.dataset.job===${JSON.stringify(original.cancelled_job)} && row.querySelector('strong').textContent.startsWith('cancelled') && row.querySelector('button').disabled)`);
  await loadFile(fixtures+'/tm-project.json');await wait('project.case.schema_version===3');
  const previous=await ev('document.querySelector("#jobs .job")?.dataset.job');await click('#start');
  await wait(`document.querySelector('#jobs .job')?.dataset.job!==${JSON.stringify(previous)} && document.querySelector('#jobs .job button')?.textContent==='結果を開く' && !document.querySelector('#jobs .job button').disabled`,90000);
  report.restarted_job=await ev('document.querySelector("#jobs .job").dataset.job');await click('#jobs .job button');await wait(`selected===${JSON.stringify(report.restarted_job)}`);
  const expected=JSON.parse(await readFile(fixtures+'/tm-reference.json','utf8'));
  if(!isDeepStrictEqual(await ev('result'),expected.result))throw Error('new server worker changed original RF');
  report.checks.push({operation:'new curved worker completes on restarted server with full original RF',passed:true});
  report.source_changed_during_run=!isDeepStrictEqual(report.source_sha256,await sourceHashes());report.passed=!report.source_changed_during_run&&report.external_requests.length===0;
  if(!report.passed)throw Error('source/external request check failed');console.log(JSON.stringify({passed:true,checks:report.checks}));
} catch(e){report.error=String(e);process.exitCode=1;console.error(e);}
finally {
  try {
    await writeFile(out + "/report.json", JSON.stringify(report, null, 2));
  } finally {
    for (const entry of pending.values()) clearTimeout(entry.timer);
    try { ws?.close(); } finally { await dispose(); }
  }
}
