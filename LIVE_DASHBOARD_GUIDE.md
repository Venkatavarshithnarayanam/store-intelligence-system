# Live Dashboard Guide

## Overview

The Store Intelligence System includes **3 live dashboard formats** that update in real-time as events flow through the system:

1. **Terminal Dashboard** - ASCII art display in terminal
2. **Web Dashboard** - HTML with auto-refresh in browser
3. **JSON Dashboard** - API endpoint for programmatic access

---

## Quick Start (5 minutes)

### Step 1: Start the API Server

```bash
cd store-intelligence
python -m uvicorn app.main:app --reload --port 8000
```

**Expected Output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

### Step 2: Generate Test Events

In a **new terminal**:

```bash
cd store-intelligence
python pipeline/run.py --num-frames 100 --output test_events.jsonl
```

**Expected Output:**
```
Starting mock pipeline for STORE_BLR_002
Mock pipeline complete: 33 events written to test_events.jsonl
```

### Step 3: Ingest Events into API

```bash
curl -X POST http://localhost:8000/events/ingest \
  -H "Content-Type: application/json" \
  -d @test_events.jsonl
```

**Expected Output:**
```json
{
  "status": "success",
  "events_ingested": 33,
  "duplicates": 0,
  "trace_id": "..."
}
```

### Step 4: View Live Dashboard

Choose one of the three formats:

---

## Dashboard Format 1: Terminal Dashboard

### View in Terminal

```bash
curl http://localhost:8000/stores/STORE_BLR_002/dashboard/terminal
```

### Output Example

```
╔════════════════════════════════════════════════════════════════╗
║                    STORE INTELLIGENCE DASHBOARD                ║
╠════════════════════════════════════════════════════════════════╣
║ Store: STORE_BLR_002                                           ║
║ Last Update: 2026-04-22T16:28:20.436025Z                      ║
║ Total Events Processed: 33                                     ║
╠════════════════════════════════════════════════════════════════╣
║ REAL-TIME METRICS                                              ║
╠════════════════════════════════════════════════════════════════╣
║ Unique Visitors:        5                                      ║
║ Avg Dwell Time (ms):    4200.5                                 ║
║ Conversion Rate (%):    15.5                                   ║
║ Converted Visitors:     1                                      ║
║ Avg Basket Value (₹):   870.01                                 ║
║ Max Queue Depth:        3                                      ║
╠════════════════════════════════════════════════════════════════╣
║ ZONE HEATMAP                                                   ║
╠════════════════════════════════════════════════════════════════╣
║ SKINCARE:    ████████████████████ 100.0%                       ║
║ BILLING:     ██████████ 50.0%                                  ║
║ CHECKOUT:    ████ 20.0%                                        ║
╠════════════════════════════════════════════════════════════════╣
║ ANOMALIES                                                      ║
╠════════════════════════════════════════════════════════════════╣
║ [WARN] Queue depth reached 3                                   ║
╚════════════════════════════════════════════════════════════════╝
```

### Auto-Refresh in Terminal

```bash
# Refresh every 5 seconds
while true; do
  clear
  curl -s http://localhost:8000/stores/STORE_BLR_002/dashboard/terminal | jq -r '.display'
  sleep 5
done
```

---

## Dashboard Format 2: Web Dashboard

### View in Browser

```bash
# Open in default browser
open http://localhost:8000/stores/STORE_BLR_002/dashboard.html

# Or use curl to save HTML
curl http://localhost:8000/stores/STORE_BLR_002/dashboard.html > dashboard.html
open dashboard.html
```

### Features

- ✅ Real-time metric cards
- ✅ Zone heatmap with visual bars
- ✅ Anomaly alerts
- ✅ Auto-refresh every 5 seconds
- ✅ Responsive design

### HTML Output

The dashboard includes:
- Store name and last update timestamp
- Real-time metrics (visitors, conversion rate, dwell time, queue depth)
- Zone heatmap with color-coded bars
- Anomaly alerts with severity levels
- Auto-refresh meta tag

---

## Dashboard Format 3: JSON Dashboard

### View as JSON

```bash
curl http://localhost:8000/stores/STORE_BLR_002/dashboard
```

### Output Example

```json
{
  "store_id": "STORE_BLR_002",
  "timestamp": "2026-04-22T16:28:20.436025Z",
  "event_count": 33,
  "metrics": {
    "unique_visitors": 5,
    "conversion_rate": 15.5,
    "avg_dwell_time_ms": 4200.5,
    "converted_visitors": 1,
    "avg_basket_value": 870.01,
    "max_queue_depth": 3
  },
  "zones": {
    "SKINCARE": 100.0,
    "BILLING": 50.0,
    "CHECKOUT": 20.0
  },
  "anomalies": [
    {
      "type": "QUEUE_SPIKE",
      "severity": "WARN",
      "message": "Queue depth reached 3"
    }
  ],
  "status": "live"
}
```

