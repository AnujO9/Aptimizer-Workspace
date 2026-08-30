"""GIS & site intelligence: Overpass feature detection, Open-Elevation terrain,
flood / wind / sun-path / accessibility analysis, suitability and buildability scoring.

All functions read the plot polygon already stored on the project document
(project["plot"]["coordinates"]) — there is no separate plot model here.
"""
import asyncio
import math
from datetime import datetime, timezone

import requests

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
ELEVATION_URL = "https://api.open-elevation.com/api/v1/lookup"
EARTH_R = 6371000.0


# ------------------------------------------------------------------ geometry
def haversine(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, [a[0], a[1], b[0], b[1]])
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_R * math.asin(math.sqrt(h))


def centroid(coords):
    return [sum(c[0] for c in coords) / len(coords), sum(c[1] for c in coords) / len(coords)]


def bbox(coords, pad_m=0.0):
    lats = [c[0] for c in coords]
    lngs = [c[1] for c in coords]
    lat0 = sum(lats) / len(lats)
    dlat = pad_m / 110540.0
    dlng = pad_m / (111320.0 * max(math.cos(math.radians(lat0)), 0.1))
    return (min(lats) - dlat, min(lngs) - dlng, max(lats) + dlat, max(lngs) + dlng)


def point_in_polygon(pt, coords):
    x, y = pt[1], pt[0]
    inside = False
    n = len(coords)
    for i in range(n):
        y1, x1 = coords[i][0], coords[i][1]
        y2, x2 = coords[(i + 1) % n][0], coords[(i + 1) % n][1]
        if (y1 > y) != (y2 > y):
            xint = x1 + (y - y1) * (x2 - x1) / ((y2 - y1) or 1e-12)
            if x < xint:
                inside = not inside
    return inside


def distance_to_polygon(pt, coords):
    """Distance in metres from a point to the polygon BOUNDARY (0 if inside).

    Measured to each edge, not to the vertices. Vertex-only distance reports a road
    running along the middle of a long edge as being as far away as the corner, which
    then understates road access and flood risk on any plot with long sides.
    """
    if point_in_polygon(pt, coords):
        return 0.0
    lat0 = sum(c[0] for c in coords) / len(coords)
    k = math.cos(math.radians(lat0))

    def xy(c):
        return (c[1] * 111320.0 * k, c[0] * 110540.0)

    px, py = xy(pt)
    best = float("inf")
    n = len(coords)
    for i in range(n):
        ax, ay = xy(coords[i])
        bx, by = xy(coords[(i + 1) % n])
        dx, dy = bx - ax, by - ay
        seg = dx * dx + dy * dy
        # Project the point onto the segment, clamped to its ends.
        t = 0.0 if seg <= 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / seg))
        best = min(best, math.hypot(px - (ax + t * dx), py - (ay + t * dy)))
    return best


def feature_distance(geometry, coords):
    if not geometry:
        return None
    return round(min(distance_to_polygon(p, coords) for p in geometry), 1)


# ------------------------------------------------------------------ overpass
def _overpass_query(bb, radius_m):
    s, w, n, e = bb
    box = f"{s},{w},{n},{e}"
    return f"""[out:json][timeout:40];
(
  way["building"]({box});
  way["highway"~"^(motorway|trunk|primary|secondary|tertiary|residential|unclassified|service|living_street)$"]({box});
  way["leisure"~"^(park|garden|pitch|playground)$"]({box});
  way["landuse"~"^(grass|forest|meadow|recreation_ground|village_green|orchard)$"]({box});
  way["natural"~"^(wood|scrub|water|wetland)$"]({box});
  way["waterway"~"^(river|stream|canal|drain)$"]({box});
  relation["natural"="water"]({box});
  node["public_transport"="station"]({box});
  node["highway"="bus_stop"]({box});
  node["railway"~"^(station|halt|subway_entrance)$"]({box});
);
out geom 900;"""


def _classify(tags):
    if "building" in tags:
        return "buildings"
    if "highway" in tags and tags.get("highway") not in ("bus_stop",):
        return "roads"
    if tags.get("highway") == "bus_stop" or tags.get("public_transport") == "station" or "railway" in tags:
        return "transit"
    if tags.get("natural") in ("water", "wetland") or "waterway" in tags:
        return "water"
    if tags.get("leisure") or tags.get("landuse") or tags.get("natural") in ("wood", "scrub"):
        return "green"
    return None


