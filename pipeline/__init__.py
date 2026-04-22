"""Pipeline package for detection and event emission."""

from pipeline.tracker import SimpleTracker, Track
from pipeline.detect import MockDetector, YOLOv8Detector, Detection
from pipeline.emit import EventEmitter
from pipeline.models import Event, EventMetadata, SessionState

__all__ = [
    "SimpleTracker",
    "Track",
    "MockDetector",
    "YOLOv8Detector",
    "Detection",
    "EventEmitter",
    "Event",
    "EventMetadata",
    "SessionState",
]
