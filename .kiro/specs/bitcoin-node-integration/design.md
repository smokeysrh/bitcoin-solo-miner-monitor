# Bitcoin Node Integration Design

## Overview

The Bitcoin Node Integration feature will extend the existing Bitcoin Solo Miner Monitor architecture to include Bitcoin Core node discovery, monitoring, and analytics. This design builds upon the existing detection infrastructure (`BitcoinNode` model and `MinerFactory` integration) while adding new components for Bitcoin RPC communication, network statistics calculation, solo mining analytics, and block discovery.

The integration will be implemented as a new device type alongside existing miners, with dedicated UI components and backend services. The design prioritizes security, performance, and maintainability while providing solo miners with comprehensive network visibility.

## Existing Foundation

**Code Audit (October 20, 2025) identified these existing components:**

### Already Implemented
- ✅ `BitcoinNode` model class (`src/backend/models/bitcoin_node.py`)
  - Multi-port detection (8332, 18332, 8333, 18333)
  - RPC, P2P, and web interface detection
  - Basic connection/disconnection methods
  - Implements `MinerInterface` for consistency
  
- ✅ `MinerFactory` integration (`src/backend/models/miner_factory.py`)
  - `create_miner()` supports "bitcoin_node" type
  - `detect_miner_type()` includes Bitcoin node detection
  - Proper cleanup and error handling

### Not Implemented (This Design Focuses On)
- ❌ Actual RPC client for blockchain data retrieval
- ❌ Data persistence layer for node configurations
- ❌ Network statistics collection service
- ❌ Solo mining analytics and probability calculations
- ❌ Block discovery detection with ZMQ support
- ❌ API endpoints for frontend communication
- ❌ Frontend UI components (pages, widgets, dialogs)
- ❌ WebSocket real-time updates
- ❌ Setup wizard integration
- ❌ Settings page integration

**This design builds on the existing detection foundation to deliver the missing 95% of functionality.**

## Architecture

### High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    Frontend (Vue.js)                             │
├──────────────┬──────────────┬──────────────┬───────────────────┤
│ App Header   │ Miners Page  │ Bitcoin      │ Dashboard Widgets │
│              │              │ Nodes Page   │                   │
│ - Halving    │ - Bitaxe     │ - Node List  │ - Network Status  │
│   Countdown  │ - Avalon     │ - Node       │ - Solo Mining     │
│              │ - Magic      │   Details    │   Stats           │
│              │   Miner      │ - RPC Config │ - Blocks Found    │
│              │              │ - ZMQ Setup  │   (Logo Rain)     │
└──────────────┴──────────────┴──────────────┴───────────────────┘
                                  │
                           ┌──────────────┐
                           │  API Layer   │
                           │  (FastAPI)   │
                           └──────────────┘
                                  │
┌──────────────────────────────────────────────────────────────────┐
│                    Backend Services Layer                        │
├──────────────┬──────────────┬──────────────┬───────────────────┤
│ Miner        │ Bitcoin Node │ Network      │ Block Discovery   │
│ Manager      │ Manager      │ Statistics   │ Service           │
│              │              │ Service      │                   │
│ - Discovery  │ - RPC Client │ - Blockchain │ - ZMQ Listener    │
│ - Monitoring │ - Node       │   Info       │ - Polling         │
│ - Control    │   Monitor    │ - Mempool    │   Fallback        │
│              │ - Health     │   Info       │ - Coinbase Check  │
│              │   Check      │ - Hashrate   │ - Celebration     │
│              │              │   Calc       │   Trigger         │
│              │              │              │                   │
│              │              │ Solo Mining  │ Time Formatting   │
│              │              │ Analytics    │ Service           │
│              │              │              │                   │
│              │              │ - Probability│ - Intelligent     │
│              │              │   Calc       │   Time Display    │
│              │              │ - Time to    │ - Halving         │
│              │              │   Block      │   Countdown       │
│              │              │ - Expected   │                   │
│              │              │   Blocks     │                   │
└──────────────┴──────────────┴──────────────┴───────────────────┘
                                  │
