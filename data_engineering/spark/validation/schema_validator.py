REQUIRED = ("latitude","longitude")


def validate(record: dict) -> bool:
    return all(k in record for k in REQUIRED) and record.get("latitude") is not None and record.get("longitude") is not None
