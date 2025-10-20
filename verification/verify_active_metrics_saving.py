"""
Verify that metrics are being actively saved during polling cycles.
This script will:
1. Check current metrics count
2. Wait for 1 minute (2 polling cycles at 30s interval)
3. Check metrics count again
4. Verify new metrics were added
"""
import sqlite3
import time
from datetime import datetime

def verify_active_saving():
    """Verify metrics are being actively saved."""
    db_path = 'data/config.db'
    
    print("=" * 80)
    print("ACTIVE METRICS SAVING VERIFICATION")
    print("=" * 80)
    print()
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get initial count
        cursor.execute("SELECT COUNT(*) FROM miner_metrics")
        initial_count = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT MAX(timestamp) FROM miner_metrics
        """)
        last_timestamp = cursor.fetchone()[0]
        
        print(f"Initial State:")
        print(f"  - Total metrics: {initial_count}")
        print(f"  - Last metric timestamp: {last_timestamp}")
        print()
        
        print("Waiting 60 seconds for new polling cycles...")
        print("(Polling interval is ~30 seconds, so we should see 2 new cycles)")
        print()
        
        # Wait for 60 seconds
        for i in range(60, 0, -10):
            print(f"  {i} seconds remaining...", end='\r')
            time.sleep(10)
        
        print("\n")
        
        # Get new count
        cursor.execute("SELECT COUNT(*) FROM miner_metrics")
        final_count = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT MAX(timestamp) FROM miner_metrics
        """)
        new_last_timestamp = cursor.fetchone()[0]
        
        # Get metrics added in the last minute
        cursor.execute("""
            SELECT miner_id, metric_type, COUNT(*) as count
            FROM miner_metrics
            WHERE timestamp > ?
            GROUP BY miner_id, metric_type
            ORDER BY miner_id, metric_type
        """, (last_timestamp,))
        new_metrics = cursor.fetchall()
        
        print(f"Final State:")
        print(f"  - Total metrics: {final_count}")
        print(f"  - Last metric timestamp: {new_last_timestamp}")
        print()
        
        metrics_added = final_count - initial_count
        print(f"Metrics Added: {metrics_added}")
        print()
        
        if metrics_added > 0:
            print("✓ SUCCESS: New metrics were saved during the test period!")
            print()
            print("New Metrics by Type:")
            for miner_id, metric_type, count in new_metrics:
                print(f"  - {miner_id} | {metric_type}: {count} new records")
            print()
            
            # Verify we got metrics from expected types
            expected_types = ['hashrate', 'temperature', 'power', 'fan_speed', 
                            'shares_accepted', 'shares_rejected', 'uptime']
            found_types = set(metric_type for _, metric_type, _ in new_metrics)
            
            print("Metric Type Coverage:")
            for expected in expected_types:
                if expected in found_types:
                    print(f"  ✓ {expected}")
                else:
                    print(f"  ✗ {expected} (missing)")
            print()
            
            return True
        else:
            print("❌ FAILURE: No new metrics were saved!")
            print()
            print("Possible issues:")
            print("  1. Application is not running")
            print("  2. No miners are configured or online")
            print("  3. Polling is disabled")
            print("  4. Metrics saving is failing silently")
            print()
            return False
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    finally:
        if conn:
            conn.close()
    
    print("=" * 80)

if __name__ == "__main__":
    success = verify_active_saving()
    exit(0 if success else 1)
