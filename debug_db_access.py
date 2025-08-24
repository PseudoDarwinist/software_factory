#!/usr/bin/env python3
"""
Debug script to test database access patterns
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from flask import Flask
from src.app import create_app

def test_db_access():
    """Test different ways to access the database"""
    print("🧪 Testing database access patterns...")
    
    # Create Flask app
    app = create_app()
    
    with app.app_context():
        try:
            # Test 1: Direct model query (how other endpoints do it)
            print("\n1. Testing direct model query...")
            try:
                from src.models.mission_control_project import MissionControlProject
                project = MissionControlProject.query.first()
                print(f"✅ Direct query works: Found {MissionControlProject.query.count()} projects")
            except Exception as e:
                print(f"❌ Direct query failed: {e}")
            
            # Test 2: Flask-SQLAlchemy extension access
            print("\n2. Testing Flask-SQLAlchemy extension...")
            try:
                from flask import current_app
                db_extension = current_app.extensions['sqlalchemy']
                print(f"✅ Extension found: {type(db_extension)}")
                print(f"   Available attributes: {[attr for attr in dir(db_extension) if not attr.startswith('_')]}")
            except Exception as e:
                print(f"❌ Extension access failed: {e}")
            
            # Test 3: Check if session exists
            print("\n3. Testing session access...")
            try:
                from flask import current_app
                db_extension = current_app.extensions['sqlalchemy']
                if hasattr(db_extension, 'session'):
                    print(f"✅ Session exists: {type(db_extension.session)}")
                else:
                    print("❌ No session attribute found")
                    
                # Try alternative session access
                from src.models.base import db
                print(f"✅ Base db session: {type(db.session)}")
                
            except Exception as e:
                print(f"❌ Session access failed: {e}")
            
            # Test 4: Test SpecificationArtifact query
            print("\n4. Testing SpecificationArtifact query...")
            try:
                from src.models.specification_artifact import SpecificationArtifact
                count = SpecificationArtifact.query.count()
                print(f"✅ SpecificationArtifact query works: Found {count} artifacts")
                
                # Test with specific filters
                test_artifacts = SpecificationArtifact.query.filter_by(
                    spec_id="spec_slack_C095S2NQQMV_1755327474.872009_22cea1a2"
                ).all()
                print(f"✅ Filtered query works: Found {len(test_artifacts)} artifacts for test spec")
                
            except Exception as e:
                print(f"❌ SpecificationArtifact query failed: {e}")
                import traceback
                traceback.print_exc()
                
        except Exception as e:
            print(f"❌ Overall test failed: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n✅ Database access test completed")

if __name__ == "__main__":
    test_db_access()