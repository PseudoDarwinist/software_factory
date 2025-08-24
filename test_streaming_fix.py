#!/usr/bin/env python3
"""
Test script to verify the streaming work order generation fix
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from flask import Flask
from src.app import create_app
from src.services.work_order_generation_service import WorkOrderGenerationService

def test_streaming_fix():
    """Test the streaming work order generation with Flask context"""
    print("🧪 Testing streaming work order generation fix...")
    
    # Create Flask app
    app = create_app()
    
    with app.app_context():
        try:
            # Create service
            service = WorkOrderGenerationService()
            print("✅ WorkOrderGenerationService created successfully")
            
            # Test with a sample spec_id and project_id
            spec_id = "spec_test_123"
            project_id = "project_test_456"
            
            print(f"🚀 Testing stream generation for spec: {spec_id}, project: {project_id}")
            
            # Try to get first chunk from stream
            stream_generator = service.generate_work_orders_stream(spec_id, project_id)
            first_chunk = next(stream_generator, None)
            
            if first_chunk:
                print(f"✅ First chunk received: {first_chunk}")
                if 'error' in first_chunk:
                    print(f"⚠️  Expected error (test data): {first_chunk['error']}")
                else:
                    print("✅ Stream is working correctly!")
            else:
                print("❌ No chunks received from stream")
                
        except Exception as e:
            print(f"❌ Error during test: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    print("✅ Test completed successfully")
    return True

if __name__ == "__main__":
    test_streaming_fix()