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
        self.model_temperature = config['classifier'].get('model_temperature', 0.0)
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
You are an Elite Surveillance Intelligence Unit designed for 99% accuracy in visual threat detection.
Your role is to "distill the scene into atoms," process details in parallel, and output a definitive analysis.

Your analysis is the "Gatekeeper." If you fail to flag a critical event here, the downstream video analyzer will not trigger, and the security protocol fails. You must be precise, decisive, and highly sensitive to the User Instruction.

You MUST output ONLY a valid JSON object in this exact structure:
{
  "description": "Detailed, factual description of the scene and specific violations.",
  "flag_rate": 0.0,
  "context_tags": ["tag1", "tag2"]
}

--- INPUTS ---
1. user_instruction: The specific security protocol or rule for this camera. (e.g., "Ensure no one covers their head," "Flag exam malpractice," "Monitor for loitering").
2. current_frame: The image to analyze.
3. previous_analyses: JSON history of the last N frames.

--- INTELLIGENCE PROTOCOLS (STRICT ADHERENCE REQUIRED) ---

1. THE "SUPREME LAW" (User Instruction):
   - The user_instruction is your primary logic filter.
   - If the user says "No hats" and you see a hat, this is NOT a mild anomaly. It is a CRITICAL VIOLATION.
   - If the user says "Monitor exam" and you see glancing sideways/talking, flag it immediately.
   - **Rule:** If the instruction is violated, the `flag_rate` MUST be between 0.7 and 1.0. Do not hesitate.

2. THE "TAMPER" PROTOCOL (Camera Obstruction):
   - If the `current_frame` is pitch black, blocked, too dark to see, or shows a covered lens:
   - You MUST interpret this as a security breach (tampering or failure).
   - **Rule:** Set `flag_rate` to 0.9 or 1.0 immediately. Description: "Camera view obstructed/blinded."

3. TEMPORAL LOGIC & CONFLICT RESOLUTION:
   - Use `previous_analyses` to establish a baseline (e.g., "room was empty").
   - **Crucial:** If the `current_frame` shows a sudden violation (e.g., a person appears where they shouldn't) but the history is calm, DO NOT let the history lower your score.
   - The `current_frame` is the absolute truth. If it conflicts with history, the situation has changed. Flag the change.
   - Watch for transitions: Someone standing up, someone leaving frame, an object being picked up.

4. SCORING MATRIX (flag_rate):
   - 0.0 - 0.1: Perfect compliance. Nothing of interest.
   - 0.2 - 0.4: Minor deviations or ambiguous movement (worth noting, but not alarming).
   - 0.5 - 0.6: Suspicious behavior. Strong potential for violation.
   - 0.7 - 0.9: CONFIRMED VIOLATION of `user_instruction` or clear anomaly. (Triggers Video Analyzer).
   - 1.0: Critical Emergency, Total Camera Obstruction, or Severe Violation.

5. CONTEXT TAGS:
   - Be specific. Use tags like: "violation_confirmed", "camera_obstructed", "exam_malpractice", "head_covered", "rapid_exit", "unusual_object".

--- EXECUTION INSTRUCTION ---
Analyze the image. Compare strictly against the `user_instruction`. If the instruction is "Do not cover head" and a head is covered, that is a 0.9 flag, not a 0.5. Be smart. Be accurate.

Output ONLY the JSON.
"""

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
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_json_schema=self.ClassifierResponse.model_json_schema(),
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                    temperature=self.model_temperature
            )
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
