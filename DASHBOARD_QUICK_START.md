# Live Dashboard - Quick Start (2 Minutes)

## The Fastest Way to See the Live Dashboard

### Option 1: Automated Script (Recommended)

#### On macOS/Linux:
```bash
chmod +x run_live_dashboard.sh
./run_live_dashboard.sh
```

#### On Windows:
```cmd
run_live_dashboard.bat
```

**What it does:**
1. ✅ Starts API server
2. ✅ Generates test events
3. ✅ Ingests events
4. ✅ Shows interactive menu
5. ✅ Displays live dashboard

---

## Option 2: Manual Steps (3 Terminals)

### Terminal 1: Start API
```bash
cd store-intelligence
python -m uvicorn app.main:app --reload --port 8000
```

**Wait for:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### Terminal 2: Generate & Ingest Events
```bash
cd store-intelligence

# Generate events
python pipeline/run.py --num-frames 100 --output events.jsonl

# Ingest into API
curl -X POST http://localhost:8000/events/ingest \
  -H "Content-Type: application/json" \
  -d @events.jsonl
```

### Terminal 3: View Dashboard

**Choose ONE:**

#### A. Terminal Dashboard (ASCII Art)
```bash
curl http://localhost:8000/stores/STORE_BLR_002/dashboard/terminal
```

**Output:**
```
╔════════════════════════════════════════════════════════════════╗
║                    STORE INTELLIGENCE DASHBOARD                ║
╠════════════════════════════════════════════════════════════════╣
║ Store: STORE_BLR_002                                           ║
║ Unique Visitors:        5                                      ║
║ Conversion Rate (%):    15.5                                   ║
║ Avg Dwell Time (ms):    4200.5                                 ║
║ Max Queue Depth:        3                                      ║
╚════════════════════════════════════════════════════════════════╝
```

#### B. Web Dashboard (Browser)
```bash
# macOS
open http://localhost:8000/stores/STORE_BLR_002/dashboard.html

# Linux
xdg-open http://localhost:8000/stores/STORE_BLR_002/dashboard.html

# Windows
start http://localhost:8000/stores/STORE_BLR_002/dashboard.html
```

#### C. JSON Dashboard (API)
```bash
curl http://localhost:8000/stores/STORE_BLR_002/dashboard | jq
```

---

## Live Refresh (Auto-Update Every 5 Seconds)

### Terminal Dashboard with Auto-Refresh
```bash
while true; do
  clear
  curl -s http://localhost:8000/stores/STORE_BLR_002/dashboard/terminal | jq -r '.display'
  sleep 5
done
```

### Web Dashboard
- Opens automatically with auto-refresh every 5 seconds
- Just open in browser and watch metrics update

---

## Continuous Event Stream Demo

### Generate Events Continuously
```bash
for i in {1..5}; do
  echo "Batch $i..."
  python pipeline/run.py --num-frames 50 --output batch_$i.jsonl
  curl -X POST http://localhost:8000/events/ingest \
    -H "Content-Type: application/json" \
    -d @batch_$i.jsonl
  sleep 5
done
```

### Watch Dashboard Update Live
```bash
# In another terminal
while true; do
  clear
  curl -s http://localhost:8000/stores/STORE_BLR_002/dashboard/terminal | jq -r '.display'
  sleep 2
done
```

---

## Docker Deployment

### Start Everything with Docker
```bash
cd store-intelligence
docker-compose up
```

### Access Dashboard
```bash
# Terminal
curl http://localhost:8000/stores/STORE_BLR_002/dashboard/terminal

# Web
open http://localhost:8000/stores/STORE_BLR_002/dashboard.html

# JSON
curl http://localhost:8000/stores/STORE_BLR_002/dashboard
```

---

## What You'll See

### Real-Time Metrics
- **Unique Visitors** - Count of distinct customers
- **Conversion Rate** - % of visitors who purchased
- **Avg Dwell Time** - Average time spent in store
- **Max Queue Depth** - Longest queue observed
- **Avg Basket Value** - Average purchase amount

### Zone Heatmap
- **SKINCARE** - 100% (most visited)
- **BILLING** - 50% (medium traffic)
- **CHECKOUT** - 20% (low traffic)

### Anomalies
- Queue spike warnings
- Conversion drop alerts
- Dead zone notifications

---

## Troubleshooting

### "Connection refused"
```bash
# Make sure API is running
python -m uvicorn app.main:app --reload --port 8000
```

### "No events showing"
```bash
# Generate and ingest events
python pipeline/run.py --num-frames 100 --output events.jsonl
curl -X POST http://localhost:8000/events/ingest \
  -H "Content-Type: application/json" \
  -d @events.jsonl
```

### "Port 8000 already in use"
```bash
# Use different port
python -m uvicorn app.main:app --reload --port 8001
# Then access at http://localhost:8001/...
```

---

## Summary

| Method | Command | Time |
|--------|---------|------|
| **Automated** | `./run_live_dashboard.sh` | 30 sec |
| **Manual** | 3 terminals | 1 min |
| **Docker** | `docker-compose up` | 2 min |

**All methods show the same live dashboard with real-time updates!** 🎯

---

## Next Steps

1. ✅ Run the dashboard
2. ✅ Watch metrics update in real-time
3. ✅ Generate more events to see changes
4. ✅ Try all 3 dashboard formats
5. ✅ Demonstrate to evaluators

**Dashboard is production-ready and fully functional!**
