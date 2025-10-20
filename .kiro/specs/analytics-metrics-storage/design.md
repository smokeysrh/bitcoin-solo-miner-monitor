# Design Document

## Overview

This design implements metrics persistence for the Analytics feature by integrating the existing TimeSeriesStorage service with the MinerManager's polling cycle. The solution focuses on minimal code changes, reusing existing components, and maintaining application performance. Additionally, it improves the time range selector UX and adds an electricity cost setting.

**Database Note**: This application uses SQLite (via aiosqlite) for all data storage, including miner configurations, metrics, and settings. The TimeSeriesStorage service provides specialized methods for efficient time-series data operations within SQLite.

## Architecture

### High-Level Flow

```
MinerManager Polling Cycle
    ↓
Fetch Miner Status
    ↓
Update Miner Data (existing)
    ↓
Save Metrics to TimeSeriesStorage (NEW)
    ↓
Broadcast via WebSocket (existing)
    ↓
Analytics Dashboard Fetches Historical Data
    ↓
Display Charts
```

### Component Interactions

1. **MinerManager** - Modified to call TimeSeriesStorage during polling
2. **TimeSeriesStorage** - Already exists, no changes needed
3. **DataStorage** - Already has `get_metrics()` method, no changes needed
4. **Analytics.vue** - Already fetches metrics, will work once data exists
5. **Settings.vue** - Add electricity cost field

## Components and Interfaces

### Backend Changes

#### 1. MinerManager Service (`src/backend/services/miner_manager.py`)

**Modification: Add TimeSeriesStorage Integration**

```python
class MinerManager:
    def __init__(self):
        # ... existing code ...
        self.timeseries_storage = None  # NEW: Will be injected
    
    def set_timeseries_storage(self, timeseries_storage):
        """Set the timeseries storage instance for metrics persistence."""
        self.timeseries_storage = timeseries_storage
    
    async def _poll_miner(self, miner_id: str):
        """
        Poll a miner for status updates.
        Modified to save metrics to timeseries storage.
        """
        # ... existing polling logic ...
        
        # NEW: Save metrics after successful poll
        if self.timeseries_storage and status:
            try:
                # Extract metrics from status
                metrics = self._extract_metrics(status)
                await self.timeseries_storage.save_metrics(
                    miner_id, 
                    metrics, 
                    datetime.now()
                )
            except Exception as e:
                logger.error(f"Failed to save metrics for {miner_id}: {e}")
                # Don't fail the polling cycle
    
    def _extract_metrics(self, status: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract relevant metrics from miner status for storage.
        Returns a flat dictionary of metric_name: value pairs.
        """
        metrics = {}
        
        # Extract common metrics
        if 'hashrate' in status:
            metrics['hashrate'] = status['hashrate']
        if 'temperature' in status:
            metrics['temperature'] = status['temperature']
        if 'power' in status:
            metrics['power'] = status['power']
        if 'fan_speed' in status:
            metrics['fan_speed'] = status['fan_speed']
        if 'shares_accepted' in status:
            metrics['shares_accepted'] = status['shares_accepted']
        if 'shares_rejected' in status:
            metrics['shares_rejected'] = status['shares_rejected']
        if 'uptime' in status:
            metrics['uptime'] = status['uptime']
        
        return metrics
```

