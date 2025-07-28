#!/usr/bin/env python3
"""
Diagnostic script to understand what's causing the 500 error
"""

import requests
import json
import time

def diagnose_server_issue():
    """Diagnose what's causing the 500 error"""
    base_url = "http://localhost:8000"
    
    print("🔍 Diagnosing Server Issue")
    print("=" * 30)
    
    # Test 1: Basic server health
    print("1. Testing basic server health...")
    try:
        response = requests.get(f"{base_url}/api/health", timeout=5)
        print(f"Health check: {response.status_code}")
        if response.status_code == 200:
            print("✅ Server is responding")
        else:
            print("❌ Server health check failed")
    except Exception as e:
        print(f"❌ Health check error: {e}")
    
    # Test 2: Basic task list
    print("\n2. Testing task list endpoint...")
    try:
        response = requests.get(f"{base_url}/api/tasks", timeout=10)
        print(f"Task list: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Task list working - {data.get('total', 0)} tasks")
        else:
            print(f"❌ Task list failed: {response.status_code}")
            print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Task list error: {e}")
    
    # Test 3: Try to get a specific task
    print("\n3. Testing specific task endpoint...")
    task_id = "spec_slack_C095S2NQQMV_1753443716.674199_ab4f9ab7_1"
    try:
        response = requests.get(f"{base_url}/api/tasks/{task_id}", timeout=10)
        print(f"Specific task: {response.status_code}")
        if response.status_code == 200:
            print("✅ Specific task endpoint working")
        elif response.status_code == 500:
            print("❌ 500 Internal Server Error on specific task")
            print("This suggests a database or model issue")
            print(f"Response: {response.text[:200]}")
        else:
            print(f"❌ Unexpected status: {response.status_code}")
            print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Specific task error: {e}")
    
    # Test 4: Try starting a task to see immediate response
    print("\n4. Testing task start (to see immediate logs)...")
    payload = {
        "agentId": "feature-builder",
        "contextOptions": {"spec_files": True},
        "branchName": "feature/diagnostic-test",
        "baseBranch": "main"
    }
    
    try:
        response = requests.post(
            f"{base_url}/api/tasks/{task_id}/start",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        print(f"Task start: {response.status_code}")
        if response.status_code == 202:
            print("✅ Task start working")
        else:
            print(f"❌ Task start failed: {response.status_code}")
            print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Task start error: {e}")

def main():
    """Main diagnostic function"""
    print("🔧 Server Issue Diagnosis")
    print("=" * 40)
    
    diagnose_server_issue()
    
    print("\n" + "=" * 40)
    print("💡 Next Steps:")
    print("1. Check Flask server logs for detailed error messages")
    print("2. Look for database connection issues")
    print("3. Check if any recent code changes broke the task model")
    print("4. Verify all database migrations were applied correctly")

if __name__ == "__main__":
    main()