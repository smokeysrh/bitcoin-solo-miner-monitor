# Implementation Plan

- [ ] 1. Implement Refresh Button Endpoint and Functionality
  - Create POST /api/miners/refresh endpoint in backend API service
  - Wire endpoint to miner manager's refresh functionality
  - Add refreshMiners() method to frontend miners store
  - Update all views using refresh buttons to call new endpoint
  - Test refresh functionality using Chrome DevTools MCP to verify data updates
  - Verify loading states and error handling work correctly
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [ ] 2. Implement Real-time Analytics Chart Updates
- [ ] 2.1 Enhance WebSocket metrics broadcasting
  - Modify backend to broadcast metrics_update events when metrics are saved
  - Ensure WebSocket payload includes miner_id and all metric fields
  - Test WebSocket message format and delivery
  - _Requirements: 2.1_

- [ ] 2.2 Add WebSocket listener in Analytics view
  - Subscribe to metrics_update events in Analytics.vue
  - Implement handleMetricsUpdate() to append new data to charts
  - Add throttling to prevent excessive updates (max 1 per second)
  - Test real-time updates using Chrome DevTools MCP by saving metrics and observing chart changes
  - Verify chart view/zoom preservation during updates
  - _Requirements: 2.2, 2.3, 2.4, 2.5_

- [ ] 3. Implement Dual Timeframe Selection (Range + Increment)
- [ ] 3.1 Create separate time range and time increment controls
  - Add Time Range button group (1h, 24h, 7d, 30d)
  - Add Time Increment button group (1m, 15m, 1h, 1d)
  - Remove Apply button from UI
  - Implement immediate update on selection change
  - _Requirements: 3.1, 3.2, 3.3_

- [ ] 3.2 Implement validation and auto-adjustment logic
  - Create adjustIncrementForRange() function to validate combinations
  - Auto-adjust increment when invalid range selected
  - Add visual feedback for active selections
  - Test all range/increment combinations using Chrome DevTools MCP
  - Verify charts update within 1.5 seconds of selection
  - Test with insufficient data scenarios
  - _Requirements: 3.4, 3.5, 3.6_

- [ ] 4. Populate Existing Analytics Charts on Miner Details Page
- [ ] 4.1 Populate existing chart sections with data
  - Locate existing Hashrate History, Temperature History, and Power Consumption chart sections in MinerDetail.vue
  - Implement fetchPreviewMetrics() to fetch last 6 hours of data for current miner
  - Wire chart data to existing canvas elements
  - Rename section title to "Analytics Preview" for clarity
  - Add "See Full Analytics" button that navigates to Analytics page with current miner pre-selected
  - _Requirements: 4.1, 4.2, 4.3, 4.5_

- [ ] 4.2 Wire preview charts to real-time updates
  - Subscribe to WebSocket metrics updates for current miner
  - Update existing charts when new metrics arrive
  - Test chart population using Chrome DevTools MCP
  - Verify navigation to Analytics page with pre-selected miner works
  - Test error states when data unavailable (show appropriate message in chart area)
  - _Requirements: 4.4, 4.6_

- [ ] 5. Remove Tab Navigation from Miner Details Page
  - Remove v-tabs and v-tab components from MinerDetail.vue
  - Convert tab content to vertically-stacked card sections
  - Add consistent spacing between sections (mt-4)
  - Ensure all content (Overview, Performance, Pool, Settings) remains accessible
  - Test scrolling behavior using Chrome DevTools MCP
  - Verify responsive layout on different screen sizes
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ] 6. Fix Network Page Refresh and Visualization
- [ ] 6.1 Enhance refresh functionality
  - Update refreshNetwork() to properly fetch and update data
  - Add success/error feedback with snackbar notifications
  - Ensure D3 visualization rebuilds after data fetch
  - Test refresh using Chrome DevTools MCP
  - Verify all layout types (Force, Radial, Grid, Tree) work after refresh
  - _Requirements: 6.2_

- [ ] 6.2 Verify and fix visualization interactions
  - Test node click to show miner details dialog
  - Verify layout type switching works correctly
  - Test export image functionality
  - Verify network statistics update correctly
  - Use Chrome DevTools MCP to interact with visualization and verify all features
  - _Requirements: 6.1, 6.3, 6.4, 6.5, 6.6_

- [ ] 7. Implement Network Health Monitoring
- [ ] 7.1 Create backend network health service
  - Create src/backend/services/network_health.py
  - Implement measure_latency() function using ping
  - Implement measure_packet_loss() function
  - Implement get_connection_uptime() function
  - Create GET /api/miners/{miner_id}/network-health endpoint
  - Test endpoint with script to verify metrics returned
  - _Requirements: 7.1, 7.2, 7.3_

- [ ] 7.2 Add database support for network health
  - Create network_health table migration
  - Implement storage and retrieval functions
  - Add background polling task (every 30 seconds)
  - Test database operations with script
  - _Requirements: 7.6_

- [ ] 7.3 Display network health on Network page
  - Add Network Health card to Network.vue
  - Display average latency, packet loss, and jitter
  - Implement color-coded node health indicators
  - Add warning badges for poor health miners
  - Test health display using Chrome DevTools MCP
  - Verify color coding reflects actual health status
  - Test with miner at 192.168.1.156
  - _Requirements: 7.4, 7.5, 7.7, 7.8_

- [ ] 8. Comprehensive Testing and Verification
- [ ] 8.1 Test all fixes with Chrome DevTools MCP
  - Start development server using controlPwshProcess
  - Navigate to each affected page using mcp_chrome_devtools
  - Take screenshots of before/after states
  - Verify all interactive elements work correctly
  - Test error scenarios and edge cases
  - Document any issues found

- [ ] 8.2 Run automated tests
  - Execute frontend unit tests for modified components
  - Run backend API tests for new endpoints
  - Verify WebSocket functionality with integration tests
  - Check for console errors and warnings

- [ ] 8.3 Performance testing
  - Verify chart updates don't cause lag
  - Test with multiple miners (5+) to ensure scalability
  - Monitor WebSocket message frequency
  - Check network health polling doesn't impact performance

- [ ] 8.4 Cross-browser compatibility
  - Test in Chrome using DevTools MCP
  - Verify responsive layouts on different screen sizes
  - Test with actual miner at 192.168.1.156
