/** Geometry helpers shared by the 3D scene. Converts the stored lat/lng plot polygon
 *  (Plot Management) into local metres so towers, terrain and GIS features share one frame. */

export const R_LAT = 110540;
export const R_LNG = 111320;

export const originOf = (coords) => [
  coords.reduce((s, c) => s + c[0], 0) / coords.length,
  coords.reduce((s, c) => s + c[1], 0) / coords.length,
];

/** [lat, lng] -> [x (east, m), z (south, m)] */
export const toLocal = ([lat, lng], origin) => {
  const k = Math.cos((origin[0] * Math.PI) / 180);
  return [(lng - origin[1]) * R_LNG * k, -(lat - origin[0]) * R_LAT];
};

export const polyToLocal = (coords, origin) => coords.map((c) => toLocal(c, origin));

export const localBounds = (pts) => {
  const xs = pts.map((p) => p[0]);
  const zs = pts.map((p) => p[1]);
  return {
    minX: Math.min(...xs), maxX: Math.max(...xs),
    minZ: Math.min(...zs), maxZ: Math.max(...zs),
    width: Math.max(...xs) - Math.min(...xs),
    depth: Math.max(...zs) - Math.min(...zs),
    cx: (Math.min(...xs) + Math.max(...xs)) / 2,
    cz: (Math.min(...zs) + Math.max(...zs)) / 2,
  };
};

/** Lay towers out on a grid inside the plot bounds (not a single row), leaving a perimeter
 *  setback and real gaps between buildings for fire-tender access, internal roads and parking —
 *  instead of squeezing every tower into one line across the plot. */
export const towerLayout = (towers, bounds) => {
  const n = Math.max(towers.length, 1);
  const setback = Math.min(Math.max(bounds.width, bounds.depth) * 0.08, 9); // perimeter margin, capped ~9m
  const usableW = Math.max(bounds.width - setback * 2, bounds.width * 0.5);
  const usableD = Math.max(bounds.depth - setback * 2, bounds.depth * 0.5);
  const minGap = 6; // minimum clear gap between towers for access/parking, in metres

  // Choose a grid (rows x cols) close to the plot's own aspect ratio so towers fill the
  // plot area rather than stringing out along one axis.
  const aspect = usableW / Math.max(usableD, 1);
  let cols = Math.max(1, Math.round(Math.sqrt(n * aspect)));
  cols = Math.min(cols, n);
  let rows = Math.ceil(n / cols);
  // If a row/col combo leaves a dangling near-empty row, prefer a squarer grid.
  if ((rows - 1) * cols >= n) rows = Math.ceil(n / cols);

  const cellW = usableW / cols;
  const cellD = usableD / rows;

  return towers.map((t, i) => {
    const row = Math.floor(i / cols);
    const col = i % cols;
    const area = Math.max(Number(t.footprint_area) || 400, 40);
    const side = Math.sqrt(area);
    const cx = bounds.minX + setback + cellW * (col + 0.5);
    const cz = bounds.minZ + setback + cellD * (row + 0.5);
    const floors = Math.max(Number(t.floors) || 1, 1);
    const fh = Number(t.floor_height) || 3;
    return {
      id: t.id, name: t.name, x: cx, z: cz,
      w: Math.min(side, cellW - minGap), d: Math.min(side, cellD - minGap),
      floors, floorHeight: fh, height: floors * fh,
      units: t.units || [], rooms: t.rooms || [],
      commonArea: Number(t.common_area) || 0,
    };
  });
};

export const UNIT_COLORS = {
  studio: "#94A3B8",
  "1bhk": "#60A5FA",
  "2bhk": "#2563EB",
  "3bhk": "#F59E0B",
  "4bhk": "#EA580C",
  penthouse: "#7C3AED",
  custom: "#0F172A",
};

export const ROOM_COLORS = {
  living: "#93C5FD",
  bedroom: "#A5B4FC",
  kitchen: "#FCD34D",
  bathroom: "#6EE7B7",
  balcony: "#CBD5E1",
  utility: "#FDBA74",
  common: "#E2E8F0",
};

/** Sun direction vector from azimuth (deg from north, clockwise) and elevation (deg). */
export const sunVector = (azimuth, elevation, dist = 240) => {
  const a = (azimuth * Math.PI) / 180;
  const e = (Math.max(elevation, 1) * Math.PI) / 180;
  return [Math.sin(a) * Math.cos(e) * dist, Math.sin(e) * dist, -Math.cos(a) * Math.cos(e) * dist];
};

/** Interpolate the stored equinox/solstice sun path for an hour of day. */
export const sunAtHour = (sun, hour, pathKey = "equinox") => {
  const path = sun?.paths?.find((p) => p.key === pathKey) || sun?.paths?.[0];
  if (!path || !path.points.length) {
    const el = Math.max(4, 70 - Math.abs(hour - 12) * 9);
    return { azimuth: 90 + (hour - 6) * 15, elevation: el };
  }
  const pts = path.points;
  if (hour <= pts[0].hour) return pts[0];
  if (hour >= pts[pts.length - 1].hour) return pts[pts.length - 1];
  for (let i = 1; i < pts.length; i += 1) {
    if (pts[i].hour >= hour) {
      const a = pts[i - 1];
      const b = pts[i];
      const t = (hour - a.hour) / (b.hour - a.hour || 1);
      return { azimuth: a.azimuth + (b.azimuth - a.azimuth) * t, elevation: a.elevation + (b.elevation - a.elevation) * t };
    }
  }
  return pts[pts.length - 1];
};

/** Grid of terrain heights (metres relative to plot mean) from GIS elevation samples. */
export const terrainHeights = (gis, origin, bounds, seg = 24) => {
  const samples = gis?.terrain?.available ? gis.terrain.samples : [];
  if (!samples.length) return { heights: null, relief: 0 };
  const mean = gis.terrain.mean_m;
  const local = samples.map((s) => {
    const [x, z] = toLocal([s.lat, s.lng], origin);
    return { x, z, h: s.elevation_m - mean };
  });
  const heights = [];
  for (let i = 0; i <= seg; i += 1) {
    for (let j = 0; j <= seg; j += 1) {
      const x = bounds.minX + (bounds.width * j) / seg;
      const z = bounds.minZ + (bounds.depth * i) / seg;
      let wsum = 0;
      let vsum = 0;
      local.forEach((s) => {
        const d2 = (s.x - x) ** 2 + (s.z - z) ** 2 + 1;
        const w = 1 / d2;
        wsum += w;
        vsum += w * s.h;
      });
      heights.push(wsum ? vsum / wsum : 0);
    }
  }
  return { heights, relief: gis.terrain.relief_m, seg };
};

/** Feature footprints (buildings/green/water) converted to local metres. */
export const featureShapes = (gis, origin, key, limit = 60) =>
  (gis?.features?.[key] || []).slice(0, limit).map((f) => {
    const pts = f.geometry.map((g) => toLocal(g, origin));
    const b = localBounds(pts);
    return { id: f.id, name: f.name || f.kind, pts, ...b, distance: f.distance_m };
  });
