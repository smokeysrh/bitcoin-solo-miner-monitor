import sqlite3
import json
from datetime import datetime, timedelta
from collections import defaultdict

conn = sqlite3.connect('data/config.db')
cursor = conn.cursor()

print("=" * 80)
print("DATA QUALITY ANALYSIS")
print("=" * 80)

# 1. Check for data gaps in metrics
print("\n1. CHECKING FOR DATA GAPS IN METRICS:")
print("-" * 80)
cursor.execute("""
    SELECT timestamp 
    FROM miner_metrics 
    WHERE miner_id = 'bitaxe_192_168_1_156'
    GROUP BY timestamp
    ORDER BY timestamp
""")
timestamps = [row[0] for row in cursor.fetchall()]

if len(timestamps) > 1:
    gaps = []
    for i in range(1, len(timestamps)):
        prev_time = datetime.fromisoformat(timestamps[i-1])
        curr_time = datetime.fromisoformat(timestamps[i])
        gap = (curr_time - prev_time).total_seconds()
        if gap > 120:  # More than 2 minutes gap
            gaps.append((timestamps[i-1], timestamps[i], gap))
    
    if gaps:
        print(f"Found {len(gaps)} significant gaps (>2 minutes):")
        for prev, curr, gap_seconds in gaps[:5]:  # Show first 5
            print(f"  - Gap of {gap_seconds/60:.1f} minutes between {prev} and {curr}")
    else:
        print("✓ No significant gaps found - data collection is consistent!")
else:
    print("Not enough data points to check for gaps")

# 2. Check metric completeness per timestamp
print("\n2. CHECKING METRIC COMPLETENESS:")
print("-" * 80)
cursor.execute("""
    SELECT timestamp, COUNT(DISTINCT metric_type) as metric_count
    FROM miner_metrics
    WHERE miner_id = 'bitaxe_192_168_1_156'
    GROUP BY timestamp
    ORDER BY timestamp DESC
    LIMIT 10
""")
recent_completeness = cursor.fetchall()
print("Recent timestamps and their metric counts:")
for ts, count in recent_completeness:
    print(f"  - {ts}: {count} metrics")

# 3. Check for null or invalid values
print("\n3. CHECKING FOR NULL OR INVALID VALUES:")
print("-" * 80)
cursor.execute("""
    SELECT metric_type, COUNT(*) as null_count
    FROM miner_metrics
    WHERE value IS NULL OR value < 0
    GROUP BY metric_type
""")
null_values = cursor.fetchall()
if null_values:
    print("Metrics with null or negative values:")
    for metric, count in null_values:
        print(f"  - {metric}: {count} invalid records")
else:
    print("✓ No null or negative values found!")

# 4. Check value ranges for key metrics
print("\n4. CHECKING VALUE RANGES FOR KEY METRICS:")
print("-" * 80)
key_metrics = ['hashrate', 'temperature', 'power', 'fan_speed']
for metric in key_metrics:
    cursor.execute("""
        SELECT MIN(value), MAX(value), AVG(value), COUNT(*)
        FROM miner_metrics
        WHERE miner_id = 'bitaxe_192_168_1_156' AND metric_type = ?
    """, (metric,))
    result = cursor.fetchone()
    if result and result[3] > 0:
        min_val, max_val, avg_val, count = result
        print(f"{metric}:")
        print(f"  - Min: {min_val:.2f}")
        print(f"  - Max: {max_val:.2f}")
        print(f"  - Avg: {avg_val:.2f}")
        print(f"  - Count: {count}")

