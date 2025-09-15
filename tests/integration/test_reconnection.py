#!/usr/bin/env python3
"""
Test script to simulate page refresh and verify WebSocket reconnection
"""

import asyncio
import websockets
import json
import time

async def test_reconnection():
    uri = "ws://localhost:8000/ws"
    
    print("=== Testing WebSocket Reconnection ===")
    
    # First connection
    print("\n1. Establishing initial connection...")
    try:
        async with websockets.connect(uri) as websocket:
            print("✓ Initial connection established")
            
            # Wait for connection established message
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(response)
            client_id = data.get("client_id", "unknown")
            print(f"✓ Client ID: {client_id}")
            
            # Send a test message
            await websocket.send(json.dumps({"type": "ping", "timestamp": "test"}))
            print("✓ Sent ping message")
            
            # Simulate connection close (like page refresh)
            print("\n2. Simulating page refresh (closing connection)...")
            await websocket.close()
            print("✓ Connection closed")
            
    except Exception as e:
        print(f"✗ Error in first connection: {e}")
        return False
    
    # Wait a moment
    print("\n3. Waiting 2 seconds before reconnection...")
    await asyncio.sleep(2)
    
    # Second connection (simulating reconnection)
    print("\n4. Testing reconnection...")
    try:
        async with websockets.connect(uri) as websocket:
            print("✓ Reconnection successful")
            
            # Wait for connection established message
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(response)
            new_client_id = data.get("client_id", "unknown")
            print(f"✓ New Client ID: {new_client_id}")
            
            # Send another test message
            await websocket.send(json.dumps({"type": "ping", "timestamp": "test2"}))
            print("✓ Sent ping message after reconnection")
            
            return True
            
    except Exception as e:
        print(f"✗ Error in reconnection: {e}")
        return False

async def main():
    success = await test_reconnection()
    
    if success:
        print("\n✓ Reconnection test passed!")
        print("The WebSocket server properly handles connection/reconnection cycles.")
    else:
        print("\n✗ Reconnection test failed!")
        
    return success

if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)