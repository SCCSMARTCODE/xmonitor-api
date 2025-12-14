"""
Layer 1: Real-Time Frame Classifier (Ported to Backend Worker)
Uses Mistral Multimodal LLM for frame-level analysis
"""
import asyncio
import base64
import json
import re
import os
from datetime import datetime
from sys import maxsize
from collections import deque
from google import genai
from google.genai import types
from typing import Optional, Dict, Any
import cv2
import numpy as np
import logging

from pydantic import BaseModel, Field

from app.worker.models.data_models import FrameAnalysis, RiskLevel

logger = logging.getLogger(__name__)


class FrameClassifier:
    """
    Real-time frame classifier using Mistral Multimodal LLM.
    Provides continuous frame analysis with flag rate computation.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        # Load Google API key for Genai client
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

        # Debug logging to verify key is loaded
        if not api_key:
            logger.error("GOOGLE_API_KEY or GEMINI_API_KEY not found in environment variables!")
            logger.error(f"Available env vars starting with 'GOOGLE': {[k for k in os.environ.keys() if 'GOOGLE' in k.upper()]}")
            raise ValueError("GOOGLE_API_KEY or GEMINI_API_KEY environment variable not set")
        else:
            logger.info(f"Google API key loaded successfully (length: {len(api_key)})")

        self.client = genai.Client(api_key=api_key)
        self.model_name = config['classifier']['model_name']
        self.flag_threshold = config['classifier']['flag_threshold']
        self.frame_skip = config['classifier'].get('frame_skip', 1)
        self.surveillance_instruction = config['surveillance']['instruction']
        self.retained_local_analyses = deque(maxlen=3)

        logger.info(f"FrameClassifier initialized with model: {self.model_name}")
        logger.info(f"Flag threshold: {self.flag_threshold}")

    def frame_to_jpg_bytes(self, frame: np.ndarray):
        """
        Convert OpenCV frame to JPEG byte array
        """
        # Resize frame for faster processing if too large
        max_dimension = 1280
        height, width = frame.shape[:2]

        if max(height, width) > max_dimension:
            scale = max_dimension / max(height, width)
            new_width = int(width * scale)
            new_height = int(height * scale)
            frame = cv2.resize(frame, (new_width, new_height))

        # Encode to JPEG
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 85]
        _, buffer = cv2.imencode('.jpg', frame, encode_param)
        return buffer.tobytes()



    async def classify_frame(self, frame: np.ndarray, frame_id: int, timestamp) -> FrameAnalysis:
        """
        Classify a single frame using Mistral multimodal LLM

        Args:
            frame: OpenCV frame to analyze
            frame_id: Unique frame identifier
            timestamp: Timestamp of the frame

        Returns:
            FrameAnalysis object with classification results
        """
        try:
            frame_jpg_bytes = self.frame_to_jpg_bytes(frame)


            prompt = """
You are a surveillance-scene analyzer.  
Your job is to evaluate the current camera frame in combination with the user’s monitoring instruction and the last N analysis results (temporal context).

You MUST output ONLY a valid JSON object in this exact structure:

{
  "description": "Scene description here",
  "flag_rate": 0.0,
  "context_tags": ["tag1", "tag2"]
}

--- INPUTS AVAILABLE TO YOU ---
1. user_instruction: Text explaining what the user wants monitored.
   Examples:
   - "Monitor the man in the blue shirt and ensure he does not stand up."
   - "Track if someone enters the restricted zone."
   - "Watch the right-side door and flag any unusual movement."
   - "Monitor if anyone starts running."

2. current_frame: The current surveillance image.

3. previous_analyses: Array of JSON outputs from the last 3–5 frames.
   These include: description, flag_rate, context_tags.

--- WHAT YOU MUST DO ---
1. Analyze the scene realistically based on the image.
2. Interpret the user_instruction and integrate it into your analysis.
   - If the instruction is actionable, adjust your suspicion/flag logic appropriately.
   - If the instruction is impossible, unsafe, or unrelated, default to simple anomaly detection.
