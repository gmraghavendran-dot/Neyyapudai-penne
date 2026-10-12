import math
import re
from collections import defaultdict
from sqlalchemy import text
from backend.database.connection import engine
from backend.database.repository import quote_ident, rows

# High-precision women-safety vocabulary. Demographic fields such as female_total
# are intentionally excluded from incident classification.
WOMEN_KEYWORDS = {
    "crime_against_women": 1.0, "crimes_against_women": 1.0, "women_crime": 1.0,
    "women": 0.95, "rape": 1.0, "rape_cases": 1.0, "sexual": 1.0,
    "molest": 0.95, "molestation": 0.95, "stalking": 0.95, "harass": 0.9,
    "harassment": 0.9, "kidnap": 0.9, "abduction": 0.85, "dowry": 0.9,
    "cruelty_by_husband": 0.95, "cruelty_by_husband_or_relatives": 0.95,
    "domestic_violence": 0.95, "acid_attack": 0.95, "trafficking": 0.9,
    "traffick": 0.9, "assault_on_women": 1.0, "cyber_crime_against_women": 1.0,
}
GENERAL_SAFETY_KEYWORDS = {
    "murder": 0.85, "crime": 0.35, "robbery": 0.65, "theft": 0.45,
    "rioting": 0.55, "violence": 0.75, "missing": 0.45, "kidnap": 0.8,
    "accident": 0.35, "emergency": 0.5, "offences": 0.3, "offenses": 0.3,
}
GEO_HINTS = ("district", "city", "town", "state", "state_ut", "location", "place", "area", "region", "zone", "taluk", "tehsil")
SIGNAL_HINTS = ("cases", "case", "incidents", "incident", "victims", "reported", "offences", "offense", "crime", "crimes", "count", "number", "rape", "assault", "sexual", "stalking", "kidnap", "abduction", "molest", "harass", "dowry", "cruelty", "traffick", "violence", "murder", "robbery", "theft")
NEGATIVE_SIGNAL_HINTS = ("population", "male_total", "female_total", "persons_arrested", "arrested_male", "arrested_female", "literacy", "age", "below_18", "above_18", "area_sq", "households", "male", "female", "persons")
INFRA_HINTS = ("streetlight", "street_light", "lighting", "light", "cctv", "camera", "police_station", "help_point", "transport", "bus_stop", "station", "infrastructure")
AGGREGATE_VALUES = {"total", "total all india", "total india", "all india", "india", "total districts", "total state(s)", "total states", "grand total", "nan", "none", "null", "n/a", "na", "0"}


def _keyword_score(value: str, mapping: dict[str, float]) -> float:
    value = (value or "").lower()
    matches = [weight for key, weight in mapping.items() if key in value]
    return min(1.0, max(matches) if matches else 0.0)


def classify_dataset(table_name: str, file_name: str, columns: list[dict]) -> tuple[float, str, float, float]:
    joined = " ".join([table_name, file_name or "", *(c["column_name"] for c in columns)]).lower()
    women = _keyword_score(joined, WOMEN_KEYWORDS)
    general = _keyword_score(joined, GENERAL_SAFETY_KEYWORDS)
    if women >= 0.55:
        return round(women, 3), "women_safety", round(women, 3), round(general, 3)
    if general >= 0.30:
        return round(max(0.25, general * 0.75), 3), "general_safety", round(women, 3), round(general, 3)
    return 0.0, "other", round(women, 3), round(general, 3)


