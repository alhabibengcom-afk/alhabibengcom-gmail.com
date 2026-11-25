# Floor plans PDF (drawings plus a colour key per floor). Usage: build_plans_pdf.py <brands dir>  -> writes plans-key.html
import sys
B = sys.argv[1]
K = {  # colour on the drawings -> activity
    'hyper': ('#a0c8e8', 'هايبر ماركت', 'Hypermarket'),
    'acc': ('#f05a28', 'إكسسوارات', 'Accessories'),
    'mob': ('#7e57c2', 'موبايلات', 'Mobiles'),
    'kids': ('#f7c7a6', 'منطقة أطفال وحضانة', 'Kids area & nursery'),
    'fb': ('#218080', 'مطاعم وكافيهات', 'Restaurants & cafés'),
    'out': ('#b8e0d8', 'تراسات المطاعم الخارجية', 'Restaurant outdoor terraces'),
    'fash': ('#f08090', 'أزياء', 'Fashion'),
    'show': ('#5080d0', 'شوروم ومعارض', 'Showrooms'),
    'bank': ('#d8e0f0', 'بنوك وخدمات مالية', 'Banks & finance'),
    'taken': ('#f0b000', 'محلات صغيرة (أنشطة سريعة)', 'Small shops (quick-service)'),
    'tel': ('#10b0c0', 'اتصالات', 'Telecom'),
    'med': ('#209050', 'صيدلية وخدمات طبية', 'Pharmacy & medical'),
    'retail': ('#303090', 'تجزئة ولايف ستايل', 'Retail & lifestyle'),
    'fc': ('#e0c070', 'فود كورت', 'Food court'),
    'fun': ('#b050a0', 'ترفيه', 'Entertainment'),
    'common': ('#e6e8e6', 'ممرات وخدمات وجراج', 'Corridors, services & parking'),
}
FLOORS = [
    ('b1', 'البدروم', 'Basement', ['hyper', 'acc', 'mob', 'kids', 'common']),
    ('g', 'الدور الأرضي', 'Ground floor', ['fb', 'out', 'fash', 'show', 'acc', 'bank', 'tel', 'med', 'retail', 'taken', 'common']),
    ('f1', 'الدور الأول', 'First floor', ['fc', 'fb', 'fash', 'show', 'acc', 'bank', 'retail', 'taken', 'common']),
    ('f2', 'الدور الثاني', 'Second floor', ['retail', 'fb', 'fun', 'common']),
]
pages = []
for f, ar, en, keys in FLOORS:
    items = ''.join(f'<li><i style="background:{K[k][0]}"></i><span><b>{K[k][1]}</b><small>{K[k][2]}</small></span></li>' for k in keys)
    pages.append(f'<section class="pg"><figure><img src="pack-img/plan-full-{f}.jpg" alt=""></figure>'
                 f'<aside><h2>{ar}<small>{en}</small></h2><p class="k">مفتاح الألوان · Colour key</p><ul>{items}</ul>'
                 f'<p class="n">هابينس بلازا · مخططات الأدوار<br>Happiness Plaza · Floor plans</p></aside></section>')
css = '''@font-face{font-family:Arabic;src:url(assets/7314b041ae057b.woff) format('woff')}
@font-face{font-family:Arabic;src:url(assets/9cebf9be7d6eee.woff) format('woff');font-weight:700}
@page{size:297mm 210mm;margin:0}*{box-sizing:border-box;margin:0;padding:0}
body{font-family:Arabic,Inter,sans-serif;color:#1f2a26}
.pg{width:297mm;height:210mm;display:grid;grid-template-columns:200mm 1fr;gap:6mm;padding:8mm;page-break-after:always;background:#fff}
.pg:last-child{page-break-after:auto}
figure{display:flex;align-items:center;justify-content:center;height:194mm}figure img{max-width:100%;max-height:100%}
aside{direction:rtl;border-inline-start:.4mm solid #ddd6c6;padding-inline-start:6mm;display:flex;flex-direction:column}
h2{font-size:17pt;color:#1f362d;line-height:1.2}h2 small{display:block;font-family:Inter,sans-serif;font-size:9.5pt;color:#7b7f78;font-weight:400;margin-top:1mm}
.k{font-size:9pt;color:#a8834a;font-weight:700;margin:6mm 0 3mm}
ul{list-style:none;display:grid;gap:2.6mm}li{display:flex;gap:3mm;align-items:center}
i{flex:0 0 9mm;height:6mm;border-radius:1mm;border:.3mm solid rgba(0,0,0,.18)}
li b{display:block;font-size:9.6pt;line-height:1.25}li small{display:block;font-family:Inter,sans-serif;font-size:7.6pt;color:#6b6f6a}
.n{margin-top:auto;font-size:7.6pt;color:#8a8e88;line-height:1.5}'''
open(B + '/plans-key.html', 'w', encoding='utf-8').write(f'<!doctype html><html lang="ar"><head><meta charset="utf-8"><title>Happiness Plaza Floor Plans</title><style>{css}</style></head><body>{"".join(pages)}</body></html>')
print('ok')
