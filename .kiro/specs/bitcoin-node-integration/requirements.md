# Bitcoin Node Integration Requirements

## Introduction

This feature will transform the Bitcoin Solo Miner Monitor into the ultimate solo mining dashboard by integrating Bitcoin node connectivity. The app will automatically discover, connect to, and monitor Bitcoin Core nodes on the local network, providing comprehensive network statistics, solo mining analytics, and block discovery tracking that solo miners desperately need.

This integration will provide solo miners with real-time Bitcoin network data, probability calculations, and the most exciting feature of all - automatic detection and celebration when they find a block! The app will become a complete solo mining command center showing both miner hardware performance and Bitcoin network status.

## Current Implementation Status

**Note:** A code audit (October 20, 2025) revealed that basic Bitcoin node detection infrastructure exists:
- ✅ `BitcoinNode` model class with multi-port detection (8332, 18332, 8333, 18333)
- ✅ Integration into `MinerFactory` for automatic discovery
- ✅ Basic connection/disconnection methods
- ❌ No RPC client for actual blockchain data retrieval
- ❌ No data persistence, analytics, UI, or API endpoints

This spec focuses on building the missing 95% of functionality on top of the existing detection foundation.

## Glossary

- **Bitcoin Core**: The reference implementation of Bitcoin node software
- **RPC (Remote Procedure Call)**: The JSON-RPC interface exposed by Bitcoin Core for programmatic access
- **Coinbase Transaction**: The first transaction in a block, which includes the mining reward and identifies the miner
- **Network Difficulty**: A measure of how difficult it is to find a new block
- **Network Hashrate**: The total computational power of the Bitcoin network
- **Solo Mining**: Mining Bitcoin independently without joining a mining pool
- **Block Discovery**: The event when a miner successfully finds a valid block
- **Mempool**: The collection of unconfirmed transactions waiting to be included in a block
- **IBD (Initial Block Download)**: The process of syncing a new Bitcoin node with the blockchain
- **P2P Port**: The peer-to-peer network port used by Bitcoin nodes to communicate (8333 mainnet, 18333 testnet)
- **RPC Port**: The JSON-RPC interface port used for programmatic access (8332 mainnet, 18332 testnet)

## Requirements

## Requirements

### Requirement 1: Bitcoin RPC Client Implementation

**User Story:** As a solo miner, I want the app to communicate with my Bitcoin Core node via RPC so that I can retrieve blockchain data and network statistics.

**Note:** Basic detection exists; this requirement focuses on implementing actual RPC communication.

#### Acceptance Criteria

1. THE Bitcoin RPC Client SHALL support JSON-RPC 1.0 protocol for Bitcoin Core communication
2. WHEN RPC credentials are provided, THE Bitcoin RPC Client SHALL authenticate using HTTP Basic Authentication
3. THE Bitcoin RPC Client SHALL enforce a whitelist of read-only RPC methods to prevent wallet access
4. WHEN an RPC call is made, THE Bitcoin RPC Client SHALL return parsed JSON response data within 10 seconds
5. WHEN an RPC call fails due to network error, THE Bitcoin RPC Client SHALL retry up to 3 times with exponential backoff
6. THE Bitcoin RPC Client SHALL support batch RPC calls to retrieve multiple data points in a single request
7. WHEN authentication fails, THE Bitcoin RPC Client SHALL return an authentication error without retrying

### Requirement 2: Bitcoin Node Data Persistence

**User Story:** As a solo miner, I want my Bitcoin node configurations saved so that I don't have to reconfigure them after restarting the app.

#### Acceptance Criteria

