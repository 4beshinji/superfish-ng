"use strict";
const $ = (id) => document.getElementById(id);
const token = location.hash.slice(1) || sessionStorage.getItem("ng-session");
if (token) sessionStorage.setItem("ng-session", token);
history.replaceState(null, "", location.pathname);
let resultRequest = 0,
  plotRequest = 0,
  geometryOriginal = null,
  geometryDirty = true,
  explicitModel = null,
  accelerationOriginal = {},
  selectedSection = null;
let sections = [],
  assemblyActive = false,
  currentResult = null,
  currentJob = null,
  imageURL = null,
  imageBlob = null,
  dirty = false;
const number = (id) => {
  const n = Number($(id).value);
  if ($(id).value.trim() === "" || !Number.isFinite(n))
    throw Error(
      `${$(id).closest("label")?.textContent.trim() || id}: 数値を入力してください`,
    );
  return n;
};
function failure(error) {
  for (const e of document.querySelectorAll("[aria-invalid]"))
    e.removeAttribute("aria-invalid");
  const targets = [
    [/^radius_m/, "radius"],
    [/^length_m/, "length"],
    [/^nr /, "nr"],
    [/^nz /, "nz"],
    [/^beta /, "beta"],
    [/normalization_j/, "energy"],
    [/conductivity_s_per_m/, "conductivity"],
  ];
  for (const [pattern, id] of targets)
    if (pattern.test(error.message)) {
      $(id).setAttribute("aria-invalid", "true");
      $(id).focus({ preventScroll: true });
      break;
    }
  $("error").hidden = false;
  $("error").textContent = `入力・操作を確認してください\n${error.message}`;
}
async function api(action, data = {}, binary = false) {
  const r = await fetch("/api", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-NG-Token": token },
    body: JSON.stringify({ action, ...data }),
  });
  if (!r.ok) {
    const e = await r.json();
    throw Error(e.error);
  }
  return binary ? r.blob() : r.json();
}
function bind(id, fn) {
  $(id).addEventListener("click", async () => {
    try {
      $("error").hidden = true;
      await fn();
    } catch (e) {
      failure(e);
    }
  });
}
function markDirty() {
  dirty = true;
  $("dirty").textContent = "変更あり — 計算前に入力を確認";
  $("preview-note").textContent = "編集後の形状は未確認です。";
}
function download(name, data, type = "application/json") {
  const blob = data instanceof Blob ? data : new Blob([data], { type });
  const url = URL.createObjectURL(blob),
    a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}
