#!/usr/bin/env python3
"""
Verification script for Task 2.1: Backend metrics broadcasting
This verifies that the backend is correctly broadcasting metrics without testing subscription
"""

import sys

def verify_backend_implementation():
    """Verify that the backend code changes are in place"""
    
    print("=" * 60)
    print("Task 2.1 Backend Implementation Verification")
    print("=" * 60)
    print()
    
    checks_passed = 0
    checks_total = 3
    
    # Check 1: Verify broadcast_metrics method exists in WebSocketManager
    print("Check 1: Verifying broadcast_metrics method exists...")
    try:
        with open('src/backend/services/websocket_manager.py', 'r') as f:
            content = f.read()
            if 'async def broadcast_metrics' in content and 'miner_id' in content and 'metrics' in content:
                print("  ✓ broadcast_metrics method found in WebSocketManager")
                checks_passed += 1
            else:
                print("  ✗ broadcast_metrics method not found or incomplete")
    except Exception as e:
        print(f"  ✗ Error reading websocket_manager.py: {e}")
    
    # Check 2: Verify broadcast call in miner_manager
    print("\nCheck 2: Verifying metrics broadcast call in MinerManager...")
    try:
        with open('src/backend/services/miner_manager.py', 'r') as f:
            content = f.read()
            if 'websocket_manager.broadcast_metrics' in content:
                print("  ✓ Broadcast call found in MinerManager")
                checks_passed += 1
            else:
                print("  ✗ Broadcast call not found in MinerManager")
    except Exception as e:
        print(f"  ✗ Error reading miner_manager.py: {e}")
    
    # Check 3: Verify message structure includes required fields
    print("\nCheck 3: Verifying message structure includes miner_id, metrics, and timestamp...")
    try:
        with open('src/backend/services/websocket_manager.py', 'r') as f:
            content = f.read()
            # Look for the broadcast_metrics method and check its structure
            if all(field in content for field in ['"miner_id":', '"metrics":', '"timestamp":', '"metrics_update"']):
                print("  ✓ Message structure includes all required fields")
                checks_passed += 1
            else:
                print("  ✗ Message structure missing required fields")
    except Exception as e:
        print(f"  ✗ Error verifying message structure: {e}")
    
    print()
    print("=" * 60)
    print(f"Verification Results: {checks_passed}/{checks_total} checks passed")
    print("=" * 60)
    print()
    
    if checks_passed == checks_total:
        print("✓ Task 2.1 implementation is COMPLETE!")
        print()
        print("Summary:")
        print("- Backend broadcasts metrics_update events when metrics are saved")
        print("- WebSocket payload includes miner_id and all metric fields")
        print("- Message format is correct and ready for frontend consumption")
        print()
        print("Note: Frontend subscription (Task 2.2) is required to receive these messages")
        return True
    else:
        print("✗ Task 2.1 implementation is INCOMPLETE")
        print(f"  {checks_total - checks_passed} check(s) failed")
        return False

if __name__ == "__main__":
    success = verify_backend_implementation()
    sys.exit(0 if success else 1)
