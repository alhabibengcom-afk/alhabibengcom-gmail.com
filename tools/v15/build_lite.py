"""Build the simple brand page (lite.html) from the full guide, applying the brand-page review.

Usage: python3 build_lite.py SITE_DIR LEASE_LIST_JSON
  LEASE_LIST_JSON: the unit codes offered for lease by Al-Habeeb (sheet "قائمة التأجير",
  rows "إيجار - الحبيب"). Only these units, plus the four units Al-Habeeb runs itself,
  appear in the simple page. Net areas, owner and sale status never appear.
Writes lite.html, site-lite.js, unit-viewer-lite.js, i18n-en-lite.js. The full guide
(index.html and its files) is not changed.
"""
import json, re, sys

B, LIST = sys.argv[1:3]
OFFER = json.load(open(LIST, encoding='utf-8'))
SELF = {'B01', 'G16-21', 'F16-20', 'G46'}
DIG = str.maketrans('0123456789.,', '٠١٢٣٤٥٦٧٨٩٫٬')
EN = {}


def t(ar, en):
    EN[ar] = en
    return ar


def num(v, d=2):
    s = f'{v:,.{d}f}'
    return s.translate(DIG)


t('الوحدات المتاحة والمخططات', 'Available units and plans'); t('المالك والمطوّر', 'The owner'); t('تواصل مع فريق التأجير', 'Contact the leasing team')
t('الأنشطة التي تفتح مع المرحلة الأولى', 'Venues opening with phase one'); t('تم نسخ رابط الدليل.', 'Link copied.'); t('مشاركة على واتساب', 'Share on WhatsApp'); t('صورة من هابينس بلازا', 'Happiness Plaza photo')
NAMES_EN = {'جيم Guru Fit': 'Guru Fit gym', 'نادي صحي نسائي AURA': 'AURA women’s spa', 'مطعم بوخارست بلاك': 'Bokharest Black restaurant', 'ألعاب أطفال Joy Park': 'Joy Park kids’ play', 'فندق بلازا · ١٤ غرفة وجناحًا': 'Plaza Hotel · 14 rooms and suites', 'سندوتشات خفيفة وآيس كريم Joy Bites': 'Joy Bites sandwiches and ice cream', 'صيدلية هابينس': 'Happiness Pharmacy'}
for _k, _v in NAMES_EN.items(): t(_k, _v)
FLOOR = {'b1': 'البدروم', 'g': 'الأرضي', 'f1': 'الأول', 'f2': 'الثاني'}
# clear internal height: ground and first 4.6 m, second 3.6 m; basement not confirmed yet
HEIGHT = {'g': ('الارتفاع الداخلي ٤٫٦ م، ', 'Clear internal height 4.6 m; '), 'f1': ('الارتفاع الداخلي ٤٫٦ م، ', 'Clear internal height 4.6 m; '),
          'f2': ('الارتفاع الداخلي ٣٫٦ م، ', 'Clear internal height 3.6 m; '), 'b1': ('الارتفاع الداخلي ٥٫٦ م، ', 'Clear internal height 5.6 m; ')}
SPECS = {}
for _f, (_ha, _he) in HEIGHT.items():
    SPECS[_f, False] = t(_ha + ('و' if _ha else '') + 'واجهة زجاجية بارتفاع ٢٫٨٠ م، والكهرباء جاهزة.',
                         _he + 'glass shopfront 2.80 m high; power is in place.' if _he else 'Glass shopfront 2.80 m high; power is in place.')
    SPECS[_f, True] = t(_ha + ('و' if _ha else '') + 'واجهة زجاجية بارتفاع ٢٫٨٠ م، والكهرباء والمياه والصرف والغاز ودكت شفاط الهود جاهزة لأنها وحدة مطاعم.',
                        (_he + 'glass shopfront 2.80 m high' if _he else 'Glass shopfront 2.80 m high') + '; power, water, drainage, gas and a hood exhaust duct are in place as a food and beverage unit.')
# operating phases (owner, Nov 2026): phase one runs now; phase two June 2027; everything else incl. hypermarket December 2027
PHASE2 = ['G39', 'G40', 'G41', 'G42', 'G42-1', 'G26-28', 'G30-32', 'G34-36', 'G38',
          'G06', 'G07-12', 'G08', 'G09', 'G11', 'G12-14', 'G13', 'G15', 'G16-21', 'F16-20']
BACK = {'G25-27': 'G26-28', 'G29-31': 'G30-32', 'G33-35': 'G34-36', 'G37': 'G38'}  # phase two only if taken with the front unit

# Optional overrides from the Drive sheet (written by tools/auto/sync_units.py): phase-two units and glass heights.
import os as _os
GLASS = {}
if _os.path.exists(B + '/site-config.json'):
    _cfg = json.load(open(B + '/site-config.json', encoding='utf-8'))
    PHASE2 = _cfg.get('phase2') or PHASE2
    GLASS = _cfg.get('glass') or {}
P2 = t('يونيو ٢٠٢٧', 'June 2027'); P3 = t('ديسمبر ٢٠٢٧', 'December 2027')
PH_NOTE2 = t('ضمن المرحلة الثانية، والتشغيل في يونيو ٢٠٢٧.', 'Part of phase two, opening in June 2027.')
PH_NOTE3 = t('ضمن المرحلة الثالثة، والتشغيل في ديسمبر ٢٠٢٧.', 'Part of phase three, opening in December 2027.')
PH_BACK = {k: t(f'ضمن المرحلة الثالثة (ديسمبر ٢٠٢٧)، وتنضم للمرحلة الثانية (يونيو ٢٠٢٧) إذا استأجرها مستأجر الوحدة {v} الملاصقة لها من الظهر.',
                f'Part of phase three (December 2027); it joins phase two (June 2027) if leased together with unit {v} directly behind it.') for k, v in BACK.items()}
def phase_of(uid):
    return 2 if uid in PHASE2 else 3
CONTACT = t('تواصل مع فريق التأجير', 'Contact the leasing team')
LOADED = t('المساحات محمّلة، والإيجار يُحتسب على المساحة المحمّلة.', 'All areas are loaded areas; rent is charged on the loaded area.')
FINAL = t('التوافر النهائي والحجز والتعاقد تتم من خلال فريق التأجير.', 'Final availability, booking and contracts are handled by the leasing team.')

# ---------------- units ----------------
site = open(B + '/site.js', encoding='utf-8').read()
i0 = site.index('const UNITS=') + len('const UNITS=')
units, e = json.JSONDecoder().raw_decode(site[i0:])
i1 = i0 + e
byid = {u['id']: u for u in units}

