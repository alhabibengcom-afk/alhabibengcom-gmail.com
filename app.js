/* Happiness Plaza as an app: install button, and screen mode for TVs and display screens (?screen=1).
   Screen mode plays the guide by itself: each section in turn (both phases floor by floor), scrolling slowly. */
(function () {
  window.sheetLink = function () { return null; };  // old unit sheets are not published
  var lite = !!window.HP_LITE, base = lite ? 'lite.html' : './';
  var en = window.HP_LANG === 'en';
  var tr = function (a, e) { return en ? e : a; };

  // Install
  var deferred = null;
  addEventListener('beforeinstallprompt', function (e) { e.preventDefault(); deferred = e; });
  document.addEventListener('click', function (e) {
    var b = e.target.closest('.hp-install');
    if (!b) return;
    e.preventDefault();
    if (deferred) { deferred.prompt(); deferred.userChoice.then(function () { deferred = null; }); return; }
    var ios = /iphone|ipad|ipod/i.test(navigator.userAgent);
    alert(ios ? tr('من Safari: اضغط زر المشاركة ثم «إضافة إلى الشاشة الرئيسية».', 'In Safari: tap Share, then “Add to Home Screen”.')
              : tr('من قائمة المتصفح اختر «تثبيت التطبيق» أو «إضافة إلى الشاشة الرئيسية».', 'From the browser menu choose “Install app” or “Add to Home screen”.'));
  });
  if (matchMedia('(display-mode: standalone)').matches) document.documentElement.classList.add('hp-installed');

  // Screen mode
  var q = new URLSearchParams(location.search);
  if (q.get('screen') !== '1') return;
  var root = document.documentElement;
  root.classList.add('hp-screen');
  var dur = Math.max(6, +q.get('sec') || 14) * 1000;
  var steps = ['home', 'owner', 'why', 'location', 'goal', 'phase', 'stages', 'phase2:g', 'phase2:f1',
               'phase3:b1', 'phase3:g', 'phase3:f1', 'phase3:f2', 'units-list', 'contact'];
  var i = 0, timer = null, anim = null;
  var bar = document.createElement('div'); bar.className = 'hp-sbar'; bar.innerHTML = '<i></i>';
  var hint = document.createElement('button'); hint.className = 'hp-shint'; hint.type = 'button';
  hint.textContent = tr('اضغط للعرض بملء الشاشة · Esc للخروج', 'Tap for full screen · Esc to exit');
  document.body.append(bar, hint);
  function scrollSlow() {
    cancelAnimationFrame(anim);
    var start = performance.now() + 2200, from = scrollY, to = Math.max(0, root.scrollHeight - innerHeight);
    (function step(t) {
      var k = Math.min(1, Math.max(0, (t - start) / (dur - 3200)));
      scrollTo(0, from + (to - from) * k);
      if (k < 1) anim = requestAnimationFrame(step);
    })(performance.now());
  }
  function go() {
    var s = steps[i % steps.length].split(':'); i++;
    var id = s[0], tab = s[1];
    if (('#' + id) !== location.hash) location.hash = '#' + id;
    setTimeout(function () {
      if (tab) {
        var b = document.querySelector('#' + id + ' .hp-ptab[data-pfloor="' + (id === 'phase2' ? 'p2' : 'p3') + '-' + tab + '"]');
        if (b) b.click();
      }
      if (id !== 'home') scrollSlow(); else scrollTo(0, 0);
    }, 800);
    var fill = bar.firstChild; fill.style.transition = 'none'; fill.style.width = '0';
    requestAnimationFrame(function () { fill.style.transition = 'width ' + dur + 'ms linear'; fill.style.width = '100%'; });
    timer = setTimeout(go, dur);
  }
  hint.addEventListener('click', function () {
    if (root.requestFullscreen) root.requestFullscreen().catch(function () {});
    hint.remove();
  });
  addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !document.fullscreenElement) location.href = base + (en ? '?lang=en' : '');
    if (e.key === 'ArrowLeft' || e.key === 'ArrowRight' || e.key === ' ') { clearTimeout(timer); go(); }
  });
  var idle; addEventListener('mousemove', function () { root.classList.remove('hp-sidle'); clearTimeout(idle); idle = setTimeout(function () { root.classList.add('hp-sidle'); }, 2500); });
  setTimeout(go, 600);
})();
