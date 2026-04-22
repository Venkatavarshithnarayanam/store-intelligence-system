"""
Real-time dashboard: displays live metrics as events flow in.
Supports both terminal output and web UI.
"""

from typing import Dict, Any, Optional
from datetime import datetime
import json


class DashboardService:
    """Manages real-time dashboard updates."""
    
    def __init__(self):
        """Initialize dashboard service."""
        self.current_metrics: Dict[str, Any] = {}
        self.event_count = 0
        self.last_update = None
    
    def update_metrics(self, store_id: str, metrics: Dict[str, Any]) -> None:
        """
        Update dashboard with new metrics.
        
        Args:
            store_id: Store identifier
            metrics: Metrics dictionary
        """
        self.current_metrics[store_id] = metrics
        self.last_update = datetime.utcnow().isoformat() + "Z"
    
    def increment_event_count(self) -> None:
        """Increment event counter."""
        self.event_count += 1
    
    def get_terminal_display(self, store_id: str) -> str:
        """
        Get terminal-friendly dashboard display.
        
        Args:
            store_id: Store identifier
        
        Returns:
            Formatted string for terminal output
        """
        if store_id not in self.current_metrics:
            return f"No data for {store_id}"
        
        metrics = self.current_metrics[store_id]
        
        display = f"""
╔════════════════════════════════════════════════════════════════╗
║                    STORE INTELLIGENCE DASHBOARD                ║
╠════════════════════════════════════════════════════════════════╣
║ Store: {store_id:<55} ║
║ Last Update: {self.last_update or 'N/A':<48} ║
║ Total Events Processed: {self.event_count:<40} ║
╠════════════════════════════════════════════════════════════════╣
║ REAL-TIME METRICS                                              ║
╠════════════════════════════════════════════════════════════════╣
║ Unique Visitors:        {metrics.get('unique_visitors', 0):<40} ║
║ Avg Dwell Time (ms):    {metrics.get('avg_dwell_time_ms', 0):<40} ║
║ Conversion Rate (%):    {metrics.get('conversion_rate', 0):<40} ║
║ Converted Visitors:     {metrics.get('converted_visitors', 0):<40} ║
║ Avg Basket Value (₹):   {metrics.get('avg_basket_value', 0):<40} ║
║ Max Queue Depth:        {metrics.get('max_queue_depth', 0):<40} ║
╠════════════════════════════════════════════════════════════════╣
║ ZONE HEATMAP                                                   ║
╠════════════════════════════════════════════════════════════════╣
"""
        
        zones = metrics.get('zones', {})
        for zone_id, score in zones.items():
            display += f"║ {zone_id:<30} {'█' * int(score/5):<30} {score:.1f}% ║\n"
        
        display += """╠════════════════════════════════════════════════════════════════╣
║ ANOMALIES                                                      ║
╠════════════════════════════════════════════════════════════════╣
"""
        
        anomalies = metrics.get('anomalies', [])
        if anomalies:
            for anomaly in anomalies[:3]:  # Show top 3 anomalies
                severity = anomaly.get('severity', 'INFO')
                msg = anomaly.get('message', '')[:50]
                display += f"║ [{severity}] {msg:<55} ║\n"
        else:
            display += "║ No anomalies detected                                          ║\n"
        
        display += """╚════════════════════════════════════════════════════════════════╝
"""
        
        return display
    
    def get_json_display(self, store_id: str) -> Dict[str, Any]:
        """
        Get JSON-formatted dashboard data.
        
        Args:
            store_id: Store identifier
        
        Returns:
            Dictionary with dashboard data
        """
        return {
            "store_id": store_id,
            "timestamp": self.last_update,
            "event_count": self.event_count,
            "metrics": self.current_metrics.get(store_id, {}),
            "status": "live"
        }


