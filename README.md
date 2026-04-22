# Store Intelligence System

**End-to-end computer vision pipeline: CCTV footage → real-time retail analytics API**

Convert raw store footage into actionable metrics: visitor counts, conversion funnels, zone heatmaps, and anomaly detection.

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Detection Pipeline
Process CCTV videos and generate events:
```bash
python pipeline/run.py --video-dir data/videos --output data/events.jsonl
```

### 3. Start API Server
```bash
python -m uvicorn app.main:app --reload --port 8000
```

### 4. Query Metrics
```bash
# Ingest events
curl -X POST http://localhost:8000/events/ingest \
  -H "Content-Type: application/json" \
  -d '[{"event_id":"...", "store_id":"STORE_BLR_002", ...}]'

# Get metrics
curl http://localhost:8000/stores/STORE_BLR_002/metrics

# Get funnel
curl http://localhost:8000/stores/STORE_BLR_002/funnel

# Get heatmap
curl http://localhost:8000/stores/STORE_BLR_002/heatmap

# Get anomalies
curl http://localhost:8000/stores/STORE_BLR_002/anomalies

# Health check
curl http://localhost:8000/health
```

## System Architecture

```
Raw Video (MP4)
    ↓
YOLOv8 Detection (person class)
    ↓
Centroid Tracker (unique visitor IDs)
    ↓
Event Emitter (ENTRY, EXIT, ZONE_DWELL, etc.)
    ↓
JSONL Events
    ↓
FastAPI Ingestion (deduplication, validation)
    ↓
SQLite Storage
    ↓
Analytics Queries (metrics, funnel, heatmap, anomalies)
```

## Project Structure

```
pipeline/
  ├── tracker.py      # Centroid-based object tracker
  ├── detect.py       # YOLOv8 detection (mock for testing)
  ├── emit.py         # Event emission logic
  ├── models.py       # Data models
  ├── run.py          # Pipeline orchestration
  └── __init__.py

app/
  ├── main.py         # FastAPI endpoints
  ├── database.py     # SQLite storage
  ├── ingestion.py    # Event validation
  ├── metrics.py      # Analytics computation
  └── __init__.py

tests/
  ├── test_pipeline.py  # Tracker & emitter tests
  ├── test_api.py       # API endpoint tests
  └── __init__.py

docs/
  ├── DESIGN.md       # Architecture & design decisions
  └── CHOICES.md      # Trade-offs & rationale
```

## Event Schema

```json
{
  "event_id": "uuid-v4",
  "store_id": "STORE_BLR_002",
  "camera_id": "CAM_ENTRY_01",
  "visitor_id": "VIS_12345",
  "event_type": "ENTRY|EXIT|ZONE_ENTER|ZONE_EXIT|ZONE_DWELL|BILLING_QUEUE_JOIN|BILLING_QUEUE_ABANDON|REENTRY",
  "timestamp": "2026-03-03T14:22:10Z",
  "zone_id": "SKINCARE",
  "dwell_ms": 8400,
  "is_staff": false,
  "confidence": 0.91,
  "metadata": {
    "queue_depth": null,
    "sku_zone": "MOISTURISER",
    "session_seq": 5
  }
}
```

## API Endpoints

### POST /events/ingest
Batch ingest events with deduplication and validation.

**Request:**
```json
[
  {
    "event_id": "uuid",
    "store_id": "STORE_BLR_002",
    "camera_id": "CAM_ENTRY_01",
    "visitor_id": "VIS_12345",
    "event_type": "ENTRY",
    "timestamp": "2026-03-03T14:22:10Z",
    "is_staff": false,
    "confidence": 0.9,
    "metadata": {"session_seq": 1}
  }
]
```

**Response:**
```json
{
  "status": "success",
  "trace_id": "uuid",
  "events_ingested": 100,
  "duplicates": 5,
  "validation_errors": [],
  "database_errors": []
}
```

**Constraints:**
- Max batch size: 500 events
- Returns 400 if batch > 500
- Idempotent by event_id

### GET /stores/{store_id}/metrics
Get store metrics for time window.

**Response:**
```json
{
  "store_id": "STORE_BLR_002",
  "time_window_hours": 24,
  "unique_visitors": 342,
  "avg_dwell_time_ms": 4200.5,
  "conversion_rate": 0.2,
  "max_queue_depth": 8,
  "trace_id": "uuid"
}
```

### GET /stores/{store_id}/funnel
Get conversion funnel: ENTRY → ZONE → BILLING → PURCHASE.

**Response:**
```json
{
  "store_id": "STORE_BLR_002",
  "time_window_hours": 24,
  "funnel": {
    "entry": 342,
    "zone_visit": 298,
    "billing_queue": 156,
    "purchase": 89
  },
  "dropoff_percentages": {
    "entry_to_zone": 12.87,
    "zone_to_billing": 47.65,
    "billing_to_purchase": 42.95
  },
  "trace_id": "uuid"
}
```

### GET /stores/{store_id}/heatmap
Get zone visit frequency (normalized 0-100).

