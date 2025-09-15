# Database Migrations

This directory contains database migration scripts for the Bitcoin Solo Miner Monitoring App.

## Migration Files

### `create_timeseries_schema.py`
Creates the new SQLite time-series schema to replace InfluxDB dependency.

**What it does:**
- Creates `miner_metrics` table for storing individual metric data points
- Creates `miner_status` table for storing complete status snapshots as JSON
- Creates optimized indexes for time-series queries
- Includes verification and sample data creation

**Usage:**
```bash
python migrations/create_timeseries_schema.py
```

### `timeseries_schema.sql`
SQL schema definition file documenting the complete time-series schema structure.

**Contains:**
- Table definitions with detailed comments
- Index definitions optimized for time-series queries
- Example queries for common use cases
- Data retention considerations
- Sample data structure examples

### `remove_user_tables.py`
Removes user authentication tables as part of the authentication system removal.

**What it does:**
- Backs up existing user data
- Removes user tables and indexes
- Verifies migration success

## Schema Overview

### Time-Series Tables

#### `miner_metrics`
Stores individual metric data points (replaces InfluxDB):
- `id`: Auto-increment primary key
- `miner_id`: References miners.id
- `timestamp`: ISO format timestamp
- `metric_type`: Type of metric (hashrate, temperature, etc.)
- `value`: Numeric value
- `unit`: Unit of measurement
- `created_at`: Record creation timestamp

#### `miner_status`
Stores complete status snapshots as JSON:
- `id`: Auto-increment primary key
- `miner_id`: References miners.id
- `timestamp`: ISO format timestamp
- `status_data`: JSON document with complete status
- `created_at`: Record creation timestamp

### Indexes

The schema includes optimized indexes for common time-series query patterns:

1. **Primary queries** (miner + time range)
2. **Metric-specific queries** (metric type + time)
3. **Filtered queries** (miner + metric type + time)
4. **Cross-miner queries** (time range across all miners)

## Migration Process

1. **Run the time-series schema creation:**
   ```bash
   python migrations/create_timeseries_schema.py
   ```

2. **Verify the schema was created correctly:**
   - Check that `miner_metrics` and `miner_status` tables exist
   - Verify all indexes were created
   - Confirm foreign key constraints are in place

3. **Test with sample data:**
   - The migration script creates sample data for testing
   - Verify queries work as expected

## Query Examples

### Get latest metrics for a miner:
```sql
SELECT metric_type, value, unit, timestamp 
FROM miner_metrics 
WHERE miner_id = 'miner_001' 
ORDER BY timestamp DESC 
LIMIT 10;
```

### Get aggregated hourly data:
```sql
SELECT 
    strftime('%Y-%m-%d %H:00', timestamp) as hour,
    metric_type,
    AVG(value) as avg_value,
    MIN(value) as min_value,
    MAX(value) as max_value
FROM miner_metrics 
WHERE miner_id = 'miner_001' 
  AND timestamp > datetime('now', '-1 day')
GROUP BY hour, metric_type
ORDER BY hour, metric_type;
```

### Get latest status:
```sql
SELECT status_data, timestamp 
FROM miner_status 
WHERE miner_id = 'miner_001' 
ORDER BY timestamp DESC 
LIMIT 1;
```

## Data Retention

Consider implementing data retention policies:
- Keep detailed metrics (1-minute intervals) for 7 days
- Keep hourly aggregates for 30 days
- Keep daily aggregates for 1 year
- Archive or delete older data

Example cleanup:
```sql
DELETE FROM miner_metrics WHERE timestamp < datetime('now', '-7 days');
DELETE FROM miner_status WHERE timestamp < datetime('now', '-30 days');
```

## Performance Considerations

1. **Indexes**: All critical query patterns are covered by indexes
2. **Batch inserts**: Use batch operations for better performance
3. **Connection pooling**: Use connection pooling for concurrent access
4. **Data cleanup**: Regular cleanup prevents database bloat
5. **Aggregation**: Pre-compute aggregates for frequently accessed data

## Troubleshooting

### Common Issues:

1. **Foreign key constraint errors**: Ensure miners exist before inserting metrics
2. **Timestamp format errors**: Use ISO format (YYYY-MM-DDTHH:MM:SS.sssZ)
3. **JSON parsing errors**: Ensure status_data is valid JSON
4. **Index performance**: Monitor query performance and adjust indexes if needed

### Verification Commands:

```sql
-- Check table structure
PRAGMA table_info(miner_metrics);
PRAGMA table_info(miner_status);

-- Check indexes
SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_miner_%';

-- Check foreign keys
PRAGMA foreign_key_list(miner_metrics);
PRAGMA foreign_key_list(miner_status);
```