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
t('صالون وبيوتي سنتر', 'Salon & beauty centre')
FLOOR = {'b1': t('البدروم', 'Basement'), 'g': t('الأرضي', 'Ground'), 'f1': t('الأول', 'First'), 'f2': t('الثاني', 'Second')}

PHASE2 = ['G39', 'G40', 'G41', 'G42', 'G42-1', 'G26-28', 'G30-32', 'G34-36', 'G38',
          'G06', 'G07-12', 'G08', 'G09', 'G11', 'G12-14', 'G13', 'G15', 'G16-21', 'F16-20']
BACK = {'G25-27': 'G26-28', 'G29-31': 'G30-32', 'G33-35': 'G34-36', 'G37': 'G38'}

# Optional overrides from the Drive sheet (written by tools/auto/sync_units.py): phase-two units and glass heights.
import os as _os
GLASS = {}
if _os.path.exists(B + '/site-config.json'):
    _cfg = json.load(open(B + '/site-config.json', encoding='utf-8'))
    PHASE2 = _cfg.get('phase2') or PHASE2
    GLASS = _cfg.get('glass') or {}
P2 = t('يونيو ٢٠٢٧', 'June 2027'); P3 = t('ديسمبر ٢٠٢٧', 'December 2027')
PH2 = t('ضمن المرحلة الثانية، والتشغيل في يونيو ٢٠٢٧.', 'Part of phase two, opening in June 2027.')
PH3 = t('ضمن المرحلة الثالثة، والتشغيل في ديسمبر ٢٠٢٧.', 'Part of phase three, opening in December 2027.')
PHB = {k: t(f'ضمن المرحلة الثالثة (ديسمبر ٢٠٢٧)، وتنضم للمرحلة الثانية (يونيو ٢٠٢٧) إذا استأجرها مستأجر الوحدة {v} الملاصقة لها من الظهر.',
            f'Part of phase three (December 2027); it joins phase two (June 2027) if leased together with unit {v} directly behind it.') for k, v in BACK.items()}
HEIGHT = {'g': ('الارتفاع الداخلي ٤٫٦ م، ', 'Clear internal height 4.6 m; '), 'f1': ('الارتفاع الداخلي ٤٫٦ م، ', 'Clear internal height 4.6 m; '),
          'f2': ('الارتفاع الداخلي ٣٫٦ م، ', 'Clear internal height 3.6 m; '), 'b1': ('الارتفاع الداخلي ٥٫٦ م، ', 'Clear internal height 5.6 m; ')}
SPECS = {}
for f, (ha, he) in HEIGHT.items():
    SPECS[f, False] = t(ha + ('و' if ha else '') + 'واجهة زجاجية بارتفاع ٢٫٨٠ م، والكهرباء جاهزة.',
                        (he + 'glass shopfront 2.80 m high' if he else 'Glass shopfront 2.80 m high') + '; power is in place.')
    SPECS[f, True] = t(ha + ('و' if ha else '') + 'واجهة زجاجية بارتفاع ٢٫٨٠ م، والكهرباء والمياه والصرف والغاز ودكت شفاط الهود جاهزة لأنها وحدة مطاعم.',
                       (he + 'glass shopfront 2.80 m high' if he else 'Glass shopfront 2.80 m high') + '; power, water, drainage, gas and a hood exhaust duct are in place as a food and beverage unit.')
FB = ('أغذية ومشروبات', 'فود كورت')