function pointRow(z = 0, r = 0) {
  const tr = document.createElement("tr");
  tr.innerHTML =
    '<td></td><td><input type="number" step="any" aria-label="頂点のz mm"></td><td><input type="number" step="any" aria-label="頂点の半径 mm"></td><td><button type="button">削除</button></td>';
  const ins = tr.querySelectorAll("input");
  ins[0].value = z;
  ins[1].value = r;
  tr.querySelector("button").onclick = () => {
    const index = [...$("points").tBodies[0].rows].indexOf(tr);
    const arcs = [...$("arcs").tBodies[0].rows];
    if (
      arcs.some((row) =>
        [index, index + 1].includes(Number(row.querySelector("input").value)),
      )
    ) {
      failure(Error("この頂点に接続する円弧を先に削除してください。"));
      return;
    }
    for (const row of arcs) {
      const input = row.querySelector("input");
      if (Number(input.value) > index) input.value = Number(input.value) - 1;
    }
    tr.remove();
    renumber();
    geometryChanged();
  };
  $("points").tBodies[0].append(tr);
  renumber();
}
function renumber() {
  [...$("points").tBodies[0].rows].forEach(
    (row, i) => (row.cells[0].textContent = i),
  );
}
function arcRow(index = 1, r = 1, direction = "ccw") {
  const tr = document.createElement("tr");
  tr.innerHTML =
    '<td><input type="number" step="1" min="1" aria-label="円弧の終点番号"></td><td><input type="number" step="any" aria-label="円弧半径 mm"></td><td><select aria-label="円弧の方向"><option value="ccw">反時計回り</option><option value="cw">時計回り</option></select></td><td><button>削除</button></td>';
  const ins = tr.querySelectorAll("input");
  ins[0].value = index;
  ins[1].value = r;
  tr.querySelector("select").value = direction;
  tr.querySelector("button").onclick = () => {
    tr.remove();
    geometryChanged();
  };
  $("arcs").tBodies[0].append(tr);
}
function geometryChanged() {
  geometryDirty = true;
  assemblyActive = false;
  markDirty();
}
let contourMeshOriginal = null;
function isContour(kind) { return ["contour", "curved_contour"].includes(kind); }
function geometryLength(g) {
  if (g.type === "curved_contour") return Math.max(...g.curves.filter((c,i)=>g.edge_tags[i]==="axis").flatMap(c=>[c.start_zr_m[0],c.end_zr_m[0]]));
  return g.type === "contour" ? Math.max(...g.vertices_zr_m.map(p=>p[0])) : g.points_zr_m.at(-1)[0];
}
function updateCurvedControls() {
  const curved = $("geometry-order").value === "2";
  $("quadrature-order").disabled = !curved;
  $("curved-refinement-levels").disabled = !curved;
}
$("geometry-order").addEventListener("change", updateCurvedControls);
function showGeometry() {
  updateCurvedControls();
  $("curved-fem-controls").hidden = $("geometry-type").value !== "curved_contour";
  const kind = $("geometry-type").value;
  $("cylinder").hidden = kind !== "pillbox";
  $("profile-editor").hidden = kind === "pillbox" || isContour(kind);
  $("contour-note").hidden = !isContour(kind);
  $("contour-mesh-controls").hidden = !isContour(kind);
  for (const id of ["nr", "nz", "triangulation"]) $(id).disabled = isContour(kind);
  $("z-min").disabled = $("z-max").disabled = isContour(kind);
  if (!isContour(kind)) for (const id of ["z-min", "z-max"]) {
    if ($(id).value === "mixed") $(id).value = "pec";
    $(id).querySelector('option[value="mixed"]')?.remove();
  }
  $("curve-editor").hidden = kind !== "curved_contour";
  $("arc-editor").hidden = kind !== "arc_profile";
}
function geometry() {
  if ($("geometry-type").value === "curved_contour") {
    if (geometryOriginal?.type !== "curved_contour") throw Error("解析曲線のファイルを読み込んでください");
    const g = structuredClone(geometryOriginal);
    g.chord_tolerance_m = $("curve-chord").value === String(g.chord_tolerance_m * 1000) ? g.chord_tolerance_m : number("curve-chord") / 1000;
    g.chord_max_segments = number("curve-segments");
    return g;
  }
  if (!geometryDirty && geometryOriginal)
    return structuredClone(geometryOriginal);
  const kind = $("geometry-type").value;
  if (isContour(kind)) {
    if (geometryOriginal?.type !== "contour") throw Error("一般輪郭のファイルを読み込んでください");
    return structuredClone(geometryOriginal);
  }
  if (kind === "pillbox")
    return {
      type: kind,
      radius_m: number("radius") / 1000,
      length_m: number("length") / 1000,
    };
  const value = (input) => {
    if (input.value.trim() === "" || !Number.isFinite(Number(input.value)))
      throw Error("頂点・円弧の数値を確認してください");
    return Number(input.value);
  };
  const g = {
    type: kind,
    points_zr_m: [...$("points").tBodies[0].rows].map((row) =>
      [...row.querySelectorAll("input")].map((i) => value(i) / 1000),
    ),
  };
  if (kind === "arc_profile") {
    g.chord_tolerance_m = number("chord") / 1000;
    g.arcs = [...$("arcs").tBodies[0].rows].map((row) => {
      const ins = row.querySelectorAll("input");
      return {
        end_index: value(ins[0]),
        radius_m: value(ins[1]) / 1000,
        direction: row.querySelector("select").value,
      };
    });
  }
  return g;
}
function collect() {
  const mesh = {
    nr: number("nr"),
    nz: number("nz"),
    triangulation: $("triangulation").value,
  };
  if (isContour($("geometry-type").value) && $("contour-edge").value !== "") {
    const original = contourMeshOriginal?.max_edge_m;
    mesh.contour_mesh = {
      max_edge_m: original !== undefined && $("contour-edge").value === String(original * 1000)
        ? original : number("contour-edge") / 1000,
      min_angle_deg: number("contour-angle"),
      max_triangles: number("contour-triangles"),
      max_rounds: number("contour-rounds"),
    };
  }
  for (const [id, key] of [
    ["boundary-size", "boundary_max_edge_m"],
    ["corner-size", "corner_max_edge_m"],
    ["corner-radius", "corner_radius_m"],
  ])
    if ($(id).value !== "") mesh[key] = number(id) / 1000;
  const p = {
    project_version: 1,
    case: {
      schema_version: 2,
      name: $("name").value,
      geometry: geometry(),
      mesh,
      solver: { modes: number("modes") },
      rf: {
        beta: number("beta"),
        conductivity_s_per_m: number("conductivity"),
        normalization_j: number("energy"),
      },
      boundaries: { z_min: $("z-min").value, z_max: $("z-max").value },
    },
    reflect_full: $("reflect").checked,
    display_length_unit: "mm",
  };
  if (number("element-order") === 2) p.case.solver.element_order = 2;
  if (number("geometry-order") === 2) {
    p.case.mesh.geometry_order = 2;
    p.case.mesh.curved_refinement_levels = number("curved-refinement-levels");
    p.case.solver.quadrature_order = number("quadrature-order");
  }
  if (isContour(p.case.geometry.type)) delete p.case.boundaries;
  if (assemblyActive) p.sections = structuredClone(sections);
  if (explicitModel !== null) {
    p.case.schema_version = 3;
    p.case.model = structuredClone(explicitModel);
  }
  const lengthInput = (id, original) => original !== undefined && $(id).value === String(original * 1000)
    ? original : number(id) / 1000;
  for (const [id, key] of [["active-length", "active_length_m"], ["phase-origin", "phase_origin_m"]])
    if ($(id).value !== "") p.case.rf[key] = lengthInput(id, accelerationOriginal[key]);
  const hasStart = $("voltage-start").value !== "", hasEnd = $("voltage-end").value !== "";
  if (hasStart !== hasEnd) throw Error("電圧区間は開始と終了を両方指定してください");
  if (hasStart) p.case.rf.voltage_interval_m = [lengthInput("voltage-start", accelerationOriginal.voltage_interval_m?.[0]),
    lengthInput("voltage-end", accelerationOriginal.voltage_interval_m?.[1])];
  if ((Object.keys(p.case.rf).length > 3 || p.case.solver.element_order === 2) && explicitModel === null) {
    p.case.schema_version = 3;
    p.case.model = { physics: "rf_eigenmode", coordinates: "axisymmetric", polarization: "tm", azimuthal_index: 0,
      materials: [{ id: "vacuum", type: "vacuum" }], regions: [{ id: "cavity", material: "vacuum", domain: "interior" }] };
  }
  return p;
}
function setGeometry(g) {
  geometryOriginal = structuredClone(g);
  geometryDirty = false;
  if (isContour(g.type)) {
    $("geometry-type").value = g.type;
    $("curve-chord").value = (g.chord_tolerance_m ?? 0.001) * 1000;
    $("curve-segments").value = g.chord_max_segments ?? 20000;
    showGeometry(); return;
  }
  const pts = g.points_zr_m;
  const cylinder =
    g.type === "pillbox" ||
    (g.type === "profile" && pts?.length === 2 && pts[0][1] === pts[1][1]);
  $("geometry-type").value = cylinder ? "pillbox" : g.type;
  $("points").tBodies[0].replaceChildren();
  $("arcs").tBodies[0].replaceChildren();
  if (cylinder) {
    $("radius").value = (g.radius_m ?? pts[0][1]) * 1000;
    $("length").value = (g.length_m ?? pts[1][0]) * 1000;
    pointRow(0, number("radius"));
    pointRow(number("length"), number("radius"));
  } else for (const [z, r] of pts) pointRow(z * 1000, r * 1000);
  for (const a of g.arcs || [])
    arcRow(a.end_index, a.radius_m * 1000, a.direction);
  $("chord").value = (g.chord_tolerance_m ?? 0.00001) * 1000;
  showGeometry();
}
function applyProject(p) {
  const c = p.case;
  $("geometry-order").value = c.mesh.geometry_order ?? 1;
  $("curved-refinement-levels").value = c.mesh.curved_refinement_levels ?? 0;
  $("quadrature-order").value = c.solver.quadrature_order ?? 8;
  contourMeshOriginal = c.mesh.contour_mesh ? structuredClone(c.mesh.contour_mesh) : null;
  $("contour-edge").value = contourMeshOriginal ? contourMeshOriginal.max_edge_m * 1000 : "";
  $("contour-angle").value = contourMeshOriginal?.min_angle_deg ?? 10;
  $("contour-triangles").value = contourMeshOriginal?.max_triangles ?? 250000;
  $("contour-rounds").value = contourMeshOriginal?.max_rounds ?? 12;
  explicitModel = c.model ? structuredClone(c.model) : null;
  accelerationOriginal = structuredClone(c.rf);
  for (const [id, value] of [["active-length", c.rf.active_length_m], ["phase-origin", c.rf.phase_origin_m],
      ["voltage-start", c.rf.voltage_interval_m?.[0]], ["voltage-end", c.rf.voltage_interval_m?.[1]]])
    $(id).value = value === undefined ? "" : value * 1000;
  setGeometry(c.geometry);
  $("name").value = c.name;
  for (const [id, v] of Object.entries({
    nr: c.mesh.nr,
    nz: c.mesh.nz,
    modes: c.solver.modes,
    "element-order": c.solver.element_order ?? 1,
    beta: c.rf.beta,
    conductivity: c.rf.conductivity_s_per_m,
    energy: c.rf.normalization_j,
  }))
    $(id).value = v;
  $("z-min").value = c.boundaries?.z_min || "pec";
  $("z-max").value = c.boundaries?.z_max || "pec";
  if (isContour(c.geometry.type)) {
    const edges = c.geometry.type === "contour"
      ? c.geometry.vertices_zr_m.map((p,i,pts)=>[p,pts[(i+1)%pts.length]])
      : c.geometry.curves.map(c=>c.type === "line" ? [c.start_zr_m,c.end_zr_m] : null);
    const length = geometryLength(c.geometry);
    for (const [id, z] of [["z-min", 0], ["z-max", length]]) {
      const tags = new Set(edges.flatMap((e,i) => e && e[0][0]===z && e[1][0]===z && c.geometry.edge_tags[i]!=="axis" ? [c.geometry.edge_tags[i]] : []));
      if (!$(id).querySelector('option[value="mixed"]')) $(id).add(new Option("辺ごとに異なる境界", "mixed"));
      $(id).value = tags.size > 1 ? "mixed" : tags.size === 0 ? "pec" : [...tags][0];
    }
  }
  $("reflect").checked = p.reflect_full;
  $("triangulation").value = c.mesh.triangulation || "diagonal";
  for (const [id, key] of [
    ["boundary-size", "boundary_max_edge_m"],
    ["corner-size", "corner_max_edge_m"],
    ["corner-radius", "corner_radius_m"],
  ])
    $(id).value = c.mesh[key] === undefined ? "" : c.mesh[key] * 1000;
  sections = structuredClone(p.sections || []);
  assemblyActive = sections.length > 0;
  selectedSection = null;
  $("replace-section").disabled = true;
  renderSections();
  dirty = false;
  $("dirty").textContent = "入力を読込済み";
}
function renderSections() {
  $("sections").replaceChildren();
  sections.forEach((s, i) => {
    const div = document.createElement("div");
    div.className = "job";
    const label = document.createElement("label");
    label.textContent = `部分 ${i + 1} / ${s.geometry.type} — 繰り返し数`;
    const input = document.createElement("input");
    input.type = "number";
    input.min = 1;
    input.step = 1;
    input.value = s.count;
    input.onchange = () => {
      s.count = Number(input.value);
      assemblyActive = false;
      markDirty();
    };
    label.append(input);
    div.append(label);
    const edit = document.createElement("button");
    edit.textContent = "輪郭へ読込";
    edit.onclick = () => {
      setGeometry(s.geometry);
      assemblyActive = false;
      selectedSection = i;
      $("replace-section").disabled = false;
      markDirty();
      renderSections();
    };
    div.append(edit);
    const remove = document.createElement("button");
    remove.textContent = "削除";
    remove.onclick = () => {
      sections.splice(i, 1);
      selectedSection = null;
      $("replace-section").disabled = true;
      assemblyActive = false;
      renderSections();
      markDirty();
    };
    div.append(remove);
    for (const [text, delta] of [
      ["↑", -1],
      ["↓", 1],
    ]) {
      const move = document.createElement("button");
      move.textContent = text;
      move.setAttribute(
        "aria-label",
        `部分 ${i + 1} を${delta < 0 ? "前" : "後"}へ`,
      );
      move.disabled = i + delta < 0 || i + delta >= sections.length;
      move.onclick = () => {
        [sections[i], sections[i + delta]] = [sections[i + delta], sections[i]];
        selectedSection = null;
        $("replace-section").disabled = true;
        assemblyActive = false;
        renderSections();
        markDirty();
      };
      div.append(move);
    }
    if (selectedSection === i) {
      const selected = document.createElement("strong");
      selected.textContent = "編集対象";
      div.append(selected);
    }
    $("sections").append(div);
  });
}
function drawOutline(points, closed = false, approximation = null) {
  const svg = $("shape");
  svg.replaceChildren();
  const ns = "http://www.w3.org/2000/svg";
  const L = closed ? Math.max(...points.map(p => p[0])) : points.at(-1)[0],
    R = Math.max(...points.map((p) => p[1])),
    scale = Math.min(700 / L, 210 / R),
    x = (z) => 55 + z * scale,
    y = (r) => 235 - r * scale;
  const el = (tag, attrs, text) => {
    const e = document.createElementNS(ns, tag);
    for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
    if (text) e.textContent = text;
    svg.append(e);
    return e;
  };
  el("polygon", {
    points: (closed ? points : [[0, 0], ...points, [L, 0]])
      .map(([z, r]) => `${x(z)},${y(r)}`)
      .join(" "),
    fill: "#d7e9f8",
    stroke: "#1d6d9b",
    "stroke-width": 2,
  });
  el("line", {
    x1: x(0),
    y1: y(0),
    x2: x(L),
    y2: y(0),
    stroke: "#526d84",
    "stroke-dasharray": "5 4",
  });
  el("text", { x: 55, y: 263 }, "軸 r=0");
  el("text", { x: 360, y: 263 }, `z →  全長 ${(L * 1000).toPrecision(6)} mm`);
  el("text", { x: 55, y: 18 }, `r ↑  最大半径 ${(R * 1000).toPrecision(6)} mm`);
  $("shape-info").textContent = `${points.length} 輪郭点`;
  if (closed) {
    $("preview-note").textContent = approximation
      ? `入力形状：解析曲線の弦近似をプレビュー。二次曲線要素を選択した場合、計算時に二次形状を構成します。指定弦誤差 ${approximation.tolerance_m * 1000} mm / 面積差 ${approximation.area_difference_m2.toExponential(4)} m² / 体積差 ${approximation.volume_difference_m3.toExponential(4)} m³（弦 − 解析）`
      : "入力形状：閉じた一般輪郭（辺タグは読込ファイルで指定）";
    return;
  }
  const boundaryNames = {
    pec: "金属端板",
    electric_symmetry: "電気対称",
    magnetic_symmetry: "磁気対称",
  };
  for (const [z, r, id] of [
    [0, points[0][1], "z-min"],
    [L, points.at(-1)[1], "z-max"],
  ]) {
    const tag = $(id).value;
    el("line", {
      x1: x(z),
      y1: y(0),
      x2: x(z),
      y2: y(r),
      stroke:
        tag === "electric_symmetry"
          ? "#058366"
          : tag === "magnetic_symmetry"
            ? "#b36b00"
            : "#1d6d9b",
      "stroke-width": 3,
      "stroke-dasharray": tag === "pec" ? "none" : "5 4",
    });
  }
  $("preview-note").textContent =
    `入力形状（円弧は指定弦誤差で表示）。側壁PEC / 左端: ${boundaryNames[$("z-min").value]} / 右端: ${boundaryNames[$("z-max").value]}`;
}
async function preview() {
  const r = await api("normalize", { document: collect() });
  drawOutline(r.outline_zr_m, r.outline_closed, r.geometry_approximation);
  return r.project;
}
bind("preview", preview);
bind("new", async () => {
  if (dirty && !confirm("編集中の内容を保存せず新規作成しますか？")) return;
  const r = await api("normalize", {
    document: {
      schema_version: 1,
      name: "新しい空洞",
      geometry: { type: "pillbox", radius_m: 0.06, length_m: 0.09 },
    },
  });
  applyProject(r.project);
  drawOutline(r.outline_zr_m, r.outline_closed, r.geometry_approximation);
});
$("open").onchange = async (e) => {
  try {
    if (!e.target.files.length) return;
    const r = await api("normalize", {
      document: await e.target.files[0].text(),
    });
    applyProject(r.project);
    drawOutline(r.outline_zr_m, r.outline_closed, r.geometry_approximation);
    $("error").hidden = true;
  } catch (err) {
    failure(err);
  } finally {
    e.target.value = "";
  }
};
bind("save", async () => {
  const p = await preview();
  download("cavity-project.json", JSON.stringify(p, null, 2));
  dirty = false;
  $("dirty").textContent = "保存用ファイルを出力";
});
bind("export", async () =>
  download("case.json", JSON.stringify((await preview()).case, null, 2)),
);
bind("add-point", () => {
  const rows = $("points").tBodies[0].rows;
  const last = rows[rows.length - 1]?.querySelectorAll("input");
  pointRow(
    last ? Number(last[0].value) + 10 : 0,
    last ? Number(last[1].value) : 50,
  );
  geometryChanged();
});
bind("add-arc", () => {
  arcRow();
  geometryChanged();
});
$("geometry-type").onchange = () => {
  showGeometry();
  geometryChanged();
};
for (const id of ["points", "arcs", "radius", "length", "chord"])
  $(id).addEventListener("input", geometryChanged);
