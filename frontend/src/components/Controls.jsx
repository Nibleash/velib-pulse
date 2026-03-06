const slotLabel = (min) =>
  `${String(Math.floor(min / 60)).padStart(2, "0")}:${String(min % 60).padStart(2, "0")}`;

const slots = Array.from({ length: 96 }, (_, i) => i * 15); // 0 → 1425

const styles = {
  bar:    { display: "flex", gap: 16, alignItems: "center", padding: "12px 16px", background: "#1a1a1a", flexWrap: "wrap" },
  label:  { fontSize: 12, color: "#aaa", marginBottom: 4 },
  group:  { display: "flex", flexDirection: "column" },
  select: { background: "#2a2a2a", color: "#f0f0f0", border: "1px solid #444", borderRadius: 6, padding: "4px 8px", fontSize: 14 },
  spin:   { fontSize: 12, color: "#888" },
};

export default function Controls({ dow, onDowChange, slotMin, onSlotChange, type, onTypeChange, dowLabels, loading }) {
  return (
    <div style={styles.bar}>
      <div style={styles.group}>
        <span style={styles.label}>Jour</span>
        <select style={styles.select} value={dow} onChange={(e) => onDowChange(Number(e.target.value))}>
          {dowLabels.map((d, i) => <option key={i} value={i + 1}>{d}</option>)}
        </select>
      </div>

      <div style={styles.group}>
        <span style={styles.label}>Créneau</span>
        <select style={styles.select} value={slotMin} onChange={(e) => onSlotChange(Number(e.target.value))}>
          {slots.map((m) => <option key={m} value={m}>{slotLabel(m)}</option>)}
        </select>
      </div>

      <div style={styles.group}>
        <span style={styles.label}>Type</span>
        <select style={styles.select} value={type} onChange={(e) => onTypeChange(e.target.value)}>
          <option value="ebike">Vélo électrique</option>
          <option value="mechanical">Vélo mécanique</option>
          <option value="docks">Places libres</option>
        </select>
      </div>

      {loading && <span style={styles.spin}>Chargement…</span>}
    </div>
  );
}
