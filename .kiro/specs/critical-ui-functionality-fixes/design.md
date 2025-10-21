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

**Backend Component: Enhanced Network Health Service**

**File**: `src/backend/services/network_health.py`

```python
class NetworkHealthMonitor:
    """Monitor network health metrics for miners and their pool connections."""
    
    async def measure_latency(self, host: str, count: int = 4) -> Optional[float]:
        """Measure network latency to a host using ping."""
        # Implement ICMP ping measurement
        # Returns average latency in milliseconds
        pass
    
    async def measure_packet_loss(self, host: str, count: int = 10) -> Optional[float]:
        """Measure packet loss percentage."""
        # Implement packet loss measurement
        # Returns percentage (0-100)
        pass
    
    async def get_connection_uptime(self, miner_id: str) -> Optional[int]:
        """Get connection uptime in seconds."""
        # Query from connection tracking
        pass
    
    async def get_pool_info_from_miner(self, miner_id: str) -> List[Dict[str, Any]]:
        """Get pool configuration from miner."""
        # Call miner's get_pool_info() method
        # Returns list of pool configurations with URL and port
        pass
    
    async def measure_pool_latency(self, pool_url: str, pool_port: int) -> Optional[float]:
        """Measure latency to mining pool or Bitcoin node."""
        # Resolve hostname to IP if needed
        # Measure latency using ping
        # Returns latency in milliseconds
        pass
    
    async def get_network_health(self, miner_id: str, host: str) -> Dict[str, Any]:
        """Get comprehensive network health metrics including pool latency."""
        miner_latency = await self.measure_latency(host)
        packet_loss = await self.measure_packet_loss(host)
        uptime = await self.get_connection_uptime(miner_id)
        
        # Get pool information and measure pool latency
        pool_info = await self.get_pool_info_from_miner(miner_id)
        pool_latency_data = None
        
        if pool_info:
            active_pool = next((p for p in pool_info if p.get('is_active')), pool_info[0])
            pool_latency = await self.measure_pool_latency(
                active_pool['url'], 
                active_pool.get('port', 3333)
            )
            
            pool_latency_data = {
                "url": active_pool['url'],
                "port": active_pool.get('port'),
                "latency_ms": pool_latency,
                "status": self._calculate_pool_health_status(pool_latency)
            }
        
        return {
            "miner_id": miner_id,
            "miner_latency_ms": miner_latency,
            "packet_loss_percent": packet_loss,
            "uptime_seconds": uptime,
            "pool_latency": pool_latency_data,
            "total_path_latency_ms": (miner_latency or 0) + (pool_latency or 0) if miner_latency and pool_latency else None,
            "status": self._calculate_health_status(miner_latency, packet_loss, pool_latency)
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

**Frontend Component: Network View - Enhanced Health Display**

**UI Enhancement**:
```vue
<v-card>
  <v-card-title>Network Health</v-card-title>
  <v-card-text>
    <v-row>
      <v-col cols="12" md="3">
        <div class="text-subtitle-1">Avg Miner Latency:</div>
        <div class="text-h5">{{ averageMinerLatency }} ms</div>
      </v-col>
      <v-col cols="12" md="3">
        <div class="text-subtitle-1">Avg Pool Latency:</div>
        <div class="text-h5">{{ averagePoolLatency }} ms</div>
      </v-col>
      <v-col cols="12" md="3">
        <div class="text-subtitle-1">Packet Loss:</div>
        <div class="text-h5">{{ packetLoss }}%</div>
      </v-col>
      <v-col cols="12" md="3">
        <div class="text-subtitle-1">Network Jitter:</div>
        <div class="text-h5">{{ networkJitter }} ms</div>
      </v-col>
    </v-row>
    <v-row class="mt-2">
      <v-col cols="12">
        <div class="text-subtitle-2">Pool Connections:</div>
        <v-chip-group>
          <v-chip 
            v-for="pool in uniquePools" 
            :key="pool.url"
            :color="getPoolHealthColor(pool.latency)"
            text-color="white"
            size="small"
          >
            {{ pool.url }}: {{ pool.latency }}ms
          </v-chip>
        </v-chip-group>
      </v-col>
    </v-row>
  </v-card-text>
