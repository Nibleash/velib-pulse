# 🚲 Vélib' Pulse

![Vélib' Pulse banner](https://placehold.co/900x180/0f172a/22d3ee?text=V%C3%A9lib%27+Pulse+%F0%9F%9A%B2)

Vélib' Pulse est une app statique qui affiche une heatmap de disponibilité des stations Vélib' (mécaniques, électriques, places libres) selon le jour et l'heure.

App déployée : [Vélib' Pulse](https://velib-pulse.vercel.app/)

## Structure rapide

- `public/index.html` : interface carte + heatmap
- `scripts/preprocess.py` : génère `public/data.json` à partir des exports CSV
- `collector/collector.py` : collecte GBFS et agrège les données dans Supabase
- `supabase_schema/schema.sql` : schéma SQL utilisé côté Supabase

## Usage local

```bash
py scripts/preprocess.py
py -m http.server 8000 --directory public
```

Puis ouvrir `http://localhost:8000`.

## Dépendances Python

```bash
pip install -r requirements.txt
```

## Licence

MIT
