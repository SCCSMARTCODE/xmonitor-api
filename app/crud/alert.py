from typing import Optional, List
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.models.alert import Alert, AlertAIAnalysis, AlertAction, AlertStatus
from app.schemas.alert import AlertCreate, AlertUpdate, AlertResolve

class CRUDAlert:
    async def get(self, db: AsyncSession, id: UUID) -> Optional[Alert]:
        """Get alert by ID with relations loaded"""
        result = await db.execute(
            select(Alert)
            .options(
                selectinload(Alert.ai_analysis),
                selectinload(Alert.actions)
            )
            .where(Alert.id == id)
        )
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        feed_id: Optional[UUID] = None,
        status: Optional[str] = None,
        severity: Optional[str] = None
    ) -> List[Alert]:
        """Get alerts with filtering"""
        query = select(Alert).options(
            selectinload(Alert.ai_analysis),
            selectinload(Alert.actions)
        )
        
        if feed_id:
            query = query.where(Alert.feed_id == feed_id)
        if status:
            query = query.where(Alert.status == status)
        if severity:
            query = query.where(Alert.severity == severity)
            
        # Order by newest first
        query = query.order_by(desc(Alert.created_at))
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()

    async def create(self, db: AsyncSession, *, obj_in: AlertCreate) -> Alert:
        """Create new alert with analysis and actions"""
        # Create alert
        db_obj = Alert(
            feed_id=obj_in.feed_id,
            title=obj_in.title,
            description=obj_in.description,
            status=obj_in.status.value,
            severity=obj_in.severity.value,
            alert_type=obj_in.alert_type.value,
            video_url=obj_in.video_url,
            thumbnail_url=obj_in.thumbnail_url
        )
        db.add(db_obj)
        await db.flush()  # Get ID

        # Create AI Analysis if provided
        if obj_in.ai_analysis:
            analysis_data = obj_in.ai_analysis
            analysis_obj = AlertAIAnalysis(
                alert_id=db_obj.id,
                confidence_score=analysis_data.confidence_score,
                detected_objects=analysis_data.detected_objects,
                scene_description=analysis_data.scene_description,
                risk_factors=analysis_data.risk_factors,
                recommendations=analysis_data.recommendations
            )
            db.add(analysis_obj)

        # Create Actions if provided
        if obj_in.actions:
            for action_data in obj_in.actions:
                action_obj = AlertAction(
                    alert_id=db_obj.id,
                    action_type=action_data.action_type,
                    recipient=action_data.recipient,
                    status=action_data.status,
                    details=action_data.details
                )
                db.add(action_obj)
            
        await db.commit()
        await db.refresh(db_obj)
        
        # Reload with relations
        return await self.get(db, db_obj.id)

    async def update(
        self, db: AsyncSession, *, db_obj: Alert, obj_in: AlertUpdate | dict
    ) -> Alert:
        """Update alert"""
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        # Handle Enum conversions
        if "status" in update_data and hasattr(update_data["status"], "value"):
            update_data["status"] = update_data["status"].value
        if "severity" in update_data and hasattr(update_data["severity"], "value"):
            update_data["severity"] = update_data["severity"].value

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def resolve(
        self, db: AsyncSession, *, db_obj: Alert, obj_in: AlertResolve, user_id: UUID
    ) -> Alert:
        """Resolve an alert"""
        db_obj.status = obj_in.status.value
        db_obj.resolution_notes = obj_in.resolution_notes
        db_obj.resolved_by = user_id
        db_obj.resolved_at = datetime.utcnow()
        
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

alert = CRUDAlert()
