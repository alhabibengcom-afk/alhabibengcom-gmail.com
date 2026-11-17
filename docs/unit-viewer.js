// The plan's x/y axes are shared by its raster, unit pins and traced outlines.
function createUnitScene(u, record, mode) {
  const panel = el('div', 'uv-scene');
  const canvas = el('canvas', 'uv-canvas');
  canvas.setAttribute('aria-label', 'موقع '+codeText(u)+' والممرات المحيطة على مسقط '+FLOORS[u.f]);
  const controls = el('div', 'uv-controls');
  const three = mode === '3d';
  const resetAngle = -.27;
  let angle = three ? resetAngle : 0, full = false, zoomFactor = 1, grab, hits = [], faces = [];
  const plan = new Image();
  const floorUnits = UNITS.filter(item => item.f === u.f);
  const geometry = UNIT_DRAWINGS;
  const outline = record.polygon || [];
  const neighbors = new Set((record.neighbors || []).map(item => item.id));
  const home = {x:u.x, y:u.y};
  let position = {...home};
  function redraw() {
    if (!panel.isConnected || !plan.naturalWidth) return;
    const w = Math.round(canvas.clientWidth), h = Math.round(canvas.clientHeight);
    if (!w || !h) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.round(w*dpr); canvas.height = Math.round(h*dpr);
    const cx = canvas.getContext('2d');
    cx.scale(dpr,dpr);
    cx.fillStyle = '#e6e5da';cx.fillRect(0,0,w,h);
    const cos = Math.cos(angle), sin = Math.sin(angle), tilt = three ? .64 : 1;
    const target = full ? {x:554,y:550} : position;
    const bb = outline.length ? outline : [[u.x-30,u.y-22],[u.x+30,u.y+22]];
    const extentX = Math.max(...bb.map(p=>Math.abs(p[0]-home.x)));
    const extentY = Math.max(...bb.map(p=>Math.abs(p[1]-home.y)));
    const viewW = full ? 1108*Math.abs(cos)+1100*Math.abs(sin)+35 : Math.max(195,2.5*extentX+90,2.0*extentY+80);
    const viewH = full ? (1108*Math.abs(sin)+1100*Math.abs(cos))*tilt+40 : Math.max(135,extentY*2.5*tilt+70,extentX*1.15+40);
    const scale = Math.min(w/viewW,h/viewH) * zoomFactor;
    const ox = w*.5-scale*(cos*target.x-sin*target.y);
    const oy = h*.53-scale*tilt*(sin*target.x+cos*target.y);
    const project = (x,y,z=0) => [ox+scale*(cos*x-sin*y), oy+scale*tilt*(sin*x+cos*y)-z];
    function path(points,fill,stroke,width=1) {
      cx.beginPath();points.forEach(([x,y],i)=>i ? cx.lineTo(x,y) : cx.moveTo(x,y));cx.closePath();
      if(fill){cx.fillStyle=fill;cx.fill()} if(stroke){cx.lineWidth=width;cx.strokeStyle=stroke;cx.stroke()}
    }
    if(three) {
      const corners=[[0,0],[1108,0],[1108,1100],[0,1100]].map(([x,y])=>project(x,y));
      path(corners.map(([x,y])=>[x+2,y+8]),'#b8b8a8');
    }
    cx.save(); cx.transform(scale*cos,scale*tilt*sin,-scale*sin,scale*tilt*cos,ox,oy);
    cx.drawImage(plan,0,0,1108,1100);
    if(three){cx.fillStyle='rgba(247,245,231,.26)';cx.fillRect(0,0,1108,1100)}
    cx.restore();
    const nearRange = Math.max(viewW,viewH)*1.15;
    const visible = floorUnits.filter(item=>full || Math.hypot(item.x-target.x,item.y-target.y)<nearRange)
      .sort((a,b)=>(sin*a.x+cos*a.y)-(sin*b.x+cos*b.y));
    faces=[];
    function prism(item) {
      const poly=geometry[item.id]?.polygon;
      if(!poly?.length)return;
      const selected=item.id===u.id, adjacent=neighbors.has(item.id);
      const base=poly.map(([x,y])=>project(x,y));
      const face=(points)=>faces.push({id:item.id,points});
      if(!three){
        face(base);
        if(selected||adjacent)path(base,selected?'rgba(23,115,100,.25)':'rgba(186,119,46,.13)',selected?'#00594d':'#976c41',selected?2.5:1.2);
        return;
      }
      const z=full?(selected?8:2):(selected?Math.min(28,8+scale*6):Math.min(12,3+scale*2.3));
      const top=base.map(([x,y])=>[x,y-z]);
      const edges=base.map((v,i)=>({a:i,b:(i+1)%base.length,sort:(v[1]+base[(i+1)%base.length][1])/2}))
        .sort((a,b)=>a.sort-b.sort);
      for(const {a,b} of edges) {
        face([base[a],base[b],top[b],top[a]]);
        path([base[a],base[b],top[b],top[a]],selected?'rgba(31,97,81,.82)':adjacent?'rgba(137,110,68,.42)':'rgba(100,105,94,.22)');
      }
      face(top);
      path(top,selected?'rgba(69,153,124,.64)':adjacent?'rgba(227,193,137,.38)':'rgba(255,255,242,.24)',
        selected?'#164e43':adjacent?'#a8834d':'#909786',selected?2:0.8);
    }
    for(const item of visible)if(item!==u)prism(item);
    prism(u);
    hits=[];
    function chip(item,selected){
      const [x,y]=project(item.x,item.y);
      if(x<8||x>w-8||y<15||y>h-9)return;
      const label=codeText(item);cx.font=(selected?'bold 15px':'bold 12px')+' Arial, sans-serif';
      const width=cx.measureText(label).width+16;
      const lift=selected?(three?35:20):0, center=y-lift, ht=selected?27:22;
      const lx=Math.min(w-width-2,Math.max(2,x-width/2)), ty=Math.max(2,center-ht);
      if(selected){cx.beginPath();cx.moveTo(x,y);cx.lineTo(x,ty+ht);cx.strokeStyle='#183e33';cx.lineWidth=2;cx.stroke();cx.beginPath();cx.arc(x,y,3.2,0,Math.PI*2);cx.fillStyle='#315c48';cx.fill()}
      cx.fillStyle=selected?'#173e34':'#fff9ec';cx.strokeStyle=selected?'#fff8e7':'#8d795b';cx.lineWidth=selected?1.7:1;
      cx.beginPath();cx.roundRect(lx,ty,width,ht,5);cx.fill();cx.stroke();cx.fillStyle=selected?'#fff':'#4b422e';
      cx.textBaseline='middle';cx.textAlign='center';cx.fillText(label,lx+width/2,ty+ht/2+1);
      hits.push({id:item.id,x:lx,y:ty,w:width,h:ht});
    }
    if(!full)for(const item of visible)if(neighbors.has(item.id))chip(item,false);
    chip(u,true);
  }
  function reset(){angle=three?resetAngle:0;position={...home};zoomFactor=1;redraw()}
  const zoomButton = (label,mult)=>btn(label,()=>{zoomFactor=Math.max(.55,Math.min(4,zoomFactor*mult));redraw()},'uv-tool');
  const scope=btn('عرض الدور بالكامل',()=>{full=!full;scope.textContent=full?'العودة إلى الوحدة':'عرض الدور بالكامل';scope.setAttribute('aria-pressed',String(full));reset()},'uv-tool');
  controls.append(scope,zoomButton('تكبير ＋',1.32),zoomButton('تصغير −',1/1.32));
  if(three)controls.append(btn('تدوير ↻',()=>{angle+=Math.PI/6;redraw()},'uv-tool'));
  controls.append(btn('ضبط العرض',()=>{full=false;scope.textContent='عرض الدور بالكامل';scope.setAttribute('aria-pressed','false');reset()},'uv-tool'));
  canvas.addEventListener('pointerdown',e=>{canvas.setPointerCapture(e.pointerId);grab={x:e.clientX,y:e.clientY,angle}});
  canvas.addEventListener('pointermove',e=>{if(grab&&three){angle=grab.angle+(e.clientX-grab.x)*.007;redraw()}});
  canvas.addEventListener('pointerup',e=>{
    if(!grab)return;
    if(Math.hypot(e.clientX-grab.x,e.clientY-grab.y)<6){
      const box=canvas.getBoundingClientRect(), x=e.clientX-box.left,y=e.clientY-box.top;
      const hit=hits.slice().reverse().find(p=>x>=p.x&&x<=p.x+p.w&&y>=p.y&&y<=p.y+p.h);
      const contains=({points})=>{let inside=false;for(let i=0,j=points.length-1;i<points.length;j=i++){
        const [ax,ay]=points[i],[bx,by]=points[j];if((ay>y)!==(by>y)&&x<(bx-ax)*(y-ay)/(by-ay)+ax)inside=!inside;
      }return inside};
      const target=hit||faces.slice().reverse().find(contains);
      if(target&&target.id!==u.id)navigateSite('unit/'+target.id);
    }
    grab=null;
  });
  canvas.addEventListener('pointercancel',()=>{grab=null});
  const caption=three?'منظور تخطيطي مبني على مسقط التأجير. اسحب أفقيًا لتدوير المشهد.':'مسقط التأجير الأصلي. العلامة الخضراء عند موقع الوحدة.';
  panel.append(canvas,controls,el('p','uv-caption',caption));
  plan.onload=redraw;
  plan.onerror=()=>canvas.replaceWith(el('p','uv-caption','تعذّر تحميل المسقط. يمكن فتح الرسم من تبويب تفاصيل الوحدة.'));
  plan.src=MAPS[u.f];
  const observer=new ResizeObserver(redraw);observer.observe(canvas);
  return {panel,dispose:()=>{observer.disconnect();plan.onload=null;plan.onerror=null}};
}

