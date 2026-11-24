// Positions are fractions of the untouched photograph. A pin is drawn only on its registered frame.
function registeredPhotos(unitId) {
  return (LOCATION_LINKS.photos[unitId] || []).filter(point =>
    Number.isFinite(point.x) && Number.isFinite(point.y) &&
    point.x >= 0 && point.x <= 1 && point.y >= 0 && point.y <= 1 &&
    typeof point.note === 'string' && point.note.trim() &&
    UNIT_GALLERY.photos.some(photo => photo.id === point.photo));
}

function locationUnitLink(u, mode, text, className, shot) {
  const link = href(text, '#unit/' + u.id, className);
  link.href = routeURL('unit/' + u.id, mode, shot);
  link.dataset.unitView = mode;
  if(shot) link.dataset.shot = shot;
  return link;
}

function unitSheet(u) {
  for (const [page, links] of Object.entries(DOCUMENT_LINKS.leasing)) {
    if (+page < 38) continue;
    if (links.some(([, target]) => typeof target === 'string' &&
        target.startsWith('?') && new URLSearchParams(target.slice(1)).get('unit') === u.id)) return +page;
  }
  return null;
}

function sheetLink(u, className) {
  const page = unitSheet(u);
  if (!page) return null;
  const link = el('a', className, 'بطاقة الوحدة PDF');
  const url = new URL(routeURL('unit/' + u.id), document.baseURI);
  url.searchParams.set('doc','leasing');
  url.searchParams.set('page',page);
  link.href = url.href;
  link.onclick = event => {
    if (event.button || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    openDocument('leasing',page);
  };
  return link;
}

function makeSV(tag, attrs) {
  const item = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [name,value] of Object.entries(attrs)) item.setAttribute(name,value);
  return item;
}

function locationMap(u, wide = false, camera = null) {
  const record = UNIT_DRAWINGS[u.id];
  const points = record.polygon;
  const xs = points.map(p => p[0]), ys = points.map(p => p[1]);
  if(camera){xs.push(camera.x);ys.push(camera.y)}
  const left = Math.min(...xs), right = Math.max(...xs), top = Math.min(...ys), bottom = Math.max(...ys);
  const width = Math.min(1108, Math.max(210,(right-left)*1.7,(bottom-top)*2.05));
  const height = Math.min(1100, Math.max(width*.78, (bottom-top)*1.5));
  const clamp = (v, max) => Math.min(Math.max(0,v),max);
  const crop = [clamp((left+right-width)/2,1108-width),clamp((top+bottom-height)/2,1100-height),width,height];
  const box = wide ? [0,0,1108,1100] : crop;
  const scale = box[2]/320;
  const svg = makeSV('svg',{viewBox:box.join(' '),role:'img','aria-label':'موضع '+codeText(u)+' على مسقط '+FLOORS[u.f], preserveAspectRatio:'xMidYMid meet'});
  svg.append(makeSV('image',{href:MAPS[u.f],x:0,y:0,width:1108,height:1100,preserveAspectRatio:'none'}));
  svg.append(makeSV('polygon',{points:points.map(pair=>pair.join(',')).join(' '),fill:'#00765d','fill-opacity':'.48',stroke:'#004331','stroke-width':2.2*scale,'stroke-linejoin':'round'}));
  const [x,y] = [u.x,u.y], label = codeText(u);
  const chip = Math.max(38, 14 + label.length*8)*scale;
  const chipX = Math.max(box[0]+chip/2+2*scale, Math.min(box[0]+box[2]-chip/2-2*scale, x));
  const below = y < box[1]+38*scale;
  const chipY = below ? y+18*scale : y-34*scale;
  svg.append(makeSV('line',{x1:x,y1:y,x2:chipX,y2:below?chipY:chipY+20*scale,stroke:'#073d31','stroke-width':1.8*scale}),
    makeSV('circle',{cx:x,cy:y,r:3.4*scale,fill:'#063d30',stroke:'white','stroke-width':1.45*scale}),
    makeSV('rect',{x:chipX-chip/2,y:chipY,width:chip,height:20*scale,rx:4*scale,fill:'#123e34',stroke:'#fff','stroke-width':scale}));
  const text = makeSV('text',{x:chipX,y:chipY+14*scale,'font-family':'Arial,sans-serif','font-weight':'700','font-size':12.6*scale,'text-anchor':'middle',fill:'white'});
  text.textContent = label;
  svg.append(text);
  if(camera){
    const marker=makeSV('g',{'class':'lv-viewpoint','aria-label':'نقطة المشاهدة واتجاه النظر'});
    const icon=makeSV('g',{'class':'lv-look',transform:'rotate('+camera.bearing+')'});
    icon.append(makeSV('path',{d:'M 0 0 L -10 -18 Q 0 -23 10 -18 Z',fill:'#3984a1','fill-opacity':'.70',stroke:'#19485b','stroke-width':1.1}));
    marker.append(icon,makeSV('circle',{cx:0,cy:0,r:4.3,fill:'#164e67',stroke:'white','stroke-width':1.7}));
    marker.setAttribute('transform','translate('+camera.x+' '+camera.y+') scale('+scale+')');
    svg.append(marker);
  }
  return svg;
}

