import { useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Html, Line, OrbitControls, PointerLockControls } from "@react-three/drei";
import * as THREE from "three";
import { Box, Compass, Eye, Layers, Move3d, Scissors, SunMedium } from "lucide-react";
import { Section } from "@/components/Field";
import { FloorPlate } from "@/components/FloorPlate";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  ROOM_COLORS, UNIT_COLORS, featureShapes, localBounds, originOf, polyToLocal, sunAtHour, sunVector,
  terrainHeights, towerLayout,
} from "@/lib/scene";
import { money, num } from "@/lib/format";

const TOWER_RULE_PARAMS = {
  min_stair_width: (tm) => tm.stair_min_width,
  min_corridor_width: (tm) => tm.corridor_width,
  min_exits_per_floor: (tm) => tm.exits_per_floor,
  max_travel_distance_m: (tm) => tm.max_travel_distance_m,
  lift_shortfall: (tm) => Math.max(Math.ceil(tm.floors / 8) - tm.lift_count, 0),
};

const towerViolations = (rules, tm) =>
  (rules || [])
    .filter((r) => r.enabled !== false && TOWER_RULE_PARAMS[r.param])
    .map((r) => {
      const actual = Number(TOWER_RULE_PARAMS[r.param](tm) || 0);
      const ok = r.operator === "max" ? actual <= Number(r.threshold) : actual >= Number(r.threshold);
      return ok ? null : { code: r.code, label: r.label, actual, threshold: r.threshold, unit: r.unit };
    })
    .filter(Boolean);

// ------------------------------------------------------------------ scene parts
const Terrain = ({ bounds, terrain }) => {
  const geom = useMemo(() => {
    const seg = terrain.seg || 24;
    const g = new THREE.PlaneGeometry(bounds.width * 2.2, bounds.depth * 2.2, seg, seg);
    if (terrain.heights) {
      const pos = g.attributes.position;
      for (let i = 0; i < pos.count; i += 1) pos.setZ(i, terrain.heights[i] ?? 0);
      g.computeVertexNormals();
    }
    return g;
  }, [bounds, terrain]);

  return (
    <mesh geometry={geom} rotation={[-Math.PI / 2, 0, 0]} position={[bounds.cx, -0.05, bounds.cz]} receiveShadow>
      <meshStandardMaterial color={terrain.heights ? "#D6D3C4" : "#E7E5E4"} roughness={0.95} />
    </mesh>
  );
};

const PlotOutline = ({ pts, roadEdges }) => {
  const closed = [...pts, pts[0]];
  return (
    <group>
      <Line points={closed.map(([x, z]) => [x, 0.35, z])} color="#2563EB" lineWidth={3} />
      {(roadEdges || []).map((r, i) => {
        const a = pts[r.edge_index % pts.length];
        const b = pts[(r.edge_index + 1) % pts.length];
        if (!a || !b) return null;
        return (
          <Line key={i} points={[[a[0], 0.5, a[1]], [b[0], 0.5, b[1]]]} color="#F59E0B" lineWidth={7} />
        );
      })}
    </group>
  );
};

const CompassRose = ({ bounds, orientation }) => {
  const r = Math.max(bounds.width, bounds.depth) * 0.62;
  const rad = (orientation * Math.PI) / 180;
  return (
    <group position={[bounds.cx, 0.4, bounds.cz]}>
      <Line points={[[0, 0, 0], [0, 0, -r]]} color="#DC2626" lineWidth={2} />
      <Html position={[0, 1, -r - 3]} center>
        <div className="text-[10px] font-mono bg-white/95 border border-slate-200 px-1 rounded-sm">N</div>
      </Html>
      <Line points={[[0, 0, 0], [Math.sin(rad) * r * 0.8, 0, -Math.cos(rad) * r * 0.8]]} color="#2563EB" lineWidth={3} />
      <Html position={[Math.sin(rad) * r * 0.85, 1, -Math.cos(rad) * r * 0.85]} center>
        <div className="text-[10px] font-mono bg-white/95 border border-slate-200 px-1 rounded-sm">
          front {orientation}°
        </div>
      </Html>
    </group>
  );
};