bind("append-section", async () => {
  const r = await api("normalize", {
    document: { schema_version: 2, geometry: geometry() },
  });
  sections.push({ geometry: r.project.case.geometry, count: 1 });
  selectedSection = null;
  $("replace-section").disabled = true;
  assemblyActive = false;
  renderSections();
  markDirty();
});
bind("assemble", async () => {
  const p = collect();
  const r = await api("assemble", {
    case: p.case,
    sections,
    reflect_full: p.reflect_full,
  });
  applyProject(r.project);
  drawOutline(r.outline_zr_m, r.outline_closed, r.geometry_approximation);
  dirty = true;
  $("dirty").textContent = "組立を展開済み — 未保存";
});
bind("clear-sections", () => {
  sections = [];
  selectedSection = null;
  $("replace-section").disabled = true;
  assemblyActive = false;
  renderSections();
  markDirty();
});
bind("run", async () => {
  $("run").disabled = true;
  try {
    const p = await preview();
    await api("start", { document: p });
    await refreshJobs();
  } finally {
    $("run").disabled = false;
  }
});
const statusNames = {
  queued: "待機",
  running: "計算中",
  complete: "計算完了 / 数値検証は別途",
  failed: "失敗",
  cancelled: "中止",
  interrupted: "中断",
};
async function refreshJobs() {
  const jobs = await api("jobs");
  trackingJobs(jobs);
  const focused = document.activeElement?.closest("#jobs .job"),
    focusedJob = focused?.dataset.job,
    focusedButton = focused
      ? [...focused.querySelectorAll("button")].indexOf(document.activeElement)
      : -1;
  $("jobs").replaceChildren();
  if (!jobs.length) $("jobs").textContent = "計算はまだありません。";
  for (const j of jobs) {
    const row = document.createElement("div");
    row.className = "job";
    row.dataset.job = j.id;
    const title = document.createElement("strong");
    title.textContent = statusNames[j.status] || j.status;
    row.append(title);
    const desc = document.createElement("small");
    const stage =
      {
        "finite element solve": "有限要素計算",
        "saving fields and RF quantities": "場とRF量を保存中",
        saved: "保存済み",
        "imported saved result": "取込結果（再計算なし）",
      }[j.stage] ||
      j.stage?.replace("point ", "条件 ") ||
      "";
    desc.textContent = `${stage} / ${j.id}${j.elapsed_seconds !== undefined ? " / " + j.elapsed_seconds.toFixed(2) + "秒" : ""}${j.error ? " / " + j.error : ""}`;
    row.append(desc);
    const action = document.createElement("button");
    action.textContent = ["running", "queued"].includes(j.status)
      ? "中止"
      : "結果を開く";
    action.disabled = !["running", "queued", "complete"].includes(j.status);
    action.onclick = async () => {
      try {
        if (["running", "queued"].includes(j.status)) {
          await api("cancel", { id: j.id });
          await refreshJobs();
        } else if (j.kind === "study") await openStudy(j.id);
        else await openResult(j.id);
      } catch (e) {
        failure(e);
      }
    };
    row.append(action);
    const log = document.createElement("button");
    log.textContent = "ログ";
    log.onclick = async () => {
      try {
        const r = await api("log", { id: j.id });
        $("error").hidden = false;
        $("error").textContent = r.text || "ログは空です。";
      } catch (e) {
        failure(e);
      }
    };
    row.append(log);
    $("jobs").append(row);
  }
  if (focusedJob && focusedButton >= 0) {
    const row = [...$("jobs").children].find(
      (e) => e.dataset.job === focusedJob,
    );
    row
      ?.querySelectorAll("button")
      [focusedButton]?.focus({ preventScroll: true });
  }
}
bind("refresh", refreshJobs);
async function openResult(id) {
  const request = ++resultRequest;
  ++plotRequest;
  $("field-image").hidden = true;
  $("save-plot").disabled = true;
  const r = await api("result", { id });
  if (request !== resultRequest) return;
  currentResult = r;
  currentJob = id;
  $("result-controls").hidden = false;
  $("output-file").replaceChildren();
  for (const file of r.files) {
    const option = document.createElement("option");
    option.value = file;
    option.textContent = file;
    $("output-file").append(option);
  }
  $("reference-result").replaceChildren();
  $("save-reference").disabled = true;
  $("band-result").replaceChildren();
  $("dispersion").hidden = true;
  $("band-csv").disabled = true;
  $("result-name").textContent = r.result.case.name;
  $("result-state").textContent =
    (r.state.origin === "imported" ? "取込結果（再計算なし）。" : "") +
    "保存済みの結果を表示中。編集中の条件とは独立しています。メッシュ収束は未検証。";
  $("mode").replaceChildren();
  for (const q of r.result.modes) {
    const opt = document.createElement("option");
    opt.value = q.mode_index;
    opt.textContent = `${q.mode_index} — ${(q.frequency_hz / 1e6).toFixed(6)} MHz`;
    $("mode").append(opt);
  }
  $("probe-z").value = geometryLength(r.result.case.geometry) * 250;
  $("conventions").replaceChildren();
  for (const [key, value] of Object.entries(r.result.conventions)) {
    const p = document.createElement("p");
    p.textContent = `${key}: ${value}`;
    $("conventions").append(p);
  }
  renderRF();
  renderRFDetails();
  await plot();
}
const rfColumns = [
  ["mode_index", "番号"],
  ["frequency_hz", "周波数 [Hz]"],
  ["q0", "Q₀"],
  ["r_over_q_accelerator_ohm", "R/Q acc [Ω]"],
  ["r_over_q_circuit_ohm", "R/Q circuit [Ω]"],
  ["stored_energy_j", "U [J]"],
  ["transit_time_factor_abs", "TTF (abs)"],
  ["epk_over_eacc_estimate", "Epk/Eacc (推定)"],
];
function renderRF() {
  const table = document.createElement("table"),
    head = document.createElement("tr");
  for (const [, label] of rfColumns) {
    const th = document.createElement("th");
    th.textContent = label;
    head.append(th);
  }
  table.append(head);
  for (const q of currentResult.result.modes) {
    const row = document.createElement("tr");
    for (const [key] of rfColumns) {
      const td = document.createElement("td");
      td.textContent =
        q[key] === undefined ? "未評価" : q[key] === null ? "未定義" : Number(q[key]).toPrecision(7);
      row.append(td);
    }
    table.append(row);
  }
  $("rf-table").replaceChildren(table);
}
async function plot() {
  const request = ++plotRequest,
    job = currentJob;
  $("plot").disabled = true;
  $("result-state").textContent = "保存場を描画中…";
  try {
    const blob = await api(
      "plot",
      {
        id: currentJob,
        mode: number("mode"),
        probe_z_m: number("probe-z") / 1000,
        mesh: $("mesh-view").checked,
      },
      true,
    );
    if (request !== plotRequest || job !== currentJob) return;
    if (imageURL) URL.revokeObjectURL(imageURL);
    imageURL = URL.createObjectURL(blob);
    imageBlob = blob;
    $("field-image").src = imageURL;
    $("field-image").hidden = false;
    await $("field-image").decode();
    if (request !== plotRequest || job !== currentJob) return;
    $("save-plot").disabled = false;
    $("result-state").textContent =
      (currentResult.state.origin === "imported"
        ? "取込結果（再計算なし）。"
        : "") + "保存されたFEM場。計算完了 / メッシュ収束は未検証。";
  } catch (error) {
    if (request === plotRequest && job === currentJob) throw error;
  } finally {
    if (request === plotRequest) $("plot").disabled = false;
  }
}
bind("plot", plot);
bind("restore", () => {
  applyProject(currentResult.project);
  return preview();
});
bind("csv", () => {
  const rows = currentResult.result.modes,
    keys = Object.keys(rows[0]);
  download(
    "modes.csv",
    [
      keys.join(","),
      ...rows.map((q) => keys.map((k) => q[k] ?? "").join(",")),
    ].join("\n"),
    "text/csv",
  );
});
bind("save-plot", () => download("fields.png", imageBlob, "image/png"));
document.querySelector(".editor").addEventListener("input", markDirty);
window.addEventListener("beforeunload", (event) => {
  if (dirty) {
    event.preventDefault();
    event.returnValue = "";
  }
});
pointRow(0, 60);
pointRow(90, 60);
showGeometry();
if (!token) failure(Error("起動時に表示されたURLから開いてください。"));
else {
  preview().catch(failure);
  refreshJobs().catch(failure);
  setInterval(() => refreshJobs().catch(() => {}), 2500);
}

