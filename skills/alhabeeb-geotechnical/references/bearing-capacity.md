# Bearing capacity of shallow foundations

Units: kN, m, kN/m², kN/m³.

## General equation (Meyerhof / Vesic form)

q_ult = c·Nc·sc·dc·ic + q·Nq·sq·dq·iq + 0.5·γ'·B'·Nγ·sγ·dγ·iγ

- c = cohesion (use cu with φ = 0 for undrained clay)
- q = effective overburden at founding level = Σ γ'·h down to depth Df
- B' = effective width (B - 2e for eccentric load), L' = L - 2e_L
- γ' = effective unit weight under the footing (see water table)

## Bearing capacity factors

Nq = e^(π·tanφ) · tan²(45° + φ/2)
Nc = (Nq - 1)·cotφ  (Nc = 5.14 for φ = 0)
Nγ:
- Vesic: Nγ = 2·(Nq + 1)·tanφ
- Meyerhof: Nγ = (Nq - 1)·tan(1.4φ)
- Hansen: Nγ = 1.5·(Nq - 1)·tanφ

Nγ varies a lot between authors; state which you used. The script defaults to Vesic.

| φ° | Nc | Nq | Nγ (Vesic) |
|---|---|---|---|
| 0 | 5.14 | 1.00 | 0.00 |
| 20 | 14.83 | 6.40 | 5.39 |
| 25 | 20.72 | 10.66 | 10.88 |
| 28 | 25.80 | 14.72 | 16.72 |
| 30 | 30.14 | 18.40 | 22.40 |
| 32 | 35.49 | 23.18 | 30.22 |
| 34 | 42.16 | 29.44 | 41.06 |
| 36 | 50.59 | 37.75 | 56.31 |
| 38 | 61.35 | 48.93 | 78.03 |
| 40 | 75.31 | 64.20 | 109.41 |

## Shape factors (Vesic / De Beer)
sc = 1 + (B/L)(Nq/Nc)
sq = 1 + (B/L)·tanφ
sγ = 1 - 0.4(B/L)  (≥ 0.6)
Strip: all = 1. Square/circle: B/L = 1.

## Depth factors (Hansen), k = Df/B if Df/B ≤ 1, else k = arctan(Df/B) in radians
dq = 1 + 2·tanφ·(1 - sinφ)²·k
dc = dq - (1 - dq)/(Nc·tanφ)  (φ > 0);  dc = 1 + 0.4k (φ = 0)
dγ = 1
Many engineers ignore depth factors (conservative) - say which you did.

## Inclination factors (Meyerhof), β = load inclination from vertical
ic = iq = (1 - β°/90)²
iγ = (1 - β/φ)²

## Water table corrections
- Water above founding level (depth Dw < Df): q = γ·Dw + γ'·(Df - Dw); use γ' in the Nγ term.
- Water between founding level and Df + B: γ in the Nγ term = γ' + (d/B)(γ - γ'), d = depth of water below founding level.
- Water deeper than Df + B: no correction.
γ' = γsat - γw, γw = 9.81 kN/m³ (10 for quick checks).

## Undrained clay (φ = 0)
q_ult = 5.14·cu·sc·dc + q, with sc = 1 + 0.2(B/L), dc = 1 + 0.4(Df/B) (Df/B ≤ 1)
Net: q_net,ult = q_ult - q. Check both short term (cu) and long term (c', φ').

## Allowable and net pressure
- q_all (gross) = q_ult / FS. FS = 3 typical for shallow foundations (verify ECP 202).
- q_net,all = (q_ult - q)/FS; compare with net applied pressure (column load + footing + backfill - removed soil, divided by area).
- Final allowable = lesser of the bearing value and the settlement-controlled value.

## Eccentric load
e = M/P. If e ≤ B/6: q_max,min = (P/A)(1 ± 6e/B). If e > B/6: q_max = 4P/(3L(B - 2e)) - avoid in design. Bearing capacity uses B' = B - 2e (Meyerhof effective area).

## Layered soil
If a weak layer lies within about 2B below the footing, check punching through the strong layer or compute bearing on the weak layer with load spread at 2V:1H. State the method.
