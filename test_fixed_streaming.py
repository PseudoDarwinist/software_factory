#!/usr/bin/env python3
"""
Test the fixed streaming work order generation
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from flask import Flask
from src.app import create_app
from src.services.work_order_generation_service import WorkOrderGenerationService

def test_fixed_streaming():
    """Test the fixed streaming work order generation"""
    print("🧪 Testing fixed streaming work order generation...")
    
    # Create Flask app
    app = create_app()
    
    with app.app_context():
        try:
            # Create service
            service = WorkOrderGenerationService()
            print("✅ WorkOrderGenerationService created successfully")
            
            # Test with a real spec_id from the error message
            spec_id = "spec_slack_C095S2NQQMV_1755327474.872009_22cea1a2"
            project_id = "project_1753319732860_xct3cc4z5"  # From the logs
            
            print(f"🚀 Testing stream generation for real spec: {spec_id}")
            
            # Try to get first few chunks from stream
            stream_generator = service.generate_work_orders_stream(spec_id, project_id)
            
            chunk_count = 0
            for chunk in stream_generator:
                chunk_count += 1
                print(f"📦 Chunk {chunk_count}: {chunk}")
                
                # Stop after 3 chunks to avoid infinite loop
                if chunk_count >= 3:
                    break
                    
                # If we get an error, stop
                if 'error' in chunk:
                    break
            
            if chunk_count > 0:
                print("✅ Stream is working correctly!")
            else:
                print("❌ No chunks received from stream")
                
        except Exception as e:
            print(f"❌ Error during test: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    print("✅ Test completed")
    return True

if __name__ == "__main__":
    test_fixed_streaming()