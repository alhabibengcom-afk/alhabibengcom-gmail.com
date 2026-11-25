# Complete project book (AR/EN): everything in the guide, organised by the three opening phases.
# Usage: build_book.py <brands dir> <grab.json>  -> book-ar.html, book-en.html (render with Playwright to A4 landscape PDF)
import json, sys, html, re, os
from PIL import Image
B, G = sys.argv[1:3]
D = json.load(open(G, encoding='utf-8'))
AR_DIG = str.maketrans('0123456789', '٠١٢٣٤٥٦٧٨٩')

# photos used by the book, resized into pack-img/
PICS = {'Happiness_Plaza_Phase_One.jpg': 1600, 'story/plaza-render.webp': 1600, 'developer/building.webp': 1100,
        'p4-room-1.jpg': 800, 'p4-room-3.jpg': 800, 'p4-room-5.jpg': 800, 'p4-room-7.jpg': 800, 'f0755181e1a7d4.webp': 1200}
for f, w in PICS.items():
    out = B + '/pack-img/' + f.rsplit('.', 1)[0] + '.jpg'
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if not os.path.exists(out):
        im = Image.open(B + '/assets/' + f).convert('RGB')
        if im.width > w: im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
        im.save(out, quality=82, optimize=True)

def build(lang):
    ar = lang == 'ar'
    n = (lambda s: s.translate(AR_DIG).replace(',', '٬').replace('.', '٫')) if ar else (lambda s: s)
    T = lambda a, e: a if ar else e
    rows = D[lang]['rows']  # unit, floor, use, loaded, outdoor, opening
    tonum = lambda x: float(x.translate(str.maketrans('٠١٢٣٤٥٦٧٨٩٫٬', '0123456789.,')).replace(',', '')) if x and x not in ('—', '-') else 0.0
    june = T('يونيو', 'June')
    p2 = [r for r in rows if r[5].startswith(june)]; p3 = [r for r in rows if not r[5].startswith(june)]
    F = T('هابينس بلازا · دليل المشروع الكامل', 'Happiness Plaza · Complete Project Book')
    pages = []
    def page(body, cls='', num=True):
        pages.append(f'<section class="pg {cls}">{body}' + (f'<footer><span>{F}</span><span class="pn"></span></footer>' if num else '') + '</section>')
    stat = lambda v, l: f'<div class="st"><b>{v}</b><span>{l}</span></div>'
    def chapter(no, title, sub, img):
        page(f'<img class="bg" src="assets/{img}" alt=""><div class="cv chap"><p class="no">{no}</p><h1>{title}</h1><p class="sub">{sub}</p></div>', 'cover', False)
    def table(rs, cols, outdoor=True):
        head = ''.join(f'<th>{c}</th>' for c in cols)
        body = ''.join('<tr>' + f'<td><bdi>{r[0]}</bdi></td>' + (f'<td>{r[1]}</td>' if len(cols) == 5 + outdoor - 1 else '')
                       + f'<td>{html.escape(r[2])}</td><td class="nm">{r[3]}</td>' + (f'<td class="nm">{r[4]}</td>' if outdoor else '') + '</tr>' for r in rs)
        return f'<table class="tb sm{" xs" if len(rs) > 16 else ""}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'

    # 1 cover
    page(f'''<img class="bg" src="assets/5febc5c17f554c.webp" alt=""><div class="cv"><p class="ey">{T('مدينة قنا الجديدة · محافظة قنا · مصر','New Qena City · Qena Governorate · Egypt')}</p>
<h1>{T('هابينس بلازا','Happiness Plaza')}</h1><p class="sub">{T('دليل المشروع الكامل للعلامات التجارية','The complete project book for brands')}</p>
<ol class="cvph"><li><b>{T('المرحلة الأولى','Phase one')}</b>{T('تعمل بالفعل','Already open')}</li><li><b>{T('المرحلة الثانية','Phase two')}</b>{T('يونيو ٢٠٢٧','June 2027')}</li><li><b>{T('المرحلة الثالثة','Phase three')}</b>{T('ديسمبر ٢٠٢٧','December 2027')}</li></ol>
<p class="dt">{T('نوفمبر ٢٠٢٦','November 2026')}</p></div>''', 'cover', False)
    # 2 contents
    toc = [T('المشروع في سطور','At a glance'), T('المالك والمطوّر','Owner and developer'), T('لماذا قنا وصعيد مصر؟','Why Qena and Upper Egypt'),
           T('الموقع والمميزات','Location and advantages'), T('هدفنا وتوزيع الأنشطة','Our goal and the tenant mix'), T('مراحل التشغيل','Opening phases'),
           T('المرحلة الأولى · تعمل بالفعل','Phase one · already open'), T('المرحلة الثانية · يونيو ٢٠٢٧','Phase two · June 2027'),
           T('المرحلة الثالثة · ديسمبر ٢٠٢٧','Phase three · December 2027'), T('المواصفات والتسليم والتعاقد','Specification, handover and leasing'), T('تواصل مع فريق التأجير','Contact the leasing team')]
    page(f'''<div class="two"><div><div class="hd"><p class="ey">{T('المحتويات','Contents')}</p><h2>{T('كل ما في الدليل التفاعلي، في ملف واحد','Everything in the interactive guide, in one file')}</h2></div>
<ol class="toc">{''.join(f'<li><i>{n(str(i+1).zfill(2))}</i>{x}</li>' for i, x in enumerate(toc))}</ol></div><figure class="ph"><img src="assets/13e41f59c10970.webp" alt=""></figure></div>''')
    # 3 at a glance
    total = sum(tonum(r[3]) for r in rows); out_all = sum(tonum(r[4]) for r in rows)
    page(f'''<div class="hd"><p class="ey">{T('المشروع في سطور','At a glance')}</p><h2>{T('مول تجاري وفندق وترفيه حول بلازا واحدة عند مدخل قنا الجديدة','Retail, hotel and leisure around one plaza at the entrance of New Qena')}</h2></div>
<div class="grid4">{stat(n('144'), T('وحدة تجارية على أربعة أدوار','retail units on four levels'))}{stat(n(str(len(rows))), T('وحدة متاحة للإيجار بإجمالي ','units for lease, ') + n(f'{total:,.0f}') + T(' م² محمّلة',' m² loaded'))}{stat(n(f'{out_all:,.0f}') + ' ' + T('م²','m²'), T('تراسات خارجية (أوت دور) لسبعة مطاعم','outdoor terraces of seven restaurants'))}{stat(n('17,785') + ' ' + T('م²','m²'), T('مساحة أرض المشروع حسب العقود','site area per the contracts'))}
{stat(n('1,857') + ' ' + T('م²','m²'), T('بلازا داخلية مع تراسات المطاعم','internal plaza with restaurant terraces'))}{stat(n('5,562') + ' ' + T('م²','m²'), T('هايبر ماركت في البدروم','hypermarket in the basement'))}{stat(n('200'), T('سيارة في جراج على مستويين','cars in a two-level garage'))}{stat(n('14'), T('غرفة وجناحًا في فندق بلازا','rooms and suites at the Plaza Hotel'))}</div>''')
    # 4 developer
    page(f'''<div class="two"><div><div class="hd"><p class="ey">{T('المالك والمطوّر','Owner and developer')}</p><h2>{T('الحبيب للتنمية والاستثمار ش.م.م.','Alhabeeb for Development & Investment LLC')}</h2></div>
<p class="lead">{T('مجموعة من الشركات تعمل في تجارة التجزئة من خلال سلسلة الحبيب ماركت، والإنتاج الزراعي من خلال مزارع الحبيب، والتطوير العقاري والتصميم والمقاولات. تأسست المجموعة ونمت وتطورت في محافظة قنا.','A group of companies in retail through the Al Habeeb Market chain, farming through Al Habeeb Farms, and real-estate development, design and contracting. The group was founded and grew in Qena Governorate.')}</p>
<ol class="biz"><li><b>{T('التجزئة: سلسلة الحبيب ماركت','Retail: Al Habeeb Market')}</b>{T('منذ ٢٠٠٨، ٤ فروع في قنا والبحر الأحمر وتطبيق للطلب أونلاين.','Since 2008, 4 branches in Qena and the Red Sea plus an online ordering app.')}</li>
<li><b>{T('الزراعة: مزارع الحبيب','Farming: Al Habeeb Farms')}</b>{T('منذ ٢٠١٤: ٢ مليون طائر و٣٬٠٠٠ رأس ماشية سنويًا.','Since 2014: 2 million birds and 3,000 head of cattle a year.')}</li>
<li><b>{T('التطوير العقاري','Real-estate development')}</b>{T('منذ ٢٠٢١ بمشروع هابينس بلازا.','Since 2021, with Happiness Plaza.')}</li>
<li><b>{T('التصميم والمقاولات','Design and contracting')}</b>{T('منذ ٢٠٠٨ في قنا: تصميم وتنفيذ وإدارة مشروعات. صمّمت المجموعة ونفّذت مبنى المرحلة الأولى.','Since 2008 in Qena: design, construction and project management. The group designed and built the phase one building.')}</li></ol>
<p class="small">{T('شركاء وجهات تعامل: جهاز مدينة قنا الجديدة، جهاز مدينة أسوان الجديدة، البنك الأهلي المصري، بنك قطر الوطني الأهلي QNB، AMA للتطوير العقاري.','Partners and counterparts: New Qena City Authority, New Aswan City Authority, National Bank of Egypt, QNB, AMA Real Estate Development.')}</p></div>
<figure class="ph"><img src="assets/developer/building.webp" alt=""></figure></div>''')
    # 5 why Qena
    why = [(T('سوق كبير في مكان واحد','A large market in one place'), T('تجمع محافظة قنا ٣٬٧٦٤٬٧٩١ نسمة، منهم ٨١١٬٦١٥ في النطاق الأقرب للمشروع، ويضع هابينس بلازا البراندات في مكان واحد قريب منهم.','Qena Governorate has 3,764,791 residents, 811,615 of them in the catchment nearest the project; Happiness Plaza brings brands to one place close to them.')),
           (T('ملتقى طرق الصعيد','A crossroads of Upper Egypt'), T('بالقرب من طريق قنا–سفاجا إلى البحر الأحمر، ومحور قنا–الطيبة إلى الأقصر، وطريق الجيش الصحراوي إلى القاهرة.','Near the Qena–Safaga road to the Red Sea, the Qena–Al Tayeba road to Luxor and the desert road to Cairo.')),
           (T('قنا الجديدة مدينة تنمو','New Qena is growing'), T('المشروع في الحي الأول عند مدخل قنا الجديدة، أول ما يقابله سكان المدينة الجديدة وزوارها، وعلى بعد نحو ٨ كم من مدينة قنا.','The project is in District 1 at the entrance of New Qena, the first stop for its residents and visitors, about 8 km from Qena city.')),
           (T('شريك من أهل السوق','A partner from the market'), T('مجموعة الحبيب نشأت في قنا وتعمل فيها منذ ٢٠٠٨ في التجزئة والزراعة والمقاولات، وتعرف عادات الشراء في الصعيد.','Al Habeeb Group was founded in Qena and has worked there since 2008 in retail, farming and contracting; it knows how Upper Egypt shops.'))]
    page(f'''<div class="hd"><p class="ey">{T('لماذا قنا وصعيد مصر؟','Why Qena and Upper Egypt?')}</p><h2>{T('سوق كبير في قلب الصعيد، على ملتقى الطرق بين القاهرة والأقصر والبحر الأحمر','A large market in the heart of Upper Egypt, where the roads to Cairo, Luxor and the Red Sea meet')}</h2></div>
<div class="grid4 mb">{stat(n('3,764,791'), T('نسمة في محافظة قنا','residents of Qena Governorate'))}{stat(n('811,615'), T('نسمة في النطاق الأقرب للمشروع','in the nearest catchment'))}{stat(n('15') + '٪' if ar else '15%', T('من الناتج المحلي للمحافظة من تجارة الجملة والتجزئة','of the governorate’s output from wholesale and retail'))}{stat(n('8') + ' ' + T('كم','km'), T('من مدينة قنا إلى المشروع','from Qena city'))}</div>
<ul class="kv cols2">{''.join(f'<li><b>{a}</b><span>{b}</span></li>' for a, b in why)}</ul>
<p class="small">{T('المصادر: تقديرات السكان في ١ يوليو ٢٠٢٥ (الجهاز المركزي للتعبئة العامة والإحصاء)، وخطة المواطن الاستثمارية لمحافظة قنا ٢٠٢٣/٢٠٢٤ (وزارة التخطيط).','Sources: CAPMAS population estimates, 1 July 2025; Citizen’s Investment Plan for Qena Governorate 2023/2024 (Ministry of Planning).')}</p>''')
    # 6 location
    loc = [(T('بلازا داخلية مفتوحة ١٬٨٥٧ م²','A 1,857 m² open internal plaza'), T('مع تراسات المطاعم، والمحلات والمطاعم والفندق والبحيرة حولها.','With the restaurant terraces; shops, restaurants, the hotel and the lake around it.')),
           (T('هايبر ماركت ٥٬٥٦٢ م²','A 5,562 m² hypermarket'), T('في البدروم، والتشغيل في ديسمبر ٢٠٢٧ مع المرحلة الثالثة.','In the basement, opening in December 2027 with phase three.')),
           (T('جراج على مستويين لـ٢٠٠ سيارة','A two-level garage for 200 cars'), T('٧٬٢٨٩ م²، بواقع ٣٬٦٤٤ م² لكل مستوى.','7,289 m², 3,644 m² on each level.')),
           (T('٣ مداخل وحركة رأسية كاملة','3 entrances and full vertical circulation'), T('مصعد بانورامي وسلّمان متحركان وسلالم رئيسية وطوارئ.','Panoramic lift, two escalators, main and emergency stairs.')),
           (T('خدمات للزائر والمستأجر','Services for visitors and tenants'), T('مصلى ودورات مياه وماكينة صراف، ورصيف تحميل ومصعد بضائع، وأمن وكاميرات وإطفاء آلي.','Prayer room, toilets, ATM, loading bay, goods lift, security, CCTV and sprinklers.'))]
    page(f'''<div class="two"><div><div class="hd"><p class="ey">{T('الموقع والمميزات','Location and advantages')}</p><h2>{T('على مدخل مدينة قنا الجديدة في الحي الأول','At the entrance of New Qena City, District 1')}</h2></div>
<ul class="kv">{''.join(f'<li><b>{a}</b><span>{b}</span></li>' for a, b in loc)}</ul></div><figure class="ph"><img src="assets/story/plaza-render.webp" alt=""><figcaption>{T('تصوّر معماري للبلازا الداخلية','Architectural view of the internal plaza')}</figcaption></figure></div>''')
    # 7 goal & mix
    mix = [('٤' if ar else '4', T('تسوق يومي','Daily shopping'), T('هايبر ماركت ومحلّا تجزئة وصيدلية.','A hypermarket, two retail stores and a pharmacy.')),
           ('٢٥' if ar else '25', T('أزياء وإكسسوارات ولايف ستايل','Fashion, accessories & lifestyle'), T('أزياء وإكسسوارات وموبايلات واتصالات ولايف ستايل.','Fashion, accessories, mobiles, telecom and lifestyle.')),
           ('٢٥' if ar else '25', T('مطاعم وكافيهات وفود كورت','Restaurants, cafés & food court'), T('مطاعم بتراسات خارجية على البلازا، وفود كورت في الدور الأول.','Restaurants with outdoor plaza terraces and a first-floor food court.')),
           ('٣' if ar else '3', T('ترفيه وأطفال','Entertainment & kids'), T('مساحتان للترفيه في الدور الثاني، ومنطقة أطفال وحضانة في البدروم.','Two entertainment spaces on the second floor and a kids’ area in the basement.')),
           ('٩' if ar else '9', T('معارض وخدمات مالية وتجميل','Showrooms, finance & beauty'), T('معارض وفروع بنوك وصالون وبيوتي سنتر وخدمات طبية.','Showrooms, bank branches, a salon and medical services.')),
           ('٧٨' if ar else '78', T('محلات تجارية','Retail shops'), T('محلات بمساحات متنوعة على الأدوار الأربعة.','Shops in a range of sizes on the four levels.'))]
    page(f'''<div class="hd"><p class="ey">{T('هدفنا','Our goal')}</p><h2>{T('نجمع البراندات في مكان واحد، ونضيف لها الأكل والترفيه والخدمات اليومية، ليصبح هابينس بلازا مقصد الأسرة في قنا','Brands in one place, with food, leisure and daily services, so Happiness Plaza becomes the family destination in Qena')}</h2></div>
<div class="mix">{''.join(f'<div><b>{a} {T("وحدة","units")}</b><h3>{b}</h3><p>{c}</p></div>' for a, b, c in mix)}</div>
<p class="small">{T('المجموع: ١٤٤ وحدة تجارية على أربعة أدوار، إلى جانب فندق بلازا وأنشطة المرحلة الأولى. الأسرة تأتي لأكثر من غرض في زيارة واحدة، فتطول الزيارة وتزيد فرص الشراء من كل محل.','Total: 144 retail units on four levels, plus the Plaza Hotel and the phase one venues. Families come for several reasons in one visit, so visits last longer and every shop gets more chances to sell.')}</p>''')
    # 8 phases timeline
    page(f'''<div class="hd"><p class="ey">{T('مراحل التشغيل','Opening phases')}</p><h2>{T('ثلاث مراحل حتى ديسمبر ٢٠٢٧','Three phases through December 2027')}</h2></div>
<div class="tl">{''.join(f'<article class="{c}"><img src="assets/{img}" alt=""><div><span>{a}</span><b>{b}</b><p>{d}</p><small>{e}</small></div></article>' for c, img, a, b, d, e in [
        ('on', 'Happiness_Plaza_Phase_One.jpg', T('المرحلة الأولى','Phase one'), T('تعمل بالفعل','Already open'), T('الفندق والأنشطة الترفيهية حول البحيرة.','The hotel and the leisure venues around the lake.'), T('فندق بلازا · بوخارست بلاك · Guru Fit · AURA · Joy Park · Joy Bites · صيدلية هابينس','Plaza Hotel · Bokharest Black · Guru Fit · AURA · Joy Park · Joy Bites · Happiness Pharmacy')),
        ('', 'entry-square.jpg', T('المرحلة الثانية','Phase two'), T('تشغيل يونيو ٢٠٢٧','Opening June 2027'), T('وحدات الأرضي المطلة على البلازا: المطاعم بتراساتها الخارجية، وواجهة الأزياء، والشوروم والبنوك، ومعها في الأول الفود كورت والبنك والشوروم الدوبلكس.','The plaza-facing ground-floor units: restaurants with outdoor terraces, the fashion frontage, showrooms and banks, plus the first-floor food court and the duplex bank and showroom.'), n(str(len(p2))) + ' ' + T('وحدة متاحة للإيجار','units for lease')),
        ('', '5febc5c17f554c.webp', T('المرحلة الثالثة','Phase three'), T('تشغيل ديسمبر ٢٠٢٧','Opening December 2027'), T('باقي المحلات التجارية بالكامل في الأدوار الأربعة، ومعها الهايبر ماركت في البدروم.','All remaining shops on the four levels, together with the basement hypermarket.'), n(str(len(p3))) + ' ' + T('وحدة متاحة للإيجار','units for lease'))])}</div>''')
    # 9 chapter: phase one
    chapter(T('المرحلة الأولى','Phase one'), T('تعمل بالفعل','Already open'), T('الفندق والأنشطة الترفيهية حول البحيرة، صمّمتها المجموعة ونفّذتها.','The hotel and leisure venues around the lake, designed and built by the group.'), 'Happiness_Plaza_Phase_One.jpg')
    acts = [('Guru_Fit.jpg', T('جيم Guru Fit','Guru Fit gym')), ('AURA.jpg', T('نادي صحي نسائي AURA','AURA women’s wellness club')), ('Bokharest_Black.jpg', T('مطعم بوخارست بلاك','Bokharest Black restaurant')),
            ('Joy_Park.jpg', T('ألعاب أطفال Joy Park','Joy Park kids’ play')), ('Plaza_Hotel.jpg', T('فندق بلازا · ١٤ غرفة وجناحًا','Plaza Hotel · 14 rooms and suites')), ('Joy_Bites.jpg', T('سندوتشات خفيفة وآيس كريم Joy Bites','Joy Bites snacks and ice cream')),
            ('Happiness_Pharmacy.jpg', T('صيدلية هابينس','Happiness Pharmacy')), ('bok-island-lake.jpg', T('البحيرة وجزيرة بوخارست','The lake and Bokharest island'))]
    page(f'''<div class="hd"><p class="ey">{T('المرحلة الأولى · تعمل بالفعل','Phase one · already open')}</p><h2>{T('الأنشطة العاملة الآن تجلب الأسرة إلى المشروع من اليوم','The venues open today already bring families to the project')}</h2></div>
<div class="acts">{''.join(f'<figure><img src="assets/{f}" alt=""><figcaption>{c}</figcaption></figure>' for f, c in acts)}</div>''')
    page(f'''<div class="two"><div><div class="hd"><p class="ey">{T('فندق بلازا','Plaza Hotel')}</p><h2>{T('١٤ غرفة وجناحًا فوق البحيرة','14 rooms and suites over the lake')}</h2></div>
<p class="lead">{T('فندق بوتيك صمّمته المجموعة ونفّذته في مبنى المرحلة الأولى: ٧ غرف في الأرضي و٧ في الأول، وحمام سباحة، ومطعم الجزيرة على البحيرة.','A boutique hotel designed and built by the group in the phase one building: 7 rooms on the ground floor and 7 on the first, a pool and the island restaurant on the lake.')}</p>
<div class="rooms">{''.join(f'<img src="assets/p4-room-{i}.jpg" alt="">' for i in (1, 3, 5, 7))}</div></div><figure class="ph"><img src="assets/bok-island-lake.jpg" alt=""><figcaption>{T('البحيرة وجزيرة بوخارست','The lake and Bokharest island')}</figcaption></figure></div>''')
    # chapter: phase two
    out2 = sum(tonum(r[4]) for r in p2)
    chapter(T('المرحلة الثانية','Phase two'), T('تشغيل يونيو ٢٠٢٧','Opening June 2027'), T('وحدات البلازا في الدور الأرضي ومطاعمها بتراساتها الخارجية، والفود كورت في الدور الأول.','The plaza units on the ground floor with the restaurants’ outdoor terraces, and the first-floor food court.'), 'entry-square.jpg')
    page(f'''<div class="plan ph2"><figure><img src="assets/map-p2-g.jpg" alt=""></figure><div>
<div class="hd"><p class="ey">{T('المرحلة الثانية · الدور الأرضي','Phase two · ground floor')}</p><h2>{T('على البلازا مباشرة','Directly on the plaza')}</h2></div>
<div class="grid2">{stat(n(str(len(p2))), T('وحدة متاحة للإيجار','units for lease'))}{stat(n(f"{sum(tonum(r[3]) for r in p2):,.2f}") + ' ' + T('م²','m²'), T('مساحة محمّلة','loaded area'))}{stat(n(f"{out2:,.2f}") + ' ' + T('م²','m²'), T('تراسات خارجية (أوت دور) للمطاعم','restaurant outdoor terraces'))}{stat(T('٣٫٢٠ م','3.20 m'), T('واجهة زجاجية لمحلات البلازا','glass shopfront on the plaza'))}</div>
<p class="small">{T('وحدات المرحلة بألوانها، والمتاحة للإيجار بإطار ذهبي. التراسات الخارجية غير محسوبة في المساحة المحمّلة.','Phase units in colour, units for lease outlined in gold. Outdoor terraces are not counted in the loaded area.')}</p></div></div>''')
    outd = [r for r in p2 if tonum(r[4])]
    page(f'''<div class="two w"><div><div class="hd"><p class="ey">{T('المرحلة الثانية · الوحدات المتاحة','Phase two · units for lease')}</p><h2>{n(str(len(p2)))} {T('وحدة','units')}</h2></div>
{table(p2, [T('الوحدة','Unit'), T('الدور','Level'), T('النشاط','Use'), T('المحمّلة م²','Loaded m²'), T('أوت دور م²','Outdoor m²')])}</div>
<div><div class="hd"><p class="ey">{T('المطاعم والأوت دور','Restaurants and outdoor')}</p><h2>{T('تراسات خارجية على البلازا','Outdoor terraces on the plaza')}</h2></div>
<div class="out">{''.join(f'<div><b><bdi>{r[0]}</bdi></b><span>{r[3]} {T("م² داخلي","m² indoor")}</span><strong>+ {r[4]} {T("م² أوت دور","m² outdoor")}</strong></div>' for r in outd)}</div>
<figure class="mini"><img src="assets/map-p2-f1.jpg" alt=""><figcaption>{T('الدور الأول: الفود كورت والبنك والشوروم الدوبلكس ضمن المرحلة الثانية','First floor: food court, the duplex bank and showroom in phase two')}</figcaption></figure></div></div>''')
    # chapter: phase three
    chapter(T('المرحلة الثالثة','Phase three'), T('تشغيل ديسمبر ٢٠٢٧','Opening December 2027'), T('باقي المحلات التجارية بالكامل في الأدوار الأربعة، ومعها الهايبر ماركت في البدروم.','All remaining shops on the four levels, together with the basement hypermarket.'), '5febc5c17f554c.webp')
    for f, lab, title in [('b1', T('البدروم','Basement'), T('البدروم · أمام الهايبر ماركت','Basement · in front of the hypermarket')), ('g', T('الأرضي','Ground'), T('الدور الأرضي','Ground floor')),
                          ('f1', T('الأول','First'), T('الدور الأول','First floor')), ('f2', T('الثاني','Second'), T('الدور الثاني','Second floor'))]:
        rs = [r for r in p3 if r[1] == lab]
        extra = T('الهايبر ماركت ٥٬٥٦٢ م² في البدروم ضمن المرحلة الثالثة وغير معروض للإيجار.','The 5,562 m² hypermarket is part of phase three and not offered for lease.') if f == 'b1' else (
                T('الوحدات G25-27 وG29-31 وG33-35 وG37 تنضم للمرحلة الثانية إذا استأجرها مستأجر الوحدة الأمامية الملاصقة لها من الظهر.','Units G25-27, G29-31, G33-35 and G37 join phase two if leased with the front unit directly behind them.') if f == 'g' else '')
        page(f'''<div class="plan"><figure><img src="assets/map-p3-{f}.jpg" alt=""></figure><div>
<div class="hd"><p class="ey">{T('المرحلة الثالثة · ديسمبر ٢٠٢٧','Phase three · December 2027')}</p><h2>{title}</h2></div>
<p class="lead">{n(str(len(rs)))} {T('وحدة متاحة للإيجار بإجمالي','units for lease,')} {n(f"{sum(tonum(r[3]) for r in rs):,.2f}")} {T('م² محمّلة','m² loaded')}</p>
{table(rs, [T('الوحدة','Unit'), T('النشاط','Use'), T('المحمّلة م²','Loaded m²')], outdoor=False)}
<p class="small">{extra}</p></div></div>''')
    # specs & handover
    spec = [(T('الارتفاع الداخلي','Clear height'), T('البدروم ٥٫٦ م · الأرضي والأول ٤٫٦ م · الثاني ٣٫٦ م','Basement 5.6 m · ground and first 4.6 m · second 3.6 m')),
            (T('الواجهة الزجاجية','Glass shopfront'), T('٣٫٢٠ م لمحلات المرحلة الثانية على البلازا · ٢٫٨٠ م لباقي المحلات','3.20 m for phase-two plaza shops · 2.80 m elsewhere')),
            (T('الكهرباء','Power'), T('جاهزة لكل وحدة','In place for every unit')),
            (T('المياه والصرف والغاز ودكت شفاط الهود','Water, drainage, gas and hood exhaust duct'), T('لوحدات المطاعم والكافيهات والفود كورت','For restaurant, café and food-court units')),
            (T('التسليم','Handover'), T('White Box: أرضية مستوية وحوائط فاصلة ولوحة كهرباء مستقلة وشبكة إطفاء وإنذار','White box: level floor, partition walls, dedicated electrical panel, sprinklers and alarms'))]
    page(f'''<div class="two"><div><div class="hd"><p class="ey">{T('المواصفات والتسليم','Specification and handover')}</p><h2>{T('كل وحدة جاهزة للتجهيز','Every unit is ready for fit-out')}</h2></div>
<table class="tb"><tbody>{''.join(f'<tr><td>{a}</td><td><b>{b}</b></td></tr>' for a, b in spec)}</tbody></table></div>
<figure class="ph"><img src="assets/f0755181e1a7d4.webp" alt=""><figcaption>{T('مقتطف من لوحة الواجهات الداخلية','Extract from the internal elevations drawing')}</figcaption></figure></div>''')
    steps = [T('معاينة','Site visit'), T('عرض وتعاقد','Offer and lease'), T('استلام فني','Technical handover'), T('اعتماد تصميم الفرع','Store design approval'), T('تجهيز وافتتاح','Fit-out and opening')]
    models = [(T('إيجار ثابت','Fixed rent'), T('قيمة شهرية للمتر تُحسب على المساحة المحمّلة.','A monthly rate per m² on the loaded area.')),
              (T('نسبة من المبيعات','Turnover rent'), T('نسبة تعاقدية من صافي مبيعات الفرع.','An agreed share of net sales.')),
              (T('إيجار مختلط','Hybrid'), T('حد أدنى مضمون مع نسبة من المبيعات.','A guaranteed minimum plus a share of sales.'))]
    page(f'''<div class="hd"><p class="ey">{T('نماذج التعاقد وخطوات الافتتاح','Lease models and steps to opening')}</p><h2>{T('الإيجار على المساحة المحمّلة','Rent is charged on the loaded area')}</h2></div>
<div class="grid3 mb">{''.join(f'<div class="st"><b class="sm">{a}</b><span>{b}</span></div>' for a, b in models)}</div>
<ol class="steps dark">{''.join(f'<li><b>{n(str(i+1))}</b>{s}</li>' for i, s in enumerate(steps))}</ol>
<figure class="strip tall"><img src="assets/Happiness_Plaza_Opening.jpg" alt=""></figure>
<p class="small">{T('الأسعار ورسوم الخدمة ومدة العقد والزيادة السنوية وفترة التجهيز والتأمين تُحدد في العرض الذي يقدمه فريق التأجير لكل وحدة.','Rates, service charge, lease term, escalation, fit-out period and deposit are set in the leasing team’s offer for each unit.')}</p>''')
    # contact
    page(f'''<img class="bg" src="assets/13e41f59c10970.webp" alt=""><div class="cv end"><p class="ey">{T('احجز وحدتك في المرحلة المناسبة لبراندك','Choose the phase that fits your brand')}</p>
<h2>{T('تواصل مع فريق التأجير','Contact the leasing team')}</h2>
<p class="ct"><span>{T('واتساب واتصال','WhatsApp and phone')}: <bdi>0122 777 7104</bdi></span><span><bdi>info@happinessplaza.com</bdi></span></p>
<p class="ct"><span>{T('الدليل التفاعلي','Interactive guide')}: <bdi>alhabibengcom-afk.github.io/alhabibengcom-gmail.com/lite/{'' if ar else 'en/'}</bdi></span></p>
<p class="small lt">{T('التوافر النهائي والحجز والتعاقد تتم من خلال فريق التأجير، والمساحات المذكورة مساحات محمّلة حسب ملف الوحدات الموحد.','Final availability, reservation and leasing are handled by the leasing team; areas are loaded areas per the unified unit file.')}</p></div>''', 'cover last', False)

    if ar: pages[:] = [pg.replace(' · ', ' – ') for pg in pages]
    pages[:] = [re.sub(r'assets/([^"]+?)\.(webp|jpg)', r'pack-img/\1.jpg', pg) for pg in pages]
    css = open(B + '/pack.css', encoding='utf-8').read() + open(B + '/book.css', encoding='utf-8').read()
    return f'<!doctype html><html lang="{lang}" dir="{"rtl" if ar else "ltr"}"><head><meta charset="utf-8"><title>Happiness Plaza Book</title><style>{css}</style></head><body class="{lang}">{"".join(pages)}</body></html>'

for l in ['ar', 'en']:
    open(f'{B}/book-{l}.html', 'w', encoding='utf-8').write(build(l))
print('ok')
