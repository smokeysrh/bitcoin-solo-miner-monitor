import sqlite3
import json
from datetime import datetime

# Connect to database
conn = sqlite3.connect('data/config.db')
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
print("=" * 80)
print("DATABASE TABLES:")
print("=" * 80)
for table in tables:
    print(f"  - {table}")

print("\n" + "=" * 80)
print("MINERS TABLE:")
print("=" * 80)
cursor.execute("SELECT id, created_at, updated_at FROM miners")
miners = cursor.fetchall()
print(f"Total miners: {len(miners)}")
for miner in miners:
    print(f"  - ID: {miner[0]}")
    print(f"    Created: {miner[1]}")
    print(f"    Updated: {miner[2]}")

print("\n" + "=" * 80)
print("MINER_METRICS TABLE:")
print("=" * 80)
cursor.execute("SELECT COUNT(*) FROM miner_metrics")
total_metrics = cursor.fetchone()[0]
print(f"Total metric records: {total_metrics}")

cursor.execute("SELECT miner_id, COUNT(*) as count FROM miner_metrics GROUP BY miner_id")
metrics_by_miner = cursor.fetchall()
print("\nMetrics per miner:")
for miner_id, count in metrics_by_miner:
    print(f"  - {miner_id}: {count} records")

cursor.execute("SELECT metric_type, COUNT(*) as count FROM miner_metrics GROUP BY metric_type ORDER BY count DESC")
metrics_by_type = cursor.fetchall()
print("\nMetrics by type (top 10):")
for metric_type, count in metrics_by_type[:10]:
    print(f"  - {metric_type}: {count} records")

cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM miner_metrics")
time_range = cursor.fetchone()
print(f"\nTime range: {time_range[0]} to {time_range[1]}")

print("\n" + "=" * 80)
print("MINER_STATUS TABLE:")
print("=" * 80)
cursor.execute("SELECT COUNT(*) FROM miner_status")
total_status = cursor.fetchone()[0]
print(f"Total status records: {total_status}")

cursor.execute("SELECT miner_id, COUNT(*) as count FROM miner_status GROUP BY miner_id")
status_by_miner = cursor.fetchall()
print("\nStatus records per miner:")
for miner_id, count in status_by_miner:
    print(f"  - {miner_id}: {count} records")

cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM miner_status")
time_range = cursor.fetchone()
print(f"\nTime range: {time_range[0]} to {time_range[1]}")

# Get a sample of the latest metrics
print("\n" + "=" * 80)
print("SAMPLE OF LATEST METRICS (last 5 records):")
print("=" * 80)
cursor.execute("""
    SELECT miner_id, timestamp, metric_type, value, unit 
    FROM miner_metrics 
    ORDER BY timestamp DESC 
    LIMIT 5
""")
latest_metrics = cursor.fetchall()
for record in latest_metrics:
    print(f"  - {record[0]} | {record[1]} | {record[2]}: {record[3]} {record[4] or ''}")

# Get a sample of the latest status
print("\n" + "=" * 80)
print("SAMPLE OF LATEST STATUS:")
print("=" * 80)
cursor.execute("""
    SELECT miner_id, timestamp, status_data 
    FROM miner_status 
    ORDER BY timestamp DESC 
    LIMIT 1
""")
latest_status = cursor.fetchone()
if latest_status:
    print(f"Miner: {latest_status[0]}")
    print(f"Timestamp: {latest_status[1]}")
    status_data = json.loads(latest_status[2])
    print("Status data keys:", list(status_data.keys()))

# Check for network_health table
print("\n" + "=" * 80)
print("NETWORK_HEALTH TABLE:")
print("=" * 80)
if 'network_health' in tables:
    cursor.execute("SELECT COUNT(*) FROM network_health")
    total_health = cursor.fetchone()[0]
    print(f"Total network health records: {total_health}")
    
    if total_health > 0:
        cursor.execute("SELECT miner_id, COUNT(*) as count FROM network_health GROUP BY miner_id")
        health_by_miner = cursor.fetchall()
        print("\nNetwork health records per miner:")
        for miner_id, count in health_by_miner:
            print(f"  - {miner_id}: {count} records")
else:
    print("Network health table does not exist")

conn.close()

print("\n" + "=" * 80)
print("DATABASE CHECK COMPLETE")
print("=" * 80)
