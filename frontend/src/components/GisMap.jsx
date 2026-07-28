import { useState } from "react";
import { MapContainer, TileLayer, Polygon, Polyline, CircleMarker, LayersControl, Tooltip } from "react-leaflet";
import "leaflet/dist/leaflet.css";

const LAYERS = [
  ["buildings", "Buildings", "#64748B", 0.45],
  ["roads", "Roads", "#F59E0B", 0],
  ["green", "Green areas", "#16A34A", 0.3],
  ["water", "Water bodies", "#0EA5E9", 0.45],
  ["transit", "Transit stops", "#7C3AED", 0.9],
];

export const GisMap = ({ coordinates = [], features = {}, height = 460 }) => {
  const [visible, setVisible] = useState({ buildings: true, roads: true, green: true, water: true, transit: true });
  const center = coordinates.length
    ? [
        coordinates.reduce((s, c) => s + c[0], 0) / coordinates.length,
        coordinates.reduce((s, c) => s + c[1], 0) / coordinates.length,
      ]
    : [12.9716, 77.5946];

  return (
    <div className="relative">
      <div className="absolute z-[500] top-2 left-2 bg-white border border-slate-200 rounded-sm p-2 space-y-1" data-testid="gis-layer-toggles">
        {LAYERS.map(([key, label, color]) => (
          <label key={key} className="flex items-center gap-2 text-[11px] cursor-pointer">
            <input
              type="checkbox"
              checked={visible[key]}
              data-testid={`gis-layer-${key}`}
              onChange={(e) => setVisible((v) => ({ ...v, [key]: e.target.checked }))}
            />
            <span className="h-2.5 w-2.5 rounded-sm" style={{ background: color }} />
            {label}
            <span className="font-mono text-slate-400">{(features[key] || []).length}</span>
          </label>
        ))}
      </div>
      <MapContainer center={center} zoom={17} style={{ height, width: "100%" }} className="rounded-sm z-0">
        <LayersControl position="topright">
          <LayersControl.BaseLayer name="OpenStreetMap">
            <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution="&copy; OpenStreetMap" />
          </LayersControl.BaseLayer>
          <LayersControl.BaseLayer checked name="Satellite">
            <TileLayer
              url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
              attribution="Tiles &copy; Esri"
            />
          </LayersControl.BaseLayer>
        </LayersControl>

        {LAYERS.map(([key, label, color, fill]) =>
          visible[key]
            ? (features[key] || []).slice(0, 90).map((f) =>
                key === "transit" || f.geometry.length === 1 ? (
                  <CircleMarker key={`${key}-${f.id}`} center={f.geometry[0]} radius={5}
                    pathOptions={{ color, fillColor: color, fillOpacity: fill }}>
                    <Tooltip>{`${f.name || f.kind} · ${f.distance_m} m`}</Tooltip>
                  </CircleMarker>
                ) : key === "roads" ? (
                  <Polyline key={`${key}-${f.id}`} positions={f.geometry} pathOptions={{ color, weight: 3, opacity: 0.85 }}>
                    <Tooltip>{`${f.name || f.kind} · ${f.road_width_m || "?"} m wide · ${f.distance_m} m away`}</Tooltip>
                  </Polyline>
                ) : (
                  <Polygon key={`${key}-${f.id}`} positions={f.geometry}
                    pathOptions={{ color, weight: 1, fillOpacity: fill }}>
                    <Tooltip>{`${f.name || f.kind} · ${f.distance_m} m away`}</Tooltip>
                  </Polygon>
                )
              )
            : null
        )}

        {coordinates.length >= 3 && (
          <Polygon positions={coordinates} pathOptions={{ color: "#2563EB", weight: 3, fillOpacity: 0.12 }}>
            <Tooltip>Project plot boundary</Tooltip>
          </Polygon>
        )}
      </MapContainer>
    </div>
  );
};
