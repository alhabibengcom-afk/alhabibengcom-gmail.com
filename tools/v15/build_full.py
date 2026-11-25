# Detailed guide (index.html) from index.src.html: opening phases, no market study, no hypermarket operator,
# lease list of 58 units, garage 200 cars, unit specs. Writes index.html, site-full.js, i18n-en-full.js.
# Usage: build_full.py <brands dir> <lease58.json>
import json, re, sys
B, LIST = sys.argv[1], sys.argv[2]
OFFER = set(json.load(open(LIST, encoding='utf-8')))
SELF = {'B01', 'G16-21', 'F16-20', 'G46'}
EN = {}
def t(ar, en):
    EN[ar] = en; return ar
AR = str.maketrans('0123456789', '٠١٢٣٤٥٦٧٨٩')
def num(x, d=2):
    return (f'{x:,.{d}f}').translate(AR).replace(',', '٬').replace('.', '٫')
FLOOR = {'b1': t('البدروم', 'Basement'), 'g': t('الأرضي', 'Ground'), 'f1': t('الأول', 'First'), 'f2': t('الثاني', 'Second')}

PHASE2 = ['G39', 'G40', 'G41', 'G42', 'G42-1', 'G26-28', 'G30-32', 'G34-36', 'G38',
          'G06', 'G07-12', 'G08', 'G09', 'G11', 'G12-14', 'G13', 'G15', 'G16-21', 'F16-20']
BACK = {'G25-27': 'G26-28', 'G29-31': 'G30-32', 'G33-35': 'G34-36', 'G37': 'G38'}
P2 = t('يونيو ٢٠٢٧', 'June 2027'); P3 = t('ديسمبر ٢٠٢٧', 'December 2027')
PH2 = t('ضمن المرحلة الثانية، والتشغيل في يونيو ٢٠٢٧.', 'Part of phase two, opening in June 2027.')
PH3 = t('ضمن المرحلة الثالثة، والتشغيل في ديسمبر ٢٠٢٧.', 'Part of phase three, opening in December 2027.')
PHB = {k: t(f'ضمن المرحلة الثالثة (ديسمبر ٢٠٢٧)، وتنضم للمرحلة الثانية (يونيو ٢٠٢٧) إذا استأجرها مستأجر الوحدة {v} الملاصقة لها من الظهر.',
            f'Part of phase three (December 2027); it joins phase two (June 2027) if leased together with unit {v} directly behind it.') for k, v in BACK.items()}
HEIGHT = {'g': ('الارتفاع الداخلي ٤٫٦ م، ', 'Clear internal height 4.6 m; '), 'f1': ('الارتفاع الداخلي ٤٫٦ م، ', 'Clear internal height 4.6 m; '),
          'f2': ('الارتفاع الداخلي ٣٫٦ م، ', 'Clear internal height 3.6 m; '), 'b1': ('', '')}
SPECS = {}
for f, (ha, he) in HEIGHT.items():
    SPECS[f, False] = t(ha + ('و' if ha else '') + 'واجهة زجاجية بارتفاع ٢٫٨٠ م، والكهرباء جاهزة.',
                        (he + 'glass shopfront 2.80 m high' if he else 'Glass shopfront 2.80 m high') + '; power is in place.')
    SPECS[f, True] = t(ha + ('و' if ha else '') + 'واجهة زجاجية بارتفاع ٢٫٨٠ م، والكهرباء والمياه والصرف والغاز ودكت شفاط الهود جاهزة لأنها وحدة مطاعم.',
                       (he + 'glass shopfront 2.80 m high' if he else 'Glass shopfront 2.80 m high') + '; power, water, drainage, gas and a hood exhaust duct are in place as a food and beverage unit.')
FB = ('أغذية ومشروبات', 'فود كورت')

