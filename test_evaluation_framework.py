#!/usr/bin/env python3
"""
Test script for the ADI Evaluation Framework

This script tests the core functionality of the evaluation system.
"""

import sys
import os
import json
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from adi.services.evaluation_service import EvaluationService, EvalBlueprint, SelectCriteria, VerifyCriteria
    from adi.services.eval_runner import EvalRunner
    from adi.services.evaluation_analytics import EvaluationAnalytics
    from adi.models.evaluation import EvalSet, EvalResult
    from models.base import db
    from app import create_app
    
    print("✓ Successfully imported ADI evaluation modules")
    
    # Test evaluation service
    app = create_app()
    with app.app_context():
        print("\n=== Testing Evaluation Service ===")
        
        evaluation_service = EvaluationService()
        print("✓ Created EvaluationService instance")
        
        # Test blueprint creation
        select_criteria = SelectCriteria(
            failure_mode_tags=['Time.SLA'],
            time_window_days=7,
            min_cases=5,
            max_cases=50,
            event_types=['FlightDelay'],
            severity_levels=['high'],
            status_filters=['OK', 'FAILED']
        )
        
        verify_criteria = VerifyCriteria(
            check_types=['sla', 'template', 'policy'],
            custom_validators=['flight_delay_validator'],
            expected_outcomes={'decision.status': 'OK'}
        )
        
        blueprint = EvalBlueprint(
            id='test_eval_001',
            tag='Time.SLA',
            select=select_criteria,
            verify=verify_criteria,
            min_pass_rate=0.85,
            description='Test evaluation for SLA compliance'
        )
        
        print("✓ Created evaluation blueprint")
        
        # Test eval runner
        print("\n=== Testing Eval Runner ===")
        
        eval_runner = EvalRunner(max_workers=2)
        print("✓ Created EvalRunner instance")
        
        # Test builtin checks
        print("✓ EvalRunner has builtin checks:", list(eval_runner.builtin_checks.keys()))
        
        # Test evaluation analytics
        print("\n=== Testing Evaluation Analytics ===")
        
        evaluation_analytics = EvaluationAnalytics()
        print("✓ Created EvaluationAnalytics instance")
        
        # Test confidence calculation (with no data)
        confidence = evaluation_analytics.calculate_deployment_confidence('test_project')
        print(f"✓ Calculated deployment confidence: {confidence.confidence_score:.2f}")
        print(f"  - Recommendation: {confidence.recommendation}")
        print(f"  - Factors: {confidence.factors}")
        
        print("\n=== All Tests Passed! ===")
        print("The ADI Evaluation Framework is ready for use.")
        
except ImportError as e:
    print(f"✗ Import error: {e}")
    print("Make sure all dependencies are installed and the database is set up.")
    sys.exit(1)
except Exception as e:
    print(f"✗ Test error: {e}")
    sys.exit(1)