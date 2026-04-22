# Store Intelligence System - Dataset Integration Guide

## Overview

This guide explains how to use the real CCTV dataset, store layouts, and POS transactions with the Store Intelligence system.

---

## Dataset Structure

### 1. CCTV Clips

**Location:** `data/videos/`

**Format:**
- 5 stores × 3 camera angles = 15 video files
- Each file: 20 minutes, 1080p, 15fps
- Naming: `CAM_1.mp4`, `CAM_2.mp4`, etc.

**Camera Angles:**
- **Entry/Exit Camera** - Detects people entering/leaving store
- **Main Floor Camera** - Tracks movement through zones
- **Billing Area Camera** - Monitors queue and checkout

**Edge Cases in Footage:**
- Group entry (2-4 people simultaneously)
- Staff movement (identifiable by uniform)
- Re-entry (same person returning)
- Partial occlusion (people behind displays)
- Queue buildup and dispersal
- Empty store periods (5-10 minutes)
- Camera angle overlap (cross-camera deduplication needed)

### 2. Store Layout

**Location:** `data/store_layout.json`

**Format:**
```json
{
  "STORE_BLR_002": {
    "store_name": "Apex Retail - Bangalore",
    "city": "Bangalore",
    "open_hours": "09:00-21:00",
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

**Key Fields:**
- `zones` - Rectangle coordinates for each zone (x1, y1, x2, y2)
- `cameras` - Camera definitions and coverage areas
- `open_hours` - Store operating hours (for filtering)

### 3. POS Transactions

**Location:** `data/pos_transactions.csv`

**Format:**
```csv
store_id,transaction_id,timestamp,basket_value_inr
STORE_BLR_002,TXN_00441,2026-03-03T14:38:12Z,1240.00
STORE_BLR_002,TXN_00442,2026-03-03T14:41:55Z,680.00
```

**Correlation Logic:**
- Match visitor in billing zone within 5 minutes before transaction
- No customer_id in POS data
- Correlation by: store_id + time window + zone presence

### 4. Sample Events

**Location:** `data/sample_events.jsonl`

**Format:**
```json
{"event_id":"uuid","store_id":"STORE_BLR_002","camera_id":"CAM_ENTRY_01","visitor_id":"VIS_12345","event_type":"ENTRY","timestamp":"2026-03-03T14:22:10Z","zone_id":null,"dwell_ms":0,"is_staff":false,"confidence":0.91,"metadata":{"queue_depth":null,"sku_zone":null,"session_seq":1}}
```

**Use:** Validate your detection layer output against expected schema.

### 5. Assertions

**Location:** `assertions.py`

**Purpose:** 10 example test assertions your API must pass.

**Example:**
```python
def test_unique_visitors_count():
    """Unique visitors should match entry events"""
    metrics = api.get_metrics("STORE_BLR_002")
    assert metrics['unique_visitors'] > 0

def test_conversion_rate_calculation():
    """Conversion rate should be calculated from POS data"""
    metrics = api.get_metrics("STORE_BLR_002")
    assert 0 <= metrics['conversion_rate'] <= 100
```

---

## Setup Instructions

### 1. Install Enhanced Dependencies

```bash
# Install computer vision dependencies
pip install ultralytics opencv-python numpy torch torchvision

# Or run the setup script
python setup_enhanced_system.py
```

### 2. Extract Dataset

```bash
# Extract ZIP archive
unzip store-intelligence-dataset.zip -d store-intelligence/data/

# Verify structure
ls -la store-intelligence/data/
# Expected:
# - videos/
# - store_layout.json
# - pos_transactions.csv
# - sample_events.jsonl
# - assertions.py
```

### 3. Load Store Layout

The system automatically loads `store_layout.json` when needed:

```python
import json

with open('data/store_layout.json', 'r') as f:
    store_layout = json.load(f)

