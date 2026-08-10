const COLORS = {
  living: "#DBEAFE",
  bedroom: "#E0E7FF",
  kitchen: "#FEF3C7",
  bathroom: "#D1FAE5",
  balcony: "#F1F5F9",
  utility: "#FDE68A",
  common: "#E2E8F0",
  closet: "#FBCFE8",
  entrance: "#E9D5FF",
  study: "#C7D2FE",
};

export const FloorPlate = ({ rooms = [], selectedId, onSelect, corridor }) => {
  if (!rooms.length) return <p className="text-sm text-slate-500">No rooms defined for this floor plate.</p>;
  const maxX = Math.max(...rooms.map((r) => Number(r.x) + Number(r.w))) + 1;
  const maxY = Math.max(...rooms.map((r) => Number(r.y) + Number(r.h))) + 1;
  const scale = 34;

  // Generated floor plates tag every room with the unit it belongs to — draw a dashed
  // outline + label around each unit's own rooms so a multi-unit floor plate reads as
  // "Unit 1 · 2BHK, Unit 2 · 3BHK, ..." instead of one undifferentiated room soup.
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

  return (
    <div className="overflow-auto bg-slate-50 border border-slate-200 rounded-sm p-3" data-testid="floor-plate-svg">
      <svg width={maxX * scale} height={maxY * scale} className="min-w-full">
        <defs>
          <pattern id="grid" width={scale} height={scale} patternUnits="userSpaceOnUse">
            <path d={`M ${scale} 0 L 0 0 0 ${scale}`} fill="none" stroke="#E2E8F0" strokeWidth="1" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#grid)" />
        {corridor > 0 && (
          <rect
            x={0}
            y={(maxY - 1 - corridor) * scale}
            width={maxX * scale}
            height={corridor * scale}
            fill="#CBD5E1"
            opacity="0.5"
          />
        )}
        {units.map((u) => (
          <g key={`unit-${u.id}`} opacity="0.6">
            <rect
              x={u.x * scale} y={u.y * scale} width={u.w * scale} height={u.h * scale}
              fill="none" stroke="#0F172A" strokeWidth={1.5} strokeDasharray="4 2"
            />
            <text
              x={u.x * scale + 4}
              y={Math.max(u.y * scale - 4, 10)}
              fontSize="9"
              fontFamily="JetBrains Mono, monospace"
              fill="#334155"
            >
              Unit {Number(u.index) + 1} · {String(u.type || "").toUpperCase()}
            </text>
          </g>
        ))}
        {rooms.map((r) => {
          const active = r.id === selectedId;
          return (
            <g
              key={r.id}
              onClick={() => onSelect && onSelect(r.id)}
              className="cursor-pointer"
              data-testid={`floor-room-${r.id}`}
            >
              <rect
                x={Number(r.x) * scale}
                y={Number(r.y) * scale}
                width={Number(r.w) * scale}
                height={Number(r.h) * scale}
                fill={COLORS[r.type] || "#F8FAFC"}
                stroke={active ? "#2563EB" : "#0F172A"}
                strokeWidth={active ? 3 : 1.2}
              />
              <text
                x={Number(r.x) * scale + 5}
                y={Number(r.y) * scale + 15}
                className="font-sans"
                fontSize="10"
                fill="#0F172A"
              >
                {r.name}
              </text>
              <text
                x={Number(r.x) * scale + 5}
                y={Number(r.y) * scale + 27}
                fontSize="9"
                fill="#475569"
                fontFamily="JetBrains Mono, monospace"
              >
                {(Number(r.w) * Number(r.h)).toFixed(1)} m²
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
};
