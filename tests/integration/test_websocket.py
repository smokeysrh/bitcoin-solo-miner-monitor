#!/usr/bin/env python3
"""
Simple WebSocket test script to verify the backend is working
"""

import asyncio
import websockets
import json
import sys

async def test_websocket():
    uri = "ws://localhost:8000/ws"
    
    try:
        print(f"Connecting to {uri}...")
        async with websockets.connect(uri) as websocket:
            print("✓ WebSocket connection established!")
            
            # Send a ping message
            ping_message = {
                "type": "ping",
                "timestamp": "2025-01-09T12:00:00Z"
            }
            
            await websocket.send(json.dumps(ping_message))
            print("✓ Ping message sent")
            
            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(response)
                print(f"✓ Received response: {data}")
                
                if data.get("type") == "connection_established":
                    print("✓ Connection properly established")
                    return True
                    
            except asyncio.TimeoutError:
                print("⚠ No response received within 5 seconds")
                return False
                
    except ConnectionRefusedError:
        print("✗ Connection refused - is the backend server running on port 8000?")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

async def main():
    print("Testing WebSocket connection to backend...")
    success = await test_websocket()
    
    if success:
        print("\n✓ WebSocket test passed!")
        sys.exit(0)
    else:
        print("\n✗ WebSocket test failed!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())