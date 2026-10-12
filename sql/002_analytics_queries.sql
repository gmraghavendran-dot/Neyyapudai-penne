-- Verification queries for the existing database.
SELECT COUNT(*) AS total_datasets FROM core.dataset_registry;
SELECT COUNT(*) AS successful_datasets FROM core.dataset_registry WHERE status='SUCCESS';
SELECT COUNT(*) AS raw_tables FROM information_schema.tables WHERE table_schema='raw' AND table_type='BASE TABLE';
SELECT COUNT(*) AS safety_profiles FROM analytics.dataset_profile WHERE safety_relevance >= 0.25;
SELECT * FROM analytics.area_risk ORDER BY risk_score DESC LIMIT 10;
SELECT * FROM analytics.time_risk ORDER BY risk_score DESC LIMIT 10;
SELECT * FROM core.incidents ORDER BY reported_at DESC LIMIT 20;
SELECT * FROM core.response_events ORDER BY dispatched_at DESC LIMIT 20;
SELECT * FROM core.outcome_events ORDER BY resolved_at DESC LIMIT 20;
