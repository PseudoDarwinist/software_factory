#!/usr/bin/env python3
"""
Simple debug script to test PRD generation format without hanging
"""

import sys
import os
sys.path.append('src')

def test_simple_generation():
    """Test what format is being generated"""
    
    try:
        from services.prd_generation_orchestrator import ProductSpecGenerator
        from services.ai_broker import AIRequest, AIResponse
        from unittest.mock import Mock
        
        # Create generator
        generator = ProductSpecGenerator()
        
        # Mock AI broker to avoid hanging
        mock_ai_broker = Mock()
        
        # Create a mock response that returns JSON (the problem we're seeing)
        mock_response = AIResponse(
            request_id="test-123",
            success=True,
            content='{"sections": {"introduction": "This is a test &amp; example", "requirements": "User can &lt;create&gt; tasks"}}',
            model_used="test-model",
            provider="test",
            processing_time=1.0,
            tokens_used=100,
            cost_estimate=0.01
        )
        
        mock_ai_broker.submit_request_sync.return_value = mock_response
        generator.ai_broker = mock_ai_broker
        
        # Test context
        context = {
            'upload_data': {'files': []},
            'template': {'sections': []},
            'conversation_context': 'Test conversation'
        }
        
        print("Testing ProductSpecGenerator...")
        result = generator.generate(context)
        
        print(f"Success: {result.success}")
        print(f"Content type: {type(result.content)}")
        print(f"Content: {result.content[:200]}...")
        
        # Check if content is JSON
        if result.content.strip().startswith('{'):
            print("❌ PROBLEM: Generator returned JSON instead of markdown!")
            
            # Check for HTML entities
            if '&amp;' in result.content or '&lt;' in result.content:
                print("❌ PROBLEM: Content contains HTML entities!")
            
        elif result.content.strip().startswith('#'):
            print("✓ GOOD: Generator returned markdown!")
        
        return result.content
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    test_simple_generation()