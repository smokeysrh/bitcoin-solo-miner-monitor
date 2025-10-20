# Bitcoin Node Integration Implementation Plan

## Task Overview

This implementation plan follows a **frontend-first, incremental integration** approach. We build UI components first with mock data, then progressively connect backend services one at a time. This allows testing each feature as it's implemented, catching bugs early without losing context.

**Note:** Code audit (October 20, 2025) revealed that basic Bitcoin node detection already exists (`BitcoinNode` model and `MinerFactory` integration). This plan builds on that foundation.

## Implementation Strategy

1. **Frontend First**: Build all UI components with mock/static data
2. **Backend Incremental**: Add backend services one at a time
3. **Test As You Go**: Connect and test each feature before moving to the next
4. **No Bug Pile-Up**: Fix issues immediately while context is fresh

## Implementation Tasks

### Phase 1: Frontend UI Components (Mock Data)

- [ ] 1. Create Bitcoin Nodes Page with Mock Data
  - Create `BitcoinNodes.vue` in `src/frontend/src/views/`
  - Display mock list of nodes with name, IP, port, status
  - Add "Add Node" button (non-functional for now)
  - Show mock node details: version, peers, sync status, block height
  - Add edit/remove buttons (non-functional for now)
  - Use mock data: `[{name: "Local Node", ip: "192.168.1.100", port: 8332, status: "online"}]`
  - Style with existing Vuetify components for consistency
  - _Requirements: 7.1, 7.2, 7.6, 7.7, 7.8_

- [ ] 1.1 Write component tests for Bitcoin Nodes page
  - Test mock data rendering
  - Test button presence
  - _Requirements: 7.1-7.8_

- [ ] 2. Create Network Status Dashboard Widget with Mock Data
  - Create `NetworkStatusWidget.vue` in `src/frontend/src/components/`
  - Display mock block height: 850,000
  - Display mock block hash: "00000000000000000002a..."
  - Display mock difficulty: "61.03 T"
  - Display mock network hashrate: "450 EH/s"
  - Display mock mempool: "2,500 transactions (3.2 MB)"
  - Display mock time since last block: "8 minutes"
  - Add to Dashboard.vue
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [ ] 2.1 Write component tests for Network Status widget
  - Test mock data display
  - _Requirements: 8.1-8.5_

- [ ] 3. Create Solo Mining Stats Widget with Mock Data
  - Create `SoloMiningStatsWidget.vue` in `src/frontend/src/components/`
  - Display mock total hashrate: "100 TH/s"
  - Display mock probability: "0.000022% (1 in 4,500,000)"
  - Display mock time to block: "8y 6m 18d 9h"
  - Display mock expected blocks: "0.003 per day, 0.02 per week, 0.09 per month, 1.1 per year"
  - Add to Dashboard.vue
  - _Requirements: 9.1, 9.2, 9.3, 9.4_

- [ ] 3.1 Write component tests for Solo Mining Stats widget
  - Test mock data display
  - _Requirements: 9.1-9.4_

- [ ] 4. Create Blocks Found Widget with Mock Data
  - Create `BlocksFoundWidget.vue` in `src/frontend/src/components/`
  - Display mock blocks found count: "0"
  - Add "View History" button (non-functional for now)
  - Show "0 Blocks Found - Keep Mining!" message
  - Add to Dashboard.vue
  - _Requirements: 10.1, 10.5, 10.9_

- [ ] 4.1 Write component tests for Blocks Found widget
  - Test display
  - _Requirements: 10.1, 10.5, 10.9_


- [ ] 5. Create Halving Countdown Header Component with Mock Data
  - Create `HalvingCountdown.vue` in `src/frontend/src/components/`
  - Add to App.vue header for persistence across pages
  - Display mock countdown: "Next Halving: 3y 8m 12d 6h"
  - Add tooltip showing mock date and block height
  - Style to fit in header without cluttering
  - _Requirements: 13.1, 13.4, 13.5, 13.6, 13.7, 13.11_

- [ ] 5.1 Write component tests for Halving Countdown
  - Test display
  - Test tooltip
  - _Requirements: 13.1-13.11_

