// SPDX-License-Identifier: Apache-2.0
// Real local browser input and computation. Requires a running GUI and Chrome.
import { spawn } from "node:child_process";
import { mkdtemp, readFile, writeFile, mkdir, readdir } from "node:fs/promises";
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
if (!args['--url'] || !args['--out'] || !args['--case']) throw Error('Require --url --out --case');
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
      }, 30000);
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
      `UI timeout: ${expression}; ${await ev('document.querySelector("#error")?.textContent')}`,
    );
  };
  const click = async (selector) => {
    const rect = await ev(
      `(async()=>{const e=document.querySelector(${JSON.stringify(selector)});e.scrollIntoView({block:'center',behavior:'instant'});await new Promise(done=>requestAnimationFrame(()=>requestAnimationFrame(done)));const r=e.getBoundingClientRect(),x=r.x+r.width/2,y=r.y+r.height/2;if(!e.contains(document.elementFromPoint(x,y)))throw Error('click target is obscured');return {x,y}})()`,
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
  const begin = performance.now();
  await call("Page.navigate", { url: args["--url"] }, sessionId);
  await wait('document.querySelector("#shape polygon")');
  report.startup_ms = performance.now() - begin;
  const check=async (operation,expression)=>{if (!await ev(expression)) throw Error(operation);report.checks.push({operation,passed:true});};


  const input=JSON.parse(await readFile(args['--case'],'utf8'));
  const {root}=await call('DOM.getDocument',{},sessionId);
  const {nodeId}=await call('DOM.querySelector',{nodeId:root.nodeId,selector:'#open'},sessionId);
  await call('DOM.setFileInputFiles',{nodeId,files:[resolve(args['--case'])]},sessionId);
  await wait('document.querySelector("#geometry-type").value==="curved_contour"');
  const prefix=input.mesh.curved_refinement_steps || Array.from({length:input.mesh.curved_refinement_levels||0},()=>({kind:'uniform'}));
  const loadMesh=async()=>{await click('#curved-selection-load');await wait('!document.querySelector("#curved-selection-load").disabled && !document.querySelector("#curved-selection-panel").hidden && document.querySelector("#curved-selection-mesh path")',120000);};
  const selectCell=async(index)=>{
    const point=await ev(`(()=>{const e=document.querySelector('#curved-selection-mesh [data-cell="${index}"]');e.scrollIntoView({block:'center',behavior:'instant'});const r=e.getBoundingClientRect();for(const u of [.5,.3,.7,.2,.8])for(const v of [.5,.3,.7,.2,.8]){const x=r.x+u*r.width,y=r.y+v*r.height;if(document.elementFromPoint(x,y)===e)return {x,y};}throw Error('cell has no visible hit target')})()`);
    for(const type of ['mousePressed','mouseReleased'])await call('Input.dispatchMouseEvent',{type,...point,button:'left',clickCount:1},sessionId);
  };
  await loadMesh();await selectCell(0);
  await check('physical cell click selects its native ID','document.querySelector("#curved-selection-mesh path").getAttribute("aria-pressed")==="true" && !document.querySelector("#curved-selection-append").disabled');
  await selectCell(0);await check('second click deselects cell','document.querySelector("#curved-selection-append").disabled');
  await selectCell(0);
  if(input.mesh.curved_refinement_steps) await click('#curved-add-uniform');
  else await fill('#curved-refinement-levels',String((input.mesh.curved_refinement_levels||0)+1));
  await click('#curved-selection-append');await wait('!document.querySelector("#error").hidden');
  await check('changed history cannot append stale cell IDs','document.querySelector("#error").textContent.includes("古い要素番号")');
  if(input.mesh.curved_refinement_steps) await click('#curved-history tbody tr:last-child .step-remove');
  else await fill('#curved-refinement-levels',String(input.mesh.curved_refinement_levels||0));
  const chord=await ev('document.querySelector("#curve-chord").value');
  await fill('#curve-chord',String(Number(chord)*.9));await click('#curved-selection-append');
  await wait('!document.querySelector("#error").hidden');
  await check('changed input cannot append stale cell IDs','document.querySelector("#error").textContent.includes("古い要素番号")');
  const old=await ev('(()=>{const m=collect().case.mesh;return m.curved_refinement_steps || Array.from({length:m.curved_refinement_levels||0},()=>({kind:"uniform"}))})()');
  if(!isDeepStrictEqual(old,prefix))throw Error('stale selection changed the history');
  await fill('#curve-chord',chord);await click('#curved-selection-append');
  const built=await ev('collect()');
  if(!isDeepStrictEqual(built.case.mesh.curved_refinement_steps,[...prefix,{kind:'marked',marked_cells:[0],minimum_corner_angle_deg:5}]))throw Error('selection did not append the correct ordered history');
  report.checks.push({operation:'graph selection appends a marked step while preserving the prefix',passed:true});
  await writeFile(out+'/built-project.json',JSON.stringify(built,null,2));
  const before=await ev('document.querySelectorAll("#jobs .job").length');
  await click('#run');await wait(`document.querySelectorAll('#jobs .job').length>${before}`);
  await wait('document.querySelector("#jobs .job strong").textContent.startsWith("計算完了")',120000);
  await click('#jobs .job button');await wait('document.querySelector("#field-image").naturalWidth>0',120000);
  const result=await ev('currentResult');
  if(!isDeepStrictEqual(result.result.case.mesh.curved_refinement_steps,built.case.mesh.curved_refinement_steps))throw Error('actual FEM lost selected IDs');
  report.checks.push({operation:'actual GUI FEM uses the selected history',passed:true});
  await writeFile(out+'/result.json',JSON.stringify(result,null,2));
  await loadMesh();await selectCell(0);
  const rect=await ev('(()=>{const r=document.querySelector("#curved-selection-panel").getBoundingClientRect();return {x:r.x+scrollX,y:r.y+scrollY,width:r.width,height:r.height,scale:1}})()');
  const shot=await call('Page.captureScreenshot',{captureBeyondViewport:true,clip:rect},sessionId);await writeFile(out+'/selection.png',Buffer.from(shot.data,'base64'));
  const historyRect=await ev('(()=>{const r=document.querySelector("#curved-history-controls").getBoundingClientRect();return {x:r.x+scrollX,y:r.y+scrollY,width:r.width,height:r.height,scale:1}})()');
  const historyShot=await call('Page.captureScreenshot',{captureBeyondViewport:true,clip:historyRect},sessionId);await writeFile(out+'/history.png',Buffer.from(historyShot.data,'base64'));
  report.source_changed_during_run=!isDeepStrictEqual(report.source_sha256,await sourceHashes());
  report.passed=!report.source_changed_during_run && report.external_requests.length===0 && report.checks.every(c=>c.passed);
  if(!report.passed)throw Error('Graphical selection checks failed');
  console.log(JSON.stringify({passed:report.passed,checks:report.checks}));
} catch(e){report.error=String(e);process.exitCode=1;console.error(e);}
finally{await writeFile(out+'/report.json',JSON.stringify(report,null,2));ws?.close();browser.kill();}
