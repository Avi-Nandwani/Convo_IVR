# app/main.py
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings

settings = get_settings()

# Basic logger setup (can be extended)
logging.basicConfig(level=settings.LOG_LEVEL.upper())
logger = logging.getLogger("conversational-ivr-poc")

app = FastAPI(
    title="Conversational IVR POC",
    version="0.1.0",
    description="POC: inbound call -> ASR -> LLM -> TTS -> (optional) WebRTC escalate",
)

# CORS - relaxed for dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.ENV == "dev" else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Try to include routers if they exist. If they don't, application still starts.
try:
    # expected to exist later: app/api/webhooks.py exposes `router`
    from app.api.webhooks import router as webhooks_router
    app.include_router(webhooks_router, prefix="/webhook", tags=["webhook"])
    logger.info("Included /webhook router")
except Exception as e:
    logger.debug("webhook router not found or failed to import: %s", e)

try:
    from app.api.flows import router as flows_router
    app.include_router(flows_router, prefix="/api/flows", tags=["flows"])
    logger.info("Included /api/flows router")
except Exception as e:
    logger.debug("flows router not found or failed to import: %s", e)

try:
    from app.api.sessions import router as sessions_router
    app.include_router(sessions_router, prefix="/api/sessions", tags=["sessions"])
    logger.info("Included /api/sessions router")
except Exception as e:
    logger.debug("sessions router not found or failed to import: %s", e)

try:
    from app.api.transcripts import router as transcripts_router
    app.include_router(transcripts_router, prefix="/api/transcripts", tags=["transcripts"])
    logger.info("Included /api/transcripts router")
except Exception as e:
    logger.debug("transcripts router not found or failed to import: %s", e)


# Serve demo recordings / generated media in development from the `demo/recordings` folder
media_path = Path(__file__).resolve().parents[1].joinpath("demo", "recordings")
if media_path.exists():
    app.mount("/media", StaticFiles(directory=str(media_path)), name="media")
    logger.info("Mounted /media -> %s", media_path)
else:
    logger.debug("Media folder not present (%s); /media not mounted", media_path)

# Simple health endpoints
@app.get("/", tags=["health"])
async def root():
    return JSONResponse({"status": "ok", "service": "conversational-ivr-poc", "env": settings.ENV})


@app.get("/health", tags=["health"])
async def health():
    return JSONResponse({"status": "ok", "db": bool(settings.DB_URL), "redis": bool(settings.REDIS_URL)})


# Startup / shutdown events (safe no-op if modules not implemented yet)
@app.on_event("startup")
async def on_startup():
    logger.info("Starting Conversational IVR POC app (env=%s)", settings.ENV)
    # Example: connect to DB / Redis if you implement db.connect(), redis.connect()
    try:
        from app.db.db import connect_db  # optional file you may add later

        await connect_db(settings.DB_URL)
        app.state.db_connected = True
        logger.info("Database connected")
    except Exception as exc:
        app.state.db_connected = False
        logger.debug("No DB connect function / failed to connect (okay for dev): %s", exc)

    try:
        from app.state.session_store import connect_redis  # optional

        await connect_redis(settings.REDIS_URL)
        app.state.redis_connected = True
        logger.info("Redis connected")
    except Exception as exc:
        app.state.redis_connected = False
        logger.debug("No Redis connect function / failed to connect (okay for dev): %s", exc)


@app.on_event("shutdown")
async def on_shutdown():
    logger.info("Shutting down Conversational IVR POC app")
    # Example: graceful shutdown for DB/Redis
    try:
        from app.db.db import disconnect_db

        await disconnect_db()
    except Exception:
        pass

    try:
        from app.state.session_store import disconnect_redis

        await disconnect_redis()
    except Exception:
        pass


# If run directly: start uvicorn programmatically (handy for `python -m app.main`)
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.ENV == "dev",
        log_level=settings.LOG_LEVEL,
    )