- [ ] 6. Add Navigation Menu Item
  - Update `src/frontend/src/router/index.js`
  - Add "Bitcoin Nodes" route pointing to BitcoinNodes.vue
  - Update main navigation to include "Bitcoin Nodes" between "Miners" and "Analytics"
  - Test navigation works
  - _Requirements: 14.1_

### Phase 2: Backend Foundation (RPC Client & Data Storage)

- [ ] 7. Implement Bitcoin RPC Client
  - Create `BitcoinRPCClient` class in `src/backend/services/bitcoin_rpc_client.py`
  - Implement JSON-RPC 1.0 protocol with HTTP Basic Authentication
  - Add whitelist of safe read-only methods
  - Implement retry logic with exponential backoff (max 3 attempts)
  - Add batch RPC call support
  - Implement connection testing method
  - Test manually with local Bitcoin node
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7_

- [ ] 7.1 Write unit tests for RPC client
  - Mock Bitcoin Core responses
  - Test authentication and retry logic
  - _Requirements: 1.1-1.7_

- [ ] 8. Enhance Existing BitcoinNode Model
  - Update `src/backend/models/bitcoin_node.py`
  - Add RPC client integration
  - Replace placeholder methods with actual RPC calls
  - Add RPC credential fields (username, password)
  - Add ZMQ endpoint configuration
  - Keep existing detection logic intact
  - Test with local Bitcoin node
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [ ] 8.1 Write unit tests for enhanced BitcoinNode
  - Test RPC integration
  - _Requirements: 1.1-1.4_

- [ ] 9. Implement Data Persistence
  - Extend `src/backend/services/data_storage.py`
  - Add bitcoin_nodes table schema
  - Add blocks_found table schema
  - Implement AES-256 password encryption
  - Implement CRUD operations for nodes
  - Test database operations
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

- [ ] 9.1 Write unit tests for data persistence
  - Test encryption/decryption
  - Test CRUD operations
  - _Requirements: 2.1-2.7_

### Phase 3: Connect Bitcoin Nodes Page to Backend

- [ ] 10. Create Bitcoin Node Management API Endpoints
  - Add endpoints to `src/backend/api/api_service.py`
  - GET /api/bitcoin-nodes - retrieve all nodes
  - POST /api/bitcoin-nodes - add new node
  - DELETE /api/bitcoin-nodes/{node_id} - remove node
  - GET /api/bitcoin-nodes/{node_id}/status - get node status
  - POST /api/bitcoin-nodes/{node_id}/test-connection - validate credentials
  - Test endpoints with Postman or curl
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [ ] 10.1 Write API integration tests
  - Test all endpoints
  - _Requirements: 6.1-6.5_

- [ ] 11. Connect Bitcoin Nodes Page to API
  - Update `BitcoinNodes.vue` to fetch real data from GET /api/bitcoin-nodes
  - Implement "Add Node" dialog with IP, port, username, password inputs
  - Connect "Test Connection" button to POST /api/bitcoin-nodes/{id}/test-connection
  - Connect "Add" button to POST /api/bitcoin-nodes
  - Connect "Remove" button to DELETE /api/bitcoin-nodes/{id}
  - Test adding, viewing, and removing nodes
  - _Requirements: 7.3, 7.4, 7.5, 7.6_

- [ ] 11.1 Write integration tests
  - Test API integration
  - _Requirements: 7.3-7.6_


### Phase 4: Network Statistics Service & Widget Connection

- [ ] 12. Create Time Formatting Service
  - Create `TimeFormattingService` class in `src/backend/services/time_formatting_service.py`
  - Implement `format_duration(seconds)` with intelligent formatting rules
  - Implement `format_halving_countdown(seconds)` with minutes for final hours
  - Implement `calculate_halving_blocks_remaining(current_height)`
  - Implement `estimate_halving_time(blocks_remaining)`
  - Test with various time values
  - _Requirements: 4.4, 4.5, 4.6, 4.7, 4.8, 13.4, 13.5, 13.6, 13.7, 13.8_

- [ ] 12.1 Write unit tests for time formatting
  - Test all formatting rules
  - _Requirements: 4.4-4.8, 13.4-13.8_