function locationMapPanel(u,camera=null) {
  const panel = el('section','lv-map');
  const header=el('div','lv-map-head');
  const title=el('h3','','موقع الوحدة على المسقط');
  let wide = false;
  const holder=el('div','lv-map-graphic');
  const toggle = btn('الدور بالكامل',()=>{
    wide = !wide;
    toggle.textContent = wide?'تكبير الوحدة':'الدور بالكامل';
    toggle.setAttribute('aria-pressed',String(wide));
    holder.replaceChildren(locationMap(u,wide,camera));
  },'lv-text-button');
  toggle.setAttribute('aria-pressed','false');
  header.append(title,toggle);
  holder.append(locationMap(u,false,camera));
  panel.append(header,holder);
  const bottom=el('div','lv-map-foot');
  bottom.append(el('span','',FLOORS[u.f]),el('bdi','',codeText(u)));
  if(camera)bottom.append(el('small','lv-look-key','الأزرق · اتجاه النظر'));
  panel.append(bottom);
  return panel;
}

// The photograph and its pins share one natural-aspect coordinate system, including in the lightbox.
function locationPhotograph(u, photo, currentPoint, showOthers, view) {
  const board = el('div','lv-shot-board');
  const useOriginal = Boolean(currentPoint || showOthers) && photo.original;
  const image = el('img');
  image.alt = photo.caption;
  image.onload = () => {board.style.setProperty('--frame-ratio',String(image.naturalWidth/image.naturalHeight))};
  image.src = useOriginal ? photo.original : photo.src;
  board.append(image);
  function addPoint(unit, point, selected) {
    const pin = selected ? el('span','lv-pin is-selected') : locationUnitLink(unit,view,'','lv-pin',photo.id);
    pin.style.setProperty('--px',point.x*100+'%');
    pin.style.setProperty('--py',point.y*100+'%');
    if(point.y < .14) pin.classList.add('is-below');
    if(point.x < .09) pin.classList.add('edge-left');
    if(point.x > .91) pin.classList.add('edge-right');
    pin.setAttribute('aria-label',(selected?'موضع الوحدة ':'فتح الوحدة ')+codeText(unit));
    const text=el('bdi','',codeText(unit));
    pin.append(text,el('i'));
    board.append(pin);
  }
  if(showOthers){
    for(const [unitId, anchors] of Object.entries(LOCATION_LINKS.photos)){
      if(unitId===u.id || !byId.has(unitId))continue;
      const point=anchors.find(p=>p.photo===photo.id);
      if(point)addPoint(byId.get(unitId),point,false);
    }
  }
  if(currentPoint)addPoint(u,currentPoint,true);
  return board;
}

