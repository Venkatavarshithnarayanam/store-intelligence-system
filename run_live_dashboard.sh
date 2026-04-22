#!/bin/bash
# Live Dashboard Quick Start Script
# Runs the complete end-to-end demo in one command

set -e

STORE_ID="STORE_BLR_002"
API_URL="http://localhost:8000"
API_PORT=8000

echo "=========================================="
echo "STORE INTELLIGENCE - LIVE DASHBOARD"
echo "=========================================="
echo ""

# Check if API is already running
if lsof -Pi :$API_PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "API already running on port $API_PORT"
    API_RUNNING=true
else
    echo "Starting API server on port $API_PORT..."
    python -m uvicorn app.main:app --reload --port $API_PORT > /tmp/api.log 2>&1 &
    API_PID=$!
    echo "API PID: $API_PID"
    sleep 3
    API_RUNNING=false
fi

echo ""
echo "Generating test events..."
python pipeline/run.py --num-frames 100 --output demo_events.jsonl

echo ""
echo "Ingesting events into API..."
INGEST_RESULT=$(curl -s -X POST $API_URL/events/ingest \
  -H "Content-Type: application/json" \
  -d @demo_events.jsonl)

EVENTS_INGESTED=$(echo $INGEST_RESULT | jq '.events_ingested')
echo "Events ingested: $EVENTS_INGESTED"

echo ""
echo "=========================================="
echo "LIVE DASHBOARD - CHOOSE FORMAT"
echo "=========================================="
echo ""
echo "1. Terminal Dashboard (ASCII art)"
echo "2. Web Dashboard (HTML in browser)"
echo "3. JSON Dashboard (API endpoint)"
echo "4. Live Stream (continuous updates)"
echo "5. Exit"
echo ""
read -p "Select option (1-5): " choice

case $choice in
    1)
        echo ""
        echo "=== TERMINAL DASHBOARD ==="
        curl -s $API_URL/stores/$STORE_ID/dashboard/terminal | jq -r '.display'
        echo ""
        read -p "Auto-refresh? (y/n): " refresh
        if [ "$refresh" = "y" ]; then
            echo "Refreshing every 5 seconds (Ctrl+C to stop)..."
            while true; do
                clear
                curl -s $API_URL/stores/$STORE_ID/dashboard/terminal | jq -r '.display'
                sleep 5
            done
        fi
        ;;
    2)
        echo ""
        echo "=== WEB DASHBOARD ==="
        echo "Opening in browser: $API_URL/stores/$STORE_ID/dashboard.html"
        if command -v open &> /dev/null; then
            open "$API_URL/stores/$STORE_ID/dashboard.html"
        elif command -v xdg-open &> /dev/null; then
            xdg-open "$API_URL/stores/$STORE_ID/dashboard.html"
        else
            echo "Please open manually: $API_URL/stores/$STORE_ID/dashboard.html"
        fi
        ;;
    3)
        echo ""
        echo "=== JSON DASHBOARD ==="
        curl -s $API_URL/stores/$STORE_ID/dashboard | jq '.'
        ;;
    4)
        echo ""
        echo "=== LIVE STREAM (Continuous Updates) ==="
        echo "Generating and ingesting events continuously..."
        echo "Press Ctrl+C to stop"
        echo ""
        
        for i in {1..10}; do
            echo "Batch $i: Generating events..."
            python pipeline/run.py --num-frames 50 --output batch_$i.jsonl
            
            echo "Ingesting batch $i..."
            curl -s -X POST $API_URL/events/ingest \
              -H "Content-Type: application/json" \
              -d @batch_$i.jsonl | jq '.events_ingested'
            
            echo ""
            echo "=== DASHBOARD UPDATE ==="
            curl -s $API_URL/stores/$STORE_ID/dashboard/terminal | jq -r '.display'
            echo ""
            
            sleep 5
        done
        ;;
    5)
        echo "Exiting..."
        ;;
    *)
        echo "Invalid option"
        ;;
esac

echo ""
echo "=========================================="
echo "Dashboard session ended"
echo "=========================================="

# Cleanup
if [ "$API_RUNNING" = false ]; then
    echo "Stopping API server..."
    kill $API_PID 2>/dev/null || true
fi

echo "Done!"
