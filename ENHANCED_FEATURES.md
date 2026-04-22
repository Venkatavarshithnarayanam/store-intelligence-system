# Enhanced Store Intelligence System

## Overview

This document describes the enhancements made to the Store Intelligence system for processing real CCTV datasets with advanced computer vision and analytics capabilities.

---

## New Features

### 1. Real YOLOv8 Detection

**What's New:**
- Integrated YOLOv8 nano model for real person detection
- Automatic model download and caching
- Confidence-based filtering (configurable threshold)
- Graceful handling of partial occlusion

**How to Use:**
```bash
# Install YOLOv8
pip install ultralytics

# Run with real detection
python pipeline/run.py --use-real --store-layout data/store_layout.json
```

**Benefits:**
- Accurate person detection from real CCTV footage
- Handles lighting variations and camera angles
- Detects multiple people simultaneously
- Confidence scores for quality assessment

### 2. Cross-Camera Deduplication

**What's New:**
- Global visitor tracking across multiple cameras
- Prevents double-counting when cameras overlap
- Maintains unique visitor IDs across store

**How It Works:**
1. Each camera has a local tracker (SimpleTracker)
2. Global tracker (CrossCameraTracker) maintains unique visitor IDs
3. Matches visitors across cameras by position and time window
4. Tracks which cameras each visitor has been seen in

**How to Use:**
```bash
python pipeline/run.py --use-real --use-cross-camera --store-layout data/store_layout.json
```

**Example:**
```
Camera 1 (Entry): VIS_001 enters
Camera 2 (Floor): VIS_001 detected (same person)
Result: 1 unique visitor (not 2)
```

### 3. Enhanced Staff Filtering

**What's New:**
- Heuristic-based staff detection
- Excludes staff from customer metrics
- Improves accuracy of customer analytics

**Detection Logic:**
```python
is_staff = (confidence > 0.9) AND (aspect_ratio > 2.0)
```

**Rationale:**
- Staff wear uniforms → higher detection confidence
- Staff stand upright → taller aspect ratio
- Staff move through all zones regularly

**Impact:**
- More accurate unique visitor counts
- Better conversion rate calculations
- Cleaner zone heatmaps

### 4. Store Layout Integration

**What's New:**
- Loads zone definitions from JSON configuration
- Supports multiple stores with different layouts
- Automatic zone detection for events

**Configuration Format:**
```json
{
  "STORE_BLR_002": {
    "zones": {
      "ENTRY": {"x1": 0, "y1": 0, "x2": 1920, "y2": 200},
      "SKINCARE": {"x1": 200, "y1": 200, "x2": 600, "y2": 600},
      "BILLING": {"x1": 800, "y1": 200, "x2": 1200, "y2": 600}
    },
    "cameras": {
      "CAM_ENTRY_01": {"type": "entry", "coverage": "ENTRY"},
      "CAM_FLOOR_01": {"type": "floor", "coverage": ["SKINCARE", "BILLING"]},
      "CAM_BILLING_01": {"type": "billing", "coverage": "BILLING"}
    }
  }
}
```

**How to Use:**
```python
from pipeline.run import load_store_layout, convert_zones_format

layout = load_store_layout("data/store_layout.json", "STORE_BLR_002")
zones = convert_zones_format(layout["zones"])
```

### 5. Real-Time Dashboard

**What's New:**
- Three dashboard formats for different use cases
- Live metrics updates
- Anomaly detection and display
- Zone heatmap visualization

**Dashboard Formats:**

#### Terminal Dashboard
```bash
curl http://localhost:8000/stores/STORE_BLR_002/dashboard/terminal
```

Output:
```
╔════════════════════════════════════════════════════════════════╗
║                    STORE INTELLIGENCE DASHBOARD                ║
╠════════════════════════════════════════════════════════════════╣
║ Store: STORE_BLR_002                                           ║
║ Unique Visitors:        335                                    ║
║ Conversion Rate (%):    15.5                                   ║
║ Avg Dwell Time (ms):    4200.5                                 ║
║ Avg Basket Value (₹):   870.01                                 ║
╚════════════════════════════════════════════════════════════════╝
```

