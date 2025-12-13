from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.feed import CameraFeed, FeedSettings
from app.schemas.feed import FeedCreate, FeedUpdate, FeedSettingsUpdate

class CRUDFeed:
    async def get(self, db: AsyncSession, id: UUID) -> Optional[CameraFeed]:
        """Get feed by ID with settings loaded"""
        result = await db.execute(
            select(CameraFeed)
            .options(
                selectinload(CameraFeed.settings),
                selectinload(CameraFeed.contacts)
            )
            .where(CameraFeed.id == id)
        )
        return result.scalar_one_or_none()

    async def get_multi_by_owner(
        self, db: AsyncSession, *, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[CameraFeed]:
        """Get all feeds for a user"""
        result = await db.execute(
            select(CameraFeed)
            .options(
                selectinload(CameraFeed.settings),
                selectinload(CameraFeed.contacts)
            )
            .where(CameraFeed.user_id == user_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_all_active(
        self, db: AsyncSession
    ) -> List[CameraFeed]:
        """Get all active feeds for the agent"""
        result = await db.execute(
            select(CameraFeed)
            .options(selectinload(CameraFeed.settings))
            .where(CameraFeed.status == 'active')
        )
        return result.scalars().all()

    async def create_with_owner(
        self, db: AsyncSession, *, obj_in: FeedCreate, user_id: UUID
    ) -> CameraFeed:
        """Create new feed for user"""
        # Create feed
        db_obj = CameraFeed(
            user_id=user_id,
            name=obj_in.name,
            feed_url=obj_in.feed_url,
            location=obj_in.location,
            feed_type=obj_in.feed_type,
            custom_instruction=obj_in.custom_instruction,
            status=obj_in.status.value
        )
        db.add(db_obj)
        await db.flush()  # Get ID

        # Create settings
        settings_in = obj_in.settings
        if settings_in:
            settings_obj = FeedSettings(
                feed_id=db_obj.id,
                push_enabled=settings_in.push_enabled,
                email_enabled=settings_in.email_enabled,
                sms_enabled=settings_in.sms_enabled,
                sound_enabled=settings_in.sound_enabled,
                sensitivity=settings_in.sensitivity.value,
                auto_record=settings_in.auto_record,
                record_duration=settings_in.record_duration
            )
        else:
            # Default settings
            settings_obj = FeedSettings(feed_id=db_obj.id)
            
        db.add(settings_obj)
        await db.commit()

        # Reload the feed with settings relationship
        result = await db.execute(
            select(CameraFeed)
            .options(selectinload(CameraFeed.settings))
            .where(CameraFeed.id == db_obj.id)
        )
        return result.scalar_one()

    async def update(
        self, db: AsyncSession, *, db_obj: CameraFeed, obj_in: FeedUpdate | dict
    ) -> CameraFeed:
        """Update feed"""
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        # Handle Enum conversions if necessary
        # if "feed_type" in update_data and hasattr(update_data["feed_type"], "value"):
        #     update_data["feed_type"] = update_data["feed_type"].value
        if "status" in update_data and hasattr(update_data["status"], "value"):
            update_data["status"] = update_data["status"].value

        for field, value in update_data.items():
            if field == "fps" and not value:
                continue  # Skip updating fps if value is None or falsy
            setattr(db_obj, field, value)

        db.add(db_obj)
        await db.commit()

        # Reload the feed with settings relationship
        result = await db.execute(
            select(CameraFeed)
            .options(selectinload(CameraFeed.settings))
            .where(CameraFeed.id == db_obj.id)
        )
        return result.scalar_one()

    async def remove(self, db: AsyncSession, *, id: UUID) -> CameraFeed:
        """Delete feed"""
        obj = await self.get(db, id=id)
        await db.delete(obj)
        await db.commit()
        return obj
        
    async def update_settings(
        self, db: AsyncSession, *, feed_id: UUID, obj_in: FeedSettingsUpdate
    ) -> Optional[FeedSettings]:
        """Update feed settings"""
        result = await db.execute(select(FeedSettings).where(FeedSettings.feed_id == feed_id))
        db_obj = result.scalar_one_or_none()
        
        if not db_obj:
            return None
            
        update_data = obj_in.model_dump(exclude_unset=True)
        
        # Handle Enum conversions
        if "sensitivity" in update_data and hasattr(update_data["sensitivity"], "value"):
            update_data["sensitivity"] = update_data["sensitivity"].value
            
        for field, value in update_data.items():
            setattr(db_obj, field, value)
            
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

feed = CRUDFeed()