ZONE = {  # review section 3
    'G05': ('خدمات مالية', 'دوبلكس بسلم داخلي مع الوحدة F08 في الدور الأول. تُعرض كل وحدة بكودها.'),
    'F08': ('خدمات مالية', 'دوبلكس بسلم داخلي مع الوحدة G05 في الدور الأرضي. تُعرض كل وحدة بكودها.'),
    'G44': ('معرض', 'دوبلكس بسلم داخلي مع الوحدة F46-48 في الدور الأول. تُعرض كل وحدة بكودها.'),
    'F46-48': ('معرض', 'دوبلكس بسلم داخلي مع الوحدة G44 في الدور الأرضي. تُعرض كل وحدة بكودها.'),
    'G13': ('أغذية ومشروبات', ''),
    'G15': ('أغذية ومشروبات', ''),
}
t('دوبلكس بسلم داخلي مع الوحدة F05-07 في الدور الأول. تُعرض كل وحدة بكودها.', 'Duplex with an internal stair to unit F05-07 on the first floor. Each unit keeps its own code.')
t('دوبلكس بسلم داخلي مع الوحدة G04 في الدور الأرضي. تُعرض كل وحدة بكودها.', 'Duplex with an internal stair to unit G04 on the ground floor. Each unit keeps its own code.')
t('دوبلكس بسلم داخلي مع الوحدة F08 في الدور الأول. تُعرض كل وحدة بكودها.', 'Duplex with an internal stair to unit F08 on the first floor. Each unit keeps its own code.')
t('دوبلكس بسلم داخلي مع الوحدة G05 في الدور الأرضي. تُعرض كل وحدة بكودها.', 'Duplex with an internal stair to unit G05 on the ground floor. Each unit keeps its own code.')
t('دوبلكس بسلم داخلي مع الوحدة F46-48 في الدور الأول. تُعرض كل وحدة بكودها.', 'Duplex with an internal stair to unit F46-48 on the first floor. Each unit keeps its own code.')
t('دوبلكس بسلم داخلي مع الوحدة G44 في الدور الأرضي. تُعرض كل وحدة بكودها.', 'Duplex with an internal stair to unit G44 on the ground floor. Each unit keeps its own code.')
t('صالون وبيوتي سنتر', 'Salon & beauty centre')
for uid, (cat, _) in ZONE.items():
    byid[uid]['cat'] = cat
    if byid[uid].get('title') not in ('مطعم وكافيه على البلازا',):
        byid[uid]['title'] = cat

# category counts over all 144 units (review 1.1)
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
    ('show', t('معارض وخدمات مالية وطبية', 'Showrooms, finance & medical'),
     lambda u: u['cat'] in ('معرض', 'خدمات مالية', 'صالون وبيوتي سنتر', 'صيدلية وخدمات طبية') and u['id'] not in DAILY,
     t('معارض وفروع بنوك وخدمات طبية.', 'Showrooms, bank branches and medical services.')),
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
# lite unit set and notes (no net area, no owner or sale status)
lite_units = []
for u in units:
    if u['id'] not in OFFER and u['id'] not in SELF:
        continue
    v = dict(u)
    note = f"المساحة المحمّلة {num(u['area'])} م². الإيجار يُحتسب على المساحة المحمّلة."
    if u.get('parts'):
        note = 'وحدة مضمومة من ' + ' و'.join(u['parts']) + ' تُعرض كوحدة واحدة. ' + note
    if u.get('extra'):
        note += f" لها تراس خارجي على البلازا مساحته {num(u['extra'])} م² غير محسوب في المساحة المحمّلة."
    z = ZONE.get(u['id'], ('', ''))[1]
    if z:
        note = z + ' ' + note
    note += ' ' + spec_text(u)
    note += ' ' + (PH_NOTE2 if u['id'] in PHASE2 else PH_BACK.get(u['id'], PH_NOTE3))
    v['note'] = note
    v.pop('net', None)
    if u['id'] in SELF:
        v['held'] = True; v['status'] = t('غير معروضة للإيجار', 'Not offered for lease')
        v['title'] = {'B01': t('هايبر ماركت', 'Hypermarket'), 'G16-21': t('محل تجزئة', 'Retail store'), 'F16-20': t('محل تجزئة', 'Retail store')}.get(u['id'], v.get('title'))
    else:
        v['held'] = False; v['status'] = t('متاحة للإيجار', 'Available for lease')
    lite_units.append(v)
assert len([u for u in lite_units if not u['held']]) == len(OFFER), (len(lite_units), len(OFFER))

slite = site[:i0] + json.dumps(lite_units, ensure_ascii=False, separators=(',', ':')) + site[i1:]
# no booking form: contact the leasing team instead
slite = re.sub(r'function booking\(u\)\{', 'function booking(u){window.HP_LAST_UNIT=u&&u.id;navigateSite("contact");return;', slite, count=1)
slite = slite.replace("'لوحة تصميم هايبر ماركت الحبيب'", "'لوحة تصميم الهايبر ماركت'").replace('"المرحلة الثالثة · هايبر ماركت الحبيب"', '"المرحلة الثالثة · الهايبر ماركت"')
t('لوحة تصميم الهايبر ماركت', 'Hypermarket design plan')
open(B + '/site-lite.js', 'w', encoding='utf-8').write(slite)

uv = open(B + '/unit-viewer.js', encoding='utf-8').read()
uv = uv.replace("btn('طلب معاينة الوحدة',()=>booking(u),'action'),", '')
uv = uv.replace("'المساحة المحملة (أساس الإيجار)'", "'المساحة المحمّلة (أساس الإيجار)'")
open(B + '/unit-viewer-lite.js', 'w', encoding='utf-8').write(uv)
t('المساحة المحمّلة (أساس الإيجار)', 'Loaded area (rent basis)')

# ---------------- page ----------------
s = open(B + '/index.src.html', encoding='utf-8').read()


def rep(a, b, count=1, need=True):
    global s
    if a not in s:
        if need:
            raise SystemExit('not found: ' + a[:80])
        return
    s = s.replace(a, b) if count == 0 else s.replace(a, b, count)


def cut(sel_start, sel_end_tag):
    """Remove the element that starts with sel_start (string) up to its matching close tag."""
    global s
    i = s.index(sel_start)
    tag = re.match(r'<(\w+)', s[i:]).group(1)
    depth, j = 0, i
    for m in re.finditer(rf'<{tag}\b|</{tag}>', s[i:]):
        depth += 1 if m.group(0) != f'</{tag}>' else -1
        if depth == 0:
            j = i + m.end(); break
    s = s[:i] + s[j:]


rep('pro.css?v=15s', 'pro.css?v=15s')
# lite flag (static)
s, nflag = re.subn(r'<script>\(function\(\)\{var (?:q=new URLSearchParams\(location\.search\),)?l=(?:q|new URLSearchParams\(location\.search\))\.get\("lite"\).*?</script>',
           '<script>window.HP_LITE=true;document.documentElement.classList.add("hp-lite")</script>', s, count=1, flags=re.S)
