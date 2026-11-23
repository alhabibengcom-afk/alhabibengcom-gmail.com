---
name: alhabeeb-model-reader
description: Read ETABS, SAFE and ADAPT models from their exported files (.e2k, .f2k/.s2k, Excel/CSV tables) without the printed reports; review and repair the model (corrected .e2k to re-import), extract design forces, compute concrete and formwork quantities, design footings, rafts, columns and beams with the office ECP 203 library (Egyptian codes/ecp203), and draw the structural sheets (foundation plan, footing details, column and beam schedules) as DXF on the company template. Use it whenever the user sends or mentions an ETABS/SAFE/ADAPT model or export (including .EDB/.FDB/.ADB files), asks to check or fix a model, wants column loads or reactions, wants footings designed from ETABS reactions, wants reinforcement drawings from the analysis, or wants model quantities - even if they just say "الموديل" or "ملف الإيتابس".
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
| `fix model.e2k [-o fixed.e2k]` | ETABS text model | corrected .e2k (import back into ETABS) + list of every change |
| `quantities model.e2k --xlsx q.xlsx` | ETABS text model | concrete m³ and formwork m² by story and element (Detail + Summary sheets) |
| `tables FILE --list` / `--table NAME --csv DIR` | SAFE/SAP `.f2k/.s2k`, any Excel/CSV export (ETABS, SAFE, ADAPT) | list of tables, rows, CSV per table |
| `footings --model m.e2k --reactions r.xlsx --q-allow Q [--raft]` | model + Joint Reactions table | ecp203 JSON: one isolated footing per column, or one raft |
| `columns --model m.e2k --forces f.xlsx --combos U1,U2 [--group]` | model + Element Forces - Columns | ecp203 JSON for columns |
| `beams --model m.e2k --forces f.xlsx --combos U1,U2 [--group]` | model + Element Forces - Beams | ecp203 JSON for beams |

Then design: `cd "Egyptian codes" && python3 -m ecp203 <file>.json -o reports/<name>.md`. Exit code 1 means at least one element is not safe: report which and why, don't hide it.

## Direct reading from the model files (no export, no report)

Both run on the user's Windows PC (ETABS / SAFE installed) through the programs' official API. They cannot run in a cloud session: if the user's computer is connected (Remote Control folder) run them there, otherwise give the user the command or the .bat launcher.

**ETABS** — `scripts/etabs_live.py` (or drag the .EDB onto `scripts/run_etabs.bat`):
```
pip install comtypes openpyxl ezdxf matplotlib
python etabs_live.py --edb "D:\Projects\Tower\Tower.EDB" --fix --q-allow 200 --project Tower -o out [--fcu 30 --stairs st.json ...]
python etabs_live.py --attach --fix --q-allow 200 -o out        # model already open
```
1. opens the model (hidden) or attaches; reads the model text ETABS keeps beside it (`.$et`, one Save creates it);
2. reviews it; with `--fix` applies the safe corrections **inside ETABS** (missing load patterns, self-weight once, base supports, ECP ultimate combination from `ecp203/params.py`), saves `<name>_ALH-fixed.EDB` (original never overwritten), **re-runs the analysis** — so the design uses corrected results; engineering items (sizes, load values, seismic data) are reported, not changed;
3. reads Joint Reactions, Element Forces (columns, beams), Pier Forces, Base Reactions, Story Drifts, Modal mass through the API database tables (table names found in ETABS's own list, so versions don't matter) → `etabs_tables.xlsx`;
4. runs `building_design.py --auto-resize`.

**SAFE** — `scripts/safe_live.py` (or drag the .FDB onto `scripts/run_safe.bat`):
```
python safe_live.py --fdb "D:\Projects\Tower\Raft.FDB" --q-allow 150 --combos U1 --service-combos SERV -o out
```
Runs the analysis, pulls strip forces, soil pressures, punching and slab properties, then `safe_design.py`: strip steel per metre with `ecp203` `design_slab_strip` (top and bottom per strip), max soil pressure vs `q_allow` (+ uplift), punching ratios, thickness proposal with `--auto-resize` (punching after resize is an estimate — re-run SAFE at the proposed thickness), `ST-ZZ-120` sheet + `safe_design.xlsx` + calculation report. `safe_design.py --tables safe_tables.xlsx` also works on a manual SAFE Excel export. Fields are matched by name; the script prints which moment/width fields it used — check them on the first run.

