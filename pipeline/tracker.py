"""
Simple centroid-based object tracker for visitor tracking.
Assigns unique IDs to detections and maintains them across frames.
Supports cross-camera deduplication to avoid counting same person twice.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Set
import math
from datetime import datetime, timedelta


@dataclass
class Track:
    """Represents a tracked object (visitor)."""
    track_id: int
    centroid: Tuple[float, float]
    age: int = 1
    max_age: int = 30
    camera_id: str = ""
    last_seen: datetime = field(default_factory=datetime.utcnow)
    confidence_history: List[float] = field(default_factory=list)
    
    def is_stale(self) -> bool:
        """Check if track should be removed."""
        return self.age > self.max_age
    
    def update_centroid(self, centroid: Tuple[float, float], confidence: float = 0.0) -> None:
        """Update centroid and increment age."""
        self.centroid = centroid
        self.age += 1
        self.last_seen = datetime.utcnow()
        
        # Keep confidence history for staff detection
        self.confidence_history.append(confidence)
        if len(self.confidence_history) > 10:
            self.confidence_history.pop(0)
    
    def increment_age(self) -> None:
        """Increment age without updating centroid (track not seen this frame)."""
        self.age += 1
    
    def get_avg_confidence(self) -> float:
        """Get average confidence over recent detections."""
        return sum(self.confidence_history) / len(self.confidence_history) if self.confidence_history else 0.0


class CrossCameraTracker:
    """
    Multi-camera tracker that deduplicates visitors across camera views.
    Maintains global visitor IDs across all cameras in a store.
    """
    
    def __init__(self, dedup_distance: float = 100.0, dedup_time_window: int = 30):
        """
        Initialize cross-camera tracker.
        
        Args:
            dedup_distance: Max distance to consider same person across cameras (pixels)
            dedup_time_window: Time window for cross-camera deduplication (seconds)
        """
        self.dedup_distance = dedup_distance
        self.dedup_time_window = dedup_time_window
        self.global_tracks: Dict[int, Track] = {}  # Global track ID -> Track
        self.camera_trackers: Dict[str, SimpleTracker] = {}  # Camera ID -> Tracker
        self.next_global_id = 1
        self.visitor_camera_map: Dict[int, Set[str]] = {}  # Global ID -> Set of camera IDs
    
    def get_camera_tracker(self, camera_id: str) -> 'SimpleTracker':
        """Get or create tracker for specific camera."""
        if camera_id not in self.camera_trackers:
            self.camera_trackers[camera_id] = SimpleTracker(max_distance=50, max_age=30)
        return self.camera_trackers[camera_id]
    
    def _find_cross_camera_match(self, track: Track, camera_id: str) -> Optional[int]:
        """
        Find if this track matches an existing global track from another camera.
        
        Args:
            track: Track to match
            camera_id: Current camera ID
        
        Returns:
            Global track ID if match found, None otherwise
        """
        current_time = datetime.utcnow()
        
        for global_id, global_track in self.global_tracks.items():
            # Skip if same camera
            if global_track.camera_id == camera_id:
                continue
            
            # Check time window
            time_diff = (current_time - global_track.last_seen).total_seconds()
            if time_diff > self.dedup_time_window:
                continue
            
            # Check distance (rough approximation across cameras)
            distance = math.sqrt(
                (track.centroid[0] - global_track.centroid[0]) ** 2 +
                (track.centroid[1] - global_track.centroid[1]) ** 2
            )
            
            if distance < self.dedup_distance:
                return global_id
        
        return None
    
    def update(self, camera_id: str, detections: List[Tuple[float, float, float, float, float, int]]) -> List[Tuple[int, Tuple[float, float, float, float, float, int]]]:
        """
        Update tracker with detections from specific camera.
        
        Args:
            camera_id: Camera identifier
            detections: List of (x1, y1, x2, y2, confidence, class_id)
        
        Returns:
            List of (global_track_id, detection) for matched detections
        """
        # Get camera-specific tracker
        camera_tracker = self.get_camera_tracker(camera_id)
        
        # Update camera tracker
        camera_matches = camera_tracker.update(detections)
        
        global_matches = []
        
        for local_track_id, detection in camera_matches:
            x1, y1, x2, y2, conf, cls_id = detection
            centroid = ((x1 + x2) / 2, (y1 + y2) / 2)
            
            # Get local track
            local_track = camera_tracker.tracks[local_track_id]
            
            # Check for cross-camera match
            global_id = self._find_cross_camera_match(local_track, camera_id)
            
            if global_id is None:
                # Create new global track
                global_id = self.next_global_id
                self.next_global_id += 1
                
                self.global_tracks[global_id] = Track(
                    track_id=global_id,
                    centroid=centroid,
                    camera_id=camera_id,
                    confidence_history=[conf]
                )
                self.visitor_camera_map[global_id] = {camera_id}
            else:
                # Update existing global track
                self.global_tracks[global_id].update_centroid(centroid, conf)
                self.global_tracks[global_id].camera_id = camera_id  # Update to current camera
                self.visitor_camera_map[global_id].add(camera_id)
            
            global_matches.append((global_id, detection))
        
        # Clean up stale global tracks
        current_time = datetime.utcnow()
        stale_ids = []
        for global_id, track in self.global_tracks.items():
            time_diff = (current_time - track.last_seen).total_seconds()
            if time_diff > 300:  # 5 minutes
                stale_ids.append(global_id)
        
        for global_id in stale_ids:
            del self.global_tracks[global_id]
            if global_id in self.visitor_camera_map:
                del self.visitor_camera_map[global_id]
        
        return global_matches
    
    def get_unique_visitors(self) -> int:
        """Get count of unique visitors across all cameras."""
        return len(self.global_tracks)
    
    def reset(self) -> None:
        """Reset all tracker state."""
        self.global_tracks.clear()
        self.camera_trackers.clear()
        self.visitor_camera_map.clear()
        self.next_global_id = 1


class SimpleTracker:
    """
    Centroid-based tracker for assigning unique IDs to detections.
    
    Algorithm:
    1. For each detection, find closest track within distance threshold
    2. If found, update that track's centroid
    3. If not found, create new track
    4. Remove stale tracks (age > max_age)
    """
    
    def __init__(self, max_distance: float = 50.0, max_age: int = 30):
        """
        Initialize tracker.
        
        Args:
            max_distance: Max centroid distance to match detection to track (pixels)
            max_age: Max frames a track can exist without being seen
        """
        self.max_distance = max_distance
        self.max_age = max_age
        self.tracks: dict[int, Track] = {}
        self.next_track_id = 1
    
    def _centroid_distance(self, c1: Tuple[float, float], c2: Tuple[float, float]) -> float:
        """Calculate Euclidean distance between two centroids."""
        return math.sqrt((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2)
    
    def _get_centroid(self, bbox: Tuple[float, float, float, float]) -> Tuple[float, float]:
        """Calculate centroid from bounding box (x1, y1, x2, y2)."""
        x1, y1, x2, y2 = bbox
        return ((x1 + x2) / 2, (y1 + y2) / 2)
    
    def update(self, detections: List[Tuple[float, float, float, float, float, int]]) -> List[Tuple[int, Tuple[float, float, float, float, float, int]]]:
        """
        Update tracker with new detections.
        
        Args:
            detections: List of (x1, y1, x2, y2, confidence, class_id)
        
        Returns:
            List of (track_id, detection) for matched detections
        """
        # Increment age for all existing tracks (they weren't seen this frame yet)
        for track in self.tracks.values():
            track.increment_age()
        
        matched_detections = []
        used_track_ids = set()
        
        # Match detections to existing tracks
        for detection in detections:
            x1, y1, x2, y2, conf, cls_id = detection
            centroid = self._get_centroid((x1, y1, x2, y2))
            
            # Find closest track
            best_track_id = None
            best_distance = self.max_distance
            
            for track_id, track in self.tracks.items():
                if track_id in used_track_ids:
                    continue
                
                distance = self._centroid_distance(centroid, track.centroid)
                if distance < best_distance:
                    best_distance = distance
                    best_track_id = track_id
            
            # Update track or create new one
            if best_track_id is not None:
                self.tracks[best_track_id].update_centroid(centroid)
                used_track_ids.add(best_track_id)
                matched_detections.append((best_track_id, detection))
            else:
                # Create new track
                new_track_id = self.next_track_id
                self.next_track_id += 1
                self.tracks[new_track_id] = Track(
                    track_id=new_track_id,
                    centroid=centroid,
                    max_age=self.max_age
                )
                matched_detections.append((new_track_id, detection))
        
        # Remove stale tracks
        stale_ids = [tid for tid, track in self.tracks.items() if track.is_stale()]
        for tid in stale_ids:
            del self.tracks[tid]
        
        return matched_detections
    
    def get_active_tracks(self) -> dict[int, Track]:
        """Get all active tracks."""
        return self.tracks.copy()
    
    def reset(self) -> None:
        """Reset tracker state."""
        self.tracks.clear()
        self.next_track_id = 1