assert nflag == 1, 'lite flag not set'
# English dictionary + lite overrides
rep('document.write(\'<script src="i18n-en.js?v=15n"><\\/script>\')',
    'document.write(\'<script src="i18n-en.js?v=15n"><\\/script><script src="i18n-en-lite.js?v=11"><\\/script>\')')
# own scripts
rep('<script src="site.js?v=15k"></script>', '<script src="site-lite.js?v=9"></script>')
rep('<script src="unit-viewer.js?v=15b"></script>', '<script src="unit-viewer-lite.js?v=1"></script>')
rep('<script src="lite.js?v=15b"></script>', '<script src="lite.js?v=3"></script>')
rep('launcher.js?v=15f', 'launcher.js?v=15f')
# links that would leave the simple page
s = s.replace('href="./#', 'href="lite.html#').replace('href="?', 'href="lite.html?')
rep('<link rel="manifest" href="manifest.webmanifest">', '<link rel="manifest" href="manifest.webmanifest">', need=False)

# meta
rep('واطلب معاينة مع إدارة التأجير.', 'وتواصل مع فريق التأجير.', need=False)

# 5.6 spelling, 5.8 spacing
rep('AL-HABEEB FOR DEVELOPMENT &amp; INVESTMENT LLC', 'ALHABEEB FOR DEVELOPMENT &amp; INVESTMENT LLC')
rep('AL-HABEEB HYPERMARKET', 'ALHABEEB HYPERMARKET')
rep('<span lang="en" dir="ltr">LEASING GUIDE</span><i aria-hidden="true"></i>', '<span lang="en" dir="ltr">LEASING GUIDE</span> <i aria-hidden="true"></i> ')

# 5.7 plain Arabic headings
for a, b, en in [('مين المالك؟', 'المالك والمطوّر', 'The owner'),
                 ('ليه قنا والصعيد؟', 'لماذا قنا وصعيد مصر؟', 'Why Qena and Upper Egypt?'),
                 ('ليه قنا', 'لماذا قنا', 'Why Qena')]:
    s = s.replace(a, b); t(b, en)

# home: operators strip (6.1), contact tile (4.1), 360 label (2.8)
strip = ('<div class="hp-ops" role="list" aria-label="' + t('المشغّلون في المشروع', 'Operators at the project') + '">'
         '<span class="hp-ops-h">' + t('المشغّلون في المشروع', 'Operators at the project') + '</span>'
         + ''.join(f'<span role="listitem">{x}</span>' for x in [
             t('هايبر ماركت الحبيب ٥٬٥٦٢ م²', 'Al Habeeb Hypermarket 5,562 m²'), 'Bokharest Black', 'Joy Park', 'Guru Fit', 'AURA',
             t('فندق بلازا', 'Plaza Hotel')]) + '</div>')
rep('<nav class="hp-grid"', strip + '<nav class="hp-grid"')
rep('<strong>احجز معاينة</strong><small>واتساب 0122 777 7104</small>', f'<strong>{CONTACT}</strong><small>واتساب 0122 777 7104</small>')
rep('جولة المحلات <bdi dir="ltr">360°</bdi></a><a href="lite.html#tour"', 'جولة الدور الأول <bdi dir="ltr">360°</bdi></a><a href="lite.html#tour"')
t('جولة الدور الأول', 'First-floor tour')


# home: units tile opens the available-units table; tagline with the available count
s = re.sub(r'<a class="hp-tile hp-gold" href="lite\.html\?floor=g" data-route="plan/g"><strong>مخططات المحلات</strong><small>[^<]*</small></a>',
           '<a class="hp-tile hp-gold" href="lite.html#units-list" data-route="units-list"><strong>' + t('الوحدات المتاحة', 'Available units') + '</strong><small>'
           + t('٥٩ وحدة متاحة للإيجار والمخططات', '59 units for lease, with plans') + '</small></a>', s, count=1)
rep('مقصد التسوق الجديد لأهالي قنا · ١٤٤ وحدة تجارية للإيجار', t('مقصد التسوق الجديد لأهالي قنا · ٥٩ وحدة متاحة للإيجار', 'Qena’s new shopping destination · 59 units for lease'))

# owner (1.2, 1.4, 1.5, 5.1)
rep("<b>٢٠٬٠٠٠ م²</b><span>أرض هابينس بلازا</span>", "<b>١٧٬٧٨٥ م²</b><span>" + t('أرض هابينس بلازا حسب العقود', 'Happiness Plaza site, per the contracts') + "</span>")
rep('صمّمت المجموعة ونفّذت مبنى الفندق والترفيه في المرحلة الأولى: ٧٬٠٠٠ م² من بدروم وثلاثة أدوار، وفندق بوتيك من ١٤ غرفة. اكتمل التنفيذ والتشطيبات، والمرحلة الأولى قيد التشغيل والافتتاح الرسمي في ديسمبر ٢٠٢٦.',
    t('صمّمت المجموعة ونفّذت مبنى الفندق والترفيه في المرحلة الأولى، وفيه فندق بوتيك من ١٤ غرفة وجناحًا. المرحلة الأولى قيد التشغيل، والافتتاح الرسمي في ديسمبر ٢٠٢٦.',
      'The group designed and built the phase one hotel and leisure building, with a 14-room boutique hotel. Phase one is in operation; the official opening is in December 2026.'))
cut('<li><strong>إدارة وتشغيل متخصصة</strong>', 'li')
rep('مدخل قنا الجديدة، الحي الأول. فندق ومطاعم', 'مدخل قنا الجديدة، الحي الأول. فندق ومطاعم')
rep('<dt>٢٠٬٠٠٠ م²</dt><dd>مساحة الأرض</dd>', '<dt>١٧٬٧٨٥ م²</dt><dd>' + t('مساحة الأرض حسب العقود', 'Site area, per the contracts') + '</dd>')
rep('<dt>٥٬٥٦٢ م²</dt><dd>مساحة الوحدة</dd>', '<dt>٥٬٥٦٢ م²</dt><dd>' + t('مساحة محمّلة', 'Loaded area') + '</dd>')
cut('<div class="dev-partners">', 'div')

# why (1.8)
rep('وخطة المواطن الاستثمارية لمحافظة قنا ٢٠٢٠/٢٠٢١ (وزارة التخطيط).',
    t('وبيانات ٢٠٢٠/٢٠٢١ الواردة في خطة المواطن الاستثمارية لمحافظة قنا ٢٠٢٣/٢٠٢٤ (وزارة التخطيط).',
      'and 2020/2021 data from the Citizen’s Investment Plan for Qena Governorate 2023/2024 (Ministry of Planning).'))

