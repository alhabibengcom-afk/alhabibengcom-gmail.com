#!/usr/bin/env python3
"""Al-Habeeb company & factory "brain": memory, problem monitoring, root-cause dossiers and one final decision.

Data lives in BRAIN_DIR (default ./brain-data, git-ignored: company data must never go to a public repository).

  brain.py init
  brain.py ingest FILE [FILE...] --area "المصنع/الإنتاج" [--tags "خط 2,صيانة"] [--date 2026-11-20]
           (pdf, docx, xlsx, csv, txt, md, json; images: describe them in chat and use 'note')
  brain.py note "نص المعلومة" --area "الشركة/المشتريات" [--source "اجتماع 20/11"]
  brain.py search "سبب تأخير التوريد" [--area X] [-n 10]
  brain.py scan [--area X] [--add N]          problem signals clustered by area and category
  brain.py issue add --title "..." --area X --category time|cost|quality|safety|supply|people|contract|technical|other
                     --impact 1-5 --likelihood 1-5 --urgency 1-5 [--owner] [--evidence "S0003,N0012"]
  brain.py issue list [--area X] [--status open]      brain.py issue update ID --status ... [--note ...]
  brain.py prioritize                          score = impact x likelihood x urgency, Pareto by category
  brain.py analyze ID                          root-cause dossier (evidence, 5 whys, fishbone, data gaps) -> decisions/
  brain.py decide ID --options options.xlsx [--weights "cost:0.25,time:0.2,risk:0.2,feasibility:0.15,impact:0.2"]
                                               weighted matrix + sensitivity -> ONE final decision + action plan
  brain.py action ID --what "..." --owner "..." --due 2026-12-10 [--kpi "..."]   brain.py action-done ID N
  brain.py report [--days 7] [-o report.md]    status: knowledge, new signals, top issues, decisions, late actions
  brain.py export -o brain.xlsx                everything in one workbook for sharing
"""
import argparse
import datetime as dt
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
from collections import Counter, defaultdict

BRAIN = os.environ.get("BRAIN_DIR", os.path.join(os.getcwd(), "brain-data"))
TODAY = dt.date.today().isoformat()

# ------------------------------------------------------------------ Arabic-aware text handling
AR_DIAC = re.compile(r"[ؗ-ًؚ-ْٰـ]")


def norm(s):
    s = AR_DIAC.sub("", str(s or ""))
    s = re.sub("[إأآٱ]", "ا", s)
    s = s.replace("ى", "ي").replace("ة", "ه").replace("ؤ", "و").replace("ئ", "ي")
    s = s.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
    return s.lower()


STOP = set(norm(w) for w in "في من على الى إلى عن مع هذا هذه ذلك التي الذي ان أن او أو و ثم لا ما هو هي كان تم ال the of and to in for on a an is are by with at".split())
PREFIX = ("وال", "بال", "كال", "فال", "لل", "ال", "و")


def tokens(s):
    out = []
    for w in re.findall(r"[\w؀-ۿ]+", norm(s)):
        for p in PREFIX:
            if w.startswith(p) and len(w) - len(p) >= 3:
                w = w[len(p):]
                break
        if len(w) > 4 and w.endswith(("ات", "ون", "ين")):
            w = w[:-2]
        if w not in STOP and len(w) > 1:
            out.append(w)
    return out


