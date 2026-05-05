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
DROP VIEW IF EXISTS aggregated_availability;

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

-- ── Vue publique (compatibilité avec le schéma v1) ───────────────────────

CREATE OR REPLACE VIEW v_aggregated_availability AS
SELECT
    station_id,
    dow,
    slot_min,
    ROUND(sum_mechanical::float / NULLIF(sample_count, 0))::INT AS avg_mechanical,
    ROUND(sum_ebike::float      / NULLIF(sample_count, 0))::INT AS avg_ebike,
    ROUND(sum_docks::float      / NULLIF(sample_count, 0))::INT AS avg_docks,
    sample_count
FROM aggregated_availability;

-- ── Fonction RPC appelée par le collecteur ───────────────────────────────
--  Paramètre : tableau JSON  [{"station_id": ..., "meca": ..., "ebike": ..., "docks": ...,
--                               "dow": ..., "slot_min": ...}, ...]

CREATE OR REPLACE FUNCTION upsert_aggregated_availability(snapshots JSONB)
RETURNS void LANGUAGE plpgsql AS $$
DECLARE
    s JSONB;
BEGIN
    FOR s IN SELECT * FROM jsonb_array_elements(snapshots)
    LOOP
        INSERT INTO aggregated_availability
               (station_id, dow, slot_min, sum_mechanical, sum_ebike, sum_docks, sample_count)
        VALUES ((s->>'station_id')::BIGINT,
                (s->>'dow')::SMALLINT,
                (s->>'slot_min')::SMALLINT,
                (s->>'meca')::INT,
                (s->>'ebike')::INT,
                (s->>'docks')::INT,
                1)
        ON CONFLICT (station_id, dow, slot_min) DO UPDATE SET
            sum_mechanical = aggregated_availability.sum_mechanical + EXCLUDED.sum_mechanical,
            sum_ebike      = aggregated_availability.sum_ebike      + EXCLUDED.sum_ebike,
            sum_docks      = aggregated_availability.sum_docks      + EXCLUDED.sum_docks,
            sample_count   = aggregated_availability.sample_count   + 1;
    END LOOP;
END;
$$;
