import DeckGL from "@deck.gl/react";
import { HeatmapLayer } from "@deck.gl/aggregation-layers";
import Map from "react-map-gl/maplibre";
import "maplibre-gl/dist/maplibre-gl.css";

const INITIAL_VIEW = {
  longitude: 2.3488,
  latitude:  48.8534,
  zoom:      12,
  pitch:     0,
  bearing:   0,
};

// Free tile style — no token required
const MAP_STYLE = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";

export default function MapView({ data }) {
  const layer = new HeatmapLayer({
    id:           "heatmap",
    data,
    getPosition:  (d) => [d.lon, d.lat],
    getWeight:    (d) => d.value ?? 0,
    radiusPixels: 40,
    intensity:    1,
    threshold:    0.03,
  });

  return (
    <div style={{ flex: 1, position: "relative" }}>
      <DeckGL
        initialViewState={INITIAL_VIEW}
        controller
        layers={[layer]}
      >
        <Map mapStyle={MAP_STYLE} />
      </DeckGL>
    </div>
  );
}