# location (1.2, 1.3)
rep('<strong>أرض ٢٠٬٠٠٠ م² وبلازا مفتوحة ٤٬٠٠٠ م²</strong>', '<strong>' + t('أرض ١٧٬٧٨٥ م² وبلازا مفتوحة ٤٬٠٠٠ م²', 'A 17,785 m² site and a 4,000 m² open plaza') + '</strong>')
rep('<strong>جراج على مستويين لـ٢٠٠ سيارة</strong><span>سعة تصميمية، منها ٣٬٦٤٤ م² في البدروم الأول.</span>',
    '<strong>' + t('جراج على مستويين بمساحة ٧٬٢٨٩ م²', 'A two-level garage of 7,289 m²') + '</strong><span>'
    + t('٣٬٦٤٤ م² لكل مستوى تحت البدروم.', '3,644 m² on each level, below ground.') + '</span>')
rep('<strong>فندق وبحيرة وأنشطة ترفيهية</strong><span>فندق بلازا ١٤ غرفة،', '<strong>فندق وبحيرة وأنشطة ترفيهية</strong><span>فندق بلازا ١٤ غرفة وجناحًا،')


rep('بدأ في ٢٠٢١ بمشروع هابينس بلازا عند مدخل قنا الجديدة: أرض ٢٠٬٠٠٠ م²، وبلازا مشتركة ٤٬٠٠٠ م²، وثلاث مراحل هي الفندق والترفيه ثم المحلات ثم الهايبر ماركت.',
    t('بدأ في ٢٠٢١ بمشروع هابينس بلازا عند مدخل قنا الجديدة: أرض ١٧٬٧٨٥ م²، وبلازا مشتركة ٤٬٠٠٠ م²، وثلاث مراحل هي الفندق والترفيه ثم المحلات ثم الهايبر ماركت.',
      'Launched in 2021 with Happiness Plaza at the entrance of New Qena: a 17,785 m² site, a 4,000 m² shared plaza and three phases: hotel and leisure, retail, then the hypermarket.'))
rep('يعرض الملف جراجًا على مستويين بسعة تصميمية ٢٠٠ سيارة. وتُظهر لوحة البدروم المعروضة للتأجير ٣٬٦٤٤ م² للجراج على هذا المستوى.',
    t('جراج على مستويين بمساحة ٧٬٢٨٩ م²، منها ٣٬٦٤٤ م² في كل مستوى.', 'A two-level garage of 7,289 m², with 3,644 m² on each level.'))
rep('ليصبح هابينس بلازا المكان اللي تقصده الأسرة', 'ليصبح هابينس بلازا المكان الذي تقصده الأسرة')

# goal (1.1)
mix = ''.join(f'<article><b>{num(counts[k], 0)} {"وحدة" if counts[k] > 10 or counts[k] < 3 else "وحدات"}</b><h3>{title}</h3><p>{body}</p></article>'
              for k, title, _, body in groups)
s = re.sub(r'<div class="story-mix">.*?</div><p class="story-note">',
           '<div class="story-mix">' + mix + '</div><p class="story-total">'
           + t('المجموع: ١٤٤ وحدة تجارية على أربعة أدوار، إلى جانب فندق بلازا (١٤ غرفة وجناحًا) وأنشطة المرحلة الأولى.',
               'Total: 144 retail units on four levels, plus the Plaza Hotel (14 rooms) and the phase one leisure venues.')
           + '</p><p class="story-note">', s, count=1, flags=re.S)
for k, v in counts.items():
    EN[num(v, 0) + ' وحدة'] = f'{v} units'; EN[num(v, 0) + ' وحدات'] = f'{v} units'

# phase (1.4, 4.4, 4.6, 5.5)
rep('<li><a href="lite.html#atlas" data-route="atlas">', '<li><a href="lite.html?floor=g" data-route="plan/g">')
rep('من غرف فندق بلازا إلى مطعم الجزيرة ونوادي الصحة واللياقة. قيد التشغيل، والافتتاح الرسمي في ديسمبر ٢٠٢٦.',
    t('فندق بلازا ومطعم الجزيرة والجيم والنادي الصحي وألعاب الأطفال. المرحلة الأولى قيد التشغيل، والافتتاح الرسمي في ديسمبر ٢٠٢٦.',
      'The Plaza Hotel, the island restaurant, gym, spa and kids’ play. Phase one is in operation; the official opening is in December 2026.'))

# market (1.8, 1.9, 5.10)
rep('في ٢٠٢٠/٢٠٢١ بحسب وزارة التخطيط.', t('في ٢٠٢٠/٢٠٢١، بحسب خطة المواطن الاستثمارية لمحافظة قنا ٢٠٢٣/٢٠٢٤ (وزارة التخطيط).',
                                             'in 2020/2021, per the Citizen’s Investment Plan for Qena Governorate 2023/2024 (Ministry of Planning).'))
rep('التقدير لزيارات المقيمين بعد افتتاح المول التجاري واستقرار تشغيله مع المرحلة الأولى. قد يزور الشخص المشروع أكثر من مرة. حركة المسافرين والسياح والزيارات من محافظات أخرى خارج الحساب.',
    t('نطاق التقدير: زيارات سكان قنا الجديدة وقسم ومركز قنا فقط، بعد افتتاح المحلات التجارية واستقرار تشغيلها مع أنشطة المرحلة الأولى، وقبل تشغيل هايبر ماركت الحبيب (المرحلة الثالثة). لا يشمل المسافرين والسياح والزوار من المحافظات الأخرى. تقدير المول كاملًا مع الهايبر موضّح أدناه.',
      'Scope: visits by residents of New Qena and Qena district and markaz only, once the shops open and settle alongside the phase one venues, before Al Habeeb Hypermarket (phase three) opens. Travellers, tourists and visitors from other governorates are excluded. The estimate for the full mall with the hypermarket follows.'))
s = re.sub(r'<a rel="noopener" href="https://drive\.google\.com/file/d/[^"]+">العرض التعريفي للمطوّر · PowerPoint</a>', '', s)

# hyper (1.5)
rep('<p><b>٥٬٥٦٢ م²</b> هي مساحة الوحدة B01 على مخطط التأجير. ويذكر ملف تصميم الهايبر، الذي بدأ في ٢٠٢٤، مساحة <b>٧٬٠٠٠ م²</b> للمشروع التصميمي في البدروم.</p>',
    '<p><b>٥٬٥٦٢ م²</b> ' + t('مساحة محمّلة للوحدة B01 في البدروم، ويشغّلها الحبيب ماركت.', 'loaded area for unit B01 in the basement, run by Al Habeeb Market.') + '</p>')

