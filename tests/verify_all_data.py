import sqlite3
import json
from datetime import datetime, timedelta

conn = sqlite3.connect('data/config.db')
cursor = conn.cursor()

print("=" * 80)
print("COMPLETE DATA VERIFICATION FOR APP RESTART TEST")
print("=" * 80)

# Get the actual time range of data
cursor.execute("""
    SELECT MIN(timestamp), MAX(timestamp)
    FROM miner_metrics
    WHERE miner_id = 'bitaxe_192_168_1_156'
""")
time_range = cursor.fetchone()
start_time = datetime.fromisoformat(time_range[0])
end_time = datetime.fromisoformat(time_range[1])

print(f"\nData Time Range:")
print(f"  Start: {time_range[0]}")
print(f"  End: {time_range[1]}")
print(f"  Duration: {(end_time - start_time).total_seconds()/3600:.1f} hours")

# Check if we have recent data (within last hour)
one_hour_ago = datetime.now() - timedelta(hours=1)
cursor.execute("""
    SELECT COUNT(*)
    FROM miner_metrics
    WHERE miner_id = 'bitaxe_192_168_1_156'
    AND timestamp >= ?
""", (one_hour_ago.isoformat(),))
recent_count = cursor.fetchone()[0]

print(f"\nRecent Data (last hour): {recent_count} records")
if recent_count > 0:
    print("✓ App is actively collecting data!")
else:
    print("⚠ No data in last hour - app may have stopped collecting")

# Get chart data for the entire available range
print("\n" + "=" * 80)
print("CHART DATA AVAILABILITY (All Time):")
print("=" * 80)

metrics_to_check = ['hashrate', 'temperature', 'power', 'fan_speed', 'shares_accepted', 'shares_rejected', 'uptime']

for metric in metrics_to_check:
    cursor.execute("""
        SELECT COUNT(*), MIN(value), MAX(value), AVG(value)
        FROM miner_metrics
        WHERE miner_id = 'bitaxe_192_168_1_156'
        AND metric_type = ?
    """, (metric,))
    
    result = cursor.fetchone()
    count, min_val, max_val, avg_val = result
    
    if count > 0:
        if metric == 'hashrate':
            print(f"\n{metric.upper()}:")
            print(f"  Records: {count}")
            print(f"  Min: {min_val/1e12:.2f} TH/s")
            print(f"  Max: {max_val/1e12:.2f} TH/s")
            print(f"  Avg: {avg_val/1e12:.2f} TH/s")
        elif metric == 'temperature':
            print(f"\n{metric.upper()}:")
            print(f"  Records: {count}")
            print(f"  Min: {min_val:.2f}°C")
            print(f"  Max: {max_val:.2f}°C")
            print(f"  Avg: {avg_val:.2f}°C")
        else:
            print(f"\n{metric.upper()}:")
            print(f"  Records: {count}")
            print(f"  Min: {min_val:.2f}")
            print(f"  Max: {max_val:.2f}")
            print(f"  Avg: {avg_val:.2f}")

# Check miner configuration
print("\n" + "=" * 80)
print("MINER CONFIGURATION:")
print("=" * 80)
cursor.execute("SELECT id, config, updated_at FROM miners WHERE id = 'bitaxe_192_168_1_156'")
miner = cursor.fetchone()
if miner:
    config = json.loads(miner[1])
    print(f"Miner ID: {miner[0]}")
    print(f"Last Updated: {miner[2]}")
    print(f"Configuration keys: {list(config.keys())}")
    print(f"\nMiner Details:")
    if 'name' in config:
        print(f"  Name: {config['name']}")
    if 'ip' in config:
        print(f"  IP: {config['ip']}")
    if 'port' in config:
        print(f"  Port: {config['port']}")

# Check app settings
print("\n" + "=" * 80)
print("APP SETTINGS:")
print("=" * 80)
cursor.execute("SELECT value FROM settings WHERE id = 'app_settings'")
settings_row = cursor.fetchone()
if settings_row:
    settings = json.loads(settings_row[0])
    print("Current settings:")
    for key, value in settings.items():
        print(f"  {key}: {value}")
else:
    print("No app settings found (will use defaults)")

# Summary for restart test
print("\n" + "=" * 80)
print("RESTART TEST READINESS:")
print("=" * 80)

checks = []

# Check 1: Database exists and has tables
cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
table_count = cursor.fetchone()[0]
checks.append(("Database tables exist", table_count >= 4))

# Check 2: Miner config exists
cursor.execute("SELECT COUNT(*) FROM miners")
miner_count = cursor.fetchone()[0]
checks.append(("Miner configuration saved", miner_count > 0))

# Check 3: Metrics data exists
cursor.execute("SELECT COUNT(*) FROM miner_metrics")
metrics_count = cursor.fetchone()[0]
checks.append(("Metrics data saved", metrics_count > 1000))

# Check 4: Network health data exists
cursor.execute("SELECT COUNT(*) FROM network_health")
health_count = cursor.fetchone()[0]
checks.append(("Network health data saved", health_count > 0))

# Check 5: Data is recent
checks.append(("Recent data available", recent_count > 0))

print("\nPre-restart checks:")
for check_name, passed in checks:
    status = "✓" if passed else "✗"
    print(f"  {status} {check_name}")

all_passed = all(passed for _, passed in checks)

print("\n" + "=" * 80)
if all_passed:
    print("✓ ALL CHECKS PASSED!")
    print("\nYou can now:")
    print("  1. Close the app")
    print("  2. Restart the app")
    print("  3. Verify that:")
    print("     - Miner appears in the list")
    print("     - Charts load with historical data")
    print("     - Latest metrics are displayed")
    print("     - Data continues to be collected")
else:
    print("⚠ SOME CHECKS FAILED")
    print("\nIssues to address before restart test:")
    for check_name, passed in checks:
        if not passed:
            print(f"  - {check_name}")

print("=" * 80)

conn.close()
