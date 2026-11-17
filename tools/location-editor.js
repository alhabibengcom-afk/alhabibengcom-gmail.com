'use strict';

function readLocationFile(text) {
  // Accept only JSON, including the one-variable envelope used by the public site.
  const cleaned = text.trim().replace(/^\uFEFF/, '');
  const declaration = cleaned.match(/^(?:(?:\/\/[^\r\n]*\r?\n)\s*)*const\s+LOCATION_LINKS\s*=\s*([\s\S]*?)\s*;?\s*$/u);
  return JSON.parse(declaration ? declaration[1] : cleaned);
}

function serializeLocations(data) {
  const escaped = JSON.stringify(data, null, 2).replace(/[<>&\u2028\u2029]/g,
    character => '\\u' + character.charCodeAt(0).toString(16).padStart(4, '0'));
  return 'const LOCATION_LINKS = ' + escaped + ';\n';
}

const CALIBRATION_PANORAMAS = new Map([
  ['575', {id:'575', caption:'الممر التجاري ١ · بانوراما تصميمية', src:'assets/panoramas/575.webp'}],
  ['576', {id:'576', caption:'الممر التجاري ٢ · بانوراما تصميمية', src:'assets/panoramas/576.webp'}]
]);

function validatedLocations(source, units, photos) {
  const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
  if (!object(source) || !object(source.photos) || !object(source.tours)) throw Error('صيغة ملف المواقع غير صحيحة.');
  const result = {photos: {}, tours: {}};
  const coordinate = value => typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 1;
  function bindings(key, field, available) {
    if (!object(source[key])) throw Error('صيغة علامات المشاهد غير صحيحة.');
    const collection = {};
    for (const [id, records] of Object.entries(source[key])) {
      if (!units.has(id) || !Array.isArray(records)) throw Error('مرجع وحدة غير معروف في علامات الصور.');
      const seen = new Set();
      for (const item of records) {
        if (!object(item) || !available.has(item[field]) || seen.has(item[field]) ||
            !coordinate(item.x) || !coordinate(item.y) || typeof item.note !== 'string' || !item.note.trim()) {
          throw Error('تحقّق من بيانات العلامة في الوحدة ' + id + '.');
        }
        seen.add(item[field]);
        const record = {[field]:item[field], x:item.x, y:item.y, note:item.note.trim()};
        if (typeof item.basis === 'string' && item.basis) record.basis = item.basis;
        (collection[id] ||= []).push(record);
      }
    }
    result[key] = collection;
  }
  bindings('photos', 'photo', photos);
  if (Object.hasOwn(source, 'panoramas')) bindings('panoramas', 'scene', CALIBRATION_PANORAMAS);
  for (const [id, raw] of Object.entries(source.tours)) {
    const url = validUnitTourURL(raw);
    if (!units.has(id) || !url) throw Error('رابط محطة غير صالح للوحدة ' + id + '.');
    result.tours[id] = url;
  }
  return result;
}

function interiorPoint(points) {
  // Select the middle of an interior interval, including for concave footprints.
  const ys = [...new Set(points.map(point => point[1]))].sort((a, b) => a - b);
  const mid = (ys[0] + ys[ys.length - 1]) / 2;
  let best = null;
  for (let cut = 1; cut < ys.length; cut++) {
    const y = (ys[cut] + ys[cut - 1]) / 2;
    const xs = [];
    for (let i = 0; i < points.length; i++) {
      const a = points[i], b = points[(i + 1) % points.length];
      if ((a[1] > y) !== (b[1] > y)) xs.push(a[0] + (y-a[1])*(b[0]-a[0])/(b[1]-a[1]));
    }
    xs.sort((a, b) => a - b);
    for (let i = 1; i < xs.length; i += 2) {
      const score = xs[i] - xs[i - 1] - .25 * Math.abs(y - mid);
      if (!best || score > best.score) best = {x:(xs[i] + xs[i - 1])/2, y, score};
    }
  }
  return best || {x:points[0][0], y:points[0][1]};
}

