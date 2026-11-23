#!/usr/bin/env python3
"""Technical-office master tracker (Al-Habeeb): one workbook for every register, with ageing, overdue flags and a
live dashboard, plus a weekly report generated from it.

  python3 tracker.py create  --project "Happiness Plaza" --code HPZ -o HPZ_tracker.xlsx
  python3 tracker.py report  HPZ_tracker.xlsx [--date 2026-11-23] [-o weekly.md] [--xlsx weekly.xlsx]
  python3 tracker.py check   HPZ_tracker.xlsx          (data problems: missing dates, duplicate refs, bad status)

Registers (one sheet each, same core columns so the dashboard and report treat them alike):
  DWG   Drawings received (from consultant)     SD   Shop drawings submitted
  MS    Material submittals                      RFI  Requests for information
  LTR   Letters in/out                           NCR  Non-conformance reports
  VO    Variations / claims                      IPC  Interim payment certificates (main + subcontractors)
  PR    Purchase requests to procurement         TSK  Team tasks
Core columns: Ref | Title | Discipline | Responsible | Date sent/opened | Due date | Date closed | Status | Rev |
              Days open (formula) | Overdue (formula) | Linked refs | Remarks
Statuses: Open, Submitted, Under review, A - Approved, B - Approved as noted, C - Revise & resubmit,
          D - Rejected, Answered, Closed, Cancelled
Response time defaults (days, editable on the Settings sheet): SD 14, MS 14, RFI 7, LTR 7, NCR 14, VO 30, IPC 30,
PR 7, DWG 7, TSK 7.
"""
import argparse
import datetime as dt
import os
import re
import sys
from collections import Counter, defaultdict

REGISTERS = [  # code, sheet title, Arabic title, default response days, extra columns
    ("DWG", "Drawings", "اللوحات الواردة من الاستشاري", 7, ["Drawing No.", "Issued for"]),
    ("SD", "Shop drawings", "الرسومات التنفيذية المقدمة", 14, ["Drawing No.", "Consultant code"]),
    ("MS", "Material submittals", "اعتمادات الخامات", 14, ["Item / BOQ ref", "Supplier"]),
    ("RFI", "RFIs", "الاستفسارات الفنية", 7, ["Question summary", "Impact (cost/time)"]),
    ("LTR", "Letters", "المراسلات", 7, ["Direction (In/Out)", "From/To"]),
    ("NCR", "NCRs", "تقارير عدم المطابقة", 14, ["Location", "Corrective action"]),
    ("VO", "Variations", "الأوامر التغييرية والمطالبات", 30, ["Value (EGP)", "Time impact (days)"]),
    ("IPC", "IPCs", "المستخلصات", 30, ["Party (client/subcontractor)", "Amount (EGP)"]),
    ("PR", "Purchase requests", "طلبات الشراء", 7, ["Materials", "Required on site"]),
    ("TSK", "Team tasks", "مهام الفريق", 7, ["Priority (1-3)", "Output"]),
]
CORE = ["Ref", "Title", "Discipline", "Responsible", "Date sent/opened", "Due date", "Date closed", "Status", "Rev"]
TAIL = ["Days open", "Overdue", "Linked refs", "Remarks"]
STATUSES = ["Open", "Submitted", "Under review", "A - Approved", "B - Approved as noted", "C - Revise & resubmit",
            "D - Rejected", "Answered", "Closed", "Cancelled"]
CLOSED = {"A - Approved", "B - Approved as noted", "D - Rejected", "Answered", "Closed", "Cancelled"}
DISCIPLINES = ["AR", "ST", "PT", "EL", "HV", "WS", "DR", "FF", "FA", "LC", "GN", "QS", "PL"]


