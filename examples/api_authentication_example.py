#!/usr/bin/env python3
"""
Example script demonstrating API authentication usage
"""

import requests
import json
import os

# Configuration
API_BASE_URL = "http://localhost:8000/api"
API_KEY = os.getenv("API_KEY", "dev-key-12345")  # Use dev key for testing

def make_authenticated_request(method, endpoint, data=None):
    """Make an authenticated API request"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    url = f"{API_BASE_URL}{endpoint}"
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data)
        elif method.upper() == "PUT":
            response = requests.put(url, headers=headers, json=data)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        return response
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None

def example_public_endpoints():
    """Examples of public endpoints (no authentication required)"""
    print("📖 Public Endpoints (No Authentication Required)")
    print("-" * 50)
    
    # Health check
    response = requests.get(f"{API_BASE_URL}/health")
    if response.status_code == 200:
        print("✅ Health check: OK")
    else:
        print(f"❌ Health check failed: {response.status_code}")
    
    # Get miners (read-only)
    response = requests.get(f"{API_BASE_URL}/miners")
    if response.status_code == 200:
        miners = response.json()
        print(f"✅ Miners list: {len(miners)} miners found")
    else:
        print(f"❌ Get miners failed: {response.status_code}")

def example_protected_endpoints():
    """Examples of protected endpoints (authentication required)"""
    print("\n🔒 Protected Endpoints (Authentication Required)")
    print("-" * 50)
    
    # Try without authentication first
    print("Testing without authentication:")
    response = requests.post(f"{API_BASE_URL}/miners", json={
        "type": "antminer",
        "ip_address": "192.168.1.100",
        "port": 4028,
        "name": "Test Miner"
    })
    if response.status_code == 401:
        print("✅ Correctly rejected without authentication (401)")
    else:
        print(f"⚠️  Unexpected response without auth: {response.status_code}")
    
    # Now try with authentication
    print("\nTesting with authentication:")
    response = make_authenticated_request("POST", "/miners", {
        "type": "antminer",
        "ip_address": "192.168.1.100",
        "port": 4028,
        "name": "Test Miner"
    })
    
    if response:
        if response.status_code == 401:
            print("❌ Authentication failed - check API key")
        elif response.status_code in [200, 201]:
            print("✅ Miner creation request accepted")
        else:
            print(f"⚠️  Request processed but returned: {response.status_code}")
            if response.text:
                print(f"   Response: {response.text[:200]}...")

def example_development_endpoints():
    """Examples of development-only endpoints"""
    print("\n🛠️  Development Endpoints")
    print("-" * 50)
    
    # Set development mode
    os.environ["DEBUG"] = "true"
    os.environ.pop("ENVIRONMENT", None)  # Remove production setting
    
    response = make_authenticated_request("POST", "/reload-miners")
    
    if response:
        if response.status_code == 404:
            print("⚠️  Development endpoint disabled (production mode)")
        elif response.status_code == 401:
            print("❌ Authentication failed for development endpoint")
        elif response.status_code == 200:
            print("✅ Development endpoint accessible")
            result = response.json()
            print(f"   Result: {result.get('message', 'No message')}")
        else:
            print(f"⚠️  Unexpected response: {response.status_code}")

def main():
    """Main example function"""
    print("🔐 API Authentication Examples")
    print("=" * 60)
    print(f"Using API Key: {API_KEY[:10]}..." if len(API_KEY) > 10 else f"Using API Key: {API_KEY}")
    print(f"API Base URL: {API_BASE_URL}")
    print()
    
    # Test public endpoints
    example_public_endpoints()
    
    # Test protected endpoints
    example_protected_endpoints()
    
    # Test development endpoints
    example_development_endpoints()
    
    print("\n" + "=" * 60)
    print("📋 Authentication Summary:")
    print("• Public endpoints: No authentication required")
    print("• Protected endpoints: Require 'Authorization: Bearer <api-key>' header")
    print("• Development endpoints: Require auth + debug mode enabled")
    print("\n💡 Tips:")
    print("• Set API_KEY environment variable for your key")
    print("• Use DEBUG=true for development endpoints")
    print("• Set ENVIRONMENT=production to disable dev endpoints")

if __name__ == "__main__":
    main()