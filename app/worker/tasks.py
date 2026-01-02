import os
import logging
import time
import asyncio
from typing import Dict, Any
from datetime import datetime

# Load environment variables FIRST before any other imports
from dotenv import load_dotenv
load_dotenv()

from app.core.celery_app import celery_app
from app.crud.feed import feed as feed_crud
from app.models.feed import FeedStatus

# Get logger for this module (will use configuration set by worker_init signal)
logger = logging.getLogger(__name__)


def _sensitivity_to_threshold(sensitivity: str) -> float:
    """
    Convert sensitivity level string to a float threshold value.

    Args:
        sensitivity: Sensitivity level ("low", "medium", "high")

    Returns:
        Float threshold value for flag_rate comparisons
    """
    sensitivity_map = {
        'high': 0.60,    # More sensitive = lower threshold triggers alerts
        'medium': 0.75,  # Default
        'low': 0.90,     # Less sensitive = higher threshold needed to trigger
    }
    # Handle both string and enum values
    sensitivity_str = str(sensitivity).lower()
    return sensitivity_map.get(sensitivity_str, 0.75)


def get_sync_engine():
    """Create a fresh async engine for the current event loop"""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from app.core.config import settings

    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        future=True,
        pool_pre_ping=True,
        pool_size=2,
        max_overflow=3,
    )
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    return engine, session_factory


async def get_feed_status(session_factory, feed_id: str) -> str:
    """Helper to fetch current status from DB"""
    async with session_factory() as db:
        feed = await feed_crud.get(db, id=feed_id)
        if feed:
            return feed.status
    return FeedStatus.INACTIVE.value


@celery_app.task(bind=True)
def monitor_feed_task(self, feed_id: str):
    """
    Background Task to monitor a camera feed.
    This runs internally in an infinite loop until the feed status is changed to INACTIVE in the DB.
    """
    logger.info(f"Starting monitoring task for Feed ID: {feed_id}")
    
    video_capture = None
    engine = None

    # Get initial details (Sync or Async run_until_complete)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Create task-specific engine and session factory (scoped to this event loop)
        engine, session_factory = get_sync_engine()

        current_status = loop.run_until_complete(get_feed_status(session_factory, feed_id))
        if current_status != FeedStatus.ACTIVE.value:
            logger.info(f"Feed {feed_id} is not ACTIVE ({current_status}). Aborting task.")
            return

        # Fetch feed details
        async def get_feed_details():
            async with session_factory() as db:
                return await feed_crud.get(db, id=feed_id)
        
        feed = loop.run_until_complete(get_feed_details())
        if not feed:
             logger.error(f"Feed {feed_id} not found.")
             return

        # Serialize feed settings
        feed_settings_dict = {}
        if feed.settings:
            feed_settings_dict = {
                'push_enabled': feed.settings.push_enabled,
                'email_enabled': feed.settings.email_enabled,
                'sms_enabled': feed.settings.sms_enabled,
                'sound_enabled': feed.settings.sound_enabled,
                'sensitivity': feed.settings.sensitivity,
                'auto_record': feed.settings.auto_record,
                'record_duration': feed.settings.record_duration,
            }

        # Serialize contacts
        contacts_list = []
        if feed.contacts:
            for contact in feed.contacts:
                contacts_list.append({
                    'id': str(contact.id),
                    'name': contact.name,
                    'phone': contact.phone,
                    'email': contact.email,
                    'is_active': contact.is_active,
                })

        settings = {
             'camera': {
                 'id': feed_id,
                 'fps': feed.fps or 40,
                 'source': feed.feed_url,
                 "resolution": {
                     "width": 1280,
                     "height": 720,
                 }
             },
             'classifier': {
                'model_name': 'gemini-2.5-flash',
                 "model_temperature": 0.0,
                'flag_threshold': _sensitivity_to_threshold(feed.settings.sensitivity if feed.settings else 'medium'),
                'frame_skip': feed.fps or 40,
                'evaluation_window': 5
             },
             'analyzer': {
                 'model_name': 'gemini-2.5-flash',
                 "model_temperature": 0.0,
                 'trigger_threshold': _sensitivity_to_threshold(feed.settings.sensitivity if feed.settings else 'medium'),
                 'segment_duration': 10
             },
            'alert': {
                "model_name": "gpt4.1"
            },
             'surveillance': {
                 'instruction': feed.custom_instruction or "Detect any anomalous behavior.",
                 'alert_configuration': {
                     "configs": feed_settings_dict,
                     "contacts": contacts_list,
                 }
             }
        }
        
        # Initialize FeedMonitor
        from app.worker.core.feed_monitor import FeedMonitor
        monitor = FeedMonitor(settings)
        
        # Initialize VideoCapture utility
        from app.worker.utils.video_capture import VideoCapture
        video_capture = VideoCapture(settings)
        
        if not video_capture.start():
            # Check for mock/test mode
            if "test" in feed.feed_url or "mock" in feed.feed_url:
                logger.info("Using mock simulation mode (VideoCapture failed on URL)")
                video_capture = None
            else:
                logger.error(f"Failed to open video capture for {feed.feed_url}")
                return

        check_interval = 5.0 
        last_check = time.time()
        frame_count = 0
        
        while True:
            # A. Check Stop Signal
            if time.time() - last_check > check_interval:
                current_status = loop.run_until_complete(get_feed_status(session_factory, feed_id))
                if current_status != FeedStatus.ACTIVE.value:
                    logger.info(f"Stop signal received (Status={current_status}). Shutting down monitoring for {feed_id}.")
                    break
                last_check = time.time()
            
            # B. Read Frame using VideoCapture utility
            if video_capture:
                result = video_capture.read_frame()
                if result is None:
                    logger.error("VideoCapture returned None - not initialized")
                    break
                    
                ret, frame = result
                if not ret:
                    logger.warning(f"Failed to read frame from {feed_id}. Retrying connection...")
                    video_capture.stop()
                    time.sleep(1)
                    video_capture = VideoCapture(settings)
                    if not video_capture.start():
                        logger.error("Failed to reconnect video capture")
                        break
                    continue
                
                # C. Processing via FeedMonitor
                frame_count += 1
                try:
                    # 1. Process Frame (Layer 1)
                    loop.run_until_complete(
                        monitor.process_frame(frame, frame_count)
                    )
                    
                    # 2. Check for Segment Trigger (Layer 2)
                    segment_to_analyze = loop.run_until_complete(
                        monitor.check_segment_trigger()
                    )
                    
                    if segment_to_analyze:
                         logger.info(f"Triggering Deep Analysis for Segment {segment_to_analyze.segment_id}")
                         loop.run_until_complete(
                             monitor.analyze_segment(segment_to_analyze)
                         )

                except Exception as e:
                    logger.error(f"Monitor error: {e}")
                
                # D. Throttle FPS
                time.sleep(1/settings['camera']['fps'])
            else:
                # Mock Processing
                logger.info(f"Simulating processing for {feed_id}...")
                time.sleep(1.0)

    except Exception as e:
        logger.error(f"Error in monitoring task {feed_id}: {e}")
    finally:
        if video_capture:
            video_capture.stop()
        # Properly dispose of the engine before closing the loop
        if engine:
            try:
                loop.run_until_complete(engine.dispose())
            except Exception as e:
                logger.warning(f"Error disposing engine: {e}")
        loop.close()
        logger.info(f"Monitoring task ended for {feed_id}")

