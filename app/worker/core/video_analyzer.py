"""
Layer 2: Contextual Analyzer & Response Agent (Ported to Backend Worker)
Uses LangChain orchestration for temporal reasoning and tool invocation
"""
import asyncio
import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Literal
import logging

from google import genai
from google.genai import types
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from app.worker.models.data_models import (
    VideoSegment, AnalyzerResponse, FrameAnalysis, AlertAction
)
from app.worker.tools.alert_tools import get_alert_tools
from app.worker.utils.clip_builder import ClipBuilder
from app.worker.utils.frame_feed import FrameFeed

logger = logging.getLogger(__name__)


class VideoAnalyzer:
    """
    Contextual video analyzer using LangChain agent with tool calling.
    Performs temporal reasoning across video segments and invokes safety tools.
    """

    def __init__(self, config: Dict[str, Any], frame_feed: FrameFeed, clip_builder: ClipBuilder):
        self.config = config
        self.frame_feed = frame_feed
        self.clip_builder = clip_builder
        self.trigger_threshold = config['analyzer']['trigger_threshold']
        self.segment_duration = config['analyzer']['segment_duration']
        self.surveillance_instruction = config['surveillance']['instruction']
        self.alert_configuration = config['surveillance']['alert_configuration']


        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
             # raise ValueError("GOOGLE_API_KEY environment variable not set")
             pass

        # Initialize LLM
        self.client = genai.Client(api_key=api_key) if api_key else genai.Client()
        self.model_name = config['analyzer']['model_name']

        # Setup tools and agent
        self.tools = get_alert_tools(config)
        # self.agent_executor = "" # self._create_agent()

        logger.info(f"VideoAnalyzer initialized with {len(self.tools)} tools")

        self.sys_prompt = """
You are the SafeX Elite Video Intelligence Unit. You are the final decision-maker.
Your analysis determines whether a security protocol has been breached.

Your goal is 100% interpretative accuracy. You do not just "see" movement; you understand intent, context, and causality based strictly on the User's Instruction.

--- INPUTS PROVIDED TO YOU ---
1. video_clip: The multi-frame video data.
2. user_instruction: The specific rule or monitoring goal (e.g., "Monitor for exam malpractice," "Ensure no one covers their head").
3. alert_configuration: The user's available contact channels, phone numbers, emails, and escalation preferences.
4. trigger_reason: (Optional) Why the Image Analyzer flagged this clip initially.

--- INTELLIGENCE PROTOCOLS ---

1. THE "SUPREME LAW" (User Instruction):
   - The user_instruction is the only definition of "threat."
   - If the instruction is "No hats," and a subject wears a hat, this is a CRITICAL incident.
   - If the instruction is "Monitor for falling," and a subject trips, this is a CRITICAL incident.
   - Do not apply generic ethical filters unless the instruction requests violence. Focus on the user's specific rule.

2. THE "TAMPER/BLIND" PROTOCOL:
   - If the video is pitch black, blurred beyond recognition, or the view is obstructed:
   - You MUST classify this as `should_trigger_alert: true`.
   - Alert Level: "critical".
   - Reasoning: "Camera view is obstructed or feed is dead. Immediate maintenance required."

3. FORENSIC ANALYSIS:
   - Do not give vague summaries. Give precise, timestamped observations.
   - Look for "micro-behaviors": glancing side-to-side, hiding objects, sudden changes in pace, checking for observers.
   - Connect the dots: If someone enters empty-handed and leaves with an object, note the theft.

--- OUTPUT STRUCTURE (JSON ONLY) ---

{
  "video_analysis": "Forensic description of events. Who, what, where, when. Focus on interaction and movement.",
  "instruction_alignment": "Explicit comparison: Did the event violate the user_instruction? Quote the specific behavior that aligns or violates.",
  "should_trigger_alert": true/false,
  "alert_level": "low" | "medium" | "high" | "critical",
  "recommended_actions": [
      "Action String 1",
      "Action String 2"
  ],
  "reasoning": "Why this decision was made. If false, explain why the event was benign."
}

--- RULES FOR RECOMMENDED ACTIONS ---
- Only generate this list if `should_trigger_alert` is true.
- YOU MUST USE THE DATA FROM `alert_configuration`. Do not invent phone numbers or emails.
- If `alert_configuration` includes SMS, format as: "Send SMS to [Number]: [Short Message]".
- If `alert_configuration` includes Call, format as: "Call [Number] and report: [Speech Script]".
- If `alert_configuration` includes Email, format as: "Email [Address] with subject [Subject] and body [Summary]".
- Tailor the urgency of the action to the `alert_level`.

--- EXECUTION ---
Analyze the video. Apply the User Instruction as Law. Output the JSON.
"""

    async def analyze_segment(self, segment: VideoSegment):
        """
        Analyze a video segment using the LangChain agent

        Args:
            segment: VideoSegment containing frame analyses

        Returns:
            AnalyzerResponse with classification and actions taken
        """
        try:
            logger.info(f"Analyzing segment {segment.segment_id} "
                       f"(avg flag rate: {segment.average_flag_rate:.2f})")

            # Prepare analysis prompt
            analysis_input = self._prepare_segment_contexts(segment)

            # Call Analyser Model
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=types.Content(
                    parts=analysis_input
                ),
                config=types.GenerateContentConfig(
                    system_instruction=self.sys_prompt,
                    response_mime_type="application/json",
                    response_json_schema=self.VideoAnalyzerResponse.model_json_schema()
                )
            )

            result = self.VideoAnalyzerResponse.model_validate_json(response.text)

            # Parse agent output
            logger.info(f"Segment {segment.segment_id} analysis complete\n\n{result.model_dump_json(indent=2)}\n")

            return result


        except Exception as e:
            logger.error(f"Error analyzing segment {segment.segment_id}: {str(e)}")
            return self.VideoAnalyzerResponse(
                video_analysis="Error during analysis",
                instruction_alignment="N/A",
                should_trigger_alert=False,
                reasoning=f"Error during analysis: {str(e)}",
                alert_level=None,
                recommended_actions=None
            )

    def _prepare_segment_contexts(self, segment: VideoSegment) -> List:
        """
        Prepare comprehensive analysis input for the agent

        Args:
            segment: VideoSegment to analyze

        Returns:
            Formatted analysis prompt
        """
        first_frame = segment.frames_analysis[0]
        last_frame = segment.frames_analysis[-1]

        segment_frames_paths = self.frame_feed.get_frames_in_range(first_frame.timestamp, last_frame.timestamp)
        video_clip_path = self.clip_builder.build_clip(frame_paths=segment_frames_paths, fps=self.config['camera']['fps'])
        video_bytes = open(video_clip_path, 'rb').read()


        contact_config = f"This is the user given alert config\n\n{json.dumps(self.alert_configuration, indent=2)}"
        available_tools = f"These are the available tools description for alerting:\n\n{', '.join([tool.__doc__ for tool in self.tools])}"

        parts = [
            types.Part(text=available_tools),
            types.Part(text=contact_config),
            types.Part(text=f"This is the given User instruction:\n\n{self.surveillance_instruction}"),
            types.Part(text=f"Current System Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (Day/Night Context)"),
            types.Part(
                inline_data=types.Blob(data=video_bytes, mime_type='video/mp4')
            )
        ]



        return parts


    def should_trigger(self, segment: VideoSegment) -> bool:
        """
        Determine if segment warrants full analysis

        Args:
            segment: VideoSegment to evaluate

        Returns:
            True if analysis should be triggered
        """
        return segment.average_flag_rate >= self.trigger_threshold

    class VideoAnalyzerResponse(BaseModel):
        video_analysis: str = Field(..., description="Detailed description of video events")
        instruction_alignment: str = Field(..., description="Relation of events to user instruction")
        should_trigger_alert: bool = Field(..., description="Whether to trigger an alert")
        alert_level: Optional[Literal["low", "medium", "high", "critical"]] = Field(None, description="Alert level if triggering an alert")
        recommended_actions: Optional[List[str]] = Field(None, description="List of recommended alert actions")
        reasoning: str = Field(..., description="Justification for analysis and decisions")
