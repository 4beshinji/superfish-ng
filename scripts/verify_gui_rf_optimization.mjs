// SPDX-License-Identifier: Apache-2.0
// Real local browser input and computation. Requires a running GUI and Chrome.
import { spawn, execFile } from "node:child_process";
import { mkdtemp, readFile, writeFile, mkdir, readdir } from "node:fs/promises";
import { resolve } from "node:path";
import { createHash } from "node:crypto";
import { isDeepStrictEqual, promisify } from "node:util";
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
    "Usage: node scripts/verify_gui_rf_optimization.mjs --url LAUNCH_URL --out NEW_DIRECTORY --request REQUEST_JSON",
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
  execution_scope: args['--checkpoint'] ? 'replay an existing completed checkpoint and inspect its fields; no new FEM or cancellation/resumption test' : 'new worker cancellation, checkpoint resumption and field inspection',
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
  const prefix=request.project.case.mesh.curved_refinement_steps || [];
  if(!args['--workspace'])throw Error('--workspace is required for observing the saved checkpoint before cancellation');
  const loadFile=async(selector,filename)=>{const {root}=await call('DOM.getDocument',{},sessionId);const {nodeId}=await call('DOM.querySelector',{nodeId:root.nodeId,selector},sessionId);await call('DOM.setFileInputFiles',{nodeId,files:[resolve(filename)]},sessionId);};
  request.max_trials=2;const input=out+'/request.json';await writeFile(input,JSON.stringify(request,null,2));
  await loadFile('#rf-opt-request-open',input);await wait('document.querySelector("#rf-opt-request").value.includes("constraint_scales")');
  await check('RF request restores project, constraints and variable order',`document.querySelector('#rf-opt-mode-id').value===${JSON.stringify(request.mode_id)} && ${request.schema_version===3 ? `JSON.stringify(JSON.parse(document.querySelector('#rf-opt-design-variables').value))===JSON.stringify(${JSON.stringify(request.variables)})` : `document.querySelector('#rf-opt-order').value===${JSON.stringify(request.variables[0].name)}`}`);
  if(request.schema_version===3) {
    await check('multivariate input restores units, law terms and RF policy',`document.querySelector('#rf-opt-geometry-kind').value==='harmonic' && !document.querySelector('#rf-opt-harmonic').hidden && document.querySelector('#rf-opt-affine-variables').hidden && document.querySelector('#rf-opt-rf-coordinates').value===${JSON.stringify(request.rf_coordinates)} && JSON.stringify(JSON.parse(document.querySelector('#rf-opt-geometry-terms').value))===JSON.stringify(${JSON.stringify(request.geometry_terms)})`);
    await click('#rf-opt-geometry-template');await wait(`JSON.parse(document.querySelector('#rf-opt-geometry-terms').value)['/curves/0/start_zr_m/0']!==undefined`);
    await check('geometry template respects the declared variable count',`Object.values(JSON.parse(document.querySelector('#rf-opt-geometry-terms').value)).every(terms=>terms[0].powers.length===${request.variables.length} && terms[0].powers.every(p=>p===0))`);
    await fill('#rf-opt-geometry-terms',JSON.stringify(request.geometry_terms));
    const originalVariables=JSON.stringify(request.variables),duplicate=originalVariables.replace('"name":','"name":"duplicate","name":');
    await fill('#rf-opt-design-variables',duplicate);await click('#rf-opt-prepare');await wait('!document.querySelector("#error").hidden');
    await check('duplicate variable keys are rejected during strict preparation','document.querySelector("#error").textContent.includes("duplicate")');
    await fill('#rf-opt-design-variables',originalVariables);
  }
  await fill('#rf-opt-request','');await click('#rf-opt-prepare');await wait('document.querySelector("#rf-opt-request").value.includes("constraint_scales")');
  const prepared=await ev('JSON.parse(document.querySelector("#rf-opt-request").value)');
  if(!isDeepStrictEqual(prepared,request)) {await writeFile(out+'/prepared.json',JSON.stringify(prepared,null,2));throw Error('complete RF request differs after form round trip');}
  report.checks.push({operation:'full RF request form round trip is exact',passed:true});
  await ev('document.querySelector("#rf-optimization").scrollIntoView({block:"start"})');
  const formImage=await call('Page.captureScreenshot',{format:'png'},sessionId);await writeFile(out+'/rf-optimization-form.png',Buffer.from(formImage.data,'base64'));
  await click('#rf-opt-request-save');
  await fill('#rf-opt-request','{"schema_version":1,"schema_version":1}');await click('#rf-opt-start');
  await wait('!rfOptBusy && !document.querySelector("#error").hidden');
  await check('duplicate request keys fail before a worker starts','document.querySelector("#error").textContent.includes("duplicate")');
  await loadFile('#rf-opt-request-open',input);await wait('document.querySelector("#rf-opt-request").value.includes("constraint_scales")');
  if(args['--checkpoint']) {
    report.checkpoint=resolve(args['--checkpoint']);
    await loadFile('#rf-opt-open',report.checkpoint);
    await wait('!rfOptBusy && rfOptResult?.document.status==="SEARCH_COMPLETE"',600000);
    await check('existing completed checkpoint replays without new computation','rfOptResult.document.completed_fem_solves===6 && !rfOptResult.document.can_resume');
    if(!isDeepStrictEqual(await ev('rfOptResult.document.request'),request))throw Error('checkpoint request differs from the declared browser input');
  } else {
  await fill('#rf-opt-limit','');await click('#rf-opt-start');
  await wait('!rfOptBusy && document.querySelector("#rf-opt-job").textContent.includes("RF探索ジョブ:")',600000);
  const first=await ev('document.querySelector("#rf-opt-job").textContent.match(/RF探索ジョブ: ([a-zA-Z0-9-]+)/)[1]');report.first_job=first;
  let prior;const started=performance.now();
  while(performance.now()-started<600000) {try{prior=JSON.parse(await readFile(resolve(args['--workspace'],first,'execution/checkpoint-001.json'),'utf8'));break;}catch{}await sleep(100);}
  if(!prior)throw Error('first RF checkpoint did not finish');
  await wait(`document.querySelector('[data-job="${first}"]')`);await click(`[data-job="${first}"] button`);
  await wait(`document.querySelector('[data-rf-optimization-checkpoints="${first}"]')`);
  await check('running RF worker can be cancelled after its first saved trial',`document.querySelector('[data-job="${first}"] strong').textContent.includes('中止')`);
  await click(`[data-rf-optimization-checkpoints="${first}"]`);await wait('!rfOptBusy && document.querySelector("#rf-opt-checkpoint-index").value==="1"');
  await check('stopped job offers its saved checkpoint','document.querySelector("#rf-opt-checkpoint-index").options[0].textContent.includes("未検証")');
  await click('#rf-opt-checkpoint-open');await wait('!rfOptBusy && rfOptResult?.document.status==="PAUSED"',600000);
  await check('owned checkpoint replays and enables resumption','rfOptResult.document.completed_fem_solves===3 && !document.querySelector("#rf-opt-resume").disabled');
  await click('#rf-opt-save');
  const saved=out+'/downloads/rf-optimization-checkpoint.json';
  for(let n=0;n<100;n++){try{JSON.parse(await readFile(saved,'utf8'));break;}catch{}await sleep(100);}
  await ev('document.querySelector("#rf-opt-job").textContent=""');
  await loadFile('#rf-opt-open',saved);await wait('!rfOptBusy && document.querySelector("#rf-opt-job").textContent.includes("再検証が完了") && rfOptResult?.document.status==="PAUSED"',600000);
  await check('downloaded checkpoint preserves all three source levels','rfOptResult.document.trial_sources_sha256[0].length===3');
  const bad=structuredClone(prior);bad.status='SEARCH_COMPLETE';const badFile=out+'/tampered.json';await writeFile(badFile,JSON.stringify(bad));
  await loadFile('#rf-opt-open',badFile);await wait('!rfOptBusy && !document.querySelector("#error").hidden',600000);
  await check('tampered checkpoint is rejected while previous verified state remains','document.querySelector("#error").textContent.includes("differs") && rfOptResult.document.status==="PAUSED"');
  await fill('#rf-opt-request','{edited and invalid request');await click('#rf-opt-resume');
  await wait('!rfOptBusy && document.querySelector("#rf-opt-job").textContent.includes("RF探索ジョブ:")',600000);
  const second=await ev('document.querySelector("#rf-opt-job").textContent.match(/RF探索ジョブ: ([a-zA-Z0-9-]+)/)[1]');report.resumed_job=second;
  await wait(`document.querySelector('[data-job="${second}"] strong')?.textContent.includes('SEARCH_COMPLETE')`,900000);
  await click(`[data-job="${second}"] button`);await wait('!rfOptBusy && rfOptResult?.document.status==="SEARCH_COMPLETE"',600000);
  await check('resumption uses the verified request and distinguishes budget termination','rfOptResult.document.completed_fem_solves===6 && rfOptResult.document.decision.search_stop==="TRIAL_LIMIT" && document.querySelector("#rf-opt-resume").disabled');
  }
  await check('final assessment uses three independently solved finer levels','JSON.stringify(rfOptResult.document.trials[1].assessment.assessment.rows.map(r=>r.refinement_level))==="[1,2,3]"');
  if(prefix.length) {
    await check('history request and explicit source mesh survive saved resumption',`rfOptResult.document.request.schema_version===${request.schema_version} && JSON.stringify(rfOptResult.document.request.project.mesh_data)===${JSON.stringify(JSON.stringify(request.project.mesh_data))}`);
    await check('RF result explains refinement after the original history',`document.querySelector('#rf-opt-status').textContent.includes('元の細分履歴${prefix.length}段')`);
    // Preserve the server's numeric types. JSON.stringify would change 0.0 to
    // 0 in the saved diagnostics and invalidate their exact replay contract.
    await writeFile(out+'/verified-checkpoint.json',await ev('rfOptResult.serialized'));
    await promisify(execFile)(resolve(args['--python'] || '.venv/bin/python'),['-c',
      'import json,sys; from pathlib import Path; d=json.loads(Path(sys.argv[1]).read_text()); Path(sys.argv[2]).write_text(json.dumps(d["trials"][1]["assessment"]["assessment"],indent=2,allow_nan=False))',
      out+'/verified-checkpoint.json',out+'/surface-assessment.json']);
    await loadFile('#surface-open',out+'/surface-assessment.json');
    await wait('!surfaceBusy && (surfaceResult?.document.schema_version===2 || !document.querySelector("#error").hidden)',600000);
    await check('surface assessment opens without a visible error','surfaceResult?.document.schema_version===2 && document.querySelector("#error").hidden');
    await check('surface report replays its fixed prefix and names additional uniform levels',`document.querySelector('#surface-status').textContent.includes('固定履歴${prefix.length}段') && JSON.stringify(surfaceResult.document.rows.map(r=>r.refinement_level))==='[1,2,3]'`);
  }
  if(request.schema_version===3) {
    await check('trial columns show each variable name and unit',`${JSON.stringify(request.variables)}.every(v=>document.querySelector('#rf-opt-trials thead').textContent.includes(v.name+' ['+(v.unit==='1'?'無次元':v.unit)+']')) && document.querySelector('#rf-opt-trials tbody tr').children.length===${request.variables.length+4}`);
    await check('final comparison derives original history on both actual shape meshes','JSON.stringify(rfOptResult.document.trials[1].tracking.request.controls.comparison_meshes[0])===JSON.stringify(rfOptResult.document.trials[1].tracking.request.controls.comparison_meshes[1])');
  }
  report.result=await ev('rfOptResult.document');
  for(const [trial,level,refinement] of [[0,0,0],[1,2,3]]) {
    await ev(`document.querySelector('#rf-opt-field-trial').value=${JSON.stringify(String(trial))};document.querySelector('#rf-opt-field-trial').dispatchEvent(new Event('change'));document.querySelector('#rf-opt-field-level').value=${JSON.stringify(String(level))}`);
    const meshCondition=prefix.length ? `(currentResult?.project.case.mesh.curved_refinement_steps?.length ?? 0)===${prefix.length+refinement}` : `(currentResult?.project.case.mesh.curved_refinement_levels ?? 0)===${refinement}`;
    await click('#rf-opt-open-field');await wait(`!rfOptBusy && ${meshCondition}`,600000);
    if(prefix.length)await check(`trial ${trial} preserves the source split choices`, `JSON.stringify(currentResult.project.case.mesh.curved_refinement_steps.slice(0,${prefix.length}))===${JSON.stringify(JSON.stringify(prefix))}`);
    await check(`trial ${trial} level ${level} imports the verified target rank`,`currentResult.state.origin==='imported' && document.querySelector('#mode').value==='1' && document.querySelector('#rf-opt-job').textContent.includes('試行 ${trial}')`);
    await click('#plot');await wait('!document.querySelector("#plot").disabled && !document.querySelector("#field-image").hidden && document.querySelector("#field-image").naturalWidth>0',180000);
  }
  await ev('document.querySelector("#rf-opt-status").scrollIntoView({block:"start"})');
  const screenshot=await call('Page.captureScreenshot',{format:'png'},sessionId);await writeFile(out+'/rf-optimization-result.png',Buffer.from(screenshot.data,'base64'));
  await check('RF request editor stays within its panel','document.querySelector("#rf-opt-request").getBoundingClientRect().width<=document.querySelector("#rf-optimization").getBoundingClientRect().width && document.querySelector("#rf-opt-request").getBoundingClientRect().width>.8*document.querySelector("#rf-optimization").getBoundingClientRect().width');
  report.source_changed_during_run=!isDeepStrictEqual(report.source_sha256,await sourceHashes());
  report.passed=!report.source_changed_during_run && report.external_requests.length===0 && report.checks.every(c=>c.passed);
  if(!report.passed)throw Error('RF optimization GUI checks failed');console.log(JSON.stringify({passed:report.passed,checks:report.checks,external_requests:report.external_requests}));
} catch(e){report.error=String(e);process.exitCode=1;console.error(e);}
finally{await writeFile(out+'/report.json',JSON.stringify(report,null,2));ws?.close();browser.kill();}
