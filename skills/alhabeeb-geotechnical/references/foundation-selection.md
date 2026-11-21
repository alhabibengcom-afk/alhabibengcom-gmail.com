# Foundation selection, settlement and construction checklist

Values marked (verify) are typical practice from general knowledge, not quoted from ECP 202. Confirm them against the code text and the project specification before using them in a submission.

## Decision guide
1. Good bearing layer near the surface, light/moderate loads → **isolated footings** with tie beams.
2. Close columns, overlapping footings, or a column on the property line → **combined / strap footings**, or **strip footings** under walls.
3. Total footing area > ~50 % of the building footprint, weak/variable soil, basement below water table, or differential settlement concerns → **raft (لبشة)**.
4. Weak upper layers with a good layer at depth, very heavy loads, large settlement on rafts, expansive clay active zone, scour → **piles** (bored cast-in-situ most common in Egyptian cities; driven where vibration is acceptable).
5. Raft on piles (piled raft) when the raft alone has adequate bearing but excessive settlement.

Also weigh: neighbouring buildings (excavation depth, dewatering, vibration), access for piling rigs, schedule, and cost of soil replacement versus deeper footings.

## Settlement limits (typical, verify)
| Item | Sand | Clay |
|---|---|---|
| Max total settlement, isolated footings | 25 mm | 40-65 mm |
| Max total settlement, raft | 50 mm | 65-100 mm |
| Max differential settlement | ~20 mm | ~40 mm |
| Angular distortion δ/L (framed buildings) | 1/500 (cracking limit for frames) | 1/500 |
Use 1/300 for architectural damage onset and 1/150 for structural damage as reference values (Skempton & MacDonald, Bjerrum).

## Immediate settlement
Se = q·B·(1 - ν²)·If / Es (flexible footing; rigid ≈ 0.93 × flexible centre value)
If (centre, flexible): square 1.12, L/B = 2 → 1.53, L/B = 5 → 2.10, strip → ~2.5. Use a weighted Es over a depth of 2B (square) to 4B (strip).
Schmertmann's method for sands is preferred when CPT data exist.

## Consolidation settlement (per clay sub-layer of thickness H)
- NC clay: Sc = Cc·H/(1 + e0) · log10((σ'0 + Δσ)/σ'0)
- OC clay, σ'0 + Δσ ≤ σ'c: Sc = Cs·H/(1 + e0) · log10((σ'0 + Δσ)/σ'0)
- OC clay, σ'0 + Δσ > σ'c: Sc = Cs·H/(1+e0)·log10(σ'c/σ'0) + Cc·H/(1+e0)·log10((σ'0+Δσ)/σ'c)
Δσ at sub-layer centre (2:1 method): Δσ = P / ((B + z)(L + z)). Split thick layers into ~1-2 m sub-layers.
Time: t = Tv·Hdr²/cv; Tv = 0.197 for U = 50 %, 0.848 for U = 90 %.

## Piles (bored, quick reference)
Q_ult = Qs + Qb
- Clay shaft: fs = α·cu, α ≈ 0.45 for bored piles (London clay practice; 0.3-0.6 range)
- Clay base: qb = 9·cu
- Sand shaft: fs = β·σ'v, β ≈ K·tanδ (bored: K ≈ 0.7-1.0 of K0, δ ≈ φ); limit fs ≈ 100 kN/m² for bored piles (common practice)
- Sand base: qb = σ'v·Nq*, cap at ~ 10-11 MN/m² driven, lower for bored (~ 1/3 of driven)
- FS: 2.5 on total, or 1.5 shaft / 3 base (verify ECP 202)
- Group: check block failure in clay; efficiency in sand ≈ 1 for bored piles at ≥ 3D spacing; typical spacing 2.5-3D.
- Negative skin friction in fill and consolidating clay - add to load, do not count as capacity.
- Load tests: working load test on a percentage of piles and an initial (preliminary) test to failure or 2× working load (number per ECP 202 - verify). Integrity tests (sonic/PIT) on a large share of bored piles.

## Soil replacement (إحلال)
- Material: well-graded sand-gravel (سن وزلط / سن وحجر), free from clay lumps and organics.
- Layers: 20-30 cm loose, each compacted to ≥ 95 % of maximum dry density by Modified Proctor (verify project spec).
- Field density test (sand cone / nuclear) per layer; plate load test on the final surface when specified.
- Extend replacement beyond the footing edge by at least the replacement thickness (1:1 spread) unless the report says otherwise.

## Groundwater and dewatering
- Lower water at least 0.5-1.0 m below excavation level during construction (verify spec).
- Methods: open sumps (stable cohesive soil, small inflow), wellpoints (sand, up to ~5-6 m drawdown per stage), deep wells (larger drawdowns).
- Check settlement of neighbouring buildings due to drawdown; monitor levels.
- Uplift: check basement buoyancy with FS ≥ 1.1-1.2 against the design flood/high water level (verify).

## Chemical attack
High sulfates (SO₃) → sulfate-resisting cement, minimum cement content and maximum w/c ratio per ECP 203 durability tables; high chlorides → cover, low w/c, protective coatings. Bitumen/membrane waterproofing for concrete in contact with aggressive soil or water.

## Excavation support
- Unsupported slopes only in stable soil and away from neighbours; typical temporary slopes 1:1 sand above water, steeper in stiff clay (verify by analysis).
- Supported: sheet piles, soldier piles and lagging, contiguous/secant bored piles, diaphragm walls; anchors or struts for depth.
- Check base heave (soft clay) and piping/boiling (sand under water).