┌──────────────────────────────────────────────────────────────────┐
│                        Data Layer                                │
├──────────────┬──────────────┬──────────────┬───────────────────┤
│ SQLite DB    │ In-Memory    │ External     │ ZMQ Interface     │
│              │ Cache        │ APIs         │                   │
│ - Node       │ - Live Data  │ - Bitcoin    │ - Block           │
│   Configs    │ - Statistics │   Core RPC   │   Notifications   │
│ - Block      │ - Calcs      │              │ - tcp://          │
│   Records    │              │              │   127.0.0.1:28332 │
│ - Settings   │              │              │                   │
└──────────────┴──────────────┴──────────────┴───────────────────┘
```

### Component Integration

The Bitcoin Node Integration will extend existing components and add new ones:

**Extending Existing Components:**
1. **BitcoinNode Model** (EXISTS): Enhance with actual RPC communication methods
2. **MinerFactory** (EXISTS): Already includes Bitcoin node detection
3. **Data Storage**: Extended schema for node configurations and block records
4. **WebSocket Manager**: New topics for node updates and network statistics
5. **API Service**: New endpoints for node management and analytics
6. **First-Run Setup**: Extended wizard with Bitcoin node discovery and RPC configuration
7. **Settings Management**: New Bitcoin node settings section with ZMQ configuration
8. **Navigation System**: New "Bitcoin Nodes" page and mobile navigation updates
9. **Notification System**: Extended alerts for Bitcoin network events and block discovery

**New Components:**
1. **Bitcoin RPC Client**: JSON-RPC 1.0 client for Bitcoin Core communication
2. **Network Statistics Service**: Collects blockchain and mempool data every 60 seconds
3. **Solo Mining Analytics Service**: Calculates probabilities and time estimates
4. **Block Discovery Service**: ZMQ-first block detection with polling fallback
5. **Time Formatting Service**: Intelligent time display (years/months/days/hours)
6. **Halving Countdown Component**: Persistent header display across all pages
7. **Bitcoin Nodes Page**: Frontend page for node management
8. **Dashboard Widgets**: Network Status, Solo Mining Stats, Blocks Found
9. **ZMQ Setup Dialog**: Instructions and retry logic for ZMQ configuration

## Components and Interfaces

### 1. Bitcoin Node Interface

```python
class BitcoinNodeInterface:
    """Interface for Bitcoin node communication and monitoring."""
    
    async def connect(self) -> bool
    async def disconnect(self) -> None
    async def get_blockchain_info(self) -> Dict[str, Any]
    async def get_network_info(self) -> Dict[str, Any]
    async def get_mempool_info(self) -> Dict[str, Any]
    async def get_block_info(self, block_hash: str) -> Dict[str, Any]
    async def get_best_block_hash(self) -> str
    async def is_block_ours(self, block_hash: str, mining_addresses: List[str]) -> bool
    async def health_check(self) -> Dict[str, Any]
```

### 2. Bitcoin RPC Client

```python
class BitcoinRPCClient:
    """Bitcoin Core RPC client with authentication and error handling."""
    
    def __init__(self, host: str, port: int, username: str = None, password: str = None)
    async def call(self, method: str, params: List = None) -> Dict[str, Any]
    async def batch_call(self, calls: List[Dict]) -> List[Dict[str, Any]]
    async def test_connection(self) -> bool
    
    # Safe read-only methods only
    ALLOWED_METHODS = [
        'getblockchaininfo', 'getnetworkinfo', 'getmempoolinfo',
        'getbestblockhash', 'getblock', 'getblockheader', 'getpeerinfo'
    ]
```

### 3. Bitcoin Node Manager

```python
class BitcoinNodeManager:
    """Service for managing Bitcoin node connections and monitoring."""
    
    async def add_node(self, ip_address: str, port: int, credentials: Dict) -> str
    async def remove_node(self, node_id: str) -> bool
    async def get_node(self, node_id: str) -> Optional[Dict[str, Any]]
    async def get_all_nodes(self) -> List[Dict[str, Any]]
    async def update_node_credentials(self, node_id: str, credentials: Dict) -> bool
    async def start_monitoring(self, node_id: str) -> bool
    async def stop_monitoring(self, node_id: str) -> bool
    async def get_network_statistics(self) -> Dict[str, Any]
```

### 4. Network Statistics Service

```python
class NetworkStatisticsService:
    """Service for collecting Bitcoin network statistics."""
    
    def __init__(self, rpc_client: BitcoinRPCClient, cache_ttl: int = 60)
    async def collect_statistics(self) -> Dict[str, Any]
    async def get_blockchain_info(self) -> Dict[str, Any]
    async def get_mempool_info(self) -> Dict[str, Any]
    async def calculate_network_hashrate(self, difficulty: float) -> float
    async def calculate_time_since_last_block(self, latest_block_time: int) -> int
    async def get_cached_statistics(self) -> Optional[Dict[str, Any]]
