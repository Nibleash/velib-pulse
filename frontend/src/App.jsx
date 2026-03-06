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
      <MapView data={data} type={type} />
    </>
  );
}
