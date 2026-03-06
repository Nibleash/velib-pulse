import { useState, useEffect } from "react";

const API = import.meta.env.VITE_API_URL;

export default function useAvailability(dow, slotMin, type) {
  const [data,    setData]    = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!API) return;
    setLoading(true);
    fetch(`${API}/availability?dow=${dow}&slot_min=${slotMin}&type=${type}`)
      .then((r) => r.json())
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [dow, slotMin, type]);

  return { data, loading };
}
