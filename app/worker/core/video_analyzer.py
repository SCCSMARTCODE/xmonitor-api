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
You are the Video Analysis Agent for the SafeX platform.

Your core responsibilities:
1. Analyze the full multi-frame video clip provided.
2. Understand and interpret the user's monitoring instruction exactly as given.
3. Produce a complete, human-level description of all relevant events in the video.
4. Compare the events against the user's instruction to determine their significance.
5. Decide whether the situation requires escalation to the alert system.
6. If escalation is required, specify exactly what steps the alert engine should take.
7. You do NOT execute tools. You only analyze, decide, and recommend.

Your output MUST include the following fields:

1. **video_analysis**  
   A full, detailed, human-level description of what occurs in the video, including movement, interactions, objects, people, timing, and any relevant observations.

2. **instruction_alignment**  
   A clear explanation of how the observed events relate to the user's instruction.  
   - What part of the instruction is relevant?  
   - Does the event violate a rule?  
   - Does it match a risk pattern the user cares about?

3. **should_trigger_alert** (boolean)  
   - true = the alert system should take action  
   - false = no action needed  

4. **alert_level**  
   ONLY provided when should_trigger_alert = true.  
   One of:
   - "low"
   - "medium"
   - "high"
   - "critical"

5. recommended_actions
   A list of explicit action strings describing exactly what the alert engine should do.
   Only include this when should_trigger_alert = true.
   Each string must be a clear, executable, human-readable instruction, such as:
   - “Call +2348100000000 immediately and report that the subject has collapsed.”
   - “Send an SMS to +2347039876543: 'Unauthorized individual entered restricted zone B.’”
   - “Log this event with severity CRITICAL including full timeline summary.”
   - “Trigger perimeter-alarm A3 for 10 seconds.”
   - “Email security-admin@safex.com with full incident reasoning.”
   You must use the user’s alert configuration and constraints to determine which channels
   are allowed, which contacts should be used, and what escalation rules apply.

6. **reasoning**  
   A brief but explicit justification explaining:
   - why escalation is or is not needed,  
   - why the chosen alert level is appropriate,  
   - and why the recommended actions are correct.

Important principles:
- You do NOT assume any predefined threat categories. The user's instruction is the only source of truth.
- You must be precise, avoid false alarms, and consider context deeply.
- You analyze temporal patterns, not single frames.
- Always respect the user's monitoring goals, thresholds, and alert preferences.
- You do NOT call tools directly.
- You only output structured analysis + recommended actions.

Your thinking process:
1. Read and internalize the user's instruction.  
2. Analyze the entire video holistically.  
3. Identify key events, behaviors, and temporal patterns.  
4. Evaluate relevance to the instruction.  
5. Decide if escalation is necessary.  
6. If escalation is necessary, design a clear and correct alert plan.  
7. Output the final structured result.
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
