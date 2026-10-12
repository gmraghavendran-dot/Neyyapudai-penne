"""
Historical Analytics Pipeline for Neyyapudaipenne.

Executes:
1. Discovery of all 265 raw tables in PostgreSQL
2. Vocabulary-based classification (Women-Safety vs General-Safety)
3. Geography & signal column discovery
4. Dataset profiling into analytics.dataset_profile
5. Logarithmic normalization of area risk across 81 Chennai / NCRB regions
6. 24-Hour temporal risk distribution modeling (prior + observed)
"""
import time
from datetime import datetime, timezone
from typing import Dict, Any

from backend.services.analytics_engine import refresh_analytics


def run() -> Dict[str, Any]:
    start_time = time.time()
    result = refresh_analytics()
    elapsed = round(time.time() - start_time, 2)

    return {
        "status": "completed",
        "pipeline": "historical_analytics_pipeline",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": elapsed,
        "metrics": result,
    }


if __name__ == "__main__":
    import pprint
    pprint.pprint(run())
