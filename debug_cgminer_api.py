"""
Debug script to query cgminer API and see what data is actually returned
"""
import socket
import json

def send_cgminer_command(ip, port, command):
    """Send a command to cgminer API and return the response"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((ip, port))
        
        # Prepare command
        payload = {"command": command}
        sock.send(json.dumps(payload).encode('utf-8'))
        
        # Receive response
        response = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk
            if response.endswith(b'\x00'):
                break
        
        sock.close()
        
        # Parse response
        if response:
            response_str = response.decode('utf-8').replace('\x00', '')
            return json.loads(response_str)
        
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

# Test the Avalon Nano 3 miner
ip = "192.168.1.85"
port = 4028

print("=" * 80)
print(f"Testing cgminer API at {ip}:{port}")
print("=" * 80)

# Test different commands
commands = ["summary", "stats", "devs", "pools", "version", "config"]

for cmd in commands:
    print(f"\n{'=' * 80}")
    print(f"Command: {cmd}")
    print("=" * 80)
    response = send_cgminer_command(ip, port, cmd)
    if response:
        print(json.dumps(response, indent=2))
    else:
        print("No response or error")
