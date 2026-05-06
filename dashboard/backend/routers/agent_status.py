"""Agent health/status API."""
from fastapi import APIRouter
from ..database import get_db
from ..models.schemas import AgentStatusSchema

router = APIRouter()


@router.get("/all", response_model=list[AgentStatusSchema])
async def agent_status_all():
    db = await get_db()
    try:
        rows = await db.fetchall(
            """
            SELECT agent_name, event_type, details,
                   MAX(created_at) as last_check,
                   COUNT(*) as event_count_today
            FROM agent_logs
            WHERE created_at >= date('now')
            GROUP BY agent_name
            """
        )
        result = []
        for r in rows:
            status = "running"
            error = None
            if error := (r["details"] or "").lower().startswith("error"):
                status = "error"
                error = r["details"]
            result.append(AgentStatusSchema(
                agent_name=r["agent_name"],
                status=status,
                last_check=r["last_check"],
                error=error,
                event_count_today=r["event_count_today"],
            ))
        return result
    finally:
        await db.close()
