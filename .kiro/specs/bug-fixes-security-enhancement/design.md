# Design Document

## Overview

This design document outlines the systematic approach to fix critical bugs, remove authentication complexity, simplify data storage, and improve the overall reliability of the Bitcoin Solo Miner Monitoring App. The design focuses on creating a simple, secure, local-only application suitable for home mining operations.

## Architecture

### High-Level Architecture Changes

```
Before:
┌─────────────────┐    ┌──────────────┐    ┌─────────────┐
│   Frontend      │    │   Backend    │    │  Databases  │
│   (Vue.js)      │◄──►│   (FastAPI)  │◄──►│  SQLite +   │
│                 │    │   + Auth     │    │  InfluxDB   │
└─────────────────┘    └──────────────┘    └─────────────┘

After:
┌─────────────────┐    ┌──────────────┐    ┌─────────────┐
│   Frontend      │    │   Backend    │    │  Database   │
│   (Vue.js)      │◄──►│   (FastAPI)  │◄──►│  SQLite     │
│   No Auth       │    │   No Auth    │    │   Only      │
└─────────────────┘    └──────────────┘    └─────────────┘
```

### Core Design Principles

1. **Simplicity First**: Remove unnecessary complexity (authentication, multiple databases)
2. **Local-Only**: All data stays on the user's machine
3. **Zero External Dependencies**: No InfluxDB, no cloud services
4. **Reliability**: Proper error handling and resource management
5. **Maintainability**: Clean imports, proper async patterns

## Components and Interfaces

### 1. Dependency Management

#### Requirements Files Creation
- **requirements.txt**: Define all Python dependencies with version pinning
- **package.json**: Define all Node.js dependencies for frontend
- **Version Strategy**: Pin major.minor versions, allow patch updates

```python
# requirements.txt structure
fastapi==0.104.*
uvicorn==0.24.*
aiosqlite==0.19.*
aiohttp==3.9.*
pydantic==2.5.*
# Remove: influxdb-client, PyJWT, bcrypt, python-multipart
```

#### Import Fixes
- Add missing `User` import in `api_service.py`
- Validate all imports across the codebase
- Remove authentication-related imports

### 2. Authentication System Removal

#### Backend Changes
```python
# Files to modify/remove:
- src/backend/models/user.py (REMOVE)
- src/backend/services/auth_service.py (REMOVE)
- src/backend/api/auth_routes.py (REMOVE)

# Files to update:
- src/backend/api/api_service.py (remove auth middleware)
- src/backend/services/data_storage.py (remove user tables)
```

#### API Endpoint Changes
```python
# Before: All endpoints require authentication
@app.get("/api/miners", dependencies=[Depends(auth_service.check_permission(UserRole.VIEWER))])

# After: Open access
@app.get("/api/miners")
```

#### Frontend Changes
```javascript
// Remove authentication components:
- Login/logout functionality
- Token management
- Auth guards in router
- User management UI

// Update WebSocket connection:
// Before: ws://localhost:8000/ws?token=xyz
// After: ws://localhost:8000/ws
```

### 3. Simplified Database Architecture

#### Single SQLite Database Design

```sql
-- Configuration Tables
CREATE TABLE miners (
    id TEXT PRIMARY KEY,
    config TEXT NOT NULL,  -- JSON configuration
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE settings (
    id TEXT PRIMARY KEY,
    value TEXT NOT NULL,  -- JSON settings
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Time-Series Metrics Tables (replacing InfluxDB)
CREATE TABLE miner_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    miner_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,  -- ISO format
    metric_type TEXT NOT NULL,  -- 'hashrate', 'temperature', etc.
    value REAL NOT NULL,
    unit TEXT,
    FOREIGN KEY (miner_id) REFERENCES miners (id),
    INDEX idx_miner_metrics_miner_time (miner_id, timestamp),
    INDEX idx_miner_metrics_type_time (metric_type, timestamp)
);

CREATE TABLE miner_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    miner_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    status_data TEXT NOT NULL,  -- JSON status snapshot
    FOREIGN KEY (miner_id) REFERENCES miners (id),
    INDEX idx_miner_status_miner_time (miner_id, timestamp)
);
```

#### Data Storage Service Redesign

