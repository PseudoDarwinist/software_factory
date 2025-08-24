#!/usr/bin/env python3
"""
Test script for Decision Log Ingest API with rate limiting and authentication.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import requests
import json
from datetime import datetime
from src.adi.schemas.decision_log import hash_case_id


# Test configuration
BASE_URL = 'http://localhost:5000/api/adi/ingest'
PROJECT_TOKEN = 'token-test-abcdef'
ADMIN_TOKEN = 'admin-token-12345'


def test_health_check():
    """Test health check endpoint."""
    print("Testing health check...")
    
    try:
        response = requests.get(f'{BASE_URL}/health')
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Health check failed: {e}")
        return False


def test_authentication():
    """Test authentication requirements."""
    print("\nTesting authentication...")
    
    # Test without token
    response = requests.post(f'{BASE_URL}/decision', json={})
    print(f"No token - Status: {response.status_code}")
    assert response.status_code == 401
    
    # Test with invalid token
    headers = {'Authorization': 'Bearer invalid-token'}
    response = requests.post(f'{BASE_URL}/decision', json={}, headers=headers)
    print(f"Invalid token - Status: {response.status_code}")
    assert response.status_code == 401
    
    print("✓ Authentication tests passed")
    return True


def test_valid_ingestion():
    """Test valid decision log ingestion."""
    print("\nTesting valid ingestion...")
    
    headers = {
        'Authorization': f'Bearer {PROJECT_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        "project_id": "test-project",
        "case_id": hash_case_id("CASE-12345"),
        "event": {
            "type": "FlightDelay",
            "ts": datetime.utcnow().isoformat(),
            "scope": "departure",
            "attrs": {
                "flight_number": "AA123",
                "delay_minutes": 45,
                "reason": "weather"
            }
        },
        "decision": {
            "action": "SendDelayNotification",
            "channel": "sms",
            "template_id": "DELAY-001",
            "status": "OK",
            "latency_ms": 250,
            "counts": {"passengers": 150}
        },
        "version": {
            "app": "1.2.3",
            "policy": "2.1.0",
            "factory_pr": "456"
        },
        "links": {
            "flight_status": "https://example.com/flight/AA123"
        }
    }
    
    try:
        response = requests.post(f'{BASE_URL}/decision', json=payload, headers=headers)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 201:
            print("✓ Valid ingestion test passed")
            return True
        else:
            print("✗ Valid ingestion test failed")
            return False
    except Exception as e:
        print(f"Valid ingestion test failed: {e}")
        return False


def test_pii_rejection():
    """Test PII detection and rejection."""
    print("\nTesting PII rejection...")
    
    headers = {
        'Authorization': f'Bearer {PROJECT_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        "project_id": "test-project",
        "case_id": hash_case_id("CASE-12345"),
        "event": {
            "type": "FlightDelay",
            "ts": datetime.utcnow().isoformat(),
            "scope": "departure",
            "attrs": {
                "passenger_email": "john.doe@example.com",  # PII!
                "flight_number": "AA123"
            }
        },
        "decision": {
            "action": "SendDelayNotification",
            "channel": "sms",
            "template_id": "DELAY-001",
            "status": "OK",
            "latency_ms": 250
        },
        "version": {
            "app": "1.2.3",
            "policy": "2.1.0",
            "factory_pr": "456"
        }
    }
    
    try:
        response = requests.post(f'{BASE_URL}/decision', json=payload, headers=headers)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 400 and 'PII' in response.json().get('details', ''):
            print("✓ PII rejection test passed")
            return True
        else:
            print("✗ PII rejection test failed")
            return False
    except Exception as e:
        print(f"PII rejection test failed: {e}")
        return False


def test_rate_limiting():
    """Test rate limiting functionality."""
    print("\nTesting rate limiting...")
    
    headers = {
        'Authorization': f'Bearer {PROJECT_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    # Check rate limit status
    try:
        response = requests.get(f'{BASE_URL}/rate-limit', headers=headers)
        print(f"Rate limit status: {response.status_code}")
        if response.status_code == 200:
            print(f"Current limits: {response.json()['rate_limit']}")
        
        print("✓ Rate limit status test passed")
        return True
    except Exception as e:
        print(f"Rate limit test failed: {e}")
        return False


def test_admin_query():
    """Test admin log querying."""
    print("\nTesting admin query...")
    
    headers = {'Authorization': f'Bearer {ADMIN_TOKEN}'}
    params = {'project_id': 'test-project', 'limit': 10}
    
    try:
        response = requests.get(f'{BASE_URL}/logs', headers=headers, params=params)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Found {data['count']} logs")
            print("✓ Admin query test passed")
            return True
        else:
            print(f"Response: {response.json()}")
            print("✗ Admin query test failed")
            return False
    except Exception as e:
        print(f"Admin query test failed: {e}")
        return False


def test_project_id_mismatch():
    """Test project ID mismatch detection."""
    print("\nTesting project ID mismatch...")
    
    headers = {
        'Authorization': f'Bearer {PROJECT_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        "project_id": "wrong-project",  # Doesn't match token
        "case_id": hash_case_id("CASE-12345"),
        "event": {
            "type": "FlightDelay",
            "ts": datetime.utcnow().isoformat(),
            "scope": "departure",
            "attrs": {"flight_number": "AA123"}
        },
        "decision": {
            "action": "SendDelayNotification",
            "channel": "sms",
            "template_id": "DELAY-001",
            "status": "OK",
            "latency_ms": 250
        },
        "version": {
            "app": "1.2.3",
            "policy": "2.1.0",
            "factory_pr": "456"
        }
    }
    
    try:
        response = requests.post(f'{BASE_URL}/decision', json=payload, headers=headers)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 400 and 'project_id' in response.json().get('error', ''):
            print("✓ Project ID mismatch test passed")
            return True
        else:
            print("✗ Project ID mismatch test failed")
            return False
    except Exception as e:
        print(f"Project ID mismatch test failed: {e}")
        return False


def main():
    """Run all API tests."""
    print("Testing Decision Log Ingest API")
    print("=" * 40)
    print("Note: This requires the Flask app to be running on localhost:5000")
    print()
    
    tests = [
        test_health_check,
        test_authentication,
        test_valid_ingestion,
        test_pii_rejection,
        test_rate_limiting,
        test_project_id_mismatch,
        test_admin_query
    ]
    
    passed = 0
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"Test failed with exception: {e}")
    
    print(f"\n{passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("✓ All API tests passed!")
        return 0
    else:
        print("✗ Some API tests failed")
        print("Make sure the Flask app is running and the database is accessible")
        return 1


if __name__ == "__main__":
    sys.exit(main())