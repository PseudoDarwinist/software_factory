#!/usr/bin/env python3
"""
Test script to directly call the work order generation API endpoint
"""

import requests
import json

# The spec and project IDs from your logs
spec_id = "spec_slack_C095S2NQQMV_1754978303.169829_f2419fa2"
project_id = "project_1753319732860_xct3cc4z5"

# API endpoint
url = f"http://localhost:8000/api/specs/{spec_id}/generate-work-orders"

# Request payload
payload = {
    "projectId": project_id
}

print(f"Testing work order generation API...")
print(f"URL: {url}")
print(f"Payload: {json.dumps(payload, indent=2)}")
print("-" * 50)

try:
    # Make the POST request
    response = requests.post(url, json=payload, stream=True)
    
    print(f"Response Status: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print("-" * 50)
    
    if response.status_code == 200:
        print("Streaming response:")
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                print(decoded_line)
                
                # Try to parse SSE data
                if decoded_line.startswith('data: '):
                    try:
                        data = json.loads(decoded_line[6:])
                        if data.get('type') == 'generation_error':
                            print(f"\n❌ Error: {data.get('error')}")
                            break
                        elif data.get('type') == 'generation_completed':
                            print(f"\n✅ Generation completed successfully!")
                            break
                    except json.JSONDecodeError:
                        pass
    else:
        print(f"Error Response: {response.text}")
        
except requests.exceptions.RequestException as e:
    print(f"Request failed: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