- [ ] 13. Create Network Statistics Service
  - Create `NetworkStatisticsService` in `src/backend/services/network_statistics_service.py`
  - Implement periodic collection every 60 seconds
  - Add getblockchaininfo and getmempoolinfo RPC calls
  - Calculate network hashrate: (difficulty / 600) * 2^32
  - Calculate time since last block
  - Implement 60-second caching
  - Test with local Bitcoin node
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8_

- [ ] 13.1 Write unit tests for network statistics
  - Mock RPC responses
  - Test calculations
  - _Requirements: 3.1-3.8_

- [ ] 14. Add Network Statistics API Endpoint
  - Add GET /api/network-statistics to `api_service.py`
  - Return blockchain info, mempool info, network hashrate, time since last block
  - Test endpoint
  - _Requirements: 6.6_

- [ ] 15. Connect Network Status Widget to API
  - Update `NetworkStatusWidget.vue` to fetch from GET /api/network-statistics
  - Replace mock data with real API data
  - Add error handling for when node is offline
  - Test with real Bitcoin node
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8_

- [ ] 16. Connect Halving Countdown to API
  - Update `HalvingCountdown.vue` to fetch block height from GET /api/network-statistics
  - Calculate blocks remaining and time estimate
  - Use intelligent time formatting
  - Update every 60 seconds
  - Test countdown display
  - _Requirements: 13.1, 13.2, 13.3, 13.9, 13.10, 13.11_

### Phase 5: Solo Mining Analytics & Widget Connection

- [ ] 17. Create Solo Mining Analytics Service
  - Create `SoloMiningAnalyticsService` in `src/backend/services/solo_mining_analytics_service.py`
  - Inject TimeFormattingService dependency
  - Implement miner hashrate aggregation every 60 seconds
  - Calculate probability: (hashrate / network_hashrate) * 100
  - Calculate time to block in seconds: (difficulty * 2^32) / hashrate
  - Use TimeFormattingService for display formatting
  - Calculate expected blocks per day/week/month/year
  - Format probability as percentage and "1 in X"
  - Test with mock miner data
  - _Requirements: 4.1, 4.2, 4.3, 4.9, 4.10, 4.11, 4.12, 4.13_

- [ ] 17.1 Write unit tests for solo mining analytics
  - Test calculations
  - _Requirements: 4.1-4.13_

- [ ] 18. Add Solo Mining Stats API Endpoint
  - Add GET /api/solo-mining-stats to `api_service.py`
  - Return probability, time to block, expected blocks
  - Test endpoint
  - _Requirements: 6.7_

- [ ] 19. Connect Solo Mining Stats Widget to API
  - Update `SoloMiningStatsWidget.vue` to fetch from GET /api/solo-mining-stats
  - Replace mock data with real calculations
  - Display intelligent time formatting
  - Handle no miners/no node states
  - Test with real miners and node
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7_

### Phase 6: Block Discovery Service & Celebration

- [ ] 20. Implement Block Discovery Service with ZMQ
  - Install pyzmq dependency
  - Create `BlockDiscoveryService` in `src/backend/services/block_discovery_service.py`
  - Implement ZMQ connection to tcp://127.0.0.1:28332
  - Implement `_zmq_listener()` for hashblock notifications
  - Implement `_polling_fallback()` for 5-minute polling when ZMQ unavailable
  - Implement `_extract_coinbase_addresses()` to parse coinbase outputs
  - Implement `_check_block_ownership()` to compare against mining addresses
  - Record block discoveries to blocks_found table
  - Calculate luck factor
  - Test with local Bitcoin node (ZMQ and polling modes)
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9, 5.10_

- [ ] 20.1 Write unit tests for block discovery
  - Mock ZMQ messages
  - Test polling fallback
  - _Requirements: 5.1-5.10_

- [ ] 21. Add Blocks Found API Endpoint
  - Add GET /api/blocks-found to `api_service.py`
  - Return block discovery history
  - Test endpoint
  - _Requirements: 6.8_

- [ ] 22. Connect Blocks Found Widget to API and Add Celebration
  - Update `BlocksFoundWidget.vue` to fetch from GET /api/blocks-found
  - Subscribe to "block_discovery" WebSocket topic (implement in next phase)
  - When block discovered, trigger existing Bitcoin logo rain animation
  - Play celebration sound effect
  - Display notification overlay with block details
  - Create block history page component
  - Test celebration trigger manually
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8, 10.9_

