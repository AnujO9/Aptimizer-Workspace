const COLORS = {
  living: "#DBEAFE",
  bedroom: "#E0E7FF",
  kitchen: "#FEF3C7",
  bathroom: "#D1FAE5",
  balcony: "#F1F5F9",
  utility: "#FDE68A",
  common: "#E2E8F0",
};

export const FloorPlate = ({ rooms = [], selectedId, onSelect, corridor }) => {
  if (!rooms.length) return <p className="text-sm text-slate-500">No rooms defined for this floor plate.</p>;
  const maxX = Math.max(...rooms.map((r) => Number(r.x) + Number(r.w))) + 1;
  const maxY = Math.max(...rooms.map((r) => Number(r.y) + Number(r.h))) + 1;
  const scale = 34;

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