const InstancedBuildings = ({ items }) => {
  const ref = useRef();
  useEffect(() => {
    if (!ref.current) return;
    const m = new THREE.Matrix4();
    items.forEach((b, i) => {
      const h = 6 + ((i * 7) % 5) * 3;
      m.compose(
        new THREE.Vector3(b.cx, h / 2, b.cz),
        new THREE.Quaternion(),
        new THREE.Vector3(Math.max(b.width, 4), h, Math.max(b.depth, 4))
      );
      ref.current.setMatrixAt(i, m);
    });
    ref.current.instanceMatrix.needsUpdate = true;
  }, [items]);

  if (!items.length) return null;
  return (
    <instancedMesh ref={ref} args={[null, null, items.length]} castShadow>
      <boxGeometry args={[1, 1, 1]} />
      <meshStandardMaterial color="#94A3B8" transparent opacity={0.75} />
    </instancedMesh>
  );
};

const FlatFeatures = ({ items, color, y = 0.06 }) =>
  items.map((f) => {
    const shape = new THREE.Shape(f.pts.map(([x, z]) => new THREE.Vector2(x, z)));
    return (
      <mesh key={f.id} rotation={[-Math.PI / 2, 0, 0]} position={[0, y, 0]}>
        <shapeGeometry args={[shape]} />
        <meshStandardMaterial color={color} transparent opacity={0.55} side={THREE.DoubleSide} />
      </mesh>
    );
  });

const TowerMesh = ({ tower, metrics, detailed, sectionFloor, selected, dimmed, violations, onSelect, layers }) => {
  const slabRef = useRef();
  const visibleFloors = sectionFloor ? Math.min(sectionFloor, tower.floors) : tower.floors;
  const unitColor = useMemo(() => {
    const dominant = (tower.units || []).reduce((a, b) => (Number(b.count) > Number(a?.count || 0) ? b : a), null);
    return UNIT_COLORS[dominant?.type] || "#2563EB";
  }, [tower.units]);
  const color = violations.length ? "#DC2626" : selected ? "#1D4ED8" : unitColor;

  useEffect(() => {
    if (!detailed || !slabRef.current) return;
    const m = new THREE.Matrix4();
    const c = new THREE.Color();
    const types = (tower.units || []).map((u) => u.type);
    for (let i = 0; i < visibleFloors; i += 1) {
      m.compose(
        new THREE.Vector3(tower.x, i * tower.floorHeight + tower.floorHeight * 0.45, tower.z),
        new THREE.Quaternion(),
        new THREE.Vector3(tower.w, tower.floorHeight * 0.82, tower.d)
      );
      slabRef.current.setMatrixAt(i, m);
      const t = types[i % Math.max(types.length, 1)];
      c.set(violations.length ? "#DC2626" : UNIT_COLORS[t] || "#2563EB");
      slabRef.current.setColorAt(i, c);
    }
    slabRef.current.count = visibleFloors;
    slabRef.current.instanceMatrix.needsUpdate = true;
    if (slabRef.current.instanceColor) slabRef.current.instanceColor.needsUpdate = true;
  }, [detailed, tower, visibleFloors, violations.length]);

  return (
    <group onClick={(e) => { e.stopPropagation(); onSelect(); }}>
      {detailed ? (
        <instancedMesh ref={slabRef} args={[null, null, Math.max(tower.floors, 1)]} castShadow>
          <boxGeometry args={[1, 1, 1]} />
          <meshStandardMaterial color="#FFFFFF" transparent opacity={dimmed ? 0.25 : 0.95} roughness={0.6} />
        </instancedMesh>
      ) : (
        <mesh position={[tower.x, (visibleFloors * tower.floorHeight) / 2, tower.z]} castShadow>
          <boxGeometry args={[tower.w, visibleFloors * tower.floorHeight, tower.d]} />
          <meshStandardMaterial color={color} transparent opacity={dimmed ? 0.2 : 0.92} roughness={0.6} />
        </mesh>
      )}

      {layers.balconies &&
        Array.from({ length: visibleFloors }).map((_, i) => (
          <mesh key={i} position={[tower.x + tower.w / 2 + 0.8, i * tower.floorHeight + 1, tower.z]}>
            <boxGeometry args={[1.6, 0.25, tower.d * 0.5]} />
            <meshStandardMaterial color="#CBD5E1" />
          </mesh>
        ))}

      <Html position={[tower.x, visibleFloors * tower.floorHeight + 4, tower.z]} center>
        <div
          onClick={onSelect}
          onPointerDown={(e) => e.stopPropagation()}
          onPointerUp={(e) => e.stopPropagation()}
          className={`text-[10px] font-mono px-1.5 py-0.5 rounded-sm border cursor-pointer ${
            violations.length ? "bg-red-50 border-red-300 text-red-700" : "bg-white/95 border-slate-200"
          }`}
          data-testid={`tower-label-${tower.id}`}
        >
          {tower.name} · {tower.floors}F{violations.length ? ` · ${violations.length} fail` : ""}
        </div>
      </Html>
      {metrics && selected && (
        <Html position={[tower.x, visibleFloors * tower.floorHeight + 9, tower.z]} center>
          <div className="text-[10px] font-mono bg-blue-600 text-white px-1.5 py-0.5 rounded-sm">isolated</div>
        </Html>
      )}
    </group>
  );
};