def fetch_overpass(coords, radius_m):
    bb = bbox(coords, radius_m)
    query = _overpass_query(bb, radius_m)
    last_error = None
    for url in OVERPASS_ENDPOINTS:
        try:
            r = requests.post(url, data={"data": query}, timeout=55,
                              headers={"User-Agent": "Aptimizer/1.0 (site-intelligence)"})
            if r.status_code != 200:
                last_error = f"{url} -> HTTP {r.status_code}"
                continue
            return _parse_overpass(r.json(), coords, radius_m), {"ok": True, "endpoint": url}
        except Exception as exc:  # network / json failure -> try next mirror
            last_error = f"{url} -> {exc}"
    return {"buildings": [], "roads": [], "green": [], "water": [], "transit": []}, {
        "ok": False, "error": last_error or "all Overpass endpoints failed"}


def _parse_overpass(data, coords, radius_m):
    out = {"buildings": [], "roads": [], "green": [], "water": [], "transit": []}
    for el in data.get("elements", []):
        tags = el.get("tags") or {}
        cat = _classify(tags)
        if not cat:
            continue
        if el.get("type") == "node":
            geometry = [[el["lat"], el["lon"]]]
        else:
            geometry = [[g["lat"], g["lon"]] for g in (el.get("geometry") or []) if g.get("lat")]
        if not geometry:
            continue
        dist = feature_distance(geometry, coords)
        if dist is None or dist > radius_m * 1.6:
            continue
        item = {
            "id": str(el.get("id")),
            "name": tags.get("name", ""),
            "kind": tags.get("building") or tags.get("highway") or tags.get("waterway")
            or tags.get("natural") or tags.get("leisure") or tags.get("landuse") or tags.get("railway") or cat,
            "geometry": geometry[:60],
            "distance_m": dist,
            "on_plot": dist == 0.0,
        }
        if cat == "roads":
            item["road_width_m"] = _road_width(tags)
            item["lanes"] = tags.get("lanes", "")
        out[cat].append(item)
    for k in out:
        out[k].sort(key=lambda f: f["distance_m"])
        out[k] = out[k][:120]
    return out


ROAD_WIDTH = {"motorway": 24, "trunk": 18, "primary": 15, "secondary": 12,
              "tertiary": 9, "residential": 7.5, "unclassified": 6, "service": 5, "living_street": 5}


def _road_width(tags):
    if tags.get("width"):
        try:
            return float(str(tags["width"]).split()[0])
        except ValueError:
            pass
    return ROAD_WIDTH.get(tags.get("highway"), 6)


# ------------------------------------------------------------------ elevation
def _sample_points(coords):
    s, w, n, e = bbox(coords)
    grid, profile, ring = [], [], []
    steps = 5
    for i in range(steps):
        for j in range(steps):
            lat = s + (n - s) * (i / (steps - 1))
            lng = w + (e - w) * (j / (steps - 1))
            if point_in_polygon([lat, lng], coords):
                grid.append([round(lat, 6), round(lng, 6)])
    grid += [[round(c[0], 6), round(c[1], 6)] for c in coords]
    for k in range(11):
        profile.append([round(s + (n - s) * k / 10, 6), round(w + (e - w) * k / 10, 6)])
    rs, rw, rn, re = bbox(coords, 250)
    for lat, lng in [(rs, rw), (rs, (rw + re) / 2), (rs, re), ((rs + rn) / 2, rw),
                     ((rs + rn) / 2, re), (rn, rw), (rn, (rw + re) / 2), (rn, re)]:
        ring.append([round(lat, 6), round(lng, 6)])
    return grid, profile, ring


def fetch_elevation(points):
    body = {"locations": [{"latitude": p[0], "longitude": p[1]} for p in points]}
    try:
        r = requests.post(ELEVATION_URL, json=body, timeout=45)
        if r.status_code != 200:
            return None, {"ok": False, "error": f"HTTP {r.status_code}"}
        results = r.json().get("results", [])
        return [float(x.get("elevation") or 0) for x in results], {"ok": True, "endpoint": ELEVATION_URL}
    except Exception as exc:
        return None, {"ok": False, "error": str(exc)}


