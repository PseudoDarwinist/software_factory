#!/usr/bin/env python3
"""
Test the custom validator framework implementation.
"""

import os
import sys
import hashlib
from datetime import datetime, timezone, timedelta

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from adi.schemas.decision_log import DecisionLog, EventData, DecisionData, VersionData
from adi.services.scoring_pipeline import get_scoring_pipeline
from adi.services.custom_validator_framework import get_custom_validator_framework

def test_custom_validator_framework():
    """Test the custom validator framework."""
    
    print("Testing Custom Validator Framework...")
    
    # Create test decision log with business hours violation
    case_id = hashlib.md5("custom_test_001".encode()).hexdigest()
    # Use a recent timestamp (5 minutes ago) for validation compliance
    test_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    
    business_hours_violation_log = DecisionLog(
        project_id="_default",
        case_id=case_id,
        event=EventData(
            type="MarketingEmail",
            ts=test_time,
            scope="marketing",
            attrs={
                "recipient_id": "user123",
                "priority": "low",  # Non-urgent
                "user_name": "John Doe",
                "recipient_locale": "en-US",
                "content_locale": "es-ES"  # Locale mismatch
            }
        ),
        decision=DecisionData(
            action="SendNotification",
            channel="email",
            template_id="MARKETING_01",
            status="OK",
            latency_ms=5000
        ),
        version=VersionData(
            app="marketing_v1.0",
            policy="marketing_policy_v1.0",
            factory_pr="12345"
        )
    )
    
    try:
        print("\n1. Testing custom validator loading and execution...")
        
        # Get scoring pipeline (this should load custom validators)
        scoring_pipeline = get_scoring_pipeline()
        
        # Score the decision log
        findings = scoring_pipeline.score_decision(business_hours_violation_log)
        
        print(f"   ✓ Generated {len(findings)} total findings")
        
        # Filter custom validator findings
        custom_findings = [f for f in findings if f.validator_name.startswith('custom:')]
        print(f"   ✓ Generated {len(custom_findings)} custom validator findings")
        
        # Display custom findings
        for finding in custom_findings:
            print(f"\n   Custom Finding:")
            print(f"     Kind: {finding.kind}")
            print(f"     Severity: {finding.severity}")
            print(f"     Validator: {finding.validator_name}")
            print(f"     Details: {finding.details}")
            if finding.suggested_fix:
                print(f"     Suggested Fix: {finding.suggested_fix}")
        
        print("\n2. Testing custom validator framework stats...")
        
        # Get framework stats
        framework = get_custom_validator_framework()
        stats = framework.get_validator_stats()
        
        print(f"   ✓ Total registered validators: {stats.get('total_validators', 0)}")
        
        for validator_name, validator_stats in stats.get('validators', {}).items():
            print(f"   Validator: {validator_name}")
            print(f"     Executions: {validator_stats['execution_count']}")
            print(f"     Success rate: {validator_stats['success_rate']:.2%}")
            print(f"     Avg execution time: {validator_stats['avg_execution_time_ms']:.2f}ms")
        
        print("\n3. Testing individual custom validator...")
        
        # Test a specific validator
        from adi.services.scoring_context import ScoringContext
        from adi.services.domain_pack_loader import get_domain_pack
        
        domain_pack = get_domain_pack("_default")
        context = ScoringContext(
            project_id="_default",
            case_id=hashlib.md5("test_case".encode()).hexdigest(),
            decision_log=business_hours_violation_log,
            domain_pack=domain_pack,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Test business hours validator specifically
        test_result = framework.test_validator("business_hours", context, debug=True)
        
        print(f"   Test result for business_hours validator:")
        print(f"     Success: {test_result['success']}")
        print(f"     Execution time: {test_result['execution_time_ms']:.2f}ms")
        print(f"     Findings count: {test_result['findings_count']}")
        
        if test_result.get('debug'):
            debug_info = test_result['debug']
            print(f"     Debug - Event type: {debug_info['event_type']}")
            print(f"     Debug - Decision action: {debug_info['decision_action']}")
        
        print("\n✓ All custom validator tests passed!")
        return True
        
    except Exception as e:
        print(f"\n✗ Custom validator test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_validator_error_handling():
    """Test error handling and timeout scenarios."""
    
    print("\nTesting validator error handling...")
    
    framework = get_custom_validator_framework()
    
    # Create a validator that will fail
    def failing_validator(context):
        raise ValueError("This validator always fails")
    
    # Create a validator that will timeout
    def timeout_validator(context):
        import time
        time.sleep(35)  # Sleep longer than default timeout
        return []
    
    # Register test validators
    framework.register_validator("failing_test", failing_validator, description="Test failing validator")
    framework.register_validator("timeout_test", timeout_validator, timeout_seconds=2, description="Test timeout validator")
    
    # Create test context
    from adi.services.scoring_context import ScoringContext
    from adi.services.domain_pack_loader import get_domain_pack
    from adi.schemas.decision_log import DecisionLog, EventData, DecisionData, VersionData
    
    test_log = DecisionLog(
        project_id="_default",
        case_id=hashlib.md5("error_test".encode()).hexdigest(),
        event=EventData(
            type="TestEvent",
            ts=datetime.now(timezone.utc),
            scope="test",
            attrs={}
        ),
        decision=DecisionData(
            action="TestAction",
            channel="test",
            template_id="TEST_01",
            status="OK",
            latency_ms=1000
        ),
        version=VersionData(
            app="test_app",
            policy="test_policy",
            factory_pr="12345"
        )
    )
    
    domain_pack = get_domain_pack("_default")
    context = ScoringContext(
        project_id="_default",
        case_id=hashlib.md5("error_test".encode()).hexdigest(),
        decision_log=test_log,
        domain_pack=domain_pack,
        timestamp=datetime.now(timezone.utc)
    )
    
    # Test failing validator
    print("   Testing failing validator...")
    result = framework.execute_validator("failing_test", context)
    print(f"     Success: {result.success}")
    print(f"     Error: {result.error}")
    
    # Test timeout validator
    print("   Testing timeout validator...")
    result = framework.execute_validator("timeout_test", context)
    print(f"     Success: {result.success}")
    print(f"     Timeout: {result.timeout}")
    print(f"     Execution time: {result.execution_time_ms:.2f}ms")
    
    print("   ✓ Error handling tests completed")

if __name__ == '__main__':
    success = test_custom_validator_framework()
    if success:
        test_validator_error_handling()
    
    sys.exit(0 if success else 1)