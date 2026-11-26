"""Reorder the brand guide around the leasing story and add the story sections.

Usage: python3 build_story.py SITE_DIR

Order of the page:
  hero, 1 the owner (#owner), 2 why Qena and Upper Egypt (#why),
  3 location and advantages (#location + site film), 4 our goal (#goal),
  5 phase one in operation (#stages #phase #phase-scenes #lake #rooms),
  6 Qena market study (#market), 7 floor plans (#atlas #sitevideo #hyper),
  then facilities, handover, deals, contact.
Rewrites the top navigation, the contents menu and the presentation chapters,
and adds the English strings. Safe to run again.
"""
import json
import re
import sys

B = sys.argv[1]
EN = {}


def t(ar, en):
    EN[ar] = en
    return ar


site = open(B + '/site.js', encoding='utf-8').read()
U = json.JSONDecoder().raw_decode(site[site.index('const UNITS=') + 12:])[0]
cat = {}
for u in U:
    cat[u['cat']] = cat.get(u['cat'], 0) + 1
DIG = str.maketrans('0123456789', '٠١٢٣٤٥٦٧٨٩')


def n(v):
    return str(v).translate(DIG)


fashion = sum(cat.get(k, 0) for k in ['أزياء', 'إكسسوارات', 'لايف ستايل', 'موبايلات', 'اتصالات'])
food = cat.get('أغذية ومشروبات', 0) + cat.get('فود كورت', 0)
shops = cat.get('محل تجاري', 0) + cat.get('تجزئة', 0) + cat.get('معرض', 0)


def card(title, body, extra=''):
    return f'<article><h3>{title}</h3><p>{body}</p>{extra}</article>'


# ---------- 2. Why Qena and Upper Egypt ----------
why = ['<section class="section story" id="why"><div class="wrap">',
       '<header class="story-head"><span class="over">WHY QENA &amp; UPPER EGYPT</span><h2>'
       + t('ليه قنا والصعيد؟', 'Why Qena and Upper Egypt?') + '</h2><p class="story-lead">'
       + t('سوق كبير في قلب الصعيد، على ملتقى الطرق بين القاهرة والأقصر والبحر الأحمر، ومدينة جديدة تنمو عند مدخله.',
           'A large market at the heart of Upper Egypt, where the roads to Cairo, Luxor and the Red Sea meet, with a new city growing at its entrance.')
       + '</p></header><div class="story-stats" role="list">']
for b, s in [(t('٣٬٧٦٤٬٧٩١', '3,764,791'), t('نسمة في محافظة قنا', 'residents of Qena Governorate')),
             (t('٨١١٬٦١٥', '811,615'), t('نسمة في النطاق الأقرب للمشروع', 'residents in the catchment nearest the project')),
             (t('١٥٪', '15%'), t('من الناتج المحلي للمحافظة من تجارة الجملة والتجزئة', 'of the governorate’s GDP from wholesale and retail trade')),
             (t('٨ كم', '8 km'), t('من مدينة قنا إلى المشروع', 'from Qena city to the project'))]:
    why.append(f'<div role="listitem"><b>{b}</b><span>{s}</span></div>')
why.append('</div><div class="story-cards">')
why.append(card(t('سوق كبير في مكان واحد', 'A large market in one place'),
                t('تجمع قنا أكثر من ٣٫٧ مليون نسمة، ويضع هابينس بلازا البراندات في مكان واحد قريب منهم.',
                  'Qena is home to more than 3.7 million people, and Happiness Plaza brings brands together in one place close to them.')))
why.append(card(t('ملتقى طرق الصعيد', 'Upper Egypt’s crossroads'),
                t('المشروع بالقرب من طريق قنا–سفاجا إلى البحر الأحمر، ومحور قنا–الطيبة إلى الأقصر، وطريق الجيش الصحراوي إلى القاهرة.',
                  'The project sits near the Qena–Safaga road to the Red Sea, the Qena–Al Tayeba axis to Luxor and the Army Desert Road to Cairo.')))
why.append(card(t('قنا الجديدة مدينة تنمو', 'New Qena is growing'),
                t('يقع المشروع في الحي الأول عند مدخل قنا الجديدة، أول ما يقابله سكان المدينة الجديدة وزوارها.',
                  'The project stands in District 1 at the entrance of New Qena, the first stop for the new city’s residents and visitors.')))
