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
