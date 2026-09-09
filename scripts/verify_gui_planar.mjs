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

  const launch=new URL(args['--url']);launch.pathname='/planar.html';
  await call('Page.navigate',{url:launch.href},sessionId);
  await wait('document.querySelector("#width")?.value==="310"');
  const check=async(operation,expression)=>{if(!await ev(expression))throw Error(operation);report.checks.push({operation,passed:true});};
  const loadFile=async(filename)=>{const {root}=await call('DOM.getDocument',{},sessionId);const {nodeId}=await call('DOM.querySelector',{nodeId:root.nodeId,selector:'#open'},sessionId);await call('DOM.setFileInputFiles',{nodeId,files:[resolve(filename)]},sessionId);};
  const readDownload=async(name)=>{for(let n=0;n<300;n++){try{return await readFile(out+'/downloads/'+name);}catch{}await sleep(100);}throw Error('download absent: '+name);};
  const runAndOpen=async()=>{const previous=await ev('document.querySelector("#jobs .job")?.dataset.job');await click('#start');await wait(`document.querySelector('#jobs .job')?.dataset.job!==${JSON.stringify(previous)} && document.querySelector('#jobs .job button')?.textContent==='結果を開く' && !document.querySelector('#jobs .job button').disabled`,90000);const next=await ev('document.querySelector("#jobs .job").dataset.job');await click('#jobs .job button');await wait(`selected===${JSON.stringify(next)} && !document.querySelector('#result').hidden`);return next;};
  await fill('#nx',8);await fill('#ny',6);await fill('#modes',2);
  report.rectangle_job=await runAndOpen();report.rectangle_project=await ev('project');
  await check('rectangle TE worker and per-length RF/N/A','result.case.model.polarization==="te" && document.querySelector("#quantities").textContent.includes("J/m") && document.querySelector("#quantities").textContent.includes("W/m") && document.querySelector("#na").textContent.includes("N/A")');
  await click('#plot');await wait('!document.querySelector("#image").hidden && document.querySelector("#image").naturalWidth>100',90000);
  await check('signed TE field image fits viewport','document.querySelector("#image").getBoundingClientRect().right<=innerWidth');
  await click('#save-image');await readDownload('planar-fields.png');
  await click('#save');const saved=await readDownload('planar-project.json');
  if(!isDeepStrictEqual(JSON.parse(saved),report.rectangle_project))throw Error('saved Project differs');
  await click('#new');await wait('document.querySelector("#nx").value==="16"');await loadFile(out+'/downloads/planar-project.json');await wait('document.querySelector("#nx").value==="8"');
  await check('Project file roundtrip preserves full form','JSON.stringify(documentFromForm())===JSON.stringify(project)');
  await ev('document.querySelector("#unit").value="m";document.querySelector("#unit").dispatchEvent(new Event("change"))');
  await wait('document.querySelector("#width").value==="0.31"');
  await check('display unit changes without changing SI width','documentFromForm().case.geometry.width_m===0.31 && documentFromForm().display_length_unit==="m"');
  await fill('#points','[[0.03,0.02],[0.21,0.11]]');await click('#probe');await click('#probe-meta');
  const csv=await readDownload('planar-probe.csv'),meta=JSON.parse(await readDownload('planar-probe.csv.json'));
  if(createHash('sha256').update(csv).digest('hex')!==meta.data_sha256 || csv.toString().split('\n')[0].split(',').length!==14)throw Error('probe download integrity or columns');
  report.probe_metadata=meta;report.checks.push({operation:'SI E/H probe CSV and metadata hash download',passed:true});
  await fill('#points','[[9,9]]');await click('#probe');await wait('!document.querySelector("#error").hidden');await check('exterior probe rejected','document.querySelector("#error").textContent.includes("inside")');
  await loadFile('examples/planar/project_triangle_tm.json');await wait('project.case.schema_version===2 && document.querySelector("#rectangle").hidden');
  report.polygon_job=await runAndOpen();report.polygon_project=await ev('project');
  await check('explicit polygon mesh preserved through worker','JSON.stringify(documentFromForm())===JSON.stringify(project) && result.case.model.polarization==="tm"');
  await click('#plot');await wait('!document.querySelector("#image").hidden && document.querySelector("#image").naturalWidth>100',90000);
  await ev('document.querySelector("#image").scrollIntoView({block:"center"})');const screenshot=await call('Page.captureScreenshot',{format:'png'},sessionId);await writeFile(out+'/polygon-fields.png',Buffer.from(screenshot.data,'base64'));
  await click('#files button');await readDownload('case.json');
  if(!isDeepStrictEqual(JSON.parse(await readDownload('case.json')),report.polygon_project.case))throw Error('native download differs');
  report.checks.push({operation:'polygon native download preserves declared mesh',passed:true});

  const polygonProject=report.polygon_project;
  const sourcePath=resolve(args['--workspace']||'out/planar-gui-browser-20260910')+'/'+report.polygon_job;
  for(const suffix of ['/solution','']){
    const previousImport=await ev('selected');
    await fill('#import-path',sourcePath+suffix);await click('#import');
    await wait(`selected!==null && selected!==${JSON.stringify(previousImport)} && project.case.schema_version===2 && document.querySelector('#selection').textContent.includes(selected)`);
    const imported=await ev('selected');
    if(!isDeepStrictEqual(await ev('project.case'),polygonProject.case))throw Error('import mesh changed');
    report.imports??=[];report.imports.push(imported);
  }
  report.rerun_job=await runAndOpen();
  if(!isDeepStrictEqual(await ev('project'),polygonProject))throw Error('managed import rerun changed Project');
  report.checks.push({operation:'direct and managed import followed by explicit-mesh rerun',passed:true});
  const invalid=out+'/invalid.json';await writeFile(invalid,JSON.stringify({...polygonProject,unsupported:true}));
  await loadFile(invalid);await wait('!document.querySelector("#error").hidden');
  if(!isDeepStrictEqual(await ev('project'),polygonProject))throw Error('invalid Project replaced current input');
  report.checks.push({operation:'unknown Project key rejected without replacing input',passed:true});
  await click('#new');await wait('project.case.schema_version===1 && document.querySelector("#nx").value==="16"');await fill('#nx',300);await fill('#ny',300);await click('#start');await wait('document.querySelector("#jobs .job button")?.textContent==="中止"');
  report.cancelled_job=await ev('document.querySelector("#jobs .job").dataset.job');await click('#jobs .job button');await wait('document.querySelector("#jobs .job strong")?.textContent.startsWith("cancelled")',30000);
  report.checks.push({operation:'actual planar worker cancellation',passed:true});
  await click('nav a');await wait('document.querySelector("#shape polygon")');
  await check('planar jobs excluded from axisymmetric tracking selectors','[...document.querySelectorAll("#tracking-previous option,#tracking-current option")].every(o=>!'+JSON.stringify([report.rectangle_job,report.polygon_job])+'.includes(o.value))');
  await click('a[href="/planar.html"]');await wait('document.querySelector("#width")?.value==="310"');
  await call('Page.navigate',{url:launch.origin+'/planar.html?job='+report.polygon_job},sessionId);await wait(`typeof selected!=="undefined" && selected===${JSON.stringify(report.polygon_job)}`);
  await check('page reload restores polygon from persistent job','project.case.schema_version===2 && result.case.model.polarization==="tm"');
  report.source_changed_during_run=!isDeepStrictEqual(report.source_sha256,await sourceHashes());
  report.passed=!report.source_changed_during_run&&report.external_requests.length===0;
  if(!report.passed)throw Error('source/external request check failed');
  console.log(JSON.stringify({passed:report.passed,checks:report.checks}));
} catch(e){report.error=String(e);process.exitCode=1;console.error(e);}
finally{await writeFile(out+'/report.json',JSON.stringify(report,null,2));ws?.close();if(browser.exitCode===null){browser.kill();await new Promise(resolve=>browser.once('exit',resolve));}}
