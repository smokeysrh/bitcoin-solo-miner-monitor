# Design Document

## Overview

This design addresses six critical functionality issues in the Bitcoin Miner Management application that impact user experience and real-time monitoring capabilities. The fixes span frontend components, backend API endpoints, data flow architecture, and real-time update mechanisms. The design follows the existing architecture patterns using Vue 3 Composition API, Pinia stores, FastAPI backend, and WebSocket for real-time updates.

## Architecture

### Current System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (Vue 3)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Analytics   │  │ MinerDetail  │  │   Network    │     │
│  │     View     │  │     View     │  │     View     │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                  │                  │              │
│  ┌──────▼──────────────────▼──────────────────▼───────┐    │
│  │           Pinia Stores (miners.js)                  │    │
│  └──────┬──────────────────────────────────────────────┘    │
│         │                                                     │
└─────────┼─────────────────────────────────────────────────────┘
          │
          │ HTTP/WebSocket
          │
┌─────────▼─────────────────────────────────────────────────────┐
│                  Backend (FastAPI/Python)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  API Service │  │MinerManager  │  │ DataStorage  │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
│         │                  │                  │                │
│  ┌──────▼──────────────────▼──────────────────▼───────┐      │
│  │         WebSocket Manager (Real-time Updates)       │      │
│  └──────────────────────────────────────────────────────┘      │
└────────────────────────────────────────────────────────────────┘
```

### Modified Data Flow for Fixes

```
┌─────────────────────────────────────────────────────────────┐
│                    Fix 1: Refresh Button                     │
│  User Click → API Call → /api/miners/refresh → Update Store │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│              Fix 2: Real-time Chart Updates                  │
│  Metrics Save → WebSocket Broadcast → Store Update → Charts │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│           Fix 3: Timeframe Selection (Dual Control)          │
│  Range Click → Immediate Update → API Call → Chart Redraw   │
│  Increment Click → Immediate Update → API Call → Chart Redraw│
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│            Fix 4: Analytics Preview on Miner Page            │
│  Navigate → Fetch Metrics → Render Preview → Link to Full   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│              Fix 5: Remove Tab Navigation                    │
│  Remove Tabs → Single Scroll View → Unified Layout          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│            Fix 6 & 7: Network Page Enhancements              │
│  Refresh → Update Viz → Click Node → Show Details           │
│  Network Health → Ping Tests → Display Metrics              │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### Fix 1: Refresh Button Endpoint

**Backend Component: API Service**
- **New Endpoint**: `POST /api/miners/refresh`
- **Purpose**: Trigger immediate refresh of all miner data
- **Implementation**:
  ```python
  async def refresh_miners(self) -> Dict[str, Any]:
      """Refresh all miner data immediately."""
      await self.miner_manager.refresh_all_miners()
      miners = await self.miner_manager.get_miners()
      return {"success": True, "miners": miners, "count": len(miners)}
  ```

**Frontend Component: Miners Store**
- **New Method**: `refreshMiners()`
- **Implementation**:
  ```javascript
  const refreshMiners = async () => {
    loading.value = true;
    try {
      const response = await axios.post(`${API_BASE_URL}/miners/refresh`);
      miners.value = response.data.miners.map(m => normalizeMinerData(m));
      return response.data;
    } finally {
      loading.value = false;
    }
  };
  ```

### Fix 2: Real-time Analytics Chart Updates

**Backend Component: WebSocket Manager**
- **Enhancement**: Broadcast metrics updates on save
- **Event Type**: `metrics_update`
- **Payload Structure**:
  ```json
  {
    "type": "metrics_update",
    "miner_id": "string",
    "metrics": {
      "hashrate": number,
      "temperature": number,
      "power": number,
      "timestamp": "ISO8601"
    }
  }
  ```

**Frontend Component: Analytics View**
- **WebSocket Listener**: Subscribe to `metrics_update` events
- **Chart Update Logic**:
  ```javascript
  const handleMetricsUpdate = (data) => {
    if (selectedMiners.value.includes(data.miner_id)) {
      // Append new data point to existing chart data
      appendDataToCharts(data.metrics);
      // Trigger chart re-render
      updateCharts();
    }
  };
  ```

