-- ════════════════════════════════════════════════════════════════════════
--  Velib-Pulse — Schéma v2  (agrégation incrémentale, quota borné)
-- ════════════════════════════════════════════════════════════════════════
--
--  PROBLÈME v1 : station_snapshots stocke TOUTES les lectures brutes.
--    1 496 stations × 96 créneaux/jour × 21 jours (3 sem.) = ~3 M lignes
--    soit ~150 Mo de données + ~100 Mo d'index ≈ 250–300 Mo → quota 500 Mo
--    atteint en quelques mois.
--
--  SOLUTION v2 : on ne stocke plus les snapshots bruts.
--    À chaque collecte on UPSERT directement la somme + le compteur dans
--    `aggregated_availability`.  Le stockage est borné à :
--      1 496 stations × 7 jours × 96 créneaux = 1 005 312 lignes max
--    ≈ 60–80 Mo (données + index) — indépendamment de la durée de collecte.
--
-- ════════════════════════════════════════════════════════════════════════

-- ── Nettoyage des objets v1 (à exécuter avant la création des tables) ────

-- La vue v1 porte le même nom que la nouvelle table : on la supprime d'abord.
-- Ce bloc gère les deux cas : si c'est encore une vue OU déjà une table.
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public' AND c.relname = 'aggregated_availability' AND c.relkind = 'v'
  ) THEN
    DROP VIEW public.aggregated_availability;
  END IF;
END;
$$;

-- ── Tables ───────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS station_information (
    station_id  BIGINT PRIMARY KEY,
    name        TEXT             NOT NULL,
    lat         DOUBLE PRECISION NOT NULL,
    lon         DOUBLE PRECISION NOT NULL,
    capacity    INT              NOT NULL
);

-- Table principale : moyenne glissante par (station, dow, créneau 15 min)
CREATE TABLE IF NOT EXISTS aggregated_availability (
    station_id      BIGINT   NOT NULL REFERENCES station_information(station_id),
    dow             SMALLINT NOT NULL CHECK (dow BETWEEN 1 AND 7),   -- 1=Lun…7=Dim (ISO)
    slot_min        SMALLINT NOT NULL CHECK (slot_min BETWEEN 0 AND 1425),  -- pas de 15 min
    sum_mechanical  BIGINT   NOT NULL DEFAULT 0,
    sum_ebike       BIGINT   NOT NULL DEFAULT 0,
    sum_docks       BIGINT   NOT NULL DEFAULT 0,
    sample_count    BIGINT   NOT NULL DEFAULT 0,
    PRIMARY KEY (station_id, dow, slot_min)
);

CREATE INDEX IF NOT EXISTS idx_agg_dow_slot ON aggregated_availability (dow, slot_min);

-- ── Row Level Security ────────────────────────────────────────────────────
-- RLS activé : les tables ne sont pas accessibles directement en écriture.
-- Les écritures passent exclusivement par les fonctions RPC SECURITY DEFINER
-- ci-dessous, qui s'exécutent avec les droits du propriétaire (postgres).

ALTER TABLE station_information     ENABLE ROW LEVEL SECURITY;
ALTER TABLE aggregated_availability ENABLE ROW LEVEL SECURITY;

-- Lecture publique (pour exports, dashboard, etc.)
DROP POLICY IF EXISTS "public read station_information"     ON station_information;
DROP POLICY IF EXISTS "public read aggregated_availability" ON aggregated_availability;

CREATE POLICY "public read station_information"
  ON station_information FOR SELECT USING (true);

CREATE POLICY "public read aggregated_availability"
  ON aggregated_availability FOR SELECT USING (true);

-- ── Vue publique (compatibilité avec le schéma v1) ───────────────────────

CREATE OR REPLACE VIEW public.v_aggregated_availability
WITH (security_invoker = on)
AS
SELECT
    station_id,
    dow,
    slot_min,
    ROUND(sum_mechanical::float / NULLIF(sample_count, 0))::INT AS avg_mechanical,
    ROUND(sum_ebike::float      / NULLIF(sample_count, 0))::INT AS avg_ebike,
    ROUND(sum_docks::float      / NULLIF(sample_count, 0))::INT AS avg_docks,
    sample_count
FROM aggregated_availability;

-- ── Fonctions RPC appelées par le collecteur ─────────────────────────────
-- SECURITY DEFINER : s'exécutent avec les droits du propriétaire (postgres),
-- ce qui leur permet d'écrire dans les tables protégées par RLS.
-- SET search_path = public : bonne pratique obligatoire avec SECURITY DEFINER.

-- 1. Upsert des infos stations
--    Paramètre : tableau JSON [{"station_id":…,"name":…,"lat":…,"lon":…,"capacity":…}, …]

CREATE OR REPLACE FUNCTION upsert_station_information(stations JSONB)
RETURNS void LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    s JSONB;
BEGIN
    FOR s IN SELECT * FROM jsonb_array_elements(stations)
    LOOP
        INSERT INTO station_information (station_id, name, lat, lon, capacity)
        VALUES (
            (s->>'station_id')::BIGINT,
            s->>'name',
            (s->>'lat')::DOUBLE PRECISION,
            (s->>'lon')::DOUBLE PRECISION,
            (s->>'capacity')::INT
        )
        ON CONFLICT (station_id) DO UPDATE SET
            name     = EXCLUDED.name,
            lat      = EXCLUDED.lat,
            lon      = EXCLUDED.lon,
            capacity = EXCLUDED.capacity;
    END LOOP;
END;
$$;

-- 2. Upsert des disponibilités agrégées
--    Paramètre : tableau JSON [{"station_id":…,"dow":…,"slot_min":…,"meca":…,"ebike":…,"docks":…}, …]

CREATE OR REPLACE FUNCTION upsert_aggregated_availability(snapshots JSONB)
RETURNS void LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  INSERT INTO aggregated_availability
       (station_id, dow, slot_min, sum_mechanical, sum_ebike, sum_docks, sample_count)
  SELECT
    station_id,
    dow,
    slot_min,
    SUM(COALESCE(meca, 0))::BIGINT,
    SUM(COALESCE(ebike, 0))::BIGINT,
    SUM(COALESCE(docks, 0))::BIGINT,
    COUNT(*)::BIGINT
  FROM jsonb_to_recordset(snapshots)
     AS s(station_id BIGINT, dow SMALLINT, slot_min SMALLINT, meca INT, ebike INT, docks INT)
  GROUP BY station_id, dow, slot_min
  ON CONFLICT (station_id, dow, slot_min) DO UPDATE SET
    sum_mechanical = aggregated_availability.sum_mechanical + EXCLUDED.sum_mechanical,
    sum_ebike      = aggregated_availability.sum_ebike      + EXCLUDED.sum_ebike,
    sum_docks      = aggregated_availability.sum_docks      + EXCLUDED.sum_docks,
    sample_count   = aggregated_availability.sample_count   + EXCLUDED.sample_count;
END;
$$;