1. THE Data Storage Service SHALL create a bitcoin_nodes table with fields for node_id, name, ip_address, port, username, and encrypted_password
2. WHEN RPC credentials are saved, THE Data Storage Service SHALL encrypt passwords using AES-256 encryption before storage
3. WHEN a Bitcoin node is added, THE Data Storage Service SHALL persist the configuration to the database within 2 seconds
4. WHEN the application starts, THE Data Storage Service SHALL load all saved Bitcoin node configurations from the database
5. WHEN a Bitcoin node is removed, THE Data Storage Service SHALL delete the configuration and all associated data from the database
6. THE Data Storage Service SHALL create a blocks_found table to store block discovery records with block_hash, height, timestamp, and reward fields
7. WHEN credentials are retrieved, THE Data Storage Service SHALL decrypt passwords only when needed for RPC calls

### Requirement 3: Network Statistics Collection Service

**User Story:** As a solo miner, I want the app to collect Bitcoin network statistics so that I can see current blockchain and mempool data.

#### Acceptance Criteria

1. THE Network Statistics Service SHALL retrieve blockchain info from Bitcoin Core every 60 seconds using getblockchaininfo RPC call
2. THE Network Statistics Service SHALL retrieve mempool info from Bitcoin Core every 60 seconds using getmempoolinfo RPC call
3. WHEN blockchain info is retrieved, THE Network Statistics Service SHALL extract block height, difficulty, and chain name
4. WHEN mempool info is retrieved, THE Network Statistics Service SHALL extract transaction count and mempool size in bytes
5. THE Network Statistics Service SHALL calculate network hashrate by dividing difficulty by 600 seconds and multiplying by 2^32
6. THE Network Statistics Service SHALL calculate time since last block by comparing current time to latest block timestamp
7. WHEN statistics are collected, THE Network Statistics Service SHALL cache results for 60 seconds to optimize performance
8. WHEN RPC calls fail, THE Network Statistics Service SHALL use cached data and log the error without crashing

### Requirement 4: Solo Mining Analytics Service

**User Story:** As a solo miner, I want to see probability calculations based on my hashrate and network difficulty so that I understand my chances of finding a block.

#### Acceptance Criteria

1. THE Solo Mining Analytics Service SHALL aggregate total hashrate from all connected miners every 60 seconds
2. WHEN total hashrate and network difficulty are known, THE Solo Mining Analytics Service SHALL calculate probability of finding next block as (hashrate / network_hashrate) * 100
3. WHEN total hashrate and network difficulty are known, THE Solo Mining Analytics Service SHALL calculate time to block in seconds as (difficulty * 2^32) / hashrate
4. WHEN formatting time to block for display, THE Solo Mining Analytics Service SHALL use intelligent formatting showing years, months, days, and hours as appropriate
5. WHEN time to block exceeds 365 days, THE Solo Mining Analytics Service SHALL display format as "Xy Xm Xd Xh" (e.g., "2y 3m 15d 8h")
6. WHEN time to block is between 30 and 365 days, THE Solo Mining Analytics Service SHALL display format as "Xm Xd Xh" (e.g., "5m 12d 6h")
7. WHEN time to block is between 1 and 30 days, THE Solo Mining Analytics Service SHALL display format as "Xd Xh" (e.g., "15d 8h")
8. WHEN time to block is less than 24 hours, THE Solo Mining Analytics Service SHALL display format as "Xh" (e.g., "11h")
9. THE Solo Mining Analytics Service SHALL calculate expected blocks per day as (hashrate / network_hashrate) * 144
10. THE Solo Mining Analytics Service SHALL calculate expected blocks per week by multiplying daily expectation by 7
11. THE Solo Mining Analytics Service SHALL calculate expected blocks per month by multiplying daily expectation by 30
12. THE Solo Mining Analytics Service SHALL calculate expected blocks per year by multiplying daily expectation by 365
13. WHEN displaying probability, THE Solo Mining Analytics Service SHALL format as both percentage and "1 in X" notation

### Requirement 5: Block Discovery Detection Service with ZMQ

**User Story:** As a solo miner, I want the app to automatically detect when I find a block using efficient notification methods so that I never miss this incredible achievement.

#### Acceptance Criteria