```python
class DataStorage:
    def __init__(self):
        self.sqlite_path = DB_CONFIG["sqlite"]["path"]
        self.sqlite_conn = None
        # Remove: InfluxDB client, query optimizer for InfluxDB
    
    async def save_metrics(self, miner_id: str, metrics: Dict[str, Any]) -> bool:
        """Save metrics to SQLite instead of InfluxDB"""
        timestamp = datetime.now().isoformat()
        
        # Insert individual metrics
        for metric_name, value in metrics.items():
            await self.sqlite_conn.execute(
                "INSERT INTO miner_metrics (miner_id, timestamp, metric_type, value) VALUES (?, ?, ?, ?)",
                (miner_id, timestamp, metric_name, value)
            )
    
    async def get_metrics(self, miner_id: str, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Query metrics from SQLite with time-series aggregation"""
        query = """
        SELECT metric_type, timestamp, value 
        FROM miner_metrics 
        WHERE miner_id = ? AND timestamp BETWEEN ? AND ?
        ORDER BY timestamp
        """
        # Implementation with SQLite time-series queries
```

### 4. Async Database Improvements

#### Replace Synchronous SQLite
```python
# Before (blocking):
import sqlite3
self.sqlite_conn = sqlite3.connect(self.sqlite_path)

# After (async):
import aiosqlite
self.sqlite_conn = await aiosqlite.connect(self.sqlite_path)
```

#### Connection Management
```python
class DatabaseManager:
    async def __aenter__(self):
        self.conn = await aiosqlite.connect(self.db_path)
        return self.conn
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            await self.conn.close()
```

### 5. HTTP Session Management

#### Session Lifecycle Management
```python
class MinerHTTPClient:
    def __init__(self, ip_address: str, port: int):
        self.ip_address = ip_address
        self.port = port
        self.session = None
        self._session_lock = asyncio.Lock()
    
    async def __aenter__(self):
        async with self._session_lock:
            if not self.session:
                self.session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=CONNECTION_TIMEOUT)
                )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            self.session = None
```

### 6. Path and Configuration Management

#### Robust Path Handling
```python
from pathlib import Path

class AppPaths:
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.data_dir = self.base_dir / "data"
        self.logs_dir = self.base_dir / "logs"
        self.config_file = self.data_dir / "config.db"
    
    def ensure_directories(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
```

#### Configuration Validation
```python
class ConfigValidator:
    @staticmethod
    def validate_required_settings():
        required_vars = ["HOST", "PORT"]
        missing = [var for var in required_vars if not os.getenv(var)]
        if missing:
            raise ConfigurationError(f"Missing required environment variables: {missing}")
```

## Data Models

### Simplified Miner Data Model

```python
@dataclass
class MinerConfig:
    id: str
    name: str
    type: str  # 'bitaxe', 'avalon_nano', 'magic_miner'
    ip_address: str
    port: int
    created_at: datetime
    updated_at: datetime

@dataclass
class MinerMetrics:
    miner_id: str
    timestamp: datetime
    hashrate: float
    temperature: float
    power: float
    shares_accepted: int
    shares_rejected: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "hashrate": self.hashrate,
            "temperature": self.temperature,
            "power": self.power,
            "shares_accepted": self.shares_accepted,
            "shares_rejected": self.shares_rejected
        }
```

### Time-Series Data Handling

```python
class TimeSeriesQuery:
    @staticmethod
    def build_aggregation_query(metric_type: str, interval: str) -> str:
        """Build SQLite query for time-series aggregation"""
        if interval == "1m":
            time_group = "strftime('%Y-%m-%d %H:%M', timestamp)"
        elif interval == "1h":
            time_group = "strftime('%Y-%m-%d %H:00', timestamp)"
        elif interval == "1d":
            time_group = "strftime('%Y-%m-%d', timestamp)"
        
        return f"""
        SELECT 
            {time_group} as time_bucket,
            AVG(value) as avg_value,
            MIN(value) as min_value,
            MAX(value) as max_value,
            COUNT(*) as sample_count
        FROM miner_metrics 
        WHERE metric_type = ? AND miner_id = ? AND timestamp BETWEEN ? AND ?
        GROUP BY {time_group}
        ORDER BY time_bucket
        """
```