# problem lexicon: category -> words (Arabic + English); matched on normalized tokens / substrings
LEXICON = {
    "time": ["تاخير", "تأخير", "متاخر", "متأخر", "تاخر", "تأخر", "تعطل التنفيذ", "توقف العمل", "مهله", "delay", "late", "overdue", "behind schedule"],
    "cost": ["تجاوز", "زياده التكلفه", "خساره", "عجز", "غرامه", "خصم", "هدر", "فاقد", "تكلفه اضافيه", "over budget", "overrun", "penalty", "loss", "waste"],
    "quality": ["رفض", "مرفوض", "عيب", "عيوب", "مرتجع", "مرتجعات", "عدم مطابقه", "شكوي", "شكاوي", "اعاده تنفيذ", "تشريخ", "تسريب", "ncr", "defect", "reject", "rework", "complaint"],
    "technical": ["عطل", "اعطال", "توقف الماكينه", "كسر", "انهيار", "تعارض", "خطا في اللوحه", "خطا تصميم", "breakdown", "failure", "clash", "design error"],
    "safety": ["اصابه", "حادث", "حريق", "خطر", "سقوط", "injury", "accident", "unsafe", "near miss"],
    "supply": ["نقص", "نفاد", "نفذ المخزون", "عدم توفر", "تاخر التوريد", "مورد", "shortage", "stock out", "supplier late"],
    "people": ["غياب", "استقاله", "نقص العماله", "تسرب", "ضغط الشغل", "خلاف", "absence", "resignation", "turnover"],
    "contract": ["نزاع", "مطالبه", "اخطار", "انذار", "اوامر تغييريه", "مستخلص متاخر", "claim", "dispute", "variation", "notice"],
}
LEX_N = {c: [norm(w) for w in ws] for c, ws in LEXICON.items()}
CATS = list(LEXICON) + ["other"]


# ------------------------------------------------------------------ storage
def path(*p):
    return os.path.join(BRAIN, *p)


def load(name, default):
    f = path(name)
    if os.path.exists(f):
        with open(f, encoding="utf-8") as fh:
            return json.load(fh)
    return default


def save(name, data):
    os.makedirs(BRAIN, exist_ok=True)
    tmp = path(name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, path(name))


def need_init():
    if not os.path.exists(path("sources.json")):
        sys.exit(f"Brain not initialised in {BRAIN}: run 'brain.py init' (or set BRAIN_DIR)")


def cmd_init(a):
    for d in ("sources", "files", "decisions"):
        os.makedirs(path(d), exist_ok=True)
    for name, default in (("sources.json", []), ("notes.json", []), ("issues.json", [])):
        if not os.path.exists(path(name)):
            save(name, default)
    gi = os.path.join(os.path.dirname(os.path.abspath(BRAIN)), ".gitignore")
    entry = os.path.basename(os.path.abspath(BRAIN)) + "/"
    try:
        lines = open(gi, encoding="utf-8").read().splitlines() if os.path.exists(gi) else []
        if entry not in lines:
            with open(gi, "a", encoding="utf-8") as fh:
                fh.write(("\n" if lines and lines[-1] else "") + entry + "\n")
    except OSError:
        pass
    print(f"Brain ready in {BRAIN} (git-ignored: {entry})")


# ------------------------------------------------------------------ ingest
def extract(fp):
    ext = os.path.splitext(fp)[1].lower()
    if ext == ".pdf":
        try:
            out = subprocess.run(["pdftotext", "-layout", fp, "-"], capture_output=True, text=True, timeout=300).stdout
            if out.strip():
                return out
        except Exception:
            pass
        from pypdf import PdfReader
        return "\n".join((p.extract_text() or "") for p in PdfReader(fp).pages)
    if ext == ".docx":
        import docx
        d = docx.Document(fp)
        parts = [p.text for p in d.paragraphs]
        for t in d.tables:
            for r in t.rows:
                parts.append(" | ".join(c.text for c in r.cells))
        return "\n".join(parts)
    if ext in (".xlsx", ".xlsm"):
        import openpyxl
        wb = openpyxl.load_workbook(fp, data_only=True, read_only=True)
        parts = []
        for ws in wb.worksheets:
            parts.append(f"## {ws.title}")
            for r in ws.iter_rows(values_only=True):
                if any(v not in (None, "") for v in r):
                    parts.append(" | ".join("" if v is None else str(v) for v in r))
        return "\n".join(parts)
    if ext in (".txt", ".md", ".csv", ".json", ".log"):
        return open(fp, encoding="utf-8", errors="replace").read()
    raise ValueError(f"unsupported type {ext} (images: describe them in chat and save with 'note')")


