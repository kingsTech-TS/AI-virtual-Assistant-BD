#!/usr/bin/env python3
"""
Seed Admin and Staff accounts.
"""

from __future__ import annotations

import asyncio
import sys

from motor.motor_asyncio import AsyncIOMotorClient

from app.constants.roles import UserRole
from app.core.config import settings
from app.core.security import hash_password
from app.database.collections import DEPARTMENTS, USERS
from app.models.user import new_user_doc

USERS_TO_SEED = [
    {
        "name": "Alex Johnson",
        "email": "admin@demo.ac.ng",
        "password": "Admin@1234",
        "role": UserRole.ADMIN.value,
        "phone": "+2348012345678",
        "faculty": "Physical Sciences",
        "dept_code": None,
    },
    {
        "name": "Sandra Okafor",
        "email": "staff@demo.ac.ng",
        "password": "Staff@1234",
        "role": UserRole.STAFF.value,
        "phone": "+2348087654321",
        "faculty": "Physical Sciences",
        "dept_code": "CSC",
    },
]


async def run():
    print(f"Connecting to MongoDB database '{settings.MONGODB_DATABASE}'...")
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DATABASE]

    try:
        await client.admin.command("ping")
        print("Connected to MongoDB successfully.\n")
    except Exception as exc:
        print(f"Database connection failed: {exc}", file=sys.stderr)
        sys.exit(1)

    dept = await db[DEPARTMENTS].find_one({"code": "CSC"})
    csc_dept_id = dept["_id"] if dept else None

    for u in USERS_TO_SEED:
        email = u["email"].lower()
        dept_id = csc_dept_id if u["dept_code"] else None
        existing = await db[USERS].find_one({"email": email})

        if existing:
            await db[USERS].update_one(
                {"_id": existing["_id"]},
                {
                    "$set": {
                        "name": u["name"],
                        "password_hash": hash_password(u["password"]),
                        "role": u["role"],
                        "is_active": True,
                        "department_id": dept_id,
                        "faculty": u.get("faculty"),
                        "phone": u.get("phone"),
                    }
                },
            )
            print(f"[UPDATED] {u['role'].upper()}: {u['email']}")
        else:
            doc = new_user_doc(
                name=u["name"],
                email=email,
                password_hash=hash_password(u["password"]),
                role=u["role"],
                department_id=dept_id,
                faculty=u.get("faculty"),
                phone=u.get("phone"),
            )
            res = await db[USERS].insert_one(doc)
            print(f"[CREATED] {u['role'].upper()}: {u['email']} (id={res.inserted_id})")

    client.close()
    print("\nCompleted.")


if __name__ == "__main__":
    asyncio.run(run())
