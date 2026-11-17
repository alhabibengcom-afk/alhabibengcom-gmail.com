// Perspective projection of the original equirectangular scenes, with a CPU path for devices without WebGL.
const PANORAMA_SCENES = [
  {id:'575',title:'الممر التجاري ١',src:'assets/panoramas/575.webp',start:[.48,.49],camera:{x:931.3,y:251.8,northOffset:.898}},
  {id:'576',title:'الممر التجاري ٢',src:'assets/panoramas/576.webp',start:[.54,.50],camera:{x:884.8,y:275.9,northOffset:-.086}}
];

function unitPanorama(u) {
  const marks=(LOCATION_LINKS.panoramas?.[u.id] || []).filter(m=>
    PANORAMA_SCENES.some(s=>s.id===m.scene) && Number.isFinite(m.x) && Number.isFinite(m.y) &&
    m.x>=0 && m.x<=1 && m.y>=0 && m.y<=1);
  const root=el('section','lv-pano');
  const header=el('div','lv-heading');
  const title=el('div');title.append(el('span','lv-overline','بانوراما تصميمية · 360°'),el('h2','','جولة الممرات'));
  const pick=el('select','lv-select');pick.setAttribute('aria-label','مشهد البانوراما');
  for(const scene of PANORAMA_SCENES)opt(pick,scene.title+(marks.some(m=>m.scene===scene.id)?' · موقع الوحدة':''),scene.id);
  header.append(title,pick);root.append(header);
  const viewport=el('div','lv-pano-window');
  const canvas=el('canvas');canvas.tabIndex=0;canvas.setAttribute('role','img');
  canvas.setAttribute('aria-label','بانوراما الممر. استخدم الأسهم لتغيير اتجاه النظر وعلامتي الجمع والطرح للتكبير والتصغير.');
  const dots=el('div','lv-panopins');
  let pinNodes=[],showNumbers=true;
  const status=el('p','lv-pano-status');status.setAttribute('role','status');
  const flag=el('span','lv-pano-flag','360°');
  viewport.append(canvas,dots,flag,status);
  const controls=el('div','lv-pano-tools');
  const layout=el('div','lv-layout');const stage=el('div','lv-photoblock');
  stage.append(viewport,controls);
  const message=el('p','lv-context');stage.append(message);
  const mapHolder=el('div','lv-map-holder');layout.append(stage,mapHolder);root.append(layout);
  let viewpoint;
  const tau=Math.PI*2, clamp=(n,min,max)=>Math.max(min,Math.min(max,n));
  const context=canvas.getContext('2d',{alpha:false});
  let scene, anchor, yaw=0, pitch=0, fov=82, drag, source, lookup, output, frame=0;
  let token=0,closed=false;
  const rad=deg=>deg*Math.PI/180;
  function lookAt(point){yaw=(point[0]-.5)*tau;pitch=(.5-point[1])*Math.PI;queue()}
  function turn(dx,dy){
    yaw=(yaw+dx)%tau;pitch=clamp(pitch+dy,rad(-78),rad(78));queue();
  }
  function zoom(step){fov=clamp(fov+step,36,110);queue()}
  const control=(name,fn)=>btn(name,fn,'uv-tool');
  const home=control('إعادة التوجيه',()=>{fov=82;lookAt(anchor?[anchor.x,anchor.y]:scene.start)});
  const nearby=control('أرقام الواجهات',()=>{showNumbers=!showNumbers;nearby.setAttribute('aria-pressed',String(showNumbers));queue()});
  nearby.setAttribute('aria-pressed',String(showNumbers));
  controls.append(nearby,control('يمين',()=>turn(rad(20),0)),control('يسار',()=>turn(rad(-20),0)),
    control('تكبير ＋',()=>zoom(-10)),control('تصغير −',()=>zoom(10)),home);
  function queue(){if(!closed&&!frame)frame=requestAnimationFrame(draw)}
  function draw(){
    frame=0;if(!source||!context||closed||!canvas.isConnected)return;
    const cw=canvas.clientWidth,ch=canvas.clientHeight;
    if(!cw||!ch)return;
    const ratio=Math.min(1.55,window.devicePixelRatio||1,930/cw,630/ch);
    const w=Math.max(1,Math.round(cw*ratio)),h=Math.max(1,Math.round(ch*ratio));
    const focal=w/(2*Math.tan(rad(fov)/2)),cp=Math.cos(pitch),sp=Math.sin(pitch);
    if(w!==canvas.width||h!==canvas.height){canvas.width=w;canvas.height=h;output=null;lookup=null}
    if(!output)output=context.createImageData(w,h);
    const sw=source.width,sh=source.height,key=[w,h,fov,pitch,sw,sh].join('|');
    if(!lookup || lookup.key!==key){
      const us=new Int32Array(w*h),vs=new Int32Array(w*h);
      for(let y=0,k=0;y<h;y++){
        const ny=(h/2-y-.5)/focal, z=cp-ny*sp, vy=ny*cp+sp;
        for(let x=0;x<w;x++,k++){
          const nx=(x+.5-w/2)/focal;
          us[k]=Math.floor((.5+Math.atan2(nx,z)/tau)*sw);
          const phi=Math.atan2(vy,Math.sqrt(nx*nx+z*z));
          vs[k]=clamp(Math.floor((.5-phi/Math.PI)*sh),0,sh-1)*sw;
        }
      }
      lookup={key,us,vs};
    }
    const offset=(Math.round(yaw/tau*sw)%sw+sw)%sw, out=new Uint32Array(output.data.buffer);
    for(let i=0;i<out.length;i++){let x=lookup.us[i]+offset;x%=sw;out[i]=source.rgba[lookup.vs[i]+x]}
    context.putImageData(output,0,0);
    if(viewpoint){
      viewpoint.bearing=yaw*180/Math.PI+scene.camera.northOffset;
      mapHolder.querySelector('.lv-look')?.setAttribute('transform','rotate('+viewpoint.bearing+')');
    }
    for(const {pt,node,selected} of pinNodes){
      if(!selected&&!showNumbers){node.hidden=true;continue}
      const lng=(pt.x-.5)*tau-yaw,lat=(.5-pt.y)*Math.PI;
      const vx=Math.sin(lng)*Math.cos(lat),sy=Math.sin(lat),sz=Math.cos(lng)*Math.cos(lat);
      const vy=sy*cp-sz*sp,vz=sy*sp+sz*cp;
      const px=.5+vx*focal/(vz*w),py=.5-vy*focal/(vz*h);
      node.hidden=vz<=0 || px<.025||px>.975||py<.09||py>.98;
      node.style.left=px*100+'%';node.style.top=py*100+'%';
    }
  }
  function buildPins(){
    dots.replaceChildren();pinNodes=[];
    for(const [id,list] of Object.entries(LOCATION_LINKS.panoramas || {})){
      const pt=list.find(m=>m.scene===scene.id), unit=byId.get(id);
      if(!pt||!unit)continue;
      const selected=id===u.id;
      const node=selected?el('span','lv-panopin is-selected'):locationUnitLink(unit,'tour','','lv-panopin');
      if(!selected){node.href=routeURL('unit/'+id,'tour',null,scene.id);node.dataset.scene=scene.id;}
      node.setAttribute('aria-label',(selected?'موضع الوحدة ':'فتح الوحدة ')+codeText(unit)+' في البانوراما');
      node.append(el('bdi','',codeText(unit)),el('i'));node.hidden=true;
      pinNodes.push({pt,node,selected});dots.append(node);
    }
    nearby.hidden=!pinNodes.some(p=>!p.selected);
  }
  function change(){
    scene=PANORAMA_SCENES.find(s=>s.id===pick.value) || PANORAMA_SCENES[0];
    anchor=marks.find(m=>m.scene===scene.id);buildPins();
    viewpoint=u.f==='f1'?{...scene.camera,bearing:0}:null;mapHolder.replaceChildren(locationMapPanel(u,viewpoint));
    home.textContent=anchor?'توجيه إلى الوحدة':'إعادة التوجيه';
    message.textContent=anchor?(u.f==='g'?'واجهة '+codeText(u)+' في الدور الأرضي، كما تظهر من الدور الأول.':'علامة '+codeText(u)+' تحدد الواجهة في هذا المشهد التصميمي.'):'بانوراما للممر التجاري. موقع '+codeText(u)+' محدد على المسقط المرافق.';
    const request=++token;source=null;lookup=null;
    status.hidden=false;status.textContent='جارٍ تحميل البانوراما…';
    if(context)context.clearRect(0,0,canvas.width,canvas.height);
    const image=new Image();
    image.onload=()=>{
      if(closed||request!==token)return;
      const s=document.createElement('canvas');s.width=image.naturalWidth;s.height=image.naturalHeight;
      try{
        const c=s.getContext('2d',{willReadFrequently:true});c.drawImage(image,0,0);
        source={rgba:new Uint32Array(c.getImageData(0,0,s.width,s.height).data.buffer),width:s.width,height:s.height};
        status.hidden=true;fov=82;lookAt(anchor?[anchor.x,anchor.y]:scene.start);
      }catch{failure()}
    };
    function failure(){if(closed||request!==token)return;status.hidden=false;status.textContent='تعذّر تحميل العرض البانورامي. ';status.append(href('فتح صورة المشهد',scene.src,'under'))}
    image.onerror=failure;image.src=scene.src;
  }
  canvas.addEventListener('pointerdown',e=>{canvas.setPointerCapture(e.pointerId);drag={id:e.pointerId,x:e.clientX,y:e.clientY}});
  canvas.addEventListener('pointermove',e=>{if(!drag||drag.id!==e.pointerId)return;const speed=rad(fov)/Math.max(150,canvas.clientWidth);turn((drag.x-e.clientX)*speed,(e.clientY-drag.y)*speed);drag.x=e.clientX;drag.y=e.clientY});
  canvas.onpointerup=canvas.onpointercancel=()=>{drag=null};
  canvas.onkeydown=e=>{
    const actions={ArrowLeft:()=>turn(-.16,0),ArrowRight:()=>turn(.16,0),ArrowUp:()=>turn(0,.14),ArrowDown:()=>turn(0,-.14),'+':()=>zoom(-10),'=':()=>zoom(-10),'-':()=>zoom(10),Home:()=>home.click()};
    if(actions[e.key]){e.preventDefault();actions[e.key]()}
  };
  const requestedScene=new URLSearchParams(location.search).get('scene');
  pick.value=PANORAMA_SCENES.some(s=>s.id===requestedScene)?requestedScene:marks[0]?.scene||PANORAMA_SCENES[0].id;
  pick.onchange=()=>{
    history.replaceState(history.state,'',routeURL('unit/'+u.id,'tour',null,pick.value));lastRouteURL=lastBaseURL=location.href;change();
  };
  const observer=new ResizeObserver(queue);observer.observe(canvas);change();
  return {panel:root,dispose(){closed=true;token++;cancelAnimationFrame(frame);observer.disconnect();source=null;lookup=null;output=null}};
}

