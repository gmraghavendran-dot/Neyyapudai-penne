def enrich_incident(record: dict) -> dict:
    text = f"{record.get('incident_type','')} {record.get('description','')}".lower()
    record["is_emergency"] = any(k in text for k in ("sos","emergency","assault","kidnap","rape"))
    return record