```

### 5. Solo Mining Analytics Service

```python
class SoloMiningAnalyticsService:
    """Service for calculating solo mining statistics and probabilities."""
    
    def __init__(self, time_formatter: TimeFormattingService)
    async def aggregate_miner_hashrate(self, miners: List[Dict]) -> float
    async def calculate_probability(self, hashrate: float, network_hashrate: float) -> Dict[str, Any]
    async def calculate_time_to_block(self, hashrate: float, difficulty: float) -> int  # Returns seconds
    async def calculate_expected_blocks(self, hashrate: float, network_hashrate: float) -> Dict[str, Any]
    async def calculate_luck_factor(self, actual_time: float, expected_time: float) -> float
```

### 6. Block Discovery Service with ZMQ

```python
class BlockDiscoveryService:
    """Service for detecting and celebrating block discoveries using ZMQ with polling fallback."""
    
    def __init__(self, rpc_client: BitcoinRPCClient, zmq_endpoint: str = "tcp://127.0.0.1:28332")
    async def initialize(self) -> bool  # Returns True if ZMQ connected
    async def start_monitoring(self, mining_addresses: List[str]) -> None
    async def stop_monitoring(self) -> None
    async def _zmq_listener(self) -> None  # ZMQ block notification handler
    async def _polling_fallback(self) -> None  # 5-minute polling fallback
    async def _check_block_ownership(self, block_hash: str, mining_addresses: List[str]) -> bool
    async def _extract_coinbase_addresses(self, block_data: Dict) -> List[str]
    async def record_block_discovery(self, block_info: Dict[str, Any]) -> None
    async def trigger_celebration(self, block_info: Dict[str, Any]) -> None
    async def get_blocks_found(self) -> List[Dict[str, Any]]
    def is_zmq_connected(self) -> bool
```

### 7. Time Formatting Service

```python
class TimeFormattingService:
    """Service for intelligent time formatting based on duration."""
    
    @staticmethod
    def format_duration(seconds: int) -> str:
        """
        Format duration intelligently:
        - Over 365 days: "2y 3m 15d 8h"
        - 30-365 days: "5m 12d 6h"
        - 1-30 days: "15d 8h"
        - Under 24 hours: "11h"
        """
        pass
    
    @staticmethod
    def format_halving_countdown(seconds: int) -> str:
        """
        Format halving countdown with minutes for final hours:
        - Over 365 days: "3y 8m 12d 6h"
        - Under 24 hours: "18h 30m"
        """
        pass
    
    @staticmethod
    def calculate_halving_blocks_remaining(current_height: int) -> int:
        """Calculate blocks until next halving."""
        return 210000 - (current_height % 210000)
    
    @staticmethod
    def estimate_halving_time(blocks_remaining: int) -> int:
        """Estimate seconds until halving (blocks * 600)."""
        return blocks_remaining * 600
```

## Data Models

### Bitcoin Node Configuration

```python
class BitcoinNodeConfig:
    node_id: str
    name: str
    ip_address: str
    port: int
    username: Optional[str]
    password_hash: Optional[str]  # AES-256 encrypted
    zmq_enabled: bool
    zmq_endpoint: str  # Default: tcp://127.0.0.1:28332
    added_at: datetime
    last_seen: Optional[datetime]
    status: str  # online, offline, syncing, error
    version: Optional[str]
    network: str  # mainnet, testnet, regtest
```

### Network Statistics

```python
class NetworkStatistics:
    timestamp: datetime
    block_height: int
    block_hash: str
    difficulty: float
    network_hashrate: float
    mempool_size: int
    mempool_bytes: int
    fee_rates: Dict[str, float]  # low, medium, high
    time_since_last_block: int
    next_difficulty_adjustment: Dict[str, Any]
```

### Block Discovery Record

```python
class BlockDiscoveryRecord:
    block_hash: str
    block_height: int
    timestamp: datetime
    reward: float
    difficulty: float
    time_to_find: int  # seconds
    expected_time: int  # seconds
    luck_factor: float
    mining_address: str
    node_id: str
