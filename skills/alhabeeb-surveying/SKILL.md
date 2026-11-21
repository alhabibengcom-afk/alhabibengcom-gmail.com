---
name: alhabeeb-surveying
description: Site surveying for Al-Habeeb projects - reducing level books (rise & fall, height of instrument), checking levelling misclosure, traverse adjustment (Bowditch), coordinates and bearings, setting out (columns, axes, curves, slopes), plot areas from coordinates, earthwork cut and fill (grid method, cross sections, average end area, prismoidal), and coordinate systems used in Egypt (UTM 36N / WGS84, Egyptian Transverse Mercator belts). Use it whenever the user mentions مساحة, ميزانية, levels, منسوب, رفع مساحي, توقيع, setting out, total station, GPS, إحداثيات, coordinates, حفر وردم, cut and fill, earthwork volume, مقاطع, traverse, مضلع, or pastes a level book or a list of points, even if they don't say "surveying".
---

# Site surveying - Al-Habeeb technical office

Covers the survey work that feeds drawings, quantities and setting out on site. Earthwork volumes produced here feed `alhabeeb-takeoff-boq`; plot areas and setbacks may need `egyptian-codes` (building law).

## Answering rules

- Reply in the user's language. For Arabic, use Egyptian Arabic with the engineering term in English between brackets.
- Metric units only: m, mm, m², m³. Angles in degrees-minutes-seconds or decimal degrees; say which. If someone gives grads (gon) or feet, convert and say so.
- Bearings are whole-circle bearings measured clockwise from grid north (0°-360°). Coordinates are Easting (E), Northing (N), Level (Z). Say which coordinate system/datum the numbers are in.
- Always run the arithmetic check (Σ backsights - Σ foresights = last RL - first RL; Σ rises - Σ falls = same) and the closure check. A level book or traverse without a closure check is not finished.
- Use `scripts/survey.py` for any calculation with more than a handful of numbers. It is exact and repeatable; hand arithmetic on long level books produces mistakes.
- Present results in a table the site engineer can copy into Excel. Offer an `.xlsx` (via the `xlsx` skill) for long outputs.
- Tolerances: the project specification governs. The values in `references/methods.md` are typical practice; say they are typical and need checking against the spec.

## Workflow by task

### Levelling (ميزانية)
1. Put the readings into the table: station, BS, IS, FS, remarks. Each change point has FS then BS on the same row.
2. Reduce with height of instrument or rise & fall: `python3 scripts/survey.py level --file book.csv --start-rl 25.000 [--close-rl 25.000] [--km 0.8]`.
3. Arithmetic check, then misclosure vs allowable (typical ±12√K mm for ordinary site levelling, K in km; verify spec). If within tolerance, distribute the error proportionally to the number of set-ups (the script does this) and report adjusted levels.
4. If over tolerance, do not adjust - ask for re-levelling and point to the likely section.

### Traverse and coordinates (مضلع)
1. Check angle misclosure: closed loop Σ interior angles = (n - 2)·180°. Allowable typically ±k√n seconds (k depends on instrument and class, e.g. 10-30"; verify).
2. Distribute the angular error equally, compute bearings, ΔE = D·sin(bearing), ΔN = D·cos(bearing).
3. Linear misclosure = √(ΣΔE² + ΣΔN²); relative precision = misclosure / perimeter (typical ≥ 1:5,000 for site control, 1:10,000 for main control; verify).
4. Adjust with Bowditch: `python3 scripts/survey.py traverse --file trav.csv --start-e .. --start-n .. --start-bearing ..`.

### Bearing and distance between two points (join / inverse)
`python3 scripts/survey.py inverse --p1 E,N --p2 E,N` - gives bearing, distance, ΔE, ΔN. Use for setting out from a station to a point (angle from backsight = bearing to point - bearing to backsight).

### Setting out (توقيع)
- Columns/axes: compute coordinates from the grid on the drawing (origin, rotation, spacing), then set-out data from the station: `python3 scripts/survey.py setout --station E,N --backsight E,N --points pts.csv`.
- Always check by an independent measurement: tape diagonals of a rectangle, or set out from a second station.
- Horizontal circular curves and vertical curves: formulas in `references/methods.md`.
- Slopes and batter boards: offset = depth × slope ratio; give levels on profile boards.

### Areas (مساحات)
Area from coordinates (shoelace / cross-multiplication): `python3 scripts/survey.py area --file plot.csv`. Give the area in m², and in feddan/qirat/sahm on request (1 feddan = 4,200.83 m² = 24 qirat; 1 qirat = 175.03 m² = 24 sahm; 1 sahm = 7.29 m²).

### Earthwork (حفر وردم)
- **Grid method** for building pads and site levelling: existing levels at grid corners vs design level → `python3 scripts/survey.py grid --file grid.csv --cell 10 --design 24.50`. Uses the four-corner averaging and splits cut and fill per cell. For a mixed cell (part cut, part fill), the script uses the standard cut²/(cut+fill) approximation; say so.
- **Cross sections** for roads, channels, trenches: section areas every 10-25 m, then volume by average end area or prismoidal: `python3 scripts/survey.py sections --file sec.csv [--prismoidal]`.
- Add a bulking/shrinkage note: excavated volume is bank measure; for trucks apply a swell factor (sand ~10-15 %, clay ~25-40 %, rock 50 %+), and compacted fill needs more borrow than the in-place volume. Use the values in the project spec or soil report when available.
- State clearly what level the excavation goes to (founding level + blinding, working space around footings, side slopes).

### Coordinate systems in Egypt
See `references/coordinate-systems.md`. Key point: projects get coordinates either in WGS84 UTM zone 36N (most of Egypt east of 30°E; zone 35 west of 30°E, zone 37 east of 36°E), or in the old Egyptian Transverse Mercator belts (Red / Purple / Blue) on the Egypt 1907 datum (Helmert 1906 ellipsoid). Mixing them gives errors of hundreds of metres. Ask which system the drawing or the survey office coordinates are in before using them. Transformations between datums need official parameters; don't approximate them for setting out.

## Output format

1. **Result** - the answer the user needs (adjusted levels, area, volume, set-out table) in 1-3 lines.
2. **Table** of the computation
3. **Checks** - arithmetic check, misclosure vs allowable, independent check performed or recommended
4. **Notes** - assumptions (coordinate system, design level, swell factor), anything that needs a site re-check

## Files

- `references/methods.md` - formulas: levelling, traverse, curves, tacheometry, earthwork, tolerances
- `references/coordinate-systems.md` - UTM / ETM / datums in Egypt, scale factor, practical notes
- `scripts/survey.py` - calculator (Python standard library only). Run `python3 scripts/survey.py -h`. CSV formats are in the script's help for each subcommand.
