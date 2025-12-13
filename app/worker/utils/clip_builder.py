import os
import cv2
import time
import glob
from datetime import datetime
from typing import List


class ClipBuilder:
    """
    Handles creation of a video clip from a set of saved frame files.
    """

    def __init__(self, output_dir: str = "clips"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def build_clip(
        self,
        frame_paths: List[str],
        fps: int = 30,
        codec: str = "mp4v"
    ) -> str:
        """
        Combines given frames into a single MP4 video.

        Args:
            frame_paths: Ordered list of frame file paths.
            fps: Frames per second.
            codec: FourCC codec (default: mp4v).

        Returns:
            The full path to the generated video file.
        """
        if not frame_paths:
            raise ValueError("No frames provided to build the clip.")

        # Load first frame to get dimensions
        first_frame = cv2.imread(frame_paths[0])
        height, width, _ = first_frame.shape

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_name = f"clip_{timestamp}.mp4"

        output_path = os.path.join(self.output_dir, output_name)

        fourcc = cv2.VideoWriter_fourcc(*codec)
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        for fpath in frame_paths:
            frame = cv2.imread(fpath)
            if frame is None:
                continue
            out.write(frame)

        out.release()
        return output_path