**ADAPT** — there is no public ADAPT API to drive, so ADAPT cannot be read from its native file. Use its Excel/text exports with `tables --list` and map the columns from the actual headers; PT checks use `Egyptian codes/aci318` (office rule: PT slabs by ACI 318-19). Ask the user for one sample export before promising automation, and never guess numbers from a binary `.ADB`.

Tested here against mocks returning tables in the programs' layouts; on the first real run, read the printed table names and row counts and report any API error verbatim.

## Auto-resize (design that corrects itself)

`--auto-resize` (on by default from the live scripts): every element failing an ECP 203 check is enlarged step by step and redesigned with the same forces — columns +50 mm alternating sides until they pass **and** steel ≤ `--max-rho` (default 2 %, economical), beams deeper (then wider), slabs +10 mm (self-weight updated), walls +50 mm, flat slabs +20 mm until punching passes. Proposals go to the "Resize proposals" sheet and the console. Always tell the user: bigger members change stiffness and weight — update the model with the proposed sizes, re-run (`etabs_live.py --fix` again), and design again before issue.

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

### 2b. Repair the model
`fix` repairs only what is unambiguous, and lists each change:
- load patterns referenced by loads/combinations but not defined → added (type guessed from the name: verify)
- self-weight counted in more than one pattern → kept in the Dead pattern only; missing → added
- columns reaching the base with no support → fixed support added
- no ultimate gravity combination → `ECP-U1` added with the factors read from `Egyptian codes/ecp203/params.py`
It never changes section sizes, live-load values, seismic/wind parameters or stiffness modifiers: those are engineering decisions — list them for the engineer. Tell the user to import the corrected file in ETABS (File > Import > ETABS .e2k Text File), re-run the analysis, and export the result tables again before designing.

### 3. Extract design forces
Ask for (or read) the exported tables: Joint Reactions, Element Forces - Columns / Beams, Story Drifts, Base Reactions, Modal Participating Mass Ratios. Use `tables` to read them and present clean tables. Typical checks: total base reaction vs total applied gravity load (should match within ~1-2 %), drift limits, modal mass ≥ 90 % (verify limits with the code).

### 4. Feed ecp203
- Footings: `footings` sums Dead + Super Dead patterns as D and Live patterns as L from the model's pattern types (override with `--dead-cases` / `--live-cases`). Get `q_allow` from the soil report (or the `alhabeeb-geotechnical` skill). Points with no column (walls) are skipped and listed: handle wall footings separately.
- Raft: `--raft` builds the raft outline from the column grid plus `--overhang` (default 0.5 m). ecp203's raft is a rigid-method check; final raft design should come from SAFE.
- Columns/beams: choose the ultimate combinations with `--combos`. The script takes a conservative envelope (max Pu with max |M|); if a column fails only because of that, re-check with the concurrent forces of each combination. He = story height by default: replace with effective/clear height per ECP 203.
- Always tell the user the fcu used (cube) and where it came from.

