"""
Test script to verify metrics saving throttling.
This script monitors the database to confirm metrics are only saved once per minute,
regardless of the polling interval.
"""
import sqlite3
import time
from datetime import datetime, timedelta

def test_metrics_throttling():
    """
    Monitor the database to verify metrics are saved at 60-second intervals.
    """
    db_path = 'data/config.db'
    
    print("=" * 80)
    print("METRICS THROTTLING TEST")
    print("=" * 80)
    print()
    print("This test will monitor the database for 3 minutes to verify that")
    print("metrics are saved at 60-second intervals, regardless of polling frequency.")
    print()
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get initial count and timestamp
        cursor.execute("SELECT COUNT(*), MAX(timestamp) FROM miner_metrics")
        initial_count, last_timestamp = cursor.fetchone()
        
        print(f"Initial State:")
        print(f"  - Total metrics: {initial_count}")
        print(f"  - Last timestamp: {last_timestamp}")
        print()
        
        print("Monitoring for 3 minutes...")
        print("Expected: ~3 new metric saves (one per minute)")
        print()
        
        start_time = time.time()
        last_check_count = initial_count
        save_times = []
        
        # Monitor for 3 minutes
        while time.time() - start_time < 180:
            time.sleep(10)  # Check every 10 seconds
            
            cursor.execute("SELECT COUNT(*), MAX(timestamp) FROM miner_metrics")
            current_count, current_timestamp = cursor.fetchone()
            
            if current_count > last_check_count:
                elapsed = time.time() - start_time
                new_records = current_count - last_check_count
                save_times.append(elapsed)
                
                print(f"[{elapsed:6.1f}s] New metrics saved!")
                print(f"           - Records added: {new_records}")
                print(f"           - Latest timestamp: {current_timestamp}")
                
                # Check interval since last save
                if len(save_times) > 1:
                    interval = save_times[-1] - save_times[-2]
                    print(f"           - Interval since last save: {interval:.1f}s")
                    
                    if 55 <= interval <= 65:
                        print(f"           ✓ Interval is within expected range (55-65s)")
                    else:
                        print(f"           ⚠️  Interval outside expected range!")
                
                print()
                last_check_count = current_count
        
        # Final analysis
        print("=" * 80)
        print("TEST RESULTS")
        print("=" * 80)
        print()
        
        cursor.execute("SELECT COUNT(*) FROM miner_metrics")
        final_count = cursor.fetchone()[0]
        
        total_new_records = final_count - initial_count
        num_saves = len(save_times)
        
        print(f"Total new records: {total_new_records}")
        print(f"Number of save events: {num_saves}")
        print(f"Expected save events: 3")
        print()
        
        if num_saves >= 2 and num_saves <= 4:
            print("✓ PASS: Metrics are being saved at approximately 60-second intervals")
            
            # Check intervals
            if len(save_times) > 1:
                print()
                print("Save Intervals:")
                for i in range(1, len(save_times)):
                    interval = save_times[i] - save_times[i-1]
                    status = "✓" if 55 <= interval <= 65 else "✗"
                    print(f"  {status} Save {i}: {interval:.1f}s after previous save")
        else:
            print(f"✗ FAIL: Expected 2-4 save events, got {num_saves}")
        
        print()
        print("=" * 80)
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    test_metrics_throttling()