### Programmatic Access

```python
import requests
import json

response = requests.get('http://localhost:8000/stores/STORE_BLR_002/dashboard')
data = response.json()

print(f"Unique Visitors: {data['metrics']['unique_visitors']}")
print(f"Conversion Rate: {data['metrics']['conversion_rate']}%")
print(f"Anomalies: {len(data['anomalies'])}")
```

---

## Live Streaming Demo

### Simulate Real-Time Event Stream

```bash
#!/bin/bash
# save as stream_events.sh

STORE_ID="STORE_BLR_002"
API_URL="http://localhost:8000"

echo "Starting live event stream..."
echo "Dashboard: curl $API_URL/stores/$STORE_ID/dashboard/terminal"
echo ""

for i in {1..10}; do
  echo "Batch $i: Generating events..."
  
  # Generate new events
  python pipeline/run.py --num-frames 50 --output batch_$i.jsonl
  
  # Ingest to API
  curl -s -X POST $API_URL/events/ingest \
    -H "Content-Type: application/json" \
    -d @batch_$i.jsonl | jq '.events_ingested'
  
  # Show dashboard
  echo ""
  echo "=== DASHBOARD UPDATE ==="
  curl -s $API_URL/stores/$STORE_ID/dashboard/terminal | jq -r '.display'
  echo ""
  
  # Wait before next batch
  sleep 5
done
```

### Run the Stream

```bash
chmod +x stream_events.sh
./stream_events.sh
```

---

## Full End-to-End Demo

### Complete Workflow

```bash
#!/bin/bash
# save as demo.sh

set -e

STORE_ID="STORE_BLR_002"
API_URL="http://localhost:8000"

echo "=========================================="
echo "STORE INTELLIGENCE - LIVE DASHBOARD DEMO"
echo "=========================================="
echo ""

# Step 1: Start API
echo "Step 1: Starting API server..."
python -m uvicorn app.main:app --reload --port 8000 &
API_PID=$!
sleep 3

# Step 2: Generate events
echo "Step 2: Generating test events..."
python pipeline/run.py --num-frames 100 --output demo_events.jsonl

# Step 3: Ingest events
echo "Step 3: Ingesting events..."
curl -s -X POST $API_URL/events/ingest \
  -H "Content-Type: application/json" \
  -d @demo_events.jsonl | jq '.'

# Step 4: Show dashboards
echo ""
echo "Step 4: Displaying dashboards..."
echo ""

echo "=== TERMINAL DASHBOARD ==="
curl -s $API_URL/stores/$STORE_ID/dashboard/terminal | jq -r '.display'

echo ""
echo "=== JSON DASHBOARD ==="
curl -s $API_URL/stores/$STORE_ID/dashboard | jq '.'

echo ""
echo "=== WEB DASHBOARD ==="
echo "Open in browser: $API_URL/stores/$STORE_ID/dashboard.html"

# Cleanup
kill $API_PID
```

### Run the Demo

```bash
chmod +x demo.sh
./demo.sh
```

---

## Docker Deployment

### Run with Docker Compose

```bash
cd store-intelligence
docker-compose up
```

### Access Dashboard

```bash
# Terminal dashboard
curl http://localhost:8000/stores/STORE_BLR_002/dashboard/terminal

# Web dashboard
open http://localhost:8000/stores/STORE_BLR_002/dashboard.html

# JSON dashboard
curl http://localhost:8000/stores/STORE_BLR_002/dashboard
```

---

## Advanced: Custom Dashboard Script

### Python Script for Live Monitoring