### Phase 7: WebSocket Real-Time Updates

- [ ] 23. Extend WebSocket Manager
  - Update `src/backend/services/websocket_manager.py`
  - Add "bitcoin_nodes" topic for node status updates
  - Add "network_statistics" topic for blockchain/mempool data
  - Add "solo_mining_stats" topic for probability updates
  - Add "block_discovery" topic for block found notifications
  - Implement 60-second rate limiting per topic (except block_discovery)
  - Integrate with Network Statistics Service for broadcasts
  - Integrate with Block Discovery Service for celebration broadcasts
  - Test WebSocket connections
  - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8_

- [ ] 23.1 Write WebSocket integration tests
  - Test subscriptions and broadcasts
  - _Requirements: 11.1-11.8_

- [ ] 24. Connect Widgets to WebSocket Updates
  - Update `NetworkStatusWidget.vue` to subscribe to "network_statistics" topic
  - Update `SoloMiningStatsWidget.vue` to subscribe to "solo_mining_stats" topic
  - Update `BlocksFoundWidget.vue` to subscribe to "block_discovery" topic
  - Update `HalvingCountdown.vue` to subscribe to "network_statistics" topic
  - Test real-time updates work correctly
  - _Requirements: 8.6, 9.5, 10.2, 13.9_

### Phase 8: Setup Wizard Integration

- [ ] 25. Extend Setup Wizard with Bitcoin Node Discovery
  - Update `NetworkDiscoveryScreen.vue` in `src/frontend/src/components/wizard/`
  - Add Bitcoin node scanning to existing miner discovery
  - Scan ports 8332, 18332, 8333, 18333
  - Display found nodes in "Bitcoin Nodes Found" section
  - Create node configuration dialog component
  - Add RPC username/password inputs
  - Add "Test Connection" button
  - Check for ZMQ availability after successful RPC test
  - Create ZMQ setup instructions dialog
  - Add "Skip - Use Polling" and "Retry Detection" buttons
  - Save configured nodes on setup completion
  - Test complete setup wizard flow
  - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7, 12.8, 12.9, 12.10, 12.11_

- [ ] 25.1 Write setup wizard tests
  - Test node discovery integration
  - _Requirements: 12.1-12.11_

### Phase 9: Settings Integration

- [ ] 26. Add Bitcoin Node Settings Section
  - Update `Settings.vue` in `src/frontend/src/views/`
  - Add "Bitcoin Node Integration" section
  - Add enable/disable toggle
  - Add RPC timeout configuration (10-120 seconds)
  - Add block discovery polling interval (3-60 minutes, default 5)
  - Add statistics refresh interval (60-300 seconds)
  - Add mining address input for block discovery
  - Display ZMQ connection status indicator
  - Add "Show ZMQ Setup Instructions" button
  - Apply settings immediately without restart
  - Test all settings persist correctly
  - _Requirements: 14.2, 14.3, 14.4, 14.5, 14.6, 14.7, 14.8, 14.9, 14.10_

- [ ] 26.1 Write settings tests
  - Test settings persistence
  - _Requirements: 14.2-14.10_

- [ ] 27. Update About Page
  - Update `About.vue` to include Bitcoin node integration in features list
  - Test display
  - _Requirements: 14.8_

### Phase 10: Final Integration and Testing

- [ ] 28. End-to-End Integration Testing
  - Test complete flow: setup wizard → node configuration → monitoring
  - Verify ZMQ connection and polling fallback
  - Test all widgets update in real-time
  - Test halving countdown across all pages
  - Test block discovery celebration (if possible with testnet)
  - Test all API endpoints work correctly
  - Verify data persists across app restarts
  - Test error handling scenarios (node offline, RPC failures, etc.)
  - Test responsive design on mobile devices
  - Verify security: credential encryption, read-only RPC methods
  - Test navigation menu item visibility toggle
  - _Requirements: All requirements comprehensive validation_

- [ ] 29. Documentation and Cleanup
  - Add inline code comments where needed
  - Update any relevant documentation
  - Remove any debug logging
  - Verify all console errors are resolved
  - Final code review
