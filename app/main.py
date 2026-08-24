from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging, RequestLoggingMiddleware, logger
from app.database.mongodb import db_manager

setup_logging()

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Intelligent Academic Support Chatbot Backend",
    docs_url="/docs",
    redoc_url="/redoc",
)

origins = [settings.FRONTEND_URL]
if settings.DEBUG or settings.APP_ENV.lower() != "production":
    origins.append("http://localhost:3000")
    origins.append("http://localhost:8080")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestLoggingMiddleware)

register_exception_handlers(app)


@app.on_event("startup")
async def startup_event() -> None:
    await db_manager.connect()
    logger.info(
        "App started",
        extra={"app_name": settings.APP_NAME, "env": settings.APP_ENV},
    )


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await db_manager.disconnect()


@app.get("/")
async def root():
    return {
        "success": True,
        "data": {
            "status": "ok",
            "app_name": settings.APP_NAME,
        },
    }


from app.api.router import api_router

app.include_router(api_router, prefix="/api/v1")
