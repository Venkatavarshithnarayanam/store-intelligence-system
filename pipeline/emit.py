"""
Event emission logic: converts tracked detections into structured events.
Handles zone transitions, dwell time, staff filtering, and edge cases.
"""

from typing import List, Tuple, Optional, Dict
from datetime import datetime, timedelta
import uuid
from pipeline.models import Event, EventMetadata, SessionState


class EventEmitter:
    """
    Converts tracked detections into events.
    Manages visitor sessions and zone transitions.
    """
    
    def __init__(
        self,
        store_id: str,
        camera_id: str,
        entry_zone_bounds: Tuple[float, float, float, float],
        zones: Optional[Dict[str, Tuple[float, float, float, float]]] = None
    ):
        """
        Initialize event emitter.
        
        Args:
            store_id: Store identifier
            camera_id: Camera identifier
            entry_zone_bounds: Entry zone (x1, y1, x2, y2)
            zones: Dict of zone_id -> (x1, y1, x2, y2)
        """
        self.store_id = store_id
        self.camera_id = camera_id
        self.entry_zone_bounds = entry_zone_bounds
        self.zones = zones or {}
        
        # Track visitor sessions
        self.sessions: Dict[int, SessionState] = {}  # track_id -> SessionState
        self.visitor_ids: Dict[int, str] = {}  # track_id -> visitor_id
    
    def _get_centroid(self, bbox: Tuple[float, float, float, float]) -> Tuple[float, float]:
        """Calculate centroid from bounding box."""
        x1, y1, x2, y2 = bbox
        return ((x1 + x2) / 2, (y1 + y2) / 2)
    
    def _point_in_zone(self, point: Tuple[float, float], zone: Tuple[float, float, float, float]) -> bool:
        """Check if point is inside zone."""
        x, y = point
        x1, y1, x2, y2 = zone
        return x1 <= x <= x2 and y1 <= y <= y2
    
    def _get_current_zone(self, centroid: Tuple[float, float]) -> Optional[str]:
        """Get zone containing centroid, or None if in entry zone."""
        for zone_id, zone_bounds in self.zones.items():
            if self._point_in_zone(centroid, zone_bounds):
                return zone_id
        return None
    
    def _is_staff(self, bbox: Tuple[float, float, float, float], confidence: float) -> bool:
        """
        Heuristic staff detection.
        Staff: high confidence + tall aspect ratio
        """
        x1, y1, x2, y2 = bbox
        width = x2 - x1
        height = y2 - y1
        
        if width == 0:
            return False
        
        aspect_ratio = height / width
        
        # Staff: confidence > 0.9 AND aspect ratio > 2.0
        return confidence > 0.9 and aspect_ratio > 2.0
    
    def _calculate_dwell_ms(self, start_time: str, end_time: str) -> int:
        """Calculate dwell time in milliseconds."""
        try:
            start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            delta = end - start
            return int(delta.total_seconds() * 1000)
        except:
            return 0
    
    def process_detection(
        self,
        track_id: int,
        bbox: Tuple[float, float, float, float],
        confidence: float,
        timestamp: str,
        queue_depth: Optional[int] = None
    ) -> List[Event]:
        """
        Process a detection and emit events.
        
        Args:
            track_id: Unique track ID from tracker
            bbox: Bounding box (x1, y1, x2, y2)
            confidence: Detection confidence
            timestamp: ISO-8601 timestamp
            queue_depth: Queue depth if in billing zone
        
        Returns:
            List of events to emit
        """
        events = []
        centroid = self._get_centroid(bbox)
        is_staff = self._is_staff(bbox, confidence)
        current_zone = self._get_current_zone(centroid)
        in_entry_zone = self._point_in_zone(centroid, self.entry_zone_bounds)
        
        # Initialize session if new track
        if track_id not in self.sessions:
            visitor_id = f"VIS_{str(uuid.uuid4())[:8].upper()}"
            self.sessions[track_id] = SessionState(
                visitor_id=visitor_id,
                track_id=track_id,
                entry_timestamp=timestamp
            )
            self.visitor_ids[track_id] = visitor_id
        
        session = self.sessions[track_id]
        visitor_id = session.visitor_id
        
        # ENTRY event: first time in entry zone
        if in_entry_zone and not session.has_exited and session.current_zone is None:
            session.session_seq += 1
            events.append(Event(
                event_id=str(uuid.uuid4()),
                store_id=self.store_id,
                camera_id=self.camera_id,
                visitor_id=visitor_id,
                event_type="ENTRY",
                timestamp=timestamp,
                zone_id=None,
                dwell_ms=0,
                is_staff=is_staff,
                confidence=confidence,
                metadata=EventMetadata(session_seq=session.session_seq)
            ))
        
        # REENTRY event: re-entering after exit
        if in_entry_zone and session.has_exited and current_zone is None:
            session.has_exited = False
            session.session_seq += 1
            events.append(Event(
                event_id=str(uuid.uuid4()),
                store_id=self.store_id,
                camera_id=self.camera_id,
                visitor_id=visitor_id,
                event_type="REENTRY",
                timestamp=timestamp,
                zone_id=None,
                dwell_ms=0,
                is_staff=is_staff,
                confidence=confidence,
                metadata=EventMetadata(session_seq=session.session_seq)
            ))
        
        # ZONE_ENTER event: entering a zone
        if current_zone and session.current_zone != current_zone:
            session.current_zone = current_zone
            session.zone_enter_timestamp = timestamp
            session.session_seq += 1
            
            events.append(Event(
                event_id=str(uuid.uuid4()),
                store_id=self.store_id,
                camera_id=self.camera_id,
                visitor_id=visitor_id,
                event_type="ZONE_ENTER",
                timestamp=timestamp,
                zone_id=current_zone,
                dwell_ms=0,
                is_staff=is_staff,
                confidence=confidence,
                metadata=EventMetadata(sku_zone=current_zone, session_seq=session.session_seq)
            ))
            
            # BILLING_QUEUE_JOIN if in billing zone with queue
            if current_zone == "BILLING" and queue_depth is not None and queue_depth > 0:
                session.session_seq += 1
                events.append(Event(
                    event_id=str(uuid.uuid4()),
                    store_id=self.store_id,
                    camera_id=self.camera_id,
                    visitor_id=visitor_id,
                    event_type="BILLING_QUEUE_JOIN",
                    timestamp=timestamp,
                    zone_id="BILLING",
                    dwell_ms=0,
                    is_staff=is_staff,
                    confidence=confidence,
                    metadata=EventMetadata(queue_depth=queue_depth, session_seq=session.session_seq)
                ))
        
        # ZONE_DWELL event: every 30 seconds in zone
        if current_zone and session.zone_enter_timestamp:
            dwell_ms = self._calculate_dwell_ms(session.zone_enter_timestamp, timestamp)
            
            # Emit dwell every 30 seconds
            if dwell_ms >= 30000:
                if session.last_dwell_emit_timestamp is None or \
                   self._calculate_dwell_ms(session.last_dwell_emit_timestamp, timestamp) >= 30000:
                    session.session_seq += 1
                    session.last_dwell_emit_timestamp = timestamp
                    
                    events.append(Event(
                        event_id=str(uuid.uuid4()),
                        store_id=self.store_id,
                        camera_id=self.camera_id,
                        visitor_id=visitor_id,
                        event_type="ZONE_DWELL",
                        timestamp=timestamp,
                        zone_id=current_zone,
                        dwell_ms=dwell_ms,
                        is_staff=is_staff,
                        confidence=confidence,
                        metadata=EventMetadata(sku_zone=current_zone, session_seq=session.session_seq)
                    ))
        
        # ZONE_EXIT event: leaving a zone
        if session.current_zone and not current_zone:
            exiting_zone = session.current_zone
            session.current_zone = None
            session.zone_enter_timestamp = None
            session.last_dwell_emit_timestamp = None
            session.session_seq += 1
            
            events.append(Event(
                event_id=str(uuid.uuid4()),
                store_id=self.store_id,
                camera_id=self.camera_id,
                visitor_id=visitor_id,
                event_type="ZONE_EXIT",
                timestamp=timestamp,
                zone_id=exiting_zone,
                dwell_ms=0,
                is_staff=is_staff,
                confidence=confidence,
                metadata=EventMetadata(sku_zone=exiting_zone, session_seq=session.session_seq)
            ))
            
            # BILLING_QUEUE_ABANDON if leaving billing zone
            if exiting_zone == "BILLING":
                session.session_seq += 1
                events.append(Event(
                    event_id=str(uuid.uuid4()),
                    store_id=self.store_id,
                    camera_id=self.camera_id,
                    visitor_id=visitor_id,
                    event_type="BILLING_QUEUE_ABANDON",
                    timestamp=timestamp,
                    zone_id="BILLING",
                    dwell_ms=0,
                    is_staff=is_staff,
                    confidence=confidence,
                    metadata=EventMetadata(session_seq=session.session_seq)
                ))
        
        # EXIT event: leaving entry zone after being inside
        if not in_entry_zone and not session.has_exited and session.current_zone is None:
            session.has_exited = True
            session.session_seq += 1
            
            events.append(Event(
                event_id=str(uuid.uuid4()),
                store_id=self.store_id,
                camera_id=self.camera_id,
                visitor_id=visitor_id,
                event_type="EXIT",
                timestamp=timestamp,
                zone_id=None,
                dwell_ms=0,
                is_staff=is_staff,
                confidence=confidence,
                metadata=EventMetadata(session_seq=session.session_seq)
            ))
        
        return events
    
    def cleanup_session(self, track_id: int) -> None:
        """Remove session when track is deleted."""
        if track_id in self.sessions:
            del self.sessions[track_id]
        if track_id in self.visitor_ids:
            del self.visitor_ids[track_id]
    
    def get_session(self, track_id: int) -> Optional[SessionState]:
        """Get session state for a track."""
        return self.sessions.get(track_id)
