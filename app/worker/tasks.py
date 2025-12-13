import logging
import time
import asyncio
from typing import Dict, Any
from datetime import datetime

from app.core.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.crud.feed import feed as feed_crud
from app.models.feed import FeedStatus

# Setup logging for worker
logger = logging.getLogger("celery_worker")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


async def get_feed_status(feed_id: str) -> str:
    """Helper to fetch current status from DB"""
    async with AsyncSessionLocal() as db:
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
    
    # Get initial details (Sync or Async run_until_complete)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        current_status = loop.run_until_complete(get_feed_status(feed_id))
        if current_status != FeedStatus.ACTIVE.value:
            logger.info(f"Feed {feed_id} is not ACTIVE ({current_status}). Aborting task.")
            return

        # Fetch feed details
        async def get_feed_details():
            async with AsyncSessionLocal() as db:
                return await feed_crud.get(db, id=feed_id)
        
        feed = loop.run_until_complete(get_feed_details())
        if not feed:
             logger.error(f"Feed {feed_id} not found.")
             return
             
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
                'flag_threshold': 0.7,
                'frame_skip': 5,
                'evaluation_window': 5
             },
             'analyzer': {
                 'model_name': 'gemini-2.5-pro',
                 'trigger_threshold': 0.7,
                 'segment_duration': 10
             },
            'alert': {
                "model_name": "gpt4.1"
            },
             'surveillance': {
                 'instruction': feed.custom_instruction or "Detect any anomalous behavior.",
                 'alert_configuration': {
                     "configs": feed.settings.model_dump_json() if feed.settings else "{}",
                     "contacts": [c.model_dump() for c in feed.contacts] if feed.contacts else [],
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
                current_status = loop.run_until_complete(get_feed_status(feed_id))
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
        loop.close()
        logger.info(f"Monitoring task ended for {feed_id}")