#### Web Dashboard
```bash
open http://localhost:8000/stores/STORE_BLR_002/dashboard.html
```

Features:
- Real-time metric cards
- Zone heatmap with visual bars
- Active anomalies list
- Auto-refresh every 5 seconds
- Responsive design

#### JSON Dashboard
```bash
curl http://localhost:8000/stores/STORE_BLR_002/dashboard
```

Output:
```json
{
  "store_id": "STORE_BLR_002",
  "timestamp": "2026-04-22T14:22:10Z",
  "metrics": {
    "unique_visitors": 335,
    "conversion_rate": 15.5,
    "avg_dwell_time_ms": 4200.5,
    "zones": {"SKINCARE": 100.0, "BILLING": 45.6}
  }
}
```

### 6. POS Transaction Correlation

**What's New:**
- Automatic matching of visitors to purchases
- Conversion rate calculation
- Revenue attribution
- Basket value analysis

**How It Works:**
1. Detects visitor in billing zone
2. Matches to POS transaction within 5-minute window
3. Counts as converted visitor
4. Calculates metrics

**Example:**
```
Visitor VIS_001 in billing zone at 14:38:00
POS transaction at 14:40:30
→ Visitor converted (within 5-minute window)
→ Basket value: ₹1240.00
```

**Metrics Returned:**
```json
{
  "conversion_rate": 15.5,
  "converted_visitors": 52,
  "total_basket_value": 45230.50,
  "avg_basket_value": 870.01,
  "unique_visitors": 335
}
```

---

## Architecture Changes

### Detection Pipeline

**Before:**
```
Mock Detector → SimpleTracker → EventEmitter → Events
```

**After:**
```
YOLOv8 Detector → CrossCameraTracker → EventEmitter → Events
     ↓                    ↓
  Real Video         Global IDs
  Processing         Deduplication
```

### Tracker Hierarchy

```
CrossCameraTracker (Global)
├── SimpleTracker (Camera 1)
├── SimpleTracker (Camera 2)
└── SimpleTracker (Camera 3)
```

### Event Flow

```
CCTV Video
    ↓
YOLOv8 Detection (person detection)
    ↓
CrossCameraTracker (assign global IDs)
    ↓
EventEmitter (generate events)
    ↓
FastAPI Ingestion (store events)
    ↓
MetricsService (calculate analytics)
    ↓
DashboardService (display results)
```

---

## Configuration

### Pipeline Configuration

```bash
python pipeline/run.py \
  --use-real                          # Enable YOLOv8 detection
  --use-cross-camera                  # Enable cross-camera deduplication
  --store-layout data/store_layout.json  # Load zone definitions
  --video-dir data/videos             # Input video directory
  --output data/events.jsonl          # Output events file
  --store-id STORE_BLR_002            # Store identifier
```

### API Configuration

```bash
python -m uvicorn app.main:app \
  --host 0.0.0.0                      # Listen on all interfaces
  --port 8000                         # API port
  --reload                            # Auto-reload on changes
```

### Dashboard Configuration

```python
# Terminal dashboard refresh
curl http://localhost:8000/stores/STORE_BLR_002/dashboard/terminal

# Web dashboard auto-refresh (5 seconds)
open http://localhost:8000/stores/STORE_BLR_002/dashboard.html

# JSON for custom integrations
curl http://localhost:8000/stores/STORE_BLR_002/dashboard
```

---

## Edge Cases Handled

### 1. Group Entry
**Problem:** Multiple people enter simultaneously
**Solution:** YOLOv8 detects each person separately, tracker assigns unique IDs

### 2. Staff Movement
**Problem:** Staff inflate visitor counts
**Solution:** Heuristic filtering (confidence > 0.9 + aspect_ratio > 2.0)

### 3. Re-entry
**Problem:** Same person returns - should be new visit
**Solution:** Track session state, emit REENTRY event

