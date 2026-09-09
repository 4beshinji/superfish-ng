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
  const check=async(operation,expression)=>{if(!await ev(expression))throw Error(operation);report.checks.push({operation,passed:true});};
  const loadFile=async(selector,filename)=>{const {root}=await call('DOM.getDocument',{},sessionId);const {nodeId}=await call('DOM.querySelector',{nodeId:root.nodeId,selector},sessionId);await call('DOM.setFileInputFiles',{nodeId,files:[resolve(filename)]},sessionId);};
  const download=async(name)=>{for(let i=0;i<300;i++){try{return await readFile(out+'/downloads/'+name);}catch{}await sleep(100);}throw Error('missing download '+name);};
  const execute=async(button,kind,selection)=>{const previous=await ev('document.querySelector("#jobs .job")?.dataset.job');await click(button);await wait(`document.querySelector('#jobs .job')?.dataset.job!==${JSON.stringify(previous)} && document.querySelector('#jobs .job strong').textContent.includes(${JSON.stringify(kind)}) && document.querySelector('#jobs .job button')?.textContent==='結果を開く' && !document.querySelector('#jobs .job button').disabled`,180000);const id=await ev('document.querySelector("#jobs .job").dataset.job');await click('#jobs .job button');await wait(`${selection}===${JSON.stringify(id)}`,90000);return id;};
  await fill('#nx',8);await fill('#ny',8);await fill('#modes',4);
  await ev('document.querySelector("#study-parameter").value="/case/geometry/width_m"');await fill('#study-values','[0.18,0.2,0.22]');
  report.study=await execute('#study-start','独立掃引','selectedStudy');
  await click('#study-points button[data-point="0"]');await wait('selected!==null && project.case.geometry.width_m===.18');report.previous=await ev('selected');await click('#tracking-select-previous');await wait(`document.querySelector('#tracking-previous').value===${JSON.stringify(report.previous)}`);
  await click('#study-points button[data-point="2"]');await wait('project.case.geometry.width_m===.22');report.current=await ev('selected');await click('#tracking-select-current');await wait(`document.querySelector('#tracking-current').value===${JSON.stringify(report.current)}`);
  report.crossing=await execute('#tracking-start','モード追跡','selectedTracking');report.request=await ev('currentTracking.request');
  await check('actual worker follows electric-field rank exchange','currentTracking.result.status==="PASS" && currentTracking.result.individual_ids_complete && JSON.stringify(currentTracking.result.current_mode_ids)===JSON.stringify(["mode-2","mode-1"])');
  await click('#tracking-save');const saved=await download('planar-tracking-request.json');if(!isDeepStrictEqual(JSON.parse(saved),report.request))throw Error('tracking request download differs');
  await fill('#tracking-ids','["changed-a","changed-b"]');await loadFile('#tracking-open',out+'/downloads/planar-tracking-request.json');await wait('document.querySelector("#tracking-ids").value===JSON.stringify(["mode-1","mode-2"])');
  await check('tracking conditions roundtrip without changing mode IDs','JSON.stringify(trackingFromForm())===JSON.stringify(currentTracking.request)');
  await click('#tracking-result-save');const resultFile=await download('planar-tracking-results.json');if(!isDeepStrictEqual(JSON.parse(resultFile),await ev('currentTracking.result')))throw Error('tracking result download differs');report.checks.push({operation:'complete tracking result download matches native replay',passed:true});
  await click('#tracking-current-import');await wait(`selected!==${JSON.stringify(report.current)} && project.case.geometry.width_m===.22`);report.copied_source=await ev('selected');await click('#plot');await wait('!document.querySelector("#image").hidden && document.querySelector("#image").naturalWidth>100',90000);report.checks.push({operation:'copied source is independently importable and plotable',passed:true});
  await click('#study-points button[data-point="1"]');await wait('project.case.geometry.width_m===.2');report.square=await ev('selected');await click('#tracking-select-current');await wait(`document.querySelector('#tracking-current').value===${JSON.stringify(report.square)}`);
  report.merged=await execute('#tracking-start','モード追跡','selectedTracking');
  await check('square correspondence retains an ID set','currentTracking.result.status==="PASS" && !currentTracking.result.individual_ids_complete && currentTracking.result.matches[0].kind==="SUBSPACE" && currentTracking.result.current_mode_ids.every(x=>x===null)');
  await click('#tracking-use-groups');await wait('document.querySelector("#tracking-ids").value==="null" && document.querySelector("#tracking-current").value===""');report.carried_source=await ev('document.querySelector("#tracking-previous").value');
  await ev(`document.querySelector('#tracking-current').value=${JSON.stringify(report.current)}`);
  report.split=await execute('#tracking-start','モード追跡','selectedTracking');
  await check('split does not restore individual identities','currentTracking.result.status==="PASS" && !currentTracking.result.individual_ids_complete && currentTracking.result.matches[0].dimension===2');
  await ev('document.querySelector("#tracking-result").scrollIntoView({block:"start"})');const screenshot=await call('Page.captureScreenshot',{format:'png'},sessionId);await writeFile(out+'/tracking-results.png',Buffer.from(screenshot.data,'base64'));
  const old=await ev('JSON.stringify(trackingFromForm())');const invalid=out+'/invalid.json';await writeFile(invalid,JSON.stringify({...report.request,mapping:'undeclared_polygon'}));await loadFile('#tracking-open',invalid);await wait('!document.querySelector("#error").hidden');if(await ev('JSON.stringify(trackingFromForm())')!==old)throw Error('invalid tracking replaced current request');report.checks.push({operation:'unsupported mapping rejected without replacing current request',passed:true});
  await call('Page.navigate',{url:launch.origin+'/planar.html?job='+report.crossing},sessionId);await wait(`typeof selectedTracking!=='undefined' && selectedTracking===${JSON.stringify(report.crossing)}`,90000);
  await check('tracking result URL restores persistent correspondence','currentTracking.result.status==="PASS" && currentTracking.result.individual_ids_complete');
  report.source_changed_during_run=!isDeepStrictEqual(report.source_sha256,await sourceHashes());report.passed=!report.source_changed_during_run&&report.external_requests.length===0;
  if(!report.passed)throw Error('source or external HTTP changed');console.log(JSON.stringify({passed:true,checks:report.checks}));
} catch(e){report.error=String(e);process.exitCode=1;console.error(e);}
finally{await writeFile(out+'/report.json',JSON.stringify(report,null,2));ws?.close();if(browser.exitCode===null){browser.kill();await new Promise(resolve=>browser.once('exit',resolve));}}