# deals (2.6, 2.7) and contact (4.1, 4.7)
rep('<section class="section contact" id="contact">', '<section class="section contact" id="contact">', need=True)
i = s.index('id="contact"'); a = s.rfind('<section', 0, i); b = s.index('</section>', i) + len('</section>')
WA = 'https://wa.me/201227777104?text=' + 'السلام عليكم، أرغب في معرفة الوحدات المتاحة في هابينس بلازا.'
contact = ('<section class="section contact" id="contact"><div class="wrap"><span class="over">LEASING TEAM</span>'
           f'<h2>{CONTACT}</h2><p>' + t('هذه الصفحة للتعريف بالمشروع والوحدات المتاحة للإيجار.', 'This page introduces the project and the units available for lease.') + ' ' + FINAL + '</p>'
           '<div class="actions">'
           f'<a class="action hp-wa" href="{WA}" rel="noopener" target="_blank">' + t('واتساب', 'WhatsApp') + ' <bdi>0122 777 7104</bdi></a>'
           '<a class="secondary" href="tel:+201227777104">' + t('اتصال', 'Call') + ' <bdi>0122 777 7104</bdi></a>'
           '<a class="secondary" href="mailto:info@happinessplaza.com"><bdi>info@happinessplaza.com</bdi></a>'
           '</div><p class="hp-pack-row"><a class="action hp-pack" href="Happiness_Plaza_Leasing_Pack.pdf" download>' + t('حمّل ملف التأجير PDF', 'Download the Leasing Pack PDF') + '</a> <small>' + t('١٢ صفحة · ٢ م.ب', '12 pages · 2 MB') + '</small></p></div></section>')
s = s[:a] + contact + s[b:]
rep('<section class="section" id="deals">', '<section class="section" id="deals">', need=False)
i = s.index('id="deals"'); b = s.index('</section>', i)
s = s[:b] + '<div class="wrap"><p class="hp-terms">' + t('الأسعار ورسوم الخدمة ومدة العقد والزيادة السنوية وفترة التجهيز والتأمين تُحدد في العرض الذي يقدمه فريق التأجير لكل وحدة.',
    'Rent, service charge, lease term, annual increase, fit-out period and deposit are set in the leasing team’s offer for each unit.') + '</p></div>' + s[b:]

# one contact button (6.2): top links, mobile bar and footer
s = re.sub(r'<a href="lite\.html#contact" data-route="contact">احجز معاينة</a></nav>', '</nav>', s, count=1)
rep('<a class="sourceLink" download href="Happiness_Plaza_Leasing.pdf">عرض دليل الوحدات PDF</a>', '')
s = re.sub(r'<a href="lite\.html#contact" data-route="contact" class="hp-back-cta">احجز معاينة</a>', '', s)
s = s.replace('</main>', '</main><a class="hp-fab" href="lite.html#contact" data-route="contact">' + CONTACT + '</a>', 1)

# 2.1/2.3 unit directory of the units available for lease
order = {'b1': 0, 'g': 1, 'f1': 2, 'f2': 3}
avail = sorted([u for u in lite_units if not u['held']], key=lambda u: (order[u['f']], u['id']))
rows, tot = [], {}
for u in avail:
    tot.setdefault(u['f'], [0, 0.0]); tot[u['f']][0] += 1; tot[u['f']][1] += u['area']
    rows.append(f'<tr><td><a href="lite.html?unit={u["id"]}" data-route="unit/{u["id"]}"><bdi>{u["id"]}</bdi></a></td>'
                f'<td>{FLOOR[u["f"]]}</td><td>{u["title"] if u.get("title") else u["cat"]}</td><td class="num">{num(u["area"])}</td>'
                f'<td class="ph{phase_of(u["id"])}">{P2 if u["id"] in PHASE2 else P3 + ("*" if u["id"] in BACK else "")}</td></tr>')
summary = ''.join(f'<li><b>{FLOOR[f]}</b> {num(n, 0)} · {num(a)} م²</li>' for f, (n, a) in sorted(tot.items(), key=lambda x: order[x[0]]))
allsum = sum(a for _, a in tot.values())
table = ('<section class="section hp-units" id="units-list"><div class="wrap"><span class="over">AVAILABLE FOR LEASE</span>'
         '<h2>' + t('دليل الوحدات المتاحة للإيجار', 'Units available for lease') + '</h2>'
         f'<p class="hp-units-lead">{num(len(avail), 0)} ' + t('وحدة متاحة للإيجار بمساحة محمّلة إجمالية', 'units available for lease, with a total loaded area of') + f' {num(allsum)} م². {LOADED} {FINAL}</p>'
         f'<ul class="hp-units-sum">{summary}</ul>'
         '<div class="hp-units-scroll"><table class="hp-units-table"><thead><tr><th>' + t('الوحدة', 'Unit') + '</th><th>' + t('الدور', 'Level') + '</th><th>'
         + t('النشاط', 'Use') + '</th><th>' + t('المحمّلة م²', 'Loaded m²') + '</th><th>' + t('التشغيل', 'Opening') + '</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>'
         '<p class="hp-units-foot">* ' + t('تنضم للمرحلة الثانية (يونيو ٢٠٢٧) إذا استأجرها مستأجر الوحدة الملاصقة لها من الظهر.', 'Joins phase two (June 2027) if leased together with the unit directly behind it.') + '</p></div></section>')
i = s.index('id="atlas"'); a = s.rfind('<section', 0, i)
s = s[:a] + table + s[a:]
t('الأرضي', 'Ground'); t('الأول', 'First'); t('الثاني', 'Second'); t('البدروم', 'Basement')


# full-sentence English for paragraphs edited above
t('المصادر: تقديرات السكان في ١ يوليو ٢٠٢٥ (الجهاز المركزي للتعبئة العامة والإحصاء)، وبيانات ٢٠٢٠/٢٠٢١ الواردة في خطة المواطن الاستثمارية لمحافظة قنا ٢٠٢٣/٢٠٢٤ (وزارة التخطيط).',
  'Sources: population estimates as of 1 July 2025 (CAPMAS), and 2020/2021 data from the Citizen’s Investment Plan for Qena Governorate 2023/2024 (Ministry of Planning).')
t('فندق بلازا ١٤ غرفة وجناحًا، وجزيرة بوخارست على البحيرة، وجيم ونادٍ صحي وألعاب أطفال.',
  'The 14-room Plaza Hotel, Bokharest Island on the lake, a gym, spa and kids’ play.')
t('نجمع البراندات في مكان واحد، ونضيف لها الأكل والترفيه والخدمات اليومية، ليصبح هابينس بلازا المكان الذي تقصده الأسرة في قنا للتسوق والخروج.',
  'We bring brands together in one place, add dining, leisure and daily services, so Happiness Plaza becomes where Qena’s families go to shop and spend time.')
t('شكّلت تجارة الجملة والتجزئة ١٥٪ من الناتج المحلي لمحافظة قنا في ٢٠٢٠/٢٠٢١، بحسب خطة المواطن الاستثمارية لمحافظة قنا ٢٠٢٣/٢٠٢٤ (وزارة التخطيط). يصف المؤشر وزن التجارة في اقتصاد المحافظة. أمّا حجم الطلب على الموقع فيعتمد على تكرار الرحلة من مدينة قنا وجاذبية الهايبر والمطاعم والترفيه.',
  'Wholesale and retail trade made up 15% of Qena Governorate’s GDP in 2020/2021, per the Citizen’s Investment Plan for Qena Governorate 2023/2024 (Ministry of Planning). The indicator shows trade’s weight in the local economy; demand at the site depends on trip frequency from Qena city and the pull of the hypermarket, dining and leisure.')
