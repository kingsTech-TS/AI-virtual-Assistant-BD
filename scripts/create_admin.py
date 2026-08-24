#!/usr/bin/env python3
"""
Admin Creation Utility Script.
Creates a super_admin user securely using environment variables or interactive CLI prompt.
"""

from __future__ import annotations

import asyncio
import getpass
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient

from app.constants.roles import UserRole
from app.core.config import settings
from app.core.security import hash_password
from app.database.collections import USERS
from app.models.user import new_user_doc
from app.services.audit_service import audit_action


async def create_admin() -> None:
    print(f"Connecting to MongoDB database '{settings.MONGODB_DATABASE}'...")
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DATABASE]

    try:
        await client.admin.command("ping")
        print("Connected to MongoDB successfully.")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}", file=sys.stderr)
        sys.exit(1)

    admin_email = os.getenv("ADMIN_EMAIL", "").strip()
    admin_password = os.getenv("ADMIN_PASSWORD", "").strip()
    admin_name = os.getenv("ADMIN_NAME", "System Administrator").strip()

    if not admin_email:
        print("\n--- Interactive Super Admin Setup ---")
        try:
            admin_email = input("Enter admin email address: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.")
            sys.exit(0)

    if not admin_email or "@" not in admin_email:
        print("Error: Valid email address is required.", file=sys.stderr)
        sys.exit(1)

    existing = await db[USERS].find_one({"email": admin_email.lower()})
    if existing:
        if existing.get("role") == UserRole.SUPER_ADMIN.value:
            print(f"\nUser '{admin_email}' already exists with role 'super_admin'. No changes made.")
            client.close()
            return
        else:
            print(f"\nUser '{admin_email}' exists with role '{existing.get('role')}'.")
            confirm = input("Upgrade this user to 'super_admin'? (y/N): ").strip().lower()
            if confirm == "y":
                await db[USERS].update_one(
                    {"_id": existing["_id"]},
                    {"$set": {"role": UserRole.SUPER_ADMIN.value, "is_active": True}}
                )
                print(f"Successfully upgraded '{admin_email}' to super_admin.")
            client.close()
            return

    if not admin_password:
        try:
            admin_password = getpass.getpass("Enter admin password (min 8 characters): ").strip()
            confirm_pwd = getpass.getpass("Confirm admin password: ").strip()
            if admin_password != confirm_pwd:
                print("Error: Passwords do not match.", file=sys.stderr)
                sys.exit(1)
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.")
            sys.exit(0)

    if len(admin_password) < 8:
        print("Error: Password must be at least 8 characters long.", file=sys.stderr)
        sys.exit(1)

    doc = new_user_doc(
        name=admin_name,
        email=admin_email,
        password_hash=hash_password(admin_password),
        role=UserRole.SUPER_ADMIN.value,
    )
    res = await db[USERS].insert_one(doc)
    doc["_id"] = res.inserted_id

    await audit_action(
        db,
        user_id=res.inserted_id,
        action="user_created",
        resource_type="user",
        resource_id=res.inserted_id,
        metadata={"role": UserRole.SUPER_ADMIN.value, "email": admin_email.lower(), "via": "create_admin_script"},
    )

    client.close()
    print(f"\n[SUCCESS] Super Admin account '{admin_email}' created successfully.")
    print("You can now log in at /api/v1/auth/login with these credentials.")


def main() -> None:
    asyncio.run(create_admin())


if __name__ == "__main__":
    main()
