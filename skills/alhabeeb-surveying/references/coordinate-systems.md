# Coordinate systems used in Egypt

Check the parameters below against the survey authority / project control sheet before relying on them for setting out. Transformation between datums must use official or project-specific parameters.

## 1. WGS84 / UTM (most common for new projects and GPS work)
- Ellipsoid WGS84; Transverse Mercator; scale factor on central meridian k0 = 0.9996; false easting 500,000 m; false northing 0 (northern hemisphere).
- Zones covering Egypt: 35N (central meridian 27°E, west of 30°E), **36N (CM 33°E, 30°E-36°E — Cairo, Delta, Canal, Red Sea coast)**, 37N (CM 39°E, east of 36°E, far south-east).
- EPSG: 32635, 32636, 32637.
- Cairo-area eastings are ~ 300,000-350,000 m (west of the CM), northings ~ 3,300,000-3,350,000 m.

## 2. Egyptian Transverse Mercator (ETM) belts — old national grid
- Datum: Egypt 1907 (Helmert 1906 ellipsoid). Older cadastral maps, many municipal and land registry plans.
- Three belts:
  | Belt | Central meridian | Latitude of origin | False E | False N | k0 | EPSG |
  |---|---|---|---|---|---|---|
  | Blue belt (east) | 35°E | 30°N | 300,000 | 1,100,000 | 1.0 | 22991 |
  | Red belt (middle) | 31°E | 30°N | 615,000 | 810,000 | 1.0 | 22992 |
  | Purple belt (west) | 27°E | 30°N | 700,000 | 200,000 | 1.0 | 22993 |
  Values are as published in the EPSG registry for Egypt 1907 / Blue, Red, Purple belts — verify against the project's control documentation.
- Cairo is in the Red belt: coordinates look like E ~ 620,000-650,000, N ~ 800,000-830,000 — very different from UTM, so confusion is obvious if you check the magnitude.
- There is also an "Extended Purple belt" variant and the newer Egyptian Geodetic Datum (EGD) / ITRF-based networks; ask the surveyor which applies.

## 3. Local / site grids
Many sites use a local grid (building axes as X-Y, arbitrary origin like 1000/1000 or 5000/5000). Keep a documented transformation: two or more common points with both local and UTM/ETM coordinates → compute rotation, translation and scale (2D Helmert/similarity). Check residuals on a third point.

## Practical notes
- Grid distance vs ground distance: combined scale factor = projection scale factor × elevation factor (R/(R + h), R ≈ 6,371 km). At UTM zone edges the projection scale factor differs from 1 by up to ~1:1,000 — significant for long dimensions; on most building sites in zone 36 the difference is small but check for long infrastructure.
- Levels: Egyptian projects usually use levels relative to mean sea level at Alexandria (national benchmarks). GPS gives ellipsoidal heights — convert with a geoid model or calibrate on benchmarks before using GPS heights.
- Always state on the deliverable: coordinate system, datum, zone/belt, and level datum.