def terrain_analysis(coords):
    grid, profile, ring = _sample_points(coords)
    all_pts = grid + profile + ring
    elevations, status = fetch_elevation(all_pts)
    if elevations is None or len(elevations) < len(all_pts):
        return {"available": False, "samples": [], "profile": [], "ring_mean_m": None,
                "min_m": None, "max_m": None, "mean_m": None, "relief_m": None,
                "avg_slope_pct": None, "slope_class": "unknown"}, status

    g = elevations[: len(grid)]
    p = elevations[len(grid): len(grid) + len(profile)]
    r = elevations[len(grid) + len(profile):]

    samples = [{"lat": pt[0], "lng": pt[1], "elevation_m": e} for pt, e in zip(grid, g)]
    s_, w_, n_, e_ = bbox(coords)
    horizontal = haversine([s_, w_], [n_, e_]) or 1.0  # plot diagonal extent
    relief = max(g) - min(g)
    slope_pct = round(relief / horizontal * 100, 2)

    start = profile[0]
    prof = [{"distance_m": round(haversine(start, pt), 1), "elevation_m": e} for pt, e in zip(profile, p)]

    return {
        "available": True,
        "samples": samples,
        "profile": prof,
        "ring_mean_m": round(sum(r) / len(r), 2) if r else None,
        "min_m": round(min(g), 2),
        "max_m": round(max(g), 2),
        "mean_m": round(sum(g) / len(g), 2),
        "relief_m": round(relief, 2),
        "horizontal_run_m": round(horizontal, 1),
        "avg_slope_pct": slope_pct,
        "slope_class": ("flat" if slope_pct < 2 else "gentle" if slope_pct < 5
                        else "moderate" if slope_pct < 10 else "steep"),
    }, status


# ------------------------------------------------------------------ flood risk
def flood_risk(terrain, water):
    reasons = []
    score = 0
    nearest_water = water[0]["distance_m"] if water else None
    if nearest_water is not None:
        if nearest_water <= 50:
            score += 45
            reasons.append(f"Water body within {nearest_water:.0f} m of the plot boundary")
        elif nearest_water <= 150:
            score += 30
            reasons.append(f"Water body {nearest_water:.0f} m from the plot")
        elif nearest_water <= 400:
            score += 15
            reasons.append(f"Water body {nearest_water:.0f} m away")
    if terrain.get("available") and terrain.get("ring_mean_m") is not None:
        delta = round(terrain["mean_m"] - terrain["ring_mean_m"], 2)
        if delta <= -2.0:
            score += 40
            reasons.append(f"Plot sits {abs(delta):.1f} m below surrounding ground (low-lying)")
        elif delta <= -0.5:
            score += 22
            reasons.append(f"Plot sits {abs(delta):.1f} m below surrounding ground")
        elif delta >= 1.0:
            reasons.append(f"Plot sits {delta:.1f} m above surrounding ground — good natural drainage")
        if (terrain.get("avg_slope_pct") or 0) < 1.0:
            score += 10
            reasons.append("Very flat terrain (<1% slope) — surface drainage must be engineered")
    else:
        reasons.append("Elevation data unavailable — flood assessment based on water proximity only")
    score = min(score, 100)
    level = "low" if score < 25 else "moderate" if score < 55 else "high"
    return {"score": score, "level": level, "reasons": reasons,
            "nearest_water_m": nearest_water,
            "elevation_delta_m": (round(terrain["mean_m"] - terrain["ring_mean_m"], 2)
                                  if terrain.get("available") and terrain.get("ring_mean_m") is not None else None)}


# ------------------------------------------------------------------ wind
WIND_REGIONS = [
    # (lat_min, lat_max, lng_min, lng_max, label, prevailing, summer, winter, speed)
    (8, 21, 68, 78, "Peninsular west India", "W", "SW (monsoon)", "NE", 3.6),
    (8, 21, 78, 88, "Peninsular east India", "SW", "SW (monsoon)", "NE", 3.2),
    (21, 31, 68, 80, "North-west India", "NW", "SW (monsoon)", "NW", 3.0),
    (21, 31, 80, 90, "Indo-Gangetic plain", "E", "SE (monsoon)", "NW", 2.6),
    (21, 31, 90, 98, "North-east India", "SE", "SW (monsoon)", "NE", 2.4),
    (-10, 8, 60, 100, "Equatorial belt", "SW", "SW", "NE", 3.4),
]


