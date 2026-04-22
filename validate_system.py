#!/usr/bin/env python3
"""
System validation script for enhanced Store Intelligence.
Tests all components without requiring external services.
"""

import json
import tempfile
import os
from pathlib import Path

print("🔍 VALIDATING ENHANCED STORE INTELLIGENCE SYSTEM\n")

# Test 1: Core imports
print("1️⃣  Testing core imports...")
try:
    from pipeline.detect import MockDetector, Detection, YOLO_AVAILABLE
    from pipeline.tracker import SimpleTracker, CrossCameraTracker
    from pipeline.emit import EventEmitter
    from pipeline.models import Event
    from app.database import EventDatabase
    from app.ingestion import EventIngestionService
    from app.metrics import MetricsService
    from app.pos_correlation import POSCorrelationService
    from app.dashboard import DashboardService, WebDashboardGenerator
    print("✅ All core imports successful\n")
except Exception as e:
    print(f"❌ Import failed: {e}\n")
    exit(1)

# Test 2: Mock detector
print("2️⃣  Testing mock detector...")
try:
    detector = MockDetector(frame_width=1920, frame_height=1080)
    detections = detector.detect(frame_index=0, num_people=3)
    assert len(detections) == 3
    assert all(isinstance(d, Detection) for d in detections)
    print(f"✅ Mock detector works (generated {len(detections)} detections)\n")
except Exception as e:
    print(f"❌ Mock detector failed: {e}\n")
    exit(1)

# Test 3: Simple tracker
print("3️⃣  Testing simple tracker...")
try:
    tracker = SimpleTracker(max_distance=50, max_age=30)
    
    # Create mock detections
    detections = [
        (100, 100, 150, 200, 0.9, 0),
        (300, 150, 350, 250, 0.8, 0)
    ]
    
    matches = tracker.update(detections)
    assert len(matches) == 2
    assert len(tracker.tracks) == 2
    print(f"✅ Simple tracker works ({len(tracker.tracks)} active tracks)\n")
except Exception as e:
    print(f"❌ Simple tracker failed: {e}\n")
    exit(1)

# Test 4: Cross-camera tracker
print("4️⃣  Testing cross-camera tracker...")
try:
    cross_tracker = CrossCameraTracker(dedup_distance=100, dedup_time_window=30)
    
    # Camera 1 detections
    cam1_detections = [(100, 100, 150, 200, 0.9, 0), (300, 150, 350, 250, 0.8, 0)]
    matches1 = cross_tracker.update("CAM_1", cam1_detections)
    
    # Camera 2 detections (overlapping)
    cam2_detections = [(120, 110, 170, 210, 0.85, 0), (500, 200, 550, 300, 0.9, 0)]
    matches2 = cross_tracker.update("CAM_2", cam2_detections)
    
    unique_visitors = cross_tracker.get_unique_visitors()
    assert unique_visitors > 0
    print(f"✅ Cross-camera tracker works ({unique_visitors} unique visitors)\n")
except Exception as e:
    print(f"❌ Cross-camera tracker failed: {e}\n")
    exit(1)

# Test 5: Event emitter
print("5️⃣  Testing event emitter...")
try:
    zones = {
        "SKINCARE": (200, 200, 600, 600),
        "BILLING": (800, 200, 1200, 600)
    }
    entry_zone = (0, 0, 1920, 200)
    
    emitter = EventEmitter(
        store_id="STORE_BLR_002",
        camera_id="CAM_ENTRY_01",
        entry_zone_bounds=entry_zone,
        zones=zones
    )
    
    # Simulate detection in entry zone
    events = emitter.process_detection(
        track_id=1,
        bbox=(100, 50, 150, 150),
        confidence=0.9,
        timestamp="2026-04-22T10:00:00Z"
    )
    
    assert len(events) > 0
    assert events[0].event_type == "ENTRY"
    print(f"✅ Event emitter works (generated {len(events)} events)\n")
except Exception as e:
    print(f"❌ Event emitter failed: {e}\n")
    exit(1)

