import os
import cv2
import time
import glob
import logging
from datetime import datetime, timedelta
from typing import List


logger = logging.getLogger(__name__)


class FrameFeed:
    """
    Handles continuous saving of frames from a camera feed into a timestamped folder structure.

    Structure:
    └── frames/
        ├── 2025-11-13/
        │   ├── 1731500001.234.jpg
        │   ├── 1731500001.259.jpg
        │   └── ...
    """

    def __init__(self, base_dir: str = "frames", frame_format: str = "jpg"):
        self.base_dir = base_dir
        self.frame_format = frame_format
        os.makedirs(self.base_dir, exist_ok=True)

    def _get_today_dir(self) -> str:
        """Creates or retrieves today's directory for frame storage."""
        today = datetime.now().strftime("%Y-%m-%d")
        day_path = os.path.join(self.base_dir, today)
        os.makedirs(day_path, exist_ok=True)
        return day_path

    def save_frame(self, frame, timestamp: datetime) -> str:
        """
        Saves a single frame with a timestamp-based filename.

        Args:
            frame: The image (OpenCV frame) to save.
            timestamp: The timestamp (epoch seconds) for the frame.

        Returns:
            The path to the saved frame file.
        """
        ts = timestamp.timestamp()  # float
        ts_str = f"{ts:.6f}".replace(".", "_")  # microsecond precision
        frame_name = f"{ts_str}.{self.frame_format}"
        save_path = os.path.join(self._get_today_dir(), frame_name)
        cv2.imwrite(save_path, frame)

        # logger.info(f"Saved frame at {save_path}")
        return save_path

    def get_frames_in_range(self, start_ts: datetime, end_ts: datetime) -> List[str]:
        """
        Retrieves list of frame paths between two datetime timestamps.
        Cleaned up with essential logging only.
        """
        today_dir = self._get_today_dir()
        logger.info(f"[FrameRange] Scanning directory: {today_dir}")

        frame_files = glob.glob(os.path.join(today_dir, f"*.{self.frame_format}"))
        logger.info(f"[FrameRange] Found {len(frame_files)} frames.")
        logger.info(f"[FrameRange] time range: {start_ts} -> {end_ts}")

        padded_start_dt = start_ts - timedelta(seconds=2)
        padded_end_dt = end_ts + timedelta(seconds=2)



        # --- 2. Prevent negative timestamps ---
        start_epoch = max(0.0, padded_start_dt.timestamp())
        end_epoch = padded_end_dt.timestamp()


        frames_in_range = []
        extracted_ts = []

        for f in frame_files:
            base = os.path.basename(f)
            name_part = base.split(".")[0]  # "1763232483_092017"

            try:
                ts = float(name_part.replace("_", "."))
                extracted_ts.append(ts)
            except ValueError:
                logger.warning(f"[FrameRange] Skipping invalid filename: {base}")
                continue

            if start_epoch <= ts <= end_epoch:
                frames_in_range.append(f)

        # Sort by timestamp
        frames_in_range.sort(
            key=lambda x: float(os.path.basename(x).split(".")[0].replace("_", "."))
        )

        logger.info(
            f"[FrameRange] Frames selected: {len(frames_in_range)} "
            f"(range: {padded_start_dt} -> {padded_end_dt})"
        )

        # Warn if timestamps in folder were not sequential
        if extracted_ts != sorted(extracted_ts):
            logger.warning("[FrameRange] Frame timestamps appear out of order.")

        return frames_in_range
