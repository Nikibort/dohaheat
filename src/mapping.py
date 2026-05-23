"""
Mapping utilities — generates a self-contained professional HTML map.

Changes from previous version
------------------------------
- Year selector removed; seasons only (Summer / Autumn / Winter / Spring)
- Layer labels: "Temperature" and "Greenery" (was LST / NDVI)
- No emoji anywhere in the UI
- Hover tooltip: district name + 1–2 sentence land-use description
- Click popup: compact 4-season profile, no year trend bars
- 12 non-overlapping district polygons from doha_districts.geojson
- Basemap toggle: Dark | Satellite | Light
"""

import json
from pathlib import Path
import config

# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------

def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _palette_css(stops, direction="to top"):
    n = len(stops)
    parts = [f"{c} {round(100*i/(n-1))}%" for i, c in enumerate(stops)]
    return f"linear-gradient({direction}, {', '.join(parts)})"


def _palette_to_js(stops, t_min, t_max):
    n = len(stops)
    return json.dumps([
        {"t": t_min + i*(t_max-t_min)/(n-1), "rgb": list(_hex_to_rgb(c))}
        for i, c in enumerate(stops)
    ])


# Greenery palette: arid brown → sparse olive → light green → lush dark green
GREENERY_PALETTE = ["#5c3a1e", "#9b7435", "#c8b850", "#7dc86e", "#2e8b57", "#1a5232"]
GREENERY_MIN, GREENERY_MAX = -0.05, 0.45


# ---------------------------------------------------------------------------
# HTML builder
# ---------------------------------------------------------------------------

def build_seasonal_map_html(
    season_year_tile_urls=None,
    season_composites=None,
    geojson_path=None,
    zonal_stats=None,
    composite_label=None,
):
    """Return a fully self-contained HTML string for the seasonal map.

    Parameters
    ----------
    season_year_tile_urls : dict | None
        {season_key: {"lst": url, "ndvi": url}}  (one entry per season,
        no year dimension).  If None, uses client-side IDW canvas.
    season_composites : dict | None   Ignored (kept for API compatibility).
    geojson_path : str | Path | None  Local GeoJSON for district polygons.
    zonal_stats  : dict | None        {season: [{name, lst_mean, ndvi_mean}]}.
    composite_label : str | None      Short UI label for the observation period.
    """
    vis = config.VIS_PARAMS
    t_min, t_max = vis["min"], vis["max"]
    lst_palette   = vis["palette"]

    use_gee = season_year_tile_urls is not None
    if composite_label is None:
        composite_label = f"{config.YEARS[0]}-{config.YEARS[-1]}"

    # Load district GeoJSON ---------------------------------------------------
    if geojson_path is None:
        geojson_path = Path(__file__).parent.parent / "data" / "doha_districts.geojson"
    geojson_path = Path(geojson_path)
    districts_geojson = (
        geojson_path.read_text(encoding="utf-8")
        if geojson_path.exists()
        else '{"type":"FeatureCollection","features":[]}'
    )

    # JS blobs ----------------------------------------------------------------
    seasons_js       = json.dumps({
        k: {"label": v["label"], "months": v["months"]}
        for k, v in config.SEASONS.items()
    })
    tile_urls_js     = json.dumps(season_year_tile_urls or {})
    lst_pal_js       = _palette_to_js(lst_palette, t_min, t_max)
    grn_pal_js       = _palette_to_js(GREENERY_PALETTE, GREENERY_MIN, GREENERY_MAX)
    zonal_js         = json.dumps(zonal_stats or {})
    bbox             = config.BBOX
    cx = (bbox["ymin"] + bbox["ymax"]) / 2
    cy = (bbox["xmin"] + bbox["xmax"]) / 2
    lst_css  = _palette_css(lst_palette)
    grn_css  = _palette_css(GREENERY_PALETTE)

    # IDW canvas control points
    # [lat, lon,  sum_lst, aut_lst, win_lst, spr_lst,  sum_grn, aut_grn, win_grn, spr_grn]
    cp_js = json.dumps([
        [25.32, 51.53,  46, 38, 24, 36,   0.04, 0.05, 0.06, 0.06],  # West Bay
        [25.37, 51.55,  40, 33, 20, 31,   0.08, 0.10, 0.12, 0.10],  # The Pearl
        [25.28, 51.526, 43, 35, 22, 33,   0.07, 0.08, 0.10, 0.09],  # Central Doha
        [25.26, 51.59,  52, 42, 28, 40,   0.02, 0.02, 0.03, 0.03],  # Industrial
        [25.31, 51.46,  41, 34, 21, 32,   0.20, 0.22, 0.25, 0.23],  # Education City
        [25.27, 51.47,  43, 35, 22, 33,   0.12, 0.14, 0.16, 0.15],  # Al Waab
        [25.26, 51.44,  42, 34, 21, 32,   0.22, 0.24, 0.28, 0.26],  # Aspire Zone
        [25.43, 51.49,  47, 39, 25, 37,   0.07, 0.08, 0.10, 0.09],  # Lusail
        [25.17, 51.59,  43, 35, 21, 33,   0.08, 0.10, 0.12, 0.10],  # Al Wakrah
        [25.27, 51.62,  49, 40, 26, 38,   0.03, 0.03, 0.04, 0.04],  # Airport/Thumama
        [25.22, 51.51,  46, 37, 23, 35,   0.04, 0.05, 0.07, 0.06],  # Al Thumama
        [25.22, 51.42,  48, 39, 25, 37,   0.02, 0.03, 0.05, 0.04],  # SW desert
        [25.46, 51.57,  43, 35, 21, 33,   0.04, 0.05, 0.07, 0.06],  # North coast
        [25.20, 51.65,  50, 41, 27, 39,   0.03, 0.03, 0.04, 0.04],  # SE industrial
        [25.38, 51.40,  44, 36, 22, 34,   0.10, 0.12, 0.14, 0.13],  # NW suburban
    ])

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>Doha Urban Climate Atlas</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
:root{{
  --bg:#0a0c14;
  --panel:rgba(10,12,20,0.94);
  --border:rgba(255,255,255,0.09);
  --text:#cdd0e0;
  --muted:rgba(205,208,224,0.42);
  --accent:#e8623a;
}}
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{height:100%;overflow:hidden;background:var(--bg);color:var(--text);
  font-family:'Inter','Segoe UI',system-ui,sans-serif;font-size:13px}}