t('جراج على مستويين بمساحة ٧٬٢٨٩ م²، منها ٣٬٦٤٤ م² في كل مستوى. يشمل البرنامج مصلى ودورات مياه للرجال والسيدات وذوي الإعاقة وماكينة صراف آلي.',
  'A two-level garage of 7,289 m², with 3,644 m² on each level. The programme includes a prayer room, toilets for men, women and people with disabilities, and an ATM.')


# ---- second round: garage capacity, unit specs, full-mall visit estimate ----
rep('<strong>جراج على مستويين بمساحة ٧٬٢٨٩ م²</strong><span>٣٬٦٤٤ م² لكل مستوى تحت البدروم.</span>',
    '<strong>' + t('جراج على مستويين يتسع لـ٢٠٠ سيارة', 'A two-level garage for 200 cars') + '</strong><span>'
    + t('٧٬٢٨٩ م²، بواقع ٣٬٦٤٤ م² لكل مستوى.', '7,289 m², 3,644 m² on each level.') + '</span>')
rep('جراج على مستويين بمساحة ٧٬٢٨٩ م²، منها ٣٬٦٤٤ م² في كل مستوى. يشمل البرنامج مصلى ودورات مياه للرجال والسيدات وذوي الإعاقة وماكينة صراف آلي.',
    t('جراج على مستويين يتسع لـ٢٠٠ سيارة بمساحة ٧٬٢٨٩ م² (٣٬٦٤٤ م² لكل مستوى). يشمل البرنامج مصلى ودورات مياه للرجال والسيدات وذوي الإعاقة وماكينة صراف آلي.',
      'A two-level garage for 200 cars, 7,289 m² (3,644 m² on each level). The programme includes a prayer room, toilets for men, women and people with disabilities, and an ATM.'))
specs = ('<ul class="hp-specs">' + ''.join(f'<li><b>{a}</b><span>{b}</span></li>' for a, b in [
    (t('٥٫٦ · ٤٫٦ · ٣٫٦ م', '5.6 · 4.6 · 3.6 m'), t('الارتفاع الداخلي: البدروم ٥٫٦ م، والأرضي والأول ٤٫٦ م، والثاني ٣٫٦ م', 'Clear height: basement 5.6 m, ground and first floors 4.6 m, second floor 3.6 m')),
    (t('٣٫٢٠ م · ٢٫٨٠ م', '3.20 m · 2.80 m'), t('الواجهة الزجاجية: ٣٫٢٠ م لمحلات المرحلة الثانية على البلازا، و٢٫٨٠ م لباقي المحلات', 'Glass shopfront: 3.20 m for the phase-two shops on the plaza, 2.80 m for the other shops')),
    (t('كل الوحدات', 'All units'), t('الكهرباء جاهزة', 'Power in place')),
    (t('المطاعم', 'Food & beverage'), t('مياه وصرف وغاز ودكت شفاط للهود لوحدات المطاعم والكافيهات والفود كورت', 'Water, drainage, gas and a hood exhaust duct for restaurant, café and food-court units'))]) + '</ul>')
s = s.replace('<ul class="hp-units-sum">', specs + '<ul class="hp-units-sum">', 1)

# full mall with the hypermarket (review 1.9): indicative estimate with its assumptions
rep(' تقدير المول كاملًا مع الهايبر موضّح أدناه.</p>', ' تقدير المول كاملًا مع الهايبر موضّح أدناه.</p>' + (
    '<div class="hp-est"><h3>' + t('تقدير المول كاملًا بعد تشغيل الهايبر', 'Full mall, once the hypermarket opens') + '</h3>'
    '<div class="hp-est-figs">'
    '<div><b>' + t('نحو ٣٬٠٠٠', 'About 3,000') + '</b><span>' + t('زيارة في اليوم', 'visits a day') + '</span></div>'
    '<div><b>' + t('نحو ٩٠ ألف', 'About 90,000') + '</b><span>' + t('زيارة في الشهر', 'visits a month') + '</span></div>'
    '<div><b>' + t('نحو ١٫١ مليون', 'About 1.1 million') + '</b><span>' + t('زيارة في السنة', 'visits a year') + '</span></div></div>'
    '<table class="hp-est-table"><tbody>'
    '<tr><td>' + t('زيارات سكان النطاق للمحلات والمطاعم والترفيه (السيناريو الأساسي أعلاه)', 'Catchment residents visiting shops, dining and leisure (base case above)') + '</td><td>' + t('٩٧٧ يوميًا', '977 a day') + '</td></tr>'
    '<tr><td>' + t('تسوق أسبوعي من الهايبر: ٦٪ من نحو ١٨٠ ألف أسرة في النطاق (٤٫٥ فرد للأسرة)', 'Weekly hypermarket shopping: 6% of about 180,000 catchment households (4.5 people each)') + '</td><td>' + t('نحو ١٬٥٥٠ يوميًا', 'About 1,550 a day') + '</td></tr>'
    '<tr><td>' + t('زوار من باقي المحافظة: ٠٫٥٪ من نحو ٢٫٩٥ مليون نسمة مرة شهريًا', 'Visitors from the rest of the governorate: 0.5% of about 2.95 million people once a month') + '</td><td>' + t('نحو ٥٠٠ يوميًا', 'About 500 a day') + '</td></tr>'
    '</tbody></table><p class="p4source">' + t('تقدير استرشادي من فريق المشروع بافتراضات متحفظة، لا يشمل المسافرين والسياح. يُحدَّث بأرقام العدّادات الفعلية بعد التشغيل.',
                                                  'Indicative estimate by the project team on conservative assumptions, excluding travellers and tourists. To be updated with actual footfall counts after opening.') + '</p></div>'))

# ---- operating phases (Nov 2026): phase one runs, phase two June 2027, rest Dec 2027; no market study, no operator for the hypermarket ----
# market section becomes the phases section (same id, so tile and launcher keep working)
i = s.index('id="market"'); a = s.rfind('<section', 0, i); b = s.index('</section>', i) + len('</section>')
p2 = [byid[k] for k in PHASE2]
p2_avail = [u for u in p2 if u['id'] in OFFER]
p2_rows = ''.join(f'<tr><td><a href="lite.html?unit={u["id"]}" data-route="unit/{u["id"]}"><bdi>{u["id"]}</bdi></a></td><td>{FLOOR[u["f"]]}</td>'
                  f'<td>{u["cat"]}</td><td class="num">{num(u["area"])}</td></tr>' for u in p2_avail)
