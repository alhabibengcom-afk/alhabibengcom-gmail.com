# Leasing Pack PDF source pages (AR/EN) for Happiness Plaza. Usage: build_pack.py <brands dir> <grab.json>
import json, sys, html, re
B, G = sys.argv[1], sys.argv[2]
D = json.load(open(G, encoding='utf-8'))
AR_DIG = str.maketrans('0123456789', '٠١٢٣٤٥٦٧٨٩')

def build(lang):
    ar = lang == 'ar'
    n = (lambda s: s.translate(AR_DIG).replace(',', '٬').replace('.', '٫')) if ar else (lambda s: s)
    T = lambda a, e: a if ar else e
    rows = D[lang]['rows']
    floors = {}
    for r in rows: floors.setdefault(r[1], []).append(r)
    F = 'هابينس بلازا · ملف التأجير' if ar else 'Happiness Plaza · Leasing Pack'
    pages = []
    def page(body, cls='', num=True):
        pages.append(f'<section class="pg {cls}">{body}' + (f'<footer><span>{F}</span><span class="pn"></span></footer>' if num else '') + '</section>')
    def stat(v, l): return f'<div class="st"><b>{v}</b><span>{l}</span></div>'

    # 1 cover
    page(f'''<img class="bg" src="assets/5febc5c17f554c.webp" alt="">
<div class="cv"><p class="ey">{T('مدينة قنا الجديدة · محافظة قنا · مصر','New Qena City · Qena Governorate · Egypt')}</p>
<h1>{T('هابينس بلازا','Happiness Plaza')}</h1>
<p class="sub">{T('ملف التأجير للعلامات التجارية','Leasing Pack for Brands')}</p>
<p class="tag">{T('مقصد التسوق الجديد لأهالي قنا','Qena’s new shopping destination')} · {n('58')} {T('وحدة متاحة للإيجار','units available for lease')}</p>
<p class="dt">{T('نوفمبر ٢٠٢٦','November 2026')}</p></div>''', 'cover', False)

    # 2 at a glance
    page(f'''<div class="hd"><p class="ey">{T('المشروع في سطور','At a glance')}</p><h2>{T('مول تجاري وفندق وترفيه حول بلازا واحدة عند مدخل قنا الجديدة','Retail, hotel and leisure around one plaza at the entrance of New Qena')}</h2></div>
<div class="grid4">{stat(n('144'), T('وحدة تجارية على أربعة أدوار','retail units on four levels'))}{stat(n('58'), T('وحدة متاحة للإيجار بإجمالي ٩٬٤٥٩ م² محمّلة','units for lease, 9,459 m² loaded in total'))}{stat(n('17,785')+' '+T('م²','m²'), T('مساحة أرض المشروع','site area'))}{stat(n('4,000')+' '+T('م²','m²'), T('بلازا مفتوحة تطل عليها المحلات','open plaza the shops face'))}
{stat(n('5,562')+' '+T('م²','m²'), T('هايبر ماركت الحبيب في البدروم (المرحلة الثالثة)','Al Habeeb Hypermarket, basement (phase three)'))}{stat(n('200'), T('سيارة في جراج على مستويين','cars in a two-level garage'))}{stat(n('8')+' '+T('كم','km'), T('من مدينة قنا','from Qena city'))}{stat(T('ديسمبر ٢٠٢٦','Dec 2026'), T('افتتاح المرحلة الأولى رسميًا، وهي قيد التشغيل الآن','official opening of phase one, already in operation'))}</div>''')

    # 3 developer
    page(f'''<div class="two"><div><div class="hd"><p class="ey">{T('المالك والمطوّر','Owner and developer')}</p><h2>{T('الحبيب للتنمية والاستثمار ش.م.م.','Alhabeeb for Development & Investment LLC')}</h2></div>
<p class="lead">{T('مجموعة من الشركات تعمل في تجارة التجزئة من خلال سلسلة الحبيب ماركت، والإنتاج الزراعي من خلال مزارع الحبيب، والتطوير العقاري والتصميم والمقاولات. تأسست المجموعة ونمت وتطورت في محافظة قنا.','A group of companies in retail through the Al Habeeb Market chain, farming through Al Habeeb Farms, and real-estate development, design and contracting. The group was founded and grew in Qena Governorate.')}</p>
<ol class="biz"><li><b>{T('التجزئة: سلسلة الحبيب ماركت','Retail: Al Habeeb Market')}</b>{T('منذ ٢٠٠٨، ٤ فروع في قنا والبحر الأحمر وتطبيق للطلب أونلاين. يشغّل الهايبر ماركت في هابينس بلازا.','Since 2008, 4 branches in Qena and the Red Sea plus an online ordering app. Operates the hypermarket at Happiness Plaza.')}</li>
<li><b>{T('الزراعة: مزارع الحبيب','Farming: Al Habeeb Farms')}</b>{T('منذ ٢٠١٤: ٢ مليون طائر و٣٬٠٠٠ رأس ماشية سنويًا.','Since 2014: 2 million birds and 3,000 head of cattle a year.')}</li>
<li><b>{T('التطوير العقاري','Real-estate development')}</b>{T('منذ ٢٠٢١ بمشروع هابينس بلازا.','Since 2021, with Happiness Plaza.')}</li>
<li><b>{T('التصميم والمقاولات','Design and contracting')}</b>{T('منذ ٢٠٠٨ في قنا: تصميم وتنفيذ وإدارة مشروعات.','Since 2008 in Qena: design, construction and project management.')}</li></ol>
<p class="small">{T('شركاء وجهات تعامل: جهاز مدينة قنا الجديدة، جهاز مدينة أسوان الجديدة، البنك الأهلي المصري، بنك قطر الوطني الأهلي QNB، AMA للتطوير العقاري.','Partners and counterparts: New Qena City Authority, New Aswan City Authority, National Bank of Egypt, QNB, AMA Real Estate Development.')}</p></div>
<figure class="ph"><img src="assets/Happiness_Plaza_Opening.jpg" alt=""></figure></div>''')

    # 4 location
    loc = [(T('على مدخل مدينة قنا الجديدة','At the entrance of New Qena City'), T('الحي الأول، على بعد نحو ٨ كم من مدينة قنا، وعلى محاور قنا–سفاجا وقنا–الأقصر والطريق الصحراوي إلى القاهرة.','District 1, about 8 km from Qena city, on the Qena–Safaga and Qena–Luxor roads and the desert road to Cairo.')),
           (T('بلازا مفتوحة ٤٬٠٠٠ م²','A 4,000 m² open plaza'), T('المحلات والمطاعم والفندق والبحيرة كلها حول بلازا واحدة.','Shops, restaurants, the hotel and the lake all face one plaza.')),
           (T('هايبر ماركت ٥٬٥٦٢ م²','A 5,562 m² hypermarket'), T('يشغّله الحبيب ماركت في البدروم ويجلب زيارات يومية للمول.','Run by Al Habeeb Market in the basement, bringing daily visits to the mall.')),
           (T('جراج على مستويين لـ٢٠٠ سيارة','A two-level garage for 200 cars'), T('٧٬٢٨٩ م²، بواقع ٣٬٦٤٤ م² لكل مستوى.','7,289 m², 3,644 m² on each level.')),
           (T('٣ مداخل وحركة رأسية كاملة','3 entrances and full vertical circulation'), T('مصعد بانورامي وسلّمان متحركان وسلالم رئيسية وطوارئ.','Panoramic lift, two escalators, main and emergency stairs.')),
           (T('خدمات للزائر والمستأجر','Services for visitors and tenants'), T('مصلى ودورات مياه وماكينة صراف، ورصيف تحميل ومصعد بضائع، وأمن وكاميرات وإطفاء آلي.','Prayer room, toilets, ATM, loading bay, goods lift, security, CCTV and sprinklers.'))]
    page(f'''<div class="two"><div><div class="hd"><p class="ey">{T('الموقع والمميزات','Location and advantages')}</p><h2>{T('عند بوابة قنا الجديدة','At the gateway to New Qena')}</h2></div>
<ul class="kv">{''.join(f'<li><b>{a}</b><span>{b}</span></li>' for a,b in loc)}</ul></div>
<figure class="ph"><img src="assets/bok-island-lake.jpg" alt=""><figcaption>{T('البحيرة وجزيرة بوخارست على البلازا','The lake and Bokharest island on the plaza')}</figcaption></figure></div>''')

    # 5 phase one
    acts = [('Guru_Fit.jpg', T('جيم Guru Fit','Guru Fit gym')), ('AURA.jpg', T('نادي صحي نسائي AURA','AURA women’s wellness club')), ('Bokharest_Black.jpg', T('مطعم بوخارست بلاك','Bokharest Black restaurant')),
            ('Joy_Park.jpg', T('ألعاب أطفال Joy Park','Joy Park kids’ play')), ('Plaza_Hotel.jpg', T('فندق بلازا · ١٤ غرفة وجناحًا','Plaza Hotel · 14 rooms and suites')), ('Joy_Bites.jpg', T('سندوتشات خفيفة وآيس كريم Joy Bites','Joy Bites snacks and ice cream')),
            ('Happiness_Pharmacy.jpg', T('صيدلية هابينس','Happiness Pharmacy'))]
    page(f'''<div class="hd"><p class="ey">{T('المرحلة الأولى · قيد التشغيل','Phase one · in operation')}</p><h2>{T('الفندق والأنشطة الترفيهية تعمل الآن، والافتتاح الرسمي ديسمبر ٢٠٢٦','The hotel and leisure venues are open; official opening December 2026')}</h2></div>
<div class="acts">{''.join(f'<figure><img src="assets/{f}" alt=""><figcaption>{c}</figcaption></figure>' for f,c in acts)}
<div class="note"><b>{T('مراحل المشروع','Project phases')}</b><span>{T('١. الفندق والترفيه: قيد التشغيل','1. Hotel and leisure: in operation')}</span><span>{T('٢. المحلات التجارية: معروضة للإيجار الآن','2. Retail units: now leasing')}</span><span>{T('٣. هايبر ماركت الحبيب','3. Al Habeeb Hypermarket')}</span></div></div>''')

    # 6 market
    page(f'''<div class="hd"><p class="ey">{T('دراسة سوق قنا · الزيارات','Qena market study · Visits')}</p><h2>{T('نحو ٣٬٠٠٠ زيارة يوميًا للمول كاملًا بعد تشغيل الهايبر','About 3,000 visits a day for the full mall once the hypermarket opens')}</h2></div>
<div class="grid3">{stat(T('نحو ٣٬٠٠٠','About 3,000'), T('زيارة في اليوم','visits a day'))}{stat(T('نحو ٩٠ ألف','About 90,000'), T('زيارة في الشهر','visits a month'))}{stat(T('نحو ١٫١ مليون','About 1.1 million'), T('زيارة في السنة','visits a year'))}</div>
<table class="tb"><thead><tr><th>{T('مصدر الزيارات','Source of visits')}</th><th>{T('يوميًا','A day')}</th></tr></thead><tbody>
<tr><td>{T('سكان قنا الجديدة وقسم ومركز قنا للمحلات والمطاعم والترفيه (السيناريو الأساسي للدراسة: ٢٩٬٣١٨ زيارة شهريًا)','Residents of New Qena and Qena district and markaz visiting shops, dining and leisure (study base case: 29,318 visits a month)')}</td><td>{n('977')}</td></tr>
<tr><td>{T('تسوق أسبوعي من الهايبر: ٦٪ من نحو ١٨٠ ألف أسرة في النطاق (٤٫٥ فرد للأسرة)','Weekly hypermarket shopping: 6% of about 180,000 catchment households (4.5 people each)')}</td><td>{T('نحو ١٬٥٥٠','About 1,550')}</td></tr>
<tr><td>{T('زوار من باقي المحافظة: ٠٫٥٪ من نحو ٢٫٩٥ مليون نسمة مرة شهريًا','Visitors from the rest of the governorate: 0.5% of about 2.95 million people once a month')}</td><td>{T('نحو ٥٠٠','About 500')}</td></tr></tbody></table>
<figure class="strip"><img src="assets/entry-square.jpg" alt=""></figure><p class="small">{T('تقدير استرشادي من فريق المشروع بافتراضات متحفظة، لا يشمل المسافرين والسياح. المصادر: تقديرات السكان (الجهاز المركزي للتعبئة العامة والإحصاء) وخطة المواطن الاستثمارية لمحافظة قنا ٢٠٢٣/٢٠٢٤. يُحدَّث بعدّادات الزوار الفعلية بعد التشغيل.','Indicative project-team estimate on conservative assumptions, excluding travellers and tourists. Sources: CAPMAS population estimates and the Citizen’s Investment Plan for Qena Governorate 2023/2024. To be updated with actual footfall counts after opening.')}</p>''')

    # 7 specs + lease
    spec = [(T('ارتفاع السقف','Ceiling height'), T('٤٫٦ م','4.6 m')), (T('الواجهة الزجاجية','Glass shopfront'), T('بارتفاع ٢٫٨٠ م','2.80 m high')),
            (T('الكهرباء','Power'), T('جاهزة لكل وحدة','In place for every unit')), (T('المياه والصرف','Water and drainage'), T('جاهزة لكل وحدة','In place for every unit')),
            (T('دكت الشفاط','Kitchen exhaust duct'), T('جاهز لكل وحدة','In place for every unit')), (T('الغاز','Gas'), T('جاهز لكل وحدة','In place for every unit'))]
    models = [(T('إيجار ثابت','Fixed rent'), T('قيمة شهرية للمتر تُحسب على المساحة المحمّلة.','A monthly rate per m² on the loaded area.')),
              (T('نسبة من المبيعات','Turnover rent'), T('نسبة تعاقدية من صافي مبيعات الفرع.','An agreed share of the store’s net sales.')),
              (T('إيجار مختلط','Hybrid'), T('حد أدنى مضمون مع نسبة من المبيعات.','A guaranteed minimum plus a share of sales.'))]
    page(f'''<div class="two"><div><div class="hd"><p class="ey">{T('المواصفات والتسليم','Specification and handover')}</p><h2>{T('كل وحدة جاهزة للتجهيز من أول يوم','Every unit is ready for fit-out from day one')}</h2></div>
<table class="tb"><tbody>{''.join(f'<tr><td>{a}</td><td><b>{b}</b></td></tr>' for a,b in spec)}</tbody></table>
<p class="small">{T('تُسلَّم الوحدة بنظام White Box: أرضية مستوية وحوائط فاصلة، ولوحة كهرباء مستقلة، وشبكة إطفاء وإنذار. التشطيبات والأثاث وتوزيع الإنارة على المستأجر، ويثبّت الملحق الفني لكل وحدة تفاصيل التسليم.','Units are handed over as a white box: level floor and partition walls, a dedicated electrical panel, and fire sprinklers and alarms. Finishes, furniture and lighting layout are the tenant’s; each unit’s technical annex sets the handover details.')}</p></div>
<div><div class="hd"><p class="ey">{T('نماذج التعاقد','Lease models')}</p><h2>{T('الإيجار على المساحة المحمّلة','Rent is charged on the loaded area')}</h2></div>
<ul class="kv">{''.join(f'<li><b>{a}</b><span>{b}</span></li>' for a,b in models)}</ul>
<p class="small">{T('الأسعار ورسوم الخدمة ومدة العقد والزيادة السنوية وفترة التجهيز والتأمين تُحدد في العرض الذي يقدمه فريق التأجير لكل وحدة.','Rates, service charge, lease term, annual escalation, fit-out period and deposit are set in the leasing team’s offer for each unit.')}</p></div></div>''')

    # 8-11 floor plans
    plans = [('plan-v15-b1.webp', T('البدروم','Basement')), ('plan-v15-g.webp', T('الأرضي','Ground')), ('plan-v15-f1.webp', T('الأول','First')), ('plan-v15-f2.webp', T('الثاني','Second'))]
    for img, fl in plans:
        rs = floors.get(fl, [])
        tot = sum(float(r[3].translate(str.maketrans('٠١٢٣٤٥٦٧٨٩٫٬', '0123456789.,')).replace(',', '')) for r in rs)
        page(f'''<div class="plan"><figure><img src="assets/{img}" alt=""></figure><div>
<div class="hd"><p class="ey">{T('مخطط الدور','Floor plan')}</p><h2>{(fl if fl in ('البدروم','Basement') else (('الدور ' + fl) if ar else (fl + ' floor')))}</h2></div>
<p class="lead">{n(str(len(rs)))} {T('وحدة متاحة للإيجار بإجمالي','units for lease,')} {n(f'{tot:,.2f}')} {T('م² محمّلة','m² loaded')}</p>
<table class="tb sm{' xs' if len(rs) > 18 else ''}"><thead><tr><th>{T('الوحدة','Unit')}</th><th>{T('النشاط المقترح','Suggested use')}</th><th>{T('المحمّلة م²','Loaded m²')}</th></tr></thead><tbody>
{''.join(f'<tr><td><bdi>{r[0]}</bdi></td><td>{html.escape(r[2])}</td><td class="nm">{r[3]}</td></tr>' for r in rs)}</tbody></table>
<p class="small">{T('الألوان في المخطط تبيّن تصنيف الأنشطة. الوحدات غير الواردة في الجدول غير معروضة للإيجار.','Plan colours show the use mix. Units not listed in the table are not offered for lease.')}</p></div></div>''')

    # 12 steps + contact
    steps = [T('معاينة','Site visit'), T('عرض وتعاقد','Offer and lease'), T('استلام فني','Technical handover'), T('اعتماد تصميم الفرع','Store design approval'), T('تجهيز وافتتاح','Fit-out and opening')]
    page(f'''<img class="bg" src="assets/13e41f59c10970.webp" alt=""><div class="cv end">
<p class="ey">{T('من اختيار الوحدة إلى افتتاح الفرع','From choosing a unit to opening the store')}</p>
<ol class="steps">{''.join(f'<li><b>{n(str(i+1))}</b>{s}</li>' for i,s in enumerate(steps))}</ol>
<h2>{T('تواصل مع فريق التأجير','Contact the leasing team')}</h2>
<p class="ct"><span>{T('واتساب واتصال','WhatsApp and phone')}: <bdi>0122 777 7104</bdi></span><span><bdi>info@happinessplaza.com</bdi></span></p>
<p class="ct"><span>{T('الدليل التفاعلي','Interactive guide')}: <bdi>alhabibengcom-afk.github.io/alhabibengcom-gmail.com/lite/{'' if ar else 'en/'}</bdi></span></p>
<p class="small lt">{T('هذا الملف للتعريف بالمشروع. التوافر النهائي والحجز والتعاقد تتم من خلال فريق التأجير، والمساحات المذكورة مساحات محمّلة.','This pack introduces the project. Final availability, reservation and leasing are handled by the leasing team; all areas are loaded areas.')}</p></div>''', 'cover last', False)

    if ar: pages[:] = [pg.replace(' · ', ' – ') for pg in pages]
    pages[:] = [re.sub(r'assets/([^"]+?)\.(webp|jpg)', r'pack-img/\1.jpg', pg) for pg in pages]
    css = open(B + '/pack.css', encoding='utf-8').read()
    return f'''<!doctype html><html lang="{lang}" dir="{'rtl' if ar else 'ltr'}"><head><meta charset="utf-8"><title>Happiness Plaza Leasing Pack</title><style>{css}</style></head><body class="{lang}">{''.join(pages)}</body></html>'''

for l in ['ar', 'en']:
    open(f'{B}/pack-{l}.html', 'w', encoding='utf-8').write(build(l))
print('ok')
