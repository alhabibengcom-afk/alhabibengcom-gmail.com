# Field test corrections and correlations

These are empirical. Always say which one you used, give a range when correlations disagree, and prefer the soil report's lab values when they exist.

## SPT corrections
N60 = N_field · (ER/60) · CB · CS · CR
- ER: hammer energy ratio %. Safety hammer ≈ 60, donut ≈ 45, automatic ≈ 70-90. If unknown in Egypt, assume 60 and say so.
- CB borehole diameter: 65-115 mm → 1.0; 150 mm → 1.05; 200 mm → 1.15
- CS sampler: standard → 1.0
- CR rod length: < 4 m → 0.75; 4-6 → 0.85; 6-10 → 0.95; > 10 → 1.0

Overburden correction (sands): (N1)60 = CN · N60, CN = √(100/σ'v) with σ'v in kN/m² (Liao & Whitman), CN ≤ 1.7.

## SPT → sand properties
| (N1)60 | Density | Dr % | φ° approx |
|---|---|---|---|
| 0-3 | very loose | 0-15 | < 28 |
| 3-8 | loose | 15-35 | 28-30 |
| 8-25 | medium | 35-65 | 30-36 |
| 25-42 | dense | 65-85 | 36-41 |
| > 42 | very dense | 85-100 | > 41 |

- Hatanaka & Uchida: φ = √(20·(N1)60) + 20
- Peck-Hanson-Thornburn (approx.): φ ≈ 27.1 + 0.3·N60 - 0.00054·N60²
- Dr ≈ √((N1)60 / 60) (Skempton, approx.)

## SPT → clay (rough only)
cu ≈ 5 to 6 × N60 (kN/m²) (Stroud: cu ≈ f1·N60, f1 ≈ 4.4-6 depending on PI). Prefer unconfined/triaxial lab tests for clay.
| N60 | Consistency | cu kN/m² |
|---|---|---|
| < 2 | very soft | < 12 |
| 2-4 | soft | 12-25 |
| 4-8 | medium | 25-50 |
| 8-15 | stiff | 50-100 |
| 15-30 | very stiff | 100-200 |
| > 30 | hard | > 200 |

## CPT
- Sand: φ ≈ arctan(0.1 + 0.38·log10(qc/σ'v)) (Kulhawy & Mayne)
- Clay: cu = (qc - σv)/Nk, Nk ≈ 15-20
- Es (sand) ≈ 2.5-3.5 qc (normally consolidated)

## Elastic modulus Es (indicative)
| Soil | Es MN/m² |
|---|---|
| Loose sand | 10-25 |
| Medium sand | 25-50 |
| Dense sand | 50-80 |
| Soft clay | 2-15 |
| Medium clay | 15-30 |
| Stiff clay | 30-100 |
Sand from SPT: Es ≈ 500·(N60 + 15) kN/m² (Bowles, approx.)
Poisson ratio: sand 0.25-0.35, saturated clay undrained 0.5, drained 0.3-0.4.

## Unit weights (indicative, kN/m³)
| Soil | γ dry/moist | γsat |
|---|---|---|
| Loose sand | 16-17 | 18-19 |
| Dense sand | 18-19 | 20-21 |
| Soft clay | 16-17 | 17-18 |
| Stiff clay | 18-19 | 19-20 |
| Fill | 16-18 | - |

## Consolidation parameters
- Cc ≈ 0.009·(LL - 10) (Terzaghi & Peck, normally consolidated clay)
- Cs ≈ Cc/5 to Cc/10
- e0 = w·Gs for saturated soil (Gs ≈ 2.65-2.75)

## Expansive clay indicators (Egypt: e.g. new cities east of Cairo)
PI > 35 and LL > 50, high free swell, swelling pressure from oedometer. High risk → deep founding, replacement, raft with void former, piles below active zone; consult the soil consultant.
