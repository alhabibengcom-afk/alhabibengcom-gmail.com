"""Shared helpers for driving ETABS and SAFE (CSI OAPI) from Python on Windows.

Both programs expose the same object model (SapModel, DatabaseTables, LoadPatterns, RespCombo, PointObj ...),
so ETABS and SAFE share this module. Everything that depends on a table name is resolved by searching the tables
the program itself lists (GetAvailableTables), so version differences in names do not break the scripts.
"""
import os
import re
import sys

KN_M_C = 6  # eUnits.kN_m_C

PROGRAMS = {
    "ETABS": ("ETABSv1.Helper", "ETABSv1", "CSI.ETABS.API.ETABSObject"),
    "SAFE": ("SAFEv1.Helper", "SAFEv1", "CSI.SAFE.API.ETABSObject"),
}

# eLoadPatternType values (CSI OAPI)
PATTERN_TYPE = {"dead": 1, "super dead": 2, "superdead": 2, "live": 3, "reducelive": 4, "quake": 5, "seismic": 5,
                "wind": 6, "snow": 7, "other": 8}


class CSI:
    def __init__(self, program, path=None, attach=False, visible=False):
        try:
            import comtypes.client
        except ImportError:
            sys.exit("pip install comtypes  (Windows, with ETABS/SAFE installed)")
        helper_id, gen_name, obj_id = PROGRAMS[program]
        helper = comtypes.client.CreateObject(helper_id)
        gen = __import__(f"comtypes.gen.{gen_name}", fromlist=["cHelper"])
        helper = helper.QueryInterface(gen.cHelper)
        self.program = program
        self.started = False
        if attach:
            try:
                self.obj = helper.GetObject(obj_id)
            except Exception:
                sys.exit(f"No running {program} to attach to. Open the model or pass the file path.")
        else:
            self.obj = helper.CreateObjectProgID(obj_id)
            self.obj.ApplicationStart()
            self.started = True
            if not visible:
                try:
                    self.obj.Hide()
                except Exception:
                    pass
        self.m = self.obj.SapModel
        if not attach:
            self.m.InitializeNewModel()
            ret = self.m.File.OpenFile(os.path.abspath(path))
            if ret != 0:
                self.close()
                sys.exit(f"{program} could not open {path} (return code {ret}).")
        self.m.SetPresentUnits(KN_M_C)

    # ------------------------------------------------------------ basics
    def close(self, save=False):
        if self.started:
            try:
                self.obj.ApplicationExit(bool(save))
            except Exception:
                pass

    def filename(self):
        try:
            return self.m.GetModelFilename(True)
        except Exception:
            return None

    def save_as(self, path):
        ret = self.m.File.Save(os.path.abspath(path))
        if ret != 0:
            raise RuntimeError(f"Save failed ({ret})")

    def has_results(self):
        try:
            r = self.m.Analyze.GetCaseStatus()
            status = [p for p in r if isinstance(p, (list, tuple))][-1]
            return any(s == 4 for s in status)
        except Exception:
            return False

    def run(self):
        ret = self.m.Analyze.RunAnalysis()
        if ret != 0:
            raise RuntimeError(f"RunAnalysis returned {ret}")

    @staticmethod
    def _names(r):
        for part in (r if isinstance(r, (list, tuple)) else []):
            if isinstance(part, (list, tuple)) and (not part or isinstance(part[0], str)):
                return list(part)
        return []

    def patterns(self):
        return self._names(self.m.LoadPatterns.GetNameList())

    def combos(self):
        return self._names(self.m.RespCombo.GetNameList())

    # ------------------------------------------------------------ tables
    def available_tables(self):
        try:
            r = list(self.m.DatabaseTables.GetAvailableTables())
            lists = [p for p in r if isinstance(p, (list, tuple))]
            return list(lists[0]) if lists else []
        except Exception:
            return []

    def find_table(self, *patterns_, avoid=()):
        """First available table whose key matches all regex patterns (case-insensitive)."""
        keys = self.available_tables()
        for k in keys:
            if all(re.search(p, k, re.I) for p in patterns_) and not any(re.search(x, k, re.I) for x in avoid):
                return k
        return None

    def table(self, key, cases=None, combos=None):
        DT = self.m.DatabaseTables
        try:
            if cases is not None:
                DT.SetLoadCasesSelectedForDisplay(cases)
            if combos is not None:
                DT.SetLoadCombinationsSelectedForDisplay(combos)
        except Exception:
            pass
        r = list(DT.GetTableForDisplayArray(key, [], "All", 0, [], 0, []))
        if r[-1] != 0:
            return None, None
        lists = [p for p in r[:-1] if isinstance(p, (list, tuple))]
        if len(lists) < 2:
            return [], []
        fields, data = list(lists[-2]), list(lists[-1])
        n = len(fields) or 1
        return fields, [data[i:i + n] for i in range(0, len(data), n)]

    # ------------------------------------------------------------ edits (used by --fix)
    def add_pattern(self, name, typ, selfwt=0.0):
        t = PATTERN_TYPE.get(typ.lower(), 8)
        return self.m.LoadPatterns.Add(name, t, float(selfwt), True)

    def set_selfweight(self, name, mult):
        return self.m.LoadPatterns.SetSelfWTMultiplier(name, float(mult))

    def restrain(self, label, story):
        r = self.m.PointObj.GetNameFromLabel(label, story)
        uname = next((p for p in (r if isinstance(r, (list, tuple)) else []) if isinstance(p, str)), None)
        if not uname:
            return -1
        res = self.m.PointObj.SetRestraint(uname, [True] * 6)
        return res[-1] if isinstance(res, (list, tuple)) else res

    def add_combo(self, name, items):
        ret = self.m.RespCombo.Add(name, 0)  # 0 = linear additive
        for case, sf in items:
            self.m.RespCombo.SetCaseList(name, 0, case, float(sf))  # 0 = load case
        return ret


def write_xlsx(tables, path):
    import openpyxl
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    used = set()
    for key, (fields, rows) in tables.items():
        title = re.sub(r"[\[\]\*\?/\\:]", "", key)[:31]
        while title in used:
            title = title[:29] + str(len(used))
        used.add(title)
        ws = wb.create_sheet(title)
        ws.append([f"TABLE:  {key}"])
        ws.append(list(fields))
        for r in rows:
            ws.append([_num(v) for v in r])
    wb.save(path)


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return v


def text_model_file(base, exts):
    c = [base + e for e in exts if os.path.exists(base + e)]
    return max(c, key=os.path.getmtime) if c else None
