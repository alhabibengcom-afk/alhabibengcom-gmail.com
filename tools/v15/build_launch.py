"""Turn the guide's first screen into a launcher: the looping site film with the main buttons.

Usage: python3 build_launch.py SITE_DIR   (safe to run again)
"""
import json, re, sys
B = sys.argv[1]
EN = {}
def t(ar, en):
    EN[ar] = en; return ar

BTNS = [
    ('owner', 'owner', t('مين المالك؟', 'The owner'), t('الحبيب للتنمية والاستثمار', 'Al-Habeeb Group'), ''),
    ('why', 'why', t('ليه قنا والصعيد؟', 'Why Qena?'), t('سوق ٣٫٧ مليون نسمة', 'A market of 3.7 million'), ''),
    ('location', 'location', t('الموقع والمميزات', 'Location'), t('مدخل قنا الجديدة', 'The entrance of New Qena'), ''),
    ('goal', 'goal', t('هدفنا', 'Our goal'), t('مقصد أهالي قنا', 'Qena’s destination'), ''),
    ('phase', 'phase', t('المرحلة الأولى', 'Phase one'), t('قيد التشغيل', 'In operation'), ''),
    ('market', 'market', t('دراسة سوق قنا', 'Market study'), t('السكان والزيارات', 'Population and visits'), ''),
    ('?floor=g', 'plan/g', t('مخططات المحلات', 'Shop plans'), t('١٤٤ وحدة على ٤ أدوار', '144 units on 4 levels'), ' hp-gold'),
    ('deals', 'deals', t('التسليم والتعاقد', 'Handover & terms'), t('White Box ونماذج التعاقد', 'White box, lease models'), ''),
    ('contact', 'contact', t('احجز معاينة', 'Book a viewing'), t('واتساب 0122 777 7104', 'WhatsApp 0122 777 7104'), ' hp-gold'),
]

def link(h, r, title, sub, cls):
    href = h if h.startswith('?') else './#' + h
    return f'<a class="hp-tile{cls}" href="{href}" data-route="{r}"><strong>{title}</strong><small>{sub}</small></a>'

home = ('<section id="home" class="pro-hero hp-launch">'
        '<video class="pro-hero-bg" autoplay muted loop playsinline preload="auto" poster="assets/Happiness_Plaza_Opening.jpg" src="assets/hero-loop.mp4" aria-hidden="true" tabindex="-1"></video>'
        '<div class="pro-hero-shade" aria-hidden="true"></div>'
        '<div class="wrap hp-launch-inner" id="project">'
        '<p class="pro-eyebrow"><span lang="en" dir="ltr">LEASING GUIDE</span><i aria-hidden="true"></i>قنا الجديدة · مصر</p>'
        '<h1>هابينس بلازا</h1>'
        '<p class="hp-tag">' + t('مقصد التسوق الجديد لأهالي قنا · ١٤٤ وحدة تجارية للإيجار', '144 retail units for lease in New Qena') + '</p>'
        '<nav class="hp-grid" aria-label="' + t('أقسام الدليل', 'Guide sections') + '">' + ''.join(link(*b) for b in BTNS) + '</nav>'
        '<div class="hp-mini">'
        '<a href="?unit=F08&amp;view=tour&amp;scene=575" data-route="unit/F08" data-unit-view="tour" data-scene="575">جولة المحلات <bdi dir="ltr">360°</bdi></a>'
        '<a href="./#tour" data-route="tour">' + t('فيلم الموقع بالصوت', 'Site film with sound') + '</a>'
        '<button type="button" class="hp-share-link" data-share>شارك الدليل <span aria-hidden="true">↗</span></button>'
        '</div></div></section>')

p = B + '/index.html'
s = open(p, encoding='utf-8').read()
i = s.index('<section id="home"'); j = s.index('</section>', i) + len('</section>')
s = s[:i] + home + s[j:]
if 'id="film"' not in s:
    s = s.replace('<section class="pro-film-section"', '<section id="film" class="pro-film-section"', 1)
bar = ('<div class="hp-backbar" role="navigation" aria-label="' + t('التنقل', 'Navigation') + '">'
       '<a href="./#home" data-route="home" class="hp-back"><span aria-hidden="true">→</span> ' + t('الرئيسية', 'Home') + '</a>'
       '<strong class="hp-backbar-title"></strong>'
       '<a href="./#contact" data-route="contact" class="hp-back-cta">احجز معاينة</a></div>')
s = re.sub(r'<div class="hp-backbar".*?</div>', '', s, flags=re.S)
s = s.replace('<main id="mainpage">', bar + '<main id="mainpage">', 1)
if 'launcher.js' not in s:
    s = re.sub(r'(<script src="site.js\?v=[^"]*"></script>)', r'\1<script src="launcher.js?v=15a"></script>', s, count=1)
open(p, 'w', encoding='utf-8').write(s)

for k in ['الحبيب للتنمية والاستثمار', 'مين المالك؟', 'ليه قنا والصعيد؟', 'هدفنا', 'المرحلة الأولى', 'احجز معاينة']:
    pass
