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
    "Usage: node scripts/verify_gui.mjs --url LAUNCH_URL --out NEW_DIRECTORY",
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
  let expectedModel;
  if (args["--model-case"]) {
    const filename = resolve(args["--model-case"]);
    expectedModel = JSON.parse(await readFile(filename, "utf8")).model;
    if (!expectedModel) throw Error("--model-case requires a v3 model");
    const { root } = await call("DOM.getDocument", {}, sessionId);
    const { nodeId } = await call("DOM.querySelector", {
      nodeId: root.nodeId, selector: "#open",
    }, sessionId);
    await call("DOM.setFileInputFiles", { nodeId, files: [filename] }, sessionId);
    await wait('collect().case.schema_version === 3');
    if (!isDeepStrictEqual(await ev("collect().case.model"), expectedModel))
      throw Error("GUI import lost the explicit physics model");
  }
  await fill("#radius", 65);
  await fill("#length", 95);
  await fill("#modes", 2);
  if (args["--quadratic"] === "yes") await ev('document.querySelector("#element-order").value="2"; document.querySelector("#element-order").dispatchEvent(new Event("change", {bubbles:true}))');
  if (args["--acceleration"] === "yes") {
    await ev('document.querySelector("#active-length").closest("details").open=true');
    for (const [selector, value] of [["#active-length", 71], ["#voltage-start", 13],
        ["#voltage-end", 39], ["#phase-origin", -8]]) await fill(selector, value);
  }
  await click("#preview");
  await wait(
    'document.querySelector("#preview-note").textContent.includes("入力形状")',
  );
  report.checks.push({
    operation: "keyboard dimensions and preview",
    radius_mm: await ev('document.querySelector("#radius").value'),
    length_mm: await ev('document.querySelector("#length").value'),
  });
  const before = await ev('document.querySelectorAll("#jobs .job").length');
  await click("#run");
  await wait(`document.querySelectorAll('#jobs .job').length > ${before}`);
  await wait(
    'document.querySelector("#jobs .job strong").textContent.startsWith("計算完了")',
  );
  await click("#jobs .job button");
  await wait('document.querySelector("#field-image").naturalWidth>0', 30000);
  report.checks.push(
    await ev(
      `({operation:'FEM and saved field display',rows:document.querySelectorAll('#rf-table tr').length,image_width:document.querySelector('#field-image').naturalWidth,result_name:document.querySelector('#result-name').textContent})`,
    ),
  );
  // Input failure must be visible while retaining the user's value.
  await fill("#radius", -1);
  await click("#preview");
  await wait('!document.querySelector("#error").hidden');
  report.checks.push({
    operation: "invalid radius retained",
    value: await ev('document.querySelector("#radius").value'),
    message: await ev('document.querySelector("#error").textContent'),
  });
  await fill("#radius", 65);
  await click("#preview");
  if (args["--quadratic"] === "yes") {
    const order = await ev("currentResult.result.field_space?.element_order");
    if (order !== 2) throw Error("GUI solve lost P2 element order");
    const roundtrip = await ev('(() => { const p = collect(); applyProject(p); return collect().case.solver.element_order; })()');
    if (roundtrip !== 2) throw Error("GUI Project roundtrip lost P2 element order");
    report.checks.push({ operation: "select P2 and solve with saved quadratic space", passed: true });
  }
  if (args["--acceleration"] === "yes") {
    const actual = await ev("currentResult.result.modes[0]");
    if (actual.active_length_m !== .071 || actual.voltage_interval_start_m !== .013 ||
        actual.voltage_interval_end_m !== .039 || actual.phase_origin_m !== -.008)
      throw Error("Accelerating conventions were lost before computation");
    report.checks.push({ operation: "edit acceleration length, voltage interval and phase origin, then solve", passed: true });
  }
  if (expectedModel) {
    for (const expression of ["collect().case", "currentResult.result.case"]) {
      const actual = await ev(expression);
      if (actual.schema_version !== 3 || !isDeepStrictEqual(actual.model, expectedModel))
        throw Error("GUI editing or FEM persistence lost the explicit model");
    }
    report.checks.push({ operation: "v3 model import, edit, FEM and result persistence", passed: true });
  }
  if (args["--io"] === "yes") {
    const downloaded = async (name) => {
      for (let i = 0; i < 150; i++) {
        try {
          return await readFile(out + "/downloads/" + name);
        } catch {}
        await sleep(100);
      }
      throw Error(`download not completed: ${name}`);
    };
    await click("#save");
    const project = JSON.parse(await downloaded("cavity-project.json"));
    await click("#export");
    const caseFile = JSON.parse(await downloaded("case.json"));
    if (!isDeepStrictEqual(project.case, caseFile))
      throw Error("GUI project and exported case differ");
    const resultCase = await ev("currentResult.result.case");
    if (!isDeepStrictEqual(resultCase, caseFile))
      throw Error("saved GUI input differs from actual solve");
    await fill("#radius", 72);
    const { root } = await call("DOM.getDocument", {}, sessionId);
    const { nodeId } = await call(
      "DOM.querySelector",
      { nodeId: root.nodeId, selector: "#open" },
      sessionId,
    );
    await call(
      "DOM.setFileInputFiles",
      { nodeId, files: [out + "/downloads/cavity-project.json"] },
      sessionId,
    );
    await wait(
      'document.querySelector("#radius").value==="65" && document.querySelector("#dirty").textContent==="入力を読込済み"',
    );
    report.checks.push({
      operation:
        "project and case download, actual case parity, reopen after editing",
      passed: true,
      job_id: await ev("currentJob"),
    });
    await click("#probe-csv");
    const csv = (await downloaded("radial.csv")).toString();
    if (csv.trim().split("\n").length !== 402)
      throw Error("radial sample count differs");
    await click("#probe-metadata");
    const meta = JSON.parse(await downloaded("radial.csv.json"));
    if (meta.mode_index !== 1 || meta.z_m !== 0.095 / 4)
      throw Error("probe metadata differs from UI");
    await click("#save-plot");
    if ((await downloaded("fields.png")).length < 1000)
      throw Error("empty field image");
    await click("#pillbox-reference");
    await wait('document.querySelectorAll("#reference-result tr").length===3');
    await click("#save-reference");
    const reference = JSON.parse(
      await downloaded("analytical-comparison.json"),
    );
    if (reference.modes.some((m) => m.status !== "PASS"))
      throw Error("cylinder analytical comparison did not pass");
    report.checks.push({
      operation:
        "probe, normalization metadata, figure and analytical report downloads",
      passed: true,
      labels: reference.modes.map((m) => m.label),
    });
    await click("#study-parameters");
    await fill("#study-values", "40, 80, 120");
    await click("#save-study");
    const study = JSON.parse(await downloaded("study.json"));
    if (!isDeepStrictEqual(study.values, [0.04, 0.08, 0.12]))
      throw Error("study display units were not converted to SI");
    const document = await call("DOM.getDocument", {}, sessionId);
    const input = await call(
      "DOM.querySelector",
      { nodeId: document.root.nodeId, selector: "#open-study" },
      sessionId,
    );
    await fill("#study-values", "1, 2");
    await call(
      "DOM.setFileInputFiles",
      { nodeId: input.nodeId, files: [out + "/downloads/study.json"] },
      sessionId,
    );
    await wait('document.querySelector("#study-values").value==="40, 80, 120"');
    report.checks.push({
      operation: "study definition SI conversion and reload",
      passed: true,
    });
    const denied = await ev(
      `fetch('/api',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'jobs'})}).then(r=>r.status)`,
    );
    if (denied !== 403)
      throw Error("unauthenticated local API request accepted");
    // Refresh must retain the session while preserving recorded jobs.
    await call("Page.reload", {}, sessionId);
    await wait(
      'document.querySelector("#jobs .job") && document.querySelector("#shape polygon")',
    );
    report.checks.push({
      operation: "page reload and local session protection",
      unauthenticated_status: denied,
      passed: true,
    });
  }
  if (args["--pillbox"] === "yes") {
    // Build the seminar dimensions using ordinary GUI fields, then run its sweep.
    await click("#new");
    await fill("#radius", 75);
    await fill("#length", 80);
    await fill("#modes", 4);
    await fill("#nr", 96);
    await fill("#nz", 105);
    await click("#preview");
    await click("#study-parameters");
    await fill("#study-values", "40, 80, 120");
    const before = await ev('document.querySelectorAll("#jobs .job").length');
    await click("#start-study");
    await wait(`document.querySelectorAll('#jobs .job').length>${before}`);
    await wait(
      'document.querySelector("#jobs .job strong").textContent.startsWith("計算完了")',
      90000,
    );
    await click("#jobs .job button");
    await wait('document.querySelectorAll("#study-report button").length===3');
    const points = [];
    for (let i = 0; i < 3; i++) {
      const previous = await ev("currentJob");
      await click(`#study-report tr:nth-child(${i * 4 + 2}) button`);
      await wait(
        `currentJob!==${JSON.stringify(previous)} && !document.querySelector('#plot').disabled && !document.querySelector('#field-image').hidden`,
        45000,
      );
      await click("#pillbox-reference");
      await wait(
        'document.querySelectorAll("#reference-result tr").length===5',
        30000,
      );
      const reference = await ev("pillboxReference");
      const targets = reference.modes.filter((m) =>
        ["TM010", "TM011"].includes(m.label),
      );
      if (targets.length !== 2 || targets.some((m) => m.status !== "PASS"))
        throw Error("GUI length sweep analytical target failed");
      points.push({
        length_m: await ev(
          "currentResult.result.case.geometry.points_zr_m.at(-1)[0]",
        ),
        job_id: await ev("currentJob"),
        modes: targets,
      });
    }
    report.checks.push({
      operation:
        "R75 mm, L40/80/120 mm GUI sweep, saved fields, actual TM010/TM011 analytical comparison",
      passed: true,
      points,
    });
  }
  if (args["--extended"] === "yes") {
    const choose = async (selector, index) => {
      await ev(`document.querySelector(${JSON.stringify(selector)}).focus()`);
      for (const name of ["Home", ...Array(index).fill("ArrowDown")])
        for (const type of ["keyDown", "keyUp"])
          await call(
            "Input.dispatchKeyEvent",
            {
              type,
              key: name,
              code: name,
              windowsVirtualKeyCode: name === "Home" ? 36 : 40,
            },
            sessionId,
          );
    };
    await choose("#study-kind", 1);
    await fill("#study-values", "1, 2");
    const beforeStudy = await ev(
      'document.querySelectorAll("#jobs .job").length',
    );
    await click("#start-study");
    await wait(
      `document.querySelectorAll('#jobs .job').length > ${beforeStudy}`,
    );
    await wait(
      'document.querySelector("#jobs .job strong").textContent.startsWith("計算完了")',
      30000,
    );
    await click("#jobs .job button");
    await wait('document.querySelector("#study-report table")');
    report.checks.push({
      operation: "mesh refinement from GUI",
      text: await ev('document.querySelector("#study-report").textContent'),
    });
    const files = [
      "seminar_pillbox_half_electric",
      "seminar_pillbox_half_magnetic",
      "seminar_4cell_flat",
      "seminar_4cell_rounded",
      "seminar_7cell_rounded",
      "seminar_4cell_flat_full_ends",
      "seminar_4cell_rounded_full_ends",
    ];
    for (const name of files) {
      const fixture = JSON.parse(
        await readFile(resolve(`examples/${name}.json`), "utf8"),
      );
      const { root } = await call("DOM.getDocument", {}, sessionId);
      const { nodeId } = await call(
        "DOM.querySelector",
        { nodeId: root.nodeId, selector: "#open" },
        sessionId,
      );
      await call(
        "DOM.setFileInputFiles",
        { nodeId, files: [resolve(`examples/${name}.json`)] },
        sessionId,
      );
      await wait(
        `document.querySelector('#dirty').textContent==='入力を読込済み' && document.querySelector('#name').value===${JSON.stringify(fixture.name)}`,
      );
      if (name.includes("half_")) await click("#reflect");
      const count = fixture.solver?.modes ?? 3;
      if (Number(await ev('document.querySelector("#modes").value')) !== count)
        throw Error("file import mode count mismatch");
      const old = await ev('document.querySelectorAll("#jobs .job").length');
      await click("#run");
      await wait(`document.querySelectorAll('#jobs .job').length > ${old}`);
      await wait(
        'document.querySelector("#jobs .job strong").textContent.startsWith("計算完了")',
        45000,
      );
      await click("#jobs .job button");
      await wait(
        `document.querySelector('#rf-table tr') && document.querySelectorAll('#rf-table tr').length===${count + 1} && document.querySelector('#result-name').textContent===${JSON.stringify(fixture.name + (name.includes("half_") ? " [reflected full cavity]" : ""))} && !document.querySelector('#plot').disabled`,
        45000,
      );
      const modes = [];
      for (let i = 0; i < count; i++) {
        await choose("#mode", i);
        const previous = await ev('document.querySelector("#field-image").src');
        await click("#plot");
        await wait(
          `!document.querySelector('#plot').disabled && document.querySelector('#field-image').src!==${JSON.stringify(previous)} && document.querySelector('#field-image').naturalWidth>0`,
          45000,
        );
        modes.push(await ev('document.querySelector("#mode").value'));
      }
      if (name.includes("cell") && !name.includes("full_ends")) {
        await ev(
          `document.querySelector('#analyze-band').closest('details').open=true`,
        );
        await fill("#band-count", count);
        await click("#analyze-band");
        await wait('!document.querySelector("#dispersion").hidden');
      }
      if (name.includes("full_ends")) {
        await ev(
          `document.querySelector('#analyze-band').closest('details').open=true`,
        );
        await fill("#band-count", count);
        await click("#analyze-band");
        await wait(
          'document.querySelector("#band-result").textContent.includes("同定できません")',
        );
      }
      report.checks.push({
        operation: "file input, solve, all saved modes",
        fixture: name,
        job_id: await ev("currentJob"),
        modes,
        rows: await ev('document.querySelectorAll("#rf-table tr").length'),
        phase_labels: await ev('!document.querySelector("#dispersion").hidden'),
      });
      console.log(`Verified ${name}: ${modes.length} modes`);
    }
  }
  if (args["--general"] === "yes") {
    const choose = async (selector, index) => {
      await ev(`document.querySelector(${JSON.stringify(selector)}).focus()`);
      for (const name of ["Home", ...Array(index).fill("ArrowDown")])
        for (const type of ["keyDown", "keyUp"])
          await call(
            "Input.dispatchKeyEvent",
            {
              type,
              key: name,
              code: name,
              windowsVirtualKeyCode: name === "Home" ? 36 : 40,
            },
            sessionId,
          );
    };
    const runAndOpen = async () => {
      const old = await ev('document.querySelectorAll("#jobs .job").length');
      await click("#run");
      await wait(`document.querySelectorAll('#jobs .job').length>${old}`);
      await wait(
        'document.querySelector("#jobs .job strong").textContent.startsWith("計算完了")',
        30000,
      );
      const previous = await ev('document.querySelector("#field-image").src');
      await click("#jobs .job button");
      await wait(
        `!document.querySelector('#plot').disabled && document.querySelector('#field-image').naturalWidth>0 && document.querySelector('#field-image').src!==${JSON.stringify(previous)}`,
        30000,
      );
    };
    await click("#new");
    await wait(
      'document.querySelector("#name").value==="新しい空洞" && document.querySelector("#radius").value==="60"',
    );
    await choose("#geometry-type", 1);
    await click("#add-point");
    for (const [i, z, r] of [
      [1, 0, 40],
      [2, 15, 60],
      [3, 30, 40],
    ]) {
      await fill(`#points tbody tr:nth-child(${i}) td:nth-child(2) input`, z);
      await fill(`#points tbody tr:nth-child(${i}) td:nth-child(3) input`, r);
    }
    await click("#preview");
    await ev(
      "document.querySelector('#append-section').closest('details').open=true",
    );
    await click("#append-section");
    await wait('document.querySelectorAll("#sections input").length===1');
    for (const count of [3, 5]) {
      await fill("#sections input", count);
      await click("#assemble");
      await wait(
        `document.querySelectorAll('#points tbody tr').length===${2 * count + 1}`,
      );
      await fill("#name", `Synthetic polygon ${count}`);
      await runAndOpen();
      report.checks.push({
        operation: "new polygon with reusable section assembly",
        count,
        vertices: await ev(
          'document.querySelectorAll("#points tbody tr").length',
        ),
        rows: await ev('document.querySelectorAll("#rf-table tr").length'),
      });
    }
    await click("#new");
    await wait(
      'document.querySelector("#name").value==="新しい空洞" && document.querySelector("#radius").value==="60"',
    );
    await choose("#geometry-type", 3);
    await click("#add-point");
    for (const [i, z, r] of [
      [1, 0, 40],
      [2, 10, 50],
      [3, 20, 40],
    ]) {
      await fill(`#points tbody tr:nth-child(${i}) td:nth-child(2) input`, z);
      await fill(`#points tbody tr:nth-child(${i}) td:nth-child(3) input`, r);
    }
    for (let i = 1; i <= 2; i++) {
      await click("#add-arc");
      await fill(`#arcs tbody tr:nth-child(${i}) td:nth-child(1) input`, i);
      await fill(`#arcs tbody tr:nth-child(${i}) td:nth-child(2) input`, 10);
      await choose(`#arcs tbody tr:nth-child(${i}) select`, 1);
    }
    await click("#preview");
    await ev(
      "document.querySelector('#append-section').closest('details').open=true",
    );
    await click("#append-section");
    await wait('document.querySelectorAll("#sections input").length===1');
    for (const count of [3, 5]) {
      await fill("#sections input", count);
      await click("#assemble");
      await wait(
        `document.querySelectorAll('#arcs tbody tr').length===${2 * count}`,
      );
      await fill("#name", `Synthetic arcs ${count}`);
      await runAndOpen();
      report.checks.push({
        operation: "new arcs with reusable section assembly",
        count,
        arcs: await ev('document.querySelectorAll("#arcs tbody tr").length'),
      });
    }
    // Modify a circular radius through its numeric field; it detaches the recipe.
    await fill("#arcs tbody tr:first-child td:nth-child(2) input", 11);
    await click("#preview");
    await runAndOpen();
    report.checks.push({
      operation: "edit circular radius without JSON",
      radius_mm: await ev(
        'document.querySelector("#arcs tbody tr:first-child td:nth-child(2) input").value',
      ),
    });
    // Real GUI cancellation followed by normal job retry is checked separately.
    await fill("#nr", 256);
    await fill("#nz", 768);
    const old = await ev('document.querySelectorAll("#jobs .job").length');
    await click("#run");
    await wait(`document.querySelectorAll('#jobs .job').length>${old}`);
    await click("#jobs .job button");
    await wait(
      'document.querySelector("#jobs .job strong").textContent==="中止"',
    );
    report.checks.push({ operation: "cancel from GUI", status: "cancelled" });
    await fill("#nr", 24);
    await fill("#nz", 32);
    await runAndOpen();
    report.checks.push({
      operation: "retry after cancellation",
      status: "complete",
    });
    await ev(
      "document.querySelector('#import-result').closest('details').open=true",
    );
    await fill("#import-path", resolve("benchmarks/validation/shaped_cell"));
    await click("#import-result");
    await wait(
      'document.querySelector("#result-name").textContent==="synthetic necked cavity; closed ends; not KEK geometry" && !document.querySelector("#plot").disabled',
      30000,
    );
    report.checks.push({
      operation: "import old NG output",
      name: await ev('document.querySelector("#result-name").textContent'),
    });
  }
  if (args["--ends"] === "yes") {
    await click("#new");
    await wait('document.querySelector("#radius").value==="60"');
    await ev(
      "document.querySelector('#append-section').closest('details').open=true",
    );
    for (const [i, r, l] of [
      [0, 50, 10],
      [1, 60, 20],
      [2, 50, 15],
    ]) {
      await fill("#radius", r);
      await fill("#length", l);
      await click("#append-section");
      await wait(
        `document.querySelectorAll('#sections .job').length===${i + 1}`,
      );
    }
    await fill("#sections .job:nth-child(2) input", 3);
    await click("#sections .job:first-child button");
    await wait('document.querySelector("#length").value==="10"');
    await fill("#length", 12);
    await click("#replace-section");
    await wait('sections[0].geometry.points_zr_m.at(-1)[0]===0.012');
    await click(
      '#sections .job:nth-child(3) button[aria-label="部分 3 を前へ"]',
    );
    await click(
      '#sections .job:nth-child(2) button[aria-label="部分 2 を後へ"]',
    );
    await click("#assemble");
    await wait(
      'document.querySelector("#dirty").textContent.includes("組立を展開済み")',
    );
    const before = await ev('document.querySelectorAll("#jobs .job").length');
    await click("#run");
    await wait(`document.querySelectorAll('#jobs .job').length>${before}`);
    await wait(
      'document.querySelector("#jobs .job strong").textContent.startsWith("計算完了")',
      30000,
    );
    await click("#jobs .job button");
    await wait(
      '!document.querySelector("#plot").disabled && !document.querySelector("#field-image").hidden',
      30000,
    );
    const project = await ev("currentResult.project");
    const profile = project.case.geometry.points_zr_m;
    if (
      Math.abs(profile.at(-1)[0] - 0.087) > 1e-14 ||
      project.sections.map((s) => s.count).join(",") !== "1,3,1" ||
      Math.abs(project.sections[0].geometry.points_zr_m.at(-1)[0] - 0.012) >
        1e-14
    )
      throw Error("End editing or order was not preserved");
    report.checks.push({
      operation:
        "independent left/right end assembly, edit selected end, reorder, expand and solve",
      passed: true,
      job_id: await ev("currentJob"),
      length_m: profile.at(-1)[0],
      counts: project.sections.map((s) => s.count),
    });
  }
  if (args["--restore-id"]) {
    const id = args["--restore-id"];
    const selector = `#jobs .job[data-job="${id}"] button`;
    await wait(`document.querySelector(${JSON.stringify(selector)})`);
    const before = await ev('document.querySelectorAll("#jobs .job").length');
    await click(selector);
    await wait(
      `currentJob===${JSON.stringify(id)} && !document.querySelector('#plot').disabled && !document.querySelector('#field-image').hidden`,
      30000,
    );
    await click("#restore");
    await wait(
      'document.querySelector("#radius").value==="65" && document.querySelector("#length").value==="95"',
    );
    if ((await ev('document.querySelectorAll("#jobs .job").length')) !== before)
      throw Error("Restoring old result started a solve");
    report.checks.push({
      operation:
        "server restart, old result and editing input restored without a solve",
      job_id: id,
      passed: true,
    });
  }
  if (args["--contour-case"]) {
    const filename = resolve(args["--contour-case"]);
    const fixture = JSON.parse(await readFile(filename, "utf8"));
    const curved = fixture.geometry.type === "curved_contour";
    const { root } = await call("DOM.getDocument", {}, sessionId);
    const { nodeId } = await call("DOM.querySelector", { nodeId: root.nodeId, selector: "#open" }, sessionId);
    await call("DOM.setFileInputFiles", { nodeId, files: [filename] }, sessionId);
    await wait(`document.querySelector("#geometry-type").value === ${JSON.stringify(fixture.geometry.type)} && document.querySelector("#preview-note").textContent.includes(${JSON.stringify(curved ? "解析曲線の弦近似" : "閉じた一般輪郭")})`);
    if (!await ev('document.querySelector("#z-min").disabled && document.querySelector("#z-max").disabled')) throw Error("contour end tags must not expose ignored edits");
    const original = await ev("collect().case.geometry");
    if (!isDeepStrictEqual(original, fixture.geometry)) throw Error("contour import changed vertices or tags");
    const count = await ev('document.querySelector("#shape polygon").points.numberOfItems');
    if (!curved && count !== fixture.geometry.vertices_zr_m.length) throw Error("contour preview added phantom vertices");
    if (curved) {
      await fill("#curve-chord", fixture.geometry.chord_tolerance_m * 500);
      original.chord_tolerance_m = fixture.geometry.chord_tolerance_m / 2;
      if (!isDeepStrictEqual(await ev("collect().case.geometry"), original)) throw Error("curve edit changed source primitives");
      await click("#preview");
      await wait(`document.querySelector("#shape polygon").points.numberOfItems > ${count}`);
      if (!await ev('document.querySelector("#preview-note").textContent.includes("体積差")')) throw Error("curve preview lacks geometry error");
    }
    let contourControls;
    if (args["--contour-auto"] === "yes") {
      if (!isDeepStrictEqual(await ev("collect().case.mesh.contour_mesh"), fixture.mesh.contour_mesh)) throw Error("contour mesh import changed controls");
      if (!await ev('["nr","nz","triangulation"].every(id=>document.getElementById(id).disabled)')) throw Error("unused profile mesh controls are enabled");
      if (args["--curved-fem"] === "yes") {
        await ev('document.querySelector("#geometry-order").value="2"; document.querySelector("#geometry-order").dispatchEvent(new Event("change", {bubbles:true}))');
        await fill("#quadrature-order", 12);
        await fill("#curved-refinement-levels", 1);
      }
      const curvedFEM = args["--curved-fem"] === "yes";
      for (const [selector,value] of [["#contour-edge",curvedFEM?20:10],["#contour-angle",curvedFEM?10:12],["#contour-triangles",curvedFEM?8000:4000],["#contour-rounds",curvedFEM?12:8]]) await fill(selector,value);
      contourControls = {max_edge_m:curvedFEM ? .02 : .01,min_angle_deg:curvedFEM?10:12,max_triangles:curvedFEM?8000:4000,max_rounds:curvedFEM?12:8};
      if (!isDeepStrictEqual(await ev("collect().case.mesh.contour_mesh"),contourControls)) throw Error("contour mesh edits lost");
      const previous = await ev('document.querySelectorAll("#jobs .job").length');
      await click("#run");
      await wait(`document.querySelectorAll('#jobs .job').length>${previous}`);
      await wait('document.querySelector("#jobs .job strong").textContent.startsWith("計算完了")',60000);
      await click("#jobs .job button");
      await wait(`currentResult?.result?.case?.geometry?.type === ${JSON.stringify(fixture.geometry.type)} && !document.querySelector("#field-image").hidden`,30000);
      if (!isDeepStrictEqual(await ev("currentResult.result.case.mesh.contour_mesh"),contourControls)) throw Error("saved contour result lost controls");
      if (await ev("currentResult.result.field_space?.element_order") !== 2) throw Error("contour solve lost P2 order");
      report.checks.push({operation:"contour mesh controls edited, automatic P2 solve and saved result",passed:true,controls:contourControls});
    }
    await click("#export");
    let exported;
    for (let i=0; i<100; ++i) {
      try { exported=JSON.parse(await readFile(out+"/downloads/case.json", "utf8")); break; } catch {}
      await sleep(100);
    }
    if (!exported || !isDeepStrictEqual(exported.geometry, original)) throw Error("contour export lost geometry");
    if (contourControls && !isDeepStrictEqual(exported.mesh.contour_mesh,contourControls)) throw Error("contour export lost controls");
    await call("DOM.setFileInputFiles", { nodeId, files: [out+"/downloads/case.json"] }, sessionId);
    await wait('document.querySelector("#dirty").textContent === "入力を読込済み"');
    if (!isDeepStrictEqual(await ev("collect().case.geometry"), original)) throw Error("contour reopen changed geometry");
    if (contourControls && !isDeepStrictEqual(await ev("collect().case.mesh.contour_mesh"),contourControls)) throw Error("contour reopen lost controls");
    if (args["--mixed-end"] === "yes") {
      if (await ev('document.querySelector("#z-min").value') !== "mixed") throw Error("mixed end summary lost");
      report.checks.push({ operation: "mixed end tags preserved in disabled summary", passed: true });
    }
    report.checks.push({ operation: "contour file import, closed preview, export and reopen", passed: true, vertices: count });
    if (args["--curved-fem"] === "yes") {
      const controls = await ev("({geometry:collect().case.mesh.geometry_order,levels:collect().case.mesh.curved_refinement_levels,quadrature:collect().case.solver.quadrature_order})");
      if (!isDeepStrictEqual(controls,{geometry:2,levels:1,quadrature:12})) throw Error("curved controls lost on export/reopen");
      if (await ev("currentResult.result.field_space.geometry_order") !== 2 || await ev("currentResult.result.field_space.curved_refinement_levels") !== 1) throw Error("saved curved field declaration lost");
      if (!await ev('currentResult.result.surface_extrema?.version === 2 && Number.isFinite(currentResult.result.modes[0].epk_over_eacc_estimate) && !document.querySelector("#rf-table").textContent.includes("NaN")')) throw Error("curved peak bounds not exposed in RF output");
      if (!await ev('currentResult.result.modes[0].peak_status.includes("not certified")')) throw Error("discrete extrema presented as physical certification");
      if (!await ev('currentResult.result.surface_corner_diagnostics?.physical_peak_status === "UNVERIFIED" && document.querySelector("#rf-details").textContent.includes("物理ピークの収束は未確認")')) throw Error("analytic corner diagnostics lost in GUI");

      report.checks.push({operation:"curved geometry, quadrature and refinement controls; solve, plot and roundtrip",passed:true,controls});
      await ev('document.querySelector("#study-kind").value="fixed_geometry_convergence"; document.querySelector("#study-kind").dispatchEvent(new Event("change", {bubbles:true}))');
      await fill("#study-values", "0, 1");
      await wait('document.querySelector("#study-parameter").value === "/case/mesh/curved_refinement_levels"');
      const before = await ev('document.querySelectorAll("#jobs .job").length');
      await click("#start-study");
      await wait(`document.querySelectorAll('#jobs .job').length>${before}`);
      await wait('document.querySelector("#jobs .job strong").textContent.startsWith("計算完了")',120000);
      await click("#jobs .job button");
      await wait('activeStudy?.study?.kind === "fixed_geometry_convergence"');
      if (await ev("activeStudy.numerical_status") !== "PASS") throw Error("fixed curved GUI Study failed numerical gates");
      report.checks.push({operation:"fixed curved geometry Study from GUI",passed:true,status:await ev("activeStudy.numerical_status")});
      await ev('document.querySelector("#rf-details").closest("details").open=true');
      for (const [selector, filename] of [["#curved-fem-controls","curved-controls.png"],["#study-report","fixed-study.png"],["#rf-details","corner-diagnostics.png"]]) {
        await ev(`document.querySelector(${JSON.stringify(selector)}).scrollIntoView({block:"center",behavior:"instant"})`);
        const shot = await call("Page.captureScreenshot", {}, sessionId);
        await writeFile(out+"/"+filename, Buffer.from(shot.data,"base64"));
      }

    }

  }
  if (args["--curved-reflection"] === "yes") {
    const base = JSON.parse(await readFile(resolve(args["--contour-case"]), "utf8"));
    for (const side of ["z_min", "z_max"]) for (const tag of ["electric_symmetry", "magnetic_symmetry"]) {
      const fixture = structuredClone(base);
      const axis = fixture.geometry.curves.find((c,i)=>fixture.geometry.edge_tags[i]==="axis");
      const plane = side === "z_min" ? 0 : Math.max(axis.start_zr_m[0],axis.end_zr_m[0]);
      const edges = fixture.geometry.curves.flatMap((c,i)=>c.type==="line" && c.start_zr_m[0]===plane && c.end_zr_m[0]===plane ? [i] : []);
      if (!edges.length) throw Error("reflection fixture needs an explicit flat end");
      for (const i of edges) fixture.geometry.edge_tags[i]=tag;
      fixture.mesh.geometry_order=2;
      fixture.mesh.curved_refinement_levels=1;
      fixture.solver.quadrature_order=12;
      const path = out+`/reflection-${side}-${tag}.json`;
      await writeFile(path,JSON.stringify(fixture));
      const {root} = await call("DOM.getDocument",{},sessionId);
      const {nodeId} = await call("DOM.querySelector",{nodeId:root.nodeId,selector:"#open"},sessionId);
      await call("DOM.setFileInputFiles",{nodeId,files:[path]},sessionId);
      await wait(`document.querySelector("#${side.replace("_","-")}").value === ${JSON.stringify(tag)} && collect().case.mesh.geometry_order===2`);
      if (await ev('document.querySelector("#reflect").checked')) throw Error("reflection unexpectedly enabled after import");
      await click("#reflect");
      const before = await ev('document.querySelectorAll("#jobs .job").length');
      await click("#run");
      await wait(`document.querySelectorAll("#jobs .job").length>${before}`);
      await wait('document.querySelector("#jobs .job strong").textContent.startsWith("計算完了")',120000);
      await click("#jobs .job button");
      await wait(`currentResult?.result?.reflection?.side === ${JSON.stringify(side)} && currentResult.result.reflection.parity === ${tag==="electric_symmetry"?1:-1} && !document.querySelector("#field-image").hidden`,60000);
      const result = await ev("currentResult.result");
      if (result.case.rf.normalization_j !== 2*fixture.rf.normalization_j || Math.abs(result.modes[0].stored_energy_j/result.case.rf.normalization_j-1)>1e-7) throw Error("reflected GUI energy incorrect");
      if (!await ev('document.querySelector("#rf-details").textContent.includes("部分スペクトル")')) throw Error("GUI reflection mode semantics missing");
      report.checks.push({operation:"curved reflection checkbox, solve, saved result and plot",side,tag,passed:true});
    }
    await ev('document.querySelector("#rf-details").closest("details").open=true;document.querySelector("#rf-details p").scrollIntoView({block:"start",behavior:"instant"})');
    const shot=await call("Page.captureScreenshot",{},sessionId);
    await writeFile(out+"/curved-reflection.png",Buffer.from(shot.data,"base64"));
  }
  if (args["--tangent-request"]) {
    const loadFile = async (selector, filename) => {
      const {root}=await call("DOM.getDocument",{},sessionId);
      const {nodeId}=await call("DOM.querySelector",{nodeId:root.nodeId,selector},sessionId);
      await call("DOM.setFileInputFiles",{nodeId,files:[resolve(filename)]},sessionId);
    };
    await ev('document.querySelector("#tangent-panel").open=true');
    const oldCase=await ev("collect().case");
    await loadFile("#tangent-open",args["--tangent-request"]);
    await wait('tangentResult?.construction.status === "CANDIDATES"');
    if (!await ev('document.querySelector("#tangent-apply").disabled && document.querySelector("#tangent-candidate").value === ""')) throw Error("tangent candidate was automatically selected or applied");
    if (!isDeepStrictEqual(oldCase,await ev("collect().case"))) throw Error("tangent preview changed current case");
    report.checks.push({operation:"tangent candidates preserve project and require explicit selection",passed:true});
    await click("#tangent-candidate");
    for (const key of ["ArrowDown","Enter"]) {
      const code=key==="ArrowDown"?40:13;
      for (const type of ["keyDown","keyUp"]) await call("Input.dispatchKeyEvent",{type,key,code:key,windowsVirtualKeyCode:code},sessionId);
    }
    await wait('document.querySelector("#tangent-candidate").value === "0"');
    await click("#tangent-build");
    await wait('tangentResult?.construction.status === "CASE_VALIDATED"');
    const built=await ev("tangentResult.construction");
    if (built.request.schema_version === 2) {
      if (built.schema_version !== 2 || built.enumeration.arc_filter_status !== "CERTIFIED_MEMBERSHIP_AND_FRACTIONS") throw Error("GUI lost certified construction version");
      const selected=built.enumeration.candidates[built.candidate_index];
      if (!selected.trim_contact_error_bounds_m.every(x=>x<=built.request.controls.position_tolerance_m)) throw Error("GUI trim contact error exceeds request");
      if (!await ev('document.querySelector("#tangent-status").textContent.includes("接点誤差上界")')) throw Error("GUI does not display contact error bound");
      report.checks.push({operation:"version 2 certificate and contact error bound display",passed:true});
    }

    await click("#tangent-save");
    let saved;
    for (let n=0;n<100;n++) {
      try {saved=JSON.parse(await readFile(out+"/downloads/tangent-construction.json","utf8"));break;} catch {}
      await sleep(100);
    }
    if (!isDeepStrictEqual(saved,built)) throw Error("saved tangent document differs from displayed construction");
    await fill("#tangent-request",JSON.stringify(built.request));
    if (!await ev('!tangentResult && document.querySelector("#tangent-apply").disabled && document.querySelector("#tangent-save").disabled')) throw Error("request edit retained stale construction");
    report.checks.push({operation:"explicit tangent selection, closure check, download and edit invalidation",passed:true});
    await loadFile("#tangent-open",out+"/downloads/tangent-construction.json");
    await wait('tangentResult?.construction.status === "CASE_VALIDATED"');
    await click("#tangent-apply");
    if (!isDeepStrictEqual(await ev("collect().case.geometry"),built.case.geometry)) throw Error("applied tangent geometry differs from saved case");
    await click("#preview");
    await wait('document.querySelector("#shape polygon") && collect().case.geometry.type === "curved_contour"');
    const before=await ev('document.querySelectorAll("#jobs .job").length');
    await click("#run");
    await wait(`document.querySelectorAll("#jobs .job").length>${before}`);
    await wait('document.querySelector("#jobs .job strong").textContent.startsWith("計算完了")',120000);
    await click("#jobs .job button");
    await wait(`currentResult?.result?.case?.name === ${JSON.stringify(built.case.name)} && !document.querySelector("#field-image").hidden`,60000);
    const computed=await ev("currentResult.result");
    if (!isDeepStrictEqual(computed.case.geometry,built.case.geometry)) throw Error("GUI solve lost constructed geometry");
    report.checks.push({operation:"saved tangent replay, explicit apply, FEM solve and saved plot",frequency_hz:computed.modes[0].frequency_hz,passed:true});
    const corrupt=structuredClone(built);corrupt.case.rf.normalization_j*=2;
    await writeFile(out+"/corrupt-construction.json",JSON.stringify(corrupt));
    await loadFile("#tangent-open",out+"/corrupt-construction.json");
    await wait('!document.querySelector("#error").hidden && document.querySelector("#error").textContent.includes("replay")');
    if (!await ev('document.querySelector("#tangent-apply").disabled')) throw Error("corrupt tangent replay left apply enabled");
    report.checks.push({operation:"modified saved construction rejected with apply disabled",passed:true});
    await loadFile("#tangent-open",out+"/downloads/tangent-construction.json");
    await wait('tangentResult?.construction.status === "CASE_VALIDATED"');
    await ev('document.querySelector("#error").hidden=true;document.querySelector("#tangent-panel").scrollIntoView({block:"start",behavior:"instant"})');
    const shot=await call("Page.captureScreenshot",{},sessionId);
    await writeFile(out+"/tangent-construction.png",Buffer.from(shot.data,"base64"));
  }
  await ev("document.activeElement?.blur()");
  await wait("(window.scrollTo({top:0,behavior:'instant'}), window.scrollY===0)");
  const screenshot = await call("Page.captureScreenshot", {}, sessionId);
  await writeFile(
    out + "/workspace.png",
    Buffer.from(screenshot.data, "base64"),
  );
  report.source_changed_during_run = !isDeepStrictEqual(
    report.source_sha256,
    await sourceHashes(),
  );
  report.passed =
    !report.source_changed_during_run &&
    report.checks[0].radius_mm === "65" &&
    report.checks[0].length_mm === "95" &&
    report.checks[1].rows === 3 &&
    report.checks[1].image_width > 0 &&
    report.checks[2].value === "-1" &&
    report.external_requests.length === 0;
  if (!report.passed) throw Error("GUI acceptance checks failed");
  console.log(JSON.stringify(report, null, 2));
} catch (e) {
  report.error = String(e);
  process.exitCode = 1;
  console.error(e);
} finally {
  await writeFile(out + "/report.json", JSON.stringify(report, null, 2));
  ws?.close();
  browser.kill();
}