def get_raw_tables() -> list[str]:
    return [r["table_name"] for r in rows("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema='raw' AND table_type='BASE TABLE' ORDER BY table_name
    """)]


def table_columns(table_name: str) -> list[dict]:
    return rows("""
        SELECT column_name, data_type FROM information_schema.columns
        WHERE table_schema='raw' AND table_name=:table ORDER BY ordinal_position
    """, {"table": table_name})


def _is_numeric_type(data_type: str) -> bool:
    return data_type in {"smallint", "integer", "bigint", "numeric", "decimal", "real", "double precision"}


def choose_geography(table: str, columns: list[dict]) -> str | None:
    candidates = []
    for c in columns:
        name = c["column_name"].lower()
        if not any(h in name for h in GEO_HINTS):
            continue
        qcol, qtable = quote_ident(c["column_name"]), quote_ident(table)
        try:
            sample = rows(f"""
                SELECT CAST({qcol} AS TEXT) AS value FROM raw.{qtable}
                WHERE {qcol} IS NOT NULL LIMIT 150
            """)
        except Exception:
            continue
        values = [str(r["value"]).strip() for r in sample if r["value"] is not None]
        if not values:
            continue
        useful = [v for v in values if v.lower() not in AGGREGATE_VALUES and not v.lower().startswith("total ")]
        non_numeric = sum(not re.fullmatch(r"[-+]?\d+(?:\.\d+)?", v) for v in useful) / max(1, len(useful))
        name_bonus = 0.0
        if name.endswith("_name") or name.endswith("name"): name_bonus += 0.35
        if "district" in name: name_bonus += 0.25
        if "state" in name: name_bonus += 0.15
        if "city" in name or "town" in name: name_bonus += 0.20
        if "code" in name: name_bonus -= 0.25
        score = non_numeric * 0.65 + min(0.35, name_bonus)
        if _is_numeric_type(c["data_type"]): score -= 0.45
        candidates.append((score, c["column_name"], non_numeric))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    best = candidates[0]
    return best[1] if best[0] > 0.10 else None


def choose_signal(table: str, columns: list[dict]) -> tuple[str | None, float, str]:
    candidates = []
    for c in columns:
        if not _is_numeric_type(c["data_type"]):
            continue
        name = c["column_name"].lower()
        if any(k in name for k in NEGATIVE_SIGNAL_HINTS):
            continue
        women = _keyword_score(name, WOMEN_KEYWORDS)
        positive = _keyword_score(name, {k: 1.0 for k in SIGNAL_HINTS})
        if positive == 0 and women == 0:
            continue
        score = positive * 0.55 + women * 0.45
        if "total" in name and women < 0.55:
            score *= 0.8
        candidates.append((score, women, c["column_name"]))
    if not candidates:
        return None, 0.0, "none"
    candidates.sort(reverse=True)
    score, women, column = candidates[0]
    return column, round(score, 3), ("women_safety" if women >= 0.55 else "general_safety")


def profile_datasets() -> list[dict]:
    registry = rows("""
        SELECT file_name, table_name, row_count, column_count, geography, status
        FROM core.dataset_registry WHERE status='SUCCESS' AND table_name IS NOT NULL ORDER BY dataset_id
    """)
    profiles = []
    for item in registry:
        table = item["table_name"]
        cols = table_columns(table)
        if not cols:
            continue
        relevance, focus, women_score, general_score = classify_dataset(table, item.get("file_name") or "", cols)
        signal, signal_strength, signal_focus = choose_signal(table, cols)
        if signal_focus == "women_safety":
            focus = "women_safety"; relevance = max(relevance, signal_strength)
        elif signal_focus == "general_safety" and relevance == 0:
            relevance = max(0.25, signal_strength * 0.75); focus = "general_safety"
        geo = choose_geography(table, cols) if relevance > 0 else None
        infra = any(any(h in c["column_name"].lower() for h in INFRA_HINTS) and _is_numeric_type(c["data_type"]) for c in cols)
        profiles.append({
            "table_name": table, "file_name": item.get("file_name"),
            "row_count": int(item.get("row_count") or 0), "column_count": int(item.get("column_count") or 0),
            "geography_column": geo, "signal_column": signal,
            "safety_relevance": round(min(1.0, relevance), 3), "focus": focus,
            "women_signal_score": women_score, "general_signal_score": general_score,
            "has_infrastructure_signal": infra,
        })
    with engine.begin() as conn:
        for p in profiles:
            conn.execute(text("""
                INSERT INTO analytics.dataset_profile
                (table_name,file_name,row_count,column_count,geography_column,signal_column,safety_relevance,focus,women_signal_score,general_signal_score)
                VALUES (:table_name,:file_name,:row_count,:column_count,:geo,:signal,:rel,:focus,:women,:general)
                ON CONFLICT (table_name) DO UPDATE SET
                  file_name=EXCLUDED.file_name,row_count=EXCLUDED.row_count,column_count=EXCLUDED.column_count,
                  geography_column=EXCLUDED.geography_column,signal_column=EXCLUDED.signal_column,
                  safety_relevance=EXCLUDED.safety_relevance,focus=EXCLUDED.focus,
                  women_signal_score=EXCLUDED.women_signal_score,general_signal_score=EXCLUDED.general_signal_score,
                  profiled_at=CURRENT_TIMESTAMP
            """), {**p, "geo": p["geography_column"], "signal": p["signal_column"], "rel": p["safety_relevance"], "women": p["women_signal_score"], "general": p["general_signal_score"]})
    return profiles


def _area_value(value) -> str | None:
    area = str(value or "").strip()
    low = area.lower()
    if not area or low in AGGREGATE_VALUES or low.startswith("total "):
        return None
    if len(area) > 100:
        return area[:100]
    if re.fullmatch(r"\d+(?:\.0+)?", area):
        # Preserve the fact that this is a code rather than pretending it is a place name.
        return f"Administrative code {area.rstrip('0').rstrip('.') if '.' in area else area}"
    return area


def build_area_risk(max_tables: int = 120) -> list[dict]:
    profiles = rows("""
        SELECT * FROM analytics.dataset_profile
        WHERE safety_relevance >= 0.25 AND geography_column IS NOT NULL AND signal_column IS NOT NULL
        ORDER BY safety_relevance DESC, row_count DESC LIMIT :limit
    """, {"limit": max_tables})
    area_acc = defaultdict(lambda: {"weighted": 0.0, "weight": 0.0, "datasets": set(), "women_weight": 0.0, "infra": 0})
    for p in profiles:
        qtable, qgeo, qsig = quote_ident(p["table_name"]), quote_ident(p["geography_column"]), quote_ident(p["signal_column"])
        try:
            data = rows(f"""
                SELECT TRIM(CAST({qgeo} AS TEXT)) AS area,
                       COALESCE(SUM(CASE WHEN CAST({qsig} AS TEXT) ~ '^-?[0-9]+(?:\\.[0-9]+)?$'
                                  THEN GREATEST(0,CAST({qsig} AS DOUBLE PRECISION)) ELSE 0 END),0) AS signal
                FROM raw.{qtable} WHERE {qgeo} IS NOT NULL GROUP BY 1
            """)
        except Exception:
            continue
        cleaned = [(a, max(0.0, float(r["signal"] or 0))) for r in data if (a := _area_value(r["area"]))]
        if not cleaned:
            continue
        maximum = max(v for _, v in cleaned) or 1.0
        weight = float(p["safety_relevance"]) * (1.25 if p["focus"] == "women_safety" else 0.75)
        for area, raw_signal in cleaned:
            normalized = min(100.0, 100.0 * math.log1p(raw_signal) / math.log1p(maximum)) if maximum > 0 else 0.0
            bucket = area_acc[area]
            bucket["weighted"] += normalized * weight
            bucket["weight"] += weight
            bucket["datasets"].add(p["table_name"])
            if p["focus"] == "women_safety": bucket["women_weight"] += weight
    ranked = []
    for area, v in area_acc.items():
        if v["weight"] <= 0: continue
        score = min(100.0, v["weighted"] / v["weight"])
        women_share = round(min(1.0, v["women_weight"] / v["weight"]), 3)
        ranked.append({
            "area": area, "risk_score": round(score, 1), "incident_signal": round(v["weighted"] / v["weight"], 1),
            "infrastructure_gap": None, "source_datasets": len(v["datasets"]), "women_safety_share": women_share,
            "trend": "critical" if score >= 80 else ("elevated" if score >= 60 else ("watch" if score >= 40 else "stable")),
        })
    ranked.sort(key=lambda x: x["risk_score"], reverse=True)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM analytics.area_risk"))
        for r in ranked[:250]:
            conn.execute(text("""
                INSERT INTO analytics.area_risk(area,risk_score,incident_signal,infrastructure_gap,source_datasets,women_safety_share,trend)
                VALUES (:area,:risk_score,:incident_signal,:infrastructure_gap,:source_datasets,:women_safety_share,:trend)
            """), r)
    return ranked[:100]


def build_time_risk() -> list[dict]:
    observed = {int(r["hour"]): int(r["n"]) for r in rows("""
        SELECT EXTRACT(HOUR FROM reported_at)::INTEGER AS hour, COUNT(*) AS n
        FROM core.incidents GROUP BY 1 ORDER BY 1
    """)}
    peak = max(observed.values(), default=0)
    values = []
    for h in range(24):
        prior = 60 if 18 <= h <= 23 else (50 if h <= 4 else (35 if h <= 7 else 25))
        observed_score = 0 if peak == 0 else 100 * observed.get(h, 0) / peak
        risk = prior if peak == 0 else 0.65 * prior + 0.35 * observed_score
        values.append({"hour": h, "risk_score": round(risk, 1), "label": f"{h:02d}:00", "source": "observed_plus_contextual_prior" if peak else "contextual_prior", "observed_incidents": observed.get(h, 0)})
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM analytics.time_risk"))
        conn.execute(text("""INSERT INTO analytics.time_risk(hour,risk_score,label,source,observed_incidents) VALUES (:hour,:risk_score,:label,:source,:observed_incidents)"""), values)
    return values


def refresh_analytics() -> dict:
    profiles = profile_datasets()
    areas = build_area_risk()
    times = build_time_risk()
    relevant = [p for p in profiles if p["safety_relevance"] >= 0.25]
    women = [p for p in relevant if p["focus"] == "women_safety"]
    general = [p for p in relevant if p["focus"] == "general_safety"]
    return {
        "profiled_datasets": len(relevant), "women_safety_datasets": len(women),
        "general_safety_datasets": len(general), "other_datasets": len(profiles) - len(relevant),
        "total_successful_datasets": len(profiles), "areas": len(areas), "time_windows": len(times),
    }
