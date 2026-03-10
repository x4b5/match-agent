"""Task status tracking API — persistente taakstatus via database."""
import uuid
import time
import asyncio
from fastapi import APIRouter, HTTPException

from backend.database import maak_task_db, update_task_db, haal_task_db, haal_alle_taken_db, cleanup_taken_db

router = APIRouter(prefix="/tasks", tags=["Tasks"])


def maak_task(task_type: str, naam: str) -> str:
    """Maak een nieuwe task aan en geef het task_id terug. Sync wrapper voor async DB call."""
    task_id = str(uuid.uuid4())[:8]
    
    # Probeer in een bestaande event loop te runnen
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(maak_task_db(task_id, task_type, naam))
    except RuntimeError:
        asyncio.run(maak_task_db(task_id, task_type, naam))
    
    return task_id


def update_task(task_id: str, **kwargs):
    """Update velden van een bestaande task. Sync wrapper voor async DB call."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(update_task_db(task_id, **kwargs))
    except RuntimeError:
        asyncio.run(update_task_db(task_id, **kwargs))


@router.get("/")
async def list_tasks():
    await cleanup_taken_db()
    return await haal_alle_taken_db()


@router.get("/{task_id}")
async def get_task(task_id: str):
    task = await haal_task_db(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task niet gevonden")
    return task
