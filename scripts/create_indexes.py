#!/usr/bin/env python3
"""
Database Index Creation Script.
Safely creates all required indexes across MongoDB collections with background=True.
"""

from __future__ import annotations

import asyncio
import sys
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings
from app.database.indexes import INDEXES


async def create_indexes() -> None:
    print(f"Connecting to MongoDB database '{settings.MONGODB_DATABASE}'...")
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DATABASE]

    try:
        await client.admin.command("ping")
        print("Connected to MongoDB successfully.")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"\nCreating {len(INDEXES)} indexes...")
    created_count = 0
    skipped_count = 0

    for idx_spec in INDEXES:
        col_name = idx_spec["collection"]
        keys = idx_spec["key"]
        unique = idx_spec.get("unique", False)
        kwargs = dict(idx_spec.get("kwargs", {}))
        kwargs["background"] = True
        if unique:
            kwargs["unique"] = True

        idx_name = kwargs.get("name", str(keys))
        collection = db[col_name]

        try:
            res = await collection.create_index(keys, **kwargs)
            print(f"  [OK] {col_name} -> {res}")
            created_count += 1
        except Exception as e:
            print(f"  [WARN] {col_name} index '{idx_name}': {e}")
            skipped_count += 1

    client.close()
    print(f"\nFinished creating indexes. Created/Verified: {created_count}, Skipped/Warnings: {skipped_count}")


def main() -> None:
    asyncio.run(create_indexes())


if __name__ == "__main__":
    main()