def create(a):
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.formatting.rule import FormulaRule
    from openpyxl.worksheet.datavalidation import DataValidation
    wb = openpyxl.Workbook()
    hdr_fill = PatternFill("solid", fgColor="1F3864")
    hdr_font = Font(bold=True, color="FFFFFF")
    red = PatternFill("solid", fgColor="F8CBAD")
    green = PatternFill("solid", fgColor="C6E0B4")
    amber = PatternFill("solid", fgColor="FFE699")

    # Settings
    st = wb.active
    st.title = "Settings"
    st.append(["Project", a.project])
    st.append(["Project code", a.code])
    st.append(["Report date (blank = today)", None])
    st.append([])
    st.append(["Register", "Sheet", "Arabic", "Response days"])
    for code, title, ar, days, _ in REGISTERS:
        st.append([code, title, ar, days])
    st.append([])
    st.append(["Statuses"])
    for s_ in STATUSES:
        st.append([s_])
    st.append([])
    st.append(["Disciplines"])
    for d in DISCIPLINES:
        st.append([d])
    st.column_dimensions["A"].width = 28
    st.column_dimensions["B"].width = 22
    st.column_dimensions["C"].width = 34
    status_first = 5 + len(REGISTERS) + 3
    status_rng = f"Settings!$A${status_first}:$A${status_first + len(STATUSES) - 1}"
    disc_first = status_first + len(STATUSES) + 2
    disc_rng = f"Settings!$A${disc_first}:$A${disc_first + len(DISCIPLINES) - 1}"
    today = 'IF(Settings!$B$3="",TODAY(),Settings!$B$3)'
    closed_list = ",".join(f'"{c}"' for c in CLOSED)

    for i, (code, title, ar, days, extra) in enumerate(REGISTERS):
        ws = wb.create_sheet(title)
        cols = CORE + extra + TAIL
        ws.append(cols)
        for c in ws[1]:
            c.fill, c.font = hdr_fill, hdr_font
            c.alignment = Alignment(wrap_text=True, vertical="center")
        ws.freeze_panes = "B2"
        L = {name: openpyxl.utils.get_column_letter(k + 1) for k, name in enumerate(cols)}
        n = a.rows
        days_cell = f"Settings!$D${6 + i}"
        for r in range(2, n + 2):
            ws[f"{L['Due date']}{r}"] = (f'=IF({L["Date sent/opened"]}{r}="","",{L["Date sent/opened"]}{r}+{days_cell})')
            ws[f"{L['Days open']}{r}"] = (f'=IF({L["Date sent/opened"]}{r}="","",IF({L["Date closed"]}{r}<>"",'
                                          f'{L["Date closed"]}{r},{today})-{L["Date sent/opened"]}{r})')
            ws[f"{L['Overdue']}{r}"] = (f'=IF(OR({L["Date sent/opened"]}{r}="",{L["Date closed"]}{r}<>"",'
                                        f'OR({L["Status"]}{r}={{{closed_list}}})),"",IF({today}>{L["Due date"]}{r},'
                                        f'"OVERDUE",""))')
            for k in ("Date sent/opened", "Due date", "Date closed"):
                ws[f"{L[k]}{r}"].number_format = "yyyy-mm-dd"
        dv = DataValidation(type="list", formula1=f"={status_rng}", allow_blank=True)
        dv.add(f"{L['Status']}2:{L['Status']}{n + 1}")
        dv2 = DataValidation(type="list", formula1=f"={disc_rng}", allow_blank=True)
        dv2.add(f"{L['Discipline']}2:{L['Discipline']}{n + 1}")
        ws.add_data_validation(dv)
        ws.add_data_validation(dv2)
        rng = f"A2:{L['Remarks']}{n + 1}"
        ws.conditional_formatting.add(rng, FormulaRule(formula=[f'${L["Overdue"]}2="OVERDUE"'], fill=red))
        ws.conditional_formatting.add(rng, FormulaRule(formula=[f'OR(${L["Status"]}2="A - Approved",'
                                                                 f'${L["Status"]}2="Closed",${L["Status"]}2="Answered")'],
                                                       fill=green))
        ws.conditional_formatting.add(rng, FormulaRule(formula=[f'OR(${L["Status"]}2="C - Revise & resubmit",'
                                                                 f'${L["Status"]}2="D - Rejected")'], fill=amber))
        widths = {"Ref": 14, "Title": 40, "Remarks": 40, "Linked refs": 16}
        for name, col in L.items():
            ws.column_dimensions[col].width = widths.get(name, 15)
        ws.auto_filter.ref = f"A1:{L['Remarks']}{n + 1}"
        ws.sheet_view.rightToLeft = False

    # Dashboard
    db = wb.create_sheet("Dashboard", 0)
    db["A1"] = f"Technical office dashboard - {a.project}"
    db["A1"].font = Font(bold=True, size=14)
    db["A2"] = "Report date"
    db["B2"] = f"={today}"
    db["B2"].number_format = "yyyy-mm-dd"
    head = ["Register", "Arabic", "Total", "Open", "Overdue", "Approved A/B", "Revise C", "Rejected D",
            "First-time approval %", "Avg days to close"]
    db.append([])
    db.append(head)
    for c in db[4]:
        c.fill, c.font = hdr_fill, hdr_font
    for i, (code, title, ar, days, extra) in enumerate(REGISTERS):
        cols = CORE + extra + TAIL
        L = {name: openpyxl.utils.get_column_letter(k + 1) for k, name in enumerate(cols)}
        sh = f"'{title}'"
        ref, stc = f"{sh}!${L['Ref']}$2:${L['Ref']}${a.rows + 1}", f"{sh}!${L['Status']}$2:${L['Status']}${a.rows + 1}"
        ov = f"{sh}!${L['Overdue']}$2:${L['Overdue']}${a.rows + 1}"
        rv = f"{sh}!${L['Rev']}$2:${L['Rev']}${a.rows + 1}"
        dop = f"{sh}!${L['Days open']}$2:${L['Days open']}${a.rows + 1}"
        dcl = f"{sh}!${L['Date closed']}$2:${L['Date closed']}${a.rows + 1}"
        r = 5 + i
        db.append([code, ar,
                   f'=COUNTA({ref})',
                   f'=SUMPRODUCT(({ref}<>"")*({dcl}="")*ISNA(MATCH({stc},{{{closed_list}}},0)))',
                   f'=COUNTIF({ov},"OVERDUE")',
                   f'=COUNTIF({stc},"A - Approved")+COUNTIF({stc},"B - Approved as noted")',
                   f'=COUNTIF({stc},"C - Revise & resubmit")',
                   f'=COUNTIF({stc},"D - Rejected")',
                   f'=IFERROR((COUNTIFS({stc},"A - Approved",{rv},0)+COUNTIFS({stc},"B - Approved as noted",{rv},0))'
                   f'/(F{r}+G{r}+H{r}),"")',
                   f'=IFERROR(AVERAGEIFS({dop},{dcl},"<>"),"")'])
        db[f"I{r}"].number_format = "0%"
        db[f"J{r}"].number_format = "0.0"
    db.conditional_formatting.add(f"E5:E{4 + len(REGISTERS)}",
                                  FormulaRule(formula=["E5>0"], fill=red))
    for col, w in zip("ABCDEFGHIJ", (10, 30, 8, 8, 10, 13, 10, 11, 18, 16)):
        db.column_dimensions[col].width = w
    db.append([])
    db.append(["Rules: due date = opened + response days (Settings). Overdue = open past due date. "
               "First-time approval = A/B at Rev 0 / all decided."])
    wb.save(a.out)
    print(f"Created {a.out}: {len(REGISTERS)} registers x {a.rows} rows, dashboard, settings")