store_id = "STORE_BLR_002"
zones = store_layout[store_id]['zones']
cameras = store_layout[store_id]['cameras']
```

### 4. Process CCTV Clips

```bash
# Run REAL detection pipeline on all videos (ENHANCED)
python pipeline/run.py \
  --use-real \
  --store-layout data/store_layout.json \
  --video-dir data/videos \
  --output data/events.jsonl \
  --use-cross-camera

# Run mock detection (for testing)
python pipeline/run.py \
  --video-dir data/videos \
  --output data/events.jsonl \
  --num-frames 1000
```

### 5. Ingest Events

```bash
# Start API
python -m uvicorn app.main:app --reload --port 8000

# Ingest events from JSONL
curl -X POST http://localhost:8000/events/ingest \
  -H "Content-Type: application/json" \
  -d @data/events.jsonl
```

### 6. View Dashboard

```bash
# Terminal dashboard
curl http://localhost:8000/stores/STORE_BLR_002/dashboard/terminal

# Web dashboard
open http://localhost:8000/stores/STORE_BLR_002/dashboard.html

# JSON metrics
curl http://localhost:8000/stores/STORE_BLR_002/metrics
```

---

## Handling Edge Cases

### Group Entry

**Problem:** Multiple people enter simultaneously through same door.

**Solution:**
- YOLOv8 detects each person separately
- Centroid tracker assigns unique IDs
- Each person gets separate ENTRY event

**Verification:**
```python
entry_events = db.get_events("STORE_BLR_002", event_type="ENTRY")
assert len(entry_events) >= num_people_in_group
```

### Staff Movement

**Problem:** Staff move through all zones, inflating visitor counts.

**Solution:**
- Heuristic: confidence > 0.9 + aspect_ratio > 2.0
- Flag as `is_staff: true`
- Exclude from metrics

**Verification:**
```python
staff_events = [e for e in events if e['is_staff']]
customer_events = [e for e in events if not e['is_staff']]
assert len(customer_events) < len(events)
```

### Re-entry

**Problem:** Same person leaves and returns - should be counted as new visit.

**Solution:**
- Track session state per visitor_id
- Emit EXIT event when leaving entry zone
- Emit REENTRY event when re-entering
- New session_seq for each entry

**Verification:**
```python
reentry_events = db.get_events("STORE_BLR_002", event_type="REENTRY")
assert len(reentry_events) > 0  # Some customers return
```

### Partial Occlusion

**Problem:** People partially obscured by displays - low confidence detection.

**Solution:**
- Accept detections with confidence >= 0.3
- Track confidence in events
- Graceful degradation (don't fail on low confidence)

**Verification:**
```python
low_conf_events = [e for e in events if e['confidence'] < 0.5]
assert len(low_conf_events) > 0  # Some low-confidence detections
```

### Queue Buildup

**Problem:** Queue forms, deepens, and disperses during billing clip.

**Solution:**
- Track queue_depth in BILLING_QUEUE_JOIN events
- Emit ZONE_DWELL every 30 seconds in billing zone
- Detect queue spike (depth > 5)

**Verification:**
```python
queue_events = db.get_events("STORE_BLR_002", event_type="BILLING_QUEUE_JOIN")
max_queue = max([e['metadata']['queue_depth'] for e in queue_events])
assert max_queue > 0
```

### Empty Store Periods

**Problem:** 5-10 minute windows with no customers.

**Solution:**
- API handles zero events gracefully
- Returns 0 for metrics, not null
- Detects "dead zone" anomaly (no events > 30 min)

**Verification:**
```python
metrics = api.get_metrics("STORE_BLR_002")
assert metrics['unique_visitors'] >= 0  # Not null
```

### Camera Angle Overlap

**Problem:** Entry camera and floor camera overlap - same person counted twice.

**Solution:**
- Cross-camera deduplication by visitor_id + timestamp
- Centroid tracker maintains unique IDs across cameras
- Merge events from overlapping cameras

**Verification:**
```python
# Count unique visitor_ids across all cameras
unique_visitors = len(set(e['visitor_id'] for e in events))
assert unique_visitors == metrics['unique_visitors']
```

---

## POS Correlation

### How It Works

1. **Detect visitor in billing zone** - ZONE_ENTER or BILLING_QUEUE_JOIN event
2. **Match to POS transaction** - Within 5-minute window
3. **Count as converted** - Visitor made a purchase

### Example

```python
from app.pos_correlation import POSCorrelationService

