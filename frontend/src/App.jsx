import { useState } from "react";
import Controls from "./components/Controls.jsx";
import MapView from "./components/MapView.jsx";
import useAvailability from "./hooks/useAvailability.js";

const DOW_LABELS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"];

export default function App() {
  const [dow,     setDow]     = useState(1);         // 1 = lundi
  const [slotMin, setSlotMin] = useState(480);       // 08:00
  const [type,    setType]    = useState("ebike");

  const { data, loading } = useAvailability(dow, slotMin, type);

  return (
    <>
      <Controls
        dow={dow}         onDowChange={setDow}
        slotMin={slotMin} onSlotChange={setSlotMin}
        type={type}       onTypeChange={setType}
        dowLabels={DOW_LABELS}
        loading={loading}
      />
      
      {/* DEBUG: Affichage tableau */}
      <div style={{ padding: '20px', background: '#1a1a1a', color: 'white', maxHeight: '300px', overflow: 'auto' }}>
        <h3>Debug - Données reçues ({data.length} stations)</h3>
        {loading && <p>Chargement...</p>}
        {!loading && data.length === 0 && <p>❌ Aucune donnée reçue</p>}
        {data.length > 0 && (
          <table style={{ width: '100%', fontSize: '12px', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={{ border: '1px solid #444', padding: '5px' }}>Station ID</th>
                <th style={{ border: '1px solid #444', padding: '5px' }}>Nom</th>
                <th style={{ border: '1px solid #444', padding: '5px' }}>Lat</th>
                <th style={{ border: '1px solid #444', padding: '5px' }}>Lon</th>
                <th style={{ border: '1px solid #444', padding: '5px' }}>Valeur</th>
              </tr>
            </thead>
            <tbody>
              {data.slice(0, 10).map((d) => (
                <tr key={d.station_id}>
                  <td style={{ border: '1px solid #444', padding: '5px' }}>{d.station_id}</td>
                  <td style={{ border: '1px solid #444', padding: '5px' }}>{d.name}</td>
                  <td style={{ border: '1px solid #444', padding: '5px' }}>{d.lat}</td>
                  <td style={{ border: '1px solid #444', padding: '5px' }}>{d.lon}</td>
                  <td style={{ border: '1px solid #444', padding: '5px' }}>{d.value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      
      <MapView data={data} type={type} />
    </>
  );
}
