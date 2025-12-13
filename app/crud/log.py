from typing import Optional, List
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_

from app.models.log import SystemLog
from app.schemas.log import SystemLogCreate, SystemLogFilter

class CRUDLog:
    async def get(self, db: AsyncSession, id: UUID) -> Optional[SystemLog]:
        """Get log by ID"""
        result = await db.execute(select(SystemLog).where(SystemLog.id == id))
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[SystemLogFilter] = None
    ) -> List[SystemLog]:
        """Get logs with filtering"""
        query = select(SystemLog)
        
        if filters:
            if filters.source:
                query = query.where(SystemLog.source == filters.source.value)
            if filters.level:
                query = query.where(SystemLog.level == filters.level.value)
            if filters.feed_id:
                query = query.where(SystemLog.feed_id == filters.feed_id)
            if filters.user_id:
                query = query.where(SystemLog.user_id == filters.user_id)
            if filters.alert_id:
                query = query.where(SystemLog.alert_id == filters.alert_id)
            if filters.start_date:
                query = query.where(SystemLog.created_at >= filters.start_date)
            if filters.end_date:
                query = query.where(SystemLog.created_at <= filters.end_date)
            if filters.search:
                # Search in message and details fields
                search_term = f"%{filters.search}%"
                query = query.where(
                    or_(
                        SystemLog.message.ilike(search_term),
                        SystemLog.details.ilike(search_term)
                    )
                )
            
        # Order by newest first
        query = query.order_by(desc(SystemLog.created_at))
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()

    async def create(self, db: AsyncSession, *, obj_in: SystemLogCreate) -> SystemLog:
        """Create new log entry"""
        db_obj = SystemLog(
            source=obj_in.source.value,
            level=obj_in.level.value,
            feed_id=obj_in.feed_id,
            user_id=obj_in.user_id,
            alert_id=obj_in.alert_id,
            message=obj_in.message,
            details=obj_in.details
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def count(
        self,
        db: AsyncSession,
        *,
        filters: Optional[SystemLogFilter] = None
    ) -> int:
        """Count logs matching filters"""
        query = select(SystemLog)
        
        if filters:
            if filters.source:
                query = query.where(SystemLog.source == filters.source.value)
            if filters.level:
                query = query.where(SystemLog.level == filters.level.value)
            if filters.feed_id:
                query = query.where(SystemLog.feed_id == filters.feed_id)
            if filters.user_id:
                query = query.where(SystemLog.user_id == filters.user_id)
            if filters.alert_id:
                query = query.where(SystemLog.alert_id == filters.alert_id)
            if filters.start_date:
                query = query.where(SystemLog.created_at >= filters.start_date)
            if filters.end_date:
                query = query.where(SystemLog.created_at <= filters.end_date)
            if filters.search:
                search_term = f"%{filters.search}%"
                query = query.where(
                    or_(
                        SystemLog.message.ilike(search_term),
                        SystemLog.details.ilike(search_term)
                    )
                )
        
        result = await db.execute(query)
        return len(result.scalars().all())

log = CRUDLog()
