"""
Earth Engine utility functions for the Doha urban heat project.

Supports:
  - Per-year, per-season Landsat 8/9 LST composites
  - Recent-years seasonal median composites
  - NDVI composites using the same scene stack
  - Zonal statistics extraction over neighbourhood polygons
"""
import ee
import config


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def get_doha_geometry():
    """Return an ee.Geometry.Rectangle covering the approximate Doha bbox."""
    b = config.BBOX
    return ee.Geometry.Rectangle([b["xmin"], b["ymin"], b["xmax"], b["ymax"]])


# ---------------------------------------------------------------------------
# Scene-level processing
# ---------------------------------------------------------------------------

def mask_qa_pixel(image):
    """Mask clouds and cloud shadows using QA_PIXEL bit flags (LC08/LC09 C2 L2)."""
    qa = image.select("QA_PIXEL")
    cloud_bit        = 1 << 3
    cloud_shadow_bit = 1 << 4
    mask = (
        qa.bitwiseAnd(cloud_bit).eq(0)
        .And(qa.bitwiseAnd(cloud_shadow_bit).eq(0))
    )
    return image.updateMask(mask)


def add_lst_celsius(image):
    """Convert ST_B10 → °C and add as band LST_C.

    Formula (USGS):  LST_K = ST_B10 × 0.00341802 + 149.0
                     LST_C = LST_K − 273.15
    """
    lst_k = image.select("ST_B10").multiply(0.00341802).add(149.0)
    lst_c = lst_k.subtract(273.15).rename("LST_C")
    return image.addBands(lst_c)


def add_ndvi(image):
    """Compute NDVI from SR_B4 (Red) and SR_B5 (NIR) and add as band NDVI.

    Landsat Collection 2 SR bands include a multiplicative scale and additive
    offset, so apply both before calculating the ratio.
    """
    red = image.select("SR_B4").multiply(0.0000275).add(-0.2)
    nir = image.select("SR_B5").multiply(0.0000275).add(-0.2)
    ndvi = nir.subtract(red).divide(nir.add(red)).rename("NDVI")
    return image.addBands(ndvi)


def preprocess(image):
    """Cloud-mask + add LST_C + add NDVI.  Returns image with both extra bands."""
    return add_ndvi(add_lst_celsius(mask_qa_pixel(image)))


# ---------------------------------------------------------------------------
# Collection loading
# ---------------------------------------------------------------------------

def load_landsat_collections(start_date, end_date, geometry, cloud_thresh=None):
    """Merge Landsat 8 and 9 C2 L2 collections filtered by date, bounds, cloud cover."""
    if cloud_thresh is None:
        cloud_thresh = config.CLOUD_COVER_THRESHOLD

    col8 = (
        ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
        .filterDate(start_date, end_date)
        .filterBounds(geometry)
        .filterMetadata("CLOUD_COVER", "less_than", cloud_thresh)
    )
    col9 = (
        ee.ImageCollection("LANDSAT/LC09/C02/T1_L2")
        .filterDate(start_date, end_date)
        .filterBounds(geometry)
        .filterMetadata("CLOUD_COVER", "less_than", cloud_thresh)
    )
    return col8.merge(col9)


# ---------------------------------------------------------------------------
# Date-range helpers
# ---------------------------------------------------------------------------

def _date_pairs_for_season_year(season_key, year):
    """Return list of (start, end) date strings for one season in one year."""
    season = config.SEASONS[season_key]
    pairs = []
    if season["cross_year"]:
        # December of `year` + Jan–Feb of `year+1`
        pairs.append((f"{year}-12-01", f"{year}-12-31"))
        pairs.append((f"{year+1}-01-01", f"{year+1}-02-28"))
    else:
        for start_md, end_md in season["date_ranges"]:
            pairs.append((f"{year}-{start_md}", f"{year}-{end_md}"))
    return pairs


def _all_date_pairs(season_key, years=None):
    """Return all (start, end) pairs for a season across selected years."""
    if years is None:
        years = config.YEARS
    pairs = []
    for y in years:
        pairs.extend(_date_pairs_for_season_year(season_key, y))
    return pairs


# ---------------------------------------------------------------------------
# Single season × year composites
# ---------------------------------------------------------------------------

def create_season_year_composite(season_key, year, band="LST_C"):
    """Median composite for one season × one year.

    Parameters
    ----------
    season_key : str   One of config.SEASONS keys.
    year       : int   Calendar year (e.g. 2022).
    band       : str   "LST_C" or "NDVI".

    Returns
    -------
    ee.Image  Single-band image clipped to the Doha bbox.
    """
    geometry = get_doha_geometry()
    pairs = _date_pairs_for_season_year(season_key, year)

    cols = [load_landsat_collections(s, e, geometry) for s, e in pairs]
    merged = cols[0]
    for c in cols[1:]:
        merged = merged.merge(c)

    processed = merged.map(preprocess).select(band)
    return processed.median().clip(geometry).rename(band)


# ---------------------------------------------------------------------------
# Seasonal composites averaged across selected years
# ---------------------------------------------------------------------------

