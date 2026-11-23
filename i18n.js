/* Happiness Plaza brand guide: Arabic / English switch.
   The page is written in Arabic. In English mode this script translates the page
   as it is built, using the dictionary in i18n-en.js (HP_EN: Arabic -> English).
   Language order of choice: ?lang=en|ar in the address, then the visitor's saved
   choice, then Arabic. Send brands the link ending in ?lang=en. */
(function () {
  var KEY = 'hp-lang';
  function pick() {
    var q = new URLSearchParams(location.search).get('lang');
    if (q === 'en' || q === 'ar') { try { localStorage.setItem(KEY, q); } catch (e) {} return q; }
    try { var s = localStorage.getItem(KEY); if (s === 'en' || s === 'ar') return s; } catch (e) {}
    return 'ar';
  }
  var lang = pick();
  window.HP_LANG = lang;

  window.HP_setLang = function (l) {
    try { localStorage.setItem(KEY, l); } catch (e) {}
    var u = new URL(location.href);
    u.searchParams.set('lang', l);
    location.href = u.toString();
  };

  if (lang !== 'en' || !window.HP_EN) return;

  var root = document.documentElement;
  root.lang = 'en';
  root.dir = 'ltr';
  root.classList.add('lang-en');

  var AR = /[؀-ۿ]/;
  var dict = window.HP_EN;
  var norm = function (s) { return s.replace(/\s+/g, ' ').trim(); };
  var exact = Object.create(null);
  var keys = [];
  for (var k in dict) {
    if (!Object.prototype.hasOwnProperty.call(dict, k)) continue;
    var nk = norm(k);
    exact[nk] = dict[k];
    if (nk.length > 1) keys.push(nk);
  }
  keys.sort(function (a, b) { return b.length - a.length; });
  var esc = function (s) { return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); };
  var big = keys.length ? new RegExp(keys.map(esc).join('|'), 'g') : null;
  var DIGITS = '٠١٢٣٤٥٦٧٨٩';

  function finish(s) {
    return s
      .replace(/[٠-٩]/g, function (d) { return String(DIGITS.indexOf(d)); })
      .replace(/٬/g, ',').replace(/٫/g, '.').replace(/،/g, ',').replace(/؛/g, ';').replace(/؟/g, '?')
      .replace(/ م²/g, ' m²').replace(/م²/g, 'm²')
      .replace(/(\d)\s*م(?=$|[\s.,;:)×·])/g, '$1 m');
  }
  // Arrows point the other way when the page reads left to right.
  function flip(s) { return s.replace(/[←→]/g, function (a) { return a === '←' ? '→' : '←'; }); }
  function tr(s) {
    if (!s || !AR.test(s)) return s;
    var lead = s.match(/^\s*/)[0], tail = s.match(/\s*$/)[0];
    var n = norm(s);
    if (exact[n] !== undefined) return lead + flip(exact[n]) + tail;
    var N = '([0-9٠-٩٬٫,.]+)';
    n = n.replace(new RegExp('وحدة مضمومة من (.+?) تُعرض كوحدة واحدة\\.', 'g'), function (m, a) { return 'Combined unit made of ' + a.split(/ و(?=[A-Z])/).join(', ') + ', offered as one unit.'; })
      .replace(new RegExp('المساحة المحملة ' + N + ' م² والصافي داخل حدود الوحدة ' + N + ' م²\\.', 'g'), 'Loaded area $1 m², net area inside the unit $2 m².')
      .replace(new RegExp('لها تراس خارجي على البلازا مساحته ' + N + ' م² غير محسوب في المساحة المحملة\\.', 'g'), 'It has an outdoor terrace on the plaza of $1 m², not counted in the loaded area.');
    if (exact[n] !== undefined) return lead + flip(exact[n]) + tail;
    var out = big ? n.replace(big, function (m) { return exact[m]; }) : n;
    return lead + flip(finish(out)) + tail;
  }
  window.HP_tr = tr;

  var SKIP = { SCRIPT: 1, STYLE: 1, NOSCRIPT: 1, TEXTAREA: 1 };
  var ATTRS = ['aria-label', 'title', 'placeholder', 'alt', 'content', 'data-title'];

  function doText(node) {
    var p = node.parentNode;
    if (!p || SKIP[p.nodeName] || (p.closest && p.closest('[data-no-i18n]'))) return;
    var v = node.nodeValue;
    if (AR.test(v)) { var t = tr(v); if (t !== v) node.nodeValue = t; }
  }
  function doEl(el) {
    if (SKIP[el.nodeName] || (el.closest && el.closest('[data-no-i18n]'))) return;
    for (var i = 0; i < ATTRS.length; i++) {
      var a = el.getAttribute && el.getAttribute(ATTRS[i]);
      if (a && AR.test(a)) { var t = tr(a); if (t !== a) el.setAttribute(ATTRS[i], t); }
    }
    if (el.getAttribute && el.getAttribute('dir') === 'rtl') el.setAttribute('dir', 'ltr');
  }
  function walk(n) {
    if (n.nodeType === 3) { doText(n); return; }
    if (n.nodeType !== 1) return;
    doEl(n);
    var w = document.createTreeWalker(n, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT);
    var c;
    while ((c = w.nextNode())) { if (c.nodeType === 3) doText(c); else doEl(c); }
  }

  var mo = new MutationObserver(function (list) {
    for (var i = 0; i < list.length; i++) {
      var m = list[i];
      if (m.type === 'characterData') doText(m.target);
      else if (m.type === 'attributes') doEl(m.target);
      else for (var j = 0; j < m.addedNodes.length; j++) walk(m.addedNodes[j]);
    }
    if (AR.test(document.title)) { var tt = tr(document.title); if (tt !== document.title) document.title = tt; }
  });
  mo.observe(root, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ATTRS.concat(['dir']) });
  if (document.body) walk(document.body);
  document.addEventListener('DOMContentLoaded', function () { walk(document.documentElement); });
})();
