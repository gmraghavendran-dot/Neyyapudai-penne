from backend.database.repository import rows
from backend.services.analytics_engine import refresh_analytics


def dashboard_risk():
    area = rows("SELECT * FROM analytics.area_risk ORDER BY risk_score DESC LIMIT 100")
    time = rows("SELECT * FROM analytics.time_risk ORDER BY hour")
    profiles = rows("""
        SELECT table_name,file_name,row_count,column_count,geography_column,signal_column,safety_relevance,focus,women_signal_score,general_signal_score,profiled_at
        FROM analytics.dataset_profile
        WHERE safety_relevance >= 0.25
        ORDER BY safety_relevance DESC,women_signal_score DESC,row_count DESC LIMIT 80
    """)
    summary = rows("""SELECT COUNT(*) AS total_successful_datasets, COUNT(*) FILTER (WHERE focus='women_safety') AS women_safety_datasets FROM analytics.dataset_profile""")[0]
    return {"areas": area, "time_windows": time, "datasets": profiles, **summary}


def refresh():
    return refresh_analytics()
