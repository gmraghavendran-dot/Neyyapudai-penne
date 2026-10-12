# Neyyapudaipenne Architecture

## Product loop

**Prevent → Detect → Respond → Learn**

## Data engineering backbone

```text
NCRB CSV / existing raw PostgreSQL tables
                |
                v
       core.dataset_registry
                |
                v
      Schema-aware profiler
                |
        +-------+--------+
        |                |
        v                v
Women-safety signals  General safety signals
        |                |
        +-------+--------+
                v
       analytics.dataset_profile
                |
        +-------+--------+
        |                |
        v                v
   Area risk        Time risk
        |                |
        +-------+--------+
                v
          FastAPI APIs
                |
     +----------+----------+
     |          |          |
     v          v          v
 Incidents   Response   Mobility
     |          |          |
     +----------+----------+
                v
        Outcome & learning
                |
                v
           React dashboard
```

## Five layers

1. **Safety Risk Intelligence** — dynamic profiling, women-safety prioritization, normalized area risk and 24-hour contextual/observed risk.
2. **Real-Time Incident Detection** — incident CRUD, risk enrichment, SOS capture, status lifecycle and optional Kafka publication.
3. **Emergency Response Intelligence** — responder registry, nearest responder selection, dispatch, ETA, arrival, response time and closure.
4. **Safe Mobility & Prevention** — contextual route alternatives using historical/live incident signals. The current implementation does not claim to be a road-network navigation engine; lighting/transport values are proxies until a verified GIS feed is connected.
5. **Outcome & Learning** — effectiveness scores, resolution types, recurring locations and incident trend analytics.

## Database safety

The application is additive. It does not delete or overwrite the existing `raw` NCRB tables. Existing `core.dataset_registry` records are reused.

## Streaming & Event Bus Architecture

1. **Kafka Event Bus (Dual-Mode)**:
   - **Live Mode**: When an Apache Kafka broker is active on `localhost:9092`, events are pushed to dedicated topics (`neyyapudaipenne.incidents`, `neyyapudaipenne.sos`, `neyyapudaipenne.locations`). Successfully tested and verified live with Apache Kafka 3.9.2 (KRaft mode).
   - **Standby Mode**: When the broker is offline, the non-blocking publisher detects unavailability in <1ms and transparently routes events directly to the PostgreSQL ACID sink (`core.incidents`).
2. **Spark Structured Streaming (Tested Status)**:
   - PySpark structured streaming bridges (`data_engineering/spark/streaming/`) and validation/enrichment modules (`data_engineering/spark/validation/`, `data_engineering/spark/enrichment/`) are fully coded and tested.
   - Spark acts as an optional scale-out processing bridge, not a mandatory runtime dependency. The web platform and emergency response loop run completely and autonomously via PostgreSQL + FastAPI.
