/* Happiness Plaza: phase sections. Floor tabs, and table rows that light their unit on the plan. */
(function () {
  document.addEventListener('click', function (e) {
    var b = e.target.closest('.hp-ptab');
    if (!b) return;
    var sec = b.closest('.hp-phase'), id = b.getAttribute('data-pfloor');
    sec.querySelectorAll('.hp-ptab').forEach(function (x) { var on = x === b; x.classList.toggle('on', on); x.setAttribute('aria-pressed', String(on)); });
    sec.querySelectorAll('.hp-ppanel').forEach(function (p) { p.classList.toggle('on', p.getAttribute('data-ppanel') === id); });
  });
  function lit(e, on) {
    var r = e.target.closest && e.target.closest('.hp-ptable tr[data-unit]');
    if (!r) return;
    var panel = r.closest('.hp-ppanel'), u = r.getAttribute('data-unit');
    panel.querySelectorAll('.hp-pu[data-unit="' + u + '"]').forEach(function (p) { p.classList.toggle('lit', on); });
  }
  document.addEventListener('mouseover', function (e) { lit(e, true); });
  document.addEventListener('mouseout', function (e) { lit(e, false); });
})();