### Fix 3: Dual Timeframe Selection

**Frontend Component: Analytics View - Time Controls**

**UI Structure**:
```vue
<v-row>
  <v-col cols="12" md="6">
    <v-card-title>Time Range</v-card-title>
    <v-btn-toggle v-model="selectedTimeRange" @update:model-value="onTimeRangeChange">
      <v-btn value="1h">1 Hour</v-btn>
      <v-btn value="24h">24 Hours</v-btn>
      <v-btn value="7d">7 Days</v-btn>
      <v-btn value="30d">30 Days</v-btn>
    </v-btn-toggle>
  </v-col>
  <v-col cols="12" md="6">
    <v-card-title>Time Increment</v-card-title>
    <v-btn-toggle v-model="selectedIncrement" @update:model-value="onIncrementChange">
      <v-btn value="1m">1 Min</v-btn>
      <v-btn value="15m">15 Min</v-btn>
      <v-btn value="1h">1 Hour</v-btn>
      <v-btn value="1d">1 Day</v-btn>
    </v-btn-toggle>
  </v-col>
</v-row>
```

**Logic**:
- Remove "Apply" button
- Both controls trigger immediate data fetch
- Validate increment against range (e.g., 1m increment not valid for 30d range)
- Auto-adjust increment if invalid combination selected

**Implementation**:
```javascript
const onTimeRangeChange = async (newRange) => {
  selectedTimeRange.value = newRange;
  // Auto-adjust increment if needed
  adjustIncrementForRange();
  await fetchMetricsData();
};

const onIncrementChange = async (newIncrement) => {
  selectedIncrement.value = newIncrement;
  await fetchMetricsData();
};

const adjustIncrementForRange = () => {
  const rangeIncrementMap = {
    '1h': ['1m', '5m', '15m'],
    '24h': ['5m', '15m', '1h'],
    '7d': ['1h', '6h', '1d'],
    '30d': ['1d']
  };
  
  const validIncrements = rangeIncrementMap[selectedTimeRange.value];
  if (!validIncrements.includes(selectedIncrement.value)) {
    selectedIncrement.value = validIncrements[0];
  }
};
```

### Fix 4: Analytics Preview Section

**Frontend Component: MinerDetail View - New Section**

**UI Structure**:
```vue
<v-row class="mt-4">
  <v-col cols="12">
    <v-card>
      <v-card-title>
        Analytics Preview
        <v-spacer></v-spacer>
        <v-btn color="primary" :to="`/analytics?miner=${minerId}`">
          See Full Analytics
        </v-btn>
      </v-card-title>
      <v-card-text>
        <v-row>
          <v-col cols="12" md="4">
            <canvas ref="previewHashrateChart" height="200"></canvas>
          </v-col>
          <v-col cols="12" md="4">
            <canvas ref="previewTemperatureChart" height="200"></canvas>
          </v-col>
          <v-col cols="12" md="4">
            <canvas ref="previewPowerChart" height="200"></canvas>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>
  </v-col>
</v-row>
```

**Data Fetching**:
```javascript
const fetchPreviewMetrics = async () => {
  const sixHoursAgo = new Date(Date.now() - 6 * 60 * 60 * 1000);
  const now = new Date();
  
  const metrics = await minersStore.fetchMinerMetrics(
    minerId,
    sixHoursAgo.toISOString(),
    now.toISOString(),
    '15m' // 15-minute intervals for 6-hour preview
  );
  
  renderPreviewCharts(metrics);
};
```

**Chart Rendering**:
- Use Chart.js with condensed configuration
- Show last 6 hours of data
- Simplified tooltips and legends
- Responsive sizing

### Fix 5: Remove Tab Navigation

**Frontend Component: MinerDetail View - Layout Simplification**

**Current Structure** (to be removed):
```vue
<v-tabs v-model="activeTab">
  <v-tab value="overview">Overview</v-tab>
  <v-tab value="performance">Performance</v-tab>
  <v-tab value="pool">Pool</v-tab>
  <v-tab value="settings">Settings</v-tab>
</v-tabs>
```