# ------------------------------------------------------------------ reading
def load(path):
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=False)
    settings = {}
    days = {}
    st = wb["Settings"]
    for row in st.iter_rows(values_only=True):
        if row and row[0] in ("Project", "Project code"):
            settings[row[0]] = row[1]
        if row and row[0] == "Report date (blank = today)":
            settings["date"] = row[1]
        if row and len(row) >= 4 and row[0] in {r[0] for r in REGISTERS} and isinstance(row[3], (int, float)):
            days[row[0]] = row[3]
    regs = {}
    for code, title, ar, d, extra in REGISTERS:
        if title not in wb.sheetnames:
            continue
        ws = wb[title]
        hdr = [c.value for c in ws[1]]
        items = []
        for row in ws.iter_rows(min_row=2, values_only=True):
            rec = dict(zip(hdr, row))
            if not rec.get("Ref") and not rec.get("Title"):
                continue
            items.append(rec)
        regs[code] = {"title": title, "ar": ar, "days": days.get(code, d), "items": items}
    return settings, regs


def as_date(v):
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    if isinstance(v, str):
        try:
            return dt.date.fromisoformat(v.strip()[:10])
        except ValueError:
            return None
    return None


def evaluate(regs, today):
    """Recompute days open / due / overdue in Python (formulas are not evaluated by openpyxl)."""
    for code, R in regs.items():
        for it in R["items"]:
            op = as_date(it.get("Date sent/opened"))
            cl = as_date(it.get("Date closed"))
            due = as_date(it.get("Due date")) if not str(it.get("Due date") or "").startswith("=") else None
            if op and not due:
                due = op + dt.timedelta(days=R["days"])
            st = str(it.get("Status") or "").strip()
            closed = bool(cl) or st in CLOSED
            it["_open"], it["_closed"], it["_due"], it["_status"] = op, closed, due, st
            it["_days"] = ((cl or today) - op).days if op else None
            it["_overdue"] = bool(op and not closed and due and today > due)
            it["_late_by"] = (today - due).days if it["_overdue"] else 0
            try:
                it["_rev"] = int(str(it.get("Rev") or 0).strip().lstrip("Rr") or 0)
            except ValueError:
                it["_rev"] = 0