# 5. Check network health data
print("\n5. CHECKING NETWORK HEALTH DATA:")
print("-" * 80)
cursor.execute("""
    SELECT 
        MIN(latency_ms) as min_latency,
        MAX(latency_ms) as max_latency,
        AVG(latency_ms) as avg_latency,
        MIN(packet_loss_percent) as min_loss,
        MAX(packet_loss_percent) as max_loss,
        AVG(packet_loss_percent) as avg_loss,
        COUNT(*) as total_records
    FROM network_health
    WHERE miner_id = 'bitaxe_192_168_1_156'
""")
health_stats = cursor.fetchone()
if health_stats and health_stats[6] > 0:
    print(f"Latency (ms):")
    print(f"  - Min: {health_stats[0]:.2f}")
    print(f"  - Max: {health_stats[1]:.2f}")
    print(f"  - Avg: {health_stats[2]:.2f}")
    print(f"Packet Loss (%):")
    print(f"  - Min: {health_stats[3]:.2f}")
    print(f"  - Max: {health_stats[4]:.2f}")
    print(f"  - Avg: {health_stats[5]:.2f}")
    print(f"Total records: {health_stats[6]}")

# 6. Check data collection timeline
print("\n6. DATA COLLECTION TIMELINE:")
print("-" * 80)
cursor.execute("""
    SELECT MIN(timestamp), MAX(timestamp)
    FROM miner_metrics
    WHERE miner_id = 'bitaxe_192_168_1_156'
""")
time_range = cursor.fetchone()
if time_range[0] and time_range[1]:
    start_time = datetime.fromisoformat(time_range[0])
    end_time = datetime.fromisoformat(time_range[1])
    duration = end_time - start_time
    
    print(f"Start: {time_range[0]}")
    print(f"End: {time_range[1]}")
    print(f"Duration: {duration.total_seconds()/3600:.1f} hours ({duration.days} days, {duration.seconds//3600} hours)")
    
    # Calculate expected vs actual data points
    cursor.execute("SELECT COUNT(DISTINCT timestamp) FROM miner_metrics WHERE miner_id = 'bitaxe_192_168_1_156'")
    actual_points = cursor.fetchone()[0]
    expected_points = duration.total_seconds() / 60  # Assuming 1-minute intervals
    
    print(f"Actual data points: {actual_points}")
    print(f"Expected data points (1/min): {expected_points:.0f}")
    print(f"Collection rate: {(actual_points/expected_points)*100:.1f}%")

# 7. Check for duplicate timestamps
print("\n7. CHECKING FOR DUPLICATE TIMESTAMPS:")
print("-" * 80)
cursor.execute("""
    SELECT timestamp, COUNT(*) as count
    FROM (
        SELECT DISTINCT timestamp, metric_type
        FROM miner_metrics
        WHERE miner_id = 'bitaxe_192_168_1_156'
    )
    GROUP BY timestamp
    HAVING COUNT(*) > 7
    ORDER BY count DESC
    LIMIT 5
""")
duplicates = cursor.fetchall()
if duplicates:
    print("Timestamps with unusual metric counts:")
    for ts, count in duplicates:
        print(f"  - {ts}: {count} metrics")
else:
    print("✓ No unusual duplicate patterns found!")

# 8. Check shares data
print("\n8. CHECKING SHARES DATA:")
print("-" * 80)
cursor.execute("""
    SELECT 
        SUM(CASE WHEN metric_type = 'shares_accepted' THEN value ELSE 0 END) as total_accepted,
        SUM(CASE WHEN metric_type = 'shares_rejected' THEN value ELSE 0 END) as total_rejected
    FROM (
        SELECT metric_type, value
        FROM miner_metrics
        WHERE miner_id = 'bitaxe_192_168_1_156' 
        AND metric_type IN ('shares_accepted', 'shares_rejected')
        AND timestamp = (SELECT MAX(timestamp) FROM miner_metrics WHERE miner_id = 'bitaxe_192_168_1_156')
    )
""")
shares = cursor.fetchone()
if shares and shares[0]:
    accepted = shares[0]
    rejected = shares[1] or 0
    total = accepted + rejected
    reject_rate = (rejected / total * 100) if total > 0 else 0
    print(f"Latest shares count:")
    print(f"  - Accepted: {accepted:.0f}")
    print(f"  - Rejected: {rejected:.0f}")
    print(f"  - Reject rate: {reject_rate:.2f}%")

conn.close()

print("\n" + "=" * 80)
print("DATA QUALITY ANALYSIS COMPLETE")
print("=" * 80)
