from pathlib import Path

# Project configuration and constants
BASE_DIR = Path(__file__).resolve().parent.parent

# Default years to process. Keeping this to two recent seasonal years makes the
# Earth Engine composites and zonal statistics much lighter.
YEARS = [2024, 2025]

# Greater Doha approximate bounding box
BBOX = {
    "xmin": 51.35,
    "ymin": 24.95,
    "xmax": 51.75,
    "ymax": 25.45,
}

# Season definitions: each entry maps season key -> display label + date ranges
# Date ranges are (start_mmdd, end_mmdd) pairs. Winter spans the year boundary
# so it requires special handling in gee_utils (see create_seasonal_composite).
SEASONS = {
    "summer": {
        "label": "Summer",
        "emoji": "☀️",
        "months": "Jun – Sep",
        "date_ranges": [("06-01", "09-30")],
        "cross_year": False,
    },
    "autumn": {
        "label": "Autumn",
        "emoji": "🍂",
        "months": "Oct – Nov",
        "date_ranges": [("10-01", "11-30")],
        "cross_year": False,
    },
    "winter": {
        "label": "Winter",
        "emoji": "❄️",
        "months": "Dec – Feb",
        "date_ranges": [("12-01", "12-31"), ("01-01", "02-28")],
        "cross_year": True,  # Dec of year N + Jan-Feb of year N+1
    },
    "spring": {
        "label": "Spring",
        "emoji": "🌸",
        "months": "Mar – May",
        "date_ranges": [("03-01", "05-31")],
        "cross_year": False,
    },
}

# Legacy alias kept for backward compatibility
SUMMER_START = "-06-01"
SUMMER_END   = "-09-30"

# Filter scenes with cloud cover greater than this (%)
CLOUD_COVER_THRESHOLD = 50

# Visualization parameters for temperature (Celsius)
# Palette maps linearly from `min` to `max` across the listed hex stops.
VIS_PARAMS = {
    "min": 20.0,
    "max": 50.0,
    "palette": [
        "#313695",  # deep blue  → ~20 °C
        "#4575b4",  # blue       → ~26 °C
        "#74add1",  # light blue → ~32 °C
        "#fee090",  # yellow     → ~38 °C
        "#f46d43",  # orange     → ~44 °C
        "#a50026",  # dark red   → ~50 °C
    ],
}

# Output folders
OUTPUTS_DIR = BASE_DIR / "outputs"
MAPS_DIR    = OUTPUTS_DIR / "maps"
IMAGES_DIR  = OUTPUTS_DIR / "images"
DATA_DIR    = BASE_DIR / "data" / "raw"