def kpis(regs):
    out = {}
    for code, R in regs.items():
        its = R["items"]
        decided = [i for i in its if i["_status"] in ("A - Approved", "B - Approved as noted", "C - Revise & resubmit",
                                                    "D - Rejected")]
        first = [i for i in decided if i["_status"] in ("A - Approved", "B - Approved as noted") and i["_rev"] == 0]
        closed_days = [i["_days"] for i in its if i["_closed"] and i["_days"] is not None]
        out[code] = {"total": len(its), "open": sum(1 for i in its if not i["_closed"]),
                     "overdue": sum(1 for i in its if i["_overdue"]),
                     "first_time": (len(first) / len(decided)) if decided else None,
                     "avg_close": (sum(closed_days) / len(closed_days)) if closed_days else None,
                     "resubmit": sum(1 for i in its if i["_status"] == "C - Revise & resubmit")}
    return out


def report(a):
    settings, regs = load(a.tracker)
    today = as_date(a.date) if a.date else (as_date(settings.get("date")) or dt.date.today())
    evaluate(regs, today)
    K = kpis(regs)
    week_ago = today - dt.timedelta(days=7)
    proj = settings.get("Project", "")
    L = [f"# التقرير الأسبوعي للمكتب الفني — {proj}", f"تاريخ التقرير: {today.isoformat()}", ""]
    tot_over = sum(k["overdue"] for k in K.values())
    tot_open = sum(k["open"] for k in K.values())
    L += ["## الملخص", f"- بنود مفتوحة: **{tot_open}** — متأخرة عن ميعاد الرد: **{tot_over}**."]
    worst = sorted(((i["_late_by"], code, i) for code, R in regs.items() for i in R["items"] if i["_overdue"]),
                   key=lambda x: -x[0])[:5]
    if worst:
        L.append("- أخطر التأخيرات: " + "؛ ".join(f"{i.get('Ref')} ({regs[c]['ar']}) متأخر {d} يوم" for d, c, i in worst))
    L += ["", "## مؤشرات الأداء", "",
          "| السجل | الإجمالي | مفتوح | متأخر | اعتماد من أول مرة | متوسط أيام الإغلاق | مطلوب إعادة تقديم |",
          "|---|---|---|---|---|---|---|"]
    for code, k in K.items():
        if not k["total"]:
            continue
        ft = f"{k['first_time']*100:.0f}%" if k["first_time"] is not None else "—"
        ac = f"{k['avg_close']:.1f}" if k["avg_close"] is not None else "—"
        L.append(f"| {regs[code]['ar']} ({code}) | {k['total']} | {k['open']} | {k['overdue']} | {ft} | {ac} | {k['resubmit']} |")
    L += ["", "## حركة الأسبوع"]
    for code, R in regs.items():
        new = [i for i in R["items"] if i["_open"] and i["_open"] > week_ago]
        done = [i for i in R["items"] if as_date(i.get("Date closed")) and as_date(i.get("Date closed")) > week_ago]
        if new or done:
            L.append(f"- {R['ar']}: جديد {len(new)}، اتقفل {len(done)}"
                     + (" — " + "، ".join(f"{i.get('Ref')} {i['_status']}" for i in done[:6]) if done else ""))
    L += ["", "## البنود المتأخرة (لازم متابعة)", "", "| المرجع | السجل | العنوان | المسؤول | الحالة | متأخر (يوم) |",
          "|---|---|---|---|---|---|"]
    for d, c, i in sorted(((i["_late_by"], code, i) for code, R in regs.items() for i in R["items"] if i["_overdue"]),
                          key=lambda x: -x[0]):
        L.append(f"| {i.get('Ref')} | {c} | {str(i.get('Title') or '')[:50]} | {i.get('Responsible') or '—'} | "
                 f"{i['_status'] or 'Open'} | {d} |")
    L += ["", "## حمل الشغل على الفريق (بنود مفتوحة لكل مسؤول)"]
    load_ = Counter(i.get("Responsible") or "غير محدد" for R in regs.values() for i in R["items"] if not i["_closed"])
    for who, n in load_.most_common():
        over = sum(1 for R in regs.values() for i in R["items"] if i["_overdue"] and (i.get("Responsible") or "غير محدد") == who)
        L.append(f"- {who}: {n} مفتوح" + (f" ({over} متأخر)" if over else ""))
    def base(ref):
        return re.sub(r"[-_ ]?(rev|r)\s*\d+$", "", str(ref or ""), flags=re.I)
    latest = {}
    for c, R in regs.items():
        for i in R["items"]:
            k = (c, base(i.get("Ref")))
            if k not in latest or i["_rev"] >= latest[k]["_rev"]:
                latest[k] = i
    # returned items whose latest revision is still C/D = resubmission not done yet
    rej = [(c, i) for (c, _), i in latest.items() if i["_status"] in ("C - Revise & resubmit", "D - Rejected")]
    if rej:
        L += ["", "## مرفوض / إعادة تقديم (محتاج تصحيح وإعادة تقديم)"]
        for c, i in rej:
            L.append(f"- {i.get('Ref')} ({c}) Rev {i['_rev']}: {str(i.get('Title') or '')[:60]} — {i.get('Remarks') or ''}")
    L += ["", "## الأسبوع الجاي",
          "- تقفيل البنود المتأخرة بالترتيب أعلاه (الأقدم أولاً) — خطاب تذكير للاستشاري لكل بند متأخر عنده.",
          "- إعادة تقديم المرفوض بعد تصحيح الملاحظات.",
          "- بنود ميعاد ردها خلال 7 أيام:"]
    soon = [(i["_due"], c, i) for c, R in regs.items() for i in R["items"]
            if not i["_closed"] and i["_due"] and today <= i["_due"] <= today + dt.timedelta(days=7)]
    for due, c, i in sorted(soon, key=lambda x: x[0]):
        L.append(f"  - {i.get('Ref')} ({c}) — {due.isoformat()} — {i.get('Responsible') or '—'}")
    md = "\n".join(L) + "\n"
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"Wrote {a.out}")
    else:
        print(md)
    if a.xlsx:
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "KPIs"
        ws.append(["Register", "Total", "Open", "Overdue", "First-time approval", "Avg days to close", "Resubmit"])
        for code, k in K.items():
            ws.append([code, k["total"], k["open"], k["overdue"],
                       round(k["first_time"], 3) if k["first_time"] is not None else None,
                       round(k["avg_close"], 1) if k["avg_close"] is not None else None, k["resubmit"]])
        ws2 = wb.create_sheet("Overdue")
        ws2.append(["Ref", "Register", "Title", "Responsible", "Status", "Due", "Days late"])
        for d, c, i in sorted(((i["_late_by"], code, i) for code, R in regs.items() for i in R["items"] if i["_overdue"]),
                              key=lambda x: -x[0]):
            ws2.append([i.get("Ref"), c, i.get("Title"), i.get("Responsible"), i["_status"],
                        i["_due"].isoformat() if i["_due"] else None, d])
        wb.save(a.xlsx)
        print(f"Wrote {a.xlsx}")