bind("import-result", async () => {
  const r = await api("import", { path: $("import-path").value });
  await refreshJobs();
  await openResult(r.id);
});
bind("download-output", async () =>
  download(
    $("output-file").value,
    await api(
      "download",
      { id: currentJob, file: $("output-file").value },
      true,
    ),
    "application/octet-stream",
  ),
);
let bandResult,
  bandRequest = 0;
bind("analyze-band", async () => {
  const view = resultRequest,
    request = ++bandRequest;
  $("band-result").textContent = "適用条件と実場を確認中…";
  $("dispersion").hidden = true;
  $("band-csv").disabled = true;
  try {
    const n = number("band-count");
    if (!Number.isInteger(n) || n < 2)
      throw Error("セル中心数は2以上の整数です");
    if (isContour(currentResult.result.case.geometry.type)) throw Error("バンド解析は周期的な半径profile形状に限定しています");
    const L = geometryLength(currentResult.result.case.geometry);
    const response = await api("band", {
      id: currentJob,
      cell_centers_z_m: Array.from({ length: n }, (_, i) => (L * i) / (n - 1)),
    });
    if (view !== resultRequest || request !== bandRequest) return;
    bandResult = response;
    const table = document.createElement("table");
    const heading = document.createElement("tr");
    for (const value of [
      "周波数順番号",
      "位相 [rad]",
      "零交差",
      "場の一致度",
      "fit残差 [Hz]",
    ]) {
      const th = document.createElement("th");
      th.textContent = value;
      heading.append(th);
    }
    table.append(heading);
    bandResult.modes.forEach((m, i) => {
      const row = document.createElement("tr");
      for (const value of [
        m.mode_index,
        m.phase_rad,
        m.zero_crossings,
        m.cell_overlap,
        bandResult.dispersion.residual_hz[i],
      ]) {
        const td = document.createElement("td");
        td.textContent = Number(value).toPrecision(7);
        row.append(td);
      }
      table.append(row);
    });
    $("band-result").replaceChildren(table);
    const svg = $("dispersion");
    svg.replaceChildren();
    svg.hidden = false;
    const ns = "http://www.w3.org/2000/svg",
      freq = bandResult.modes.map(
        (m) => currentResult.result.modes[m.mode_index - 1].frequency_hz / 1e6,
      ),
      lo = Math.min(...freq),
      hi = Math.max(...freq),
      x = (t) => 60 + (580 * t) / Math.PI,
      y = (f) => 210 - (165 * (f - lo)) / (hi - lo || 1);
    const add = (tag, attrs, text) => {
      const el = document.createElementNS(ns, tag);
      for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
      if (text) el.textContent = text;
      svg.append(el);
    };
    add("polyline", {
      points: Array.from({ length: 81 }, (_, i) => {
        const t = (i * Math.PI) / 80,
          f =
            (bandResult.dispersion.m1_hz +
              bandResult.dispersion.m2_hz * Math.cos(t)) /
            1e6;
        return `${x(t)},${y(f)}`;
      }).join(" "),
      fill: "none",
      stroke: "#55778e",
      "stroke-width": 2,
    });
    bandResult.modes.forEach((m, i) =>
      add("circle", {
        cx: x(m.phase_rad),
        cy: y(freq[i]),
        r: 5,
        fill: "#1767a6",
      }),
    );
    add(
      "text",
      { x: 60, y: 20 },
      `周波数 [MHz] ${lo.toFixed(4)} – ${hi.toFixed(4)} / f = m₁ + m₂ cosθ`,
    );
    add("text", { x: 60, y: 245 }, "0");
    add("text", { x: 300, y: 245 }, "位相 θ [rad]");
    add("text", { x: 635, y: 245 }, "π");
    $("band-csv").disabled = false;
  } catch (e) {
    if (view !== resultRequest || request !== bandRequest) return;
    $("band-result").textContent =
      "同定できません。通常のモード番号で結果を確認してください。";
    throw e;
  }
});
bind("band-csv", () =>
  download(
    "dispersion.csv",
    [
      "mode_index,phase_rad,frequency_hz,fit_residual_hz",
      ...bandResult.modes.map((m, i) =>
        [
          m.mode_index,
          m.phase_rad,
          currentResult.result.modes[m.mode_index - 1].frequency_hz,
          bandResult.dispersion.residual_hz[i],
        ].join(","),
      ),
    ].join("\n"),
    "text/csv",
  ),
);