why.append(card(t('شريك من أهل السوق', 'A partner that knows the market'),
                t('مجموعة الحبيب نشأت في قنا وتعمل فيها منذ ٢٠٠٨ في التجزئة والزراعة والمقاولات، وتعرف عادات الشراء في الصعيد.',
                  'The Al-Habeeb group was born in Qena and has worked there since 2008 in retail, farming and contracting; it knows how Upper Egypt shops.')))
why.append('</div><p class="story-source">' + t('المصادر: تقديرات السكان في ١ يوليو ٢٠٢٥ (الجهاز المركزي للتعبئة العامة والإحصاء)، وخطة المواطن الاستثمارية لمحافظة قنا ٢٠٢٠/٢٠٢١ (وزارة التخطيط).',
                                                'Sources: population estimates as of 1 July 2025 (CAPMAS) and the Citizen’s Investment Plan for Qena Governorate 2020/2021 (Ministry of Planning).')
           + ' <a href="./#market" data-route="market">' + t('دراسة سوق قنا كاملة', 'Full Qena market study') + '</a></p></div></section>')
WHY = ''.join(why)

# ---------- 3. Location and advantages ----------
svg = ('<svg class="story-map" viewBox="0 0 420 300" role="img" aria-label="' + t('رسم إرشادي لطرق الوصول إلى المشروع', 'Indicative access diagram') + '">'
       '<g stroke="#b9a37b" stroke-width="2" fill="none"><line x1="210" y1="160" x2="60" y2="160"/><line x1="210" y1="160" x2="220" y2="40"/>'
       '<line x1="210" y1="160" x2="350" y2="80"/><line x1="210" y1="160" x2="320" y2="270"/></g>'
       '<g fill="#b9a37b"><circle cx="60" cy="160" r="5"/><circle cx="220" cy="40" r="5"/><circle cx="350" cy="80" r="5"/><circle cx="320" cy="270" r="5"/></g>'
       '<circle cx="210" cy="160" r="10" fill="#e2c38b"/></svg>')
labels = [('story-m-qena', t('مدينة قنا', 'Qena city')), ('story-m-cairo', t('إلى القاهرة', 'To Cairo')),
          ('story-m-safaga', t('إلى سفاجا والبحر الأحمر', 'To Safaga & the Red Sea')), ('story-m-luxor', t('إلى الأقصر', 'To Luxor')),
          ('story-m-hp', t('هابينس بلازا', 'Happiness Plaza')), ('story-m-km', t('٨ كم', '8 km'))]
loc = ['<section class="section story story-alt" id="location"><div class="wrap">',
       '<header class="story-head"><span class="over">LOCATION &amp; ADVANTAGES</span><h2>'
       + t('موقع المشروع ومميزاته', 'Location and advantages') + '</h2><p class="story-lead">'
       + t('على مدخل مدينة قنا الجديدة في الحي الأول، على بعد نحو ٨ كم من مدينة قنا.',
           'At the entrance of New Qena, District 1, about 8 km from Qena city.') + '</p></header>',
       '<div class="story-split"><figure class="story-mapbox">' + svg
       + ''.join(f'<span class="story-m {c}">{l}</span>' for c, l in labels)
       + '<figcaption>' + t('رسم إرشادي لمسارات الوصول، دون مقياس.', 'Indicative access diagram, not to scale.') + '</figcaption></figure>',
       '<ul class="story-list">']
for title, body in [
        (t('أرض ٢٠٬٠٠٠ م² وبلازا مفتوحة ٤٬٠٠٠ م²', 'A 20,000 m² site and a 4,000 m² open plaza'),
         t('المحلات والمطاعم والفندق والبحيرة كلها حول بلازا واحدة.', 'Shops, restaurants, the hotel and the lake all face one plaza.')),
        (t('هايبر ماركت ٥٬٥٦٢ م² في البدروم', 'A 5,562 m² hypermarket in the basement'),
         t('يشغّله الحبيب ماركت ويجلب زيارات يومية للمول.', 'Run by Al Habeeb Market, it brings daily visits to the mall.')),
        (t('٣ مداخل وحركة رأسية كاملة', '3 entrances and full vertical circulation'),
         t('مصعد بانورامي وسلّمان متحركان وسير كهربائي وسلالم رئيسية وطوارئ.', 'A panoramic lift, two escalators, a travelator, main and emergency stairs.')),
        (t('جراج على مستويين لـ٢٠٠ سيارة', 'A two-level garage for 200 cars'),
         t('سعة تصميمية، منها ٣٬٦٤٤ م² في البدروم الأول.', 'Design capacity, with 3,644 m² on basement level 1.')),
        (t('فندق وبحيرة وأنشطة ترفيهية', 'A hotel, a lake and leisure'),
         t('فندق بلازا ١٤ غرفة، وجزيرة بوخارست على البحيرة، وجيم ونادٍ صحي وألعاب أطفال.', 'The 14-room Plaza Hotel, Bokharest Island on the lake, a gym, spa and kids’ play.')),
        (t('خدمات للزائر والمستأجر', 'Services for visitors and tenants'),
         t('مصلى ودورات مياه وماكينة صراف، ورصيف تحميل ومصعد بضائع، وأمن وكاميرات وإطفاء آلي.', 'Prayer room, toilets, ATM, loading dock and goods lift, security, CCTV and automatic fire suppression.'))]:
    loc.append(f'<li><strong>{title}</strong><span>{body}</span></li>')
