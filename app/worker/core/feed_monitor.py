"""
Main controller orchestrating the two-layer agent system (Ported from AgentController)
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from collections import deque
import uuid
import os

from app.worker.core.alert_engine import AlertEngine
from app.worker.core.frame_classifier import FrameClassifier
from app.worker.core.video_analyzer import VideoAnalyzer
from app.worker.models.data_models import FrameAnalysis, VideoSegment, AlertEvent
from app.worker.utils.clip_builder import ClipBuilder
from app.worker.utils.event_buffer import EventBuffer
from app.worker.utils.frame_feed import FrameFeed

# Database Imports for Alert Saving
from app.core.database import AsyncSessionLocal
from app.crud.alert import alert as alert_crud
from app.schemas.alert import (
    AlertCreate, AlertAIAnalysisCreate, AlertActionCreate,
    AlertStatus, AlertSeverity, AlertType
)

logger = logging.getLogger(__name__)


class FeedMonitor:
    """
    Orchestrates the two-layer SafeX-Agent system for a single feed:
    - Layer 1: Real-time frame classification (Mistral)
    - Layer 2: Contextual video analysis and response (Gemini)
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Initialize Utilities
        self.frame_feed = FrameFeed()
        self.clip_builder = ClipBuilder()

        # Initialize Layers
        self.frame_classifier = FrameClassifier(config)
        self.video_analyzer = VideoAnalyzer(config, self.frame_feed, self.clip_builder)
        self.alert_engine = AlertEngine(config)

        # Event Buffering
        self.event_buffer = EventBuffer(
            window_size=config['classifier'].get('evaluation_window', 5),
            fps=config['camera']['fps']
        )

        # Segment Tracking
        self.current_segment_frames: List[FrameAnalysis] = []
        self.segment_duration = config['analyzer']['segment_duration']

        # Statistics
        self.stats = {
            "frames_processed": 0,
            "segments_analyzed": 0,
            "alerts_triggered": 0,
            "start_time": datetime.now()
        }

        logger.info(f"FeedMonitor initialized for feed {config.get('camera', {}).get('id')}")

    async def process_frame(self, frame, frame_id: int) -> Optional[FrameAnalysis]:
        """
        Process a single frame through Layer 1 classifier
        """
        frame_timestamp = datetime.now()
        self.frame_feed.save_frame(frame, frame_timestamp)

        # Check if frame should be skipped
        if self.frame_classifier.should_skip_frame(frame_id):
            return None

        # Classify frame
        analysis = await self.frame_classifier.classify_frame(frame, frame_id, frame_timestamp)

        # Update statistics
        self.stats["frames_processed"] += 1

        # Add to event buffer
        self.event_buffer.add_frame_analysis(analysis)

        # Add to current segment
        self.current_segment_frames.append(analysis)

        # Save ALL detections to database for comprehensive analytics
        # This ensures we have a complete record of all frame analyses
        await self._save_detection_internal(analysis)

        # Log High-Risk Frames separately
        if analysis.flag_rate >= self.config['classifier']['flag_threshold']:
            logger.warning(
                f"🚨 HIGH FLAG: Frame {frame_id} | "
                f"Rate: {analysis.flag_rate:.2f} | "
                f"{analysis.description[:60]}..."
            )

        return analysis

    async def _save_detection_internal(self, analysis: FrameAnalysis):
        """
        Save a high-risk frame analysis as a Detection in the database.
        """
        import traceback
        from uuid import UUID as PyUUID
        from app.core.database import AsyncSessionLocal
        from app.crud.analytics import analytics
        from app.schemas.analytics import DetectionCreate
        
        try:
            feed_id = self.config['camera']['id']
            logger.info(f"Attempting to save detection for frame {analysis.frame_id}, feed_id: {feed_id}")

            # Convert feed_id to UUID if it's a string
            if isinstance(feed_id, str):
                feed_id = PyUUID(feed_id)
            
            detection_data = DetectionCreate(
                feed_id=feed_id,
                detection_type=analysis.risk_level.value if hasattr(analysis, 'risk_level') and analysis.risk_level else "anomaly",
                confidence=analysis.flag_rate,
                description=analysis.description,
                bounding_box=None,  # Not available from classifier
                context_tags=analysis.context_tags if hasattr(analysis, 'context_tags') else [],
                metadata={
                    "description": analysis.description,
                    "risk_level": analysis.risk_level.value if hasattr(analysis, 'risk_level') and analysis.risk_level else None,
                    "timestamp": analysis.timestamp.isoformat(),
                },
                frame_id=str(analysis.frame_id)
            )
            
            logger.info(f"Detection data prepared: {detection_data.detection_type}, confidence: {detection_data.confidence}")

            async with AsyncSessionLocal() as db:
                # 1. Save Detection
                result = await analytics.create_detection(db, obj_in=detection_data)
                
                # 2. Update Feed Stability Stats (Running Average)
                # We do this here inside the worker to avoid API latency
                from app.crud.feed import feed as feed_crud
                feed_obj = await feed_crud.get(db, id=feed_id)
                if feed_obj:
                    new_sum = (feed_obj.rolling_confidence_sum or 0.0) + detection_data.confidence
                    new_count = (feed_obj.total_detection_count or 0) + 1
                    await feed_crud.update(db, db_obj=feed_obj, obj_in={
                        "rolling_confidence_sum": new_sum,
                        "total_detection_count": new_count
                    })

                logger.info(f"✓ Detection saved & Stability updated! ID: {result.id}")

        except Exception as e:
            logger.error(f"❌ Failed to save detection for frame {analysis.frame_id}: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")

    async def _save_alert_to_db(self, segment: VideoSegment, response):
        """
        Save the triggered alert and its analysis to the database.
        """
        try:
            feed_id = self.config['camera']['id']
            # feed_id parsing if string
            from uuid import UUID as PyUUID
            if isinstance(feed_id, str):
                feed_id = PyUUID(feed_id)

            # Map specific types to Generic for now, or infer from instruction/response
            # Defaulting to 'intrusion' or 'other' based on simple keywords if needed
            alert_type = AlertType.OTHER
            if "intrusion" in response.video_analysis.lower():
                alert_type = AlertType.INTRUSION
            elif "weapon" in response.video_analysis.lower():
                alert_type = AlertType.WEAPON
            elif "fire" in response.video_analysis.lower():
                alert_type = AlertType.FIRE
            
            # Map Level
            severity_map = {
                "low": AlertSeverity.LOW,
                "medium": AlertSeverity.MEDIUM,
                "high": AlertSeverity.HIGH,
                "critical": AlertSeverity.CRITICAL
            }
            severity = severity_map.get(response.alert_level, AlertSeverity.MEDIUM)

            # Prepare Actions
            actions_create = []
            if response.recommended_actions:
                for act in response.recommended_actions:
                    # Simple parser for the action type
                    atype = "log"
                    recipient = "system"
                    if "sms" in act.lower():
                        atype = "sms"
                        recipient = "configured_contact" # Placeholder logic
                    elif "email" in act.lower():
                        atype = "email"
                    
                    actions_create.append(AlertActionCreate(
                        action_type=atype,
                        recipient=recipient,
                        status="pending", # Engine proceeds to process
                        details=act
                    ))

            # Prepare Analysis Object
            ai_analysis_create = AlertAIAnalysisCreate(
                confidence_score=0.95, # High confidence by default for triggered alerts
                detected_objects=[], # Extracted from frame tags if merged?
                scene_description=response.video_analysis,
                risk_factors=[response.instruction_alignment], # Using alignment as risk factor
                recommendations=response.recommended_actions or []
            )

            # Main Alert Object
            alert_in = AlertCreate(
                feed_id=feed_id,
                title=f"AI Alert: {severity.value.upper()} Risk Detected",
                description=response.reasoning[:1000] if response.reasoning else response.video_analysis[:1000],
                status=AlertStatus.ACTIVE,
                severity=severity,
                alert_type=alert_type,
                video_url=None, # To be linked with built clip later
                thumbnail_url=None,
                ai_analysis=ai_analysis_create,
                actions=actions_create
            )

            async with AsyncSessionLocal() as db:
                created_alert = await alert_crud.create(db, obj_in=alert_in)
                logger.info(f"✓✓✓ ALERT SAVED TO DB: {created_alert.id} | {created_alert.title}")
        
        except Exception as e:
            logger.error(f"CRITICAL: Failed to save ALERT to DB: {e}")
            import traceback
            logger.error(traceback.format_exc())

    async def check_segment_trigger(self) -> Optional[VideoSegment]:
        """
        Check if current segment should trigger Layer 2 analysis
        """
        if not self.current_segment_frames:
            return None

        # since we process 1 frame per seconds (roughly, if skipped), tracking array length is proxy for time
        # Better: use timestamp diff
        start_t = self.current_segment_frames[0].timestamp
        end_t = self.current_segment_frames[-1].timestamp
        elapsed = (end_t - start_t).total_seconds()
        
        # Or simple count based on skip rate
        # elapsed = len(self.current_segment_frames) 

        # Using Agent Logic (Length check)
        if len(self.current_segment_frames) >= self.segment_duration:
            # Create segment
            segment = self._create_segment()

            # Check if trigger threshold met
            should_trigger = self.video_analyzer.should_trigger(segment)

            if should_trigger:
                logger.info(
                    f"TRIGGER: Segment {segment.segment_id} | "
                    f"Avg Flag: {segment.average_flag_rate:.2f}"
                )
                return segment
            else:
                logger.debug(
                    f"Segment {segment.segment_id} below threshold "
                    f"({segment.average_flag_rate:.2f})"
                )

            # Updated segment (Pruning logic ported from AgentController)
            self._update_segment(self.video_analyzer.trigger_threshold, segment.average_flag_rate)

        return None

    async def analyze_segment(self, segment: VideoSegment):
        """
        Trigger Layer 2 analysis on a video segment
        """
        try:
            response = await self.video_analyzer.analyze_segment(segment)

            self.stats["segments_analyzed"] += 1
            
            # Process Response (Alerts, DB save)
            if response.should_trigger_alert:
                self.stats["alerts_triggered"] += 1
                logger.critical(
                    f"🚨 ALERT TRIGGERED: Level={response.alert_level} | "
                    f"Analysis: {response.video_analysis[:100]}..."
                )

                # Execute recommended actions via AlertEngine
                if response.recommended_actions:
                    await self.alert_engine.process_alert(
                        response.recommended_actions,
                        context={
                            "segment_id": segment.segment_id,
                            "alert_level": response.alert_level,
                            "video_analysis": response.video_analysis
                        }
                    )

                # SAVE TO DB (Fix for missing alerts)
                await self._save_alert_to_db(segment, response)

            return response

        except Exception as e:
            logger.error(f"Error in analyze_segment: {str(e)}")
            return None

    def _create_segment(self) -> VideoSegment:
        """
        Create VideoSegment from current frame buffer
        """
        if not self.current_segment_frames:
            raise ValueError("No frames in current segment")

        # Calculate average flag rate
        avg_flag_rate = sum(f.flag_rate for f in self.current_segment_frames) / len(self.current_segment_frames)

        segment = VideoSegment(
            segment_id=f"seg_{uuid.uuid4().hex[:8]}",
            start_frame=self.current_segment_frames[0].frame_id,
            end_frame=self.current_segment_frames[-1].frame_id,
            start_time=self.current_segment_frames[0].timestamp,
            end_time=self.current_segment_frames[-1].timestamp,
            frames_analysis=self.current_segment_frames.copy(),
            average_flag_rate=avg_flag_rate
        )

        return segment

    def _update_segment(
            self,
            threshold: float,
            avg_flag_rate: float,
            *,
            retain_goal_delta: float = None,
            min_keep_frames: int = 1,
            fallback_keep_fraction: float = 0.25
    ):
        """
        Update retained frames after evaluating a segment.
        Ported exact logic from AgentController.
        """

        frames = self.current_segment_frames
        n = len(frames)
        if n == 0:
            return

        # Ensure sensible parameters
        threshold = float(threshold)
        avg_flag_rate = float(avg_flag_rate)
        if retain_goal_delta is None:
            retain_goal_delta = max(0.05 * threshold, 0.01)

        # If we've already reached or exceeded the threshold -> finalize/clear
        if avg_flag_rate >= threshold:
            self.current_segment_frames = []
            return

        # Compute retain goal
        retain_goal = min(threshold, avg_flag_rate + retain_goal_delta)
        rates = [float(f.flag_rate) for f in frames]

        suffix_found_index = None
        for k in range(1, n + 1):
            suffix = rates[-k:]
            suffix_avg = sum(suffix) / len(suffix)
            if suffix_avg >= retain_goal:
                suffix_found_index = n - k
                break

        if suffix_found_index is not None:
            self.current_segment_frames = frames[suffix_found_index:]
            if len(self.current_segment_frames) < min_keep_frames:
                self.current_segment_frames = frames[-min_keep_frames:]
            return

        fallback_keep = max(min_keep_frames, int(n * fallback_keep_fraction))
        if fallback_keep >= n:
            return

        self.current_segment_frames = frames[-fallback_keep:]
        return

    def get_statistics(self) -> Dict[str, Any]:
        uptime = (datetime.now() - self.stats["start_time"]).total_seconds()
        return {
            **self.stats,
            "uptime_seconds": uptime,
            "buffer_status": self.event_buffer.get_status()
        }