phases = ('<section class="section hp-phases" id="market"><div class="wrap"><span class="over">OPENING PHASES</span>'
          '<h2>' + t('مراحل تشغيل هابينس بلازا', 'Happiness Plaza opening phases') + '</h2>'
          '<ol class="hp-phase-cards">'
          '<li class="on"><span>' + t('المرحلة الأولى', 'Phase one') + '</span><b>' + t('تعمل بالفعل', 'Already open') + '</b><p>'
          + t('فندق بلازا ومطعم بوخارست بلاك والجيم والنادي الصحي وألعاب الأطفال حول البحيرة.', 'Plaza Hotel, Bokharest Black restaurant, the gym, the wellness club and the kids’ play area around the lake.') + '</p></li>'
          '<li><span>' + t('المرحلة الثانية', 'Phase two') + '</span><b>' + t('تشغيل يونيو ٢٠٢٧', 'Opening June 2027') + '</b><p>'
          + t('مطاعم البلازا وواجهة الأزياء والمحلات المطلة على البلازا في الدور الأرضي، والوحدة F16-20 في الدور الأول.', 'The plaza restaurants, the fashion frontage and the shops facing the plaza on the ground floor, plus unit F16-20 on the first floor.') + '</p></li>'
          '<li><span>' + t('المرحلة الثالثة', 'Phase three') + '</span><b>' + t('تشغيل ديسمبر ٢٠٢٧', 'Opening December 2027') + '</b><p>'
          + t('باقي المحلات التجارية بالكامل في كل الأدوار، ومعها الهايبر ماركت في البدروم.', 'All remaining shops on every level, together with the basement hypermarket.') + '</p></li></ol>'
          '<h3>' + t('وحدات المرحلة الثانية المتاحة للإيجار', 'Phase two units available for lease') + '</h3>'
          '<div class="hp-units-scroll"><table class="hp-units-table"><thead><tr><th>' + t('الوحدة', 'Unit') + '</th><th>' + t('الدور', 'Level') + '</th><th>'
          + t('النشاط', 'Use') + '</th><th>' + t('المحمّلة م²', 'Loaded m²') + '</th></tr></thead><tbody>' + p2_rows + '</tbody></table></div>'
          '<p class="hp-units-foot">' + t('الوحدات G25-27 وG29-31 وG33-35 وG37 خلف واجهة الأزياء ضمن المرحلة الثالثة، وتنضم للمرحلة الثانية إذا استأجرها مستأجر الوحدة الأمامية الملاصقة لها من الظهر.',
                                          'Units G25-27, G29-31, G33-35 and G37 behind the fashion frontage are in phase three; each joins phase two if leased together with the front unit directly behind it.') + '</p>'
          '</div></section>')
s = s[:a] + phases + s[b:]

# tile, menus and links that pointed at the market study
rep('<strong>دراسة سوق قنا</strong><small>السكان والزيارات</small>', '<strong>' + t('مراحل التشغيل', 'Opening phases') + '</strong><small>' + t('المرحلة الثانية يونيو ٢٠٢٧', 'Phase two June 2027') + '</small>')
rep('<a href="lite.html#market" data-route="market">سوق قنا</a>', '<a href="lite.html#market" data-route="market">' + t('مراحل التشغيل', 'Opening phases') + '</a>')
rep('<strong>٣ · السوق والمخططات</strong><a href="lite.html#market" data-route="market">دراسة سوق قنا</a>', '<strong>' + t('٣ · المراحل والمخططات', '3 · Phases and plans') + '</strong><a href="lite.html#market" data-route="market">' + t('مراحل التشغيل', 'Opening phases') + '</a>')
rep(' <a href="lite.html#market" data-route="market">دراسة سوق قنا كاملة</a>', '')

# phases roadmap
i = s.index('id="stages"'); a = s.rfind('<section', 0, i); b = s.index('</section>', i) + len('</section>')
s = s[:a] + ('<section class="phase-roadmap" id="stages"><div class="wrap"><h2>' + t('مراحل التشغيل', 'Opening phases') + '</h2><ol>'
             '<li><a href="lite.html#phase" data-route="phase"><span>' + t('المرحلة الأولى', 'Phase one') + '</span><strong>' + t('الفندق والأنشطة الترفيهية', 'Hotel and leisure') + '</strong><small>' + t('تعمل بالفعل', 'Already open') + '</small></a></li>'
             '<li><a href="lite.html#market" data-route="market"><span>' + t('المرحلة الثانية', 'Phase two') + '</span><strong>' + t('مطاعم البلازا وواجهة الأزياء', 'Plaza restaurants and fashion frontage') + '</strong><small>' + t('تشغيل يونيو ٢٠٢٧', 'Opening June 2027') + '</small></a></li>'
             '<li><a href="lite.html?floor=g" data-route="plan/g"><span>' + t('المرحلة الثالثة', 'Phase three') + '</span><strong>' + t('باقي المحلات التجارية والهايبر ماركت', 'All remaining shops and the hypermarket') + '</strong><small>' + t('تشغيل ديسمبر ٢٠٢٧', 'Opening December 2027') + '</small></a></li>'
             '</ol></div></section>') + s[b:]

# phase one is running; no December 2026 date
rep('المرحلة الأولى قيد التشغيل، والافتتاح الرسمي في ديسمبر ٢٠٢٦.', t('المرحلة الأولى تعمل بالفعل.', 'Phase one is already open.'), count=0)
rep('<strong>المرحلة الأولى</strong><small>قيد التشغيل</small>', '<strong>' + t('المرحلة الأولى', 'Phase one') + '</strong><small>' + t('تعمل بالفعل', 'Already open') + '</small>')
rep('<h2>المرحلة الثانية · المحلات التجارية</h2>', '<h2>' + t('المحلات التجارية · المرحلتان الثانية والثالثة', 'Retail units · phases two and three') + '</h2>')

