---
name: alhabeeb-model-reader
description: Read structural analysis models from ETABS, SAFE and ADAPT (ADAPT-Builder / ADAPT-PT) directly from their exported files - without the programs' printed design reports - then review the model, extract design forces (column loads, base reactions, beam moments), compute concrete and formwork quantities, and feed the forces into the office's ECP 203 calculator (Egyptian codes/ecp203) to design footings, rafts, columns and beams. Use it whenever the user sends or mentions an ETABS/SAFE/ADAPT model or export (.e2k, .$et, .f2k, .s2k, .$2k, exported Excel/CSV tables, .EDB/.FDB/.ADB files), asks to check or review a model, wants column loads or reactions out of a model, wants footings designed from ETABS reactions, or wants quantities from a model - even if they just say "الموديل" or "ملف الإيتابس".
---

# Model reader - ETABS / SAFE / ADAPT

Gets data out of analysis models as files, not as printed reports, and turns it into checks, tables, quantities and ECP 203 designs.

## Answering rules

- Reply in the user's language. For Arabic, use Egyptian Arabic with the technical term in English between brackets (same as the other Al-Habeeb skills).
- Report in kN, kN·m, m, mm, N/mm². The script converts the model's units; still say which units the file was in.
- The binary model files (`.EDB` ETABS, `.FDB` SAFE, `.ADB` ADAPT-Builder) are closed formats: they cannot be read here. If the user sends one, explain this kindly and give them the export steps from `references/export-guide.md` (it takes under a minute in the program). Never guess the contents of a binary file.
- Every number you report should be traceable to the file: name the table/section and the element label and story.
- Design checks and code values belong to the existing tools: run `Egyptian codes/ecp203` for designs and use the `egyptian-codes` skill for code clauses. Don't hard-code ECP values in your answer from memory.
- ETABS concrete strength is cylinder f'c; ECP 203 uses cube fcu (≈ f'c / 0.8). Always state which one you are using when passing fcu to ecp203.

## Tool

`scripts/model_reader.py` (Python standard library + openpyxl for .xlsx). Run `python3 scripts/model_reader.py -h`.

| Command | Input | Output |
|---|---|---|
| `summary model.e2k` | ETABS text model | stories, materials, sections, slabs/walls, load patterns, combinations, object counts |
| `review model.e2k` | ETABS text model | findings ranked HIGH / MEDIUM / CHECK |
| `quantities model.e2k --xlsx q.xlsx` | ETABS text model | concrete m³ and formwork m² by story and element (Detail + Summary sheets) |
| `tables FILE --list` / `--table NAME --csv DIR` | SAFE/SAP `.f2k/.s2k`, any Excel/CSV export (ETABS, SAFE, ADAPT) | list of tables, rows, CSV per table |
| `footings --model m.e2k --reactions r.xlsx --q-allow Q [--raft]` | model + Joint Reactions table | ecp203 JSON: one isolated footing per column, or one raft |
| `columns --model m.e2k --forces f.xlsx --combos U1,U2 [--group]` | model + Element Forces - Columns | ecp203 JSON for columns |
| `beams --model m.e2k --forces f.xlsx --combos U1,U2 [--group]` | model + Element Forces - Beams | ecp203 JSON for beams |

Then design: `cd "Egyptian codes" && python3 -m ecp203 <file>.json -o reports/<name>.md`. Exit code 1 means at least one element is not safe: report which and why, don't hide it.

## Workflow

### 1. Identify what you got
- `.e2k` / `.$et` → ETABS model text: use `summary`, `review`, `quantities`.
- `.f2k` / `.s2k` / `.$2k` → SAFE or SAP2000 text database: use `tables --list` and read the relevant tables (point coordinates, slab properties, loads, soil springs).
- `.xlsx` / `.csv` → exported tables: `tables --list` first to see what's inside.
- ADAPT → its exported tables (Excel/CSV) or text output: `tables --list`, then map the columns by hand (formats differ between ADAPT versions; read the headers, don't assume). Post-tensioned slabs follow ACI 318-19 in the office (`Egyptian codes/aci318`), not ECP 203.
- Binary `.EDB/.FDB/.ADB` or a PDF report only → ask for the export (see guide).

### 2. Review the model
Run `review`, then add engineering judgement the script can't do:
- Loads: finishes/partitions (SDL) values, live load by occupancy (ECP 201), wall line loads on beams, stair and water tank loads.
- Seismic/wind: present when required; mass source definition.
- Stiffness modifiers for cracked sections; diaphragms; supports (fixed vs pinned) matching the foundation concept.
- Section sizes against the architectural drawings.
Present findings as: (1) errors that change results, (2) items to verify, (3) remarks.

### 3. Extract design forces
Ask for (or read) the exported tables: Joint Reactions, Element Forces - Columns / Beams, Story Drifts, Base Reactions, Modal Participating Mass Ratios. Use `tables` to read them and present clean tables. Typical checks: total base reaction vs total applied gravity load (should match within ~1-2 %), drift limits, modal mass ≥ 90 % (verify limits with the code).

### 4. Feed ecp203
- Footings: `footings` sums Dead + Super Dead patterns as D and Live patterns as L from the model's pattern types (override with `--dead-cases` / `--live-cases`). Get `q_allow` from the soil report (or the `alhabeeb-geotechnical` skill). Points with no column (walls) are skipped and listed: handle wall footings separately.
- Raft: `--raft` builds the raft outline from the column grid plus `--overhang` (default 0.5 m). ecp203's raft is a rigid-method check; final raft design should come from SAFE.
- Columns/beams: choose the ultimate combinations with `--combos`. The script takes a conservative envelope (max Pu with max |M|); if a column fails only because of that, re-check with the concurrent forces of each combination. He = story height by default: replace with effective/clear height per ECP 203.
- Always tell the user the fcu used (cube) and where it came from.

### 5. Quantities
`quantities` measures columns and walls up to the slab soffit, beams below the slab (drop only), slabs by plan area × thickness, beam lengths centre-to-centre of supports. Openings are deducted only if modeled. Foundations aren't in the superstructure model. Hand the Summary sheet to `alhabeeb-takeoff-boq` for the BOQ, and say these are model quantities (not shop-drawing quantities).

## Output format

1. **Model in one paragraph**: program/version, units, stories, main sections, loads.
2. **Findings / results table** (depends on the task)
3. **What was generated**: files written (JSON for ecp203, xlsx quantities, reports) with paths
4. **Assumptions and items to verify**: case mapping, fcu conversion, effective lengths, unmatched points

## Files

- `references/export-guide.md` - how to export from ETABS, SAFE, ADAPT without printing reports; which tables to export for each task
- `references/e2k-format.md` - what the parser reads from .e2k and known limitations
- `scripts/model_reader.py` - the reader
- `tests/` - small sample files (sample.e2k, reactions.xlsx, forces.xlsx, sample.f2k) to try the commands
