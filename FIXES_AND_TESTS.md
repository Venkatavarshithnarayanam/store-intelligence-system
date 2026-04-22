# Fixes and Tests - Store Intelligence System

## Date: April 22, 2026

---

## ISSUE 1: Staff Filtering in API Queries ✅ FIXED

### Problem
Database queries for visitor counts did not explicitly filter out staff events (`is_staff = false`). This could inflate visitor counts and conversion rates.

### Solution
Added `AND is_staff = 0` clause to all visitor-related database queries:

#### Files Modified
- `app/database.py`

#### Changes Made

**1. get_unique_visitors()**
```sql
-- BEFORE
SELECT COUNT(DISTINCT visitor_id) as count
FROM events
WHERE store_id = ? AND event_type = 'ENTRY' AND timestamp > ?

-- AFTER
SELECT COUNT(DISTINCT visitor_id) as count
FROM events
WHERE store_id = ? AND event_type = 'ENTRY' AND timestamp > ? AND is_staff = 0
```

**2. get_avg_dwell_time()**
```sql
-- BEFORE
SELECT AVG(dwell_ms) as avg_dwell
FROM events
WHERE store_id = ? AND event_type = 'ZONE_DWELL' AND timestamp > ?

-- AFTER
SELECT AVG(dwell_ms) as avg_dwell
FROM events
WHERE store_id = ? AND event_type = 'ZONE_DWELL' AND timestamp > ? AND is_staff = 0
```

**3. get_zone_visits()**
```sql
-- BEFORE
SELECT zone_id, COUNT(*) as count
FROM events
WHERE store_id = ? AND event_type = 'ZONE_ENTER' AND timestamp > ?
GROUP BY zone_id

-- AFTER
SELECT zone_id, COUNT(*) as count
FROM events
WHERE store_id = ? AND event_type = 'ZONE_ENTER' AND timestamp > ? AND is_staff = 0
GROUP BY zone_id
```

#### Test Results
```
✅ Staff filtering works correctly!
Unique visitors (staff excluded): 5
Staff events: 3 (correctly excluded)
```

---

## ISSUE 2: Edge Case Tests ✅ ADDED

### Problem
Test suite was missing edge case tests for:
- Empty store (no events)
- All-staff events (should be excluded)
- Zero purchases (visitors but no conversions)
- Re-entry handling (same visitor, multiple sessions)

### Solution
Added comprehensive edge case tests to `tests/test_api.py` and created `test_edge_cases.py`

#### Files Modified
- `tests/test_api.py` - Added TestEdgeCases class
- `test_edge_cases.py` - New comprehensive edge case test file

#### Test Cases Added

**1. test_empty_store()**
```python
# Verify metrics for store with no events
response = client.get("/stores/STORE_EMPTY/metrics")
assert response.json()["unique_visitors"] == 0
assert response.json()["avg_dwell_time_ms"] == 0.0
assert response.json()["conversion_rate"] == 0.0
assert response.json()["max_queue_depth"] == 0
```

**2. test_all_staff_events()**
```python
# Ingest 5 staff events
# Verify metrics show 0 visitors (staff excluded)
assert response.json()["unique_visitors"] == 0
```

**3. test_zero_purchases()**
```python
# Ingest 10 entry events (no billing/purchase)
# Verify metrics show 10 visitors but 0 conversion rate
assert response.json()["unique_visitors"] == 10
assert response.json()["conversion_rate"] == 0.0
```

**4. test_reentry_handling()**
```python
# Ingest: ENTRY → EXIT → REENTRY
# Verify funnel counts correctly
assert response.json()["funnel"]["entry"] >= 1
```

#### Test Results
```
Testing Edge Cases...

1. Testing empty store...
   ✅ Empty store handled correctly

2. Testing all-staff events...
   ✅ Staff events excluded correctly

3. Testing zero purchases...
   ✅ Zero purchases handled correctly

4. Testing re-entry handling...
   ✅ Re-entry handled correctly

============================================================
✅ ALL EDGE CASE TESTS PASSED!
============================================================
```

---

## Additional Fixes

### Issue 3: Metadata Serialization ✅ FIXED

**Problem:** Metadata dict was not being JSON serialized before insertion into SQLite.

**Solution:** Added JSON serialization in `insert_event()` and `insert_events()`:
```python
import json
json.dumps(event.metadata.to_dict() if event.metadata else {})
```

Also converted `is_staff` boolean to integer (0/1) for SQLite compatibility:
```python
int(event.is_staff)
```

---

## Validation Results

### Quick Validation Script
```
✅ ALL VALIDATION TESTS PASSED!

📊 SYSTEM COMPONENTS:
✓ Detection pipeline (mock + YOLOv8 ready)
✓ Centroid tracker
✓ Cross-camera deduplication
✓ Event emission
✓ Dashboard services (terminal, web, JSON)
✓ Pipeline integration

8/8 tests passed
```

### Edge Case Tests
```
✅ ALL EDGE CASE TESTS PASSED!

4/4 edge case tests passed:
✓ Empty store
✓ All-staff events
✓ Zero purchases
✓ Re-entry handling
```

### Staff Filtering Test
```
✅ Staff filtering works correctly!

Test: Insert 5 customer events + 3 staff events
Result: get_unique_visitors() returns 5 (staff excluded)
```

---

## Summary

### Issues Fixed: 3
1. ✅ Staff filtering in API queries
2. ✅ Edge case tests added
3. ✅ Metadata serialization

### Tests Added: 4
1. ✅ test_empty_store()
2. ✅ test_all_staff_events()
3. ✅ test_zero_purchases()
4. ✅ test_reentry_handling()

### Tests Passed: 12+
- 8 quick validation tests
- 4 edge case tests
- 1 staff filtering test
- All existing tests still passing

### System Status: ✅ READY FOR SUBMISSION

All issues fixed, all tests passing, system ready for evaluation.