# ---------- units (site-full.js) ----------
site = open(B + '/site.js', encoding='utf-8').read()
i0 = site.index('const UNITS=') + len('const UNITS=')
units, e = json.JSONDecoder().raw_decode(site[i0:]); i1 = i0 + e
byid = {u['id']: u for u in units}
NOT = t('غير معروضة للتأجير حاليًا', 'Not currently offered for lease')
for u in units:
    if u['id'] in SELF:
        u['title'] = {'B01': t('هايبر ماركت', 'Hypermarket'), 'G16-21': t('محل تجزئة', 'Retail store'), 'F16-20': t('محل تجزئة', 'Retail store')}.get(u['id'], u.get('title'))
    if u['id'] in OFFER:
        u['held'] = False; u['status'] = 'متاحة للإيجار'
    else:
        u['held'] = True; u['status'] = NOT
    u['note'] = (u.get('note') or '').strip() + ' ' + SPECS[u['f'], u['cat'] in FB] + ' ' + (PH2 if u['id'] in PHASE2 else PHB.get(u['id'], PH3))
assert sum(1 for u in units if not u['held']) == len(OFFER) == 58
sfull = site[:i0] + json.dumps(units, ensure_ascii=False, separators=(',', ':')) + site[i1:]
sfull = sfull.replace("'لوحة تصميم هايبر ماركت الحبيب'", "'" + t('لوحة تصميم الهايبر ماركت', 'Hypermarket design plan') + "'")
sfull = sfull.replace('"المرحلة الثالثة · هايبر ماركت الحبيب"', '"' + t('المرحلة الثالثة · الهايبر ماركت', 'Phase three · the hypermarket') + '"')
sfull = sfull.replace('["market", "دراسة سوق قنا"]', '["market", "' + t('مراحل التشغيل', 'Opening phases') + '"]')
open(B + '/site-full.js', 'w', encoding='utf-8').write(sfull)

# ---------- page ----------
s = open(B + '/index.src.html', encoding='utf-8').read()
def rep(a, b, count=1):
    global s
    if a not in s: raise SystemExit('not found: ' + a[:90])
    s = s.replace(a, b) if count == 0 else s.replace(a, b, count)
def section(id_):
    i = s.index(f'id="{id_}"'); a = s.rfind('<section', 0, i); b = s.index('</section>', i) + len('</section>')
    return a, b

rep('<script src="site.js?v=15k"></script>', '<script src="site-full.js?v=1"></script>')
rep('<script src="i18n.js?v=15b"></script>', '<script src="i18n-en-full.js?v=1"></script><script src="i18n.js?v=15b"></script>')

# phases section replaces the market study (same id)
a, b = section('market')
p2a = [byid[k] for k in PHASE2 if k in OFFER]
row = lambda u, extra='': (f'<tr><td><a href="?unit={u["id"]}" data-route="unit/{u["id"]}"><bdi>{u["id"]}</bdi></a></td><td>{FLOOR[u["f"]]}</td>'
                           f'<td>{u["title"] if u.get("title") else u["cat"]}</td><td class="num">{num(u["area"])}</td>{extra}</tr>')
TH = lambda extra='': ('<thead><tr><th>' + t('الوحدة', 'Unit') + '</th><th>' + t('الدور', 'Level') + '</th><th>' + t('النشاط', 'Use') + '</th><th>'
                       + t('المحمّلة م²', 'Loaded m²') + '</th>' + extra + '</tr></thead>')
BACKNOTE = t('الوحدات G25-27 وG29-31 وG33-35 وG37 خلف واجهة الأزياء ضمن المرحلة الثالثة، وتنضم للمرحلة الثانية إذا استأجرها مستأجر الوحدة الأمامية الملاصقة لها من الظهر.',
             'Units G25-27, G29-31, G33-35 and G37 behind the fashion frontage are in phase three; each joins phase two if leased together with the front unit directly behind it.')
