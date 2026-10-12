from backend.database.repository import rows


def outcomes():
    return {
        "summary": rows("""
            SELECT COUNT(*) AS total_outcomes,
                   COALESCE(ROUND(AVG(effectiveness_score)::numeric,1),0) AS avg_effectiveness,
                   COUNT(*) FILTER (WHERE effectiveness_score >= 80) AS effective_resolutions
            FROM core.outcome_events
        """)[0],
        "resolution": rows("""
            SELECT COALESCE(resolution_type,'unclassified') AS resolution_type,
                   COUNT(*) AS incidents,
                   COALESCE(ROUND(AVG(effectiveness_score)::numeric,1),0) AS effectiveness
            FROM core.outcome_events GROUP BY 1 ORDER BY incidents DESC
        """),
        "recurring_areas": rows("""
            SELECT COALESCE(NULLIF(location_label,''),'Unknown location') AS area,
                   COUNT(*) AS incidents,
                   COALESCE(ROUND(AVG(risk_score)::numeric,1),0) AS avg_risk
            FROM core.incidents GROUP BY 1 ORDER BY incidents DESC,avg_risk DESC LIMIT 15
        """),
        "response_learning": rows("""
            SELECT COALESCE(ROUND(AVG(re.response_time_minutes)::numeric,1),0) AS avg_response_minutes,
                   COUNT(*) FILTER (WHERE re.response_time_minutes <= 10) AS within_10_minutes,
                   COUNT(*) AS completed_responses
            FROM core.response_events re WHERE re.response_time_minutes IS NOT NULL
        """)[0],
        "before_after": rows("""
            SELECT DATE_TRUNC('day',reported_at)::date AS day,
                   COUNT(*) AS incidents,
                   COALESCE(ROUND(AVG(risk_score)::numeric,1),0) AS avg_risk
            FROM core.incidents GROUP BY 1 ORDER BY 1 DESC LIMIT 30
        """),
        "period_comparison": rows("""
            WITH buckets AS (
                SELECT CASE WHEN reported_at >= CURRENT_TIMESTAMP - INTERVAL '7 days' THEN 'Recent 7 days' ELSE 'Previous 7 days' END AS period,
                       COUNT(*) AS incidents,
                       COALESCE(ROUND(AVG(risk_score)::numeric,1),0) AS avg_risk
                FROM core.incidents
                WHERE reported_at >= CURRENT_TIMESTAMP - INTERVAL '14 days'
                GROUP BY 1
            ) SELECT * FROM buckets ORDER BY period DESC
        """),
    }