const ParkingLayer = ({ bounds, parking, slots }) => {
  const ref = useRef();
  const levels = Number(parking?.basement_levels) || 0;
  useEffect(() => {
    if (!ref.current) return;
    const m = new THREE.Matrix4();
    const perRow = Math.max(Math.floor(bounds.width / 3), 1);
    for (let i = 0; i < slots; i += 1) {
      const row = Math.floor(i / perRow);
      const col = i % perRow;
      m.compose(
        new THREE.Vector3(bounds.minX + col * 3 + 1.5, -3 - Math.floor(row / 8) * 3, bounds.minZ + (row % 8) * 5.5 + 2.5),
        new THREE.Quaternion(),
        new THREE.Vector3(2.5, 0.12, 5)
      );
      ref.current.setMatrixAt(i, m);
    }
    ref.current.instanceMatrix.needsUpdate = true;
  }, [bounds, slots]);

  return (
    <group>
      {Array.from({ length: levels }).map((_, i) => (
        <mesh key={i} position={[bounds.cx, -3 - i * 3.2, bounds.cz]}>
          <boxGeometry args={[bounds.width * 0.9, 0.2, bounds.depth * 0.9]} />
          <meshStandardMaterial color="#78716C" transparent opacity={0.4} />
        </mesh>
      ))}
      {slots > 0 && (
        <instancedMesh ref={ref} args={[null, null, slots]}>
          <boxGeometry args={[1, 1, 1]} />
          <meshStandardMaterial color="#38BDF8" transparent opacity={0.8} />
        </instancedMesh>
      )}
    </group>
  );
};

const CommonAreaLayer = ({ bounds, area }) => {
  if (!area) return null;
  const side = Math.sqrt(area);
  return (
    <mesh position={[bounds.minX + side / 2 + 2, 1.6, bounds.maxZ - side / 2 - 2]}>
      <boxGeometry args={[side, 3.2, side]} />
      <meshStandardMaterial color="#A7F3D0" transparent opacity={0.85} />
    </mesh>
  );
};