function startLocationEditor() {
  const $ = id => document.getElementById(id);
  if (typeof UNIT_GALLERY === 'undefined' || typeof UNIT_DRAWINGS === 'undefined' ||
      typeof LOCATION_LINKS === 'undefined' || typeof validUnitTourURL !== 'function') {
    throw Error('تعذّر تحميل ملفات الدليل. فك ضغط الحزمة كاملة واحتفظ بمجلدي brands وtools جنبًا إلى جنب.');
  }
  const floorNames = {b1:'البدروم الأول', g:'الدور الأرضي', f1:'الدور الأول', f2:'الدور الثاني'};
  const getFloor = id => id.startsWith('F2-') || id.startsWith('S') ? 'f2' : ({B:'b1', G:'g', F:'f1'})[id[0]];
  const ids = Object.keys(UNIT_DRAWINGS).sort((a, b) => a.localeCompare(b, 'en', {numeric:true}));
  const knownUnits = new Set(ids);
  const photos = new Map(UNIT_GALLERY.photos.map(photo => [photo.id, photo]));
  const normalize = source => validatedLocations(source, knownUnits, photos);
  let data = normalize(LOCATION_LINKS);
  let hash = 2166136261;
  for (const ch of JSON.stringify(data)) hash = Math.imul(hash ^ ch.charCodeAt(0), 16777619);
  const storageKey = 'hp-location-calibration/v1/' + location.pathname + '/' + (hash >>> 0);
  let recovered = false;
  try {
    const draft = localStorage.getItem(storageKey);
    if (draft) { data = normalize(JSON.parse(draft)); recovered = true; }
  } catch { /* The editor also runs with browser storage disabled. */ }
  const unitSelect = $('unit'), floorSelect = $('floor'), photoSelect = $('photo');
  const basis = $('basis'), note = $('note'), tour = $('tour'), img = $('scene'), frame = $('frame'), marker = $('pin');
  const status = $('status'), svg = $('plan');
  let activeUnit = '', activePhoto = '', mode = 'photos', point = null, zoomed = false, pendingPhoto = false, pendingTour = false;
  const sourceField = () => mode === 'photos' ? 'photo' : 'scene';
  const catalog = () => mode === 'photos' ? photos : CALIBRATION_PANORAMAS;
  const unitBindings = () => data[mode]?.[activeUnit] || [];

  function say(message, error = false) {
    status.textContent = message;
    status.dataset.error = String(error);
  }
  function save(message) {
    try { localStorage.setItem(storageKey, JSON.stringify(data)); say(message); }
    catch { say(message + ' صدّر الملف للاحتفاظ بالتعديلات على جهازك.'); }
  }
  function discardIfPending(photo = true, station = true) {
    if (!(photo && pendingPhoto || station && pendingTour)) return true;
    return window.confirm('توجد تعديلات لم تُحفظ بعد. هل تريد تجاهلها؟');
  }
  function stored() { return unitBindings().find(item => item[sourceField()] === activePhoto); }
  function syncPhotoControls() {
    marker.hidden = !point;
    if (point) {
      marker.style.left = (100 * point.x) + '%';
      marker.style.top = (100 * point.y) + '%';
      marker.firstElementChild.textContent = activeUnit;
      marker.classList.toggle('flip-down', point.y < .1);
      marker.classList.toggle('start-edge', point.x < .09);
      marker.classList.toggle('end-edge', point.x > .91);
    }
    $('save-pin').disabled = !point || !note.value.trim() || !pendingPhoto;
    $('remove-pin').disabled = !stored();
  }
  function syncTourControls() {
    const target = validUnitTourURL(tour.value);
    const preview = $('tour-test');
    preview.hidden = !target;
    if (target) preview.href = target; else preview.removeAttribute('href');
    $('save-tour').disabled = !pendingTour || !tour.value.trim();
    $('remove-tour').disabled = !data.tours[activeUnit];
  }
  function boundPhotos() {
    const list = $('mapped');
    list.replaceChildren();
    for (const binding of unitBindings()) {
      const key = binding[sourceField()];
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = '✓ ' + catalog().get(key).caption;
      button.title = binding.note;
      button.addEventListener('click', () => {
        if (key === activePhoto || !discardIfPending(true, false)) return;
        photoSelect.value = key;
        showPhoto();
      });
      list.append(button);
    }
  }
  function showPhoto() {
    activePhoto = photoSelect.value;
    const record = catalog().get(activePhoto), binding = stored();
    pendingPhoto = false;
    point = binding ? {x:binding.x, y:binding.y} : null;
    note.value = binding?.note || '';
    const temporary = basis.querySelector('[data-extra]');
    if (temporary) temporary.remove();
    if (binding?.basis && ![...basis.options].some(option => option.value === binding.basis)) {
      const known = new Option(binding.basis, binding.basis); known.dataset.extra = 'true'; basis.add(known);
    }
    basis.value = binding?.basis || (mode === 'panoramas' ? 'architectural-correspondence' : 'field-confirmed');
    img.alt = record.caption;
    img.src = '../brands/' + (record.original || record.src);
    frame.setAttribute('aria-label', 'تحديد موقع '+activeUnit+' على '+record.caption);
    syncPhotoControls();
  }
  function showPlan() {
    const poly = UNIT_DRAWINGS[activeUnit].polygon;
    const floor = getFloor(activeUnit);
    $('plan-img').setAttribute('href', '../brands/assets/drawings/'+floor+'.png');
    $('plan-caption').textContent = floorNames[floor]+'، حدود '+activeUnit;
    $('floor-name').textContent = floorNames[floor]+' · '+activeUnit;
    $('zoom').setAttribute('aria-pressed', String(zoomed));
    $('zoom').textContent = zoomed ? 'عرض الدور' : 'تكبير الوحدة';
    $('outline').setAttribute('points', poly.map(p => p.join(',')).join(' '));
    const p = interiorPoint(poly);
    for (const id of ['plan-halo','plan-dot']) {
      $(id).setAttribute('cx', p.x);
      $(id).setAttribute('cy', p.y);
    }
    const setBox = (x,y,w,h) => svg.setAttribute('viewBox', [x,y,w,h].join(' '));
    if (!zoomed) setBox(0,0,1108,1100);
    else {
      const xs = poly.map(pair => pair[0]), ys = poly.map(pair => pair[1]);
      const l = Math.min(...xs), r = Math.max(...xs), t = Math.min(...ys), b = Math.max(...ys);
      const pad = Math.max(15, .18 * Math.max(r-l, b-t));
      setBox(l-pad, t-pad, r-l+2*pad, b-t+2*pad);
    }
    const viewWidth=svg.viewBox.baseVal.width;
    $('plan-halo').setAttribute('r',viewWidth*.009);
    $('plan-dot').setAttribute('r',viewWidth*.004);
    $('plan-halo').setAttribute('stroke-width',viewWidth*.002);
  }
  function showUnit() {
    activeUnit = unitSelect.value;
    pendingTour = false;
    tour.value = data.tours[activeUnit] || '';
    showPlan(); mediaChoices(); syncTourControls();
  }
  function mediaChoices() {
    photoSelect.replaceChildren();
    const marked = new Set(unitBindings().map(item => item[sourceField()]));
    const zone = UNIT_GALLERY.zones[activeUnit];
    const sorted = [...catalog().values()].sort((a,b) =>
      Number(marked.has(b.id))-Number(marked.has(a.id)) || Number(b.group===zone)-Number(a.group===zone));
    for (const photo of sorted) {
      photoSelect.add(new Option((marked.has(photo.id) ? '✓ ' : '') + photo.caption + ' · '+photo.id, photo.id));
    }
    showPhoto(); boundPhotos();
  }
  function populateUnits() {
    unitSelect.replaceChildren();
    ids.filter(id => getFloor(id) === floorSelect.value).forEach(id => unitSelect.add(new Option(id,id)));
    showUnit();
  }
  Object.entries(floorNames).forEach(([key,label]) => floorSelect.add(new Option(label,key)));
  floorSelect.value = 'g';
  floorSelect.addEventListener('change', () => {
    if (discardIfPending()) populateUnits(); else floorSelect.value = getFloor(activeUnit);
  });
  unitSelect.addEventListener('change', () => {
    if (discardIfPending()) showUnit(); else unitSelect.value = activeUnit;
  });
  photoSelect.addEventListener('change', () => {
    if (discardIfPending(true, false)) showPhoto(); else photoSelect.value = activePhoto;
  });
  function changeMode(next) {
    if (mode === next || !discardIfPending(true, false)) return;
    mode = next;
    const pano = mode === 'panoramas';
    $('select-photo').setAttribute('aria-pressed',String(!pano));
    $('select-pano').setAttribute('aria-pressed',String(pano));
    $('media-label').textContent = pano ? 'البانوراما الأصلية' : 'الصورة الأصلية';
    $('frame-help').textContent = pano
      ? 'اضغط مركز واجهة المحل على الصورة البانورامية الكاملة. الحافة اليمنى واليسرى تلتقيان في الجولة. استخدم الأسهم للضبط الدقيق.'
      : 'اضغط على فتحة المحل لتحديد موضعها. من لوحة المفاتيح استخدم الأسهم لضبط العلامة وShift + سهم للتحريك بخطوة أكبر.';
    mediaChoices();
  }
  $('select-photo').addEventListener('click', () => changeMode('photos'));
  $('select-pano').addEventListener('click', () => changeMode('panoramas'));
  $('zoom').addEventListener('click', () => { zoomed = !zoomed; showPlan(); });
  function place(x,y) {
    const clamp = value => Number(Math.min(1, Math.max(0,value)).toFixed(6));
    point = {x:clamp(x),y:clamp(y)}; pendingPhoto=true; syncPhotoControls();
  }
  frame.addEventListener('click', event => {
    if (!img.naturalWidth || !img.complete) return;
    if (event.detail === 0) { if (!point) place(.5,.5); return; }
    const bounds = img.getBoundingClientRect();
    if (bounds.width && bounds.height) place((event.clientX-bounds.left)/bounds.width, (event.clientY-bounds.top)/bounds.height);
  });
  frame.addEventListener('keydown', event => {
    const arrow = {ArrowLeft:[-1,0],ArrowRight:[1,0],ArrowUp:[0,-1],ArrowDown:[0,1]}[event.key];
    if (!arrow || !img.naturalWidth) return;
    event.preventDefault();
    const from = point || {x:.5, y:.5}, pixels = event.shiftKey ? 10 : 1;
    place(from.x + pixels*arrow[0]/img.naturalWidth, from.y + pixels*arrow[1]/img.naturalHeight);
  });
  basis.addEventListener('change', () => { pendingPhoto = true; syncPhotoControls(); });
  note.addEventListener('input', () => { pendingPhoto = true; syncPhotoControls(); });
  $('save-pin').addEventListener('click', () => {
    if (!point || !note.value.trim()) return;
    const all = data[mode] || (data[mode] = {});
    const list = all[activeUnit] || (all[activeUnit] = []);
    const field = sourceField();
    const at = list.findIndex(item => item[field] === activePhoto);
    const item = {[field]:activePhoto, x:point.x, y:point.y, note:note.value.trim(), basis:basis.value};
    if (at < 0) list.push(item); else list[at] = item;
    pendingPhoto = false; note.value = item.note;
    photoSelect.selectedOptions[0].textContent = '✓ '+catalog().get(activePhoto).caption+' · '+activePhoto;
    boundPhotos(); syncPhotoControls(); save('تم حفظ علامة '+activeUnit+' على المشهد.');
  });
  $('remove-pin').addEventListener('click', () => {
    if (!stored() || !window.confirm('حذف رابط هذا المشهد من الوحدة '+activeUnit+'؟')) return;
    data[mode][activeUnit] = unitBindings().filter(item => item[sourceField()] !== activePhoto);
    if (!data[mode][activeUnit].length) delete data[mode][activeUnit];
    photoSelect.selectedOptions[0].textContent = catalog().get(activePhoto).caption+' · '+activePhoto;
    showPhoto(); boundPhotos(); save('تم حذف علامة المشهد.');
  });
  tour.addEventListener('input', () => { pendingTour = true; tour.setCustomValidity(''); syncTourControls(); });
  $('save-tour').addEventListener('click', () => {
    const target = validUnitTourURL(tour.value);
    if (!target) {
      const message = 'أدخل رابط HTTPS لمحطة محددة من الجولة الرسمية على alhabeebconst.com.';
      tour.setCustomValidity(message); tour.reportValidity(); say(message,true); return;
    }
    data.tours[activeUnit] = target; tour.value = target; pendingTour = false;
    syncTourControls(); save('تم حفظ محطة الجولة للوحدة '+activeUnit+'.');
  });
  $('remove-tour').addEventListener('click', () => {
    if (!data.tours[activeUnit] || !window.confirm('حذف رابط محطة الجولة من هذه الوحدة؟')) return;
    delete data.tours[activeUnit]; tour.value = ''; tour.setCustomValidity(''); pendingTour = false;
    syncTourControls(); save('تم حذف رابط المحطة.');
  });
  $('export').addEventListener('click', () => {
    if (pendingPhoto || pendingTour) {
      say('احفظ التعديلات الظاهرة أو تجاهلها قبل تصدير الملف.',true); return;
    }
    const blob = new Blob([serializeLocations(data)], {type:'text/javascript;charset=utf-8'});
    const href = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = href; a.download = 'location-links.js';
    document.body.append(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(href), 30000);
    say('تم تجهيز ملف المواقع. ارفعه إلى مجلد brands.');
  });
  $('import').addEventListener('change', async event => {
    const file = event.target.files[0];
    event.target.value = '';
    if (!file) return;
    try {
      if (file.size > 12 * 1024 * 1024) throw Error('حجم ملف المواقع أكبر من المتوقع.');
      const next = normalize(readLocationFile(await file.text()));
      if (!window.confirm('استبدال مسودة المواقع الحالية بالملف المختار؟')) return;
      data = next; showUnit(); save('تم استيراد ملف المواقع.');
    } catch (err) { say('تعذّر الاستيراد. '+ (err instanceof SyntaxError ? 'اختر ملف المواقع المصدّر بصيغته الأصلية.' : err.message),true); }
  });
  window.addEventListener('beforeunload', event => {
    if (pendingPhoto || pendingTour) { event.preventDefault(); event.returnValue = ''; }
  });
  populateUnits();
  if (recovered) say('تم فتح مسودة التوثيق المحفوظة على هذا الجهاز.');
}

try { startLocationEditor(); }
catch (error) {
  const fatal = document.getElementById('fatal');
  fatal.hidden = false; fatal.textContent = error.message;
  document.getElementById('editor').hidden = true;
  document.querySelector('.handoff').hidden = true;
}
