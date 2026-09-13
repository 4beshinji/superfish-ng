'use strict';
const $ = id => document.getElementById(id);
const token = location.hash.slice(1) || sessionStorage.getItem('ng-session');
if (token) sessionStorage.setItem('ng-session', token);
history.replaceState(null, '', location.pathname + location.search);
let selected = new URLSearchParams(location.search).get("job"), rendered = null, refreshing = false;
const states = {queued:'待機中', running:'再計算・照合中', verifying:'元の場と全報告を再検証中', ready:'元の場と全報告の照合完了', complete:'取込完了', failed:'検証失敗', interrupted:'中断', cancelled:'中止'};
const show = value => value === null ? '未計算' : Array.isArray(value) ? JSON.stringify(value) : String(value);
function reportJSON(value, depth = 0) {
  // JSON.stringify converts IEEE -0 to +0. Keep the sign in auditable raw data.
  if (value === null || typeof value !== 'object') return Object.is(value, -0) ? '-0' : JSON.stringify(value);
  const array = Array.isArray(value), entries = array ? value : Object.entries(value);
  const [open, close] = array ? ['[', ']'] : ['{', '}'];
  if (!entries.length) return open + close;
  const indent = '  '.repeat(depth + 1);
  const rows = entries.map(item => indent + (array ? reportJSON(item, depth + 1) : JSON.stringify(item[0]) + ': ' + reportJSON(item[1], depth + 1)));
  return open + '\n' + rows.join(',\n') + '\n' + '  '.repeat(depth) + close;
}
async function api(action, data = {}, binary = false) {
  const response = await fetch('/api', {method:'POST', headers:{'Content-Type':'application/json', 'X-NG-Token':token}, body:JSON.stringify({action, ...data})});
  if (!response.ok) { const error = await response.json(); throw Error(error.error || response.statusText); }
  return binary ? response.blob() : response.json();
}
function failure(error) {
  $('error').hidden = false; $('error').textContent = error.message;
  $('report-view').hidden = true; rendered = null;
}
function run(fn) { return async event => { if (event) event.preventDefault(); try { $('error').hidden = true; await fn(); } catch (error) { failure(error); } }; }
function table(target, headers, rows) {
  target.replaceChildren(); const table = document.createElement('table');
  const heading = document.createElement('tr');
  for (const label of headers) { const cell = document.createElement('th'); cell.textContent = label; heading.append(cell); }
  table.append(heading);
  for (const values of rows) { const row = document.createElement('tr'); for (const value of values) { const cell = document.createElement('td'); cell.textContent = show(value); row.append(cell); } table.append(row); }
  target.append(table);
}
async function download(name) {
  const blob = await api('magnetic-report-download', {id:selected, file:name}, true);
  const url = URL.createObjectURL(blob), anchor = document.createElement('a'); anchor.href = url;
  anchor.download = name.replaceAll('/', '-'); anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function render(view) {
  $('selection').textContent = `${view.title} / ${selected}`;
  $('report-physics').textContent = `元の物理モデル: ${view.physics} / 報告版 ${view.report_schema_version}`;
  $('convention').textContent = view.convention;
  $('diagnostics').textContent = reportJSON(view.diagnostics);
  $('source-case').textContent = reportJSON(view.source_case);
  $('source-hashes').textContent = reportJSON(view.source_native_sha256);
  const multipole = view.kind === 'planar_multipole';
  $('multipoles').hidden = !multipole; $('work').hidden = multipole; $('quantities').replaceChildren();
  if (multipole) {
    const frame = view.frame;
    $('frame').textContent = `原点 [m]: ${show(frame.center_xy_m)} / 基準半径 [m]: ${frame.reference_radius_m} / 局所軸回転 [rad]: ${frame.rotation_rad}`;
    table($('coefficients'), ['次数 n', 'normal [T]', 'skew [T]'], view.coefficients.map(row => [row.order, row.normal_t, row.skew_t]));
    table($('traces'), ['標本数', '半径 [m]', '元場RMS [T]', '再構成RMS誤差 [T]', '相対再構成差', '負次数RMS [T]', '打切り正次数RMS [T]'],
      view.traces.map(row => [row.sample_count, row.radius_m, row.field_rms_t, row.truncated_field_rms_error_t, row.truncated_field_relative_error, row.negative_harmonic_rms_t, row.discarded_positive_harmonic_rms_t]));
  } else {
    const body = document.createElement('p'); body.textContent = `対象領域: ${view.body_region_ids.join(', ')}` + (view.origin_xy_m === null ? ' / 軸対称の全周量' : ` / トルク原点 [m]: ${show(view.origin_xy_m)}`);
    $('quantities').append(body); const values = document.createElement('div'); $('quantities').append(values);
    table(values, ['量', '値', '単位'], view.quantities.map(row => [row.name, row.value, row.unit]));
    const labels = {not_performed:'未実施', complete:'差分計算完了', failed:'変位したFEMの求解に失敗'};
    $('work-status').textContent = `${labels[view.virtual_work_status]} / ポテンシャルの単位: ${view.work_potential_unit}`;
    $('work-status').dataset.status = view.virtual_work_status;
    $('work-comparison').replaceChildren(); $('work-detail').hidden = view.virtual_work === null;
    $('work-json').textContent = view.virtual_work === null ? '' : reportJSON(view.virtual_work);
    if (view.work_comparison !== null) {
      const axial = view.kind === 'axial_force';
      table($('work-comparison'), ['変位', '刻み', '刻み単位', '対応する応力', '仮想仕事の差分', '差分 − 応力', '量の単位'], view.work_comparison.map(row =>
        axial ? ['z', row.step_m, 'm', row.stress_force_z_n, row.virtual_force_z_n, row.difference_n, 'N']
          : [row.kind === 'rotation' ? '節点回転' : row.kind, row.step, row.kind === 'rotation' ? 'rad' : 'm', row.stress_value, row.virtual_work_value, row.difference, row.unit]));
    }
  }
  $('downloads').replaceChildren();
  for (const name of ['report.json', 'request.json', ...Object.keys(view.source_native_sha256).map(name => `source/${name}`)]) {
    const button = document.createElement('button'); button.textContent = name; button.dataset.file = name; button.onclick = run(() => download(name)); $('downloads').append(button);
  }
  $('report-view').hidden = false; rendered = selected;
}
async function openSelected() {
  if (!selected) return;
  const id = selected, result = await api('magnetic-report-result', {id});
  if (selected !== id) return;
  $('verification').textContent = states[result.status] || result.status;
  if (result.status === 'ready') { if (rendered !== id) render(result.view); }
  else { $('report-view').hidden = true; rendered = null; if (result.status === 'failed') throw Error(result.error || result.state?.error || '検証に失敗しました'); }
}
async function refresh() {
  const jobs = await api('magnetic-report-jobs'); $('jobs').replaceChildren();
  for (const job of jobs) {
    const row = document.createElement('div'); row.className = 'job';
    const label = document.createElement('p'); label.textContent = `${job.id}: ${states[job.status] || job.status}` + (job.report_status === 'virtual_work_failed' ? ' / 仮想仕事の求解失敗を保存' : ''); row.append(label);
    if (job.status === 'complete') { const button = document.createElement('button'); button.textContent = '照合して表示'; button.dataset.job = job.id; button.onclick = run(async () => { selected = job.id; rendered = null; $('report-view').hidden = true; await openSelected(); }); row.append(button); }
    if (['queued', 'running'].includes(job.status)) { const button = document.createElement('button'); button.textContent = '中止'; button.onclick = run(async () => { await api('cancel', {id:job.id}); await refresh(); }); row.append(button); }
    if (job.error) { const error = document.createElement('p'); error.textContent = job.error; row.append(error); }
    $('jobs').append(row);
  }
  await openSelected();
}
$('import-form').onsubmit = run(async () => {
  const result = await api('magnetic-report-import', {source:$('source-path').value, report:$('report-path').value});
  selected = result.id; rendered = null; $('report-view').hidden = true; $('import-status').textContent = `取込を開始しました: ${result.id}`; await refresh();
});
$('refresh').onclick = run(refresh);
run(refresh)();
setInterval(async () => { if (refreshing) return; refreshing = true; try { await refresh(); } catch (error) { failure(error); } finally { refreshing = false; } }, 1500);
