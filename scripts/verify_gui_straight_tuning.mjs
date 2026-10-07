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
if (!args["--url"] || !args["--out"] || !args["--request"])
  throw Error(
    "Usage: node scripts/verify_gui_straight_tuning.mjs --url LAUNCH_URL --out NEW_DIRECTORY --request REQUEST_JSON",
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

  const request=JSON.parse(await readFile(args["--request"],"utf8"));
  const loadFile=async filename=>{const {root}=await call("DOM.getDocument",{},sessionId);const {nodeId}=await call("DOM.querySelector",{nodeId:root.nodeId,selector:"#tune-open"},sessionId);await call("DOM.setFileInputFiles",{nodeId,files:[resolve(filename)]},sessionId);};
  const launch=async selector=>{
    const old=await ev('document.querySelector("#tune-job").textContent');await click(selector);
    await wait(`!tuningBusy && document.querySelector("#tune-job").textContent!==${JSON.stringify(old)}`);
    return await ev('document.querySelector("#tune-job").textContent.match(/開始しました: ([a-zA-Z0-9-]+)/)[1]');
  };
  const openJob=async(id,status,count)=>{
    await wait(`document.querySelector('[data-job="${id}"] strong')?.textContent.includes(${JSON.stringify(status)})`,60000);
    await click(`[data-job="${id}"] button`);
    await wait(`!tuningBusy && tuningResult?.document.status===${JSON.stringify(status)} && tuningResult.document.trials.length===${count}`,60000);
  };
  if(args["--checkpoint"]) {
    await loadFile(args["--checkpoint"]);
    await wait('!tuningBusy && tuningResult?.document.status==="PAUSED"');
  } else {
    await fill("#tune-request",JSON.stringify(request));await fill("#tune-limit","2");
    report.first=await launch("#tune-start");await openJob(report.first,"PAUSED",2);
  }
  await writeFile(out+"/paused.json",await ev('tuningResult.serialized'));
  report.restored_law=await ev('document.querySelector("#tune-binding-law").value');
  await check("owned straight law is restored as its own editable method",'document.querySelector("#tune-binding-law").value==="straight-piecewise" && !document.querySelector("#tune-straight-settings").hidden');
  if(!isDeepStrictEqual(await ev('JSON.parse(document.querySelector("#tune-straight-law").value)'),request.shape_law))throw Error("restored straight law differs");
  await check("original parameter units and both frequency gates are restored",`document.querySelector("#tune-parameter-unit").value==="1" && Number(document.querySelector("#tune-low").value)===${request.bounds[0]} && Number(document.querySelector("#tune-frequency-tolerance").value)===${request.frequency_tolerance_hz} && Number(document.querySelector("#tune-mesh-tolerance").value)===${request.mesh_frequency_tolerance_hz}`);
  await fill("#tune-request","");await click("#tune-prepare");await wait('document.querySelector("#tune-request").value.includes("shape_law")');
  report.rebuilt=await ev('JSON.parse(document.querySelector("#tune-request").value)');
  if(!isDeepStrictEqual(report.rebuilt,request))throw Error("GUI rebuild differs from original request");
  report.checks.push({operation:"form rebuild preserves the complete original Project, shape law, units and controls",passed:true});
  const prior=await ev('document.querySelector("#tune-job").textContent');
  const law=JSON.stringify(request.shape_law);
  await fill("#tune-straight-law",law.replace('"version":1','"version":1,"version":1'));
  await fill("#tune-request","");await click("#tune-prepare");await wait('document.querySelector("#tune-request").value.includes("shape_law")');
  await click("#tune-start");await wait('!tuningBusy && !document.querySelector("#error").hidden');
  await check("duplicate law keys are rejected before a new worker",`document.querySelector("#error").textContent.includes("duplicate JSON key") && document.querySelector("#tune-job").textContent===${JSON.stringify(prior)}`);
  await fill("#tune-straight-law",law);await fill("#tune-request","");await click("#tune-prepare");await wait('document.querySelector("#tune-request").value.includes("shape_law")');
  await fill("#tune-limit","");report.final=await launch("#tune-resume");await openJob(report.final,"TUNED",4);
  await writeFile(out+"/completed.json",await ev('tuningResult.serialized'));
  await check("resume retains original owned request and both original gates",'tuningResult.document.request.schema_version===9 && tuningResult.document.decision.refined_target_met && tuningResult.document.decision.mesh_difference_met && document.querySelector("#tune-resume").disabled');
  await click("#tune-save");
  let downloaded;
  for(let n=0;n<100;n++){try{downloaded=await readFile(out+"/downloads/tune-checkpoint.json","utf8");break;}catch{}await sleep(100);}
  if(downloaded!==await ev('tuningResult.serialized'))throw Error("download differs from verified text");
  await loadFile(out+"/downloads/tune-checkpoint.json");await wait('!tuningBusy && tuningResult?.document.status==="TUNED"');
  const forged=JSON.parse(downloaded);forged.request.shape_law.bindings[0].vertex=99999;
  await writeFile(out+"/forged.json",JSON.stringify(forged));await loadFile(out+"/forged.json");
  await wait('!tuningBusy && !document.querySelector("#error").hidden');
  await check("a forged original shape law cannot replace the verified result",'tuningResult.document.status==="TUNED" && JSON.parse(document.querySelector("#tune-request").value).shape_law.bindings[0].vertex!==99999');
  const oldJob=await ev('currentJob');await click("#tune-open-field");await wait(`currentJob!==${JSON.stringify(oldJob)} && !document.querySelector("#field-image").hidden`,60000);
  await check("final original field opens at its tracked individual rank",'Number(document.querySelector("#mode").value)===tuningResult.document.trials.at(-1).current_mode_ids.indexOf(tuningResult.document.request.mode_id)+1');
  report.field_job=await ev('currentJob');
  const rect=await ev('(()=>{const r=document.querySelector("#tune-status").getBoundingClientRect(),b=document.querySelector("#tune-trials").getBoundingClientRect();return {x:r.x+scrollX,y:r.y+scrollY,width:r.width,height:b.bottom-r.top,scale:1}})()');
  const shot=await call("Page.captureScreenshot",{captureBeyondViewport:true,clip:rect},sessionId);await writeFile(out+"/tuning-result.png",Buffer.from(shot.data,"base64"));
  report.source_changed_during_run=!isDeepStrictEqual(report.source_sha256,await sourceHashes());
  report.passed=!report.source_changed_during_run && report.external_requests.length===0 && report.checks.every(c=>c.passed);
  if(!report.passed)throw Error("straight tuning GUI checks failed");
  console.log(JSON.stringify({passed:report.passed,checks:report.checks,external_requests:report.external_requests}));
} catch(e){report.error=String(e);process.exitCode=1;console.error(e);}
finally {
  try {
    await writeFile(out + "/report.json", JSON.stringify(report, null, 2));
  } finally {
    for (const entry of pending.values()) clearTimeout(entry.timer);
    try { ws?.close(); } finally { await dispose(); }
  }
}