def wind_profile(lat, lng):
    for a, b, c, d, label, prevailing, summer, winter, speed in WIND_REGIONS:
        if a <= lat <= b and c <= lng <= d:
            region, prev, sm, wt, sp = label, prevailing, summer, winter, speed
            break
    else:
        if lat > 30:
            region, prev, sm, wt, sp = "Northern mid-latitude westerlies", "W", "SW", "NW", 4.2
        elif lat < -30:
            region, prev, sm, wt, sp = "Southern mid-latitude westerlies", "W", "NW", "SW", 4.5
        else:
            region, prev, sm, wt, sp = "Tropical trade-wind belt", "E", "SE", "NE", 3.8
    rose = {"N": 6, "NE": 9, "E": 12, "SE": 14, "S": 12, "SW": 18, "W": 16, "NW": 13}
    rose[prev.split()[0]] = 24
    return {"region": region, "prevailing": prev, "summer": sm, "winter": wt,
            "mean_speed_ms": sp, "rose": [{"direction": k, "frequency_pct": v} for k, v in rose.items()],
            "guidance": f"Orient living-room and balcony openings toward {sm.split()[0]} for monsoon cross-ventilation; "
                        f"shelter service cores on the {wt} face."}


# ------------------------------------------------------------------ sun path
# Several zones this app targets are NOT whole-hour offsets, so deriving the offset as
# round(lng/15) puts every solar result half an hour out. India is the worst case: IST is
# +5:30 on the 82.5E meridian, but round(77/15) = 5 for most Indian cities. Boxes are
# generous bounding boxes, checked before the whole-hour fallback.
# Ordered most specific first: the India box overlaps Nepal and Myanmar, so those must be
# tested before it or they inherit IST.
HALF_HOUR_ZONES = [
    (26.3, 30.5, 80.0, 88.3, 5.75),  # Nepal
    (9.0, 28.6, 92.0, 101.2, 6.5),   # Myanmar
    (29.3, 38.5, 60.5, 75.0, 4.5),   # Afghanistan
    (25.0, 40.0, 44.0, 63.4, 3.5),   # Iran
    (6.5, 37.5, 68.0, 97.5, 5.5),    # India + Sri Lanka (IST)
]


def utc_offset_hours(lat, lng):
    """Standard-time UTC offset for a location, honouring half-hour zones."""
    for s, n, w, e, off in HALF_HOUR_ZONES:
        if s <= lat <= n and w <= lng <= e:
            return off
    return float(round(lng / 15.0))


def solar_position(lat, lng, doy, hour_local):
    tz_offset = utc_offset_hours(lat, lng)
    gamma = 2 * math.pi / 365.0 * (doy - 1 + (hour_local - 12) / 24.0)
    eqtime = 229.18 * (0.000075 + 0.001868 * math.cos(gamma) - 0.032077 * math.sin(gamma)
                       - 0.014615 * math.cos(2 * gamma) - 0.040849 * math.sin(2 * gamma))
    decl = (0.006918 - 0.399912 * math.cos(gamma) + 0.070257 * math.sin(gamma)
            - 0.006758 * math.cos(2 * gamma) + 0.000907 * math.sin(2 * gamma)
            - 0.002697 * math.cos(3 * gamma) + 0.00148 * math.sin(3 * gamma))
    time_offset = eqtime + 4 * lng - 60 * tz_offset
    tst = hour_local * 60 + time_offset
    ha = math.radians(tst / 4.0 - 180.0)
    latr = math.radians(lat)
    cos_zen = math.sin(latr) * math.sin(decl) + math.cos(latr) * math.cos(decl) * math.cos(ha)
    cos_zen = max(-1.0, min(1.0, cos_zen))
    zen = math.acos(cos_zen)
    elev = 90 - math.degrees(zen)
    denom = math.sin(zen) * math.cos(latr)
    if abs(denom) < 1e-6:
        az = 180.0
    else:
        sin_az = -math.sin(ha) * math.cos(decl) / math.sin(zen)
        cos_az = (math.sin(decl) - math.sin(latr) * math.cos(zen)) / denom
        az = math.degrees(math.atan2(sin_az, cos_az)) % 360
    return round(az, 2), round(elev, 2)


SUN_DATES = [("summer_solstice", 172, "21 Jun"), ("equinox", 80, "21 Mar"), ("winter_solstice", 355, "21 Dec")]


