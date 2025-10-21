# Implementation Plan

- [x] 1. Implement Header Refresh Button Endpoint and Functionality

  - Create POST /api/miners/refresh endpoint in backend API service
  - Wire endpoint to miner manager's refresh functionality
  - Add refreshMiners() method to frontend miners store
  - Update all views using refresh buttons to call new endpoint
  - Test refresh functionality using Chrome DevTools MCP to verify data updates
  - Verify loading states and error handling work correctly
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 2. Implement Real-time Analytics Chart Updates

- [x] 2.1 Enhance WebSocket metrics broadcasting

  - Modify backend to broadcast metrics_update events when metrics are saved
  - Ensure WebSocket payload includes miner_id and all metric fields
  - Test WebSocket message format and delivery
  - _Requirements: 2.1_

- [x] 2.2 Add WebSocket listener in Analytics view

  - Subscribe to metrics_update events in Analytics.vue
  - Implement handleMetricsUpdate() to append new data to charts
  - Add throttling to prevent excessive updates (max 1 per second)
  - Test real-time updates using Chrome DevTools MCP by saving metrics and observing chart changes
  - Verify chart view/zoom preservation during updates
  - _Requirements: 2.2, 2.3, 2.4, 2.5_

- [x] 3. Implement Dual Timeframe Selection (Range + Increment)

- [x] 3.1 Create separate time range and time increment controls for the Analytics Page

  - Update existing Time Range button group (1h, 15m, 1h, 24h, 7d, 30d, All Time)
  - Add Time Increment button group (1m, 15m, 1h, 1d)
  - Remove Apply button from UI
  - Implement immediate update on selection change
  - _Requirements: 3.1, 3.2, 3.3_

- [x] 3.2 Implement validation and auto-adjustment logic

  - Create adjustIncrementForRange() function to validate combinations
  - Auto-adjust increment when invalid range selected
  - Add visual feedback for active selections
  - Test all range/increment combinations using Chrome DevTools MCP
  - Verify charts update within 1.5 seconds of selection
  - Test with insufficient data scenarios
  - _Requirements: 3.4, 3.5, 3.6_

- [x] 4. Populate Existing Analytics Charts on Miner Details Page

- [x] 4.1 Populate existing chart sections with data

  - Locate existing Hashrate History, Temperature History, and Power Consumption chart sections in MinerDetail.vue
  - Implement fetchPreviewMetrics() to fetch last 6 hours of data for current miner
  - Wire chart data to existing canvas elements
  - Rename section title to "Analytics Preview" for clarity
  - Add "See Full Analytics" button that navigates to Analytics page with current miner pre-selected
  - _Requirements: 4.1, 4.2, 4.3, 4.5_

- [x] 4.2 Wire preview charts to real-time updates

  - Subscribe to WebSocket metrics updates for current miner
  - Update existing charts when new metrics arrive
  - Test chart population using Chrome DevTools MCP
  - Verify navigation to Analytics page with pre-selected miner works
  - Test error states when data unavailable (show appropriate message in chart area)
  - _Requirements: 4.4, 4.6_

- [x] 5. ~~Remove Tab Navigation from Miner Details Page~~ (NOT NEEDED - Tabs were fixed by migrating to Vuetify 3 components)

  - ~~Remove v-tabs and v-tab components from MinerDetail.vue~~
  - ~~Convert tab content to vertically-stacked card sections~~
  - Fixed by replacing deprecated Vuetify 2 components (v-tabs-items, v-tab-item, v-simple-table) with Vuetify 3 equivalents (v-window, v-window-item, v-table)
  - Tabs now work correctly and provide better UX than vertical stacking
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 6. Fix Network Page Refresh and Visualization

- [x] 6.1 Enhance refresh functionality

  - Update refreshNetwork() to properly fetch and update data
  - Add success/error feedback with snackbar notifications
  - Ensure D3 visualization rebuilds after data fetch
  - Test refresh using Chrome DevTools MCP
  - Verify all layout types (Force, Radial, Grid, Tree) work after refresh
  - _Requirements: 6.2_

- [x] 6.2 Verify and fix visualization interactions

  - Test node click to show miner details dialog
  - Verify layout type switching works correctly
  - Test export image functionality
  - Verify network statistics update correctly
  - Use Chrome DevTools MCP to interact with visualization and verify all features
  - _Requirements: 6.1, 6.3, 6.4, 6.5, 6.6_

- [x] 7. Implement Network Health Monitoring

- [x] 7.1 Create backend network health service

  - Create src/backend/services/network_health.py
  - Implement measure_latency() function using ping
  - Implement measure_packet_loss() function
  - Implement get_connection_uptime() function
  - Create GET /api/miners/{miner_id}/network-health endpoint
  - Test endpoint with script to verify metrics returned
  - _Requirements: 7.1, 7.2, 7.3_

- [x] 7.2 Add database support for network health

  - Create network_health table migration
  - Implement storage and retrieval functions
  - Add background polling task (every 30 seconds)
  - Test database operations with script
  - _Requirements: 7.6_

