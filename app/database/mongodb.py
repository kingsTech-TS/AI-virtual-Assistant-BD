import time
from typing import Any, Dict, Optional

from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorCollection,
    AsyncIOMotorDatabase,
)
from pymongo.errors import ConnectionFailure, InvalidURI

from app.core.config import settings
from app.core.logging import logger
from app.database.collections import ALL_COLLECTIONS, get_collection


class MongoDBManager:
    _instance: Optional["MongoDBManager"] = None
    _initialized: bool = False

    def __new__(cls, *args: Any, **kwargs: Any) -> "MongoDBManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._client: Optional[AsyncIOMotorClient] = None
        self._db: Optional[AsyncIOMotorDatabase] = None
        self._initialized = True

    @property
    def client(self) -> AsyncIOMotorClient:
        if self._client is None:
            raise RuntimeError("MongoDB client is not connected. Call connect() first.")
        return self._client

    @property
    def db(self) -> AsyncIOMotorDatabase:
        if self._db is None:
            raise RuntimeError("MongoDB database is not connected. Call connect() first.")
        return self._db

    async def connect(self) -> None:
        if self._client is not None:
            return

        if not settings.MONGODB_URI:
            raise ValueError("MONGODB_URI environment variable is not set.")

        try:
            self._client = AsyncIOMotorClient(
                settings.MONGODB_URI,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                retryWrites=True,
                w="majority",
            )
            await self._client.admin.command("ping")
            self._db = self._client[settings.MONGODB_DATABASE]
            logger.info(
                "MongoDB connected",
                extra={
                    "database": settings.MONGODB_DATABASE,
                    "collections": ALL_COLLECTIONS,
                },
            )
        except (InvalidURI, ConnectionFailure) as exc:
            self._client = None
            self._db = None
            logger.error(f"MongoDB connection failed: {exc}")
            raise

    async def disconnect(self) -> None:
        if self._client is not None:
            self._client.close()
            logger.info("MongoDB disconnected")
            self._client = None
            self._db = None

    def get_collection(self, name: str) -> AsyncIOMotorCollection:
        return get_collection(self.db, name)

    def get_database(self) -> AsyncIOMotorDatabase:
        return self.db

    async def health_check(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "status": "disconnected",
            "ping_ms": None,
        }

        if self._client is None:
            return result

        try:
            start = time.perf_counter()
            await self._client.admin.command("ping")
            ping_ms = int((time.perf_counter() - start) * 1000)
            result["status"] = "connected"
            result["ping_ms"] = ping_ms
        except Exception as exc:
            logger.error(f"MongoDB health check failed: {exc}")
            result["status"] = "disconnected"

        return result


db_manager = MongoDBManager()
