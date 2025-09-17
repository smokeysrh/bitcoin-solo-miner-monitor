#!/usr/bin/env python3
"""
Script to call the reload-miners endpoint
"""

import os
import requests
from config.app_config import HOST, PORT, CONNECTION_TIMEOUT, RETRY_ATTEMPTS, RETRY_DELAY
import time

def reload_miners():
    """Call the reload-miners endpoint"""
    
    print("🔄 Reloading miners from database...")
    
    # Use configurable host and port from app config
    # Allow override via environment variables for different deployment scenarios
    api_host = os.getenv("API_HOST", HOST)
    api_port = int(os.getenv("API_PORT", PORT))
    
    # Construct the URL using configurable endpoints
    api_url = f"http://{api_host}:{api_port}/api/reload-miners"
    
    print(f"Connecting to: {api_url}")
    
    # Use production-appropriate timeout and retry settings
    for attempt in range(RETRY_ATTEMPTS):
        try:
            response = requests.post(
                api_url,
                timeout=CONNECTION_TIMEOUT,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'MinerReloadScript/1.0'
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ {result.get('message', 'Success')}")
                print(f"Miners count: {result.get('miners_count', 0)}")
                return
            else:
                print(f"❌ Error: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"Error: {error_data}")
                except:
                    print(f"Error text: {response.text}")
                
                # Don't retry on client errors (4xx)
                if 400 <= response.status_code < 500:
                    return
                    
        except requests.exceptions.ConnectTimeout:
            print(f"⏱️ Connection timeout (attempt {attempt + 1}/{RETRY_ATTEMPTS})")
        except requests.exceptions.ConnectionError as e:
            print(f"🔌 Connection error (attempt {attempt + 1}/{RETRY_ATTEMPTS}): {e}")
        except requests.exceptions.Timeout:
            print(f"⏱️ Request timeout (attempt {attempt + 1}/{RETRY_ATTEMPTS})")
        except Exception as e:
            print(f"❌ Exception (attempt {attempt + 1}/{RETRY_ATTEMPTS}): {e}")
        
        # Wait before retrying (except on last attempt)
        if attempt < RETRY_ATTEMPTS - 1:
            print(f"Waiting {RETRY_DELAY} seconds before retry...")
            time.sleep(RETRY_DELAY)
    
    print(f"❌ Failed to reload miners after {RETRY_ATTEMPTS} attempts")

if __name__ == "__main__":
    reload_miners()