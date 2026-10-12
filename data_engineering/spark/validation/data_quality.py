def check_quality(records) -> dict:
    total = len(records)
    valid = sum(1 for r in records if r.get("location_valid", True))
    return {"total": total, "valid": valid, "invalid": total-valid, "quality_pct": round(100*valid/total,1) if total else 100.0}
