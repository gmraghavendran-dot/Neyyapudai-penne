def enrich_location(record: dict) -> dict:
    lat, lng = record.get("latitude"), record.get("longitude")
    if lat is not None and lng is not None:
        record["location_valid"] = -90 <= float(lat) <= 90 and -180 <= float(lng) <= 180
    else:
        record["location_valid"] = False
    return record
