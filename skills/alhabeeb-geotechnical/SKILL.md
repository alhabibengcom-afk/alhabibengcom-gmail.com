---
name: alhabeeb-geotechnical
description: Geotechnical and foundation engineering for Al-Habeeb site and technical office work - reading soil investigation reports (boreholes, SPT, CPT, lab tests), allowable bearing capacity, immediate and consolidation settlement, choosing the foundation type (isolated, strip, raft, piles), pile capacity, groundwater, dewatering, excavation support and soil replacement. Use it whenever the user mentions soil, تربة, تقرير تربة, جسات, bearing capacity, قدرة تحمل, settlement, هبوط, piles, خوازيق, raft, لبشة, dewatering, نزح مياه, soil replacement, إحلال, excavation or shoring, even if they only paste numbers from a borehole log.
---

# Geotechnical engineering - Al-Habeeb technical office

Helps with everything between the soil report and the foundation drawings. Structural design of the concrete footing itself (reinforcement, punching) belongs to the `ecp203-structural-analyst` agent; hand over to it once the allowable bearing pressure and foundation type are settled.

## Answering rules

- Reply in the user's language. For Arabic, use Egyptian Arabic with the engineering term in English between brackets.
- Metric (SI) units only: kN, kN/m², kN/m³, m, mm. Convert any imperial input and say you converted it. 1 kg/cm² ≈ 98.1 kN/m² (≈ 100 for quick checks).
- Governing code in Egypt: **ECP 202 (Egyptian Code for Soil Mechanics and Foundation Design and Execution)**. Its text is **not** in the `egyptian-codes` reference files. Any value you quote from ECP 202 (safety factors, settlement limits, pile load test rules) comes from general knowledge, so mark it "يحتاج تحقق من نص الكود" / "verify against the code text". Never invent a clause number.
- The soil report's recommendations (allowable bearing, founding level, replacement layer) take precedence over your calculation. Your calculation checks them; it does not overrule them. If your check disagrees significantly, say so and recommend asking the geotechnical consultant.
- Show every calculation: formula, then substitution with units, then the result, and say where each factor comes from.
- State assumptions plainly (water table level, drained or undrained, soil parameters estimated from SPT). A geotechnical answer is only as good as its input parameters.

## Workflow

### 1. Read the soil report
Extract into a table, per borehole:
- Layer depths, description, USCS class if given
- SPT N (field) per depth; CPT qc if given
- Groundwater level and date measured
- Lab results: γ, w%, LL, PL, PI, c / cu, φ, Cc, Cs, e0, OCR, qu, swelling pressure, chemical (SO₃, Cl⁻)
- The report's recommendations: foundation type, founding level, allowable bearing, settlement estimate, replacement, cement type, dewatering

Then flag problems: expansive clay (high PI, swelling), collapsible soil, soft clay near the surface, loose saturated sand (liquefaction in seismic zones), high sulfates/chlorides (needs sulfate-resisting cement and protection), high water table, fill/rubbish layers, big variation between boreholes.

### 2. Correct SPT values (sand)
Use `scripts/geotech.py spt` or do it by hand. See `references/correlations.md` for N60 correction, overburden correction (N1)60, and correlations to φ and relative density. Say which correlation you used, because they differ by several degrees.

### 3. Bearing capacity
Use the general bearing capacity equation (Terzaghi / Meyerhof / Vesic factors) - `references/bearing-capacity.md` has the equations, shape/depth/inclination factors and water table corrections. Run `scripts/geotech.py bearing` for the numbers.
- Factor of safety on ultimate capacity: 3 is the usual value for shallow foundations (verify against ECP 202).
- For clay, check undrained (φ = 0, cu) - usually governs short term.
- Allowable bearing = min(bearing capacity / FS, pressure that keeps settlement within limits). On sand, settlement usually governs for wide footings and rafts.

### 4. Settlement
- Immediate (elastic) settlement for sand and the short-term part on clay.
- Consolidation settlement for saturated clay: normally consolidated vs over-consolidated, using Cc / Cs and stress increase by 2:1 method or Boussinesq.
- Run `scripts/geotech.py consolidation` for layered clay.
- Compare with limits in `references/foundation-selection.md` (typical values; verify against ECP 202 and the structural engineer's tolerance) and check differential settlement and angular distortion between adjacent columns.

### 5. Choose the foundation type
Follow the decision guide in `references/foundation-selection.md`: isolated -> combined/strip -> raft -> piles, driven by allowable pressure, the ratio of footing area to building footprint (above ~50 % go to raft), settlement, and site constraints (neighbours, water, noise/vibration for driven piles).

### 6. Piles
Single pile capacity = shaft friction + end bearing (α method for clay, β or SPT-based for sand), FS typically 2-3, group efficiency and block failure for clay, negative skin friction in fill/soft clay. Bored cast-in-situ piles are the common choice in Egyptian cities. Always recommend a pile load test to confirm design capacity (number and type according to ECP 202, verify).

### 7. Construction issues
Dewatering (wells/wellpoints, effect on neighbours), excavation side slopes and shoring (sheet piles, secant/contiguous piles, diaphragm walls), soil replacement (material, layer thickness 25-30 cm, compaction 95 % modified Proctor typical, plate load test after), protecting the foundation from sulfates/chlorides, waterproofing below the water table.

## Output format

For a report review or design check, use:

1. **Summary** - the soil, the water table, the recommended foundation and allowable pressure in 3-5 lines.
2. **Soil profile table**
3. **Calculations** - each step with formula, substitution and units
4. **Notes, ranked**: (1) safety/code issues, (2) items affecting cost or schedule, (3) general
5. **Items to verify** - code values from memory, assumed parameters, questions for the geotechnical consultant

For a quick question, answer in a few lines but still give the units and the source of any number.

## Files

- `references/bearing-capacity.md` - bearing capacity equations, factors, water table, eccentric loads
- `references/correlations.md` - SPT/CPT corrections and correlations, typical soil parameters
- `references/foundation-selection.md` - foundation selection, settlement limits, pile notes, construction checklist
- `scripts/geotech.py` - calculator (Python standard library only). Run `python3 scripts/geotech.py -h`.