### 4b. Design the whole building and draw it
```bash
pip install ezdxf matplotlib openpyxl   # once
python3 scripts/building_design.py --model m.e2k --reactions reactions.xlsx --forces forces.xlsx \
    --combos U1,U2 --q-allow 200 --fcu 30 --fcu-found 25 --fy 400 \
    --project "Project name" --client "Client" --project-code PRJ -o out/
```
It designs every footing, column (per story) and beam (per story) with `ecp203`, groups identical results into types (F1.., CT1.., BT1.. — CT/BT so they don't clash with ETABS labels), and writes:
- `PRJ-ST-ZZ-101_R00.dxf` foundation plan (grids, dimensions, footings, columns), footing schedule, plan + section of each footing type with bars
- `PRJ-ST-ZZ-501_R00.dxf` column types (sections with bars and ties), column-by-story table, schedule
- `PRJ-ST-ZZ-502_R00.dxf` beam types (sections), schedule
- `PRJ-ST-ZZ-111.._R00.dxf` one slab sheet per story: plan with grids, beams, walls, columns; each panel labelled with its type and thickness, bottom mesh both ways, top bars over continuous supports; slab schedule
  - beam-supported slabs: panels found from the beam/wall grid, designed with `design_two_way_slab` (switches to one-way when r > 2) using own weight + the model's SDL and live area loads, continuity from neighbouring panels
  - stories without beams: flat slab with `design_flat_slab_floor` (equivalent frame, column/middle strips, punching at every column; failing columns marked FAIL on the plan)
  - anything irregular (missing edge beam, cantilever, non-rectangular region, irregular column grid in a flat slab) is listed as skipped - design manually or from SAFE strips
- `PRJ-ST-ZZ-503_R00.dxf` wall types (plan section of a 1 m strip, bars each face) and schedule, from the ETABS **Pier Forces** table (export it; walls need pier labels in ETABS). Pu/m = max compression / pier length; out-of-plane moment 0; shear-wall in-plane design, boundary elements and openings are not covered.
- PNG previews of each sheet, `design.xlsx` (every element, its type, pass/fail and failing checks), `reports/*.md` (full ECP 203 calculations)
Drawings follow `alhabeeb-cad-standards`: mm, origin at grid A/1, ST-/GN- layers, A1 layout with the AH-TITLE block filled (purpose "للمراجعة", R00). Check them with that skill's `check_standards.py`.

- `PRJ-ST-ZZ-401_R00.dxf` stair details (with `--stairs stairs.json`): longitudinal flights drawn in section with steps, waist, landing, main bars crossing at the knee, top starters L/4, distribution bars; cantilever steps with the anchored top bar; stair schedule. Stairs are usually not in the ETABS model, so their geometry comes from the JSON (format at the top of `scripts/stairs_bbs.py`, example `tests/stairs.json`); ask the user for span (horizontal), riser, going, waist t, width, landing length, type and number of identical flights. Designed with `ecp203` `design_stair`.
- `PRJ-ST-ZZ-504.._R00.dxf` **bar bending schedule** (one or more sheets) + BBS and steel-summary sheets in `design.xlsx`: every bar mark with element, member, shape, segment lengths, diameter, number per member, members, total, cut length, total length and weight (Ø²/162 kg/m), summary by diameter and by element. Rules printed on the schedule: laps/anchorage = Ld from `ecp203` `development_length` × `--lap-factor` (default 1.0 — confirm with the ECP 203 splice clause), 12Ø bend legs, 135° tie hooks 10Ø, no bend deduction, beam top bars full length (conservative). Not included: cross-ties for intermediate column bars, slab edge U-bars, opening trimmers, flat-slab strips, wastage — tell the user to add the specification's wastage allowance before ordering steel.

Options: `--fy-slab` (slab steel, default = `--fy`), `--no-slabs`, `--no-walls`, `--stairs FILE`, `--lap-factor F`, `--no-bbs`. Spacings are always rounded DOWN to 5 mm (never less steel than designed).

Report to the user: number of types, every element that fails (and why — e.g. anchorage length → hooks, or section too small → resize in ETABS and re-run), what was skipped (wall reactions, slabs). These drawings are design drafts: the engineer completes slabs, walls, stairs, laps/curtailment and general notes, reviews, and signs before issue. Never present them as issued drawings.

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
- `scripts/model_reader.py` - the reader (summary, review, fix, quantities, tables, ecp203 JSON)
- `scripts/building_design.py` - full design + DXF drawings
- `scripts/slabs_walls.py` - slab panel detection, slab/flat-slab/wall design and their sheets
- `scripts/stairs_bbs.py` - stair design and drawing, bar bending schedule
- `scripts/csi_api.py` - shared ETABS/SAFE API layer (connect, table discovery, edits)
- `scripts/etabs_live.py` + `run_etabs.bat` - ETABS .EDB direct: review, fix in ETABS, re-analyse, design
- `scripts/safe_live.py` + `run_safe.bat`, `scripts/safe_design.py` - SAFE .FDB direct: strips, soil, punching, drawing
- `scripts/resize.py` - auto-resize of failing elements
- `tests/` - small sample files (sample.e2k, reactions.xlsx, forces.xlsx, sample.f2k) to try the commands
