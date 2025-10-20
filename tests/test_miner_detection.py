"""
Test script to directly check if a specific IP can be detected as a miner.
This bypasses the full network scan to isolate the detection logic.
"""

import asyncio
import sys
sys.path.insert(0, 'src')

from backend.models.miner_factory import MinerFactory

async def test_single_ip(ip_address, ports=None):
    """Test miner detection for a single IP."""
    if ports is None:
        ports = [80, 4028, 8332, 18332, 8333, 18333, 8080]
    
    print(f"\n{'='*60}")
    print(f"Testing miner detection for: {ip_address}")
    print(f"Ports to check: {ports}")
    print(f"{'='*60}\n")
    
    # First, check which ports are open
    print("Step 1: Checking for open ports...")
    open_ports = []
    
    for port in ports:
        try:
            print(f"  Checking port {port}...", end=" ")
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip_address, port),
                timeout=2.0
            )
            writer.close()
            await writer.wait_closed()
            print(f"✓ OPEN")
            open_ports.append(port)
        except asyncio.TimeoutError:
            print(f"✗ Timeout")
        except ConnectionRefusedError:
            print(f"✗ Connection refused")
        except OSError as e:
            print(f"✗ OS Error: {e}")
        except Exception as e:
            print(f"✗ Error: {e}")
    
    if not open_ports:
        print(f"\n❌ No open ports found on {ip_address}")
        return None
    
    print(f"\n✓ Found {len(open_ports)} open port(s): {open_ports}")
    
    # Now try to detect miner type
    print(f"\nStep 2: Attempting miner type detection...")
    try:
        result = await asyncio.wait_for(
            MinerFactory.detect_miner_type(ip_address, open_ports),
            timeout=10.0
        )
        
        if result:
            print(f"\n✓ MINER DETECTED!")
            print(f"  Type: {result.get('type', 'Unknown')}")
            print(f"  Model: {result.get('model', 'Unknown')}")
            print(f"  IP: {result.get('ip_address', 'Unknown')}")
            print(f"  Full result: {result}")
            return result
        else:
            print(f"\n❌ No miner detected (detection returned None)")
            return None
            
    except asyncio.TimeoutError:
        print(f"\n❌ Miner detection timed out after 10 seconds")
        return None
    except Exception as e:
        print(f"\n❌ Error during miner detection: {e}")
        import traceback
        traceback.print_exc()
        return None

async def main():
    """Main test function."""
    # Test the known miner IP
    target_ip = "192.168.1.156"
    
    print("\n" + "="*60)
    print("MINER DETECTION TEST")
    print("="*60)
    
    result = await test_single_ip(target_ip)
    
    print("\n" + "="*60)
    if result:
        print("TEST RESULT: ✓ SUCCESS - Miner detected")
    else:
        print("TEST RESULT: ✗ FAILED - No miner detected")
    print("="*60 + "\n")
    
    # Also test a few IPs around it to compare
    print("\nTesting nearby IPs for comparison...")
    for ip_suffix in [155, 157]:
        ip = f"192.168.1.{ip_suffix}"
        print(f"\n--- Testing {ip} ---")
        await test_single_ip(ip)

if __name__ == "__main__":
    asyncio.run(main())
