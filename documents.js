// Read local PDFs as pages in the same tab, including browsers without a PDF plug-in.
const docByPath=new Map(Object.entries(SITE_DOCUMENTS).map(([key,doc])=>[new URL(doc.file,document.baseURI).pathname,key]));
function currentDocument(){
  const key=new URLSearchParams(location.search).get('doc');
  return Object.hasOwn(SITE_DOCUMENTS,key)?key:null;
}
function documentURL(key,page){
  const url=new URL(location.href);
  url.searchParams.set('doc',key);
  if(page>1)url.searchParams.set('page',page);
  else url.searchParams.delete('page');
  return url;
}
function openDocument(key,page=1){
  const url=documentURL(key,page);
  history.pushState({readerEntry:true},'',url);
  lastRouteURL=location.href;
  showDocument(key,page);
}
function closeReaderOrDialog(){
  if(!currentDocument()){dialog.close();return}
  if(history.state?.readerEntry){history.back();return}
  const url=new URL(location.href);
  url.searchParams.delete('doc');url.searchParams.delete('page');
  history.replaceState(null,'',url);
  lastRouteURL=location.href;
  dialog.close();
}
function syncDocument(){
  const key=currentDocument();
  if(key)showDocument(key,Number(new URLSearchParams(location.search).get('page'))||1);
  else if(dialog.open&&body.querySelector('.pdf-reader'))dialog.close();
}
function showDocument(key,initialPage=1){
  const doc=SITE_DOCUMENTS[key];
  openBox(doc.title);
  const reader=el('div','pdf-reader');
  const pageImage=el('img','pdf-page');
  const canvas=el('div','pdf-sheet'),links=el('div','pdf-links');canvas.append(pageImage,links);
  const controls=el('div','pager');
  const count=el('span');
  const choose=el('input','pdf-jump');choose.type='number';choose.min=1;choose.max=doc.pages;choose.step=1;
  choose.setAttribute('aria-label','رقم الصفحة');
  const unitLink=el('a','secondary');unitLink.hidden=true;
  const previous=btn('السابق',()=>setPage(page-1),'tool');
  const next=btn('التالي',()=>setPage(page+1),'tool');
  let page=1;
  function setPage(n){
    if(!Number.isFinite(n))return;
    page=Math.min(doc.pages,Math.max(1,Math.floor(n)));
    choose.value=page;
    const url=documentURL(key,page);
    if(url.href!==location.href){history.replaceState(history.state,'',url);lastRouteURL=location.href;}
    pageImage.alt=doc.title+' · صفحة '+page;
    pageImage.src='assets/documents/'+(doc.dir||key)+'/p-'+String(page).padStart(doc.digits,'0')+'.jpg?v=15f';
    previous.disabled=page===1;next.disabled=page===doc.pages;
    count.textContent='من '+doc.pages.toLocaleString('ar-EG');
    links.replaceChildren();unitLink.hidden=true;
    for(const [rect,target] of DOCUMENT_LINKS[key]?.[page]||[]){
      const anchor=el('a');
      if(typeof target==='number'){
        anchor.href=documentURL(key,target).href;anchor.setAttribute('aria-label','انتقل إلى صفحة '+target);
        anchor.onclick=event=>{if(event.button===0&&!event.metaKey&&!event.ctrlKey&&!event.shiftKey&&!event.altKey){event.preventDefault();setPage(target);dialog.scrollTop=0}};
      }else{
        const url=new URL(target,document.baseURI);
        if(target.startsWith('?')||target.startsWith('#')){
          const route=url.searchParams.has('unit')?'unit/'+url.searchParams.get('unit'):url.searchParams.has('floor')?'plan/'+url.searchParams.get('floor'):url.hash.slice(1);
          const view=url.searchParams.get('view');
          anchor.dataset.route=route;anchor.href=routeURL(route,view);
          if(view)anchor.dataset.unitView=view;
          if(!view&&route.startsWith('unit/')&&((key==='leasing'&&page>=38)||(key==='basement'&&page>1))){
            unitLink.hidden=false;unitLink.href=anchor.href;unitLink.dataset.route=route;
            unitLink.textContent='افتح بطاقة الوحدة ↗';
          }
          const action=view==='real'?'صور الموقع':view==='tour'?'الجولة البصرية':'بطاقة الوحدة';
          anchor.setAttribute('aria-label',route.startsWith('unit/')?action+' '+route.slice(5):'فتح القسم في الدليل');
          if(route.endsWith('-film'))anchor.setAttribute('data-play-film','');
        }else{anchor.href=target;anchor.setAttribute('aria-label',url.hostname==='wa.me'?'فتح واتساب':url.protocol==='tel:'?'الاتصال بإدارة التأجير':url.protocol==='mailto:'?'مراسلة إدارة التأجير':'فتح الرابط '+url.hostname)}
      }
      const [x,y,w,h]=rect;Object.assign(anchor.style,{left:x+'%',top:y+'%',width:w+'%',height:h+'%'});links.append(anchor);
    }
  }
  choose.onchange=()=>setPage(Number.isFinite(choose.valueAsNumber)?choose.valueAsNumber:page);
  choose.onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();setPage(choose.valueAsNumber)}};
  const dl=href('تنزيل ملف PDF الأصلي',doc.file+'?v=15f','secondary');dl.download=doc.file.split('/').pop();dl.dataset.rawFile='true';
  const raw=href('فتح ملف PDF مباشرة',doc.file+'?v=15f','under');raw.dataset.rawFile='true';
  const actions=el('div','actions');actions.append(unitLink,dl,raw);
  if(doc.pages>1){controls.append(previous,el('span','','صفحة'),choose,count,next);reader.append(controls)}
  reader.append(canvas,actions);body.append(reader);setPage(initialPage);
}
document.addEventListener('click',event=>{
  if(event.defaultPrevented||event.button!==0||event.metaKey||event.ctrlKey||event.shiftKey||event.altKey)return;
  const a=event.target.closest('a[href]');
  if(!a||a.hasAttribute('data-raw-file'))return;
  const url=new URL(a.getAttribute('href'),document.baseURI);
  const doc=url.origin===location.origin&&docByPath.get(url.pathname);
  if(doc){event.preventDefault();openDocument(doc)}
});
