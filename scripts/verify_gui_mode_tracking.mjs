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
if (!args["--url"] || !args["--out"] || !args["--sources"])
  throw Error(
    "Usage: node scripts/verify_gui_mode_tracking.mjs --url LAUNCH_URL --out NEW_DIRECTORY --sources CLUSTER_VALIDATION_DIRECTORY",
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
  const check = async (name, expression) => {
    if (!await ev(expression)) throw Error(name);
    report.checks.push({operation:name,passed:true});
  };
  const select = async (id,value) => ev(`(()=>{const e=document.getElementById(${JSON.stringify(id)});e.value=${JSON.stringify(value)};e.dispatchEvent(new Event("change",{bubbles:true}))})()`);
  const loadFile = async filename => {
    const {root}=await call("DOM.getDocument",{},sessionId);
    const {nodeId}=await call("DOM.querySelector",{nodeId:root.nodeId,selector:"#tracking-open"},sessionId);
    await call("DOM.setFileInputFiles",{nodeId,files:[resolve(filename)]},sessionId);
  };
  await ev('document.querySelector("#import-path").closest("details").open=true');
  const imported={},known=new Set();
  for (const stage of ["a","b","c"]) {
    await fill("#import-path",resolve(args["--sources"],stage));await click("#import-result");
    await wait(`document.querySelector("#tracking-current").options.length===${known.size+2}`);
    const ids=await ev('[...document.querySelector("#tracking-current").options].map(x=>x.value).filter(Boolean)');
    imported[stage]=ids.find(id=>!known.has(id));known.add(imported[stage]);
  }
  report.checks.push({operation:"native result import populates completed result selectors",passed:true});
  await select("tracking-previous",imported.a);await select("tracking-current",imported.b);
  await fill("#tracking-ids",'["TM010","TM020","TM011"]');await click("#tracking-retain");
  await click("#tracking-compare");await wait('trackingResult?.document.status==="PASS" && !trackingBusy');
  await check("merge is displayed as a subspace with unresolved individual IDs",'document.querySelector("#tracking-status").textContent.includes("個別IDは未確定") && document.querySelector("#tracking-matches tbody").rows.length===2 && trackingResult.document.tracking.cluster_transitions.events[0].kind==="MERGE"');
  await click("#tracking-start");await wait('trackingResult?.document.document_type==="mode_tracking_history" && !trackingBusy');
  await check("history disables manual previous ID editing",'document.querySelector("#tracking-ids").disabled && document.querySelector("#tracking-previous").disabled && !document.querySelector("#tracking-extend").disabled');
  await select("tracking-current",imported.c);await click("#tracking-extend");
  await wait('trackingResult?.document.steps?.length===2 && !trackingBusy');
  await check("split retains the ID set in the GUI history",'trackingResult.document.status==="PASS" && trackingResult.document.steps.at(-1).tracking.cluster_transitions.events[0].kind==="SPLIT" && trackingResult.document.current_mode_ids[1]===null');
  await click("#tracking-save");
  let downloaded;
  for (let n=0;n<100;n++) {try {downloaded=JSON.parse(await readFile(out+"/downloads/mode-tracking-history.json","utf8"));break;} catch {} await sleep(100);}
  if (!downloaded || !isDeepStrictEqual(downloaded,await ev('trackingResult.document'))) throw Error("download differs from displayed verified history");
  report.checks.push({operation:"download equals the server-verified history",passed:true});
  await click("#tracking-reset");await loadFile(out+"/downloads/mode-tracking-history.json");
  await wait('trackingResult?.document.steps?.length===2 && !trackingBusy');
  await check("file replay restores history and policy controls",'document.querySelector("#tracking-retain").checked && document.querySelector("#tracking-gap").value==="0.001" && !document.querySelector("#tracking-extend").disabled');
  const rect=await ev('(()=>{const r=document.querySelector("#mode-tracking").getBoundingClientRect();return {x:r.x+scrollX,y:r.y+scrollY,width:r.width,height:r.height,scale:1}})()');
  const shot=await call("Page.captureScreenshot",{captureBeyondViewport:true,clip:rect},sessionId);
  await writeFile(out+"/tracking-history.png",Buffer.from(shot.data,"base64"));
  const altered=structuredClone(downloaded);altered.current_identity_groups[0].ids[0]="modified";
  await writeFile(out+"/modified-history.json",JSON.stringify(altered));await loadFile(out+"/modified-history.json");
  await wait('!document.querySelector("#error").hidden && !trackingBusy');
  await check("modified history is rejected without replacing verified data",'trackingResult.document.current_identity_groups[0].ids[0]==="TM010" && document.querySelector("#error").textContent.includes("replay")');
  await click("#tracking-reset");await select("tracking-previous",imported.a);await select("tracking-current",imported.c);
  await fill("#tracking-overlap",1);await click("#tracking-compare");await wait('trackingResult?.document.status==="UNVERIFIED" && !trackingBusy');
  await click("#tracking-start");await wait('trackingResult?.document.document_type==="mode_tracking_history" && !trackingBusy');
  await check("unverified history remains downloadable but cannot extend",'document.querySelector("#tracking-extend").disabled && !document.querySelector("#tracking-save").disabled && document.querySelector("#tracking-status").textContent.includes("継続はできません")');
  if (args["--repartition"]) {
    await click("#tracking-reset");
    await loadFile(resolve(args["--repartition"],"pair-12.json"));
    await wait('trackingResult?.document.tracking?.cluster_transitions?.events[0]?.kind==="REPARTITION" && !trackingBusy');
    await check("repartition replay restores the explicit connected policy",'document.querySelector("#tracking-retain").checked && document.querySelector("#tracking-policy")?.value==="retain_connected_subspace" && !document.querySelector("#tracking-policy-label").hidden');
    await check("repartition shows an ID set and preserves the unrelated individual",'trackingResult.document.tracking.current_mode_ids[0]==="fundamental" && trackingResult.document.tracking.current_mode_ids.slice(1).every(x=>x===null) && document.querySelector("#tracking-status").textContent.includes("個別IDは未確定")');
    await select("tracking-policy","retain_subspace");
    await check("one-to-many policy remains explicitly selectable",'trackingControls().cluster_transition_policy==="retain_subspace"');
    await click("#tracking-retain");
    await check("disabling union omits both optional controls",'!("cluster_transition_policy" in trackingControls()) && !("minimum_cluster_link" in trackingControls()) && document.querySelector("#tracking-policy-label").hidden');
    await click("#tracking-retain");await select("tracking-policy","retain_connected_subspace");
    await fill("#import-path",resolve(args["--repartition"],"native"));await click("#import-result");
    await wait(`document.querySelector("#tracking-current").options.length===${known.size+2}`);
    const nativeId=await ev(`[...document.querySelector("#tracking-current").options].map(x=>x.value).find(x=>x && !${JSON.stringify([...known])}.includes(x))`);
    await click("#tracking-start");await wait('trackingResult?.document.document_type==="mode_tracking_history" && !trackingBusy');
    await select("tracking-current",nativeId);await click("#tracking-extend");
    await wait('trackingResult?.document.steps?.length===2 && !trackingBusy');
    await check("GUI history extension preserves the connected policy and ID union",'trackingResult.document.status==="PASS" && trackingResult.document.steps.at(-1).request.controls.cluster_transition_policy==="retain_connected_subspace" && trackingResult.document.current_identity_groups[1].ids.join(",")==="A,B,C,D"');
    await ev('document.querySelector("#mode-tracking").scrollIntoView({behavior:"instant",block:"start"})');
    const capture=await call("Page.captureScreenshot",{captureBeyondViewport:false},sessionId);
    await writeFile(out+"/connected-policy.png",Buffer.from(capture.data,"base64"));
  }
  report.source_changed_during_run=!isDeepStrictEqual(report.source_sha256,await sourceHashes());
  report.passed=!report.source_changed_during_run && report.external_requests.length===0 && report.checks.every(c=>c.passed);
  if (!report.passed) throw Error("mode tracking GUI checks failed");
  console.log(JSON.stringify({passed:report.passed,checks:report.checks,external_requests:report.external_requests}));
} catch (e) {
  report.error=String(e);process.exitCode=1;console.error(e);
} finally {
  await writeFile(out+"/report.json",JSON.stringify(report,null,2));ws?.close();browser.kill();
}