1. THE Block Discovery Service SHALL attempt to connect to Bitcoin Core ZMQ interface on tcp://127.0.0.1:28332 during initialization
2. WHEN ZMQ connection succeeds, THE Block Discovery Service SHALL subscribe to hashblock notifications for instant block detection
3. WHEN ZMQ connection fails, THE Block Discovery Service SHALL fall back to polling getbestblockhash RPC call every 5 minutes
4. WHEN a new block is detected via ZMQ or polling, THE Block Discovery Service SHALL retrieve full block data using getblock RPC call with verbosity 1
5. WHEN block data is retrieved, THE Block Discovery Service SHALL extract coinbase transaction output addresses from the block
6. THE Block Discovery Service SHALL compare coinbase output addresses against configured mining addresses
7. WHEN a mining address match is found, THE Block Discovery Service SHALL record the block discovery with hash, height, timestamp, and reward
8. WHEN a block is discovered, THE Block Discovery Service SHALL calculate luck factor as (actual_time / expected_time) * 100
9. WHEN a block is discovered, THE Block Discovery Service SHALL trigger celebration events through the notification system
10. THE Block Discovery Service SHALL persist all discovered blocks to the blocks_found database table

### Requirement 6: Bitcoin Node Management API

**User Story:** As a solo miner, I want API endpoints to manage Bitcoin nodes so that the frontend can interact with node features.

#### Acceptance Criteria

1. THE API Service SHALL provide GET /api/bitcoin-nodes endpoint to retrieve all configured Bitcoin nodes
2. THE API Service SHALL provide POST /api/bitcoin-nodes endpoint to add a new Bitcoin node with ip_address, port, username, and password
3. THE API Service SHALL provide DELETE /api/bitcoin-nodes/{node_id} endpoint to remove a Bitcoin node configuration
4. THE API Service SHALL provide GET /api/bitcoin-nodes/{node_id}/status endpoint to retrieve current node status and connection health
5. THE API Service SHALL provide POST /api/bitcoin-nodes/{node_id}/test-connection endpoint to validate RPC credentials
6. THE API Service SHALL provide GET /api/network-statistics endpoint to retrieve current Bitcoin network data
7. THE API Service SHALL provide GET /api/solo-mining-stats endpoint to retrieve probability calculations and mining statistics
8. THE API Service SHALL provide GET /api/blocks-found endpoint to retrieve block discovery history

### Requirement 7: Bitcoin Nodes Frontend Page

**User Story:** As a solo miner, I want a dedicated page to view and manage my Bitcoin nodes so that I can monitor their status and configure connections.

#### Acceptance Criteria

1. THE Bitcoin Nodes Page SHALL display a list of all configured Bitcoin nodes with name, IP address, port, and connection status
2. WHEN viewing a Bitcoin node, THE Bitcoin Nodes Page SHALL display node version, peer count, sync status, and block height
3. THE Bitcoin Nodes Page SHALL provide an "Add Node" button that opens a configuration dialog
4. WHEN adding a node, THE Configuration Dialog SHALL accept ip_address, port, username, and password inputs with validation
5. THE Configuration Dialog SHALL provide a "Test Connection" button that validates RPC credentials before saving
6. THE Bitcoin Nodes Page SHALL provide "Edit" and "Remove" buttons for each configured node
7. WHEN a node is offline, THE Bitcoin Nodes Page SHALL display a red status indicator and last seen timestamp
8. WHEN a node is syncing, THE Bitcoin Nodes Page SHALL display sync progress percentage

### Requirement 8: Dashboard Widgets for Network Statistics

**User Story:** As a solo miner, I want to see Bitcoin network statistics on my dashboard so that I have quick access to blockchain data.

#### Acceptance Criteria

