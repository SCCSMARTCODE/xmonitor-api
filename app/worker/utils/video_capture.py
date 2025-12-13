"""
Video capture utility for camera/stream input (Ported to Backend Worker)
"""
import cv2
import asyncio
from typing import Optional, AsyncGenerator, Tuple
import numpy as np
import logging

logger = logging.getLogger(__name__)


class VideoCapture:
    """
    Async video capture wrapper for OpenCV
    Supports webcam, video files, and RTSP streams
    """

    def __init__(self, config: dict):
        self.source = config['camera']['source']
        self.fps = config['camera']['fps']
        self.resolution = (
            config['camera'].get('resolution', {}).get('width', 640),
            config['camera'].get('resolution', {}).get('height', 480)
        )
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_running = False

        logger.info(f"VideoCapture configured: source={self.source}, fps={self.fps}")

    def start(self) -> bool:
        """
        Initialize video capture

        Returns:
            True if successful, False otherwise
        """
        try:
            self.cap = cv2.VideoCapture(self.source)

            if not self.cap.isOpened():
                logger.error(f"Failed to open video source: {self.source}")
                return False

            # Set properties
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)

            # Verify settings
            actual_width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            actual_height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            actual_fps = self.cap.get(cv2.CAP_PROP_FPS)

            logger.info(
                f"Video capture started: {actual_width}x{actual_height} @ {actual_fps}fps"
            )

            self.is_running = True
            return True

        except Exception as e:
            logger.error(f"Error starting video capture: {str(e)}")
            return False

    async def stream_frames(self) -> AsyncGenerator[Tuple[np.ndarray, int], None]:
        """
        Async generator for video frames

        Yields:
            Tuple of (frame, frame_id)
        """
        frame_id = 0
        frame_interval = 1.0 / self.fps

        while self.is_running and self.cap is not None:
            # Read frame in thread to avoid blocking
            ret, frame = await asyncio.to_thread(self.cap.read)

            if not ret:
                logger.warning("Failed to read frame from video source")
                break

            yield frame, frame_id
            frame_id += 1

            # Control frame rate
            await asyncio.sleep(frame_interval)

    def read_frame(self) -> Optional[Tuple[bool, np.ndarray]]:
        """
        Synchronous frame read

        Returns:
            Tuple of (success, frame) or None
        """
        if self.cap is None:
            return None
        return self.cap.read()

    def stop(self):
        """Release video capture resources"""
        self.is_running = False

        if self.cap is not None:
            self.cap.release()
            self.cap = None
            logger.info("Video capture stopped")

    def get_properties(self) -> dict:
        """
        Get current capture properties

        Returns:
            Dictionary of video properties
        """
        if self.cap is None:
            return {}

        return {
            "width": self.cap.get(cv2.CAP_PROP_FRAME_WIDTH),
            "height": self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT),
            "fps": self.cap.get(cv2.CAP_PROP_FPS),
            "frame_count": self.cap.get(cv2.CAP_PROP_FRAME_COUNT),
            "is_opened": self.cap.isOpened()
        }

    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop()
