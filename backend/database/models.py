from sqlalchemy import text
from backend.database.connection import engine

OPERATIONAL_SCHEMA_SQL = """
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS core.dataset_registry (
    dataset_id BIGSERIAL PRIMARY KEY,
    file_name TEXT NOT NULL, file_path TEXT, table_name TEXT, file_hash TEXT,
    row_count BIGINT DEFAULT 0, column_count INTEGER DEFAULT 0, year TEXT, geography TEXT,
    status TEXT DEFAULT 'SUCCESS', loaded_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS core.incidents (
    incident_id BIGSERIAL PRIMARY KEY,
    incident_type TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'medium',
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    location_label TEXT,
    reported_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'open',
    source TEXT NOT NULL DEFAULT 'dashboard',
    description TEXT,
    risk_score DOUBLE PRECISION DEFAULT 0,
    assigned_responder_id BIGINT,
    resolved_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS core.responders (
    responder_id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    responder_type TEXT NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    status TEXT NOT NULL DEFAULT 'available',
    phone TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS core.response_events (
    response_id BIGSERIAL PRIMARY KEY,
    incident_id BIGINT NOT NULL REFERENCES core.incidents(incident_id) ON DELETE CASCADE,
    responder_id BIGINT REFERENCES core.responders(responder_id),
    dispatched_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    arrived_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    eta_minutes DOUBLE PRECISION,
    response_time_minutes DOUBLE PRECISION,
    outcome TEXT
);

CREATE TABLE IF NOT EXISTS core.sos_events (
    sos_id BIGSERIAL PRIMARY KEY,
    incident_id BIGINT REFERENCES core.incidents(incident_id) ON DELETE SET NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    triggered_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'active',
    device_ref TEXT
);

CREATE TABLE IF NOT EXISTS core.mobility_checks (
    check_id BIGSERIAL PRIMARY KEY,
    origin_lat DOUBLE PRECISION NOT NULL,
    origin_lng DOUBLE PRECISION NOT NULL,
    destination_lat DOUBLE PRECISION NOT NULL,
    destination_lng DOUBLE PRECISION NOT NULL,
    route_name TEXT,
    distance_km DOUBLE PRECISION,
    risk_score DOUBLE PRECISION,
    lighting_score DOUBLE PRECISION,
    transport_score DOUBLE PRECISION,
    context_source TEXT DEFAULT 'historical_operational_proxy',
    generated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS core.outcome_events (
    outcome_id BIGSERIAL PRIMARY KEY,
    incident_id BIGINT REFERENCES core.incidents(incident_id) ON DELETE SET NULL,
    resolution_type TEXT,
    resolved_at TIMESTAMPTZ,
    effectiveness_score DOUBLE PRECISION,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS core.area_directory (
    area_id BIGSERIAL PRIMARY KEY,
    area_name TEXT UNIQUE NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    zone TEXT NOT NULL DEFAULT 'Chennai',
    active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS core.audit_events (
    event_id BIGSERIAL PRIMARY KEY,
    event_type TEXT NOT NULL,
    entity_type TEXT,
    entity_id BIGINT,
    payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE core.mobility_checks ADD COLUMN IF NOT EXISTS context_source TEXT DEFAULT 'historical_operational_proxy';
ALTER TABLE core.incidents ADD COLUMN IF NOT EXISTS risk_score DOUBLE PRECISION DEFAULT 0;
ALTER TABLE core.incidents ADD COLUMN IF NOT EXISTS assigned_responder_id BIGINT;
ALTER TABLE core.incidents ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMPTZ;
ALTER TABLE core.responders ADD COLUMN IF NOT EXISTS phone TEXT;

CREATE TABLE IF NOT EXISTS analytics.dataset_profile (
    table_name TEXT PRIMARY KEY,
    file_name TEXT,
    row_count BIGINT DEFAULT 0,
    column_count INTEGER DEFAULT 0,
    geography_column TEXT,
    signal_column TEXT,
    safety_relevance DOUBLE PRECISION DEFAULT 0,
    focus TEXT DEFAULT 'other',
    women_signal_score DOUBLE PRECISION DEFAULT 0,
    general_signal_score DOUBLE PRECISION DEFAULT 0,
    profiled_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE analytics.dataset_profile ADD COLUMN IF NOT EXISTS focus TEXT DEFAULT 'other';
ALTER TABLE analytics.dataset_profile ADD COLUMN IF NOT EXISTS women_signal_score DOUBLE PRECISION DEFAULT 0;
ALTER TABLE analytics.dataset_profile ADD COLUMN IF NOT EXISTS general_signal_score DOUBLE PRECISION DEFAULT 0;

CREATE TABLE IF NOT EXISTS analytics.area_risk (
    area TEXT PRIMARY KEY,
    risk_score DOUBLE PRECISION NOT NULL,
    incident_signal DOUBLE PRECISION DEFAULT 0,
    infrastructure_gap DOUBLE PRECISION DEFAULT 0,
    source_datasets INTEGER DEFAULT 0,
    women_safety_share DOUBLE PRECISION DEFAULT 0,
    trend TEXT DEFAULT 'stable',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE analytics.area_risk ADD COLUMN IF NOT EXISTS women_safety_share DOUBLE PRECISION DEFAULT 0;

CREATE TABLE IF NOT EXISTS analytics.time_risk (
    hour INTEGER PRIMARY KEY,
    risk_score DOUBLE PRECISION NOT NULL,
    label TEXT,
    source TEXT DEFAULT 'contextual_prior',
    observed_incidents INTEGER DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE analytics.time_risk ADD COLUMN IF NOT EXISTS observed_incidents INTEGER DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_incidents_status ON core.incidents(status);
CREATE INDEX IF NOT EXISTS idx_incidents_reported_at ON core.incidents(reported_at DESC);
CREATE INDEX IF NOT EXISTS idx_incidents_location ON core.incidents(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_response_incident ON core.response_events(incident_id);
CREATE INDEX IF NOT EXISTS idx_outcome_incident ON core.outcome_events(incident_id);
"""


def initialize_operational_schema() -> None:
    with engine.begin() as conn:
        for statement in OPERATIONAL_SCHEMA_SQL.split(";"):
            statement = statement.strip()
            if statement:
                conn.execute(text(statement))


def seed_responders() -> None:
    with engine.begin() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM core.responders")).scalar_one()
        if count:
            return
        responders = [
            ("Chennai Police Unit A", "police", 13.0827, 80.2707, "available"),
            ("Chennai Police Unit B", "police", 13.0674, 80.2376, "available"),
            ("Emergency Medical Team", "ambulance", 13.0475, 80.2090, "available"),
            ("Women Help Response Team", "women_safety", 13.0569, 80.2425, "available"),
            ("North Zone Patrol", "police", 13.1155, 80.2870, "available"),
        ]
        conn.execute(
            text("""INSERT INTO core.responders
            (name,responder_type,latitude,longitude,status)
            VALUES (:name,:type,:lat,:lng,:status)"""),
            [{"name": r[0], "type": r[1], "lat": r[2], "lng": r[3], "status": r[4]} for r in responders],
        )
