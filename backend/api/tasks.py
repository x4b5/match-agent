"""Task status tracking API — in-memory taakstatus voor achtergrondtaken."""
import uuid
import time
from fastapi import APIRouter

router = APIRouter(prefix="/tasks", tags=["Tasks"])

# In-memory task store
_tasks: dict[str, dict] = {}

# Automatische cleanup na 1 uur
_MAX_AGE_SECONDS = 3600


def _cleanup():
    """Verwijder tasks ouder dan 1 uur."""
    now = time.time()
    te_verwijderen = [
        tid for tid, t in _tasks.items()
        if now - t["started_at"] > _MAX_AGE_SECONDS
    ]
    for tid in te_verwijderen:
        del _tasks[tid]


def maak_task(task_type: str, naam: str) -> str:
    """Maak een nieuwe task aan en geef het task_id terug."""
    _cleanup()
    task_id = str(uuid.uuid4())[:8]
    _tasks[task_id] = {
        "id": task_id,
        "status": "pending",
        "type": task_type,
        "naam": naam,
        "progress": None,
        "error": None,
        "started_at": time.time(),
    }
    return task_id


def update_task(task_id: str, **kwargs):
    """Update velden van een bestaande task."""
    if task_id in _tasks:
        _tasks[task_id].update(kwargs)


def haal_task(task_id: str) -> dict | None:
    """Haal een task op."""
    return _tasks.get(task_id)


@router.get("/")
async def list_tasks():
    _cleanup()
    return list(_tasks.values())


@router.get("/{task_id}")
async def get_task(task_id: str):
    task = haal_task(task_id)
    if not task:
        return {"error": "Task niet gevonden"}
    return task
