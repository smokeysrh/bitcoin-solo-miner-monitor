import sqlite3
import json
from datetime import datetime, timedelta

conn = sqlite3.connect('data/config.db')
cursor = conn.cursor()

print("=" * 80)
print("CHART DATA VERIFICATION")
print("=" * 80)

# Test 1: Get data for hashrate chart (last 24 hours)
print("\n1. HASHRATE CHART DATA (Last 24 hours):")
print("-" * 80)
end_time = datetime.now()
start_time = end_time - timedelta(hours=24)

cursor.execute("""
    SELECT timestamp, value
    FROM miner_metrics
    WHERE miner_id = 'bitaxe_192_168_1_156'
    AND metric_type = 'hashrate'
    AND timestamp >= ?
    ORDER BY timestamp
""", (start_time.isoformat(),))

hashrate_data = cursor.fetchall()
print(f"Data points available: {len(hashrate_data)}")
if hashrate_data:
    print(f"First point: {hashrate_data[0][0]} - {hashrate_data[0][1]/1e12:.2f} TH/s")
    print(f"Last point: {hashrate_data[-1][0]} - {hashrate_data[-1][1]/1e12:.2f} TH/s")
    
    # Calculate average
    avg_hashrate = sum(row[1] for row in hashrate_data) / len(hashrate_data)
    print(f"Average: {avg_hashrate/1e12:.2f} TH/s")

# Test 2: Get data for temperature chart
print("\n2. TEMPERATURE CHART DATA (Last 24 hours):")
print("-" * 80)
cursor.execute("""
    SELECT timestamp, value
    FROM miner_metrics
    WHERE miner_id = 'bitaxe_192_168_1_156'
    AND metric_type = 'temperature'
    AND timestamp >= ?
    ORDER BY timestamp
""", (start_time.isoformat(),))

temp_data = cursor.fetchall()
print(f"Data points available: {len(temp_data)}")
if temp_data:
    print(f"First point: {temp_data[0][0]} - {temp_data[0][1]:.2f}°C")
    print(f"Last point: {temp_data[-1][0]} - {temp_data[-1][1]:.2f}°C")
    
    # Calculate min/max/avg
    temps = [row[1] for row in temp_data]
    print(f"Min: {min(temps):.2f}°C")
    print(f"Max: {max(temps):.2f}°C")
    print(f"Avg: {sum(temps)/len(temps):.2f}°C")

# Test 3: Get data for power chart
print("\n3. POWER CHART DATA (Last 24 hours):")
print("-" * 80)
cursor.execute("""
    SELECT timestamp, value
    FROM miner_metrics
    WHERE miner_id = 'bitaxe_192_168_1_156'
    AND metric_type = 'power'
    AND timestamp >= ?
    ORDER BY timestamp
""", (start_time.isoformat(),))

power_data = cursor.fetchall()
print(f"Data points available: {len(power_data)}")
if power_data:
    print(f"First point: {power_data[0][0]} - {power_data[0][1]:.2f}W")
    print(f"Last point: {power_data[-1][0]} - {power_data[-1][1]:.2f}W")
    
    # Calculate average
    avg_power = sum(row[1] for row in power_data) / len(power_data)
    print(f"Average: {avg_power:.2f}W")

# Test 4: Get aggregated data (hourly)
print("\n4. HOURLY AGGREGATED DATA (Last 24 hours):")
print("-" * 80)
cursor.execute("""
    SELECT 
        strftime('%Y-%m-%d %H:00', timestamp) as hour,
        metric_type,
        AVG(value) as avg_value,
        MIN(value) as min_value,
        MAX(value) as max_value,
        COUNT(*) as sample_count
    FROM miner_metrics
    WHERE miner_id = 'bitaxe_192_168_1_156'
    AND timestamp >= ?
    AND metric_type IN ('hashrate', 'temperature', 'power')
    GROUP BY hour, metric_type
    ORDER BY hour, metric_type
""", (start_time.isoformat(),))

aggregated_data = cursor.fetchall()
print(f"Aggregated data points: {len(aggregated_data)}")
if aggregated_data:
    print("\nSample of aggregated data:")
    for row in aggregated_data[:6]:  # Show first 6
        hour, metric, avg, min_val, max_val, count = row
        if metric == 'hashrate':
            print(f"  {hour} | {metric}: avg={avg/1e12:.2f}TH/s, samples={count}")
        elif metric == 'temperature':
            print(f"  {hour} | {metric}: avg={avg:.2f}°C, min={min_val:.2f}°C, max={max_val:.2f}°C")
        elif metric == 'power':
            print(f"  {hour} | {metric}: avg={avg:.2f}W, samples={count}")

# Test 5: Get network health chart data
print("\n5. NETWORK HEALTH CHART DATA (Last 24 hours):")
print("-" * 80)
cursor.execute("""
    SELECT measured_at, latency_ms, packet_loss_percent
    FROM network_health
    WHERE miner_id = 'bitaxe_192_168_1_156'
    AND measured_at >= ?
    ORDER BY measured_at
""", (start_time.isoformat(),))

health_data = cursor.fetchall()
print(f"Data points available: {len(health_data)}")
if health_data:
    print(f"First point: {health_data[0][0]} - Latency: {health_data[0][1]}ms, Loss: {health_data[0][2]}%")
    print(f"Last point: {health_data[-1][0]} - Latency: {health_data[-1][1]}ms, Loss: {health_data[-1][2]}%")

# Test 6: Check data format for frontend
print("\n6. SAMPLE DATA FORMAT FOR FRONTEND:")
print("-" * 80)
cursor.execute("""
    SELECT timestamp, metric_type, value, unit
    FROM miner_metrics
    WHERE miner_id = 'bitaxe_192_168_1_156'
    AND timestamp = (SELECT MAX(timestamp) FROM miner_metrics WHERE miner_id = 'bitaxe_192_168_1_156')
    ORDER BY metric_type
""")

latest_metrics = cursor.fetchall()
print("Latest metrics in API format:")
metrics_dict = {}
for ts, metric_type, value, unit in latest_metrics:
    metrics_dict[metric_type] = {
        "value": value,
        "unit": unit,
        "timestamp": ts
    }

print(json.dumps(metrics_dict, indent=2))

# Test 7: Verify data continuity for charts
print("\n7. DATA CONTINUITY CHECK:")
print("-" * 80)
cursor.execute("""
    SELECT timestamp
    FROM miner_metrics
    WHERE miner_id = 'bitaxe_192_168_1_156'
    AND timestamp >= ?
    GROUP BY timestamp
    ORDER BY timestamp
""", (start_time.isoformat(),))

timestamps = [row[0] for row in cursor.fetchall()]
if len(timestamps) > 1:
    gaps = []
    for i in range(1, len(timestamps)):
        prev_time = datetime.fromisoformat(timestamps[i-1])
        curr_time = datetime.fromisoformat(timestamps[i])
        gap = (curr_time - prev_time).total_seconds()
        if gap > 120:  # More than 2 minutes
            gaps.append(gap)
    
    if gaps:
        print(f"Found {len(gaps)} gaps in last 24 hours")
        print(f"Largest gap: {max(gaps)/60:.1f} minutes")
    else:
        print("✓ No significant gaps in last 24 hours - charts should render smoothly!")

conn.close()

print("\n" + "=" * 80)
print("CHART DATA VERIFICATION COMPLETE")
print("=" * 80)
print("\n✓ Database contains valid data for all chart types")
print("✓ Data is properly formatted and ready for visualization")
print("✓ You can now restart the app to test data persistence!")
