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
    "Usage: node scripts/verify_gui_adaptive_execution.mjs --url LAUNCH_URL --out NEW_DIRECTORY --request REQUEST_JSON",
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
    await wait(`!trackedExecutionBusy && trackedExecutionResult?.document.status===${JSON.stringify(status)} && trackedExecutionResult.document.attempts?.length===${count}`);
  };
  await click("#tracked-execution-adaptive");await click("#tracked-execution-prepare");
  await wait('JSON.parse(document.querySelector("#tracked-execution-request").value || "{}").adaptive?.max_depth===4');
  await check("adaptive controls produce an explicit reviewable request",'!document.querySelector("#tracked-adaptive-settings").hidden && JSON.parse(document.querySelector("#tracked-execution-request").value).adaptive.max_attempts===16');
  if(args["--recovery"]) {
    const previousMessage=await ev('document.querySelector("#tracked-execution-job").textContent');
    await fill("#tracked-execution-request",JSON.stringify(request).replace('"schema_version":2','"schema_version":2,"schema_version":2'));
    await click("#tracked-execution-start");await wait('!trackedExecutionBusy && !document.querySelector("#error").hidden');
    await check("duplicate original recovery request keys are rejected before worker creation",`document.querySelector("#error").textContent.includes("duplicate JSON key") && document.querySelector("#tracked-execution-job").textContent===${JSON.stringify(previousMessage)}`);
  }
  await fill("#tracked-execution-request",JSON.stringify(request));await fill("#tracked-execution-limit","1");
  const first=await launch("#tracked-execution-start");await openJob(first,"PAUSED",1);
  await check("failed coarse comparison pauses for bisection and distinguishes computed from accepted points",'document.querySelector("#tracked-execution-status").textContent.includes("計算済み 2 点、採用 1 点") && document.querySelector("#tracked-adaptive-attempts tbody").rows[0].textContent.includes("UNVERIFIED") && document.querySelector("#tracked-adaptive-attempts tbody").rows[0].textContent.includes("二分") && document.querySelector("#tracked-adaptive-pending").textContent.includes("0.0675")'.replace('0.0675',args['--recovery'] ? '0.0475' : '0.0675'));
  await check("adaptive job is excluded from individual result selectors",`![...document.querySelector("#tracking-current").options].some(o=>o.value===${JSON.stringify(first)})`);
  await click("#tracked-execution-save");let downloaded;
  for(let n=0;n<100;n++){try{downloaded=await readFile(out+"/downloads/adaptive-study-checkpoint.json","utf8");break;}catch{}await sleep(100);}
  if(downloaded!==await ev('trackedExecutionResult.serialized'))throw Error("adaptive checkpoint download differs from verified text");
  report.checks.push({operation:"adaptive download preserves exact checkpoint text",passed:true});
  if(args["--recovery"])await writeFile(out+"/initial-checkpoint.json",downloaded);
  await fill("#tracked-execution-request",'{}');await fill("#tracked-adaptive-depth","0");await loadFile(out+"/downloads/adaptive-study-checkpoint.json");
  await wait('!trackedExecutionBusy && JSON.parse(document.querySelector("#tracked-execution-request").value).adaptive?.max_depth===4');
  await check("file replay restores the adaptive settings and enables pending work",'document.querySelector("#tracked-adaptive-depth").value==="4" && !document.querySelector("#tracked-execution-resume").disabled');
  const changed=JSON.parse(downloaded);changed.attempts[0].decision="ACCEPT";await writeFile(out+"/modified.json",JSON.stringify(changed));await loadFile(out+"/modified.json");
  await wait('!trackedExecutionBusy && !document.querySelector("#error").hidden');
  await check("modified decision is rejected without replacing verified failure evidence",'document.querySelector("#error").textContent.includes("replay") && trackedExecutionResult.document.attempts[0].decision==="BISECT"');
  await fill("#tracked-execution-request",'{}');await click("#tracked-execution-adaptive");const second=await launch("#tracked-execution-resume");await openJob(second,"PAUSED",2);
  await check("resume uses saved adaptive settings and adds only the midpoint to accepted points",'trackedExecutionResult.document.request.adaptive.max_depth===4 && trackedExecutionResult.document.points.length===3 && trackedExecutionResult.document.accepted_point_indices.length===2 && document.querySelector("#tracked-adaptive-points tbody").rows[2].textContent.includes("追加点")');
  let third,recoveredJob,finalJob;
  if(args["--recovery"]) {
    await fill("#tracked-execution-limit","1");third=await launch("#tracked-execution-resume");await openJob(third,"PAUSED",3);
    await check("the declared anchor is reached after the inserted midpoint",'trackedExecutionResult.document.accepted_point_indices.join(",")==="0,2,1" && trackedExecutionResult.document.reached_target_indices.join(",")==="0,1"');
    await fill("#tracked-execution-limit","2");recoveredJob=await launch("#tracked-execution-resume");await openJob(recoveredJob,"PAUSED",5);
    await check("recovery binds original target one to accepted snapshot two",'trackedExecutionResult.document.schema_version===3 && trackedExecutionResult.document.attempts[4].identity_recovery.anchor_target_index===1 && trackedExecutionResult.document.attempts[4].identity_recovery.anchor_snapshot_index===2 && trackedExecutionResult.document.history.current_mode_ids.join(",")==="TM010,TM011,TM020" && document.querySelector("#tracked-adaptive-attempts tbody").rows[4].cells[8].textContent.includes("目標 3 ← 1: 確認済み")');
    const verified=await ev('trackedExecutionResult.serialized');await click("#tracked-execution-save");let saved;
    for(let n=0;n<100;n++){try{saved=await readFile(out+"/downloads/adaptive-study-checkpoint.json","utf8");if(saved===verified)break;}catch{}await sleep(100);}
    if(saved!==verified)throw Error("recovery checkpoint download differs");await writeFile(out+"/recovered-checkpoint.json",saved);
    await loadFile(out+"/recovered-checkpoint.json");await wait('!trackedExecutionBusy && trackedExecutionResult?.document.history?.individual_ids_complete');
    await check("saved recovery replays with its original-target plan and actual binding",'JSON.parse(document.querySelector("#tracked-execution-request").value).identity_recoveries[0].anchor_target_index===1 && JSON.parse(document.querySelector("#tracked-execution-diagnostics").textContent).identity_recoveries[0].anchor_snapshot_index===2');
    const forged=JSON.parse(saved);forged.attempts[4].identity_recovery.anchor_snapshot_index=1;
    await writeFile(out+"/forged-binding.json",JSON.stringify(forged));await loadFile(out+"/forged-binding.json");await wait('!trackedExecutionBusy && !document.querySelector("#error").hidden');
    await check("changing the target-to-history binding does not replace the verified checkpoint",'trackedExecutionResult.document.attempts[4].identity_recovery.anchor_snapshot_index===2 && document.querySelector("#error").textContent.includes("replay") && !document.querySelector("#tracked-execution-resume").disabled');
    await fill("#tracked-execution-request",'{}');await fill("#tracked-execution-limit","");finalJob=await launch("#tracked-execution-resume");await openJob(finalJob,"COMPLETE",7);
    await check("resume reuses a previously recovered original target after later grouping",'trackedExecutionResult.document.history.identity_recoveries.length===2 && trackedExecutionResult.document.attempts[6].identity_recovery.anchor_target_index===3 && trackedExecutionResult.document.attempts[6].identity_recovery.anchor_snapshot_index===4 && trackedExecutionResult.document.points.length===7 && document.querySelector("#tracked-execution-resume").disabled');
    await writeFile(out+"/completed-recovery.json",await ev('trackedExecutionResult.serialized'));
  } else {
    await fill("#tracked-execution-limit","");third=await launch("#tracked-execution-resume");await openJob(third,"COMPLETE",3);
    await check("completed adaptive execution retains failed comparisons and the accepted parameter order",'document.querySelector("#tracked-execution-resume").disabled && trackedExecutionResult.document.accepted_point_indices.join(",")==="0,2,1" && document.querySelector("#tracked-adaptive-attempts tbody").rows.length===3 && document.querySelector("#tracked-adaptive-attempts tbody").rows[0].textContent.includes("UNVERIFIED")');
  }
  const capture=async name=>{const rect=await ev('(()=>{const r=document.querySelector("#tracked-execution").getBoundingClientRect();return {x:r.x+scrollX,y:r.y+scrollY,width:r.width,height:r.height,scale:1}})()');const shot=await call("Page.captureScreenshot",{captureBeyondViewport:true,clip:rect},sessionId);await writeFile(out+"/"+name,Buffer.from(shot.data,"base64"));};
  await capture("adaptive-complete.png");
  const stopped=structuredClone(request);
  if(args["--recovery"])stopped.identity_recoveries[0].target_index=2;else stopped.adaptive.max_depth=0;
  await fill("#tracked-execution-request",JSON.stringify(stopped));const fourth=await launch("#tracked-execution-start");await openJob(fourth,"UNVERIFIED",args["--recovery"] ? 4 : 1);
  if(args["--recovery"]) {
    await check("failed recovery retains the accepted prefix and stops before later targets",'trackedExecutionResult.document.stop_reason==="identity_recovery_unverified" && trackedExecutionResult.document.accepted_point_indices.join(",")==="0,2,1" && trackedExecutionResult.document.attempts[3].correspondence.status==="PASS" && document.querySelector("#tracked-adaptive-attempts tbody").rows[3].cells[8].textContent.includes("未確認") && document.querySelector("#tracked-execution-status").textContent.includes("個別ID回復が未確認") && document.querySelector("#tracked-execution-resume").disabled && !document.querySelector("#tracked-execution-save").disabled');
    await writeFile(out+"/unverified-recovery.json",await ev('trackedExecutionResult.serialized'));
  } else {
    await check("depth limit shows unreached targets and prohibits resume while allowing download",'document.querySelector("#tracked-execution-status").textContent.includes("二分深さの上限") && document.querySelector("#tracked-adaptive-pending").textContent.includes("未到達の元目標番号: 1") && document.querySelector("#tracked-execution-resume").disabled && !document.querySelector("#tracked-execution-save").disabled');
  }
  await capture("adaptive-stopped.png");
  const large=structuredClone(request);large.study.project.case.mesh.nr=350;large.study.project.case.mesh.nz=350;await fill("#tracked-execution-request",JSON.stringify(large));const fifth=await launch("#tracked-execution-start");
  await wait(`document.querySelector('[data-job="${fifth}"] button')?.textContent==="中止"`);await click(`[data-job="${fifth}"] button`);await wait(`document.querySelector('[data-job="${fifth}"] strong')?.textContent.startsWith("中止")`);
  await check("running adaptive job can be cancelled without opening a false completed result",`document.querySelector('[data-job="${fifth}"] button').disabled`);
  report.job_ids={first,second,third,recoveredJob,finalJob,fourth,fifth};report.source_changed_during_run=!isDeepStrictEqual(report.source_sha256,await sourceHashes());
  report.passed=!report.source_changed_during_run && report.external_requests.length===0 && report.checks.every(c=>c.passed);
  if(!report.passed)throw Error("adaptive GUI verification failed");console.log(JSON.stringify({passed:report.passed,checks:report.checks,external_requests:report.external_requests}));
}catch(e){report.error=String(e);process.exitCode=1;console.error(e);}
finally{await writeFile(out+"/report.json",JSON.stringify(report,null,2));ws?.close();browser.kill();}
