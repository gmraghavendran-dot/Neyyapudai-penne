-- Idempotent operational/analytics schema.
-- The canonical executable version is backend/database/models.py.
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS analytics;

-- Existing core.dataset_registry is preserved. The application only creates it
-- when it does not already exist.
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

CREATE TABLE IF NOT EXISTS core.audit_events (
    event_id BIGSERIAL PRIMARY KEY,
    event_type TEXT NOT NULL,
    entity_type TEXT,
    entity_id BIGINT,
    payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