class WebDashboardGenerator:
    """Generates HTML for web-based dashboard."""
    
    @staticmethod
    def generate_html(store_id: str, metrics: Dict[str, Any]) -> str:
        """
        Generate HTML dashboard.
        
        Args:
            store_id: Store identifier
            metrics: Metrics dictionary
        
        Returns:
            HTML string
        """
        zones_html = ""
        for zone_id, score in metrics.get('zones', {}).items():
            zones_html += f"""
            <div class="zone-item">
                <span class="zone-name">{zone_id}</span>
                <div class="zone-bar">
                    <div class="zone-fill" style="width: {score}%"></div>
                </div>
                <span class="zone-score">{score:.1f}%</span>
            </div>
            """
        
        anomalies_html = ""
        for anomaly in metrics.get('anomalies', [])[:5]:
            severity_class = anomaly.get('severity', 'info').lower()
            anomalies_html += f"""
            <div class="anomaly-item {severity_class}">
                <span class="anomaly-type">{anomaly.get('type', 'UNKNOWN')}</span>
                <span class="anomaly-message">{anomaly.get('message', '')}</span>
            </div>
            """
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Store Intelligence Dashboard - {store_id}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        .header {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        
        .header h1 {{
            color: #333;
            margin-bottom: 10px;
        }}
        
        .header p {{
            color: #666;
            font-size: 14px;
        }}
        
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}
        
        .metric-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        
        .metric-label {{
            color: #666;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }}
        
        .metric-value {{
            color: #333;
            font-size: 32px;
            font-weight: bold;
        }}
        
        .metric-unit {{
            color: #999;
            font-size: 14px;
            margin-left: 5px;
        }}
        
        .section {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        
        .section-title {{
            color: #333;
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 15px;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}
        
        .zone-item {{
            display: flex;
            align-items: center;
            margin-bottom: 15px;
            gap: 15px;
        }}
        
        .zone-name {{
            min-width: 100px;
            font-weight: 500;
            color: #333;
        }}
        
        .zone-bar {{
            flex: 1;
            height: 20px;
            background: #eee;
            border-radius: 10px;
            overflow: hidden;
        }}
        
        .zone-fill {{
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            transition: width 0.3s ease;
        }}
        
        .zone-score {{
            min-width: 50px;
            text-align: right;
            color: #666;
            font-size: 12px;
        }}
        
        .anomaly-item {{
            padding: 12px;
            margin-bottom: 10px;
            border-left: 4px solid #999;
            background: #f5f5f5;
            border-radius: 4px;
        }}
        
        .anomaly-item.warn {{
            border-left-color: #ff9800;
            background: #fff3e0;
        }}
        
        .anomaly-item.critical {{
            border-left-color: #f44336;
            background: #ffebee;
        }}
        
        .anomaly-type {{
            display: inline-block;
            font-weight: bold;
            margin-right: 10px;
            color: #333;
        }}
        
        .anomaly-message {{
            color: #666;
            font-size: 14px;
        }}
        
        .refresh-indicator {{
            display: inline-block;
            width: 10px;
            height: 10px;
            background: #4caf50;
            border-radius: 50%;
            margin-right: 5px;
            animation: pulse 2s infinite;
        }}
        
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1><span class="refresh-indicator"></span>Store Intelligence Dashboard</h1>
            <p>Store: <strong>{store_id}</strong> | Last Update: <strong>{datetime.utcnow().isoformat()}Z</strong></p>
        </div>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">Unique Visitors</div>
                <div class="metric-value">{metrics.get('unique_visitors', 0)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Conversion Rate</div>
                <div class="metric-value">{metrics.get('conversion_rate', 0)}<span class="metric-unit">%</span></div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Avg Dwell Time</div>
                <div class="metric-value">{metrics.get('avg_dwell_time_ms', 0)}<span class="metric-unit">ms</span></div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Avg Basket Value</div>
                <div class="metric-value">₹{metrics.get('avg_basket_value', 0)}</div>
            </div>
        </div>
        
        <div class="section">
            <div class="section-title">Zone Heatmap</div>
            {zones_html}
        </div>
        
        <div class="section">
            <div class="section-title">Active Anomalies</div>
            {anomalies_html if anomalies_html else '<p style="color: #999;">No anomalies detected</p>'}
        </div>
    </div>
    
    <script>
        // Auto-refresh every 5 seconds
        setInterval(() => {{
            location.reload();
        }}, 5000);
    </script>
</body>
</html>
"""
        
        return html
