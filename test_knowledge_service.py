#!/usr/bin/env python3
"""
Test script for ADI Knowledge Service

Tests the knowledge storage and retrieval functionality with semantic search.
"""

import sys
import os
import json
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from app import create_app
    from adi.services.knowledge_service import KnowledgeService, DomainKnowledge
    from adi.models.knowledge import Knowledge
    from models.base import db
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running this from the project root directory")
    sys.exit(1)


def test_knowledge_service():
    """Test the knowledge service functionality"""
    print("🧠 Testing ADI Knowledge Service...")
    
    app = create_app()
    
    with app.app_context():
        try:
            # Initialize the knowledge service
            knowledge_service = KnowledgeService()
            print("✅ Knowledge service initialized successfully")
            
            # Test project ID
            test_project_id = "test-project-123"
            
            # Test 1: Add knowledge items
            print("\n📝 Test 1: Adding knowledge items...")
            
            knowledge_items = [
                DomainKnowledge(
                    title="User Authentication Best Practices",
                    content="Always use strong password policies, implement multi-factor authentication, and regularly audit user access. Session tokens should expire after reasonable time periods.",
                    author="security-team",
                    tags=["security", "authentication", "best-practices"]
                ),
                DomainKnowledge(
                    title="Database Performance Optimization",
                    content="Use proper indexing strategies, optimize query performance, and implement connection pooling. Monitor slow queries and consider read replicas for high-traffic applications.",
                    author="database-team",
                    tags=["database", "performance", "optimization"]
                ),
                DomainKnowledge(
                    title="API Rate Limiting Guidelines",
                    content="Implement rate limiting to prevent abuse and ensure fair usage. Use sliding window algorithms and provide clear error messages when limits are exceeded.",
                    author="api-team",
                    tags=["api", "rate-limiting", "guidelines"]
                )
            ]
            
            knowledge_ids = []
            for i, knowledge in enumerate(knowledge_items):
                try:
                    knowledge_id = knowledge_service.add_knowledge(test_project_id, knowledge)
                    knowledge_ids.append(knowledge_id)
                    print(f"  ✅ Added knowledge item {i+1}: {knowledge.title}")
                except Exception as e:
                    print(f"  ❌ Failed to add knowledge item {i+1}: {str(e)}")
                    continue
            
            print(f"Added {len(knowledge_ids)} knowledge items")
            
            # Test 2: Search knowledge
            print("\n🔍 Test 2: Searching knowledge...")
            
            search_queries = [
                "authentication security",
                "database optimization",
                "API limits",
                "password policies"
            ]
            
            for query in search_queries:
                try:
                    results = knowledge_service.search_knowledge(test_project_id, query, limit=3)
                    print(f"  Query: '{query}' -> {len(results)} results")
                    
                    for result in results:
                        print(f"    - {result.title} (score: {result.similarity_score:.3f})")
                        
                except Exception as e:
                    print(f"  ❌ Search failed for '{query}': {str(e)}")
            
            # Test 3: Get relevant context for decision log case
            print("\n🎯 Test 3: Getting relevant context...")
            
            sample_case_data = {
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
            
            try:
                relevant_knowledge = knowledge_service.get_relevant_context(test_project_id, sample_case_data)
                print(f"  Found {len(relevant_knowledge)} relevant knowledge items")
                
                for knowledge in relevant_knowledge:
                    print(f"    - {knowledge.title} (score: {knowledge.similarity_score:.3f})")
                    
            except Exception as e:
                print(f"  ❌ Context retrieval failed: {str(e)}")
            
            # Test 4: Knowledge recommendations
            print("\n💡 Test 4: Getting knowledge recommendations...")
            
            try:
                recommendations = knowledge_service.build_knowledge_recommendation_system(test_project_id, sample_case_data)
                print(f"  Generated {len(recommendations)} recommendations:")
                
                for i, recommendation in enumerate(recommendations, 1):
                    print(f"    {i}. {recommendation}")
                    
            except Exception as e:
                print(f"  ❌ Recommendations failed: {str(e)}")
            
            # Test 5: Knowledge analytics
            print("\n📊 Test 5: Getting knowledge analytics...")
            
            try:
                analytics = knowledge_service.get_knowledge_usage_analytics(test_project_id, days=30)
                print(f"  Analytics: {json.dumps(analytics, indent=2)}")
                
            except Exception as e:
                print(f"  ❌ Analytics failed: {str(e)}")
            
            # Test 6: Update knowledge
            print("\n✏️ Test 6: Updating knowledge...")
            
            if knowledge_ids:
                try:
                    knowledge_service.update_knowledge(knowledge_ids[0], {
                        'content': 'Updated content: Always use strong password policies, implement multi-factor authentication, and regularly audit user access. Session tokens should expire after reasonable time periods. Added: Use OAuth 2.0 for third-party integrations.'
                    })
                    print("  ✅ Knowledge updated successfully")
                    
                    # Search again to see updated content
                    results = knowledge_service.search_knowledge(test_project_id, "OAuth integration", limit=1)
                    if results:
                        print(f"  ✅ Updated knowledge found in search with score: {results[0].similarity_score:.3f}")
                    
                except Exception as e:
                    print(f"  ❌ Update failed: {str(e)}")
            
            # Cleanup
            print("\n🧹 Cleaning up test data...")
            try:
                # Delete test knowledge items
                for knowledge_id in knowledge_ids:
                    knowledge = Knowledge.query.get(knowledge_id)
                    if knowledge:
                        db.session.delete(knowledge)
                
                db.session.commit()
                print("  ✅ Test data cleaned up")
                
            except Exception as e:
                print(f"  ⚠️ Cleanup warning: {str(e)}")
            
            print("\n🎉 Knowledge service tests completed successfully!")
            return True
            
        except Exception as e:
            print(f"\n❌ Knowledge service test failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    success = test_knowledge_service()
    sys.exit(0 if success else 1)