function interactiveTour(u){
  const root=el('section','lv-tour');
  const switches=el('div','lv-switches');
  const display=el('div');
  const options=[['panorama','بانوراما الممر 360°'],['photos','جولة بالصور']];
  let current=null,cleanup;
  function show(mode){
    if(current===mode)return;
    cleanup?.();cleanup=null;current=mode;
    for(const b of switches.children)b.setAttribute('aria-pressed',String(b.dataset.kind===mode));
    if(mode==='panorama'){
      const s=unitPanorama(u);display.replaceChildren(s.panel);cleanup=s.dispose;
    }else display.replaceChildren(photographicVisit(u,true));
  }
  for(const [id,title] of options){const b=btn(title,()=>{
    if(id==='panorama'){
      const scene=LOCATION_LINKS.panoramas?.[u.id]?.[0]?.scene || PANORAMA_SCENES[0].id;
      history.replaceState(history.state,'',routeURL('unit/'+u.id,'tour',null,scene));
    }else{
      const photo=registeredPhotos(u.id)[0]?.photo || (unitPhotoRecords(u).contextual[0]?.id);
      history.replaceState(history.state,'',routeURL('unit/'+u.id,'tour',photo));
    }
    lastRouteURL=lastBaseURL=location.href;show(id);
  },'uv-tool');b.dataset.kind=id;switches.append(b)}
  root.append(switches,display);
  const fromShot=new URLSearchParams(location.search).has('shot');
  const hasPanorama=LOCATION_LINKS.panoramas?.[u.id]?.length;
  show(!fromShot&&(hasPanorama||new URLSearchParams(location.search).has('scene')||!registeredPhotos(u.id).length)?'panorama':'photos');
  root.append(nativeTourPanel(u));
  return {panel:root,dispose:()=>cleanup?.()};
}
