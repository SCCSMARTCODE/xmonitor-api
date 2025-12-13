
import asyncio
import sys
import os

# Add the current directory to sys.path to make imports work
sys.path.append(os.getcwd())

from app.core.database import SessionLocal
from app.crud.user import user as user_crud
from app.models.user import User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

async def list_users():
    async with SessionLocal() as db:
        result = await db.execute(select(User))
        users = result.scalars().all()
        print(f"Found {len(users)} users:")
        for u in users:
            print(f" - {u.email} (Active: {u.is_active})")

if __name__ == "__main__":
    asyncio.run(list_users())