def create_seasonal_composite(season_key, years=None, band="LST_C"):
    """Recent-years median composite for a given season.

    Merges every qualifying scene across configured years, applies cloud masking,
    and returns the overall median — averaging out year-to-year variability.

    Parameters
    ----------
    season_key : str          One of config.SEASONS keys.
    years      : list | None  Years to include.  Defaults to config.YEARS.
    band       : str          "LST_C" or "NDVI".

    Returns
    -------
    ee.Image  Single-band image clipped to the Doha bbox.
    """
    geometry  = get_doha_geometry()
    date_pairs = _all_date_pairs(season_key, years)

    cols = [load_landsat_collections(s, e, geometry) for s, e in date_pairs]
    merged = cols[0]
    for c in cols[1:]:
        merged = merged.merge(c)

    processed = merged.map(preprocess).select(band)
    return processed.median().clip(geometry).rename(band)


def create_seasonal_multiband_composite(season_key, years=None, bands=("LST_C", "NDVI")):
    """Recent-years median composite containing both LST and NDVI bands."""
    geometry = get_doha_geometry()
    date_pairs = _all_date_pairs(season_key, years)

    cols = [load_landsat_collections(s, e, geometry) for s, e in date_pairs]
    merged = cols[0]
    for c in cols[1:]:
        merged = merged.merge(c)

    processed = merged.map(preprocess).select(list(bands))
    return processed.median().clip(geometry).rename(list(bands))


def create_all_seasonal_composites(years=None, band="LST_C"):
    """Create multi-year composites for all four seasons.

    Returns
    -------
    dict[str, ee.Image]
    """
    return {
        key: create_seasonal_composite(key, years, band)
        for key in config.SEASONS
    }


# ---------------------------------------------------------------------------
# Full season × year matrix
# ---------------------------------------------------------------------------

def create_season_year_matrix(season_keys=None, years=None, band="LST_C"):
    """Compute composites for every season × year combination.

    Returns
    -------
    dict[season_key, dict[year, ee.Image]]
    """
    if season_keys is None:
        season_keys = list(config.SEASONS.keys())
    if years is None:
        years = config.YEARS

    matrix = {}
    for sk in season_keys:
        matrix[sk] = {}
        for yr in years:
            print(f"  [{sk}] {yr} …")
            matrix[sk][yr] = create_season_year_composite(sk, yr, band)
    return matrix


# ---------------------------------------------------------------------------
# Zonal statistics (neighbourhood averages from GEE)
# ---------------------------------------------------------------------------

def _geojson_feature_collection(geojson_path):
    """Convert a local GeoJSON FeatureCollection into an ee.FeatureCollection."""
    import json

    with open(geojson_path, encoding="utf-8") as f:
        raw_geojson = json.load(f)

    features = []
    for feat in raw_geojson.get("features", []):
        props = feat.get("properties", {})
        features.append(
            ee.Feature(
                ee.Geometry(feat["geometry"]),
                {
                    "name": props.get("name_en") or props.get("name", ""),
                    "name_en": props.get("name_en") or props.get("name", ""),
                    "name_ar": props.get("name_ar", ""),
                },
            )
        )
    return ee.FeatureCollection(features)


def zonal_means(image, geojson_path, bands=("LST_C", "NDVI"), scale=30):
    """Extract per-polygon means for one or more bands in a single GEE request.

    Parameters
    ----------
    image        : ee.Image
    geojson_path : str or Path   Local GeoJSON FeatureCollection.
    bands        : sequence[str]  Band names to reduce.
    scale        : int           Landsat pixel size (m).

    Returns
    -------
    list[dict]  One dict per feature with name and available mean fields.
    """
    bands = list(bands)
    fc = _geojson_feature_collection(geojson_path)
    reduced = image.select(bands).reduceRegions(
        collection=fc,
        reducer=ee.Reducer.mean(),
        scale=scale,
        tileScale=4,
        maxPixelsPerRegion=1e8,
    )

    results = []
    for feat in reduced.getInfo().get("features", []):
        props = feat.get("properties", {})
        row = {"name": props.get("name_en") or props.get("name", "")}
        if "LST_C" in bands:
            row["lst_mean"] = props.get("LST_C")
        if "NDVI" in bands:
            row["ndvi_mean"] = props.get("NDVI")
        for band in bands:
            row.setdefault(band, props.get(band))
        results.append(row)
    return results


def zonal_mean(image, geojson_path, band, scale=30):
    """Backward-compatible single-band wrapper around batched zonal stats."""
    rows = zonal_means(image, geojson_path, (band,), scale)
    return [
        {
            "name": row["name"],
            "mean_value": row.get(band),
        }
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Legacy aliases
# ---------------------------------------------------------------------------

def create_yearly_summer_median_lst(year):
    """Legacy: single-year summer LST composite."""
    return create_season_year_composite("summer", year, "LST_C")


def create_multi_year_composites(years=None):
    """Legacy: per-year summer composites as a flat dict {year: ee.Image}."""
    if years is None:
        years = config.YEARS
    return {y: create_yearly_summer_median_lst(y) for y in years}
