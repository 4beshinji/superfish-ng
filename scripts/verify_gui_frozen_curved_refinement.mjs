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




  const {root}=await call('DOM.getDocument',{},sessionId);
  const {nodeId}=await call('DOM.querySelector',{nodeId:root.nodeId,selector:'#open'},sessionId);
  const open=async(path)=>{
    await ev('window.__opened=false;window.__apply=applyProject;applyProject=p=>{__apply(p);window.__opened=true;applyProject=__apply}');
    await call('DOM.setFileInputFiles',{nodeId,files:[resolve(path)]},sessionId);await wait('__opened');
  };
  await open(args['--case']);
  const expected=JSON.parse(await readFile(args['--case'].replace('source-project.json','frozen-project.json'),'utf8'));
  await click('#curved-freeze');
  await wait('!$("curved-freeze").disabled && curvedHistoryRows().filter(r=>r.querySelector(".step-kind").value==="marked").every(r=>r._splitPattern)');
  const frozen=await ev('collect()');
  if(!isDeepStrictEqual(frozen.case.mesh.curved_refinement_steps,expected.case.mesh.curved_refinement_steps) || !isDeepStrictEqual(frozen.mesh_data,expected.mesh_data))throw Error('GUI freeze differs from native CLI capture');
  report.checks.push({operation:'GUI capture equals CLI split choices and original source mesh',passed:true});
  await check('fixed rows expose state and protect their marked IDs','curvedHistoryRows().filter(r=>r._splitPattern).every(r=>r.querySelector(".step-kind").disabled && r.querySelector(".step-cells").disabled && !r.querySelector(".step-release").hidden && r.querySelector(".step-split-note").textContent.includes("固定"))');
  await click('#save');
  for(let n=0;n<100 && !(await readdir(out+'/downloads')).includes('cavity-project.json');n++)await sleep(100);
  const saved=JSON.parse(await readFile(out+'/downloads/cavity-project.json','utf8'));
  if(!isDeepStrictEqual(saved.case.mesh.curved_refinement_steps,expected.case.mesh.curved_refinement_steps))throw Error('GUI save dropped frozen choices');
  await open(out+'/downloads/cavity-project.json');
  await check('saved Project restores fixed rows and full declarations','curvedHistoryRows().filter(r=>r._splitPattern).length===2');
  const restored=await ev('collect()');
  if(!isDeepStrictEqual(restored.case.mesh.curved_refinement_steps,frozen.case.mesh.curved_refinement_steps))throw Error('reload changes patterns');
  await click('#curved-history tbody tr:first-child .step-release');
  await check('explicit release clears downstream IDs and frozen patterns','!curvedHistoryRows()[0]._splitPattern && !curvedHistoryRows()[0].querySelector(".step-cells").disabled && curvedHistoryRows()[2].querySelector(".step-cells").value==="" && !curvedHistoryRows()[2]._splitPattern');
  await click('#save');await check('unfinished released suffix cannot save','!$("error").hidden && $("error").textContent.includes("3段目")');
  await open(out+'/downloads/cavity-project.json');
  await click('#curved-history tbody tr:last-child .step-pick');
  await wait('!$("curved-selection-load").disabled && document.querySelector("#curved-selection-mesh path")');
  await ev('document.querySelector("#curved-selection-mesh path").focus()');
  await call('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',windowsVirtualKeyCode:13},sessionId);
  await call('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13},sessionId);
  await click('#curved-selection-append');
  await check('graphical replacement explicitly releases only that fixed step','curvedHistoryRows()[0]._splitPattern && !curvedHistoryRows()[2]._splitPattern');
  await click('#curved-history-undo');
  if(!isDeepStrictEqual(await ev('collect().case.mesh.curved_refinement_steps'),frozen.case.mesh.curved_refinement_steps))throw Error('undo lost frozen metadata');
  report.checks.push({operation:'graphical undo restores complete frozen history',passed:true});
  const jobs=await ev('document.querySelectorAll("#jobs .job").length');
  await click('#run');await wait(`document.querySelectorAll('#jobs .job').length>${jobs}`);
  await wait('document.querySelector("#jobs .job strong").textContent.startsWith("計算完了")',120000);
  await click('#jobs .job button');await wait('$("field-image").naturalWidth>0',120000);
  const result=await ev('currentResult');
  if(!isDeepStrictEqual(result.result.case.mesh.curved_refinement_steps,frozen.case.mesh.curved_refinement_steps))throw Error('native GUI solve dropped frozen choices');
  await writeFile(out+'/result.json',JSON.stringify(result,null,2));
  report.checks.push({operation:'actual GUI worker and native save retain all frozen choices',passed:true});
  await open(args['--case']);
  await ev('window.__normalApi=api;window.__release=null;api=async(...args)=>{const value=await __normalApi(...args);if(args[0]==="freeze-curved-refinement")await new Promise(resolve=>window.__release=resolve);return value}');
  await click('#curved-freeze');await wait('!!window.__release');
  await fill('#beta',.9);await ev('__release()');await wait('!$("curved-freeze").disabled');
  await check('in-flight input change rejects stale freezing without replacing the Project','$("error").textContent.includes("入力が変わりました") && explicitProjectMesh===null && curvedHistoryRows().every(r=>!r._splitPattern) && $("beta").value==="0.9"');
  await ev('api=__normalApi');await open(out+'/downloads/cavity-project.json');
  const rect=await ev('(()=>{const r=$("curved-history-controls").getBoundingClientRect();return {x:r.x+scrollX,y:r.y+scrollY,width:r.width,height:r.height,scale:1}})()');
  const shot=await call('Page.captureScreenshot',{captureBeyondViewport:true,clip:rect},sessionId);await writeFile(out+'/frozen-history.png',Buffer.from(shot.data,'base64'));
  report.source_changed_during_run=!isDeepStrictEqual(report.source_sha256,await sourceHashes());
  report.passed=!report.source_changed_during_run && report.external_requests.length===0 && report.checks.every(c=>c.passed);
  if(!report.passed)throw Error('Graphical selection checks failed');
  console.log(JSON.stringify({passed:report.passed,checks:report.checks}));
} catch(e){report.error=String(e);process.exitCode=1;console.error(e);}
finally{await writeFile(out+'/report.json',JSON.stringify(report,null,2));ws?.close();browser.kill();}
