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
    "Usage: node scripts/verify_gui_tuning.mjs --url LAUNCH_URL --out NEW_DIRECTORY --request REQUEST_JSON",
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
  await click("#tune-prepare");await wait('document.querySelector("#tune-request").value.includes("target_hz")');
  await check("form builds an SI request from current geometry and tracking controls",'JSON.parse(document.querySelector("#tune-request").value).target_hz===2000000000 && JSON.parse(document.querySelector("#tune-request").value).parameter==="/case/geometry/points_zr_m/1/0"');
  await check("request editor fills its panel",'document.querySelector("#tune-request").getBoundingClientRect().width>.8*document.querySelector("#tuning").getBoundingClientRect().width');
  await fill("#tune-request",JSON.stringify(request));await fill("#tune-limit","2");
  const first=await launch("#tune-start");await openJob(first,"PAUSED",2);
  await check("paused tune displays tracked rank crossing and permits resume",'tuningResult.document.trials[0].current_mode_ids.indexOf("TM011")===2 && tuningResult.document.trials[1].current_mode_ids.indexOf("TM011")===1 && !document.querySelector("#tune-resume").disabled');
  await check("tune jobs are excluded from individual result selectors",`![...document.querySelector("#tracking-current").options].some(o=>o.value===${JSON.stringify(first)})`);
  await click("#tune-save");let downloaded;
  for(let n=0;n<100;n++){try{downloaded=await readFile(out+"/downloads/tune-checkpoint.json","utf8");break;}catch{}await sleep(100);}
  if(downloaded!==await ev('tuningResult.serialized'))throw Error("download differs from verified text");
  report.checks.push({operation:"checkpoint download preserves server-verified JSON text",passed:true});
  await fill("#tune-request",'{}');await loadFile(out+"/downloads/tune-checkpoint.json");await wait('!tuningBusy && JSON.parse(document.querySelector("#tune-request").value).mode_id==="TM011"');
  await check("checkpoint replay restores editable settings",'document.querySelector("#tune-mode-id").value==="TM011" && document.querySelector("#tune-low").value==="0.06"');
  const changed=JSON.parse(downloaded);changed.trials[0].value=.5;await writeFile(out+"/modified.json",JSON.stringify(changed));await loadFile(out+"/modified.json");
  await wait('!tuningBusy && !document.querySelector("#error").hidden');
  await check("modified checkpoint cannot replace the verified result",'document.querySelector("#error").textContent.includes("replay") && tuningResult.document.trials[0].value===.06');
  await fill("#tune-request",'{}');await fill("#tune-limit","");const second=await launch("#tune-resume");await openJob(second,"TUNED",17);
  await check("resume uses verified settings and separates final frequency gates",'tuningResult.document.request.mode_id==="TM011" && tuningResult.document.decision.refined_target_met && tuningResult.document.decision.mesh_difference_met && document.querySelector("#tune-gates").textContent.includes("粗細差: 条件内") && document.querySelector("#tune-resume").disabled');
  await check("trial table distinguishes final refinement",'document.querySelector("#tune-trials tbody").rows[16].textContent.includes("最終細分")');
  const rect=await ev('(()=>{const r=document.querySelector("#tune-status").getBoundingClientRect(),b=document.querySelector("#tune-trials").getBoundingClientRect();return {x:r.x+scrollX,y:r.y+scrollY,width:r.width,height:b.bottom-r.top,scale:1}})()');
  const shot=await call("Page.captureScreenshot",{captureBeyondViewport:true,clip:rect},sessionId);await writeFile(out+"/tuning-result.png",Buffer.from(shot.data,"base64"));
  const oldJob=await ev('currentJob');await click("#tune-open-field");await wait(`currentJob!==${JSON.stringify(oldJob)} && document.querySelector("#mode").value==="2" && !document.querySelector("#field-image").hidden`,60000);
  await check("final field opens the tracked mode rather than frequency rank one",'Number(document.querySelector("#mode").value)===tuningResult.document.trials.at(-1).current_mode_ids.indexOf("TM011")+1');
  const unresolved=structuredClone(request);unresolved.controls.minimum_overlap=1;
  await fill("#tune-request",JSON.stringify(unresolved));const third=await launch("#tune-start");await openJob(third,"UNVERIFIED",2);
  await check("unverified correspondence cannot resume or open a tuned field",'document.querySelector("#tune-resume").disabled && document.querySelector("#tune-open-field").disabled && document.querySelector("#tune-trials tbody").rows[1].textContent.includes("評価不可")');
  const fine=structuredClone(request);fine.mesh_frequency_tolerance_hz=1;
  await fill("#tune-request",JSON.stringify(fine));const fourth=await launch("#tune-start");await openJob(fourth,"REFINEMENT_FAILED",17);
  await check("failed mesh gate is visible despite completed execution",'document.querySelector("#tune-gates").textContent.includes("粗細差: 未達") && document.querySelector("#tune-open-field").disabled && !document.querySelector("#tune-save").disabled');
  const large=structuredClone(request);large.project.case.mesh.nr=350;large.project.case.mesh.nz=350;
  await fill("#tune-request",JSON.stringify(large));const fifth=await launch("#tune-start");
  await wait(`document.querySelector('[data-job="${fifth}"] button')?.textContent==="中止"`);await click(`[data-job="${fifth}"] button`);
  await wait(`document.querySelector('[data-job="${fifth}"] strong')?.textContent.startsWith("中止")`);
  await check("active tuning can be cancelled without publishing success",`document.querySelector('[data-job="${fifth}"] button').disabled`);
  await click(`[data-tune-checkpoints="${fifth}"]`);await wait('!tuningBusy && document.querySelector("#tune-checkpoint-job").textContent.includes("保存済み試行はありません")');
  await check("cancelled job without saved trials cannot open a checkpoint",'document.querySelector("#tune-checkpoint-open").disabled');
  await click(`[data-tune-checkpoints="${first}"]`);await wait('!tuningBusy && document.querySelector("#tune-checkpoint-index").options.length===2');
  await check("checkpoint list labels unverified candidates and defaults to latest",'document.querySelector("#tune-checkpoint-index").value==="2" && document.querySelector("#tune-checkpoint-index").textContent.includes("未検証")');
  await ev('document.querySelector("#tune-checkpoint-index").value="1"');await click("#tune-checkpoint-open");
  await wait('!tuningBusy && tuningResult.document.trials.length===1');
  await check("selected earlier checkpoint is verified before enabling resume",'tuningResult.document.status==="PAUSED" && !document.querySelector("#tune-resume").disabled');
  if(args["--workspace"]) {
    const recoverable=structuredClone(request);recoverable.project.case.mesh.nr=64;recoverable.project.case.mesh.nz=64;
    await fill("#tune-request",JSON.stringify(recoverable));await fill("#tune-limit","");
    const interrupted=await launch("#tune-start");let saved=false;
    for(let n=0;n<300;n++){try{JSON.parse(await readFile(resolve(args["--workspace"],interrupted,"execution/checkpoint-001.json"),"utf8"));saved=true;break;}catch{}await sleep(20);}
    if(!saved)throw Error("recoverable checkpoint was not saved");
    await click(`[data-job="${interrupted}"] button`);
    await wait(`document.querySelector('[data-job="${interrupted}"] strong')?.textContent.startsWith("中止")`);
    await click(`[data-tune-checkpoints="${interrupted}"]`);await wait('!tuningBusy && document.querySelector("#tune-checkpoint-index").options.length>0');
    await ev('document.querySelector("#tune-checkpoint-index").value="1"');await click("#tune-checkpoint-open");
    await wait('!tuningBusy && tuningResult.document.request.project.case.mesh.nr===64 && tuningResult.document.trials.length===1');
    await fill("#tune-limit","1");const resumed=await launch("#tune-resume");await openJob(resumed,"PAUSED",2);
    await check("cancelled tuning resumes from the selected saved trial",`tuningResult.document.trial_runs[0].includes(${JSON.stringify(interrupted)}) && tuningResult.document.trial_runs[1].includes(${JSON.stringify(resumed)})`);
    const rect=await ev('(()=>{const a=document.querySelector("#tune-checkpoint-job").getBoundingClientRect(),b=document.querySelector("#tune-trials").getBoundingClientRect();return {x:a.x+scrollX,y:a.y+scrollY,width:a.width,height:b.bottom-a.top,scale:1}})()');
    const shot=await call("Page.captureScreenshot",{captureBeyondViewport:true,clip:rect},sessionId);await writeFile(out+"/checkpoint-recovery.png",Buffer.from(shot.data,"base64"));
    report.recovery_job_ids={interrupted,resumed};
  }
  if(args["--coupled"]) {
    const coupled=JSON.parse(await readFile(args["--coupled"],"utf8"));
    await click("#tune-coupled");
    await ev('document.querySelector("#tune-parameter-unit").value="1";document.querySelector("#tune-parameter-unit").dispatchEvent(new Event("change"))');
    await fill("#tune-bindings",JSON.stringify(coupled.bindings));await click("#tune-prepare");
    await wait('JSON.parse(document.querySelector("#tune-request").value).schema_version===2');
    await check("coupled form generates explicit bindings and dimensionless units",'JSON.parse(document.querySelector("#tune-request").value).schema_version===2 && JSON.parse(document.querySelector("#tune-request").value).bindings.length===2 && JSON.parse(document.querySelector("#tune-request").value).parameter_unit==="1" && document.querySelector(".tune-unit-label").textContent==="無次元" && document.querySelector("#tune-vertex").disabled');
    await fill("#tune-request",JSON.stringify(coupled));await fill("#tune-limit","2");
    const coupledFirst=await launch("#tune-start");await openJob(coupledFirst,"PAUSED",2);
    await check("saved coupled request restores bindings and variable heading",'document.querySelector("#tune-coupled").checked && document.querySelector("#tune-variable-heading").textContent==="radius [無次元]" && JSON.parse(document.querySelector("#tune-bindings").value)[0].multiplier===.1');
    const expected=await ev('tuningResult.serialized');await click("#tune-save");let coupledDownload;
    for(let n=0;n<100;n++){try{const candidate=await readFile(out+"/downloads/tune-checkpoint.json","utf8");if(candidate===expected){coupledDownload=candidate;break;}}catch{}await sleep(100);}
    if(!coupledDownload)throw Error("coupled download differs from verified text");
    await loadFile(out+"/downloads/tune-checkpoint.json");await wait('!tuningBusy && tuningResult.document.request.schema_version===2');
    report.checks.push({operation:"coupled checkpoint download and replay retain original JSON",passed:true});
    const modified=JSON.parse(coupledDownload);modified.request.bindings[0].multiplier=.11;
    await writeFile(out+"/modified-binding.json",JSON.stringify(modified));await loadFile(out+"/modified-binding.json");await wait('!tuningBusy && !document.querySelector("#error").hidden');
    await check("changed binding cannot replace verified coupled data",'tuningResult.document.request.bindings[0].multiplier===.1 && document.querySelector("#error").textContent.includes("constant radius")');
    await click("#tune-coupled");await fill("#tune-request",'{}');await fill("#tune-limit","");
    const coupledLast=await launch("#tune-resume");await openJob(coupledLast,"TUNED",15);
    await check("coupled resume retains saved variable despite form changes",'document.querySelector("#tune-coupled").checked && tuningResult.document.request.parameter_unit==="1" && tuningResult.document.decision.mesh_difference_met');
    await click("#tune-open-field");await wait('document.querySelector("#mode").value==="1" && currentResult.result.case.geometry.points_zr_m[0][1]===currentResult.result.case.geometry.points_zr_m[1][1] && !document.querySelector("#field-image").hidden',60000);
    await check("final coupled field retains a cylinder at the tuned radius",'Math.abs(currentResult.result.case.geometry.points_zr_m[0][1]/.093-1)<.00002');
    const rect=await ev('(()=>{const a=document.querySelector("#tune-status").getBoundingClientRect(),b=document.querySelector("#tune-trials").getBoundingClientRect();return {x:a.x+scrollX,y:a.y+scrollY,width:a.width,height:b.bottom-a.top,scale:1}})()');
    const image=await call("Page.captureScreenshot",{captureBeyondViewport:true,clip:rect},sessionId);await writeFile(out+"/coupled-result.png",Buffer.from(image.data,"base64"));
    report.coupled_job_ids={coupledFirst,coupledLast};
  }
  if(args["--polynomial"]) {
    const polynomial=JSON.parse(await readFile(args["--polynomial"],"utf8"));
    await ev('document.querySelector("#tune-coupled").checked=true;document.querySelector("#tune-binding-law").value="polynomial";document.querySelector("#tune-binding-law").dispatchEvent(new Event("change"));document.querySelector("#tune-parameter-unit").value="1"');
    await fill("#tune-bindings",JSON.stringify(polynomial.bindings));await click("#tune-prepare");
    await wait('JSON.parse(document.querySelector("#tune-request").value).schema_version===3');
    await check("polynomial form creates ascending-power coefficients and shows units",'JSON.parse(document.querySelector("#tune-request").value).bindings[0].coefficients[2]===.1 && !document.querySelector("#tune-polynomial-help").hidden');
    await fill("#tune-request",JSON.stringify(polynomial));await fill("#tune-limit","2");
    const polynomialFirst=await launch("#tune-start");await openJob(polynomialFirst,"PAUSED",2);
    await check("polynomial result restores law and coefficients",'document.querySelector("#tune-binding-law").value==="polynomial" && JSON.parse(document.querySelector("#tune-bindings").value)[0].coefficients[2]===.1');
    await ev('document.querySelector("#tune-binding-law").value="linear"');await fill("#tune-request",'{}');await fill("#tune-limit","");
    const polynomialLast=await launch("#tune-resume");
    await wait(`document.querySelector('[data-job="${polynomialLast}"] strong')?.textContent.includes("TUNED")`,60000);
    await click(`[data-job="${polynomialLast}"] button`);await wait('!tuningBusy && tuningResult.document.status==="TUNED"');
    await check("polynomial resume retains saved nonlinear law and refinement gates",'document.querySelector("#tune-binding-law").value==="polynomial" && Math.abs(tuningResult.document.decision.value/Math.sqrt(.93)-1)<.00002 && tuningResult.document.decision.mesh_difference_met');
    await click("#tune-open-field");await wait('document.querySelector("#mode").value==="1" && Math.abs(currentResult.result.case.geometry.points_zr_m[0][1]/.093-1)<.00002 && !document.querySelector("#field-image").hidden',60000);
    await check("polynomial tuning final field has the independently expected radius",'currentResult.result.case.geometry.points_zr_m[0][1]===currentResult.result.case.geometry.points_zr_m[1][1]');
    const rect=await ev('(()=>{const a=document.querySelector("#tune-status").getBoundingClientRect(),b=document.querySelector("#tune-trials").getBoundingClientRect();return {x:a.x+scrollX,y:a.y+scrollY,width:a.width,height:b.bottom-a.top,scale:1}})()');
    const shot=await call("Page.captureScreenshot",{captureBeyondViewport:true,clip:rect},sessionId);await writeFile(out+"/polynomial-result.png",Buffer.from(shot.data,"base64"));
    report.polynomial_job_ids={polynomialFirst,polynomialLast};
  }
  if(args["--curved"]) {
    const curved=JSON.parse(await readFile(args["--curved"],"utf8"));
    await ev(`applyProject(${JSON.stringify(curved.project)})`);
    await ev('document.querySelector("#tune-coupled").checked=true;document.querySelector("#tune-binding-law").value="affine";document.querySelector("#tune-parameter-unit").value="1";tuningParameterMode()');
    await fill("#tune-affine-coefficients",JSON.stringify(curved.affine_coefficients));await click("#tune-prepare");
    await wait('JSON.parse(document.querySelector("#tune-request").value).schema_version===4');
    await check("curved form generates affine laws and derives correspondence per trial",'JSON.parse(document.querySelector("#tune-request").value).controls.mapping==="affine_remesh" && !("affine_map" in JSON.parse(document.querySelector("#tune-request").value).controls) && !document.querySelector("#tune-affine-settings").hidden && document.querySelector("#tune-profile-bindings").hidden');
    await fill("#tune-request",JSON.stringify(curved));await fill("#tune-limit","2");
    const curvedFirst=await launch("#tune-start");await openJob(curvedFirst,"PAUSED",2);
    await check("curved result restores coefficients and RF coordinate policy",'document.querySelector("#tune-binding-law").value==="affine" && document.querySelector("#tune-rf-coordinates").value==="axial" && JSON.parse(document.querySelector("#tune-affine-coefficients").value).radial_scale[1]===1');
    await fill("#tune-affine-coefficients",'{}');await fill("#tune-limit","");
    const curvedLast=await launch("#tune-resume");await openJob(curvedLast,"TUNED",4);
    await check("curved resume restores saved law and accepts fixed geometry refinement",'Math.abs(tuningResult.document.decision.value-1.1)<1e-12 && tuningResult.document.decision.mesh_difference_met && JSON.parse(document.querySelector("#tune-affine-coefficients").value).radial_scale[1]===1');
    const previous=await ev('currentJob');await click("#tune-open-field");
    await wait(`currentJob!==${JSON.stringify(previous)} && currentResult?.result.case.geometry.type==="curved_contour" && !document.querySelector("#field-image").hidden`,60000);
    await check("curved final field retains quadratic geometry and explicit partition",'currentResult.result.case.mesh.geometry_order===2 && currentResult.result.case.geometry.segments_per_curve.length===2');
    report.curved_job_ids={curvedFirst,curvedLast};
  }
  if(args["--mesh-project"]) {
    const expected=JSON.parse(await readFile(args["--mesh-project"],"utf8"));
    const {root}=await call("DOM.getDocument",{},sessionId);const {nodeId}=await call("DOM.querySelector",{nodeId:root.nodeId,selector:"#open"},sessionId);
    await call("DOM.setFileInputFiles",{nodeId,files:[resolve(args["--mesh-project"])]},sessionId);
    await wait('explicitProjectMesh!==null && document.querySelector("#explicit-project-mesh").textContent.includes("明示元メッシュ")');
    await check("project form preserves embedded mesh and version",`collect().project_version===2 && JSON.stringify(collect().mesh_data)===JSON.stringify(${JSON.stringify(expected.mesh_data)})`);
    if(expected.case.geometry.segments_per_curve)await check("fixed native partition is restored in the form",`JSON.stringify(collect().case.geometry.segments_per_curve)===JSON.stringify(${JSON.stringify(expected.case.geometry.segments_per_curve)}) && document.querySelector("#curve-fixed-segments").value!==""`);
    const launched=await ev('(async()=>{const result=await api("start",{document:await preview()});await refreshJobs();return result.id})()');
    await wait(`document.querySelector('[data-job="${launched}"] strong')?.textContent.includes("完了")`,60000);
    await click(`[data-job="${launched}"] button`);await wait(`currentJob===${JSON.stringify(launched)} && !document.querySelector("#field-image").hidden`,60000);
    await check("completed explicit mesh job restores embedded input",`collect().project_version===2 && JSON.stringify(collect().mesh_data)===JSON.stringify(${JSON.stringify(expected.mesh_data)})`);
    await click("#save");let saved;
    for(let n=0;n<100;n++){try{for(const file of await readdir(out+"/downloads")){if(file!=="tune-checkpoint.json" && file.endsWith('.json')){const candidate=JSON.parse(await readFile(out+"/downloads/"+file,"utf8"));if(candidate.project_version===2)saved=candidate;}}if(saved)break;}catch{}await sleep(100);}
    if(!saved || JSON.stringify(saved.mesh_data)!==JSON.stringify(expected.mesh_data))throw Error('saved project dropped explicit mesh');
    if(expected.case.geometry.segments_per_curve && JSON.stringify(saved.case.geometry.segments_per_curve)!==JSON.stringify(expected.case.geometry.segments_per_curve))throw Error('saved project dropped curve partition');
    report.checks.push({operation:"GUI download retains exact explicit mesh",passed:true});
    await click("#refine-prepare");await wait('document.querySelector("#refine-request").value.trim().startsWith("{") && JSON.parse(document.querySelector("#refine-request").value).initial_mesh!==null');
    await check("adaptive request retains explicitly supplied initial mesh",`JSON.stringify(JSON.parse(document.querySelector("#refine-request").value).initial_mesh)===JSON.stringify(${JSON.stringify(expected.mesh_data)})`);
    if(args["--mesh-import"]) {
      await click("#mesh-detach");await wait('explicitProjectMesh===null');
      await check("detach restores generated mesh input",'collect().project_version===1 && !("mesh_data" in collect())');
      const file=out+"/standalone-mesh.json";await writeFile(file,JSON.stringify(expected.mesh_data));
      const loadMesh=async path=>{const {root}=await call("DOM.getDocument",{},sessionId);const {nodeId}=await call("DOM.querySelector",{nodeId:root.nodeId,selector:"#mesh-open"},sessionId);await call("DOM.setFileInputFiles",{nodeId,files:[path]},sessionId);};
      await loadMesh(file);await wait('explicitProjectMesh!==null && document.querySelector("#error").hidden');
      await check("standalone mesh import preserves numbered connectivity",`JSON.stringify(collect().mesh_data)===JSON.stringify(${JSON.stringify(expected.mesh_data)})`);
      const bad=out+"/duplicate-mesh.json";await writeFile(bad,'{"schema_version":1,"schema_version":1}');await loadMesh(bad);
      await wait('!document.querySelector("#error").hidden');
      await check("invalid duplicate-key mesh import keeps current input",`document.querySelector("#error").textContent.includes("duplicate") && JSON.stringify(collect().mesh_data)===JSON.stringify(${JSON.stringify(expected.mesh_data)})`);
      await ev('document.querySelector("#study-kind").value="fixed_geometry_convergence";document.querySelector("#study-kind").dispatchEvent(new Event("change"))');
      await wait('document.querySelector("#study-parameter").value==="additional_uniform_refinements"');
      await check("straight explicit mesh exposes fixed-domain refinement",'document.querySelector("#study-hint").textContent.includes("P1/P2")');
      const studyJob=await ev('(async()=>{const r=await api("start-study",{study:await studyDefinition()});await refreshJobs();return r.id})()');
      await wait(`document.querySelector('[data-job="${studyJob}"] strong')?.textContent.includes("完了")`,60000);
      await click(`[data-job="${studyJob}"] button`);await wait('activeStudy?.geometry_refinement?.includes("same polygonal domain")');
      await check("imported mesh study computes and displays both refinements",'activeStudy.points.length===2 && activeStudy.study.project.mesh_data!==undefined && !document.querySelector("#study-chart").hidden');
      report.mesh_study_job=studyJob;
    }
    await click("#new");await wait('explicitProjectMesh===null');
    await check("new project clears the previous embedded mesh",'collect().project_version===1 && !("mesh_data" in collect())');
    report.mesh_job=launched;
  }
  report.job_ids={first,second,third,fourth,fifth};
  report.source_changed_during_run=!isDeepStrictEqual(report.source_sha256,await sourceHashes());report.passed=!report.source_changed_during_run && report.external_requests.length===0 && report.checks.every(c=>c.passed);
  if(!report.passed)throw Error("tuning GUI checks failed");console.log(JSON.stringify({passed:report.passed,checks:report.checks,external_requests:report.external_requests}));
} catch(e){report.error=String(e);process.exitCode=1;console.error(e);}
finally{await writeFile(out+"/report.json",JSON.stringify(report,null,2));ws?.close();browser.kill();}