loc.append('</ul></div><figure class="story-render"><img loading="lazy" src="assets/story/plaza-render.webp" alt="'
           + t('تصوّر معماري للبلازا الداخلية للمول', 'Architectural rendering of the mall’s inner plaza') + '"><figcaption>'
           + t('تصوّر معماري للبلازا الداخلية للمول.', 'Architectural rendering of the mall’s inner plaza.') + '</figcaption></figure></div></section>')
LOC = ''.join(loc)

# ---------- 4. Our goal ----------
goal = ['<section class="section story" id="goal"><div class="wrap">',
        '<header class="story-head"><span class="over">OUR GOAL</span><h2>'
        + t('هدفنا: مقصد أهالي قنا', 'Our goal: the destination for Qena') + '</h2><p class="story-lead">'
        + t('نجمع البراندات في مكان واحد، ونضيف لها الأكل والترفيه والخدمات اليومية، ليصبح هابينس بلازا المكان اللي تقصده الأسرة في قنا للتسوق والخروج.',
            'We bring brands together in one place, add dining, leisure and daily services, so Happiness Plaza becomes where Qena’s families go to shop and spend time.')
        + '</p></header><div class="story-mix">']
mix = [
    (t('تسوق يومي', 'Daily shopping'), t('هايبر ماركت الحبيب والحبيب ستور وصيدلية الحبيب، يشغّلها المالك نفسه.', 'Al Habeeb Hypermarket, Al Habeeb Store and Al Habeeb Pharmacy, run by the owner.'), t('٣ وحدات', '3 units')),
    (t('أزياء وإكسسوارات ولايف ستايل', 'Fashion, accessories & lifestyle'), t('أزياء وإكسسوارات وموبايلات واتصالات ولايف ستايل على الأدوار التجارية.', 'Fashion, accessories, mobiles, telecom and lifestyle across the retail floors.'), n(fashion) + ' ' + t('وحدة', 'units')),
    (t('مطاعم وكافيهات وفود كورت', 'Restaurants, cafés & food court'), t('مطاعم وكافيهات بتراسات على البلازا، وفود كورت في الدور الأول.', 'Restaurants and cafés with terraces on the plaza, and a first-floor food court.'), n(food) + ' ' + t('وحدة', 'units')),
    (t('ترفيه وأطفال', 'Entertainment & kids'), t('مساحتان للترفيه في الدور الثاني، ومنطقة أطفال وحضانة في البدروم، وجوي بارك في المرحلة الأولى.', 'Two entertainment spaces on the second floor, a kids’ area and nursery in the basement, and Joy Park in phase one.'), t('٩٤٤ م² للترفيه', '944 m² of entertainment')),
    (t('فندق وصحة ولياقة', 'Hotel, health & fitness'), t('فندق بلازا وجيم ونادٍ صحي ومطعم الجزيرة في المرحلة الأولى.', 'The Plaza Hotel, gym, spa and the island restaurant in phase one.'), t('١٤ غرفة', '14 rooms')),
    (t('محلات ومعارض وخدمات', 'Shops, showrooms & services'), t('محلات بمساحات متنوعة ومعارض وخدمات مالية تكمّل احتياجات الزائر.', 'Shops in a range of sizes, showrooms and financial services to complete each visit.'), n(shops + cat.get('خدمات مالية', 0)) + ' ' + t('وحدة', 'units')),
]
for title, body, fig in mix:
    goal.append(f'<article><b>{fig}</b><h3>{title}</h3><p>{body}</p></article>')
