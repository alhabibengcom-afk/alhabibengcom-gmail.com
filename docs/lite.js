/* Happiness Plaza: simple brand page (lite.html, or index.html?lite=1).
   Same data and pages as the full guide, with less on screen and contact through
   the leasing team only. Runs after site.js and launcher.js. */
(function () {
  if (!window.HP_LITE) return;
  var tr = function (s) { return window.HP_tr ? window.HP_tr(s) : s; };

  // No unit PDF sheets in the simple page (they hold all units and internal areas).
  window.sheetLink = function () { return null; };

  // Phase one: the activities opening with it, as photo cards.
  var NAMES = {
    'guru-film': 'جيم Guru Fit', 'aura-film': 'نادي صحي نسائي AURA', 'restaurant-film': 'مطعم بوخارست بلاك',
    'play-film': 'ألعاب أطفال Joy Park', 'hotel-film': 'فندق بلازا · ١٤ غرفة وجناحًا',
    'bites-film': 'سندوتشات خفيفة وآيس كريم Joy Bites', 'pharmacy-film': 'صيدلية هابينس'
  };
  function phase() {
    document.querySelectorAll('#phase .ed-card').forEach(function (card) {
      var v = card.querySelector('video');
      if (v) {
        var img = document.createElement('img');
        img.src = v.getAttribute('data-poster') || v.getAttribute('poster') || '';
        img.alt = NAMES[card.id] || v.getAttribute('aria-label') || '';
        img.loading = 'lazy';
        v.replaceWith(img);
      }
      card.querySelectorAll('.film-file, .ed-caption > div').forEach(function (e) { e.remove(); });
      var h3 = card.querySelector('h3');
      if (h3 && NAMES[card.id]) h3.textContent = tr(NAMES[card.id]);
    });
    var films = document.querySelector('#phase .ed-films');
    if (films && !document.querySelector('#phase .hp-lite-acts')) {
      var h = document.createElement('h3');
      h.className = 'hp-lite-acts';
      h.textContent = tr('الأنشطة التي تفتح مع المرحلة الأولى');
      films.parentNode.insertBefore(h, films);
    }
  }

  // Every picture gets a text alternative.
  function alts() {
    document.querySelectorAll('img').forEach(function (im) {
      if (im.getAttribute('alt')) return;
      var box = im.closest('figure, button, a, article, li');
      var txt = box ? (box.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 90) : '';
      im.setAttribute('alt', txt || tr('صورة من هابينس بلازا'));
    });
  }

  // WhatsApp message names the last unit the visitor looked at.
  function whatsapp() {
    var a = document.querySelector('#contact .hp-wa');
    if (!a) return;
    var r = typeof currentRoute === 'function' ? currentRoute() : '';
    if (r.indexOf('unit/') === 0) window.HP_LAST_UNIT = r.slice(5);
    var unit = window.HP_LAST_UNIT;
    var msg = window.HP_LANG === 'en'
      ? 'Hello, I would like to know more about ' + (unit ? 'unit ' + unit + ' at ' : '') + 'Happiness Plaza.'
      : 'السلام عليكم، أرغب في معرفة تفاصيل ' + (unit ? 'الوحدة ' + unit + ' في ' : 'الوحدات المتاحة في ') + 'هابينس بلازا.';
    a.href = 'https://wa.me/201227777104?text=' + encodeURIComponent(msg);
  }

  // Share: the phone's share sheet, otherwise copy the link and offer WhatsApp.
  window.HP_SHARE_PATH = 'lite/';
  function toast(html) {
    var t = document.querySelector('.hp-toast');
    if (!t) { t = document.createElement('div'); t.className = 'hp-toast'; t.setAttribute('role', 'status'); document.body.append(t); }
    t.innerHTML = html; t.classList.add('on');
    clearTimeout(t._h); t._h = setTimeout(function () { t.classList.remove('on'); }, 6000);
  }
  document.addEventListener('click', function (e) {
    var b = e.target.closest('[data-share]');
    if (!b) return;
    e.preventDefault(); e.stopImmediatePropagation();
    var url = 'https://alhabibengcom-afk.github.io/alhabibengcom-gmail.com/lite/' + (window.HP_LANG === 'en' ? 'en/' : '');
    var text = window.HP_LANG === 'en'
      ? 'Happiness Plaza, New Qena: retail units for lease. Plans, areas and photos:'
      : 'هابينس بلازا، قنا الجديدة: وحدات تجارية للإيجار. المخططات والمساحات والصور:';
    if (navigator.share) { navigator.share({ title: 'Happiness Plaza', text: text, url: url }).catch(function () {}); return; }
    var wa = 'https://wa.me/?text=' + encodeURIComponent(text + ' ' + url);
    var done = function () {
      toast(tr('تم نسخ رابط الدليل.') + ' <a href="' + wa + '" target="_blank" rel="noopener">' + tr('مشاركة على واتساب') + '</a>');
    };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(url).then(done, done); else done();
  }, true);

  // Leasing Pack PDF in the page language.
  function pack() {
    document.querySelectorAll('.hp-pack').forEach(function (a) {
      a.href = window.HP_LANG === 'en' ? 'Happiness_Plaza_Leasing_Pack_EN.pdf' : 'Happiness_Plaza_Leasing_Pack.pdf';
    });
    document.querySelectorAll('.hp-book').forEach(function (a) {
      a.href = window.HP_LANG === 'en' ? 'Happiness_Plaza_Book_EN.pdf' : 'Happiness_Plaza_Book.pdf';
    });
  }

  function run() { phase(); alts(); whatsapp(); pack(); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', run); else run();
  ['pushState', 'replaceState'].forEach(function (k) {
    var o = history[k]; history[k] = function () { var r = o.apply(this, arguments); setTimeout(function () { whatsapp(); alts(); }, 0); return r; };
  });
  window.addEventListener('popstate', whatsapp);
})();
