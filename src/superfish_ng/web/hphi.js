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
function isCurved(c){return c.format==='superfish_ng_curved_hphi_case';}
function isMaterial(c){return c.format==='superfish_ng_material_hphi_case';}
function explicitMesh(c){return isCurved(c)?c.geometry.base_mesh:isMaterial(c)?c.partition.mesh:c.mesh;}
function isAxis(c){return c.format==='superfish_ng_axis_hphi_case'||(isCurved(c)||isMaterial(c))&&explicitMesh(c).format==='superfish_ng_axis_connected_mesh';}
function accelerationInputs(){for(const id of ['axis-start','axis-end','axis-origin','axis-beta'])$(id).disabled=!$('acceleration-enabled').checked;}
function rqText(q){return q.r_over_q_accelerator_ohm===null?'N/A / N/A':`${q.r_over_q_accelerator_ohm.toPrecision(5)} / ${q.r_over_q_circuit_ohm.toPrecision(5)} Ω`;}
function documentFromForm(){
 const p=structuredClone(project),c=p.case;c.name=$('name').value;c.modes=numeric('modes');
 const fem=isCylinder(c)?c.mesh:c.fem;fem.element_order=numeric('order');if(!isAxis(c)||isCurved(c)||isMaterial(c))fem.quadrature_order=numeric('quadrature');
 if(isAxis(c)){const scale=unit==='mm'?1000:1;c.acceleration=$('acceleration-enabled').checked?{path:'axis',z_start_m:numeric('axis-start')/scale,z_end_m:numeric('axis-end')/scale,phase_origin_m:numeric('axis-origin')/scale,beta:numeric('axis-beta')}:null;}
 c.rf.stored_energy_j=numeric('energy');c.rf.conductivity_s_per_m=numeric('conductivity');
 if(isCylinder(c)){const scale=unit==='mm'?1000:1;c.geometry.inner_radius_m=numeric('inner-radius')/scale;c.geometry.outer_radius_m=numeric('outer-radius')/scale;c.geometry.length_m=numeric('length')/scale;c.mesh.nr=numeric('nr');c.mesh.nz=numeric('nz');}
 p.display_length_unit=$('unit').value;return p;
}
function loadProject(p){
 project=structuredClone(p);const c=p.case;unit=p.display_length_unit;$('unit').value=unit;
 $('name').value=c.name;$('modes').value=c.modes;$('energy').value=c.rf.stored_energy_j;$('conductivity').value=c.rf.conductivity_s_per_m;
 const cylinder=isCylinder(c),fem=cylinder?c.mesh:c.fem;$('order').value=fem.element_order;$('quadrature').value=fem.quadrature_order??'';
 $('quadrature-row').hidden=isAxis(c)&&!isCurved(c)&&!isMaterial(c);$('axis-acceleration').hidden=!isAxis(c);
 if(isAxis(c)){const scale=unit==='mm'?1000:1,z=explicitMesh(c).outer_rz_m.filter(p=>p[0]===0).map(p=>p[1]);const a=c.acceleration??{z_start_m:Math.min(...z),z_end_m:Math.max(...z),phase_origin_m:0,beta:1};$('acceleration-enabled').checked=c.acceleration!==null;$('axis-start').value=a.z_start_m*scale;$('axis-end').value=a.z_end_m*scale;$('axis-origin').value=a.phase_origin_m*scale;$('axis-beta').value=a.beta;accelerationInputs();}
 $('spectrum-note').textContent=(isAxis(c)?(isMaterial(c)?'対称軸':'真空軸')+'の正則な場を使い、零モードを除外せず正周波数を小さい順に計算します。':'静的な循環磁場を除き、正周波数を小さい順に計算します。')+'同じ順位は同一モードの追跡IDではありません。';
 $('cylinder').hidden=!cylinder;$('explicit-note').hidden=cylinder;
 if(cylinder){const scale=unit==='mm'?1000:1;$('inner-radius').value=c.geometry.inner_radius_m*scale;$('outer-radius').value=c.geometry.outer_radius_m*scale;$('length').value=c.geometry.length_m*scale;$('nr').value=c.mesh.nr;$('nz').value=c.mesh.nz;}
 else {const m=explicitMesh(c);$('explicit-note').textContent=isCurved(c)?`明示した二次曲線：${m.points_rz_m.length}頂点、${c.geometry.edge_midpoints_rz_m.length}辺中点、${m.triangles.length}曲線三角形、${m.holes_rz_m.length}個の穴。形状はProject JSONで保持しています。独立掃引を利用できます。曲線の細分差診断と追跡は未対応です。`:`明示した一般断面：${m.points_rz_m.length}節点、${m.triangles.length}三角形、${m.holes_rz_m.length}個の穴。形状はProject JSONで保持しています。`;}
 $('material-input').hidden=!isMaterial(c);if(isMaterial(c)){const materials=new Map(c.partition.materials.map(m=>[m.id,m]));$('material-input').textContent='無損失・等方・区分一定材料（Project JSONで保持）\n'+c.partition.regions.map(r=>{const m=materials.get(r.material);return `${r.id} / 材料 ${m.id}: εr=${m.epsilon_r}, μr=${m.mu_r}, ${r.cell_indices.length}セル`;}).join('\n')+'\n軸加速経路はεr=μr=1の真空区間だけ指定できます。壁は非磁性金属です。';}
 document.querySelectorAll('.length-unit').forEach(el=>el.textContent=unit);$('document').value=JSON.stringify(p,null,2);$('dirty').textContent='入力を復元済み';
}
function fresh(){return {format:'superfish_ng_hphi_project',project_version:1,display_length_unit:'mm',case:{format:'superfish_ng_coaxial_case',schema_version:1,name:'閉同軸円筒',model:{physics:'rf_eigenmode',coordinates:'axisymmetric',azimuthal_index:0,field_family:'Hphi',material:'vacuum',boundary:'closed_pec'},geometry:{type:'coaxial_cylinder',inner_radius_m:.025,outer_radius_m:.05,length_m:.18},mesh:{nr:8,nz:24,element_order:2,quadrature_order:8},modes:4,rf:{stored_energy_j:1,conductivity_s_per_m:5.8e7}}};}
function clearImage(){request++;if(imageURL)URL.revokeObjectURL(imageURL);imageURL=null;imageBlob=null;$('image').hidden=true;$('save-image').disabled=true;}
function showQuantities(){
 if(!result)return;$('curved-display-note').hidden=!isCurved(result.case);const q=result.modes[Number($('mode').value)-1];
 $('material-result').hidden=!isMaterial(result.case);if(isMaterial(result.case))$('material-result').textContent='領域別エネルギー・隣接PEC壁損失\n'+q.regions.map(r=>`${r.id} / ${r.material}: Ue=${r.electric_energy_j.toPrecision(6)} J, Um=${r.magnetic_energy_j.toPrecision(6)} J, 壁P=${r.adjacent_wall_loss_w.toPrecision(6)} W`).join('\n')+'\nB=μ0 μr H（元セルの片側値）。壁金属のμr=1、体積損失=0。';
 $('quantities').textContent=`f = ${(q.frequency_hz/1e6).toFixed(6)} MHz / U = ${q.stored_energy_j.toPrecision(6)} J / 全壁損失 P = ${q.wall_loss_w.toPrecision(6)} W / Q0 = ${q.q0.toPrecision(6)} / G = ${q.geometry_factor_ohm.toPrecision(6)} Ω`;
 if(q.vacc_v!==null)$('na').textContent=`R/Q（加速器 / 回路）= ${rqText(q)} / Vacc（実部, 虚部）= (${q.vacc_v.real.toPrecision(6)}, ${q.vacc_v.imag.toPrecision(6)}) V / Eacc = ${q.eacc_v_per_m.toPrecision(6)} V/m`;
 else $('na').textContent=isAxis(result.case)?'R/Q（加速器定義・回路定義）・加速電圧：N/A。加速経路を宣言していません。':'R/Q（加速器定義・回路定義）・加速電圧：N/A。軸は真空領域外で、加速経路を宣言していません。';
 const labels={inner_conductor:'内導体',outer_conductor:'外導体',z_min_end_plate:'z下端板',z_max_end_plate:'z上端板'};
 const walls=q.wall_h2_integral_a2_by_component?q.wall_h2_integral_a2_by_component.map((v,i)=>[i?`穴 ${i}`:'外周',v]):Object.entries(q.wall_h2_integral_a2_by_surface).map(([k,v])=>[labels[k]||k,v]);
 $('walls').textContent='各境界の壁損失 [W]\n'+walls.map(([name,v])=>`${name}: ${(q.surface_resistance_ohm*v/2).toPrecision(6)}`).join('\n');
 $('wall-segments').hidden=!q.wall_h2_integral_a2_by_segment;
 if(q.wall_h2_integral_a2_by_segment){let offset=0;const lines=[];for(const [component,contour] of [explicitMesh(result.case).outer_rz_m,...explicitMesh(result.case).holes_rz_m].entries()){for(let edge=0;edge<contour.length;edge++)lines.push(`${component?'穴 '+component:'外周'} / ${isCurved(result.case)?'区間':'線分'} ${edge+1}${contour[edge][0]===0&&contour[(edge+1)%contour.length][0]===0?(isMaterial(result.case)?'（対称軸）':'（真空軸）'):''}: ${(q.surface_resistance_ohm*q.wall_h2_integral_a2_by_segment[offset++]/2).toPrecision(6)}`);}$('segment-losses').textContent=lines.join('\n');}
}
async function openResult(id){
 const sequence=++request,data=await api('hphi-result',{id});if(sequence!==request)return;
 selected=id;result=data.result;loadProject(data.project);clearImage();$('result').hidden=false;$('selection').textContent=`${result.case.name} / ${id}`;
 $('mode').replaceChildren();result.modes.forEach((q,i)=>{const option=document.createElement('option');option.value=i+1;option.textContent=`${i+1}: ${(q.frequency_hz/1e6).toFixed(6)} MHz`;$('mode').append(option);});showQuantities();
 $('files').replaceChildren();for(const file of data.files){const button=document.createElement('button');button.textContent=file;button.onclick=run(async()=>download(await api('hphi-download',{id,file},true),file));$('files').append(button);}
 history.replaceState(null,'',`/hphi.html?job=${encodeURIComponent(id)}`);
}
async function refresh(){
 const jobs=(await api('jobs')).filter(job=>['hphi_solve','hphi_study','hphi_convergence','hphi_tracking','hphi_tracking_history','hphi_tune'].includes(job.kind)),signature=JSON.stringify(jobs);
 trackingCandidates(jobs);historyCandidates(jobs);if($('jobs').dataset.signature===signature)return;$('jobs').dataset.signature=signature;$('jobs').replaceChildren();
 if(!jobs.length)$('jobs').textContent='Hφの計算はまだありません。';
 for(const job of jobs){const row=document.createElement('div');row.className='job';row.dataset.job=job.id;
 const label=document.createElement('strong');label.textContent=`${job.status}${job.kind==='hphi_tune'?' / 周波数調整':job.kind==='hphi_study'?' / 独立掃引':job.kind==='hphi_convergence'?' / 細分差診断':job.kind==='hphi_tracking_history'?' / 追跡履歴':job.kind==='hphi_tracking'?' / 部分空間対応':''} / ${job.id}`;row.append(label);
 const details=document.createElement('small');details.textContent=job.error||job.stage||'';row.append(details);
 const button=document.createElement('button'),active=['queued','running'].includes(job.status);button.textContent=active?'中止':'結果を開く';button.disabled=!active&&job.status!=='complete';
 button.onclick=run(async()=>{if(active){await api('cancel',{id:job.id});await refresh();}else if(job.kind==='hphi_tune')await openHphiTune(job.id);else if(job.kind==='hphi_study')await openStudy(job.id);else if(job.kind==='hphi_convergence')await openConvergence(job.id);else if(job.kind==='hphi_tracking_history')await openHphiHistory(job.id);else if(job.kind==='hphi_tracking')await openTracking(job.id);else await openResult(job.id);});row.append(button);
 if(job.kind==='hphi_tune'&&!active){const checkpoints=document.createElement('button');checkpoints.textContent='保存地点を選ぶ';checkpoints.dataset.hphiTuneCheckpoints=job.id;checkpoints.onclick=run(async()=>{const data=await api('hphi-tune-checkpoints',{id:job.id});let list=row.querySelector('.hphi-tune-checkpoints');if(!list){list=document.createElement('div');list.className='hphi-tune-checkpoints';row.append(list);}list.replaceChildren();if(!data.indices.length)list.textContent='完了した保存地点はありません。';for(const index of data.indices){const open=document.createElement('button');open.textContent=`試行 ${index} までを再検証`;open.dataset.hphiTuneCheckpoint=index;open.onclick=run(async()=>showHphiTune(await api('hphi-open-tune-checkpoint',{id:job.id,index}),`${job.id} / 試行 ${index}`));list.append(open);}});row.append(checkpoints);}
 $('jobs').append(row);}
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
let convergenceRequest=null,currentConvergence=null;
const convergenceThresholdLabels={frequency_relative:'周波数の相対差',electric_field_relative:'電場L2の相対差',magnetic_field_relative:'磁場L2の相対差',rf_relative:'各RF量・壁線分の相対差',axis_voltage_relative:'複素加速電圧の相対差',spectral_gap_relative:'近傍周波数との最小相対間隔',minimum_overlap:'E/H対応の最小内積',overlap_margin:'他モードに対する内積の差'};
for(const [key,title] of Object.entries(convergenceThresholdLabels)){const label=document.createElement('label');label.textContent=title;const input=document.createElement('input');input.type='number';input.step='any';input.id='convergence-'+key;input.disabled=true;input.oninput=()=>{$('convergence-dirty').textContent='未保存の診断条件';};label.append(input);$('convergence-thresholds').append(label);}
function loadConvergence(request){
 convergenceRequest=structuredClone(request);$('convergence-document').value=JSON.stringify(request,null,2);$('convergence-ranks').value=JSON.stringify(request.mode_ranks);$('convergence-ranks').disabled=false;
 for(const key of Object.keys(convergenceThresholdLabels)){const input=$('convergence-'+key);input.value=request.thresholds[key];input.disabled=false;}
 $('convergence-preview').textContent=`${request.projects.length}水準 / 各水準${request.projects[0].case.modes}モード / 形状・規格化・導電率・加速経路を固定`;
 $('convergence-save').disabled=false;$('convergence-start').disabled=false;$('convergence-dirty').textContent='';
}
function convergenceFromForm(){
 if(!convergenceRequest)throw Error('診断要求を開いてください');const request=structuredClone(convergenceRequest);request.mode_ranks=JSON.parse($('convergence-ranks').value);
 for(const key of Object.keys(convergenceThresholdLabels))request.thresholds[key]=numeric('convergence-'+key);return request;
}
const convergenceQuantityLabels={frequency_relative:'周波数',electric_field_relative:'電場L2',magnetic_field_relative:'磁場L2',axis_voltage_relative:'複素Vacc','rf/stored_energy_j':'全蓄積エネルギー','rf/electric_energy_j':'電気エネルギー','rf/magnetic_energy_j':'磁気エネルギー','rf/wall_loss_w':'全壁損失','rf/surface_resistance_ohm':'表面抵抗','rf/q0':'Q0','rf/geometry_factor_ohm':'G','rf/r_over_q_accelerator_ohm':'R/Q 加速器定義','rf/r_over_q_circuit_ohm':'R/Q 回路定義'};
const convergenceReasons={'upper spectral neighbor was not computed':'上側の近傍モードが未計算','spectral separation is unresolved or near-degenerate':'近傍モードとの分離を確認できません','same-rank electric overlap is not uniquely dominant':'同順位の電場対応が一意ではありません','same-rank magnetic overlap is not uniquely dominant':'同順位の磁場対応が一意ではありません','electric and magnetic correspondence require different coefficient phases':'電場と磁場の対応で符号が一致しません'};
async function openConvergence(id){
 const data=await api('hphi-convergence-result',{id});currentConvergence=data;loadConvergence(data.request);history.replaceState(null,'',`/hphi.html?convergence=${encodeURIComponent(id)}`);
 $('convergence-result').hidden=false;let allowance=$('convergence-allowance');if(!allowance){allowance=document.createElement('p');allowance.id='convergence-allowance';$('convergence-status').after(allowance);}allowance.textContent='増加の検査には微小な差の許容幅があります（前の差×1e-8 または1e-12の大きい方）。';$('convergence-selection').textContent=id;$('convergence-status').textContent=`実行・保存: ${data.state.status} / 最後の3水準の差: ${data.result.status}`;$('convergence-decisions').replaceChildren();$('convergence-levels').replaceChildren();
 for(const decision of data.result.decisions){const section=document.createElement('div');section.className='job';const title=document.createElement('strong');title.textContent=`周波数順位 ${decision.mode_rank}: ${decision.status}`;section.append(title);
  const reasons=[...new Set(data.result.comparisons.slice(-2).flatMap(pair=>pair.modes.find(mode=>mode.mode_rank===decision.mode_rank).reasons))];if(reasons.length){const paragraph=document.createElement('p');paragraph.textContent=reasons.map(reason=>convergenceReasons[reason]||reason).join(' / ');section.append(paragraph);}
  const table=document.createElement('table'),head=document.createElement('tr');for(const text of ['量','一つ前の差','最後の差','しきい値','増加の検査','判定']){const th=document.createElement('th');th.textContent=text;head.append(th);}table.append(head);
  for(const [name,check] of Object.entries(decision.checks)){const row=document.createElement('tr');row.dataset.check=name;const label=convergenceQuantityLabels[name]||(name.startsWith('wall_segment/')?'壁線分 '+name.split('/')[1]:name);for(const text of [label,check.previous.toExponential(3),check.last.toExponential(3),check.threshold.toExponential(3),check.nonincreasing?'許容内':'増加',check.passed?'PASS':'UNVERIFIED']){const td=document.createElement('td');td.textContent=text;row.append(td);}table.append(row);}section.append(table);$('convergence-decisions').append(section);
 }
 data.request.projects.forEach((project,index)=>{const section=document.createElement('div');section.className='job';const caseData=project.case,cylinder=isCylinder(caseData),label=document.createElement('strong');const cells=cylinder?2*caseData.mesh.nr*caseData.mesh.nz:caseData.mesh.triangles.length;label.textContent=`水準 ${index+1}: P${(cylinder?caseData.mesh:caseData.fem).element_order} / ${cells}三角形`;section.append(label);
  const button=document.createElement('button');button.textContent='元の結果を取り込む';button.dataset.convergenceLevel=index;button.onclick=run(async()=>{const imported=await api('hphi-convergence-point',{id,index});await refresh();await openResult(imported.id);});section.append(button);$('convergence-levels').append(section);});
}
$('convergence-open').onchange=run(async()=>{const file=$('convergence-open').files[0];if(file)loadConvergence(await api('hphi-normalize-convergence',{document:await file.text()}));});
$('convergence-apply').onclick=run(async()=>loadConvergence(await api('hphi-normalize-convergence',{document:$('convergence-document').value})));
$('convergence-save').onclick=run(async()=>{const request=await api('hphi-normalize-convergence',{document:convergenceFromForm()});loadConvergence(request);download(new Blob([JSON.stringify(request,null,2)+'\n'],{type:'application/json'}),'hphi-convergence.json');$('convergence-dirty').textContent='診断要求を保存しました';});
$('convergence-start').onclick=run(async()=>{const request=convergenceFromForm(),data=await api('hphi-start-convergence',{document:request});$('convergence-dirty').textContent=`診断投入済み: ${data.id}`;await refresh();});
$('convergence-result-save').onclick=run(async()=>{if(!currentConvergence)throw Error('診断結果を選択してください');download(new Blob([JSON.stringify(currentConvergence.result,null,2)+'\n'],{type:'application/json'}),'hphi-convergence-results.json');});
$('convergence-ranks').oninput=()=>{$('convergence-dirty').textContent='未保存の診断条件';};

let trackingRequest=null,currentTracking=null;
const trackingControlLabels={minimum_overlap:'E/Hの最小主内積',minimum_assignment_margin:'他候補への割当余裕',relative_cluster_gap:'周波数を群にする相対間隔',minimum_relative_singular_value:'基底の最小相対特異値',minimum_cluster_link:'群の結合候補の内積',maximum_relative_projection_error:'比較空間への最大射影誤差',quadrature_order:'比較空間の積分次数',max_candidate_tests:'共通領域の探索予算',max_overlay_triangles:'共通三角形の上限',max_dofs:'各比較空間の自由度上限',max_gram_modes:'内積を計算するモード数の上限'};
for(const [key,title] of Object.entries(trackingControlLabels)){const label=document.createElement('label');label.textContent=title;const input=document.createElement('input');input.type='number';input.step=key.startsWith('max_')||key==='quadrature_order'?'1':'any';input.id='tracking-'+key;input.disabled=true;input.oninput=()=>{$('tracking-dirty').textContent='未保存の追跡条件';};label.append(input);$('tracking-controls').append(label);}
function trackingCandidates(jobs){
 const candidates=jobs.filter(j=>j.kind==='hphi_solve'&&j.status==='complete'&&!['superfish_ng_curved_hphi_case','superfish_ng_material_hphi_case'].includes(j.case_format)),signature=JSON.stringify(candidates.map(j=>j.id));
 for(const name of ['tracking-previous','tracking-current']){const select=$(name);if(select.dataset.signature===signature)continue;const selected=select.value;select.dataset.signature=signature;select.replaceChildren();const empty=document.createElement('option');empty.value='';empty.textContent='保存結果を選択';select.append(empty);for(const job of candidates){const option=document.createElement('option');option.value=job.id;option.textContent=`${job.id} / ${job.modes}モード`;select.append(option);}if(candidates.some(j=>j.id===selected))select.value=selected;}
}
function loadTracking(q){
 trackingRequest=structuredClone(q);$('tracking-document').value=JSON.stringify(q,null,2);
 $('tracking-previous-count').value=q.previous_mode_count;$('tracking-current-count').value=q.current_mode_count;$('tracking-ids').value=JSON.stringify(q.previous_mode_ids);$('tracking-groups').value=JSON.stringify(q.previous_identity_groups);
 for(const id of ['tracking-previous-count','tracking-current-count','tracking-ids','tracking-groups'])$(id).disabled=false;
 for(const key of Object.keys(trackingControlLabels)){const input=$('tracking-'+key);input.value=q.controls[key];input.disabled=false;}
 const a=q.previous_comparison_mesh,b=q.current_comparison_mesh;
 $('tracking-preview').textContent=`比較空間：前 P${q.previous_comparison_order} ${a.triangles.length}三角形 / 現在 P${q.current_comparison_order} ${b.triangles.length}三角形。両方ともSI座標・全穴を保持。`;
 $('tracking-save').disabled=false;$('tracking-start').disabled=false;$('tracking-dirty').textContent='';
}
function trackingFromForm(){
 if(!trackingRequest)throw Error('追跡要求を開いてください');const q=structuredClone(trackingRequest);
 q.previous_mode_count=numeric('tracking-previous-count');q.current_mode_count=numeric('tracking-current-count');q.previous_mode_ids=JSON.parse($('tracking-ids').value);q.previous_identity_groups=JSON.parse($('tracking-groups').value);
 for(const key of Object.keys(trackingControlLabels))q.controls[key]=numeric('tracking-'+key);return q;
}
const trackingReasonLabels={
 'finite spectral resolution group crosses the tracked band into its upper guard':'追跡帯域の群が上側のguardモードまで及んでいます',
 'previous tracked band or first upper guard has unresolved projection or inverse spectrum':'前の帯域またはguardの射影・有限区間が未検証です',
 'current tracked band or first upper guard has unresolved projection or inverse spectrum':'現在の帯域またはguardの射影・有限区間が未検証です',
 'electric subspace correspondence is incomplete or ambiguous':'電場の部分空間対応が不足または曖昧です',
 'magnetic subspace correspondence is incomplete or ambiguous':'磁場の部分空間対応が不足または曖昧です',
 'electric and magnetic subspace assignments differ':'電場と磁場の部分空間の割当が一致しません',
 'electric and magnetic modes require different coefficient phases':'電場と磁場で必要な係数の符号が一致しません',
 'original scalar field projection loss exceeds the declared limit':'射影で失う場が指定の上限を超えています',
 'shifted inverse residual does not give a finite upper frequency':'有限な上端周波数を確認できません',
 'comparison interval reaches the static constant-q circulation':'比較区間が静的な循環磁場まで及んでいます'};
function trackingTable(headers){const table=document.createElement('table'),head=document.createElement('tr');for(const title of headers){const th=document.createElement('th');th.textContent=title;head.append(th);}table.append(head);return table;}
function trackingRow(table,values){const row=document.createElement('tr');for(const value of values){const cell=document.createElement('td');cell.textContent=value;row.append(cell);}table.append(row);return row;}
async function openTracking(id){
 const data=await api('hphi-tracking-result',{id});currentTracking={id,...data};loadTracking(data.request);history.replaceState(null,'',`/hphi.html?tracking=${encodeURIComponent(id)}`);
 $('tracking-result').hidden=false;$('tracking-selection').textContent=id;const r=data.result;
 $('tracking-status').textContent=`実行・保存: ${data.state.status} / E/H部分空間対応: ${r.status} / 個別ID: ${r.individual_ids_complete?'全て対応済み':'未確定の順位あり'}`;
 $('tracking-current-ids').textContent='現在の周波数順位と個別ID：'+r.current_mode_ids.map((v,i)=>`${i+1}: ${v??'未確定'}`).join(' / ');
 $('tracking-reasons').textContent=r.verification_reasons.map(x=>trackingReasonLabels[x]||x).join(' / ');$('tracking-matches').replaceChildren();
 const heading=document.createElement('p');heading.textContent=r.status==='PASS'?'対応したモード・ID集合':'対応候補（未確定）';$('tracking-matches').append(heading);
 const table=trackingTable(['前の順位','現在の順位','ID / ID集合','対応','Eの最小主内積','Hの最小主内積','係数位相']);
 for(const match of r.matches){const row=trackingRow(table,[match.previous_indices.join(', '),match.current_indices.join(', '),match.previous_ids.join(', '),match.kind==='SUBSPACE'?'部分空間（個別IDは未定）':'個別モード',Math.min(...match.principal_overlaps).toPrecision(6),match.magnetic_principal_overlaps?Math.min(...match.magnetic_principal_overlaps).toPrecision(6):'未確定',r.status!=='PASS'?'未確定':match.previous_phase_multiplier===null?'集合のため未定義':String(match.previous_phase_multiplier)]);row.dataset.trackingDimension=match.dimension;}
 $('tracking-matches').append(table);$('tracking-resolution').replaceChildren();
 r.spectral_resolution.forEach((resolution,index)=>{const section=document.createElement('section'),title=document.createElement('h4');title.textContent=`${index?'現在':'前'} / P${resolution.comparison_order} / ${resolution.comparison_triangles}比較三角形`;
 const groups=document.createElement('p');groups.textContent='有限区間と周波数から作った群：'+r.spectral_resolution_groups[index].map(g=>'['+g.join(', ')+']').join(' ');section.append(title,groups);
 const table=trackingTable(['元の順位','元の周波数 [MHz]','比較区間 [MHz]','射影誤差','逆行列の相対残差','判定・理由']);
 resolution.modes.forEach((row,i)=>{const interval=resolution.nearby_comparison_frequency_intervals_hz[i];trackingRow(table,[row.mode_rank,(resolution.original_frequencies_hz[i]/1e6).toFixed(6),`${(interval[0]/1e6).toFixed(6)} ～ ${interval[1]===null?'上端未定':(interval[1]/1e6).toFixed(6)}`,resolution.projection.relative_mass_error[i].toExponential(3),resolution.relative_inverse_residual[i].toExponential(3),row.status+(row.reasons.length?' / '+row.reasons.map(x=>trackingReasonLabels[x]||x).join(' / '):'')]);});section.append(table);$('tracking-resolution').append(section);});
 $('tracking-sides').replaceChildren();for(const side of ['previous','current']){const p=data.projects[side],section=document.createElement('section'),title=document.createElement('h4');title.textContent=`${side==='previous'?'前':'現在'}：${p.case.name}`;const text=document.createElement('p');text.textContent=`${p.case.modes}モード / 表示 ${p.display_length_unit} / 元Project・元係数を保持`;
 const button=document.createElement('button');button.textContent='元の場を取り込む';button.dataset.trackingSide=side;button.onclick=run(async()=>{const imported=await api('hphi-tracking-side',{id,side});await refresh();await openResult(imported.id);});section.append(title,text,button);$('tracking-sides').append(section);
 const source=data.sources[side],selector=$('tracking-'+side);selector.value='';if(source.kind==='hphi_job'){const identifier=source.path.split('/').pop();if([...selector.options].some(o=>o.value===identifier))selector.value=identifier;}}
}
$('tracking-open').onchange=run(async()=>{const file=$('tracking-open').files[0];if(file)loadTracking(await api('hphi-normalize-tracking',{document:await file.text()}));});
$('tracking-apply').onclick=run(async()=>loadTracking(await api('hphi-normalize-tracking',{document:$('tracking-document').value})));
$('tracking-save').onclick=run(async()=>{const q=await api('hphi-normalize-tracking',{document:trackingFromForm()});loadTracking(q);download(new Blob([JSON.stringify(q,null,2)+'\n'],{type:'application/json'}),'hphi-tracking.json');$('tracking-dirty').textContent='追跡要求を保存しました';});
$('tracking-start').onclick=run(async()=>{const previous_id=$('tracking-previous').value,current_id=$('tracking-current').value;if(!previous_id||!current_id)throw Error('前と現在の保存場を選択してください');const reply=await api('hphi-start-tracking',{previous_id,current_id,document:trackingFromForm()});$('tracking-dirty').textContent=`追跡投入済み: ${reply.id}`;await refresh();});
$('tracking-repeat').onclick=run(async()=>{if(!currentTracking)throw Error('保存した対応結果を選択してください');const reply=await api('hphi-repeat-tracking',{id:currentTracking.id,document:trackingFromForm()});$('tracking-dirty').textContent=`保存した前後の場で再比較: ${reply.id}`;await refresh();});
$('tracking-result-save').onclick=run(async()=>{if(!currentTracking)throw Error('対応結果を選択してください');download(new Blob([JSON.stringify(currentTracking.result,null,2)+'\n'],{type:'application/json'}),'hphi-tracking-results.json');});
for(const id of ['tracking-previous-count','tracking-current-count','tracking-ids','tracking-groups'])$(id).oninput=()=>{$('tracking-dirty').textContent='未保存の追跡条件';};

let currentHphiHistory=null,historyPairJobs=[],hphiHistoryRequest=null;
function historyCandidates(jobs){
 historyPairJobs=jobs.filter(j=>j.kind==='hphi_tracking'&&j.status==='complete');const signature=JSON.stringify(historyPairJobs.map(j=>j.id));
 for(const name of ['history-pair','history-next']){const select=$(name);if(select.dataset.signature===signature)continue;const selected=select.value;select.dataset.signature=signature;select.replaceChildren();const empty=document.createElement('option');empty.value='';empty.textContent='保存した部分空間対応を選択';select.append(empty);for(const job of historyPairJobs){const option=document.createElement('option');option.value=job.id;option.textContent=job.id;select.append(option);}if(historyPairJobs.some(j=>j.id===selected))select.value=selected;}
}
function historyFromForm(){const q=hphiHistoryRequest?structuredClone(hphiHistoryRequest):{format:'superfish_ng_hphi_tracking_history_request',history_version:1};q.step_count=numeric('history-count');q.max_steps=numeric('history-max');return q;}
function loadHistoryRequest(q){hphiHistoryRequest=structuredClone(q);$('history-count').value=q.step_count;$('history-max').value=q.max_steps;$('history-note').textContent=`履歴の段階数と上限を復元済み / 明示ID回復 ${q.recoveries?.length||0}件`;}
async function openHphiHistory(id){
 const data=await api('hphi-history-result',{id});currentHphiHistory={id,...data};loadHistoryRequest(data.request);history.replaceState(null,'',`/hphi.html?history=${encodeURIComponent(id)}`);const r=data.result;
 $('history-result').hidden=false;$('history-selection').textContent=id;$('history-status').textContent=`実行・保存: ${data.state.status} / 最終E/H対応: ${r.status} / 個別ID: ${r.individual_ids_complete?'全て対応済み':'未確定の順位あり'}`;
 $('history-current-ids').textContent='現在の順位と個別ID：'+r.current_mode_ids.map((v,i)=>`${i+1}: ${v??'未確定'}`).join(' / ');
 $('history-stop').textContent=r.can_extend?'保存場・帯域・ID集合がつながる次の比較を追加できます。':r.status!=='PASS'?'最終の対応またはID回復がUNVERIFIEDのため延長できません。':'履歴の段階上限に達したため延長できません。';$('history-extend').disabled=!r.can_extend;$('history-next').disabled=!r.can_extend;
 const sourceIds=data.sources.steps.map(s=>s.path.split('/').pop()),available=sourceIds.every(id=>historyPairJobs.some(j=>j.id===id));$('history-step-ids').value=JSON.stringify(available?sourceIds:[]);
 if(!available)$('history-note').textContent='元の段階一覧に選択できない保存先があります。所有した履歴の表示・元場取込・延長は利用できます。';
 $('history-steps').replaceChildren();r.steps.forEach((step,index)=>{
  const section=document.createElement('section'),title=document.createElement('h4');title.textContent=`段階 ${index+1} / ${step.status} / ${step.individual_ids_complete?'個別IDを保持':'ID集合または未確定'}`;section.append(title);
  const reasons=document.createElement('p');reasons.textContent=step.verification_reasons.map(x=>trackingReasonLabels[x]||x).join(' / ');section.append(reasons);
  const recovery=r.identity_recoveries?.find(event=>event.after_step_index===index);if(recovery){const note=document.createElement('p');note.textContent=`明示ID回復: ${recovery.status} / anchor保存点 ${recovery.request.anchor_snapshot_index}（0始まり） / ${recovery.stop_reason||recovery.assessment.current_mode_ids.join(', ')}`;section.append(note);}
  const table=trackingTable(['前の順位','現在の順位','ID / ID集合','Eの最小主内積','Hの最小主内積','係数位相']);for(const match of step.matches)trackingRow(table,[match.previous_indices.join(', '),match.current_indices.join(', '),match.previous_ids.join(', '),Math.min(...match.principal_overlaps).toPrecision(6),match.magnetic_principal_overlaps?Math.min(...match.magnetic_principal_overlaps).toPrecision(6):'未確定',step.status!=='PASS'?'未確定':match.previous_phase_multiplier===null?'集合のため未定義':String(match.previous_phase_multiplier)]);section.append(table);
  for(const [name,value,label] of [['request',data.step_requests[index],'この段階の追跡要求を保存'],['result',step,'この段階の対応結果を保存']]){const button=document.createElement('button');button.textContent=label;button.dataset.historyDownload=`${index}-${name}`;button.onclick=()=>download(new Blob([JSON.stringify(value,null,2)+'\n'],{type:'application/json'}),`hphi-history-step-${index+1}-${name}.json`);section.append(button);}
  for(const side of ['previous','current']){const button=document.createElement('button');button.textContent=(side==='previous'?'前':'現在')+'の元場を取り込む';button.dataset.historySource=`${index}-${side}`;button.onclick=run(async()=>{const imported=await api('hphi-history-source',{id,index,side});await refresh();await openResult(imported.id);});section.append(button);}
  $('history-steps').append(section);
 });
}
$('history-add-pair').onclick=run(async()=>{const id=$('history-pair').value;if(!id)throw Error('段階に追加する保存済みの対応を選択してください');const ids=JSON.parse($('history-step-ids').value);if(!Array.isArray(ids))throw Error('段階一覧はIDの配列です');ids.push(id);$('history-step-ids').value=JSON.stringify(ids);$('history-count').value=ids.length;});
$('history-open').onchange=run(async()=>{const file=$('history-open').files[0];if(file)loadHistoryRequest(await api('hphi-normalize-history',{document:await file.text()}));});
$('history-save').onclick=run(async()=>{const q=await api('hphi-normalize-history',{document:historyFromForm()});loadHistoryRequest(q);download(new Blob([JSON.stringify(q,null,2)+'\n'],{type:'application/json'}),'hphi-history.json');});
$('history-start').onclick=run(async()=>{const reply=await api('hphi-start-history',{document:historyFromForm(),step_ids:JSON.parse($('history-step-ids').value)});$('history-note').textContent=`履歴を投入済み: ${reply.id}`;await refresh();});
$('history-extend').onclick=run(async()=>{if(!currentHphiHistory||!$('history-next').value)throw Error('保存した履歴と次の比較を選択してください');const reply=await api('hphi-extend-history',{id:currentHphiHistory.id,next_id:$('history-next').value});$('history-note').textContent=`新しい保存先へ延長: ${reply.id}`;await refresh();});
$('history-result-save').onclick=run(async()=>{if(!currentHphiHistory)throw Error('履歴を選択してください');download(new Blob([JSON.stringify(currentHphiHistory.result,null,2)+'\n'],{type:'application/json'}),'hphi-history-results.json');});

let currentHphiTune=null,hphiTuneInputVersion=0;
function hphiTuneLimit(){const value=$('hphi-tune-new-trials').value.trim();return value?numeric('hphi-tune-new-trials'):null;}
function hphiTuneRequestText(){const value=$('hphi-tune-document').value;if(!value.trim())throw Error('Hφ調整要求を開いてください');return value;}
function hphiTuneUnit(request){return request.project?.display_length_unit||'m';}
function hphiTuneParameterUnit(request){return request.mapping?.kind==='coaxial_dimensions'?'m':'dimensionless';}
function loadHphiTune(request){
 loadProject(request.project);$('hphi-tune-document').value=JSON.stringify(request,null,2);hphiTuneInputVersion++;
 const mesh=request.project.case.format==='superfish_ng_coaxial_case'?request.project.case.mesh:request.project.case.mesh||request.project.case.fem;
 const triangles=request.project.case.format==='superfish_ng_coaxial_case'?2*mesh.nr*mesh.nz:mesh.triangles.length;
 $('hphi-tune-preview').textContent=`${request.parameter} / 範囲 ${JSON.stringify(request.bounds)}（${hphiTuneParameterUnit(request)}） / 目標 ${(request.target_hz/1e6).toPrecision(8)} MHz / 対象ID ${request.mode_id} / 保存座標 SI [m]・Project表示 ${hphiTuneUnit(request)} / ${triangles}三角形`;
 $('hphi-tune-start').disabled=false;$('hphi-tune-dirty').textContent='';
}
function hphiTuneFrequency(value){return value===null?'未評価':Number(value).toPrecision(10);}
function hphiTuneRank(trial,target){const ids=Array.isArray(trial.current_mode_ids)?trial.current_mode_ids:[];const index=ids.indexOf(target);return index<0?'未確認':index+1;}
function hphiTuneReasons(trial){const reasons=trial.tracking?.verification_reasons||[];return reasons.length?reasons.join(' / '):'';}
function showHphiTune(data,label){
 currentHphiTune=data;const d=data.document;loadHphiTune(d.request);$('hphi-tune-result').hidden=false;$('hphi-tune-selection').textContent=label;$('hphi-tune-resume').disabled=!d.can_resume;
 const decision=d.decision,requestData=d.request;
 if(Object.hasOwn(decision,'mesh_difference_met'))$('hphi-tune-gates').textContent=`最終細分の目標ゲート: ${decision.refined_target_met?'PASS':'未達'}（許容 ${requestData.frequency_tolerance_hz} Hz） / 粗細差ゲート: ${decision.mesh_difference_met?'PASS':'未達'}（${decision.mesh_frequency_difference_hz.toPrecision(10)} Hz / 許容 ${requestData.mesh_frequency_tolerance_hz} Hz）`;
 else if(d.status==='PAUSED')$('hphi-tune-gates').textContent=`途中保存: 目標ゲート未確定 / 粗細差ゲート未実施。追加試行は保存地点から行います（許容 ${requestData.frequency_tolerance_hz} Hz、粗細差 ${requestData.mesh_frequency_tolerance_hz} Hz）。`;
 else $('hphi-tune-gates').textContent=`停止理由: ${decision.reason||d.status}。未確認値を目標達成として扱いません。`;
 $('hphi-tune-status').textContent=`実行状態: ${label.includes('/')?label.split('/')[0]:'保存結果'} / 調整状態: ${d.status} / 対象ID: ${requestData.mode_id} / parameter unit: ${d.parameter_unit||hphiTuneParameterUnit(requestData)} / frequency unit: ${d.frequency_unit||'Hz'}`;
 $('hphi-tune-trials').replaceChildren();
 const table=document.createElement('table'),header=document.createElement('tr');for(const text of ['試行','段階',`${requestData.parameter} [${hphiTuneParameterUnit(requestData)}]`,'対象ID','実順位','周波数 [Hz]','目標との差 [Hz]','状態','元場']){const cell=document.createElement('th');cell.textContent=text;header.append(cell);}table.append(header);
 for(const trial of d.trials){const row=document.createElement('tr'),rank=hphiTuneRank(trial,requestData.mode_id);for(const value of [trial.index+1,trial.phase==='refinement'?'最終細分':'探索',trial.value,requestData.mode_id,rank,hphiTuneFrequency(trial.frequency_hz),hphiTuneFrequency(trial.target_error_hz),trial.status]){const cell=document.createElement('td');cell.textContent=value;row.append(cell);}
  const cell=document.createElement('td'),button=document.createElement('button');button.textContent='対象モードの場を開く';button.disabled=rank==='未確認';button.dataset.hphiTuneTrial=trial.index+1;button.onclick=run(async()=>{const imported=await api('hphi-tune-trial',{document:data.serialized,index:trial.index+1});await refresh();await openResult(imported.id);$('mode').value=imported.mode;showQuantities();$('hphi-tune-status').textContent+=` / 試行 ${trial.index+1} の元場を表示中`;});cell.append(button);row.append(cell);table.append(row);
  if(trial.identity_recovery){const recovery=trial.identity_recovery,detail=document.createElement('tr'),message=document.createElement('td');message.colSpan=9;message.textContent=`試行 ${trial.index+1} の明示ID回復: ${recovery.status} / 比較親の試行 ${recovery.parent_trial_index===null?'なし':recovery.parent_trial_index+1} / anchor試行 ${recovery.anchor_trial_index===null?'なし':recovery.anchor_trial_index+1}${recovery.stop_reason?' / '+recovery.stop_reason:''}`;detail.append(message);table.append(detail);}
  const reason=hphiTuneReasons(trial);if(reason){const detail=document.createElement('tr'),message=document.createElement('td');message.colSpan=9;message.textContent=`試行 ${trial.index+1} の未確認理由: ${reason}`;detail.append(message);table.append(detail);}
 }
 $('hphi-tune-trials').append(table);
}
async function openHphiTune(id){const data=await api('hphi-tune-result',{id});showHphiTune(data,id);history.replaceState(null,'',`/hphi.html?tune=${encodeURIComponent(id)}`);}
$('hphi-tune-open').onchange=run(async()=>{const file=$('hphi-tune-open').files[0];$('hphi-tune-open').value='';if(!file)return;const version=hphiTuneInputVersion;const normalized=await api('hphi-normalize-tune',{request:await file.text()});if(version!==hphiTuneInputVersion)throw Error('入力が変わりました。読み込みをやり直してください。');loadHphiTune(normalized);});
$('hphi-tune-apply').onclick=run(async()=>loadHphiTune(await api('hphi-normalize-tune',{request:hphiTuneRequestText()})));
$('hphi-tune-save-request').onclick=run(async()=>{const version=hphiTuneInputVersion,text=hphiTuneRequestText(),normalized=await api('hphi-normalize-tune',{request:text});if(version!==hphiTuneInputVersion||text!==hphiTuneRequestText())throw Error('入力が変わりました。現在の条件を再確認してください。');loadHphiTune(normalized);download(new Blob([JSON.stringify(normalized,null,2)+'\n'],{type:'application/json'}),'hphi-tune-request.json');$('hphi-tune-dirty').textContent='調整要求を保存しました';});
$('hphi-tune-start').onclick=run(async()=>{const data=await api('hphi-start-tune',{request:hphiTuneRequestText(),max_new_trials:hphiTuneLimit()});$('hphi-tune-dirty').textContent=`調整投入済み: ${data.id}`;await refresh();});
$('hphi-tune-checkpoint-open').onchange=run(async()=>{const file=$('hphi-tune-checkpoint-open').files[0];$('hphi-tune-checkpoint-open').value='';if(!file)return;const version=hphiTuneInputVersion;const data=await api('hphi-replay-tune',{document:await file.text()});if(version!==hphiTuneInputVersion)throw Error('入力が変わりました。保存地点を再選択してください。');showHphiTune(data,file.name);});
$('hphi-tune-checkpoint-save').onclick=()=>{if(currentHphiTune)download(new Blob([currentHphiTune.serialized],{type:'application/json'}),'hphi-tune-checkpoint.json');};
$('hphi-tune-resume').onclick=run(async()=>{if(!currentHphiTune?.document.can_resume)throw Error('再開できるHφ保存地点を選択してください');const data=await api('hphi-resume-tune',{document:currentHphiTune.serialized,max_new_trials:hphiTuneLimit()});$('hphi-tune-dirty').textContent=`保存地点から再開投入済み: ${data.id}`;await refresh();});
$('hphi-tune-document').addEventListener('input',()=>{hphiTuneInputVersion++;$('hphi-tune-dirty').textContent='未保存の調整要求';});

run(async()=>{loadProject(await api('hphi-normalize',{document:fresh()}));await refresh();const parameters=new URLSearchParams(location.search),id=parameters.get('job'),studyId=parameters.get('study'),convergenceId=parameters.get('convergence'),trackingId=parameters.get('tracking'),historyId=parameters.get('history'),tuneId=parameters.get('tune');if(tuneId)await openHphiTune(tuneId);else if(historyId)await openHphiHistory(historyId);else if(trackingId)await openTracking(trackingId);else if(convergenceId)await openConvergence(convergenceId);else if(studyId)await openStudy(studyId);else if(id)await openResult(id);})();// Explicit operations retain errors; background refresh does not clear them.
setInterval(()=>refresh().catch(failure),2000);