# hypermarket without an operator
rep('<h2>المرحلة الثالثة · هايبر ماركت الحبيب</h2>', '<h2>' + t('المرحلة الثالثة · الهايبر ماركت', 'Phase three · the hypermarket') + '</h2>')
s = re.sub(r'<span class="over">ALHABEEB HYPERMARKET', '<span class="over">HYPERMARKET', s, count=1)
rep(' مساحة محمّلة للوحدة B01 في البدروم، ويشغّلها الحبيب ماركت.', t(' مساحة محمّلة للوحدة B01 في البدروم، والتشغيل في ديسمبر ٢٠٢٧ مع باقي المحلات.', ' loaded area for unit B01 in the basement, opening in December 2027 with the remaining shops.'))
rep('<span>يشغّله الحبيب ماركت ويجلب زيارات يومية للمول.</span>', '<span>' + t('ضمن المرحلة الثالثة، والتشغيل في ديسمبر ٢٠٢٧.', 'Part of phase three, opening in December 2027.') + '</span>')
rep('<h4>أمام هايبر ماركت الحبيب</h4>', '<h4>' + t('أمام الهايبر ماركت', 'In front of the hypermarket') + '</h4>')
rep('alt="تصميم توزيع أقسام هايبر ماركت الحبيب والكاشيرات"', 'alt="' + t('تصميم توزيع أقسام الهايبر ماركت والكاشيرات', 'Hypermarket department and checkout layout') + '"')
rep('<span role="listitem">هايبر ماركت الحبيب ٥٬٥٦٢ م²</span>', '<span role="listitem">' + t('هايبر ماركت ٥٬٥٦٢ م²', 'Hypermarket 5,562 m²') + '</span>')
s = re.sub(r'<div class="wrap marketlook">.*?</div></div>', '', s, count=1, flags=re.S) if 'class="wrap marketlook"' in s else s
rep(' وفي هابينس بلازا يشغّل الحبيب هايبر ماركت B01 بمساحة ٥٬٥٦٢ م² بأقسام الأغذية الطازجة والسلع سريعة التداول والمنسوجات والسلع غير الغذائية، إلى جانب الحبيب ستور وصيدلية الحبيب.', '')
s = re.sub(r'<li><strong>الهايبر ماركت مُشغَّل من المالك</strong><p>[^<]*</p></li>', '', s, count=1)
s = re.sub(r'<article><img loading="lazy" src="assets/developer/market-sign\.webp"[^>]*>.*?</article>', '', s, count=1, flags=re.S)
s = re.sub(r'<div><img loading="lazy" src="assets/developer/market-fresh\.webp"[^>]*><span>[^<]*</span></div>', '', s, count=1)
rep('<figcaption>تصميم الحبيب ماركت داخل المول، والمرحلة الأولى كما نُفّذت.</figcaption>', '<figcaption>' + t('المرحلة الأولى كما صمّمتها المجموعة ونفّذتها.', 'Phase one as designed and built by the group.') + '</figcaption>')
s = re.sub(r'<div><img loading="lazy" src="assets/developer/market-sign\.webp"[^>]*><span>[^<]*</span></div>', '', s, count=1)
rep('بدأ في ٢٠٢١ بمشروع هابينس بلازا عند مدخل قنا الجديدة: أرض ١٧٬٧٨٥ م²، وبلازا مشتركة ٤٬٠٠٠ م²، وثلاث مراحل هي الفندق والترفيه ثم المحلات ثم الهايبر ماركت.',
    t('بدأ في ٢٠٢١ بمشروع هابينس بلازا عند مدخل قنا الجديدة: أرض ١٧٬٧٨٥ م²، وبلازا داخلية ١٬٨٥٧ م²، وثلاث مراحل: الفندق والترفيه، ثم مطاعم البلازا وواجهة الأزياء، ثم باقي المحلات والهايبر ماركت.',
      'Launched in 2021 with Happiness Plaza at the entrance of New Qena: a 17,785 m² site, a 1,857 m² internal plaza and three phases: the hotel and leisure, then the plaza restaurants and fashion frontage, then the remaining shops and the hypermarket.'))
rep('تأسست سلسلة الحبيب ماركت عام ٢٠٠٨، ولها ٤ فروع في محافظتي قنا والبحر الأحمر، منها الفرع الرئيسي في قنا وفرع الغردقة، وتطبيق للطلب أونلاين.</p>',
    t('تأسست سلسلة الحبيب ماركت عام ٢٠٠٨، ولها ٤ فروع في محافظتي قنا والبحر الأحمر، منها الفرع الرئيسي في قنا وفرع الغردقة، وتطبيق للطلب أونلاين.',
      'Alhabeeb Market was founded in 2008 and has 4 branches in Qena and Red Sea governorates, including its main Qena branch and a Hurghada branch, plus an app for online orders.') + '</p>')
rep('صمّمت المجموعة ونفّذت مبنى الفندق والترفيه في المرحلة الأولى، وفيه فندق بوتيك من ١٤ غرفة وجناحًا. المرحلة الأولى تعمل بالفعل.',
    t('صمّمت المجموعة ونفّذت مبنى الفندق والترفيه في المرحلة الأولى، وفيه فندق بوتيك من ١٤ غرفة وجناحًا. المرحلة الأولى تعمل بالفعل.',
      'The group designed and built the phase one hotel and leisure building, with a 14-room boutique hotel. Phase one is already open.'))
rep('فندق بلازا ومطعم الجزيرة والجيم والنادي الصحي وألعاب الأطفال. المرحلة الأولى تعمل بالفعل.',
    t('فندق بلازا ومطعم الجزيرة والجيم والنادي الصحي وألعاب الأطفال. المرحلة الأولى تعمل بالفعل.',
      'Plaza Hotel, the island restaurant, the gym, the wellness club and the kids’ play area. Phase one is already open.'))
rep('<strong>٢ · المرحلة الأولى قيد التشغيل</strong><a href="lite.html#stages" data-route="stages">مراحل التنفيذ</a>',
    '<strong>' + t('٢ · المرحلة الأولى تعمل بالفعل', '2 · Phase one is open') + '</strong><a href="lite.html#stages" data-route="stages">' + t('مراحل التشغيل', 'Opening phases') + '</a>')
s = s.replace('١٤٤ وحدة تجارية للإيجار', '٥٩ وحدة متاحة للإيجار').replace('144 retail units for lease', '59 units for lease')
for _bad in ['هايبر ماركت الحبيب', 'يشغّلها الحبيب', 'يشغّله الحبيب', 'الحبيب ستور', 'ديسمبر ٢٠٢٦', 'دراسة سوق', 'زيارة في اليوم', 'hp-est']:
    assert _bad not in s, _bad

import importlib.util as _iu
_sp = _iu.spec_from_file_location('drive_fix', __file__.rsplit('/', 1)[0] + '/drive_fix.py'); _df = _iu.module_from_spec(_sp); _sp.loader.exec_module(_df)
s = _df.apply(s, t)

open(B + '/lite.html', 'w', encoding='utf-8').write(s)

# English overrides (lite only)
en = {k: v for k, v in EN.items()}
for k in ['دليل الوحدات المتاحة للإيجار']:
    pass
open(B + '/i18n-en-lite.js', 'w', encoding='utf-8').write(
    '/* English for the simple page: overrides and spelling (Alhabeeb). */\n'
    '(function(){var D=window.HP_EN;if(!D)return;var A=' + json.dumps(en, ensure_ascii=False, separators=(',', ':')) + ';'
    'for(var k in A)D[k]=A[k];for(var k2 in D){if(typeof D[k2]==="string")D[k2]=D[k2].replace(/Al-Habeeb|Al Habeeb|Alhabib|AL-HABEEB/g,"Alhabeeb")}})();\n')
print('lite built:', len(lite_units), 'units in the simple page,', len(avail), 'available;', counts)