def spec_text(u):
    """Clear height by floor; glass shopfront 3.20 m for the phase-two units on the plaza (ground), 2.80 m elsewhere;
    water, drainage, gas and hood duct only for food and beverage units."""
    ha, he = {'g': ('الارتفاع الداخلي ٤٫٦ م، ', 'Clear internal height 4.6 m; '), 'f1': ('الارتفاع الداخلي ٤٫٦ م، ', 'Clear internal height 4.6 m; '),
              'f2': ('الارتفاع الداخلي ٣٫٦ م، ', 'Clear internal height 3.6 m; '), 'b1': ('الارتفاع الداخلي ٥٫٦ م، ', 'Clear internal height 5.6 m; ')}[u['f']]
    plaza = u['id'] in PHASE2 and u['f'] == 'g'
    ga, ge = ('٣٫٢٠', '3.20') if plaza else ('٢٫٨٠', '2.80')
    if u['id'] in GLASS:
        g = float(GLASS[u['id']]); ge = f'{g:.2f}'; ga = ge.translate(str.maketrans('0123456789.', '٠١٢٣٤٥٦٧٨٩٫'))
    fb = u['cat'] in ('أغذية ومشروبات', 'فود كورت')
    ar = ha + ('و' if ha else '') + f'واجهة زجاجية بارتفاع {ga} م، ' + ('والكهرباء والمياه والصرف والغاز ودكت شفاط الهود جاهزة لأنها وحدة مطاعم.' if fb else 'والكهرباء جاهزة.')
    en = (he + 'glass shopfront' if he else 'Glass shopfront') + f' {ge} m high; ' + ('power, water, drainage, gas and a hood exhaust duct are in place as a food and beverage unit.' if fb else 'power is in place.')
    return t(ar, en)
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
    u['note'] = (u.get('note') or '').strip() + ' ' + spec_text(u) + ' ' + (PH2 if u['id'] in PHASE2 else PHB.get(u['id'], PH3))
assert sum(1 for u in units if not u['held']) == len(OFFER)
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

rep('<script src="site.js?v=15k"></script>', '<script src="site-full.js?v=5"></script>')
rep('<script src="i18n.js?v=15b"></script>', '<script src="i18n-en-full.js?v=5"></script><script src="i18n.js?v=15b"></script>')

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
    (t('٥٫٦ · ٤٫٦ · ٣٫٦ م', '5.6 · 4.6 · 3.6 m'), t('الارتفاع الداخلي: البدروم ٥٫٦ م، والأرضي والأول ٤٫٦ م، والثاني ٣٫٦ م', 'Clear height: basement 5.6 m, ground and first floors 4.6 m, second floor 3.6 m')),
    (t('٣٫٢٠ م · ٢٫٨٠ م', '3.20 m · 2.80 m'), t('الواجهة الزجاجية: ٣٫٢٠ م لمحلات المرحلة الثانية على البلازا، و٢٫٨٠ م لباقي المحلات', 'Glass shopfront: 3.20 m for the phase-two shops on the plaza, 2.80 m for the other shops')),
    (t('كل الوحدات', 'All units'), t('الكهرباء جاهزة', 'Power in place')),
    (t('المطاعم', 'Food & beverage'), t('مياه وصرف وغاز ودكت شفاط للهود لوحدات المطاعم والكافيهات والفود كورت', 'Water, drainage, gas and a hood exhaust duct for restaurant, café and food-court units'))]) + '</ul>')
summary = ''.join(f'<li><b>{FLOOR[f]}</b> {num(n, 0)} · {num(ar)} م²</li>' for f, (n, ar) in sorted(tot.items(), key=lambda x: order[x[0]]))
table = ('<section class="section hp-units" id="units-list"><div class="wrap"><span class="over">AVAILABLE FOR LEASE</span>'
         '<h2>' + t('دليل الوحدات المتاحة للإيجار', 'Units available for lease') + '</h2>'
         f'<p class="hp-units-lead">{num(len(avail), 0)} ' + t('وحدة متاحة للإيجار بمساحة محمّلة إجمالية', 'units available for lease, with a total loaded area of')
         + f' {num(sum(x[1] for x in tot.values()))} م². ' + t('المساحات محمّلة، والإيجار يُحتسب على المساحة المحمّلة.', 'All areas are loaded areas; rent is charged on the loaded area.') + '</p>'
         + specs + f'<ul class="hp-units-sum">{summary}</ul>'
         '<div class="hp-units-scroll"><table class="hp-units-table">' + TH('<th>' + t('التراس الخارجي م²', 'Outdoor terrace m²') + '</th><th>' + t('التشغيل', 'Opening') + '</th>') + '<tbody>'
         + ''.join(row(u, (f'<td class="num">{num(u["extra"])}</td>' if u.get("extra") else '<td class="num">—</td>') + f'<td class="ph{2 if u["id"] in PHASE2 else 3}">{P2 if u["id"] in PHASE2 else P3 + ("*" if u["id"] in BACK else "")}</td>') for u in avail)
         + '</tbody></table></div><p class="hp-units-foot">* ' + t('تنضم للمرحلة الثانية (يونيو ٢٠٢٧) إذا استأجرها مستأجر الوحدة الملاصقة لها من الظهر.', 'Joins phase two (June 2027) if leased together with the unit directly behind it.') + '</p>'
         '<p class="hp-pack-row"><a class="action" href="Happiness_Plaza_Leasing_Pack.pdf" download>' + t('ملف التأجير PDF · عربي', 'Leasing Pack PDF · Arabic') + '</a> '
         '<a class="secondary" href="Happiness_Plaza_Leasing_Pack_EN.pdf" download>Leasing Pack PDF · English</a> '
         '<a class="action" href="Happiness_Plaza_Book.pdf" download>' + t('الدليل الكامل بالمراحل PDF · عربي', 'Complete book PDF · Arabic') + '</a> '
         '<a class="secondary" href="Happiness_Plaza_Book_EN.pdf" download>Complete book PDF · English</a></p></div></section>')
