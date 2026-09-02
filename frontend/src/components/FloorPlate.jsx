import { useState, useRef, useEffect } from "react";
import { ZoomIn, ZoomOut, RotateCcw, Maximize2 } from "lucide-react";
import { Button } from "./ui/button";

const COLORS = {
  living: "#F0F7FF",
  bedroom: "#EEF2FF",
  kitchen: "#FFFBEB",
  bathroom: "#F0FDF4",
  balcony: "#F8FAFC",
  utility: "#FEF3C7",
  common: "#F1F5F9",
  closet: "#FDF2F8",
  entrance: "#FAF5FF",
  study: "#EEF2FF",
};

export const FloorPlate = ({ rooms = [], selectedId, onSelect, corridor }) => {
  const [zoom, setZoom] = useState(1.0);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const dragStartRef = useRef({ x: 0, y: 0 });
  const movedRef = useRef(false);
  const containerRef = useRef(null);

  // Wheel zoom with passive: false to prevent scrolling parent container
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const onWheel = (e) => {
      e.preventDefault();
      const delta = e.deltaY < 0 ? 0.15 : -0.15;
      setZoom((prev) => Math.min(Math.max(Number((prev + delta).toFixed(2)), 0.4), 3.5));
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, []);

  if (!rooms.length) return <p className="text-sm text-slate-500">No rooms defined for this floor plate.</p>;
  const minX = Math.min(...rooms.map((r) => Number(r.x)));
  const minY = Math.min(...rooms.map((r) => Number(r.y)));
  const maxX = Math.max(...rooms.map((r) => Number(r.x) + Number(r.w))) + 1;
  const maxY = Math.max(...rooms.map((r) => Number(r.y) + Number(r.h))) + 1;
  const scale = 36;
  const padding = 20;

  const svgW = (maxX - minX + 2) * scale + padding * 2;
  const svgH = (maxY - minY + 2) * scale + padding * 2;

  const units = [];
  const seenUnits = new Set();
  rooms.forEach((r) => {
    if (r.unit_id == null || seenUnits.has(r.unit_id)) return;
    seenUnits.add(r.unit_id);
    const inUnit = rooms.filter((x) => x.unit_id === r.unit_id);
    const ux = Math.min(...inUnit.map((x) => Number(x.x)));
    const uy = Math.min(...inUnit.map((x) => Number(x.y)));
    const ux2 = Math.max(...inUnit.map((x) => Number(x.x) + Number(x.w)));
    const uy2 = Math.max(...inUnit.map((x) => Number(x.y) + Number(x.h)));
    units.push({ id: r.unit_id, type: r.unit_type, index: r.unit_index, x: ux, y: uy, w: ux2 - ux, h: uy2 - uy });
  });

  const handleMouseDown = (e) => {
    if (e.button !== 0) return;
    setIsDragging(true);
    movedRef.current = false;
    dragStartRef.current = { x: e.clientX - pan.x, y: e.clientY - pan.y };
  };

  const handleMouseMove = (e) => {
    if (!isDragging) return;
    const dx = e.clientX - dragStartRef.current.x;
    const dy = e.clientY - dragStartRef.current.y;
    if (Math.hypot(dx - pan.x, dy - pan.y) > 3) {
      movedRef.current = true;
    }
    setPan({ x: dx, y: dy });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleReset = () => {
    setZoom(1.0);
    setPan({ x: 0, y: 0 });
  };

  return (
    <div
      className="relative flex flex-col bg-slate-900/5 rounded-sm border border-slate-200 shadow-inner overflow-hidden select-none"
      data-testid="floor-plate-svg"
    >
      {/* Top Header & Zoom Controls Bar */}
      <div className="flex items-center justify-between px-3 py-2 bg-white/80 backdrop-blur-xs border-b border-slate-200 text-xs text-slate-600 z-10">
        <span className="flex items-center gap-2 font-medium">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-blue-600" />
          Floor Plate View
          <span className="text-[11px] font-mono text-slate-400 font-normal hidden sm:inline">
            · 1m = {scale}px
          </span>
        </span>

        {/* Zoom Controls */}
        <div className="flex items-center gap-1">
          <Button
            size="sm"
            variant="outline"
            className="h-6 w-6 p-0 rounded-xs text-slate-600 hover:text-slate-900"
            onClick={() => setZoom((prev) => Math.max(Number((prev - 0.15).toFixed(2)), 0.4))}
            title="Zoom Out"
          >
            <ZoomOut className="h-3 w-3" />
          </Button>
          <span className="font-mono text-[11px] px-1.5 min-w-[42px] text-center text-slate-700 font-medium">
            {Math.round(zoom * 100)}%
          </span>
          <Button
            size="sm"
            variant="outline"
            className="h-6 w-6 p-0 rounded-xs text-slate-600 hover:text-slate-900"
            onClick={() => setZoom((prev) => Math.min(Number((prev + 0.15).toFixed(2)), 3.5))}
            title="Zoom In"
          >
            <ZoomIn className="h-3 w-3" />
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="h-6 px-1.5 rounded-xs text-[11px] text-slate-600 hover:text-slate-900 ml-1"
            onClick={handleReset}
            title="Fit to Screen"
          >
            <RotateCcw className="h-2.5 w-2.5 mr-1" /> Fit
          </Button>
        </div>
      </div>

      {/* Main Floor Plan Viewport — no scrollbars, cleanly auto-fitted */}
      <div
        ref={containerRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        className={`relative w-full h-[380px] md:h-[420px] flex items-center justify-center overflow-hidden bg-slate-100/60 ${
          isDragging ? "cursor-grabbing" : zoom > 1 ? "cursor-grab" : "cursor-default"
        }`}
      >
        <div
          style={{
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
            transformOrigin: "center center",
            transition: isDragging ? "none" : "transform 0.12s ease-out",
          }}
          className="flex items-center justify-center max-w-full max-h-full"
        >
          <svg
            viewBox={`0 0 ${svgW} ${svgH}`}
            className="max-h-[340px] md:max-h-[380px] max-w-[95%] w-auto h-auto bg-white rounded border border-slate-300 shadow-sm"
          >
            <defs>
              <pattern id="arch-grid" width={scale} height={scale} patternUnits="userSpaceOnUse">
                <path d={`M ${scale} 0 L 0 0 0 ${scale}`} fill="none" stroke="#F1F5F9" strokeWidth="1" />
              </pattern>
              <pattern id="balcony-rail" width="6" height="6" patternUnits="userSpaceOnUse">
                <line x1="0" y1="6" x2="6" y2="0" stroke="#CBD5E1" strokeWidth="1" />
              </pattern>
            </defs>

            <rect width="100%" height="100%" fill="url(#arch-grid)" />

            {/* North Indicator */}
            <g transform="translate(35, 35)">
              <circle cx="0" cy="0" r="16" fill="#F8FAFC" stroke="#94A3B8" strokeWidth="1" />
              <path d="M 0 -12 L 5 8 L 0 4 L -5 8 Z" fill="#2563EB" />
              <text x="0" y="-14" textAnchor="middle" fontSize="9" fontWeight="bold" fill="#1E293B" fontFamily="sans-serif">N</text>
            </g>

            {corridor > 0 && (
              <rect
                x={padding}
                y={(maxY - minY - corridor) * scale + padding}
                width={(maxX - minX) * scale}
                height={corridor * scale}
                fill="#E2E8F0"
                stroke="#94A3B8"
                strokeWidth="1.5"
              />
            )}

            {/* Unit boundaries */}
            {units.map((u) => (
              <g key={`unit-${u.id}`}>
                <rect
                  x={(u.x - minX) * scale + padding}
                  y={(u.y - minY) * scale + padding}
                  width={u.w * scale}
                  height={u.h * scale}
                  fill="none"
                  stroke="#2563EB"
                  strokeWidth={1.5}
                  strokeDasharray="6 3"
                  rx={2}
                />
                <rect
                  x={(u.x - minX) * scale + padding + 4}
                  y={Math.max((u.y - minY) * scale + padding - 18, 4)}
                  width={Math.max(u.w * scale - 8, 90)}
                  height="16"
                  fill="#EFF6FF"
                  stroke="#BFDBFE"
                  rx={2}
                />
                <text
                  x={(u.x - minX) * scale + padding + 8}
                  y={Math.max((u.y - minY) * scale + padding - 6, 16)}
                  fontSize="9.5"
                  fontWeight="600"
                  fontFamily="JetBrains Mono, monospace"
                  fill="#1E40AF"
                >
                  UNIT {Number(u.index) + 1} · {String(u.type || "").toUpperCase()}
                </text>
              </g>
            ))}

            {/* Rooms */}
            {rooms.map((r) => {
              const active = r.id === selectedId;
              const rx = (Number(r.x) - minX) * scale + padding;
              const ry = (Number(r.y) - minY) * scale + padding;
              const rw = Number(r.w) * scale;
              const rh = Number(r.h) * scale;
              const areaSqm = Number(r.w) * Number(r.h);
              const areaSqft = areaSqm * 10.7639;
              const isBalcony = r.type === "balcony";
              const hasWindow = r.has_window || r.type === "living" || r.type === "bedroom";

              return (
                <g
                  key={r.id}
                  onClick={(e) => {
                    if (movedRef.current) return;
                    e.stopPropagation();
                    if (onSelect) onSelect(r.id);
                  }}
                  className="cursor-pointer group"
                  data-testid={`floor-room-${r.id}`}
                >
                  {/* Room floor */}
                  <rect
                    x={rx}
                    y={ry}
                    width={rw}
                    height={rh}
                    fill={COLORS[r.type] || "#FFFFFF"}
                    stroke={active ? "#2563EB" : "#1E293B"}
                    strokeWidth={active ? 2.5 : 1.5}
                  />

                  {isBalcony && (
                    <rect x={rx + 2} y={ry + 2} width={rw - 4} height={rh - 4} fill="url(#balcony-rail)" />
                  )}

                  {/* Exterior window band if applicable */}
                  {hasWindow && !isBalcony && (
                    <line
                      x1={rx + 10}
                      y1={ry + 1}
                      x2={rx + Math.max(rw - 10, 15)}
                      y2={ry + 1}
                      stroke="#38BDF8"
                      strokeWidth="3.5"
                    />
                  )}

                  {/* Door swing arc in the corner */}
                  {!isBalcony && rw > 40 && rh > 40 && (
                    <g opacity="0.6">
                      <path
                        d={`M ${rx + 1} ${ry + rh - 18} A 16 16 0 0 1 ${rx + 18} ${ry + rh - 1}`}
                        fill="none"
                        stroke="#64748B"
                        strokeWidth="1"
                        strokeDasharray="2 2"
                      />
                      <line x1={rx + 1} y1={ry + rh - 18} x2={rx + 1} y2={ry + rh - 1} stroke="#1E293B" strokeWidth="1.5" />
                    </g>
                  )}

                  {/* Room name */}
                  <text
                    x={rx + 8}
                    y={ry + 16}
                    fontFamily="sans-serif"
                    fontSize="10"
                    fontWeight="600"
                    fill={active ? "#1D4ED8" : "#0F172A"}
                  >
                    {r.name}
                  </text>

                  {/* Dual metric area label: m² and sq.ft */}
                  <text
                    x={rx + 8}
                    y={ry + 30}
                    fontSize="9"
                    fontFamily="JetBrains Mono, monospace"
                    fill="#475569"
                  >
                    {areaSqm.toFixed(1)} m² <tspan fill="#94A3B8">({areaSqft.toFixed(0)} sqft)</tspan>
                  </text>

                  {/* Dimensions */}
                  <text
                    x={rx + 8}
                    y={ry + 42}
                    fontSize="8"
                    fontFamily="JetBrains Mono, monospace"
                    fill="#94A3B8"
                  >
                    {Number(r.w).toFixed(1)}m × {Number(r.h).toFixed(1)}m
                  </text>
                </g>
              );
            })}
          </svg>
        </div>

        {/* Floating Pan & Zoom Hint */}
        <div className="absolute bottom-2 right-3 pointer-events-none text-[10px] font-mono text-slate-400 bg-white/75 px-1.5 py-0.5 rounded-xs border border-slate-200/60 shadow-2xs">
          Scroll to zoom · Drag to pan
        </div>
      </div>
    </div>
  );
};

