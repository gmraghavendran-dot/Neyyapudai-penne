VALID_SEVERITIES = {"low", "medium", "high", "critical"}
VALID_STATUSES = {"open", "dispatched", "responding", "resolved", "cancelled"}

def valid_coordinates(latitude, longitude):
    return -90 <= float(latitude) <= 90 and -180 <= float(longitude) <= 180

def validate_severity(value):
    value = str(value).lower()
    if value not in VALID_SEVERITIES:
        raise ValueError(f"Invalid severity: {value}")
    return value
