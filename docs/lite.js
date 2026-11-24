/* Happiness Plaza brand guide: simple version (?lite=1, link /lite/).
   Same data and pages as the full guide, with less on screen: phase one shows its
   full film and the activities opening with it, and the extras are hidden. */
(function () {
  if (!window.HP_LITE) return;
  function run() {
    // Phase one: activity cards become photo cards; no separate activity films.
    document.querySelectorAll('#phase .ed-card').forEach(function (card) {
      var v = card.querySelector('video');
      if (v) {
        var img = document.createElement('img');
        img.src = v.getAttribute('data-poster') || v.getAttribute('poster') || '';
        img.alt = v.getAttribute('aria-label') || '';
        img.loading = 'lazy';
        v.replaceWith(img);
      }
      card.querySelectorAll('.film-file, .ed-caption span[dir="ltr"]').forEach(function (e) { e.remove(); });
      var NAMES = {"guru-film": "جيم Guru Fit", "aura-film": "نادي صحي AURA", "restaurant-film": "مطعم بوخارست بلاك", "play-film": "ألعاب أطفال Joy Park", "hotel-film": "فندق بلازا · ١٤ غرفة", "bites-film": "سناكس Joy Bites", "pharmacy-film": "صيدلية هابينس"};
      var h3 = card.querySelector('h3'); if (h3 && NAMES[card.id]) h3.textContent = window.HP_tr ? window.HP_tr(NAMES[card.id]) : NAMES[card.id];
      var top = card.querySelector('.ed-caption > div'); if (top) top.remove();
    });
    var films = document.querySelector('#phase .ed-films');
    if (films && !document.querySelector('#phase .hp-lite-acts')) {
      var h = document.createElement('h3');
      h.className = 'hp-lite-acts';
      h.textContent = window.HP_tr ? window.HP_tr('الأنشطة اللي بتفتح مع المرحلة الأولى') : 'الأنشطة اللي بتفتح مع المرحلة الأولى';
      films.parentNode.insertBefore(h, films);
    }
    // Share the simple link.
    window.HP_SHARE_PATH = 'lite/';
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', run); else run();
})();