goal.append('</div><p class="story-note">' + t('لماذا يهم ذلك للبراند؟ الأسرة تأتي لأكثر من غرض في زيارة واحدة، فتطول الزيارة وتزيد فرص الشراء من كل محل.',
                                              'Why it matters to a brand: families come for more than one reason in a single visit, so they stay longer and every shop gets more chances to sell.')
            + '</p></div></section>')
GOAL = ''.join(goal)

CSS = r'''
/* ---------- Leasing story sections (v15) ---------- */
.mast-links a { white-space: nowrap; }
.lang-en .mast-links { gap: 18px; }
.start-presentation { white-space: nowrap; }
@media (max-width: 1240px) { .mast-links { display: none !important; } }
.story { background: #f4f1e9; color: var(--ink); padding: clamp(60px, 8vw, 110px) 0; }
.story-alt { background: #ebe6da; }
.story-head { max-width: 860px; }
.story-head .over { color: var(--pro-gold-ink); }
.story-lead { margin-top: 16px; font-size: clamp(17px, 1.5vw, 20px); color: #3f4a45; }
.story-stats { display: grid; grid-template-columns: repeat(4, 1fr); margin-top: clamp(32px, 4vw, 52px); border-top: 1px solid var(--pro-line); border-bottom: 1px solid var(--pro-line); }
.story-stats > div { padding: 20px 18px 24px; border-inline-end: 1px solid var(--pro-line); }
.story-stats > div:last-child { border-inline-end: 0; }
.story-stats b { display: block; font: 400 clamp(26px, 2.6vw, 38px)/1.3 Edition, Arabic, serif; color: var(--pro-green); white-space: nowrap; }
.story-stats span { display: block; margin-top: 6px; font-size: 14px; color: #5b635e; }
.story-cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 18px; margin-top: 36px; }
.story-cards article, .story-mix article { background: #fffdf8; border: 1px solid var(--pro-line); border-radius: 6px; padding: 24px 22px; }
.story h3 { font-size: 19px; line-height: 1.5; color: var(--pro-green); }
.story-cards p, .story-mix p { margin-top: 8px; font-size: 15px; line-height: 1.85; color: #4d5751; }
.story-source { margin-top: 22px; font-size: 13px; color: #6a716c; }
.story-source a { color: var(--pro-gold-ink); text-decoration: underline; }
.story-split { display: grid; grid-template-columns: 1fr 1.1fr; gap: clamp(26px, 5vw, 64px); align-items: start; margin-top: 36px; }
.story-mapbox { position: relative; margin: 0; background: #1f362d; border-radius: 6px; padding: 18px; }
.story-map { display: block; width: 100%; height: auto; direction: ltr; }
.story-m { position: absolute; font-size: 13px; color: #e8e2d2; white-space: nowrap; transform: translate(-50%, -50%); }
.story-m-qena { left: calc(18px + 60/420*(100% - 36px)); top: calc(18px + 140/300*(100% - 76px)); font-weight: 700; }
.story-m-cairo { left: calc(18px + 220/420*(100% - 36px)); top: calc(18px + 20/300*(100% - 76px)); }
.story-m-safaga { left: calc(18px + 330/420*(100% - 36px)); top: calc(18px + 58/300*(100% - 76px)); }
.story-m-luxor { left: calc(18px + 320/420*(100% - 36px)); top: calc(18px + 292/300*(100% - 76px)); }
.story-m-hp { left: calc(18px + 210/420*(100% - 36px)); top: calc(18px + 188/300*(100% - 76px)); color: #e2c38b; font-weight: 700; }
.story-m-km { left: calc(18px + 135/420*(100% - 36px)); top: calc(18px + 145/300*(100% - 76px)); color: #e2c38b; }
.story-mapbox figcaption { margin-top: 26px; font-size: 12px; color: #aeb8ad; }
.story-list { list-style: none; margin: 0; padding: 0; }
.story-list li { padding: 14px 0; border-top: 1px solid #d4ccb9; }
.story-list strong { display: block; font-size: 17px; color: var(--pro-green); }
.story-list span { display: block; margin-top: 4px; font-size: 15px; color: #4d5751; line-height: 1.8; }
.story-render { margin: 28px 0 0; }
.story-render img { width: 100%; max-height: 460px; object-fit: cover; border-radius: 6px; }
.story-render figcaption { margin-top: 8px; font-size: 13px; color: #6a716c; }
.story-mix { display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; margin-top: 36px; }
.story-mix b { display: block; font: 400 26px/1.3 Edition, Arabic, serif; color: var(--pro-gold-ink); margin-bottom: 8px; }
.story-note { margin-top: 26px; padding: 18px 22px; background: #1f362d; color: #eef0e8 !important; border-radius: 6px; font-size: 16px; }
@media (max-width: 1100px) {
  .story-cards { grid-template-columns: 1fr 1fr; }
  .story-mix { grid-template-columns: 1fr 1fr; }
}
@media (max-width: 760px) {
  .story-stats { grid-template-columns: 1fr 1fr; }
  .story-stats > div:nth-child(2) { border-inline-end: 0; }
  .story-stats > div:nth-child(-n+2) { border-bottom: 1px solid var(--pro-line); }
  .story-stats b { font-size: 26px; }
  .story-cards, .story-mix, .story-split { grid-template-columns: 1fr; }
  .story-m { font-size: 11px; }
}
'''