let activeStudy,
  studyRequest = 0,
  studyParameterUnits = new Map();
async function updateStudyParameters(preferred) {
  const p = await preview();
  $("study-parameter").replaceChildren();
  studyParameterUnits = new Map();
  const add = (value, label, scale = 1) => {
    const opt = document.createElement("option");
    opt.value = value;
    opt.textContent = label;
    $("study-parameter").append(opt);
    studyParameterUnits.set(value, scale);
  };
  const kind = $("study-kind").value;
  if (kind === "mesh_convergence") {
    add("mesh_scale", "基準メッシュに対する細分倍率");
    $("study-hint").textContent =
      "nr/nzを倍率倍し、指定された最大辺長を倍率で割ります。元曲線と弦誤差は固定ですが、二次境界は変わることがあります。周波数・RF・軸場を別々に判定します。";
  } else if (kind === "fixed_geometry_convergence") {
    add("/case/mesh/curved_refinement_levels", "二次形状を保つ細分段数");
    $("study-hint").textContent = "二次曲線要素で使用します。元メッシュと二次形状を固定し、0, 1, 2などの段数を比較します。1段で要素数は4倍になります。";
  } else if (kind === "geometry_convergence") {
    add("/case/geometry/chord_tolerance_m", "曲線の最大弦誤差 [mm]", 0.001);
    $("study-hint").textContent =
      "元曲線とFEM設定を固定し、弦誤差を小さくします。arc_profile / curved_contourで使用できます。";
  } else {
    (p.case.geometry.points_zr_m || []).forEach((point, i) => {
      if (i)
        add(`/case/geometry/points_zr_m/${i}/0`, `頂点 ${i} のz [mm]`, 0.001);
      add(`/case/geometry/points_zr_m/${i}/1`, `頂点 ${i} の半径 [mm]`, 0.001);
    });
    (p.case.geometry.arcs || []).forEach((a, i) =>
      add(
        `/case/geometry/arcs/${i}/radius_m`,
        `円弧 ${i + 1} の半径 [mm]`,
        0.001,
      ),
    );
    for (const [key, label] of [
      ["beta", "粒子速度 β"],
      ["conductivity_s_per_m", "導電率 [S/m]"],
      ["normalization_j", "入力領域の蓄積エネルギー [J]"],
    ])
      add(`/case/rf/${key}`, label);
    (p.sections || []).forEach((section, i) =>
      add(`/sections/${i}/count`, `組立部分 ${i + 1} の繰り返し数`),
    );
    $("study-hint").textContent =
      "各条件を独立に計算します。同じ番号は同一物理モードを意味しません。形状を直接変更する掃引は組立定義から切り離した入力を保存します。";
  }
  if (
    preferred &&
    [...$("study-parameter").options].some((o) => o.value === preferred)
  )
    $("study-parameter").value = preferred;
  else if (kind === "sweep" && p.case.geometry.points_zr_m?.length === 2)
    $("study-parameter").value = "/case/geometry/points_zr_m/1/0";
  return p;
}
async function studyDefinition() {
  const selected = $("study-parameter").value;
  const project = await updateStudyParameters(selected);
  if (!$("study-parameter").value)
    throw Error("変更する項目を選択してください");
  const values = $("study-values")
    .value.split(/[\s,]+/)
    .filter(Boolean)
    .map(Number);
  if (values.length < 2 || values.some((v) => !Number.isFinite(v)))
    throw Error("2個以上の有限な数値を入力してください");
  const parameter = $("study-parameter").value;
  return {
    study_version: 1,
    project,
    kind: $("study-kind").value,
    parameter,
    values: values.map((v) => v * studyParameterUnits.get(parameter)),
  };
}
bind("study-parameters", () => updateStudyParameters());
$("study-kind").onchange = () => {
  if ($("study-kind").value === "mesh_convergence")
    $("study-values").value = "1, 2, 4";
  else if ($("study-kind").value === "fixed_geometry_convergence")
    $("study-values").value = "0, 1";
  else if ($("study-kind").value === "geometry_convergence")
    $("study-values").value = "0.01, 0.0025, 0.000625";
  updateStudyParameters().catch(failure);
};
bind("start-study", async () => {
  const study = await studyDefinition();
  await api("start-study", { study });
  await refreshJobs();
});
bind("save-study", async () =>
  download("study.json", JSON.stringify(await studyDefinition(), null, 2)),
);
$("open-study").onchange = async (event) => {
  try {
    const file = event.target.files[0];
    if (!file) return;
    const data = await api("normalize-study", { document: await file.text() });
    applyProject(data.project);
    $("study-kind").value = data.kind;
    await updateStudyParameters(data.parameter);
    $("study-values").value = data.values
      .map((v) => v / studyParameterUnits.get(data.parameter))
      .join(", ");
  } catch (e) {
    failure(e);
  } finally {
    event.target.value = "";
  }
};
async function openStudy(id) {
  const request = ++studyRequest;
  const response = await api("study-result", { id });
  if (request !== studyRequest) return;
  activeStudy = response;
  const report = activeStudy;
  $("study-report").replaceChildren();
  const title = document.createElement("p");
  title.textContent = `計算完了 / 数値判定: ${report.numerical_status}（最後の細分段階）。一般のモード追跡は未実施。`;
  if (report.study.kind === "sweep")
    title.textContent =
      "掃引の計算完了。独立したスペクトルを表示します。収束判定・モード追跡は未実施。";
  $("study-report").append(title);
  const table = document.createElement("table");
  let heading = document.createElement("tr");
  for (const label of [
    "条件値 [SI / 倍率]",
    "周波数順番号",
    "周波数 [MHz]",
    "R/Q acc [Ω]",
    "結果",
  ]) {
    const th = document.createElement("th");
    th.textContent = label;
    heading.append(th);
  }
  table.append(heading);
  report.points.forEach((point, i) =>
    point.modes.forEach((m, j) => {
      const row = document.createElement("tr");
      for (const v of [
        point.value,
        m.mode_index,
        m.frequency_hz / 1e6,
        m.r_over_q_accelerator_ohm,
      ]) {
        const td = document.createElement("td");
        td.textContent = Number(v).toPrecision(7);
        row.append(td);
      }
      const td = document.createElement("td");
      if (j === 0) {
        const button = document.createElement("button");
        button.textContent = "場を開く";
        button.onclick = async () => {
          try {
            const item = await api("study-point", { id, index: i + 1 });
            await refreshJobs();
            await openResult(item.id);
          } catch (e) {
            failure(e);
          }
        };
        td.append(button);
      }
      row.append(td);
      table.append(row);
    }),
  );
  $("study-report").append(table);
  for (const [i, c] of report.comparisons.entries()) {
    const details = document.createElement("details"),
      summary = document.createElement("summary");
    summary.textContent = `細分 ${i + 1} → ${i + 2}: ${c.status}`;
    details.append(summary);
    for (const m of c.modes) {
      const p = document.createElement("p");
      p.textContent = `番号 ${m.first_mode_index} → ${m.second_mode_index}: ${m.status} / 対応一致度 ${m.field_overlap.toFixed(6)} / 周波数 ${(m.relative_changes.frequency_hz * 100).toPrecision(4)}% / 軸場 ${m.axis_relative_l2 === null ? "未判定" : (m.axis_relative_l2 * 100).toPrecision(4) + "%"} / RF ${m.gates.rf ? "PASS" : "FAIL"}。表面場の精度は保証しません。`;
      details.append(p);
    }
    $("study-report").append(details);
  }
  const svg = $("study-chart");
  svg.replaceChildren();
  svg.hidden = false;
  const ns = "http://www.w3.org/2000/svg";
  const xs = report.points.map((p) => p.value),
    ys = report.points.flatMap((p) => p.modes.map((m) => m.frequency_hz / 1e6)),
    xmin = Math.min(...xs),
    xmax = Math.max(...xs),
    ymin = Math.min(...ys),
    ymax = Math.max(...ys),
    x = (v) => 65 + (570 * (v - xmin)) / (xmax - xmin || 1),
    y = (v) => 225 - (170 * (v - ymin)) / (ymax - ymin || 1);
  const add = (tag, attrs, text) => {
    const el = document.createElementNS(ns, tag);
    for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
    if (text) el.textContent = text;
    svg.append(el);
  };
  report.points.forEach((p) =>
    p.modes.forEach((m) =>
      add("circle", {
        cx: x(p.value),
        cy: y(m.frequency_hz / 1e6),
        r: 4,
        fill: "#1767a6",
      }),
    ),
  );
  add(
    "text",
    { x: 60, y: 20 },
    `独立スペクトル / 周波数 [MHz] ${ymin.toFixed(3)} – ${ymax.toFixed(3)}`,
  );
  add(
    "text",
    { x: 60, y: 263 },
    `${xmin} → ${xmax}  条件値 [SI / 倍率]（モード間を線で結びません）`,
  );
  $("study-csv").hidden = false;
}
bind("study-csv", () =>
  download(
    "study.csv",
    [
      "parameter_value,mode_index,frequency_hz,r_over_q_accelerator_ohm",
      ...activeStudy.points.flatMap((p) =>
        p.modes.map((m) =>
          [
            p.value,
            m.mode_index,
            m.frequency_hz,
            m.r_over_q_accelerator_ohm,
          ].join(","),
        ),
      ),
    ].join("\n"),
    "text/csv",
  ),
);
if (token) updateStudyParameters().catch(failure);