```

### Solo Mining Statistics

```python
class SoloMiningStats:
    total_hashrate: float
    probability_next_block: float
    estimated_time_to_block: Dict[str, Any]  # seconds, formatted
    expected_blocks_per_day: float
    expected_blocks_per_week: float
    expected_blocks_per_month: float
    expected_blocks_per_year: float
    current_luck: Optional[float]
```

## Error Handling

### Bitcoin RPC Error Handling

```python
class BitcoinRPCError(Exception):
    """Bitcoin RPC specific errors."""
    pass

class BitcoinNodeConnectionError(BitcoinRPCError):
    """Node connection failures."""
    pass

class BitcoinNodeAuthError(BitcoinRPCError):
    """Authentication failures."""
    pass

class BitcoinNodeSyncError(BitcoinRPCError):
    """Node synchronization issues."""
    pass
```

### Error Recovery Strategies

1. **Connection Failures**: Retry with exponential backoff, mark node offline
2. **Authentication Errors**: Disable node, notify user to update credentials
3. **RPC Timeouts**: Implement request timeouts, fallback to cached data
4. **Node Sync Issues**: Display sync status, continue with available data
5. **Invalid Responses**: Log errors, use default values, alert user

## Testing Strategy

### Unit Tests

1. **Bitcoin RPC Client Tests**
   - Mock Bitcoin Core responses
   - Test authentication handling
   - Test error scenarios
   - Test connection management

2. **Analytics Service Tests**
   - Test probability calculations
   - Test time estimation algorithms
   - Test difficulty adjustment calculations
   - Test edge cases (zero hashrate, extreme difficulty)

3. **Block Discovery Tests**
   - Mock block detection scenarios
   - Test ownership verification
   - Test celebration triggers
   - Test record keeping

### Integration Tests

1. **Node Discovery Tests**
   - Test Bitcoin node detection in network scan
   - Test RPC connection establishment
   - Test credential validation

2. **End-to-End Monitoring Tests**
   - Test complete node monitoring workflow
   - Test data flow from RPC to frontend
   - Test WebSocket updates

3. **Analytics Integration Tests**
   - Test combined miner + node data processing
   - Test real-time calculation updates
   - Test block discovery workflow

### Security Tests

1. **RPC Security Tests**
   - Test credential encryption/decryption
   - Test read-only command enforcement
   - Test network isolation (local only)

2. **Input Validation Tests**
   - Test RPC response validation
   - Test malformed data handling
   - Test injection attack prevention

## Performance Considerations

### Optimization Strategies

1. **RPC Call Batching**: Combine multiple RPC calls into single requests
2. **Caching**: Cache network statistics for 30-second intervals
3. **Async Processing**: Non-blocking RPC calls and calculations
4. **Connection Pooling**: Reuse RPC connections efficiently
5. **Selective Updates**: Only update changed data via WebSocket

### Resource Management

1. **Memory Usage**: Limit cached network data, rotate old statistics
2. **Network Bandwidth**: Minimize RPC call frequency, batch requests
3. **CPU Usage**: Optimize probability calculations, use efficient algorithms
4. **Database I/O**: Batch database writes, use prepared statements

## Security Implementation

### Authentication and Authorization

1. **RPC Credentials**: Store encrypted in database, decrypt only when needed
2. **Local Network Only**: Restrict connections to private IP ranges
3. **Read-Only Access**: Whitelist safe RPC methods, block wallet commands
4. **Input Validation**: Sanitize all RPC responses and user inputs

### Data Protection

1. **Credential Encryption**: Use AES-256 encryption for stored passwords
2. **Secure Communication**: Use HTTPS for RPC when available
3. **Error Information**: Avoid exposing sensitive data in error messages
4. **Audit Logging**: Log all RPC calls and authentication attempts

## Deployment Considerations

### Configuration Management

1. **Default Settings**: Sensible defaults for RPC ports and timeouts
2. **Environment Variables**: Support for RPC credentials via environment
3. **Configuration Validation**: Validate node settings before saving
4. **Migration Support**: Handle upgrades from non-node versions

### Monitoring and Alerting

1. **Health Checks**: Regular node connectivity and sync status checks
2. **Performance Metrics**: Track RPC response times and success rates
3. **Error Alerting**: Notify users of node connectivity issues
4. **Resource Monitoring**: Track memory and CPU usage of node monitoring

This design provides a comprehensive foundation for integrating Bitcoin node monitoring into the existing solo mining application while maintaining security, performance, and usability standards.