**Response:**
```json
{
  "store_id": "STORE_BLR_002",
  "time_window_hours": 24,
  "zones": {
    "SKINCARE": 100,
    "BILLING": 45.6,
    "CHECKOUT": 23.2
  },
  "trace_id": "uuid"
}
```

### GET /stores/{store_id}/anomalies
Detect anomalies: queue spike, dead zone, conversion drop.

**Response:**
```json
{
  "store_id": "STORE_BLR_002",
  "time_window_hours": 24,
  "anomalies": [
    {
      "type": "QUEUE_SPIKE",
      "severity": "WARN",
      "message": "Queue depth reached 12",
      "value": 12
    },
    {
      "type": "CONVERSION_DROP",
      "severity": "CRITICAL",
      "message": "Visitor count down 25.3% vs 7-day avg",
      "current": 256,
      "expected": 343
    }
  ],
  "count": 2,
  "trace_id": "uuid"
}
```

### GET /health
Health check with stale feed detection.

**Response:**
```json
{
  "status": "healthy|degraded|unhealthy",
  "timestamp": "2026-03-03T14:22:10Z",
  "last_event_timestamp": "2026-03-03T14:20:10Z",
  "stale_feed_warning": false,
  "trace_id": "uuid"
}
```

## Testing

Run all tests:
```bash
pytest tests/ -v
```

Run specific test file:
```bash
pytest tests/test_pipeline.py -v
pytest tests/test_api.py -v
```

Test coverage includes:
- Tracker: ID assignment, frame-to-frame consistency, stale removal
- Emitter: All 8 event types, zone transitions, dwell calculation
- API: Ingestion, idempotency, batch validation, metrics queries
- Schema: Validation, serialization, edge cases

## Production Features

✓ **Idempotent Ingestion**: Deduplication by event_id (primary key)
✓ **Structured Logging**: Trace IDs, latency, status codes
✓ **Error Handling**: Graceful responses, no stack traces
✓ **Batch Processing**: Partial success, detailed error reporting
✓ **Real-time Queries**: No caching, always current data
✓ **Anomaly Detection**: Queue spikes, dead zones, conversion drops

## Design Decisions

See `docs/DESIGN.md` for complete architecture.
See `docs/CHOICES.md` for trade-offs and rationale.

**Key Choices:**
- **YOLOv8 nano**: Fast on CPU, accurate for person detection
- **Centroid tracker**: Simple, debuggable, sufficient for single-camera
- **SQLite**: Zero setup, sufficient for <1M events
- **Heuristic staff filtering**: Confidence + aspect ratio
- **JSONL events**: Streaming-friendly, queryable, portable

## Why These Choices?

**YOLOv8 vs Alternatives:**
- RT-DETR: Better accuracy but slower (15 FPS vs 30 FPS)
- MediaPipe: Lightweight but less accurate in crowds
- YOLOv8: Best balance for 48-hour deadline

**Centroid Tracker vs DeepSORT:**
- DeepSORT: Better re-ID but requires external model
- Centroid: Simple, fast, sufficient for MVP
- Trade-off: Single-camera only, can upgrade later

**SQLite vs PostgreSQL:**
- PostgreSQL: Better for scale but requires Docker + setup
- SQLite: Zero setup, sufficient for <1M events
- Trade-off: Single machine, can migrate post-submission

**JSONL vs Binary:**
- Binary: Faster but less portable
- JSONL: Human-readable, queryable, streaming-friendly
- Trade-off: Slightly larger file size

## Correctness Properties

1. **Entry/Exit Accuracy**: entry_count ≈ exit_count (±5%)
2. **Unique Visitor Deduplication**: No duplicate visitor_ids in ENTRY events
3. **Idempotent Ingestion**: POST /events/ingest twice → same result
4. **Funnel Monotonicity**: Entry ≥ Zone ≥ Billing ≥ Purchase

## Known Limitations

- Single-camera tracking (no cross-camera re-ID)
- Heuristic staff filtering (not ML-based)
- Hardcoded zone rectangles (not learned)
- Simplified conversion rate (not POS-correlated)
- SQLite scalability (single machine, ~1M events max)

## Future Improvements

- Re-ID model (OSNet) for cross-camera tracking
- VLM zone classification (GPT-4V)
- Real-time streaming (Kafka)
- Web dashboard (React)
- POS integration
- ML anomaly detection (Isolation Forest)
- Multi-store distributed architecture

## Deployment

### Local Development
```bash
python -m uvicorn app.main:app --reload --port 8000
```

### Docker (Production)
```bash
docker build -t store-intelligence:latest .
docker run -p 8000:8000 -v /data:/app/data store-intelligence:latest
```

## Troubleshooting

**No events generated:**
- Check `data/videos/` contains MP4 files
- Verify `pipeline/run.py` completes without errors
- Check `data/events.jsonl` for output

**API returns 503:**
- Database may be locked
- Check `store_intelligence.db` permissions
- Restart API server

**Metrics show zero:**
- Ensure events were ingested via POST /events/ingest
- Check store_id matches in queries
- Verify timestamps are recent (within time_window_hours)

## Support

For questions about architecture, see `docs/DESIGN.md`.
For questions about trade-offs, see `docs/CHOICES.md`.
For questions about implementation, check test files for examples.
