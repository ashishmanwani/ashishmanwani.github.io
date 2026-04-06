#!/usr/bin/env python3
"""
CLI script to create an admin user.
Usage: python scripts/add_user.py --email admin@example.com --password secret123
"""

import argparse
import asyncio
import sys

sys.path.insert(0, "/app")

from sqlalchemy import select

from api.db.session import AsyncSessionLocal
from api.models.user import User
from api.services.auth_service import hash_password


async def create_user(email: str, password: str):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        existing = result.scalar_one_or_none()
        if existing:
            print(f"User with email {email} already exists (id={existing.id})")
            return

        user = User(email=email, password_hash=hash_password(password))
        db.add(user)
        await db.commit()
        await db.refresh(user)
        print(f"Created user: {user.email} (id={user.id})")


def main():
    parser = argparse.ArgumentParser(description="Create a Price Tracker user")
    parser.add_argument("--email", required=True, help="User email address")
    parser.add_argument("--password", required=True, help="User password")
    args = parser.parse_args()

    asyncio.run(create_user(args.email, args.password))


if __name__ == "__main__":
    main()