function unitPhotoRecords(u) {
  const gallery=UNIT_GALLERY;
  const exactIds=registeredPhotos(u.id).map(point=>point.photo);
  const sceneKey=gallery.zones[u.id] || ({b1:'hall',g:'ground',f1:'first',f2:'upper'})[u.f];
  const primary=gallery.photos.filter(photo=>exactIds.includes(photo.id));
  const contextual=gallery.photos.filter(photo=>photo.group===sceneKey && !exactIds.includes(photo.id));
  const others=gallery.photos.filter(photo=>photo.group!==sceneKey&&!exactIds.includes(photo.id));
  return {primary,contextual,others};
}

let unitSceneDispose;
function closeUnitScene(){if(unitSceneDispose){unitSceneDispose();unitSceneDispose=null}}
function showUnitDetails(u) {
  closeUnitScene(); shownUnit=u;
  document.title=codeText(u)+' | '+FLOORS[u.f]+' | هابينس بلازا';
  main.hidden=true;detail.hidden=false;
  const host=$('#unitcontent');host.replaceChildren();
  const record=UNIT_DRAWINGS[u.id] || {};
  const back=href('→  مخطط '+FLOORS[u.f],'#plan/'+u.f,'uv-back');
  const top=el('div','uv-topline');top.append(back);const sheet=sheetLink(u,'lv-sheet');if(sheet)top.append(sheet);
  const title=el('h1','uv-title',u.pending?'وحدة '+fmt(u.area):'الوحدة ');
  if(!u.pending){const id=el('bdi','',u.id);title.append(id)}title.tabIndex=-1;
  const floor=el('span','uv-floor',FLOORS[u.f]);
  const head=el('div','uv-heading');head.append(title,floor);
  const shell=el('div','uv-grid');
  const viewer=el('section','uv-viewer');viewer.setAttribute('aria-label','استكشاف الوحدة');
  const tabs=el('div','uv-tabs');tabs.setAttribute('role','tablist');tabs.setAttribute('aria-label','طريقة عرض الوحدة');
  const stage=el('div','uv-stage');stage.id='uv-stage';stage.setAttribute('role','tabpanel');
  const modes=[['plan','المسقط'],['real','صور الموقع'],['tour','الجولة البصرية'],['corridor','من الممر'],['3d','منظور 3D']];
  let sitePhotoPreview;
  function show(mode,updateURL=true){
    if(updateURL){history.replaceState(null,'',routeURL('unit/'+u.id,mode));lastRouteURL=location.href;lastBaseURL=location.href;}
    closeUnitScene();
    if(sitePhotoPreview)sitePhotoPreview.hidden=mode==='real';
    for(const t of tabs.children){const chosen=t.dataset.mode===mode;t.setAttribute('aria-selected',String(chosen));t.tabIndex=chosen?0:-1;if(chosen)stage.setAttribute('aria-labelledby',t.id)}
    stage.replaceChildren();
    if(mode==='real'){stage.append(photographicVisit(u));return}
    if(mode==='tour'){const visit=interactiveTour(u);stage.append(visit.panel);unitSceneDispose=visit.dispose;return}
    const scene=mode==='corridor'?createCorridorView(u,record):createUnitScene(u,record,mode);stage.append(scene.panel);unitSceneDispose=scene.dispose;
  }
  modes.forEach(([mode,label],i)=>{
    const b=btn(label,()=>show(mode),'uv-tab');b.dataset.mode=mode;b.id='uv-tab-'+mode;b.setAttribute('role','tab');b.setAttribute('aria-controls',stage.id);
    b.onkeydown=e=>{let n;if(e.key==='ArrowLeft')n=(i+1)%modes.length;else if(e.key==='ArrowRight')n=(i+modes.length-1)%modes.length;else if(e.key==='Home')n=0;else if(e.key==='End')n=modes.length-1;else return;e.preventDefault();const t=tabs.children[n];show(t.dataset.mode);t.focus()};
    tabs.append(b);
  });
  viewer.append(tabs,stage);
  const facts=el('aside','uv-facts');
  facts.append(el('h2','',u.title));
  const area=el('div','uv-area');area.append(el('span','','المساحة على مخطط التأجير'),el('strong','',fmt(u.area)));facts.append(area);
  const metricList=el('dl','uv-metrics');
  function metric(label,value){const row=el('div');row.append(el('dt','',label),el('dd','',value));metricList.append(row)}
  if(u.extra)metric(u.elab,fmt(u.extra));
  const dim=record.dimensions;
  const num=n=>Number(n).toLocaleString('ar-EG',{maximumFractionDigits:3});
  const printed=dim?.method==='dimensioned_drawing'||dim?.method==='printed'||dim?.method==='schedule';
  if(printed){
    if(dim.width>0&&dim.depth>0)metric('أبعاد داخلية مدوّنة على الرسم',num(dim.width)+' × '+num(dim.depth)+' م');
    else if(dim.width>0||dim.depth>0)metric('بُعد داخلي مدوّن على الرسم',num(dim.width||dim.depth)+' م');
    for(const seg of (dim.segments||[])){if(seg.value>0&&seg.label)metric(seg.label,num(seg.value)+' م')}
  }
  const cad=record.cadInterior;
  if(!printed&&cad&&!(cad.width>0&&cad.depth>0)&&(cad.width>0||cad.depth>0))metric(cad.width>0?'عرض داخلي تقريبي من الرسم المعماري':'عمق داخلي تقريبي من الرسم المعماري',num(cad.width||cad.depth)+' م');
  if(!printed&&cad?.width>0&&cad?.depth>0)metric('أبعاد داخلية تقريبية من الرسم المعماري',num(cad.width)+' × '+num(cad.depth)+' م');
  const approx=printed?(dim.width>0&&dim.depth>0?null:record.envelope):cad?.width>0&&cad?.depth>0?null:dim;
  if(approx?.width>0&&approx?.depth>0){
    metric('الأبعاد التقريبية للمستطيل المحيط',num(Math.min(approx.width,approx.depth))+' × '+num(Math.max(approx.width,approx.depth))+' م');
  }else if(!printed&&!(cad?.width>0&&cad?.depth>0)){metric('الأبعاد الطولية','راجع تفصيل اللوحة الأصلي أدناه')}
  metric('حالة التأجير',u.status);facts.append(metricList);
  if(approx?.method==='area_ratio')facts.append(el('p','uv-caption','الضلع القصير والطويل تقدير من شكل المسقط والمساحة الإجمالية المعلنة.'));
  else if(approx?.width&&approx?.depth)facts.append(el('p','uv-caption','تقدير للامتداد الكلي بين أطراف الوحدة من مقياس رسم اللوحة. راجع شكل الأركان والارتدادات في تفصيل الوحدة.'));
  if(u.note)facts.append(el('p','uv-note',u.note));
  const actions=el('div','uv-actions');actions.append(btn('طلب معاينة الوحدة',()=>booking(u),'action'),makeCompareButton(u),btn('مقارنة الوحدات',openComparison,'secondary'));facts.append(actions);
  const supporting=el('div','uv-supporting');
  if(u.id==='B01')supporting.append(btn('مشاهدة تصميم الهايبر',()=>picture('hyper'),'under'));
  supporting.append(href('مواصفات التسليم','#handover','under'));facts.append(supporting);
  const relatedPhotos=unitPhotoRecords(u);
  const previewPhoto=relatedPhotos.primary[0]||relatedPhotos.contextual[0];
  if(previewPhoto){
    sitePhotoPreview=btn('',()=>{
      show('real');tabs.querySelector('[data-mode=real]').focus({preventScroll:true});
      viewer.scrollIntoView({block:'start',behavior:'instant'});
    },'uv-real-preview');
    const previewImg=img(previewPhoto.src,'');
    const teaser=el('span');teaser.append(el('strong','',relatedPhotos.primary.length?'واجهة الوحدة على الطبيعة':UNIT_GALLERY.groups[previewPhoto.group]),el('small','','فتح صور الموقع ←'));
    sitePhotoPreview.append(previewImg,teaser);facts.append(sitePhotoPreview);
  }
  shell.append(viewer,facts);

  const lower=el('div','uv-lower');
  const neighbors=el('section','uv-neighbors');
  neighbors.append(el('h2','','الوحدات المجاورة على الرسم'));
  const sides={left:'يسار الرسم',right:'يمين الرسم',top:'أعلى الرسم',bottom:'أسفل الرسم'};
  const have=new Set();
  function links(items,isBorder){
    const list=el('div','uv-neighbor-list');
    for(const item of items){
      const id=typeof item==='string'?item:item.id, neighbor=byId.get(id);
      if(!neighbor||have.has(id)||id===u.id)continue;
      have.add(id);
      const link=href('','#unit/'+id,'uv-neighbor');
      link.append(el('bdi','',codeText(neighbor)),el('span','',isBorder?(sides[item.side]||'حد مشترك'):'على نفس الدور'),el('small','',fmt(neighbor.area)));
      list.append(link);
    }return list;
  }
  const walls=links(record.neighbors||[],true);
  if(walls.children.length)neighbors.append(el('p','uv-caption','وحدات تشترك مع الوحدة في حد ظاهر على المسقط.'),walls);
  const close=links((record.nearby||[]).slice(0,5),false);
  if(close.children.length){neighbors.append(el('h3','','وحدات قريبة على نفس الدور'),el('p','uv-caption','القرب محسوب من مواضع الأرقام على المسقط.'),close)}
  if(!walls.children.length&&!close.children.length)neighbors.append(el('p','uv-caption','راجع حدود الوحدة وأرقام المحلات المحيطة في الرسم.'));
  const drawing=el('section','uv-drawing');drawing.append(el('h2','','تفصيل الوحدة من اللوحة'));
  const showSource=()=>{openBox('لوحة الأبعاد · '+codeText(u));body.append(sourceDetail(u,record,true),el('p','caption','اسحب لتحريك الرسم وكبّر لقراءة الأبعاد المكتوبة حول حدود الوحدة.'))};
  const cropButton=btn('',showSource,'uv-crop');
  cropButton.setAttribute('aria-label','تكبير لوحة الأبعاد للوحدة '+codeText(u));cropButton.append(sourceDetail(u,record,false));
  const sourceActions=el('div','uv-supporting');sourceActions.append(btn('تكبير لوحة الأبعاد',showSource,'under'),href('فتح مسقط الدور الأصلي ↗','assets/drawings/'+u.f+'.png','under'));
  drawing.append(cropButton,sourceActions);
  lower.append(neighbors,drawing);
  host.append(top,head,shell,lower);
  const requested=new URLSearchParams(location.search).get('view');show(modes.some(([id])=>id===requested)?requested:(registeredPhotos(u.id).length?'real':'plan'),false);
  window.scrollTo({top:0,behavior:'instant'});title.focus({preventScroll:true});
}

