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
if (!args['--url'] || !args['--out'] || !args['--sources']) throw Error('Require --url --out --sources');
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
  scope: 'native P2 boundary generation documents, strict replay, stale response guards and real Study worker',
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




  const sources=resolve(args['--sources']);
  const expected=JSON.parse(await readFile(sources+'/study-v2.json','utf8'));
  const expectedGeneration=JSON.parse(await readFile(sources+'/v2-generation.json','utf8'));
  const loadFile=async(selector,path)=>{const {root}=await call('DOM.getDocument',{},sessionId);const {nodeId}=await call('DOM.querySelector',{nodeId:root.nodeId,selector},sessionId);await call('DOM.setFileInputFiles',{nodeId,files:[resolve(path)]},sessionId);};
  const select=async(id,value)=>ev(`(()=>{const e=$(${JSON.stringify(id)});e.value=${JSON.stringify(value)};e.dispatchEvent(new Event('change',{bubbles:true}))})()`);
  const restore=async(path,version)=>{await loadFile('#study-remesh-generation-open',path);await wait(`!remeshGenerationBusy && remeshGenerationResult?.settings.schema_version===${version}`,60000);};
  const assertDocument=async()=>{if(!isDeepStrictEqual(await ev('remeshGenerationResult'),expectedGeneration))throw Error('GUI document differs from complete API generation');};
  await loadFile('#open',sources+'/source-project.json');
  await wait('explicitProjectMesh?.triangles.length===26');
  await select('study-kind','curved_remesh_sweep');
  await wait('!$("study-remesh").hidden && $("study-parameter").options.length===1');
  await ev('$("study-remesh-generation-settings").closest("details").open=true');
  await fill('#study-remesh-cutover',.75);
  await fill('#study-harmonic-parameter',expected.parameter);await select('study-harmonic-unit',expected.parameter_unit);
  await select('study-harmonic-rf',expected.rf_coordinates);await fill('#study-harmonic-angle',expected.minimum_corner_angle_deg);
  await fill('#study-harmonic-coefficients',JSON.stringify(expected.geometry_coefficients));await fill('#study-values',expected.values.join(', '));
  if(args['--restore-document']) {
    await fill('#modes',2);
    await restore(args['--restore-document'],2);await assertDocument();
    if(!isDeepStrictEqual(await ev('preview()'),expectedGeneration.source_project))throw Error('Fresh server/browser restoration lost source Project');
    if(!isDeepStrictEqual(await ev('studyDefinition()'),expected))throw Error('Fresh server/browser restoration lost Study plan');
    report.checks.push({operation:'fresh server and browser replay restore original Project, settings, frozen plan and Study definition',passed:true});
  } else {
    await check('initial controls retain legacy settings and have no unsaved generation artifact','JSON.parse($("study-remesh-generation-settings").value).schema_version===1 && $("study-remesh-generation-save").disabled');
    await select('study-remesh-generation-template-version','2');
    await check('selecting a version does not silently rewrite raw settings','JSON.parse($("study-remesh-generation-settings").value).schema_version===1');
    await click('#study-remesh-generation-template');
    if(!isDeepStrictEqual(await ev('JSON.parse($("study-remesh-generation-settings").value)'),expectedGeneration.settings))throw Error('Version 2 template differs from declared settings');
    report.checks.push({operation:'explicit version 2 template supplies native boundary policy and both budgets',passed:true});
    await click('#study-remesh-generate');await wait('!remeshGenerationBusy && remeshGenerationResult?.settings.schema_version===2',60000);
    await assertDocument();
    if(!isDeepStrictEqual(await ev('preview()'),expectedGeneration.source_project))throw Error('Generation changed source Project');
    if(!isDeepStrictEqual(await ev('JSON.parse($("study-remesh-schedule").value)'),expected.mesh_schedule))throw Error('Generated Study schedule differs');
    report.checks.push({operation:'version 2 generates complete API-identical document and schedule without modifying Project',passed:true});
    await check('all final geometry measurements and physical-accuracy limits are visible','$("study-remesh-generation-status").textContent.includes("設定版2") && $("study-remesh-generation-status").textContent.includes("境界辺 10 → 28") && $("study-remesh-generation-status").textContent.includes("弦面積") && $("study-remesh-generation-status").textContent.includes("P2隅角") && $("study-remesh-generation-status").textContent.includes("RF精度は未検証")');
    await click('#study-remesh-generation-save');
    let saved;
    for(let n=0;n<300;n++){try{saved=JSON.parse(await readFile(out+'/downloads/curved-remesh-generation.json','utf8'));break;}catch{}await sleep(100);}
    if(!isDeepStrictEqual(saved,expectedGeneration))throw Error('Generation download lost document fields');
    report.checks.push({operation:'download contains full source Project, settings, frozen plan, all validation and null error bound',passed:true});
    const retained=await ev('$("study-remesh-schedule").value');
    for(const [label,settings,needle] of [
      ['duplicate raw settings',JSON.stringify(expectedGeneration.settings).replace('"schema_version":2','"schema_version":2,"schema_version":2'),'duplicate JSON key'],
      ['impossible boundary budget',JSON.stringify({...expectedGeneration.settings,max_boundary_edges:9}),'max_boundary_edges']]) {
      await fill('#study-remesh-generation-settings',settings);await click('#study-remesh-generate');
      await wait(`!remeshGenerationBusy && !$("error").hidden && $("error").textContent.includes(${JSON.stringify(needle)})`,60000);
      await assertDocument();if(await ev('$("study-remesh-schedule").value')!==retained)throw Error(label+' replaced previous plan');
      report.checks.push({operation:label+' rejected with previous document and plan preserved',passed:true});
    }
    await fill('#study-remesh-generation-settings',JSON.stringify(expectedGeneration.settings));
    for(const [label,edit,reset] of [
      ['settings',()=>fill('#study-remesh-generation-settings',JSON.stringify({...expectedGeneration.settings,max_rounds:21})),()=>fill('#study-remesh-generation-settings',JSON.stringify(expectedGeneration.settings))],
      ['Project',()=>fill('#modes',2),()=>fill('#modes',1)],
      ['history',()=>select('curved-refinement-mode','levels'),()=>select('curved-refinement-mode','steps')]]) {
      await ev('window.__remeshApi=api;window.__remeshRelease=null;api=async(...args)=>{const r=await __remeshApi(...args);if(args[0]==="generate-curved-remesh-plan")await new Promise(done=>window.__remeshRelease=done);return r}');
      await click('#study-remesh-generate');await wait('!!window.__remeshRelease',60000);await edit();await ev('__remeshRelease()');
      await wait('!remeshGenerationBusy && !$("error").hidden && $("error").textContent.includes("メッシュ生成中に入力が変わりました")');
      await assertDocument();if(await ev('$("study-remesh-schedule").value')!==retained)throw Error('Stale '+label+' changed schedule');
      await ev('api=__remeshApi');await reset();report.checks.push({operation:'in-flight generation rejects changed '+label+' and retains previous verified result',passed:true});
    }
    const duplicate=JSON.stringify(saved).replace('"seed_triangle_count":8','"seed_triangle_count":8,"seed_triangle_count":8');
    await writeFile(out+'/duplicate-generation.json',duplicate);
    const changed=structuredClone(saved);changed.validation.prefix_boundary_edge_counts[0]=9;await writeFile(out+'/tampered-generation.json',JSON.stringify(changed));
    for(const [file,needle] of [['duplicate-generation.json','duplicate JSON key'],['tampered-generation.json','full reconstruction']]) {
      await loadFile('#study-remesh-generation-open',out+'/'+file);
      await wait(`!remeshGenerationBusy && !$("error").hidden && $("error").textContent.includes(${JSON.stringify(needle)})`,60000);
      await assertDocument();if(await ev('$("study-remesh-schedule").value')!==retained)throw Error('Rejected file changed plan');
      report.checks.push({operation:file+' rejected before editor restoration',passed:true});
    }
    for(const action of ['replay-curved-remesh-generation','normalize']) {
      await ev(`window.__remeshApi=api;window.__remeshRelease=null;api=async(...args)=>{const r=await __remeshApi(...args);if(args[0]===${JSON.stringify(action)})await new Promise(done=>window.__remeshRelease=done);return r}`);
      await loadFile('#study-remesh-generation-open',sources+'/v1-generation.json');await wait('!!window.__remeshRelease',60000);
      await fill('#modes',2);await ev('__remeshRelease()');
      await wait('!remeshGenerationBusy && !$("error").hidden && $("error").textContent.includes("入力が変わりました")');
      await assertDocument();await check('stale '+action+' preserves edited Project and current plan','$("modes").value==="2"');
      await ev('api=__remeshApi');await fill('#modes',1);
    }
    await ev('window.__originalFileText=File.prototype.text;window.__fileRelease=null;File.prototype.text=async function(){const text=await __originalFileText.call(this);await new Promise(done=>window.__fileRelease=done);return text}');
    await loadFile('#study-remesh-generation-open',sources+'/v1-generation.json');await wait('!!window.__fileRelease');await fill('#study-remesh-cutover',.6);await ev('__fileRelease()');
    await wait('!remeshGenerationBusy && !$("error").hidden && $("error").textContent.includes("生成文書の読込中に入力が変わりました")');
    await ev('File.prototype.text=__originalFileText');await fill('#study-remesh-cutover',.75);await assertDocument();
    report.checks.push({operation:'stale raw file read does not issue a restore or overwrite current document',passed:true});
    await restore(sources+'/v1-generation.json',1);
    await check('legacy generation document restores explicit version 1 semantics','JSON.parse($("study-remesh-generation-settings").value).schema_version===1 && $("study-remesh-generation-template-version").value==="1"');
    await fill('#modes',2);await restore(out+'/downloads/curved-remesh-generation.json',2);await assertDocument();
    if(!isDeepStrictEqual(await ev('preview()'),expectedGeneration.source_project))throw Error('Restore did not restore original Project');
    if(!isDeepStrictEqual(await ev('studyDefinition()'),expected))throw Error('Restore changed Study definition');
    report.checks.push({operation:'complete replay restores original Project, settings, source mesh, history and current-cutover plan',passed:true});
    await click('#save-study');let study;
    for(let n=0;n<300;n++){try{study=JSON.parse(await readFile(out+'/downloads/study.json','utf8'));break;}catch{}await sleep(100);}
    if(!isDeepStrictEqual(study,expected))throw Error('Downloaded Study differs from complete native definition');
    report.checks.push({operation:'downloaded Study retains generated portable plan and original geometry laws',passed:true});
    await ev('window.__remeshJobApi=api;window.__remeshStudyJob=null;api=async(...args)=>{const r=await __remeshJobApi(...args);if(args[0]==="start-study")window.__remeshStudyJob=r.id;return r}');
    await click('#start-study');await wait('!!window.__remeshStudyJob');
    const job=await ev('__remeshStudyJob'),selector=`#jobs .job[data-job="${job}"]`;
    await wait(`document.querySelector(${JSON.stringify(selector+' strong')})?.textContent.startsWith("計算完了")`,240000);
    await click(selector+' button');await wait('activeStudy?.study.kind==="curved_remesh_sweep"',240000);
    const result=await ev('activeStudy');if(!isDeepStrictEqual(result.study,expected))throw Error('Worker changed generated plan');
    await writeFile(out+'/study-result.json',JSON.stringify(result,null,2));await writeFile(out+'/study-job.json',JSON.stringify({id:job}));
    await check('real worker reports independent spectra and preserves every mode/RF quantity','activeStudy.points.length===2 && activeStudy.comparisons.length===0 && activeStudy.numerical_status==="UNVERIFIED"');
  }
  const rect=await ev('(()=>{const r=$("study-remesh").getBoundingClientRect();return {x:r.x+scrollX,y:r.y+scrollY,width:r.width,height:r.height,scale:1}})()');
  const shot=await call('Page.captureScreenshot',{captureBeyondViewport:true,clip:rect},sessionId);await writeFile(out+'/boundary-generation.png',Buffer.from(shot.data,'base64'));
  report.source_changed_during_run=!isDeepStrictEqual(report.source_sha256,await sourceHashes());
  report.passed=!report.source_changed_during_run && report.external_requests.length===0;
  if(!report.passed)throw Error('Source changed or external HTTP occurred');console.log(JSON.stringify({passed:true,checks:report.checks.length}));
} catch(e){report.error=String(e);process.exitCode=1;console.error(e);}
finally {
  try {await writeFile(out+'/report.json',JSON.stringify(report,null,2));}
  finally {for(const entry of pending.values())clearTimeout(entry.timer);try{ws?.close();}finally{await dispose();}}
}