**New Structure**:
```vue
<v-container>
  <!-- Overview Section -->
  <v-row>
    <v-col cols="12">
      <v-card>
        <v-card-title>Miner Overview</v-card-title>
        <!-- Overview content -->
      </v-card>
    </v-col>
  </v-row>
  
  <!-- Analytics Preview Section -->
  <v-row class="mt-4">
    <!-- Analytics preview from Fix 4 -->
  </v-row>
  
  <!-- Performance Metrics Section -->
  <v-row class="mt-4">
    <v-col cols="12">
      <v-card>
        <v-card-title>Performance Metrics</v-card-title>
        <!-- Performance content -->
      </v-card>
    </v-col>
  </v-row>
  
  <!-- Pool Configuration Section -->
  <v-row class="mt-4">
    <v-col cols="12">
      <v-card>
        <v-card-title>Pool Configuration</v-card-title>
        <!-- Pool content -->
      </v-card>
    </v-col>
  </v-row>
  
  <!-- Settings Section -->
  <v-row class="mt-4">
    <v-col cols="12">
      <v-card>
        <v-card-title>Miner Settings</v-card-title>
        <!-- Settings content -->
      </v-card>
    </v-col>
  </v-row>
</v-container>
```

**Implementation**:
- Remove `v-tabs` and `v-tab` components
- Remove `activeTab` state variable
- Convert tab content to vertically-stacked cards
- Add consistent spacing between sections
- Ensure smooth scrolling behavior

### Fix 6: Network Page Refresh and Visualization

**Frontend Component: Network View - Refresh Enhancement**

**Current Issue**: Refresh button calls `refreshNetwork()` which fetches miners but may not properly update visualization

**Fix Implementation**:
```javascript
const refreshNetwork = async () => {
  loading.value = true;
  try {
    // Fetch latest miner data
    await minersStore.fetchMiners();
    
    // Force re-render of visualization
    await nextTick();
    updateNetworkVisualization();
    
    // Show success feedback
    showSnackbar('Network refreshed successfully', 'success');
  } catch (error) {
    console.error('Error refreshing network:', error);
    showSnackbar('Failed to refresh network', 'error');
  } finally {
    loading.value = false;
  }
};
```

**Visualization Update Logic**:
- Clear existing D3 visualization
- Rebuild nodes and links from fresh miner data
- Maintain selected layout type
- Preserve user's zoom/pan state if possible

### Fix 7: Network Health Monitoring

**Backend Component: New Network Health Service**

**File**: `src/backend/services/network_health.py`

```python
class NetworkHealthMonitor:
    """Monitor network health metrics for miners."""
    
    async def measure_latency(self, host: str, port: int) -> float:
        """Measure network latency to a host."""
        # Implement ping/connection time measurement
        pass
    
    async def measure_packet_loss(self, host: str, count: int = 10) -> float:
        """Measure packet loss percentage."""
        # Implement packet loss measurement
        pass
    
    async def get_connection_uptime(self, miner_id: str) -> int:
        """Get connection uptime in seconds."""
        # Query from database or miner manager
        pass
    
    async def get_network_health(self, miner_id: str) -> Dict[str, Any]:
        """Get comprehensive network health metrics."""
        return {
            "latency_ms": await self.measure_latency(...),
            "packet_loss_percent": await self.measure_packet_loss(...),
            "uptime_seconds": await self.get_connection_uptime(...),
            "status": self._calculate_health_status(...)
        }
```

**Backend API Endpoint**:
```python
@app.get("/api/miners/{miner_id}/network-health")
async def get_miner_network_health(miner_id: str) -> Dict[str, Any]:
    """Get network health metrics for a miner."""
    health = await network_health_monitor.get_network_health(miner_id)
    return health
```

**Frontend Component: Network View - Health Display**

**UI Enhancement**:
```vue
<v-card>
  <v-card-title>Network Health</v-card-title>
  <v-card-text>
    <v-row>
      <v-col cols="12" md="4">
        <div class="text-subtitle-1">Average Latency:</div>
        <div class="text-h5">{{ averageLatency }} ms</div>
      </v-col>
      <v-col cols="12" md="4">
        <div class="text-subtitle-1">Packet Loss:</div>
        <div class="text-h5">{{ packetLoss }}%</div>
      </v-col>
      <v-col cols="12" md="4">
        <div class="text-subtitle-1">Network Jitter:</div>
        <div class="text-h5">{{ networkJitter }} ms</div>
      </v-col>
    </v-row>
  </v-card-text>
</v-card>
```