def sun_events(lat, lng, doy):
    """Sunrise, sunset and daylight length in local clock hours (NOAA solar equations).

    Solved from the sunrise hour angle rather than read off the 30-minute sampling grid
    used to draw the path, which could only ever be right to the nearest half hour.
    Includes the standard -0.833 deg refraction/semi-diameter correction.
    """
    gamma = 2 * math.pi / 365.0 * (doy - 1)
    eqtime = 229.18 * (0.000075 + 0.001868 * math.cos(gamma) - 0.032077 * math.sin(gamma)
                       - 0.014615 * math.cos(2 * gamma) - 0.040849 * math.sin(2 * gamma))
    decl = (0.006918 - 0.399912 * math.cos(gamma) + 0.070257 * math.sin(gamma)
            - 0.006758 * math.cos(2 * gamma) + 0.000907 * math.sin(2 * gamma)
            - 0.002697 * math.cos(3 * gamma) + 0.00148 * math.sin(3 * gamma))
    latr = math.radians(lat)
    cos_ha = ((math.cos(math.radians(90.833)) / (math.cos(latr) * math.cos(decl)))
              - math.tan(latr) * math.tan(decl))
    tz = utc_offset_hours(lat, lng)
    if cos_ha > 1:      # sun never rises
        return {"sunrise_hour": None, "sunset_hour": None, "daylight_hours": 0.0}
    if cos_ha < -1:     # sun never sets
        return {"sunrise_hour": None, "sunset_hour": None, "daylight_hours": 24.0}
    ha = math.degrees(math.acos(cos_ha))
    rise = (720 - 4 * (lng + ha) - eqtime) / 60.0 + tz
    seti = (720 - 4 * (lng - ha) - eqtime) / 60.0 + tz
    return {"sunrise_hour": round(rise, 2), "sunset_hour": round(seti, 2),
            "daylight_hours": round(seti - rise, 2)}


def sun_path(lat, lng, orientation_deg):
    paths = []
    for key, doy, label in SUN_DATES:
        points = []
        for h in [x * 0.5 for x in range(8, 40)]:  # 04:00 -> 19:30
            az, el = solar_position(lat, lng, doy, h)
            if el > 0:
                points.append({"hour": round(h, 1), "azimuth": az, "elevation": el})
        peak = max(points, key=lambda p: p["elevation"]) if points else None
        paths.append({
            "key": key, "label": label,
            "points": points,
            **sun_events(lat, lng, doy),
            "peak_elevation": peak["elevation"] if peak else None,
            "peak_azimuth": peak["azimuth"] if peak else None,
        })
    o = ((orientation_deg or 0) % 360 + 360) % 360
    facades = []
    for name, bearing in [("Front (as drawn)", o), ("Right", (o + 90) % 360),
                          ("Rear", (o + 180) % 360), ("Left", (o + 270) % 360)]:
        eq = next((p for p in paths if p["key"] == "equinox"), None)
        hours = 0
        if eq:
            hours = sum(0.5 for pt in eq["points"] if abs(((pt["azimuth"] - bearing + 180) % 360) - 180) < 90)
        facades.append({
            "facade": name, "bearing_deg": round(bearing, 1),
            "sun_hours_equinox": hours,
            "recommendation": ("Prime daylight — place living rooms and balconies here" if 90 <= bearing <= 180
                               else "Harsh afternoon heat gain — deep shading or service rooms" if 225 <= bearing <= 300
                               else "Soft morning sun — bedrooms work well" if 45 <= bearing < 90
                               else "Low direct gain — good for stairs, cores and utility"),
        })
    return {"latitude": lat, "longitude": lng, "orientation_deg": o, "paths": paths, "facades": facades}


# ------------------------------------------------------------------ solar yield
# Rooftop PV defaults for India. A flat roof needs tilt frames with row spacing to avoid
# self-shading, which is why the area per kWp is roughly 10 m2 and not the ~5 m2 the bare
# module area would suggest.
SOLAR_DEFAULTS = {
    "roof_usable_pct": 60.0,      # lifts, tanks, stairs, AC plant and access paths take the rest
    "sqm_per_kwp": 10.0,          # tilted rows on a flat terrace
    "performance_ratio": 0.78,    # soiling, heat derate, inverter and cable losses
    "cost_per_kwp": 50000.0,      # INR, installed, grid-tied without battery
    "tariff_per_kwh": 8.0,        # INR, displaced residential/common-area tariff
    "degradation_pct_yr": 0.7,
    "life_years": 25,
}

# Clear-sky beam transmittance in the ASHRAE/Meinel air-mass model. The clearness factor
# scales that ideal down to what Indian sites actually see once monsoon cloud and dust are
# in: clear-sky integration alone lands near 2400 kWh/m2/yr, while measured GHI across
# most of India is 1700-2000.
SOLAR_CLEARNESS = 0.80
SOLAR_CONSTANT = 1353.0
DIFFUSE_FRACTION = 0.14           # of the beam component on a horizontal plane

