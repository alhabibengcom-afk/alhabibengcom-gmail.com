# بطاقة التعريف الرقمية — الحبيب للهندسة والمقاولات
**Al-Habeeb Engineering & Contracting — Digital Business Card**

صفحة واحدة (`index.html`) تُرسل للعملاء كبطاقة تعريف. كل الأزرار روابط عادية
(`tel:` / `wa.me` / `mailto:` / Google Maps / ملف `.vcf`) ولا تعتمد على أي سيرفر أو JavaScript.

## الملفات
| الملف | الوظيفة |
|---|---|
| `index.html` | البطاقة |
| `alhabeeb.vcf` | زر «احفظ جهة الاتصال» |
| `assets/logo.png`, `assets/cover.jpg` | اللوجو وصورة الغلاف |

## تفعيل الأزرار المخفية
- **لينكدإن:** في `index.html` ابحث عن `btn-linkedin`، ضع رابط الصفحة مكان `LINKEDIN_URL` واحذف كلمة `hidden`.
- **الملف التعريفي:** ارفع ملف الـ PDF في نفس الفولدر باسم `Al-Habeeb-Company-Profile-AR.pdf`،
  ثم ابحث عن `btn-profile` واحذف كلمة `hidden`.

## النشر (GitHub Pages)
Settings ← Pages ← Source: *Deploy from a branch* ← اختر الفرع والمجلد `/ (root)` ← Save.
يُفضّل ربط دومين فرعي مثل `card.alhabeebconst.com` ليظهر الرابط باسم الشركة.

## نسخة الـ PDF
`Al-Habeeb-Engineering-Introduction.pdf` — صفحة A4 واحدة بنفس التصميم، كل الأزرار فيها روابط قابلة للضغط.
المصدر: `pdf/introduction.html`. لإعادة التوليد بعد أي تعديل، اطبع الصفحة من Chrome (Save as PDF، الهوامش None، مع تفعيل Background graphics).

## الرفع على موقع الشركة (alhabeebconst.com)
`upload/alhabeeb-card-upload.zip` فيه فولدر `card` جاهز. فكّه وارفعه في الفولدر الرئيسي للموقع (`public_html`)، فيبقى:
- الكارت: `https://alhabeebconst.com/card/`
- صفحة الاتصال: `https://alhabeebconst.com/card/call.html` (زرار الاتصال في الـ PDF بيفتحها)
- صفحة الإيميل: `https://alhabeebconst.com/card/mail.html` (زرار الإيميل في الـ PDF بيفتحها)

السبب: عارض الـ PDF في Chrome على أندرويد مبيفتحش لينكات `tel:` و`mailto:` مباشرة، فالزرارين بيفتحوا صفحة على الموقع وهي اللي تبدأ الاتصال أو الإيميل.
