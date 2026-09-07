from fastapi import APIRouter, Query, HTTPException, status
import uuid

router = APIRouter(prefix="/api/v1/admin/dead-jobs", tags=["dlq"])

@router.get("", status_code=status.HTTP_200_OK)
async def list_dead_jobs():
    return []

@router.post("/retry", status_code=status.HTTP_200_OK)
async def retry_dead_job(id: str = Query(...)):
    try:
        dead_uuid = uuid.UUID(id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid dead job id")
    
    # Mock behavior for retry
    return {
        "message": "Failed job re-queued successfully for verification",
        "new_job_id": str(uuid.uuid4()),
        "requeued_at": "timestamp"
    }
