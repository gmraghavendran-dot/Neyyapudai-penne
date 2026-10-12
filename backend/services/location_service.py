from backend.database.repository import rows
from backend.database.connection import engine
from sqlalchemy import text

# Operational area directory for the Chennai demonstration environment.
# Coordinates are stable map centroids, not live device positions.
CHENNAI_AREAS = [
    ("Adyar", 13.0067, 80.2572, "South Chennai"),
    ("Anna Nagar", 13.0850, 80.2101, "Central Chennai"),
    ("Ambattur", 13.1143, 80.1548, "West Chennai"),
    ("Avadi", 13.1067, 80.0970, "West Chennai"),
    ("Besant Nagar", 12.9980, 80.2660, "South Chennai"),
    ("Egmore", 13.0732, 80.2609, "Central Chennai"),
    ("Guindy", 13.0067, 80.2206, "South Chennai"),
    ("Kilpauk", 13.0789, 80.2425, "Central Chennai"),
    ("Kodambakkam", 13.0524, 80.2213, "Central Chennai"),
    ("Mylapore", 13.0339, 80.2676, "Central Chennai"),
    ("Nungambakkam", 13.0569, 80.2425, "Central Chennai"),
    ("Perambur", 13.1147, 80.2326, "North Chennai"),
    ("Porur", 13.0359, 80.1565, "West Chennai"),
    ("Royapettah", 13.0523, 80.2642, "Central Chennai"),
    ("Saidapet", 13.0213, 80.2231, "South Chennai"),
    ("Sholinganallur", 12.9010, 80.2279, "South Chennai"),
    ("T Nagar", 13.0418, 80.2341, "Central Chennai"),
    ("Tambaram", 12.9249, 80.1000, "South Chennai"),
    ("Velachery", 12.9815, 80.2180, "South Chennai"),
    ("OMR", 12.9008, 80.2271, "South Chennai"),
]


def seed_area_directory() -> None:
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS core.area_directory (
                area_id BIGSERIAL PRIMARY KEY,
                area_name TEXT UNIQUE NOT NULL,
                latitude DOUBLE PRECISION NOT NULL,
                longitude DOUBLE PRECISION NOT NULL,
                zone TEXT NOT NULL DEFAULT 'Chennai',
                active BOOLEAN NOT NULL DEFAULT TRUE
            )
        """))
        for name, lat, lng, zone in CHENNAI_AREAS:
            conn.execute(text("""
                INSERT INTO core.area_directory(area_name,latitude,longitude,zone)
                VALUES (:name,:lat,:lng,:zone)
                ON CONFLICT (area_name) DO UPDATE SET
                    latitude=EXCLUDED.latitude,
                    longitude=EXCLUDED.longitude,
                    zone=EXCLUDED.zone,
                    active=TRUE
            """), {"name": name, "lat": lat, "lng": lng, "zone": zone})


def list_areas() -> list[dict]:
    seed_area_directory()
    return rows("""
        SELECT a.area_id,a.area_name,a.latitude,a.longitude,a.zone,
               COALESCE(r.risk_score, NULL) AS historical_risk,
               COALESCE(r.trend, 'contextual') AS risk_trend
        FROM core.area_directory a
        LEFT JOIN analytics.area_risk r
          ON LOWER(r.area)=LOWER(a.area_name)
        WHERE a.active=TRUE
        ORDER BY a.area_name
    """)


def resolve_area(area_name: str) -> dict:
    if not area_name or not str(area_name).strip():
        raise ValueError("Area name is required")
    area = one_area(str(area_name).strip())
    if not area:
        raise ValueError(f"Unknown area '{area_name}'. Choose an area from /api/locations/areas.")
    return area


def one_area(area_name: str) -> dict | None:
    seed_area_directory()
    return next(iter(rows("""
        SELECT a.area_id,a.area_name,a.latitude,a.longitude,a.zone,
               COALESCE(r.risk_score, NULL) AS historical_risk,
               COALESCE(r.trend, 'contextual') AS risk_trend
        FROM core.area_directory a
        LEFT JOIN analytics.area_risk r ON LOWER(r.area)=LOWER(a.area_name)
        WHERE LOWER(a.area_name)=LOWER(:name) AND a.active=TRUE
        LIMIT 1
    """, {"name": area_name})), None)
