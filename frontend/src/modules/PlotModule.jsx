import { useState } from "react";
import { PlotMap } from "@/components/PlotMap";
import { Metric, NumField, Section, TextField } from "@/components/Field";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { api, apiError } from "@/lib/api";
import { COMPASS, num } from "@/lib/format";
import { Plus, Trash2 } from "lucide-react";

// Distinct styled layers so envelope, circulation, amenities and packable land stay
// visually separable on the map.
const LAYER_STYLE = {
  envelope: { color: "#16A34A", weight: 2, dashArray: "6 4", fillOpacity: 0.06 },
  ring: { color: "#F59E0B", weight: 1, fillColor: "#F59E0B", fillOpacity: 0.45 },
  driveways: { color: "#D97706", weight: 1, fillColor: "#FBBF24", fillOpacity: 0.5 },
  amenity: { color: "#7C3AED", weight: 1, fillColor: "#A78BFA", fillOpacity: 0.65 },
  residual: { color: "#16A34A", weight: 1, fillColor: "#4ADE80", fillOpacity: 0.35 },
  tower: { color: "#1D4ED8", weight: 1.5, fillColor: "#2563EB", fillOpacity: 0.8 },
};

export default function PlotModule({ project, analysis, update, readOnly }) {
  const plot = project.plot || {};
  const coords = plot.coordinates || [];
  const areas = analysis?.areas;

  const [setbacks, setSetbacks] = useState({ default: 6, front: 9, rear: 4.5, side: 4.5 });
  const [road, setRoad] = useState({ ring_width: 6, driveway_width: 4.5, max_distance_to_road: 45 });
  const [towerCfg, setTowerCfg] = useState({ max_towers: "", floors_min: 4, floors_max: 24 });
  const [layout, setLayout] = useState(null);
  const [layoutError, setLayoutError] = useState("");
  const [running, setRunning] = useState("");

  const setPlot = (key, value) => update((p) => {
    p.plot[key] = value;
    if (key === "coordinates") p.plot.is_placeholder = false;
    setLayout(null);          // geometry changed — the old layout no longer applies
    setLayoutError("");
  });

  const runStage = async (stage) => {
    setRunning(stage);
    setLayoutError("");
    try {
      const { data } = await api.post(`/site-layout/${stage}`, {
        project,
        config: {
          setbacks,
          road,
          // Blank means "as many as the land allows" — only send a real cap.
          towers: {
            floors_min: Number(towerCfg.floors_min) || 4,
            floors_max: Number(towerCfg.floors_max) || 24,
            ...(Number(towerCfg.max_towers) > 0 ? { max_towers: Number(towerCfg.max_towers) } : {}),
          },
        },
      });
      if (data.ok) {
        setLayout(data);
        // Persist a full layout on the project so the 3D view and the map read the same
        // engine output instead of each deriving their own placement.
        if (stage === "plan") update((p) => { p.site_layout = data; });
      } else {
        setLayout(null);
        setLayoutError(data.error?.message || "Could not compute the site layout.");
      }
    } catch (e) {
      setLayout(null);
      setLayoutError(apiError(e.response?.data?.detail));
    } finally {
      setRunning("");
    }
  };

  const overlays = [];
  if (layout) {
    overlays.push({ key: "envelope", polygons: layout.envelope.polygons, style: LAYER_STYLE.envelope,
                    label: `Buildable envelope · ${num(layout.envelope.area_sqm, 0)} m²` });
    if (layout.residual)
      overlays.push({ key: "residual", polygons: layout.residual.polygons, style: LAYER_STYLE.residual,
                      label: `Packable land · ${num(layout.residual.area_sqm, 0)} m²` });
    if (layout.roads) {
      overlays.push({ key: "ring", polygons: layout.roads.ring_polygons, style: LAYER_STYLE.ring,
                      label: `Perimeter access road · ${layout.roads.ring_width_m} m wide` });
      overlays.push({ key: "drive", polygons: layout.roads.driveway_polygons, style: LAYER_STYLE.driveways,
                      label: `Internal driveway · ${layout.roads.driveway_width_m} m wide` });
    }
    (layout.amenities || []).forEach((a) =>
      overlays.push({ key: `amenity-${a.key}`, polygons: a.polygons, style: LAYER_STYLE.amenity,
                      label: `${a.name} · ${num(a.area_sqm, 0)} m² · ${a.floors} floor(s), ${a.height_m} m` }));
    (layout.towers || []).forEach((t, i) =>
      overlays.push({ key: `tower-${i}`, polygons: t.polygons, style: LAYER_STYLE.tower,
                      label: `${t.name} · ${t.floors}F · ${num(t.footprint_sqm, 0)} m² · ${t.units} units` }));
  }

  return (
    <div className="space-y-4">
      {plot.is_placeholder && (
        <p className="text-[11px] text-amber-700 bg-amber-50 border border-amber-200 rounded-sm px-2 py-1" data-testid="plot-placeholder-hint">
          This boundary is an approximate placeholder near the selected city — it is <span className="font-semibold">not</span> your
          actual plot. Draw the real boundary below (or enter corner coordinates further down) so GIS analysis, the 3D model and
          area calculations reflect your actual land.
        </p>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Metric label="Plot area" value={num(areas?.plot_area_sqm, 2)} unit="m²" testid="plot-area-sqm" />
        <Metric label="Plot area" value={num(areas?.plot_area_acres, 4)} unit="acres" testid="plot-area-acres" />
        <Metric label="Vertices" value={coords.length} testid="plot-vertices" />
        <Metric
          label="Orientation"
          value={`${num(plot.orientation_deg, 0)}° ${COMPASS(plot.orientation_deg || 0)}`}
          testid="plot-orientation-metric"
        />
      </div>

      <Section
        title="Plot boundary — draw or drag vertices"
        description="Click 'Draw plot' then click the map to add vertices. Drag a vertex to edit the boundary; area updates live."
        testid="plot-map-section"
      >
        <PlotMap
          coordinates={coords}
          roadEdges={plot.road_edges || []}
          overlays={overlays}
          readOnly={readOnly}
          onChange={(next) => setPlot("coordinates", next)}
        />
      </Section>

      <Section
        title="Site layout engine"
        description="Setbacks are measured inward from the boundary; front applies to edges marked road-facing below, rear is the edge opposite them. Reserve additionally carves the access ring, driveways and amenity blocks out of the envelope."
        testid="site-layout-section"
        actions={
          <div className="flex gap-1.5">
            <Button
              size="sm"
              variant="outline"
              className="h-7 rounded-sm text-xs"
              data-testid="compute-envelope-button"
              disabled={!!running || coords.length < 3}
              onClick={() => runStage("envelope")}
            >
              {running === "envelope" ? "Computing…" : "1 · Envelope"}
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="h-7 rounded-sm text-xs"
              data-testid="compute-reserve-button"
              disabled={!!running || coords.length < 3}
              onClick={() => runStage("reserve")}
            >
              {running === "reserve" ? "Computing…" : "2 · Reserve roads & amenities"}
            </Button>
            <Button
              size="sm"
              className="h-7 rounded-sm text-xs"
              data-testid="compute-plan-button"
              disabled={!!running || readOnly || coords.length < 3}
              onClick={() => runStage("plan")}
            >
              {running === "plan" ? "Packing towers…" : "3 · Generate layout"}
            </Button>
          </div>
        }
      >
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {["default", "front", "rear", "side"].map((k) => (
            <NumField
              key={k}
              label={`Setback — ${k}`}
              suffix="m"
              value={setbacks[k]}
              testid={`setback-${k}-input`}
              onChange={(v) => setSetbacks((s) => ({ ...s, [k]: v }))}
            />
          ))}
          <NumField label="Access ring width" suffix="m" value={road.ring_width} testid="road-ring-width-input"
                    onChange={(v) => setRoad((r) => ({ ...r, ring_width: v }))} />
          <NumField label="Driveway width" suffix="m" value={road.driveway_width} testid="road-driveway-width-input"
                    onChange={(v) => setRoad((r) => ({ ...r, driveway_width: v }))} />
          <NumField label="Max distance to road" suffix="m" value={road.max_distance_to_road}
                    testid="road-max-distance-input"
                    onChange={(v) => setRoad((r) => ({ ...r, max_distance_to_road: v }))} />
          <NumField label="Max residential towers" suffix="blank = max that fits"
                    value={towerCfg.max_towers} testid="tower-max-count-input"
                    onChange={(v) => setTowerCfg((t) => ({ ...t, max_towers: v }))} />
          <NumField label="Min floors" value={towerCfg.floors_min} testid="tower-floors-min-input"
                    onChange={(v) => setTowerCfg((t) => ({ ...t, floors_min: v }))} />
          <NumField label="Max floors" value={towerCfg.floors_max} testid="tower-floors-max-input"
                    onChange={(v) => setTowerCfg((t) => ({ ...t, floors_max: v }))} />
        </div>

        {layoutError && (
          <p className="text-[11px] text-red-700 bg-red-50 border border-red-200 rounded-sm px-2 py-1 mt-3"
             data-testid="layout-error">
            {layoutError}
          </p>
        )}

        {layout && (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-3">
              <Metric label="Envelope area" value={num(layout.envelope.area_sqm, 2)} unit="m²" testid="envelope-area" />
              <Metric label="Of plot area" value={num(layout.envelope.pct_of_plot, 1)} unit="%" testid="envelope-pct" />
              <Metric label="Regions" value={layout.envelope.part_count} testid="envelope-parts" />
              <Metric label="Plot area" value={num(layout.plot.area_sqm, 2)} unit="m²" testid="envelope-plot-area" />
            </div>

            {layout.reservation_summary && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-3">
                <Metric label="Roads reserved" value={num(layout.reservation_summary.road_area_sqm, 2)} unit="m²" testid="reserve-road-area" />
                <Metric label="Amenities" value={num(layout.reservation_summary.amenity_area_sqm, 2)} unit="m²" testid="reserve-amenity-area" />
                <Metric label="Packable land" value={num(layout.residual.area_sqm, 2)} unit="m²" testid="reserve-packable-area" />
                <Metric label="Packable of envelope" value={num(layout.residual.pct_of_envelope, 1)} unit="%" testid="reserve-packable-pct" />
              </div>
            )}

            {layout.layout_metrics && (
              <>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-3">
                  <Metric label="Towers packed" value={layout.layout_metrics.tower_count} testid="layout-tower-count" />
                  <Metric label="Buildable area" value={num(layout.layout_metrics.total_buildable_area_sqm, 0)} unit="m²" testid="layout-buildable-area" />
                  <Metric label="Achieved FAR" value={num(layout.layout_metrics.achieved_far, 3)} unit={`/ ${layout.layout_metrics.far_cap}`} testid="layout-far" />
                  <Metric label="Units" value={layout.layout_metrics.unit_count} testid="layout-units" />
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-3">
                  <Metric label="Ground coverage" value={num(layout.layout_metrics.ground_coverage_pct, 1)} unit="%" testid="layout-coverage" />
                  <Metric label="Open space" value={num(layout.layout_metrics.open_space_pct, 1)} unit="%" testid="layout-open-space" />
                  <Metric label="Total footprint" value={num(layout.layout_metrics.total_footprint_sqm, 0)} unit="m²" testid="layout-footprint" />
                  <Metric label="Constraints" value={layout.layout_metrics.feasible ? "all satisfied" : "violated"} testid="layout-feasible" />
                </div>
                <p className="text-[11px] text-slate-500 mt-2">
                  Saved to the project — the 3D model now renders these towers instead of the bounding-box fallback.
                </p>
              </>
            )}

            {layout.warnings.map((w, i) => (
              <p key={i} className="text-[11px] text-amber-700 bg-amber-50 border border-amber-200 rounded-sm px-2 py-1 mt-2"
                 data-testid={`layout-warning-${i}`}>
                {w}
              </p>
            ))}

            {!!(layout.amenities || []).length && (
              <Table className="mt-3">
                <TableHeader>
                  <TableRow>
                    <TableHead>Amenity</TableHead>
                    <TableHead>Footprint</TableHead>
                    <TableHead>Size</TableHead>
                    <TableHead>Floors</TableHead>
                    <TableHead>Height</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {layout.amenities.map((a) => (
                    <TableRow key={a.key} data-testid={`amenity-row-${a.key}`}>
                      <TableCell className="py-1 text-xs">{a.name}</TableCell>
                      <TableCell className="py-1 font-mono text-xs">{num(a.area_sqm, 1)} m²</TableCell>
                      <TableCell className="py-1 font-mono text-xs">{num(a.width_m, 1)} × {num(a.depth_m, 1)} m</TableCell>
                      <TableCell className="py-1 font-mono text-xs">{a.floors}</TableCell>
                      <TableCell className="py-1 font-mono text-xs">{num(a.height_m, 1)} m</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}

            <Table className="mt-3">
              <TableHeader>
                <TableRow>
                  <TableHead className="w-16">Edge</TableHead>
                  <TableHead>Class</TableHead>
                  <TableHead>Setback</TableHead>
                  <TableHead>Length</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {layout.edges.map((e) => (
                  <TableRow key={e.index} data-testid={`envelope-edge-${e.index}`}>
                    <TableCell className="py-1 font-mono text-xs">{e.index}</TableCell>
                    <TableCell className="py-1 text-xs capitalize">{e.class}</TableCell>
                    <TableCell className="py-1 font-mono text-xs">{num(e.setback_m, 2)} m</TableCell>
                    <TableCell className="py-1 font-mono text-xs">{num(e.length_m, 2)} m</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </>
        )}
      </Section>

      <div className="grid lg:grid-cols-2 gap-4">
        <Section title="Plot dimensions & orientation" testid="plot-dimensions-section">
          <div className="grid grid-cols-2 gap-3">
            <NumField label="Length" suffix="m" value={plot.length} disabled={readOnly} onChange={(v) => setPlot("length", v)} testid="plot-length-input" />
            <NumField label="Width" suffix="m" value={plot.width} disabled={readOnly} onChange={(v) => setPlot("width", v)} testid="plot-width-input" />
            <NumField label="Orientation (from North)" suffix="deg" value={plot.orientation_deg} disabled={readOnly} onChange={(v) => setPlot("orientation_deg", v)} testid="plot-orientation-input" />
            <TextField label="Plot reference" value={project.plot_reference} disabled={readOnly} onChange={(v) => update((p) => { p.plot_reference = v; })} testid="plot-reference-input" />
          </div>
          <p className="text-[11px] text-slate-500 mt-3">
            Length × width is used only when no polygon of 3+ vertices exists. Polygon geometry always takes priority.
          </p>
        </Section>

        <Section
          title="Manual coordinate entry"
          description="Latitude / longitude per vertex"
          testid="plot-coordinates-section"
          actions={
            !readOnly && (
              <Button
                size="sm"
                variant="outline"
                className="h-7 rounded-sm text-xs"
                data-testid="add-vertex-button"
                onClick={() =>
                  setPlot("coordinates", [...coords, coords.length ? [coords[0][0] + 0.0002, coords[0][1] + 0.0002] : [12.9716, 77.5946]])
                }
              >
                <Plus className="h-3 w-3 mr-1" /> Add vertex
              </Button>
            )
          }
        >
          <div className="max-h-[260px] overflow-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-10">#</TableHead>
                  <TableHead>Latitude</TableHead>
                  <TableHead>Longitude</TableHead>
                  <TableHead className="w-10" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {coords.map((c, i) => (
                  <TableRow key={i} data-testid={`vertex-row-${i}`}>
                    <TableCell className="py-1 font-mono text-xs">{i + 1}</TableCell>
                    <TableCell className="py-1">
                      <Input
                        type="number"
                        step="0.000001"
                        disabled={readOnly}
                        className="h-8 font-mono text-xs rounded-sm"
                        data-testid={`vertex-lat-${i}`}
                        value={c[0]}
                        onChange={(e) => setPlot("coordinates", coords.map((p, idx) => (idx === i ? [Number(e.target.value), p[1]] : p)))}
                      />
                    </TableCell>
                    <TableCell className="py-1">
                      <Input
                        type="number"
                        step="0.000001"
                        disabled={readOnly}
                        className="h-8 font-mono text-xs rounded-sm"
                        data-testid={`vertex-lng-${i}`}
                        value={c[1]}
                        onChange={(e) => setPlot("coordinates", coords.map((p, idx) => (idx === i ? [p[0], Number(e.target.value)] : p)))}
                      />
                    </TableCell>
                    <TableCell className="py-1">
                      {!readOnly && (
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-7 px-1 text-red-600"
                          data-testid={`vertex-delete-${i}`}
                          onClick={() => setPlot("coordinates", coords.filter((_, idx) => idx !== i))}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </Section>
      </div>

      <Section
        title="Road access"
        description="Mark plot edges that face a road (edge n connects vertex n to n+1) and the road width."
        testid="road-access-section"
        actions={
          !readOnly && (
            <Button
              size="sm"
              variant="outline"
              className="h-7 rounded-sm text-xs"
              data-testid="add-road-edge-button"
              onClick={() => setPlot("road_edges", [...(plot.road_edges || []), { edge_index: 0, width: 9 }])}
            >
              <Plus className="h-3 w-3 mr-1" /> Add road edge
            </Button>
          )
        }
      >
        {(plot.road_edges || []).length === 0 ? (
          <p className="text-sm text-slate-500">No road-facing edge defined.</p>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {(plot.road_edges || []).map((r, i) => (
              <div key={i} className="border border-slate-200 rounded-sm p-3 space-y-2" data-testid={`road-edge-${i}`}>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono uppercase text-slate-500">Road {i + 1}</span>
                  {!readOnly && (
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-6 px-1 text-red-600"
                      data-testid={`road-edge-delete-${i}`}
                      onClick={() => setPlot("road_edges", plot.road_edges.filter((_, idx) => idx !== i))}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  )}
                </div>
                <NumField
                  label="Edge index"
                  value={r.edge_index}
                  disabled={readOnly}
                  testid={`road-edge-index-${i}`}
                  onChange={(v) => setPlot("road_edges", plot.road_edges.map((x, idx) => (idx === i ? { ...x, edge_index: v } : x)))}
                />
                <NumField
                  label="Road width"
                  suffix="m"
                  value={r.width}
                  disabled={readOnly}
                  testid={`road-edge-width-${i}`}
                  onChange={(v) => setPlot("road_edges", plot.road_edges.map((x, idx) => (idx === i ? { ...x, width: v } : x)))}
                />
              </div>
            ))}
          </div>
        )}
      </Section>

      <Section
        title="Land boundary coordinates"
        description="Optional surveyed boundary points (point name + latitude/longitude) from the survey sketch."
        testid="boundary-points-section"
        actions={
          !readOnly && (
            <Button
              size="sm"
              variant="outline"
              className="h-7 rounded-sm text-xs"
              data-testid="add-boundary-point-button"
              onClick={() => {
                const pts = plot.boundary_points || [];
                const c = plot.center || [12.9716, 77.5946];
                setPlot("boundary_points", [...pts, { point_name: `P${pts.length + 1}`, lat: c[0], lng: c[1] }]);
              }}
            >
              <Plus className="h-3 w-3 mr-1" /> Add point
            </Button>
          )
        }
      >
        {(plot.boundary_points || []).length === 0 ? (
          <p className="text-sm text-slate-500">No surveyed boundary points recorded.</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-40">Point name</TableHead>
                <TableHead>Latitude</TableHead>
                <TableHead>Longitude</TableHead>
                <TableHead className="w-12" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {(plot.boundary_points || []).map((b, i) => {
                const edit = (patch) =>
                  setPlot("boundary_points", plot.boundary_points.map((x, idx) => (idx === i ? { ...x, ...patch } : x)));
                return (
                  <TableRow key={i} data-testid={`boundary-point-${i}`}>
                    <TableCell className="py-1.5">
                      <Input className="h-8 rounded-sm text-sm" value={b.point_name || ""} disabled={readOnly}
                        data-testid={`boundary-name-${i}`} onChange={(e) => edit({ point_name: e.target.value })} />
                    </TableCell>
                    <TableCell className="py-1.5">
                      <Input type="number" step="0.000001" className="h-8 rounded-sm font-mono text-sm"
                        value={b.lat ?? ""} disabled={readOnly} data-testid={`boundary-lat-${i}`}
                        onChange={(e) => edit({ lat: Number(e.target.value) })} />
                    </TableCell>
                    <TableCell className="py-1.5">
                      <Input type="number" step="0.000001" className="h-8 rounded-sm font-mono text-sm"
                        value={b.lng ?? ""} disabled={readOnly} data-testid={`boundary-lng-${i}`}
                        onChange={(e) => edit({ lng: Number(e.target.value) })} />
                    </TableCell>
                    <TableCell className="py-1.5">
                      {!readOnly && (
                        <Button size="sm" variant="ghost" className="h-7 px-1 text-red-600"
                          data-testid={`boundary-delete-${i}`}
                          onClick={() => setPlot("boundary_points", plot.boundary_points.filter((_, idx) => idx !== i))}>
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        )}
        {(plot.boundary_points || []).length >= 3 && !readOnly && (
          <Button size="sm" variant="outline" className="mt-3 h-7 rounded-sm text-xs"
            data-testid="apply-boundary-points-button"
            onClick={() => setPlot("coordinates", plot.boundary_points.map((b) => [Number(b.lat), Number(b.lng)]))}>
            Use these points as the plot boundary
          </Button>
        )}
      </Section>
    </div>
  );
}
