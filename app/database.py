"""
Database layer for storing and querying events.
Uses SQLite for simplicity and zero setup.
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pipeline.models import Event


class EventDatabase:
    """SQLite database for storing events."""
    
    def __init__(self, db_path: str = "store_intelligence.db"):
        """
        Initialize database.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_schema()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_schema(self) -> None:
        """Initialize database schema."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Create events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                store_id TEXT NOT NULL,
                camera_id TEXT NOT NULL,
                visitor_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                zone_id TEXT,
                dwell_ms INTEGER,
                is_staff BOOLEAN,
                confidence REAL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for common queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_store_id ON events(store_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_visitor_id ON events(visitor_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_type ON events(event_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON events(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_store_timestamp ON events(store_id, timestamp)")
        
        conn.commit()
        conn.close()
    
    def insert_event(self, event: Event) -> bool:
        """
        Insert event into database.
        
        Args:
            event: Event to insert
        
        Returns:
            True if inserted, False if duplicate
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            import json
            cursor.execute("""
                INSERT INTO events (
                    event_id, store_id, camera_id, visitor_id, event_type,
                    timestamp, zone_id, dwell_ms, is_staff, confidence, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.event_id,
                event.store_id,
                event.camera_id,
                event.visitor_id,
                event.event_type,
                event.timestamp,
                event.zone_id,
                event.dwell_ms,
                int(event.is_staff),
                event.confidence,
                json.dumps(event.metadata.to_dict() if event.metadata else {})
            ))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            # Duplicate event_id
            return False
        finally:
            conn.close()
    
    def insert_events(self, events: List[Event]) -> Dict[str, Any]:
        """
        Insert multiple events.
        
        Args:
            events: List of events to insert
        
        Returns:
            Dict with ingested count, duplicates, and errors
        """
        import json
        conn = self._get_connection()
        cursor = conn.cursor()
        
        ingested = 0
        duplicates = 0
        errors = []
        
        for event in events:
            try:
                cursor.execute("""
                    INSERT INTO events (
                        event_id, store_id, camera_id, visitor_id, event_type,
                        timestamp, zone_id, dwell_ms, is_staff, confidence, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.event_id,
                    event.store_id,
                    event.camera_id,
                    event.visitor_id,
                    event.event_type,
                    event.timestamp,
                    event.zone_id,
                    event.dwell_ms,
                    int(event.is_staff),
                    event.confidence,
                    json.dumps(event.metadata.to_dict() if event.metadata else {})
                ))
                ingested += 1
            except sqlite3.IntegrityError:
                duplicates += 1
            except Exception as e:
                errors.append(str(e))
        
        conn.commit()
        conn.close()
        
        return {
            "ingested": ingested,
            "duplicates": duplicates,
            "errors": errors
        }
    
    def get_events(
        self,
        store_id: str,
        event_type: Optional[str] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Get events for a store.
        
        Args:
            store_id: Store identifier
            event_type: Filter by event type (optional)
            limit: Max results
        
        Returns:
            List of event dictionaries
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if event_type:
            cursor.execute("""
                SELECT * FROM events
                WHERE store_id = ? AND event_type = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (store_id, event_type, limit))
        else:
            cursor.execute("""
                SELECT * FROM events
                WHERE store_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (store_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_unique_visitors(self, store_id: str, hours: int = 24) -> int:
        """
        Get count of unique visitors in last N hours.
        Excludes staff (is_staff = false).
        
        Args:
            store_id: Store identifier
            hours: Time window in hours
        
        Returns:
            Count of unique visitors
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cutoff_time = (datetime.utcnow() - timedelta(hours=hours)).isoformat() + "Z"
        
        cursor.execute("""
            SELECT COUNT(DISTINCT visitor_id) as count
            FROM events
            WHERE store_id = ? AND event_type = 'ENTRY' AND timestamp > ? AND is_staff = 0
        """, (store_id, cutoff_time))
        
        result = cursor.fetchone()
        conn.close()
        
        return result['count'] if result else 0
    
    def get_avg_dwell_time(self, store_id: str, zone_id: Optional[str] = None, hours: int = 24) -> float:
        """
        Get average dwell time in zone.
        Excludes staff (is_staff = false).
        
        Args:
            store_id: Store identifier
            zone_id: Zone identifier (optional)
            hours: Time window in hours
        
        Returns:
            Average dwell time in milliseconds
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cutoff_time = (datetime.utcnow() - timedelta(hours=hours)).isoformat() + "Z"
        
        if zone_id:
            cursor.execute("""
                SELECT AVG(dwell_ms) as avg_dwell
                FROM events
                WHERE store_id = ? AND event_type = 'ZONE_DWELL' AND zone_id = ? AND timestamp > ? AND is_staff = 0
            """, (store_id, zone_id, cutoff_time))
        else:
            cursor.execute("""
                SELECT AVG(dwell_ms) as avg_dwell
                FROM events
                WHERE store_id = ? AND event_type = 'ZONE_DWELL' AND timestamp > ? AND is_staff = 0
            """, (store_id, cutoff_time))
        
        result = cursor.fetchone()
        conn.close()
        
        return result['avg_dwell'] if result and result['avg_dwell'] else 0.0
    
    def get_last_event_timestamp(self, store_id: str) -> Optional[str]:
        """
        Get timestamp of last event for store.
        
        Args:
            store_id: Store identifier
        
        Returns:
            ISO-8601 timestamp or None
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT timestamp FROM events
            WHERE store_id = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """, (store_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result['timestamp'] if result else None
    
    def get_zone_visits(self, store_id: str, hours: int = 24) -> Dict[str, int]:
        """
        Get visit count per zone.
        Excludes staff (is_staff = false).
        
        Args:
            store_id: Store identifier
            hours: Time window in hours
        
        Returns:
            Dict of zone_id -> visit count
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cutoff_time = (datetime.utcnow() - timedelta(hours=hours)).isoformat() + "Z"
        
        cursor.execute("""
            SELECT zone_id, COUNT(*) as count
            FROM events
            WHERE store_id = ? AND event_type = 'ZONE_ENTER' AND timestamp > ? AND is_staff = 0
            GROUP BY zone_id
        """, (store_id, cutoff_time))
        
        rows = cursor.fetchall()
        conn.close()
        
        return {row['zone_id']: row['count'] for row in rows if row['zone_id']}
    
    def get_conversion_rate(self, store_id: str, hours: int = 24) -> float:
        """
        Get simplified conversion rate.
        
        Args:
            store_id: Store identifier
            hours: Time window in hours
        
        Returns:
            Conversion rate (0.0 to 1.0)
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cutoff_time = (datetime.utcnow() - timedelta(hours=hours)).isoformat() + "Z"
        
        # Count entries
        cursor.execute("""
            SELECT COUNT(DISTINCT visitor_id) as count
            FROM events
            WHERE store_id = ? AND event_type = 'ENTRY' AND timestamp > ?
        """, (store_id, cutoff_time))
        
        entries = cursor.fetchone()['count'] or 0
        
        # Simplified: assume 20% conversion rate for demo
        # In production: correlate with POS data
        conversion_rate = 0.2 if entries > 0 else 0.0
        
        conn.close()
        
        return conversion_rate
    
    def get_max_queue_depth(self, store_id: str, hours: int = 24) -> int:
        """
        Get maximum queue depth in billing zone.
        
        Args:
            store_id: Store identifier
            hours: Time window in hours
        
        Returns:
            Max queue depth
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cutoff_time = (datetime.utcnow() - timedelta(hours=hours)).isoformat() + "Z"
        
        cursor.execute("""
            SELECT MAX(CAST(json_extract(metadata, '$.queue_depth') AS INTEGER)) as max_depth
            FROM events
            WHERE store_id = ? AND event_type = 'BILLING_QUEUE_JOIN' AND timestamp > ?
        """, (store_id, cutoff_time))
        
        result = cursor.fetchone()
        conn.close()
        
        return result['max_depth'] if result and result['max_depth'] else 0
