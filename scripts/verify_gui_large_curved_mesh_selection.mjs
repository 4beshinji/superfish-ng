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
  const {root}=await call('DOM.getDocument',{},sessionId);
  const {nodeId}=await call('DOM.querySelector',{nodeId:root.nodeId,selector:'#open'},sessionId);
  await call('DOM.setFileInputFiles',{nodeId,files:[resolve(args['--case'])]},sessionId);
  await wait('document.querySelector("#geometry-type").value==="curved_contour"');
  const load=async()=>{
    const begin=performance.now();await click('#curved-selection-load');
    await wait('!document.querySelector("#curved-selection-load").disabled && curvedCanvasPicker?.ready && !curvedCanvasPicker.frame',240000);
    report.load_ms=performance.now()-begin;
    report.mesh=await ev('({cells:curvedCanvasPicker.paths.length,points:curvedCanvasPicker.mesh.points_rz_m.length,build_ms:curvedCanvasPicker.buildMilliseconds,draw_ms:curvedCanvasPicker.lastDrawMilliseconds,dom_cells:document.querySelectorAll("[data-cell]").length})');
  };
  await load();
  await check('canvas size follows the served stylesheet',`getComputedStyle(document.querySelector('#curved-selection-canvas')).height==='360px' && document.querySelector('#curved-selection-canvas').getBoundingClientRect().width>300`);
  if(report.mesh.cells<=5000||report.mesh.dom_cells!==0)throw Error('large native mesh did not use the bounded DOM view');
  report.checks.push({operation:'large native mesh without per-cell DOM objects',passed:true});
  await writeFile(out+'/mesh-document.json',JSON.stringify(await ev('curvedCanvasPicker.mesh')));
  await ev('window.meshSelectionFixture=structuredClone(curvedCanvasPicker.mesh);window.meshSelectionProject=collect()');
  report.selection_times_ms=[];
  const ids=[0,1999,2000,Math.floor(report.mesh.cells/2),report.mesh.cells-1];
  const nativeCenter=async(index)=>ev(`(()=>{
    const picker=curvedCanvasPicker;picker.canvas.scrollIntoView({block:'center',behavior:'instant'});
    const mesh=picker.mesh,p=mesh.cell_nodes[${index}].map(i=>mesh.points_rz_m[i]);
    const rz=[0,1].map(k=>p.reduce((s,v,i)=>s+v[k]*(i<3?-1/9:4/9),0));
    const q=[(rz[1]-picker.origin[0])/picker.length,(picker.origin[1]-rz[0])/picker.length];
    const xy=picker.screen(q),r=picker.canvas.getBoundingClientRect();return {x:r.left+xy[0],y:r.top+xy[1]};
  })()`);
  const physicalClick=async(point)=>{for(const type of ['mousePressed','mouseReleased'])await call('Input.dispatchMouseEvent',{type,...point,button:'left',clickCount:1},sessionId);};
  for(const index of ids) {
    await fill('#curved-selection-cell',index);await click('#curved-selection-focus');
    await wait('curvedCanvasPicker && !curvedCanvasPicker.frame');
    const start=performance.now();await physicalClick(await nativeCenter(index));
    await check('quadratic centroid click selects native cell '+index,`curvedSelection.cells.has(${index})`);
    report.selection_times_ms.push(performance.now()-start);
  }
  await physicalClick(await nativeCenter(ids.at(-1)));
  await check('repeat click deselects the same native cell',`!curvedSelection.cells.has(${ids.at(-1)})`);
  await ev('curvedCanvasPicker.canvas.focus()');
  for(const type of ['keyDown','keyUp'])await call('Input.dispatchKeyEvent',{type,key:'Enter',code:'Enter',windowsVirtualKeyCode:13},sessionId);
  await check('keyboard selects the focused native cell',`curvedSelection.cells.has(${ids.at(-1)}) && document.querySelector('#curved-selection-canvas').getAttribute('aria-label').includes('選択済み')`);
  await click('#curved-selection-zoom-in');await wait('!curvedCanvasPicker.frame');
  await check('zoom retains native selections',`curvedSelection.cells.size===${ids.length}`);
  await ev('curvedCanvasPicker.canvas.focus()');
  const offset=await ev('curvedCanvasPicker.offset');
  for(const type of ['keyDown','keyUp'])await call('Input.dispatchKeyEvent',{type,key:'ArrowRight',code:'ArrowRight',windowsVirtualKeyCode:39},sessionId);
  await check('keyboard pans the view without changing selection',`curvedCanvasPicker.offset[0]===${offset[0]}-50 && curvedSelection.cells.size===${ids.length}`);
  const dragStart=await ev('(()=>{const c=curvedCanvasPicker.canvas;c.scrollIntoView({block:"center",behavior:"instant"});const r=c.getBoundingClientRect();return {x:r.left+r.width/2,y:r.top+r.height/2}})()');
  const dragOffset=await ev('curvedCanvasPicker.offset');
  await call('Input.dispatchMouseEvent',{type:'mousePressed',...dragStart,button:'left',clickCount:1},sessionId);
  await call('Input.dispatchMouseEvent',{type:'mouseMoved',x:dragStart.x+23,y:dragStart.y+17,button:'left',buttons:1},sessionId);
  await call('Input.dispatchMouseEvent',{type:'mouseReleased',x:dragStart.x+23,y:dragStart.y+17,button:'left',clickCount:1},sessionId);
  await check('pointer drag pans without selecting a cell',`Math.abs(curvedCanvasPicker.offset[0]-(${dragOffset[0]})-23)<1 && Math.abs(curvedCanvasPicker.offset[1]-(${dragOffset[1]})-17)<1 && curvedSelection.cells.size===${ids.length}`);
  const wheelZoom=await ev('curvedCanvasPicker.zoom');
  await call('Input.dispatchMouseEvent',{type:'mouseWheel',...dragStart,deltaX:0,deltaY:-100},sessionId);
  await wait(`curvedCanvasPicker.zoom>${wheelZoom} && !curvedCanvasPicker.frame`);
  await check('wheel zoom retains native selections',`curvedSelection.cells.size===${ids.length}`);
  await click('#curved-selection-fit');await wait('!curvedCanvasPicker.frame');
  await check('fit restores the full mesh',`curvedCanvasPicker.zoom===1 && curvedCanvasPicker.offset.every(v=>v===0)`);
  await fill('#curved-selection-cell',report.mesh.cells);await click('#curved-selection-focus');
  await check('out of range focus is rejected',`document.querySelector('#error').textContent.includes('要素番号') && curvedSelection.cells.size===${ids.length}`);
  const chord=await ev('document.querySelector("#curve-chord").value');
  await fill('#curve-chord',String(Number(chord)*.9));await click('#curved-selection-append');
  await check('modified case cannot append stale native indices',`document.querySelector('#error').textContent.includes('古い要素番号')`);
  await fill('#curve-chord',chord);
  await ev('curvedCanvasPicker.focusCell(2000)');await wait('!curvedCanvasPicker.frame');
  const rect=await ev('(()=>{const r=document.querySelector("#curved-selection-large").getBoundingClientRect();return {x:r.x+scrollX,y:r.y+scrollY,width:r.width,height:r.height,scale:1}})()');
  const shot=await call('Page.captureScreenshot',{captureBeyondViewport:true,clip:rect},sessionId);await writeFile(out+'/selection.png',Buffer.from(shot.data,'base64'));
  const prefix=await ev('(()=>{const m=collect().case.mesh;return m.curved_refinement_steps||Array.from({length:m.curved_refinement_levels||0},()=>({kind:"uniform"}))})()');
  await click('#curved-selection-append');const built=await ev('collect()');
  if(!isDeepStrictEqual(built.case.mesh.curved_refinement_steps,[...prefix,{kind:'marked',marked_cells:[...ids].sort((a,b)=>a-b),minimum_corner_angle_deg:5}]))throw Error('large selection did not preserve the exact ordered history');
  await writeFile(out+'/built-project.json',JSON.stringify(built,null,2));
  await check('append clears old paths and selections',`curvedCanvasPicker===null && curvedSelection===null && document.querySelector('#curved-selection-panel').hidden`);
  // Independent visibly curved triangle: the point r=.85,z=.5 is outside its
  // straight corner triangle but inside the quadratic edge (midpoint r=.8).
  const curve=await ev(`(async()=>{
    const canvas=document.createElement('canvas');canvas.style='width:420px;height:300px';document.body.prepend(canvas);
    const selected=new Set(),mesh={points_rz_m:[[1,0],[1,1],[2,0],[.8,.5],[1.5,.5],[1.5,0]],cell_nodes:[[0,1,2,3,4,5]]};
    const picker=new CurvedMeshCanvas(canvas,mesh,selected,()=>{},()=>{});await picker.build();await new Promise(r=>requestAnimationFrame(r));
    const hit=(r,z)=>picker.hit(picker.screen([(z-picker.origin[0])/picker.length,(picker.origin[1]-r)/picker.length]));
    const result={insideBulge:hit(.85,.5),outsideBulge:hit(.75,.5),inside:hit(1.2,.2)};
    picker.dispose();canvas.remove();return result;
  })()`);
  if(!isDeepStrictEqual(curve,{insideBulge:0,outsideBulge:null,inside:0}))throw Error('quadratic edge hit invariant failed: '+JSON.stringify(curve));
  report.checks.push({operation:'quadratic bulge hit differs from a straight display triangle',passed:true});
  if(args['--maximum-renderer']==='yes') {
    report.maximum_renderer=await ev(`(async()=>{
      const mesh={points_rz_m:[],cell_nodes:[]},nx=500,ny=250,stride=2*nx+1;
      for(let y=0;y<=2*ny;y++)for(let x=0;x<=2*nx;x++)mesh.points_rz_m.push([y/(2*ny),x/(2*nx)]);
      const id=(x,y)=>y*stride+x;
      for(let y=0;y<ny;y++)for(let x=0;x<nx;x++) {
        const a=id(2*x,2*y),b=id(2*x+2,2*y),c=id(2*x+2,2*y+2),d=id(2*x,2*y+2);
        mesh.cell_nodes.push([a,b,c,id(2*x+1,2*y),id(2*x+2,2*y+1),id(2*x+1,2*y+1)]);
        mesh.cell_nodes.push([a,c,d,id(2*x+1,2*y+1),id(2*x+1,2*y+2),id(2*x,2*y+1)]);
      }
      document.querySelector('#curved-selection-panel').hidden=false;
      document.querySelector('#curved-selection-large').hidden=false;
      const picker=new CurvedMeshCanvas(document.querySelector('#curved-selection-canvas'),mesh,new Set(),()=>{},()=>{});
      await picker.build();await new Promise(r=>requestAnimationFrame(r));
      const draw_ms=picker.lastDrawMilliseconds,results=[],begin=performance.now();
      for(const x of [0,17,249,499])for(const y of [0,123,249])for(const [u,v,k] of [[.75,.25,0],[.25,.75,1]]) {
        const expected=2*(y*nx+x)+k;
        const actual=picker.hit(picker.screen([(x+u)/nx,1-(y+v)/ny]));
        if(actual!==expected)throw Error('maximum mesh analytic cell ID mismatch '+actual+' != '+expected);
        results.push(actual);
      }
      const value={cells:mesh.cell_nodes.length,points:mesh.points_rz_m.length,build_ms:picker.buildMilliseconds,
        draw_ms,hit_tests:results.length,total_hit_ms:performance.now()-begin,dom_cells:document.querySelectorAll('[data-cell]').length};
      picker.dispose();document.querySelector('#curved-selection-panel').hidden=true;return value;
    })()`);
    if(report.maximum_renderer.cells!==250000||report.maximum_renderer.hit_tests!==24||report.maximum_renderer.dom_cells!==0)throw Error('maximum renderer scope mismatch');
    report.checks.push({operation:'250000-cell renderer and 24 independently known grid cell hits',passed:true});
  }
  // Use the already verified native response to exercise a pending UI build;
  // this is a controlled UI race, not another native reconstruction/solve.
  await ev(`(()=>{
    applyProject(window.meshSelectionProject);
    window.meshSelectionOriginalApi=api;window.meshSelectionOriginalBuild=CurvedMeshCanvas.prototype.build;
    api=async(action,data)=>{
      if(action!=='curved-selection-mesh')return window.meshSelectionOriginalApi(action,data);
      if(JSON.stringify(data.document)!==JSON.stringify(window.meshSelectionProject))throw Error('test response input mismatch');
      return structuredClone(window.meshSelectionFixture);
    };
    CurvedMeshCanvas.prototype.build=async function(){
      await new Promise(resolve=>window.releaseMeshSelectionBuild=resolve);
      return window.meshSelectionOriginalBuild.call(this);
    };
  })()`);
  await click('#curved-selection-load');await wait('typeof window.releaseMeshSelectionBuild==="function"');
  await check('pending build disables focus, zoom and append',`[...document.querySelectorAll('#curved-selection-large button,#curved-selection-large input,#curved-selection-append')].every(e=>e.disabled)`);
  await fill('#beta',.9);await ev('window.releaseMeshSelectionBuild()');
  await wait('!document.querySelector("#curved-selection-load").disabled');
  await check('input edited during build clears stale geometry',`curvedCanvasPicker===null && curvedSelection===null && document.querySelector('#curved-selection-panel').hidden && document.querySelector('#error').textContent.includes('作成中に入力が変わりました')`);
  await ev('api=window.meshSelectionOriginalApi;CurvedMeshCanvas.prototype.build=window.meshSelectionOriginalBuild');
  const cancelled=await ev(`(async()=>{
    const canvas=document.createElement('canvas'),picker=new CurvedMeshCanvas(canvas,window.meshSelectionFixture,new Set(),()=>{},()=>{});
    const pending=picker.build();picker.dispose();await pending;return picker.disposed&&picker.paths.length===0;
  })()`);
  if(!cancelled)throw Error('disposed build retained native paths');
  report.checks.push({operation:'dispose during asynchronous construction releases native paths',passed:true});
  report.source_changed_during_run=!isDeepStrictEqual(report.source_sha256,await sourceHashes());
  report.passed=!report.source_changed_during_run&&report.external_requests.length===0&&report.checks.every(c=>c.passed);
  if(!report.passed)throw Error('large selection verification failed');
  console.log(JSON.stringify({passed:report.passed,mesh:report.mesh,load_ms:report.load_ms,checks:report.checks.length}));
} catch(e){report.error=String(e);process.exitCode=1;console.error(e);}
finally{await writeFile(out+'/report.json',JSON.stringify(report,null,2));ws?.close();browser.kill();}
