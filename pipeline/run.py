"""
Main pipeline runner: processes video frames and emits events.
Supports both real CCTV video processing and mock data generation.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from pipeline.tracker import SimpleTracker, CrossCameraTracker
from pipeline.detect import MockDetector, YOLOv8Detector, VideoProcessor, YOLO_AVAILABLE
from pipeline.emit import EventEmitter
from pipeline.models import Event


def load_store_layout(layout_file: str, store_id: str) -> Dict[str, Any]:
    """
    Load store layout configuration from JSON file.
    
    Args:
        layout_file: Path to store_layout.json
        store_id: Store identifier
    
    Returns:
        Store layout configuration
    """
    try:
        with open(layout_file, 'r') as f:
            layouts = json.load(f)
        
        if store_id not in layouts:
            raise ValueError(f"Store {store_id} not found in layout file")
        
        return layouts[store_id]
    except FileNotFoundError:
        print(f"Warning: Layout file {layout_file} not found, using default zones")
        return {
            "zones": {
                "SKINCARE": {"x1": 200, "y1": 200, "x2": 600, "y2": 600},
                "BILLING": {"x1": 800, "y1": 200, "x2": 1200, "y2": 600},
                "CHECKOUT": {"x1": 1200, "y1": 200, "x2": 1600, "y2": 600}
            },
            "cameras": {
                "CAM_ENTRY_01": {"type": "entry", "coverage": "ENTRY"},
                "CAM_FLOOR_01": {"type": "floor", "coverage": ["SKINCARE", "BILLING"]},
                "CAM_BILLING_01": {"type": "billing", "coverage": "BILLING"}
            }
        }


def convert_zones_format(zones_config: Dict[str, Dict[str, int]]) -> Dict[str, Tuple[int, int, int, int]]:
    """
    Convert zone configuration from JSON format to tuple format.
    
    Args:
        zones_config: Zones from store layout JSON
    
    Returns:
        Dict mapping zone_id to (x1, y1, x2, y2) tuple
    """
    zones = {}
    for zone_id, coords in zones_config.items():
        zones[zone_id] = (coords["x1"], coords["y1"], coords["x2"], coords["y2"])
    return zones


def run_real_pipeline(
    video_dir: str,
    output_file: str,
    store_layout_file: str,
    store_id: str = "STORE_BLR_002",
    use_cross_camera: bool = True
) -> None:
    """
    Run detection pipeline on real CCTV videos.
    
    Args:
        video_dir: Directory containing video files
        output_file: Output JSONL file for events
        store_layout_file: Path to store_layout.json
        store_id: Store identifier
        use_cross_camera: Whether to use cross-camera deduplication
    """
    if not YOLO_AVAILABLE:
        print("Warning: ultralytics not available, falling back to mock pipeline")
        return run_mock_pipeline(video_dir, output_file, store_id)
    
    print(f"Starting real pipeline for {store_id}")
    
    # Load store layout
    store_layout = load_store_layout(store_layout_file, store_id)
    zones = convert_zones_format(store_layout["zones"])
    cameras = store_layout["cameras"]
    
    print(f"Loaded layout: {len(zones)} zones, {len(cameras)} cameras")
    
    # Initialize detector and processor
    detector = YOLOv8Detector(confidence_threshold=0.3)
    processor = VideoProcessor(detector)
    
    # Initialize tracker
    if use_cross_camera:
        tracker = CrossCameraTracker(dedup_distance=100, dedup_time_window=30)
    else:
        tracker = SimpleTracker(max_distance=50, max_age=30)
    
    # Process all videos in directory
    video_results = processor.process_video_directory(video_dir, store_id)
    
    if not video_results:
        print("No video files processed")
        return
    
    print(f"Processed {len(video_results)} video files")
    
    # Process each camera's video
    all_events: List[Event] = []
    
    for camera_id, frame_results in video_results.items():
        print(f"Processing {len(frame_results)} frames from {camera_id}")
        
        # Get camera configuration
        camera_config = cameras.get(camera_id, {"type": "unknown", "coverage": []})
        
        # Determine entry zone based on camera type
        if camera_config["type"] == "entry":
            entry_zone = (0, 0, 1920, 200)  # Top of frame for entry camera
        else:
            entry_zone = None  # Non-entry cameras don't detect entry/exit
        
        # Initialize event emitter for this camera
        emitter = EventEmitter(
            store_id=store_id,
            camera_id=camera_id,
            entry_zone_bounds=entry_zone,
            zones=zones
        )
        
        # Process each frame
        for frame_idx, detections, timestamp in frame_results:
            # Convert detections to tuple format
            detection_tuples = [d.to_tuple() for d in detections]
            
            # Update tracker
            if use_cross_camera:
                tracked = tracker.update(camera_id, detection_tuples)
            else:
                tracked = tracker.update(detection_tuples)
            
            # Emit events for each tracked detection
            for track_id, detection in tracked:
                x1, y1, x2, y2, conf, cls_id = detection
                bbox = (x1, y1, x2, y2)
                
                # Determine queue depth (rough estimate based on detections in billing zone)
                queue_depth = None
                if "BILLING" in zones:
                    billing_zone = zones["BILLING"]
                    billing_detections = [
                        d for d in detections 
                        if (billing_zone[0] <= d.get_centroid()[0] <= billing_zone[2] and
                            billing_zone[1] <= d.get_centroid()[1] <= billing_zone[3])
                    ]
                    queue_depth = len(billing_detections) if billing_detections else None
                
                events = emitter.process_detection(
                    track_id=track_id,
                    bbox=bbox,
                    confidence=conf,
                    timestamp=timestamp,
                    queue_depth=queue_depth
                )
                all_events.extend(events)
    
    # Write events to JSONL file
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        for event in all_events:
            f.write(event.to_json() + '\n')
    
    print(f"Real pipeline complete: {len(all_events)} events written to {output_file}")
    
    if use_cross_camera:
        print(f"Unique visitors across all cameras: {tracker.get_unique_visitors()}")


def run_mock_pipeline(
    video_dir: str,
    output_file: str,
    store_id: str = "STORE_BLR_002",
    camera_id: str = "CAM_ENTRY_01",
    num_frames: int = 100,
    num_people: int = 3
) -> None:
    """
    Run detection pipeline with mock data (for testing).
    
    Args:
        video_dir: Directory containing video files (unused in mock mode)
        output_file: Output JSONL file for events
        store_id: Store identifier
        camera_id: Camera identifier
        num_frames: Number of frames to process (for mock detector)
        num_people: Number of people to simulate (for mock detector)
    """
    print(f"Starting mock pipeline for {store_id}")
    
    # Initialize components
    tracker = SimpleTracker(max_distance=50, max_age=30)
    detector = MockDetector(frame_width=1920, frame_height=1080)
    
    # Define zones
    zones = {
        "SKINCARE": (200, 200, 600, 600),
        "BILLING": (800, 200, 1200, 600),
        "CHECKOUT": (1200, 200, 1600, 600)
    }
    
    entry_zone = (0, 0, 1920, 200)
    
    emitter = EventEmitter(
        store_id=store_id,
        camera_id=camera_id,
        entry_zone_bounds=entry_zone,
        zones=zones
    )
    
    # Process frames
    all_events: List[Event] = []
    
    for frame_idx in range(num_frames):
        # Get detections for this frame
        detections = detector.detect(frame_idx, num_people=num_people)
        timestamp = detector.get_timestamp(frame_idx, fps=15)
        
        # Update tracker
        tracked = tracker.update([d.to_tuple() for d in detections])
        
        # Emit events for each tracked detection
        for track_id, detection in tracked:
            x1, y1, x2, y2, conf, cls_id = detection
            bbox = (x1, y1, x2, y2)
            
            events = emitter.process_detection(
                track_id=track_id,
                bbox=bbox,
                confidence=conf,
                timestamp=timestamp,
                queue_depth=None
            )
            all_events.extend(events)
    
    # Write events to JSONL file
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        for event in all_events:
            f.write(event.to_json() + '\n')
    
    print(f"Mock pipeline complete: {len(all_events)} events written to {output_file}")


def run_pipeline(
    video_dir: str,
    output_file: str,
    store_layout_file: Optional[str] = None,
    store_id: str = "STORE_BLR_002",
    use_real_detection: bool = True,
    use_cross_camera: bool = True,
    **kwargs
) -> None:
    """
    Run detection pipeline (real or mock based on availability).
    
    Args:
        video_dir: Directory containing video files
        output_file: Output JSONL file for events
        store_layout_file: Path to store_layout.json (optional)
        store_id: Store identifier
        use_real_detection: Whether to use real YOLOv8 detection
        use_cross_camera: Whether to use cross-camera deduplication
        **kwargs: Additional arguments for mock pipeline
    """
    if use_real_detection and YOLO_AVAILABLE and store_layout_file:
        run_real_pipeline(
            video_dir=video_dir,
            output_file=output_file,
            store_layout_file=store_layout_file,
            store_id=store_id,
            use_cross_camera=use_cross_camera
        )
    else:
        if use_real_detection and not YOLO_AVAILABLE:
            print("YOLOv8 not available, using mock detection")
        if use_real_detection and not store_layout_file:
            print("Store layout file not provided, using mock detection")
        
        run_mock_pipeline(
            video_dir=video_dir,
            output_file=output_file,
            store_id=store_id,
            **kwargs
        )


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run detection pipeline")
    parser.add_argument("--video-dir", default="data/videos", help="Video directory")
    parser.add_argument("--output", default="data/events.jsonl", help="Output JSONL file")
    parser.add_argument("--store-layout", help="Path to store_layout.json")
    parser.add_argument("--store-id", default="STORE_BLR_002", help="Store ID")
    parser.add_argument("--use-real", action="store_true", help="Use real YOLOv8 detection")
    parser.add_argument("--use-cross-camera", action="store_true", default=True, help="Use cross-camera deduplication")
    parser.add_argument("--camera-id", default="CAM_ENTRY_01", help="Camera ID (mock mode only)")
    parser.add_argument("--num-frames", type=int, default=100, help="Number of frames (mock mode only)")
    parser.add_argument("--num-people", type=int, default=3, help="Number of people (mock mode only)")
    
    args = parser.parse_args()
    
    run_pipeline(
        video_dir=args.video_dir,
        output_file=args.output,
        store_layout_file=args.store_layout,
        store_id=args.store_id,
        use_real_detection=args.use_real,
        use_cross_camera=args.use_cross_camera,
        camera_id=args.camera_id,
        num_frames=args.num_frames,
        num_people=args.num_people
    )
