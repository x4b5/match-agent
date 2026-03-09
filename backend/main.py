import logging
import time
from collections import defaultdict

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from backend.config import LOG_LEVEL
from backend.database import init_db
from backend.services.llm_instance import init_provider
from backend.api import status, candidates, employers, matching, gdpr, tasks

# ── Structured Logging ──
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("matchflix")

# ── Rate Limiter (in-memory) ──
RATE_LIMIT_MAX = 60  # max requests per minuut
RATE_LIMIT_WINDOW = 60  # seconden
_rate_store: dict[str, list[float]] = defaultdict(list)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 MATCHFLIX backend opgestart")
    init_provider()
    await init_db()
    yield
    logger.info("🛑 MATCHFLIX backend afgesloten")

app = FastAPI(title="Matchflix API", version="1.0.0", lifespan=lifespan)

# Setup CORS (expliciete whitelist voor lokale dev)
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:4173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:4173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Rate Limiting Middleware ──
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()

    # Schoon oude entries op
    _rate_store[client_ip] = [
        t for t in _rate_store[client_ip]
        if now - t < RATE_LIMIT_WINDOW
    ]

    if len(_rate_store[client_ip]) >= RATE_LIMIT_MAX:
        logger.warning(f"Rate limit bereikt voor {client_ip}")
        return Response(
            content='{"detail":"Te veel verzoeken. Probeer het later opnieuw."}',
            status_code=429,
            media_type="application/json"
        )

    _rate_store[client_ip].append(now)
    response = await call_next(request)
    return response


# ── Request Logging Middleware ──
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = round((time.time() - start) * 1000)
    if not request.url.path.startswith("/api/tasks"):  # Skip noisy polling
        logger.info(f"{request.method} {request.url.path} → {response.status_code} ({duration}ms)")
    return response

# Include routers
app.include_router(status.router, prefix="/api")
app.include_router(candidates.router, prefix="/api")
app.include_router(employers.router, prefix="/api")
app.include_router(matching.router, prefix="/api")
app.include_router(gdpr.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Matchflix API is running"}
