from typing import Optional, List
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from sqlalchemy.orm import selectinload

from app.models.analytics import SystemMetric, Detection, AgentSession
from app.models.alert import Alert, AlertAction
from app.models.log import SystemLog
from app.schemas.analytics import (
    SystemMetricCreate,
    DetectionCreate,
    AgentSessionCreate,
    AgentSessionUpdate
)

class CRUDAnalytics:
    # System Metrics
    async def create_metric(self, db: AsyncSession, *, obj_in: SystemMetricCreate) -> SystemMetric:
        """Create new system metric"""
        db_obj = SystemMetric(
            cpu_usage=obj_in.cpu_usage,
            memory_usage=obj_in.memory_usage,
            disk_usage=obj_in.disk_usage,
            network_latency=obj_in.network_latency,
            active_feeds=obj_in.active_feeds,
            active_agents=obj_in.active_agents,
            feed_id=obj_in.feed_id
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get_latest_metrics_by_feed(self, db: AsyncSession) -> List[SystemMetric]:
        """Get the most recent system metric for each feed"""
        # PostgreSQL specific 'DISTINCT ON' is efficient for this
        result = await db.execute(
            select(SystemMetric)
            .distinct(SystemMetric.feed_id)
            .order_by(SystemMetric.feed_id, desc(SystemMetric.created_at))
        )
        return result.scalars().all()

    async def get_avg_metrics(self, db: AsyncSession, *, hours: int = 24) -> dict:
        """Get average metrics for the last N hours"""
        since = datetime.utcnow() - timedelta(hours=hours)
        result = await db.execute(
            select(
                func.avg(SystemMetric.cpu_usage).label("avg_cpu"),
                func.avg(SystemMetric.memory_usage).label("avg_memory"),
                func.avg(SystemMetric.network_latency).label("avg_latency")
            ).where(SystemMetric.created_at >= since)
        )
        row = result.first()
        return {
            "avg_cpu_usage": float(row.avg_cpu) if row.avg_cpu else 0.0,
            "avg_memory_usage": float(row.avg_memory) if row.avg_memory else 0.0,
            "avg_network_latency": float(row.avg_latency) if row.avg_latency else None
        }

    # Detections
    async def create_detection(self, db: AsyncSession, *, obj_in: DetectionCreate) -> Detection:
        """Create new detection"""
        db_obj = Detection(
            feed_id=obj_in.feed_id,
            alert_id=obj_in.alert_id,
            detection_type=obj_in.detection_type,
            confidence=obj_in.confidence,
            bounding_box=obj_in.bounding_box,
            metadata_=obj_in.metadata,
            frame_id=obj_in.frame_id
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get_recent_detections(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100, feed_id: Optional[UUID] = None
    ) -> List[Detection]:
        """Get recent detections"""
        query = select(Detection).order_by(desc(Detection.timestamp))
        
        if feed_id:
            query = query.where(Detection.feed_id == feed_id)
        
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    async def count_detections_since(self, db: AsyncSession, *, since: datetime) -> int:
        """Count detections since a given time"""
        result = await db.execute(
            select(func.count(Detection.id)).where(Detection.timestamp >= since)
        )
        return result.scalar()

    async def get_detection_types_count(self, db: AsyncSession, *, since: datetime) -> dict:
        """Get count of detections by type"""
        result = await db.execute(
            select(
                Detection.detection_type,
                func.count(Detection.id).label("count")
            )
            .where(Detection.timestamp >= since)
            .group_by(Detection.detection_type)
        )
        return {row.detection_type: row.count for row in result}

    # Agent Sessions
    async def create_agent_session(self, db: AsyncSession, *, obj_in: AgentSessionCreate) -> AgentSession:
        """Create new agent session"""
        db_obj = AgentSession(
            feed_id=obj_in.feed_id,
            agent_version=obj_in.agent_version,
            status=obj_in.status,
            frames_processed=obj_in.frames_processed,
            detections_count=obj_in.detections_count,
            alerts_triggered=obj_in.alerts_triggered,
            average_latency=obj_in.average_latency
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update_agent_session(
        self, db: AsyncSession, *, db_obj: AgentSession, obj_in: AgentSessionUpdate
    ) -> AgentSession:
        """Update agent session"""
        update_data = obj_in.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        
        # Update heartbeat
        db_obj.last_heartbeat = datetime.utcnow()
        
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get_active_agent_sessions(self, db: AsyncSession) -> List[AgentSession]:
        """Get all active agent sessions"""
        result = await db.execute(
            select(AgentSession).where(AgentSession.status == "active")
        )
        return result.scalars().all()

    async def count_active_alerts(self, db: AsyncSession) -> int:
        """Count active alerts"""
        result = await db.execute(
            select(func.count(Alert.id)).where(Alert.status == "active")
        )
        return result.scalar()

    async def count_actions_today(self, db: AsyncSession, *, action_type: str) -> int:
        """Count actions of a specific type today"""
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        result = await db.execute(
            select(func.count(AlertAction.id))
            .where(AlertAction.action_type == action_type)
            .where(AlertAction.created_at >= today_start)
        )
        return result.scalar()

analytics = CRUDAnalytics()
