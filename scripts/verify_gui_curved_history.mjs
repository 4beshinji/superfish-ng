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
if (!args['--url'] || !args['--out'] || !args['--case']) throw Error('Require --url --out --case');
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

  const input=JSON.parse(await readFile(args['--case'],'utf8'));
  const expected=input.mesh.curved_refinement_steps;
  if(!expected?.length) throw Error('Fixture must have a nonempty curved history');
  const loadFile=async(filename)=>{const {root}=await call('DOM.getDocument',{},sessionId);const {nodeId}=await call('DOM.querySelector',{nodeId:root.nodeId,selector:'#open'},sessionId);await call('DOM.setFileInputFiles',{nodeId,files:[resolve(filename)]},sessionId);};
  const select=async(selector,value)=>await ev(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});e.value=${JSON.stringify(value)};e.dispatchEvent(new Event('change',{bubbles:true}));e.dispatchEvent(new Event('input',{bubbles:true}))})()`);
  const history=()=>ev('collect().case.mesh.curved_refinement_steps');
  const equal=async(label,value,wanted)=>{if(!isDeepStrictEqual(value,wanted))throw Error(label);report.checks.push({operation:label,passed:true});};
  await loadFile(args['--case']);
  await wait('document.querySelector("#geometry-type").value==="curved_contour"');
  await equal('native history survives GUI open and collect',await history(),expected);
  await click('#curved-add-uniform');
  await equal('append uniform step',await history(),[...expected,{kind:'uniform'}]);
  await click('#curved-history tbody tr:last-child .step-up');
  await equal('move step up',await history(),[...expected.slice(0,-1),{kind:'uniform'},expected.at(-1)]);
  await click('#curved-history tbody tr:nth-last-child(2) .step-down');
  await equal('move step down',await history(),[...expected,{kind:'uniform'}]);
  await click('#curved-history tbody tr:last-child .step-remove');
  await click('#curved-add-marked');
  await fill('#curved-history tbody tr:last-child .step-cells','0, 2');
  await fill('#curved-history tbody tr:last-child .step-angle','6');
  await equal('edit marked cells and tangent angle',await history(),[...expected,{kind:'marked',marked_cells:[0,2],minimum_corner_angle_deg:6}]);
  for(const invalid of ['0,0','1.5','-1','9007199254740992','']) {
    await fill('#curved-history tbody tr:last-child .step-cells',invalid);
    await click('#preview');
    await wait('!document.querySelector("#error").hidden');
    await check(`reject invalid cell indices ${JSON.stringify(invalid)}`,'document.querySelector("#error").textContent.includes("重複のない0以上の整数")');
  }
  await fill('#curved-history tbody tr:last-child .step-cells','0');
  await fill('#curved-history tbody tr:last-child .step-angle','60');await click('#preview');
  await wait('!document.querySelector("#error").hidden');
  await check('reject angle endpoint','document.querySelector("#error").textContent.includes("60より小さい")');
  await select('#curved-history tbody tr:last-child .step-kind','uniform');
  await equal('uniform kind omits stale marked fields',await history(),[...expected,{kind:'uniform'}]);
  await click('#curved-history tbody tr:last-child .step-remove');
  await select('#geometry-order','1');await click('#preview');await wait('!document.querySelector("#error").hidden');
  await check('geometry downgrade cannot silently drop history','document.querySelector("#error").textContent.includes("履歴")');
  await select('#geometry-order','2');
  await click('#save');
  const saved=out+'/downloads/cavity-project.json';let project;
  for(let i=0;i<300;i++){try{project=JSON.parse(await readFile(saved,'utf8'));break;}catch{}await sleep(100);}
  if(!project)throw Error('Project download missing');
  await equal('saved project preserves history',project.case.mesh.curved_refinement_steps,expected);
  await call('Page.navigate',{url:'about:blank'},sessionId);await wait('document.URL==="about:blank"');
  await call('Page.navigate',{url:args['--url']},sessionId);await wait('document.querySelector("#shape polygon")');
  await loadFile(saved);await wait('document.querySelector("#geometry-type").value==="curved_contour"');
  await equal('downloaded project reopens with ordered history',await history(),expected);
  const before=await ev('document.querySelectorAll("#jobs .job").length');
  await click('#run');await wait(`document.querySelectorAll('#jobs .job').length>${before}`);
  await wait('document.querySelector("#jobs .job strong").textContent.startsWith("計算完了")',120000);
  await click('#jobs .job button');await wait('document.querySelector("#field-image").naturalWidth>0',120000);
  await equal('actual FEM result retains requested history',await ev('currentResult.result.case.mesh.curved_refinement_steps'),expected);
  await writeFile(out+'/result.json',JSON.stringify(await ev('currentResult'),null,2));
  await select('#curved-refinement-mode','levels');await fill('#curved-refinement-levels','1');
  await check('uniform level mode sends only levels','(()=>{const m=collect().case.mesh;return m.curved_refinement_levels===1 && !("curved_refinement_steps" in m)})()');
  await select('#curved-refinement-mode','steps');
  while(await ev('document.querySelector("#curved-history tbody").rows.length'))await click('#curved-history tbody tr:last-child .step-remove');
  await click('#preview');await wait('!document.querySelector("#error").hidden');
  await check('empty explicit history is rejected','document.querySelector("#error").textContent.includes("1段以上")');
  const legacy=structuredClone(input);delete legacy.mesh.curved_refinement_steps;legacy.mesh.curved_refinement_levels=0;
  await writeFile(out+'/levels-only.json',JSON.stringify(legacy));await loadFile(out+'/levels-only.json');
  await wait('document.querySelector("#curved-refinement-mode").value==="levels"');
  await check('opening levels-only Case clears previous history','document.querySelector("#curved-history tbody").rows.length===0 && !("curved_refinement_steps" in collect().case.mesh)');
  report.source_changed_during_run=!isDeepStrictEqual(report.source_sha256,await sourceHashes());
  report.passed=!report.source_changed_during_run && report.external_requests.length===0 && report.checks.every(c=>c.passed);
  if(!report.passed)throw Error('History GUI verification failed');
  console.log(JSON.stringify({passed:report.passed,checks:report.checks}));
} catch(e){report.error=String(e);process.exitCode=1;console.error(e);}
finally{await writeFile(out+'/report.json',JSON.stringify(report,null,2));ws?.close();browser.kill();}
