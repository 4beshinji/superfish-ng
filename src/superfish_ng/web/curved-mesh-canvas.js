// SPDX-License-Identifier: Apache-2.0
"use strict";
// Exact quadratic edge paths with a conservative control-hull spatial index.
// Canvas supplies curve hit testing; no display triangle substitutes a FEM cell.
class CurvedMeshCanvas {
  constructor(canvas, mesh, selected, onChange, onFocus) {
    this.canvas=canvas; this.mesh=mesh; this.selected=selected;
    this.onChange=onChange; this.onFocus=onFocus; this.activeCell=0;
    this.context=canvas.getContext('2d');
    this.scene=document.createElement('canvas'); this.sceneContext=this.scene.getContext('2d');
    this.hitContext=document.createElement('canvas').getContext('2d');
    this.paths=[]; this.bounds=[]; this.bins=new Map(); this.allPath=new Path2D();
    this.events=new AbortController(); this.disposed=false; this.frame=0; this.sceneDirty=true;
    this.ready=false; this.zoom=1; this.offset=[0,0];
  }
  async build() {
    const begin=performance.now(), raw=this.mesh.points_rz_m;
    let z0=Infinity,z1=-Infinity,r0=Infinity,r1=-Infinity;
    for(const [r,z] of raw) { z0=Math.min(z0,z);z1=Math.max(z1,z);r0=Math.min(r0,r);r1=Math.max(r1,r); }
    const length=Math.max(z1-z0,r1-r0);
    if(!(length>0 && Number.isFinite(length)))throw Error('メッシュの表示範囲が不正です');
    this.origin=[z0,r1]; this.length=length;
    const points=raw.map(([r,z])=>[(z-z0)/length,(r1-r)/length]);
    this.gridSize=Math.min(128,Math.max(8,Math.ceil(Math.sqrt(this.mesh.cell_nodes.length/8))));
    let xmin=Infinity,ymin=Infinity,xmax=-Infinity,ymax=-Infinity;
    for(let index=0;index<this.mesh.cell_nodes.length;index++) {
      if(index%2000===0) {
        await new Promise(resolve=>requestAnimationFrame(resolve));
        if(this.disposed)return;
      }
      const p=this.mesh.cell_nodes[index].map(i=>points[i]), path=new Path2D();
      path.moveTo(...p[0]); const hull=[...p.slice(0,3)];
      for(const [a,b,m] of [[0,1,3],[1,2,4],[2,0,5]]) {
        const c=p[m].map((v,k)=>2*v-(p[a][k]+p[b][k])/2);
        path.quadraticCurveTo(...c,...p[b]); hull.push(c);
      }
      path.closePath(); this.paths.push(path); this.allPath.addPath(path);
      const xs=hull.map(p=>p[0]),ys=hull.map(p=>p[1]);
      const bounds=[Math.min(...xs),Math.min(...ys),Math.max(...xs),Math.max(...ys)];
      this.bounds.push(bounds);
      xmin=Math.min(xmin,bounds[0]); ymin=Math.min(ymin,bounds[1]);
      xmax=Math.max(xmax,bounds[2]); ymax=Math.max(ymax,bounds[3]);
      const [a,b,c,d]=this.binRange(bounds);
      for(let x=a;x<=c;x++)for(let y=b;y<=d;y++) {
        const key=x+','+y; if(!this.bins.has(key))this.bins.set(key,[]);
        this.bins.get(key).push(index);
      }
    }
    this.extent=[xmin,ymin,xmax,ymax]; this.ready=true;
    const listen=(type,handler,options={})=>this.canvas.addEventListener(type,handler,{...options,signal:this.events.signal});
    listen('wheel',e=>{e.preventDefault();this.zoomAt(Math.exp(-Math.sign(e.deltaY)*.25),this.localPoint(e));},{passive:false});
    listen('pointerdown',e=>{
      if(e.button!==0)return;
      this.canvas.focus(); this.canvas.setPointerCapture(e.pointerId);
      this.drag={start:this.localPoint(e),offset:[...this.offset],moved:false};
    });
    listen('pointermove',e=>{
      if(this.drag) {
        const p=this.localPoint(e),dx=p[0]-this.drag.start[0],dy=p[1]-this.drag.start[1];
        if(Math.hypot(dx,dy)>4)this.drag.moved=true;
        if(this.drag.moved) {this.offset=[this.drag.offset[0]+dx,this.drag.offset[1]+dy];this.draw(true);}
      }
    });
    listen('pointerup',e=>{
      if(!this.drag)return;
      if(!this.drag.moved) {const index=this.hit(this.localPoint(e));if(index!==null){this.activeCell=index;this.toggle();}}
      this.drag=null;
    });
    listen('pointercancel',()=>{this.drag=null;});
    listen('lostpointercapture',()=>{this.drag=null;});
    listen('keydown',e=>{
      if(e.key==='Enter'||e.key===' ') {e.preventDefault();this.toggle();}
      else if(e.key==='+'||e.key==='=') {e.preventDefault();this.zoomAt(1.6);}
      else if(e.key==='-') {e.preventDefault();this.zoomAt(1/1.6);}
      else if(e.key==='0') {e.preventDefault();this.fit();}
      else if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key)) {
        e.preventDefault();const d={ArrowLeft:[50,0],ArrowRight:[-50,0],ArrowUp:[0,50],ArrowDown:[0,-50]}[e.key];
        this.offset=this.offset.map((v,i)=>v+d[i]);this.draw(true);
      }
    });
    this.observer=new ResizeObserver(()=>this.resize()); this.observer.observe(this.canvas);
    this.resize(); this.onFocus(this.activeCell); this.buildMilliseconds=performance.now()-begin;
  }
  dispose() {
    this.disposed=true;this.events.abort();this.observer?.disconnect();cancelAnimationFrame(this.frame);
    this.paths=[];this.bounds=[];this.bins.clear();this.allPath=null;this.mesh=null;
    this.scene.width=0;this.scene.height=0;
  }
  binRange([a,b,c,d]) {const n=this.gridSize;return [Math.floor(a*n),Math.floor(b*n),Math.floor(c*n),Math.floor(d*n)];}
  localPoint(e) {const r=this.canvas.getBoundingClientRect();return [e.clientX-r.left,e.clientY-r.top];}
  resize() {
    if(!this.ready||this.disposed)return;
    const rect=this.canvas.getBoundingClientRect();if(!rect.width||!rect.height)return;
    this.width=rect.width;this.height=rect.height;this.dpr=Math.min(2,window.devicePixelRatio||1);
    for(const c of [this.canvas,this.scene]) {c.width=Math.round(this.width*this.dpr);c.height=Math.round(this.height*this.dpr);}
    const [a,b,c,d]=this.extent;
    this.baseScale=Math.min((this.width-32)/(c-a),(this.height-32)/(d-b));
    this.draw(true);
  }
  transform() {
    const [a,b,c,d]=this.extent, scale=this.baseScale*this.zoom;
    return [scale,this.width/2-(a+c)*scale/2+this.offset[0],this.height/2-(b+d)*scale/2+this.offset[1]];
  }
  world([x,y]) {const [s,dx,dy]=this.transform();return [(x-dx)/s,(y-dy)/s];}
  screen([x,y]) {const [s,dx,dy]=this.transform();return [x*s+dx,y*s+dy];}
  hit(point) {
    if(!this.ready)return null;
    const [x,y]=this.world(point),key=Math.floor(x*this.gridSize)+','+Math.floor(y*this.gridSize);
    // Reverse order matches the topmost native cell at a shared boundary.
    const candidates=this.bins.get(key)||[];
    for(let i=candidates.length-1;i>=0;i--) {
      const index=candidates[i];
      if(this.hitContext.isPointInPath(this.paths[index],x,y))return index;
    }
    return null;
  }
  fit() {this.zoom=1;this.offset=[0,0];this.draw(true);}
  zoomAt(factor,point=[this.width/2,this.height/2]) {
    if(!this.ready)return;
    const before=this.world(point);this.zoom=Math.max(.5,Math.min(512,this.zoom*factor));
    const after=this.screen(before);this.offset=this.offset.map((v,i)=>v+point[i]-after[i]);this.draw(true);
  }
  focusCell(index) {
    if(!this.ready||this.disposed)throw Error('メッシュの表示が完了してから要素番号へ移動してください');
    if(!Number.isSafeInteger(index)||index<0||index>=this.paths.length)throw Error('存在する0始まりの要素番号を入力してください');
    this.activeCell=index;
    const [a,b,c,d]=this.bounds[index],size=Math.max(c-a,d-b);
    this.zoom=Math.max(1,Math.min(512,Math.min(this.width,this.height)/5/(this.baseScale*size)));
    this.offset=[0,0];const p=this.screen([(a+c)/2,(b+d)/2]);
    this.offset=[this.width/2-p[0],this.height/2-p[1]];
    this.onFocus(index);this.canvas.focus();this.draw(true);
  }
  toggle() {
    const index=this.activeCell;
    if(this.selected.has(index))this.selected.delete(index);else this.selected.add(index);
    this.onFocus(index);this.onChange();this.draw(false);
  }
  visiblePath() {
    if(this.zoom<=1)return this.allPath;
    const lo=this.world([0,0]),hi=this.world([this.width,this.height]);
    const ext=this.extent;
    const region=[Math.max(lo[0],ext[0]),Math.max(lo[1],ext[1]),Math.min(hi[0],ext[2]),Math.min(hi[1],ext[3])];
    const result=new Path2D();if(region[0]>region[2]||region[1]>region[3])return result;
    const [a,b,c,d]=this.binRange(region),seen=new Set();
    for(let x=a;x<=c;x++)for(let y=b;y<=d;y++)for(const index of this.bins.get(x+','+y)||[]) {
      if(!seen.has(index)){seen.add(index);result.addPath(this.paths[index]);}
    }
    return result;
  }
  draw(rebuild) {
    if(!this.ready||this.disposed)return;
    this.sceneDirty ||= rebuild;
    if(this.frame)return;
    this.frame=requestAnimationFrame(()=>{
      this.frame=0;if(this.disposed)return;
      const begin=performance.now(),[s,x,y]=this.transform(),ratio=this.dpr;
      if(this.sceneDirty) {
        const ctx=this.sceneContext;
        ctx.resetTransform();ctx.fillStyle='#fff';ctx.fillRect(0,0,this.scene.width,this.scene.height);
        ctx.setTransform(s*ratio,0,0,s*ratio,x*ratio,y*ratio);
        const visible=this.visiblePath();ctx.fillStyle='#d7e9f8';ctx.strokeStyle='#35647c';ctx.lineWidth=.6/s;
        ctx.fill(visible);ctx.stroke(visible);this.sceneDirty=false;
      }
      const ctx=this.context;ctx.resetTransform();ctx.clearRect(0,0,this.canvas.width,this.canvas.height);ctx.drawImage(this.scene,0,0);
      ctx.setTransform(s*ratio,0,0,s*ratio,x*ratio,y*ratio);
      ctx.fillStyle='#efb44c';ctx.strokeStyle='#785000';ctx.lineWidth=1/s;
      for(const index of this.selected){ctx.fill(this.paths[index]);ctx.stroke(this.paths[index]);}
      ctx.strokeStyle='#b10066';ctx.lineWidth=2/s;ctx.stroke(this.paths[this.activeCell]);
      this.lastDrawMilliseconds=performance.now()-begin;
    });
  }
}
