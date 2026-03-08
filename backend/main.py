from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from backend.database import init_db
from backend.api import status, candidates, employers, matching

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup database on startup
    await init_db()
    yield
    # Teardown logic if needed

app = FastAPI(title="Matchflix API", version="1.0.0", lifespan=lifespan)

# Setup CORS (allow all for local dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(status.router, prefix="/api")
app.include_router(candidates.router, prefix="/api")
app.include_router(employers.router, prefix="/api")
app.include_router(matching.router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Matchflix API is running"}