</v-card>
```

**Node Visual Indicators**:
```javascript
const getNodeHealthColor = (health) => {
  if (!health) return '#9E9E9E'; // Grey for unknown
  
  const latency = health.miner_latency_ms;
  const packetLoss = health.packet_loss_percent;
  
  // Red: High latency (>200ms) or packet loss (>5%)
  if (latency > 200 || packetLoss > 5) return '#E53935';
  
  // Yellow: Medium latency (>100ms) or packet loss (>2%)
  if (latency > 100 || packetLoss > 2) return '#FFC107';
  
  // Green: Good health
  return '#43A047';
};
```

### Fix 8: Pool and Node Visualization in Network Topology

**Frontend Component: Network View - Enhanced D3 Visualization**

**Network Topology Structure**:
```
Current: Router → Miners
Enhanced: Router → Miners → Pools/Nodes
```

**Node Types**:
1. **Router Node** (existing) - Central hub
2. **Miner Nodes** (existing) - Mining devices
3. **Pool Nodes** (new) - Mining pool servers
4. **Bitcoin Node** (new) - Local Bitcoin Core nodes

**Implementation Strategy**:

```javascript
const buildNetworkGraph = () => {
  const nodes = [];
  const links = [];
  
  // Add router node (existing)
  nodes.push({
    id: 'router',
    name: 'Network Router',
    type: 'router',
    status: 'online'
  });
  
  // Track unique pools/nodes
  const poolMap = new Map();
  
  // Add miner nodes and collect pool information
  miners.value.forEach(miner => {
    // Add miner node
    nodes.push({
      id: miner.id,
      name: miner.name,
      type: miner.type,
      status: miner.status,
      data: miner
    });
    
    // Link miner to router
    links.push({
      source: 'router',
      target: miner.id,
      type: 'miner-connection',
      latency: networkHealthData.value[miner.id]?.miner_latency_ms
    });
    
    // Get pool information from network health data
    const health = networkHealthData.value[miner.id];
    if (health?.pool_latency) {
      const poolKey = `${health.pool_latency.url}:${health.pool_latency.port}`;
      
      // Add pool node if not already added
      if (!poolMap.has(poolKey)) {
        const poolId = `pool_${poolKey.replace(/[.:]/g, '_')}`;
        poolMap.set(poolKey, poolId);
        
        nodes.push({
          id: poolId,
          name: health.pool_latency.url,
          type: miner.type === 'bitcoin_node' ? 'bitcoin_node_pool' : 'pool',
          status: health.pool_latency.status,
          url: health.pool_latency.url,
          port: health.pool_latency.port,
          latency: health.pool_latency.latency_ms,
          connectedMiners: []
        });
      }
      
      // Link miner to pool
      const poolId = poolMap.get(poolKey);
      links.push({
        source: miner.id,
        target: poolId,
        type: 'pool-connection',
        latency: health.pool_latency.latency_ms,
        status: health.pool_latency.status
      });
      
      // Track connected miners for pool node
      const poolNode = nodes.find(n => n.id === poolId);
      if (poolNode) {
        poolNode.connectedMiners.push(miner.id);
      }
    }
  });
  
  return { nodes, links };
};
```

**Visual Styling**:

```javascript
// Node colors
const getNodeColor = (node) => {
  if (node.type === 'router') return '#FFC107'; // Orange
  if (node.type === 'bitcoin_node_pool') return '#F7931A'; // Bitcoin orange
  if (node.type === 'pool') return '#2196F3'; // Blue
  
  // Miner nodes - use health color
  if (node.status !== 'online') return '#9E9E9E'; // Grey
  const health = networkHealthData.value[node.id];
  return getNodeHealthColor(health);
};

// Node size
const getNodeSize = (node) => {
  if (node.type === 'router') return 25;
  if (node.type === 'pool' || node.type === 'bitcoin_node_pool') {
    // Size based on number of connected miners
    return 15 + (node.connectedMiners?.length || 0) * 3;
  }
  return 15; // Miner nodes
};

// Link colors (based on latency)
const getLinkColor = (link) => {
  if (link.type === 'miner-connection') {
    // Router to miner - use miner health color
    if (!link.latency) return '#999';
    if (link.latency > 50) return '#E53935'; // Red
    if (link.latency > 25) return '#FFC107'; // Yellow
    return '#43A047'; // Green
  }
  
  if (link.type === 'pool-connection') {
    // Miner to pool - use pool health color
    if (!link.latency) return '#999';
    if (link.latency > 200) return '#E53935'; // Red
    if (link.latency > 100) return '#FFC107'; // Yellow
    return '#43A047'; // Green
  }
  
  return '#999';
};

