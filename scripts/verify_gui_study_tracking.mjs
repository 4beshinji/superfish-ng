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
if (!args["--url"] || !args["--out"])
  throw Error(
    "Usage: node scripts/verify_gui_study_tracking.mjs --url LAUNCH_URL --out NEW_DIRECTORY",
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
      `(()=>{const e=document.querySelector(${JSON.stringify(selector)});e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()`,
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
  const loadFile=async filename=>{const {root}=await call("DOM.getDocument",{},sessionId);const {nodeId}=await call("DOM.querySelector",{nodeId:root.nodeId,selector:"#tracking-open"},sessionId);await call("DOM.setFileInputFiles",{nodeId,files:[resolve(filename)]},sessionId);};
  await wait('[...document.querySelector("#tracking-study").options].some(o=>o.value==="study")');
  await ev('document.querySelector("#tracking-study-panel").open=true;document.querySelector("#tracking-study").value="study"');
  await fill("#tracking-study-ids",'["TM010","TM020","TM011"]');await click("#tracking-retain");
  await click("#tracking-study-run");await wait('trackingResult?.document.document_type==="study_mode_tracking" && !trackingBusy');
  await check("completed Study uses shared controls and displays all point states",'trackingResult.document.status==="PASS" && document.querySelector("#tracking-study-points tbody").rows.length===3 && document.querySelector("#tracking-status").textContent.includes("3/3")');
  await check("Study result cannot be mistaken for an extendable pair history",'document.querySelector("#tracking-start").disabled && document.querySelector("#tracking-extend").disabled && document.querySelector("#tracking-status").textContent.includes("個別IDは未確定")');
  await click("#tracking-save");let downloaded;
  for (let n=0;n<100;n++){try {downloaded=JSON.parse(await readFile(out+"/downloads/study-mode-tracking.json","utf8"));break;}catch{}await sleep(100);}
  if (!downloaded || !isDeepStrictEqual(downloaded,await ev('trackingResult.document'))) throw Error("Study download differs from verified document");
  report.checks.push({operation:"Study document download equals displayed evidence",passed:true});
  await click("#tracking-reset");await loadFile(out+"/downloads/study-mode-tracking.json");await wait('trackingResult?.document.document_type==="study_mode_tracking" && !trackingBusy');
  await check("Study file replay restores IDs and per-step controls",'JSON.parse(document.querySelector("#tracking-study-controls").value).length===2 && JSON.parse(document.querySelector("#tracking-study-ids").value)[0]==="TM010"');
  const changed=structuredClone(downloaded);changed.point_results[0].value=.123;
  await writeFile(out+"/modified-study.json",JSON.stringify(changed));await loadFile(out+"/modified-study.json");await wait('!document.querySelector("#error").hidden && !trackingBusy');
  await check("modified Study tracking is rejected without replacing the last verified result",'document.querySelector("#error").textContent.includes("replay") && trackingResult.document.point_results[0].value===0.055');
  const controls=structuredClone(downloaded.request.step_controls);delete controls[0].cluster_transition_policy;delete controls[0].minimum_cluster_link;
  await fill("#tracking-study-controls",JSON.stringify(controls));await click("#tracking-study-run");await wait('trackingResult?.document.status==="UNVERIFIED" && !trackingBusy');
  await check("first unverified step leaves later Study points visibly unvisited",'trackingResult.document.unvisited_point_indices[0]===2 && document.querySelector("#tracking-study-points tbody").rows[2].textContent.includes("未追跡") && document.querySelector("#tracking-status").textContent.includes("2/3") && !document.querySelector("#tracking-save").disabled');
  const rect=await ev('(()=>{const r=document.querySelector("#mode-tracking").getBoundingClientRect();return {x:r.x+scrollX,y:r.y+scrollY,width:r.width,height:r.height,scale:1}})()');
  const shot=await call("Page.captureScreenshot",{captureBeyondViewport:true,clip:rect},sessionId);await writeFile(out+"/study-tracking.png",Buffer.from(shot.data,"base64"));
  controls[1].unsupported=true;await fill("#tracking-study-controls",JSON.stringify(controls));await click("#tracking-study-run");await wait('!document.querySelector("#error").hidden && !trackingBusy');
  await check("invalid controls in an unvisited step still fail validation",'document.querySelector("#error").textContent.includes("unsupported")');
  report.source_changed_during_run=!isDeepStrictEqual(report.source_sha256,await sourceHashes());report.passed=!report.source_changed_during_run && report.external_requests.length===0 && report.checks.every(c=>c.passed);
  if (!report.passed) throw Error("Study tracking GUI checks failed");console.log(JSON.stringify({passed:report.passed,checks:report.checks,external_requests:report.external_requests}));
} catch(e){report.error=String(e);process.exitCode=1;console.error(e);}
finally {await writeFile(out+"/report.json",JSON.stringify(report,null,2));ws?.close();browser.kill();}