# One representative day per month (the 15th), weighted by that month's length.
_MONTH_DOY = [15, 46, 74, 105, 135, 166, 196, 227, 258, 288, 319, 349]
_MONTH_DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def annual_insolation(lat, lng):
    """Annual global horizontal irradiation, kWh/m2/yr, from the same solar geometry the
    sun path uses.

    Integrated hourly over twelve representative days rather than all 8760 hours: the
    declination barely moves within a month, so the extra 700-odd position calls buy
    nothing a rooftop estimate can use.
    """
    monthly = []
    for doy, days in zip(_MONTH_DOY, _MONTH_DAYS):
        wh = 0.0
        for step in range(48):                       # half-hourly, 00:00 -> 23:30
            hour = step * 0.5
            _, elev = solar_position(lat, lng, doy, hour)
            if elev <= 3:                            # below this, air mass makes it noise
                continue
            am = 1.0 / math.sin(math.radians(elev))
            beam = SOLAR_CONSTANT * (0.7 ** (am ** 0.678))
            horiz = beam * math.sin(math.radians(elev))
            wh += (horiz * (1 + DIFFUSE_FRACTION)) * 0.5    # W/m2 over half an hour
        day_kwh = wh / 1000.0 * SOLAR_CLEARNESS
        monthly.append({"days": days, "kwh_per_sqm_day": round(day_kwh, 2),
                        "kwh_per_sqm_month": round(day_kwh * days, 1)})
    annual = sum(m["kwh_per_sqm_month"] for m in monthly)
    return {"annual_kwh_per_sqm": round(annual, 1),
            "daily_average_kwh_per_sqm": round(annual / 365.0, 2),
            "monthly": monthly}


def solar_potential(lat, lng, roof_area_sqm, config=None):
    """Installable rooftop PV, annual yield and simple payback.

    Payback is against the tariff the generation displaces, undiscounted, and ignores any
    subsidy or net-metering export price -- both vary by state and neither is knowable
    from the project data.
    """
    cfg = {**SOLAR_DEFAULTS, **{k: v for k, v in (config or {}).items() if v is not None}}
    ins = annual_insolation(lat, lng)
    roof = max(float(roof_area_sqm or 0), 0.0)
    usable = roof * cfg["roof_usable_pct"] / 100.0
    kwp = usable / cfg["sqm_per_kwp"] if cfg["sqm_per_kwp"] else 0.0
    # A 1 kWp array is rated at 1000 W/m2, so annual yield is simply the site's kWh/m2
    # times the rating times the performance ratio.
    yield_kwh = kwp * ins["annual_kwh_per_sqm"] * cfg["performance_ratio"]
    capex = kwp * cfg["cost_per_kwp"]
    saving = yield_kwh * cfg["tariff_per_kwh"]
    payback = (capex / saving) if saving > 0 else None

    # Straight-line degradation over the panel life.
    life = int(cfg["life_years"])
    deg = cfg["degradation_pct_yr"] / 100.0
    lifetime_kwh = sum(yield_kwh * max(0.0, 1 - deg * y) for y in range(life))

    return {
        "insolation": ins,
        "roof_area_sqm": round(roof, 2),
        "usable_area_sqm": round(usable, 2),
        "installable_kwp": round(kwp, 2),
        "annual_yield_kwh": round(yield_kwh, 0),
        "specific_yield_kwh_per_kwp": round(yield_kwh / kwp, 0) if kwp else 0,
        "capex_inr": round(capex, 0),
        "annual_saving_inr": round(saving, 0),
        "payback_years": round(payback, 1) if payback else None,
        "lifetime_kwh": round(lifetime_kwh, 0),
        "lifetime_saving_inr": round(lifetime_kwh * cfg["tariff_per_kwh"], 0),
        "co2_avoided_tonnes_per_yr": round(yield_kwh * 0.71 / 1000.0, 1),
        "config": cfg,
    }