function sourceDetail(u,record,large){
  // Link the unit to its own window on the unmodified architectural layer.
  const region=el('div','uv-source-detail');
  const preview=el('canvas');preview.setAttribute('role','img');preview.setAttribute('aria-label','الأبعاد والتقسيمات كما تظهر في اللوحة الأصلية للوحدة '+codeText(u));
  region.append(preview);
  const source=new Image(), poly=record.polygon||[];
  let radius=Math.max(28,...poly.map(([x,y])=>Math.abs(x-u.x)),...poly.map(([x,y])=>Math.abs(y-u.y)));
  radius=Math.min(575,Math.max(40,radius*1.19));
  let zoom=1, pos={x:u.x,y:u.y}, drag=null, transform;
  const draw=()=>{
    if(!preview.isConnected||!source.naturalWidth)return;
    const w=preview.clientWidth,h=preview.clientHeight;
    if(!w||!h)return;
    const size=Math.min(devicePixelRatio||1,2.5);
    preview.width=Math.round(w*size);preview.height=Math.round(h*size);
    const c=preview.getContext('2d');c.scale(size,size);c.fillStyle='#fff';c.fillRect(0,0,w,h);
    const scale=Math.min(w,h)/(2*radius)*zoom;
    transform=scale;
    c.translate(w/2,h/2);c.scale(scale,scale);c.translate(-pos.x,-pos.y);c.drawImage(source,0,0,1108,1100);
  };
  source.onload=draw;source.src='assets/drawings/'+u.f+'.png';
  const observer=new ResizeObserver(()=>{if(preview.isConnected)draw();else observer.disconnect()});observer.observe(preview);
  if(large){
    preview.className='uv-detail-large';
    const tools=el('div','uv-controls');
    for(const [label,amount] of [['تكبير ＋',1.45],['تصغير −',1/1.45]])tools.append(btn(label,()=>{zoom=Math.min(8,Math.max(.25,zoom*amount));draw()},'uv-tool'));
    tools.append(btn('العودة إلى الوحدة',()=>{pos={x:u.x,y:u.y};zoom=1;draw()},'uv-tool'));
    preview.onpointerdown=e=>{drag={x:e.clientX,y:e.clientY,start:{...pos}};preview.setPointerCapture(e.pointerId)};
    preview.onpointermove=e=>{if(drag&&transform){pos.x=Math.max(0,Math.min(1108,drag.start.x-(e.clientX-drag.x)/transform));pos.y=Math.max(0,Math.min(1100,drag.start.y-(e.clientY-drag.y)/transform));draw()}};
    preview.onpointerup=preview.onpointercancel=()=>drag=null;region.append(tools);
    const release=()=>{observer.disconnect();source.onload=null;dialog.removeEventListener('close',release)};dialog.addEventListener('close',release);
  }
  return region;
}