pos_service = POSCorrelationService("data/pos_transactions.csv")

# Get billing zone events
billing_events = db.get_events("STORE_BLR_002", event_type="BILLING_QUEUE_JOIN")

# Calculate conversion
converted_count, total_value = pos_service.find_converted_visitors(
    "STORE_BLR_002",
    billing_events,
    time_window_minutes=5
)

conversion_rate = (converted_count / unique_visitors) * 100
```

### Metrics Returned

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

## Dashboard Features

### Terminal Dashboard

```bash
curl http://localhost:8000/stores/STORE_BLR_002/dashboard/terminal
```

**Output:**
```
╔════════════════════════════════════════════════════════════════╗
║                    STORE INTELLIGENCE DASHBOARD                ║
╠════════════════════════════════════════════════════════════════╣
║ Store: STORE_BLR_002                                           ║
║ Last Update: 2026-03-03T14:22:10Z                              ║
║ Total Events Processed: 1245                                   ║
╠════════════════════════════════════════════════════════════════╣
║ REAL-TIME METRICS                                              ║
╠════════════════════════════════════════════════════════════════╣
║ Unique Visitors:        335                                    ║
║ Avg Dwell Time (ms):    4200.5                                 ║
║ Conversion Rate (%):    15.5                                   ║
║ Converted Visitors:     52                                     ║
║ Avg Basket Value (₹):   870.01                                 ║
║ Max Queue Depth:        8                                      ║
╠════════════════════════════════════════════════════════════════╣
║ ZONE HEATMAP                                                   ║
╠════════════════════════════════════════════════════════════════╣
║ SKINCARE                 ████████████████████████████ 100.0%   ║
║ BILLING                  ██████████████ 45.6%                  ║
║ CHECKOUT                 ███████ 23.2%                         ║
╠════════════════════════════════════════════════════════════════╣
║ ANOMALIES                                                      ║
╠════════════════════════════════════════════════════════════════╣
║ [WARN] Queue depth reached 8                                   ║
║ [INFO] No conversion drop detected                             ║
╚════════════════════════════════════════════════════════════════╝
```

### Web Dashboard

```bash
open http://localhost:8000/stores/STORE_BLR_002/dashboard.html
```

**Features:**
- Real-time metrics cards
- Zone heatmap with visual bars
- Active anomalies list
- Auto-refresh every 5 seconds
- Responsive design

### JSON Dashboard

```bash
curl http://localhost:8000/stores/STORE_BLR_002/dashboard
```

**Output:**
```json
{
  "store_id": "STORE_BLR_002",
  "timestamp": "2026-03-03T14:22:10Z",
  "event_count": 1245,
  "metrics": {
    "unique_visitors": 335,
    "avg_dwell_time_ms": 4200.5,
    "conversion_rate": 15.5,
    "converted_visitors": 52,
    "avg_basket_value": 870.01,
    "max_queue_depth": 8,
    "zones": {
      "SKINCARE": 100.0,
      "BILLING": 45.6,
      "CHECKOUT": 23.2
    },
    "anomalies": [
      {
        "type": "QUEUE_SPIKE",
        "severity": "WARN",
        "message": "Queue depth reached 8"
      }
    ]
  },
  "status": "live"
}
```

---

## Validation

### Run Assertions

```bash
# Run provided assertions
python assertions.py

# Expected output:
# test_unique_visitors_count ... PASS
# test_conversion_rate_calculation ... PASS
# test_funnel_monotonicity ... PASS
# ... (10 assertions total)
```

### Validate Against Sample Events

```bash
# Compare your output to sample_events.jsonl
python -c "
import json

with open('data/sample_events.jsonl', 'r') as f:
    for line in f:
        event = json.loads(line)
        print(f'Event: {event[\"event_type\"]} - {event[\"visitor_id\"]}')