def cmd_ingest(a):
    need_init()
    src = load("sources.json", [])
    known = {s["sha1"] for s in src}
    for fp in a.files:
        data = open(fp, "rb").read()
        sha = hashlib.sha1(data).hexdigest()
        if sha in known:
            print(f"skip (already ingested): {fp}")
            continue
        try:
            txt = extract(fp)
        except Exception as e:
            print(f"FAILED {fp}: {e}")
            continue
        sid = f"S{len(src) + 1:04d}"
        with open(path("sources", sid + ".txt"), "w", encoding="utf-8") as fh:
            fh.write(txt)
        shutil.copy2(fp, path("files", sid + "_" + os.path.basename(fp)))
        src.append({"id": sid, "file": os.path.basename(fp), "area": a.area, "tags": a.tags or "", "date": a.date or TODAY,
                    "added": TODAY, "chars": len(txt), "sha1": sha})
        known.add(sha)
        print(f"{sid}: {os.path.basename(fp)} ({len(txt):,} chars) -> {a.area}")
        if len(txt.strip()) < 50:
            print("   ! almost no text extracted (scanned PDF?) - send the pages as images in chat")
    save("sources.json", src)


def cmd_note(a):
    need_init()
    notes = load("notes.json", [])
    nid = f"N{len(notes) + 1:04d}"
    notes.append({"id": nid, "text": a.text, "area": a.area, "source": a.source or "", "date": a.date or TODAY,
                  "added": TODAY})
    save("notes.json", notes)
    print(f"{nid} saved ({a.area})")


# ------------------------------------------------------------------ search (BM25 over chunks)
def chunks():
    out = []
    for s in load("sources.json", []):
        try:
            txt = open(path("sources", s["id"] + ".txt"), encoding="utf-8").read()
        except OSError:
            continue
        paras = re.split(r"\n\s*\n|\n(?=##)", txt)
        buf, k = "", 0
        for p in paras:
            if len(buf) + len(p) > 900 and buf:
                out.append({"ref": f"{s['id']}#{k}", "src": s, "text": buf})
                k += 1
                buf = ""
            buf += p + "\n"
        if buf.strip():
            out.append({"ref": f"{s['id']}#{k}", "src": s, "text": buf})
    for n in load("notes.json", []):
        out.append({"ref": n["id"], "src": {"id": n["id"], "file": "note: " + n.get("source", ""), "area": n["area"],
                                            "date": n["date"]}, "text": n["text"]})
    return out


def search(q, area=None, n=10):
    docs = [c for c in chunks() if not area or norm(area) in norm(c["src"].get("area", ""))]
    if not docs:
        return []
    toks = [tokens(d["text"]) for d in docs]
    N = len(docs)
    avg = sum(map(len, toks)) / N or 1
    df = Counter(t for ts in toks for t in set(ts))
    qt = tokens(q)
    res = []
    for d, ts in zip(docs, toks):
        tf = Counter(ts)
        s = 0.0
        for t in qt:
            if tf[t]:
                idf = math.log(1 + (N - df[t] + 0.5) / (df[t] + 0.5))
                s += idf * tf[t] * 2.2 / (tf[t] + 1.2 * (0.25 + 0.75 * len(ts) / avg))
        if norm(q) in norm(d["text"]):
            s += 3
        if s > 0:
            res.append((s, d))
    res.sort(key=lambda x: -x[0])
    return res[:n]