t('الموقع والمميزات', 'Location and advantages'); t('دراسة سوق قنا', 'Qena market study'); t('مخططات المحلات', 'Shop plans')
t('التسليم والتعاقد', 'Handover and leasing')
p = B + '/i18n-en.js'
x = open(p, encoding='utf-8').read(); i = x.index('{'); j = x.rindex('}')
d = json.loads(x[i:j + 1]); d.update(EN)
open(p, 'w', encoding='utf-8').write(x[:i] + json.dumps(d, ensure_ascii=False, separators=(',', ':')) + x[j + 1:])

CSS = r'''
/* ---------- One-screen launcher (v15) ---------- */
.hp-launch { min-height: 100svh; justify-content: center; }
.hp-launch .pro-hero-shade { background: linear-gradient(180deg, rgba(14, 26, 22, .55) 0%, rgba(14, 26, 22, .45) 40%, rgba(14, 26, 22, .88) 100%); }
.hp-launch-inner { width: 100%; padding-top: clamp(96px, 12vh, 140px); padding-bottom: clamp(40px, 6vh, 72px); }
.hp-launch h1 { margin: 0; }
.hp-launch-inner#project { border-top: 0; }
.hp-tag { margin-top: 10px; font-size: clamp(17px, 1.6vw, 21px); color: #efe4cc; }
.hp-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin-top: clamp(24px, 4vh, 40px); max-width: 980px; }
.hp-tile { display: flex; flex-direction: column; gap: 2px; padding: 16px 18px; border-radius: 10px; background: rgba(20, 36, 31, .55); border: 1px solid rgba(255, 255, 255, .22); color: #fbf8f0; text-decoration: none; backdrop-filter: blur(6px); -webkit-backdrop-filter: blur(6px); transition: background .2s, transform .2s; }
.hp-tile strong { font-size: 18px; line-height: 1.4; }
.hp-tile small { font-size: 13px; color: #d9ddd3; line-height: 1.5; }
.hp-tile:hover, .hp-tile:focus-visible { background: rgba(31, 54, 45, .85); transform: translateY(-2px); }
.hp-tile.hp-gold { background: #e2c38b; border-color: #e2c38b; color: #1b2e28; }
.hp-tile.hp-gold small { color: #3d3a2f; }
.hp-mini { display: flex; flex-wrap: wrap; gap: 10px 22px; margin-top: 18px; font-size: 15px; }
.hp-mini a, .hp-share-link { color: #fbf8f0; text-decoration: underline; text-underline-offset: 4px; background: none; border: 0; padding: 0; font: inherit; cursor: pointer; }
/* views */
body[data-view="home"] #mainpage > section:not(#home),
body[data-view="section"] #mainpage > section:not(.hp-on) { display: none !important; }
body[data-view="home"] .appbar, body[data-view="home"] .mast-links, body[data-view="home"] .foot { display: none !important; }
.hp-backbar { display: none; }
body[data-view="section"] .hp-backbar { display: flex; position: sticky; top: 72px; z-index: 9; align-items: center; gap: 14px; padding: 10px clamp(16px, 5vw, 80px); background: #f4f1e9; border-bottom: 1px solid #d8d2c4; }
.hp-back { font-weight: 700; color: #1f362d; text-decoration: none; white-space: nowrap; }
.hp-backbar-title { flex: 1; font-size: 15px; color: #5b605c; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.hp-back-cta { padding: 6px 14px; border-radius: 6px; background: #e2c38b; color: #1b2e28; font-weight: 700; text-decoration: none; white-space: nowrap; font-size: 14px; }
@media (max-width: 900px) { body[data-view="section"] .hp-backbar { top: 62px; } }
@media (max-width: 700px) {
  body[data-view="section"] .hp-backbar { top: 55px; }
  .hp-grid { grid-template-columns: 1fr 1fr; gap: 8px; }
  .hp-tile { padding: 12px 12px; border-radius: 8px; }
  .hp-tile strong { font-size: 16px; }
  .hp-tile small { font-size: 12px; }
  .hp-tile:last-child { grid-column: 1 / -1; }
  .hp-launch { min-height: calc(100svh - 55px); }
  .hp-launch-inner { padding-top: 18px; padding-bottom: 18px; }
  .hp-launch .pro-eyebrow { display: none; }
  .hp-launch h1 { font-size: 42px; line-height: 1.2; }
  .hp-tag { font-size: 15px; margin-top: 4px; }
  .hp-grid { margin-top: 16px; }
  .hp-tile { padding: 9px 11px; gap: 0; }
  .hp-tile strong { font-size: 15px; }
  .hp-tile small { font-size: 11.5px; }
  .hp-mini { margin-top: 12px; font-size: 14px; gap: 8px 16px; }
}
'''
p = B + '/pro.css'
x = open(p, encoding='utf-8').read()
x = re.sub(r'\n/\* ---------- One-screen launcher \(v15\) ---------- \*/.*?(?=\n/\* ----------|\Z)', '', x, flags=re.S)
open(p, 'w', encoding='utf-8').write(x.rstrip() + '\n' + CSS)
print('launcher built')
