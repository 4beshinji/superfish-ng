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
let explicitProjectMesh = null;
function isContour(kind) { return ["contour", "curved_contour"].includes(kind); }
function geometryLength(g) {
  if (g.type === "curved_contour") return Math.max(...g.curves.filter((c,i)=>g.edge_tags[i]==="axis").flatMap(c=>[c.start_zr_m[0],c.end_zr_m[0]]));
  return g.type === "contour" ? Math.max(...g.vertices_zr_m.map(p=>p[0])) : g.points_zr_m.at(-1)[0];
}
function updateCurvedControls() {
  const curved = $("geometry-order").value === "2";
  const history = $("curved-refinement-mode").value === "steps";
  $("quadrature-order").disabled = !curved;
  $("curved-refinement-mode").disabled = !curved;
  $("curved-refinement-levels").disabled = !curved || history;
  $("curved-history-controls").disabled = !curved || !history;
  $("curved-history-controls").hidden = !history;
  updateCurvedSelectionTarget();
}
$("geometry-order").addEventListener("change", updateCurvedControls);
$("curved-refinement-mode").addEventListener("change", updateCurvedControls);
let curvedHistoryRowId = 0;
let curvedHistoryUndo = null;
const curvedHistoryRows = () => [...$("curved-history").tBodies[0].rows];
function updateCurvedSelectionTarget() {
  $("curved-selection-stage").disabled = $("curved-selection-position").value === "end";
  curvedHistoryRows().forEach((row,i) => row.querySelector('.step-number').textContent = `${i+1}段目 `);
}
$("curved-selection-position").addEventListener("change", updateCurvedSelectionTarget);
function curvedHistoryDraft() {
  return {mode:$("curved-refinement-mode").value, levels:$("curved-refinement-levels").value,
    rows:curvedHistoryRows().map(row => ({id:row.dataset.historyId,
      kind:row.querySelector('.step-kind').value, cells:row.querySelector('.step-cells').value,
      angle:row.querySelector('.step-angle').value, previous:row.querySelector('.step-previous').textContent, splitPattern:structuredClone(row._splitPattern)}))};
}
function curvedSelectionTarget() {
  const mode = $("curved-selection-position").value;
  const rows = curvedHistoryRows();
  const count = $("curved-refinement-mode").value === "steps" ? rows.length : number("curved-refinement-levels");
  if (!Number.isSafeInteger(count) || count < 0) throw Error("細分段数は0以上の整数を指定してください");
  if ($("curved-refinement-mode").value === "levels" && count > Math.log(number("contour-triangles"))/Math.log(4))
    throw Error("一様細分の段数が要素数上限を超えます。段数を減らしてください");
  const index = mode === "end" ? count : number("curved-selection-stage")-1;
  if (!Number.isSafeInteger(index) || index < 0 || index > count || (mode === "replace" && index === count))
    throw Error("対象段階は現在の履歴内を指定してください。挿入は末尾の次の段階も指定できます");
  if (mode === "replace" && ($("curved-refinement-mode").value !== "steps" || rows[index].querySelector('.step-kind').value !== "marked"))
    throw Error("選び直す対象には、選択要素の細分段階を指定してください");
  return {mode,index};
}
function curvedSelectionInput() {
  const target = curvedSelectionTarget();
  // The suffix may be an unfinished draft. Only the prefix is sent as a valid Project.
  const project = collect(target.mode === "end" ? null : target.index);
  const signature = JSON.stringify({project, target, draft:curvedHistoryDraft()});
  return {target,project,signature};
}
function curvedSelectionMatches(signature) {
  try { return curvedSelectionInput().signature === signature; } catch { return false; }
}
function curvedRefinementRow(step = {kind: "uniform"}) {
  const row = $("curved-history").tBodies[0].insertRow();
  row.dataset.historyId = String(++curvedHistoryRowId);
  row.innerHTML = '<td><span class="step-number"></span><span class="step-split-note hint"></span><select class="step-kind" aria-label="細分方法"><option value="uniform">一様</option><option value="marked">選択要素</option></select></td><td><input class="step-cells" aria-label="細分する要素番号" /><span class="step-previous hint"></span></td><td><input class="step-angle" aria-label="最小頂点接線角" type="number" min="0" max="60" step="any" /></td><td><button type="button" class="step-release">固定を解除</button><button type="button" class="step-pick">図上で選び直す</button><button type="button" class="step-up" aria-label="この段階を上へ">↑</button><button type="button" class="step-down" aria-label="この段階を下へ">↓</button><button type="button" class="step-remove">削除</button></td>';
  const kind = row.querySelector('.step-kind'), cells = row.querySelector('.step-cells'), angle = row.querySelector('.step-angle');
  kind.value = step.kind;
  cells.value = (step.marked_cells || []).join(', ');
  angle.value = step.minimum_corner_angle_deg ?? 5;
  row._splitPattern=structuredClone(step.split_pattern ?? null);
  const update = () => {
    const fixed=!!row._splitPattern;
    kind.disabled=fixed;cells.disabled=kind.value==='uniform' || fixed;
    angle.disabled=row.querySelector('.step-pick').disabled=kind.value==='uniform';
    row.querySelector('.step-release').hidden=!fixed;
    row.querySelector('.step-split-note').textContent=fixed?'分割固定済み':'';
  };
  row.updateRefinementFields=update;
  row.querySelector('.step-release').onclick=()=>{
    row._splitPattern=null;update();
    const pending=invalidateCurvedSuffix(curvedHistoryRows().indexOf(row)+1);
    clearCurvedSelection();
    $("curved-history-edit-status").textContent=pending ? `${pending}段階の後続要素を再指定してください。` : 'この段階は形状に応じて分割を選び直します。';
    markDirty();
  };
  kind.addEventListener('change', update); update();
  row.querySelector('.step-pick').onclick = () => {
    $("curved-selection-position").value = "replace";
    $("curved-selection-stage").value = curvedHistoryRows().indexOf(row)+1;
    updateCurvedSelectionTarget();$("curved-selection-load").click();
  };
  row.querySelector('.step-up').onclick = () => { if (row.previousElementSibling) row.parentNode.insertBefore(row, row.previousElementSibling); updateCurvedSelectionTarget(); markDirty(); };
  row.querySelector('.step-down').onclick = () => { if (row.nextElementSibling) row.nextElementSibling.after(row); updateCurvedSelectionTarget(); markDirty(); };
  row.querySelector('.step-remove').onclick = () => { row.remove(); updateCurvedSelectionTarget(); markDirty(); };
  updateCurvedSelectionTarget();
  return row;
}
bind('curved-add-uniform', () => { curvedRefinementRow(); markDirty(); });
bind('curved-add-marked', () => { curvedRefinementRow({kind: 'marked'}); markDirty(); });
function invalidateCurvedSuffix(start) {
  let pending=0;
  for(const row of curvedHistoryRows().slice(start)) {
    if(row.querySelector('.step-kind').value!=='marked')continue;
    const input=row.querySelector('.step-cells');
    if(input.value.trim())row.querySelector('.step-previous').textContent=`変更前の番号（参照用）: ${input.value}。この段階のメッシュで再指定してください。`;
    input.value='';row._splitPattern=null;row.updateRefinementFields();pending++;
  }
  return pending;
}
bind('curved-freeze',async()=>{
  $('curved-freeze').disabled=true;
  try {
    const project=collect(),signature=JSON.stringify(project);
    const result=await api('freeze-curved-refinement',{document:project});
    if(JSON.stringify(collect())!==signature)throw Error('分割を固定する間に入力が変わりました。現在の入力でやり直してください');
    applyProject(result);markDirty();
    $('curved-history-edit-status').textContent='元メッシュと局所分割を固定しました。形状調整でも同じ親子関係を使います。';
  } finally {$('curved-freeze').disabled=false;}
});
function collectCurvedRefinementSteps(limit = null) {
  const rows = limit === null ? curvedHistoryRows() : curvedHistoryRows().slice(0,limit);
  if (!rows.length) throw Error('順序付き細分履歴を1段以上追加するか、一様細分の段数を選んでください');
  return rows.map((row, index) => {
    if (row.querySelector('.step-kind').value === 'uniform') return {kind: 'uniform'};
    const tokens = row.querySelector('.step-cells').value.split(',').map(s => s.trim());
    const cells = tokens.map(Number);
    if (tokens.some(s => !/^(0|[1-9][0-9]*)$/.test(s)) || cells.some(n => !Number.isSafeInteger(n)) || new Set(cells).size !== cells.length)
      throw Error(`細分履歴${index + 1}段目の要素番号は、重複のない0以上の整数をカンマで区切ってください`);
    const angle = Number(row.querySelector('.step-angle').value);
    if (!Number.isFinite(angle) || angle <= 0 || angle >= 60) throw Error(`細分履歴${index + 1}段目の最小頂点接線角は0より大きく60より小さい値を指定してください`);
    return {kind: 'marked', marked_cells: cells, minimum_corner_angle_deg: angle, ...(row._splitPattern ? {split_pattern:structuredClone(row._splitPattern)} : {})};
  });
}
let curvedSelection = null;
let curvedCanvasPicker = null;
function clearCurvedSelection() {
  curvedCanvasPicker?.dispose();curvedCanvasPicker=null;
  curvedSelection=null;$("curved-selection-panel").hidden=true;
  $("curved-selection-mesh").replaceChildren();
  $("curved-selection-canvas").width=1;
  $("curved-selection-append").disabled=true;
}
function selectionStatus() {
  const ids = [...curvedSelection.cells].sort((a,b)=>a-b);
  $("curved-selection-status").textContent = `選択 ${ids.length} 要素: ${ids.join(", ")}`;
  $("curved-selection-append").disabled = !ids.length;
}
bind("curved-selection-zoom-in",()=>curvedCanvasPicker?.zoomAt(1.6));
bind("curved-selection-zoom-out",()=>curvedCanvasPicker?.zoomAt(1/1.6));
bind("curved-selection-fit",()=>curvedCanvasPicker?.fit());
bind("curved-selection-focus",()=>curvedCanvasPicker?.focusCell(number("curved-selection-cell")));
bind("curved-selection-load", async () => {
  $("curved-selection-load").disabled = true;
  try {
    const {project, signature, target} = curvedSelectionInput();
    const mesh = await api("curved-selection-mesh", {document:project});
    if (!curvedSelectionMatches(signature)) throw Error("メッシュ作成中に入力が変わりました。再表示してください");
    clearCurvedSelection();
    curvedSelection = {signature, target, cells:new Set()};
    $("curved-selection-append").textContent = target.mode === "end" ? "選択要素の細分を履歴末尾へ追加" :
      target.mode === "insert" ? `${target.index+1}段目の直前へ挿入` : `${target.index+1}段目の選択要素を置き換える`;
    if (target.mode === "replace") $("curved-selection-angle").value = curvedHistoryRows()[target.index].querySelector('.step-angle').value;
    selectionStatus();
    const svg = $("curved-selection-mesh"), ns = "http://www.w3.org/2000/svg";
    const large=mesh.cell_nodes.length>5000;
    svg.toggleAttribute("hidden",large);$("curved-selection-large").hidden=!large;
    $("curved-selection-panel").hidden=false;
    if(large) {
      const controls=$("curved-selection-large").querySelectorAll('button,input');
      for(const control of controls)control.disabled=true;
      const picker=new CurvedMeshCanvas($("curved-selection-canvas"),mesh,curvedSelection.cells,selectionStatus,index=>{
        $("curved-selection-cell").value=index;
        $("curved-selection-canvas").setAttribute("aria-label",`要素 ${index}、${curvedSelection.cells.has(index)?"選択済み":"未選択"}。EnterまたはSpaceで選択を切り替えます`);
      });
      curvedCanvasPicker=picker;
      try {await picker.build();} catch(error) {clearCurvedSelection();throw error;}
      if(picker.disposed)return;
      if(!curvedSelectionMatches(signature)) {
        clearCurvedSelection();throw Error("メッシュ作成中に入力が変わりました。再表示してください");
      }
      for(const control of controls)control.disabled=false;
      selectionStatus();return;
    }
    svg.replaceChildren();
    const radii=mesh.points_rz_m.map(p=>p[0]), zs=mesh.points_rz_m.map(p=>p[1]);
    const z0=Math.min(...zs), r0=Math.min(...radii);
    const scale=Math.min(760/(Math.max(...zs)-z0),360/(Math.max(...radii)-r0));
    const point=p=>[20+(p[1]-z0)*scale,380-(p[0]-r0)*scale];
    mesh.cell_nodes.forEach((nodes,index) => {
      const p=nodes.map(i=>point(mesh.points_rz_m[i]));
      let d=`M ${p[0].join(" ")}`;
      for (const [a,b,m] of [[0,1,3],[1,2,4],[2,0,5]]) {
        const control=p[m].map((v,k)=>2*v-(p[a][k]+p[b][k])/2);
        d+=` Q ${control.join(" ")} ${p[b].join(" ")}`;
      }
      const path=window.document.createElementNS(ns,"path");
      for (const [name,value] of Object.entries({d:d+" Z",fill:"#d7e9f8",stroke:"#35647c","stroke-width":.6,tabindex:0,role:"button","aria-label":`要素 ${index}`,"aria-pressed":"false","data-cell":index})) path.setAttribute(name,value);
      const toggle=()=>{
        if(curvedSelection.cells.has(index))curvedSelection.cells.delete(index);else curvedSelection.cells.add(index);
        const selected=curvedSelection.cells.has(index);path.setAttribute("fill",selected?"#efb44c":"#d7e9f8");path.setAttribute("aria-pressed",String(selected));selectionStatus();
      };
      path.onclick=toggle;path.onkeydown=event=>{if(event.key==="Enter"||event.key===" "){event.preventDefault();toggle();}};
      svg.append(path);
    });
    $("curved-selection-panel").hidden=false;selectionStatus();
  } finally { $("curved-selection-load").disabled=false; }
});
bind("curved-selection-append", () => {
  if(!curvedSelection || !curvedSelectionMatches(curvedSelection.signature))
    throw Error("入力や履歴、対象段階が変わりました。古い要素番号は反映できません。メッシュを再表示してください");
  const ids=[...curvedSelection.cells].sort((a,b)=>a-b), angle=number("curved-selection-angle");
  if(!ids.length || angle<=0 || angle>=60)throw Error("要素を選び、最小頂点接線角を0より大きく60より小さく指定してください");
  const {mode,index} = curvedSelection.target;
  const undo = {draft:curvedHistoryDraft(), base:JSON.stringify(collect(0))};
  if($("curved-refinement-mode").value==="levels") {
    $("curved-history").tBodies[0].replaceChildren();
    for(let i=0;i<number("curved-refinement-levels");i++)curvedRefinementRow();
    $("curved-refinement-mode").value="steps";
  }
  let changed = true;
  if (mode === "replace") {
    const row=curvedHistoryRows()[index];
    changed = !!row._splitPattern || row.querySelector('.step-cells').value !== ids.join(', ') || Number(row.querySelector('.step-angle').value) !== angle;
    row._splitPattern=null;row.updateRefinementFields();
    row.querySelector('.step-cells').value=ids.join(', ');
    row.querySelector('.step-angle').value=angle;
    row.querySelector('.step-previous').textContent='';
  } else {
    const before=curvedHistoryRows()[index];
    const row=curvedRefinementRow({kind:"marked",marked_cells:ids,minimum_corner_angle_deg:angle});
    if(before)before.before(row);
  }
  const pending=changed ? invalidateCurvedSuffix(index+1) : 0;
  curvedHistoryUndo=undo;$("curved-history-undo").disabled=false;
  $("curved-history-edit-status").textContent=pending ? `${pending}段階の選択要素を再指定してください。保存・計算は再指定後に行えます。` : "図上選択を履歴に反映しました。";
  clearCurvedSelection();
  $("curved-selection-position").value="end";
  updateCurvedControls();markDirty();
});
bind("curved-history-undo", () => {
  if(!curvedHistoryUndo)return;
  if(JSON.stringify(collect(0)) !== curvedHistoryUndo.base)
    throw Error("形状や計算設定が変わったため、旧要素番号の履歴へ戻せません。図上変更時の入力に戻してください");
  const {draft}=curvedHistoryUndo;
  clearCurvedSelection();
  $("curved-refinement-mode").value=draft.mode;$("curved-refinement-levels").value=draft.levels;
  $("curved-history").tBodies[0].replaceChildren();
  for(const step of draft.rows) {
    const row=curvedRefinementRow({kind:step.kind,split_pattern:step.splitPattern});
    row.querySelector('.step-cells').value=step.cells;row.querySelector('.step-angle').value=step.angle;
    row.querySelector('.step-previous').textContent=step.previous;
  }
  curvedHistoryUndo=null;$("curved-history-undo").disabled=true;
  $("curved-history-edit-status").textContent="直前の図上変更前の履歴に戻しました。";
  $("curved-selection-position").value="end";updateCurvedControls();markDirty();
});

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
    if($("curve-fixed-segments").value.trim())g.segments_per_curve=JSON.parse($("curve-fixed-segments").value);
    else delete g.segments_per_curve;
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
function collect(curvedPrefix = null) {
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
    if (curvedPrefix === 0) p.case.mesh.curved_refinement_levels = 0;
    else if ($("curved-refinement-mode").value === "steps") p.case.mesh.curved_refinement_steps = collectCurvedRefinementSteps(curvedPrefix);
    else p.case.mesh.curved_refinement_levels = curvedPrefix ?? number("curved-refinement-levels");
    p.case.solver.quadrature_order = number("quadrature-order");
  } else if ($("curved-refinement-mode").value === "steps") {
    throw Error('順序付き細分履歴には二次曲線要素が必要です。履歴を外す場合は細分の指定方法を切り替えてください');
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
  if(explicitProjectMesh!==null) {p.project_version=2;p.mesh_data=structuredClone(explicitProjectMesh);}
  return p;
}
function setGeometry(g) {
  geometryOriginal = structuredClone(g);
  geometryDirty = false;
  if (isContour(g.type)) {
    $("geometry-type").value = g.type;
    $("curve-chord").value = (g.chord_tolerance_m ?? 0.001) * 1000;
    $("curve-segments").value = g.chord_max_segments ?? 20000;
    $("curve-fixed-segments").value = g.segments_per_curve ? JSON.stringify(g.segments_per_curve) : "";
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
  curvedHistoryUndo=null;$("curved-history-undo").disabled=true;
  $("curved-history-edit-status").textContent="";$("curved-selection-position").value="end";
  explicitProjectMesh=p.mesh_data ? structuredClone(p.mesh_data) : null;
  $("explicit-project-mesh").textContent=explicitProjectMesh ? `明示元メッシュを使用: ${explicitProjectMesh.points.length}頂点 / ${explicitProjectMesh.triangles.length}三角形。通常のメッシュ生成設定では置き換えません。` : "メッシュは形状と生成設定から作成します。";
  clearCurvedSelection();
  const c = p.case;
  $("geometry-order").value = c.mesh.geometry_order ?? 1;
  $("curved-refinement-levels").value = c.mesh.curved_refinement_levels ?? 0;
  $("curved-refinement-mode").value = c.mesh.curved_refinement_steps?.length ? "steps" : "levels";
  $("curved-history").tBodies[0].replaceChildren();
  for (const step of c.mesh.curved_refinement_steps || []) curvedRefinementRow(step);
  $("quadrature-order").value = c.solver.quadrature_order ?? 8;
  contourMeshOriginal = c.mesh.contour_mesh ? structuredClone(c.mesh.contour_mesh) : null;
  $("contour-edge").value = contourMeshOriginal ? contourMeshOriginal.max_edge_m * 1000 : "";
  $("contour-angle").value = contourMeshOriginal?.min_angle_deg ?? 10;
  $("contour-triangles").value = contourMeshOriginal?.max_triangles ?? 250000;
  $("contour-rounds").value = contourMeshOriginal?.max_rounds ?? 12;
  explicitModel = c.model ? structuredClone(c.model) : null;
  $("polarization").value = explicitModel?.polarization || "tm";
  $("te-model-note").hidden = $("polarization").value !== "te";
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
async function replaceMesh(document) {
  const r=await api("replace-mesh",{document:collect(),mesh_document:document});
  applyProject(r.project);
  markDirty();
  drawOutline(r.outline_zr_m,r.outline_closed,r.geometry_approximation);
  $("error").hidden=true;
}
$("mesh-open").onchange=async event=>{
  try {if(event.target.files.length)await replaceMesh(await event.target.files[0].text());}
  catch(error){failure(error);}
  finally {event.target.value="";}
};
bind("mesh-detach",()=>replaceMesh(null));
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
    title.textContent = (statusNames[j.status] || j.status) + (["tracked_study","adaptive_study"].includes(j.kind) ? ` / ${j.kind === "adaptive_study" ? "適応" : "追跡"}Study${j.tracking_status ? " " + j.tracking_status : ""}` : "");
    if (j.kind === "adaptive_refinement") title.textContent += ` / 適応細分${j.refinement_status ? " " + j.refinement_status : ""}`;
    if (j.kind === "rf_optimization") title.textContent += ` / RF探索${j.optimization_status ? " " + j.optimization_status : ""}`;
    if (j.kind === "tune") title.textContent += ` / 周波数調整${j.tuning_status ? " " + j.tuning_status : ""}`;
    if (j.kind === "static_field_solve") title.textContent += " / 静電場・静磁場";
    if (j.kind === "static_field_study") title.textContent += ` / 静的Study${j.all_points_successful === false ? "（非線形失敗を含む）" : ""}`;
    if (j.kind === "magnetic_report_import") title.textContent += " / 磁気後処理報告";
    if (["hphi_solve","hphi_study","hphi_convergence","hphi_tracking","hphi_tracking_history"].includes(j.kind)) title.textContent += " / Hφ RF";
    if (["planar_solve","planar_study","planar_convergence","planar_tracking","planar_tracking_history"].includes(j.kind)) title.textContent += " / 平面RF";
    row.append(title);
    const desc = document.createElement("small");
    const stage =
      {
        "tracked adaptive FEM refinement and RF confirmation": "メッシュを細分・対象モードのRF量を確認中",
        "constrained RF coordinate search and final three-level refinement": "RF制約付き探索と最終細分を実行中",
        "tracked FEM frequency tuning and final mesh refinement": "追跡しながら周波数を調整・細分検査中",
        "adaptive FEM solves and saved-field tracking": "中点を追加して計算・追跡中",
        "sequential FEM solves and saved-field tracking": "各点を計算・追跡中",
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
    action.disabled = !["running", "queued", "complete"].includes(j.status) && !(j.kind === "static_field_solve" && j.outcome_saved === true);
    action.onclick = async () => {
      try {
        if (["running", "queued"].includes(j.status)) {
          await api("cancel", { id: j.id });
          await refreshJobs();
        } else if (["tracked_study","adaptive_study"].includes(j.kind)) await openTrackedExecution(j.id,j.kind === "adaptive_study");
        else if (j.kind === "adaptive_refinement") await openRefinement(j.id);
        else if (j.kind === "rf_optimization") await openRFOptimization(j.id);
        else if (j.kind === "tune") await openTuning(j.id);
        else if (j.kind === "study") await openStudy(j.id);
        else if (j.kind === "static_field_study") location.href = `/static-study.html?job=${encodeURIComponent(j.id)}`;
        else if (j.kind === "static_field_solve") location.href = `/static.html?job=${encodeURIComponent(j.id)}`;
        else if (j.kind === "magnetic_report_import") location.href = `/magnetic.html?job=${encodeURIComponent(j.id)}`;
        else if (j.kind === "hphi_tracking_history") location.href = `/hphi.html?history=${encodeURIComponent(j.id)}`;
        else if (j.kind === "hphi_tracking") location.href = `/hphi.html?tracking=${encodeURIComponent(j.id)}`;
        else if (j.kind === "hphi_convergence") location.href = `/hphi.html?convergence=${encodeURIComponent(j.id)}`;
        else if (j.kind === "hphi_study") location.href = `/hphi.html?study=${encodeURIComponent(j.id)}`;
        else if (j.kind === "hphi_solve") location.href = `/hphi.html?job=${encodeURIComponent(j.id)}`;
        else if (["planar_solve","planar_study","planar_convergence","planar_tracking","planar_tracking_history"].includes(j.kind)) location.href = `/planar.html?job=${encodeURIComponent(j.id)}`;
        else await openResult(j.id);
      } catch (e) {
        failure(e);
      }
    };
    row.append(action);
    if(j.kind==='rf_optimization' && ['complete','cancelled','interrupted','failed'].includes(j.status)) {
      const checkpoints=document.createElement('button');checkpoints.textContent='RF探索の途中保存を選ぶ';checkpoints.dataset.rfOptimizationCheckpoints=j.id;
      checkpoints.onclick=async()=>{try{await openRFOptimizationCheckpoints(j.id);}catch(e){failure(e);}};row.append(checkpoints);
    }
    if(j.kind==="tune" && ["complete","cancelled","interrupted","failed"].includes(j.status)) {
      const checkpoints=document.createElement("button");checkpoints.textContent="途中保存を選ぶ";
      checkpoints.dataset.tuneCheckpoints=j.id;
      checkpoints.onclick=async()=>{try{await openTuningCheckpoints(j.id);}catch(e){failure(e);}};
      row.append(checkpoints);
    }
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
async function openResult(id, modeIndex=null) {
  resetRFPeaks();
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
  if (r.result.reflection) $("result-state").textContent += " 鏡映された部分スペクトルです。番号は全空洞の周波数順位ではありません。";
  $("mode").replaceChildren();
  for (const q of r.result.modes) {
    const opt = document.createElement("option");
    opt.value = q.mode_index;
    opt.textContent = `${q.mode_index} — ${(q.frequency_hz / 1e6).toFixed(6)} MHz`;
    $("mode").append(opt);
  }
  if (modeIndex!==null) {
    if (![...$("mode").options].some(o=>Number(o.value)===modeIndex)) throw Error("指定された追跡モードの順位が保存結果にありません");
    $("mode").value=modeIndex;
  }
  $("probe-z").value = geometryLength(r.result.case.geometry) * 250;
  $("conventions").replaceChildren();
  for (const [key, value] of Object.entries(r.result.conventions)) {
    const p = document.createElement("p");
    p.textContent = `${key}: ${value}`;
    $("conventions").append(p);
  }
  const teResult = r.result.physics === "axisymmetric_m0_te";
  for (const id of ['pillbox-reference','analyze-band']) {
    $(id).disabled = teResult;
    $(id).title = teResult ? 'この評価はTM専用です。TEの場・プローブは通常表示から利用できます。' : '';
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
        q[key] === undefined ? "未評価" : q[key] === null ? (q.accelerating_quantities_status?.startsWith("NOT_APPLICABLE") ? "N/A（TEの軸方向電場はゼロ）" : "未定義") : Number(q[key]).toPrecision(7);
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
    if (currentResult.result.reflection) $("result-state").textContent += " 鏡映された部分スペクトルです。番号は全空洞の周波数順位ではありません。";
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
  $("study-affine").hidden=kind!=="curved_affine_sweep";
  $("study-harmonic").hidden=kind!=="curved_harmonic_sweep";
  $("study-parameter-label").hidden=["curved_affine_sweep","curved_harmonic_sweep"].includes(kind);
  if (kind === "curved_affine_sweep") {
    add("affine_parameter","宣言変換の変数");
    $("study-hint").textContent="TMの二次曲線Projectで使用します。元メッシュと参照細分の親子関係を保ち、各点で形状・品質・予算を再検査します。独立スペクトルの掃引であり、固定形状の収束判定ではありません。追跡時は各区間のaffine_remesh閾値を使用し、写像は宣言から導出します。";
  } else if (kind === "curved_harmonic_sweep") {
    add("harmonic_parameter","曲線寸法の変数");
    $("study-hint").textContent="閉PEC・軸のTM二次曲線で、元メッシュと固定分割を保つ形状掃引を作ります。全指定点の幾何と品質を事前検査します。独立スペクトルであり、固定領域の収束比較ではありません。追跡には各実比較点から構成した曲線比較メッシュを使います。";
  } else if (kind === "mesh_convergence") {
    add("mesh_scale", "基準メッシュに対する細分倍率");
    $("study-hint").textContent =
      "nr/nzを倍率倍し、指定された最大辺長を倍率で割ります。元曲線と弦誤差は固定ですが、二次境界は変わることがあります。周波数・RF・軸場を別々に判定します。";
  } else if (kind === "fixed_geometry_convergence") {
    const history = !!p.case.mesh.curved_refinement_steps?.length;
    const straight=!!p.mesh_data && (p.case.mesh.geometry_order ?? 1)===1;
    add(history || straight ? "additional_uniform_refinements" : "/case/mesh/curved_refinement_levels",
        straight ? "元メッシュからの一様細分段数" : history ? "保存履歴の後に追加する一様細分段数" : "二次形状を保つ細分段数");
    $("study-hint").textContent = straight
      ? "明示した直線メッシュを一様に分割し、多角形境界とタグを保持します。0は元メッシュ、1は全要素を4分割します。P1/P2場に対応します。"
      : history
      ? "現在の順序付き履歴を保持し、その末尾へ一様細分を追加します。0は現在の履歴のまま、1はそこから全要素を4分割します。初期メッシュと二次形状は固定です。"
      : "二次曲線要素で使用します。元メッシュと二次形状を固定し、0, 1, 2などの段数を比較します。1段で要素数は4倍になります。";
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
function curvedStudySignature() {
  return JSON.stringify({project:collect(),kind:$("study-kind").value,values:$("study-values").value,
    name:$("study-affine-parameter").value,unit:$("study-affine-unit").value,
    coefficients:$("study-affine-coefficients").value,rf:$("study-affine-rf").value,
    harmonicName:$("study-harmonic-parameter").value,harmonicUnit:$("study-harmonic-unit").value,
    harmonicRf:$("study-harmonic-rf").value,harmonicAngle:$("study-harmonic-angle").value,
    harmonicCoefficients:$("study-harmonic-coefficients").value});
}
async function studyDefinition() {
  const kind=$("study-kind").value, affine=kind==="curved_affine_sweep", harmonic=kind==="curved_harmonic_sweep";
  const signature=affine || harmonic ? curvedStudySignature() : null;
  const selected = $("study-parameter").value;
  const project = await updateStudyParameters(selected);
  if(kind!==$("study-kind").value || ((affine || harmonic) && signature!==curvedStudySignature()))throw Error("Studyの確認中に入力が変わりました。現在の入力でやり直してください。");
  if (!$("study-parameter").value)
    throw Error("変更する項目を選択してください");
  const values = $("study-values")
    .value.split(/[\s,]+/)
    .filter(Boolean)
    .map(Number);
  if (values.length < 2 || values.some((v) => !Number.isFinite(v)))
    throw Error("2個以上の有限な数値を入力してください");
  if(affine) {
    const result=await api('normalize-study',{document:JSON.stringify({study_version:2,project,kind,
      parameter:$("study-affine-parameter").value,parameter_unit:$("study-affine-unit").value,values,
      affine_coefficients:JSON.parse($("study-affine-coefficients").value),rf_coordinates:$("study-affine-rf").value})});
    if(signature!==curvedStudySignature())throw Error("Studyの確認中に入力が変わりました。現在の入力でやり直してください。");
    return result;
  }
  if(harmonic) {
    const base={study_version:3,project,kind,parameter:$("study-harmonic-parameter").value,
      parameter_unit:$("study-harmonic-unit").value,values,rf_coordinates:$("study-harmonic-rf").value,
      minimum_corner_angle_deg:number("study-harmonic-angle")};
    // Preserve the entered object text so the strict server reader can reject
    // duplicate law paths instead of silently losing them in JSON.parse.
    const document=JSON.stringify(base).slice(0,-1)+',"geometry_coefficients":'+$("study-harmonic-coefficients").value+'}';
    const result=await api('normalize-study',{document});
    if(signature!==curvedStudySignature())throw Error("Studyの確認中に入力が変わりました。現在の入力でやり直してください。");
    return result;
  }
  const parameter = $("study-parameter").value;
  return {
    study_version: 1,
    project,
    kind: $("study-kind").value,
    parameter,
    values: values.map((v) => v * studyParameterUnits.get(parameter)),
  };
}
bind("study-harmonic-template",async()=>{
  const signature=curvedStudySignature(),project=await preview();
  if(signature!==curvedStudySignature())throw Error("Studyの確認中に入力が変わりました。現在の入力でやり直してください。");
  if(!project.case.geometry.curves)throw Error("native曲線のProjectを先に開いてください。");
  const laws={},arrays=["start_zr_m","end_zr_m","center_zr_m","semiaxes_m"],scalars=["rotation_rad","start_rad","sweep_rad","start_parameter","end_parameter"];
  project.case.geometry.curves.forEach((curve,i)=>{
    for(const key of arrays)if(Array.isArray(curve[key]))curve[key].forEach((value,j)=>laws[`/curves/${i}/${key}/${j}`]=[value]);
    for(const key of scalars)if(typeof curve[key]==="number")laws[`/curves/${i}/${key}`]=[curve[key]];
  });
  $("study-harmonic-coefficients").value=JSON.stringify(laws,null,2);
});
bind("study-parameters", () => updateStudyParameters());
$("study-kind").onchange = () => {
  if ($("study-kind").value === "curved_affine_sweep")
    $("study-values").value = "1, 1.1, 1.2";
  else if ($("study-kind").value === "curved_harmonic_sweep")
    $("study-values").value = "0, 0.5, 1";
  else if ($("study-kind").value === "mesh_convergence")
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
    if(data.kind==='curved_affine_sweep') {
      $("study-affine-parameter").value=data.parameter;$("study-affine-unit").value=data.parameter_unit;
      $("study-affine-rf").value=data.rf_coordinates;$("study-affine-coefficients").value=JSON.stringify(data.affine_coefficients,null,2);
    }
    if(data.kind==='curved_harmonic_sweep') {
      $("study-harmonic-parameter").value=data.parameter;$("study-harmonic-unit").value=data.parameter_unit;
      $("study-harmonic-rf").value=data.rf_coordinates;$("study-harmonic-angle").value=data.minimum_corner_angle_deg;
      $("study-harmonic-coefficients").value=JSON.stringify(data.geometry_coefficients,null,2);
    }
    await updateStudyParameters(data.parameter);
    $("study-values").value = data.values
      .map((v) => ['curved_affine_sweep','curved_harmonic_sweep'].includes(data.kind) ? v : v / studyParameterUnits.get(data.parameter))
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
  if (["sweep","curved_affine_sweep","curved_harmonic_sweep"].includes(report.study.kind))
    title.textContent =
      "掃引の計算完了。独立したスペクトルを表示します。収束判定・モード追跡は未実施。";
  const reflectedTE = report.physics === "axisymmetric_m0_te" && report.study.project.reflect_full;
  if (reflectedTE) {
    title.textContent += " 鏡映された部分スペクトルです。番号は全空洞の周波数順位ではありません。";
    if (report.comparisons.length) title.textContent += " 細分比較は再構成・再検証した元半領域で行います。";
  }
  $("study-report").append(title);
  const table = document.createElement("table");
  let heading = document.createElement("tr");
  for (const label of [
    "条件値 [SI / 倍率]",
    reflectedTE ? "部分スペクトル内の番号" : "周波数順番号",
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
        td.textContent = v === null ? (m.accelerating_quantities_status?.startsWith("NOT_APPLICABLE") ? "N/A（TEの軸方向電場はゼロ）" : "未定義") : Number(v).toPrecision(7);
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
      if (c.physics === "axisymmetric_m0_te") {
        p.textContent = `番号 ${m.first_mode_index} → ${m.second_mode_index}: ${m.status} / 対応一致度 ${m.field_overlap.toFixed(6)} / 周波数 ${(m.relative_changes.frequency_hz * 100).toPrecision(4)}% / 電場 ${(m.electric_relative_l2 * 100).toPrecision(4)}% / 磁場 ${(m.magnetic_relative_l2 * 100).toPrecision(4)}% / RF ${m.gates.rf ? "PASS" : "FAIL"} / 積分次数照合 ${m.integration_stable ? "PASS" : "UNVERIFIED"}。軸加速量はN/A。体積場の細分差は物理誤差上界ではなく、表面ピーク精度は未評価です。`;
      }
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
  resetRFPeaks(true);
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
        ? (q.accelerating_quantities_status?.startsWith("NOT_APPLICABLE") ? "N/A（TEの軸方向電場はゼロ）" : "未定義")
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
  if ([2,3,5,6,7,8,9,10].includes(c.schema_version)) {
    const selected = c.candidate_index === null ? null : report.candidates[c.candidate_index];
    $("tangent-status").textContent += selected?.trim_contact_error_bounds_m
      ? ` 接点誤差上界は最大${(Math.max(...selected.trim_contact_error_bounds_m,...(selected.fillet_contact_error_bounds_m ?? []))*1000).toExponential(3)} mmです。接線角度は数値検査です。`
      : ` 弧の所属と位置区間を検査する版${c.schema_version}の構築要求です。`;
  }
  if (c.schema_version === 4) {
    $("tangent-status").textContent += ` 指定半径${(report.radius_m*1000).toPrecision(7)} mmの線分フィレットです。長さは円弧長、接点・接線角度は数値検査です。`;
  }
  if ([5,6,7,8,9,10].includes(c.schema_version)) {
    $("tangent-status").textContent += ` 指定半径${(report.radius_m*1000).toPrecision(7)} mm、${report.turn_direction === 1 ? "反時計回り" : "時計回り"}の弧フィレットです。長さは円弧長です。`;
  }
  const diagnosis = response.offset_diagnosis?.diagnosis;
  $("tangent-diagnosis-save").disabled = !diagnosis;
  $("tangent-offset-status").hidden = !diagnosis;
  if (diagnosis) {
    const names = {DISJOINT:"共有する中心点なし", SINGLE_TANGENCY:"1点で接触", FINITE_CENTERS:`共有する中心点は${diagnosis.finite_center_count}個`, TANGENCY_WITNESSES:`接触のある中心点を${diagnosis.evidence.tangency_witness_center_count}個確認`, INFINITE_PARAMETER_PAIRS:"対応するパラメータ対が無限個", SHARED_PARAMETER_ENDPOINT:"共有端点あり", COINCIDENT_SUPPORTING_CIRCLES:"支持円が一致"};
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


// Surface assessment retains the exact server document and its source history.
function surfaceHistory() {
  const d=trackingResult?.document;
  return d?.document_type === "study_mode_tracking" ? d.history : d?.document_type === "mode_tracking_history" ? d : null;
}
function surfaceButtons() {
  $("surface-assess").disabled=surfaceBusy || trackingBusy || (surfaceHistory()?.steps?.length ?? 0)<2;
  for (const id of ["surface-save","surface-replay"]) $(id).disabled=surfaceBusy || !surfaceResult;
  $("surface-open").disabled=surfaceBusy;
  $("surface-mode-id").disabled=surfaceBusy;
  $("surface-progress").textContent=surfaceBusy ? "保存場・履歴と表面評価を検証しています…" : "";
}
function showSurfaceAssessment(response) {
  surfaceResult=response;
  const d=response.document;
  $("surface-mode-id").value=d.mode_id;
  const statuses={TARGETS_MET:"基準達成（細分差）",NOT_CONVERGED:"未収束",UNVERIFIED:"未確認",SINGULAR_GEOMETRY:"特異形状：有限ピークは未認定",UNVERIFIED_GEOMETRY:"形状未確認：ピークは未認定"};
  $("surface-status").textContent=`${statuses[d.status] ?? d.status}。対象ID: ${d.mode_id}。${d.rows.length}水準、直近2区間を判定。`;
  const corners=d.geometry_diagnostic.joins.counts;
  $("surface-geometry-status").textContent=`再入角 ${corners.reentrant_pec_corner}、凸角 ${corners.convex_pec_corner}。形状診断: ${d.geometry_diagnostic.status === "SMOOTH_WITHIN_TOLERANCE" ? "接線・軸端を許容差内で確認" : "未認定の接続があります"}。`;
  const numberText=x => typeof x === "number" && Number.isFinite(x) ? x.toPrecision(8) : "未確認";
  const interval=(v,scale=1) => v === null ? "未確認" : v[0]===v[1] ? numberText(v[0]*scale) : `${numberText(v[0]*scale)} ～ ${numberText(v[1]*scale)}`;
  const append=(body,values) => {const row=document.createElement("tr");for (const value of values) {const cell=document.createElement("td");cell.textContent=value;row.append(cell);}body.append(row);};
  const values=$("surface-values").querySelector("tbody"),peaks=$("surface-peaks").querySelector("tbody"),changes=$("surface-changes").querySelector("tbody");
  for (const body of [values,peaks,changes]) body.replaceChildren();
  for (const row of d.rows) {
    const q=row.intervals;
    append(values,[row.refinement_level,row.mode_index,row.triangles,interval(q.frequency_hz,1e-6),interval(q.r_over_q_accelerator_ohm),interval(q.geometry_factor_ohm)]);
    append(peaks,[row.refinement_level,interval(q.epk_over_eacc),interval(q.bpk_over_eacc_mt_per_mv_per_m)]);
  }
  const labels={frequency_hz:"周波数",r_over_q_accelerator_ohm:"R/Q（加速器）",geometry_factor_ohm:"G",epk_over_eacc:"Epk/Eacc",bpk_over_eacc_mt_per_mv_per_m:"Bpk/Eacc"};
  for (const [index,c] of d.refinement_diagnostic.comparisons.entries()) for (const [key,label] of Object.entries(labels)) {
    const change=c.relative_change_upper_bounds[key];
    append(changes,[`${d.rows[c.previous_row].refinement_level} → ${d.rows[c.current_row].refinement_level}`,label,change===null ? "未確認" : numberText(100*change),numberText(100*d.limits[key]),d.refinement_diagnostic.acceptance_comparison_indices.includes(index) ? "対象" : "履歴",change===null ? "未確認" : c.gates[key] ? "基準内" : "未達"]);
  }
  $("surface-diagnostics").textContent=JSON.stringify({mode_id:d.mode_id,source_runs:d.rows.map(r=>r.run),geometry:d.geometry_diagnostic,refinement:d.refinement_diagnostic,geometry_approximation_assessed:d.geometry_approximation_assessed,physical_error_bound:d.physical_error_bound,scope:d.scope},null,2);
  surfaceButtons();
}
async function runSurfaceAssessment(action,data) {
  if (surfaceBusy) throw Error("表面評価の検証が終わるまで待ってください。");
  surfaceBusy=true;surfaceButtons();
  try {showSurfaceAssessment(await api(action,data));}
  finally {surfaceBusy=false;surfaceButtons();}
}
bind("surface-assess",async()=>{await runSurfaceAssessment("assess-surface-convergence",{document:trackingResult.serialized,mode_id:$("surface-mode-id").value});});
bind("surface-replay",async()=>{await runSurfaceAssessment("replay-surface-convergence",{document:surfaceResult.serialized});});
bind("surface-save",()=>{download("surface-convergence.json",surfaceResult.serialized);});
$("surface-open").addEventListener("change",async event=>{
  const file=event.target.files[0];if(!file)return;
  try {$("error").hidden=true;await runSurfaceAssessment("replay-surface-convergence",{document:await file.text()});}
  catch(error){failure(error);}
  finally{event.target.value="";}
});

// Saved-field mode tracking; the server owns validation and ID propagation.
let trackingResult = null, trackingBusy = false, trackingJobSignature = "";
let surfaceResult = null, surfaceBusy = false;
function trackingJobs(jobs) {
  const completed = jobs.filter(j => j.status === "complete" && !["study","tracked_study","adaptive_study","tune","adaptive_refinement","hphi_solve","hphi_study","hphi_convergence","hphi_tracking","hphi_tracking_history","planar_solve","planar_study","planar_convergence","planar_tracking","planar_tracking_history","magnetic_report_import","static_field_solve","static_field_study"].includes(j.kind));
  const signature = JSON.stringify(jobs.filter(j => j.status === "complete").map(j => [j.id,j.kind]));
  if (signature === trackingJobSignature) return;
  trackingJobSignature = signature;
  for (const id of ["tracking-previous", "tracking-current", "tracking-study"]) {
    const available = id === "tracking-study" ? jobs.filter(j => j.status === "complete" && j.kind === "study") : completed;
    const select = $(id), previous = select.value;
    select.replaceChildren(new Option("結果を選択", ""));
    for (const j of available) select.add(new Option(j.id, j.id));
    if (available.some(j => j.id === previous)) select.value = previous;
  }
}
function trackingButtons() {
  const d = trackingResult?.document, study = d?.document_type === "study_mode_tracking", history = study || d?.document_type === "mode_tracking_history";
  $("tracking-compare").disabled = trackingBusy || history;
  $("tracking-start").disabled = trackingBusy || !d || history;
  $("tracking-extend").disabled = trackingBusy || study || !history || !d.can_extend;
  $("tracking-save").disabled = trackingBusy || !d;
  $("tracking-study-run").disabled = trackingBusy;
  $("tracking-reset").disabled = trackingBusy;
  $("tracking-open").disabled = trackingBusy;
  $("tracking-previous").disabled = trackingBusy || history;
  $("tracking-ids").disabled = trackingBusy || history;
  $("tracking-previous").closest("label").hidden = history;
  $("tracking-ids").closest("label").hidden = history;
  $("tracking-origin").hidden = !history;
  $("tracking-origin").textContent = history ? `履歴末尾の基準結果: ${study ? d.history.current_run : d.current_run}` : "";
  $("tracking-comparison").hidden = $("tracking-mapping").value !== "piecewise_remesh";
  $("tracking-comparison-swap").disabled = trackingBusy;
  $("tracking-affine").hidden = $("tracking-mapping").value !== "affine_remesh";
  $("tracking-affine-invert").disabled = trackingBusy;
  $("tracking-curved-note").hidden = $("tracking-mapping").value !== "curved_same_domain";
  $("tracking-domain-note").hidden = $("tracking-mapping").value !== "same_domain";
  $("tracking-pairs-label").hidden = $("tracking-mapping").value !== "paired_mesh";
  $("tracking-policy-label").hidden = !$("tracking-retain").checked;
  $("tracking-link-label").hidden = !$("tracking-retain").checked;
  surfaceButtons();
}
function trackingControls(derivedAffine=false,derivedCurved=false) {
  const controls = {mapping: derivedCurved ? "piecewise_remesh" : derivedAffine ? "affine_remesh" : $("tracking-mapping").value, sample_order: number("tracking-order"),
    minimum_overlap: number("tracking-overlap"), minimum_assignment_margin: number("tracking-margin"),
    relative_cluster_gap: number("tracking-gap"), minimum_relative_singular_value: number("tracking-rank")};
  if (controls.mapping === "piecewise_remesh" && !derivedCurved) controls.comparison_meshes = JSON.parse($("tracking-comparison-json").value);
  if (controls.mapping === "affine_remesh" && !derivedAffine) controls.affine_map = {radial_scale: number("tracking-affine-radial"), axial_scale: number("tracking-affine-axial"), axial_shear: number("tracking-affine-shear")};
  if (controls.mapping === "paired_mesh") controls.vertex_pairs = JSON.parse($("tracking-pairs").value);
  if ($("tracking-retain").checked) Object.assign(controls, {cluster_transition_policy: $("tracking-policy").value, minimum_cluster_link: number("tracking-link")});
  return controls;
}
function showTracking(response) {
  trackingResult = response;
  const d = response.document, study = d.document_type === "study_mode_tracking", history = study || d.document_type === "mode_tracking_history";
  const sequence = study ? d.history : d;
  const pair = history ? sequence.steps.at(-1) : d, r = pair.tracking, controls = pair.request.controls;
  $("tracking-study-points").hidden = !study;
  const pointBody = $("tracking-study-points").querySelector("tbody"); pointBody.replaceChildren();
  if (study) {
    $("tracking-study-ids").value = JSON.stringify(d.request.initial_ids);
    $("tracking-study-controls").value = JSON.stringify(d.request.step_controls,null,2);
    for (const point of d.point_results) {
      const row=document.createElement("tr");
      for (const value of [point.index,point.value,({INITIAL:"初期点",PASS:"確認済み",UNVERIFIED:"未確認",NOT_VISITED:"未追跡"})[point.status],
        point.current_mode_ids === null ? "未追跡" : point.current_mode_ids.map(id=>id ?? "個別ID未確定").join(", ")]) {
        const cell=document.createElement("td");cell.textContent=value;row.append(cell);
      }
      pointBody.append(row);
    }
  }
  $("tracking-mapping").value = controls.mapping;
  for (const [id,key] of [["order","sample_order"],["overlap","minimum_overlap"],["margin","minimum_assignment_margin"],["gap","relative_cluster_gap"],["rank","minimum_relative_singular_value"]])
    $(`tracking-${id}`).value = controls[key];
  $("tracking-retain").checked = controls.cluster_transition_policy !== undefined;
  $("tracking-policy").value = controls.cluster_transition_policy ?? "retain_subspace";
  if (controls.minimum_cluster_link !== undefined) $("tracking-link").value = controls.minimum_cluster_link;
  if (controls.vertex_pairs) $("tracking-pairs").value = JSON.stringify(controls.vertex_pairs);
  if (controls.comparison_meshes) $("tracking-comparison-json").value = JSON.stringify(controls.comparison_meshes,null,2);
  if (controls.affine_map) for (const [id,key] of [["radial","radial_scale"],["axial","axial_scale"],["shear","axial_shear"]]) $( `tracking-affine-${id}` ).value = controls.affine_map[key];

  $("tracking-status").textContent = `${d.status} — ${study ? `Study ${d.visited_point_indices.length}/${d.point_results.length} 点を追跡。未追跡 ${d.unvisited_point_indices.length} 点。` : history ? `履歴 ${d.steps.length} 段階。` : "2時点の比較。"} ${d.status !== "PASS" ? "未確認の対応があります。" : r.individual_ids_complete ? "全個別IDの対応を確認しました。" : "部分空間の対応を確認しました。集合内の個別IDは未確定です。"}${history && !sequence.can_extend ? " この履歴からの継続はできません。" : ""}`;
  if (r.physical_mapping?.boundary_conditions) {
    $("tracking-status").textContent += r.physical_mapping.reflected_partial_spectrum
      ? " 鏡映された部分スペクトルの対応です。番号は全空洞の周波数順位ではありません。"
      : " 同じ端条件の半領域を比較しました。";
  }
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
    study_run: study ? d.request.study_run : null, unvisited_point_indices: study ? d.unvisited_point_indices : [],
    physical_mapping: r.physical_mapping ?? null,
    stop_reason: sequence.stop_reason ?? null, unmatched_previous: r.unmatched_previous, unmatched_current: r.unmatched_current,
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
  trackingResult = null; $("tracking-study-points").hidden = true; $("tracking-status").textContent = "比較する結果とIDを指定してください。";
  $("tracking-matches").querySelector("tbody").replaceChildren(); $("tracking-diagnostics").textContent = ""; trackingButtons();
});
bind("tracking-save", () => { download(trackingResult.document.document_type === "study_mode_tracking" ? "study-mode-tracking.json" : trackingResult.document.document_type === "mode_tracking_history" ? "mode-tracking-history.json" : "mode-tracking.json", trackingResult.serialized); });
$("tracking-open").addEventListener("change", async event => {
  const file = event.target.files[0]; if (!file) return;
  try { $("error").hidden = true; await runTracking("replay-mode-tracking", {document: await file.text()}); }
  catch (error) { failure(error); }
  finally { event.target.value = ""; }
});
bind("tracking-comparison-swap", () => {
  const meshes=JSON.parse($("tracking-comparison-json").value);
  if (!Array.isArray(meshes) || meshes.length!==2 || meshes.some(m=>!m || typeof m!=="object" || Array.isArray(m)))
    throw Error("旧・新の比較メッシュを2要素のJSON配列で入力してください。");
  $("tracking-comparison-json").value=JSON.stringify([meshes[1],meshes[0]],null,2);
});
bind("tracking-affine-invert", () => {
  const a=number("tracking-affine-radial"), c=number("tracking-affine-axial"), b=number("tracking-affine-shear");
  const inverse=[1/a,1/c,-b/a/c];
  if (!(a>0 && c>0) || !inverse.every(Number.isFinite) || !(inverse[0]>0 && inverse[1]>0))
    throw Error("逆変換には有限の正の半径倍率・軸方向倍率と有限のせん断係数が必要です。");
  for (const [i,id] of ["radial","axial","shear"].entries()) $(`tracking-affine-${id}`).value=inverse[i];
});
$("tracking-mapping").addEventListener("change", trackingButtons);
$("tracking-retain").addEventListener("change", trackingButtons);
trackingButtons();

bind("tracking-study-run", async () => {
  const data = {study_id: $("tracking-study").value, initial_ids: JSON.parse($("tracking-study-ids").value)};
  if ($("tracking-study-controls").value.trim()) data.step_controls = JSON.parse($("tracking-study-controls").value);
  else {
    const report=await api('study-result',{id:data.study_id});
    if(data.study_id!==$("tracking-study").value)throw Error("追跡するStudyが変わりました。選び直してください。");
    data.controls = trackingControls(report.study.kind==='curved_affine_sweep',report.study.kind==='curved_harmonic_sweep');
  }
  await runTracking("track-study-modes", data);
});

// A checkpoint's original JSON text is retained for exact server replay.
let trackedExecutionResult = null, trackedExecutionBusy = false;
function trackedExecutionButtons() {
  $("tracked-execution-start").disabled = trackedExecutionBusy;
  $("tracked-execution-resume").disabled = trackedExecutionBusy || !trackedExecutionResult?.document.can_resume;
  $("tracked-execution-save").disabled = trackedExecutionBusy || !trackedExecutionResult;
  $("tracked-execution-open").disabled = trackedExecutionBusy;
  $("tracked-execution-prepare").disabled = trackedExecutionBusy;
}
function trackedPointLimit(adaptive=false) {
  const raw = $("tracked-execution-limit").value.trim();
  if (!raw) return {};
  const value = Number(raw);
  if (!Number.isInteger(value) || value < 1) throw Error("今回の処理上限は正の整数で指定してください");
  return adaptive ? {max_new_attempts:value} : {max_new_points:value};
}
function showTrackedExecution(response) {
  trackedExecutionResult = response;
  const d=response.document, adaptive=d.document_type === "adaptive_tracked_study";
  $("tracked-execution-points").hidden=adaptive;
  $("tracked-adaptive-results").hidden=!adaptive;
  if (adaptive) {showAdaptiveExecution(response);return;}
  $("tracked-execution-status").textContent = `${d.status} — ${{PAUSED:"一時停止",COMPLETE:"全指定点の対応を確認",UNVERIFIED:"対応未確認で停止"}[d.status]}。計算済み ${d.point_runs.length}/${d.point_results.length} 点。`;
  const body=$("tracked-execution-points").querySelector("tbody");body.replaceChildren();
  for (const point of d.point_results) {
    const row=document.createElement("tr");
    for (const value of [point.index,point.value,({INITIAL:"初期点",PASS:"確認済み",UNVERIFIED:"未確認",NOT_COMPUTED:"未計算"})[point.status],
      point.current_mode_ids === null ? "未計算" : point.current_mode_ids.map(id=>id ?? "個別ID未確定").join(", ")]) {
      const cell=document.createElement("td");cell.textContent=value;row.append(cell);
    }
    body.append(row);
  }
  restoreExecutionRequest(d.request);
  $("tracked-execution-diagnostics").textContent=JSON.stringify({identity_groups:d.history?.current_identity_groups ?? null,
    stop_reason:d.history?.stop_reason ?? null,last_correspondence:d.history?.steps.at(-1)?.tracking ?? null,point_runs:d.point_runs},null,2);
  trackedExecutionButtons();
}
async function trackedExecutionAction(action,data) {
  trackedExecutionBusy=true;trackedExecutionButtons();
  try {
    const response=await api(action,data);
    if (response.document) showTrackedExecution(response);
    else {$("tracked-execution-job").textContent=`追跡付きStudyを開始しました: ${response.id}。計算一覧から中止・結果表示できます。`;await refreshJobs();}
    return response;
  } finally {trackedExecutionBusy=false;trackedExecutionButtons();}
}
async function openTrackedExecution(id,adaptive=false) {
  await trackedExecutionAction(adaptive ? "adaptive-study-result" : "tracked-study-result",{id});
  $("tracked-execution").scrollIntoView({behavior:"smooth"});
}
bind("tracked-execution-prepare", async () => {
  const study=await studyDefinition(), explicit=$("tracking-study-controls").value.trim();
  const request={schema_version:1,study,initial_ids:JSON.parse($("tracking-study-ids").value),
    step_controls:explicit ? JSON.parse(explicit) : study.values.slice(1).map(()=>trackingControls(study.kind==='curved_affine_sweep',study.kind==='curved_harmonic_sweep'))};
  if ($("tracked-execution-adaptive").checked) request.adaptive={max_depth:Number($("tracked-adaptive-depth").value),max_attempts:Number($("tracked-adaptive-attempts-limit").value),minimum_parameter_step:Number($("tracked-adaptive-step").value)};
  $("tracked-execution-request").value=JSON.stringify(request,null,2);
});
bind("tracked-execution-start", async () => {
  const request=JSON.parse($("tracked-execution-request").value), adaptive=Object.hasOwn(request,"adaptive");
  await trackedExecutionAction(adaptive ? "start-adaptive-study" : "start-tracked-study",{request,...trackedPointLimit(adaptive)});
});
bind("tracked-execution-resume", async () => {
  const adaptive=trackedExecutionResult.document.document_type === "adaptive_tracked_study";
  await trackedExecutionAction(adaptive ? "resume-adaptive-study" : "resume-tracked-study",{document:trackedExecutionResult.serialized,...trackedPointLimit(adaptive)});
});
bind("tracked-execution-save", () => download(trackedExecutionResult.document.document_type === "adaptive_tracked_study" ? "adaptive-study-checkpoint.json" : "tracked-study-checkpoint.json",trackedExecutionResult.serialized));
$("tracked-execution-open").addEventListener("change",async event => {
  const file=event.target.files[0];if (!file) return;
  try {$("error").hidden=true;const document=await file.text(), adaptive=JSON.parse(document).document_type === "adaptive_tracked_study";await trackedExecutionAction(adaptive ? "replay-adaptive-study" : "replay-tracked-study",{document});}
  catch(e) {failure(e);}
  finally {event.target.value="";}
});
trackedExecutionButtons();

function restoreExecutionRequest(request) {
  $("tracked-execution-request").value=JSON.stringify(request,null,2);
  $("tracked-execution-adaptive").checked=!!request.adaptive;
  $("tracked-adaptive-settings").hidden=!request.adaptive;
  if (request.adaptive) for (const [id,key] of [["depth","max_depth"],["attempts-limit","max_attempts"],["step","minimum_parameter_step"]])
    $(`tracked-adaptive-${id}`).value=request.adaptive[key];
}
function showAdaptiveExecution(response) {
  const d=response.document;
  const reason=({maximum_attempts:"比較回数の上限",maximum_depth:"二分深さの上限",minimum_parameter_step:"追加区間の最小幅",floating_point_resolution:"数値で区別できる幅の限界"})[d.stop_reason];
  $("tracked-execution-status").textContent=`${d.status} — 適応二分${d.status==="PAUSED" ? "を一時停止" : d.status==="COMPLETE" ? "で全目標の対応を確認" : "を停止"}。計算済み ${d.points.length} 点、採用 ${d.accepted_point_indices.length} 点、比較 ${d.attempts.length} 回。到達目標 ${d.reached_target_indices.length}/${d.request.study.values.length}。${reason ? " 停止理由: "+reason : ""}`;
  const rows=(id,values)=>{const body=$(id).querySelector("tbody");body.replaceChildren();for(const valuesRow of values){const row=document.createElement("tr");for(const value of valuesRow){const cell=document.createElement("td");cell.textContent=value;row.append(cell);}body.append(row);}};
  rows("tracked-adaptive-points",d.points.map((point,i)=>{const order=d.accepted_point_indices.indexOf(i),target=d.request.study.values.indexOf(point.value);return [i,point.value,target<0 ? "追加点" : `元目標 ${target}`,order<0 ? "未採用" : `採用（順序 ${order}）`];}));
  rows("tracked-adaptive-attempts",d.attempts.map((a,i)=>[i,d.points[a.previous_point].value,d.points[a.current_point].value,a.original_target_index,a.depth,a.correspondence.status,({ACCEPT:"採用",BISECT:"二分",STOP:"停止"})[a.decision],a.midpoint ?? "—"]));
  $("tracked-adaptive-pending").textContent=`次の比較目標: ${d.pending_targets?.map(p=>p.value).join(", ") || "なし"}。未到達の元目標番号: ${d.unreached_target_indices.join(", ") || "なし"}。`;
  restoreExecutionRequest(d.request);
  $("tracked-execution-diagnostics").textContent=JSON.stringify({identity_groups:d.history?.current_identity_groups ?? null,stop_reason:d.stop_reason,
    last_correspondence:d.attempts.at(-1)?.correspondence.tracking ?? null,point_runs:d.points.map(p=>p.run)},null,2);
  trackedExecutionButtons();
}
$("tracked-execution-adaptive").addEventListener("change",()=>{$("tracked-adaptive-settings").hidden=!$("tracked-execution-adaptive").checked;});


let tuningResult=null, tuningBusy=false;
function tuningParameterMode() {
  const coupled=$("tune-coupled").checked,unit=coupled ? $("tune-parameter-unit").value : "m";
  $("tune-binding-settings").hidden=!coupled;
  $("tune-linear-help").hidden=$("tune-binding-law").value!=="linear";
  $("tune-polynomial-help").hidden=$("tune-binding-law").value!=="polynomial";
  $("tune-affine-settings").hidden=$("tune-binding-law").value!=="affine";
  $("tune-profile-bindings").hidden=$("tune-binding-law").value==="affine";
  $("tune-vertex").disabled=coupled;$("tune-coordinate").disabled=coupled;
  for(const label of document.querySelectorAll(".tune-unit-label"))label.textContent=unit==="1" ? "無次元" : unit;
}
function tuningButtons() {
  for (const id of ["start","prepare","open"]) $(`tune-${id}`).disabled=tuningBusy;
  $("tune-resume").disabled=tuningBusy || !tuningResult?.document.can_resume;
  $("tune-save").disabled=tuningBusy || !tuningResult;
  $("tune-open-field").disabled=tuningBusy || tuningResult?.document.status!=="TUNED";
  $("tune-checkpoint-index").disabled=tuningBusy || !$("tune-checkpoint-index").options.length;
  $("tune-checkpoint-open").disabled=tuningBusy || !$("tune-checkpoint-index").options.length;
}
async function openTuningCheckpoints(id) {
  tuningBusy=true;tuningButtons();
  try {
    const response=await api("tune-checkpoints",{id}),select=$("tune-checkpoint-index");
    select.replaceChildren();select.dataset.job=id;
    for(const index of response.indices) {
      const option=document.createElement("option");option.value=index;option.textContent=`${index}試行の保存（未検証）`;select.append(option);
    }
    if(response.indices.length)select.value=response.indices.at(-1);
    $("tune-checkpoint-job").textContent=`${id}: `+(response.indices.length ? "保存済み試行を選んで再検証してください。" : "保存済み試行はありません。");
    $("tuning").scrollIntoView({behavior:"smooth"});
  } finally {tuningBusy=false;tuningButtons();}
}
function tuningLimit() {
  if (!$("tune-limit").value.trim()) return {};
  const n=number("tune-limit");if(!Number.isInteger(n) || n<1) throw Error("今回の計算上限は正の整数で指定してください");
  return {max_new_trials:n};
}
function showTuning(response) {
  tuningResult=response;const d=response.document,r=d.request;
  const names={PAUSED:"一時停止",TUNED:"目標周波数と粗細差の条件を確認",UNVERIFIED:"個別モードの対応未確認で停止",REFINEMENT_FAILED:"細メッシュの検査未達",UNBRACKETED:"両端で目標を挟めません",ITERATION_LIMIT:"探索回数の上限",PARAMETER_LIMIT:"探索幅の下限"};
  $("tune-status").textContent=`${d.status} — ${names[d.status]}。計算済み ${d.trials.length} 試行。対象ID: ${r.mode_id}`;
  const verdict=v=>v===undefined ? "未実施" : v ? "条件内" : "未達", display=v=>Number(v.toPrecision(9));
  $("tune-gates").textContent=`細メッシュの目標差: ${verdict(d.decision.refined_target_met)}（許容 ${r.frequency_tolerance_hz} Hz）。粗細差: ${verdict(d.decision.mesh_difference_met)}（${d.decision.mesh_frequency_difference_hz===undefined ? "—" : display(d.decision.mesh_frequency_difference_hz)} Hz / 許容 ${r.mesh_frequency_tolerance_hz} Hz）。`;
  const body=$("tune-trials").querySelector("tbody");body.replaceChildren();
  for (const trial of d.trials) {
    const rank=trial.current_mode_ids.indexOf(r.mode_id),row=document.createElement("tr");
    for (const value of [trial.index,trial.phase==="refinement" ? "最終細分" : "探索",display(trial.value),
      {INITIAL:"初期ID",PASS:"確認済み",UNVERIFIED:"未確認"}[trial.status],rank<0 ? "—" : rank+1,
      trial.frequency_hz===null ? "評価不可" : (trial.frequency_hz/1e6).toFixed(6),trial.target_error_hz===null ? "—" : display(trial.target_error_hz)]) {
      const cell=document.createElement("td");cell.textContent=value;row.append(cell);
    }
    body.append(row);
  }
  $("tune-request").value=JSON.stringify(r,null,2);$("tune-coupled").checked=r.schema_version>=2;
  $("tune-binding-law").value=r.schema_version===4 ? "affine" : r.schema_version===3 ? "polynomial" : "linear";
  if(r.schema_version>=2) {
    $("tune-parameter-name").value=r.parameter;$("tune-parameter-unit").value=r.parameter_unit;
    if(r.schema_version===4) {
      $("tune-affine-coefficients").value=JSON.stringify(r.affine_coefficients,null,2);
      $("tune-rf-coordinates").value=r.rf_coordinates;
    } else $("tune-bindings").value=JSON.stringify(r.bindings,null,2);
  } else {
    const parts=r.parameter.split("/");$("tune-vertex").value=parts.at(-2);$("tune-coordinate").value=parts.at(-1);
  }
  tuningParameterMode();
  $("tune-variable-heading").textContent=r.schema_version>=2 ? `${r.parameter} [${r.parameter_unit==="1" ? "無次元" : "m"}]` : "座標 [m]";
  $("tune-low").value=r.bounds[0];$("tune-high").value=r.bounds[1];$("tune-target").value=r.target_hz/1e6;
  for (const [id,key] of [["frequency-tolerance","frequency_tolerance_hz"],["parameter-tolerance","parameter_tolerance"],["max-trials","max_trials"],["refinement","refinement_scale"],["mesh-tolerance","mesh_frequency_tolerance_hz"]]) $(`tune-${id}`).value=r[key];
  $("tune-ids").value=JSON.stringify(r.initial_ids);$("tune-mode-id").value=r.mode_id;
  $("tune-diagnostics").textContent=JSON.stringify({decision:d.decision,controls:r.controls,trial_runs:d.trial_runs,last_correspondence:d.trials.at(-1)?.tracking?.tracking ?? null},null,2);
  tuningButtons();
}
async function tuningAction(action,data) {
  tuningBusy=true;tuningButtons();
  try {
    const response=await api(action,data);
    if(response.document) showTuning(response);
    else {$("tune-job").textContent=`周波数調整を開始しました: ${response.id}。計算一覧から中止・結果表示できます。`;await refreshJobs();}
    return response;
  } finally {tuningBusy=false;tuningButtons();}
}
async function openTuning(id) {await tuningAction("tune-result",{id});$("tuning").scrollIntoView({behavior:"smooth"});}
bind("tune-prepare",async()=>{
  const project=await preview(),coupled=$("tune-coupled").checked,vertex=coupled ? 0 : number("tune-vertex");
  const affine=coupled && $("tune-binding-law").value==="affine";
  if(!Number.isInteger(vertex) || vertex<0) throw Error("頂点番号は0以上の整数で指定してください");
  const initial_ids=$("tune-ids").value.trim() ? JSON.parse($("tune-ids").value) : Array.from({length:project.case.solver.modes},(_,i)=>`mode-${i+1}`);
  const request={schema_version:1,project,parameter:`/case/geometry/points_zr_m/${vertex}/${$("tune-coordinate").value}`,
    bounds:[number("tune-low"),number("tune-high")],target_hz:number("tune-target")*1e6,frequency_tolerance_hz:number("tune-frequency-tolerance"),
    parameter_tolerance:number("tune-parameter-tolerance"),max_trials:number("tune-max-trials"),initial_ids,mode_id:$("tune-mode-id").value,
    controls:trackingControls(affine),refinement_scale:number("tune-refinement"),mesh_frequency_tolerance_hz:number("tune-mesh-tolerance")};
  if(affine) Object.assign(request,{schema_version:4,parameter:$("tune-parameter-name").value,parameter_unit:$("tune-parameter-unit").value,
    affine_coefficients:JSON.parse($("tune-affine-coefficients").value),rf_coordinates:$("tune-rf-coordinates").value});
  else if(coupled) Object.assign(request,{schema_version:$("tune-binding-law").value==="polynomial" ? 3 : 2,parameter:$("tune-parameter-name").value,
    parameter_unit:$("tune-parameter-unit").value,bindings:JSON.parse($("tune-bindings").value)});
  $("tune-request").value=JSON.stringify(request,null,2);
});
bind("tune-start",()=>tuningAction("start-tune",{request:JSON.parse($("tune-request").value),...tuningLimit()}));
bind("tune-resume",()=>tuningAction("resume-tune",{document:tuningResult.serialized,...tuningLimit()}));
bind("tune-save",()=>download("tune-checkpoint.json",tuningResult.serialized));
bind("tune-checkpoint-open",()=>tuningAction("open-tune-checkpoint",{id:$("tune-checkpoint-index").dataset.job,index:Number($("tune-checkpoint-index").value)}));
$("tune-open").addEventListener("change",async event=>{
  const file=event.target.files[0];if(!file)return;
  try {$("error").hidden=true;await tuningAction("replay-tune",{document:await file.text()});}
  catch(e){failure(e);}finally{event.target.value="";}
});
bind("tune-open-field",async()=>{
  await tuningAction("replay-tune",{document:tuningResult.serialized});
  const d=tuningResult.document,mode=d.trials.at(-1).current_mode_ids.indexOf(d.request.mode_id)+1;
  const result=await api("import",{path:d.trial_runs.at(-1)});await refreshJobs();await openResult(result.id,mode);
});
tuningButtons();

$("tune-coupled").addEventListener("change",tuningParameterMode);
$("tune-binding-law").addEventListener("change",tuningParameterMode);
$("tune-parameter-unit").addEventListener("change",tuningParameterMode);
tuningParameterMode();


let refinementResult=null, refinementBusy=false, affineSurfaceResult=null, affineSurfaceBusy=false;
const refinementQuantities=[['frequency_hz','周波数','frequency'],['r_over_q_accelerator_ohm','R/Q = V²/(ωU)','rq'],['geometry_factor_ohm','G','g']];
const refinementPeaks=[['epk_over_eacc','Epk/Eacc','epk'],['bpk_over_eacc_mt_per_mv_per_m','Bpk/Eacc [mT/(MV/m)]','bpk']];
function refinementButtons() {
  affineSurfaceButtons();
  for (const id of ['prepare','start','open']) $(`refine-${id}`).disabled=refinementBusy;
  $('refine-resume').disabled=refinementBusy || !refinementResult?.document.can_resume;
  $('refine-save').disabled=refinementBusy || !refinementResult;
  $('refine-open-field').disabled=refinementBusy || !refinementResult?.document.levels[Number($('refine-field-event').value)]?.quantities;
}
function refinementVersion() {
  const version=Number($('refine-version').value);$('refine-order').disabled=version!==1;
  $('refine-surface-policy').disabled=version!==5;
  $('refine-bulk-label').textContent=version===5 ? 'RF寄与の選択割合（0より大きく1以下）':'残差指標の選択割合（0より大きく1以下）';
  $('refine-max-levels-label').textContent=version===5 ? '全計算回数の上限（初期・未採用の確認・局所を含む）':'水準上限（初回を含む）';
  $('refine-limit-label').textContent=version===5 ? '今回追加する計算回数（確認も含む。空欄なら停止判断まで）':'今回追加する水準の上限（空欄なら停止判断まで）';
  $('refine-max-levels').min=version>=2 ? 5:3;
  for(const [, ,id] of refinementPeaks)$(`refine-${id}`).disabled=version<3;
  for(const id of ['quadrature-order','quadrature-tolerance'])$(`refine-${id}`).disabled=version<4;
  $('refine-angle-label').textContent=version>=4 ? '曲線写像の頂点接線間の最小角 [度]（内部の条件数は未評価）':'直線三角形の最小角 [度]';
}
function refinementLimit() {
  if(!$('refine-limit').value.trim())return {};
  const n=number('refine-limit');if(!Number.isInteger(n)||n<1)throw Error('今回の水準上限は正の整数で指定してください');
  return {max_new_levels:n};
}
function showRefinement(response) {
  refinementResult=response;const d=response.document,r=d.request,branched=r.schema_version===5;
  const names={QUADRATURE_UNVERIFIED:'高次積分との比較を確認できず停止',PAUSED:'一時停止・再開可能',TARGETS_MET:'指定した細分差を達成',UNVERIFIED:'個別ID未確認で停止',QUANTITY_UNVERIFIED:'正の有限な判定量を確認できず停止',LEVEL_LIMIT:'水準上限で停止',REFINEMENT_LIMIT:'要素数または最小角の制約で停止',TRACKING_BUDGET:'追跡の作業量上限で停止',ZERO_INDICATOR:'選択可能な残差指標がなく停止'};
  $('refine-status').textContent=`${d.status} — ${names[d.status]}。計算済み ${d.levels.length} ${branched ? '回（未採用の確認も含む）':'水準'}。対象ID: ${r.mode_id}`;
  const cost=response.execution_cost;
  $('refine-cost').textContent=cost ? `関連ジョブの観測時間: ${cost.recorded_seconds.toFixed(2)} 秒${cost.all_event_owners_timed ? '':'（記録のある部分の合計）'}。時間記録あり ${cost.jobs.filter(j=>j.elapsed_seconds!==null).length} ジョブ。時間不明の計算 ${cost.unknown_event_indices.length} 回。`:'関連ジョブの観測時間: 不明。';
  const phase={initial:'初期',residual:'局所細分',uniform_confirmation:'全域確認',uniform_probe:'RF確認',rf_local:'RF局所細分'};
  $('refine-confirmation').textContent=`版${r.schema_version}: ${r.schema_version>=2 ? '全域確認 '+d.levels.filter(l=>l.refinement_kind==='uniform_confirmation').length+' 回（最低2回）' : '局所差のみ・全域確認なし'}。${d.decision.next_refinement_kind ? '次: '+phase[d.decision.next_refinement_kind]+'。' : ''} 表面ピーク: ${{UNASSESSED:'未評価',NOT_CONFIRMED:'全条件の確認未完',UNVERIFIED:'未確認',TARGETS_MET:'指定した区間変化を達成'}[d.surface_status]} (${d.surface_status})。物理誤差上界: なし。`;
  const accepted=branched ? d.decision.accepted_event_indices : d.levels.map(l=>l.index);
  let gateChanges=d.decision.changes ?? [],peakGateChanges=d.decision.surface_changes ?? [];
  if(branched) {
    const probe=[...d.levels].reverse().find(l=>l.refinement_kind==='uniform_probe');
    const parent=probe ? d.levels[probe.parent_event_index]:null;
    const previous=parent?.refinement_kind==='uniform_probe' && parent.accepted ? parent.confirmation_comparison:null;
    gateChanges=[previous?.changes,probe?.confirmation_comparison?.changes];
    peakGateChanges=[previous?.surface_changes,probe?.confirmation_comparison?.surface_changes];
    $('refine-confirmation').textContent=`版5: 採用列 ${accepted.map(i=>i+1).join(' → ') || 'なし'}。確認 ${d.levels.filter(l=>l.refinement_kind==='uniform_probe').length} 回、局所 ${d.levels.filter(l=>l.refinement_kind==='rf_local').length} 回。最終連続確認 ${d.levels[accepted.at(-1)]?.uniform_confirmations ?? 0} 回（必要2回）。${d.decision.next_refinement_kind ? '次: '+phase[d.decision.next_refinement_kind]+'、親計算 '+(d.decision.parent_event_index+1)+'。':''} 表面ピーク: ${d.surface_status}。物理誤差上界: なし。`;
    const surfaceProgress=probe?.accepted && !probe.confirmation_comparison?.passed;
    $('refine-gate-context').textContent=probe ? `最後の比較: 親計算 ${probe.parent_event_index+1} → 確認計算 ${probe.index+1}（${surfaceProgress ? '確認未達・次の親として採用':probe.accepted ? '採用':'未採用'}）。${surfaceProgress ? '合格数は0から数え直します。':'局所細分の後は新しい確認が必要です。'}`:'一様確認はまだありません。';
    if(r.surface_refinement_policy==='uniform_when_rf_passes')$('refine-confirmation').textContent+=' 方針: RF三量が合格し表面だけ未達なら、確認解を次の親にして一様細分。';
  } else $('refine-gate-context').textContent='';
  for(const element of document.querySelectorAll('[data-refine-branch]'))element.hidden=!branched;
  const field=$('refine-field-event');field.replaceChildren();
  for(const level of d.levels) {
    const option=document.createElement('option');option.value=level.index;
    option.textContent=`計算 ${level.index+1}: ${phase[level.refinement_kind] ?? '局所細分'}${branched ? level.accepted ? '（採用）':'（未採用）':''}`;
    option.disabled=!level.quantities;field.append(option);
  }
  field.value=accepted.at(-1) ?? d.levels.at(-1)?.index ?? '';
  const display=v=>Number.isFinite(v) ? Number(v.toPrecision(9)) : '—';
  const row=(body,values)=>{const tr=document.createElement('tr');for(const value of values){const td=document.createElement('td');td.textContent=value;tr.append(td);}body.append(tr);};
  const body=$('refine-levels').querySelector('tbody');body.replaceChildren();
  for(const level of d.levels) {
    const q=level.quantities;
    row(body,[level.index+1,phase[level.refinement_kind ?? (level.index===0 ? 'initial':'residual')],level.triangles,level.dofs,
      {INITIAL:'初期ID',PASS:'確認済み',UNVERIFIED:'未確認'}[level.status],level.mode_index===null ? '—':level.mode_index+1,
      q ? display(q.frequency_hz/1e6):'評価不可',q ? display(q.r_over_q_accelerator_ohm):'評価不可',q ? display(q.geometry_factor_ohm):'評価不可',...(branched ? [level.parent_event_index===null ? '—':level.parent_event_index+1,level.accepted ? '採用':'未採用']:[])]);
  }
  const gates=$('refine-gates').querySelector('tbody');gates.replaceChildren();
  for(const [key,label,id] of refinementQuantities) {
    const a=gateChanges[0]?.[key],b=gateChanges[1]?.[key];
    row(gates,[label,display(a?.relative_change),display(b?.relative_change),r.relative_tolerances[key],!a||!b ? '未評価' : a.passed&&b.passed ? '条件内':'未達']);
    $(`refine-${id}`).value=r.relative_tolerances[key];
  }
  const peakBody=$('refine-peaks').querySelector('tbody');peakBody.replaceChildren();$('refine-peaks').hidden=r.schema_version<3;
  if(r.schema_version>=3) {
    for(const [key,label,id] of refinementPeaks) {
      const a=peakGateChanges[0]?.[key],b=peakGateChanges[1]?.[key];
      row(gates,[label,display(a?.relative_change_upper_bound),display(b?.relative_change_upper_bound),r.surface_relative_tolerances[key],!a||!b ? '未評価' : a.passed&&b.passed ? '条件内':'未達']);
      $(`refine-${id}`).value=r.surface_relative_tolerances[key];
    }
    for(const level of d.levels) {
      const intervals=level.surface?.intervals;
      row(peakBody,[level.index+1,...refinementPeaks.flatMap(([key])=>[display(intervals?.[key]?.[0]),display(intervals?.[key]?.[1])]),level.surface?.geometry_diagnostic.status ?? '個別ID未確認']);
    }
  }
  const quadratureBody=$('refine-quadrature').querySelector('tbody');quadratureBody.replaceChildren();
  for(const id of ['quadrature','quadrature-note'])$(`refine-${id}`).hidden=r.schema_version<4;
  if(r.schema_version>=4)for(const level of d.levels) {
    const q=level.quadrature_check;
    row(quadratureBody,[level.index+1,q?.base_order ?? '—',q?.check_order ?? '—',
      ...['volume_relative_squared','interior_relative_squared','boundary_relative_squared','rayleigh_frequency','mass_form'].map(key=>display(q?.relative_differences[key])),
      q?.relative_tolerance ?? r.quadrature_relative_tolerance,q ? q.passed ? '条件内':'未達':'未評価']);
  }
  $('refine-quadrature-order').value=r.quadrature_check_order ?? 24;
  $('refine-quadrature-tolerance').value=r.quadrature_relative_tolerance ?? .000001;
  $('refine-surface-policy').value=r.surface_refinement_policy ?? 'rf_goal';
  $('refine-request').value=JSON.stringify(r,null,2);$('refine-version').value=r.schema_version;refinementVersion();
  for(const [id,key] of [['bulk','bulk_fraction'],['max-levels','max_levels'],['max-triangles','max_triangles'],['angle',r.schema_version>=4 ? 'minimum_corner_angle_deg':'minimum_angle_deg']])$(`refine-${id}`).value=r[key];
  for(const [id,key] of [['overlap','minimum_overlap'],['margin','minimum_assignment_margin'],['gap','relative_cluster_gap'],['rank','minimum_relative_singular_value']])$(`refine-${id}`).value=r.controls[key];
  if(r.schema_version===1)$('refine-order').value=r.controls.sample_order;
  $('refine-ids').value=JSON.stringify(r.initial_ids);$('refine-mode-id').value=r.mode_id;
  $('refine-diagnostics').textContent=JSON.stringify({execution_cost:cost ?? null,decision:d.decision,controls:r.controls,initial_mesh:r.initial_mesh,level_runs:d.level_runs,
    quality:d.levels.map(l=>l.quality),quadrature:d.levels.map(l=>l.quadrature_check ?? null),last_correspondence:d.levels.at(-1)?.tracking ?? null},null,2);
  refinementButtons();
}
async function refinementAction(action,data) {
  if(refinementBusy)throw Error('適応計算の要求を処理中です');
  refinementBusy=true;refinementButtons();
  try {
    const response=await api(action,data);
    if(response.document)showRefinement(response);
    else {$('refine-job').textContent=`適応計算を開始しました: ${response.id}。計算一覧から中止・結果表示できます。`;await refreshJobs();}
    return response;
  } finally {refinementBusy=false;refinementButtons();}
}
async function openRefinement(id) {await refinementAction('adaptive-refinement-result',{id});$('adaptive-refinement').scrollIntoView({behavior:'smooth'});}
bind('refine-prepare',async()=>{
  const project=await preview(),version=Number($('refine-version').value);
  const controls={mapping:version>=4 ? 'nested_curved':version>=2 ? 'nested_affine':'same_domain',minimum_overlap:number('refine-overlap'),minimum_assignment_margin:number('refine-margin'),relative_cluster_gap:number('refine-gap'),minimum_relative_singular_value:number('refine-rank')};
  if(version===1)controls.sample_order=number('refine-order');
  const request={schema_version:version,case:project.case,initial_mesh:project.mesh_data ?? null,
    initial_ids:$('refine-ids').value.trim() ? JSON.parse($('refine-ids').value):Array.from({length:project.case.solver.modes},(_,i)=>`mode-${i+1}`),
    mode_id:$('refine-mode-id').value,controls,bulk_fraction:number('refine-bulk'),max_levels:number('refine-max-levels'),max_triangles:number('refine-max-triangles'),[version>=4 ? 'minimum_corner_angle_deg':'minimum_angle_deg']:number('refine-angle'),
    relative_tolerances:Object.fromEntries(refinementQuantities.map(([key,label,id])=>[key,number(`refine-${id}`)]))};
  if(version>=2)request.confirmation='uniform_two_steps';
  if(version>=3)request.surface_relative_tolerances=Object.fromEntries(refinementPeaks.map(([key,label,id])=>[key,number(`refine-${id}`)]));
  if(version>=4){request.quadrature_check_order=number('refine-quadrature-order');request.quadrature_relative_tolerance=number('refine-quadrature-tolerance');}
  if(version===5 && $('refine-surface-policy').value!=='rf_goal')request.surface_refinement_policy=$('refine-surface-policy').value;
  $('refine-request').value=JSON.stringify(request,null,2);
});
bind('refine-start',()=>refinementAction('start-adaptive-refinement',{request:$('refine-request').value,...refinementLimit()}));
bind('refine-resume',()=>refinementAction('resume-adaptive-refinement',{document:refinementResult.serialized,...refinementLimit()}));
bind('refine-save',()=>download('adaptive-refinement-checkpoint.json',refinementResult.serialized));
$('refine-open').addEventListener('change',async event=>{
  const file=event.target.files[0];if(!file)return;
  try {$('error').hidden=true;await refinementAction('replay-adaptive-refinement',{document:await file.text()});}
  catch(e){failure(e);}finally{event.target.value='';}
});
bind('refine-open-field',async()=>{
  const index=Number($('refine-field-event').value);
  await refinementAction('replay-adaptive-refinement',{document:refinementResult.serialized});
  const d=refinementResult.document,level=d.levels[index];
  if(!Number.isInteger(index) || !level?.quantities || level.mode_index===null)throw Error('選択した計算の対象IDは未確認です');
  $('refine-field-event').value=index;
  const result=await api('import',{path:d.level_runs[index]});await refreshJobs();await openResult(result.id,level.mode_index+1);
});
$('refine-field-event').addEventListener('change',refinementButtons);
$('refine-version').addEventListener('change',refinementVersion);
refinementButtons();refinementVersion();


function affineSurfaceButtons() {
  $('affine-surface-assess').disabled=affineSurfaceBusy || refinementBusy || (refinementResult?.document.levels.length ?? 0)<3 || refinementResult?.document.request.schema_version>=4;
  for(const id of ['save','replay','open-field'])$(`affine-surface-${id}`).disabled=affineSurfaceBusy || !affineSurfaceResult;
  for(const id of ['open','mode-id'])$(`affine-surface-${id}`).disabled=affineSurfaceBusy;
  $('affine-surface-progress').textContent=affineSurfaceBusy ? '元の適応系列・保存場・ピーク上下界を再検証しています…':'';
}
function showAffineSurface(response) {
  affineSurfaceResult=response;const d=response.document;
  $('affine-surface-mode-id').value=d.mode_id;
  const statuses={TARGETS_MET:'基準達成（細分差）',NOT_CONVERGED:'未収束',UNVERIFIED:'未確認',CONFIRMATION_PENDING:'全域確認待ち',SINGULAR_GEOMETRY:'再入角：有限ピークは未認定',UNVERIFIED_GEOMETRY:'形状未確認：ピークは未認定'};
  $('affine-surface-status').textContent=`${d.status} — ${statuses[d.status]}。対象ID: ${d.mode_id}。${d.rows.length}水準、直近2区間を判定。`;
  $('affine-surface-confirmation').textContent=`${d.uniform_confirmation_required ? '版2：最後の全域確認2水準 '+(d.two_uniform_steps_present ? 'あり':'不足'):'版1：局所差のみ・全域確認なし'}。元の適応判定: ${d.checkpoint.status}。物理誤差上界: なし。`;
  const joins=d.geometry_diagnostic.joins;
  $('affine-surface-geometry').textContent=`元輪郭の再入角 ${joins.filter(j=>j.classification==='reentrant_pec_corner').length}、凸角 ${joins.filter(j=>j.classification==='convex_pec_corner').length}。形状診断: ${d.geometry_diagnostic.status}。${d.geometry_diagnostic.analytic_geometry_approximated ? '解析曲線の弦近似：元幾何は未確認。':''}`;
  const text=x=>Number.isFinite(x) ? x.toPrecision(8):'未確認';
  const interval=(v,scale=1)=>v===null ? '未確認':v[0]===v[1] ? text(v[0]*scale):`${text(v[0]*scale)} ～ ${text(v[1]*scale)}`;
  const append=(body,values)=>{const row=document.createElement('tr');for(const value of values){const cell=document.createElement('td');cell.textContent=value;row.append(cell);}body.append(row);};
  const values=$('affine-surface-values').querySelector('tbody'),peaks=$('affine-surface-peaks').querySelector('tbody'),changes=$('affine-surface-changes').querySelector('tbody');
  for(const body of [values,peaks,changes])body.replaceChildren();
  const phases={initial:'初期',residual:'局所細分',uniform_confirmation:'全域確認'};
  for(const row of d.rows) {
    const q=row.intervals;
    append(values,[row.refinement_level+1,phases[row.refinement_kind],row.mode_index+1,row.triangles,interval(q.frequency_hz,1e-6),interval(q.r_over_q_accelerator_ohm),interval(q.geometry_factor_ohm)]);
    append(peaks,[row.refinement_level+1,interval(q.epk_over_eacc),interval(q.bpk_over_eacc_mt_per_mv_per_m)]);
  }
  const labels={frequency_hz:'周波数',r_over_q_accelerator_ohm:'R/Q（加速器）',geometry_factor_ohm:'G',epk_over_eacc:'Epk/Eacc',bpk_over_eacc_mt_per_mv_per_m:'Bpk/Eacc'};
  for(const [index,c] of d.refinement_diagnostic.comparisons.entries())for(const [key,label] of Object.entries(labels)) {
    const change=c.relative_change_upper_bounds[key];
    append(changes,[`${d.rows[c.previous_row].refinement_level+1} → ${d.rows[c.current_row].refinement_level+1}`,label,change===null ? '未確認':text(100*change),text(100*d.limits[key]),d.refinement_diagnostic.acceptance_comparison_indices.includes(index) ? '対象':'履歴',change===null ? '未確認':c.gates[key] ? '基準内':'未達']);
  }
  $('affine-surface-diagnostics').textContent=JSON.stringify({mode_id:d.mode_id,source_runs:d.rows.map(r=>r.run),geometry:d.geometry_diagnostic,refinement:d.refinement_diagnostic,geometry_approximation_assessed:d.geometry_approximation_assessed,physical_error_bound:d.physical_error_bound,scope:d.scope},null,2);
  affineSurfaceButtons();
}
async function runAffineSurface(action,data) {
  if(affineSurfaceBusy)throw Error('直線表面評価を再検証中です');
  affineSurfaceBusy=true;affineSurfaceButtons();
  try {showAffineSurface(await api(action,data));}
  finally {affineSurfaceBusy=false;affineSurfaceButtons();}
}
bind('affine-surface-assess',()=>runAffineSurface('assess-affine-surface-convergence',{document:refinementResult.serialized,mode_id:$('affine-surface-mode-id').value}));
bind('affine-surface-replay',()=>runAffineSurface('replay-affine-surface-convergence',{document:affineSurfaceResult.serialized}));
bind('affine-surface-save',()=>download('affine-surface-convergence.json',affineSurfaceResult.serialized));
$('affine-surface-open').addEventListener('change',async event=>{
  const file=event.target.files[0];if(!file)return;
  try {$('error').hidden=true;await runAffineSurface('replay-affine-surface-convergence',{document:await file.text()});}
  catch(error){failure(error);}finally{event.target.value='';}
});
bind('affine-surface-open-field',async()=>{
  await runAffineSurface('replay-affine-surface-convergence',{document:affineSurfaceResult.serialized});
  const row=affineSurfaceResult.document.rows.at(-1),result=await api('import',{path:row.run});
  await refreshJobs();await openResult(result.id,row.mode_index+1);
});
affineSurfaceButtons();

let rfPeakResult=null,rfPeakBusy=false,rfPeakReady=false,rfPeakRequest=0;
function rfPeakButtons() {
  const te = currentResult?.result.physics === 'axisymmetric_m0_te';
  $('rf-peaks-assess').disabled=te || !rfPeakReady || rfPeakBusy;
  $('rf-peaks-open').disabled=te || !rfPeakReady || rfPeakBusy;
  for(const id of ['save','replay'])$(`rf-peaks-${id}`).disabled=!rfPeakResult || rfPeakBusy;
}
function resetRFPeaks(ready=false) {
  ++rfPeakRequest;rfPeakResult=null;rfPeakBusy=false;rfPeakReady=ready;
  $('rf-peaks-status').textContent=currentResult?.result.physics === 'axisymmetric_m0_te' ? 'TEの連続表面ピーク評価は未対応です。描画サンプルをピーク値として扱いません。' : '選択した保存結果・順位の連続離散ピークはまだ評価していません。';
  $('rf-peaks-values').querySelector('tbody').replaceChildren();$('rf-peaks-diagnostics').textContent='';rfPeakButtons();
}
function showRFPeaks(response) {
  rfPeakResult=response;const d=response.document;
  $('rf-peaks-status').textContent=`${d.case_name} — 順位 ${d.mode_index+1}: 連続離散ピークのみ (${d.status})。メッシュ収束: 未評価。物理誤差上界: なし。幾何診断: ${d.geometry_diagnostic.status}。`;
  const body=$('rf-peaks-values').querySelector('tbody');body.replaceChildren();
  const display=v=>v===null ? '未定義' : Number.isFinite(v) ? Number(v.toPrecision(9)) : '未評価';
  for(const [key,label,estimate] of [['epk_v_per_m','Epk [V/m]','epk_surface_estimate_v_per_m'],['hpk_a_per_m','Hpk [A/m]',null],['bpk_t','Bpk [T]','bpk_surface_estimate_t'],['epk_over_eacc','Epk/Eacc','epk_over_eacc_estimate'],['bpk_over_eacc_mt_per_mv_per_m','Bpk/Eacc [mT/(MV/m)]','bpk_over_eacc_estimate_mt_per_mv_per_m']]) {
    const row=document.createElement('tr'),interval=d.intervals[key];
    for(const value of [label,display(estimate ? d.rf[estimate] : undefined),display(interval?.[0] ?? null),display(interval?.[1] ?? null)]){const cell=document.createElement('td');cell.textContent=value;row.append(cell);}body.append(row);
  }
  $('rf-peaks-diagnostics').textContent=JSON.stringify({run:d.run,mode_index:d.mode_index,element_order:d.element_order,geometry_order:d.geometry_order,
    geometry_diagnostic:d.geometry_diagnostic,stored_energy_j:d.rf.stored_energy_j,eacc_v_per_m:d.rf.eacc_v_per_m,conventions:d.conventions,controls:d.controls,source:d.source},null,2);
  rfPeakButtons();
}
async function rfPeakAction(action,document=null) {
  if(!rfPeakReady || rfPeakBusy)throw Error('保存結果の読込またはピーク評価を処理中です');
  const token=++rfPeakRequest,job=currentJob,mode=Number($('mode').value);rfPeakBusy=true;rfPeakButtons();
  try {
    const response=await api(action,{id:job,mode,...(document===null ? {} : {document})});
    if(token===rfPeakRequest && job===currentJob && mode===Number($('mode').value))showRFPeaks(response);
  } catch(e) {if(token===rfPeakRequest)throw e;}
  finally {if(token===rfPeakRequest){rfPeakBusy=false;rfPeakButtons();}}
}
bind('rf-peaks-assess',()=>rfPeakAction('assess-rf-peaks'));
bind('rf-peaks-replay',()=>rfPeakAction('replay-rf-peaks',rfPeakResult.serialized));
bind('rf-peaks-save',()=>download('rf-discrete-peaks.json',rfPeakResult.serialized));
$('rf-peaks-open').addEventListener('change',async event=>{
  const file=event.target.files[0];if(!file)return;
  try {$('error').hidden=true;await rfPeakAction('replay-rf-peaks',await file.text());}
  catch(e){failure(e);}finally{event.target.value='';}
});
rfPeakButtons();

// RF design search uses three native mesh levels per trial.
const rfOptQuantities=[['frequency_hz','周波数','Hz'],['r_over_q_accelerator_ohm','R/Q（加速器定義）','Ω'],['r_over_q_circuit_ohm','R/Q（回路定義）','Ω'],['geometry_factor_ohm','G','Ω'],['epk_over_eacc','Epk/Eacc','無次元'],['bpk_over_eacc_mt_per_mv_per_m','Bpk/Eacc','mT/(MV/m)']];
const rfOptControlFields=[['sample_order','標本次数',3],['minimum_overlap','最小重なり',.98],['minimum_assignment_margin','対応の差',.05],['relative_cluster_gap','近接固有値の相対幅',1e-6],['minimum_relative_singular_value','最小相対特異値',1e-8]];
let rfOptResult=null,rfOptBusy=false,rfOptControls={mapping:'affine_remesh'},rfOptConstraintOrder=rfOptQuantities.map(q=>q[0]);
function rfOptInput(id,value) {const input=document.createElement('input');input.id=id;input.type='number';input.step='any';input.value=value;return input;}
function rfOptCell(row,content) {const cell=document.createElement('td');if(content instanceof Node)cell.append(content);else cell.textContent=content;row.append(cell);}
for(const [name,label] of [['radial_scale','半径'],['axial_scale','軸方向']]) {
  const row=document.createElement('tr');rfOptCell(row,label);
  for(const [field,value] of [['lower',1],['upper',1.01],['initial',1],['step',.01],['tolerance',.01]])rfOptCell(row,rfOptInput(`rf-opt-${name}-${field}`,value));
  $('rf-opt-variables').querySelector('tbody').append(row);
}
for(const [key,label,unit] of rfOptQuantities) {
  const option=document.createElement('option');option.value=key;option.textContent=`${label} [${unit}]`;$('rf-opt-objective').append(option);
  const row=document.createElement('tr'),use=document.createElement('input');use.type='checkbox';use.id=`rf-opt-${key}-use`;
  use.checked=['r_over_q_accelerator_ohm','epk_over_eacc'].includes(key);use.setAttribute('aria-label',`${label}の制約を使う`);rfOptCell(row,use);rfOptCell(row,`${label} [${unit}]`);
  rfOptCell(row,rfOptInput(`rf-opt-${key}-lower`,key==='r_over_q_accelerator_ohm' ? 1 : ''));
  rfOptCell(row,rfOptInput(`rf-opt-${key}-upper`,key==='r_over_q_accelerator_ohm' ? 10000 : key==='epk_over_eacc' ? 100 : ''));
  rfOptCell(row,rfOptInput(`rf-opt-${key}-scale`,key==='r_over_q_accelerator_ohm' ? 100 : 1));
  $('rf-opt-constraints').querySelector('tbody').append(row);
}
for(const [key,label,value] of rfOptControlFields) {const element=document.createElement('label');element.textContent=label;element.append(rfOptInput(`rf-opt-control-${key}`,value));$('rf-opt-controls').append(element);}
function rfOptUnit() {$('rf-opt-objective-unit').textContent=`[${rfOptQuantities.find(q=>q[0]===$('rf-opt-objective').value)[2]}]`;}
function rfOptButtons() {
  for(const element of $('rf-optimization').querySelectorAll('button,input,select,textarea'))element.disabled=rfOptBusy;
  $('rf-opt-start').disabled=rfOptBusy || !$('rf-opt-request').value.trim();$('rf-opt-request-save').disabled=$('rf-opt-start').disabled;
  $('rf-opt-resume').disabled=rfOptBusy || !rfOptResult?.document.can_resume;
  $('rf-opt-save').disabled=rfOptBusy || !rfOptResult;
  $('rf-opt-checkpoint-index').disabled=rfOptBusy || !$('rf-opt-checkpoint-index').options.length;
  $('rf-opt-checkpoint-open').disabled=$('rf-opt-checkpoint-index').disabled;
  $('rf-opt-open-field').disabled=rfOptBusy || !rfOptResult?.document.trials[Number($('rf-opt-field-trial').value)]?.assessment;
}
function restoreRFOptimizationRequest(r) {
  $('rf-opt-order').value=r.variables[0].name;
  for(const variable of r.variables)for(const field of ['lower','upper','initial','step','tolerance'])$(`rf-opt-${variable.name}-${field}`).value=variable[field];
  $('rf-opt-objective').value=r.criteria.objective.quantity;$('rf-opt-direction').value=r.criteria.objective.direction;rfOptUnit();
  $('rf-opt-improvement').value=r.objective_improvement;$('rf-opt-max-trials').value=r.max_trials;$('rf-opt-rf-coordinates').value=r.rf_coordinates;
  $('rf-opt-ids').value=JSON.stringify(r.initial_ids);$('rf-opt-mode-id').value=r.mode_id;
  rfOptControls=structuredClone(r.controls);for(const [key] of rfOptControlFields)$(`rf-opt-control-${key}`).value=r.controls[key];
  rfOptConstraintOrder=r.criteria.constraints.map(c=>c.quantity);
  for(const [key] of rfOptQuantities) {const c=r.criteria.constraints.find(c=>c.quantity===key);$(`rf-opt-${key}-use`).checked=!!c;
    for(const side of ['lower','upper'])$(`rf-opt-${key}-${side}`).value=c?.[side] ?? '';
    $(`rf-opt-${key}-scale`).value=r.constraint_scales[key] ?? 1;
  }
  $('rf-opt-request').value=JSON.stringify(r,null,2);rfOptButtons();
}
function showRFOptimization(response) {
  rfOptResult=response;const d=response.document,r=d.request;restoreRFOptimizationRequest(r);
  const status={PAUSED:'保存地点で一時停止',SEARCH_COMPLETE:'最終の設計条件を確認して終了',FINAL_UNVERIFIED:'最終の対応・細分・形状条件が未確認',FINAL_CRITERIA_FAILED:'最終の設計条件が未達'};
  $('rf-opt-status').textContent=`${d.status} — ${status[d.status]}。${d.completed_fem_solves}/${d.max_fem_solves} 完了解、対象ID ${r.mode_id}。停止理由: ${d.decision.search_stop || '探索途中'}。`;
  const body=$('rf-opt-trials').querySelector('tbody'),select=$('rf-opt-field-trial');body.replaceChildren();select.replaceChildren();
  for(const trial of d.trials) {
    const values=Object.fromEntries(r.variables.map((v,i)=>[v.name,trial.values[i]])),a=trial.assessment,row=document.createElement('tr');
    for(const value of [trial.index,trial.phase==='final' ? '最終細分' : '探索',values.radial_scale,values.axial_scale,a?.status ?? 'UNVERIFIED',a?.objective.eligible_value==null ? 'N/A' : `${a.objective.eligible_value} ${a.objective.unit}`])rfOptCell(row,value);
    body.append(row);const option=document.createElement('option');option.value=trial.index;option.textContent=`試行 ${trial.index} (${trial.phase})`;select.append(option);
  }
  if(d.trials.length)select.value=d.trials.at(-1).index;
  $('rf-opt-diagnostics').textContent=JSON.stringify({decision:d.decision,trials:d.trials.map(t=>({index:t.index,refinement_status:t.assessment?.refinement_status ?? null,constraints:t.assessment?.constraints ?? null,levels:t.assessment?.assessment.rows ?? null})),trial_directories:d.trial_directories,scope:d.scope},null,2);
  rfOptButtons();
}
function rfOptLimit() {if(!$('rf-opt-limit').value.trim())return {};const n=number('rf-opt-limit');if(!Number.isInteger(n)||n<1)throw Error('今回の試行上限は正の整数で指定してください');return {max_new_trials:n};}
async function rfOptAction(action,data) {
  rfOptBusy=true;rfOptButtons();$('rf-opt-job').textContent='保存場・入力を検証しています。状態確認や他ジョブの中止は計算一覧から行えます。';
  try {const response=await api(action,data);
    if(response.document)showRFOptimization(response);
    else {$('rf-opt-job').textContent=`RF探索ジョブ: ${response.id}。計算一覧から中止・結果表示できます。`;await refreshJobs();}
    if(response.document)$('rf-opt-job').textContent='保存文書と場の再検証が完了しました。';return response;
  } catch(e) {$('rf-opt-job').textContent='操作を完了できませんでした。エラーを確認してください。';throw e;} finally {rfOptBusy=false;rfOptButtons();}
}
async function openRFOptimization(id) {await rfOptAction('rf-optimization-result',{id});$('rf-optimization').scrollIntoView({behavior:'smooth'});}
async function openRFOptimizationCheckpoints(id) {
  rfOptBusy=true;rfOptButtons();
  try {const r=await api('rf-optimization-checkpoints',{id}),select=$('rf-opt-checkpoint-index');select.replaceChildren();select.dataset.job=id;
    for(const index of r.indices){const option=document.createElement('option');option.value=index;option.textContent=`${index}試行の保存（未検証）`;select.append(option);}
    if(r.indices.length)select.value=r.indices.at(-1);$('rf-opt-checkpoint-job').textContent=`${id}: ${r.indices.length ? '保存地点を選んで再検証してください。' : '保存済み試行はありません。'}`;$('rf-optimization').scrollIntoView({behavior:'smooth'});
  }finally{rfOptBusy=false;rfOptButtons();}
}
bind('rf-opt-prepare',async()=>{
  const project=await preview(),order=$('rf-opt-order').value==='radial_scale' ? ['radial_scale','axial_scale'] : ['axial_scale','radial_scale'];
  const variables=order.map(name=>Object.assign({name},Object.fromEntries(['lower','upper','initial','step','tolerance'].map(k=>[k,number(`rf-opt-${name}-${k}`)]))));
  const constraints=[],constraint_scales={},keys=[...rfOptConstraintOrder,...rfOptQuantities.map(q=>q[0]).filter(q=>!rfOptConstraintOrder.includes(q))];
  for(const key of keys)if($(`rf-opt-${key}-use`).checked){const c={quantity:key};for(const side of ['lower','upper'])if($(`rf-opt-${key}-${side}`).value.trim())c[side]=number(`rf-opt-${key}-${side}`);constraints.push(c);constraint_scales[key]=number(`rf-opt-${key}-scale`);}
  const controls={...rfOptControls,mapping:'affine_remesh',...Object.fromEntries(rfOptControlFields.map(([key])=>[key,number(`rf-opt-control-${key}`)]))};
  const initial_ids=$('rf-opt-ids').value.trim() ? JSON.parse($('rf-opt-ids').value) : Array.from({length:project.case.solver.modes},(_,i)=>`mode-${i+1}`);
  const request={schema_version:1,project,variables,criteria:{schema_version:1,objective:{quantity:$('rf-opt-objective').value,direction:$('rf-opt-direction').value},constraints},constraint_scales,objective_improvement:number('rf-opt-improvement'),max_trials:number('rf-opt-max-trials'),initial_ids,mode_id:$('rf-opt-mode-id').value,controls,rf_coordinates:$('rf-opt-rf-coordinates').value};
  const r=await api('prepare-rf-optimization',{request});$('rf-opt-request').value=r.serialized;rfOptButtons();
});
bind('rf-opt-start',()=>rfOptAction('start-rf-optimization',{request:$('rf-opt-request').value,...rfOptLimit()}));
bind('rf-opt-resume',()=>rfOptAction('resume-rf-optimization',{document:rfOptResult.serialized,...rfOptLimit()}));
bind('rf-opt-save',()=>download('rf-optimization-checkpoint.json',rfOptResult.serialized));
bind('rf-opt-request-save',async()=>{const r=await api('prepare-rf-optimization',{request:$('rf-opt-request').value});download('rf-optimization-request.json',r.serialized);});
bind('rf-opt-checkpoint-open',()=>rfOptAction('open-rf-optimization-checkpoint',{id:$('rf-opt-checkpoint-index').dataset.job,index:Number($('rf-opt-checkpoint-index').value)}));
for(const [id,action] of [['rf-opt-open','replay-rf-optimization'],['rf-opt-request-open','prepare-rf-optimization']])$(id).addEventListener('change',async event=>{
  const file=event.target.files[0];if(!file)return;
  try {$('error').hidden=true;
    if(action==='replay-rf-optimization')await rfOptAction(action,{document:await file.text()});
    else {const r=await api(action,{request:await file.text()}),p=await api('normalize',{document:r.request.project});applyProject(p.project);drawOutline(p.outline_zr_m,p.outline_closed,p.geometry_approximation);restoreRFOptimizationRequest(r.request);}
  }catch(e){failure(e);}finally{event.target.value='';}
});
bind('rf-opt-open-field',async()=>{
  const data={document:rfOptResult.serialized,trial:Number($('rf-opt-field-trial').value),level:Number($('rf-opt-field-level').value)};
  rfOptBusy=true;rfOptButtons();
  try {const result=await api('rf-optimization-field',data);await refreshJobs();await openResult(result.id,result.mode);$('rf-opt-job').textContent=`試行 ${result.trial} の水準 ${result.level+1}、ID ${result.mode_id}、順位 ${result.mode} の保存場を表示しました。`;}
  finally{rfOptBusy=false;rfOptButtons();}
});
$('rf-opt-objective').addEventListener('change',rfOptUnit);$('rf-opt-request').addEventListener('input',rfOptButtons);$('rf-opt-field-trial').addEventListener('change',rfOptButtons);rfOptUnit();rfOptButtons();

$("polarization").onchange = () => {
  const polarization = $("polarization").value;
  explicitModel = explicitModel || {physics:"rf_eigenmode",coordinates:"axisymmetric",azimuthal_index:0,
    materials:[{id:"vacuum",type:"vacuum"}],regions:[{id:"cavity",material:"vacuum",domain:"interior"}]};
  explicitModel.polarization = polarization;
  $("te-model-note").hidden = polarization !== "te";
};
