"""
Event buffering and windowing utilities (Ported to Backend Worker)
"""
from collections import deque
from typing import List, Dict, Any
from datetime import datetime, timedelta
import logging

from app.worker.models.data_models import FrameAnalysis

logger = logging.getLogger(__name__)


class EventBuffer:
    """
    Circular buffer for frame analysis events with windowing support
    """

    def __init__(self, window_size: int = 5, fps: int = 15):
        """
        Initialize event buffer

        Args:
            window_size: Time window in seconds
            fps: Frames per second
        """
        self.window_size = window_size
        self.fps = fps
        self.max_frames = window_size * fps

        self.buffer: deque[FrameAnalysis] = deque(maxlen=self.max_frames)
        self.high_risk_buffer: deque[FrameAnalysis] = deque(maxlen=100)

        logger.debug(f"EventBuffer initialized: window={window_size}s, max_frames={self.max_frames}")

    def add_frame_analysis(self, analysis: FrameAnalysis):
        """
        Add frame analysis to buffer

        Args:
            analysis: FrameAnalysis object
        """
        self.buffer.append(analysis)

        # Track high-risk frames separately
        if analysis.flag_rate >= 0.6:
            self.high_risk_buffer.append(analysis)

    def get_window_stats(self) -> Dict[str, Any]:
        """
        Get statistics for current window

        Returns:
            Dictionary with window statistics
        """
        if not self.buffer:
            return {
                "frame_count": 0,
                "average_flag_rate": 0.0,
                "max_flag_rate": 0.0,
                "high_risk_count": 0
            }

        flag_rates = [f.flag_rate for f in self.buffer]

        return {
            "frame_count": len(self.buffer),
            "average_flag_rate": sum(flag_rates) / len(flag_rates),
            "max_flag_rate": max(flag_rates),
            "high_risk_count": sum(1 for f in self.buffer if f.flag_rate >= 0.7),
            "time_span": (self.buffer[-1].timestamp - self.buffer[0].timestamp).total_seconds()
        }

    def get_high_risk_frames(self, count: int = 10) -> List[FrameAnalysis]:
        """
        Get most recent high-risk frames

        Args:
            count: Number of frames to return

        Returns:
            List of FrameAnalysis objects
        """
        return list(self.high_risk_buffer)[-count:]

    def get_recent_frames(self, count: int = 10) -> List[FrameAnalysis]:
        """
        Get most recent frames from buffer

        Args:
            count: Number of frames to return

        Returns:
            List of FrameAnalysis objects
        """
        return list(self.buffer)[-count:]

    def clear(self):
        """Clear all buffers"""
        self.buffer.clear()
        self.high_risk_buffer.clear()

    def get_status(self) -> Dict[str, Any]:
        """
        Get buffer status information

        Returns:
            Status dictionary
        """
        return {
            "buffer_size": len(self.buffer),
            "buffer_capacity": self.max_frames,
            "high_risk_count": len(self.high_risk_buffer),
            "window_size_seconds": self.window_size
        }