3. Use previous_analyses to understand trends:
   - escalating motion
   - increasing movement in restricted area
   - loitering over time
   - repetitive behavior
   - suspicious buildup

4. flag_rate:
   - 0.0 → normal activity
   - 0.1–0.3 → mild unusual activity
   - 0.4–0.6 → moderate anomaly
   - 0.7–1.0 → critical or highly suspicious behavior

5. context_tags:
   Tags should highlight relevant concepts:
   Examples:
   ["human_motion", "loitering", "restricted_area", "rapid_movement", "interaction", "object_in_hand", "standing_up", "falling_down", "unusual_activity"]

--- STRICT RULES ---
- DO NOT output anything outside the JSON.
- DO NOT mention guidelines or reasoning.
- DO NOT reference the user inputs directly.
- DO NOT invent violent, harmful, or disciplinary actions.
- Focus ONLY on benign surveillance: detection, monitoring, anomaly scoring.
}"""

            previous_analyses = list(self.retained_local_analyses)


            messages = [
                f"This is the given User instruction:\n\n{self.surveillance_instruction}",

                types.Part.from_bytes(
                    data=frame_jpg_bytes,
                    mime_type='image/jpeg',
                ),
                        ]


            if previous_analyses:
                analyses_text = json.dumps(previous_analyses, indent=2)
                messages = [prompt, f"Previous analyses for context:\n{analyses_text}"] + messages
            else:
                messages.insert(0, prompt)



            # Call Model API
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=messages,
                config={
                    "response_mime_type": "application/json",
                    "response_json_schema": self.ClassifierResponse.model_json_schema(),
                }
            )


            result = self.ClassifierResponse.model_validate_json(response.text)
            if result:
                self.retained_local_analyses.append(result.model_dump())

                # Determine risk level
                risk_level = self._determine_risk_level(result.flag_rate)

                analysis = FrameAnalysis(
                    frame_id=frame_id,
                    timestamp=timestamp,
                    description=result.description,
                    flag_rate=result.flag_rate,
                    context_tags=result.context_tags,
                    risk_level=risk_level
                )

                logger.debug(f"Frame {frame_id} analyzed: flag_rate={result.flag_rate:.2f}")
                logger.info(analysis.to_json())
                return analysis
            else:
                raise ValueError("Invalid response from Model model")
        except Exception as e:
            logger.error(f"Error classifying frame {frame_id}: {str(e)}")
            # Return safe default
            return FrameAnalysis(
                frame_id=frame_id,
                timestamp=timestamp,
                description=f"Error analyzing frame: {str(e)}",
                flag_rate=0.0,
                context_tags=["error"],
                risk_level=RiskLevel.LOW
            )


    def _determine_risk_level(self, flag_rate: float) -> RiskLevel:
        """
        Convert flag rate to risk level category

        Args:
            flag_rate: Float between 0.0 and 1.0

        Returns:
            RiskLevel enum value
        """
        if flag_rate < 0.3:
            return RiskLevel.LOW
        elif flag_rate < 0.6:
            return RiskLevel.MEDIUM
        elif flag_rate < 0.8:
            return RiskLevel.HIGH
        return RiskLevel.CRITICAL

    def should_skip_frame(self, frame_id: int) -> bool:
        """
        Determine if frame should be skipped based on frame_skip config

        Args:
            frame_id: Current frame ID

        Returns:
            True if frame should be skipped
        """
        return frame_id % self.frame_skip != 0

    class ClassifierResponse(BaseModel):
        description: str = Field(..., description="Textual description of the frame analysis")
        flag_rate: float = Field(..., ge=0.0, le=1.0, description="Flag rate between 0.0 and 1.0 indicating risk level")
        context_tags: list[str] = Field(..., description="List of context tags relevant to the frame analysis")
