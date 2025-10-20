"""
Check the actual intervals between metric saves to verify throttling.
"""
import sqlite3
from datetime import datetime

def check_save_intervals():
    """Check intervals between consecutive metric saves."""
    db_path = 'data/config.db'
    
    print("=" * 80)
    print("METRICS SAVE INTERVAL ANALYSIS")
    print("=" * 80)
    print()
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get distinct timestamps for the last 20 saves
        cursor.execute("""
            SELECT DISTINCT timestamp
            FROM miner_metrics
            WHERE miner_id = 'bitaxe_192_168_1_156'
            ORDER BY timestamp DESC
            LIMIT 20
        """)
        
        timestamps = [row[0] for row in cursor.fetchall()]
        timestamps.reverse()  # Oldest first
        
        if len(timestamps) < 2:
            print("Not enough data to analyze intervals")
            return
        
        print(f"Analyzing last {len(timestamps)} metric saves...")
        print()
        
        intervals = []
        
        print("Timestamp                      | Interval from Previous")
        print("-" * 80)
        
        for i, ts_str in enumerate(timestamps):
            if i == 0:
                print(f"{ts_str} | (first)")
            else:
                prev_ts = datetime.fromisoformat(timestamps[i-1])
                curr_ts = datetime.fromisoformat(ts_str)
                interval = (curr_ts - prev_ts).total_seconds()
                intervals.append(interval)
                
                status = "✓" if 55 <= interval <= 65 else "⚠️"
                print(f"{ts_str} | {status} {interval:6.1f}s")
        
        print()
        print("=" * 80)
        print("INTERVAL STATISTICS")
        print("=" * 80)
        print()
        
        if intervals:
            avg_interval = sum(intervals) / len(intervals)
            min_interval = min(intervals)
            max_interval = max(intervals)
            
            print(f"Average interval: {avg_interval:.1f}s")
            print(f"Minimum interval: {min_interval:.1f}s")
            print(f"Maximum interval: {max_interval:.1f}s")
            print()
            
            # Count intervals in expected range (55-65 seconds)
            in_range = sum(1 for i in intervals if 55 <= i <= 65)
            percentage = (in_range / len(intervals)) * 100
            
            print(f"Intervals in expected range (55-65s): {in_range}/{len(intervals)} ({percentage:.1f}%)")
            print()
            
            if percentage >= 80:
                print("✓ PASS: Throttling is working correctly!")
                print("  Metrics are being saved at ~60 second intervals.")
            elif avg_interval >= 55:
                print("⚠️  PARTIAL: Average interval is good, but some outliers exist.")
                print("  This may be due to application restarts or errors.")
            else:
                print("✗ FAIL: Intervals are too short!")
                print("  Throttling may not be working correctly.")
        
        print()
        print("=" * 80)
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_save_intervals()
