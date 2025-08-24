#!/usr/bin/env python3
"""
Test script for ADI Knowledge API

Tests the knowledge API endpoints directly.
"""

import requests
import json
import sys

# Configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/adi/knowledge"

def test_knowledge_api():
    """Test the knowledge API endpoints"""
    print("🧠 Testing ADI Knowledge API...")
    
    # Test project ID
    test_project_id = "test-project-api"
    
    # Test 1: Health check
    print("\n❤️ Test 1: Health check...")
    try:
        response = requests.get(f"{API_BASE}/health")
        if response.status_code == 200:
            health_data = response.json()
            print(f"  ✅ Health check passed: {health_data['status']}")
            print(f"  Vector service: {health_data.get('vector_service', 'unknown')}")
        else:
            print(f"  ❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"  ❌ Health check error: {str(e)}")
        return False
    
    # Test 2: Create knowledge items
    print("\n📝 Test 2: Creating knowledge items...")
    
    knowledge_items = [
        {
            "project_id": test_project_id,
            "title": "User Authentication Best Practices",
            "content": "Always use strong password policies, implement multi-factor authentication, and regularly audit user access. Session tokens should expire after reasonable time periods.",
            "author": "security-team",
            "tags": ["security", "authentication", "best-practices"]
        },
        {
            "project_id": test_project_id,
            "title": "Database Performance Optimization",
            "content": "Use proper indexing strategies, optimize query performance, and implement connection pooling. Monitor slow queries and consider read replicas for high-traffic applications.",
            "author": "database-team",
            "tags": ["database", "performance", "optimization"]
        },
        {
            "project_id": test_project_id,
            "title": "API Rate Limiting Guidelines",
            "content": "Implement rate limiting to prevent abuse and ensure fair usage. Use sliding window algorithms and provide clear error messages when limits are exceeded.",
            "author": "api-team",
            "tags": ["api", "rate-limiting", "guidelines"]
        }
    ]
    
    created_ids = []
    for i, knowledge_data in enumerate(knowledge_items):
        try:
            response = requests.post(API_BASE, json=knowledge_data)
            if response.status_code == 201:
                created_knowledge = response.json()
                created_ids.append(created_knowledge['id'])
                print(f"  ✅ Created knowledge item {i+1}: {knowledge_data['title']}")
            else:
                print(f"  ❌ Failed to create knowledge item {i+1}: {response.status_code}")
                print(f"      Response: {response.text}")
        except Exception as e:
            print(f"  ❌ Error creating knowledge item {i+1}: {str(e)}")
    
    print(f"Created {len(created_ids)} knowledge items")
    
    # Test 3: List knowledge items
    print("\n📋 Test 3: Listing knowledge items...")
    try:
        response = requests.get(API_BASE, params={"project_id": test_project_id})
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ Found {data['total_count']} knowledge items")
            for item in data['knowledge']:
                print(f"    - {item['title']} (v{item['version']})")
        else:
            print(f"  ❌ Failed to list knowledge: {response.status_code}")
    except Exception as e:
        print(f"  ❌ Error listing knowledge: {str(e)}")
    
    # Test 4: Search knowledge
    print("\n🔍 Test 4: Searching knowledge...")
    
    search_queries = [
        "authentication security",
        "database optimization",
        "API limits",
        "password policies"
    ]
    
    for query in search_queries:
        try:
            response = requests.get(f"{API_BASE}/search", params={
                "project_id": test_project_id,
                "q": query,
                "limit": 3
            })
            if response.status_code == 200:
                data = response.json()
                print(f"  Query: '{query}' -> {data['count']} results")
                for result in data['results']:
                    score = result.get('similarity_score', 'N/A')
                    print(f"    - {result['title']} (score: {score})")
            else:
                print(f"  ❌ Search failed for '{query}': {response.status_code}")
        except Exception as e:
            print(f"  ❌ Search error for '{query}': {str(e)}")
    
    # Test 5: Get relevant context
    print("\n🎯 Test 5: Getting relevant context...")
    
    sample_case_data = {
        "project_id": test_project_id,
        "case_data": {
            "event": {
                "type": "user_login_attempt",
                "attrs": {
                    "user_id": "user123",
                    "ip_address": "192.168.1.100",
                    "failed_attempts": 3
                }
            },
            "decision": {
                "action": "block_user",
                "template_id": "security_template",
                "status": "approved"
            }
        }
    }
    
    try:
        response = requests.post(f"{API_BASE}/context", json=sample_case_data)
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ Found {data['count']} relevant knowledge items")
            for item in data['relevant_knowledge']:
                score = item.get('similarity_score', 'N/A')
                print(f"    - {item['title']} (score: {score})")
        else:
            print(f"  ❌ Context retrieval failed: {response.status_code}")
            print(f"      Response: {response.text}")
    except Exception as e:
        print(f"  ❌ Context retrieval error: {str(e)}")
    
    # Test 6: Get recommendations
    print("\n💡 Test 6: Getting recommendations...")
    
    try:
        response = requests.post(f"{API_BASE}/recommendations", json=sample_case_data)
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ Generated {data['count']} recommendations:")
            for i, recommendation in enumerate(data['recommendations'], 1):
                print(f"    {i}. {recommendation}")
        else:
            print(f"  ❌ Recommendations failed: {response.status_code}")
            print(f"      Response: {response.text}")
    except Exception as e:
        print(f"  ❌ Recommendations error: {str(e)}")
    
    # Test 7: Get analytics
    print("\n📊 Test 7: Getting analytics...")
    
    try:
        response = requests.get(f"{API_BASE}/analytics", params={
            "project_id": test_project_id,
            "days": 30
        })
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ Analytics: {json.dumps(data, indent=2)}")
        else:
            print(f"  ❌ Analytics failed: {response.status_code}")
    except Exception as e:
        print(f"  ❌ Analytics error: {str(e)}")
    
    # Test 8: Update knowledge
    print("\n✏️ Test 8: Updating knowledge...")
    
    if created_ids:
        try:
            update_data = {
                "content": "Updated content: Always use strong password policies, implement multi-factor authentication, and regularly audit user access. Session tokens should expire after reasonable time periods. Added: Use OAuth 2.0 for third-party integrations."
            }
            response = requests.put(f"{API_BASE}/{created_ids[0]}", json=update_data)
            if response.status_code == 200:
                updated_knowledge = response.json()
                print(f"  ✅ Knowledge updated to version {updated_knowledge['version']}")
            else:
                print(f"  ❌ Update failed: {response.status_code}")
        except Exception as e:
            print(f"  ❌ Update error: {str(e)}")
    
    # Cleanup
    print("\n🧹 Cleaning up test data...")
    cleanup_count = 0
    for knowledge_id in created_ids:
        try:
            response = requests.delete(f"{API_BASE}/{knowledge_id}")
            if response.status_code == 200:
                cleanup_count += 1
        except Exception as e:
            print(f"  ⚠️ Cleanup warning for {knowledge_id}: {str(e)}")
    
    print(f"  ✅ Cleaned up {cleanup_count} knowledge items")
    
    print("\n🎉 Knowledge API tests completed!")
    return True


if __name__ == "__main__":
    print("Make sure the Flask application is running on http://localhost:8000")
    print("You can start it with: python src/app.py")
    print()
    
    success = test_knowledge_api()
    sys.exit(0 if success else 1)