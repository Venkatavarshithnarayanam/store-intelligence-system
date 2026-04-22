"""
POS transaction correlation: match visitor sessions to transactions.
Converts raw POS data into conversion metrics.
"""

import csv
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class POSTransaction:
    """Represents a POS transaction."""
    store_id: str
    transaction_id: str
    timestamp: str
    basket_value: float
    
    def get_datetime(self) -> datetime:
        """Parse ISO-8601 timestamp."""
        return datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))


class POSCorrelationService:
    """Correlates visitor sessions with POS transactions."""
    
    def __init__(self, pos_csv_path: str = "data/pos_transactions.csv"):
        """
        Initialize POS correlation service.
        
        Args:
            pos_csv_path: Path to POS transactions CSV file
        """
        self.pos_csv_path = pos_csv_path
        self.transactions: Dict[str, List[POSTransaction]] = {}  # store_id -> transactions
        self._load_transactions()
    
    def _load_transactions(self) -> None:
        """Load POS transactions from CSV."""
        try:
            with open(self.pos_csv_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    store_id = row['store_id']
                    transaction = POSTransaction(
                        store_id=store_id,
                        transaction_id=row['transaction_id'],
                        timestamp=row['timestamp'],
                        basket_value=float(row['basket_value_inr'])
                    )
                    
                    if store_id not in self.transactions:
                        self.transactions[store_id] = []
                    self.transactions[store_id].append(transaction)
        except FileNotFoundError:
            # POS file not available, continue without it
            pass
    
    def find_converted_visitors(
        self,
        store_id: str,
        billing_zone_events: List[Dict],
        time_window_minutes: int = 5
    ) -> Tuple[int, float]:
        """
        Find visitors who converted (made a purchase).
        
        Args:
            store_id: Store identifier
            billing_zone_events: Events from billing zone (ZONE_ENTER, ZONE_EXIT)
            time_window_minutes: Time window to match visitor to transaction
        
        Returns:
            (converted_count, total_basket_value)
        """
        if store_id not in self.transactions:
            return 0, 0.0
        
        converted_visitors = set()
        total_value = 0.0
        
        # Get transactions for this store
        store_transactions = self.transactions[store_id]
        
        # For each transaction, find visitors in billing zone within time window
        for transaction in store_transactions:
            txn_time = transaction.get_datetime()
            window_start = txn_time - timedelta(minutes=time_window_minutes)
            window_end = txn_time
            
            # Find visitors in billing zone during this window
            for event in billing_zone_events:
                try:
                    event_time = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
                    
                    # Check if event is in time window
                    if window_start <= event_time <= window_end:
                        # Check if event is a billing zone event
                        if event.get('zone_id') == 'BILLING' or event.get('event_type') in ['BILLING_QUEUE_JOIN', 'ZONE_ENTER']:
                            visitor_id = event.get('visitor_id')
                            if visitor_id and visitor_id not in converted_visitors:
                                converted_visitors.add(visitor_id)
                                total_value += transaction.basket_value
                except (ValueError, KeyError):
                    continue
        
        return len(converted_visitors), total_value
    
    def get_conversion_rate(
        self,
        store_id: str,
        unique_visitors: int,
        billing_zone_events: List[Dict]
    ) -> Dict[str, float]:
        """
        Calculate conversion rate and metrics.
        
        Args:
            store_id: Store identifier
            unique_visitors: Total unique visitors
            billing_zone_events: Events from billing zone
        
        Returns:
            Dict with conversion_rate, converted_count, avg_basket_value
        """
        converted_count, total_value = self.find_converted_visitors(store_id, billing_zone_events)
        
        conversion_rate = (converted_count / unique_visitors * 100) if unique_visitors > 0 else 0.0
        avg_basket_value = (total_value / converted_count) if converted_count > 0 else 0.0
        
        return {
            "conversion_rate": round(conversion_rate, 2),
            "converted_visitors": converted_count,
            "total_basket_value": round(total_value, 2),
            "avg_basket_value": round(avg_basket_value, 2),
            "unique_visitors": unique_visitors
        }
