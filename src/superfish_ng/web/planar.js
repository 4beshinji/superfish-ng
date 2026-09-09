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
 const jobs=await api('jobs');if(jobs.find(job=>job.id===id)?.kind==='planar_study')return openStudy(id);
 const sequence=++request;const data=await api('planar-result',{id});if(sequence!==request)return;
 selected=id;result=data.result;loadProject(data.project);clearImage();$('result').hidden=false;$('selection').textContent=`${result.case.name} / ${id}`;
 $('mode').replaceChildren();result.modes.forEach((q,i)=>{const option=document.createElement('option');option.value=i+1;option.textContent=`${i+1}: ${(q.frequency_hz/1e6).toFixed(6)} MHz`;$('mode').append(option);});showQuantities();
 $('files').replaceChildren();for(const file of data.files){const button=document.createElement('button');button.textContent=file;button.onclick=run(async()=>download(await api('planar-download',{id,file},true),file));$('files').append(button);}
}
async function refresh(){
 const jobs=(await api('jobs')).filter(job=>['planar_solve','planar_study'].includes(job.kind));
 // Preserve focused controls when only an unrelated state changes.
 const signature=JSON.stringify(jobs);if($('jobs').dataset.signature===signature)return;$('jobs').dataset.signature=signature;
 $('jobs').replaceChildren();if(!jobs.length)$('jobs').textContent='平面RFの計算はまだありません。';
 for(const job of jobs){const row=document.createElement('div');row.className='job';row.dataset.job=job.id;
 const label=document.createElement('strong');label.textContent=`${job.status}${job.kind==='planar_study'?' / 独立掃引':''} / ${job.id}`;row.append(label);
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