s = s[:a] + ('<section class="section hp-phases" id="market"><div class="wrap"><span class="over">OPENING PHASES</span>'
    '<h2>' + t('مراحل تشغيل هابينس بلازا', 'Happiness Plaza opening phases') + '</h2><ol class="hp-phase-cards">'
    '<li class="on"><span>' + t('المرحلة الأولى', 'Phase one') + '</span><b>' + t('تعمل بالفعل', 'Already open') + '</b><p>'
    + t('فندق بلازا ومطعم بوخارست بلاك والجيم والنادي الصحي وألعاب الأطفال حول البحيرة.', 'Plaza Hotel, Bokharest Black restaurant, the gym, the wellness club and the kids’ play area around the lake.') + '</p></li>'
    '<li><span>' + t('المرحلة الثانية', 'Phase two') + '</span><b>' + t('تشغيل يونيو ٢٠٢٧', 'Opening June 2027') + '</b><p>'
    + t('مطاعم البلازا وواجهة الأزياء والمحلات المطلة على البلازا في الدور الأرضي، والوحدة F16-20 في الدور الأول.', 'The plaza restaurants, the fashion frontage and the shops facing the plaza on the ground floor, plus unit F16-20 on the first floor.') + '</p></li>'
    '<li><span>' + t('المرحلة الثالثة', 'Phase three') + '</span><b>' + t('تشغيل ديسمبر ٢٠٢٧', 'Opening December 2027') + '</b><p>'
    + t('باقي المحلات التجارية بالكامل في كل الأدوار، ومعها الهايبر ماركت في البدروم.', 'All remaining shops on every level, together with the basement hypermarket.') + '</p></li></ol>'
    '<h3>' + t('وحدات المرحلة الثانية المتاحة للإيجار', 'Phase two units available for lease') + '</h3>'
    '<div class="hp-units-scroll"><table class="hp-units-table">' + TH() + '<tbody>' + ''.join(row(u) for u in p2a) + '</tbody></table></div>'
    '<p class="hp-units-foot">' + BACKNOTE + '</p></div></section>') + s[b:]

# units list (58) with specs and opening, before the plans
order = {'b1': 0, 'g': 1, 'f1': 2, 'f2': 3}
avail = sorted([u for u in units if not u['held']], key=lambda u: (order[u['f']], u['id']))
tot = {}
for u in avail:
    tot.setdefault(u['f'], [0, 0.0]); tot[u['f']][0] += 1; tot[u['f']][1] += u['area']
specs = ('<ul class="hp-specs">' + ''.join(f'<li><b>{x}</b><span>{y}</span></li>' for x, y in [
    (t('٤٫٦ م · ٣٫٦ م', '4.6 m · 3.6 m'), t('الارتفاع الداخلي: الأرضي والأول ٤٫٦ م، والثاني ٣٫٦ م', 'Clear height: ground and first floors 4.6 m, second floor 3.6 m')),
    (t('٢٫٨٠ م', '2.80 m'), t('ارتفاع الواجهة الزجاجية', 'Glass shopfront height')),
    (t('كل الوحدات', 'All units'), t('الكهرباء جاهزة', 'Power in place')),
    (t('المطاعم', 'Food & beverage'), t('مياه وصرف وغاز ودكت شفاط للهود لوحدات المطاعم والكافيهات والفود كورت', 'Water, drainage, gas and a hood exhaust duct for restaurant, café and food-court units'))]) + '</ul>')
summary = ''.join(f'<li><b>{FLOOR[f]}</b> {num(n, 0)} · {num(ar)} م²</li>' for f, (n, ar) in sorted(tot.items(), key=lambda x: order[x[0]]))
table = ('<section class="section hp-units" id="units-list"><div class="wrap"><span class="over">AVAILABLE FOR LEASE</span>'
         '<h2>' + t('دليل الوحدات المتاحة للإيجار', 'Units available for lease') + '</h2>'
         f'<p class="hp-units-lead">{num(len(avail), 0)} ' + t('وحدة متاحة للإيجار بمساحة محمّلة إجمالية', 'units available for lease, with a total loaded area of')
         + f' {num(sum(x[1] for x in tot.values()))} م². ' + t('المساحات محمّلة، والإيجار يُحتسب على المساحة المحمّلة.', 'All areas are loaded areas; rent is charged on the loaded area.') + '</p>'
         + specs + f'<ul class="hp-units-sum">{summary}</ul>'
         '<div class="hp-units-scroll"><table class="hp-units-table">' + TH('<th>' + t('التشغيل', 'Opening') + '</th>') + '<tbody>'
         + ''.join(row(u, f'<td class="ph{2 if u["id"] in PHASE2 else 3}">{P2 if u["id"] in PHASE2 else P3 + ("*" if u["id"] in BACK else "")}</td>') for u in avail)
         + '</tbody></table></div><p class="hp-units-foot">* ' + t('تنضم للمرحلة الثانية (يونيو ٢٠٢٧) إذا استأجرها مستأجر الوحدة الملاصقة لها من الظهر.', 'Joins phase two (June 2027) if leased together with the unit directly behind it.') + '</p>'
         '<p class="hp-pack-row"><a class="action" href="Happiness_Plaza_Leasing_Pack.pdf" download>' + t('ملف التأجير PDF · عربي', 'Leasing Pack PDF · Arabic') + '</a> '
         '<a class="secondary" href="Happiness_Plaza_Leasing_Pack_EN.pdf" download>Leasing Pack PDF · English</a></p></div></section>')
