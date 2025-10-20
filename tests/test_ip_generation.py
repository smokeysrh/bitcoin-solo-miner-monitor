"""
Test script to verify IP address generation logic.
This will help us understand if IPs are being skipped during generation.
"""

import ipaddress

def test_cidr_generation(network_cidr):
    """Test CIDR notation IP generation."""
    print(f"\n=== Testing CIDR: {network_cidr} ===")
    network_obj = ipaddress.ip_network(network_cidr)
    hosts = list(network_obj.hosts())
    
    print(f"Total hosts: {len(hosts)}")
    print(f"First 10 hosts: {[str(h) for h in hosts[:10]]}")
    print(f"Last 10 hosts: {[str(h) for h in hosts[-10:]]}")
    
    # Check if .156 is in the list
    target_ip = "192.168.1.156"
    if any(str(h) == target_ip for h in hosts):
        print(f"✓ {target_ip} IS in the generated list")
        # Find its position
        for i, h in enumerate(hosts):
            if str(h) == target_ip:
                print(f"  Position: {i+1}/{len(hosts)}")
                print(f"  Previous: {hosts[i-1] if i > 0 else 'N/A'}")
                print(f"  Next: {hosts[i+1] if i < len(hosts)-1 else 'N/A'}")
                break
    else:
        print(f"✗ {target_ip} is NOT in the generated list")
    
    # Check the range around .156
    print(f"\nIPs around .156:")
    for h in hosts:
        ip_str = str(h)
        if ip_str.endswith('.150') or ip_str.endswith('.155') or ip_str.endswith('.156') or ip_str.endswith('.157') or ip_str.endswith('.160') or ip_str.endswith('.163'):
            print(f"  {ip_str}")

def test_range_generation(start_ip, end_ip):
    """Test IP range generation."""
    print(f"\n=== Testing Range: {start_ip} - {end_ip} ===")
    
    start_addr = ipaddress.ip_address(start_ip)
    end_addr = ipaddress.ip_address(end_ip)
    
    hosts = []
    current = int(start_addr)
    end = int(end_addr)
    
    while current <= end:
        hosts.append(ipaddress.ip_address(current))
        current += 1
    
    print(f"Total hosts: {len(hosts)}")
    print(f"All hosts: {[str(h) for h in hosts]}")
    
    # Check if .156 is in the list
    target_ip = "192.168.1.156"
    if any(str(h) == target_ip for h in hosts):
        print(f"✓ {target_ip} IS in the generated list")
    else:
        print(f"✗ {target_ip} is NOT in the generated list")

if __name__ == "__main__":
    # Test common network ranges
    test_cidr_generation("192.168.1.0/24")
    test_cidr_generation("192.168.1.0/28")
    test_cidr_generation("192.168.1.144/28")  # Range that includes .156
    
    # Test range format
    test_range_generation("192.168.1.150", "192.168.1.160")
    test_range_generation("192.168.1.156", "192.168.1.156")  # Single IP