#map{{position:absolute;inset:0}}

/* ── Top bar ───────────────────────────────────────── */
#topbar{{
  position:absolute;top:0;left:0;right:0;z-index:900;
  height:48px;display:flex;align-items:center;gap:10px;padding:0 14px;
  background:var(--panel);border-bottom:1px solid var(--border);
  backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);
}}
.brand-title{{font-size:13px;font-weight:700;letter-spacing:.2px;flex-shrink:0}}
.brand-sub{{font-size:10px;color:var(--muted);flex-shrink:0}}
.vr{{width:1px;height:26px;background:var(--border);flex-shrink:0}}

/* Season pills */
#season-pills{{display:flex;gap:4px}}
.s-pill{{
  cursor:pointer;border:1.5px solid var(--border);border-radius:16px;
  padding:4px 13px;font-size:12px;font-weight:600;letter-spacing:.2px;
  background:rgba(255,255,255,0.03);color:var(--muted);
  transition:all .15s;user-select:none;white-space:nowrap
}}
.s-pill:hover{{color:var(--text);background:rgba(255,255,255,0.08)}}
.s-pill.active{{color:#fff}}
.s-pill[data-s=summer].active{{background:#c0522a;border-color:#c0522a}}
.s-pill[data-s=autumn].active{{background:#b08020;border-color:#b08020}}
.s-pill[data-s=winter].active{{background:#4a90b8;border-color:#4a90b8}}
.s-pill[data-s=spring].active{{background:#3a8c5a;border-color:#3a8c5a;color:#fff}}

/* Layer + basemap (right side) */
#right-ctrls{{display:flex;align-items:center;gap:6px;margin-left:auto;flex-shrink:0}}
.lyr-btn{{
  cursor:pointer;border:1.5px solid var(--border);border-radius:7px;
  padding:5px 12px;font-size:11px;font-weight:600;
  background:rgba(255,255,255,0.03);color:var(--muted);
  transition:all .15s;user-select:none
}}
.lyr-btn:hover{{color:var(--text);background:rgba(255,255,255,0.08)}}
.lyr-btn.active-t{{background:rgba(200,80,40,.20);border-color:#c05028;color:#e07050}}
.lyr-btn.active-g{{background:rgba(40,130,80,.20);border-color:#2e8b57;color:#5cb87a}}
.bm-group{{display:flex;border:1.5px solid var(--border);border-radius:7px;overflow:hidden}}
.bm-btn{{
  cursor:pointer;padding:5px 10px;font-size:11px;font-weight:600;
  background:rgba(255,255,255,0.03);color:var(--muted);
  border-right:1px solid var(--border);transition:all .15s;user-select:none
}}
.bm-btn:last-child{{border-right:none}}
.bm-btn:hover{{background:rgba(255,255,255,0.08);color:var(--text)}}
.bm-btn.active{{background:rgba(255,255,255,0.16);color:#fff}}

/* ── Legend ────────────────────────────────────────── */
#legend{{
  position:absolute;bottom:28px;left:14px;z-index:800;
  background:var(--panel);border:1px solid var(--border);border-radius:10px;
  padding:12px 14px;backdrop-filter:blur(12px);min-width:110px
}}
#leg-title{{font-size:10px;font-weight:700;letter-spacing:.7px;text-transform:uppercase;
  color:var(--muted);margin-bottom:8px}}
.cb-wrap{{display:flex;gap:7px;align-items:stretch;height:164px}}
.cb-bar{{width:15px;border-radius:3px;flex-shrink:0}}
#cb-t{{background:{lst_css}}}
#cb-g{{background:{grn_css};display:none}}
.cb-ticks{{display:flex;flex-direction:column;justify-content:space-between;
  font-size:10px;color:var(--muted)}}
#leg-note{{margin-top:8px;font-size:9px;color:var(--muted);line-height:1.5;max-width:110px}}

/* ── Info panel ─────────────────────────────────────── */
#infopanel{{
  position:absolute;top:56px;right:14px;z-index:800;
  background:var(--panel);border:1px solid var(--border);border-radius:10px;
  padding:14px 15px;width:220px;backdrop-filter:blur(12px)
}}
#ip-season{{font-size:19px;font-weight:800;line-height:1;margin-bottom:2px}}
#ip-months{{font-size:10px;color:var(--muted);margin-bottom:10px}}
.ip-stat{{display:flex;justify-content:space-between;font-size:11px;
  padding:3px 0;border-bottom:1px solid rgba(255,255,255,.04)}}
.ip-stat:last-of-type{{border:none}}
.ip-val{{font-weight:700}}
#ip-note{{margin-top:10px;font-size:10px;color:var(--muted);line-height:1.55}}

/* ── Hover tooltip ──────────────────────────────────── */
#htip{{
  position:fixed;z-index:2000;pointer-events:none;
  background:rgba(8,10,20,.97);border:1px solid var(--border);
  border-radius:9px;padding:11px 14px;line-height:1.6;
  display:none;max-width:240px;
  box-shadow:0 4px 28px rgba(0,0,0,.65)
}}
.ht-name{{font-size:13px;font-weight:700;margin-bottom:0}}
.ht-ar{{font-size:10px;color:var(--muted);margin-bottom:8px}}
.ht-val{{font-size:22px;font-weight:800;margin-bottom:1px;line-height:1}}
.ht-label{{font-size:10px;color:var(--muted);margin-bottom:8px}}
.ht-desc{{font-size:11px;color:rgba(205,208,224,.72);line-height:1.58}}

/* ── Click popup ────────────────────────────────────── */
.pop{{font-family:'Inter','Segoe UI',system-ui,sans-serif;padding:3px;min-width:200px}}
.pop-name{{font-size:14px;font-weight:800;margin-bottom:1px}}
.pop-ar{{font-size:10px;opacity:.45;margin-bottom:10px}}
.pop-section{{font-size:9px;font-weight:700;letter-spacing:.6px;text-transform:uppercase;
  opacity:.4;margin-bottom:5px}}
.pop-bar{{display:flex;align-items:center;gap:6px;margin-bottom:3px;font-size:11px}}
.pop-bar-label{{width:56px;opacity:.65;flex-shrink:0}}
.pop-bar-track{{flex:1;height:10px;background:rgba(255,255,255,.07);border-radius:2px;overflow:hidden}}
.pop-bar-fill{{height:100%;border-radius:2px}}
.pop-bar-num{{width:38px;text-align:right;font-weight:700}}
.pop-desc{{margin-top:10px;font-size:10px;opacity:.5;line-height:1.55}}
.pop-src{{margin-top:8px;font-size:9px;opacity:.3;line-height:1.4}}

/* ── Loader ─────────────────────────────────────────── */
#loader{{
  position:absolute;inset:0;z-index:3000;background:var(--bg);
  display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px
}}
.ld-ring{{
  width:40px;height:40px;border:3px solid rgba(255,255,255,.07);
  border-top-color:var(--accent);border-radius:50%;
  animation:spin .7s linear infinite
}}
.ld-txt{{font-size:11px;color:var(--muted)}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}

/* ── Leaflet overrides ──────────────────────────────── */
.leaflet-popup-content-wrapper{{
  background:rgba(10,12,22,.97)!important;color:#cdd0e0!important;
  border-radius:10px!important;border:1px solid rgba(255,255,255,.09)!important;
  box-shadow:0 6px 32px rgba(0,0,0,.7)!important
}}
.leaflet-popup-tip{{background:rgba(10,12,22,.97)!important}}
.leaflet-popup-close-button{{color:rgba(205,208,224,.45)!important}}
.leaflet-control-attribution{{font-size:9px!important;background:rgba(0,0,0,.55)!important;
  color:rgba(255,255,255,.3)!important}}
.leaflet-control-zoom a{{
  background:rgba(10,12,22,.94)!important;color:#cdd0e0!important;
  border-color:rgba(255,255,255,.09)!important
}}
</style>
</head>
<body>
<div id="loader"><div class="ld-ring"></div><div class="ld-txt">Rendering satellite layers…</div></div>
<div id="map"></div>

<!-- TOP BAR -->
<div id="topbar">
  <span class="brand-title">Doha Urban Climate Atlas</span>
  <span class="brand-sub">Landsat 8/9 · {composite_label} median land-surface composite</span>
  <div class="vr"></div>
  <div id="season-pills"></div>
  <div id="right-ctrls">
    <div class="lyr-btn active-t" id="btn-t" onclick="setLayer('t')">Surface Heat</div>
    <div class="lyr-btn"          id="btn-g" onclick="setLayer('g')">Greenery</div>
    <div class="bm-group">
      <div class="bm-btn active" id="bm-dark"      onclick="setBasemap('dark')">Dark</div>
      <div class="bm-btn"        id="bm-satellite" onclick="setBasemap('satellite')">Satellite</div>
      <div class="bm-btn"        id="bm-light"     onclick="setBasemap('light')">Light</div>
    </div>
  </div>
</div>

<!-- LEGEND -->
<div id="legend">
  <div id="leg-title">Temp (°C)</div>
  <div class="cb-wrap">
    <div class="cb-bar" id="cb-t"></div>
    <div class="cb-bar" id="cb-g"></div>
    <div class="cb-ticks" id="tick-t"></div>
    <div class="cb-ticks" id="tick-g" style="display:none"></div>
  </div>
  <div id="leg-note">Median seasonal<br>composite from<br>all cloud-free scenes</div>
</div>

<!-- INFO PANEL -->
<div id="infopanel">
  <div id="ip-season"></div>
  <div id="ip-months"></div>
  <div class="ip-stat"><span>Hottest district</span><span class="ip-val" id="ip-hot"></span></div>
  <div class="ip-stat"><span>Coolest district</span><span class="ip-val" id="ip-cool"></span></div>
  <div class="ip-stat"><span>Surface avg</span><span class="ip-val" id="ip-avg"></span></div>
  <div id="ip-note">Hover over a district to read its climate characteristics.</div>
</div>

<!-- HOVER TOOLTIP -->
<div id="htip">
  <div class="ht-name" id="ht-name"></div>
  <div class="ht-ar"   id="ht-ar"></div>
  <div class="ht-val"  id="ht-val"></div>
  <div class="ht-label"id="ht-label"></div>
  <div class="ht-desc" id="ht-desc"></div>
</div>

<script>
// ════════════════════════════════════════════════════
// DATA
// ════════════════════════════════════════════════════
const SEASONS     = {seasons_js};
const SKEYS       = Object.keys(SEASONS);
const TILE_URLS   = {tile_urls_js};
const USE_GEE     = {str(use_gee).lower()};
const ZONAL       = {zonal_js};
const T_PAL       = {lst_pal_js};
const G_PAL       = {grn_pal_js};
const T_MIN={t_min}, T_MAX={t_max};
const G_MIN={GREENERY_MIN}, G_MAX={GREENERY_MAX};
const BBOX={{w:{bbox["xmin"]},e:{bbox["xmax"]},s:{bbox["ymin"]},n:{bbox["ymax"]}}};
const CP_RAW      = {cp_js};
const DISTRICTS   = {districts_geojson};
const S_IDX={{summer:0,autumn:1,winter:2,spring:3}};

const SEASON_STATS={{
  summer:{{hot:"Industrial Area",cool:"The Pearl-Qatar",avg:"44°C",
    note:"Peak summer: industrial surfaces reach 52°C; coastal districts stay near 40°C."}},
  autumn:{{hot:"Industrial Area",cool:"The Pearl-Qatar",avg:"36°C",
    note:"Autumn brings 8–10°C of relief. Coastal and green districts cool fastest."}},
  winter:{{hot:"Industrial Area",cool:"The Pearl-Qatar",avg:"23°C",
    note:"Mild city-wide. Even in winter, industrial surfaces sit above 27°C."}},
  spring:{{hot:"Industrial Area",cool:"The Pearl-Qatar",avg:"34°C",
    note:"Rapid urban warming begins. Dense paved zones heat up ahead of greener areas."}},
}};

// ════════════════════════════════════════════════════
// COLOUR UTILS
// ════════════════════════════════════════════════════
function lerp(a,b,t){{return a+t*(b-a)}}
function palRGB(v,pal,vmin,vmax){{
  const f=Math.max(0,Math.min(1,(v-vmin)/(vmax-vmin)));
  const p=f*(pal.length-1), lo=Math.floor(p), hi=Math.min(pal.length-1,lo+1), a=p-lo;
  const A=pal[lo].rgb, B=pal[hi].rgb;
  return [lerp(A[0],B[0],a),lerp(A[1],B[1],a),lerp(A[2],B[2],a)].map(Math.round);
}}
function hex(r,g,b){{return'#'+[r,g,b].map(v=>v.toString(16).padStart(2,'0')).join('')}}
function tHex(v){{const[r,g,b]=palRGB(v,T_PAL,T_MIN,T_MAX);return hex(r,g,b)}}
function gHex(v){{const[r,g,b]=palRGB(v,G_PAL,G_MIN,G_MAX);return hex(r,g,b)}}
function curHex(v){{return curLayer==='g'?gHex(v):tHex(v)}}

// ════════════════════════════════════════════════════
// IDW CANVAS SIMULATION
// ════════════════════════════════════════════════════
function idw(lat,lon,pts,pw){{
  let ws=0,wt=0;
  for(const p of pts){{
    const dx=(lon-p[1])*Math.cos(lat*Math.PI/180),dy=lat-p[0];
    const d2=dx*dx+dy*dy;
    if(d2<1e-9)return p[2];
    const w=1/Math.pow(d2,pw/2);
    ws+=w*p[2];wt+=w;
  }}
  return ws/wt;
}}
const RES=320;
const cvCache={{}};
function makeCanvas(season,layer){{
  const key=season+layer;
  if(cvCache[key])return cvCache[key];
  const si=S_IDX[season];
  const off=layer==='g'?6:2;
  const pal=layer==='g'?G_PAL:T_PAL;
  const vmin=layer==='g'?G_MIN:T_MIN;
  const vmax=layer==='g'?G_MAX:T_MAX;
  const pts=CP_RAW.map(p=>[p[0],p[1],p[off+si]]);
  const cv=document.createElement('canvas');
  cv.width=RES;cv.height=RES;
  const ctx=cv.getContext('2d');
  const img=ctx.createImageData(RES,RES);
  for(let py=0;py<RES;py++){{
    for(let px=0;px<RES;px++){{
      const lon=BBOX.w+(px/(RES-1))*(BBOX.e-BBOX.w);
      const lat=BBOX.n-(py/(RES-1))*(BBOX.n-BBOX.s);
      const v=idw(lat,lon,pts,layer==='g'?2.6:2.2);
      const[r,g,b]=palRGB(v,pal,vmin,vmax);
      const i=(py*RES+px)*4;
      img.data[i]=r;img.data[i+1]=g;img.data[i+2]=b;img.data[i+3]=192;
    }}
  }}
  ctx.putImageData(img,0,0);
  const url=cv.toDataURL('image/png');
  cvCache[key]=url;
  return url;
}}

// ════════════════════════════════════════════════════
// MAP SETUP
// ════════════════════════════════════════════════════
const map=L.map('map',{{center:[{cx:.4f},{cy:.4f}],zoom:11,
  zoomControl:false,attributionControl:true}});
L.control.zoom({{position:'bottomright'}}).addTo(map);

const BM={{
  dark:L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png',
       {{attribution:'© OpenStreetMap © CARTO',subdomains:'abcd',maxZoom:20}}),
  satellite:L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}',
       {{attribution:'© Esri',maxZoom:20}}),
  light:L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png',
       {{attribution:'© OpenStreetMap © CARTO',subdomains:'abcd',maxZoom:20}}),
}};
BM.dark.addTo(map);
const SW=L.latLng(BBOX.s,BBOX.w),NE=L.latLng(BBOX.n,BBOX.e);
const BOUNDS=L.latLngBounds(SW,NE);

// ════════════════════════════════════════════════════
// STATE
// ════════════════════════════════════════════════════
let curSeason='summer', curLayer='t', activeKey=null;
const ovCache={{}};

function overlayKey(s,l){{return s+'_'+l}}

function getOverlay(s,l){{
  const k=overlayKey(s,l);
  if(ovCache[k])return ovCache[k];
  let ov;
  if(USE_GEE&&TILE_URLS[s]&&TILE_URLS[s][l]){{
    ov=L.tileLayer(TILE_URLS[s][l],{{opacity:0,maxZoom:20,zIndex:5}});
  }}else{{
    ov=L.imageOverlay(makeCanvas(s,l),BOUNDS,{{opacity:0,interactive:false,zIndex:5}});
  }}
  ov.addTo(map);
  ovCache[k]=ov;
  return ov;
}}

function showOverlay(s,l){{
  const k=overlayKey(s,l);
  if(k===activeKey)return;
  if(activeKey&&ovCache[activeKey])fadeOut(ovCache[activeKey]);
  const ov=getOverlay(s,l);
  fadeIn(ov,0.88);
  activeKey=k;
}}

function fadeIn(ov,target){{
  let op=0;
  const id=setInterval(()=>{{op=Math.min(target,op+0.07);ov.setOpacity(op);
    if(op>=target)clearInterval(id);}},14);
}}
function fadeOut(ov){{
  let op=ov.options.opacity||0;
  const id=setInterval(()=>{{op=Math.max(0,op-0.07);ov.setOpacity(op);
    if(op<=0)clearInterval(id);}},14);
}}

// ════════════════════════════════════════════════════
// DISTRICT VALUE LOOKUP
// ════════════════════════════════════════════════════
function distVal(props,s,l){{
  if(ZONAL[s]){{
    const r=(ZONAL[s]||[]).find(x=>x.name===props.name_en||x.name===props.name);
    if(r){{
      const v=l==='g'?r.ndvi_mean:r.lst_mean;
      if(v!==undefined&&v!==null)return v;
    }}
  }}
  // IDW fallback at polygon centroid
  const feat=DISTRICTS.features.find(f=>
    f.properties.name===props.name||f.properties.name_en===props.name_en);
  if(!feat)return null;
  const cs=feat.geometry.coordinates[0];
  let la=0,lo=0;
  for(const[ln,lt] of cs){{la+=lt;lo+=ln;}}
  la/=cs.length;lo/=cs.length;
  const si=S_IDX[s];
  const off=l==='g'?6:2;
  const pts=CP_RAW.map(p=>[p[0],p[1],p[off+si]]);
  return idw(la,lo,pts,l==='g'?2.6:2.2);
}}

// ════════════════════════════════════════════════════
// DISTRICT LAYER
// ════════════════════════════════════════════════════
let distLayer=null;
function buildDistricts(){{
  if(distLayer){{map.removeLayer(distLayer);distLayer=null;}}
  if(!DISTRICTS.features.length)return;
  distLayer=L.geoJSON(DISTRICTS,{{
    style:f=>styleD(f),
    onEachFeature:(f,l)=>{{
      l.on({{
        mouseover:e=>onOver(e,f,l),
        mousemove:e=>moveTip(e.originalEvent),
        mouseout:()=>onOut(l),
        click:()=>onClickD(f),
      }});
    }}
  }}).addTo(map);
}}
function styleD(f){{
  const col='rgba(255,255,255,0.82)';
  return{{color:col,weight:1.8,fillColor:'#ffffff',fillOpacity:0.0}};
}}
function refreshStyles(){{if(distLayer)distLayer.setStyle(f=>styleD(f));}}

function activeValues(s,l){{
  return (DISTRICTS.features||[]).map(f=>distVal(f.properties,s,l))
    .filter(v=>v!==undefined&&v!==null&&!isNaN(v));
}}
function activeAvg(s,l){{
  const vals=activeValues(s,l);
  if(!vals.length)return null;
  return vals.reduce((a,b)=>a+b,0)/vals.length;
}}
function greeneryClass(v){{
  return v<0.05?'very sparse vegetation':v<0.10?'minimal vegetation':
         v<0.16?'low greenery':v<0.22?'moderate greenery':'high greenery';
}}
function climateNote(p,s,l,v){{
  const base=p.description||'';
  if(v===undefined||v===null||isNaN(v))return base;
  const avg=activeAvg(s,l);
  if(l==='g'){{
    const rel=avg==null?'':v>=avg?'above':'below';
    return `This polygon has ${{greeneryClass(v)}}${{avg==null?'':' and is '+rel+' the current district average'}}. ${{base}}`;
  }}
  const ndvi=distVal(p,s,'g');
  const rel=avg==null?'':v>=avg+1?'above':v<=avg-1?'below':'near';
  const relTxt=avg==null?'':rel==='near'
    ?'near the current district average'
    :`${{Math.abs(v-avg).toFixed(1)}}°C ${{rel}} the current district average`;
  const vegTxt=ndvi==null||isNaN(ndvi)?''
    :` The same composite shows ${{greeneryClass(ndvi)}} (NDVI ${{ndvi.toFixed(2)}}), which helps explain the surface heat pattern.`;
  return `This polygon mean is ${{relTxt}}.${{vegTxt}} ${{base}}`;
}}

// ════════════════════════════════════════════════════
// HOVER TOOLTIP
// ════════════════════════════════════════════════════
const htip=document.getElementById('htip');
function onOver(e,f,l){{
  l.setStyle({{color:curLayer==='g'?'#8bdc8f':'#ffd08a',fillOpacity:0.04,weight:2.8}});l.bringToFront();
  const p=f.properties;
  const v=distVal(p,curSeason,curLayer);
  document.getElementById('ht-name').textContent=p.name_en||p.name;
  document.getElementById('ht-ar').textContent=p.name_ar||'';
  if(v!=null){{
    const col=curHex(v);
    if(curLayer==='t'){{
      document.getElementById('ht-val').textContent=v.toFixed(1)+'°C';
      document.getElementById('ht-label').textContent='Surface temperature · '+SEASONS[curSeason].label;
    }}else{{
      // Convert NDVI to qualitative greenery descriptor
      const desc=v<0.05?'Bare / impervious':v<0.10?'Minimal vegetation':
                  v<0.16?'Low greenery':v<0.22?'Moderate greenery':'High greenery';
      document.getElementById('ht-val').textContent=desc;
      document.getElementById('ht-label').textContent='Greenery index ('+v.toFixed(2)+') · '+SEASONS[curSeason].label;
    }}
    document.getElementById('ht-val').style.color=col;
  }}else{{
    document.getElementById('ht-val').textContent='—';
    document.getElementById('ht-val').style.color='var(--muted)';
    document.getElementById('ht-label').textContent='';
  }}
  document.getElementById('ht-desc').textContent=climateNote(p,curSeason,curLayer,v);
  htip.style.display='block';
  moveTip(e.originalEvent);
}}
function moveTip(ev){{
  const w=htip.offsetWidth||240;
  const x=ev.clientX+w+24>window.innerWidth?ev.clientX-w-12:ev.clientX+16;
  htip.style.left=Math.max(8,x)+'px';
  htip.style.top=(ev.clientY-10)+'px';
}}
function onOut(l){{distLayer.resetStyle(l);htip.style.display='none';}}

// ════════════════════════════════════════════════════
// CLICK POPUP — seasonal profile (no year axis)
// ════════════════════════════════════════════════════
function onClickD(f){{
  const p=f.properties;
  const vmin=curLayer==='g'?G_MIN:T_MIN;
  const vmax=curLayer==='g'?G_MAX:T_MAX;

  const bars=SKEYS.map(sk=>{{
    const v=distVal(p,sk,curLayer);
    if(v==null)return'';
    const pct=Math.round(Math.max(0,Math.min(100,(v-vmin)/(vmax-vmin)*100)));
    const col=curHex(v); // uses curLayer
    // Temporarily swap season for colour
    const tmpL=curLayer;
    const lbl=tmpL==='g'
      ?(v<0.05?'Bare':v<0.10?'Minimal':v<0.16?'Low':v<0.22?'Moderate':'High')
      :v.toFixed(1)+'°C';
    return `<div class="pop-bar">
      <div class="pop-bar-label">${{SEASONS[sk].label}}</div>
      <div class="pop-bar-track"><div class="pop-bar-fill" style="width:${{pct}}%;background:${{col}}"></div></div>
      <div class="pop-bar-num" style="color:${{col}}">${{lbl}}</div>
    </div>`;
  }}).join('');

  const layerLabel=curLayer==='g'?'Greenery':'Surface heat';
  const cs=f.geometry.coordinates[0];
  let la=0,lo=0;
  for(const[ln,lt] of cs){{la+=lt;lo+=ln;}}

  L.popup({{maxWidth:248,minWidth:230}})
    .setLatLng([la/cs.length,lo/cs.length])
    .setContent(`<div class="pop">
      <div class="pop-name">${{p.name_en||p.name}}</div>
      <div class="pop-ar">${{p.name_ar||''}}</div>
      <div class="pop-section">${{layerLabel}} by season</div>
      ${{bars}}
      <div class="pop-desc">${{p.description||''}}</div>
      <div class="pop-src">Median Landsat 8/9 land-surface composite · {composite_label} · 30 m resolution ·
        ${{USE_GEE?'Google Earth Engine':'Simulated — run with GEE for real data'}}</div>
    </div>`)
    .openOn(map);
}}

// ════════════════════════════════════════════════════
// STATE SETTERS
// ════════════════════════════════════════════════════
function setSeason(s){{
  curSeason=s;
  document.querySelectorAll('.s-pill').forEach(b=>b.classList.toggle('active',b.dataset.s===s));
  updatePanel();
  showOverlay(s,curLayer);
  refreshStyles();
  map.closePopup();
}}

function setLayer(l){{
  curLayer=l;
  document.getElementById('cb-t').style.display =l==='t'?'block':'none';
  document.getElementById('cb-g').style.display =l==='g'?'block':'none';
  document.getElementById('tick-t').style.display=l==='t'?'flex':'none';
  document.getElementById('tick-g').style.display=l==='g'?'flex':'none';
  document.getElementById('leg-title').textContent=l==='g'?'Greenery':'Temp (°C)';
  document.getElementById('btn-t').className='lyr-btn'+(l==='t'?' active-t':'');
  document.getElementById('btn-g').className='lyr-btn'+(l==='g'?' active-g':'');
  showOverlay(curSeason,l);
  refreshStyles();
  map.closePopup();
}}

function setBasemap(bm){{
  Object.entries(BM).forEach(([k,v])=>{{
    if(k===bm){{if(!map.hasLayer(v))v.addTo(map);v.bringToBack();}}
    else if(map.hasLayer(v))map.removeLayer(v);
  }});
  document.querySelectorAll('.bm-btn').forEach(b=>
    b.classList.toggle('active',b.id==='bm-'+bm));
}}

function updatePanel(){{
  const s=SEASONS[curSeason];
  document.getElementById('ip-season').textContent=s.label;
  document.getElementById('ip-months').textContent=s.months;
  const values=(DISTRICTS.features||[]).map(f=>({{
    name:f.properties.name_en||f.properties.name,
    value:distVal(f.properties,curSeason,'t')
  }})).filter(x=>x.value!==undefined&&x.value!==null&&!isNaN(x.value));
  const st=SEASON_STATS[curSeason];
  if(values.length){{
    const hot=values.reduce((a,b)=>a.value>b.value?a:b);
    const cool=values.reduce((a,b)=>a.value<b.value?a:b);
    const avg=values.reduce((sum,x)=>sum+x.value,0)/values.length;
    document.getElementById('ip-hot').textContent=hot.name;
    document.getElementById('ip-cool').textContent=cool.name;
    document.getElementById('ip-avg').textContent=avg.toFixed(1)+'°C';
    document.getElementById('ip-note').textContent=USE_GEE
      ?'District values are polygon means from the active seasonal composite; hover for local land-use interpretation.'
      :'Demo values use a client-side surface simulation; run with GEE for measured district means.';
  }}else{{
    document.getElementById('ip-hot').textContent=st.hot;
    document.getElementById('ip-cool').textContent=st.cool;
    document.getElementById('ip-avg').textContent=st.avg;
    document.getElementById('ip-note').textContent=st.note;
  }}
}}

// ════════════════════════════════════════════════════
// LEGEND TICKS
// ════════════════════════════════════════════════════
function buildLegend(){{
  [['tick-t',T_MAX,(T_MAX+T_MIN)/2,T_MIN,'°C'],
   ['tick-g',G_MAX,((G_MAX+G_MIN)/2).toFixed(2),G_MIN,'']].forEach(([id,hi,mid,lo,unit])=>{{
    const el=document.getElementById(id);
    [hi,mid,lo].forEach(v=>{{
      const s=document.createElement('span');
      s.textContent=(typeof v==='number'&&!isNaN(v)?v:v)+unit;
      el.appendChild(s);
    }});
  }});
}}

// ════════════════════════════════════════════════════
// BOOT
// ════════════════════════════════════════════════════
window.addEventListener('load',()=>{{
  // Build season pills
  const sp=document.getElementById('season-pills');
  Object.keys(SEASONS).forEach(k=>{{
    const b=document.createElement('div');
    b.className='s-pill';b.dataset.s=k;
    b.textContent=SEASONS[k].label;
    b.onclick=()=>setSeason(k);
    sp.appendChild(b);
  }});

  buildLegend();
  buildDistricts();
  setSeason('summer');
  map.fitBounds(BOUNDS,{{padding:[50,50]}});

  setTimeout(()=>{{
    const ld=document.getElementById('loader');
    ld.style.transition='opacity .45s';ld.style.opacity='0';
    setTimeout(()=>ld.remove(),450);
  }},550);
}});
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------

def save_map_html(html_content, outpath):
    out = Path(outpath)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html_content, encoding="utf-8")
    return out


def extract_tile_urls(season_composites, vis_params):
    """Convert {season: {band: ee.Image}} to {season: {band: url}}."""
    import ee
    urls = {}
    for sk, band_dict in season_composites.items():
        urls[sk] = {}
        for band, img in band_dict.items():
            if band not in vis_params:
                continue
            vp = vis_params.get(band, {})
            map_id = ee.data.getMapId({
                "image": img,
                "min":   str(vp.get("min", 0)),
                "max":   str(vp.get("max", 1)),
                "palette": ",".join(vp.get("palette", [])),
            })
            urls[sk][band] = map_id["tile_fetcher"].url_format
    return urls


def save_map(m, outpath):
    if isinstance(m, str):
        return save_map_html(m, outpath)
    out = Path(outpath)
    out.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(m, "to_html"):
        m.to_html(str(out))
    else:
        m.save(str(out))
    return out