a, b = section('atlas'); s = s[:a] + table + s[a:]
s = re.sub(r'<a class="hp-tile hp-gold" href="\?floor=g" data-route="plan/g"><strong>مخططات المحلات</strong><small>[^<]*</small></a>',
           '<a class="hp-tile hp-gold" href="./#units-list" data-route="units-list"><strong>' + t('الوحدات المتاحة', 'Available units') + '</strong><small>'
           + t('٥٨ وحدة متاحة للإيجار والمخططات', '58 units for lease, with plans') + '</small></a>', s, count=1)

# menus and tiles that pointed at the market study
rep('<strong>دراسة سوق قنا</strong><small>السكان والزيارات</small>', '<strong>' + t('مراحل التشغيل', 'Opening phases') + '</strong><small>' + t('المرحلة الثانية يونيو ٢٠٢٧', 'Phase two June 2027') + '</small>')
rep('<a href="./#market" data-route="market">سوق قنا</a>', '<a href="./#market" data-route="market">' + t('مراحل التشغيل', 'Opening phases') + '</a>')
rep('<strong>٣ · السوق والمخططات</strong><a href="./#market" data-route="market">دراسة سوق قنا</a>', '<strong>' + t('٣ · المراحل والمخططات', '3 · Phases and plans') + '</strong><a href="./#market" data-route="market">' + t('مراحل التشغيل', 'Opening phases') + '</a>')
rep(' <a href="./#market" data-route="market">دراسة سوق قنا كاملة</a>', '')

# phases roadmap
a, b = section('stages')
s = s[:a] + ('<section class="phase-roadmap" id="stages"><div class="wrap"><h2>' + t('مراحل التشغيل', 'Opening phases') + '</h2><ol>'
    '<li><a href="./#phase" data-route="phase"><span>' + t('المرحلة الأولى', 'Phase one') + '</span><strong>' + t('الفندق والأنشطة الترفيهية', 'Hotel and leisure') + '</strong><small>' + t('تعمل بالفعل', 'Already open') + '</small></a></li>'
    '<li><a href="./#market" data-route="market"><span>' + t('المرحلة الثانية', 'Phase two') + '</span><strong>' + t('مطاعم البلازا وواجهة الأزياء', 'Plaza restaurants and fashion frontage') + '</strong><small>' + t('تشغيل يونيو ٢٠٢٧', 'Opening June 2027') + '</small></a></li>'
    '<li><a href="?floor=g" data-route="plan/g"><span>' + t('المرحلة الثالثة', 'Phase three') + '</span><strong>' + t('باقي المحلات التجارية والهايبر ماركت', 'All remaining shops and the hypermarket') + '</strong><small>' + t('تشغيل ديسمبر ٢٠٢٧', 'Opening December 2027') + '</small></a></li>'
    '</ol></div></section>') + s[b:]

# phase one runs; no December 2026
rep('<p>صمّمت المجموعة ونفّذت مبنى الفندق والترفيه في المرحلة الأولى: ٧٬٠٠٠ م² من بدروم وثلاثة أدوار، وفندق بوتيك من ١٤ غرفة. اكتمل التنفيذ والتشطيبات، والمرحلة الأولى قيد التشغيل والافتتاح الرسمي في ديسمبر ٢٠٢٦.</p>',
    '<p>' + t('صمّمت المجموعة ونفّذت مبنى الفندق والترفيه في المرحلة الأولى: ٧٬٠٠٠ م² من بدروم وثلاثة أدوار، وفندق بوتيك من ١٤ غرفة. المرحلة الأولى تعمل بالفعل.',
              'The group designed and built the phase one hotel and leisure building: 7,000 m² over a basement and three levels, with a 14-room boutique hotel. Phase one is already open.') + '</p>')
