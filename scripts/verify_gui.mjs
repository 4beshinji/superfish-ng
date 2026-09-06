// SPDX-License-Identifier: Apache-2.0
// Real local browser input and computation. Requires a running GUI and Chrome.
import {spawn} from 'node:child_process';
import {mkdtemp,readFile,writeFile,mkdir} from 'node:fs/promises';
import {resolve} from 'node:path';
const args=Object.fromEntries(process.argv.slice(2).reduce((a,v,i,s)=>i%2?a:[...a,[v,s[i+1]]],[]));
if(!args['--url']||!args['--out'])throw Error('Usage: node scripts/verify_gui.mjs --url LAUNCH_URL --out NEW_DIRECTORY');
const out=resolve(args['--out']);await mkdir(out,{recursive:false});
const profile=await mkdtemp('/tmp/ng-gui-chrome-');
const browser=spawn('/usr/bin/google-chrome',['--headless','--remote-debugging-port=0',`--user-data-dir=${profile}`,'--disable-background-networking','--no-first-run','about:blank']);
let stderr='',ws,id=0;const pending=new Map(),sleep=ms=>new Promise(r=>setTimeout(r,ms));
browser.stderr.on('data',b=>stderr+=b);
const report={passed:false,node:process.version,checks:[],external_requests:[]};
try{
 let info;for(let n=0;n<100;n++){try{info=await readFile(profile+'/DevToolsActivePort','utf8');break;}catch{}await sleep(100);}if(!info)throw Error(stderr);
 const [port,path]=info.trim().split('\n');ws=new WebSocket(`ws://127.0.0.1:${port}${path}`);await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j;});
 ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.method==='Network.requestWillBeSent'){const url=m.params.request.url;if(/^https?:/.test(url)&&new URL(url).origin!==new URL(args['--url']).origin)report.external_requests.push(url);}if(pending.has(m.id)){const{done,fail,timer}=pending.get(m.id);pending.delete(m.id);clearTimeout(timer);m.error?fail(Error(JSON.stringify(m.error))):done(m.result);}};
 const call=(method,params={},sessionId)=>new Promise((done,fail)=>{const n=++id;const timer=setTimeout(()=>{pending.delete(n);fail(Error(`timeout ${method}`));},30000);pending.set(n,{done,fail,timer});ws.send(JSON.stringify({id:n,method,params,sessionId}));});
 report.browser=await call('Browser.getVersion');
 const{targetId}=await call('Target.createTarget',{url:'about:blank'});const{sessionId}=await call('Target.attachToTarget',{targetId,flatten:true});
 const ev=async expression=>{const r=await call('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true},sessionId);if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
 const wait=async(expression,ms=15000)=>{const start=performance.now();while(performance.now()-start<ms){if(await ev(expression))return;await sleep(100);}throw Error(`UI timeout: ${expression}; ${await ev('document.querySelector("#error")?.textContent')}`);};
 const click=async selector=>{const rect=await ev(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()`);for(const type of ['mousePressed','mouseReleased'])await call('Input.dispatchMouseEvent',{type,...rect,button:'left',clickCount:1},sessionId);};
 const fill=async(selector,value)=>{await ev(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});e.focus();e.select()})()`);await call('Input.insertText',{text:String(value)},sessionId);await call('Input.dispatchKeyEvent',{type:'keyDown',key:'Tab',code:'Tab',windowsVirtualKeyCode:9},sessionId);await call('Input.dispatchKeyEvent',{type:'keyUp',key:'Tab',code:'Tab',windowsVirtualKeyCode:9},sessionId);};
 await call('Page.enable',{},sessionId);await call('Network.enable',{},sessionId);
 await call('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false},sessionId);
 const begin=performance.now();await call('Page.navigate',{url:args['--url']},sessionId);await wait('document.querySelector("#shape polygon")');report.startup_ms=performance.now()-begin;
 await fill('#radius',65);await fill('#length',95);await fill('#modes',2);await click('#preview');await wait('document.querySelector("#preview-note").textContent.includes("入力形状")');
 report.checks.push({operation:'keyboard dimensions and preview',radius_mm:await ev('document.querySelector("#radius").value'),length_mm:await ev('document.querySelector("#length").value')});
 const before=await ev('document.querySelectorAll("#jobs .job").length');await click('#run');await wait(`document.querySelectorAll('#jobs .job').length > ${before}`);await wait('document.querySelector("#jobs .job strong").textContent.startsWith("計算完了")');
 await click('#jobs .job button');await wait('document.querySelector("#field-image").naturalWidth>0',30000);
 report.checks.push(await ev(`({operation:'FEM and saved field display',rows:document.querySelectorAll('#rf-table tr').length,image_width:document.querySelector('#field-image').naturalWidth,result_name:document.querySelector('#result-name').textContent})`));
 // Input failure must be visible while retaining the user's value.
 await fill('#radius',-1);await click('#preview');await wait('!document.querySelector("#error").hidden');
 report.checks.push({operation:'invalid radius retained',value:await ev('document.querySelector("#radius").value'),message:await ev('document.querySelector("#error").textContent')});
 await fill('#radius',65);await click('#preview');
 await ev('window.scrollTo(0,0)');const screenshot=await call('Page.captureScreenshot',{},sessionId);await writeFile(out+'/workspace.png',Buffer.from(screenshot.data,'base64'));
 report.passed=report.checks[0].radius_mm==='65'&&report.checks[0].length_mm==='95'&&report.checks[1].rows===3&&report.checks[1].image_width>0&&report.checks[2].value==='-1'&&report.external_requests.length===0;
 if(!report.passed)throw Error('GUI acceptance checks failed');
 console.log(JSON.stringify(report,null,2));
}catch(e){report.error=String(e);process.exitCode=1;console.error(e);}finally{await writeFile(out+'/report.json',JSON.stringify(report,null,2));ws?.close();browser.kill();}
