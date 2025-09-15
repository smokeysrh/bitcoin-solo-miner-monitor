-- Time-Series Schema for Bitcoin Solo Miner Monitoring App
-- This schema replaces InfluxDB with SQLite-only storage for time-series data

-- ============================================================================
-- MINER METRICS TABLE
-- ============================================================================
-- Stores individual metric data points for miners (replaces InfluxDB)
-- Each row represents a single metric value at a specific timestamp

CREATE TABLE IF NOT EXISTS miner_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    miner_id TEXT NOT NULL,                    -- References miners.id
    timestamp TEXT NOT NULL,                   -- ISO format: 2024-01-01T12:00:00.000Z
    metric_type TEXT NOT NULL,                 -- Type of metric: 'hashrate', 'temperature', 'power', etc.
    value REAL NOT NULL,                       -- Numeric value of the metric
    unit TEXT,                                 -- Unit of measurement: 'TH/s', '°C', 'W', etc.
    created_at TEXT NOT NULL DEFAULT (datetime('now')),  -- Record creation timestamp
    
    -- Foreign key constraint
    FOREIGN KEY (miner_id) REFERENCES miners (id) ON DELETE CASCADE
);

-- ============================================================================
-- MINER STATUS TABLE
-- ============================================================================
-- Stores complete status snapshots for miners as JSON documents
-- Each row represents a complete status snapshot at a specific timestamp

CREATE TABLE IF NOT EXISTS miner_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    miner_id TEXT NOT NULL,                    -- References miners.id
    timestamp TEXT NOT NULL,                   -- ISO format: 2024-01-01T12:00:00.000Z
    status_data TEXT NOT NULL,                 -- JSON document with complete status
    created_at TEXT NOT NULL DEFAULT (datetime('now')),  -- Record creation timestamp
    
    -- Foreign key constraint
    FOREIGN KEY (miner_id) REFERENCES miners (id) ON DELETE CASCADE
);

-- ============================================================================
-- INDEXES FOR TIME-SERIES QUERIES
-- ============================================================================

-- Primary index for miner_metrics: miner + time (most common query pattern)
-- Optimizes queries like: SELECT * FROM miner_metrics WHERE miner_id = ? AND timestamp BETWEEN ? AND ?
CREATE INDEX IF NOT EXISTS idx_miner_metrics_miner_time 
ON miner_metrics (miner_id, timestamp DESC);

-- Index for metric type + time queries (for specific metric analysis)
-- Optimizes queries like: SELECT * FROM miner_metrics WHERE metric_type = 'hashrate' AND timestamp > ?
CREATE INDEX IF NOT EXISTS idx_miner_metrics_type_time 
ON miner_metrics (metric_type, timestamp DESC);

-- Composite index for miner + metric type + time (for filtered queries)
-- Optimizes queries like: SELECT * FROM miner_metrics WHERE miner_id = ? AND metric_type = ? AND timestamp BETWEEN ? AND ?
CREATE INDEX IF NOT EXISTS idx_miner_metrics_miner_type_time 
ON miner_metrics (miner_id, metric_type, timestamp DESC);

-- Index for timestamp only (for time-range queries across all miners)
-- Optimizes queries like: SELECT * FROM miner_metrics WHERE timestamp > ? ORDER BY timestamp DESC
CREATE INDEX IF NOT EXISTS idx_miner_metrics_timestamp 
ON miner_metrics (timestamp DESC);

-- Primary index for miner_status: miner + time
-- Optimizes queries like: SELECT * FROM miner_status WHERE miner_id = ? AND timestamp BETWEEN ? AND ?
CREATE INDEX IF NOT EXISTS idx_miner_status_miner_time 
ON miner_status (miner_id, timestamp DESC);

-- Index for timestamp only (for time-range queries across all miners)
-- Optimizes queries like: SELECT * FROM miner_status WHERE timestamp > ? ORDER BY timestamp DESC
CREATE INDEX IF NOT EXISTS idx_miner_status_timestamp 
ON miner_status (timestamp DESC);