rep('<p>من غرف فندق بلازا إلى مطعم الجزيرة ونوادي الصحة واللياقة. قيد التشغيل، والافتتاح الرسمي في ديسمبر ٢٠٢٦.</p>',
    '<p>' + t('من غرف فندق بلازا إلى مطعم الجزيرة ونوادي الصحة واللياقة. المرحلة الأولى تعمل بالفعل.', 'From the Plaza Hotel rooms to the island restaurant and the health and fitness clubs. Phase one is already open.') + '</p>')
s = re.sub(r'<strong>المرحلة الأولى</strong><small>قيد التشغيل</small>', '<strong>' + t('المرحلة الأولى', 'Phase one') + '</strong><small>' + t('تعمل بالفعل', 'Already open') + '</small>', s)
rep('<strong>٢ · المرحلة الأولى قيد التشغيل</strong><a href="./#stages" data-route="stages">مراحل التنفيذ</a>',
    '<strong>' + t('٢ · المرحلة الأولى تعمل بالفعل', '2 · Phase one is open') + '</strong><a href="./#stages" data-route="stages">' + t('مراحل التشغيل', 'Opening phases') + '</a>')
rep('<h2>المرحلة الثانية · المحلات التجارية</h2>', '<h2>' + t('المحلات التجارية · المرحلتان الثانية والثالثة', 'Retail units · phases two and three') + '</h2>')

# hypermarket without an operator
rep('<span class="over">AL-HABEEB HYPERMARKET', '<span class="over">HYPERMARKET')
rep('<h2>المرحلة الثالثة · هايبر ماركت الحبيب</h2>', '<h2>' + t('المرحلة الثالثة · الهايبر ماركت', 'Phase three · the hypermarket') + '</h2>')
s = re.sub(r'<p><b>٥٬٥٦٢ م²</b> هي مساحة الوحدة B01 على مخطط التأجير\.[^<]*<b>٧٬٠٠٠ م²</b>[^<]*</p>',
           '<p><b>٥٬٥٦٢ م²</b> ' + t('مساحة محمّلة للوحدة B01 في البدروم، والتشغيل في ديسمبر ٢٠٢٧ مع باقي المحلات.', 'loaded area for unit B01 in the basement, opening in December 2027 with the remaining shops.') + '</p>', s, count=1)
rep('<span>يشغّله الحبيب ماركت ويجلب زيارات يومية للمول.</span>', '<span>' + t('ضمن المرحلة الثالثة، والتشغيل في ديسمبر ٢٠٢٧.', 'Part of phase three, opening in December 2027.') + '</span>')
rep('<h4>أمام هايبر ماركت الحبيب</h4>', '<h4>' + t('أمام الهايبر ماركت', 'In front of the hypermarket') + '</h4>')
s = s.replace('alt="تصميم توزيع أقسام هايبر ماركت الحبيب والكاشيرات"', 'alt="' + t('تصميم توزيع أقسام الهايبر ماركت والكاشيرات', 'Hypermarket department and checkout layout') + '"')
s = re.sub(r'<div class="wrap marketlook">.*?</div></div>', '', s, count=1, flags=re.S)
rep(' وفي هابينس بلازا يشغّل الحبيب هايبر ماركت B01 بمساحة ٥٬٥٦٢ م² بأقسام الأغذية الطازجة والسلع سريعة التداول والمنسوجات والسلع غير الغذائية، إلى جانب الحبيب ستور وصيدلية الحبيب.', '')
rep('تأسست سلسلة الحبيب ماركت عام ٢٠٠٨، ولها ٤ فروع في محافظتي قنا والبحر الأحمر، منها الفرع الرئيسي في قنا وفرع الغردقة، وتطبيق للطلب أونلاين.</p>',
    t('تأسست سلسلة الحبيب ماركت عام ٢٠٠٨، ولها ٤ فروع في محافظتي قنا والبحر الأحمر، منها الفرع الرئيسي في قنا وفرع الغردقة، وتطبيق للطلب أونلاين.',
      'Alhabeeb Market was founded in 2008 and has 4 branches in Qena and Red Sea governorates, including its main Qena branch and a Hurghada branch, plus an app for online orders.') + '</p>')
