"""Raybotix Digital — FastAPI backend entry point."""
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pathlib import Path
import logging
import os

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from db import db, close_client  # noqa: E402
from routes_auth import router as auth_router  # noqa: E402
from routes_users import router as users_router  # noqa: E402
from routes_projects import router as projects_router  # noqa: E402
from routes_tasks import router as tasks_router  # noqa: E402
from routes_messages import router as messages_router  # noqa: E402
from routes_notifications import router as notifications_router, activity_router  # noqa: E402
from routes_analytics import router as analytics_router  # noqa: E402
from routes_settings import router as settings_router  # noqa: E402
from seed import seed  # noqa: E402

app = FastAPI(title="Raybotix Digital API")

api_router = APIRouter(prefix="/api")


@api_router.get("/")
async def root():
    return {"app": "Raybotix Digital", "status": "ok"}


api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(projects_router)
api_router.include_router(tasks_router)
api_router.include_router(messages_router)
api_router.include_router(notifications_router)
api_router.include_router(activity_router)
api_router.include_router(analytics_router)
api_router.include_router(settings_router)

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("raybotix")


@app.on_event("startup")
async def on_startup():
    try:
        await seed()
        logger.info("Seed complete")
    except Exception as e:
        logger.exception("Seed failed: %s", e)


@app.on_event("shutdown")
async def on_shutdown():
    close_client()
