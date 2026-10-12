from fastapi import APIRouter, Query
from backend.database.repository import rows

router = APIRouter(prefix="/api/datasets", tags=["datasets"])

@router.get("")
def datasets(limit: int = Query(500, ge=1, le=1000)):
    return rows("""
        SELECT dataset_id,file_name,table_name,row_count,column_count,year,geography,status,loaded_at
        FROM core.dataset_registry ORDER BY dataset_id DESC LIMIT :limit
    """, {"limit": limit})

@router.get("/summary")
def dataset_summary():
    return rows("""
        SELECT COUNT(*) AS total_datasets,
               COUNT(*) FILTER (WHERE status='SUCCESS') AS successful_datasets,
               COUNT(*) FILTER (WHERE status='FAILED') AS failed_datasets,
               COUNT(*) FILTER (WHERE status='SUCCESS') AS raw_tables,
               COALESCE(SUM(column_count) FILTER (WHERE status='SUCCESS'),0) AS total_columns
        FROM core.dataset_registry
    """)[0]