1. THE Network Status Widget SHALL display current block height and block hash
2. THE Network Status Widget SHALL display current network difficulty formatted with appropriate units
3. THE Network Status Widget SHALL display estimated network hashrate in EH/s (exahashes per second)
4. THE Network Status Widget SHALL display mempool size showing transaction count and total bytes
5. THE Network Status Widget SHALL display time since last block in minutes
6. THE Network Status Widget SHALL update every 60 seconds via WebSocket or polling
7. WHEN no Bitcoin node is configured, THE Network Status Widget SHALL display a message prompting user to add a node
8. WHEN the Bitcoin node is offline, THE Network Status Widget SHALL display "Node Offline" status

### Requirement 9: Dashboard Widget for Solo Mining Statistics

**User Story:** As a solo miner, I want to see my mining probability and statistics on the dashboard so that I understand my chances of finding a block.

#### Acceptance Criteria

1. THE Solo Mining Stats Widget SHALL display total combined hashrate from all connected miners
2. THE Solo Mining Stats Widget SHALL display probability of finding next block as both percentage and "1 in X" format
3. THE Solo Mining Stats Widget SHALL display estimated time to find a block using intelligent formatting (e.g., "2y 3m 15d 8h" or "11h")
4. THE Solo Mining Stats Widget SHALL display expected blocks per day, week, month, and year
5. THE Solo Mining Stats Widget SHALL update every 60 seconds when hashrate or difficulty changes
6. WHEN no miners are connected, THE Solo Mining Stats Widget SHALL display "No miners connected" message
7. WHEN no Bitcoin node is configured, THE Solo Mining Stats Widget SHALL display "Bitcoin node required" message

### Requirement 10: Block Discovery Celebration and History

**User Story:** As a solo miner, I want to see a celebration when I find a block and view my block history so that I can track my mining success.

#### Acceptance Criteria

1. THE Blocks Found Widget SHALL display total count of blocks found prominently on the dashboard
2. WHEN a block is discovered, THE Blocks Found Widget SHALL trigger the existing Bitcoin logo rain animation easter egg
3. WHEN a block is discovered, THE Blocks Found Widget SHALL play a celebration sound effect
4. WHEN a block is discovered, THE Blocks Found Widget SHALL display a prominent notification overlay with block details including hash, height, and reward
5. THE Blocks Found Widget SHALL provide a "View History" button that opens the block history page
6. THE Block History Page SHALL display all discovered blocks in a table with block_hash, height, timestamp, reward, and luck_factor
7. THE Block History Page SHALL calculate and display total rewards earned from all discovered blocks
8. THE Block History Page SHALL provide a "Block Details" modal showing full information for each block
9. WHEN no blocks have been found, THE Blocks Found Widget SHALL display "0 Blocks Found - Keep Mining!" message

### Requirement 11: WebSocket Real-Time Updates

**User Story:** As a solo miner, I want real-time updates for Bitcoin network data so that I see changes immediately without refreshing.

#### Acceptance Criteria

1. THE WebSocket Manager SHALL create a "bitcoin_nodes" topic for node status updates
2. THE WebSocket Manager SHALL create a "network_statistics" topic for blockchain and mempool data updates
3. THE WebSocket Manager SHALL create a "solo_mining_stats" topic for probability calculation updates
4. THE WebSocket Manager SHALL create a "block_discovery" topic for immediate block found notifications
5. WHEN network statistics change, THE WebSocket Manager SHALL broadcast updates to all subscribed clients within 5 seconds
6. WHEN a block is discovered, THE WebSocket Manager SHALL broadcast celebration event to all clients immediately
7. WHEN a node status changes, THE WebSocket Manager SHALL broadcast status update to all clients within 10 seconds
8. THE WebSocket Manager SHALL limit broadcast frequency to once per 60 seconds per topic to prevent flooding

### Requirement 12: Setup Wizard Bitcoin Node Discovery Integration

**User Story:** As a solo miner, I want the setup wizard to discover and configure Bitcoin nodes during initial setup so that I can start monitoring immediately.

#### Acceptance Criteria

