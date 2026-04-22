#!/usr/bin/env python3
"""Test edge cases for Store Intelligence System."""

from app.database import EventDatabase
from app.metrics import MetricsService
from pipeline.models import Event, EventMetadata
import os

print('Testing Edge Cases...\n')

# Create test database
db_path = 'test_edge_cases.db'
if os.path.exists(db_path):
    os.remove(db_path)

db = EventDatabase(db_path)
metrics = MetricsService(db)

# TEST 1: Empty store
print('1. Testing empty store...')
empty_metrics = metrics.get_store_metrics('STORE_EMPTY', hours=24)
assert empty_metrics['unique_visitors'] == 0
assert empty_metrics['avg_dwell_time_ms'] == 0.0
assert empty_metrics['conversion_rate'] == 0.0
assert empty_metrics['max_queue_depth'] == 0
print('   ✅ Empty store handled correctly\n')

# TEST 2: All staff events
print('2. Testing all-staff events...')
for i in range(5):
    event = Event(
        event_id=f'staff-{i}',
        store_id='STORE_STAFF',
        camera_id='CAM_1',
        visitor_id=f'STAFF_{i}',
        event_type='ENTRY',
        timestamp='2026-04-22T10:00:00Z',
        is_staff=True,
        confidence=0.95
    )
    db.insert_event(event)

staff_metrics = metrics.get_store_metrics('STORE_STAFF', hours=24)
assert staff_metrics['unique_visitors'] == 0, f"Expected 0, got {staff_metrics['unique_visitors']}"
print('   ✅ Staff events excluded correctly\n')

# TEST 3: Zero purchases
print('3. Testing zero purchases...')
for i in range(10):
    event = Event(
        event_id=f'entry-{i}',
        store_id='STORE_NO_PURCHASE',
        camera_id='CAM_1',
        visitor_id=f'VIS_{i}',
        event_type='ENTRY',
        timestamp='2026-04-22T10:00:00Z',
        is_staff=False,
        confidence=0.9
    )
    db.insert_event(event)

purchase_metrics = metrics.get_store_metrics('STORE_NO_PURCHASE', hours=24)
assert purchase_metrics['unique_visitors'] == 10
assert purchase_metrics['conversion_rate'] == 0.0
print('   ✅ Zero purchases handled correctly\n')

# TEST 4: Re-entry handling
print('4. Testing re-entry handling...')
# First, insert an entry event
entry_event = Event(
    event_id='entry-reentry-1',
    store_id='STORE_REENTRY',
    camera_id='CAM_1',
    visitor_id='VIS_REENTRY',
    event_type='ENTRY',
    timestamp='2026-04-22T10:00:00Z',
    is_staff=False,
    confidence=0.9
)
db.insert_event(entry_event)

# Then exit
exit_event = Event(
    event_id='exit-reentry-1',
    store_id='STORE_REENTRY',
    camera_id='CAM_1',
    visitor_id='VIS_REENTRY',
    event_type='EXIT',
    timestamp='2026-04-22T10:10:00Z',
    is_staff=False,
    confidence=0.9
)
db.insert_event(exit_event)

# Then re-entry
reentry_event = Event(
    event_id='reentry-1',
    store_id='STORE_REENTRY',
    camera_id='CAM_1',
    visitor_id='VIS_REENTRY',
    event_type='REENTRY',
    timestamp='2026-04-22T10:20:00Z',
    is_staff=False,
    confidence=0.9
)
db.insert_event(reentry_event)

reentry_metrics = metrics.get_store_metrics('STORE_REENTRY', hours=24)
# Should count the initial ENTRY event
assert reentry_metrics['unique_visitors'] == 1, f"Expected 1, got {reentry_metrics['unique_visitors']}"
print('   ✅ Re-entry handled correctly\n')

# Cleanup
os.remove(db_path)

print('=' * 60)
print('✅ ALL EDGE CASE TESTS PASSED!')
print('=' * 60)
