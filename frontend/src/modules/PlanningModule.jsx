import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Plus, RefreshCw, Trash2 } from "lucide-react";
import { api, apiError } from "../lib/api";
import { Metric, NumField, Section, TextField } from "../components/Field";
import { FloorPlate } from "../components/FloorPlate";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Slider } from "../components/ui/slider";
import { int, num } from "../lib/format";

const UNIT_TYPES = ["studio", "1bhk", "2bhk", "3bhk", "4bhk", "penthouse", "custom"];
const ROOM_TYPES = ["living", "bedroom", "kitchen", "bathroom", "balcony", "utility", "closet", "entrance", "study", "common"];
const STAIR_TYPES = ["dog-legged", "open-well", "spiral", "straight-flight"];

const uid = () => Math.random().toString(36).slice(2, 10);

export default function PlanningModule({ project, analysis, update, readOnly, projectId, setProject }) {
  const towers = project.towers || [];
  const societyAmenities = project.society_amenities || [];
  const [activeIdx, setActiveIdx] = useState(0);
  const [floor, setFloor] = useState(1);
  const [selectedRoom, setSelectedRoom] = useState(null);
  const t = towers[activeIdx];
  const tm = analysis?.areas?.towers?.[activeIdx];
  const [floorLoading, setFloorLoading] = useState(false);
  const [floorStale, setFloorStale] = useState(false);
  const [floorValidation, setFloorValidation] = useState({});

  const setT = (key, value) => update((p) => { p.towers[activeIdx][key] = value; });
  const setList = (key, list) => setT(key, list);
  const setSocietyAmenities = (list) => update((p) => { p.society_amenities = list; });

  const addTower = async () => {
    try {
      const { data } = await api.post(`/projects/${projectId}/towers`);
      setProject((prev) => ({ ...prev, towers: data.towers }));
      setActiveIdx(data.towers.length - 1);
      toast.success(`${data.tower.name} added`);
    } catch (e) {
      toast.error(apiError(e.response?.data?.detail));
    }
  };

  // Each floor gets its own generated room layout (unit programs + a seeded pack, see
  // backend/layout.py) so floors and towers no longer share one static plan. A floor is
  // only ever regenerated on an explicit click — visiting it the first time fills it in,
  // revisiting it reuses whatever's stored (including hand edits).
  const fetchFloorLayout = async (regenerate = false) => {
    if (!t) return;
    setFloorLoading(true);
    try {
      const { data } = await api.post(`/projects/${projectId}/towers/${t.id}/floor-layout`, { floor, regenerate });
      setProject((prev) => ({ ...prev, towers: data.towers }));
      setFloorStale(!!data.stale);
      setFloorValidation(data.validation || {});
      if (regenerate) toast.success(`Floor ${floor} layout regenerated`);
    } catch (e) {
      toast.error(apiError(e.response?.data?.detail));
    } finally {
      setFloorLoading(false);
    }
  };

  useEffect(() => {
    if (!t) return;
    if (!t.floor_layouts?.[String(floor)]) fetchFloorLayout(false);
  }, [t?.id, floor]);

  if (!t) return <p className="text-sm text-slate-500">No towers defined. Add a tower to begin.</p>;

  const floorRooms = t.floor_layouts?.[String(floor)]?.rooms || [];
  const floorRoomAreaSqm = floorRooms.reduce((s, r) => s + Number(r.w || 0) * Number(r.h || 0), 0);
  const setRooms = (list) => update((p) => {
    const tw = p.towers[activeIdx];
    tw.floor_layouts = tw.floor_layouts || {};
    tw.floor_layouts[String(floor)] = { ...(tw.floor_layouts[String(floor)] || {}), rooms: list };
    if (Number(floor) === 1) tw.rooms = list; // keep engineering calcs / 3D view in sync
  });
  const room = floorRooms.find((r) => r.id === selectedRoom);

  return (
    <div className="space-y-4">
      <Section
        title="Society amenities (shared)"
        description="Entered once for the whole project — clubhouse, gym, pool etc. are shared by every tower, not duplicated per building"
        testid="society-amenities-section"
        actions={
          !readOnly && (
            <Button size="sm" variant="outline" className="h-7 rounded-sm text-xs" data-testid="add-society-amenity-button"
              onClick={() => setSocietyAmenities([...societyAmenities, { id: uid(), name: "New amenity", type: "amenity", area: 50 }])}>
              <Plus className="h-3 w-3 mr-1" /> Add amenity
            </Button>
          )
        }
      >
        {societyAmenities.length === 0 ? (
          <p className="text-sm text-slate-500">No shared amenities yet — add a clubhouse, gym, pool or play area for the whole society.</p>
        ) : (
          <div className="space-y-2">
            {societyAmenities.map((c, i) => (
              <div key={c.id} className="flex items-end gap-2" data-testid={`society-amenity-${i}`}>
                <div className="flex-1">
                  <TextField label="Name" value={c.name} disabled={readOnly} testid={`society-amenity-name-${i}`}
                    onChange={(v) => setSocietyAmenities(societyAmenities.map((x, idx) => (idx === i ? { ...x, name: v } : x)))} />
                </div>
                <div className="w-24">
                  <NumField label="Area" suffix="m²" value={c.area} disabled={readOnly} testid={`society-amenity-area-${i}`}
                    onChange={(v) => setSocietyAmenities(societyAmenities.map((x, idx) => (idx === i ? { ...x, area: v } : x)))} />
                </div>
                {!readOnly && (
                  <Button size="sm" variant="ghost" className="h-9 px-1 text-red-600" data-testid={`society-amenity-delete-${i}`}
                    onClick={() => setSocietyAmenities(societyAmenities.filter((_, idx) => idx !== i))}>
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                )}
              </div>
            ))}
            <div className="text-xs text-slate-500 pt-1 font-mono" data-testid="society-amenity-total">
              Total shared amenity area: {num(societyAmenities.reduce((s, c) => s + Number(c.area || 0), 0), 1)} m²
            </div>
          </div>
        )}
      </Section>

      <Section
        title="Towers"
        description="Define multiple towers on the plot"
        testid="towers-section"
        actions={
          !readOnly && (
            <Button size="sm" className="h-7 rounded-sm text-xs" onClick={addTower} data-testid="add-tower-button">
              <Plus className="h-3 w-3 mr-1" /> Add tower
            </Button>
          )
        }
      >
        <div className="flex gap-2 flex-wrap">
          {towers.map((tw, i) => (
            <button
              key={tw.id}
              onClick={() => { setActiveIdx(i); setFloor(1); }}
              data-testid={`tower-tab-${i}`}
              className={`px-3 py-2 border rounded-sm text-left transition-colors ${
                i === activeIdx ? "border-blue-600 bg-blue-50" : "border-slate-200 bg-white hover:bg-slate-50"
              }`}
            >
              <div className="text-sm font-semibold tracking-tight">{tw.name}</div>
              <div className="text-[11px] font-mono text-slate-500">
                {tw.floors}F · {(tw.units || []).reduce((s, u) => s + Number(u.count || 0), 0)} units/floor
              </div>
            </button>
          ))}
          {towers.length > 1 && !readOnly && (
            <Button
              size="sm"
              variant="outline"
              className="h-auto rounded-sm text-xs text-red-600"
              data-testid="delete-tower-button"
              onClick={() => { update((p) => { p.towers.splice(activeIdx, 1); }); setActiveIdx(0); }}
            >
              <Trash2 className="h-3.5 w-3.5 mr-1" /> Remove {t.name}
            </Button>
          )}
        </div>
      </Section>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <Metric label="Floors" value={int(tm?.floors)} testid="tower-floors-metric" />
        <Metric label="Height" value={num(tm?.height_m, 1)} unit="m" testid="tower-height-metric" />
        <Metric label="Units in tower" value={int(tm?.total_units)} testid="tower-units-metric" />
        <Metric label="Built-up" value={num(tm?.builtup_sqm, 0)} unit="m²" testid="tower-builtup-metric" />
        <Metric label="Core / floor" value={num(tm?.service_core_per_floor_sqm, 1)} unit="m²" testid="tower-core-metric" />
      </div>

      <div className="grid lg:grid-cols-2 gap-4">
        <Section title={`${t.name} — floor planning`} testid="floor-planning-section">
          <div className="grid grid-cols-2 gap-3">
            <TextField label="Tower name" value={t.name} disabled={readOnly} onChange={(v) => setT("name", v)} testid="tower-name-input" />
            <NumField label="Floor count" value={t.floors} disabled={readOnly} onChange={(v) => setT("floors", v)} testid="tower-floors-input" />
            <NumField label="Floor-to-floor height" suffix="m" step={0.1} value={t.floor_height} disabled={readOnly} onChange={(v) => setT("floor_height", v)} testid="tower-floor-height-input" />
            <NumField label="Typical floor plate footprint" suffix="m²" value={t.footprint_area} disabled={readOnly} onChange={(v) => setT("footprint_area", v)} testid="tower-footprint-input" />
            <NumField label="Corridor width" suffix="m" step={0.1} value={t.corridor_width} disabled={readOnly} onChange={(v) => setT("corridor_width", v)} testid="tower-corridor-width-input" />
            <NumField label="Corridor path length" suffix="m" value={t.corridor_length} disabled={readOnly} onChange={(v) => setT("corridor_length", v)} testid="tower-corridor-length-input" />
            <NumField label="Fire exits per floor" value={t.exits_per_floor} disabled={readOnly} onChange={(v) => setT("exits_per_floor", v)} testid="tower-exits-input" />
            <NumField label="Max travel distance to exit" suffix="m" value={t.max_travel_distance} disabled={readOnly} onChange={(v) => setT("max_travel_distance", v)} testid="tower-travel-distance-input" />
          </div>
          <div className="mt-4">
            <div className="flex items-center justify-between text-xs text-slate-500 mb-2">
              <span className="uppercase tracking-wide">Floor selector</span>
              <span className="font-mono" data-testid="active-floor-label">
                Floor {floor} / {t.floors} · level {num((floor - 1) * (t.floor_height || 3), 1)} m
              </span>
            </div>
            <Slider
              min={1}
              max={Math.max(Number(t.floors) || 1, 1)}
              step={1}
              value={[Math.min(floor, Number(t.floors) || 1)]}
              onValueChange={([v]) => setFloor(v)}
              data-testid="floor-slider"
            />
          </div>
        </Section>

        <Section title="Unit mix (per typical floor)" testid="unit-mix-section"
          actions={!readOnly && (
            <Button size="sm" variant="outline" className="h-7 rounded-sm text-xs" data-testid="add-unit-button"
              onClick={() => setList("units", [...(t.units || []), { id: uid(), type: "2bhk", count: 1, carpet_area: 75, balcony_area: 7 }])}>
              <Plus className="h-3 w-3 mr-1" /> Add unit type
            </Button>
          )}>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Type</TableHead>
                <TableHead className="text-right">Count/floor</TableHead>
                <TableHead className="text-right">Carpet m²</TableHead>
                <TableHead className="text-right">Balcony m²</TableHead>
                <TableHead className="w-8" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {(t.units || []).map((u, i) => (
                <TableRow key={u.id} data-testid={`unit-row-${i}`}>
                  <TableCell className="py-1">
                    <Select
                      value={u.type}
                      disabled={readOnly}
                      onValueChange={(v) => setList("units", t.units.map((x, idx) => (idx === i ? { ...x, type: v } : x)))}
                    >
                      <SelectTrigger className="h-8 rounded-sm text-xs" data-testid={`unit-type-${i}`}>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {UNIT_TYPES.map((ut) => (
                          <SelectItem key={ut} value={ut}>{ut.toUpperCase()}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </TableCell>
                  {["count", "carpet_area", "balcony_area"].map((k) => (
                    <TableCell key={k} className="py-1">
                      <Input
                        type="number"
                        disabled={readOnly}
                        className="h-8 font-mono text-xs text-right rounded-sm"
                        data-testid={`unit-${k}-${i}`}
                        value={u[k]}
                        onChange={(e) => setList("units", t.units.map((x, idx) => (idx === i ? { ...x, [k]: Number(e.target.value) } : x)))}
                      />
                    </TableCell>
                  ))}
                  <TableCell className="py-1">
                    {!readOnly && (
                      <Button size="sm" variant="ghost" className="h-7 px-1 text-red-600" data-testid={`unit-delete-${i}`}
                        onClick={() => setList("units", t.units.filter((_, idx) => idx !== i))}>
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <p className="text-[11px] text-slate-500 mt-2">
            Tower total = units/floor × floors = <span className="font-mono">{int(tm?.total_units)}</span> flats,
            carpet <span className="font-mono">{num(tm?.carpet_sqm, 0)} m²</span>.
          </p>
        </Section>
      </div>

      <div className="grid lg:grid-cols-3 gap-4">
        <Section title="Staircases" testid="staircase-section"
          actions={!readOnly && (
            <Button size="sm" variant="outline" className="h-7 rounded-sm text-xs" data-testid="add-staircase-button"
              onClick={() => setList("staircases", [...(t.staircases || []), { id: uid(), count: 1, width: 1.5, type: "dog-legged", location: "core" }])}>
              <Plus className="h-3 w-3" />
            </Button>
          )}>
          {(t.staircases || []).map((s, i) => (
            <div key={s.id} className="border border-slate-200 rounded-sm p-2.5 mb-2 space-y-2" data-testid={`staircase-${i}`}>
              <div className="grid grid-cols-2 gap-2">
                <NumField label="Count" value={s.count} disabled={readOnly} testid={`staircase-count-${i}`}
                  onChange={(v) => setList("staircases", t.staircases.map((x, idx) => (idx === i ? { ...x, count: v } : x)))} />
                <NumField label="Width" suffix="m" step={0.1} value={s.width} disabled={readOnly} testid={`staircase-width-${i}`}
                  onChange={(v) => setList("staircases", t.staircases.map((x, idx) => (idx === i ? { ...x, width: v } : x)))} />
              </div>
              <Select value={s.type} disabled={readOnly}
                onValueChange={(v) => setList("staircases", t.staircases.map((x, idx) => (idx === i ? { ...x, type: v } : x)))}>
                <SelectTrigger className="h-8 rounded-sm text-xs" data-testid={`staircase-type-${i}`}><SelectValue /></SelectTrigger>
                <SelectContent>{STAIR_TYPES.map((st) => <SelectItem key={st} value={st}>{st}</SelectItem>)}</SelectContent>
              </Select>
              <div className="flex items-center justify-between">
                <TextField label="Location" value={s.location} disabled={readOnly} testid={`staircase-location-${i}`}
                  onChange={(v) => setList("staircases", t.staircases.map((x, idx) => (idx === i ? { ...x, location: v } : x)))} />
                {!readOnly && (
                  <Button size="sm" variant="ghost" className="h-7 px-1 mt-4 text-red-600" data-testid={`staircase-delete-${i}`}
                    onClick={() => setList("staircases", t.staircases.filter((_, idx) => idx !== i))}>
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                )}
              </div>
            </div>
          ))}
        </Section>

        <Section title="Lifts" testid="lift-section"
          actions={!readOnly && (
            <Button size="sm" variant="outline" className="h-7 rounded-sm text-xs" data-testid="add-lift-button"
              onClick={() => setList("lifts", [...(t.lifts || []), { id: uid(), count: 1, capacity: 8, location: "core" }])}>
              <Plus className="h-3 w-3" />
            </Button>
          )}>
          {(t.lifts || []).map((l, i) => (
            <div key={l.id} className="border border-slate-200 rounded-sm p-2.5 mb-2 space-y-2" data-testid={`lift-${i}`}>
              <div className="grid grid-cols-2 gap-2">
                <NumField label="Lifts" value={l.count} disabled={readOnly} testid={`lift-count-${i}`}
                  onChange={(v) => setList("lifts", t.lifts.map((x, idx) => (idx === i ? { ...x, count: v } : x)))} />
                <NumField label="Capacity (persons)" value={l.capacity} disabled={readOnly} testid={`lift-capacity-${i}`}
                  onChange={(v) => setList("lifts", t.lifts.map((x, idx) => (idx === i ? { ...x, capacity: v } : x)))} />
              </div>
              <div className="flex items-end justify-between gap-2">
                <TextField label="Location" value={l.location} disabled={readOnly} testid={`lift-location-${i}`}
                  onChange={(v) => setList("lifts", t.lifts.map((x, idx) => (idx === i ? { ...x, location: v } : x)))} />
                {!readOnly && (
                  <Button size="sm" variant="ghost" className="h-8 px-1 text-red-600" data-testid={`lift-delete-${i}`}
                    onClick={() => setList("lifts", t.lifts.filter((_, idx) => idx !== i))}>
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                )}
              </div>
            </div>
          ))}
        </Section>

        <Section title={`Common areas & amenities — ${t.name} only`} testid="common-area-section"
          description="Building-specific spaces for this tower (entrance/lift lobby etc). Shared society-wide amenities like clubhouse, gym or pool go in the Society amenities section above."
          actions={!readOnly && (
            <Button size="sm" variant="outline" className="h-7 rounded-sm text-xs" data-testid="add-common-space-button"
              onClick={() => setList("common_spaces", [...(t.common_spaces || []), { id: uid(), name: "New amenity", type: "amenity", area: 30 }])}>
              <Plus className="h-3 w-3" />
            </Button>
          )}>
          <NumField label="Total common area (used in super built-up)" suffix="m²" value={t.common_area} disabled={readOnly}
            onChange={(v) => setT("common_area", v)} testid="tower-common-area-input" />
          <div className="mt-3 space-y-2">
            {(t.common_spaces || []).map((c, i) => (
              <div key={c.id} className="flex items-end gap-2" data-testid={`common-space-${i}`}>
                <div className="flex-1">
                  <TextField label="Name" value={c.name} disabled={readOnly} testid={`common-space-name-${i}`}
                    onChange={(v) => setList("common_spaces", t.common_spaces.map((x, idx) => (idx === i ? { ...x, name: v } : x)))} />
                </div>
                <div className="w-24">
                  <NumField label="Area" suffix="m²" value={c.area} disabled={readOnly} testid={`common-space-area-${i}`}
                    onChange={(v) => setList("common_spaces", t.common_spaces.map((x, idx) => (idx === i ? { ...x, area: v } : x)))} />
                </div>
                {!readOnly && (
                  <Button size="sm" variant="ghost" className="h-9 px-1 text-red-600" data-testid={`common-space-delete-${i}`}
                    onClick={() => setList("common_spaces", t.common_spaces.filter((_, idx) => idx !== i))}>
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                )}
              </div>
            ))}
          </div>
        </Section>
      </div>

      <Section
        title={`Room planning — ${t.name}, floor ${floor}`}
        description="Procedurally generated per floor from the unit mix above — every unit type gets its own room program, reseeded per floor and per tower. Click a room to hand-edit it."
        testid="room-planning-section"
        actions={
          <div className="flex items-center gap-2">
            {floorStale && (
              <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded-sm bg-amber-50 text-amber-700" data-testid="floor-layout-stale-badge">
                unit mix changed
              </span>
            )}
            {!readOnly && (
              <>
                <Button size="sm" variant="outline" className="h-7 rounded-sm text-xs" data-testid="regenerate-layout-button"
                  disabled={floorLoading} onClick={() => fetchFloorLayout(true)}>
                  <RefreshCw className={`h-3 w-3 mr-1 ${floorLoading ? "animate-spin" : ""}`} /> Regenerate
                </Button>
                <Button size="sm" variant="outline" className="h-7 rounded-sm text-xs" data-testid="add-room-button"
                  onClick={() => setRooms([...floorRooms, { id: uid(), name: "New room", type: "bedroom", x: 0, y: 0, w: 3, h: 3 }])}>
                  <Plus className="h-3 w-3 mr-1" /> Add room
                </Button>
              </>
            )}
          </div>
        }>
        <div className="grid lg:grid-cols-[1fr_320px] gap-4">
          {floorLoading && !floorRooms.length ? (
            <p className="text-sm text-slate-500">Generating floor {floor}…</p>
          ) : (
            <FloorPlate rooms={floorRooms} selectedId={selectedRoom} onSelect={setSelectedRoom} corridor={0} />
          )}
          <div className="space-y-3">
            <div className="border border-slate-200 rounded-sm p-3">
              <div className="text-[11px] uppercase tracking-wide text-slate-500">Floor plate room area</div>
              <div className="font-mono text-lg" data-testid="floor-room-area">{num(floorRoomAreaSqm, 2)} m²</div>
            </div>
            <div className="border border-slate-200 rounded-sm p-3" data-testid="floor-validation-summary">
              <div className="text-[11px] uppercase tracking-wide text-slate-500">Layout validation</div>
              {(() => {
                const unitIds = [...new Set(floorRooms.map((r) => r.unit_id).filter(Boolean))];
                const failing = Object.keys(floorValidation);
                if (!unitIds.length) return <p className="text-xs text-slate-500 mt-1">No units on this floor.</p>;
                return (
                  <>
                    <div className={`font-mono text-sm mt-1 ${failing.length ? "text-amber-700" : "text-emerald-700"}`}>
                      {unitIds.length - failing.length}/{unitIds.length} units passed every schema/adjacency rule
                    </div>
                    {failing.length > 0 && (
                      <ul className="text-[11px] text-slate-600 mt-1.5 space-y-1 max-h-32 overflow-auto">
                        {failing.map((uid) => (
                          <li key={uid}>
                            <span className="font-mono">{uid}</span>: {floorValidation[uid].join("; ")}
                          </li>
                        ))}
                      </ul>
                    )}
                  </>
                );
              })()}
            </div>
            {room ? (
              <div className="border border-slate-200 rounded-sm p-3 space-y-2" data-testid="room-editor">
                <TextField label="Room name" value={room.name} disabled={readOnly} testid="room-name-input"
                  onChange={(v) => setRooms(floorRooms.map((r) => (r.id === room.id ? { ...r, name: v } : r)))} />
                <Select value={room.type} disabled={readOnly}
                  onValueChange={(v) => setRooms(floorRooms.map((r) => (r.id === room.id ? { ...r, type: v } : r)))}>
                  <SelectTrigger className="h-9 rounded-sm text-xs" data-testid="room-type-select"><SelectValue /></SelectTrigger>
                  <SelectContent>{ROOM_TYPES.map((rt) => <SelectItem key={rt} value={rt}>{rt}</SelectItem>)}</SelectContent>
                </Select>
                <div className="grid grid-cols-2 gap-2">
                  {[["w", "Width"], ["h", "Depth"], ["x", "X offset"], ["y", "Y offset"]].map(([k, label]) => (
                    <NumField key={k} label={label} suffix="m" step={0.1} value={room[k]} disabled={readOnly} testid={`room-${k}-input`}
                      onChange={(v) => setRooms(floorRooms.map((r) => (r.id === room.id ? { ...r, [k]: v } : r)))} />
                  ))}
                </div>
                <div className="text-xs text-slate-500 font-mono" data-testid="room-area-readout">
                  Area: {num(Number(room.w) * Number(room.h), 2)} m²
                </div>
                {!readOnly && (
                  <Button size="sm" variant="outline" className="w-full rounded-sm text-xs text-red-600" data-testid="room-delete-button"
                    onClick={() => { setRooms(floorRooms.filter((r) => r.id !== room.id)); setSelectedRoom(null); }}>
                    <Trash2 className="h-3.5 w-3.5 mr-1" /> Delete room
                  </Button>
                )}
              </div>
            ) : (
              <p className="text-sm text-slate-500">Select a room in the diagram to edit it.</p>
            )}
          </div>
        </div>
      </Section>
    </div>
  );
}
