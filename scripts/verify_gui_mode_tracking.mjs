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
  if (args["--same-domain"]) {
    await click("#tracking-reset");await loadFile(resolve(args["--same-domain"],"folded-1-3-pair.json"));
    await wait('trackingResult?.document.request?.controls.mapping==="same_domain" && !trackingBusy');
    await check("saved remesh correspondence restores the same-domain mapping",'document.querySelector("#tracking-mapping").value==="same_domain" && document.querySelector("#tracking-pairs-label").hidden && !document.querySelector("#tracking-domain-note").hidden');
    const remeshed=[];
    for (const stage of [0,1]) {
      const beforeIds=await ev('[...document.querySelector("#tracking-current").options].map(x=>x.value)');
      await fill("#import-path",resolve(args["--same-domain"],`folded-1-${stage}`));await click("#import-result");
      await wait(`document.querySelector("#tracking-current").options.length===${beforeIds.length+1}`);
      remeshed.push(await ev(`[...document.querySelector("#tracking-current").options].map(x=>x.value).find(x=>!${JSON.stringify(beforeIds)}.includes(x))`));
    }
    await click("#tracking-reset");await select("tracking-previous",remeshed[0]);await select("tracking-current",remeshed[1]);
    await fill("#tracking-ids",'["ID0"]');await select("tracking-mapping","same_domain");
    await click("#tracking-compare");await wait('trackingResult?.document.status==="PASS" && !trackingBusy');
    await check("GUI compares independently remeshed folded fields without vertex pairs",'trackingResult.document.request.controls.mapping==="same_domain" && !("vertex_pairs" in trackingResult.document.request.controls) && trackingResult.document.tracking.physical_mapping.triangle_counts[0]!==trackingResult.document.tracking.physical_mapping.triangle_counts[1]');
    await click("#tracking-start");await wait('trackingResult?.document.document_type==="mode_tracking_history" && !trackingBusy');
    await select("tracking-current",remeshed[0]);await click("#tracking-extend");await wait('trackingResult?.document.steps?.length===2 && !trackingBusy');
    await check("remesh history extends with stable individual identity",'trackingResult.document.status==="PASS" && trackingResult.document.current_mode_ids[0]==="ID0" && trackingResult.document.steps[1].request.controls.mapping==="same_domain"');
    await select("tracking-current",imported.a);await click("#tracking-extend");await wait('!document.querySelector("#error").hidden && !trackingBusy');
    await check("a different physical domain is rejected without changing the verified history",'document.querySelector("#error").textContent.includes("boundary differs") && trackingResult.document.steps.length===2 && trackingResult.document.current_mode_ids[0]==="ID0"');
    await ev('document.querySelector("#mode-tracking").scrollIntoView({behavior:"instant",block:"start"})');
    const capture=await call("Page.captureScreenshot",{captureBeyondViewport:false},sessionId);
    await writeFile(out+"/same-domain.png",Buffer.from(capture.data,"base64"));
  }
  if (args["--affine"]) {
    await click("#tracking-reset");await loadFile(resolve(args["--affine"],"sheared_triangle-1-3-pair.json"));
    await wait('trackingResult?.document.request?.controls.mapping==="affine_remesh" && !trackingBusy');
    await check("saved affine mapping restores all three coefficients",'document.querySelector("#tracking-mapping").value==="affine_remesh" && !document.querySelector("#tracking-affine").hidden && document.querySelector("#tracking-affine-radial").value==="1.1" && document.querySelector("#tracking-affine-axial").value==="0.9" && document.querySelector("#tracking-affine-shear").value==="0.1"');
    const affineIds=[];
    for (const stage of [0,1]) {
      const beforeIds=await ev('[...document.querySelector("#tracking-current").options].map(x=>x.value)');
      await fill("#import-path",resolve(args["--affine"],`sheared_triangle-1-${stage}`));await click("#import-result");
      await wait(`document.querySelector("#tracking-current").options.length===${beforeIds.length+1}`);
      affineIds.push(await ev(`[...document.querySelector("#tracking-current").options].map(x=>x.value).find(x=>!${JSON.stringify(beforeIds)}.includes(x))`));
    }
    await click("#tracking-reset");await select("tracking-previous",affineIds[0]);await select("tracking-current",affineIds[1]);
    await fill("#tracking-ids",'["fundamental"]');await click("#tracking-compare");await wait('trackingResult?.document.status==="PASS" && !trackingBusy');
    await check("GUI applies the declared shear to independent remeshes",'trackingResult.document.request.controls.affine_map.axial_shear===0.1 && trackingResult.document.tracking.physical_mapping.triangle_counts[0]!==trackingResult.document.tracking.physical_mapping.triangle_counts[1]');
    await click("#tracking-start");await wait('trackingResult?.document.document_type==="mode_tracking_history" && !trackingBusy');
    await select("tracking-current",affineIds[0]);await click("#tracking-extend");await wait('!document.querySelector("#error").hidden && !trackingBusy');
    await check("forward coefficients are rejected for reverse history continuation",'trackingResult.document.steps.length===1 && document.querySelector("#error").textContent.includes("affine_map")');
    await click("#tracking-affine-invert");await click("#tracking-extend");await wait('trackingResult?.document.steps?.length===2 && !trackingBusy');
    await check("explicit inverse coefficients continue the verified history",'trackingResult.document.status==="PASS" && trackingResult.document.current_mode_ids[0]==="fundamental" && Math.abs(trackingResult.document.steps[1].request.controls.affine_map.axial_shear+0.1/1.1/0.9)<1e-15');
    await select("tracking-mapping","same_domain");
    await check("other mappings omit affine inputs",'document.querySelector("#tracking-affine").hidden && !("affine_map" in trackingControls())');
    await select("tracking-mapping","affine_remesh");
    await ev('document.querySelector("#mode-tracking").scrollIntoView({behavior:"instant",block:"start"})');
    const capture=await call("Page.captureScreenshot",{captureBeyondViewport:false},sessionId);
    await writeFile(out+"/affine-history.png",Buffer.from(capture.data,"base64"));
    const axialBefore=await ev('document.querySelector("#tracking-affine-axial").value');
    await fill("#tracking-affine-radial",0);await click("#tracking-affine-invert");await wait('!document.querySelector("#error").hidden');
    await check("invalid inversion leaves other coefficients and verified history intact",`document.querySelector("#tracking-affine-radial").value==="0" && document.querySelector("#tracking-affine-axial").value===${JSON.stringify(axialBefore)} && trackingResult.document.steps.length===2`);
  }
  if (args["--piecewise"]) {
    await click("#tracking-reset");await loadFile(resolve(args["--piecewise"],"folded-1-6-pair.json"));
    await wait('trackingResult?.document.request?.controls.mapping==="piecewise_remesh" && !trackingBusy');
    await check("saved piecewise map restores both complete comparison meshes",'document.querySelector("#tracking-mapping").value==="piecewise_remesh" && !document.querySelector("#tracking-comparison").hidden && JSON.stringify(JSON.parse(document.querySelector("#tracking-comparison-json").value))===JSON.stringify(trackingResult.document.request.controls.comparison_meshes)');
    const mappedIds=[];
    for (const stage of [0,1]) {
      const beforeIds=await ev('[...document.querySelector("#tracking-current").options].map(x=>x.value)');
      await fill("#import-path",resolve(args["--piecewise"],`folded-1-${stage}`));await click("#import-result");
      await wait(`document.querySelector("#tracking-current").options.length===${beforeIds.length+1}`);
      mappedIds.push(await ev(`[...document.querySelector("#tracking-current").options].map(x=>x.value).find(x=>!${JSON.stringify(beforeIds)}.includes(x))`));
    }
    await click("#tracking-reset");await select("tracking-previous",mappedIds[0]);await select("tracking-current",mappedIds[1]);
    await fill("#tracking-ids",'["fundamental"]');await click("#tracking-compare");await wait('trackingResult?.document.status==="PASS" && !trackingBusy');
    await check("GUI compares non-affine folded meshes using the declared comparison mesh",'trackingResult.document.tracking.physical_mapping.comparison_triangle_count===44 && trackingResult.document.tracking.physical_mapping.solver_triangle_counts.join(",")==="74,167"');
    await click("#tracking-start");await wait('trackingResult?.document.document_type==="mode_tracking_history" && !trackingBusy');
    await select("tracking-current",mappedIds[0]);await click("#tracking-extend");await wait('!document.querySelector("#error").hidden && !trackingBusy');
    await check("unswapped comparison meshes cannot overwrite reverse history",'trackingResult.document.steps.length===1 && document.querySelector("#error").textContent.includes("mesh")');
    await click("#tracking-comparison-swap");await click("#tracking-extend");await wait('trackingResult?.document.steps?.length===2 && !trackingBusy');
    await check("explicit comparison-mesh swap continues the identity history",'trackingResult.document.status==="PASS" && trackingResult.document.current_mode_ids[0]==="fundamental" && JSON.stringify(trackingResult.document.steps[1].request.controls.comparison_meshes[0])===JSON.stringify(trackingResult.document.steps[0].request.controls.comparison_meshes[1])');
    const expectedHistory=await ev('trackingResult.document');await click("#tracking-save");
    let savedHistory;
    for (let n=0;n<100;n++) {
      try {
        const candidate=JSON.parse(await readFile(out+"/downloads/mode-tracking-history.json","utf8"));
        if (isDeepStrictEqual(candidate,expectedHistory)) {savedHistory=candidate;break;}
      } catch {}
      await sleep(100);
    }
    if (!savedHistory) throw Error("piecewise history download differs from verified data");
    report.checks.push({operation:"piecewise history download preserves both mesh declarations",passed:true});
    await select("tracking-mapping","same_domain");
    await check("other mappings omit comparison mesh declarations",'document.querySelector("#tracking-comparison").hidden && !("comparison_meshes" in trackingControls())');
    await select("tracking-mapping","piecewise_remesh");
    await ev('document.querySelector("#mode-tracking").scrollIntoView({behavior:"instant",block:"start"})');
    const capture=await call("Page.captureScreenshot",{captureBeyondViewport:false},sessionId);
    await writeFile(out+"/piecewise-history.png",Buffer.from(capture.data,"base64"));
    await fill("#tracking-comparison-json",'[{}]');await click("#tracking-comparison-swap");await wait('!document.querySelector("#error").hidden');
    await check("invalid comparison input is not partly swapped or committed",'document.querySelector("#tracking-comparison-json").value==="[{}]" && trackingResult.document.steps.length===2');
  }
  if (args["--curved"]) {
    if (!args["--reprojected"]) throw Error("--curved requires --reprojected native result directory");
    await click("#tracking-reset");await loadFile(resolve(args["--curved"],"ellipsoid-1-3-pair.json"));
    await wait('trackingResult?.document.request?.controls.mapping==="curved_same_domain" && !trackingBusy',30000);
    await check("saved curved mapping restores the discrete-boundary condition",'document.querySelector("#tracking-mapping").value==="curved_same_domain" && !document.querySelector("#tracking-curved-note").hidden && document.querySelector("#tracking-comparison").hidden && document.querySelector("#tracking-affine").hidden');
    const curvedIds=[];
    for (const directory of [resolve(args["--curved"],"ellipsoid-1-0"),resolve(args["--curved"],"ellipsoid-1-1"),resolve(args["--reprojected"])]) {
      const beforeIds=await ev('[...document.querySelector("#tracking-current").options].map(x=>x.value)');
      await fill("#import-path",directory);await click("#import-result");
      await wait(`document.querySelector("#tracking-current").options.length===${beforeIds.length+1}`,30000);
      curvedIds.push(await ev(`[...document.querySelector("#tracking-current").options].map(x=>x.value).find(x=>!${JSON.stringify(beforeIds)}.includes(x))`));
    }
    await click("#tracking-reset");await select("tracking-previous",curvedIds[0]);await select("tracking-current",curvedIds[1]);
    await fill("#tracking-ids",'["fundamental"]');await click("#tracking-compare");await wait('trackingResult?.document.status==="PASS" && !trackingBusy',30000);
    await check("GUI compares fixed-boundary curved remeshes with full-edge evidence",'trackingResult.document.tracking.physical_mapping.triangle_counts.join(",")==="90,360" && trackingResult.document.tracking.physical_mapping.boundary_coincidence.maximum_coefficient_distance_m<=trackingResult.document.tracking.physical_mapping.boundary_coincidence.roundoff_tolerance_m && document.querySelector("#tracking-diagnostics").textContent.includes("boundary_coincidence")');
    await click("#tracking-start");await wait('trackingResult?.document.document_type==="mode_tracking_history" && !trackingBusy',30000);
    await select("tracking-current",curvedIds[0]);await click("#tracking-extend");await wait('trackingResult?.document.steps?.length===2 && !trackingBusy',30000);
    await check("curved remesh history preserves the fundamental identity",'trackingResult.document.status==="PASS" && trackingResult.document.current_mode_ids[0]==="fundamental" && trackingResult.document.steps[1].request.controls.mapping==="curved_same_domain"');
    await select("tracking-current",curvedIds[2]);await click("#tracking-extend");await wait('!document.querySelector("#error").hidden && !trackingBusy',30000);
    await check("analytic reprojection changes the boundary and cannot overwrite history",'document.querySelector("#error").textContent.includes("quadratic boundary differs") && trackingResult.document.steps.length===2');
    const expected=await ev('trackingResult.document');await click("#tracking-save");let saved;
    for (let n=0;n<100;n++) {try {const candidate=JSON.parse(await readFile(out+"/downloads/mode-tracking-history.json","utf8"));if(isDeepStrictEqual(candidate,expected)){saved=candidate;break;}} catch {} await sleep(100);}
    if(!saved)throw Error("curved history download differs from verified data");
    report.checks.push({operation:"curved history download retains boundary evidence",passed:true});
    await ev('document.querySelector("#mode-tracking").scrollIntoView({behavior:"instant",block:"start"})');
    const capture=await call("Page.captureScreenshot",{captureBeyondViewport:false},sessionId);
    await writeFile(out+"/curved-history.png",Buffer.from(capture.data,"base64"));
  }
  if (args["--curved-affine"]) {
    await click("#tracking-reset");await loadFile(resolve(args["--curved-affine"],"ellipsoid-1-3-pair.json"));
    await wait('trackingResult?.document.request?.controls.mapping==="affine_remesh" && !trackingBusy',30000);
    await check("curved affine controls restore coefficients and boundary requirement",'document.querySelector("#tracking-affine-radial").value==="1.2" && document.querySelector("#tracking-affine-axial").value==="0.8" && document.querySelector("#tracking-affine").textContent.includes("二次曲線")');
    const ids=[];
    for (const stage of [0,1]) {
      const before=await ev('[...document.querySelector("#tracking-current").options].map(x=>x.value)');
      await fill("#import-path",resolve(args["--curved-affine"],`ellipsoid-1-${stage}`));await click("#import-result");
      await wait(`document.querySelector("#tracking-current").options.length===${before.length+1}`,30000);
      ids.push(await ev(`[...document.querySelector("#tracking-current").options].map(x=>x.value).find(x=>!${JSON.stringify(before)}.includes(x))`));
    }
    await click("#tracking-reset");await select("tracking-previous",ids[0]);await select("tracking-current",ids[1]);
    await click("#tracking-compare");await wait('trackingResult?.document.document_type==="saved_mode_tracking" && !trackingBusy',30000);
    await check("curved affine native comparison retains full-boundary and volume evidence",'trackingResult.document.status==="PASS" && trackingResult.document.tracking.physical_mapping.triangle_counts[0]!==trackingResult.document.tracking.physical_mapping.triangle_counts[1] && trackingResult.document.tracking.physical_mapping.boundary_coincidence.maximum_coefficient_distance_m<=trackingResult.document.tracking.physical_mapping.boundary_coincidence.roundoff_tolerance_m && Math.abs(trackingResult.document.tracking.physical_mapping.physical_volume_ratio-1.152)<1e-14');
    await click("#tracking-start");await wait('trackingResult?.document.document_type==="mode_tracking_history" && !trackingBusy',30000);
    await select("tracking-current",ids[0]);await click("#tracking-extend");await wait('!document.querySelector("#error").hidden && !trackingBusy',30000);
    await check("curved reverse continuation rejects the forward map without changing history",'trackingResult.document.steps.length===1 && document.querySelector("#error").textContent.includes("quadratic boundary")');
    await click("#tracking-affine-invert");await click("#tracking-extend");await wait('trackingResult?.document.steps?.length===2 && !trackingBusy',30000);
    await check("curved affine inverse preserves the fundamental identity",'trackingResult.document.status==="PASS" && trackingResult.document.current_mode_ids[0]==="fundamental"');
    const expected=await ev('trackingResult.document');await click("#tracking-save");let saved;
    for (let n=0;n<100;n++) {try {const candidate=JSON.parse(await readFile(out+"/downloads/mode-tracking-history.json","utf8"));if(isDeepStrictEqual(candidate,expected)){saved=candidate;break;}} catch {} await sleep(100);}
    if(!saved)throw Error("curved affine history download differs from verified data");
    report.checks.push({operation:"curved affine history download preserves the verified map and boundary",passed:true});
    await ev('document.querySelector("#mode-tracking").scrollIntoView({behavior:"instant",block:"start"})');
    const capture=await call("Page.captureScreenshot",{captureBeyondViewport:false},sessionId);
    await writeFile(out+"/curved-affine-history.png",Buffer.from(capture.data,"base64"));
  }
  if (args["--surface"]) {
    if(!args["--surface-singular"] || !args["--surface-study"])throw Error("--surface requires --surface-singular and --surface-study");
    const openSurface=async filename=>{const {root}=await call("DOM.getDocument",{},sessionId);const {nodeId}=await call("DOM.querySelector",{nodeId:root.nodeId,selector:"#surface-open"},sessionId);await call("DOM.setFileInputFiles",{nodeId,files:[resolve(filename)]},sessionId);await wait("surfaceBusy",5000);};
    await click("#tracking-reset");
    await check("surface assessment requires a usable three-level history",'document.querySelector("#surface-assess").disabled && document.querySelector("#surface-save").disabled');
    await loadFile(resolve(args["--surface"],"history-1.json"));await wait('trackingResult?.document.document_type==="mode_tracking_history" && !trackingBusy',60000);
    await fill("#surface-mode-id","fundamental");await click("#surface-assess");await wait('surfaceResult?.document.status==="TARGETS_MET" && !surfaceBusy',60000);
    await check("surface GUI shows separate frequency RF and bounded peak series",'document.querySelector("#surface-status").textContent.includes("基準達成（細分差）") && document.querySelector("#surface-values tbody").rows.length===3 && document.querySelector("#surface-peaks tbody").rows.length===3 && document.querySelector("#surface-changes tbody").rows.length===10 && document.querySelector("#surface-convergence").textContent.includes("物理誤差の上界") && surfaceResult.document.rows.map(r=>r.triangles).join(",")==="36,144,576"');
    await check("surface GUI retains individual identity and independent criterion values",'surfaceResult.document.mode_id==="fundamental" && surfaceResult.document.limits.frequency_hz===0.0001 && surfaceResult.document.limits.epk_over_eacc===0.01 && document.querySelector("#surface-diagnostics").textContent.includes("source_runs")');
    const expected=await ev('surfaceResult.serialized');await click("#surface-save");let saved;
    for(let n=0;n<100;n++){try{saved=await readFile(out+"/downloads/surface-convergence.json","utf8");if(saved===expected)break;}catch{}await sleep(100);}
    if(saved!==expected)throw Error("surface download changes verified document text");
    report.checks.push({operation:"surface download preserves exact server document text",passed:true});
    await openSurface(out+"/downloads/surface-convergence.json");await wait('!surfaceBusy',60000);
    await check("saved surface assessment replays without changing its values",`surfaceResult.serialized===${JSON.stringify(expected)} && document.querySelector("#surface-mode-id").value==="fundamental"`);
    await fill("#surface-mode-id","missing-mode");await click("#surface-assess");await wait('!surfaceBusy && !document.querySelector("#error").hidden',60000);
    await check("invalid identity leaves the preceding verified surface assessment intact",`surfaceResult.serialized===${JSON.stringify(expected)} && document.querySelector("#surface-status").textContent.includes("fundamental") && document.querySelector("#error").textContent.includes("mode_id")`);
    const changed=JSON.parse(expected);changed.limits.frequency_hz=1;await writeFile(out+"/changed-surface.json",JSON.stringify(changed));
    await openSurface(out+"/changed-surface.json");await wait('!surfaceBusy && document.querySelector("#error").textContent.includes("differs")',60000);
    await check("modified criteria are rejected without replacing verified surface data",`surfaceResult.serialized===${JSON.stringify(expected)} && !document.querySelector("#surface-save").disabled`);
    await click("#surface-replay");await wait('!surfaceBusy && document.querySelector("#error").hidden',60000);
    await check("explicit surface revalidation restores the saved mode selection",'document.querySelector("#surface-mode-id").value==="fundamental"');
    await ev('document.querySelector("#surface-convergence").scrollIntoView({behavior:"instant",block:"start"})');
    let capture=await call("Page.captureScreenshot",{captureBeyondViewport:false},sessionId);await writeFile(out+"/surface-targets.png",Buffer.from(capture.data,"base64"));
    await click("#tracking-reset");await loadFile(resolve(args["--surface-singular"],"history.json"));await wait('trackingResult?.document.document_type==="mode_tracking_history" && !trackingBusy',60000);
    await click("#surface-assess");await wait('surfaceResult?.document.status==="SINGULAR_GEOMETRY" && !surfaceBusy',60000);
    await check("reentrant native geometry is displayed as unaccepted despite completed evaluation",'document.querySelector("#surface-status").textContent.includes("特異形状") && document.querySelector("#surface-geometry-status").textContent.includes("再入角 1") && !document.querySelector("#surface-save").disabled && document.querySelector("#surface-values tbody").rows.length===3');
    await click("#surface-replay");await wait('!surfaceBusy',60000);
    await check("singular surface diagnostics remain singular after replay",'surfaceResult.document.status==="SINGULAR_GEOMETRY" && surfaceResult.document.physical_error_bound===null');
    await ev('document.querySelector("#surface-convergence").scrollIntoView({behavior:"instant",block:"start"})');
    capture=await call("Page.captureScreenshot",{captureBeyondViewport:false},sessionId);await writeFile(out+"/surface-singular.png",Buffer.from(capture.data,"base64"));
    await click("#tracking-reset");await loadFile(resolve(args["--surface-study"]));await wait('trackingResult?.document.document_type==="study_mode_tracking" && !trackingBusy',60000);
    await click("#surface-assess");await wait('surfaceResult?.document.status==="TARGETS_MET" && !surfaceBusy',60000);
    await check("verified fixed-geometry Study history feeds the same surface assessment",'trackingResult.document.document_type==="study_mode_tracking" && surfaceResult.document.rows.every(r=>r.run.includes("point-")) && document.querySelector("#surface-values tbody").rows.length===3');
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
