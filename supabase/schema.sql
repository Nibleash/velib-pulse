-- ─── Tables ────────────────────────────────────────────────────────────────

CREATE TABLE station_information (
    station_id  BIGINT PRIMARY KEY,
    name        TEXT   NOT NULL,
    lat         DOUBLE PRECISION NOT NULL,
    lon         DOUBLE PRECISION NOT NULL,
    capacity    INT    NOT NULL
);

CREATE TABLE station_snapshots (
    id            BIGSERIAL PRIMARY KEY,
    station_id    BIGINT    NOT NULL REFERENCES station_information(station_id),
    captured_at   TIMESTAMPTZ NOT NULL,
    mechanical    SMALLINT  NOT NULL DEFAULT 0,
    ebike         SMALLINT  NOT NULL DEFAULT 0,
    docks_available SMALLINT NOT NULL DEFAULT 0
);

-- Index for aggregation queries (day-of-week + time slot)
CREATE INDEX idx_snapshots_time ON station_snapshots (station_id, captured_at);

-- ─── Purge function (rolling 3 weeks) ────────────────────────────────────────

CREATE OR REPLACE FUNCTION purge_old_snapshots()
RETURNS void LANGUAGE sql AS $$
    DELETE FROM station_snapshots
    WHERE captured_at < NOW() - INTERVAL '3 weeks';
$$;

-- ─── Aggregation view ─────────────────────────────────────────────────────────
-- Returns average availability per station / day-of-week / 15-min slot

CREATE OR REPLACE VIEW aggregated_availability AS
SELECT
    station_id,
    EXTRACT(ISODOW FROM captured_at AT TIME ZONE 'Europe/Paris')::INT  AS dow,        -- 1=Mon … 7=Sun
    (EXTRACT(HOUR   FROM captured_at AT TIME ZONE 'Europe/Paris') * 60
   + FLOOR(EXTRACT(MINUTE FROM captured_at AT TIME ZONE 'Europe/Paris') / 15) * 15
    )::INT                                                               AS slot_min,  -- minutes since midnight, step 15
    ROUND(AVG(mechanical))::INT       AS avg_mechanical,
    ROUND(AVG(ebike))::INT            AS avg_ebike,
    ROUND(AVG(docks_available))::INT  AS avg_docks
FROM station_snapshots
GROUP BY station_id, dow, slot_min;