// Link width (thicker for better connections)
const getLinkWidth = (link) => {
  if (!link.latency) return 1;
  if (link.latency < 50) return 3; // Excellent
  if (link.latency < 100) return 2; // Good
  return 1; // Poor
};
```

**Node Icons**:

```javascript
const addNodeIcons = (nodeSelection) => {
  nodeSelection.each(function(d) {
    const nodeGroup = d3.select(this);
    
    if (d.type === 'router') {
      // Router icon
      nodeGroup.append("text")
        .attr("text-anchor", "middle")
        .attr("dominant-baseline", "central")
        .attr("fill", "#fff")
        .attr("font-size", "20px")
        .text("🌐");
    } else if (d.type === 'bitcoin_node_pool') {
      // Bitcoin node icon
      nodeGroup.append("image")
        .attr("xlink:href", "/bitcoin-symbol.svg")
        .attr("x", -12)
        .attr("y", -12)
        .attr("width", 24)
        .attr("height", 24);
    } else if (d.type === 'pool') {
      // Pool server icon
      nodeGroup.append("text")
        .attr("text-anchor", "middle")
        .attr("dominant-baseline", "central")
        .attr("fill", "#fff")
        .attr("font-size", "18px")
        .text("🏊");
    } else {
      // Miner icons (existing logic)
      // ... existing miner icon code
    }
  });
};
```

**Pool Node Click Handler**:

```javascript
const handlePoolNodeClick = (event, poolNode) => {
  selectedPool.value = {
    url: poolNode.url,
    port: poolNode.port,
    latency: poolNode.latency,
    status: poolNode.status,
    connectedMiners: poolNode.connectedMiners.map(minerId => {
      const miner = miners.value.find(m => m.id === minerId);
      return {
        id: minerId,
        name: miner?.name || minerId,
        type: miner?.type
      };
    })
  };
  showPoolDetails.value = true;
};
```

**Pool Details Dialog**:

```vue
<v-dialog v-model="showPoolDetails" max-width="600px">
  <v-card v-if="selectedPool">
    <v-card-title>
      Pool Server Details
      <v-spacer></v-spacer>
      <v-chip :color="getPoolStatusColor(selectedPool.status)" dark small>
        {{ selectedPool.status }}
      </v-chip>
    </v-card-title>
    <v-card-text>
      <v-table>
        <tbody>
          <tr>
            <td><strong>URL:</strong></td>
            <td>{{ selectedPool.url }}</td>
          </tr>
          <tr>
            <td><strong>Port:</strong></td>
            <td>{{ selectedPool.port }}</td>
          </tr>
          <tr>
            <td><strong>Latency:</strong></td>
            <td :style="{ color: getLatencyColor(selectedPool.latency) }">
              {{ selectedPool.latency ? `${selectedPool.latency.toFixed(1)} ms` : 'N/A' }}
            </td>
          </tr>
          <tr>
            <td><strong>Connected Miners:</strong></td>
            <td>{{ selectedPool.connectedMiners.length }}</td>
          </tr>
        </tbody>
      </v-table>
      
      <div class="mt-4">
        <div class="text-subtitle-2 mb-2">Miners Using This Pool:</div>
        <v-chip-group column>
          <v-chip 
            v-for="miner in selectedPool.connectedMiners" 
            :key="miner.id"
            :color="getMinerTypeColor(miner.type)"
            text-color="white"
            size="small"
            @click="navigateToMiner(miner.id)"
          >
            {{ miner.name }}
          </v-chip>
        </v-chip-group>
      </div>
    </v-card-text>
    <v-card-actions>
      <v-spacer></v-spacer>
      <v-btn color="primary" @click="showPoolDetails = false">Close</v-btn>
    </v-card-actions>
  </v-card>
</v-dialog>
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

### Network Health Data Model (Enhanced)

```typescript
interface PoolLatency {
  url: string;
  port: number;
  latency_ms: number | null;
  status: 'healthy' | 'degraded' | 'poor' | 'unreachable';
}

interface NetworkHealth {
  miner_id: string;
  miner_latency_ms: number | null;
  packet_loss_percent: number;
  uptime_seconds: number;
  jitter_ms: number;
  pool_latency: PoolLatency | null;
  total_path_latency_ms: number | null;
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

**Enhanced Table for Network Health with Pool Latency**:
```sql
CREATE TABLE IF NOT EXISTS network_health (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    miner_id TEXT NOT NULL,
    miner_latency_ms REAL,
    packet_loss_percent REAL,
    uptime_seconds INTEGER,
    jitter_ms REAL,
    pool_url TEXT,
    pool_port INTEGER,
    pool_latency_ms REAL,
    total_path_latency_ms REAL,
    status TEXT,
    measured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (miner_id) REFERENCES miners(id) ON DELETE CASCADE
);

CREATE INDEX idx_network_health_miner_time 
ON network_health(miner_id, measured_at);

CREATE INDEX idx_network_health_pool
ON network_health(pool_url, measured_at);
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
