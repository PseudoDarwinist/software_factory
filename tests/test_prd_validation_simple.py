"""
Simple integration test for PRD requirement validation.
Tests the core functionality without complex Flask app setup.
"""

import pytest
import json
import uuid
from datetime import datetime, timezone

# Test the validation function directly
def test_prd_validation_function():
    """Test the PRD validation function directly"""
    try:
        from src.api.stages import _validate_prd_requirement
    except ImportError:
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        from src.api.stages import _validate_prd_requirement
    
    # Test with non-existent project (should fail open)
    result = _validate_prd_requirement("non-existent-project", "test-item")
    
    # Should fail open (allow transition) when validation fails
    assert result['has_prd'] is True
    assert result['prd_status'] == 'unknown'
    
    print("✅ PRD validation function works correctly")


def test_prd_model_functionality():
    """Test PRD model functionality directly"""
    try:
        from src.models.prd import PRD
        from src.models.base import db
        from src.app import create_app
    except ImportError:
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        from src.models.prd import PRD
        from src.models.base import db
        from src.app import create_app
    
    # Create test app
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.app_context():
        db.create_all()
        
        # Test PRD creation
        project_id = str(uuid.uuid4())
        draft_id = str(uuid.uuid4())
        
        # Create draft PRD
        prd = PRD.create_draft(
            project_id=project_id,
            draft_id=draft_id,
            md_content="# Test PRD\n\nThis is a test PRD.",
            json_summary={'problem': {'text': 'Test problem'}},
            created_by='test_user'
        )
        
        assert prd is not None
        assert prd.status == 'draft'
        assert prd.version == 'v0'
        
        # Test freezing PRD
        frozen_prd = prd.freeze_version('test_user')
        assert frozen_prd.status == 'frozen'
        
        # Test retrieval
        latest_prd = PRD.get_latest_for_session(draft_id)
        assert latest_prd is not None
        assert latest_prd.status == 'frozen'
        
        print("✅ PRD model functionality works correctly")


def test_api_endpoint_structure():
    """Test that the API endpoint structure is correct"""
    try:
        from src.api.stages import stages_bp
    except ImportError:
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        from src.api.stages import stages_bp
    
    # Check that the blueprint has the expected routes
    routes = [rule.rule for rule in stages_bp.url_map.iter_rules()]
    
    # Check for PRD status endpoint
    prd_status_route = '/api/project/<project_id>/prd-status'
    assert any(prd_status_route in route for route in routes), f"PRD status route not found in {routes}"
    
    # Check for move stage endpoint
    move_stage_route = '/api/idea/<item_id>/move-stage'
    assert any(move_stage_route in route for route in routes), f"Move stage route not found in {routes}"
    
    print("✅ API endpoint structure is correct")


if __name__ == '__main__':
    test_prd_validation_function()
    test_prd_model_functionality()
    test_api_endpoint_structure()
    print("\n🎉 All simple tests passed!")