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
    "Usage: node scripts/verify_gui_planar_similarity_remesh_tracking.mjs --url LAUNCH_URL --out NEW_DIRECTORY",
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

  const template=JSON.parse(await readFile('examples/planar/project_triangle_tm.json','utf8'));
  const scale=.7,angle=.31,tx=.04,ty=-.03,cosine=Math.cos(angle),sine=Math.sin(angle);
  const transform=([x,y])=>[scale*(cosine*x-sine*y)+tx,scale*(sine*x+cosine*y)+ty];
  const makeProject=(n,flipped,mapped)=>{const p=structuredClone(template),points=[],triangles=[];p.case.name=mapped?'transformed interior mesh':'original square mesh';
    const corners=[[0,0],[.2,0],[.2,.2],[0,.2]].map(mapped?transform:v=>v);
    for(let j=0;j<=n;j++)for(let i=0;i<=n;i++){const v=[.2*(i/n),.2*(j/n)];points.push(mapped?transform(v):v);}
    for(let j=0;j<n;j++)for(let i=0;i<n;i++){const a=j*(n+1)+i,b=a+1,d=a+n+1,c=d+1;triangles.push(...(flipped?[[a,b,d],[b,c,d]]:[[a,b,c],[a,c,d]]));}
    p.case.geometry.vertices_xy_m=corners;p.case.mesh={points_xy_m:points,triangles,element_order:2};return p;};
  await writeFile(out+'/previous-project.json',JSON.stringify(makeProject(6,false,false)));await loadFile('#open',out+'/previous-project.json');await wait('project.case.name==="original square mesh"');
  report.previous=await execute('#start','','selected');await click('#tracking-select-previous');
  await writeFile(out+'/current-project.json',JSON.stringify(makeProject(6,true,true)));await loadFile('#open',out+'/current-project.json');await wait('project.case.name==="transformed interior mesh"');report.current=await execute('#start','','selected');
  await ev('document.querySelector("#tracking-mapping").value="polygon_similarity_remesh";document.querySelector("#tracking-mapping").dispatchEvent(new Event("change"))');await click('#tracking-select-current');
  await fill('#tracking-scale',scale);await fill('#tracking-angle',angle);await fill('#tracking-translation-x',tx);await fill('#tracking-translation-y',ty);await fill('#tracking-previous-count',1);await fill('#tracking-current-count',1);await fill('#tracking-ids','["fundamental"]');await fill('#tracking-candidate-tests',123456);
  report.tracking=await execute('#tracking-start','モード追跡','selectedTracking');report.request=await ev('currentTracking.request');
  await check('composed similarity and independent interior track the original field','currentTracking.result.status==="PASS" && currentTracking.result.result_version===5 && currentTracking.result.current_mode_ids[0]==="fundamental"');
  await check('composed declaration and physical mapping are saved','currentTracking.result.physical_mapping.name==="polygon_similarity_remesh" && currentTracking.result.physical_mapping.declaration.max_candidate_tests===123456 && currentTracking.result.physical_mapping.current_to_previous_rotation.length===2');
  await click('#tracking-save');if(!isDeepStrictEqual(JSON.parse(await download('planar-tracking-request.json')),report.request))throw Error('request download differs');
  await fill('#tracking-candidate-tests',1);await loadFile('#tracking-open',out+'/downloads/planar-tracking-request.json');await wait('document.querySelector("#tracking-candidate-tests").value==="123456"');
  if(!isDeepStrictEqual(await ev('trackingFromForm()'),report.request))throw Error('request form differs');report.checks.push({operation:'composed declaration, rotation and budget roundtrip',passed:true});
  await click('#tracking-result-save');if(!isDeepStrictEqual(JSON.parse(await download('planar-tracking-results.json')),await ev('currentTracking.result')))throw Error('result download differs');report.checks.push({operation:'composed full result download matches replay',passed:true});
  await click('#tracking-current-import');await wait(`selected!==${JSON.stringify(report.current)}`);report.imported=await ev('selected');await click('#plot');await wait('!document.querySelector("#image").hidden && document.querySelector("#image").naturalWidth>100',90000);report.checks.push({operation:'transformed native is imported and plotted',passed:true});
  await click('#history-select-tracking');report.first_history=await execute('#history-start','追跡履歴','selectedHistory');
  await ev(`document.querySelector('#tracking-previous').value=${JSON.stringify(report.current)};document.querySelector('#tracking-current').value=${JSON.stringify(report.previous)};document.querySelector('#tracking-inverse').checked=true;`);
  report.reverse=await execute('#tracking-start','モード追跡','selectedTracking');await check('reverse declared composed pair preserves the ID','currentTracking.result.status==="PASS" && currentTracking.result.current_mode_ids[0]==="fundamental" && currentTracking.request.mapping.inverse===true');
  await ev(`document.querySelector('#history-next').value=${JSON.stringify(report.reverse)}`);report.extended_history=await execute('#history-extend','追跡履歴','selectedHistory');
  await check('owned history replays the composed and reverse steps','currentHistory.result.can_extend && currentHistory.result.steps.length===2 && currentHistory.result.current_mode_ids[0]==="fundamental"');
  const before=await ev('JSON.stringify(trackingFromForm())');await writeFile(out+'/invalid.json',JSON.stringify({...report.request,mapping:{...report.request.mapping,shear:0}}));await loadFile('#tracking-open',out+'/invalid.json');await wait('!document.querySelector("#error").hidden');if(await ev('JSON.stringify(trackingFromForm())')!==before)throw Error('unsupported map changed inputs');report.checks.push({operation:'unsupported composed map fields preserve inputs',passed:true});
  await call('Page.navigate',{url:launch.origin+'/planar.html?job='+report.reverse},sessionId);await wait(`typeof selectedTracking!=='undefined' && selectedTracking===${JSON.stringify(report.reverse)}`,90000);
  await check('URL restores composed controls and hides refinement fields','Math.abs(trackingFromForm().mapping.scale-.7)<1e-12 && trackingFromForm().mapping.max_candidate_tests===123456 && !document.querySelector("#tracking-remesh-options").hidden && !document.querySelector("#tracking-similarity-options").hidden && document.querySelector("#tracking-refinement-options").hidden');
  await ev('document.querySelector("#tracking-result").scrollIntoView({block:"start"})');const screenshot=await call('Page.captureScreenshot',{format:'png'},sessionId);await writeFile(out+'/similarity-remesh-tracking.png',Buffer.from(screenshot.data,'base64'));
  report.source_changed_during_run=!isDeepStrictEqual(report.source_sha256,await sourceHashes());report.passed=!report.source_changed_during_run&&report.external_requests.length===0;
  if(!report.passed)throw Error('source or external HTTP changed');console.log(JSON.stringify({passed:true,checks:report.checks}));
} catch(e){report.error=String(e);process.exitCode=1;console.error(e);}
finally{await writeFile(out+'/report.json',JSON.stringify(report,null,2));ws?.close();if(browser.exitCode===null){browser.kill();await new Promise(resolve=>browser.once('exit',resolve));}}
