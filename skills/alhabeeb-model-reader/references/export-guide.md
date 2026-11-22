# How to export models and results (no printed report needed)

Menu names below are for recent versions (ETABS 18-22, SAFE 16-22). Older versions have the same commands with slightly different menus. Tell the user to keep the units as kN-m when exporting if possible.

## ETABS

### Model (geometry, sections, loads, combinations)
File > Export > **ETABS .e2k Text File** → save `ProjectName.e2k`.
- Takes seconds, no analysis needed.
- Older versions may save `.$et` (same format) — also readable.

### Results tables
Run the analysis first. Then Display > **Show Tables** (Ctrl+T) → tick the tables → OK → in the table window: File > **Export All Tables > To Excel** (or Export Current Table).
Tick, depending on the task:
| Task | Tables |
|---|---|
| Footings / raft | Analysis Results > Joint Output > Reactions > **Joint Reactions** (select load patterns Dead, SDL, Live, not only combos) |
| Columns | Analysis Results > Frame Output > **Element Forces - Columns** (select ultimate combinations) |
| Beams | Analysis Results > Frame Output > **Element Forces - Beams** |
| Walls | Analysis Results > Wall Output > **Pier Forces** (ultimate combinations; assign pier labels to walls first: Assign > Shell > Pier Label) |
| Global checks | **Base Reactions**, **Story Drifts**, **Modal Participating Mass Ratios**, **Story Forces** |
| Design results | Design > Concrete Frame Design > summary tables (if the office uses ETABS design for comparison) |

Tip: Load Patterns/Cases/Combos selection is the button "Select Load Patterns/Cases" in the table dialog — include both patterns (for footings) and ultimate combos (for members).

### No export at all: read the .EDB directly
Use `scripts/etabs_live.py` (or drag the .EDB onto `scripts/run_etabs.bat`) on the PC where ETABS is installed: it opens the model through the ETABS API, runs the analysis, reads the tables and designs. Also: ETABS keeps a text copy of the model (`ModelName.$et`) beside the `.EDB` - that file is readable directly.

## SAFE

### Model
File > Export > **SAFE .f2k Text File** (SAFE 12 and later). Readable with `tables --list`: point coordinates, slab properties, soil subgrade, loads, design strips.

### Results
Display > Show Tables → tick Joint Reactions, Strip Forces, Slab Forces, Punching Shear Design, Soil Pressures → Export to Excel.
For a raft: Soil Pressures (max under service combination) vs q_allow, Punching Shear ratios, Strip moments for reinforcement.

### From ETABS to SAFE
ETABS: File > Export > **Story as SAFE V12 .f2k file** (exports a floor or the base reactions to SAFE). That `.f2k` is also readable here.

## ADAPT (ADAPT-Builder / ADAPT-PT/RC)

Formats vary between versions; ask the user for a sample and read its headers.
- ADAPT-Builder: tabular results (reports manager / result tables) can be exported to **Excel or text** — export: design strip actions, tendon profiles, stresses, punching checks.
- ADAPT-PT/RC (strip analysis): the tabular output can be saved as text/Excel; read the span moments, stresses at transfer and service, required reinforcement.
- ADAPT-Builder can import ETABS models; for this skill the ETABS `.e2k` remains the cleaner source for geometry.
- Post-tensioned slab checks in the office use ACI 318-19 (`Egyptian codes/aci318`: `pt_section`, `pt_punching`, `floor_pt`).

## What cannot be read
- `.EDB` (ETABS), `.FDB` (SAFE), `.ADB` (ADAPT-Builder), `.SDB` (SAP2000) — binary, proprietary.
- PDF reports can be read as text but lose structure; exported tables are much more reliable.