const Floor3D = ({ tower, floor, onSelectRoom, selectedRoomId, violated }) => {
  const rooms = tower.rooms || [];
  if (!rooms.length) return null;
  const b = localBounds(rooms.map((r) => [Number(r.x), Number(r.y)]));
  const ox = -(b.minX + b.maxX) / 2;
  const oz = -(b.minZ + b.maxZ) / 2;
  const wallH = 2.9;
  const y = (floor - 1) * tower.floorHeight;

  return (
    <group position={[0, y, 0]}>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.02, 0]} receiveShadow>
        <planeGeometry args={[b.width + 14, b.depth + 14]} />
        <meshStandardMaterial color="#F1F5F9" />
      </mesh>
      {rooms.map((r) => {
        const w = Number(r.w);
        const d = Number(r.h);
        const cx = Number(r.x) + w / 2 + ox;
        const cz = Number(r.y) + d / 2 + oz;
        const active = r.id === selectedRoomId;
        const col = violated ? "#FCA5A5" : ROOM_COLORS[r.type] || "#E2E8F0";
        const doorGap = Math.min(1.0, w * 0.35);
        return (
          <group key={r.id} onClick={(e) => { e.stopPropagation(); onSelectRoom(r); }}>
            <mesh rotation={[-Math.PI / 2, 0, 0]} position={[cx, 0.06, cz]}>
              <planeGeometry args={[w, d]} />
              <meshStandardMaterial color={active ? "#93C5FD" : col} />
            </mesh>
            {/* rear + side walls */}
            <mesh position={[cx, wallH / 2, cz - d / 2]}>
              <boxGeometry args={[w, wallH, 0.2]} />
              <meshStandardMaterial color={active ? "#2563EB" : "#CBD5E1"} />
            </mesh>
            <mesh position={[cx - w / 2, wallH / 2, cz]}>
              <boxGeometry args={[0.2, wallH, d]} />
              <meshStandardMaterial color={active ? "#2563EB" : "#CBD5E1"} />
            </mesh>
            <mesh position={[cx + w / 2, wallH / 2, cz]}>
              <boxGeometry args={[0.2, wallH, d]} />
              <meshStandardMaterial color={active ? "#2563EB" : "#CBD5E1"} />
            </mesh>
            {/* front wall split to leave a door opening */}
            <mesh position={[cx - (w - doorGap) / 4 - doorGap / 4, wallH / 2, cz + d / 2]}>
              <boxGeometry args={[(w - doorGap) / 2, wallH, 0.2]} />
              <meshStandardMaterial color={active ? "#2563EB" : "#CBD5E1"} />
            </mesh>
            <mesh position={[cx + (w - doorGap) / 4 + doorGap / 4, wallH / 2, cz + d / 2]}>
              <boxGeometry args={[(w - doorGap) / 2, wallH, 0.2]} />
              <meshStandardMaterial color={active ? "#2563EB" : "#CBD5E1"} />
            </mesh>
            {/* window band on the rear wall */}
            <mesh position={[cx, 1.9, cz - d / 2 - 0.02]}>
              <boxGeometry args={[Math.max(w * 0.5, 0.6), 1.0, 0.08]} />
              <meshStandardMaterial color="#7DD3FC" transparent opacity={0.7} />
            </mesh>
            <Html position={[cx, 3.2, cz]} center>
              <div
                onClick={() => onSelectRoom(r)}
                onPointerDown={(e) => e.stopPropagation()}
                onPointerUp={(e) => e.stopPropagation()}
                className="text-[9px] font-mono bg-white/95 border border-slate-200 px-1 rounded-sm whitespace-nowrap cursor-pointer hover:border-blue-500"
                data-testid={`room3d-${r.id}`}
              >
                {r.name} · {(w * d).toFixed(1)} m²
              </div>
            </Html>
          </group>
        );
      })}
    </group>
  );
};

const SunLight = ({ azimuth, elevation, bounds }) => {
  const [x, y, z] = sunVector(azimuth, elevation, Math.max(bounds.width, 120) * 1.6);
  return (
    <>
      <directionalLight position={[x, y, z]} intensity={1.15} castShadow
        shadow-mapSize={[1024, 1024]} />
      <mesh position={[x * 0.65, y * 0.65, z * 0.65]}>
        <sphereGeometry args={[Math.max(bounds.width, 60) * 0.05, 16, 16]} />
        <meshBasicMaterial color="#FBBF24" />
      </mesh>
    </>
  );
};

const WalkController = ({ enabled, y }) => {
  const { camera } = useThree();
  const keys = useRef({});
  useEffect(() => {
    const down = (e) => (keys.current[e.code] = true);
    const up = (e) => (keys.current[e.code] = false);
    window.addEventListener("keydown", down);
    window.addEventListener("keyup", up);
    return () => {
      window.removeEventListener("keydown", down);
      window.removeEventListener("keyup", up);
    };
  }, []);
  useFrame((_, dt) => {
    if (!enabled) return;
    const speed = 12 * dt;
    const dir = new THREE.Vector3();
    camera.getWorldDirection(dir);
    dir.y = 0;
    dir.normalize();
    const side = new THREE.Vector3().crossVectors(camera.up, dir).normalize();
    if (keys.current.KeyW || keys.current.ArrowUp) camera.position.addScaledVector(dir, speed);
    if (keys.current.KeyS || keys.current.ArrowDown) camera.position.addScaledVector(dir, -speed);
    if (keys.current.KeyA || keys.current.ArrowLeft) camera.position.addScaledVector(side, speed);
    if (keys.current.KeyD || keys.current.ArrowRight) camera.position.addScaledVector(side, -speed);
    camera.position.y = y + 1.65;
  });
  return null;
};