**Node Visual Indicators**:
```javascript
const getNodeHealthColor = (health) => {
  if (!health) return '#9E9E9E'; // Grey for unknown
  
  const latency = health.latency_ms;
  const packetLoss = health.packet_loss_percent;
  
  // Red: High latency (>200ms) or packet loss (>5%)
  if (latency > 200 || packetLoss > 5) return '#E53935';
  
  // Yellow: Medium latency (>100ms) or packet loss (>2%)
  if (latency > 100 || packetLoss > 2) return '#FFC107';
  
  // Green: Good health
  return '#43A047';
};
```

## Data Models

### Metrics Data Model (Enhanced)

```typescript
interface MinerMetrics {
  miner_id: string;
  timestamp: string; // ISO 8601
  hashrate: number;
  temperature: number;
  power: number;
  shares_accepted: number;
  shares_rejected: number;
  fan_speed?: number;
  uptime?: number;
}
```

### Network Health Data Model (New)

```typescript
interface NetworkHealth {
  miner_id: string;
  latency_ms: number;
  packet_loss_percent: number;
  uptime_seconds: number;
  jitter_ms: number;
  status: 'healthy' | 'degraded' | 'poor' | 'unknown';
  last_measured: string; // ISO 8601
}
```

### Timeframe Selection Model (New)

```typescript
interface TimeframeSelection {
  range: '1h' | '24h' | '7d' | '30d' | 'custom';
  increment: '1m' | '5m' | '15m' | '1h' | '6h' | '1d';
  startDate?: string; // For custom range
  endDate?: string; // For custom range
}
```

## Error Handling

### API Error Responses

**Standard Error Format**:
```json
{
  "error": "string",
  "message": "string",
  "details": {}
}
```

**Specific Error Cases**:

1. **Refresh Endpoint Failure**:
   - Status: 500
   - Message: "Failed to refresh miners"
   - Frontend: Show error snackbar, maintain current data

2. **Metrics Fetch Failure**:
   - Status: 404 (miner not found) or 500 (server error)
   - Message: "Failed to fetch metrics for miner {id}"
   - Frontend: Show empty state with retry button

3. **Invalid Timeframe Combination**:
   - Status: 400
   - Message: "Invalid combination of range and increment"
   - Frontend: Auto-adjust to valid combination

4. **Network Health Measurement Failure**:
   - Status: 500
   - Message: "Failed to measure network health"
   - Frontend: Display "N/A" for unavailable metrics

### Frontend Error Handling

**Global Error Handler**:
```javascript
const handleApiError = (error, context) => {
  console.error(`Error in ${context}:`, error);
  
  const message = error.response?.data?.message || 
                  error.message || 
                  'An unexpected error occurred';
  
  showSnackbar(message, 'error');
  
  // Log to monitoring service if available
  if (window.errorMonitoring) {
    window.errorMonitoring.logError(error, context);
  }
};
```

## Testing Strategy

### Unit Tests

**Backend Tests**:
1. Test refresh endpoint returns correct data structure
2. Test metrics aggregation with different intervals
3. Test network health measurement functions
4. Test WebSocket broadcast on metrics save

**Frontend Tests**:
1. Test timeframe selection logic and validation
2. Test chart update on WebSocket message
3. Test analytics preview data fetching
4. Test network visualization refresh

### Integration Tests

1. **End-to-End Refresh Flow**:
   - Click refresh button → API call → Store update → UI update
   
2. **Real-time Metrics Update**:
   - Save metrics → WebSocket broadcast → Chart update
   
3. **Timeframe Selection**:
   - Change range → Fetch data → Render charts
   - Change increment → Fetch data → Render charts
   
4. **Analytics Preview Navigation**:
   - View miner details → See preview → Click "See Full Analytics" → Navigate with pre-selected miner

### Manual Testing Checklist