1. THE Network Discovery Screen SHALL scan for Bitcoin nodes on ports 8332, 18332, 8333, and 18333 alongside miner discovery
2. WHEN Bitcoin nodes are detected, THE Network Discovery Screen SHALL display them in a separate "Bitcoin Nodes Found" section
3. THE Network Discovery Screen SHALL provide a "Configure" button for each detected Bitcoin node
4. WHEN the Configure button is clicked, THE Node Configuration Dialog SHALL open requesting RPC username and password
5. THE Node Configuration Dialog SHALL provide a "Test Connection" button that validates RPC credentials before saving
6. WHEN RPC credentials are validated, THE Node Configuration Dialog SHALL check for ZMQ availability on port 28332
7. WHEN ZMQ is not detected, THE Node Configuration Dialog SHALL display setup instructions with steps to enable ZMQ in bitcoin.conf
8. THE ZMQ Setup Instructions SHALL provide options to "Skip - Use Polling" or "Retry Detection" after configuration
9. WHEN Retry Detection is clicked, THE Node Configuration Dialog SHALL re-check ZMQ availability
10. THE Network Discovery Screen SHALL allow users to skip Bitcoin node configuration and continue with miner-only setup
11. WHEN setup is complete with configured nodes, THE Application SHALL automatically start monitoring those nodes

### Requirement 13: Bitcoin Halving Countdown Display

**User Story:** As a solo miner, I want to see a countdown to the next Bitcoin halving in the app header so that I can track this important network event.

#### Acceptance Criteria

1. THE Application Header SHALL display a Bitcoin halving countdown that persists across all pages
2. THE Halving Countdown SHALL calculate blocks remaining until next halving as (210000 - (current_block_height % 210000))
3. THE Halving Countdown SHALL estimate time remaining by multiplying blocks remaining by 10 minutes
4. THE Halving Countdown SHALL use intelligent formatting matching Requirement 4 time display rules
5. WHEN time to halving exceeds 365 days, THE Halving Countdown SHALL display format as "Next Halving: Xy Xm Xd Xh"
6. WHEN time to halving is between 30 and 365 days, THE Halving Countdown SHALL display format as "Next Halving: Xm Xd Xh"
7. WHEN time to halving is between 1 and 30 days, THE Halving Countdown SHALL display format as "Next Halving: Xd Xh"
8. WHEN time to halving is less than 24 hours, THE Halving Countdown SHALL display format as "Next Halving: Xh Xm"
9. THE Halving Countdown SHALL update every 60 seconds when connected to a Bitcoin node
10. WHEN no Bitcoin node is configured, THE Halving Countdown SHALL display "Connect node to see halving countdown"
11. THE Halving Countdown SHALL include a tooltip showing estimated date and current block height

### Requirement 14: Navigation and Settings Integration

**User Story:** As a solo miner, I want Bitcoin node features integrated into the app navigation and settings so that I can easily access and configure them.

#### Acceptance Criteria

1. THE Main Navigation SHALL include a "Bitcoin Nodes" menu item between "Miners" and "Analytics"
2. THE Settings Page SHALL include a "Bitcoin Node Integration" section with enable/disable toggle
3. THE Settings Page SHALL provide configuration options for RPC timeout values between 10 and 120 seconds
4. THE Settings Page SHALL provide configuration options for block discovery polling interval between 3 and 60 minutes with default of 5 minutes
5. THE Settings Page SHALL provide configuration options for statistics refresh interval between 60 and 300 seconds
6. THE Settings Page SHALL provide configuration options for mining address input to enable block discovery detection
7. THE Settings Page SHALL display ZMQ connection status and provide "Show ZMQ Setup Instructions" button when ZMQ is not configured
8. THE About Page SHALL include information about Bitcoin node integration feature in the features list
9. WHEN Bitcoin node integration is disabled, THE Main Navigation SHALL hide the "Bitcoin Nodes" menu item
10. WHEN settings are changed, THE Settings Page SHALL apply changes immediately without requiring app restart

