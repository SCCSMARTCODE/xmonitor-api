"""
Data models for SafeX Worker (Ported from Agent)
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
import json


class RiskLevel(Enum):
    """Risk level classification for frame analysis"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertAction(Enum):
    """Types of alert actions"""
    SMS = "sms"
    EMAIL = "email"
    API_SYNC = "api_sync"
    LOG = "log"
    CALL = "call"


@dataclass
class FrameAnalysis:
    """Analysis result for a single frame"""
    frame_id: int
    timestamp: datetime
    description: str
    flag_rate: float
    context_tags: List[str]
    risk_level: RiskLevel

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "frame_id": self.frame_id,
            "timestamp": self.timestamp.isoformat(),
            "description": self.description,
            "flag_rate": self.flag_rate,
            "context_tags": self.context_tags,
            "risk_level": self.risk_level.value
        }

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())


@dataclass
class VideoSegment:
    """Represents a segment of video for analysis"""
    segment_id: str
    start_frame: int
    end_frame: int
    start_time: datetime
    end_time: datetime
    frames_analysis: List[FrameAnalysis]
    average_flag_rate: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "segment_id": self.segment_id,
            "start_frame": self.start_frame,
            "end_frame": self.end_frame,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "frames_count": len(self.frames_analysis),
            "average_flag_rate": self.average_flag_rate
        }


@dataclass
class AnalyzerResponse:
    """Response from the video analyzer agent"""
    segment_id: str
    classification: str
    confidence: float
    actions_taken: List[str]
    timestamp: datetime
    reasoning: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "segment_id": self.segment_id,
            "classification": self.classification,
            "confidence": self.confidence,
            "actions_taken": self.actions_taken,
            "timestamp": self.timestamp.isoformat(),
            "reasoning": self.reasoning,
            "metadata": self.metadata
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


@dataclass
class AlertEvent:
    """Alert event to be processed"""
    event_id: str
    timestamp: datetime
    risk_level: RiskLevel
    description: str
    segment: VideoSegment
    actions: List[AlertAction]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "risk_level": self.risk_level.value,
            "description": self.description,
            "segment": self.segment.to_dict(),
            "actions": [action.value for action in self.actions],
            "metadata": self.metadata
        }
