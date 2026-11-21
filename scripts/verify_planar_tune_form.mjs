// SPDX-License-Identifier: Apache-2.0
// Isolated form round trips; not a browser or backend physics acceptance.
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const source=readFileSync('src/superfish_ng/web/planar.js','utf8');
const elements=new Map();let project;
const sandbox={$:id=>{if(!elements.has(id))elements.set(id,{value:''});return elements.get(id);},document:{addEventListener(){}},numeric:id=>Number(sandbox.$(id).value),documentFromForm:()=>project,loadProject:value=>{project=value;}};
vm.createContext(sandbox);
vm.runInContext(source.slice(source.indexOf('let currentTune='),source.indexOf('function showTune(')),sandbox);
const base={format:'superfish_ng_planar_tune',schema_version:1,project:{name:'original'},parameter:'uniform_scale',mode_id:'x',target_hz:1,frequency_tolerance_hz:2,mesh_frequency_tolerance_hz:3,parameter_tolerance:4,max_trials:8,refinement_levels:1,max_triangles:20000,bounds:[1,2],initial_ids:['x','y'],controls:{minimum_overlap:.9}};
for(const value of [base,{...base,schema_version:2,parameter:'deformation',shape_law:{bounds:[1,2]}},{...base,schema_version:3,identity_recovery:{anchor_selection:'fixed_trial',anchor_trial_index:0,controls:{minimum_overlap:.95}}},{...base,schema_version:3,parameter:'deformation',shape_law:{bounds:[1,2]},identity_recovery:{anchor_selection:'latest_resolved_trial',controls:{minimum_overlap:.95}}}]){
 sandbox.value=value;vm.runInContext('loadTune(value)',sandbox);
 assert.deepEqual(JSON.parse(vm.runInContext('tuneRequestText()',sandbox)),value);
}
console.log('PASS: 4 exact form round trips, including v1/v2/v3 and both recovery policies');
