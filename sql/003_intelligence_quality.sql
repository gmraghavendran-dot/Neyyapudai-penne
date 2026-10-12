-- Idempotent intelligence-layer migration.
ALTER TABLE analytics.dataset_profile ADD COLUMN IF NOT EXISTS focus TEXT DEFAULT 'other';
ALTER TABLE analytics.dataset_profile ADD COLUMN IF NOT EXISTS women_signal_score DOUBLE PRECISION DEFAULT 0;
ALTER TABLE analytics.dataset_profile ADD COLUMN IF NOT EXISTS general_signal_score DOUBLE PRECISION DEFAULT 0;
ALTER TABLE analytics.area_risk ADD COLUMN IF NOT EXISTS women_safety_share DOUBLE PRECISION DEFAULT 0;
ALTER TABLE analytics.time_risk ADD COLUMN IF NOT EXISTS observed_incidents INTEGER DEFAULT 0;
ALTER TABLE core.mobility_checks ADD COLUMN IF NOT EXISTS context_source TEXT DEFAULT 'historical_operational_proxy';

-- The raw NCRB layer is intentionally not altered by this migration.
