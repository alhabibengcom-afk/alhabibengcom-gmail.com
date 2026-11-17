# Al-Habeeb Company Profile (2026)

Bilingual (Arabic / English) company profile, A4 landscape, 19 pages.

- `profile.html` — single source for both languages (`?lang=en` for English).
- `assets/` — logo, QR codes and project images (taken from the previous profile and the Happiness Plaza leasing atlas on Google Drive).
- `render.js` — builds the PDFs: `node render.js` → `output/Al-Habeeb_Company_Profile_AR.pdf` and `_EN.pdf`.

To edit text, change the `<span class="a">` (Arabic) and `<span class="e">` (English) pair in `profile.html`, then re-run `node render.js`.