-- ============================================================================
-- EXAMPLE QUERIES FOR TIME-SERIES DATA
-- ============================================================================

-- Get latest metrics for a specific miner
-- SELECT metric_type, value, unit, timestamp 
-- FROM miner_metrics 
-- WHERE miner_id = 'miner_001' 
-- ORDER BY timestamp DESC 
-- LIMIT 10;

-- Get hashrate data for a miner over the last 24 hours
-- SELECT timestamp, value 
-- FROM miner_metrics 
-- WHERE miner_id = 'miner_001' 
--   AND metric_type = 'hashrate' 
--   AND timestamp > datetime('now', '-1 day')
-- ORDER BY timestamp;

-- Get aggregated metrics (hourly averages) for a miner
-- SELECT 
--     strftime('%Y-%m-%d %H:00', timestamp) as hour,
--     metric_type,
--     AVG(value) as avg_value,
--     MIN(value) as min_value,
--     MAX(value) as max_value,
--     COUNT(*) as sample_count
-- FROM miner_metrics 
-- WHERE miner_id = 'miner_001' 
--   AND timestamp > datetime('now', '-1 day')
-- GROUP BY hour, metric_type
-- ORDER BY hour, metric_type;

-- Get latest status for a specific miner
-- SELECT status_data, timestamp 
-- FROM miner_status 
-- WHERE miner_id = 'miner_001' 
-- ORDER BY timestamp DESC 
-- LIMIT 1;

-- Get status history for a miner over the last week
-- SELECT timestamp, status_data 
-- FROM miner_status 
-- WHERE miner_id = 'miner_001' 
--   AND timestamp > datetime('now', '-7 days')
-- ORDER BY timestamp DESC;

-- ============================================================================
-- DATA RETENTION CONSIDERATIONS
-- ============================================================================

-- For production use, consider implementing data retention policies:
-- 
-- 1. Keep detailed metrics (1-minute intervals) for 7 days
-- 2. Keep hourly aggregates for 30 days  
-- 3. Keep daily aggregates for 1 year
-- 4. Archive or delete older data
--
-- Example cleanup query (to be run periodically):
-- DELETE FROM miner_metrics WHERE timestamp < datetime('now', '-7 days');
-- DELETE FROM miner_status WHERE timestamp < datetime('now', '-30 days');

-- ============================================================================
-- SAMPLE DATA STRUCTURE
-- ============================================================================

-- Example miner_metrics records:
-- INSERT INTO miner_metrics (miner_id, timestamp, metric_type, value, unit) VALUES
-- ('bitaxe_001', '2024-01-01T12:00:00.000Z', 'hashrate', 500.0, 'TH/s'),
-- ('bitaxe_001', '2024-01-01T12:00:00.000Z', 'temperature', 65.5, '°C'),
-- ('bitaxe_001', '2024-01-01T12:00:00.000Z', 'power', 3250.0, 'W'),
-- ('bitaxe_001', '2024-01-01T12:00:00.000Z', 'shares_accepted', 150, 'count'),
-- ('bitaxe_001', '2024-01-01T12:00:00.000Z', 'shares_rejected', 2, 'count');

-- Example miner_status record:
-- INSERT INTO miner_status (miner_id, timestamp, status_data) VALUES
-- ('bitaxe_001', '2024-01-01T12:00:00.000Z', '{
--   "status": "mining",
--   "uptime": 86400,
--   "pool_url": "stratum+tcp://solo.ckpool.org:3333",
--   "worker": "bc1qexample",
--   "difficulty": 1000000,
--   "network_hashrate": "500000000000000000",
--   "last_share": "2024-01-01T11:45:00.000Z",
--   "firmware_version": "2.1.0",
--   "chip_count": 1,
--   "frequency": 500
-- }');