bind("probe-csv", async () =>
  download(
    "radial.csv",
    await api(
      "probe",
      {
        id: currentJob,
        mode: number("mode"),
        probe_z_m: number("probe-z") / 1000,
      },
      true,
    ),
    "text/csv",
  ),
);
const rfDetailNames = {
  stored_energy_j: "蓄積エネルギー U [J]",
  electric_energy_j: "電気エネルギー [J]",
  magnetic_energy_j: "磁気エネルギー [J]",
  energy_balance_relative: "電気・磁気エネルギー整合の相対差",
  relative_eigen_residual: "代数固有値残差（メッシュ誤差ではありません）",
  surface_resistance_ohm: "表面抵抗 [Ω]",
  wall_loss_w: "壁損失 [W]",
  geometry_factor_ohm: "幾何係数 G [Ω]",
  vacc_v: "加速電圧 Vacc [V]",
  voltage_real_v: "通過位相を含む電圧・実部 [V]",
  voltage_imag_v: "通過位相を含む電圧・虚部 [V]",
  beta: "粒子速度 β",
  active_length_m: "加速長 [m]",
  voltage_interval_start_m: "電圧積分開始 [m]",
  voltage_interval_end_m: "電圧積分終了 [m]",
  phase_origin_m: "位相原点 [m]",
  eacc_v_per_m: "加速電場 Eacc [V/m]",
  r_shunt_accelerator_ohm: "シャントインピーダンス acc [Ω]",
  r_shunt_circuit_ohm: "シャントインピーダンス circuit [Ω]",
  epk_surface_estimate_v_per_m: "最大表面電場（推定）[V/m]",
  bpk_surface_estimate_t: "最大表面磁束密度（推定）[T]",
  bpk_over_eacc_estimate_mt_per_mv_per_m: "Bpk/Eacc [mT/(MV/m)]",
  epk_discrete_lower_bound_v_per_m: "離散電場の連続最大・下界 [V/m]",
  epk_discrete_upper_bound_v_per_m: "離散電場の連続最大・上界 [V/m]",
  hpk_discrete_lower_bound_a_per_m: "離散磁場の連続最大・下界 [A/m]",
  hpk_discrete_upper_bound_a_per_m: "離散磁場の連続最大・上界 [A/m]",
  peak_status: "表面ピーク比の状態",
};
function renderRFDetails() {
  if (!currentResult) return;
  const q = currentResult.result.modes[Number($("mode").value) - 1],
    table = document.createElement("table");
  for (const [key, label] of Object.entries(rfDetailNames)) {
    const row = document.createElement("tr"),
      th = document.createElement("th"),
      td = document.createElement("td");
    th.textContent = label;
    td.textContent =
      q[key] === undefined
        ? "未評価"
        : q[key] === null
        ? "未定義"
        : typeof q[key] === "number"
          ? q[key].toPrecision(8)
          : String(q[key]);
    row.append(th, td);
    table.append(row);
  }
  $("rf-details").replaceChildren(table);
  if (currentResult.result.reflection || currentResult.result.reflection_source_case) {
    const note = document.createElement("p");
    note.textContent = "鏡映で構成した全空洞です。モード番号は対称条件で選ばれた部分スペクトルの順序で、全空洞の固有周波数順位ではありません。";
    $("rf-details").prepend(note);
  }
  const corners = currentResult.result.surface_corner_diagnostics;
  if (corners) {
    const note = document.createElement("p");
    const c = corners.counts;
    note.textContent = `元の解析曲線の接続点：再入角 ${c.reentrant_pec_corner}、凸角 ${c.convex_pec_corner}、軸接続 ${c.axis_join}、異種境界接続 ${c.mixed_boundary_join}。物理ピークの収束は未確認です。`;
    $("rf-details").prepend(note);
  }
}
$("mode").addEventListener("change", () => {
  renderRFDetails();
  $("field-image").hidden = true;
  $("save-plot").disabled = true;
  ++plotRequest;
  $("plot").disabled = false;
  $("result-state").textContent =
    "モードを変更しました。「場を表示」で描画を更新してください。";
});

let pillboxReference;
bind("pillbox-reference", async () => {
  const view = resultRequest;
  $("reference-result").textContent = "形状と実場を確認中…";
  $("save-reference").disabled = true;
  try {
    const response = await api("pillbox-reference", { id: currentJob });
    if (view !== resultRequest) return;
    pillboxReference = response;
    const table = document.createElement("table"),
      head = document.createElement("tr");
    for (const title of [
      "番号",
      "場から同定したモード",
      "周波数差 [%]",
      "軸場差 [%]",
      "RF判定",
      "総合",
    ]) {
      const th = document.createElement("th");
      th.textContent = title;
      head.append(th);
    }
    table.append(head);
    for (const m of pillboxReference.modes) {
      const tr = document.createElement("tr");
      for (const value of [
        m.mode_index,
        m.label ?? "未同定",
        (m.relative_errors.frequency_hz * 100).toPrecision(5),
        (m.axis_relative_l2 * 100).toPrecision(5),
        m.gates.rf ? "PASS" : "FAIL",
        m.status,
      ]) {
        const td = document.createElement("td");
        td.textContent = value;
        tr.append(td);
      }
      table.append(tr);
    }
    $("reference-result").replaceChildren(table);
    $("save-reference").disabled = false;
  } catch (e) {
    if (view !== resultRequest) return;
    $("reference-result").textContent =
      "解析比較は利用できません。一定半径の全PEC円筒が対象です。";
    throw e;
  }
});
bind("save-reference", () =>
  download(
    "analytical-comparison.json",
    JSON.stringify(pillboxReference, null, 2),
  ),
);