# ---------- reorder ----------
p = B + '/index.html'
s = open(p, encoding='utf-8').read()
main_a = s.index('<main id="mainpage">') + len('<main id="mainpage">')


def take(sec_id):
    """Cut the <section> that has this id (or contains it) out of s and return it."""
    global s
    i = s.index(f'id="{sec_id}"')
    a = s.rfind('<section', 0, i)
    depth, j = 0, a
    for m in re.finditer(r'<section\b|</section>', s[a:]):
        depth += 1 if m.group(0) != '</section>' else -1
        if depth == 0:
            j = a + m.end()
            break
    block = s[a:j]
    s = s[:a] + s[j:]
    return block


for old in ['why', 'location', 'goal']:
    if f'id="{old}"' in s:
        take(old)
film = take('tour')
blocks = {k: take(k) for k in ['home', 'owner', 'stages', 'phase', 'phase-scenes', 'lake', 'rooms', 'market', 'atlas',
                               'sitevideo', 'hyper', 'facilities', 'handover', 'deals', 'contact']}
main_a = s.index('<main id="mainpage">') + len('<main id="mainpage">')
rest_start = main_a
order = (blocks['home'] + blocks['owner'] + WHY + LOC + film + GOAL + blocks['stages'] + blocks['phase'] + blocks['phase-scenes']
         + blocks['lake'] + blocks['rooms'] + blocks['market'] + blocks['atlas'] + blocks['sitevideo'] + blocks['hyper']
         + blocks['facilities'] + blocks['handover'] + blocks['deals'] + blocks['contact'])
s = s[:main_a] + order + s[main_a:]

# phase one is in operation
for a, b in [('الافتتاح المقرر في ديسمبر ٢٠٢٦.', 'قيد التشغيل، والافتتاح الرسمي في ديسمبر ٢٠٢٦.'),
             ('الافتتاح المقرر في ديسمبر ٢٠٢٦', 'قيد التشغيل · الافتتاح الرسمي ديسمبر ٢٠٢٦'),
             ('<span>افتتاح المرحلة الأولى</span>', '<span>المرحلة الأولى قيد التشغيل · الافتتاح الرسمي</span>'),
             ('مقرر في ديسمبر ٢٠٢٦.', 'قيد التشغيل، والافتتاح الرسمي في ديسمبر ٢٠٢٦.')]:
    s = s.replace(a, b)
t('قيد التشغيل، والافتتاح الرسمي في ديسمبر ٢٠٢٦.', 'In operation; official opening in December 2026.')
t('من غرف فندق بلازا إلى مطعم الجزيرة ونوادي الصحة واللياقة. قيد التشغيل، والافتتاح الرسمي في ديسمبر ٢٠٢٦.',
  'From the Plaza Hotel rooms to the island restaurant and the health and fitness clubs. In operation; official opening in December 2026.')
t('قيد التشغيل · الافتتاح الرسمي ديسمبر ٢٠٢٦', 'In operation · official opening December 2026')
t('المرحلة الأولى قيد التشغيل · الافتتاح الرسمي', 'Phase one in operation · official opening')