# Test 6: Database operations
print("6️⃣  Testing database operations...")
try:
    # Use in-memory database for testing
    db = EventDatabase(":memory:")
    
    # Create test event as Event object
    test_event = Event(
        event_id="test-123",
        store_id="STORE_BLR_002",
        camera_id="CAM_1",
        visitor_id="VIS_001",
        event_type="ENTRY",
        timestamp="2026-04-22T10:00:00Z",
        zone_id=None,
        dwell_ms=0,
        is_staff=False,
        confidence=0.9
    )
    
    # Insert event
    db.insert_event(test_event)
    
    # Query events
    events = db.get_events("STORE_BLR_002")
    assert len(events) > 0
    print(f"✅ Database works (stored and retrieved events)\n")
except Exception as e:
    print(f"❌ Database failed: {e}\n")
    exit(1)

# Test 7: Event ingestion
print("7️⃣  Testing event ingestion...")
try:
    db = EventDatabase(":memory:")
    ingestion = EventIngestionService(db)
    
    # Create test events
    test_events = [
        Event(
            event_id=f"test-{i}",
            store_id="STORE_BLR_002",
            camera_id="CAM_1",
            visitor_id=f"VIS_{i:03d}",
            event_type="ENTRY",
            timestamp="2026-04-22T10:00:00Z",
            zone_id=None,
            dwell_ms=0,
            is_staff=False,
            confidence=0.9
        )
        for i in range(5)
    ]
    
    result = ingestion.ingest_events(test_events)
    assert result['status'] in ['success', 'partial']
    assert result['events_ingested'] > 0
    print(f"✅ Event ingestion works (ingested {result['events_ingested']} events)\n")
except Exception as e:
    print(f"❌ Event ingestion failed: {e}\n")
    exit(1)

# Test 8: Metrics calculation
print("8️⃣  Testing metrics calculation...")
try:
    db = EventDatabase(":memory:")
    ingestion = EventIngestionService(db)
    metrics_service = MetricsService(db)
    
    # Create diverse test events
    test_events = [
        Event(
            event_id="e1",
            store_id="STORE_BLR_002",
            camera_id="CAM_1",
            visitor_id="VIS_001",
            event_type="ENTRY",
            timestamp="2026-04-22T10:00:00Z",
            zone_id=None,
            dwell_ms=0,
            is_staff=False,
            confidence=0.9
        ),
        Event(
            event_id="e2",
            store_id="STORE_BLR_002",
            camera_id="CAM_1",
            visitor_id="VIS_001",
            event_type="ZONE_ENTER",
            timestamp="2026-04-22T10:01:00Z",
            zone_id="SKINCARE",
            dwell_ms=0,
            is_staff=False,
            confidence=0.9
        ),
        Event(
            event_id="e3",
            store_id="STORE_BLR_002",
            camera_id="CAM_1",
            visitor_id="VIS_002",
            event_type="ENTRY",
            timestamp="2026-04-22T10:02:00Z",
            zone_id=None,
            dwell_ms=0,
            is_staff=False,
            confidence=0.9
        )
    ]
    
    ingestion.ingest_events(test_events)
    
    # Calculate metrics
    metrics = metrics_service.get_store_metrics("STORE_BLR_002")
    assert metrics['unique_visitors'] > 0
    assert 'avg_dwell_time_ms' in metrics
    print(f"✅ Metrics calculation works ({metrics['unique_visitors']} unique visitors)\n")
except Exception as e:
    print(f"❌ Metrics calculation failed: {e}\n")
    exit(1)

# Test 9: POS correlation
print("9️⃣  Testing POS correlation...")
try:
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test POS file
        pos_file = os.path.join(tmpdir, "pos.csv")
        with open(pos_file, 'w') as f:
            f.write("store_id,transaction_id,timestamp,basket_value_inr\n")
            f.write("STORE_BLR_002,TXN_001,2026-04-22T10:05:00Z,1000.00\n")
        
        pos_service = POSCorrelationService(pos_file)
        
        # Create test billing events
        billing_events = [
            {
                "visitor_id": "VIS_001",
                "timestamp": "2026-04-22T10:04:00Z",
                "zone_id": "BILLING",
                "event_type": "BILLING_QUEUE_JOIN"
            }
        ]
        
        metrics = pos_service.get_conversion_rate("STORE_BLR_002", 10, billing_events)
        assert 'conversion_rate' in metrics
        assert metrics['conversion_rate'] >= 0
        print(f"✅ POS correlation works ({metrics['conversion_rate']}% conversion rate)\n")