# ------------------------------------------------------------------ accessibility
def accessibility(roads, transit, coords, road_edges):
    nearest = roads[0] if roads else None
    widest = max(roads, key=lambda r: r.get("road_width_m") or 0) if roads else None
    within_100 = [r for r in roads if r["distance_m"] <= 100]
    score = 0
    notes = []
    if nearest:
        if nearest["distance_m"] <= 10:
            score += 50
            notes.append(f"Plot abuts a {nearest['kind']} road ({nearest['distance_m']:.0f} m)")
        elif nearest["distance_m"] <= 50:
            score += 38
            notes.append(f"Nearest road {nearest['distance_m']:.0f} m away")
        elif nearest["distance_m"] <= 150:
            score += 22
            notes.append(f"Nearest road {nearest['distance_m']:.0f} m away — access road required")
        else:
            notes.append(f"Nearest mapped road is {nearest['distance_m']:.0f} m away — no direct access")
    else:
        notes.append("No mapped road detected within the search radius")
    if widest and (widest.get("road_width_m") or 0) >= 12:
        score += 20
        notes.append(f"{widest.get('road_width_m')} m wide {widest['kind']} road nearby supports fire-tender access")
    elif widest:
        score += 10
    score += min(len(within_100) * 2, 12)
    nearest_transit = transit[0] if transit else None
    if nearest_transit:
        if nearest_transit["distance_m"] <= 500:
            score += 18
        elif nearest_transit["distance_m"] <= 1000:
            score += 10
        notes.append(f"Nearest transit stop ({nearest_transit['kind']}) {nearest_transit['distance_m']:.0f} m away")
    else:
        notes.append("No transit stop mapped nearby")
    if road_edges:
        score += 6
        notes.append(f"{len(road_edges)} plot edge(s) marked as road-facing in Plot Management")
    score = min(score, 100)
    return {"score": score, "roads_within_100m": len(within_100),
            "nearest_road_m": nearest["distance_m"] if nearest else None,
            "nearest_road_kind": nearest["kind"] if nearest else None,
            "widest_road_m": (widest.get("road_width_m") if widest else None),
            "nearest_transit_m": nearest_transit["distance_m"] if nearest_transit else None,
            "notes": notes}


# ------------------------------------------------------------------ scoring
def suitability(terrain, flood, access, sun):
    slope = terrain.get("avg_slope_pct")
    if slope is None:
        slope_score = 60.0
        slope_note = "Elevation data unavailable — neutral slope score applied"
    else:
        slope_score = max(0.0, min(100.0, 100 - slope * 7))
        slope_note = f"Average slope {slope}% ({terrain.get('slope_class')})"
    flood_score = 100 - flood["score"]
    access_score = float(access["score"])
    best_facade = max(sun["facades"], key=lambda f: f["sun_hours_equinox"]) if sun["facades"] else None
    orientation_score = min(100.0, 55 + (best_facade["sun_hours_equinox"] * 4 if best_facade else 0))

    weights = [("Slope & terrain", slope_score, 0.30, slope_note),
               ("Flood risk", flood_score, 0.25, f"Flood risk {flood['level']} ({flood['score']}/100)"),
               ("Road access", access_score, 0.25,
                f"Access score {access['score']} — nearest road {access['nearest_road_m']} m"),
               ("Orientation & solar", orientation_score, 0.20,
                f"Best facade: {best_facade['facade'] if best_facade else '—'} "
                f"({best_facade['sun_hours_equinox'] if best_facade else 0} sun-hours at equinox)")]
    total = round(sum(v * w for _, v, w, _ in weights), 1)
    return {
        "score": total,
        "grade": "excellent" if total >= 80 else "good" if total >= 65 else "fair" if total >= 50 else "poor",
        "breakdown": [{"factor": n, "score": round(v, 1), "weight_pct": round(w * 100),
                       "contribution": round(v * w, 1), "note": note} for n, v, w, note in weights],
    }


def buildability(terrain, flood, access, features):
    flags = []
    slope = terrain.get("avg_slope_pct")
    if slope is not None and slope >= 10:
        flags.append({"id": "steep_slope", "severity": "critical", "title": "Steep slope",
                      "detail": f"Average slope {slope}% requires terracing, retaining walls and cut-fill balancing."})
    elif slope is not None and slope >= 5:
        flags.append({"id": "moderate_slope", "severity": "warning", "title": "Moderate slope",
                      "detail": f"Average slope {slope}% — stepped foundations and site levelling cost allowance needed."})
    if flood["level"] == "high":
        flags.append({"id": "flood_zone", "severity": "critical", "title": "Elevated flood risk",
                      "detail": "; ".join(flood["reasons"]) + ". Raise plinth and design storm-water retention."})
    elif flood["level"] == "moderate":
        flags.append({"id": "flood_watch", "severity": "warning", "title": "Moderate flood risk",
                      "detail": "; ".join(flood["reasons"])})
    if access["nearest_road_m"] is None or access["nearest_road_m"] > 150:
        flags.append({"id": "no_road_access", "severity": "critical", "title": "No direct road access",
                      "detail": "No mapped road within 150 m — an approach road / right of way is required before construction."})
    elif (access["widest_road_m"] or 0) < 9:
        flags.append({"id": "narrow_road", "severity": "warning", "title": "Narrow access road",
                      "detail": f"Widest nearby road is {access['widest_road_m']} m — check fire-tender and setback bye-laws."})
    on_plot = [b for b in features.get("buildings", []) if b["on_plot"]]
    if on_plot:
        flags.append({"id": "existing_structures", "severity": "warning", "title": f"{len(on_plot)} existing structure(s) on plot",
                      "detail": "Demolition / clearance allowance required before construction."})
    if not flags:
        flags.append({"id": "clear", "severity": "ok", "title": "No hard constraints detected",
                      "detail": "Slope, flood exposure and road access are all within workable limits."})
    return {"flags": flags,
            "buildable": not any(f["severity"] == "critical" for f in flags),
            "critical_count": sum(1 for f in flags if f["severity"] == "critical"),
            "warning_count": sum(1 for f in flags if f["severity"] == "warning")}


