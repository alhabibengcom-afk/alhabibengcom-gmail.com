# Surveying methods and formulas

Tolerances here are typical practice. The project specification and the consultant's requirements govern.

## Levelling
Height of instrument (HI) method:
- HI = RL(known) + BS
- RL = HI - IS (or FS)
- Check: ΣBS - ΣFS = last RL - first RL

Rise and fall method:
- difference = previous reading - current reading; positive = rise, negative = fall
- RL = previous RL + rise (or - fall)
- Check: ΣBS - ΣFS = ΣRise - ΣFall = last RL - first RL
- Rise & fall checks intermediate sights too; HI does not.

Misclosure: e = observed closing RL - known closing RL.
Allowable (typical):
| Class | Allowable (mm), K in km |
|---|---|
| Precise / benchmark transfer | ±4√K to ±6√K |
| Ordinary engineering | ±12√K |
| Rough / earthwork | ±24√K |
If K unknown: ±5 to 10 mm √n with n = number of set-ups is also used on short site runs.
Adjustment: correction at set-up i = -e × i / n (cumulative, proportional to set-ups), or proportional to distance.

Good practice: equalize BS and FS distances (cancels collimation error), sights ≤ 50-60 m, two-peg test on the level at the start of work (collimation error within spec, e.g. ≤ 1 mm per 20-30 m sight), close every line on a known benchmark (not on the start point unless no other BM).

Curvature and refraction (long sights): c = 0.0673·D² (m, D in km).

## Angles and bearings
- Closed traverse interior angles: Σ = (n - 2)·180°; exterior: (n + 2)·180°.
- Forward bearing = back bearing ± 180°.
- Bearing of next leg = bearing of previous leg + 180° + clockwise angle at station (subtract 360 if > 360).
- Angular misclosure allowable: typically ±k√n" (k ≈ 10" for 1"-5" total stations on control, 30"-60" for rougher work; verify).

## Traverse computation
ΔE = D·sinθ, ΔN = D·cosθ
Linear misclosure f = √(fE² + fN²); precision = 1 : (ΣD / f)
Bowditch (compass) correction: δE_i = -fE·D_i/ΣD; δN_i = -fN·D_i/ΣD
Transit rule (when angles are more precise than distances): δE_i = -fE·|ΔE_i|/Σ|ΔE|.

## Inverse (join) computation
ΔE = E2 - E1, ΔN = N2 - N1
D = √(ΔE² + ΔN²)
θ = atan2(ΔE, ΔN) (normalize to 0-360°)

## Area from coordinates (shoelace)
2A = |Σ (E_i·N_{i+1} - E_{i+1}·N_i)|
Egyptian land units: 1 feddan = 24 qirat = 4,200.83 m²; 1 qirat = 24 sahm = 175.03 m²; 1 sahm ≈ 7.29 m².

## Horizontal circular curve
Given radius R and deflection angle Δ:
- Tangent length T = R·tan(Δ/2)
- Curve length L = π·R·Δ/180
- Long chord C = 2R·sin(Δ/2)
- External E = R·(sec(Δ/2) - 1)
- Mid-ordinate M = R·(1 - cos(Δ/2))
- Chainage of TC = chainage of PI - T; TC to CT = + L
Setting out by deflection angles from TC: δ (deg) = 1718.9·c / R (minutes) for chord c, i.e. δ = (c / 2R) rad; cumulative deflections. Chords ≤ R/20 for accuracy.
By offsets from the tangent: y = R - √(R² - x²).

## Vertical curve (parabolic)
y = y_BVC + g1·x + (g2 - g1)·x²/(2L), grades as decimals, x from BVC.
Turning point at x = -g1·L/(g2 - g1).
K = L / |g2 - g1|(%) — check against design speed criteria in the road spec.

## Tacheometry / total station
Horizontal distance H = S·sin(z) (zenith angle z) ; ΔZ = S·cos(z) + instrument height - target height.

## Earthwork volumes
Grid (borrow pit) method: V = A_cell/4 · (Σh1 + 2Σh2 + 3Σh3 + 4Σh4), where h_k is the cut/fill depth at corners shared by k cells. Equivalent: each cell V = A × mean of its four corner depths.
Mixed cell (part cut, part fill), approximation: V_cut = A/4 · (Σcut)²/(Σcut + Σfill), V_fill = A/4 · (Σfill)²/(Σcut + Σfill) (absolute corner depths).
Average end area: V = L·(A1 + A2)/2 — overestimates for pyramid-like shapes.
Prismoidal: V = L/6 · (A1 + 4Am + A2), Am = area of the middle section (not the mean of A1 and A2). With sections at equal interval d and an odd number of sections: V = d/3·(A1 + 4A2 + 2A3 + 4A4 + ... + An) (Simpson).
If no middle section was surveyed, survey one or use Simpson over three or more sections.
Trapezoidal section area with level ground: A = h·(b + s·h), b = bottom width, s = side slope horizontal:vertical.
Swell/shrinkage: loose volume = bank × (1 + swell); compacted = bank × (1 - shrinkage). Typical swell: sand 10-15 %, gravel 12-15 %, clay 25-40 %, rock 50-80 %.

## Typical site tolerances (verify spec)
- Setting out of building axes: ±5 mm relative, ±10-20 mm absolute to control
- Column position: ±5-10 mm
- Levels of formwork/slabs: ±5-10 mm
- Earthwork formation level: ±25-50 mm
- Control traverse precision: ≥ 1:10,000; site traverses ≥ 1:5,000