except Exception as e:
    print(f"❌ POS correlation failed: {e}\n")
    exit(1)

# Test 10: Dashboard service
print("🔟 Testing dashboard service...")
try:
    dashboard = DashboardService()
    
    test_metrics = {
        'unique_visitors': 150,
        'conversion_rate': 12.5,
        'avg_dwell_time_ms': 4200,
        'zones': {'SKINCARE': 85.2, 'BILLING': 45.8},
        'anomalies': [{'type': 'QUEUE_SPIKE', 'severity': 'WARN', 'message': 'Queue depth reached 6'}]
    }
    
    dashboard.update_metrics("STORE_BLR_002", test_metrics)
    
    # Test terminal display
    terminal = dashboard.get_terminal_display("STORE_BLR_002")
    assert "STORE INTELLIGENCE DASHBOARD" in terminal
    
    # Test JSON display
    json_display = dashboard.get_json_display("STORE_BLR_002")
    assert json_display['store_id'] == "STORE_BLR_002"
    
    # Test HTML generation
    html = WebDashboardGenerator.generate_html("STORE_BLR_002", test_metrics)
    assert "Store Intelligence Dashboard" in html
    
    print(f"✅ Dashboard service works (all 3 formats)\n")
except Exception as e:
    print(f"❌ Dashboard service failed: {e}\n")
    exit(1)

# Test 11: YOLOv8 availability
print("1️⃣1️⃣  Checking YOLOv8 availability...")
if YOLO_AVAILABLE:
    print("✅ YOLOv8 is available - ready for real video processing\n")
else:
    print("⚠️  YOLOv8 not available - system will use mock detection\n")
    print("   To enable real detection: pip install ultralytics\n")

# Test 12: Pipeline integration
print("1️⃣2️⃣  Testing pipeline integration...")
try:
    from pipeline.run import run_pipeline
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = os.path.join(tmpdir, "events.jsonl")
        
        # Run mock pipeline
        run_pipeline(
            video_dir="nonexistent",
            output_file=output_file,
            use_real_detection=False,
            num_frames=30,
            num_people=2
        )
        
        # Verify output
        assert os.path.exists(output_file)
        with open(output_file, 'r') as f:
            events = [json.loads(line) for line in f if line.strip()]
        
        assert len(events) > 0
        print(f"✅ Pipeline integration works (generated {len(events)} events)\n")
except Exception as e:
    print(f"❌ Pipeline integration failed: {e}\n")
    exit(1)

# Summary
print("=" * 60)
print("✅ ALL VALIDATION TESTS PASSED!")
print("=" * 60)
print("\n📊 SYSTEM STATUS:")
print("✓ Core components working")
print("✓ Detection pipeline functional")
print("✓ Tracking system operational")
print("✓ Event emission working")
print("✓ Database operations successful")
print("✓ Event ingestion functional")
print("✓ Metrics calculation working")
print("✓ POS correlation operational")
print("✓ Dashboard services functional")
print("✓ Pipeline integration complete")

if YOLO_AVAILABLE:
    print("✓ YOLOv8 real detection available")
else:
    print("⚠ YOLOv8 not available (mock detection only)")

print("\n🚀 NEXT STEPS:")
print("1. Extract dataset: unzip store-intelligence-dataset.zip -d data/")
print("2. Run pipeline: python pipeline/run.py --use-real --store-layout data/store_layout.json")
print("3. Start API: python -m uvicorn app.main:app --reload")
print("4. View dashboard: curl http://localhost:8000/stores/STORE_BLR_002/dashboard/terminal")
print("\n✨ Enhanced Store Intelligence System is ready!")