# ------------------------------------------------------------------ orchestrator
async def analyse_site(project, radius_m=500):
    plot = project.get("plot") or {}
    coords = plot.get("coordinates") or []
    if len(coords) < 3:
        raise ValueError("Draw a plot polygon with at least 3 vertices in Plot Management first")
    radius_m = max(100, min(int(radius_m or 500), 2000))
    c = centroid(coords)

    (features, ov_status), (terrain, el_status) = await asyncio.gather(
        asyncio.to_thread(fetch_overpass, coords, radius_m),
        asyncio.to_thread(terrain_analysis, coords),
    )
    flood = flood_risk(terrain, features["water"])
    access = accessibility(features["roads"], features["transit"], coords, plot.get("road_edges") or [])
    sun = sun_path(round(c[0], 6), round(c[1], 6), plot.get("orientation_deg") or 0)
    # Roof available for PV is the towers' combined footprint -- the terrace is the
    # footprint, one storey up.
    roof_sqm = sum(float(t.get("footprint_area") or 0) for t in (project.get("towers") or []))
    solar = solar_potential(round(c[0], 6), round(c[1], 6), roof_sqm,
                            (project.get("solar") or {}))
    wind = wind_profile(c[0], c[1])
    suit = suitability(terrain, flood, access, sun)
    build = buildability(terrain, flood, access, features)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "radius_m": radius_m,
        "centroid": [round(c[0], 6), round(c[1], 6)],
        "polygon_signature": _signature(coords),
        "vertices": len(coords),
        "features": features,
        "feature_counts": {k: len(v) for k, v in features.items()},
        "terrain": terrain,
        "flood": flood,
        "wind": wind,
        "sun": sun,
        "solar": solar,
        "accessibility": access,
        "suitability": suit,
        "buildability": build,
        "sources": {"overpass": ov_status, "elevation": el_status},
        "ai_summary": (project.get("gis") or {}).get("ai_summary")
        if (project.get("gis") or {}).get("polygon_signature") == _signature(coords) else None,
    }


def _signature(coords):
    return "|".join(f"{round(c[0], 6)},{round(c[1], 6)}" for c in coords)


def ai_context(project, gis):
    t, f, a, s = gis["terrain"], gis["flood"], gis["accessibility"], gis["suitability"]
    return {
        "project": {"name": project.get("name"), "location": project.get("location"),
                    "client": project.get("client")},
        "plot": {"area_sqm": (project.get("plot") or {}).get("area_hint"),
                 "orientation_deg": (project.get("plot") or {}).get("orientation_deg"),
                 "vertices": gis["vertices"], "centroid": gis["centroid"]},
        "terrain": {k: t.get(k) for k in ("available", "min_m", "max_m", "mean_m", "relief_m",
                                          "avg_slope_pct", "slope_class", "ring_mean_m")},
        "flood": {"level": f["level"], "score": f["score"], "reasons": f["reasons"],
                  "nearest_water_m": f["nearest_water_m"]},
        "accessibility": {k: a.get(k) for k in ("score", "nearest_road_m", "nearest_road_kind",
                                                "widest_road_m", "nearest_transit_m", "roads_within_100m")},
        "wind": {k: gis["wind"].get(k) for k in ("region", "prevailing", "summer", "winter", "mean_speed_ms")},
        "sun": {"facades": gis["sun"]["facades"],
                "daylight_hours": {p["key"]: p["daylight_hours"] for p in gis["sun"]["paths"]}},
        "nearby": gis["feature_counts"],
        "suitability": {"score": s["score"], "grade": s["grade"],
                        "breakdown": [{"factor": b["factor"], "score": b["score"],
                                       "contribution": b["contribution"]} for b in s["breakdown"]]},
        "buildability": gis["buildability"],
    }