bind("replace-section", async () => {
  if (selectedSection === null)
    throw Error("編集する部分を「輪郭へ読込」で選択してください");
  const r = await api("normalize", {
    document: { schema_version: 2, geometry: geometry() },
  });
  sections[selectedSection].geometry = r.project.case.geometry;
  assemblyActive = false;
  renderSections();
  markDirty();
});
for (const id of ["probe-z", "mesh-view"])
  $(id).addEventListener("change", () => {
    ++plotRequest;
    $("field-image").hidden = true;
    $("save-plot").disabled = true;
    $("plot").disabled = false;
    $("result-state").textContent =
      "表示条件を変更しました。「場を表示」で更新してください。";
  });

bind("probe-metadata", async () =>
  download(
    "radial.csv.json",
    await api(
      "probe-metadata",
      {
        id: currentJob,
        mode: number("mode"),
        probe_z_m: number("probe-z") / 1000,
      },
      true,
    ),
  ),
);


// Construction is separate from the current project until explicit application.
let tangentGeneration = 0, tangentResult = null;
function clearTangent() {
  tangentGeneration++;
  tangentResult = null;
  $("tangent-candidate").replaceChildren(new Option("候補を選択してください", ""));
  $("tangent-table").tBodies[0].replaceChildren();
  for (const id of ["tangent-candidate", "tangent-build", "tangent-save", "tangent-apply", "tangent-diagnosis-save"]) $(id).disabled = true;
  $("tangent-offset-status").hidden = true;
  $("tangent-offset-status").textContent = "";
  $("tangent-status").textContent = "要求を変更しました。接線候補を調べ直してください。";
  $("tangent-diagnostics").textContent = "";
}
$("tangent-request").addEventListener("input", clearTangent);
function showTangent(response) {
  tangentResult = response;
  const c = response.construction, report = c.enumeration;
  const labels = {FORWARD:"順方向", OPPOSED:"逆向き（接続不可）", ZERO_LENGTH:"ゼロ長（接続不可）", EMPTY_ARC:"空の弧（接続不可）", EMPTY_LINE:"空の線分（接続不可）", OUTSIDE_SEGMENT:"線分外（延長未許可）", SWEEP_LIMIT:"円弧角の上限超過", UNVERIFIED:"未確認（接続不可）"};
  $("tangent-table").tBodies[0].replaceChildren();
  $("tangent-candidate").replaceChildren(new Option("候補を選択してください", ""));
  report.candidates.forEach((candidate, index) => {
    const row = document.createElement("tr");
    const positions = [0,1].map(i => {
      const p = candidate.contacts_zr_m[i];
      if (!p || p.length !== 2) return "未復元";
      const role = candidate.contact_roles ? ({line_start:"線分始点: ",line_end:"線分終点: ",conic_contact:"接点: "}[candidate.contact_roles[i]]) : "";
      return role + p.map(v=>(v*1000).toPrecision(7)).join(", ");
    });
    const length = candidate.fillet_arc_length_m ?? candidate.contact_distance_m;
    const values = [index, ...positions, Number.isFinite(length) ? (length*1000).toPrecision(7) : "未復元", labels[candidate.connection_direction]];
    for (const value of values) {const cell=document.createElement("td");cell.textContent=value;row.append(cell);}
    $("tangent-table").tBodies[0].append(row);
    const option = new Option(`${index}: ${labels[candidate.connection_direction]}`, String(index));
    option.disabled = candidate.connection_direction !== "FORWARD" || report.status !== "PASS";
    $("tangent-candidate").append(option);
  });
  $("tangent-candidate").disabled = report.status !== "PASS";
  if (c.candidate_index !== null) $("tangent-candidate").value = String(c.candidate_index);
  $("tangent-build").disabled = $("tangent-candidate").value === "" || report.status !== "PASS";
  $("tangent-save").disabled = false;
  $("tangent-apply").disabled = c.status !== "CASE_VALIDATED";
  $("tangent-status").textContent = c.status === "CASE_VALIDATED"
    ? "閉輪郭と計算条件の検査に合格しました。編集画面へ適用できます。FEM精度は別途検証が必要です。"
    : `${c.status === "UNVERIFIED" ? "未確認" : "候補表示"}: ${report.candidates.length}候補、${report.unresolved.length}件未確認。候補表示だけでは計算できません。`;
  if ([2,3,5,6].includes(c.schema_version)) {
    const selected = c.candidate_index === null ? null : report.candidates[c.candidate_index];
    $("tangent-status").textContent += selected?.trim_contact_error_bounds_m
      ? ` 接点誤差上界は最大${(Math.max(...selected.trim_contact_error_bounds_m,...(selected.fillet_contact_error_bounds_m ?? []))*1000).toExponential(3)} mmです。接線角度は数値検査です。`
      : ` 弧の所属と位置区間を検査する版${c.schema_version}の構築要求です。`;
  }
  if (c.schema_version === 4) {
    $("tangent-status").textContent += ` 指定半径${(report.radius_m*1000).toPrecision(7)} mmの線分フィレットです。長さは円弧長、接点・接線角度は数値検査です。`;
  }
  if ([5,6].includes(c.schema_version)) {
    $("tangent-status").textContent += ` 指定半径${(report.radius_m*1000).toPrecision(7)} mm、${report.turn_direction === 1 ? "反時計回り" : "時計回り"}の弧フィレットです。長さは円弧長です。`;
  }
  const diagnosis = response.offset_diagnosis?.diagnosis;
  $("tangent-diagnosis-save").disabled = !diagnosis;
  $("tangent-offset-status").hidden = !diagnosis;
  if (diagnosis) {
    const names = {DISJOINT:"共有する中心点なし", SINGLE_TANGENCY:"1点で接触", INFINITE_PARAMETER_PAIRS:"対応するパラメータ対が無限個", SHARED_PARAMETER_ENDPOINT:"共有端点あり", COINCIDENT_SUPPORTING_CIRCLES:"支持円が一致"};
    $("tangent-offset-status").textContent = diagnosis.status === "UNVERIFIED"
      ? "中心軌跡の特殊ケース診断: 対象外または未確認です。構築の可否は上の検査結果を参照してください。"
      : `中心軌跡の特殊ケース診断: ${names[diagnosis.classification] ?? diagnosis.classification}。${diagnosis.finite_domain_complete ? "指定範囲全体を分類済みです。" : "この事実を確認しました。指定範囲全体の分類は未完了です。"} 構築の可否は上の検査結果を参照してください。`;
  }
  $("tangent-diagnostics").textContent = JSON.stringify({status:c.status, scope:c.scope, enumeration:report, joins:c.joins, offset_diagnosis:diagnosis ?? null},null,2);
}
async function requestTangent(candidate = null) {
  const source = $("tangent-request").value;
  const generation = ++tangentGeneration;
  tangentResult = null;
  for (const id of ["tangent-build", "tangent-save", "tangent-apply", "tangent-diagnosis-save"]) $(id).disabled = true;
  $("tangent-offset-status").hidden = true;
  let response;
  try { response = await api("tangent", {document:source, candidate_index:candidate}); }
  catch (error) { if (generation === tangentGeneration) throw error; else return; }
  if (generation !== tangentGeneration || source !== $("tangent-request").value) return;
  showTangent(response);
}
bind("tangent-enumerate", () => requestTangent());
$("tangent-candidate").addEventListener("change", () => {
  tangentGeneration++;
  if (tangentResult) tangentResult = null;
  $("tangent-save").disabled = $("tangent-apply").disabled = true;
  $("tangent-diagnosis-save").disabled = true;
  $("tangent-offset-status").hidden = true;
  $("tangent-build").disabled = $("tangent-candidate").value === "";
  $("tangent-status").textContent = "候補を変更しました。選択した接線で閉輪郭を検査してください。";
});
bind("tangent-build", () => {
  if ($("tangent-candidate").value === "") throw Error("接線候補を明示的に選択してください");
  return requestTangent(Number($("tangent-candidate").value));
});
$("tangent-open").addEventListener("change", async event => {
  clearTangent();
  const generation = tangentGeneration;
  try {
    const file = event.target.files[0]; if (!file) return;
    const source = await file.text();
    if (generation !== tangentGeneration) return;
    const parsed = JSON.parse(source);
    if (Object.hasOwn(parsed, "request_sha256") || parsed.document_type === "construction_offset_diagnosis") {
      const response = await api("replay-tangent", {document:source});
      if (generation !== tangentGeneration) return;
      $("tangent-request").value = JSON.stringify(response.construction.request,null,2);
      showTangent(response);
    } else {
      $("tangent-request").value = source;
      await requestTangent().catch(failure);
    }
  } catch (error) { if (generation === tangentGeneration) failure(error); }
  finally { event.target.value = ""; }
});
bind("tangent-save", () => {
  if (!tangentResult) throw Error("構築要求を調べ直してください");
  download("tangent-construction.json", tangentResult.serialized);
});
bind("tangent-diagnosis-save", () => {
  if (!tangentResult?.diagnosis_serialized) throw Error("構築要求を調べ直してください");
  download("construction-offset-diagnosis.json", tangentResult.diagnosis_serialized);
});
bind("tangent-apply", () => {
  if (!tangentResult?.preview || tangentResult.construction.status !== "CASE_VALIDATED") throw Error("閉輪郭の検査が必要です");
  const p = tangentResult.preview;
  applyProject(p.project);
  drawOutline(p.outline_zr_m,p.outline_closed,p.geometry_approximation);
  markDirty();
  $("tangent-status").textContent = "検査済み形状と条件を編集画面へ適用しました。計算または入力保存へ進めます。";
});

