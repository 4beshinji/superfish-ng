'use strict';
const $=id=>document.getElementById(id);
const token=location.hash.slice(1)||sessionStorage.getItem('ng-session');
if(token)sessionStorage.setItem('ng-session',token);
history.replaceState(null,'',location.pathname+location.search);
let project=null,selected=null,result=null,unit='mm',request=0,imageURL=null,imageBlob=null;
async function api(action,data={},binary=false){
 const response=await fetch('/api',{method:'POST',headers:{'Content-Type':'application/json','X-NG-Token':token},body:JSON.stringify({action,...data})});
 if(!response.ok){const error=await response.json();throw Error(error.error||response.statusText);}
 return binary?response.blob():response.json();
}
function failure(error){$('error').hidden=false;$('error').textContent=error.message;}
function run(fn){return async()=>{try{$('error').hidden=true;await fn();}catch(error){failure(error);}};}
function download(blob,name){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function numeric(id){const value=$(id).value;if(!value.trim()||!Number.isFinite(Number(value)))throw Error(`${id}: 有限の数値を入力してください`);return Number(value);}
function isCylinder(c){return c.format==='superfish_ng_coaxial_case';}
function isAxis(c){return c.format==='superfish_ng_axis_hphi_case';}
function accelerationInputs(){for(const id of ['axis-start','axis-end','axis-origin','axis-beta'])$(id).disabled=!$('acceleration-enabled').checked;}
function rqText(q){return q.r_over_q_accelerator_ohm===null?'N/A / N/A':`${q.r_over_q_accelerator_ohm.toPrecision(5)} / ${q.r_over_q_circuit_ohm.toPrecision(5)} Ω`;}
function documentFromForm(){
 const p=structuredClone(project),c=p.case;c.name=$('name').value;c.modes=numeric('modes');
 const fem=isCylinder(c)?c.mesh:c.fem;fem.element_order=numeric('order');if(!isAxis(c))fem.quadrature_order=numeric('quadrature');
 if(isAxis(c)){const scale=unit==='mm'?1000:1;c.acceleration=$('acceleration-enabled').checked?{path:'axis',z_start_m:numeric('axis-start')/scale,z_end_m:numeric('axis-end')/scale,phase_origin_m:numeric('axis-origin')/scale,beta:numeric('axis-beta')}:null;}
 c.rf.stored_energy_j=numeric('energy');c.rf.conductivity_s_per_m=numeric('conductivity');
 if(isCylinder(c)){const scale=unit==='mm'?1000:1;c.geometry.inner_radius_m=numeric('inner-radius')/scale;c.geometry.outer_radius_m=numeric('outer-radius')/scale;c.geometry.length_m=numeric('length')/scale;c.mesh.nr=numeric('nr');c.mesh.nz=numeric('nz');}
 p.display_length_unit=$('unit').value;return p;
}
function loadProject(p){
 project=structuredClone(p);const c=p.case;unit=p.display_length_unit;$('unit').value=unit;
 $('name').value=c.name;$('modes').value=c.modes;$('energy').value=c.rf.stored_energy_j;$('conductivity').value=c.rf.conductivity_s_per_m;
 const cylinder=isCylinder(c),fem=cylinder?c.mesh:c.fem;$('order').value=fem.element_order;$('quadrature').value=fem.quadrature_order??'';
 $('quadrature-row').hidden=isAxis(c);$('axis-acceleration').hidden=!isAxis(c);
 if(isAxis(c)){const scale=unit==='mm'?1000:1,z=c.mesh.outer_rz_m.filter(p=>p[0]===0).map(p=>p[1]);const a=c.acceleration??{z_start_m:Math.min(...z),z_end_m:Math.max(...z),phase_origin_m:0,beta:1};$('acceleration-enabled').checked=c.acceleration!==null;$('axis-start').value=a.z_start_m*scale;$('axis-end').value=a.z_end_m*scale;$('axis-origin').value=a.phase_origin_m*scale;$('axis-beta').value=a.beta;accelerationInputs();}
 $('spectrum-note').textContent=(isAxis(c)?'真空軸の正則な場を使い、零モードを除外せず正周波数を小さい順に計算します。':'静的な循環磁場を除き、正周波数を小さい順に計算します。')+'同じ順位は同一モードの追跡IDではありません。';
 $('cylinder').hidden=!cylinder;$('explicit-note').hidden=cylinder;
 if(cylinder){const scale=unit==='mm'?1000:1;$('inner-radius').value=c.geometry.inner_radius_m*scale;$('outer-radius').value=c.geometry.outer_radius_m*scale;$('length').value=c.geometry.length_m*scale;$('nr').value=c.mesh.nr;$('nz').value=c.mesh.nz;}
 else $('explicit-note').textContent=`明示した一般断面：${c.mesh.points_rz_m.length}節点、${c.mesh.triangles.length}三角形、${c.mesh.holes_rz_m.length}個の穴。形状はProject JSONで保持しています。`;
 document.querySelectorAll('.length-unit').forEach(el=>el.textContent=unit);$('document').value=JSON.stringify(p,null,2);$('dirty').textContent='入力を復元済み';
}
function fresh(){return {format:'superfish_ng_hphi_project',project_version:1,display_length_unit:'mm',case:{format:'superfish_ng_coaxial_case',schema_version:1,name:'閉同軸円筒',model:{physics:'rf_eigenmode',coordinates:'axisymmetric',azimuthal_index:0,field_family:'Hphi',material:'vacuum',boundary:'closed_pec'},geometry:{type:'coaxial_cylinder',inner_radius_m:.025,outer_radius_m:.05,length_m:.18},mesh:{nr:8,nz:24,element_order:2,quadrature_order:8},modes:4,rf:{stored_energy_j:1,conductivity_s_per_m:5.8e7}}};}
function clearImage(){request++;if(imageURL)URL.revokeObjectURL(imageURL);imageURL=null;imageBlob=null;$('image').hidden=true;$('save-image').disabled=true;}
function showQuantities(){
 if(!result)return;const q=result.modes[Number($('mode').value)-1];
 $('quantities').textContent=`f = ${(q.frequency_hz/1e6).toFixed(6)} MHz / U = ${q.stored_energy_j.toPrecision(6)} J / 全壁損失 P = ${q.wall_loss_w.toPrecision(6)} W / Q0 = ${q.q0.toPrecision(6)} / G = ${q.geometry_factor_ohm.toPrecision(6)} Ω`;
 if(q.vacc_v!==null)$('na').textContent=`R/Q（加速器 / 回路）= ${rqText(q)} / Vacc（実部, 虚部）= (${q.vacc_v.real.toPrecision(6)}, ${q.vacc_v.imag.toPrecision(6)}) V / Eacc = ${q.eacc_v_per_m.toPrecision(6)} V/m`;
 else $('na').textContent=isAxis(result.case)?'R/Q（加速器定義・回路定義）・加速電圧：N/A。加速経路を宣言していません。':'R/Q（加速器定義・回路定義）・加速電圧：N/A。軸は真空領域外で、加速経路を宣言していません。';
 const labels={inner_conductor:'内導体',outer_conductor:'外導体',z_min_end_plate:'z下端板',z_max_end_plate:'z上端板'};
 const walls=q.wall_h2_integral_a2_by_component?q.wall_h2_integral_a2_by_component.map((v,i)=>[i?`穴 ${i}`:'外周',v]):Object.entries(q.wall_h2_integral_a2_by_surface).map(([k,v])=>[labels[k]||k,v]);
 $('walls').textContent='各境界の壁損失 [W]\n'+walls.map(([name,v])=>`${name}: ${(q.surface_resistance_ohm*v/2).toPrecision(6)}`).join('\n');
 $('wall-segments').hidden=!q.wall_h2_integral_a2_by_segment;
 if(q.wall_h2_integral_a2_by_segment){let offset=0;const lines=[];for(const [component,contour] of [result.case.mesh.outer_rz_m,...result.case.mesh.holes_rz_m].entries()){for(let edge=0;edge<contour.length;edge++)lines.push(`${component?'穴 '+component:'外周'} / 線分 ${edge+1}${contour[edge][0]===0&&contour[(edge+1)%contour.length][0]===0?'（真空軸）':''}: ${(q.surface_resistance_ohm*q.wall_h2_integral_a2_by_segment[offset++]/2).toPrecision(6)}`);}$('segment-losses').textContent=lines.join('\n');}
}
async function openResult(id){
 const sequence=++request,data=await api('hphi-result',{id});if(sequence!==request)return;
 selected=id;result=data.result;loadProject(data.project);clearImage();$('result').hidden=false;$('selection').textContent=`${result.case.name} / ${id}`;
 $('mode').replaceChildren();result.modes.forEach((q,i)=>{const option=document.createElement('option');option.value=i+1;option.textContent=`${i+1}: ${(q.frequency_hz/1e6).toFixed(6)} MHz`;$('mode').append(option);});showQuantities();
 $('files').replaceChildren();for(const file of data.files){const button=document.createElement('button');button.textContent=file;button.onclick=run(async()=>download(await api('hphi-download',{id,file},true),file));$('files').append(button);}
 history.replaceState(null,'',`/hphi.html?job=${encodeURIComponent(id)}`);
}
async function refresh(){
 const jobs=(await api('jobs')).filter(job=>['hphi_solve','hphi_study'].includes(job.kind)),signature=JSON.stringify(jobs);
 if($('jobs').dataset.signature===signature)return;$('jobs').dataset.signature=signature;$('jobs').replaceChildren();
 if(!jobs.length)$('jobs').textContent='Hφの計算はまだありません。';
 for(const job of jobs){const row=document.createElement('div');row.className='job';row.dataset.job=job.id;
 const label=document.createElement('strong');label.textContent=`${job.status}${job.kind==='hphi_study'?' / 独立掃引':''} / ${job.id}`;row.append(label);
 const details=document.createElement('small');details.textContent=job.error||job.stage||'';row.append(details);
 const button=document.createElement('button'),active=['queued','running'].includes(job.status);button.textContent=active?'中止':'結果を開く';button.disabled=!active&&job.status!=='complete';
 button.onclick=run(async()=>{if(active){await api('cancel',{id:job.id});await refresh();}else if(job.kind==='hphi_study')await openStudy(job.id);else await openResult(job.id);});row.append(button);$('jobs').append(row);}
}
$('new').onclick=run(async()=>loadProject(await api('hphi-normalize',{document:fresh()})));
$('open').onchange=run(async()=>{const file=$('open').files[0];if(file)loadProject(await api('hphi-normalize',{document:await file.text()}));});
$('save').onclick=run(async()=>{const p=await api('hphi-normalize',{document:documentFromForm()});loadProject(p);download(new Blob([JSON.stringify(p,null,2)+'\n'],{type:'application/json'}),'hphi-project.json');$('dirty').textContent='保存済み';});
$('apply').onclick=run(async()=>loadProject(await api('hphi-normalize',{document:$('document').value})));
$('start').onclick=run(async()=>{const data=await api('hphi-start',{document:documentFromForm()});$('dirty').textContent=`投入済み: ${data.id}`;await refresh();});
$('import').onclick=run(async()=>{const data=await api('hphi-import',{path:$('import-path').value});await refresh();await openResult(data.id);});
$('unit').onchange=run(async()=>{loadProject(await api('hphi-normalize',{document:documentFromForm()}));clearImage();});
$('mode').onchange=()=>{clearImage();showQuantities();};$('mesh').onchange=clearImage;
$('plot').onclick=run(async()=>{if(!selected)throw Error('結果を選択してください');const sequence=++request,id=selected,mode=Number($('mode').value),blob=await api('hphi-plot',{id,mode,mesh:$('mesh').checked,length_unit:$('unit').value},true);if(sequence!==request||id!==selected)return;if(imageURL)URL.revokeObjectURL(imageURL);imageBlob=blob;imageURL=URL.createObjectURL(blob);$('image').src=imageURL;$('image').hidden=false;$('save-image').disabled=false;});
$('save-image').onclick=()=>{if(imageBlob)download(imageBlob,'hphi-fields.png');};
for(const [id,action,name] of [['probe','hphi-probe','hphi-probe.csv'],['probe-meta','hphi-probe-metadata','hphi-probe.csv.json']])$(id).onclick=run(async()=>{if(!selected)throw Error('結果を選択してください');const points_rz_m=JSON.parse($('points').value),data=await api(action,{id:selected,mode:Number($('mode').value),points_rz_m},id==='probe');download(id==='probe'?data:new Blob([JSON.stringify(data,null,2)+'\n'],{type:'application/json'}),name);});
$('acceleration-enabled').onchange=()=>{accelerationInputs();$('dirty').textContent='未保存の入力';};
for(const id of ['axis-start','axis-end','axis-origin','axis-beta','name','inner-radius','outer-radius','length','nr','nz','order','quadrature','modes','energy','conductivity'])$(id).addEventListener('input',()=>{$('dirty').textContent='未保存の入力';});
let selectedStudy=null,currentStudy=null;
function studyFromForm(){return {format:'superfish_ng_hphi_study',study_version:1,kind:'sweep',project:documentFromForm(),parameter:$('study-parameter').value,values:JSON.parse($('study-values').value)};}
function loadStudy(study){loadProject(study.project);$('study-parameter').value=study.parameter;$('study-values').value=JSON.stringify(study.values);}
async function openStudy(id){
 const data=await api('hphi-study-result',{id});history.replaceState(null,'',`/hphi.html?study=${encodeURIComponent(id)}`);selectedStudy=id;currentStudy=data;loadStudy(data.study);$('study-result').hidden=false;$('study-selection').textContent=`${data.study.parameter} / ${id}`;$('study-points').replaceChildren();
 for(const point of data.result.points){const section=document.createElement('div');section.className='job';const title=document.createElement('strong');title.textContent=`点 ${point.index+1}: ${point.value}`;section.append(title);
 const table=document.createElement('table'),head=document.createElement('tr');for(const label of ['順位','f [MHz]','U [J]','P [W]','Q0','G [Ω]','R/Q（加速器/回路）']){const th=document.createElement('th');th.textContent=label;head.append(th);}table.append(head);
 point.modes.forEach((q,index)=>{const row=document.createElement('tr');for(const value of [index+1,(q.frequency_hz/1e6).toFixed(6),q.stored_energy_j.toPrecision(5),q.wall_loss_w.toPrecision(5),q.q0.toPrecision(5),q.geometry_factor_ohm.toPrecision(5),rqText(q)]){const td=document.createElement('td');td.textContent=value;row.append(td);}table.append(row);});section.append(table);
 const button=document.createElement('button');button.textContent='結果を取り込む';button.dataset.point=point.index;button.onclick=run(async()=>{const imported=await api('hphi-study-point',{id,index:point.index});await refresh();await openResult(imported.id);});section.append(button);$('study-points').append(section);}
}
$('study-start').onclick=run(async()=>{const data=await api('hphi-start-study',{document:studyFromForm()});$('dirty').textContent=`掃引投入済み: ${data.id}`;await refresh();});
$('study-save').onclick=run(async()=>{const study=await api('hphi-normalize-study',{document:studyFromForm()});loadStudy(study);download(new Blob([JSON.stringify(study,null,2)+'\n'],{type:'application/json'}),'hphi-study.json');});
$('study-open').onchange=run(async()=>{const file=$('study-open').files[0];if(file)loadStudy(await api('hphi-normalize-study',{document:await file.text()}));});

for(const id of ["study-parameter","study-values"])$(id).addEventListener("input",()=>{$("dirty").textContent="未保存のStudy編集";});

$('study-result-save').onclick=run(async()=>{if(!currentStudy)throw Error('掃引結果を選択してください');download(new Blob([JSON.stringify(currentStudy.result,null,2)+'\n'],{type:'application/json'}),'hphi-study-results.json');});
run(async()=>{loadProject(await api('hphi-normalize',{document:fresh()}));await refresh();const parameters=new URLSearchParams(location.search),id=parameters.get('job'),studyId=parameters.get('study');if(studyId)await openStudy(studyId);else if(id)await openResult(id);})();// Explicit operations retain errors; background refresh does not clear them.
setInterval(()=>refresh().catch(failure),2000);
