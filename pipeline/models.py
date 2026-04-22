"""
Data models for events and related structures.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any
from datetime import datetime
import uuid
import json


@dataclass
class EventMetadata:
    """Metadata for events."""
    queue_depth: Optional[int] = None
    sku_zone: Optional[str] = None
    session_seq: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class Event:
    """
    Represents a single event from the detection pipeline.
    
    Event types:
    - ENTRY: Person enters store
    - EXIT: Person leaves store
    - ZONE_ENTER: Person enters a zone
    - ZONE_EXIT: Person leaves a zone
    - ZONE_DWELL: Person has been in zone for 30+ seconds
    - BILLING_QUEUE_JOIN: Person joins billing queue
    - BILLING_QUEUE_ABANDON: Person leaves billing queue
    - REENTRY: Person re-enters store
    """
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    store_id: str = ""
    camera_id: str = ""
    visitor_id: str = ""
    event_type: str = ""
    timestamp: str = ""
    zone_id: Optional[str] = None
    dwell_ms: int = 0
    is_staff: bool = False
    confidence: float = 0.0
    metadata: EventMetadata = field(default_factory=EventMetadata)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_id": self.event_id,
            "store_id": self.store_id,
            "camera_id": self.camera_id,
            "visitor_id": self.visitor_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "zone_id": self.zone_id,
            "dwell_ms": self.dwell_ms,
            "is_staff": self.is_staff,
            "confidence": self.confidence,
            "metadata": self.metadata.to_dict()
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Event":
        """Create Event from dictionary."""
        metadata_data = data.pop("metadata", {})
        metadata = EventMetadata(**metadata_data)
        return Event(metadata=metadata, **data)


@dataclass
class SessionState:
    """Tracks state of a visitor session."""
    visitor_id: str
    track_id: int
    entry_timestamp: str
    current_zone: Optional[str] = None
    zone_enter_timestamp: Optional[str] = None
    last_dwell_emit_timestamp: Optional[str] = None
    has_exited: bool = False
    session_seq: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
