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
if (!args['--url'] || !args['--out'] || !args['--sources']) throw Error('Require --url --out --sources');
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



  const source=resolve(args['--sources']);
  const expected=JSON.parse(await readFile(source+'/scale-1-transfer.json','utf8'));
  const contained=JSON.parse(await readFile(source+'/scale-1-contained.json','utf8'));
  const target=JSON.parse(await readFile(source+'/scale-1-current-project.json','utf8'));
  const refined=JSON.parse(await readFile(source+'/scale-1-refined-project.json','utf8'));
  const numerical=JSON.parse(await readFile(source+'/report.json','utf8'));
  const fileInput=async(selector,path)=>{
    const {root}=await call('DOM.getDocument',{},sessionId);
    const {nodeId}=await call('DOM.querySelector',{nodeId:root.nodeId,selector},sessionId);
    await call('DOM.setFileInputFiles',{nodeId,files:[resolve(path)]},sessionId);
  };
  const open=async path=>{
    await ev('window.__opened=false;window.__applyProject=applyProject;applyProject=p=>{__applyProject(p);__opened=true;applyProject=__applyProject}');
    await fileInput('#open',path);await wait('__opened');
  };
  const select=async(id,value)=>ev(`$("${id}").value=${JSON.stringify(value)};$("${id}").dispatchEvent(new Event('change',{bubbles:true}))`);
  const same=async(operation,expression,value)=>{if(!isDeepStrictEqual(await ev(expression),value))throw Error(operation);report.checks.push({operation,passed:true});};
  const selected=()=>ev('[...curvedSelection.cells].sort((a,b)=>a-b)');
  const loadMesh=async()=>{await click('#curved-selection-load');await wait('!$("curved-selection-load").disabled && !$("curved-selection-panel").hidden && (curvedCanvasPicker?.ready || document.querySelector("#curved-selection-mesh path"))',120000);};
  const transfer=async policy=>{
    await select('curved-transfer-policy',policy);await ev('window.__lastTransfer=curvedTransferResult');
    await click('#curved-transfer-run');await wait('!$("curved-transfer-run").disabled && curvedTransferResult!==__lastTransfer',120000);
  };
  await open(source+'/scale-1-current-project.json');await loadMesh();
  const original=await ev('collect()');
  await ev('$("curved-transfer-controls").open=true');
  await fileInput('#curved-transfer-source-file',source+'/scale-1-previous-project.json');
  await wait('$("curved-transfer-source").value.includes("project_version")');
  const sourceText=await ev('$("curved-transfer-source").value');
  await fill('#curved-transfer-cells',JSON.stringify(expected.request.selected_cells));
  await select('curved-transfer-boundary',expected.request.boundary_pairing);
  await fill('#curved-transfer-budget',expected.request.max_pair_tests);
  await transfer('intersects');
  await same('GUI transfer has the same exact reference intersections as CLI','curvedTransferResult.selection',expected.selection);
  await same('base numbering correspondence equals the independent CLI','curvedTransferResult.base_correspondence',expected.base_correspondence);
  await same('region calculation retains the current Project','collect()',original);
  await same('SVG selection receives the exact target IDs','[...curvedSelection.cells].sort((a,b)=>a-b)',expected.selection.selected_cells);
  await check('all selected SVG cells are visibly marked',`[...document.querySelectorAll('#curved-selection-mesh [aria-pressed="true"]')].length===${expected.selection.selected_cells.length}`);
  const verified=await ev('curvedTransferResult'),retained=await selected();
  await fill('#curved-transfer-source','{"project_version":2,"project_version":2}');await click('#curved-transfer-run');
  await wait('!$("curved-transfer-run").disabled && $("error").textContent.includes("duplicate JSON key")');
  await same('duplicate source keys preserve current selection and result','[...curvedSelection.cells].sort((a,b)=>a-b)',retained);
  if(!isDeepStrictEqual(await ev('curvedTransferResult'),verified))throw Error('failed source replaced result');
  await fill('#curved-transfer-source',sourceText);await fill('#curved-transfer-budget',1);await click('#curved-transfer-run');
  await wait('!$("curved-transfer-run").disabled && $("error").textContent.includes("max_pair_tests")');
  await same('pair budget failure preserves current selection','[...curvedSelection.cells].sort((a,b)=>a-b)',retained);
  await fill('#curved-transfer-budget',expected.request.max_pair_tests);
  await transfer('contained');await same('containment policy selects the independently verified subset','[...curvedSelection.cells].sort((a,b)=>a-b)',contained.selection.selected_cells);
  await transfer('intersects');
  // Delay a real completed response, then change a manual selection.
  await ev('window.__normalTransferApi=api;window.__releaseTransfer=null;api=async(...args)=>{const result=await __normalTransferApi(...args);if(args[0]==="transfer-curved-selection")await new Promise(done=>__releaseTransfer=done);return result}');
  await click('#curved-transfer-run');await wait('!!__releaseTransfer');
  await ev(`document.querySelector('#curved-selection-mesh [data-cell="0"]').focus()`);
  await call('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',windowsVirtualKeyCode:13},sessionId);
  await call('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13},sessionId);
  const manual=await selected();await ev('__releaseTransfer()');await wait('!$("curved-transfer-run").disabled && $("error").textContent.includes("移送の検査中")');
  await same('manual selection changes reject an in-flight completed transfer','[...curvedSelection.cells].sort((a,b)=>a-b)',manual);
  await ev('__releaseTransfer=null');await click('#curved-transfer-run');await wait('!!__releaseTransfer');
  await fill('#curved-transfer-budget',100001);await ev('__releaseTransfer()');await wait('!$("curved-transfer-run").disabled && $("error").textContent.includes("移送の検査中")');
  await same('changed transfer settings reject an in-flight result','[...curvedSelection.cells].sort((a,b)=>a-b)',manual);
  await ev('api=__normalTransferApi');await fill('#curved-transfer-budget',expected.request.max_pair_tests);await transfer('intersects');
  await click('#curved-transfer-save');let saved;
  for(let n=0;n<100;n++){try{saved=JSON.parse(await readFile(out+'/downloads/curved-selection-transfer.json','utf8'));break;}catch{}await sleep(100);}
  if(!isDeepStrictEqual(saved,await ev('curvedTransferResult')))throw Error('saved transfer differs');
  report.checks.push({operation:'download preserves the complete input, rational overlap and selection document',passed:true});
  const changed=structuredClone(saved);changed.selection.selected_cells=[];
  await writeFile(out+'/changed-transfer.json',JSON.stringify(changed));await fileInput('#curved-transfer-open',out+'/changed-transfer.json');
  await wait('!$("error").hidden && $("error").textContent.includes("full reconstruction")');
  await same('modified saved selection cannot replace a verified transfer','curvedTransferResult',saved);
  await fill('#curved-transfer-cells','[1]');await fileInput('#curved-transfer-open',out+'/downloads/curved-selection-transfer.json');
  await wait('$("curved-transfer-status").textContent.includes("条件を復元")');
  await same('saved replay restores the original selection declaration','JSON.parse($("curved-transfer-cells").value)',expected.request.selected_cells);
  await transfer('intersects');await fill('#curved-selection-angle',1);await click('#curved-selection-append');
  await same('existing history append consumes transferred target IDs','collect().case.mesh.curved_refinement_steps',refined.case.mesh.curved_refinement_steps);
  await writeFile(out+'/built-project.json',JSON.stringify(await ev('collect()'),null,2));await click('#save');
  for(let n=0;n<100 && !(await readdir(out+'/downloads')).includes('cavity-project.json');n++)await sleep(100);
  await open(out+'/downloads/cavity-project.json');
  await same('saved Project preserves the new marked stage','collect().case.mesh.curved_refinement_steps',refined.case.mesh.curved_refinement_steps);
  const jobs=await ev('document.querySelectorAll("#jobs .job").length');await click('#run');
  await wait(`document.querySelectorAll('#jobs .job').length>${jobs}`);await wait('document.querySelector("#jobs .job strong").textContent.startsWith("計算完了")',120000);
  await click('#jobs .job button');await wait('$("field-image").naturalWidth>0',120000);
  const result=await ev('currentResult');await writeFile(out+'/result.json',JSON.stringify(result,null,2));
  if(!isDeepStrictEqual(result.result.case.mesh.curved_refinement_steps,refined.case.mesh.curved_refinement_steps))throw Error('actual FEM lost transferred stage');
  for(const key of ['frequency_hz','r_over_q_accelerator_ohm','r_over_q_circuit_ohm','geometry_factor_ohm','transit_time_factor_abs']) {
    if(Math.abs(result.result.modes[0][key]/numerical.rows[0].rf[1][key]-1)>1e-12)throw Error('GUI/native RF mismatch '+key);
  }
  report.checks.push({operation:'actual GUI FEM consumes the transferred selection and matches independent RF',passed:true});
  // Return to the prefix before the inserted step for a visible small result.
  await select('curved-selection-position','replace');await fill('#curved-selection-stage',3);await loadMesh();await transfer('intersects');
  const small=await ev('(()=>{const a=$("curved-selection-panel").getBoundingClientRect(),b=$("curved-transfer-controls").getBoundingClientRect();return {x:Math.min(a.x,b.x)+scrollX,y:a.y+scrollY,width:Math.max(a.width,b.width),height:b.bottom-a.top,scale:1}})()');
  const shot=await call('Page.captureScreenshot',{captureBeyondViewport:true,clip:small},sessionId);await writeFile(out+'/selection-transfer.png',Buffer.from(shot.data,'base64'));
  // The Canvas picker shares its mutable selection Set with the transfer UI.
  const large=structuredClone(target);delete large.case.mesh.curved_refinement_steps;large.case.mesh.curved_refinement_levels=4;
  await writeFile(out+'/large-project.json',JSON.stringify(large));await open(out+'/large-project.json');await loadMesh();
  await check('large transfer uses the actual 6656-cell Canvas mesh','curvedCanvasPicker?.ready && curvedCanvasPicker.mesh.cell_nodes.length===6656');
  await transfer('intersects');
  await check('Canvas retains precisely the transferred cell IDs','JSON.stringify([...curvedCanvasPicker.selected].sort((a,b)=>a-b))===JSON.stringify(curvedTransferResult.selection.selected_cells) && curvedCanvasPicker.selected.size>0');
  await writeFile(out+'/large-transfer.json',JSON.stringify(await ev('curvedTransferResult'),null,2));
  await fill('#curved-selection-cell',(await selected())[0]);await click('#curved-selection-focus');
  const largeRect=await ev('(()=>{const r=$("curved-selection-large").getBoundingClientRect();return {x:r.x+scrollX,y:r.y+scrollY,width:r.width,height:r.height,scale:1}})()');
  const largeShot=await call('Page.captureScreenshot',{captureBeyondViewport:true,clip:largeRect},sessionId);await writeFile(out+'/large-transfer.png',Buffer.from(largeShot.data,'base64'));
  report.new_fem_solves=1;

  report.source_changed_during_run=!isDeepStrictEqual(report.source_sha256,await sourceHashes());
  report.passed=!report.source_changed_during_run && report.external_requests.length===0 && report.checks.every(c=>c.passed);
  if(!report.passed)throw Error('Graphical selection checks failed');
  console.log(JSON.stringify({passed:report.passed,checks:report.checks}));
} catch(e){report.error=String(e);process.exitCode=1;console.error(e);}
finally{await writeFile(out+'/report.json',JSON.stringify(report,null,2));ws?.close();browser.kill();}