### 4. Partial Occlusion
**Problem:** People partially obscured by displays
**Solution:** Accept detections with confidence >= 0.3, graceful degradation

### 5. Queue Buildup
**Problem:** Queue forms and disperses
**Solution:** Track queue_depth in BILLING_QUEUE_JOIN events

### 6. Empty Store Periods
**Problem:** No customers for extended periods
**Solution:** API handles zero events gracefully, returns 0 not null

### 7. Camera Overlap
**Problem:** Same person counted twice
**Solution:** Cross-camera deduplication by visitor_id + timestamp

---

## Performance Characteristics

### Detection
- YOLOv8 nano: ~50ms per frame (1080p)
- Mock detector: <1ms per frame
- Batch processing: 15fps video = 1 frame per 67ms

### Tracking
- SimpleTracker: O(n²) per frame (n = active tracks)
- CrossCameraTracker: O(n*m) per frame (n = cameras, m = tracks)
- Typical: <10ms for 50 active tracks

### Metrics Calculation
- Unique visitors: O(n) query
- Conversion rate: O(n) with POS matching
- Heatmap: O(n) zone aggregation
- Typical: <100ms for 10k events

### Dashboard
- Terminal: <10ms generation
- Web HTML: <50ms generation
- JSON: <5ms generation

---

## Testing

### Quick Validation
```bash
python quick_validate.py
```

Tests:
- Core imports
- Mock detector
- Simple tracker
- Cross-camera tracker
- Event emitter
- Dashboard service
- Pipeline integration

### Full Test Suite
```bash
pytest tests/
```

### Manual Testing
```bash
# Generate test events
python pipeline/run.py --num-frames 100 --output test_events.jsonl

# Start API
python -m uvicorn app.main:app --reload

# Ingest events
curl -X POST http://localhost:8000/events/ingest \
  -H "Content-Type: application/json" \
  -d @test_events.jsonl

# View metrics
curl http://localhost:8000/stores/STORE_BLR_002/metrics

# View dashboard
curl http://localhost:8000/stores/STORE_BLR_002/dashboard/terminal
```

---

## Troubleshooting

### YOLOv8 Not Available
```
Warning: ultralytics import failed
```

**Solution:**
```bash
pip install ultralytics opencv-python torch torchvision
```

### No Events Generated
**Check:**
1. Video files exist: `ls -la data/videos/`
2. Video format: `ffprobe data/videos/CAM_1.mp4`
3. Detection output: `python pipeline/run.py --verbose`

### POS Correlation Not Working
**Check:**
1. POS file exists: `ls -la data/pos_transactions.csv`
2. File format: `head -5 data/pos_transactions.csv`
3. Timestamps match: Compare event timestamps to POS timestamps

### Dashboard Not Updating
**Check:**
1. API running: `curl http://localhost:8000/health`
2. Events ingested: `curl http://localhost:8000/stores/STORE_BLR_002/metrics`
3. Browser cache: Hard refresh (Ctrl+Shift+R)

---

## Future Enhancements

### Planned Features
- [ ] Real-time event streaming (WebSocket)
- [ ] Multi-store aggregation
- [ ] Advanced anomaly detection (ML-based)
- [ ] Customer journey mapping
- [ ] Predictive analytics
- [ ] Mobile dashboard app

### Optimization Opportunities
- [ ] GPU acceleration for YOLOv8
- [ ] Distributed tracking across servers
- [ ] Event compression and archival
- [ ] Caching layer for metrics
- [ ] Incremental heatmap updates

---

## References

- **YOLOv8:** https://github.com/ultralytics/ultralytics
- **FastAPI:** https://fastapi.tiangolo.com/
- **SQLite:** https://www.sqlite.org/
- **OpenCV:** https://opencv.org/

---

## Support

For issues or questions:
1. Check DATASET_GUIDE.md for dataset integration
2. Review DESIGN.md for architecture details
3. See CHOICES.md for design decisions
4. Run quick_validate.py to verify setup

---

**Enhanced Store Intelligence System v2.0** ✨