a, b = section('atlas'); s = s[:a] + table + s[a:]
s = re.sub(r'<a class="hp-tile hp-gold" href="\?floor=g" data-route="plan/g"><strong>مخططات المحلات</strong><small>[^<]*</small></a>',
           '<a class="hp-tile hp-gold" href="./#units-list" data-route="units-list"><strong>' + t('الوحدات المتاحة', 'Available units') + '</strong><small>'
           + t('٦١ وحدة متاحة للإيجار والمخططات', '61 units for lease, with plans') + '</small></a>', s, count=1)

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
s = s[:m.start()] + '<p>' + t('بدأ في ٢٠٢١ بمشروع هابينس بلازا عند مدخل قنا الجديدة: أرض ١٧٬٧٨٥ م²، وبلازا داخلية ١٬٨٥٧ م²، وثلاث مراحل: الفندق والترفيه، ثم مطاعم البلازا وواجهة الأزياء، ثم باقي المحلات والهايبر ماركت.',
      'Launched in 2021 with Happiness Plaza at the entrance of New Qena: a 17,785 m² site, a 1,857 m² internal plaza and three phases: the hotel and leisure, then the plaza restaurants and fashion frontage, then the remaining shops and the hypermarket.') + '</p>' + s[m.end():]

# garage 200 cars
rep('<strong>جراج على مستويين لـ٢٠٠ سيارة</strong><span>سعة تصميمية، منها ٣٬٦٤٤ م² في البدروم الأول.</span>',
    '<strong>' + t('جراج على مستويين يتسع لـ٢٠٠ سيارة', 'A two-level garage for 200 cars') + '</strong><span>' + t('٧٬٢٨٩ م²، بواقع ٣٬٦٤٤ م² لكل مستوى.', '7,289 m², 3,644 m² on each level.') + '</span>')
s = re.sub(r'<p>يعرض الملف جراجًا[^<]*</p>', lambda m: (
    '<p>' + t('جراج على مستويين يتسع لـ٢٠٠ سيارة بمساحة ٧٬٢٨٩ م² (٣٬٦٤٤ م² لكل مستوى). يشمل البرنامج مصلى ودورات مياه للرجال والسيدات وذوي الإعاقة وماكينة صراف آلي.',
              'A two-level garage for 200 cars, 7,289 m² (3,644 m² on each level). The programme includes a prayer room, toilets for men, women and people with disabilities, and an ATM.') + '</p>'), s, count=1)

rep('مقصد التسوق الجديد لأهالي قنا · ١٤٤ وحدة تجارية للإيجار', t('مقصد التسوق الجديد لأهالي قنا · ٦١ وحدة متاحة للإيجار', 'Qena’s new shopping destination · 61 units for lease'))
s = s.replace('١٤٤ وحدة تجارية للإيجار', '٦١ وحدة متاحة للإيجار').replace('144 retail units for lease', '61 units for lease')
s = s.replace('<a class="sourceLink" download href="Happiness_Plaza_Leasing.pdf">عرض دليل الوحدات PDF</a>', '<a class="sourceLink" download href="Happiness_Plaza_Book.pdf">' + t('الدليل الكامل بالمراحل PDF', 'Complete book by phase PDF') + '</a>')
for bad in ['هايبر ماركت الحبيب', 'يشغّلها الحبيب', 'يشغّله الحبيب', 'يشغّلها المالك', 'الحبيب ستور', 'ديسمبر ٢٠٢٦', 'دراسة سوق', 'زيارة في اليوم', 'سعة تصميمية', 'Qena_Market_and_Footfall']:
    assert bad not in s, bad