s = re.sub(r'<li><strong>الهايبر ماركت مُشغَّل من المالك</strong><p>[^<]*</p></li>', '', s, count=1)
s = re.sub(r'<article><img loading="lazy" src="assets/developer/market-sign\.webp"[^>]*>.*?</article>', '', s, count=1, flags=re.S)
s = re.sub(r'<div><img loading="lazy" src="assets/developer/market-(sign|fresh)\.webp"[^>]*><span>[^<]*</span></div>', '', s)
rep('<figcaption>تصميم الحبيب ماركت داخل المول، والمرحلة الأولى كما نُفّذت.</figcaption>', '<figcaption>' + t('المرحلة الأولى كما صمّمتها المجموعة ونفّذتها.', 'Phase one as designed and built by the group.') + '</figcaption>')
rep('<p>هايبر ماركت الحبيب والحبيب ستور وصيدلية الحبيب، يشغّلها المالك نفسه.</p>', '<p>' + t('هايبر ماركت ومحلّا تجزئة وصيدلية.', 'A hypermarket, two retail stores and a pharmacy.') + '</p>')
m = re.search(r'<p>بدأ في ٢٠٢١ بمشروع هابينس بلازا[^<]*</p>', s)
s = s[:m.start()] + '<p>' + t('بدأ في ٢٠٢١ بمشروع هابينس بلازا عند مدخل قنا الجديدة: أرض ١٧٬٧٨٥ م²، وبلازا مشتركة ٤٬٠٠٠ م²، وثلاث مراحل: الفندق والترفيه، ثم مطاعم البلازا وواجهة الأزياء، ثم باقي المحلات والهايبر ماركت.',
      'Launched in 2021 with Happiness Plaza at the entrance of New Qena: a 17,785 m² site, a 4,000 m² shared plaza and three phases: the hotel and leisure, then the plaza restaurants and fashion frontage, then the remaining shops and the hypermarket.') + '</p>' + s[m.end():]

# garage 200 cars
rep('<strong>جراج على مستويين لـ٢٠٠ سيارة</strong><span>سعة تصميمية، منها ٣٬٦٤٤ م² في البدروم الأول.</span>',
    '<strong>' + t('جراج على مستويين يتسع لـ٢٠٠ سيارة', 'A two-level garage for 200 cars') + '</strong><span>' + t('٧٬٢٨٩ م²، بواقع ٣٬٦٤٤ م² لكل مستوى.', '7,289 m², 3,644 m² on each level.') + '</span>')
s = re.sub(r'<p>يعرض الملف جراجًا[^<]*</p>', lambda m: (
    '<p>' + t('جراج على مستويين يتسع لـ٢٠٠ سيارة بمساحة ٧٬٢٨٩ م² (٣٬٦٤٤ م² لكل مستوى). يشمل البرنامج مصلى ودورات مياه للرجال والسيدات وذوي الإعاقة وماكينة صراف آلي.',
              'A two-level garage for 200 cars, 7,289 m² (3,644 m² on each level). The programme includes a prayer room, toilets for men, women and people with disabilities, and an ATM.') + '</p>'), s, count=1)

rep('مقصد التسوق الجديد لأهالي قنا · ١٤٤ وحدة تجارية للإيجار', t('مقصد التسوق الجديد لأهالي قنا · ٥٨ وحدة متاحة للإيجار', 'Qena’s new shopping destination · 58 units for lease'))
s = s.replace('١٤٤ وحدة تجارية للإيجار', '٥٨ وحدة متاحة للإيجار').replace('144 retail units for lease', '58 units for lease')
for bad in ['هايبر ماركت الحبيب', 'يشغّلها الحبيب', 'يشغّله الحبيب', 'يشغّلها المالك', 'الحبيب ستور', 'ديسمبر ٢٠٢٦', 'دراسة سوق', 'زيارة في اليوم', 'سعة تصميمية', 'Qena_Market_and_Footfall']:
    assert bad not in s, bad
open(B + '/index.html', 'w', encoding='utf-8').write(s)
open(B + '/i18n-en-full.js', 'w', encoding='utf-8').write(
    '/* English for the detailed guide: phases, specs and edited sentences. Loaded after i18n-en.js. */\n'
    '(function(){var D=window.HP_EN;if(!D)return;var A=' + json.dumps(EN, ensure_ascii=False, separators=(',', ':')) + ';for(var k in A)D[k]=A[k];})();\n')
print('full built:', len(avail), 'units for lease;', len(EN), 'English entries')
