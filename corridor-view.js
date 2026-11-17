/* Eye-level view extruded directly from the floor's recorded two-dimensional boundaries. */
function createCorridorView(u, record) {
  const panel = el('div', 'uv-scene');
  const heading = el('p', 'uv-caption', 'منظور تخطيطي باتجاه '+codeText(u)+' · '+FLOORS[u.f]);
  heading.style.cssText = 'padding:12px 12px 5px;font-weight:700';
  panel.append(heading);

  const nearIds = new Set((record?.neighbors || []).map(item=>item.id));
  const floor = UNITS.filter(item=>item.f===u.f);
  const footprints = [];
  for (const item of floor) {
    const poly = (item.id===u.id ? record : UNIT_DRAWINGS[item.id])?.polygon;
    if (!Array.isArray(poly) || poly.length < 3 || !poly.every(p=>Array.isArray(p) && p.length===2 && p.every(Number.isFinite))) continue;
    const xs = poly.map(p=>p[0]), ys = poly.map(p=>p[1]);
    footprints.push({item,poly,minX:Math.min(...xs),maxX:Math.max(...xs),minY:Math.min(...ys),maxY:Math.max(...ys)});
  }
  const selected = footprints.find(entry=>entry.item.id===u.id);
  function inside(p, entry) {
    if (p[0]<entry.minX || p[0]>entry.maxX || p[1]<entry.minY || p[1]>entry.maxY) return false;
    let flag = false;
    const v = entry.poly;
    for (let i=0, j=v.length-1; i<v.length; j=i++) {
      const a=v[i], b=v[j];
      if ((a[1]>p[1]) !== (b[1]>p[1]) && p[0]<(b[0]-a[0])*(p[1]-a[1])/(b[1]-a[1])+a[0]) flag=!flag;
    }
    return flag;
  }
  const target = [u.x,u.y];
  if (selected && !inside(target,selected)) {
    // Some labels sit outside a concave unit. Aim at an actual interior point.
    let nearest = Infinity;
    for(let i=1;i<=14;i++) for(let j=1;j<=14;j++) {
      const p=[selected.minX+(selected.maxX-selected.minX)*i/15,selected.minY+(selected.maxY-selected.minY)*j/15];
      const d=Math.hypot(p[0]-u.x,p[1]-u.y);
      if (d<nearest && inside(p,selected)) {target[0]=p[0];target[1]=p[1];nearest=d}
    }
  }
  const edges=[];
  for(const box of footprints) box.poly.forEach((a,i)=>{
    const b=box.poly[(i+1)%box.poly.length];
    const dx=b[0]-a[0], dy=b[1]-a[1], l=Math.hypot(dx,dy);
    if(l>0.1) edges.push({a,dx,dy,box,nx:-dy/l,ny:dx/l});
  });
  function ray(origin, vx,vy, pool=edges) {
    let distance=Infinity, hit=null;
    for(const edge of pool) {
      const den=vx*edge.dy-vy*edge.dx;
      if(Math.abs(den)<1e-8) continue;
      const ax=edge.a[0]-origin[0], ay=edge.a[1]-origin[1];
      const t=(ax*edge.dy-ay*edge.dx)/den, s=(ax*vy-ay*vx)/den;
      if(t>.02 && s>=0 && s<=1 && t<distance) {distance=t;hit=edge}
    }
    return {distance,hit};
  }
  const inPlan=p=>p[0]>=0 && p[0]<=1108 && p[1]>=0 && p[1]<=1100;
  const open=p=>inPlan(p) && !footprints.some(e=>inside(p,e));
  const standpoints=[];
  if(selected) {
    const center=[(selected.minX+selected.maxX)/2,(selected.minY+selected.maxY)/2];
    for(const edge of edges.filter(e=>e.box===selected)){
      const base=[edge.a[0]+edge.dx/2,edge.a[1]+edge.dy/2];
      for(const s of [-1,1]) for(const offset of [11,20,32]){
        const p=[base[0]+s*edge.nx*offset,base[1]+s*edge.ny*offset];
        if(!open(p)) continue;
        const dx=target[0]-p[0],dy=target[1]-p[1],ln=Math.hypot(dx,dy);
        if(ln<1 || ray(p,dx/ln,dy/ln).hit?.box!==selected) continue;
        // An opposite footprint across an open strip is usually the other side of the corridor.
        const opposite=ray(p,s*edge.nx,s*edge.ny);
        const across=opposite.hit && opposite.hit.box!==selected && opposite.distance<80;
        const score=(across?80:0)+Math.min(40,Math.hypot(edge.dx,edge.dy)) - Math.abs(offset-20)*.7 - Math.hypot(center[0]-base[0],center[1]-base[1])*.08;
        standpoints.push({p,score});
      }
    }
    standpoints.sort((a,b)=>b.score-a.score);
  }
  const choices=[];
  for(const candidate of standpoints){
    if(!choices.some(p=>Math.hypot(p[0]-candidate.p[0],p[1]-candidate.p[1])<17)) choices.push(candidate.p);
  }
  let camera=choices[0] || null, choice=0;
  const svgNS='http://www.w3.org/2000/svg';
  function sn(tag,attrs){const n=document.createElementNS(svgNS,tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,v);return n}
  const canvas=el('canvas','uv-canvas');
  canvas.style.cssText='display:block;width:100%;height:clamp(210px,29vw,390px);cursor:default;background:#e9e9dc';
  canvas.setAttribute('role','img');canvas.setAttribute('aria-label','منظور حدود الوحدات من نقطة الوقوف على الرسم باتجاه '+codeText(u));
  const prompt=el('p','uv-caption',selected?'اضغط على مساحة مفتوحة في الرسم لتغيير نقطة الوقوف. الأخضر يحدد الوحدة، والذهبي يحدد الوحدات الملاصقة.':'نقطة الوحدة موضحة على الرسم. يلزم تحديد حدودها لرسم منظور الممر.');
  prompt.style.cssText='padding:8px 12px 4px';
  const live=el('p','uv-caption');live.setAttribute('aria-live','polite');live.style.cssText='padding:4px 12px 10px;margin:0';
  if(selected) panel.append(canvas);
  panel.append(prompt);
  const svg=sn('svg',{role:selected?'group':'img','aria-label':'نقطة الوقوف والاتجاه نحو '+codeText(u)+' على مسقط الدور',preserveAspectRatio:'xMidYMid meet'});
  svg.style.cssText='display:block;width:100%;height:clamp(165px,20vw,245px);background:#f4f1e9;'+(selected?'cursor:crosshair;':'');
  const side=Math.min(1108,Math.max(150,selected?Math.max(selected.maxX-selected.minX,selected.maxY-selected.minY)*1.55+96:260));
  const left=Math.max(0,Math.min(1108-side,target[0]-side/2)), top=Math.max(0,Math.min(1100-side*.72,target[1]-side*.36));
  const vh=Math.min(1100,side*.72);
  svg.setAttribute('viewBox',[left,top,side,vh].join(' '));
  const layer=sn('g',{});layer.append(sn('image',{href:MAPS[u.f],x:0,y:0,width:1108,height:1100,preserveAspectRatio:'none'}));
  const sw=side/160;
  if(selected) layer.append(sn('polygon',{points:selected.poly.map(p=>p.join(',')).join(' '),fill:'#167966','fill-opacity':'.35',stroke:'#125847','stroke-width':sw}));
  for(const box of footprints.filter(f=>nearIds.has(f.item.id)))layer.append(sn('polygon',{points:box.poly.map(p=>p.join(',')).join(' '),fill:'#e1a53a','fill-opacity':'.20',stroke:'#9d743b','stroke-width':sw*.6}));
  const viewLine=sn('line',{x2:target[0],y2:target[1],stroke:'#154c68','stroke-width':sw,'stroke-dasharray':(2.4*sw)+' '+1.15*sw});
  const dot=sn('circle',{cx:target[0],cy:target[1],r:sw*2.6,fill:'#116653',stroke:'white','stroke-width':sw*.8});
  const camDot=sn('path',{d:'M 0 -4.8 L 3.6 3.4 L 0 2.1 L -3.6 3.4 Z',fill:'#0d4c73',stroke:'white','stroke-width':'.85'});
  layer.append(viewLine,dot,camDot);svg.append(layer);panel.append(svg);
  const controls=el('div','uv-controls');
  if(selected && choices.length>1)controls.append(btn('زاوية أخرى',()=>{choice=(choice+1)%choices.length;setCamera(choices[choice]);},'uv-tool'));
  if(selected && choices.length)controls.append(btn('النقطة الأولى',()=>{choice=0;setCamera(choices[0]);},'uv-tool'));
  if(controls.childElementCount) panel.append(controls);
  panel.append(live);
  const note=el('p','uv-caption','ارتفاعات الحدود افتراضية. موضع النظر المختار على المسقط تخطيطي.');if(selected)panel.append(note);
  function setCamera(p){
    if(!open(p)){live.textContent='اختَر نقطة خارج حدود الوحدات.';return}
    camera=p;live.textContent='السهم الأزرق هو نقطة الوقوف، والخط المتقطع يوضح اتجاه النظر.';redraw();
  }
  function pick(event){
    const matrix=svg.getScreenCTM();
    if(!matrix) return;
    const q=svg.createSVGPoint();q.x=event.clientX;q.y=event.clientY;
    const p=q.matrixTransform(matrix.inverse());
    if(p.x<left || p.x>left+side || p.y<top || p.y>top+vh)return;
    setCamera([p.x,p.y]);
  }
  function handleKey(event){
    const delta={ArrowUp:[0,-1],ArrowDown:[0,1],ArrowRight:[1,0],ArrowLeft:[-1,0]}[event.key];
    if(!delta || !camera)return;
    event.preventDefault();const step=side/45;
    const p=[camera[0]+delta[0]*step,camera[1]+delta[1]*step];
    if(p[0]>=left && p[0]<=left+side && p[1]>=top && p[1]<=top+vh)setCamera(p);
  }
  if(selected){svg.setAttribute('tabindex','0');svg.addEventListener('click',pick);svg.addEventListener('keydown',handleKey)}
  if(!selected || !camera){
    viewLine.setAttribute('visibility','hidden');camDot.setAttribute('visibility','hidden');
    if(selected) live.textContent='حدّد نقطة مفتوحة على الرسم لعرض المنظور.';
  }else live.textContent='السهم الأزرق هو نقطة الوقوف، والخط المتقطع يوضح اتجاه النظر.';
  function redraw(){
    if(!selected || !camera)return;
    const dx=target[0]-camera[0], dy=target[1]-camera[1],dist=Math.hypot(dx,dy);
    if(dist<.01)return;
    const fx=dx/dist, fy=dy/dist;
    viewLine.setAttribute('visibility','visible');camDot.setAttribute('visibility','visible');
    viewLine.setAttribute('x1',camera[0]);viewLine.setAttribute('y1',camera[1]);
    camDot.setAttribute('transform','translate('+camera.join(' ')+') rotate('+(Math.atan2(fy,fx)*180/Math.PI+90)+') scale('+sw+')');
    const w=Math.round(canvas.clientWidth), h=Math.round(canvas.clientHeight);
    if(!w || !h)return;
    const dpr=Math.min(2,window.devicePixelRatio||1);canvas.width=Math.ceil(w*dpr);canvas.height=Math.ceil(h*dpr);
    const c=canvas.getContext('2d');if(!c)return;c.scale(dpr,dpr);
    const horizon=h*.47;
    c.fillStyle='#f3f2e9';c.fillRect(0,0,w,horizon);
    const gradient=c.createLinearGradient(0,horizon,0,h);
    gradient.addColorStop(0,'#deddd1');gradient.addColorStop(1,'#f1ece1');c.fillStyle=gradient;c.fillRect(0,horizon,w,h-horizon);
    c.strokeStyle='#c3c2b2';c.beginPath();c.moveTo(0,horizon);c.lineTo(w,horizon);c.stroke();
    const columns=Math.max(140,Math.min(680,Math.round(w))), stride=w/columns, fov=Math.tan(Math.PI*37/180), focal=w/(2*fov);
    const eye=5.8, wall=12, visible=[];
    let section=null, previous=null, pickedVisible=false;
    for(let i=0;i<columns;i++){
      const plane=(2*(i+.5)/columns-1)*fov;
      const hit=ray(camera,fx-fy*plane,fy+fx*plane);
      if(!hit.hit || hit.distance>360){previous=null;section=null;continue}
      const e=hit.hit,id=e.box.item.id, selectedWall=id===u.id, neighbor=nearIds.has(id), depth=Math.max(1,hit.distance);
      const ceil=horizon-(wall-eye)*focal/depth, base=horizon+eye*focal/depth;
      const light=.13*Math.abs(e.nx*.75+e.ny*.65), haze=Math.min(.46,depth/410);
      const mat=selectedWall?[31,108,86]:neighbor?[171,137,84]:[140,148,136];
      const rgb=mat.map((n,k)=>Math.round((n*(1-light))*(1-haze)+[226,225,212][k]*haze));
      c.fillStyle='rgb('+rgb.join(',')+')';c.fillRect(i*stride,ceil,stride+.45,base-ceil);
      c.fillStyle=selectedWall?'#225844':neighbor?'#997a4e':'#858c80';
      c.fillRect(i*stride,ceil,stride+.45,1.4);c.fillRect(i*stride,base-1.4,stride+.45,1.4);
      if(previous && previous!==e){c.fillStyle='rgba(53,60,48,.25)';c.fillRect(i*stride,ceil,1,base-ceil)}
      if(!section || section.id!==id){section={id,first:i,last:i,depth};visible.push(section)} else section.last=i;
      if(selectedWall)pickedVisible=true;previous=e;
    }
    const labels=visible.filter(z=>z.last-z.first>columns*.054).sort((a,b)=>(b.id===u.id)-(a.id===u.id)||(b.last-b.first)-(a.last-a.first));
    const labeled=new Set(), spans=[];
    for(const z of labels){
      if(labeled.has(z.id) || (!nearIds.has(z.id) && z.id!==u.id) || spans.length>=6)continue;
      const unit=floor.find(f=>f.id===z.id),label=codeText(unit);
      c.font='bold '+(z.id===u.id?14:12)+'px Arial,sans-serif';
      const bw=c.measureText(label).width+14,bh=22, x=Math.max(bw/2+4,Math.min(w-bw/2-4,(z.first+z.last+1)*stride/2));
      if(spans.some(s=>Math.abs(s.x-x)<(s.width+bw)/2+4))continue;
      spans.push({x,width:bw});labeled.add(z.id);c.fillStyle=z.id===u.id?'#124b39':'#fff5df';c.fillRect(x-bw/2,horizon-bh/2,bw,bh);
      c.fillStyle=z.id===u.id?'#fff':'#574326';c.textAlign='center';c.textBaseline='middle';c.fillText(label,x,horizon+1);
    }
    if(!pickedVisible)live.textContent='الوحدة محجوبة من نقطة النظر دي. اختَر نقطة تانية على الرسم.';
  }
  const observer=typeof ResizeObserver==='function'?new ResizeObserver(redraw):null;
  if(selected)observer?.observe(canvas);
  let start=requestAnimationFrame(redraw);
  return {panel,dispose(){cancelAnimationFrame(start);observer?.disconnect();svg.removeEventListener('click',pick);svg.removeEventListener('keydown',handleKey)}};
}