- [x] 7.3 Display network health on Network page

  - Add Network Health card to Network.vue
  - Display average latency, packet loss, and jitter
  - Implement color-coded node health indicators
  - Add warning badges for poor health miners
  - Test health display using Chrome DevTools MCP
  - Verify color coding reflects actual health status
  - Test with miner at 192.168.1.156
  - _Requirements: 7.4, 7.5, 7.7, 7.8_

- [x] 8. Implement Pool/Node Latency Monitoring

- [x] 8.1 Enhance network health service for pool latency

  - Add get_pool_info_from_miner() method to retrieve pool configuration from miners
  - Implement measure_pool_latency() method to ping pool servers
  - Add DNS resolution logic for pool hostnames
  - Handle both IP addresses and hostnames in pool URLs
  - Update get_network_health() to include pool latency measurements
  - Calculate total_path_latency_ms (miner + pool latency)
  - Implement \_calculate_pool_health_status() with thresholds (100ms warning, 200ms critical)
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 8.2 Update database schema for pool latency

  - Modify network_health table migration to add pool_url, pool_port, pool_latency_ms, total_path_latency_ms columns
  - Update save_network_health() in timeseries_storage.py to store pool latency data
  - Update query methods to retrieve pool latency data
  - Create index on pool_url for efficient queries
  - Test database operations with pool latency data
  - _Requirements: 8.5_

- [x] 8.3 Display pool latency on Network page

  - Update Network Health card to show separate miner and pool latency averages
  - Add "Pool Connections" section showing unique pools with their latencies
  - Implement color coding for pool latency (green < 100ms, yellow < 200ms, red >= 200ms)
  - Update node tooltips to show pool information and latency
  - Display total path latency for each miner
  - Add visual indicators for high pool latency (warning/critical)
  - Test display with miner at 192.168.1.156
  - _Requirements: 8.5, 8.6, 8.7, 8.8_

- [x] 8.4 Handle edge cases and errors

  - Handle unreachable pool servers gracefully (display "Unreachable")
  - Handle DNS resolution failures for pool hostnames
  - Handle miners with no pool configuration
  - Handle ICMP ping blocked by firewalls (fallback to TCP connection timing)
  - Display appropriate error messages for unavailable metrics

  - _Requirements: 8.9_

- [ ] 9. Add Pool and Node Visualization to Network Topology




- [x] 9.1 Enhance network graph building logic

  - Modify buildNetworkGraph() to extract pool information from network health data
  - Create pool nodes for unique pool URLs (deduplicate if multiple miners use same pool)
  - Add links from miners to their respective pools
  - Track connected miners count for each pool node
  - Distinguish between pool servers and local Bitcoin nodes
  - _Requirements: 9.1, 9.2, 9.4, 9.5_

- [x] 9.2 Implement pool node visual styling


  - Add pool node colors (blue for pools, Bitcoin Orange for local nodes)
  - Size pool nodes based on number of connected miners
  - Add pool server icon (🏊) for pool nodes
  - Use Bitcoin logo for local Bitcoin node pools
  - Color-code connection lines based on pool latency (green/yellow/red)
  - Vary link width based on connection quality
  - _Requirements: 9.3, 9.7_

- [x] 9.3 Add pool node interaction



  - Implement click handler for pool nodes
  - Create pool details dialog showing URL, port, latency, and connected miners
  - Add navigation from pool dialog to individual miners
  - Display pool status indicator (healthy/degraded/poor/unreachable)
  - Test pool node interactions using Chrome DevTools MCP
  - _Requirements: 9.6, 9.8_

- [x] 9.4 Update network statistics



  - Add pool count to network statistics card
  - Show unique pools being used across all miners
  - Display average pool latency in statistics
  - Update export image functionality to include pool nodes
  - Test complete visualization with pools and nodes
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8_

- [ ] 10. Comprehensive Testing and Verification
- [ ] 10.1 Test all fixes with Chrome DevTools MCP

  - Start development server using controlPwshProcess
  - Navigate to each affected page using mcp_chrome_devtools
  - Take screenshots of before/after states
  - Verify all interactive elements work correctly
  - Test error scenarios and edge cases
  - Document any issues found

- [ ] 10.2 Run automated tests

  - Execute frontend unit tests for modified components
  - Run backend API tests for new endpoints
  - Verify WebSocket functionality with integration tests
  - Check for console errors and warnings

- [ ] 10.3 Performance testing

  - Verify chart updates don't cause lag
  - Test with multiple miners (5+) to ensure scalability
  - Monitor WebSocket message frequency
  - Check network health polling doesn't impact performance
  - Verify pool latency measurements don't slow down UI

- [ ] 10.4 Cross-browser compatibility and real-world testing
  - Test in Chrome using DevTools MCP
  - Verify responsive layouts on different screen sizes
  - Test with actual miner at 192.168.1.156
  - Verify pool latency measurements with real pool connections
  - Test with both local Bitcoin nodes and remote pools
