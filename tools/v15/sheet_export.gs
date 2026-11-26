/**
 * Happiness Plaza: public read-only export of the unit data the website needs.
 * Paste into the sheet (Extensions > Apps Script), then Deploy > New deployment >
 * Web app, Execute as: Me, Who has access: Anyone. Send the web app URL to the site team.
 *
 * Only these columns leave the sheet: unit, floor, section, loaded and net area,
 * status, marketing channel, components, unit type, zoning, and the optional
 * columns "المرحلة" and "الواجهة الزجاج م". Owner names, rents and negotiation
 * notes are never exported.
 */
function doGet() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName('الوحدات');
  var rows = sh.getDataRange().getValues();
  var head = rows.shift().map(function (h) { return String(h).trim(); });
  var col = function (name) { return head.indexOf(name); };
  var keep = {
    id: col('الوحدة'), floor: col('الدور'), section: col('القسم'), area: col('المساحة المحملة م²'),
    net: col('المساحة الصافي م²'), status: col('الحالة'), channel: col('قناة التسويق'),
    parts: col('المكونات'), type: col('نوع الوحدة'), zoning: col('النشاط (الزوننج)'),
    phase: col('المرحلة'), glass: col('الواجهة الزجاج م')
  };
  var units = [];
  rows.forEach(function (r) {
    if (String(r[keep.section]).trim() !== 'تجاري' || !r[keep.id]) return;
    var u = {};
    Object.keys(keep).forEach(function (k) { if (keep[k] >= 0) u[k] = r[keep[k]]; });
    units.push(u);
  });
  var out = { updated: new Date().toISOString(), units: units };
  return ContentService.createTextOutput(JSON.stringify(out)).setMimeType(ContentService.MimeType.JSON);
}
