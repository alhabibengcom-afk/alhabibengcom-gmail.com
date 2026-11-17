// Renders profile.html to PDF (Arabic + English).
// usage: node render.js [outdir]      (set PREVIEW=<dir> to also save one PNG per page)
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

(async () => {
  const out = process.argv[2] || path.join(__dirname, 'output');
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch();
  for (const lang of ['ar', 'en']) {
    const page = await browser.newPage({ viewport: { width: 1123, height: 794 } });
    await page.goto('file://' + path.join(__dirname, 'profile.html') + '?lang=' + lang, { waitUntil: 'networkidle' });
    await page.evaluate(() => document.fonts.ready);
    if (process.env.PREVIEW) {
      const pages = await page.$$('.page');
      for (let i = 0; i < pages.length; i++) {
        await pages[i].screenshot({ path: path.join(process.env.PREVIEW, `${lang}-${String(i + 1).padStart(2, '0')}.png`) });
      }
    }
    await page.emulateMedia({ media: 'print' });
    await page.pdf({
      path: path.join(out, `Al-Habeeb_Company_Profile_${lang.toUpperCase()}.pdf`),
      width: '297mm', height: '210mm', printBackground: true, preferCSSPageSize: true,
    });
    await page.close();
  }
  await browser.close();
})();