// ------------------------------------------------------------------ module
export default function ThreeDModule({ project, analysis }) {
  const [view, setView] = useState("site");
  const [detailed, setDetailed] = useState(false);
  const [simpleView, setSimpleView] = useState(false);
  const [sectionCut, setSectionCut] = useState(false);
  const [walk, setWalk] = useState(false);
  const [floor, setFloor] = useState(1);
  const [hour, setHour] = useState(12);
  const [season, setSeason] = useState("equinox");
  const [towerIdx, setTowerIdx] = useState(0);
  const [selected, setSelected] = useState(null);
  const [layers, setLayers] = useState({ parking: true, balconies: true, common: true, violations: true });

  const coords = project.plot?.coordinates || [];
  const gis = project.gis;

  const scene = useMemo(() => {
    if (coords.length < 3) return null;
    const origin = originOf(coords);
    const pts = polyToLocal(coords, origin);
    const bounds = localBounds(pts);
    return {
      origin, pts, bounds,
      towers: towerLayout(project.towers || [], bounds),
      terrain: terrainHeights(gis, origin, bounds),
      buildings: featureShapes(gis, origin, "buildings"),
      green: featureShapes(gis, origin, "green", 25),
      water: featureShapes(gis, origin, "water", 15),
    };
  }, [coords, project.towers, gis]);

  const tower = scene?.towers[towerIdx];
  const tm = analysis?.areas?.towers?.[towerIdx];
  const violations = useMemo(
    () => (tm && layers.violations ? towerViolations(project.compliance_rules, tm) : []),
    [tm, project.compliance_rules, layers.violations]
  );
  const sun = sunAtHour(gis?.sun, hour, season);

  useEffect(() => {
    if (tower && floor > tower.floors) setFloor(tower.floors);
  }, [tower, floor]);

  if (!scene)
    return (
      <p className="text-sm text-slate-500" data-testid="three-no-plot">
        Draw a plot polygon in Plot &amp; Site to generate the 3D model.
      </p>
    );

  const camDist = Math.max(scene.bounds.width, scene.bounds.depth, 60) * 1.5;
  const roomSpan = tower?.rooms?.length
    ? Math.max(
        ...tower.rooms.map((r) => Number(r.x) + Number(r.w)),
        ...tower.rooms.map((r) => Number(r.y) + Number(r.h))
      )
    : 20;
  const camera =
    view === "floorplan"
      ? { position: [roomSpan * 0.9, roomSpan * 1.1, roomSpan * 1.4], fov: 50, far: 4000 }
      : view === "massing"
      ? { position: [camDist * 0.5, camDist * 0.45, camDist * 0.5], fov: 50, far: 6000 }
      : { position: [camDist * 0.8, camDist * 0.6, camDist * 0.8], fov: 50, far: 6000 };
  const sectionFloor = sectionCut ? floor : 0;

  const unitTypeOf = (i) => {
    const units = tower?.units || [];
    return units.length ? units[i % units.length].type : "custom";
  };

  return (
    <div className="space-y-4">
      <Section
        title="3D visualisation"
        description="Live from the same project document — plot polygon, GIS terrain, towers, floors, parking and compliance state."
        testid="three-controls-section"
        actions={
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-1.5 text-[11px]">
              <Switch checked={simpleView} onCheckedChange={setSimpleView} data-testid="simple-view-toggle" />
              Simple 2D view
            </label>
          </div>
        }
      >
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex gap-1">
            {[
              ["site", "Site", Compass],
              ["massing", "Massing", Box],
              ["floorplan", "Floor plan", Layers],
            ].map(([key, label, Icon]) => (
              <Button
                key={key}
                size="sm"
                variant={view === key ? "default" : "outline"}
                className="h-8 rounded-sm text-xs"
                data-testid={`view-mode-${key}`}
                onClick={() => setView(key)}
              >
                <Icon className="h-3.5 w-3.5 mr-1" />
                {label}
              </Button>
            ))}
          </div>

          <Select value={String(towerIdx)} onValueChange={(v) => setTowerIdx(Number(v))}>
            <SelectTrigger className="h-8 w-40 rounded-sm text-xs" data-testid="three-tower-select">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {scene.towers.map((t, i) => (
                <SelectItem key={t.id} value={String(i)}>
                  {t.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <label className="flex items-center gap-1.5 text-[11px]">
            <Switch checked={detailed} onCheckedChange={setDetailed} data-testid="detailed-view-toggle" />
            Detailed floors
          </label>
          <label className="flex items-center gap-1.5 text-[11px]">
            <Switch checked={sectionCut} onCheckedChange={setSectionCut} data-testid="section-cut-toggle" />
            <Scissors className="h-3 w-3" /> Section cut
          </label>
          <label className="flex items-center gap-1.5 text-[11px]">
            <Switch checked={walk} onCheckedChange={setWalk} data-testid="walk-mode-toggle" />
            <Move3d className="h-3 w-3" /> Walk mode
          </label>
          {["parking", "balconies", "common", "violations"].map((k) => (
            <label key={k} className="flex items-center gap-1.5 text-[11px] capitalize">
              <Switch
                checked={layers[k]}
                onCheckedChange={(v) => setLayers((l) => ({ ...l, [k]: v }))}
                data-testid={`layer-${k}-toggle`}
              />
              {k}
            </label>
          ))}
        </div>

        <div className="grid md:grid-cols-2 gap-4 mt-4">
          <div>
            <div className="flex items-center justify-between text-[11px] text-slate-500 mb-1">
              <span className="uppercase tracking-wide">Floor</span>
              <span className="font-mono" data-testid="three-floor-label">
                {floor} / {tower?.floors ?? 0} · {num((floor - 1) * (tower?.floorHeight || 3), 1)} m
              </span>
            </div>
            <Slider
              min={1}
              max={Math.max(tower?.floors || 1, 1)}
              step={1}
              value={[Math.min(floor, tower?.floors || 1)]}
              onValueChange={([v]) => setFloor(v)}
              data-testid="three-floor-slider"
            />
            <div className="flex gap-1 mt-1.5">
              <Button size="sm" variant="outline" className="h-6 px-2 rounded-sm text-[11px]"
                data-testid="three-floor-down" onClick={() => setFloor((f) => Math.max(1, f - 1))}>
                − floor
              </Button>
              <Button size="sm" variant="outline" className="h-6 px-2 rounded-sm text-[11px]"
                data-testid="three-floor-up"
                onClick={() => setFloor((f) => Math.min(tower?.floors || 1, f + 1))}>
                + floor
              </Button>
            </div>
          </div>
          <div>
            <div className="flex items-center justify-between text-[11px] text-slate-500 mb-1">
              <span className="uppercase tracking-wide flex items-center gap-1">
                <SunMedium className="h-3 w-3" /> Time of day
              </span>
              <span className="font-mono" data-testid="three-sun-label">
                {hour}:00 · az {Math.round(sun.azimuth)}° alt {Math.round(sun.elevation)}°
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Slider min={5} max={19} step={0.5} value={[hour]} onValueChange={([v]) => setHour(v)}
                className="flex-1" data-testid="three-sun-slider" />
              <Button size="sm" variant="outline" className="h-8 px-2 rounded-sm text-[11px]"
                data-testid="three-sun-earlier" onClick={() => setHour((h) => Math.max(5, h - 1))}>
                −1h
              </Button>
              <Button size="sm" variant="outline" className="h-8 px-2 rounded-sm text-[11px]"
                data-testid="three-sun-later" onClick={() => setHour((h) => Math.min(19, h + 1))}>
                +1h
              </Button>
              <Select value={season} onValueChange={setSeason}>
                <SelectTrigger className="h-8 w-36 rounded-sm text-xs" data-testid="three-season-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="summer_solstice">21 Jun</SelectItem>
                  <SelectItem value="equinox">21 Mar</SelectItem>
                  <SelectItem value="winter_solstice">21 Dec</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>
        {view === "floorplan" && (
          <p className="text-[11px] text-blue-700 bg-blue-50 border border-blue-200 rounded-sm px-2 py-1 mt-3" data-testid="three-floorplan-readonly-hint">
            This is a live read-only preview of the room layout. To add, move, resize or delete rooms, use the{" "}
            <span className="font-semibold">Planning</span> tab — changes there update this view automatically.
          </p>
        )}
        {!gis && (
          <p className="text-[11px] text-amber-700 bg-amber-50 border border-amber-200 rounded-sm px-2 py-1 mt-3" data-testid="three-no-gis">
            Run the GIS site analysis to drive the terrain surface and true sun path — a flat plane and an
            approximate sun arc are used until then.
          </p>
        )}
      </Section>

      {simpleView ? (
        <Section title={`Simple 2D view — ${tower?.name} floor ${floor}`} testid="three-simple-view">
          <FloorPlate rooms={tower?.rooms || []} selectedId={selected?.room?.id} onSelect={(id) =>
            setSelected({ type: "room", room: (tower?.rooms || []).find((r) => r.id === id) })} />
        </Section>
      ) : (
        <div className="grid lg:grid-cols-[1fr_320px] gap-4">
          <div className="border border-slate-200 bg-white rounded-sm overflow-hidden" data-testid="three-canvas-wrapper">
            <Canvas
              key={view}
              shadows
              style={{ height: 560, background: "#EEF2F7" }}
              camera={camera}
              onPointerMissed={() => setSelected(null)}
            >
              <ambientLight intensity={0.55} />
              <hemisphereLight args={["#DCEAFE", "#B8B0A2", 0.5]} />
              <SunLight azimuth={sun.azimuth} elevation={sun.elevation} bounds={scene.bounds} />

              {view !== "floorplan" && (
                <>
                  <Terrain bounds={scene.bounds} terrain={scene.terrain} />
                  <PlotOutline pts={scene.pts} roadEdges={project.plot?.road_edges} />
                  <CompassRose bounds={scene.bounds} orientation={project.plot?.orientation_deg || 0} />
                </>
              )}

              {view === "site" && (
                <>
                  <InstancedBuildings items={scene.buildings} />
                  <FlatFeatures items={scene.green} color="#16A34A" y={0.08} />
                  <FlatFeatures items={scene.water} color="#0EA5E9" y={0.1} />
                </>
              )}

              {view !== "floorplan" &&
                scene.towers.map((t, i) => (
                  <TowerMesh
                    key={t.id}
                    tower={t}
                    metrics={analysis?.areas?.towers?.[i]}
                    detailed={detailed}
                    sectionFloor={sectionFloor}
                    selected={i === towerIdx && selected?.type === "tower"}
                    dimmed={selected?.type === "tower" && i !== towerIdx}
                    violations={
                      layers.violations && analysis?.areas?.towers?.[i]
                        ? towerViolations(project.compliance_rules, analysis.areas.towers[i])
                        : []
                    }
                    layers={layers}
                    onSelect={() => {
                      setTowerIdx(i);
                      setSelected({ type: "tower", index: i });
                    }}
                  />
                ))}

              {view === "floorplan" && tower && (
                <Floor3D
                  tower={tower}
                  floor={floor}
                  selectedRoomId={selected?.room?.id}
                  violated={violations.length > 0}
                  onSelectRoom={(room) => setSelected({ type: "room", room })}
                />
              )}

              {layers.parking && view !== "floorplan" && (
                <ParkingLayer bounds={scene.bounds} parking={project.parking}
                  slots={Math.min(analysis?.parking?.provided_slots || 0, 220)} />
              )}
              {layers.common && view !== "floorplan" && (
                <CommonAreaLayer bounds={scene.bounds} area={tower?.commonArea} />
              )}

              {walk ? (
                <>
                  <PointerLockControls />
                  <WalkController enabled={walk} y={view === "floorplan" ? (floor - 1) * (tower?.floorHeight || 3) : 0} />
                </>
              ) : (
                <OrbitControls makeDefault enablePan enableZoom enableRotate maxPolarAngle={Math.PI / 2.05} />
              )}
            </Canvas>
            <div className="px-3 py-1.5 border-t border-slate-200 text-[11px] text-slate-500 flex items-center gap-3">
              <Eye className="h-3 w-3" />
              {walk ? "Walk mode: click the scene to lock the pointer, WASD to move, Esc to exit" :
                "Drag to orbit · scroll to zoom · right-drag to pan · click a tower or room for details"}
            </div>
          </div>

          <aside className="border border-slate-200 bg-white rounded-sm p-4 space-y-3" data-testid="three-side-panel">
            <h3 className="text-sm font-semibold tracking-tight">Selection</h3>
            {selected?.type === "tower" && tm ? (
              <div className="space-y-2 text-sm" data-testid="selection-tower">
                <div className="font-semibold">{scene.towers[selected.index]?.name}</div>
                {[
                  ["Floors", tm.floors],
                  ["Height", `${num(tm.height_m, 1)} m`],
                  ["Units", tm.total_units],
                  ["Carpet", `${num(tm.carpet_sqm, 0)} m²`],
                  ["Built-up", `${num(tm.builtup_sqm, 0)} m²`],
                  ["Cost / m²", money(analysis?.cost?.per_sqm, analysis?.cost?.currency)],
                  ["Est. tower cost", money((analysis?.cost?.per_sqm || 0) * tm.builtup_sqm, analysis?.cost?.currency)],
                ].map(([k, v]) => (
                  <div key={k} className="flex justify-between border-b border-slate-100 pb-1">
                    <span className="text-slate-500 text-xs uppercase tracking-wide">{k}</span>
                    <span className="font-mono">{v}</span>
                  </div>
                ))}
                <div className={`rounded-sm px-2 py-1.5 text-xs border ${
                  violations.length ? "bg-red-50 border-red-200 text-red-800" : "bg-emerald-50 border-emerald-200 text-emerald-800"
                }`} data-testid="selection-compliance">
                  {violations.length
                    ? violations.map((v) => `[${v.code}] ${v.label}: ${v.actual}${v.unit} vs ${v.threshold}${v.unit}`).join(" · ")
                    : "Passes all tower-level compliance rules"}
                </div>
              </div>
            ) : selected?.type === "room" && selected.room ? (
              <div className="space-y-2 text-sm" data-testid="selection-room">
                <div className="font-semibold">{selected.room.name}</div>
                {[
                  ["Type", selected.room.type],
                  ["Carpet area", `${num(Number(selected.room.w) * Number(selected.room.h), 2)} m²`],
                  ["Dimensions", `${num(selected.room.w, 1)} × ${num(selected.room.h, 1)} m`],
                  ["Cost / m²", money(analysis?.cost?.per_sqm, analysis?.cost?.currency)],
                  [
                    "Room cost",
                    money((analysis?.cost?.per_sqm || 0) * Number(selected.room.w) * Number(selected.room.h),
                      analysis?.cost?.currency),
                  ],
                  ["Floor", `${floor} of ${tower?.floors}`],
                  ["Unit type on floor", unitTypeOf(floor - 1).toUpperCase()],
                ].map(([k, v]) => (
                  <div key={k} className="flex justify-between border-b border-slate-100 pb-1">
                    <span className="text-slate-500 text-xs uppercase tracking-wide">{k}</span>
                    <span className="font-mono">{v}</span>
                  </div>
                ))}
                <div className={`rounded-sm px-2 py-1.5 text-xs border ${
                  violations.length ? "bg-red-50 border-red-200 text-red-800" : "bg-emerald-50 border-emerald-200 text-emerald-800"
                }`}>
                  {violations.length
                    ? `Floor flagged: ${violations.map((v) => v.code).join(", ")}`
                    : `Compliance: ${analysis?.compliance?.passed}/${analysis?.compliance?.total} rules pass`}
                </div>
              </div>
            ) : (
              <p className="text-sm text-slate-500">
                Click a tower (Site / Massing view) or a room (Floor plan view) to see its live calculated data.
              </p>
            )}

            <div className="pt-2 border-t border-slate-200 space-y-1 text-[11px] text-slate-500">
              <div className="flex justify-between">
                <span>Terrain source</span>
                <span className="font-mono">{scene.terrain.heights ? `GIS · relief ${num(scene.terrain.relief, 1)} m` : "flat"}</span>
              </div>
              <div className="flex justify-between">
                <span>Parking slots rendered</span>
                <span className="font-mono">{Math.min(analysis?.parking?.provided_slots || 0, 220)}</span>
              </div>
              <div className="flex justify-between">
                <span>Nearby buildings</span>
                <span className="font-mono">{scene.buildings.length}</span>
              </div>
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}
