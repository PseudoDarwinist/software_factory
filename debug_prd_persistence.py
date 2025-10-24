#!/usr/bin/env python3
"""
DEBUG SCRIPT: PRD Persistence Issue
Test the complete save/load flow to identify why persistence is failing
"""
import requests
import json
import sys
import time

BASE_URL = "http://localhost:8000"
TEST_SESSION_ID = "debug-test-session"

def test_api_endpoints():
    """Test if all required API endpoints are accessible"""
    print("🔍 Testing API endpoints...")
    
    # Test server health
    try:
        response = requests.get(f"{BASE_URL}/api/system/health", timeout=5)
        print(f"✅ Server health: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Server not accessible: {e}")
        return False
    
    return True

def test_save_prd_blocks():
    """Test saving PRD blocks to database"""
    print(f"\n💾 Testing PRD block save for session: {TEST_SESSION_ID}")
    
    test_blocks = [
        {
            "type": "header",
            "data": {
                "text": "Test PRD Document",
                "level": 1
            }
        },
        {
            "type": "paragraph", 
            "data": {
                "text": "This is a test PRD document created for debugging persistence issues."
            }
        },
        {
            "type": "list",
            "data": {
                "style": "unordered",
                "items": [
                    "Test requirement 1",
                    "Test requirement 2", 
                    "Test requirement 3"
                ]
            }
        }
    ]
    
    metadata = {
        "title": "Debug Test PRD",
        "lastModified": "2024-01-01T12:00:00Z",
        "source": "ai_generation"
    }
    
    payload = {
        "blocks": test_blocks,
        "metadata": metadata
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/prd-editor/save-blocks/{TEST_SESSION_ID}",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"📤 Save response code: {response.status_code}")
        print(f"📤 Save response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print(f"✅ Save successful! PRD ID: {result.get('data', {}).get('prdId')}")
                return True
            else:
                print(f"❌ Save failed: {result.get('error', 'Unknown error')}")
                return False
        else:
            print(f"❌ Save failed with HTTP {response.status_code}: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Save request failed: {e}")
        return False

def test_load_prd_content():
    """Test loading PRD content from database"""
    print(f"\n📂 Testing PRD content load for session: {TEST_SESSION_ID}")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/prd-editor/{TEST_SESSION_ID}",
            timeout=10
        )
        
        print(f"📥 Load response code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"📥 Load response: {json.dumps(result, indent=2)}")
            
            # Check if blocks are present
            data = result.get('data', {})
            blocks = data.get('blocks', [])
            
            if blocks:
                print(f"✅ Load successful! Found {len(blocks)} blocks")
                print(f"🎯 First block: {blocks[0]}")
                return True
            else:
                print("❌ Load successful but no blocks found!")
                return False
        else:
            print(f"❌ Load failed with HTTP {response.status_code}: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Load request failed: {e}")
        return False

def test_database_direct():
    """Test database operations directly"""
    print(f"\n🗄️ Testing direct database access...")
    
    try:
        # Import here to ensure path is correct
        import sys
        import os
        
        # Add project root to path
        project_root = os.path.abspath(os.path.dirname(__file__))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
            
        from src.models import PRD, db
        from src.app import create_app
        
        app = create_app()
        with app.app_context():
            # Check if PRD exists for our test session
            prds = PRD.query.filter_by(session_id=TEST_SESSION_ID).all()
            print(f"📊 Found {len(prds)} PRD records for session {TEST_SESSION_ID}")
            
            if prds:
                for prd in prds:
                    print(f"🔍 PRD {prd.id}: title='{prd.title}', summary length={len(prd.summary or '')}")
                    
                    # Check if summary contains block_document
                    if prd.summary:
                        try:
                            summary_data = json.loads(prd.summary)
                            blocks = summary_data.get('block_document')
                            if blocks:
                                print(f"✅ Found {len(blocks)} persisted blocks in summary")
                            else:
                                print("❌ No block_document found in summary")
                                print(f"Summary keys: {list(summary_data.keys())}")
                        except json.JSONDecodeError:
                            print("❌ Summary is not valid JSON")
                    else:
                        print("❌ PRD summary is empty")
            else:
                print("❌ No PRD records found for test session")
                
        return len(prds) > 0
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_complete_test():
    """Run complete persistence test"""
    print("🚀 DEBUG: PRD Persistence Issue Analysis")
    print("=" * 50)
    
    # Step 1: Test API endpoints
    if not test_api_endpoints():
        print("❌ Server not accessible. Please start the Flask server first.")
        sys.exit(1)
    
    # Step 2: Test save operation
    save_success = test_save_prd_blocks()
    
    # Wait a moment for database writes
    if save_success:
        print("\n⏳ Waiting 2 seconds for database write...")
        time.sleep(2)
    
    # Step 3: Test load operation
    load_success = test_load_prd_content()
    
    # Step 4: Test database directly
    db_success = test_database_direct()
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 TEST SUMMARY:")
    print(f"✅ Save API: {'PASS' if save_success else 'FAIL'}")
    print(f"✅ Load API: {'PASS' if load_success else 'FAIL'}")  
    print(f"✅ Database: {'PASS' if db_success else 'FAIL'}")
    
    if save_success and load_success and db_success:
        print("\n🎉 All tests PASSED! Persistence should be working.")
    else:
        print("\n❌ Some tests FAILED. Persistence issue identified.")
        
    return save_success and load_success and db_success

if __name__ == "__main__":
    run_complete_test()