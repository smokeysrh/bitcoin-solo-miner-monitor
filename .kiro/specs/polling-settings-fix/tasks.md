# Implementation Plan

- [x] 1. Create Polling Manager Composable

  - Create `src/frontend/src/composables/usePollingManager.js` with reactive interval management
  - Implement settings watcher that automatically updates intervals when settings change
  - Add polling state tracking (isPolling, lastPollTime, pollCount)
  - Implement automatic cleanup on component unmount
  - Add minimum interval enforcement (5 seconds) for safety
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 2. Enhance Settings Store with Change Events

  - Add event emitter to Settings Store for broadcasting settings changes
  - Implement `emitSettingsChange` method that fires when refresh_interval changes
  - Add `getCurrentInterval` helper method with fallback to defaults

  - Ensure settings changes are logged at info level (not debug)
  - _Requirements: 1.1, 1.3, 4.3_

- [x] 3. Update Dashboard Component Polling

  - Replace manual `setInterval` in Dashboard.vue with `usePollingManager`
  - Remove old `refreshInterval` variable and cleanup code
  - Test that polling interval updates when settings change
  - Verify component cleanup on unmount
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.3_

- [x] 4. Update Miners Component Polling

  - Replace manual `setInterval` in Miners.vue with `usePollingManager`
  - Remove old `refreshInterval` variable and cleanup code
  - Test that polling interval updates when settings change
  - Verify component cleanup on unmount
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.3_

- [x] 5. Update MinerDetail Component Polling

  - Replace manual `setInterval` in MinerDetail.vue with `usePollingManager`
  - Remove old `refreshInterval` variable and cleanup code
  - Test that polling interval updates when settings change
  - Verify component cleanup on unmount
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.3_

- [x] 6. Update Network Component Polling

  - Replace manual `setInterval` in Network.vue with `usePollingManager`
  - Remove old `refreshInterval` variable and cleanup code
  - Test that polling interval updates when settings change
  - Verify component cleanup on unmount
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.3_

- [x] 7. Remove Console Logging Spam

  - Add DEBUG_MODE flag to settingsService.js based on environment
  - Update axios interceptors to only log in debug mode
  - Remove "No auth required" log statements for /api/miners requests
  - Keep error logging for all failed requests with status codes
  - Test that production mode has minimal console output
  - _Requirements: 4.1, 4.2, 4.4_

- [x] 8. Implement WebSocket Message Priority Queue

  - Add message priority queue structure to websocket.js (high, normal, low)
  - Implement `processMessageQueue` function that processes high-priority first
  - Update ping handler to queue pong responses with high priority
  - Ensure heartbeat responses are sent within 100ms
  - _Requirements: 3.1, 3.2, 3.3_

- [x] 9. Implement Backend Change Detection

  - Add `_last_broadcast_data` cache dictionary to WebSocketManager
  - Implement `_hash_data` method for generating data hashes
  - Update `broadcast` method to check for data changes before broadcasting
  - Skip broadcasts when data hash matches previous broadcast
  - Log skipped broadcasts at debug level
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 10. Update Backend Broadcast Intervals

  - Change miners broadcast interval from 1.0s to 5.0s in WebSocketManager
  - Change alerts broadcast interval from 5.0s to 10.0s
  - Change system broadcast interval from 10.0s to 30.0s
  - Keep discovery interval at 0.5s for real-time scan updates
  - _Requirements: 5.1, 5.2_

- [x] 11. Increase WebSocket Heartbeat Timeout

  - Update heartbeat timeout in WebSocketManager from 75s to 180s
  - Update stale connection detection threshold (2.5 × heartbeat_interval)
  - Test that connections stay alive during heavy load
  - _Requirements: 3.4_

- [x] 12. Add Polling Coordination Logic

  - Implement duplicate request detection in usePollingManager
  - Add 5-second window check to prevent simultaneous polls from multiple components
  - Log warnings when multiple polling sources are detected
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [ ] 13. Create Diagnostics Page

  - Create `src/frontend/src/views/Diagnostics.vue` component
  - Display current polling intervals for all active components
  - Show WebSocket connection status, latency, and last heartbeat
  - Display last 10 API requests with timestamps
  - Show current settings values and last update time
  - Add export functionality for diagnostic data as JSON
  - _Requirements: 6.4, 6.5_

- [ ] 14. Add Diagnostics Route

  - Add route for /diagnostics in router configuration
  - Make accessible only in development mode or with ?diagnostics=true parameter
  - Add navigation link in development mode
  - _Requirements: 6.4_

- [ ] 15. Test Settings Application End-to-End

  - Open Settings page and change refresh_interval to 120 seconds
  - Open browser DevTools Network tab
  - Verify /api/miners requests occur every 120 seconds (±2 seconds)
  - Navigate between Dashboard, Miners, and Network pages
  - Verify interval persists across navigation
  - Check that settings are saved to localStorage
  - _Requirements: 1.1, 1.3, 1.4, 6.1, 6.2_

- [ ] 16. Test WebSocket Stability During Network Scan
- [ ] 16.1 Short Scan Test (No Miners Expected)
  - Start a network scan of 192.168.1.0/28 (16 hosts, quick scan)
  - Open browser DevTools and monitor WebSocket connection
  - Verify connection stays open for entire scan duration
  - Verify progress updates appear in real-time
  - Verify scan completes and shows "0 miners found" result
  - Check that no "Client is stale" messages appear in backend logs
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 6.3_
- [ ] 16.2 Long Scan Test (Real Miner Detection)

  - Start a network scan that includes 192.168.1.156 (your miner)
  - Use a larger range like 192.168.1.0/24 (254 hosts) for longer duration
  - Open browser DevTools and monitor WebSocket connection
  - Verify connection stays open for entire scan duration (5+ minutes)
  - Verify progress updates appear in real-time throughout the scan
  - Verify scan detects the miner at .156 and displays it in results
  - Verify miner details are correct (type, model, IP address)
  - Check that WebSocket remains stable during the entire long scan
  - Check that no "Client is stale" messages appear in backend logs
  - Verify no browser freezing or UI lockups during the scan
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 6.3_

- [ ] 17. Test Console Logging Cleanup

  - Open browser console in production mode
  - Navigate through Dashboard, Miners, Settings pages
  - Verify no "No auth required" messages appear
  - Trigger an API error (disconnect network briefly)
  - Verify error is logged with status code and endpoint
  - Switch to development mode and verify debug logs appear
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [ ] 18. Test Backend Broadcast Optimization

  - Monitor backend logs during normal operation
  - Verify miners_update broadcasts occur every 5 seconds (not 1 second)
  - Verify broadcasts are skipped when miner data hasn't changed
  - Add a new miner and verify broadcast occurs immediately
  - Check that "Skipping broadcast - no changes" appears in debug logs
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ] 19. Verify Performance Improvements

  - Measure HTTP request frequency before and after fixes
  - Measure backend broadcast frequency before and after fixes
  - Measure console log count before and after fixes
  - Document performance improvements in test results
  - Verify 90%+ reduction in HTTP requests and broadcasts
  - _Requirements: 2.5, 5.1, 5.2_

- [ ] 20. Create Test Summary Report
  - Document all test results in a summary report
  - Include screenshots of Network tab showing correct intervals
  - Include screenshots of successful network scan completion
  - Include backend log excerpts showing optimized broadcasts
  - Include performance metrics (before/after comparisons)
  - Verify all acceptance criteria are met
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_
