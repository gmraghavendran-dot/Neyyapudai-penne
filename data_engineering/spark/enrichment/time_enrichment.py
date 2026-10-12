from datetime import datetime


def enrich_time(record: dict) -> dict:
    value = record.get("reported_at") or record.get("timestamp")
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z","+00:00"))
            record["hour"] = dt.hour
            record["day_of_week"] = dt.strftime("%A")
            record["is_night"] = dt.hour >= 19 or dt.hour <= 5
        except ValueError:
            pass
    return record
