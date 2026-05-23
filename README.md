# Doha Urban Climate Atlas

Interactive map of land surface temperature and vegetation (greenery) across Doha
districts, derived from Landsat 8/9 satellite imagery via Google Earth Engine.

**Live demo** → https://&lt;your-github-username&gt;.github.io/&lt;repo-name&gt;/

---

## What it shows

| Layer | Source | Description |
|---|---|---|
| Surface heat | Landsat 8/9 ST_B10 | Median land surface temperature (°C), all cloud-free scenes |
| Greenery | Landsat 8/9 SR_B4/B5 | Median NDVI (Normalised Difference Vegetation Index), using Collection 2 reflectance scaling |

Four seasonal composites are calculated over two recent default seasonal years
(2024–2025) to keep Earth Engine processing light:
- **Summer** Jun – Sep
- **Autumn** Oct – Nov
- **Winter** Dec – Feb
- **Spring** Mar – May

---

## Quick start (demo mode — no GEE required)

```bash
git clone https://github.com/<you>/<repo>.git
cd doha-urban-heat
pip install -r requirements.txt
python map_doha_temperature.py --demo --publish
# Open docs/index.html in a browser
```

## Full run with Google Earth Engine

```bash
earthengine authenticate          # one-time setup
EE_PROJECT=dohaheat python map_doha_temperature.py --publish
```

If your Earth Engine account does not have a default project, pass it explicitly:

```bash
python map_doha_temperature.py --project dohaheat --publish
```

To process a different observation window:

```bash
python map_doha_temperature.py --project dohaheat --years 2023,2024 --publish
```

The full run calculates district averages with one batched Earth Engine
`reduceRegions()` request per season. Use `--skip-zonal` if you only need tile
layers and want to avoid fetching district statistics.

---

## Project structure

```
doha-urban-heat/
├── src/
│   ├── config.py          # bounding box, seasons, colour palette
│   ├── gee_utils.py       # GEE scene loading, LST/NDVI composites
│   └── mapping.py         # HTML map generator
├── data/
│   └── doha_districts.geojson   # 12 district polygons
├── docs/
│   ├── index.html         # self-contained map (GitHub Pages entry point)
│   └── .nojekyll
├── outputs/maps/          # local build artefacts
├── map_doha_temperature.py
└── requirements.txt
```

## GitHub Pages deployment

1. Push the repository to GitHub.
2. Go to **Settings → Pages → Source → Deploy from a branch → `main` / `docs/`**.
3. The map is live at `https://<user>.github.io/<repo>/`.

Alternatively, the included GitHub Actions workflow (`.github/workflows/pages.yml`)
deploys automatically on every push to `main`.

---

## Requirements

```
earthengine-api
geemap
geopandas
pandas
numpy
matplotlib
folium
```

All mapping output is a single self-contained HTML file with no server-side
dependencies — Leaflet is loaded from CDN.
