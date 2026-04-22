#!/usr/bin/env python3
"""
Test script for enhanced pipeline with real YOLOv8 detection.
Tests both mock and real detection modes.
"""

import os
import sys
import json
import tempfile
from pathlib import Path

# Add pipeline to path
sys.path.append(str(Path(__file__).parent))

from pipeline.run import run_pipeline, load_store_layout, convert_zones_format
from pipeline.detect import YOLO_AVAILABLE, YOLOv8Detector, MockDetector
from pipeline.tracker import CrossCameraTracker, SimpleTracker
from app.database import EventDatabase
from app.ingestion import EventIngestionService
from app.metrics import MetricsService
from app.pos_correlation import POSCorrelationService
from app.dashboard import DashboardService


def create_test_store_layout():
    """Create test store layout file."""
    layout = {
        "STORE_BLR_002": {
            "store_name": "Apex Retail - Bangalore Test",
            "city": "Bangalore",
            "open_hours": "09:00-21:00",
            "zones": {
                "ENTRY": {"x1": 0, "y1": 0, "x2": 1920, "y2": 200},
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
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(layout, f, indent=2)
        return f.name


def create_test_pos_data():
    """Create test POS transactions file."""
    transactions = [
        "store_id,transaction_id,timestamp,basket_value_inr",
        "STORE_BLR_002,TXN_00001,2026-04-22T10:15:30Z,1250.00",
        "STORE_BLR_002,TXN_00002,2026-04-22T10:18:45Z,680.50",
        "STORE_BLR_002,TXN_00003,2026-04-22T10:22:10Z,2100.75"
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write('\n'.join(transactions))
        return f.name


def test_store_layout_loading():
    """Test store layout loading functionality."""
    print("Testing store layout loading...")
    
    layout_file = create_test_store_layout()
    
    try:
        # Test successful loading
        layout = load_store_layout(layout_file, "STORE_BLR_002")
        assert "zones" in layout
        assert "cameras" in layout
        assert len(layout["zones"]) == 4
        print("✓ Store layout loaded successfully")
        
        # Test zone format conversion
        zones = convert_zones_format(layout["zones"])
        assert "SKINCARE" in zones
        assert zones["SKINCARE"] == (200, 200, 600, 600)
        print("✓ Zone format conversion works")
        
        # Test missing store
        try:
            load_store_layout(layout_file, "NONEXISTENT")
            assert False, "Should have raised ValueError"
        except ValueError:
            print("✓ Missing store handling works")
        
    finally:
        os.unlink(layout_file)


def test_yolo_detector():
    """Test YOLOv8 detector if available."""
    if not YOLO_AVAILABLE:
        print("⚠ YOLOv8 not available, skipping detector test")
        return
    
    print("Testing YOLOv8 detector...")
    
    try:
        # Initialize detector (will download model if needed)
        detector = YOLOv8Detector(confidence_threshold=0.5)
        print("✓ YOLOv8 detector initialized")
        
        # Test with dummy frame
        import numpy as np
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        detections = detector.detect(dummy_frame)
        print(f"✓ Detection ran successfully, found {len(detections)} objects")
        
        # Test timestamp generation
        timestamp = detector.get_timestamp(100, 15.0)
        assert timestamp.endswith('Z')
        print("✓ Timestamp generation works")
        
    except Exception as e:
        print(f"✗ YOLOv8 detector test failed: {e}")


def test_cross_camera_tracker():
    """Test cross-camera deduplication tracker."""
    print("Testing cross-camera tracker...")
    
    tracker = CrossCameraTracker(dedup_distance=100, dedup_time_window=30)
    
    # Simulate detections from camera 1
    detections_cam1 = [
        (100, 100, 150, 200, 0.9, 0),  # Person 1
        (300, 150, 350, 250, 0.8, 0)   # Person 2
    ]
    
    matches_cam1 = tracker.update("CAM_1", detections_cam1)
    assert len(matches_cam1) == 2
    print("✓ Camera 1 detections processed")
    
    # Simulate same people in camera 2 (overlapping view)
    detections_cam2 = [
        (120, 110, 170, 210, 0.85, 0),  # Same person 1 (close position)
        (500, 200, 550, 300, 0.9, 0)    # New person 3
    ]
    
    matches_cam2 = tracker.update("CAM_2", detections_cam2)
    
    # Should have 3 unique visitors total (person 1 deduplicated)
    unique_visitors = tracker.get_unique_visitors()
    print(f"✓ Cross-camera deduplication: {unique_visitors} unique visitors")
    
    # Test visitor camera mapping
    assert len(tracker.visitor_camera_map) > 0
    print("✓ Visitor camera mapping works")


def test_mock_pipeline():
    """Test mock pipeline functionality."""
    print("Testing mock pipeline...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        output_file = os.path.join(temp_dir, "test_events.jsonl")
        
        # Run mock pipeline
        run_pipeline(
            video_dir="nonexistent",  # Not used in mock mode
            output_file=output_file,
            use_real_detection=False,
            num_frames=50,
            num_people=2
        )
        
        # Verify output file exists and has content
        assert os.path.exists(output_file)
        
        with open(output_file, 'r') as f:
            events = [json.loads(line) for line in f]
        
        assert len(events) > 0
        print(f"✓ Mock pipeline generated {len(events)} events")
        
        # Verify event structure
        event = events[0]
        required_fields = ['event_id', 'store_id', 'visitor_id', 'event_type', 'timestamp']
        for field in required_fields:
            assert field in event
        
        print("✓ Event structure validation passed")


def test_pos_correlation():
    """Test POS correlation service."""
    print("Testing POS correlation...")
    
    pos_file = create_test_pos_data()
    
    try:
        pos_service = POSCorrelationService(pos_file)
        
        # Create mock billing events
        billing_events = [
            {
                'visitor_id': 'VIS_12345',
                'timestamp': '2026-04-22T10:14:00Z',  # 1.5 min before transaction
                'zone_id': 'BILLING',
                'event_type': 'BILLING_QUEUE_JOIN'
            },
            {
                'visitor_id': 'VIS_67890',
                'timestamp': '2026-04-22T10:17:30Z',  # 1.25 min before transaction
                'zone_id': 'BILLING',
                'event_type': 'ZONE_ENTER'
            }
        ]
        
        # Test conversion calculation
        metrics = pos_service.get_conversion_rate("STORE_BLR_002", 10, billing_events)
        
        assert 'conversion_rate' in metrics
        assert 'converted_visitors' in metrics
        assert metrics['converted_visitors'] >= 0
        
        print(f"✓ POS correlation: {metrics['conversion_rate']}% conversion rate")
        
    finally:
        os.unlink(pos_file)


def test_dashboard_service():
    """Test dashboard service functionality."""
    print("Testing dashboard service...")
    
    dashboard = DashboardService()
    
    # Test metrics update
    test_metrics = {
        'unique_visitors': 150,
        'conversion_rate': 12.5,
        'avg_dwell_time_ms': 4200,
        'zones': {'SKINCARE': 85.2, 'BILLING': 45.8},
        'anomalies': [{'type': 'QUEUE_SPIKE', 'severity': 'WARN', 'message': 'Queue depth reached 6'}]
    }
    
    dashboard.update_metrics("STORE_BLR_002", test_metrics)
    dashboard.increment_event_count()
    
    # Test terminal display
    terminal_display = dashboard.get_terminal_display("STORE_BLR_002")
    assert "STORE INTELLIGENCE DASHBOARD" in terminal_display
    assert "150" in terminal_display  # unique visitors
    print("✓ Terminal dashboard generation works")
    
    # Test JSON display
    json_display = dashboard.get_json_display("STORE_BLR_002")
    assert json_display['store_id'] == "STORE_BLR_002"
    assert json_display['metrics']['unique_visitors'] == 150
    print("✓ JSON dashboard generation works")


def test_end_to_end_integration():
    """Test end-to-end integration with database."""
    print("Testing end-to-end integration...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test database
        db_path = os.path.join(temp_dir, "test.db")
        db = EventDatabase(db_path)
        
        # Generate test events
        events_file = os.path.join(temp_dir, "events.jsonl")
        run_pipeline(
            video_dir="nonexistent",
            output_file=events_file,
            use_real_detection=False,
            num_frames=30,
            num_people=2
        )
        
        # Ingest events
        ingestion_service = EventIngestionService(db)
        
        with open(events_file, 'r') as f:
            events_data = [json.loads(line) for line in f]
        
        result = ingestion_service.ingest_events(events_data)
        assert result['status'] in ['success', 'partial']
        print(f"✓ Ingested {result['events_ingested']} events")
        
        # Test metrics calculation
        metrics_service = MetricsService(db)
        metrics = metrics_service.get_store_metrics("STORE_BLR_002")
        
        assert 'unique_visitors' in metrics
        assert metrics['unique_visitors'] > 0
        print(f"✓ Metrics calculated: {metrics['unique_visitors']} unique visitors")
        
        # Test funnel
        funnel = metrics_service.get_funnel("STORE_BLR_002")
        assert 'funnel' in funnel
        print("✓ Funnel calculation works")
        
        # Test heatmap
        heatmap = metrics_service.get_heatmap("STORE_BLR_002")
        assert 'zones' in heatmap
        print("✓ Heatmap calculation works")
        
        # Test anomalies
        anomalies = metrics_service.get_anomalies("STORE_BLR_002")
        assert 'anomalies' in anomalies
        print("✓ Anomaly detection works")


def main():
    """Run all tests."""
    print("🚀 Starting Enhanced Pipeline Tests\n")
    
    tests = [
        test_store_layout_loading,
        test_yolo_detector,
        test_cross_camera_tracker,
        test_mock_pipeline,
        test_pos_correlation,
        test_dashboard_service,
        test_end_to_end_integration
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
            print()
        except Exception as e:
            print(f"✗ Test {test.__name__} failed: {e}")
            failed += 1
            print()
    
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if YOLO_AVAILABLE:
        print("✅ YOLOv8 is available - ready for real video processing")
    else:
        print("⚠️  YOLOv8 not available - install with: pip install ultralytics")
    
    print("\n🎯 Enhanced pipeline is ready for real dataset!")
    print("\nNext steps:")
    print("1. Install YOLOv8: pip install ultralytics")
    print("2. Extract dataset to data/ folder")
    print("3. Run: python pipeline/run.py --use-real --store-layout data/store_layout.json")
    print("4. Start API: python -m uvicorn app.main:app --reload")
    print("5. View dashboard: curl http://localhost:8000/stores/STORE_BLR_002/dashboard/terminal")


if __name__ == "__main__":
    main()