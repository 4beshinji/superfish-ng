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
      `UI timeout: ${expression}; ${await ev('document.querySelector("#error")?.textContent')}`,
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
  const begin = performance.now();
  await call("Page.navigate", { url: args["--url"] }, sessionId);
  await wait('document.querySelector("#shape polygon")');
  report.startup_ms = performance.now() - begin;
  const check=async (operation,expression)=>{if (!await ev(expression)) throw Error(operation);report.checks.push({operation,passed:true});};
  const loadFile=async(selector,filename)=>{const {root}=await call('DOM.getDocument',{},sessionId);const {nodeId}=await call('DOM.querySelector',{nodeId:root.nodeId,selector},sessionId);await call('DOM.setFileInputFiles',{nodeId,files:[resolve(filename)]},sessionId);};
  await ev('document.querySelector("#polarization").value="te";document.querySelector("#polarization").dispatchEvent(new Event("change"))');
  await check('TE selection creates an explicit TE model','collect().case.model.polarization==="te" && !document.querySelector("#te-model-note").hidden');
  await fill('#nr',8);await fill('#nz',12);await fill('#modes',1);
  await click('#run');
  await wait('!document.querySelector("#run").disabled && document.querySelector("#jobs .job button")?.textContent==="結果を開く" && !document.querySelector("#jobs .job button").disabled',180000);
  await click('#jobs .job button');
  await wait('currentResult?.result.physics==="axisymmetric_m0_te"',180000);
  await check('ordinary GUI worker solves TE and preserves N/A reason','currentResult.state.status==="complete" && document.querySelector("#rf-table").textContent.includes("N/A")');
  report.job=await ev('currentJob');report.project=await ev('currentResult.project');
  await click('#plot');await wait('!document.querySelector("#plot").disabled && !document.querySelector("#field-image").hidden && document.querySelector("#field-image").naturalWidth>0',180000);
  await check('TE field image loads','document.querySelector("#field-image").naturalWidth>100');
  await ev('document.querySelector("#field-image").scrollIntoView({block:"start"})');
  const screenshot=await call('Page.captureScreenshot',{format:'png'},sessionId);await writeFile(out+'/te-fields.png',Buffer.from(screenshot.data,'base64'));
  const saved=out+'/roundtrip.json';await writeFile(saved,JSON.stringify(report.project));
  await ev('document.querySelector("#polarization").value="tm";document.querySelector("#polarization").dispatchEvent(new Event("change"))');
  await loadFile('#open',saved);await wait('document.querySelector("#polarization").value==="te"');
  report.roundtrip=await ev('(async()=>{const r=await api("normalize",{document:collect()});return r.project})()');
  if(!isDeepStrictEqual(report.roundtrip,report.project))throw Error('TE Project form roundtrip differs after strict normalization');
  report.checks.push({operation:'TE Project reload and form roundtrip preserve the full document',passed:true});
  const downloadProbe = async (prefix,te) => {
    await click('#probe-csv');await click('#probe-metadata');
    let csv,meta;
    for(let n=0;n<1800;n++) {
      try {csv=await readFile(out+'/downloads/radial.csv','utf8');meta=JSON.parse(await readFile(out+'/downloads/radial.csv.json','utf8'));break;}catch{}await sleep(100);
    }
    if(!csv || !meta)throw Error('probe download incomplete');
    const header=csv.split('\n')[0];
    if(te ? !header.includes('Ephi_V_per_m') || !header.includes('Bz_quadrature_T') || meta.physics!=='axisymmetric_m0_te' : !header.includes('Ez_quadrature_V_per_m'))throw Error('probe physics or units disagree');
    await rename(out+'/downloads/radial.csv',out+'/downloads/'+prefix+'.csv');
    await rename(out+'/downloads/radial.csv.json',out+'/downloads/'+prefix+'.csv.json');
    report.checks.push({operation:prefix+' CSV and metadata download with matching physics and SI units',passed:true});
  };
  await downloadProbe('te-p1',true);
  await check('TE disables unsupported TM result assessments','document.querySelector("#pillbox-reference").disabled && document.querySelector("#analyze-band").disabled && document.querySelector("#rf-peaks-assess").disabled && document.querySelector("#rf-peaks-status").textContent.includes("TE")');
  const runAndOpen = async () => {
    const previous=await ev('document.querySelector("#jobs .job")?.dataset.job');
    await click('#run');
    await wait(`!document.querySelector('#run').disabled && document.querySelector('#jobs .job')?.dataset.job!==${JSON.stringify(previous)} && document.querySelector('#jobs .job button')?.textContent==='結果を開く' && !document.querySelector('#jobs .job button').disabled`,180000);
    await click('#jobs .job button');
    await wait('!document.querySelector("#plot").disabled && !document.querySelector("#field-image").hidden && document.querySelector("#field-image").naturalWidth>0',180000);
  };
  await loadFile('#open',resolve('examples/te/sphere.json'));
  await wait('collect().case.mesh.geometry_order===2');
  await runAndOpen();
  await check('curved P2 TE computes and renders through GUI','currentResult.project.case.model.polarization==="te" && currentResult.project.case.mesh.geometry_order===2');
  report.curved_job=await ev('currentJob');report.curved_project=await ev('currentResult.project');
  await downloadProbe('te-curved',true);
  await ev('document.querySelector("#field-image").scrollIntoView({block:"start"})');
  const curvedImage=await call('Page.captureScreenshot',{format:'png'},sessionId);await writeFile(out+'/te-curved.png',Buffer.from(curvedImage.data,'base64'));
  await loadFile('#open',saved);await wait('collect().case.mesh.geometry_order!==2');
  await ev('document.querySelector("#polarization").value="tm";document.querySelector("#polarization").dispatchEvent(new Event("change"))');
  await runAndOpen();
  await check('TM switch restores ordinary TM result and assessments','currentResult.project.case.model.polarization==="tm" && !document.querySelector("#pillbox-reference").disabled && !document.querySelector("#analyze-band").disabled && !document.querySelector("#rf-peaks-assess").disabled && !document.querySelector("#te-model-note").hidden===false');
  report.tm_job=await ev('currentJob');report.tm_project=await ev('currentResult.project');
  await downloadProbe('tm',false);
  report.source_changed_during_run=!isDeepStrictEqual(report.source_sha256,await sourceHashes());
  report.passed=!report.source_changed_during_run && report.external_requests.length===0;
  if(!report.passed)throw Error('TE GUI source/external request check failed');
  console.log(JSON.stringify({passed:report.passed,checks:report.checks}));
} catch(e){report.error=String(e);process.exitCode=1;console.error(e);}
finally{await writeFile(out+'/report.json',JSON.stringify(report,null,2));ws?.close();browser.kill();}
