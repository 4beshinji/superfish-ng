'use strict';
const $ = id => document.getElementById(id);
const token = location.hash.slice(1) || sessionStorage.getItem('ng-session');
if (token) sessionStorage.setItem('ng-session', token);
history.replaceState(null, '', location.pathname + location.search);
let selected = new URLSearchParams(location.search).get('job'), selectedIndex = 0, renderedStudy = null, renderedPoint = null, view = null, refreshing = false;
const states = {queued:'待機中', running:'各条件を求解・保存中', verifying:'元の場・履歴を再検証中', ready:'保存内容の照合完了', complete:'全条件の実行完了', failed:'実行または保存の失敗', interrupted:'中断', cancelled:'中止'};
function jsonText(value, depth = 0) {
  if (value === null || typeof value !== 'object') {
    if (typeof value === 'number' && !Number.isFinite(value)) throw Error('有限のJSON数値が必要です');
    // Python parses integer -0 as +0; use a floating token for lossless input replay.
    return Object.is(value, -0) ? '-0.0' : JSON.stringify(value);
  }
  const array = Array.isArray(value), entries = array ? value : Object.entries(value), [open, close] = array ? ['[', ']'] : ['{', '}'];
  if (!entries.length) return open + close;
  const indent = '  '.repeat(depth + 1);
  return open + '\n' + entries.map(item => indent + (array ? jsonText(item, depth + 1) : JSON.stringify(item[0]) + ': ' + jsonText(item[1], depth + 1))).join(',\n') + '\n' + '  '.repeat(depth) + close;
}
async function api(action, data = {}, binary = false) {
  const response = await fetch('/api', {method:'POST', headers:{'Content-Type':'application/json', 'X-NG-Token':token}, body:JSON.stringify({action, ...data})});
  if (!response.ok) { const error = await response.json(); throw Error(error.error || response.statusText); }
  return binary ? response.blob() : response.json();
}
function clearPoint() { $('result-view').hidden = true; $('field-view').hidden = true; renderedPoint = null; view = null; }
function clearResult() { $('study-view').hidden = true; renderedStudy = null; clearPoint(); }
function failure(error) { $('error').hidden = false; $('error').textContent = error.message; clearResult(); }
const run = fn => async event => { if (event) event.preventDefault(); $('error').hidden = true; try { await fn(event); } catch (error) { failure(error); } };
function input() { return {document:$('document').value, display_length_unit:$('length-unit').value}; }
function setStudy(study) { $('document').value = jsonText(study) + '\n'; $('length-unit').value = study.project.display_length_unit; }
function saveBlob(blob, name) { const a = document.createElement('a'), url = URL.createObjectURL(blob); a.href = url; a.download = name; document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000); }
async function download(name) { const id = selected; saveBlob(await api('static-study-download', {id, file:name}, true), name.replaceAll('/', '-')); }
function drawField() {
  if (!view?.plot) return;
  const plot = view.plot, field = $('field').value, values = plot.cell_center_probe.fields[field];
  const canvas = $('field-canvas'), ctx = canvas.getContext('2d'); ctx.clearRect(0, 0, canvas.width, canvas.height);
  const points = plot.points_m, xs = points.map(p => p[0]), ys = points.map(p => p[1]);
  // Loop bounds support large explicit meshes without spreading arrays into function arguments.
  const extent = numbers => numbers.reduce((b, n) => [Math.min(b[0], n), Math.max(b[1], n)], [Infinity, -Infinity]);
  const [xmin,xmax] = extent(xs), [ymin,ymax] = extent(ys), [vmin,vmax] = extent(values);
  const colorLimit = Math.max(Math.abs(vmin), Math.abs(vmax));
  const margin = 70, scale = Math.min((canvas.width - 2*margin)/(xmax-xmin), (canvas.height - 2*margin)/(ymax-ymin));
  const ox = (canvas.width-scale*(xmax-xmin))/2, oy = (canvas.height-scale*(ymax-ymin))/2;
  const xy = p => [ox+(p[0]-xmin)*scale, canvas.height-oy-(p[1]-ymin)*scale];
  plot.triangles.forEach((tri, i) => {
    const t = colorLimit === 0 ? .5 : .5 + .5 * (values[i] / colorLimit);
    ctx.fillStyle = `hsl(${240*(1-t)}, 72%, 48%)`; ctx.beginPath();
    tri.forEach((node, j) => { const p = xy(points[node]); if (j) ctx.lineTo(...p); else ctx.moveTo(...p); }); ctx.closePath(); ctx.fill();
  });
  ctx.strokeStyle = '#172c39'; ctx.lineWidth = 1.2;
  for (const [a,b] of plot.boundary_edges) { ctx.beginPath(); ctx.moveTo(...xy(points[a])); ctx.lineTo(...xy(points[b])); ctx.stroke(); }
  const unit = view.project.display_length_unit, factor = unit === 'mm' ? 1000 : 1;
  ctx.fillStyle = '#172c39'; ctx.font = '14px sans-serif'; ctx.textAlign = 'left';
  ctx.fillText(`${plot.coordinate_labels[0]}: ${(xmin*factor).toPrecision(5)} … ${(xmax*factor).toPrecision(5)} ${unit}`, margin, canvas.height-20);
  ctx.fillText(`${plot.coordinate_labels[1]}: ${(ymin*factor).toPrecision(5)} … ${(ymax*factor).toPrecision(5)} ${unit}`, margin, 25);
  ctx.textAlign = 'right'; ctx.fillText(`${field} [${plot.field_units[field]}]`, canvas.width-margin, 25);
  $('field-caption').textContent = `${field} [${plot.field_units[field]}] / セル中心 ${values.length}点 / 最小 ${vmin.toPrecision(8)} / 最大 ${vmax.toPrecision(8)} / 色範囲 [${(-colorLimit).toPrecision(8)}, ${colorLimit.toPrecision(8)}] / 青=負・緑=0・赤=正 / 座標 ${unit}`;
  canvas.dataset.field = field; canvas.dataset.samples = String(values.length); canvas.dataset.unit = plot.field_units[field]; canvas.dataset.rangeMin = String(-colorLimit); canvas.dataset.rangeMax = String(colorLimit);
}
function renderPoint(result) {
  view = result.view; const failed = view.solver_status === 'nonlinear_failed';
  $('physics').textContent = `${view.project.case.name} / ${view.family.physics} / ${view.family.coordinates} / P${view.project.case.element_order} / ${view.measure === 'per_unit_length' ? '平面・単位長量' : '軸対称・全周量'}`;
  $('solver-status').textContent = failed ? '非線形求解失敗 — 停止理由と全履歴を保存。成功した場はありません。' : '求解成功 — 元のFEMと保存内容を照合済み。離散化精度は別途検証が必要です。';
  $('solver-status').dataset.status = view.solver_status;
  $('outcome-title').textContent = failed ? '停止理由・全反復履歴' : '保存された全量・規約';
  $('quantity-table').replaceChildren(); $('failure-reason').hidden = !failed;
  $('failure-reason').textContent = failed ? `停止理由: ${view.outcome.reason}` : '';
  if (!failed) {
    const table = document.createElement('table'), head = table.createTHead().insertRow();
    for (const label of ['量（保存名・SI単位）', '値']) { const th = document.createElement('th'); th.textContent = label; head.append(th); }
    const body = table.createTBody();
    for (const [name, value] of Object.entries(view.outcome.quantities)) {
      if (typeof value !== 'number') continue;
      const row = body.insertRow(); row.insertCell().textContent = name; row.insertCell().textContent = Object.is(value, -0) ? '-0' : String(value);
    }
    $('quantity-table').append(table);
  }
  $('outcome-json').textContent = jsonText(view.outcome); $('project-json').textContent = jsonText(view.project);
  $('field-view').hidden = failed; $('probe-json').textContent = view.plot ? jsonText(view.plot.cell_center_probe) : '';
  $('field').replaceChildren();
  if (view.plot) {
    for (const [name, unit] of Object.entries(view.plot.field_units)) { const option = document.createElement('option'); option.value = name; option.textContent = `${name} [${unit}]`; $('field').append(option); }
    drawField();
  }
  $('downloads').replaceChildren();
  for (const name of result.files) { const button = document.createElement('button'); button.textContent = name; button.dataset.file = name; button.onclick = run(() => download(name)); $('downloads').append(button); }
  $('result-view').hidden = false; renderedPoint = selected + ':' + result.index;
}
function renderStudy(result) {
  const summary = result.summary;
  $('selection').textContent = result.id;
  $('study-status').textContent = `全${summary.points.length}条件の実行完了 / 求解成功 ${summary.successful_points} / 非線形失敗 ${summary.nonlinear_failed_points}`;
  $('study-status').dataset.allPointsSuccessful = String(summary.all_points_successful);
  $('study-json').textContent = jsonText(summary.study); $('study-result-json').textContent = jsonText(summary);
  $('point-index').replaceChildren();
  for (const point of summary.points) {
    const option = document.createElement('option'); option.value = String(point.index);
    const value = Object.is(point.value, -0) ? '-0' : String(point.value);
    option.textContent = `${point.index + 1}: ${summary.study.parameter} = ${value} / ${point.result.status === 'complete' ? '求解成功' : '非線形失敗'}`;
    $('point-index').append(option);
  }
  if (selectedIndex >= summary.points.length) selectedIndex = 0;
  $('point-index').value = String(selectedIndex);
  $('study-downloads').replaceChildren();
  for (const name of result.files.filter(name => !name.includes('/'))) {
    const button = document.createElement('button'); button.textContent = name; button.dataset.file = name;
    button.onclick = run(() => download(name)); $('study-downloads').append(button);
  }
  $('study-view').hidden = false; renderedStudy = result.id;
}
async function openPoint() {
  if (!selected || renderedStudy !== selected) return;
  const id = selected, index = selectedIndex; let result;
  try { result = await api('static-study-point', {id, index}); }
  catch (error) { if (id !== selected || index !== selectedIndex) return; throw error; }
  if (id !== selected || index !== selectedIndex) return;
  $('point-verification').textContent = states[result.status] || result.status;
  if (result.status === 'ready') { if (renderedPoint !== id + ':' + index) renderPoint(result); }
  else { clearPoint(); if (result.status === 'failed') throw Error(result.error || result.state?.error || 'この条件の保存内容を検証できませんでした'); }
}
async function openSelected() {
  if (!selected) return;
  const id = selected; let result;
  try { result = await api('static-study-result', {id}); }
  catch (error) { if (selected !== id) return; throw error; }
  if (selected !== id) return;
  $('verification').textContent = states[result.status] || result.status;
  if (result.status === 'ready') {
    if (renderedStudy !== id) renderStudy(result);
    await openPoint();
  } else {
    clearResult(); if (result.status === 'failed') throw Error(result.error || result.state?.error || '実行または保存内容の検証に失敗しました');
  }
}
async function refresh() {
  const jobs = await api('static-study-jobs'); $('jobs').replaceChildren();
  for (const job of jobs) {
    const row = document.createElement('div'); row.className = 'job'; row.dataset.job = job.id;
    const label = document.createElement('p');
    label.textContent = `${job.id}: ${states[job.status] || job.status}` + (job.status === 'complete' ? ` / 成功 ${job.successful_points}・非線形失敗 ${job.nonlinear_failed_points}` : ''); row.append(label);
    if (job.status === 'complete') {
      const button = document.createElement('button'); button.textContent = '照合して表示'; button.dataset.job = job.id;
      button.onclick = run(async () => { selected = job.id; selectedIndex = 0; clearResult(); await openSelected(); }); row.append(button);
    }
    if (['queued', 'running'].includes(job.status)) {
      const button = document.createElement('button'); button.textContent = '中止';
      button.onclick = run(async () => { await api('cancel', {id:job.id}); await refresh(); }); row.append(button);
    }
    if (job.error) { const error = document.createElement('p'); error.textContent = job.error; row.append(error); }
    $('jobs').append(row);
  }
  await openSelected();
}
$('input-file').onchange = run(async event => {
  const file = event.target.files[0]; if (!file) return;
  setStudy(await api('static-study-validate', {document:await file.text(), display_length_unit:null}));
  $('input-status').textContent = '全条件の入力を確認しました。';
});
$('validate').onclick = run(async () => { setStudy(await api('static-study-validate', input())); $('input-status').textContent = '全条件の入力を確認しました。求解の成功や精度を保証するものではありません。'; });
$('save-study').onclick = run(async () => saveBlob(await api('static-study-download-input', input(), true), 'static-study.json'));
$('solve').onclick = run(async () => {
  const result = await api('static-study-solve', input()); selected = result.id; selectedIndex = 0; clearResult();
  $('error').hidden = true; $('input-status').textContent = '全条件の実行を開始しました。'; await refresh();
});
$('edit-selected').onclick = run(async () => {
  const id = selected, result = await api('static-study-result', {id}); if (id !== selected) return;
  if (result.status !== 'ready') throw Error('全条件の検証完了を待ってください');
  setStudy(result.summary.study); $('input-status').textContent = '元のStudyを編集できます。実行すると別の履歴を作成します。';
});
$('point-index').onchange = run(async () => { selectedIndex = Number($('point-index').value); clearPoint(); await openPoint(); });
$('field').onchange = () => drawField(); $('refresh').onclick = run(refresh);
async function tick() { if (refreshing) return; refreshing = true; try { await refresh(); } catch (error) { failure(error); } finally { refreshing = false; } }
tick(); setInterval(tick, 1000);
