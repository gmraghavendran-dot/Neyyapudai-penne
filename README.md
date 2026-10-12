# NEYYAPUDAIPENNE — Final Working Project

**Real-Time Women Safety Intelligence & Emergency Response Platform**

Core idea: **Prevent → Detect → Respond → Learn**

## What is implemented

### Layer 1 — Safety Risk Intelligence
- Profiles the existing successful NCRB datasets in `core.dataset_registry`.
- Does not hard-code the 265 raw tables.
- Uses high-precision women-safety vocabulary and excludes demographic fields from incident-signal selection.
- Chooses usable geographic columns by inspecting actual values.
- Numeric administrative codes are labelled as codes rather than being presented as human-readable place names.
- Normalizes signals per dataset before aggregation so one large table cannot dominate the score.
- Produces `analytics.dataset_profile`, `analytics.area_risk`, and `analytics.time_risk`.
- Time risk is explicitly marked as contextual when no operational incidents exist; observed incident activity is incorporated once available.

### Layer 2 — Real-Time Incident Detection
- Creates persistent incidents with location, severity, source, timestamp and risk score.
- SOS creates a critical incident and a persistent SOS event.
- SOS attempts automatic responder dispatch.
- Incident status lifecycle: `open → dispatched → responding → resolved`.
- Optional Kafka publication is controlled by `ENABLE_KAFKA`.

### Layer 3 — Emergency Response Intelligence
- Seeded responder fleet for the working demonstration.
- Nearest available responder selection using Haversine distance.
- Responder-type preference for women-safety/SOS events.
- ETA calculation and persisted dispatch event.
- Arrival endpoint records response time.
- Response closure releases the responder.
- Response metrics: dispatches, ETA, response time and ≤10-minute arrivals.

### Layer 4 — Safe Mobility & Prevention
- Compares three contextual route alternatives.
- Uses live/historical incident context at origin and destination.
- Stores route checks for later analytics.
- Clearly labels lighting/transport values as **proxies**; this project does not pretend to have a verified road-routing/GIS feed when one is not connected.

### Layer 5 — Outcome & Learning
- Resolving incidents creates outcome records.
- Effectiveness score is derived from response performance and incident severity.
- Resolution-type analysis.
- Recurring problem locations.
- Response learning metrics.
- Daily incident trend.

## Existing database

Your supplied database already contains the NCRB raw layer. The previously verified state was:

- 265 successful datasets
- 0 failed datasets
- 265 raw tables
- 4,946 columns

The application **does not re-ingest those datasets** during normal startup. It adds operational and analytics tables around them.

## Backend setup — Windows PowerShell

From the project root:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn backend.app:app --reload --port 8000
```

Open:

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/api/health`
- `http://127.0.0.1:8000/docs`

The included `.env` is configured for the supplied PostgreSQL database. If your PostgreSQL password changes, update `.env` rather than source code.

## First-time intelligence refresh

The backend creates missing operational/analytics tables on startup. Then open Swagger and execute:

```text
POST /api/safety/refresh
```

Then:

```text
GET /api/safety/intelligence
```

Expected refresh fields:

- `profiled_datasets`
- `women_safety_datasets`
- `general_safety_datasets`
- `other_datasets`
- `total_successful_datasets`
- `areas`
- `time_windows`

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

The dashboard contains:

- Command Center
- Safety Intelligence
- Live Incidents
- Emergency Response
- Safe Mobility
- Outcome Learning

## End-to-end demo flow

1. Refresh Safety Intelligence.
2. Open Live Incidents.
3. Create a normal incident or use **SOS TEST**.
4. Open Emergency Response.
5. Dispatch the nearest responder.
6. Mark the responder as arrived.
7. Resolve the incident.
8. Open Outcome Learning.
9. Open Safe Mobility and compare routes.

## Kafka & Spark Streaming Architecture