def check(a):
    settings, regs = load(a.tracker)
    evaluate(regs, dt.date.today())
    issues = []
    for code, R in regs.items():
        seen = Counter(str(i.get("Ref")).strip() for i in R["items"] if i.get("Ref"))
        for ref, n in seen.items():
            if n > 1 and not re.search(r"rev|r\d", ref, re.I):
                issues.append(f"{code}: duplicate reference {ref} ({n} rows) - use the Rev column for resubmissions")
        for i in R["items"]:
            ref = i.get("Ref") or "(no ref)"
            if not i.get("Ref"):
                issues.append(f"{code}: row '{str(i.get('Title'))[:40]}' has no reference number")
            if not i["_open"]:
                issues.append(f"{code} {ref}: no sent/opened date - ageing cannot be tracked")
            if i["_status"] and i["_status"] not in STATUSES:
                issues.append(f"{code} {ref}: status '{i['_status']}' not in the standard list")
            if i["_closed"] and not as_date(i.get("Date closed")) and i["_status"] not in ("Cancelled",):
                issues.append(f"{code} {ref}: status {i['_status']} but no closing date")
            if not i.get("Responsible") and not i["_closed"]:
                issues.append(f"{code} {ref}: open item without a responsible engineer")
    print(f"{len(issues)} data issue(s)")
    for x in issues:
        print(" - " + x)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("create")
    x.add_argument("--project", required=True)
    x.add_argument("--code", required=True)
    x.add_argument("--rows", type=int, default=300)
    x.add_argument("-o", "--out", required=True)
    x.set_defaults(fn=create)
    x = s.add_parser("report")
    x.add_argument("tracker")
    x.add_argument("--date")
    x.add_argument("-o", "--out")
    x.add_argument("--xlsx")
    x.set_defaults(fn=report)
    x = s.add_parser("check")
    x.add_argument("tracker")
    x.set_defaults(fn=check)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
