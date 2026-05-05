# 🚲 Vélib' Pulse

> Heatmap interactive de la disponibilité des vélos Vélib' à Paris, par jour de la semaine et créneau horaire.

**[→ Voir la démo live](https://velib-pulse.vercel.app)** *(après déploiement)*

![Capture d'écran de l'app](https://placehold.co/800x450/0f172a/22d3ee?text=Vélib'+Pulse+Heatmap)

---

## Fonctionnalités

- 🗺 Fond de carte **CartoDB Dark** (données OpenStreetMap)
- 🔥 **Heatmap** des 1 496 stations Vélib' d'Île-de-France
- 📅 Sélection du **jour de la semaine** (Lun → Dim)
- 🕐 **Slider horaire** par créneaux de 15 min (00:00 → 23:45)
- ⬅ ➡ Navigation au clavier par flèches
- ▶ **Animation automatique** de la journée
- Trois métriques : **vélos mécaniques**, **vélos électriques**, **places libres**
- Statistiques en temps réel (total disponible, stations actives)

---

## Architecture

```
collector/
  collector.py          ← Collecte GBFS → Supabase (agrégation incrémentale)
  requirements.txt

data/
  Station Information.csv              ← Export Supabase (station_information)
  Velib Aggregated Availability.csv    ← Export Supabase (aggregated_availability)

scripts/
  preprocess.py         ← Convertit les CSV → public/data.json

public/
  index.html            ← Application statique (Leaflet + Leaflet.heat)
  data.json             ← Données prétraitées (généré par preprocess.py)

supabase_schema/
  schema.sql            ← Schéma (agrégation incrémentale, quota borné)

vercel.json             ← Configuration de déploiement Vercel
```

---

## Problème de quota Supabase & solution

### Pourquoi le quota 500 Mo est atteint (ancienne approche)

L'ancienne architecture stockait **toutes les lectures brutes** dans `station_snapshots` :

```
1 496 stations × 96 collectes/jour × 21 jours (rétention 3 sem.) ≈ 3 M lignes ≈ 250 Mo
```

Même avec la purge automatique, le quota est atteint en quelques mois d'accumulation d'index.

### Solution : agrégation incrémentale

Au lieu de stocker les snapshots bruts, le collecteur **accumule directement les sommes** dans une table `aggregated_availability` avec la clé `(station_id, dow, slot_min)`.

| | Ancienne approche (snapshots bruts) | Nouvelle approche (agrégation) |
|---|---|---|
| Lignes max | ~3 M (et croissantes) | **~1 M (bornées à jamais)** |
| Taille estimée | 250–450 Mo | **~60–80 Mo** |
| Purge nécessaire | Oui (rolling 3 semaines) | **Non** |
| Précision | Données exactes | Moyenne glissante (identique pour l’usage) |

Pour migrer :
1. Exécuter `supabase_schema/schema.sql` dans l'éditeur SQL Supabase
2. Supprimer l'ancienne table `station_snapshots` (libère l'espace)

---

## Générer les données statiques

### Prérequis

- Python 3.10+
- Les deux CSV dans `data/` (exports Supabase)

### Lancer le prétraitement

```bash
py scripts/preprocess.py
```

Cela génère `public/data.json` (~9 Mo brut, ~2 Mo servi par Vercel après gzip).

---

## Déploiement sur Vercel (pas à pas)

### 1. Pré-requis

- Un compte [Vercel](https://vercel.com) (gratuit)
- [Git](https://git-scm.com) installé
- Le fichier `public/data.json` généré (voir ci-dessus)

### 2. Pousser le projet sur GitHub

```bash
# Si ce n'est pas encore fait :
git init
git remote add origin https://github.com/Nibleash/velib-pulse.git

# S'assurer que data.json est inclus (pas dans .gitignore)
git add public/data.json public/index.html vercel.json scripts/ supabase_schema/ collector/ README.md
git commit -m "feat: add static heatmap app"
git push origin main
```

> ⚠️ `data.json` fait ~9 Mo. GitHub accepte les fichiers jusqu'à 100 Mo. Si le dépôt devient trop lourd après de futures mises à jour, envisager [Git LFS](https://git-lfs.github.com).

### 3. Importer le projet dans Vercel

1. Aller sur **[vercel.com/new](https://vercel.com/new)**
2. Cliquer **"Import Git Repository"** → choisir `Nibleash/velib-pulse`
3. Vercel détecte automatiquement `vercel.json` → **outputDirectory = `public`**
4. Laisser les autres paramètres par défaut
5. Cliquer **"Deploy"**

Vercel construit et déploie le site en ~30 secondes. Une URL en `.vercel.app` est assignée.

### 4. Domaine personnalisé (optionnel)

Dans le dashboard Vercel → *Settings → Domains* → ajouter votre domaine.

### 5. Mettre à jour les données

Quand vous disposez d'un nouveau export CSV :

```bash
py scripts/preprocess.py          # régénère public/data.json
git add public/data.json
git commit -m "data: update aggregated availability"
git push origin main              # Vercel redéploie automatiquement
```

---

## Développement local

```bash
# Serveur HTTP simple (nécessaire pour fetch('data.json'))
py -m http.server 8000 --directory public
# Puis ouvrir http://localhost:8000
```

---

## Stack technique

| Composant | Technologie |
|---|---|
| Carte | [Leaflet.js](https://leafletjs.com) 1.9 |
| Heatmap | [Leaflet.heat](https://github.com/Leaflet/Leaflet.heat) |
| Tuiles | [CartoDB Dark Matter](https://carto.com/basemaps/) (OpenStreetMap) |
| Données | API GBFS [Vélib' Métropole](https://www.velib-metropole.fr/donnees-open-data-gbfs-du-service-velib-metropole) |
| Backend (collecte) | [Supabase](https://supabase.com) (PostgreSQL) |
| Hébergement | [Vercel](https://vercel.com) |
| Prétraitement | Python 3.10+ (stdlib uniquement) |

---

## Licence

MIT — Données Vélib' © Smovengo / Île-de-France Mobilités, tuiles © OpenStreetMap contributors, © CARTO.
