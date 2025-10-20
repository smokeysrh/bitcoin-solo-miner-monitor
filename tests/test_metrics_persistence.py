"""
Test script to verify metrics persistence in the database.
This script will:
1. Check if the miner_metrics table exists
2. Query for any existing metrics data
3. Display the results
"""
import sqlite3
import sys
from datetime import datetime, timedelta

def test_metrics_persistence():
    """Test that metrics are being persisted to the database."""
    db_path = 'data/config.db'
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("=" * 80)
        print("METRICS PERSISTENCE TEST")
        print("=" * 80)
        print()
        
        # Check if miner_metrics table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='miner_metrics'
        """)
        table_exists = cursor.fetchone()
        
        if not table_exists:
            print("❌ ERROR: miner_metrics table does not exist!")
            return False
        
        print("✓ miner_metrics table exists")
        print()
        
        # Get table schema
        cursor.execute("PRAGMA table_info(miner_metrics)")
        columns = cursor.fetchall()
        print("Table Schema:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
        print()
        
        # Count total metrics
        cursor.execute("SELECT COUNT(*) FROM miner_metrics")
        total_count = cursor.fetchone()[0]
        print(f"Total metrics records: {total_count}")
        print()
        
        if total_count == 0:
            print("⚠️  WARNING: No metrics data found in database")
            print("   This could mean:")
            print("   1. The application hasn't been running long enough")
            print("   2. No miners are configured")
            print("   3. Metrics saving is not working")
            print()
            return False
        
        # Get metrics by type
        cursor.execute("""
            SELECT metric_type, COUNT(*) as count
            FROM miner_metrics
            GROUP BY metric_type
            ORDER BY count DESC
        """)
        metrics_by_type = cursor.fetchall()
        
        print("Metrics by Type:")
        for metric_type, count in metrics_by_type:
            print(f"  - {metric_type}: {count} records")
        print()
        
        # Get metrics by miner
        cursor.execute("""
            SELECT miner_id, COUNT(*) as count
            FROM miner_metrics
            GROUP BY miner_id
            ORDER BY count DESC
        """)
        metrics_by_miner = cursor.fetchall()
        
        print("Metrics by Miner:")
        for miner_id, count in metrics_by_miner:
            print(f"  - {miner_id}: {count} records")
        print()
        
        # Get recent metrics (last 10)
        cursor.execute("""
            SELECT miner_id, timestamp, metric_type, value, unit
            FROM miner_metrics
            ORDER BY timestamp DESC
            LIMIT 10
        """)
        recent_metrics = cursor.fetchall()
        
        print("Recent Metrics (last 10):")
        for miner_id, timestamp, metric_type, value, unit in recent_metrics:
            unit_str = f" {unit}" if unit else ""
            print(f"  - {timestamp} | {miner_id} | {metric_type}: {value}{unit_str}")
        print()
        
        # Check time range of data
        cursor.execute("""
            SELECT 
                MIN(timestamp) as first_metric,
                MAX(timestamp) as last_metric
            FROM miner_metrics
        """)
        first_metric, last_metric = cursor.fetchone()
        
        print("Time Range:")
        print(f"  - First metric: {first_metric}")
        print(f"  - Last metric:  {last_metric}")
        print()
        
        # Check for metrics in the last 5 minutes
        five_minutes_ago = (datetime.now() - timedelta(minutes=5)).isoformat()
        cursor.execute("""
            SELECT COUNT(*) FROM miner_metrics
            WHERE timestamp > ?
        """, (five_minutes_ago,))
        recent_count = cursor.fetchone()[0]
        
        print(f"Metrics in last 5 minutes: {recent_count}")
        
        if recent_count > 0:
            print("✓ Metrics are being actively saved!")
        else:
            print("⚠️  No recent metrics - application may not be running")
        
        print()
        print("=" * 80)
        print("TEST COMPLETE")
        print("=" * 80)
        
        conn.close()
        return total_count > 0
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_metrics_persistence()
    sys.exit(0 if success else 1)
