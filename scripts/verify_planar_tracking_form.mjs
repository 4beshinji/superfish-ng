// SPDX-License-Identifier: Apache-2.0
// Isolated real form functions; DOM and browser acceptance are separate.
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const source=readFileSync('src/superfish_ng/web/planar.js','utf8');
const elements=new Map();
const sandbox={$:id=>{if(!elements.has(id))elements.set(id,{value:''});return elements.get(id);},numeric:id=>Number(sandbox.$(id).value),refreshTrackingSources(){},trackingJobs:[]};
vm.createContext(sandbox);
vm.runInContext(source.slice(source.indexOf(' function trackingFromForm()'),source.indexOf('async function openTracking(')),sandbox);
const requests=JSON.parse(readFileSync(process.argv[2],'utf8'));
for(const request of requests){sandbox.request=request;vm.runInContext('loadTracking(request)',sandbox);assert.deepEqual(JSON.parse(JSON.stringify(vm.runInContext('trackingFromForm()',sandbox))),request);}
console.log(`PASS: ${requests.length} exact tracking form round trips`);

for(const request of requests){
  sandbox.request=request;vm.runInContext('loadTracking(request)',sandbox);
  assert.deepEqual(JSON.parse(vm.runInContext('trackingRequestText()',sandbox)),request);
  if([8,9,10].includes(request.tracking_version)){
    const name=JSON.stringify(request.mapping.name), needle='"name": '+name;
    const declaration=sandbox.$('tracking-polynomial-mapping').value;
    const duplicate='"name": '+name+', "name": '+name;
    sandbox.$('tracking-polynomial-mapping').value=declaration.replace(needle,duplicate);
    assert.ok(vm.runInContext('trackingRequestText()',sandbox).includes(duplicate));
  }
  const controls=sandbox.$('tracking-controls').value;
  const duplicate='"minimum_overlap": 0.9, "minimum_overlap": 0.1';
  sandbox.$('tracking-controls').value=controls.replace('"minimum_overlap": 0.9',duplicate);
  assert.ok(vm.runInContext('trackingRequestText()',sandbox).includes(duplicate));
}
console.log('PASS raw mapping/control duplicate keys reach strict server transport');