def snippet(text, q, width=220):
    t = " ".join(text.split())
    nt = norm(t)
    pos = min([nt.find(w) for w in tokens(q) if nt.find(w) >= 0] or [0])
    s = max(pos - width // 3, 0)
    return ("…" if s else "") + t[s:s + width] + ("…" if s + width < len(t) else "")


def cmd_search(a):
    need_init()
    res = search(a.query, a.area, a.n)
    if not res:
        print("No match. Try other words (synonyms, Arabic/English), or ingest more sources.")
    for s, d in res:
        src = d["src"]
        print(f"[{d['ref']}] {src.get('file')} | {src.get('area')} | {src.get('date')} | score {s:.1f}\n   {snippet(d['text'], a.query)}")


# ------------------------------------------------------------------ scan for problem signals
def signals(area=None, since=None):
    hits = []
    for d in chunks():
        src = d["src"]
        if area and norm(area) not in norm(src.get("area", "")):
            continue
        if since and str(src.get("date", "")) < since:
            continue
        t = norm(d["text"])
        for cat, words in LEX_N.items():
            found = [w for w in words if w in t]
            if found:
                hits.append({"cat": cat, "area": src.get("area", ""), "ref": d["ref"], "words": found,
                             "snip": snippet(d["text"], " ".join(found)), "date": src.get("date", "")})
    return hits


def cmd_scan(a):
    need_init()
    hits = signals(a.area)
    groups = defaultdict(list)
    for h in hits:
        groups[(h["area"], h["cat"])].append(h)
    ranked = sorted(groups.items(), key=lambda kv: -len(kv[1]))
    print(f"{len(hits)} problem signals in {len(groups)} area/category groups")
    for (area, cat), hs in ranked[:25]:
        w = Counter(x for h in hs for x in h["words"]).most_common(4)
        print(f"- {area} / {cat}: {len(hs)} signals; words: {', '.join(f'{k}({v})' for k, v in w)}")
        for h in hs[:3]:
            print(f"     [{h['ref']}] {h['snip'][:160]}")
    if a.add:
        issues = load("issues.json", [])
        for (area, cat), hs in ranked[:a.add]:
            iid = f"P{len(issues) + 1:03d}"
            top = Counter(x for h in hs for x in h["words"]).most_common(2)
            issues.append({"id": iid, "title": f"{cat}: {', '.join(k for k, _ in top)} ({area})", "area": area,
                           "category": cat, "impact": 3, "likelihood": min(5, 1 + len(hs) // 3), "urgency": 3,
                           "owner": "", "status": "draft", "evidence": [h["ref"] for h in hs[:10]], "opened": TODAY,
                           "log": [f"{TODAY} created by scan from {len(hs)} signals - review scores"], "actions": []})
            print(f"  + {iid} draft issue")
        save("issues.json", issues)


# ------------------------------------------------------------------ issues
def score(i):
    return int(i.get("impact", 0)) * int(i.get("likelihood", 0)) * int(i.get("urgency", 0))


def cmd_issue(a):
    need_init()
    issues = load("issues.json", [])
    if a.op == "add":
        iid = f"P{len(issues) + 1:03d}"
        issues.append({"id": iid, "title": a.title, "area": a.area, "category": a.category, "impact": a.impact,
                       "likelihood": a.likelihood, "urgency": a.urgency, "owner": a.owner or "", "status": "open",
                       "evidence": [e.strip() for e in (a.evidence or "").split(",") if e.strip()], "opened": TODAY,
                       "log": [f"{TODAY} opened"], "actions": []})
        save("issues.json", issues)
        print(f"{iid} added, score {a.impact * a.likelihood * a.urgency}")
    elif a.op == "list":
        for i in sorted(issues, key=lambda i: -score(i)):
            if a.area and norm(a.area) not in norm(i["area"]):
                continue
            if a.status and i["status"] != a.status:
                continue
            print(f"{i['id']} [{i['status']}] score {score(i):3d} | {i['area']} | {i['category']} | {i['title']}"
                  + (f" | owner {i['owner']}" if i.get("owner") else ""))
    elif a.op == "update":
        i = next((x for x in issues if x["id"] == a.id), None)
        if not i:
            sys.exit(f"{a.id} not found")
        for k in ("status", "owner", "impact", "likelihood", "urgency", "title"):
            v = getattr(a, k, None)
            if v not in (None, ""):
                i[k] = v
        if a.evidence:
            i["evidence"] += [e.strip() for e in a.evidence.split(",") if e.strip()]
        i["log"].append(f"{TODAY} update" + (f": {a.note}" if a.note else ""))
        save("issues.json", issues)
        print(f"{a.id} updated, score {score(i)}")


def cmd_prioritize(a):
    need_init()
    issues = [i for i in load("issues.json", []) if i["status"] not in ("closed", "rejected")]
    issues.sort(key=lambda i: -score(i))
    tot = sum(score(i) for i in issues) or 1
    print("Priority (impact x likelihood x urgency, max 125):")
    run = 0
    for i in issues:
        run += score(i)
        print(f"  {i['id']} {score(i):3d}  cum {run / tot * 100:4.0f}%  {i['area']} / {i['category']}: {i['title']}")
    by = Counter()
    for i in issues:
        by[i["category"]] += score(i)
    print("Pareto by category: " + ", ".join(f"{c} {v / tot * 100:.0f}%" for c, v in by.most_common()))


# ------------------------------------------------------------------ analysis dossier
FISHBONE = ["الأفراد (People)", "الطريقة والإجراءات (Method/Process)", "المعدات والماكينات (Machine)",
            "الخامات والتوريد (Material/Supply)", "القياس والبيانات (Measurement)", "البيئة والموقع (Environment)",
            "الإدارة والتعاقد (Management/Contract)"]


def cmd_analyze(a):
    need_init()
    issues = load("issues.json", [])
    i = next((x for x in issues if x["id"] == a.id), None)
    if not i:
        sys.exit(f"{a.id} not found")
    ev = []
    allc = {c["ref"]: c for c in chunks()}
    for r in i.get("evidence", []):
        c = allc.get(r) or next((v for k, v in allc.items() if k.startswith(r + "#")), None)
        if c:
            ev.append((r, c))
    rel = search(i["title"], None, 12)
    L = [f"# ملف تحليل {i['id']} — {i['title']}", "",
         f"- الإدارة/الفرع: {i['area']} — النوع: {i['category']} — الأولوية: {score(i)}/125 "
         f"(أثر {i['impact']} × احتمال {i['likelihood']} × إلحاح {i['urgency']}) — المسؤول: {i.get('owner') or '—'}",
         f"- تاريخ الفتح: {i['opened']} — الحالة: {i['status']}", "",
         "## 1. الأدلة المسجلة"]
    for r, c in ev:
        L.append(f"- [{r}] {c['src'].get('file')} ({c['src'].get('date')}): {snippet(c['text'], i['title'], 300)}")
    if not ev:
        L.append("- لا توجد أدلة مربوطة — اربط مصادر بـ `issue update --evidence`.")
    L += ["", "## 2. معلومات مرتبطة من الذاكرة (بحث تلقائي)"]
    for s, c in rel:
        if any(c["ref"] == e or c["ref"].startswith(e + "#") for e in i.get("evidence", [])):
            continue
        L.append(f"- [{c['ref']}] {c['src'].get('area')} | {c['src'].get('file')}: {snippet(c['text'], i['title'], 220)}")
    L += ["", "## 3. توصيف المشكلة (حقائق فقط، كل حقيقة بمصدرها)",
          "- ماذا يحدث؟ أين؟ متى بدأ؟ كم مرة؟ ما الأثر بالأرقام (وقت/تكلفة/جودة/سلامة)؟", "",
          "## 4. لماذا؟ (5 Whys — كل إجابة بدليل)"] + [f"{k}. لماذا …؟ ← … [دليل]" for k in range(1, 6)] + [
          "", "## 5. عظمة السمكة (الأسباب المحتملة لكل محور — مؤكد/محتمل/مستبعد)"] + [f"- {f}: …" for f in FISHBONE] + [
          "", "## 6. السبب الجذري", "- السبب الجذري المرجّح: … (درجة الثقة: عالية/متوسطة/منخفضة، ولماذا)", "",
          "## 7. فجوات البيانات (لازم تتجاب قبل القرار)", "- …", "",
          "## 8. البحث العميق", "- داخلي: …", "- خارجي (معايير، أفضل ممارسات، موردين، حالات مشابهة — بالمصادر والروابط): …", "",
          "## 9. البدائل", "- اكتب البدائل في ملف options.xlsx وشغّل `brain.py decide " + i["id"] + " --options options.xlsx`."]
    os.makedirs(path("decisions"), exist_ok=True)
    out = path("decisions", f"{i['id']}-analysis.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    i["status"] = "analyzing" if i["status"] in ("open", "draft") else i["status"]
    i["log"].append(f"{TODAY} analysis dossier created")
    save("issues.json", issues)
    print(f"Dossier: {out}  ({len(ev)} linked evidence, {len(rel)} related chunks)")


# ------------------------------------------------------------------ decision
DEFAULT_W = "cost:0.25,time:0.20,risk:0.20,feasibility:0.15,impact:0.20"


def cmd_decide(a):
    need_init()
    import openpyxl
    issues = load("issues.json", [])
    i = next((x for x in issues if x["id"] == a.id), None)
    if not i:
        sys.exit(f"{a.id} not found")
    W = {k.strip(): float(v) for k, v in (p.split(":") for p in a.weights.split(","))}
    s = sum(W.values())
    W = {k: v / s for k, v in W.items()}
    ws = openpyxl.load_workbook(a.options, data_only=True).active
    hdr = [str(c.value or "").strip().lower() for c in ws[1]]
    opts = []
    for r in ws.iter_rows(min_row=2, values_only=True):
        if not r or not r[0]:
            continue
        d = dict(zip(hdr, r))
        sc = {k: float(d.get(k) or 0) for k in W}
        opts.append({"name": str(r[0]), "scores": sc, "desc": d.get("description") or d.get("الوصف") or "",
                     "cost_egp": d.get("cost egp") or d.get("التكلفة") or "", "duration": d.get("duration") or d.get("المدة") or ""})
    if len(opts) < 2:
        sys.exit("Need at least 2 options (rows) with scores 1-5 per criterion: " + ", ".join(W))
    for o in opts:
        o["total"] = sum(o["scores"][k] * w for k, w in W.items())
    opts.sort(key=lambda o: -o["total"])
    best = opts[0]
    # sensitivity: shift each weight by +/-0.10 (renormalised); does the winner change?
    flips = []
    for k in W:
        for dlt in (-0.10, 0.10):
            w2 = dict(W)
            w2[k] = max(0.0, w2[k] + dlt)
            t = sum(w2.values())
            w2 = {kk: v / t for kk, v in w2.items()}
            win = max(opts, key=lambda o: sum(o["scores"][kk] * ww for kk, ww in w2.items()))
            if win["name"] != best["name"]:
                flips.append(f"{k} {dlt:+.2f} -> {win['name']}")
    margin = best["total"] - opts[1]["total"]
    robust = "ثابت" if not flips else "حساس للأوزان"
    print(f"Decision for {i['id']}: {best['name']} (score {best['total']:.2f}/5, margin {margin:.2f} over "
          f"{opts[1]['name']}) - {robust}" + (f"; flips: {', '.join(flips)}" if flips else ""))
    for o in opts:
        print(f"   {o['total']:.2f}  {o['name']}  " + "  ".join(f"{k}={o['scores'][k]:g}" for k in W))
    L = [f"# القرار النهائي — {i['id']} — {i['title']}", "", f"**القرار: {best['name']}**", "",
         f"- الدرجة {best['total']:.2f} من 5، بفارق {margin:.2f} عن البديل التالي ({opts[1]['name']}).",
         f"- ثبات القرار: {robust}" + (f" (يتغير لو: {'; '.join(flips)})" if flips else " — لا يتغير بتحريك أي وزن ±0.10."),
         f"- الأوزان: " + ", ".join(f"{k} {v:.2f}" for k, v in W.items()), "", "## مقارنة البدائل", "",
         "| البديل | " + " | ".join(W) + " | الإجمالي |", "|---|" + "---|" * (len(W) + 1)]
    for o in opts:
        L.append(f"| {o['name']} | " + " | ".join(f"{o['scores'][k]:g}" for k in W) + f" | {o['total']:.2f} |")
    L += ["", "## لماذا هذا الحل (من ملف التحليل)", "- …", "", "## المخاطر والاحتياطات", "- …", "",
          "## خطة التنفيذ", "| # | الإجراء | المسؤول | الميعاد | مؤشر النجاح |", "|---|---|---|---|---|", "",
          "## متى نراجع القرار", "- لو مؤشر النجاح ما اتحققش في الميعاد، أو ظهرت معلومة تغيّر درجات البدائل."]
    out = path("decisions", f"{i['id']}-decision.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    i["status"] = "decided"
    i["decision"] = {"option": best["name"], "score": round(best["total"], 2), "margin": round(margin, 2),
                     "robust": not flips, "date": TODAY}
    i["log"].append(f"{TODAY} decided: {best['name']}")
    save("issues.json", issues)
    print(f"-> {out} (complete the 'why', risks and action plan; add actions with 'brain.py action')")


def cmd_action(a):
    need_init()
    issues = load("issues.json", [])
    i = next((x for x in issues if x["id"] == a.id), None)
    if not i:
        sys.exit(f"{a.id} not found")
    i.setdefault("actions", []).append({"what": a.what, "owner": a.owner, "due": a.due, "kpi": a.kpi or "", "done": None})
    i["status"] = "in progress" if i["status"] == "decided" else i["status"]
    save("issues.json", issues)
    print(f"{a.id}: action {len(i['actions'])} added")


def cmd_action_done(a):
    need_init()
    issues = load("issues.json", [])
    i = next((x for x in issues if x["id"] == a.id), None)
    i["actions"][a.n - 1]["done"] = TODAY
    if all(x.get("done") for x in i["actions"]):
        i["status"] = "verify"
        i["log"].append(f"{TODAY} all actions done - verify the KPI before closing")
    save("issues.json", issues)
    print(f"{a.id}: action {a.n} done; status {i['status']}")


# ------------------------------------------------------------------ report / export
def cmd_report(a):
    need_init()
    since = (dt.date.today() - dt.timedelta(days=a.days)).isoformat()
    src, notes, issues = load("sources.json", []), load("notes.json", []), load("issues.json", [])
    by_area = Counter(s["area"] for s in src) + Counter(n["area"] for n in notes)
    new_sig = signals(None, since)
    L = [f"# تقرير الـ Brain — {TODAY}", "", "## الذاكرة",
         f"- مصادر: {len(src)} ملف، {len(notes)} ملاحظة. حسب الإدارة: " + "، ".join(f"{k} {v}" for k, v in by_area.most_common()),
         "", f"## إشارات مشاكل جديدة آخر {a.days} يوم: {len(new_sig)}"]
    g = Counter((h["area"], h["cat"]) for h in new_sig)
    for (ar, c), n in g.most_common(10):
        L.append(f"- {ar} / {c}: {n}")
    act = [i for i in issues if i["status"] not in ("closed", "rejected")]
    act.sort(key=lambda i: -score(i))
    L += ["", "## أهم المشاكل المفتوحة", "", "| المشكلة | الإدارة | النوع | الأولوية | الحالة | القرار |", "|---|---|---|---|---|---|"]
    for i in act[:12]:
        L.append(f"| {i['id']} {i['title'][:50]} | {i['area']} | {i['category']} | {score(i)} | {i['status']} | "
                 f"{(i.get('decision') or {}).get('option', '—')} |")
    late = [(i, k, x) for i in issues for k, x in enumerate(i.get("actions", []), 1)
            if not x.get("done") and x.get("due") and x["due"] < TODAY]
    L += ["", "## إجراءات متأخرة"]
    L += [f"- {i['id']} إجراء {k}: {x['what']} — {x['owner']} — كان {x['due']}" for i, k, x in late] or ["- لا يوجد"]
    stale = [i for i in act if i["status"] in ("open", "draft") and i["opened"] < since]
    if stale:
        L += ["", "## مشاكل مفتوحة من غير تحليل أكتر من المدة"] + [f"- {i['id']} {i['title']}" for i in stale]
    md = "\n".join(L) + "\n"
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(md)
        print(f"-> {a.out}")
    else:
        print(md)


def cmd_export(a):
    need_init()
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Issues"
    ws.append(["ID", "Title", "Area", "Category", "Impact", "Likelihood", "Urgency", "Score", "Status", "Owner",
               "Decision", "Evidence", "Opened"])
    for i in sorted(load("issues.json", []), key=lambda i: -score(i)):
        ws.append([i["id"], i["title"], i["area"], i["category"], i["impact"], i["likelihood"], i["urgency"], score(i),
                   i["status"], i.get("owner"), (i.get("decision") or {}).get("option"), ", ".join(i.get("evidence", [])),
                   i["opened"]])
    w2 = wb.create_sheet("Actions")
    w2.append(["Issue", "#", "Action", "Owner", "Due", "KPI", "Done"])
    for i in load("issues.json", []):
        for k, x in enumerate(i.get("actions", []), 1):
            w2.append([i["id"], k, x["what"], x["owner"], x["due"], x["kpi"], x.get("done")])
    w3 = wb.create_sheet("Sources")
    w3.append(["ID", "File", "Area", "Tags", "Date", "Chars"])
    for s in load("sources.json", []):
        w3.append([s["id"], s["file"], s["area"], s["tags"], s["date"], s["chars"]])
    w4 = wb.create_sheet("Notes")
    w4.append(["ID", "Area", "Date", "Source", "Text"])
    for n in load("notes.json", []):
        w4.append([n["id"], n["area"], n["date"], n["source"], n["text"]])
    wb.save(a.out)
    print(f"-> {a.out}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = p.add_subparsers(dest="cmd", required=True)
    s.add_parser("init").set_defaults(fn=cmd_init)
    x = s.add_parser("ingest"); x.add_argument("files", nargs="+"); x.add_argument("--area", required=True)
    x.add_argument("--tags"); x.add_argument("--date"); x.set_defaults(fn=cmd_ingest)
    x = s.add_parser("note"); x.add_argument("text"); x.add_argument("--area", required=True); x.add_argument("--source")
    x.add_argument("--date"); x.set_defaults(fn=cmd_note)
    x = s.add_parser("search"); x.add_argument("query"); x.add_argument("--area"); x.add_argument("-n", type=int, default=10)
    x.set_defaults(fn=cmd_search)
    x = s.add_parser("scan"); x.add_argument("--area"); x.add_argument("--add", type=int, default=0); x.set_defaults(fn=cmd_scan)
    x = s.add_parser("issue"); x.add_argument("op", choices=["add", "list", "update"]); x.add_argument("id", nargs="?")
    x.add_argument("--title"); x.add_argument("--area"); x.add_argument("--category", choices=CATS)
    for k in ("impact", "likelihood", "urgency"):
        x.add_argument(f"--{k}", type=int, choices=range(1, 6))
    x.add_argument("--owner"); x.add_argument("--evidence"); x.add_argument("--status"); x.add_argument("--note")
    x.set_defaults(fn=cmd_issue)
    s.add_parser("prioritize").set_defaults(fn=cmd_prioritize)
    x = s.add_parser("analyze"); x.add_argument("id"); x.set_defaults(fn=cmd_analyze)
    x = s.add_parser("decide"); x.add_argument("id"); x.add_argument("--options", required=True)
    x.add_argument("--weights", default=DEFAULT_W); x.set_defaults(fn=cmd_decide)
    x = s.add_parser("action"); x.add_argument("id"); x.add_argument("--what", required=True); x.add_argument("--owner", required=True)
    x.add_argument("--due", required=True); x.add_argument("--kpi"); x.set_defaults(fn=cmd_action)
    x = s.add_parser("action-done"); x.add_argument("id"); x.add_argument("n", type=int); x.set_defaults(fn=cmd_action_done)
    x = s.add_parser("report"); x.add_argument("--days", type=int, default=7); x.add_argument("-o", "--out"); x.set_defaults(fn=cmd_report)
    x = s.add_parser("export"); x.add_argument("-o", "--out", required=True); x.set_defaults(fn=cmd_export)
    a = p.parse_args()
    if a.cmd == "issue" and a.op == "add" and not (a.title and a.area and a.category and a.impact and a.likelihood and a.urgency):
        sys.exit("issue add needs --title --area --category --impact --likelihood --urgency")
    if a.cmd == "issue" and a.op == "update" and not a.id:
        sys.exit("issue update needs an ID")
    a.fn(a)


if __name__ == "__main__":
    main()