DAILY = ['B01', 'G16-21', 'F16-20', 'G46']
groups = [
    ('daily', t('تسوق يومي', 'Daily shopping'), lambda u: u['id'] in DAILY,
     t('هايبر ماركت ومحلّا تجزئة وصيدلية.', 'A hypermarket, two retail stores and a pharmacy.')),
    ('fashion', t('أزياء وإكسسوارات ولايف ستايل', 'Fashion, accessories & lifestyle'),
     lambda u: u['cat'] in ('أزياء', 'إكسسوارات', 'لايف ستايل', 'موبايلات', 'اتصالات'),
     t('أزياء وإكسسوارات وموبايلات واتصالات ولايف ستايل.', 'Fashion, accessories, mobiles, telecom and lifestyle.')),
    ('food', t('مطاعم وكافيهات وفود كورت', 'Restaurants, cafés & food court'),
     lambda u: u['cat'] in ('أغذية ومشروبات', 'فود كورت'),
     t('مطاعم وكافيهات بتراسات على البلازا، وفود كورت في الدور الأول.', 'Restaurants and cafés with plaza terraces, and a first-floor food court.')),
    ('fun', t('ترفيه وأطفال', 'Entertainment & kids'),
     lambda u: u['cat'] in ('ترفيه', 'منطقة أطفال وحضانة'),
     t('مساحتان للترفيه في الدور الثاني، ومنطقة أطفال وحضانة في البدروم.', 'Two entertainment spaces on the second floor and a kids’ area and nursery in the basement.')),
    ('show', t('معارض وخدمات مالية وتجميل', 'Showrooms, finance & beauty'),
     lambda u: u['cat'] in ('معرض', 'خدمات مالية', 'صالون وبيوتي سنتر', 'صيدلية وخدمات طبية') and u['id'] not in DAILY,
     t('معارض وفروع بنوك وصالون وبيوتي سنتر وخدمات طبية.', 'Showrooms, bank branches, a salon and beauty centre and medical services.')),
    ('retail', t('محلات تجارية', 'Retail shops'), lambda u: True,
     t('محلات بمساحات متنوعة على الأدوار الأربعة.', 'Shops in a range of sizes across the four levels.')),
]
counts, seen = {}, set()
for key, _, test, _ in groups:
    n = 0
    for u in units:
        if u['id'] not in seen and test(u):
            seen.add(u['id']); n += 1
    counts[key] = n
assert sum(counts.values()) == len(units) == 144, counts
mix = ''.join(f'<article><b>{num(counts[k], 0)} {"وحدة" if counts[k] > 10 or counts[k] < 3 else "وحدات"}</b><h3>{title}</h3><p>{body}</p></article>'
              for k, title, _, body in groups)
for k, v in counts.items():
    EN[num(v, 0) + ' وحدة'] = f'{v} units'; EN[num(v, 0) + ' وحدات'] = f'{v} units'
s = re.sub(r'<div class="story-mix">.*?</div><p class="story-note">',
           '<div class="story-mix">' + mix + '</div><p class="story-total">'
           + t('المجموع: ١٤٤ وحدة تجارية على أربعة أدوار، إلى جانب فندق بلازا (١٤ غرفة وجناحًا) وأنشطة المرحلة الأولى.',
               'Total: 144 retail units on four levels, plus the Plaza Hotel (14 rooms) and the phase one leisure venues.')
           + '</p><p class="story-note">', s, count=1, flags=re.S)

# ---- interactive phase sections (phase two June 2027, phase three December 2027) ----
import importlib.util as _iu2
_sp2 = _iu2.spec_from_file_location('phase_sections', __file__.rsplit('/', 1)[0] + '/phase_sections.py'); _ps = _iu2.module_from_spec(_sp2); _sp2.loader.exec_module(_ps)
_PRE = ''
_s2, _s3 = _ps.build(B, units, OFFER, PHASE2, BACK, t, num, FLOOR, pre=_PRE)
i = s.index('id="market"'); b = s.index('</section>', i) + len('</section>')
s = s[:b] + _s2 + _s3 + s[b:]
_n2 = sum(1 for k in PHASE2 if k in set(OFFER)); _n3 = len(OFFER) - _n2
_tiles = ('<a class="hp-tile" href="./#phase2" data-route="phase2"><strong>' + t('المرحلة الثانية', 'Phase two') + '</strong><small>'
          + t('تشغيل يونيو ٢٠٢٧', 'Opening June 2027') + ' · ' + num(_n2, 0) + ' ' + t('وحدة', 'units') + '</small></a>'
          '<a class="hp-tile" href="./#phase3" data-route="phase3"><strong>' + t('المرحلة الثالثة', 'Phase three') + '</strong><small>'
          + t('تشغيل ديسمبر ٢٠٢٧', 'Opening December 2027') + ' · ' + num(_n3, 0) + ' ' + t('وحدة', 'units') + '</small></a>')
