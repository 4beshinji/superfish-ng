// SPDX-License-Identifier: Apache-2.0
"use strict";

// Preserve raw target JSON and SI values for the strict server reader.
function buildCurvedDeformationRequest({collect, $, number}) {
  return {document:collect(),geometry_document:$('deformation-geometry').value,
    rf_coordinates:$('deformation-rf').value,minimum_corner_angle_deg:number('deformation-angle')};
}

// Draw the native quadratic boundary returned by the existing operation.
function renderCurvedDeformation($, response) {
  const svg=$('deformation-boundary'),ns='http://www.w3.org/2000/svg';svg.replaceChildren();
  const edges=name=>response[name].native_boundary.edges_rz_m;
  const control=([a,b,m])=>m.map((v,i)=>2*v-(a[i]+b[i])/2);
  let r0=Infinity,z0=Infinity,r1=-Infinity,z1=-Infinity;
  for(const name of ['source','target'])for(const edge of edges(name))for(const [r,z] of [...edge,control(edge)]) {
    r0=Math.min(r0,r);r1=Math.max(r1,r);z0=Math.min(z0,z);z1=Math.max(z1,z);
  }
  const scale=Math.min(740/(z1-z0),270/(r1-r0));
  const point=([r,z])=>[30+(z-z0)*scale,300-(r-r0)*scale];
  for(const name of ['source','target']) {
    const path=document.createElementNS(ns,'path');
    path.setAttribute('d',edges(name).map(edge=>`M ${point(edge[0]).join(' ')} Q ${point(control(edge)).join(' ')} ${point(edge[1]).join(' ')}`).join(' '));
    path.setAttribute('fill','none');path.setAttribute('stroke',name==='source'?'#64748b':'#175ea8');
    path.setAttribute('stroke-width',name==='source'?'2':'2.5');
    if(name==='source')path.setAttribute('stroke-dasharray','6 4');
    path.dataset.geometry=name;svg.append(path);
  }
  const label=document.createElementNS(ns,'text');label.setAttribute('x','30');label.setAttribute('y','330');
  label.textContent=`z → 表示幅 ${((z1-z0)*1000).toPrecision(6)} mm ／ r ↑`;svg.append(label);
  $('deformation-mesh-info').textContent=['source','target'].map(name=>{
    const mesh=response[name].native_boundary;return `${name==='source'?'元':'変形後'}: ${mesh.cell_count}要素 / ${mesh.node_count}節点`;
  }).join(' → ');
  $('deformation-rf-info').textContent=['source','target'].map(name=>{
    const rf=response[name].rf_coordinates,mm=x=>(x*1000).toPrecision(6);
    return `${name==='source'?'元':'変形後'}のRF座標: 有効長 ${mm(rf.active_length_m)} mm、電圧区間 [${rf.voltage_interval_m.map(mm).join(', ')}] mm、位相原点 ${mm(rf.phase_origin_m)} mm${rf.phase_origin_explicit?'':'（暗黙値）'}`;
  }).join(' → ');
  $('deformation-view').hidden=false;
}

