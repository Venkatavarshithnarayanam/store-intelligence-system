"""
Event ingestion logic: validates, deduplicates, and stores events.
"""

from typing import List, Dict, Any, Optional
import json
from pipeline.models import Event, EventMetadata


class EventValidator:
    """Validates event schema and required fields."""
    
    REQUIRED_FIELDS = {
        "event_id",
        "store_id",
        "camera_id",
        "visitor_id",
        "event_type",
        "timestamp",
        "is_staff",
        "confidence"
    }
    
    VALID_EVENT_TYPES = {
        "ENTRY",
        "EXIT",
        "ZONE_ENTER",
        "ZONE_EXIT",
        "ZONE_DWELL",
        "BILLING_QUEUE_JOIN",
        "BILLING_QUEUE_ABANDON",
        "REENTRY"
    }
    
    @staticmethod
    def validate(data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate event data.
        
        Args:
            data: Event dictionary
        
        Returns:
            (is_valid, error_message)
        """
        # Check required fields
        missing = EventValidator.REQUIRED_FIELDS - set(data.keys())
        if missing:
            return False, f"Missing required fields: {missing}"
        
        # Validate event type
        if data.get("event_type") not in EventValidator.VALID_EVENT_TYPES:
            return False, f"Invalid event_type: {data.get('event_type')}"
        
        # Validate timestamp format (ISO-8601)
        timestamp = data.get("timestamp", "")
        if not timestamp.endswith("Z"):
            return False, "Timestamp must be ISO-8601 UTC (end with Z)"
        
        # Validate confidence
        confidence = data.get("confidence")
        if not isinstance(confidence, (int, float)) or not (0.0 <= confidence <= 1.0):
            return False, "Confidence must be between 0.0 and 1.0"
        
        # Validate is_staff
        if not isinstance(data.get("is_staff"), bool):
            return False, "is_staff must be boolean"
        
        return True, None
    
    @staticmethod
    def parse_event(data: Dict[str, Any]) -> Optional[Event]:
        """
        Parse event from dictionary.
        
        Args:
            data: Event dictionary
        
        Returns:
            Event object or None if invalid
        """
        is_valid, error = EventValidator.validate(data)
        if not is_valid:
            return None
        
        try:
            metadata_data = data.get("metadata", {})
            metadata = EventMetadata(**metadata_data) if metadata_data else EventMetadata()
            
            return Event(
                event_id=data["event_id"],
                store_id=data["store_id"],
                camera_id=data["camera_id"],
                visitor_id=data["visitor_id"],
                event_type=data["event_type"],
                timestamp=data["timestamp"],
                zone_id=data.get("zone_id"),
                dwell_ms=data.get("dwell_ms", 0),
                is_staff=data["is_staff"],
                confidence=data["confidence"],
                metadata=metadata
            )
        except Exception as e:
            return None


class EventIngestionService:
    """Service for ingesting events."""
    
    def __init__(self, db):
        """
        Initialize ingestion service.
        
        Args:
            db: EventDatabase instance
        """
        self.db = db
    
    def ingest_events(self, events_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Ingest batch of events.
        
        Args:
            events_data: List of event dictionaries
        
        Returns:
            Ingestion result with stats
        """
        # Validate batch size
        if len(events_data) > 500:
            return {
                "status": "error",
                "error_code": "BATCH_TOO_LARGE",
                "message": f"Batch size {len(events_data)} exceeds limit of 500",
                "events_ingested": 0,
                "duplicates": 0,
                "errors": []
            }
        
        # Parse and validate events
        events = []
        validation_errors = []
        
        for i, event_data in enumerate(events_data):
            is_valid, error = EventValidator.validate(event_data)
            if not is_valid:
                validation_errors.append({
                    "index": i,
                    "error": error
                })
                continue
            
            event = EventValidator.parse_event(event_data)
            if event:
                events.append(event)
            else:
                validation_errors.append({
                    "index": i,
                    "error": "Failed to parse event"
                })
        
        # Insert into database
        result = self.db.insert_events(events)
        
        return {
            "status": "success" if result["ingested"] > 0 else "partial",
            "events_ingested": result["ingested"],
            "duplicates": result["duplicates"],
            "validation_errors": validation_errors,
            "database_errors": result["errors"]
        }
    
    def ingest_jsonl(self, jsonl_content: str) -> Dict[str, Any]:
        """
        Ingest events from JSONL content.
        
        Args:
            jsonl_content: JSONL string (one JSON object per line)
        
        Returns:
            Ingestion result with stats
        """
        events_data = []
        parse_errors = []
        
        for line_num, line in enumerate(jsonl_content.strip().split('\n'), 1):
            if not line.strip():
                continue
            
            try:
                event_data = json.loads(line)
                events_data.append(event_data)
            except json.JSONDecodeError as e:
                parse_errors.append({
                    "line": line_num,
                    "error": str(e)
                })
        
        result = self.ingest_events(events_data)
        result["parse_errors"] = parse_errors
        
        return result
