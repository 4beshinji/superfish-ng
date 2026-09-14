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
if (!args["--url"] || !args["--out"] || !args["--request"])
  throw Error(
    "Usage: node scripts/verify_gui_tracked_execution.mjs --url LAUNCH_URL --out NEW_DIRECTORY --request REQUEST_JSON",
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
  const loadFile=async filename=>{const {root}=await call("DOM.getDocument",{},sessionId);const {nodeId}=await call("DOM.querySelector",{nodeId:root.nodeId,selector:"#tracked-execution-open"},sessionId);await call("DOM.setFileInputFiles",{nodeId,files:[resolve(filename)]},sessionId);};
  const launch=async selector=>{
    const previous=await ev('document.querySelector("#tracked-execution-job").textContent');
    await click(selector);await wait(`!trackedExecutionBusy && document.querySelector("#tracked-execution-job").textContent!==${JSON.stringify(previous)}`);
    return await ev('document.querySelector("#tracked-execution-job").textContent.match(/開始しました: ([a-zA-Z0-9-]+)/)[1]');
  };
  const openJob=async (id,status,count)=>{
    await wait(`document.querySelector('[data-job="${id}"] strong')?.textContent.includes(${JSON.stringify(status)})`,30000);
    await click(`[data-job="${id}"] button`);
    await wait(`!trackedExecutionBusy && trackedExecutionResult?.document.status===${JSON.stringify(status)} && trackedExecutionResult.document.point_runs.length===${count}`);
  };
  await click("#tracked-execution-prepare");await wait('document.querySelector("#tracked-execution-request").value.includes("step_controls")');
  await check("current Study and tracking controls produce a reviewable execution request",'JSON.parse(document.querySelector("#tracked-execution-request").value).study.study_version===1');
  await check("execution request editor uses the available panel width",'document.querySelector("#tracked-execution-request").getBoundingClientRect().width > .8*document.querySelector("#tracked-execution").getBoundingClientRect().width');
  if(args["--recovery"]) {
    const originalJobMessage=await ev('document.querySelector("#tracked-execution-job").textContent');
    await fill("#tracked-execution-request",JSON.stringify(request).replace('"schema_version":2','"schema_version":2,"schema_version":2'));
    await click("#tracked-execution-start");await wait('!trackedExecutionBusy && !document.querySelector("#error").hidden');
    await check("duplicate keys in the original request text are rejected before starting a worker",`document.querySelector("#error").textContent.includes("duplicate JSON key") && document.querySelector("#tracked-execution-job").textContent===${JSON.stringify(originalJobMessage)}`);
  }
  await fill("#tracked-execution-request",JSON.stringify(request));await fill("#tracked-execution-limit","1");
  const first=await launch("#tracked-execution-start");await openJob(first,"PAUSED",1);
  await check("first point can pause without a pair history and shows later points as uncomputed",'trackedExecutionResult.document.history===null && document.querySelector("#tracked-execution-points tbody").rows[1].textContent.includes("未計算") && !document.querySelector("#tracked-execution-resume").disabled');
  await check("tracked jobs are excluded from individual result selectors",`![...document.querySelector("#tracking-current").options].some(o=>o.value===${JSON.stringify(first)})`);
  await click("#tracked-execution-save");let downloaded;
  for (let n=0;n<100;n++){try {downloaded=await readFile(out+"/downloads/tracked-study-checkpoint.json","utf8");break;}catch{}await sleep(100);}
  if (downloaded!==await ev('trackedExecutionResult.serialized'))throw Error("checkpoint download differs from verified text");
  report.checks.push({operation:"checkpoint download preserves original JSON text",passed:true});
  await fill("#tracked-execution-request",'{}');await loadFile(out+"/downloads/tracked-study-checkpoint.json");await wait('!trackedExecutionBusy && JSON.parse(document.querySelector("#tracked-execution-request").value).initial_ids?.[0]==="TM010"');
  await check("checkpoint file replay restores the verified request",'JSON.parse(document.querySelector("#tracked-execution-request").value).initial_ids[0]==="TM010"');
  const changed=JSON.parse(downloaded);changed.point_results[0].value=.123;await writeFile(out+"/modified.json",JSON.stringify(changed));await loadFile(out+"/modified.json");
  await wait('!trackedExecutionBusy && !document.querySelector("#error").hidden');
  await check("modified checkpoint is rejected while the previous verified result remains",'document.querySelector("#error").textContent.includes("replay") && trackedExecutionResult.document.point_results[0].value===.055');
  await fill("#tracked-execution-request",'{}');const second=await launch("#tracked-execution-resume");await openJob(second,"PAUSED",2);
  await check("resume retains saved settings despite editor changes and carries a degenerate ID set",'trackedExecutionResult.document.request.initial_ids[0]==="TM010" && trackedExecutionResult.document.history.current_identity_groups.some(g=>g.ids.length===2) && document.querySelector("#tracked-execution-points tbody").rows[1].textContent.includes("個別ID未確定")');
  let third,afterRecovery;
  if(args["--recovery"]) {
    await fill("#tracked-execution-limit","1");third=await launch("#tracked-execution-resume");await openJob(third,"PAUSED",3);
    await check("a pause at the recovery point preserves individual IDs and visible recovery status",'trackedExecutionResult.document.schema_version===2 && trackedExecutionResult.document.history.current_mode_ids.join(",")==="TM010,TM011,TM020" && document.querySelector("#tracked-execution-points tbody").rows[2].cells[4].textContent==="確認済み" && !document.querySelector("#tracked-execution-resume").disabled');
    const recovered=await ev('trackedExecutionResult.serialized');await writeFile(out+"/recovered-pause.json",recovered);
    await loadFile(out+"/recovered-pause.json");await wait('!trackedExecutionBusy && trackedExecutionResult?.document.history?.individual_ids_complete');
    await check("replayed recovery restores the full plan and earlier-anchor evidence",'JSON.parse(document.querySelector("#tracked-execution-request").value).identity_recoveries.length===2 && JSON.parse(document.querySelector("#tracked-execution-diagnostics").textContent).identity_recoveries[0].request.anchor_snapshot_index===0');
    const forged=JSON.parse(recovered);forged.history.identity_recoveries[0].assessment.current_mode_ids[1]="forged";
    await writeFile(out+"/forged-recovery.json",JSON.stringify(forged));await loadFile(out+"/forged-recovery.json");await wait('!trackedExecutionBusy && !document.querySelector("#error").hidden');
    await check("modified recovery evidence cannot replace a resumable checkpoint",'trackedExecutionResult.document.history.current_mode_ids[1]==="TM011" && !document.querySelector("#tracked-execution-resume").disabled && document.querySelector("#error").textContent.includes("replay")');
    await fill("#tracked-execution-request",'{}');await fill("#tracked-execution-limit","");afterRecovery=await launch("#tracked-execution-resume");await openJob(afterRecovery,"COMPLETE",6);
    await check("resume after recovery crosses the next ordering change and uses a recovered anchor",'trackedExecutionResult.document.point_results[3].current_mode_ids.join(",")==="TM010,TM020,TM011" && trackedExecutionResult.document.history.identity_recoveries.length===2 && trackedExecutionResult.document.history.identity_recoveries[1].request.anchor_snapshot_index===2 && document.querySelector("#tracked-execution-resume").disabled');
    await writeFile(out+"/completed-recovery.json",await ev('trackedExecutionResult.serialized'));
  } else {
    await fill("#tracked-execution-limit","");third=await launch("#tracked-execution-resume");await openJob(third,"COMPLETE",3);
    await check("completed tracking cannot resume and retains the subspace after split",'document.querySelector("#tracked-execution-resume").disabled && trackedExecutionResult.document.history.current_identity_groups.some(g=>g.ids.length===2)');
  }
  const stopped=structuredClone(request);
  if(args["--recovery"])stopped.identity_recoveries[0].point_index=1;
  else for (const c of stopped.step_controls){delete c.cluster_transition_policy;delete c.minimum_cluster_link;}
  await fill("#tracked-execution-request",JSON.stringify(stopped));const fourth=await launch("#tracked-execution-start");await openJob(fourth,"UNVERIFIED",2);
  await check("unverified correspondence stops computation and remains downloadable",'document.querySelector("#tracked-execution-resume").disabled && !document.querySelector("#tracked-execution-save").disabled && document.querySelector("#tracked-execution-points tbody").rows[2].textContent.includes("未計算")');
  if(args["--recovery"]) {
    await check("unverified recovery retains the passing adjacent comparison and leaves the next point uncomputed",'trackedExecutionResult.document.history.steps[0].status==="PASS" && trackedExecutionResult.document.history.identity_recoveries[0].status==="UNVERIFIED" && document.querySelector("#tracked-execution-points tbody").rows[1].cells[4].textContent==="未確認"');
    await writeFile(out+"/unverified-recovery.json",await ev('trackedExecutionResult.serialized'));
  }
  const rect=await ev('(()=>{const r=document.querySelector("#tracked-execution").getBoundingClientRect();return {x:r.x+scrollX,y:r.y+scrollY,width:r.width,height:r.height,scale:1}})()');
  const shot=await call("Page.captureScreenshot",{captureBeyondViewport:true,clip:rect},sessionId);await writeFile(out+"/tracked-execution.png",Buffer.from(shot.data,"base64"));
  const large=structuredClone(request);large.study.project.case.mesh.nr=350;large.study.project.case.mesh.nz=350;
  await fill("#tracked-execution-request",JSON.stringify(large));const fifth=await launch("#tracked-execution-start");
  await wait(`document.querySelector('[data-job="${fifth}"] button')?.textContent==="中止"`);await click(`[data-job="${fifth}"] button`);
  await wait(`document.querySelector('[data-job="${fifth}"] strong')?.textContent.startsWith("中止")`);
  await check("running tracked Study can be cancelled without publishing success",`document.querySelector('[data-job="${fifth}"] button').disabled`);
  report.job_ids={first,second,third,afterRecovery,fourth,fifth};
  report.source_changed_during_run=!isDeepStrictEqual(report.source_sha256,await sourceHashes());report.passed=!report.source_changed_during_run && report.external_requests.length===0 && report.checks.every(c=>c.passed);
  if (!report.passed) throw Error("tracked execution GUI checks failed");console.log(JSON.stringify({passed:report.passed,checks:report.checks,external_requests:report.external_requests}));
} catch(e){report.error=String(e);process.exitCode=1;console.error(e);}
finally {await writeFile(out+"/report.json",JSON.stringify(report,null,2));ws?.close();browser.kill();}
