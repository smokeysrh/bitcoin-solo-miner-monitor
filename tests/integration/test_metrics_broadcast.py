#!/usr/bin/env python3
"""
Test script to verify WebSocket metrics broadcasting functionality
"""

import asyncio
import websockets
import json
import sys
from datetime import datetime

async def test_metrics_broadcast():
    """Test that metrics updates are broadcasted via WebSocket"""
    uri = "ws://localhost:8000/ws"
    
    try:
        print(f"Connecting to {uri}...")
        async with websockets.connect(uri) as websocket:
            print("✓ WebSocket connection established!")
            
            # Wait for connection_established message
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(response)
                print(f"✓ Received connection message: {data.get('type')}")
                
                if data.get("type") != "connection_established":
                    print(f"⚠ Unexpected first message type: {data.get('type')}")
                    
            except asyncio.TimeoutError:
                print("⚠ No connection message received")
            
            # Subscribe to metrics topic
            subscribe_message = {
                "type": "subscribe",
                "topics": ["metrics"]
            }
            
            await websocket.send(json.dumps(subscribe_message))
            print("✓ Subscribed to 'metrics' topic")
            
            # Wait for subscription confirmation
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(response)
                print(f"✓ Received subscription response: {data.get('type')}")
                
            except asyncio.TimeoutError:
                print("⚠ No subscription confirmation received")
            
            # Wait for metrics_update messages
            print("\nWaiting for metrics_update messages (60 seconds)...")
            print("Note: Metrics are saved every 60 seconds by default")
            
            metrics_received = False
            timeout = 65  # Wait slightly longer than metrics save interval
            
            try:
                while timeout > 0:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        data = json.loads(response)
                        
                        if data.get("type") == "metrics_update":
                            print(f"\n✓ Received metrics_update message!")
                            print(f"  Miner ID: {data.get('data', {}).get('miner_id')}")
                            print(f"  Timestamp: {data.get('data', {}).get('timestamp')}")
                            print(f"  Metrics: {list(data.get('data', {}).get('metrics', {}).keys())}")
                            
                            # Verify message structure
                            if not data.get('data', {}).get('miner_id'):
                                print("  ⚠ Missing miner_id in message")
                                return False
                            
                            if not data.get('data', {}).get('metrics'):
                                print("  ⚠ Missing metrics in message")
                                return False
                            
                            if not data.get('data', {}).get('timestamp'):
                                print("  ⚠ Missing timestamp in message")
                                return False
                            
                            metrics_received = True
                            break
                        elif data.get("type") == "ping":
                            # Respond to ping
                            pong_message = {"type": "pong", "timestamp": datetime.now().isoformat()}
                            await websocket.send(json.dumps(pong_message))
                        else:
                            print(f"  Received other message: {data.get('type')}")
                            
                    except asyncio.TimeoutError:
                        timeout -= 1
                        if timeout % 10 == 0:
                            print(f"  Still waiting... ({timeout}s remaining)")
                        continue
                        
            except Exception as e:
                print(f"✗ Error while waiting for metrics: {e}")
                return False
            
            if not metrics_received:
                print("\n⚠ No metrics_update message received within timeout period")
                print("  This could mean:")
                print("  1. No miners are currently being polled")
                print("  2. Metrics save interval hasn't elapsed yet")
                print("  3. WebSocket broadcasting is not working")
                return False
            
            return True
                
    except ConnectionRefusedError:
        print("✗ Connection refused - is the backend server running on port 8000?")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print("=" * 60)
    print("Testing WebSocket Metrics Broadcasting")
    print("=" * 60)
    print()
    
    success = await test_metrics_broadcast()
    
    print()
    print("=" * 60)
    if success:
        print("✓ Metrics broadcast test PASSED!")
        print("=" * 60)
        sys.exit(0)
    else:
        print("✗ Metrics broadcast test FAILED!")
        print("=" * 60)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
