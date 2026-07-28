import { PlotMap } from "@/components/PlotMap";
import { Metric, NumField, Section, TextField } from "@/components/Field";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { COMPASS, num } from "@/lib/format";
import { Plus, Trash2 } from "lucide-react";

export default function PlotModule({ project, analysis, update, readOnly }) {
  const plot = project.plot || {};
  const coords = plot.coordinates || [];
  const areas = analysis?.areas;

  const setPlot = (key, value) => update((p) => { p.plot[key] = value; });

  return (
    <div className="space-y-4">
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
          readOnly={readOnly}
          onChange={(next) => setPlot("coordinates", next)}
        />
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
    </div>
  );
}