s, _k = re.subn(r'<a class="hp-tile" href="[^"]*#market" data-route="market"><strong>مراحل التشغيل</strong><small>[^<]*</small></a>', _tiles, s, count=1)
assert _k == 1, 'phase tile'
s = s.replace('href="./#market" data-route="market"><span>المرحلة الثانية', 'href="./#phase2" data-route="phase2"><span>المرحلة الثانية')
s = s.replace('data-route="plan/g"><span>المرحلة الثالثة', 'data-route="phase3"><span>المرحلة الثالثة').replace('href="?floor=g" data-route="phase3"', 'href="./#phase3" data-route="phase3"')
_P2TXT = t('وحدات الأرضي المطلة على البلازا: المطاعم بتراساتها الخارجية، وواجهة الأزياء، والشوروم والبنوك، ومعها في الدور الأول الفود كورت والبنك والشوروم الدوبلكس.',
           'The ground-floor units facing the plaza: restaurants with outdoor terraces, the fashion frontage, showrooms and banks, plus the first-floor food court and the duplex bank and showroom.')
s = s.replace('مطاعم البلازا وواجهة الأزياء والمحلات المطلة على البلازا في الدور الأرضي، والوحدة F16-20 في الدور الأول.', _P2TXT)
s = s.replace('<strong>مطاعم البلازا وواجهة الأزياء</strong>', '<strong>' + t('وحدات البلازا والفود كورت', 'Plaza units and the food court') + '</strong>')
s, _k = re.subn(r'<h3>وحدات المرحلة الثانية المتاحة للإيجار</h3>.*?</table></div>',
                '<p class="hp-pbtns"><a class="action" href="./#phase2" data-route="phase2">' + t('استكشف المرحلة الثانية', 'Explore phase two') + '</a>'
                '<a class="secondary" href="./#phase3" data-route="phase3">' + t('استكشف المرحلة الثالثة', 'Explore phase three') + '</a></p>', s, count=1, flags=re.S)
assert _k == 1, 'overview table'
s = s.replace('<script src="launcher.js?v=15f"></script>', '<script src="launcher.js?v=15g"></script><script src="phases.js?v=1"></script>')

# ---- app: install button, screen mode, own manifest ----
s = s.replace('<script src="phases.js?v=1"></script>', '<script src="phases.js?v=1"></script><script src="app.js?v=1"></script>', 1)
s = s.replace('<div class="hp-mini">', '<div class="hp-mini"><a class="hp-screen-link" href="./?screen=1">' + t('عرض على الشاشة', 'Show on a screen') + ' <span aria-hidden="true">▶</span></a>'
              '<button type="button" class="hp-install">' + t('ثبّت التطبيق', 'Install the app') + ' <span aria-hidden="true">⤓</span></button>', 1)


import importlib.util as _iu
_sp = _iu.spec_from_file_location('drive_fix', __file__.rsplit('/', 1)[0] + '/drive_fix.py'); _df = _iu.module_from_spec(_sp); _sp.loader.exec_module(_df)
s = _df.apply(s, t)

open(B + '/index.html', 'w', encoding='utf-8').write(s)
open(B + '/i18n-en-full.js', 'w', encoding='utf-8').write(
    '/* English for the detailed guide: phases, specs and edited sentences. Loaded after i18n-en.js. */\n'
    '(function(){var D=window.HP_EN;if(!D)return;var A=' + json.dumps(EN, ensure_ascii=False, separators=(',', ':')) + ';for(var k in A)D[k]=A[k];})();\n')
print('full built:', len(avail), 'units for lease;', len(EN), 'English entries')