# top navigation and contents menu
nav = ('<nav class="mast-links" aria-label="التنقل الرئيسي">'
       + ''.join(f'<a href="./#{h}" data-route="{h}">{l}</a>' for h, l in [
           ('owner', t('المالك', 'Owner')), ('why', t('ليه قنا', 'Why Qena')), ('location', t('الموقع', 'Location')),
           ('goal', t('هدفنا', 'Goal')), ('phase', t('المرحلة الأولى', 'Phase 1')), ('market', t('سوق قنا', 'Market'))])
       + '<a href="?floor=g" data-route="plan/g">' + t('المخططات', 'Plans') + '</a>'
       + '<a href="./#contact" data-route="contact">احجز معاينة</a></nav>')
s = re.sub(r'<nav class="mast-links"[^>]*>.*?</nav>', nav, s, count=1, flags=re.S)


def col(title, items):
    out = f'<div><strong>{title}</strong>'
    for h, l in items:
        if h.startswith('?'):
            out += f'<a href="{h}" data-route="plan/g">{l}</a>'
        else:
            out += f'<a href="./#{h}" data-route="{h}">{l}</a>'
    return out + '</div>'


menu = ('<div class="nav-cols">'
        + col(t('١ · المالك والموقع', '1 · Owner & location'), [
            ('owner', t('مين المالك؟', 'Who is the owner?')), ('why', t('ليه قنا والصعيد؟', 'Why Qena and Upper Egypt?')),
            ('location', t('موقع المشروع ومميزاته', 'Location and advantages')), ('tour', 'فيديو الموقع'),
            ('goal', t('هدفنا: مقصد أهالي قنا', 'Our goal: the destination for Qena'))])
        + col(t('٢ · المرحلة الأولى قيد التشغيل', '2 · Phase one in operation'), [
            ('stages', 'مراحل التنفيذ'), ('phase', 'الفندق والأنشطة الترفيهية'), ('lake', 'البحيرة وجزيرة بوخارست'), ('rooms', 'غرف الفندق')])
        + col(t('٣ · السوق والمخططات', '3 · Market & floor plans'), [
            ('market', t('دراسة سوق قنا', 'Qena market study')), ('?floor=g', t('مخططات المحلات لكل الأدوار', 'Shop plans for every floor')),
            ('sitevideo', 'جولة المحلات'), ('hyper', 'المرحلة الثالثة · الهايبر ماركت'), ('facilities', 'المرافق والتشغيل'),
            ('handover', 'تجهيز الفرع'), ('deals', 'نماذج التعاقد'), ('contact', 'حجز معاينة')])
        + '</div>')
s = re.sub(r'<div class="nav-cols">.*?</div></div></nav>', menu + '</nav>', s, count=1, flags=re.S)
open(p, 'w', encoding='utf-8').write(s)

# presentation chapters follow the same story
stops = [['home', t('هابينس بلازا', 'Happiness Plaza')], ['owner', t('مين المالك؟', 'Who is the owner?')],
         ['why', t('ليه قنا والصعيد؟', 'Why Qena and Upper Egypt?')], ['location', t('موقع المشروع ومميزاته', 'Location and advantages')],
         ['goal', t('هدفنا: مقصد أهالي قنا', 'Our goal: the destination for Qena')],
         ['stages', 'مراحل تنفيذ المشروع'], ['phase', t('المرحلة الأولى قيد التشغيل', 'Phase one in operation')],
         ['lake', 'البحيرة وجزيرة بوخارست'], ['rooms', 'الفندق وغرفه'], ['market', t('دراسة سوق قنا', 'Qena market study')],
         ['plan/g', t('مخططات المحلات', 'Shop plans')], ['hyper', 'المرحلة الثالثة · هايبر ماركت الحبيب'], ['contact', 'حجز معاينة']]
site = re.sub(r'const chapterStops=\[.*?\]\];', 'const chapterStops=' + json.dumps(stops, ensure_ascii=False) + ';', site, count=1, flags=re.S)
open(B + '/site.js', 'w', encoding='utf-8').write(site)

p = B + '/i18n-en.js'
x = open(p, encoding='utf-8').read()
i = x.index('{'); j = x.rindex('}')
d = json.loads(x[i:j + 1]); d.update(EN)
open(p, 'w', encoding='utf-8').write(x[:i] + json.dumps(d, ensure_ascii=False, separators=(',', ':')) + x[j + 1:])

p = B + '/pro.css'
x = open(p, encoding='utf-8').read()
x = re.sub(r'\n/\* ---------- Leasing story sections \(v15\) ---------- \*/.*?(?=\n/\* ----------|\Z)', '', x, flags=re.S)
open(p, 'w', encoding='utf-8').write(x.rstrip() + '\n' + CSS)
print('story built', len(EN), 'strings')
