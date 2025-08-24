#!/usr/bin/env python3
"""
Test the real streaming endpoint like the frontend does
"""

import sys
import os
import requests
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_real_endpoint():
    """Test the real streaming endpoint"""
    print("🧪 Testing real streaming endpoint...")
    
    # The exact request the frontend is making
    url = "http://localhost:8000/api/specs/spec_slack_C095S2NQQMV_1755327474.872009_22cea1a2/generate-work-orders"
    payload = {
        "projectId": "project_1753319732860_xct3cc4z5"
    }
    
    print(f"🚀 Making POST request to: {url}")
    print(f"📦 Payload: {payload}")
    
    try:
        # Make the request with streaming
        response = requests.post(
            url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            stream=True,
            timeout=30
        )
        
        print(f"📊 Response status: {response.status_code}")
        print(f"📋 Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("✅ Request successful, reading stream...")
            
            chunk_count = 0
            for line in response.iter_lines():
                if line:
                    chunk_count += 1
                    line_str = line.decode('utf-8')
                    print(f"📦 Chunk {chunk_count}: {line_str}")
                    
                    # Parse SSE data
                    if line_str.startswith('data: '):
                        try:
                            data = json.loads(line_str[6:])  # Remove 'data: ' prefix
                            print(f"   📄 Parsed: {data}")
                        except json.JSONDecodeError:
                            print(f"   ❌ Failed to parse JSON: {line_str}")
                    
                    # Stop after 5 chunks to avoid infinite loop
                    if chunk_count >= 5:
                        break
            
            print(f"✅ Received {chunk_count} chunks")
            
        else:
            print(f"❌ Request failed with status {response.status_code}")
            print(f"📄 Response text: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection error - is the server running on localhost:8000?")
    except Exception as e:
        print(f"❌ Error making request: {e}")
        import traceback
        traceback.print_exc()
    
    print("✅ Test completed")

if __name__ == "__main__":
    test_real_endpoint()