- [ ] Refresh button updates all miner data
- [ ] Charts update automatically when new metrics are saved
- [ ] Time range selection works without Apply button
- [ ] Time increment selection works without Apply button
- [ ] Invalid range/increment combinations are handled
- [ ] Analytics preview displays on miner details page
- [ ] "See Full Analytics" button navigates correctly
- [ ] Miner details page shows all sections in single scroll view
- [ ] Network page refresh updates visualization
- [ ] Network health metrics display correctly
- [ ] Network node colors reflect health status
- [ ] All error states display appropriate messages

## Performance Considerations

### Chart Rendering Optimization

**Problem**: Frequent chart updates can cause performance issues

**Solutions**:
1. **Debounce Updates**: Wait 500ms after last data point before re-rendering
2. **Incremental Updates**: Append new data points instead of full re-render when possible
3. **Data Point Limiting**: Limit visible data points based on time range
   - 1h range: Max 60 points (1 per minute)
   - 24h range: Max 288 points (1 per 5 minutes)
   - 7d range: Max 168 points (1 per hour)
   - 30d range: Max 30 points (1 per day)

### WebSocket Message Throttling

**Problem**: High-frequency metrics updates can overwhelm frontend

**Solution**:
```javascript
const throttledMetricsUpdate = throttle((data) => {
  handleMetricsUpdate(data);
}, 1000); // Max 1 update per second per miner
```

### Network Health Polling

**Strategy**:
- Poll network health every 30 seconds
- Cache results for 30 seconds
- Only measure for visible/selected miners
- Use background worker to avoid blocking UI

## Security Considerations

1. **API Endpoint Protection**:
   - Refresh endpoint requires authentication
   - Rate limiting: Max 10 refresh requests per minute per user

2. **WebSocket Authentication**:
   - Validate WebSocket connections
   - Only broadcast to authenticated clients

3. **Input Validation**:
   - Validate timeframe parameters
   - Sanitize miner IDs in all requests
   - Validate network health measurement targets

4. **Data Exposure**:
   - Only expose network health for user's own miners
   - Don't expose internal network topology details

## Migration and Deployment

### Database Migrations

**New Table for Network Health**:
```sql
CREATE TABLE IF NOT EXISTS network_health (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    miner_id TEXT NOT NULL,
    latency_ms REAL,
    packet_loss_percent REAL,
    uptime_seconds INTEGER,
    jitter_ms REAL,
    status TEXT,
    measured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (miner_id) REFERENCES miners(id) ON DELETE CASCADE
);

CREATE INDEX idx_network_health_miner_time 
ON network_health(miner_id, measured_at);
```

### Deployment Steps

1. **Backend Deployment**:
   - Deploy new API endpoints
   - Run database migrations
   - Start network health monitoring service
   - Verify WebSocket broadcasts working

2. **Frontend Deployment**:
   - Build updated frontend with fixes
   - Deploy static assets
   - Clear browser caches
   - Verify all routes working

3. **Rollback Plan**:
   - Keep previous version available
   - Database migrations are backward compatible
   - Can revert frontend without backend changes

### Feature Flags

Consider using feature flags for gradual rollout:
- `enable_network_health`: Toggle network health monitoring
- `enable_dual_timeframe`: Toggle new timeframe selection UI
- `enable_analytics_preview`: Toggle analytics preview on miner details

## Dependencies

### New Dependencies

**Backend**:
- `ping3` or `icmplib`: For network latency measurement
- No additional dependencies for other fixes

**Frontend**:
- No new dependencies required
- Uses existing Chart.js, D3.js, Vue 3, Vuetify

### Version Compatibility

- Vue 3: ^3.2.0
- Vuetify: ^3.0.0
- Chart.js: ^4.0.0
- D3.js: ^7.0.0
- FastAPI: ^0.100.0
- Python: ^3.9

## Future Enhancements

1. **Advanced Network Diagnostics**:
   - Bandwidth usage tracking
   - DNS resolution time
   - Connection quality score

2. **Chart Interactions**:
   - Zoom and pan on charts
   - Export chart data as CSV
   - Compare multiple miners on same chart

3. **Predictive Analytics**:
   - Predict miner failures based on metrics trends
   - Alert on anomalous patterns

4. **Mobile Optimization**:
   - Responsive chart sizing
   - Touch-friendly network visualization
   - Simplified mobile layouts