"
```

---

## Troubleshooting

### No Events Generated

**Problem:** Pipeline runs but produces no events.

**Solution:**
1. Check video files exist: `ls -la data/videos/`
2. Verify video format: `ffprobe data/videos/CAM_1.mp4`
3. Check detection output: `python pipeline/run.py --verbose`

### POS Correlation Not Working

**Problem:** Conversion rate always 0.

**Solution:**
1. Verify POS file exists: `ls -la data/pos_transactions.csv`
2. Check file format: `head -5 data/pos_transactions.csv`
3. Verify timestamps match: Compare event timestamps to POS timestamps

### Dashboard Not Updating

**Problem:** Dashboard shows stale data.

**Solution:**
1. Check API is running: `curl http://localhost:8000/health`
2. Verify events are being ingested: `curl http://localhost:8000/stores/STORE_BLR_002/metrics`
3. Check browser cache: Hard refresh (Ctrl+Shift+R)

---

## Performance Tips

### For Large Datasets

1. **Batch Ingestion:** Ingest events in batches of 500
2. **Database Indexes:** Already created on store_id, visitor_id, timestamp
3. **Query Optimization:** Use time windows (hours parameter)

### For Real-Time Processing

1. **Stream Events:** Ingest as they're generated, not in batch
2. **Dashboard Refresh:** Set to 5-second intervals
3. **Anomaly Detection:** Runs on every query (no caching)

---

## Next Steps

1. Extract dataset ZIP
2. Run detection pipeline: `python pipeline/run.py`
3. Start API: `python -m uvicorn app.main:app --reload`
4. View dashboard: `curl http://localhost:8000/stores/STORE_BLR_002/dashboard/terminal`
5. Run assertions: `python assertions.py`

---

**Ready to process real CCTV data!** ✓

---

## Enhanced Features (NEW)

### Real YOLOv8 Detection

The system now supports real computer vision with YOLOv8:

```bash
# Install YOLOv8
pip install ultralytics

# Run with real detection
python pipeline/run.py --use-real --store-layout data/store_layout.json
```

**Features:**
- Automatic YOLOv8 nano model download
- Person detection with confidence filtering
- Handles partial occlusion gracefully
- Staff detection heuristics (high confidence + tall aspect ratio)

### Cross-Camera Deduplication

Prevents counting the same person multiple times across cameras:

```bash
# Enable cross-camera deduplication
python pipeline/run.py --use-real --use-cross-camera --store-layout data/store_layout.json
```

**How it works:**
- Maintains global visitor IDs across all cameras
- Matches visitors by position and time window
- Handles camera overlap zones automatically
- Tracks which cameras each visitor has been seen in

### Enhanced Staff Filtering

Improved heuristics for identifying staff members:

```python
def is_likely_staff(detection):
    # Staff: confidence > 0.9 AND aspect ratio > 2.0
    return detection.confidence > 0.9 and detection.get_aspect_ratio() > 2.0
```

**Rationale:**
- Staff wear uniforms (higher detection confidence)
- Staff stand upright more often (taller aspect ratio)
- Staff move through all zones regularly

### Real-Time Dashboard

Three dashboard formats available:

1. **Terminal Dashboard** - ASCII art with live metrics
2. **Web Dashboard** - HTML with auto-refresh
3. **JSON Dashboard** - For API consumption

```bash
# All three formats
curl http://localhost:8000/stores/STORE_BLR_002/dashboard/terminal
curl http://localhost:8000/stores/STORE_BLR_002/dashboard.html
curl http://localhost:8000/stores/STORE_BLR_002/dashboard
```

### POS Transaction Correlation

Automatic correlation of visitors to purchases:

```python
# Matches visitors in billing zone within 5-minute window
pos_service = POSCorrelationService("data/pos_transactions.csv")
conversion_metrics = pos_service.get_conversion_rate(store_id, unique_visitors, billing_events)
```

**Returns:**
- Conversion rate percentage
- Number of converted visitors  
- Total and average basket values
- Revenue attribution
