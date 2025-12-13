from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.contact import AlertContact
from app.schemas.contact import AlertContactCreate, AlertContactUpdate

class CRUDContact:
    async def get(self, db: AsyncSession, id: UUID) -> Optional[AlertContact]:
        """Get contact by ID"""
        result = await db.execute(select(AlertContact).where(AlertContact.id == id))
        return result.scalar_one_or_none()

    async def get_multi_by_feed(
        self, db: AsyncSession, *, feed_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[AlertContact]:
        """Get all contacts for a feed"""
        result = await db.execute(
            select(AlertContact)
            .where(AlertContact.feed_id == feed_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def create_with_feed(
        self, db: AsyncSession, *, obj_in: AlertContactCreate, feed_id: UUID
    ) -> AlertContact:
        """Create new contact for feed"""
        db_obj = AlertContact(
            feed_id=feed_id,
            name=obj_in.name,
            phone=obj_in.phone,
            email=obj_in.email,
            is_active=obj_in.is_active
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self, db: AsyncSession, *, db_obj: AlertContact, obj_in: AlertContactUpdate | dict
    ) -> AlertContact:
        """Update contact"""
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def remove(self, db: AsyncSession, *, id: UUID) -> AlertContact:
        """Delete contact"""
        obj = await self.get(db, id=id)
        await db.delete(obj)
        await db.commit()
        return obj

contact = CRUDContact()
