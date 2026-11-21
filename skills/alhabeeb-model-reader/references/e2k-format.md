# What the parser reads from an ETABS .e2k file

The .e2k file is plain text in sections starting with `$ SECTION NAME`. Each line is a keyword followed by quoted names and KEY value pairs. The parser reads by keyword, not by section title, so it tolerates version differences.

| Keyword | Used for |
|---|---|
| `UNITS "KN" "M" "C"` | conversion to kN and m (supports KN, N, TONF, KGF, KIP, LB / M, MM, CM, FT, IN) |
| `STORY "name" HEIGHT h` / `ELEV e` | stories listed top → bottom; the last one (base) has ELEV |
| `POINT "label" x y` | plan coordinates |
| `LINE "label" COLUMN|BEAM|BRACE "pi" "pj" n` | connectivity; for columns n = number of stories spanned below |
| `AREA "label" FLOOR|PANEL n "p1".."pn" o1..on` | slabs (FLOOR) and walls (PANEL; offsets 1 = point at story below) |
| `LINEASSIGN "label" "story" SECTION "s" ANG a ...` | frame instances per story |
| `AREAASSIGN "label" "story" SECTION "s" ...` | slab/wall instances per story |
| `POINTASSIGN "label" "story" RESTRAINT "UX UY UZ ..."` | supports |
| `FRAMESECTION "s" MATERIAL "m" SHAPE "..." D d B b` | section sizes (D = depth along local 2, B = width) |
| `SHELLPROP / SLABPROP / WALLPROP "p" ... *THICKNESS t` | slab and wall thickness |
| `MATERIAL "m" TYPE "Concrete" FC f WEIGHTPERVOLUME w`, `FY` | material strength and weight |
| `LOADPATTERN "p" TYPE "Dead" SELFWEIGHT 1` | pattern types (used to split D and L) |
| `AREALOAD / LINELOAD / POINTLOAD ... LC "p" FVAL v` | applied loads (checked for undefined patterns) |
| `COMBO "c" TYPE ...` + `COMBO "c" LOAD "p" SF f` | combinations |

## Known limitations
- Column orientation: the local-axis angle (`ANG`) is read but not applied; ecp203 receives b = B and t = D with Mx = M3. Check orientation for columns rotated 90°.
- Inclined beams and columns with offsets: lengths use plan distance and story heights.
- Walls: length = longest distance between the panel's plan points; openings in walls are not deducted.
- Curved slabs/beams, deck slabs and ribbed/waffle slabs: thickness taken from the property; ribs are not computed — check with the user.
- Section designer / nonprismatic sections: dimensions may be missing (reported as no size).
- Load cases (modal, response spectrum, nonlinear) are not interpreted; only patterns and combinations.
- Tested on a sample file written to the documented format. If a real file has a line the parser doesn't know, `summary` lists the section under "read but not interpreted" — tell the user and adapt the parser.
