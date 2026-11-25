/* Happiness Plaza brand guide: one-screen launcher.
   The home screen is the looping site film with the main buttons. Each button
   opens only its own part of the guide, with a bar to go back home.
   Routing stays in site.js; this file only decides which sections are shown. */
(function () {
  var GROUPS = {
    owner: ['owner'],
    why: ['why'],
    location: ['location', 'film'],
    goal: ['goal'],
    phase: ['stages', 'phase', 'phase-scenes', 'lake', 'rooms'],
    market: ['market'],
    plans: ['units-list', 'atlas', 'sitevideo', 'hyper'],
    leasing: ['facilities', 'handover', 'deals'],
    contact: ['contact']
  };
  var TITLES = {
    owner: 'مين المالك؟', why: 'ليه قنا والصعيد؟', location: 'الموقع والمميزات', goal: 'هدفنا',
    phase: 'المرحلة الأولى', market: 'مراحل التشغيل', plans: 'الوحدات المتاحة والمخططات', leasing: 'التسليم والتعاقد',
    contact: 'احجز معاينة'
  };
  if (window.HP_LITE) {
    GROUPS.phase = ['stages', 'phase']; GROUPS.location = ['location', 'film']; GROUPS.plans = ['units-list', 'atlas', 'sitevideo', 'hyper'];
    TITLES.owner = 'المالك والمطوّر'; TITLES.why = 'لماذا قنا وصعيد مصر؟'; TITLES.contact = 'تواصل مع فريق التأجير'; TITLES.plans = 'الوحدات المتاحة والمخططات'; TITLES.market = 'مراحل التشغيل';
  }
  var main = document.getElementById('mainpage');
  var bar = document.querySelector('.hp-backbar');
  var barTitle = bar && bar.querySelector('.hp-backbar-title');

  function route() {
    if (typeof currentRoute === 'function') return currentRoute();
    return decodeURIComponent(location.hash.slice(1));
  }
  function groupOf(id) {
    for (var g in GROUPS) if (GROUPS[g].indexOf(id) >= 0) return g;
    return null;
  }
  function sectionOf(id) {
    var el = id && document.getElementById(id);
    if (!el) return null;
    var s = el.closest('#mainpage > section');
    return s ? s.id : null;
  }
  function apply() {
    var r = route();
    var body = document.body;
    if (r.indexOf('unit/') === 0) {
      var known = typeof byId === 'undefined' || byId.get(r.slice(5));
      if (known) { body.setAttribute('data-view', 'unit'); return; }
      r = '';
    }
    var target = null, g = null;
    if (r.indexOf('plan/') === 0) { g = 'plans'; target = 'atlas'; }
    else if (r && r !== 'home') {
      target = r;
      g = groupOf(r) || groupOf(sectionOf(r));
    }
    if (!g) {
      body.setAttribute('data-view', 'home');
      main.querySelectorAll(':scope > section').forEach(function (s) { s.classList.toggle('hp-on', s.id === 'home'); });
      return;
    }
    body.setAttribute('data-view', 'section');
    var ids = GROUPS[g];
    main.querySelectorAll(':scope > section').forEach(function (s) { s.classList.toggle('hp-on', ids.indexOf(s.id) >= 0); });
    if (barTitle) barTitle.textContent = window.HP_tr ? window.HP_tr(TITLES[g]) : TITLES[g];
    var el = document.getElementById(target) || document.getElementById(ids[0]);
    var first = document.getElementById(ids[0]);
    var dest = (el && el.closest('#mainpage > section') === first) ? first : el;
    if (dest) requestAnimationFrame(function () { dest.scrollIntoView({ behavior: 'instant', block: 'start' }); });
  }
  ['pushState', 'replaceState'].forEach(function (k) {
    var orig = history[k];
    history[k] = function () { var out = orig.apply(this, arguments); apply(); return out; };
  });
  window.addEventListener('popstate', apply);
  window.addEventListener('hashchange', apply);
  apply();
})();
