from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings
from backend.database.connection import ping_database
from backend.database.models import initialize_operational_schema, seed_responders
from backend.database.repository import overview, one
from backend.api.datasets import router as datasets_router
from backend.api.incidents import router as incidents_router
from backend.api.safety import router as safety_router
from backend.api.response import router as response_router
from backend.api.mobility import router as mobility_router
from backend.api.outcomes import router as outcomes_router
from backend.api.sos import router as sos_router
from backend.api.stream import router as stream_router
from backend.api.locations import router as locations_router
from backend.api.data_engineering import router as data_engineering_router
from backend.api.erss import router as erss_router
from backend.services.location_service import seed_area_directory

app = FastAPI(
    title="Neyyapudaipenne",
    version="1.0.0",
    description="Real-Time Women Safety Intelligence & Emergency Response Platform",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[x.strip() for x in settings.cors_origins.split(",") if x.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (
    datasets_router, incidents_router, safety_router,
    response_router, mobility_router, outcomes_router, sos_router, stream_router, locations_router, data_engineering_router, erss_router
):
    app.include_router(router)


@app.on_event("startup")
def startup():
    initialize_operational_schema()
    seed_responders()
    seed_area_directory()


@app.get("/")
def root():
    return {"name":"NEYYAPUDAIPENNE","status":"running","message":"Prevent → Detect → Respond → Learn"}


@app.get("/api/health")
def health():
    database_ok = ping_database()
    tables_ok = False
    if database_ok:
        try:
            tables_ok = bool(one("SELECT to_regclass('core.incidents') AS incidents_table"))
        except Exception:
            tables_ok = False
    return {"api":"ok","database":"ok" if database_ok else "unavailable","operational_schema":"ok" if tables_ok else "not_initialized"}


@app.get("/api/overview")
def overview_endpoint():
    return overview()