### Kafka: Dual-Mode (Live vs Standby)
Kafka is architected as an optional, decoupled event bus with automatic fallback:
- **Live Mode**: When an Apache Kafka broker is running on `localhost:9092` (KRaft or ZooKeeper), events are published to topic partitions (`neyyapudaipenne.incidents`, `neyyapudaipenne.sos`, `neyyapudaipenne.locations`) and can be consumed by streaming workers.
  - *Verification Status*: Tested and verified with Apache Kafka 3.9.2 (KRaft mode). Both producer publishing and consumer receipt were verified live on `localhost:9092`.
- **Standby Mode**: When the Kafka broker is offline or not installed, the publisher automatically detects socket unavailability within milliseconds and falls back to direct, transactional PostgreSQL sinks (`core.incidents`, `core.sos_events`). No requests hang or time out.

Configuration in `.env`:
```text
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
ENABLE_KAFKA=true
```

To start the local Kafka broker (KRaft mode):
```powershell
$env:KAFKA_HEAP_OPTS="-Xmx1G -Xms1G"
& "C:\kafka\kafka_2.13-3.9.2\bin\windows\kafka-server-start.bat" "C:\kafka\kafka_2.13-3.9.2\config\kraft\server.properties"
```

### Spark: Tested Status
- **Architecture**: Spark is designed as an optional analytical and structured streaming bridge (`pyspark.sql.streaming`), not a mandatory runtime requirement.
- **Implemented Modules**:
  - Structured Streaming Bridges: `data_engineering/spark/streaming/incident_stream.py`, `sos_stream.py`, `location_stream.py`
  - Validation Transformers: `data_engineering/spark/validation/schema_validator.py`, `data_quality.py`
  - Enrichment Transformers: `data_engineering/spark/enrichment/incident_enrichment.py`, `location_enrichment.py`, `time_enrichment.py`
- **Verification Status**:
  - The validation and enrichment logic is unit-tested and actively exercised by the Real-Time Event Pipeline engine (`quality_pct: 100.0%`).
  - PySpark stream queries require a distributed Spark session (`spark-submit` or PySpark with Kafka connectors) and are loaded when scaling beyond single-node throughput. The web application and command center function natively without Spark.

## Important honesty boundary

This is a working intelligence prototype. Risk scores are contextual indicators, not guarantees that a location or person is safe/unsafe. The Safe Mobility module intentionally does not claim turn-by-turn road routing or verified street-light/transit infrastructure without an actual GIS/infrastructure feed.

## Demo UX updates
- Incident reporting and SOS use **area names** instead of manual latitude/longitude entry.
- Safe Mobility uses **origin and destination areas** and resolves their operational coordinates internally.
- Command Center highlights Active SOS, high-risk areas, responder readiness, response time and data coverage.
- Live safety map shows operational area context and live incident markers.
- SOS console exposes the real processing flow: detected → location resolved → risk enriched → dispatch/ETA.
- Outcome Learning shows resolution effectiveness, recurring areas and daily incident trend.
- Data Engineering page exposes the NCRB → Kafka → Spark → validation → PostgreSQL → FastAPI → React architecture.

## Final demo flow
1. Start FastAPI: `uvicorn backend.app:app --reload --port 8000`
2. Start React from `frontend`: `npm install` then `npm run dev`
3. Open the Command Center.
4. Use Live Incidents → select an area name → Create incident or TEST SOS.
5. Open Emergency Response → dispatch → mark arrived → Resolve & learn.
6. Open Safe Mobility → select origin and destination areas → compare routes.
7. Open Outcome Learning to inspect effectiveness and recent-vs-previous incident windows.
8. Open Data Engineering to explain the complete data pipeline during the viva/demo.

### Area-name design
The operational UI intentionally avoids manual latitude/longitude entry. A seeded Chennai area directory maps human-readable area names to stable map centroids. Coordinates remain an internal implementation detail used for distance, ETA and map rendering.
