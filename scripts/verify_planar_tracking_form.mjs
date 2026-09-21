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