function photographicVisit(u, tour = false) {
  const gallery=UNIT_GALLERY;
  const view = tour ? 'tour':'real';
  const zone = gallery.zones[u.id] || ({g:'ground',f1:'first',f2:'upper',b1:'hall'})[u.f];
  const registered=registeredPhotos(u.id);
  const exact=registered.map(p=>gallery.photos.find(photo=>photo.id===p.photo));
  const context=gallery.photos.filter(p=>p.group===zone && !exact.some(other=>other.id===p.id));
  const lanes=new Map();
  if(exact.length)lanes.set('marked',{title:'واجهات الوحدة المحددة',photos:exact});
  if(context.length)lanes.set('context',{title:gallery.groups[zone],photos:context});
  if(!tour) for(const [key,title] of Object.entries(gallery.groups)){
    if(key===zone && context.length)continue;
    const photos=gallery.photos.filter(p=>p.group===key);
    if(photos.length)lanes.set(key,{title,photos});
  }
  const panel=el('section','lv-visit');
  const head=el('div','lv-heading');
  const text=el('div');
  text.append(el('span','lv-overline',FLOORS[u.f]),el('h2','',tour?'الجولة البصرية':'صور الموقع'));
  const select=el('select','lv-select');select.setAttribute('aria-label','مجموعة المشاهد');
  for(const [key,lane] of lanes)opt(select,lane.title,key);
  head.append(text);if(lanes.size>1)head.append(select);panel.append(head);
  if(!lanes.size){panel.append(locationMapPanel(u));return panel}
  const layout=el('div','lv-layout');
  const photoBlock=el('div','lv-photoblock');
  const frame=el('div','lv-shot');
  const caption=el('div','lv-caption');
  const photoName=el('strong'), count=el('span','lv-count');
  caption.append(photoName,count);
  const detail=el('p','lv-context');
  const actions=el('div','lv-actions');
  const light=btn('تكبير الصورة',()=>showLightbox(false),'uv-tool');
  const original=btn('الصورة الأصلية',()=>showLightbox(true),'uv-tool');
  let otherPins=false;
  const adjacent=btn('إظهار أرقام الواجهات',()=>{otherPins=!otherPins;draw()},'uv-tool');
  actions.append(light,original,adjacent);
  photoBlock.append(frame,caption,detail,actions);
  layout.append(photoBlock,locationMapPanel(u));
  panel.append(layout);
  const filmstrip=el('div','lv-filmstrip');filmstrip.setAttribute('aria-label','اختيار المشهد');
  const nav=el('div','lv-nav');
  const prev=btn('السابق',()=>move(idx-1),'uv-tool');
  const next=btn('التالي',()=>move(idx+1),'uv-tool');
  nav.append(prev,filmstrip,next);panel.append(nav);
  let photos=[], idx=0;
  function showLightbox(raw){
    const photo=photos[idx], point=registered.find(p=>p.photo===photo.id);
    openBox(photo.caption+' · '+codeText(u));
    const shot=el('div','lv-shot lv-expanded');
    shot.append(locationPhotograph(u,raw?{...photo,src:photo.original||photo.src}:photo,point,!raw&&otherPins,view));body.append(shot);
    body.append(el('p','caption',detail.textContent));
  }
  function draw(){
    const photo=photos[idx], point=registered.find(p=>p.photo===photo.id);
    const other=Object.entries(LOCATION_LINKS.photos).some(([id,ps])=>id!==u.id && ps.some(p=>p.photo===photo.id));
    adjacent.hidden=!other;
    adjacent.setAttribute('aria-pressed',String(otherPins));
    adjacent.textContent=otherPins?'إخفاء أرقام الواجهات':'إظهار أرقام الواجهات';
    frame.replaceChildren(locationPhotograph(u,photo,point,otherPins&&other,view));
    photoName.textContent=photo.caption;
    count.textContent=(idx+1).toLocaleString('ar-EG')+' / '+photos.length.toLocaleString('ar-EG');
    original.hidden=!photo.original || Boolean(point) || (otherPins&&other);
    detail.textContent=point?(point.basis==='field-confirmed'?'موضع الوحدة '+codeText(u)+' مؤكد من الموقع.':point.basis==='approximate'?'موضع تقريبي للوحدة '+codeText(u)+' على الواجهة بحسب ترتيب الوحدات في المسقط.':point.basis==='facade-projection'?'موضع الوحدة '+codeText(u)+' مُسقط على امتداد الواجهة من المخطط.':'العلامة على واجهة الوحدة '+codeText(u)+' وفق المطابقة المعمارية.'):
      photo.group==='hall'?'صورة عامة لقاعة بالمشروع. موضع الوحدة محدد على المسقط المرافق.':
      'مشهد عام من الموقع. موضع الوحدة '+codeText(u)+' محدد على المسقط المرافق.';
    for(const [i,button] of [...filmstrip.children].entries())button.setAttribute('aria-current',String(i===idx));
    const current=filmstrip.children[idx];
    if(current && panel.isConnected)filmstrip.scrollLeft+=current.getBoundingClientRect().left-filmstrip.getBoundingClientRect().left-(filmstrip.clientWidth-current.clientWidth)/2;
    prev.disabled=next.disabled=photos.length<2;
  }
  function rememberShot(){
    const path=routeURL('unit/'+u.id,view,photos[idx].id);
    history.replaceState(history.state,'',path);
    lastRouteURL=lastBaseURL=location.href;
  }
  function move(index){idx=(index+photos.length)%photos.length;draw();rememberShot()}
  function change(shot){
    photos=lanes.get(select.value).photos;idx=Math.max(0,photos.findIndex(p=>p.id===shot));otherPins=false;
    filmstrip.replaceChildren();
    photos.forEach((photo,i)=>{
      const cell=btn('',()=>move(i),'lv-thumb');cell.setAttribute('aria-label',photo.caption+'، مشهد '+(i+1));
      const thumb=img(photo.src,'');thumb.loading='lazy';cell.append(thumb);filmstrip.append(cell);
    });
    draw();
  }
  const shot=new URLSearchParams(location.search).get('shot');
  if(shot) for(const [key,lane] of lanes)if(lane.photos.some(p=>p.id===shot)){select.value=key;break}
  select.onchange=()=>{change();rememberShot()};
  change(shot);
  return panel;
}

function nativeTourPanel(u){
  const panel=el('div','lv-native');
  const title=el('div');
  title.append(el('h3','','الجولة البانورامية 360°'));
  const direct=validUnitTourURL(LOCATION_LINKS.tours[u.id]);

  const full='https://alhabeebconst.com/Virtual-Tour/viewer/index.php?code=a87ff679a2f3e71d9181a67b7542122c';
  const target=direct || full;
  title.append(el('p','',direct?'محطة الوحدة '+codeText(u):'جولة هابينس بلازا العامة'));
  panel.append(title);
  if(target){
    const link=el('a','lv-primary',direct?'افتح محطة الوحدة ↗':'افتح الجولة العامة ↗');
    link.href=target;link.target='_blank';link.rel='noopener noreferrer';panel.append(link);
  }
  return panel;
}
