// SPDX-License-Identifier: Apache-2.0
// Real local browser input and computation. Requires a running GUI and Chrome.
import { launchBrowser } from "./browser-session.mjs";
import { readFile, writeFile, mkdir, readdir } from "node:fs/promises";
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
if(args['--url-file'])args['--url']=(await readFile(args['--url-file'],'utf8')).trim();
if (!args['--url'] || !args['--out'] || !args['--sources']) throw Error('Require --url or --url-file, --out and --sources');
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
  const read=async name=>JSON.parse(await readFile(source+'/'+name,'utf8'));
  const expected=await read('intersects-transfer.json'),contained=await read('contained-transfer.json');
  const current=await read('current-project.json'),refined=await read('refined-project.json');
  const native=await read('current-native-mesh.json'),refinedNative=await read('refined-native-mesh.json');
  const old=await read('v1-transfer.json');
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
  const same=async(operation,expression,value)=>{
    const actual=await ev(expression);
    if(!isDeepStrictEqual(actual,value)){
      await writeFile(out+'/comparison-failure.json',JSON.stringify({operation,actual,expected:value},null,2));
      throw Error(operation);
    }
    report.checks.push({operation,passed:true});
  };
  const selected='[...curvedSelection.cells].sort((a,b)=>a-b)';
  // Compare the strict Project representation; collect() explicitly emits
  // default diagonal triangulation and zero uniform refinement fields.
  const project='api("normalize",{document:JSON.stringify(collect())}).then(result=>result.project)';
  const loadMesh=async()=>{
    await click('#curved-selection-load');
    await wait('!$("curved-selection-load").disabled && !$("curved-selection-panel").hidden && document.querySelector("#curved-selection-mesh path")');
  };
  const transfer=async policy=>{
    await select('curved-transfer-policy',policy);await ev('window.__lastTransfer=curvedTransferResult');
    await click('#curved-transfer-run');await wait('!$("curved-transfer-run").disabled && curvedTransferResult!==__lastTransfer');
  };
  await check('explicit reference-chart boundary option is available',
    '[...$("curved-transfer-boundary").options].some(o=>o.value==="declared_reference_polylines")');
  await open(source+'/current-project.json');await loadMesh();
  await same('displayed target retains the exact independent Project',project,current);
  await same('target SVG IDs match the actual native cell numbering',
    '[...$("curved-selection-mesh").querySelectorAll("[data-cell]")].map(e=>Number(e.dataset.cell))',native.cell_nodes.map((_,i)=>i));
  await ev('$("curved-transfer-controls").open=true');
  await fileInput('#curved-transfer-source-file',source+'/previous-project.json');
  await wait('$("curved-transfer-source").value.includes("project_version")');
  const sourceText=await ev('$("curved-transfer-source").value');
  await fill('#curved-transfer-cells',JSON.stringify(expected.request.selected_cells));
  await select('curved-transfer-boundary',expected.request.boundary_pairing);
  await check('chart controls appear only for the explicit boundary policy','!$("curved-transfer-charts").hidden');
  for(const [index,name] of ['previous-chart','current-chart'].entries())
    await fill('#curved-transfer-'+name,JSON.stringify(expected.request.reference_vertices[index]));
  await fill('#curved-transfer-budget',expected.request.max_pair_tests);
  await fill('#curved-transfer-triangles',expected.request.max_triangles);
  await transfer('intersects');
  await same('GUI document equals independent API with all rational partition evidence','curvedTransferResult',expected);
  await same('intersection cover marks the exact native target IDs',selected,expected.selection.selected_cells);
  await check('all selected SVG elements are visibly marked',
    `[...document.querySelectorAll('#curved-selection-mesh [aria-pressed="true"]')].length===${expected.selection.selected_cells.length}`);
  await same('transfer keeps the current Project',project,current);
  const verified=await ev('curvedTransferResult'),retained=await ev(selected);
  const reject=async(selector,value,message,operation)=>{
    const original=await ev(`document.querySelector(${JSON.stringify(selector)}).value`);
    await fill(selector,value);await click('#curved-transfer-run');
    await wait(`!$("curved-transfer-run").disabled && !$("error").hidden && $("error").textContent.includes(${JSON.stringify(message)})`);
    await same(operation+' retains the selection',selected,retained);
    await same(operation+' retains the verified result','curvedTransferResult',verified);
    await fill(selector,original);
  };
  await reject('#curved-transfer-previous-chart','[{"x":0,"x":0},[1,0],[0,1]]','duplicate JSON key','raw duplicate chart object');
  await reject('#curved-transfer-current-chart','[[NaN,0],[1,0],[0,1]]','finite','raw nonfinite chart');
  await reject('#curved-transfer-cells','[0.0]','integers','raw float cell ID');
  await reject('#curved-transfer-cells','[false]','integers','raw boolean cell ID');
  await reject('#curved-transfer-budget','40','max_pair_tests','whole chart pair budget');
  await reject('#curved-transfer-triangles','3','max_triangles','common triangle budget');
  await reject('#curved-transfer-source','{"project_version":2,"project_version":2}','duplicate JSON key','raw duplicate source');
  await transfer('contained');
  await same('contained preserves the exact independently computed document','curvedTransferResult',contained);
  await same('empty contained subset is successful',selected,[]);
  await check('empty subset disables history append','$("curved-selection-append").disabled');
  await transfer('intersects');
  await ev('window.__normalApi=api;window.__release=null;api=async(...args)=>{const result=await __normalApi(...args);if(args[0]==="transfer-curved-selection")await new Promise(done=>__release=done);return result}');
  for(const name of ['previous-chart','current-chart','triangles']){
    await ev('__release=null');await click('#curved-transfer-run');await wait('!!__release');
    const selector='#curved-transfer-'+name,original=await ev(`document.querySelector(${JSON.stringify(selector)}).value`);
    await fill(selector,name==='triangles'?'10001':original+' ');await ev('__release()');
    await wait('!$("curved-transfer-run").disabled && $("error").textContent.includes("移送の検査中")');
    await same('changing '+name+' rejects a completed in-flight response',selected,retained);
    await fill(selector,original);
  }
  await ev('__release=null');await click('#curved-transfer-run');await wait('!!__release');
  await ev(`document.querySelector(${JSON.stringify('#curved-selection-mesh [data-cell="0"]')}).focus()`);
  for(const type of ['keyDown','keyUp'])await call('Input.dispatchKeyEvent',{type,key:'Enter',code:'Enter',windowsVirtualKeyCode:13},sessionId);
  const manual=await ev(selected);await ev('__release()');
  await wait('!$("curved-transfer-run").disabled && $("error").textContent.includes("移送の検査中")');
  await same('manual selection rejects the in-flight response',selected,manual);
  await ev('__release=null');await click('#curved-transfer-run');await wait('!!__release');
  await fill('#name','changed while checking');await ev('__release()');
  await wait('!$("curved-transfer-run").disabled && $("error").textContent.includes("移送の検査中")');
  await same('changed Project rejects the in-flight response',selected,manual);
  await fill('#name',current.case.name);await loadMesh();
  await ev('__release=null');await click('#curved-transfer-run');await wait('!!__release');
  await select('curved-selection-position','insert');await fill('#curved-selection-stage',1);await ev('__release()');
  await wait('!$("curved-transfer-run").disabled && $("error").textContent.includes("移送の検査中")');
  await check('changed target stage rejects the in-flight response','curvedSelection.cells.size===0');
  await ev('api=__normalApi');await select('curved-selection-position','end');await loadMesh();await transfer('intersects');
  await click('#curved-transfer-save');let saved;
  for(let n=0;n<100;n++){try{saved=JSON.parse(await readFile(out+'/downloads/curved-selection-transfer.json','utf8'));break;}catch{}await sleep(100);}
  if(!isDeepStrictEqual(saved,expected))throw Error('download differs from complete API document');
  report.checks.push({operation:'download retains the full version-2 document',passed:true});
  const changed=structuredClone(saved);changed.reference_partition.triangles[0].current_cell=true;
  await writeFile(out+'/tampered.json',JSON.stringify(changed));await fileInput('#curved-transfer-open',out+'/tampered.json');
  await wait('!$("error").hidden && $("error").textContent.includes("full reconstruction")');
  await same('tampered saved partition cannot replace the verified result','curvedTransferResult',expected);
  await fileInput('#curved-transfer-open',source+'/v1-transfer.json');
  await wait('curvedTransferResult?.schema_version===1');
  await check('v1 replay hides and clears both new charts and the triangle budget',
    '$("curved-transfer-charts").hidden && !$("curved-transfer-previous-chart").value && !$("curved-transfer-current-chart").value && !$("curved-transfer-triangles").value');
  await transfer('intersects');await same('original v1 transfer is unchanged in the current GUI','curvedTransferResult',old);
  await fileInput('#curved-transfer-open',out+'/downloads/curved-selection-transfer.json');
  await wait('curvedTransferResult?.schema_version===2 && !$("curved-transfer-charts").hidden');
  await same('v2 replay restores both full charts','[JSON.parse($("curved-transfer-previous-chart").value),JSON.parse($("curved-transfer-current-chart").value)]',expected.request.reference_vertices);
  await same('v2 replay restores the full triangle budget','Number($("curved-transfer-triangles").value)',expected.request.max_triangles);
  await same('saved replay leaves the current target unchanged',project,current);
  await ev('api=async(...args)=>{const result=await __normalApi(...args);if(args[0]==="replay-curved-selection-transfer")await new Promise(done=>__release=done);return result};__release=null');
  await fileInput('#curved-transfer-open',source+'/v1-transfer.json');await wait('!!__release');
  await fill('#curved-transfer-current-chart',JSON.stringify(expected.request.reference_vertices[1])+' ');await ev('__release()');
  await wait('!$("error").hidden && $("error").textContent.includes("再検証中")');
  await same('changed chart refuses in-flight saved replay','curvedTransferResult',expected);
  await ev('api=__normalApi');await fill('#curved-transfer-current-chart',JSON.stringify(expected.request.reference_vertices[1]));
  await transfer('intersects');await fill('#curved-selection-angle',1);await click('#curved-selection-append');
  await same('history append uses exactly the transferred native IDs',project,refined);
  await writeFile(out+'/built-project.json',JSON.stringify(await ev(project),null,2));
  await loadMesh();
  await same('appended mesh has the independent native cell count',
    '[...$("curved-selection-mesh").querySelectorAll("[data-cell]")].map(e=>Number(e.dataset.cell))',refinedNative.cell_nodes.map((_,i)=>i));
  await click('#save');
  for(let n=0;n<100 && !(await readdir(out+'/downloads')).includes('cavity-project.json');n++)await sleep(100);
  await open(out+'/downloads/cavity-project.json');await same('saved Project keeps the transferred marked stage',project,refined);
  await select('curved-selection-position','replace');await fill('#curved-selection-stage',1);await loadMesh();await transfer('intersects');
  const rect=await ev('(()=>{const a=$("curved-selection-panel").getBoundingClientRect(),b=$("curved-transfer-controls").getBoundingClientRect();return {x:Math.min(a.x,b.x)+scrollX,y:a.y+scrollY,width:Math.max(a.width,b.width),height:b.bottom-a.top,scale:1}})()');
  const shot=await call('Page.captureScreenshot',{captureBeyondViewport:true,clip:rect},sessionId);
  await writeFile(out+'/selection-charts.png',Buffer.from(shot.data,'base64'));
  await check('no solver jobs were created by geometry operations','document.querySelectorAll("#jobs .job").length===0');
  report.new_fem_solves=0;
  if(args['--native-sources']){
    const nativeRoot=resolve(args['--native-sources']);
    report.saved_native_imports=[];
    await ev('$("import-path").closest("details").open=true');
    for(const scale of [1,2])for(const name of ['previous','current','refined']){
      const path=`${nativeRoot}/scale-${scale}-${name}`;
      const expectedResult=JSON.parse(await readFile(path+'/results.json','utf8'));
      const expectedProject=JSON.parse(await readFile(`${nativeRoot}/scale-${scale}-${name}-project.json`,'utf8'));
      await ev('window.__lastResult=currentResult');
      await fill('#import-path',`${nativeRoot}/managed/scale-${scale}-${name}`);await click('#import-result');
      await wait('currentResult!==__lastResult && $("field-image").naturalWidth>0',120000);
      await same(`saved native ${scale}/${name} retains every RF quantity and metadata`,'currentResult.result',expectedResult);
      await same(`saved native ${scale}/${name} retains the original Project`,'currentResult.project',expectedProject);
      report.saved_native_imports.push({scale,stage:name,path});
      await writeFile(out+`/native-${scale}-${name}-view.json`,JSON.stringify(await ev('currentResult'),null,2));
    }
    const fieldShot=await call('Page.captureScreenshot',{},sessionId);
    await writeFile(out+'/saved-native-field.png',Buffer.from(fieldShot.data,'base64'));
  }

  report.source_changed_during_run=!isDeepStrictEqual(report.source_sha256,await sourceHashes());
  report.passed=!report.source_changed_during_run && report.external_requests.length===0 && report.checks.every(c=>c.passed);
  if(!report.passed)throw Error('Graphical selection checks failed');
  console.log(JSON.stringify({passed:report.passed,checks:report.checks}));
} catch(e){report.error=String(e);process.exitCode=1;console.error(e);}
finally {
  try {
    await writeFile(out + "/report.json", JSON.stringify(report, null, 2));
  } finally {
    for (const entry of pending.values()) clearTimeout(entry.timer);
    try { ws?.close(); } finally { await dispose(); }
  }
}