**Rationale**: 
- Minimal changes to existing polling logic
- Non-blocking metrics save (errors don't affect polling)
- Reuses existing TimeSeriesStorage service
- Extracts only relevant numeric metrics

#### 2. API Service (`src/backend/api/api_service.py`)

**Modification: Wire TimeSeriesStorage to MinerManager**

```python
class APIService:
    def __init__(self, miner_manager: MinerManager, data_storage: DataStorage):
        # ... existing code ...
        
        # NEW: Connect timeseries storage to miner manager
        self.miner_manager.set_timeseries_storage(
            self.data_storage.timeseries_storage
        )
```

**Rationale**: Simple dependency injection, no architectural changes needed

#### 3. DataStorage Service (`src/backend/services/data_storage.py`)

**Modification: Expose get_metrics with proper aggregation**

The `get_metrics()` method already exists but needs to be verified it properly calls TimeSeriesStorage:

```python
async def get_metrics(
    self, 
    miner_id: str, 
    start_time: datetime, 
    end_time: datetime, 
    interval: str = "1h",
    metric_types: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Get metrics for a miner with aggregation.
    """
    if not self.timeseries_storage:
        return []
    
    # Use aggregated metrics for better performance
    return await self.timeseries_storage.get_aggregated_metrics(
        miner_id,
        start_time,
        end_time,
        interval,
        metric_types
    )
```

**Rationale**: Reuse existing method, ensure it uses aggregation for performance

### Frontend Changes

#### 1. Analytics.vue Time Range Selector

**Modifications:**

1. Update time range options:
```javascript
const timeRangeOptions = [
  { value: '1m', label: '1 Min' },
  { value: '15m', label: '15 Min' },
  { value: '1h', label: '1 Hour' },
  { value: '24h', label: '24 Hours' },
  { value: '7d', label: '7 Days' },
  { value: '30d', label: '30 Days' },
  { value: 'custom', label: 'Custom' }
];
```

2. Fix date picker auto-close:
```vue
<v-date-picker
  v-model="startDate"
  @input="startDateMenu = false"  <!-- Already exists -->
  @change="startDateMenu = false"  <!-- NEW: Also close on change -->
></v-date-picker>
```

3. Add close button to custom date range:
```vue
<v-row v-if="selectedTimeRange === 'custom'">
  <v-col cols="12" class="d-flex justify-end">
    <v-btn text small @click="cancelCustomRange">
      <v-icon left>mdi-close</v-icon>
      Cancel
    </v-btn>
  </v-col>
  <!-- ... existing date pickers ... -->
</v-row>
```

**Rationale**: 
- Minimal template changes
- Improves UX without major refactoring
- Maintains existing functionality

#### 2. Settings.vue Electricity Cost

**Modification: Add electricity cost field**

```vue
<template>
  <!-- ... existing settings ... -->
  
  <v-card outlined class="mt-4">
    <v-card-title>Power Cost Settings</v-card-title>
    <v-card-text>
      <v-text-field
        v-model.number="electricityCost"
        label="Electricity Cost (USD per kWh)"
        type="number"
        step="0.01"
        min="0.01"
        max="10.00"
        prefix="$"
        suffix="/ kWh"
        hint="Enter your electricity cost for power calculations"
        persistent-hint
        @change="saveElectricityCost"
      ></v-text-field>
      <div class="text-caption mt-2">
        Default: $0.13/kWh (US national average)
      </div>
    </v-card-text>
  </v-card>
</template>

<script>
export default {
  data() {
    return {
      electricityCost: 0.13,
      // ... existing data ...
    };
  },
  
  async mounted() {
    await this.loadSettings();
  },
  
  methods: {
    async loadSettings() {
      const settings = await this.settingsStore.fetchSettings();
      this.electricityCost = settings.electricity_cost || 0.13;
    },
    
    async saveElectricityCost() {
      await this.settingsStore.updateSettings({
        electricity_cost: this.electricityCost
      });
    }
  }
};
</script>
```

**Rationale**:
- Simple form field addition
- Reuses existing settings store
- Validates input range
- Provides helpful defaults and hints

## Data Models

### Metrics Storage Schema

The existing `miner_metrics` table in SQLite already supports our needs:

```sql
CREATE TABLE miner_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    miner_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    metric_type TEXT NOT NULL,
    value REAL NOT NULL,
    unit TEXT,
    FOREIGN KEY (miner_id) REFERENCES miners(id)
);

CREATE INDEX idx_miner_metrics_lookup 
ON miner_metrics(miner_id, timestamp, metric_type);
```

**Metric Types Stored:**
- `hashrate` (TH/s)
- `temperature` (°C)
- `power` (W)
- `fan_speed` (RPM)
- `shares_accepted` (count)
- `shares_rejected` (count)
- `uptime` (seconds)

### Settings Schema

Add to existing settings table:

```sql
-- Settings table already exists, just add new field
ALTER TABLE settings ADD COLUMN electricity_cost REAL DEFAULT 0.13;
```

## Error Handling

### Metrics Save Failures

```python
try:
    await self.timeseries_storage.save_metrics(miner_id, metrics, timestamp)
except Exception as e:
    logger.error(f"Failed to save metrics for {miner_id}: {e}")
    # Continue polling - don't let metrics save failure break polling
```

**Strategy**: Log and continue - metrics persistence is important but not critical to real-time monitoring

### Empty Metrics Data

The Analytics page already handles this:
```vue
<div v-else-if="!hasData" class="text-center pa-5">
  <p class="text-subtitle-1">
    No data available for the selected time range
  </p>
</div>
```

**Strategy**: Graceful degradation with helpful messaging

## Testing Strategy

### Unit Tests

1. **MinerManager._extract_metrics()**
   - Test with various status formats
   - Test with missing fields
   - Test with invalid data types

2. **TimeSeriesStorage.save_metrics()**
   - Already has tests
   - Verify concurrent writes work

3. **Settings validation**
   - Test electricity cost range validation
   - Test default value handling

### Integration Tests

1. **End-to-End Metrics Flow**
   - Start miner polling
   - Wait for polling cycle
   - Verify metrics in database
   - Fetch via API
   - Verify in Analytics page

2. **Time Range Selector**
   - Test each time range option
   - Test custom date picker
   - Verify correct data retrieval

### Manual Testing

1. Add a miner and wait 5-10 minutes
2. Navigate to Analytics page
3. Verify graphs populate with data
4. Test different time ranges
5. Test custom date picker close behavior
6. Update electricity cost in settings
7. Verify setting persists

## Performance Considerations

### Metrics Write Performance

- **Batch Writes**: TimeSeriesStorage already uses `executemany()` for batch inserts
- **Non-Blocking**: Metrics save happens asynchronously, doesn't block polling
- **Error Isolation**: Save failures don't affect miner polling

### Query Performance

- **Aggregation**: Use `get_aggregated_metrics()` instead of raw data for large time ranges
- **Indexes**: Existing indexes on `(miner_id, timestamp, metric_type)` optimize queries
- **Time-based Partitioning**: Consider if data grows large (future optimization)

### Frontend Performance

- **Chart.js**: Already used, efficient for time-series data
- **Data Decimation**: For large datasets, Chart.js automatically decimates points
- **Lazy Loading**: Charts only load when Analytics tab is active

## Migration Strategy

### Database Migration

No schema changes needed - tables already exist. Just need to start populating them.

### Deployment Steps

1. Deploy backend changes (MinerManager + API Service)
2. Restart application
3. Metrics will start accumulating automatically
4. Deploy frontend changes (Analytics + Settings)
5. Users will see data appear as it accumulates

### Rollback Plan

If issues occur:
1. Revert MinerManager changes
2. Metrics stop being saved
3. Existing data remains in database
4. No data loss, just stops accumulating new data

## Future Enhancements

### Cost Calculations (Future Spec)

With electricity cost setting in place, future features can calculate:
- Daily/monthly power costs
- Cost per TH/s
- Profitability estimates
- Cost alerts

### Data Retention

Consider implementing:
- Automatic cleanup of old metrics (already exists in TimeSeriesStorage)
- Configurable retention periods
- Data export functionality

## Security Considerations

- **Input Validation**: Electricity cost validated on frontend and backend
- **SQL Injection**: Using parameterized queries (already implemented)
- **Rate Limiting**: Existing rate limiting applies to metrics endpoints
- **Authentication**: Metrics endpoints use existing auth middleware

## Accessibility

- **Form Labels**: Electricity cost field has proper label and hint text
- **Keyboard Navigation**: Date picker supports keyboard navigation
- **Screen Readers**: All form fields have aria-labels
- **Color Contrast**: Charts use accessible color schemes

## Summary

This design leverages existing infrastructure (TimeSeriesStorage, DataStorage, Analytics page) and makes minimal, focused changes to enable metrics persistence. The solution is performant, maintainable, and sets up future cost calculation features while improving the user experience of the time range selector.