## Error Handling

### Structured Error Handling

```python
class MinerError(Exception):
    """Base exception for miner-related errors"""
    pass

class MinerConnectionError(MinerError):
    """Raised when miner connection fails"""
    pass

class MinerDataError(MinerError):
    """Raised when miner data is invalid"""
    pass

# Usage:
try:
    await miner.connect()
except MinerConnectionError as e:
    logger.error(f"Failed to connect to miner {miner.ip_address}: {e}")
    # Specific handling for connection errors
except MinerDataError as e:
    logger.error(f"Invalid data from miner {miner.ip_address}: {e}")
    # Specific handling for data errors
```

### Retry Logic with Exponential Backoff

```python
async def retry_with_backoff(func, max_retries=3, base_delay=1):
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt)
            logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay}s: {e}")
            await asyncio.sleep(delay)
```

## Testing Strategy

### Unit Tests for Critical Fixes

```python
# Test import fixes
def test_api_service_imports():
    """Ensure all required imports are present"""
    from src.backend.api.api_service import APIService
    # Should not raise ImportError

# Test database migration
async def test_database_migration():
    """Test migration from dual-database to SQLite-only"""
    # Test data preservation during migration
    
# Test session management
async def test_http_session_cleanup():
    """Ensure HTTP sessions are properly cleaned up"""
    # Test session lifecycle
```

### Integration Tests

```python
async def test_end_to_end_without_auth():
    """Test complete flow without authentication"""
    # Test API access without tokens
    # Test WebSocket connection without auth
    # Test miner management operations
```

### Performance Tests

```python
async def test_sqlite_time_series_performance():
    """Test SQLite performance with time-series data"""
    # Insert large amounts of metrics data
    # Test query performance
    # Compare with previous InfluxDB performance
```

## Migration Strategy

### Database Migration Plan

1. **Backup Existing Data**
   ```python
   async def backup_existing_data():
       # Export InfluxDB data to JSON
       # Backup SQLite configuration data
   ```

2. **Create New Schema**
   ```python
   async def create_new_schema():
       # Create new time-series tables in SQLite
       # Preserve existing configuration tables
   ```

3. **Migrate Data**
   ```python
   async def migrate_influx_to_sqlite():
       # Convert InfluxDB time-series data to SQLite format
       # Preserve all historical metrics
   ```

4. **Cleanup**
   ```python
   async def cleanup_old_system():
       # Remove InfluxDB configuration
       # Remove authentication tables
       # Update configuration files
   ```

### Frontend Migration

1. **Remove Authentication UI**
   - Remove login/logout components
   - Remove user management pages
   - Remove auth guards from router

2. **Update API Calls**
   - Remove token headers from HTTP requests
   - Update WebSocket connection (no auth token)
   - Remove auth error handling

3. **Simplify Navigation**
   - Remove user profile menu
   - Remove admin-only sections
   - Streamline main navigation

## Deployment Considerations

### Simplified Installation

```json
// Updated installer config
{
  "dependencies": {
    "python": ">=3.11.0",
    "nodejs": ">=18.0.0"
    // Remove: "influxdb": ">=2.7.0"
  },
  "bundled_dependencies": true
}
```

### Health Checks

```python
async def health_check():
    """Simplified health check without external dependencies"""
    checks = {
        "database": await check_sqlite_connection(),
        "disk_space": await check_disk_space(),
        "memory": await check_memory_usage()
        # Remove: InfluxDB check, auth service check
    }
    return checks
```

### Configuration Management

```python
# Simplified configuration
class AppConfig:
    def __init__(self):
        self.host = os.getenv("HOST", "0.0.0.0")
        self.port = int(os.getenv("PORT", "8000"))
        self.database_path = self.get_database_path()
        # Remove: JWT secrets, InfluxDB config, auth settings
    
    def validate(self):
        """Validate configuration is complete"""
        if not self.database_path.parent.exists():
            raise ConfigError("Database directory does not exist")
```

This design provides a comprehensive approach to fixing all identified issues while significantly simplifying the application for home users. The removal of authentication and InfluxDB dependency will make installation and maintenance much easier while maintaining all core functionality.