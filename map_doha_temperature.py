"""Entry point — build the Doha Urban Climate Atlas HTML.

Modes
-----
  --demo        Skip GEE.  Produces a fully interactive map using a
                client-side IDW canvas simulation.  No credentials needed.
  (default)     Authenticate with GEE, compute recent seasonal composites
                for Temperature and Greenery, embed real GEE tile URLs.

Flags
-----
  --publish     Also write the output to docs/index.html for GitHub Pages.
  --seasons     Comma-separated subset e.g. "summer,winter"
  --years       Comma-separated years for the GEE composite e.g. "2024,2025"
  --output      Override the output HTML path

Usage examples
--------------
  python map_doha_temperature.py --demo
  python map_doha_temperature.py --demo --publish
  python map_doha_temperature.py                      # full GEE run
  python map_doha_temperature.py --publish            # GEE run + publish
"""

from pathlib import Path
import sys, os

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR      = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

import argparse
import config
import gee_utils
import mapping


# ---------------------------------------------------------------------------
# GEE helpers
# ---------------------------------------------------------------------------

def init_ee(project=None):
    try:
        import ee
        ee.Initialize()
        print("Earth Engine initialized.")
        return
    except Exception as e:
        print(f"Default init failed: {e}")

    project = project or os.getenv("EE_PROJECT", "").strip()
    if project and project != "your-project-id":
        try:
            import ee
            ee.Initialize(project=project)
            print(f"Earth Engine initialized with project={project}")
            return
        except Exception as e2:
            print(f"Project init failed: {e2}")

    try:
        import ee
        print("Attempting ee.Authenticate()…")
        ee.Authenticate()
        ee.Initialize()
        print("Earth Engine ready after authentication.")
    except Exception as auth_err:
        raise RuntimeError(
            "Could not initialize Earth Engine.\n"
            "Set EE_PROJECT=dohaheat, pass --project dohaheat, run `earthengine authenticate`, or use --demo."
        ) from auth_err


def year_label(years):
    if not years:
        years = config.YEARS
    years = sorted(years)
    if len(years) == 1:
        return str(years[0])
    if years == list(range(years[0], years[-1] + 1)):
        return f"{years[0]}-{years[-1]}"
    return ", ".join(str(y) for y in years)


def build_composites(season_keys, years=None):
    """Return {season: {band: ee.Image}} using one multi-band composite per season."""
    label = year_label(years)
    print(f"\nComputing seasonal composites for {label}: {season_keys}")
    composites = {}
    for sk in season_keys:
        print(f"  [{sk}] …", end=" ", flush=True)
        img = gee_utils.create_seasonal_multiband_composite(sk, years)
        composites[sk] = {
            "combined": img,
            "lst": img.select("LST_C"),
            "ndvi": img.select("NDVI"),
        }
        print("done")
    return composites


VIS = {
    "lst":  {
        "min": config.VIS_PARAMS["min"],
        "max": config.VIS_PARAMS["max"],
        "palette": config.VIS_PARAMS["palette"],
    },
    "ndvi": {
        "min": -0.05,
        "max":  0.45,
        "palette": ["#6b3a2a", "#a57c44", "#d4c44a", "#7ec850", "#2e8b57", "#1a5c35"],
    },
}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Build Doha Urban Climate Atlas")
    parser.add_argument("--demo",    action="store_true",
                        help="Skip GEE; use canvas simulation")
    parser.add_argument("--publish", action="store_true",
                        help="Also write output to docs/index.html for GitHub Pages")
    parser.add_argument("--seasons", default=None,
                        help="Comma-separated seasons (summer,autumn,winter,spring)")
    parser.add_argument("--years",   default=None,
                        help="Comma-separated years (e.g. 2024,2025)")
    parser.add_argument("--project", default=None,
                        help="Earth Engine project ID (or set EE_PROJECT)")
    parser.add_argument("--skip-zonal", action="store_true",
                        help="Skip district zonal statistics")
    parser.add_argument("--output",  default=None,
                        help="Override output HTML path")
    args = parser.parse_args()

    out_path = args.output or str(
        PROJECT_ROOT / "outputs" / "maps" / "doha_seasonal_temperature_map.html"
    )
    docs_path = PROJECT_ROOT / "docs" / "index.html"
    geojson_path = PROJECT_ROOT / "data" / "doha_districts.geojson"

    def _save(html):
        mapping.save_map_html(html, out_path)
        print(f"Saved → {out_path}")
        if args.publish:
            mapping.save_map_html(html, docs_path)
            print(f"Published → {docs_path}  (commit docs/ to deploy via GitHub Pages)")

    # ── Demo mode ───────────────────────────────────────────────────────────
    if args.demo:
        print("Demo mode — building canvas-simulated map…")
        html = mapping.build_seasonal_map_html(
            geojson_path=geojson_path,
            composite_label="simulated demo",
        )
        _save(html)
        return

    # ── GEE mode ────────────────────────────────────────────────────────────
    season_keys = list(config.SEASONS.keys())
    if args.seasons:
        season_keys = [s.strip() for s in args.seasons.split(",") if s.strip()]

    years = config.YEARS
    if args.years:
        years = [int(y.strip()) for y in args.years.split(",") if y.strip()]

    project = args.project or os.getenv("EE_PROJECT", "").strip()
    init_ee(project=project)

    composite_years = years if args.years else config.YEARS
    composite_label = year_label(composite_years)
    composites = build_composites(season_keys, composite_years)

    print("\nFetching GEE tile URLs…")
    tile_urls = mapping.extract_tile_urls(composites, VIS)

    # Optional: zonal statistics for richer district tooltips
    zonal = None
    if not args.skip_zonal and geojson_path.exists():
        print("Computing zonal statistics with one batched request per season…")
        zonal = {}
        for sk in season_keys:
            try:
                zonal[sk] = gee_utils.zonal_means(
                    composites[sk]["combined"],
                    geojson_path,
                    ("LST_C", "NDVI"),
                )
            except Exception as e:
                print(f"  Warning: zonal stats failed for {sk}: {e}")
                zonal[sk] = []

    print("Building HTML…")
    html = mapping.build_seasonal_map_html(
        season_year_tile_urls=tile_urls,
        geojson_path=geojson_path,
        zonal_stats=zonal,
        composite_label=composite_label,
    )
    _save(html)
    print("Note: GEE tile tokens expire in ~24 h — re-run to refresh.")


if __name__ == "__main__":
    main()
