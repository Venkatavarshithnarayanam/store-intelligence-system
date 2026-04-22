"""
Live terminal dashboard for Store Intelligence.
Displays real-time metrics from the API.
"""

import requests
import time
import os
import sys
from datetime import datetime


class LiveDashboard:
    """Simple terminal dashboard that polls metrics every 2 seconds."""
    
    def __init__(self, api_url: str = "http://localhost:8000", store_id: str = "STORE_BLR_002"):
        """
        Initialize dashboard.
        
        Args:
            api_url: Base URL of the API
            store_id: Store ID to monitor
        """
        self.api_url = api_url
        self.store_id = store_id
        self.metrics_endpoint = f"{api_url}/stores/{store_id}/metrics"
        self.running = True
    
    def clear_screen(self):
        """Clear terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def fetch_metrics(self) -> dict:
        """Fetch metrics from API."""
        try:
            response = requests.get(self.metrics_endpoint, timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                return None
        except requests.exceptions.RequestException as e:
            return None
    
    def format_metrics(self, metrics: dict) -> str:
        """Format metrics for display."""
        if metrics is None:
            return "❌ Unable to connect to API\nMake sure the API is running: python -m uvicorn app.main:app --port 8000"
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        output = f"""
╔════════════════════════════════════════════════════════════╗
║           STORE INTELLIGENCE - LIVE DASHBOARD              ║
╚════════════════════════════════════════════════════════════╝

Store ID:              {metrics.get('store_id', 'N/A')}
Time Window:           {metrics.get('time_window_hours', 24)} hours

📊 METRICS
─────────────────────────────────────────────────────────────
Unique Visitors:       {metrics.get('unique_visitors', 0)}
Conversion Rate:       {metrics.get('conversion_rate', 0):.2f}%
Avg Dwell Time:        {metrics.get('avg_dwell_time_ms', 0):.0f} ms
Max Queue Depth:       {metrics.get('max_queue_depth', 0)}

⏱️  Last Updated:       {timestamp}
─────────────────────────────────────────────────────────────
"""
        return output
    
    def run(self, interval: int = 2):
        """
        Run the dashboard.
        
        Args:
            interval: Update interval in seconds
        """
        print("Starting Live Dashboard...")
        print(f"Monitoring: {self.store_id}")
        print(f"API: {self.api_url}")
        print("Press Ctrl+C to stop\n")
        
        time.sleep(2)  # Give user time to read startup message
        
        try:
            while self.running:
                self.clear_screen()
                
                metrics = self.fetch_metrics()
                output = self.format_metrics(metrics)
                print(output)
                
                # Show connection status
                if metrics:
                    print("✓ Connected to API")
                else:
                    print("✗ Waiting for API connection...")
                
                time.sleep(interval)
        
        except KeyboardInterrupt:
            self.clear_screen()
            print("\n✓ Dashboard stopped\n")
            sys.exit(0)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Live dashboard for Store Intelligence")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--store-id", default="STORE_BLR_002", help="Store ID to monitor")
    parser.add_argument("--interval", type=int, default=2, help="Update interval in seconds")
    
    args = parser.parse_args()
    
    dashboard = LiveDashboard(api_url=args.api_url, store_id=args.store_id)
    dashboard.run(interval=args.interval)


if __name__ == "__main__":
    main()