// Own only deformation preparation, asynchronous guards and Undo.
// Adapters resolve the current editor/API at call time.
function createCurvedDeformationWorkflow({
  $, bind, collect, number, api, applyProject, markDirty, drawOutline, download, failure,
}) {
let deformationGeneration=0, deformationResult=null, deformationUndo=null;
function projectSignature() {
  try {return JSON.stringify(collect());} catch {return null;}
}
function clearDeformationUndo() {
  deformationUndo=null;$('deformation-undo').disabled=true;
}
function invalidateDeformation() {
  deformationGeneration++;deformationResult=null;
  $('deformation-apply').disabled=$('deformation-save').disabled=true;
  $('deformation-view').hidden=true;$('deformation-boundary').replaceChildren();
  $('deformation-status').textContent='現在の入力で変形を検査してください。編集中のProjectは保持します。';
}
function deformationInput() {
  return buildCurvedDeformationRequest({collect, $, number});
}
function deformationMatches(generation,signature) {
  try {return generation===deformationGeneration && JSON.stringify(deformationInput())===signature;} catch {return false;}
}
for(const id of ['deformation-geometry','deformation-rf','deformation-angle'])
  $(id).addEventListener('input',invalidateDeformation);
bind('deformation-template',async()=>{
  invalidateDeformation();const generation=deformationGeneration,project=collect(),signature=JSON.stringify(project);
  $('deformation-template').disabled=true;
  try {
    const result=await api('normalize',{document:project});
    if(generation!==deformationGeneration || projectSignature()!==signature)throw Error('目標形状の準備中に入力が変わりました。やり直してください');
    if(result.project.case.geometry.type!=='curved_contour')throw Error('現在の曲線Projectを開いてください');
    $('deformation-geometry').value=JSON.stringify(result.project.case.geometry,null,2);
    $('deformation-status').textContent='元の曲線を目標形状へコピーしました。寸法を編集してプレビューしてください。';
  } finally {$('deformation-template').disabled=false;}
});
$('deformation-open').onchange=async event=>{
  try {
    if(!event.target.files.length)return;
    invalidateDeformation();const generation=deformationGeneration;
    const text=await event.target.files[0].text();
    if(generation!==deformationGeneration)throw Error('ファイル読込中に入力が変わりました。やり直してください');
    $('deformation-geometry').value=text;
    $('deformation-status').textContent='目標形状を読み込みました。形状と全履歴を検査してください。';
  } catch(error){failure(error);} finally {event.target.value='';}
};
function drawDeformation(response) {
  renderCurvedDeformation($, response);
}
bind('deformation-preview',async()=>{
  invalidateDeformation();const generation=deformationGeneration,input=deformationInput(),signature=JSON.stringify(input);
  $('deformation-preview').disabled=true;$('deformation-status').textContent='元メッシュと全細分段階の幾何・品質を検査中です。';
  try {
    const response=await api('preview-curved-deformation',input);
    if(!deformationMatches(generation,signature))throw Error('変形の検査中に入力が変わりました。現在の入力でやり直してください');
    drawDeformation(response);
    deformationResult={generation,signature,response,before:input.document};
    $('deformation-apply').disabled=$('deformation-save').disabled=false;
    $('deformation-status').textContent='変形後の幾何と全細分履歴の検査が完了しました。元Projectを保持したまま、保存または適用できます。';
  } catch(error) {
    if(generation===deformationGeneration)$('deformation-status').textContent='変形を準備できませんでした。入力・操作のエラーを確認してください。';
    throw error;
  } finally {$('deformation-preview').disabled=false;}
});
function checkedDeformation() {
  if(!deformationResult || !deformationMatches(deformationResult.generation,deformationResult.signature)) {
    invalidateDeformation();throw Error('入力が変わりました。形状変形を再検査してください');
  }
  return deformationResult;
}
bind('deformation-save',()=>download('deformed-project.json',checkedDeformation().response.serialized));
bind('deformation-apply',()=>{
  const prepared=checkedDeformation(),target=prepared.response.target;
  applyProject(target.project);markDirty();
  drawOutline(target.outline_zr_m,target.outline_closed,target.geometry_approximation);
  deformationUndo={before:prepared.before,preview:prepared.response.source,applied:projectSignature()};
  $('deformation-undo').disabled=false;
  $('deformation-status').textContent='変形済みProjectを適用しました。保存・通常計算・図上メッシュ確認へ進めます。';
});
bind('deformation-undo',()=>{
  if(!deformationUndo || projectSignature()!==deformationUndo.applied) {
    clearDeformationUndo();throw Error('適用後にProjectが変わりました。元に戻す操作は利用できません');
  }
  const saved=deformationUndo;applyProject(saved.before);markDirty();
  drawOutline(saved.preview.outline_zr_m,saved.preview.outline_closed,saved.preview.geometry_approximation);
  $('deformation-status').textContent='形状変形前のProject・元メッシュ・全細分履歴・RF条件へ戻しました。';
});
  return Object.freeze({
    invalidate: invalidateDeformation,
    projectChanged() {
      invalidateDeformation();
      if(deformationUndo && projectSignature()!==deformationUndo.applied) clearDeformationUndo();
    },
    reset() { invalidateDeformation();clearDeformationUndo(); },
    get prepared() { return deformationResult; },
    get undo() { return deformationUndo; },
  });
}