// Saved-field mode tracking; the server owns validation and ID propagation.
let trackingResult = null, trackingBusy = false, trackingJobSignature = "";
function trackingJobs(jobs) {
  const completed = jobs.filter(j => j.status === "complete" && j.kind !== "study");
  const signature = JSON.stringify(completed.map(j => j.id));
  if (signature === trackingJobSignature) return;
  trackingJobSignature = signature;
  for (const id of ["tracking-previous", "tracking-current"]) {
    const select = $(id), previous = select.value;
    select.replaceChildren(new Option("結果を選択", ""));
    for (const j of completed) select.add(new Option(j.id, j.id));
    if (completed.some(j => j.id === previous)) select.value = previous;
  }
}
function trackingButtons() {
  const d = trackingResult?.document, history = d?.document_type === "mode_tracking_history";
  $("tracking-compare").disabled = trackingBusy || history;
  $("tracking-start").disabled = trackingBusy || !d || history;
  $("tracking-extend").disabled = trackingBusy || !history || !d.can_extend;
  $("tracking-save").disabled = trackingBusy || !d;
  $("tracking-reset").disabled = trackingBusy;
  $("tracking-open").disabled = trackingBusy;
  $("tracking-previous").disabled = trackingBusy || history;
  $("tracking-ids").disabled = trackingBusy || history;
  $("tracking-previous").closest("label").hidden = history;
  $("tracking-ids").closest("label").hidden = history;
  $("tracking-origin").hidden = !history;
  $("tracking-origin").textContent = history ? `履歴末尾の基準結果: ${d.current_run}` : "";
  $("tracking-pairs-label").hidden = $("tracking-mapping").value !== "paired_mesh";
  $("tracking-link-label").hidden = !$("tracking-retain").checked;
}
function trackingControls() {
  const controls = {mapping: $("tracking-mapping").value, sample_order: number("tracking-order"),
    minimum_overlap: number("tracking-overlap"), minimum_assignment_margin: number("tracking-margin"),
    relative_cluster_gap: number("tracking-gap"), minimum_relative_singular_value: number("tracking-rank")};
  if (controls.mapping === "paired_mesh") controls.vertex_pairs = JSON.parse($("tracking-pairs").value);
  if ($("tracking-retain").checked) Object.assign(controls, {cluster_transition_policy: "retain_subspace", minimum_cluster_link: number("tracking-link")});
  return controls;
}
function showTracking(response) {
  trackingResult = response;
  const d = response.document, history = d.document_type === "mode_tracking_history";
  const pair = history ? d.steps.at(-1) : d, r = pair.tracking, controls = pair.request.controls;
  $("tracking-mapping").value = controls.mapping;
  for (const [id,key] of [["order","sample_order"],["overlap","minimum_overlap"],["margin","minimum_assignment_margin"],["gap","relative_cluster_gap"],["rank","minimum_relative_singular_value"]])
    $(`tracking-${id}`).value = controls[key];
  $("tracking-retain").checked = controls.cluster_transition_policy === "retain_subspace";
  if (controls.minimum_cluster_link !== undefined) $("tracking-link").value = controls.minimum_cluster_link;
  if (controls.vertex_pairs) $("tracking-pairs").value = JSON.stringify(controls.vertex_pairs);

  $("tracking-status").textContent = `${d.status} — ${history ? `履歴 ${d.steps.length} 段階。` : "2時点の比較。"} ${d.status !== "PASS" ? "未確認の対応があります。" : r.individual_ids_complete ? "全個別IDの対応を確認しました。" : "部分空間の対応を確認しました。集合内の個別IDは未確定です。"}${history && !d.can_extend ? " この履歴からの継続はできません。" : ""}`;
  const body = $("tracking-matches").querySelector("tbody"); body.replaceChildren();
  for (const m of r.matches) {
    const row = document.createElement("tr");
    for (const value of [m.previous_ids.join(", "), m.kind === "SUBSPACE" ? "部分空間（個別ID未確定）" : "個別モード",
      m.current_indices.join(", "), m.current_frequencies_hz.map(f => (f / 1e6).toPrecision(9)).join(", "), m.minimum_principal_overlap.toPrecision(9)]) {
      const cell = document.createElement("td"); cell.textContent = value; row.append(cell);
    }
    body.append(row);
  }
  $("tracking-diagnostics").textContent = JSON.stringify({previous_run: pair.request.previous_run, current_run: pair.request.current_run,
    stop_reason: d.stop_reason ?? null, unmatched_previous: r.unmatched_previous, unmatched_current: r.unmatched_current,
    unresolved: r.unresolved, cluster_transitions: r.cluster_transitions ?? null, controls: pair.request.controls,
    scope: d.scope}, null, 2);
  trackingButtons();
}
async function runTracking(action, data) {
  if (trackingBusy) throw Error("追跡の検証中です。完了を待ってください。");
  trackingBusy = true; trackingButtons();
  try { showTracking(await api(action, data)); }
  finally { trackingBusy = false; trackingButtons(); }
}
bind("tracking-compare", async () => {
  await runTracking("compare-modes", {previous_id: $("tracking-previous").value, current_id: $("tracking-current").value,
    previous_ids: JSON.parse($("tracking-ids").value), controls: trackingControls()});
});
bind("tracking-start", async () => { await runTracking("start-mode-history", {document: trackingResult.serialized}); });
bind("tracking-extend", async () => { await runTracking("extend-mode-history", {document: trackingResult.serialized,
  current_id: $("tracking-current").value, controls: trackingControls()}); });
bind("tracking-reset", () => {
  trackingResult = null; $("tracking-status").textContent = "比較する結果とIDを指定してください。";
  $("tracking-matches").querySelector("tbody").replaceChildren(); $("tracking-diagnostics").textContent = ""; trackingButtons();
});
bind("tracking-save", () => { download(trackingResult.document.document_type === "mode_tracking_history" ? "mode-tracking-history.json" : "mode-tracking.json", trackingResult.serialized); });
$("tracking-open").addEventListener("change", async event => {
  const file = event.target.files[0]; if (!file) return;
  try { $("error").hidden = true; await runTracking("replay-mode-tracking", {document: await file.text()}); }
  catch (error) { failure(error); }
  finally { event.target.value = ""; }
});
$("tracking-mapping").addEventListener("change", trackingButtons);
$("tracking-retain").addEventListener("change", trackingButtons);
trackingButtons();
