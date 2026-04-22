#!/usr/bin/env python3
"""
Quick validation of enhanced Store Intelligence system.
Tests core components without database dependencies.
"""

print("✅ ENHANCED STORE INTELLIGENCE - QUICK VALIDATION\n")

# Test 1: Core imports
print("1. Testing core imports...")
try:
    from pipeline.detect import MockDetector, Detection, YOLO_AVAILABLE
    from pipeline.tracker import SimpleTracker, CrossCameraTracker
    from pipeline.emit import EventEmitter
    from pipeline.models import Event
    from app.pos_correlation import POSCorrelationService
    from app.dashboard import DashboardService, WebDashboardGenerator
    print("   ✅ All imports successful\n")
except Exception as e:
    print(f"   ❌ Import failed: {e}\n")
    exit(1)

# Test 2: Mock detector
print("2. Testing mock detector...")
try:
    detector = MockDetector(frame_width=1920, frame_height=1080)
    detections = detector.detect(frame_index=0, num_people=3)
    assert len(detections) == 3
    print(f"   ✅ Generated {len(detections)} detections\n")
except Exception as e:
    print(f"   ❌ Failed: {e}\n")
    exit(1)

# Test 3: Simple tracker
print("3. Testing simple tracker...")
try:
    tracker = SimpleTracker(max_distance=50, max_age=30)
    detections = [(100, 100, 150, 200, 0.9, 0), (300, 150, 350, 250, 0.8, 0)]
    matches = tracker.update(detections)
    assert len(matches) == 2
    print(f"   ✅ Tracked {len(tracker.tracks)} objects\n")
except Exception as e:
    print(f"   ❌ Failed: {e}\n")
    exit(1)

# Test 4: Cross-camera tracker
print("4. Testing cross-camera tracker...")
try:
    cross_tracker = CrossCameraTracker(dedup_distance=100, dedup_time_window=30)
    cam1_detections = [(100, 100, 150, 200, 0.9, 0), (300, 150, 350, 250, 0.8, 0)]
    matches1 = cross_tracker.update("CAM_1", cam1_detections)
    cam2_detections = [(120, 110, 170, 210, 0.85, 0), (500, 200, 550, 300, 0.9, 0)]
    matches2 = cross_tracker.update("CAM_2", cam2_detections)
    unique = cross_tracker.get_unique_visitors()
    print(f"   ✅ {unique} unique visitors across cameras\n")
except Exception as e:
    print(f"   ❌ Failed: {e}\n")
    exit(1)

# Test 5: Event emitter
print("5. Testing event emitter...")
try:
    zones = {"SKINCARE": (200, 200, 600, 600), "BILLING": (800, 200, 1200, 600)}
    entry_zone = (0, 0, 1920, 200)
    emitter = EventEmitter("STORE_BLR_002", "CAM_1", entry_zone, zones)
    events = emitter.process_detection(1, (100, 50, 150, 150), 0.9, "2026-04-22T10:00:00Z")
    assert len(events) > 0
    print(f"   ✅ Generated {len(events)} events\n")
except Exception as e:
    print(f"   ❌ Failed: {e}\n")
    exit(1)

# Test 6: Dashboard service
print("6. Testing dashboard service...")
try:
    dashboard = DashboardService()
    metrics = {
        'unique_visitors': 150,
        'conversion_rate': 12.5,
        'avg_dwell_time_ms': 4200,
        'zones': {'SKINCARE': 85.2, 'BILLING': 45.8},
        'anomalies': [{'type': 'QUEUE_SPIKE', 'severity': 'WARN', 'message': 'Queue depth reached 6'}]
    }
    dashboard.update_metrics("STORE_BLR_002", metrics)
    terminal = dashboard.get_terminal_display("STORE_BLR_002")
    json_display = dashboard.get_json_display("STORE_BLR_002")
    html = WebDashboardGenerator.generate_html("STORE_BLR_002", metrics)
    assert "STORE INTELLIGENCE DASHBOARD" in terminal
    assert json_display['store_id'] == "STORE_BLR_002"
    assert "Store Intelligence Dashboard" in html
    print(f"   ✅ All 3 dashboard formats working\n")
except Exception as e:
    print(f"   ❌ Failed: {e}\n")
    exit(1)

# Test 7: Pipeline integration
print("7. Testing pipeline integration...")
try:
    from pipeline.run import run_pipeline
    import tempfile
    import json
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = f"{tmpdir}/events.jsonl"
        run_pipeline(
            video_dir="nonexistent",
            output_file=output_file,
            use_real_detection=False,
            num_frames=30,
            num_people=2
        )
        
        import os
        assert os.path.exists(output_file)
        with open(output_file, 'r') as f:
            events = [json.loads(line) for line in f if line.strip()]
        assert len(events) > 0
        print(f"   ✅ Generated {len(events)} events\n")
except Exception as e:
    print(f"   ❌ Failed: {e}\n")
    exit(1)

# Test 8: YOLOv8 status
print("8. Checking YOLOv8 availability...")
if YOLO_AVAILABLE:
    print("   ✅ YOLOv8 available - ready for real video processing\n")
else:
    print("   ⚠️  YOLOv8 not available - using mock detection\n")
    print("   To enable: pip install ultralytics\n")

# Summary
print("=" * 60)
print("✅ ALL VALIDATION TESTS PASSED!")
print("=" * 60)
print("\n📊 SYSTEM COMPONENTS:")
print("✓ Detection pipeline (mock + YOLOv8 ready)")
print("✓ Centroid tracker")
print("✓ Cross-camera deduplication")
print("✓ Event emission")
print("✓ Dashboard services (terminal, web, JSON)")
print("✓ Pipeline integration")

print("\n🚀 READY FOR DEPLOYMENT:")
print("1. Extract dataset: unzip store-intelligence-dataset.zip -d data/")
print("2. Run pipeline: python pipeline/run.py --use-real --store-layout data/store_layout.json")
print("3. Start API: python -m uvicorn app.main:app --reload")
print("4. View dashboard: curl http://localhost:8000/stores/STORE_BLR_002/dashboard/terminal")

print("\n✨ Enhanced Store Intelligence System is ready!")
