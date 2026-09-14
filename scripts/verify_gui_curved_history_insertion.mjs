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
  const open=async(path)=>{
    await ev('window.__opened=false; window.__applyProject=applyProject; applyProject=(p)=>{__applyProject(p);window.__opened=true;applyProject=__applyProject}');
    await call('DOM.setFileInputFiles',{nodeId,files:[resolve(path)]},sessionId);
    await wait('window.__opened');
  };
  await open(args['--case']);
  const original=await ev('collect()');
  await ev('window.__meshes=[];window.__api=api;api=async(...args)=>{const result=await __api(...args);if(args[0]==="curved-selection-mesh")__meshes.push({project:args[1].document,mesh:result});return result}');
  const position=async(mode,stage=1)=>{
    await ev(`$("curved-selection-position").value=${JSON.stringify(mode)};$("curved-selection-position").dispatchEvent(new Event("change",{bubbles:true}))`);
    if(mode!=='end')await fill('#curved-selection-stage',stage);
  };
  const loadMesh=async()=>{await click('#curved-selection-load');await wait('!$("curved-selection-load").disabled && !$("curved-selection-panel").hidden && (curvedCanvasPicker?.ready || $("curved-selection-mesh path") || document.querySelector("#curved-selection-mesh path"))',120000);};
  const selectCell=async(index)=>{
    const point=await ev(`(()=>{const e=document.querySelector('#curved-selection-mesh [data-cell="${index}"]');e.scrollIntoView({block:'center',behavior:'instant'});const r=e.getBoundingClientRect();for(const u of [.5,.3,.7,.2,.8])for(const v of [.5,.3,.7,.2,.8]){const x=r.x+u*r.width,y=r.y+v*r.height;if(document.elementFromPoint(x,y)===e)return {x,y};}throw Error('cell has no visible hit target')})()`);
    for(const type of ['mousePressed','mouseReleased'])await call('Input.dispatchMouseEvent',{type,...point,button:'left',clickCount:1},sessionId);
  };
  const same=async(operation,expression,expected)=>{
    if(!isDeepStrictEqual(await ev(expression),expected))throw Error(operation);
    report.checks.push({operation,passed:true});
  };
  const draft=()=>ev('curvedHistoryDraft()');
  const originalDraft=await draft();
  await position('insert',1);await loadMesh();
  await same('before first stage displays the initial 26-cell mesh','__meshes.at(-1).mesh.cell_nodes.length',26);
  await position('insert',2);await loadMesh();await selectCell(0);
  await same('middle insertion displays exactly the preceding marked prefix','__meshes.at(-1).project.case.mesh.curved_refinement_steps',input.mesh.curved_refinement_steps.slice(0,1));
  await same('prefix native cell count is 39','__meshes.at(-1).mesh.cell_nodes.length',39);
  await position('insert',1);await click('#curved-selection-append');
  await check('changed insertion target rejects stale IDs','$("error").textContent.includes("古い要素番号")');
  await same('target rejection leaves draft intact','curvedHistoryDraft()',originalDraft);
  await position('insert',2);
  await fill('#curved-history tbody tr:nth-child(3) .step-cells','21');await click('#curved-selection-append');
  await check('suffix changes invalidate a prefix selection','$("error").textContent.includes("古い要素番号")');
  await fill('#curved-history tbody tr:nth-child(3) .step-cells','20');await click('#curved-selection-append');
  await check('inserted step preserves prefix and uniform suffix, requires marked reselection',
    'curvedHistoryRows().length===4 && curvedHistoryRows()[0].querySelector(".step-cells").value==="0" && curvedHistoryRows()[1].querySelector(".step-cells").value==="0" && curvedHistoryRows()[2].querySelector(".step-kind").value==="uniform" && curvedHistoryRows()[3].querySelector(".step-cells").value==="" && curvedHistoryRows()[3].querySelector(".step-previous").textContent.includes("20")');
  const jobs=await ev('document.querySelectorAll("#jobs .job").length');
  await click('#save');await check('unresolved suffix cannot save','!$("error").hidden && $("error").textContent.includes("4段目")');
  await click('#run');await check('unresolved suffix cannot run',`!$("error").hidden && document.querySelectorAll("#jobs .job").length===${jobs}`);
  if((await readdir(out+'/downloads')).length)throw Error('unresolved draft was downloaded');
  const beta=await ev('$("beta").value');await fill('#beta',Number(beta)*.9);await click('#curved-history-undo');
  await check('undo rejects changed calculation inputs','$("error").textContent.includes("旧要素番号") && curvedHistoryRows().length===4');
  await fill('#beta',beta);await click('#curved-history-undo');
  await same('undo restores the complete original valid Project','collect()',original);

  // Delay an actual response to exercise a target change while the request is pending.
  await ev('window.__normalApi=api;window.__releaseMesh=null;api=async(...args)=>{const result=await __normalApi(...args);if(args[0]==="curved-selection-mesh")await new Promise(resolve=>window.__releaseMesh=resolve);return result}');
  await position('insert',2);await click('#curved-selection-load');await wait('!!window.__releaseMesh');
  await position('insert',1);await ev('__releaseMesh()');await wait('!$("curved-selection-load").disabled');
  await check('in-flight target change rejects the actual mesh response','$("error").textContent.includes("メッシュ作成中") && $("curved-selection-panel").hidden');
  await ev('api=__normalApi');
  await position('insert',2);await loadMesh();await selectCell(0);await click('#curved-selection-append');
  await click('#curved-history tbody tr:nth-child(4) .step-pick');
  await wait('!$("curved-selection-load").disabled && !$("curved-selection-panel").hidden');
  await same('reselection accepts a pending row and renders only its valid prefix','__meshes.at(-1).project.case.mesh.curved_refinement_steps',[{kind:'marked',marked_cells:[0],minimum_corner_angle_deg:5},{kind:'marked',marked_cells:[0],minimum_corner_angle_deg:5},{kind:'uniform'}]);
  await selectCell(20);await click('#curved-selection-append');
  const built=await ev('collect()');
  const expected=[input.mesh.curved_refinement_steps[0],{kind:'marked',marked_cells:[0],minimum_corner_angle_deg:5},...input.mesh.curved_refinement_steps.slice(1)];
  if(!isDeepStrictEqual(built.case.mesh.curved_refinement_steps,expected))throw Error('final repaired history is wrong');
  report.checks.push({operation:'repaired Project contains the inserted stage and explicitly reselected downstream IDs',passed:true});
  await writeFile(out+'/built-project.json',JSON.stringify(built,null,2));
  await click('#save');
  for(let n=0;n<100 && !(await readdir(out+'/downloads')).includes('cavity-project.json');n++)await sleep(100);
  const saved=JSON.parse(await readFile(out+'/downloads/cavity-project.json','utf8'));
  if(!isDeepStrictEqual(saved.case.mesh.curved_refinement_steps,expected))throw Error('save lost history');
  await open(out+'/downloads/cavity-project.json');
  await same('saved Project reloads the exact inserted and repaired history','collect().case.mesh.curved_refinement_steps',expected);
  await check('reload clears edit draft and undo state','$("curved-history-undo").disabled && curvedHistoryRows().every(row=>!row.querySelector(".step-previous").textContent)');
  await click('#run');await wait(`document.querySelectorAll('#jobs .job').length>${jobs}`);
  await wait('document.querySelector("#jobs .job strong").textContent.startsWith("計算完了")',120000);
  await click('#jobs .job button');await wait('$("field-image").naturalWidth>0',120000);
  const result=await ev('currentResult');
  if(!isDeepStrictEqual(result.result.case.mesh.curved_refinement_steps,expected))throw Error('actual FEM lost inserted history');
  report.checks.push({operation:'actual GUI FEM consumes the saved repaired history',passed:true});
  await writeFile(out+'/result.json',JSON.stringify(result,null,2));

  // Uniform-level input must also support inserting before existing uniform steps.
  const levels=structuredClone(input);delete levels.mesh.curved_refinement_steps;levels.mesh.curved_refinement_levels=5;
  await writeFile(out+'/levels-case.json',JSON.stringify(levels));await open(out+'/levels-case.json');
  await position('insert',5);await loadMesh();
  await check('large middle prefix uses Canvas and exactly 6656 native cells','curvedCanvasPicker?.ready && __meshes.at(-1).mesh.cell_nodes.length===6656 && __meshes.at(-1).project.case.mesh.curved_refinement_levels===4');
  await fill('#curved-selection-cell',0);await click('#curved-selection-focus');
  await ev('$("curved-selection-canvas").focus()');
  await call('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',windowsVirtualKeyCode:13},sessionId);
  await call('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13},sessionId);
  await click('#curved-selection-append');
  await same('large insertion preserves four prefix and one suffix uniform stages','collect().case.mesh.curved_refinement_steps',[...Array.from({length:4},()=>({kind:'uniform'})),{kind:'marked',marked_cells:[0],minimum_corner_angle_deg:5},{kind:'uniform'}]);
  await writeFile(out+'/large-built-project.json',JSON.stringify(await ev('collect()'),null,2));
  await click('#curved-history-undo');
  await check('undo restores uniform-level representation','collect().case.mesh.curved_refinement_levels===5 && !collect().case.mesh.curved_refinement_steps');
  await writeFile(out+'/mesh-documents.json',JSON.stringify(await ev('__meshes')));
  // End in a visible small draft so the reference and repair controls can be inspected.
  await open(args['--case']);await position('insert',2);await loadMesh();await selectCell(0);await click('#curved-selection-append');
  const rect=await ev('(()=>{const r=$("curved-history-controls").getBoundingClientRect();return {x:r.x+scrollX,y:r.y+scrollY,width:r.width,height:r.height,scale:1}})()');
  const shot=await call('Page.captureScreenshot',{captureBeyondViewport:true,clip:rect},sessionId);await writeFile(out+'/history.png',Buffer.from(shot.data,'base64'));
  report.source_changed_during_run=!isDeepStrictEqual(report.source_sha256,await sourceHashes());
  report.passed=!report.source_changed_during_run && report.external_requests.length===0 && report.checks.every(c=>c.passed);
  if(!report.passed)throw Error('Graphical selection checks failed');
  console.log(JSON.stringify({passed:report.passed,checks:report.checks}));
} catch(e){report.error=String(e);process.exitCode=1;console.error(e);}
finally{await writeFile(out+'/report.json',JSON.stringify(report,null,2));ws?.close();browser.kill();}