```python
#!/usr/bin/env python3
"""
Live dashboard monitoring script
Displays real-time metrics and updates every 5 seconds
"""

import requests
import time
import os
from datetime import datetime

API_URL = "http://localhost:8000"
STORE_ID = "STORE_BLR_002"

def clear_screen():
    os.system('clear' if os.name == 'posix' else 'cls')

def get_dashboard():
    try:
        response = requests.get(f"{API_URL}/stores/{STORE_ID}/dashboard")
        return response.json()
    except Exception as e:
        return None

def display_dashboard(data):
    clear_screen()
    
    if not data:
        print("Error: Could not fetch dashboard data")
        return
    
    metrics = data.get('metrics', {})
    anomalies = data.get('anomalies', [])
    zones = data.get('zones', {})
    
    print("=" * 70)
    print("STORE INTELLIGENCE - LIVE DASHBOARD")
    print("=" * 70)
    print(f"Store: {data['store_id']}")
    print(f"Last Update: {data['timestamp']}")
    print(f"Events Processed: {data['event_count']}")
    print()
    
    print("REAL-TIME METRICS")
    print("-" * 70)
    print(f"  Unique Visitors:      {metrics.get('unique_visitors', 0)}")
    print(f"  Conversion Rate:      {metrics.get('conversion_rate', 0):.1f}%")
    print(f"  Avg Dwell Time:       {metrics.get('avg_dwell_time_ms', 0):.0f}ms")
    print(f"  Converted Visitors:   {metrics.get('converted_visitors', 0)}")
    print(f"  Avg Basket Value:     ₹{metrics.get('avg_basket_value', 0):.2f}")
    print(f"  Max Queue Depth:      {metrics.get('max_queue_depth', 0)}")
    print()
    
    print("ZONE HEATMAP")
    print("-" * 70)
    for zone, value in zones.items():
        bar = "█" * int(value / 5)
        print(f"  {zone:15} {bar:20} {value:.1f}%")
    print()
    
    if anomalies:
        print("ANOMALIES")
        print("-" * 70)
        for anomaly in anomalies:
            print(f"  [{anomaly['severity']}] {anomaly['message']}")
    else:
        print("ANOMALIES: None")
    
    print()
    print("=" * 70)
    print("Press Ctrl+C to exit. Refreshing in 5 seconds...")

def main():
    print("Starting live dashboard monitor...")
    print("Connecting to API at", API_URL)
    time.sleep(2)
    
    try:
        while True:
            data = get_dashboard()
            display_dashboard(data)
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nDashboard monitor stopped.")

if __name__ == "__main__":
    main()
```

### Run the Script

```bash
python live_dashboard.py
```

---

## Troubleshooting

### Issue: "Connection refused"

**Solution:** Make sure API is running
```bash
python -m uvicorn app.main:app --reload --port 8000
```

### Issue: "No events in dashboard"

**Solution:** Ingest events first
```bash
python pipeline/run.py --num-frames 100 --output events.jsonl
curl -X POST http://localhost:8000/events/ingest \
  -H "Content-Type: application/json" \
  -d @events.jsonl
```

### Issue: "Dashboard shows zero metrics"

**Solution:** Wait for events to be processed and check store_id
```bash
# Verify events were ingested
curl http://localhost:8000/stores/STORE_BLR_002/metrics

# Check available stores
curl http://localhost:8000/health
```

### Issue: "Web dashboard not loading"

**Solution:** Check browser console and verify API is accessible
```bash
# Test API connectivity
curl http://localhost:8000/health
```

---

## Performance Tips

### 1. Batch Events for Better Performance

```bash
# Instead of single events, batch them
python pipeline/run.py --num-frames 500 --output large_batch.jsonl
curl -X POST http://localhost:8000/events/ingest \
  -H "Content-Type: application/json" \
  -d @large_batch.jsonl
```

### 2. Use JSON Dashboard for Programmatic Access

```python
# More efficient than parsing HTML
import requests
response = requests.get('http://localhost:8000/stores/STORE_BLR_002/dashboard')
data = response.json()
```

### 3. Reduce Refresh Rate for Terminal Dashboard

```bash
# Refresh every 10 seconds instead of 5
while true; do
  clear
  curl -s http://localhost:8000/stores/STORE_BLR_002/dashboard/terminal | jq -r '.display'
  sleep 10
done
```

---

## Summary

**3 Ways to View Live Dashboard:**

| Format | Command | Best For |
|--------|---------|----------|
| **Terminal** | `curl http://localhost:8000/stores/STORE_BLR_002/dashboard/terminal` | Quick monitoring in terminal |
| **Web** | `open http://localhost:8000/stores/STORE_BLR_002/dashboard.html` | Visual monitoring in browser |
| **JSON** | `curl http://localhost:8000/stores/STORE_BLR_002/dashboard` | Programmatic access |

**Quick Start:**
```bash
# Terminal 1: Start API
python -m uvicorn app.main:app --reload --port 8000

# Terminal 2: Generate events
python pipeline/run.py --num-frames 100 --output events.jsonl

# Terminal 3: Ingest events
curl -X POST http://localhost:8000/events/ingest \
  -H "Content-Type: application/json" \
  -d @events.jsonl

# Terminal 4: View dashboard
curl http://localhost:8000/stores/STORE_BLR_002/dashboard/terminal
```

---

**Dashboard is now LIVE and updating in real-time!** 🎯
