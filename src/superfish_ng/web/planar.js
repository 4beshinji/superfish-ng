'use strict';
const $=id=>document.getElementById(id);
const token=location.hash.slice(1)||sessionStorage.getItem('ng-session');
if(token)sessionStorage.setItem('ng-session',token);
history.replaceState(null,'',location.pathname+location.search);
let project=null,selected=null,result=null,imageURL=null,imageBlob=null,request=0,unit='mm';
async function api(action,data={},binary=false){
 const response=await fetch('/api',{method:'POST',headers:{'Content-Type':'application/json','X-NG-Token':token},body:JSON.stringify({action,...data})});
 if(!response.ok){const error=await response.json();throw Error(error.error||response.statusText);}
 return binary?response.blob():response.json();
}
function failure(error){$('error').hidden=false;$('error').textContent=error.message;}
function run(fn){return async()=>{try{$('error').hidden=true;await fn();}catch(error){failure(error);}};}
function download(blob,name){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function numeric(id){const value=$(id).value;if(!value.trim()||!Number.isFinite(Number(value)))throw Error(`${id}: 有限の数値を入力してください`);return Number(value);}
function documentFromForm(){
 const p=structuredClone(project),c=p.case;c.name=$('name').value;c.model.polarization=$('polarization').value;
 c.mesh.element_order=numeric('order');c.modes=numeric('modes');c.rf.stored_energy_j_per_m=numeric('energy');c.rf.conductivity_s_per_m=numeric('conductivity');
 if(c.schema_version===1){const scale=unit==='mm'?1000:1;c.geometry.width_m=numeric('width')/scale;c.geometry.height_m=numeric('height')/scale;c.mesh.nx=numeric('nx');c.mesh.ny=numeric('ny');}
 p.display_length_unit=$('unit').value;return p;
}
function loadProject(p){
 project=structuredClone(p);const c=p.case;unit=p.display_length_unit;$('unit').value=unit;
 $('name').value=c.name;$('polarization').value=c.model.polarization;$('order').value=c.mesh.element_order;$('modes').value=c.modes;
 $('energy').value=c.rf.stored_energy_j_per_m;$('conductivity').value=c.rf.conductivity_s_per_m;
 $('rectangle').hidden=c.schema_version!==1;$('polygon-note').hidden=c.schema_version===1;
 if(c.schema_version===1){const scale=unit==='mm'?1000:1;$('width').value=c.geometry.width_m*scale;$('height').value=c.geometry.height_m*scale;$('nx').value=c.mesh.nx;$('ny').value=c.mesh.ny;}
 document.querySelectorAll('.length-unit').forEach(el=>el.textContent=unit);
 $('document').value=JSON.stringify(p,null,2);$('dirty').textContent='入力を復元済み';
}
function fresh(){return {format:'superfish_ng_planar_project',project_version:1,display_length_unit:'mm',case:{format:'superfish_ng_planar_case',schema_version:1,name:'矩形断面',model:{physics:'rf_eigenmode',coordinates:'cartesian',polarization:'te',propagation_constant_per_m:0,material:'vacuum',boundary:'pec'},geometry:{type:'rectangle',width_m:.31,height_m:.2},mesh:{nx:16,ny:12,element_order:2},rf:{stored_energy_j_per_m:1,conductivity_s_per_m:5.8e7},modes:4}};}
function clearImage(){request++;if(imageURL)URL.revokeObjectURL(imageURL);imageURL=null;imageBlob=null;$('image').hidden=true;$('save-image').disabled=true;}
function showQuantities(){if(!result)return;const q=result.modes[Number($('mode').value)-1];$('quantities').textContent=`f = ${(q.frequency_hz/1e6).toFixed(6)} MHz / U′ = ${q.stored_energy_j_per_m.toPrecision(6)} J/m / 壁損失 P′ = ${q.wall_loss_w_per_m.toPrecision(6)} W/m / Q0 = ${q.q0.toPrecision(6)} / G = ${q.geometry_factor_ohm.toPrecision(6)} Ω`;$('na').textContent='R/Q（加速器定義・回路定義）・加速電圧：N/A。遮断断面には有限の加速経路を定義していません。';}
async function openResult(id){
 const jobs=await api('jobs'),kind=jobs.find(job=>job.id===id)?.kind;if(kind==='planar_study')return openStudy(id);if(kind==='planar_convergence')return openConvergence(id);if(kind==='planar_tracking')return openTracking(id);
 const sequence=++request;const data=await api('planar-result',{id});if(sequence!==request)return;
 selected=id;result=data.result;loadProject(data.project);clearImage();$('result').hidden=false;$('selection').textContent=`${result.case.name} / ${id}`;
 $('mode').replaceChildren();result.modes.forEach((q,i)=>{const option=document.createElement('option');option.value=i+1;option.textContent=`${i+1}: ${(q.frequency_hz/1e6).toFixed(6)} MHz`;$('mode').append(option);});showQuantities();
 $('files').replaceChildren();for(const file of data.files){const button=document.createElement('button');button.textContent=file;button.onclick=run(async()=>download(await api('planar-download',{id,file},true),file));$('files').append(button);}
}
async function refresh(){
 const jobs=(await api('jobs')).filter(job=>['planar_solve','planar_study','planar_convergence','planar_tracking'].includes(job.kind));
 // Preserve focused controls when only an unrelated state changes.
 const signature=JSON.stringify(jobs);if($('jobs').dataset.signature===signature)return;$('jobs').dataset.signature=signature;
 refreshTrackingSources(jobs);$('jobs').replaceChildren();if(!jobs.length)$('jobs').textContent='平面RFの計算はまだありません。';
 for(const job of jobs){const row=document.createElement('div');row.className='job';row.dataset.job=job.id;
 const label=document.createElement('strong');label.textContent=`${job.status}${job.kind==='planar_study'?' / 独立掃引':job.kind==='planar_convergence'?' / 細分診断':job.kind==='planar_tracking'?' / モード追跡':''} / ${job.id}`;row.append(label);
 const details=document.createElement('small');details.textContent=job.error||job.stage||'';row.append(details);
 const button=document.createElement('button'),active=['queued','running'].includes(job.status);button.textContent=active?'中止':'結果を開く';button.disabled=!active&&job.status!=='complete';
 button.onclick=run(async()=>{if(active){await api('cancel',{id:job.id});await refresh();}else await openResult(job.id);});row.append(button);$('jobs').append(row);}
}
$('new').onclick=run(async()=>loadProject(await api('planar-normalize',{document:fresh()})));
$('open').onchange=run(async()=>{const file=$('open').files[0];if(file)loadProject(await api('planar-normalize',{document:await file.text()}));});
$('save').onclick=run(async()=>{const p=await api('planar-normalize',{document:documentFromForm()});loadProject(p);download(new Blob([JSON.stringify(p,null,2)+'\n'],{type:'application/json'}),'planar-project.json');$('dirty').textContent='保存済み';});
$('apply').onclick=run(async()=>loadProject(await api('planar-normalize',{document:$('document').value})));
$('start').onclick=run(async()=>{const data=await api('planar-start',{document:documentFromForm()});$('dirty').textContent=`投入済み: ${data.id}`;await refresh();});
$('import').onclick=run(async()=>{const data=await api('planar-import',{path:$('import-path').value});await refresh();await openResult(data.id);});
$('unit').onchange=run(async()=>{const p=documentFromForm();loadProject(await api('planar-normalize',{document:p}));clearImage();});
$('mode').onchange=()=>{clearImage();showQuantities();};$('mesh').onchange=clearImage;
$('plot').onclick=run(async()=>{if(!selected)throw Error('結果を選択してください');const sequence=++request,id=selected,mode=Number($('mode').value);const blob=await api('planar-plot',{id,mode,mesh:$('mesh').checked,length_unit:$('unit').value},true);if(sequence!==request||id!==selected)return;if(imageURL)URL.revokeObjectURL(imageURL);imageBlob=blob;imageURL=URL.createObjectURL(blob);$('image').src=imageURL;$('image').hidden=false;$('save-image').disabled=false;});
$('save-image').onclick=()=>{if(imageBlob)download(imageBlob,'planar-fields.png');};
for(const [id,action,name] of [['probe','planar-probe','planar-probe.csv'],['probe-meta','planar-probe-metadata','planar-probe.csv.json']])$(id).onclick=run(async()=>{if(!selected)throw Error('結果を選択してください');const data={id:selected,mode:Number($('mode').value),points_xy_m:JSON.parse($('points').value)};if(id==='probe')download(await api(action,data,true),name);else download(new Blob([JSON.stringify(await api(action,data),null,2)+'\n'],{type:'application/json'}),name);});
for(const input of document.querySelectorAll('.editor input,.editor select,.editor textarea'))input.addEventListener('input',()=>{$('dirty').textContent='未保存の編集';});
window.addEventListener('beforeunload',()=>{if(imageURL)URL.revokeObjectURL(imageURL);});
run(async()=>{loadProject(await api('planar-normalize',{document:fresh()}));await refresh();const id=new URLSearchParams(location.search).get('job');if(id)await openResult(id);})();
let refreshing=false;setInterval(async()=>{if(refreshing)return;refreshing=true;try{await refresh();}catch(error){failure(error);}finally{refreshing=false;}},1500);

let selectedStudy=null,currentStudy=null;
function studyFromForm(){return {format:'superfish_ng_planar_study',study_version:1,kind:'sweep',project:documentFromForm(),parameter:$('study-parameter').value,values:JSON.parse($('study-values').value)};}
function loadStudy(study){loadProject(study.project);$('study-parameter').value=study.parameter;$('study-values').value=JSON.stringify(study.values);}
async function openStudy(id){
 const data=await api('planar-study-result',{id});selectedStudy=id;currentStudy=data;loadStudy(data.study);$('study-result').hidden=false;$('study-selection').textContent=`${data.study.parameter} / ${id}`;$('study-points').replaceChildren();
 for(const point of data.result.points){const section=document.createElement('div');section.className='job';const title=document.createElement('strong');title.textContent=`点 ${point.index+1}: ${point.value}`;section.append(title);
 const table=document.createElement('table'),head=document.createElement('tr');for(const label of ['順位','f [MHz]','U′ [J/m]','P′ [W/m]','Q0','G [Ω]','R/Q（加速器/回路）']){const th=document.createElement('th');th.textContent=label;head.append(th);}table.append(head);
 point.modes.forEach((q,index)=>{const row=document.createElement('tr');for(const value of [index+1,(q.frequency_hz/1e6).toFixed(6),q.stored_energy_j_per_m.toPrecision(5),q.wall_loss_w_per_m.toPrecision(5),q.q0.toPrecision(5),q.geometry_factor_ohm.toPrecision(5),'N/A / N/A']){const td=document.createElement('td');td.textContent=value;row.append(td);}table.append(row);});section.append(table);
 const button=document.createElement('button');button.textContent='結果を取り込む';button.dataset.point=point.index;button.onclick=run(async()=>{const imported=await api('planar-study-point',{id,index:point.index});await refresh();await openResult(imported.id);});section.append(button);$('study-points').append(section);}
}
$('study-start').onclick=run(async()=>{const data=await api('planar-start-study',{document:studyFromForm()});$('dirty').textContent=`掃引投入済み: ${data.id}`;await refresh();});
$('study-save').onclick=run(async()=>{const study=await api('planar-normalize-study',{document:studyFromForm()});loadStudy(study);download(new Blob([JSON.stringify(study,null,2)+'\n'],{type:'application/json'}),'planar-study.json');});
$('study-open').onchange=run(async()=>{const file=$('study-open').files[0];if(file)loadStudy(await api('planar-normalize-study',{document:await file.text()}));});

for(const id of ["study-parameter","study-values"])$(id).addEventListener("input",()=>{$("dirty").textContent="未保存のStudy編集";});

let currentConvergence=null;
function convergenceFromForm(){return {format:'superfish_ng_planar_convergence',convergence_version:1,project:documentFromForm(),levels:numeric('convergence-levels'),mode_ranks:JSON.parse($('convergence-ranks').value),max_triangles:numeric('convergence-budget'),thresholds:JSON.parse($('convergence-thresholds').value)};}
function loadConvergence(value){loadProject(value.project);$('convergence-levels').value=value.levels;$('convergence-ranks').value=JSON.stringify(value.mode_ranks);$('convergence-budget').value=value.max_triangles;$('convergence-thresholds').value=JSON.stringify(value.thresholds,null,2);}
async function openConvergence(id){
 const data=await api('planar-convergence-result',{id});currentConvergence=data;loadConvergence(data.request);$('convergence-result').hidden=false;$('convergence-selection').textContent=`${data.result.status} / ${id}`;
 $('convergence-checks').replaceChildren();
 const labels={frequency_relative:'周波数',electric_field_relative:'電場',magnetic_field_relative:'磁場',rf_max_relative:'単位長RF（最大差）'};
 for(const decision of data.result.decisions){
  const title=document.createElement('h4');title.textContent=`順位 ${decision.mode_rank}: ${decision.status}`;$('convergence-checks').append(title);
  const table=document.createElement('table'),head=document.createElement('tr');
  for(const label of ['量','前回の相対差','最後の相対差','閾値','判定']){const th=document.createElement('th');th.textContent=label;head.append(th);}table.append(head);
  for(const [name,check] of Object.entries(decision.checks)){const row=document.createElement('tr');for(const value of [labels[name],check.previous.toExponential(4),check.last.toExponential(4),check.threshold,check.passed?'PASS':'UNVERIFIED']){const td=document.createElement('td');td.textContent=value;row.append(td);}table.append(row);}$('convergence-checks').append(table);
  const reasons=new Set(data.result.comparisons.slice(-2).flatMap(pair=>pair.modes.find(mode=>mode.mode_rank===decision.mode_rank).reasons));
  if(reasons.size){const note=document.createElement('p');note.textContent=Array.from(reasons).join(' / ');$('convergence-checks').append(note);}
 }
 $('convergence-points').replaceChildren();
 for(let index=0;index<data.request.levels;index++){const button=document.createElement('button');button.dataset.level=index;button.textContent=`水準 ${index+1} の結果を取り込む`;button.onclick=run(async()=>{const imported=await api('planar-convergence-point',{id,index});await refresh();await openResult(imported.id);});$('convergence-points').append(button);}
}
$('convergence-start').onclick=run(async()=>{const data=await api('planar-start-convergence',{document:convergenceFromForm()});$('dirty').textContent=`細分診断投入済み: ${data.id}`;await refresh();});
$('convergence-save').onclick=run(async()=>{const value=await api('planar-normalize-convergence',{document:convergenceFromForm()});loadConvergence(value);download(new Blob([JSON.stringify(value,null,2)+'\n'],{type:'application/json'}),'planar-convergence.json');});
$('convergence-open').onchange=run(async()=>{const file=$('convergence-open').files[0];if(file)loadConvergence(await api('planar-normalize-convergence',{document:await file.text()}));});
$('convergence-result-save').onclick=()=>{if(currentConvergence)download(new Blob([JSON.stringify(currentConvergence.result,null,2)+'\n'],{type:'application/json'}),'planar-convergence-results.json');};
for(const id of ['convergence-levels','convergence-ranks','convergence-budget','convergence-thresholds'])$(id).addEventListener('input',()=>{$('dirty').textContent='未保存の細分要求';});

let currentTracking=null,selectedTracking=null,trackingJobs=[];
function refreshTrackingSources(jobs){
 trackingJobs=jobs;const polygon=$('tracking-mapping').value==='polygon_uniform_scale';$('tracking-polygon-options').hidden=!polygon;
 const candidates=jobs.filter(job=>job.kind==='planar_solve'&&job.status==='complete'&&job.case_schema_version===(polygon?2:1));
 for(const id of ['tracking-previous','tracking-current']){const select=$(id),old=select.value;select.replaceChildren();const empty=document.createElement('option');empty.value='';empty.textContent=polygon?'保存済みの明示多角形を選択':'保存済みの矩形を選択';select.append(empty);for(const job of candidates){const option=document.createElement('option');option.value=job.id;option.textContent=`${job.id} / ${job.modes}モード`;select.append(option);}if(candidates.some(job=>job.id===old))select.value=old;}
}
function trackingFromForm(){const polygon=$('tracking-mapping').value==='polygon_uniform_scale';return {format:'superfish_ng_planar_tracking_request',tracking_version:polygon?2:1,mapping:polygon?{name:'polygon_uniform_scale',scale:numeric('tracking-scale'),previous_refinements:numeric('tracking-previous-refinements'),current_refinements:numeric('tracking-current-refinements')}:'normalized_rectangle',previous_mode_count:numeric('tracking-previous-count'),current_mode_count:numeric('tracking-current-count'),previous_mode_ids:JSON.parse($('tracking-ids').value),previous_identity_groups:JSON.parse($('tracking-groups').value),controls:JSON.parse($('tracking-controls').value)};}
function loadTracking(request){const polygon=request.tracking_version===2;$('tracking-mapping').value=polygon?'polygon_uniform_scale':'normalized_rectangle';if(polygon){$('tracking-scale').value=request.mapping.scale;$('tracking-previous-refinements').value=request.mapping.previous_refinements;$('tracking-current-refinements').value=request.mapping.current_refinements;}refreshTrackingSources(trackingJobs);$('tracking-previous-count').value=request.previous_mode_count;$('tracking-current-count').value=request.current_mode_count;$('tracking-ids').value=JSON.stringify(request.previous_mode_ids);$('tracking-groups').value=JSON.stringify(request.previous_identity_groups);$('tracking-controls').value=JSON.stringify(request.controls,null,2);}
async function openTracking(id){
 const data=await api('planar-tracking-result',{id});currentTracking=data;selectedTracking=id;loadTracking(data.request);$('tracking-result').hidden=false;$('tracking-selection').textContent=`${data.result.status} / ${id}`;
 $('tracking-notes').textContent=(data.result.individual_ids_complete?'対象帯域の個別IDが対応しました。':'個別IDが未確定です。部分空間のID集合と未解決の対応を区別してください。')+' '+data.result.verification_reasons.join(' / ');
 const table=document.createElement('table'),head=document.createElement('tr');for(const label of ['ID（集合）','前の順位','次の順位','対応','最小内積','前の場の位相符号']){const th=document.createElement('th');th.textContent=label;head.append(th);}table.append(head);
 for(const match of data.result.matches){const row=document.createElement('tr');for(const value of [match.previous_ids.join(', '),match.previous_indices.join(', '),match.current_indices.join(', '),match.kind==='MODE'?'単一モード':'部分空間',match.minimum_principal_overlap.toPrecision(7),match.previous_phase_multiplier??'個別未定義']){const td=document.createElement('td');td.textContent=value;row.append(td);}table.append(row);}
 $('tracking-matches').replaceChildren(table);for(const [side,label] of [['unmatched_previous','前'],['unmatched_current','次']])for(const item of data.result[side]){const note=document.createElement('p');note.textContent=`${label}の順位 ${item.indices.join(', ')}: ${item.reason}`;$('tracking-matches').append(note);}
 $('tracking-use-groups').disabled=data.result.status!=='PASS';
}
for(const side of ['previous','current'])$(`tracking-select-${side}`).onclick=run(async()=>{if(!selected||![1,2].includes(result?.case.schema_version))throw Error('平面の保存結果を選択してください');$('tracking-mapping').value=result.case.schema_version===2?'polygon_uniform_scale':'normalized_rectangle';await refresh();refreshTrackingSources(trackingJobs);$(`tracking-${side}`).value=selected;$(`tracking-${side}`).scrollIntoView({block:'center'});});
$('tracking-start').onclick=run(async()=>{const previous_id=$('tracking-previous').value,current_id=$('tracking-current').value;if(!previous_id||!current_id)throw Error('前と次の保存場を選択してください');const data=await api('planar-start-tracking',{previous_id,current_id,document:trackingFromForm()});$('dirty').textContent=`追跡投入済み: ${data.id}`;await refresh();});
$('tracking-save').onclick=run(async()=>{const request=await api('planar-normalize-tracking',{document:trackingFromForm()});loadTracking(request);download(new Blob([JSON.stringify(request,null,2)+'\n'],{type:'application/json'}),'planar-tracking-request.json');});
$('tracking-open').onchange=run(async()=>{const file=$('tracking-open').files[0];if(file)loadTracking(await api('planar-normalize-tracking',{document:await file.text()}));});
$('tracking-result-save').onclick=()=>{if(currentTracking)download(new Blob([JSON.stringify(currentTracking.result,null,2)+'\n'],{type:'application/json'}),'planar-tracking-results.json');};
for(const side of ['previous','current'])$(`tracking-${side}-import`).onclick=run(async()=>{if(!selectedTracking)throw Error('追跡結果を選択してください');const value=await api('planar-tracking-source',{id:selectedTracking,side});await refresh();await openResult(value.id);});
$('tracking-use-groups').onclick=run(async()=>{if(currentTracking?.result.status!=='PASS')throw Error('対応が確認できた追跡結果を選択してください');const value=await api('planar-tracking-source',{id:selectedTracking,side:'current'});const groups=currentTracking.result.matches.map(match=>({indices:match.current_indices,ids:match.previous_ids})).sort((a,b)=>a.indices[0]-b.indices[0]);await refresh();$('tracking-previous').value=value.id;$('tracking-current').value='';$('tracking-previous-count').value=currentTracking.request.current_mode_count;$('tracking-ids').value='null';$('tracking-groups').value=JSON.stringify(groups);$('dirty').textContent='ID集合を引継ぎ済み。次の保存場を選択してください。';});
for(const id of ['tracking-previous-count','tracking-current-count','tracking-ids','tracking-groups','tracking-controls'])$(id).addEventListener('input',()=>{$('dirty').textContent='未保存の追跡要求';});

$('tracking-mapping').onchange=()=>{refreshTrackingSources(trackingJobs);$('dirty').textContent='未保存の追跡写像';};
for(const id of ['tracking-scale','tracking-previous-refinements','tracking-current-refinements'])$(id).addEventListener('input',()=>{$('dirty').textContent='未保存の追跡写像';});
