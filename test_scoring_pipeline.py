#!/usr/bin/env python3
"""
Test the ADI scoring pipeline implementation.
"""

import os
import sys
import hashlib
from datetime import datetime, timezone

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from adi.schemas.decision_log import DecisionLog, EventData, DecisionData, VersionData
from adi.services.scoring_pipeline import get_scoring_pipeline
from adi.services.domain_pack_loader import get_domain_pack

def test_scoring_pipeline():
    """Test the scoring pipeline with sample data."""
    
    print("Testing ADI Scoring Pipeline...")
    
    # Create sample decision log with proper hashed case_id
    case_id_hash = hashlib.md5("test_case_001".encode()).hexdigest()
    
    decision_log = DecisionLog(
        project_id="_default",  # Use default pack for testing
        case_id=case_id_hash,
        event=EventData(
            type="FlightDelay",
            ts=datetime.now(timezone.utc),
            scope="passenger_care",
            attrs={
                "delay_minutes": 180,
                "reason": "mechanical",
                "channel": "email",
                "market": "US"
            }
        ),
        decision=DecisionData(
            action="SendDelayNotification",
            channel="email",
            template_id="WRONG_TEMPLATE",  # This should trigger template validator
            status="OK",
            latency_ms=900000  # 15 minutes - should trigger SLA validator (over 10 min default)
        ),
        version=VersionData(
            app="irops_v2.1.0",
            policy="delay_policy_v1.2",
            factory_pr="12345"
        )
    )
    
    try:
        # Test domain pack loading
        print("\n1. Testing domain pack loading...")
        domain_pack = get_domain_pack("_default")
        print(f"   ✓ Loaded domain pack: {domain_pack.pack_config.pack.name}")
        print(f"   ✓ Pack version: {domain_pack.pack_config.pack.version}")
        print(f"   ✓ Failure modes: {len(domain_pack.ontology)}")
        
        # Test scoring pipeline
        print("\n2. Testing scoring pipeline...")
        
        # Debug: Check SLA for the test case
        sla_ms = domain_pack.get_sla_for_event("FlightDelay")
        print(f"   SLA for FlightDelay: {sla_ms}ms")
        print(f"   Test latency: {decision_log.decision.latency_ms}ms")
        print(f"   Should violate: {decision_log.decision.latency_ms > sla_ms}")
        
        scoring_pipeline = get_scoring_pipeline()
        findings = scoring_pipeline.score_decision(decision_log)
        
        print(f"   ✓ Generated {len(findings)} findings")
        
        # Display findings
        for i, finding in enumerate(findings, 1):
            print(f"\n   Finding {i}:")
            print(f"     Kind: {finding.kind}")
            print(f"     Severity: {finding.severity}")
            print(f"     Validator: {finding.validator_name}")
            print(f"     Details: {finding.details}")
            if finding.suggested_fix:
                print(f"     Suggested Fix: {finding.suggested_fix}")
        
        # Test signature generation
        print("\n3. Testing signature generation...")
        for finding in findings:
            signature = scoring_pipeline.generate_signature(finding, decision_log.project_id)
            print(f"   {finding.kind} -> {signature}")
        
        print("\n✓ All tests passed!")
        return True
        
    except Exception as e:
        print(f"\n✗ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_builtin_validators():
    """Test individual builtin validators."""
    
    print("\nTesting individual validators...")
    
    # Test SLA validator with violation
    sla_case_id_hash = hashlib.md5("sla_test".encode()).hexdigest()
    
    sla_violation_log = DecisionLog(
        project_id="_default",
        case_id=sla_case_id_hash,
        event=EventData(
            type="FlightCancellation",
            ts=datetime.now(timezone.utc),
            scope="passenger_care",
            attrs={}
        ),
        decision=DecisionData(
            action="SendCancellationNotice",
            channel="sms",
            template_id="CANCEL_01",
            status="OK",
            latency_ms=900000  # 15 minutes - should violate 10 minute default SLA
        ),
        version=VersionData(
            app="test_app",
            policy="test_policy",
            factory_pr="12345"
        )
    )
    
    scoring_pipeline = get_scoring_pipeline()
    
    # Debug: Check what SLA is being used
    domain_pack = get_domain_pack("_default")
    sla_ms = domain_pack.get_sla_for_event("FlightCancellation")
    print(f"   SLA for FlightCancellation: {sla_ms}ms")
    print(f"   Actual latency: {sla_violation_log.decision.latency_ms}ms")
    print(f"   Should violate: {sla_violation_log.decision.latency_ms > sla_ms}")
    
    findings = scoring_pipeline.score_decision(sla_violation_log)
    
    sla_findings = [f for f in findings if f.kind == "Time.SLA"]
    print(f"   SLA violations detected: {len(sla_findings)}")
    
    if sla_findings:
        finding = sla_findings[0]
        print(f"   Expected SLA: {finding.details.get('expected_sla_ms')}ms")
        print(f"   Actual latency: {finding.details.get('actual_latency_ms')}ms")
        print(f"   Overage: {finding.details.get('overage_ms')}ms")
    else:
        print("   No SLA findings generated - checking all findings:")
        for finding in findings:
            print(f"     {finding.kind}: {finding.details}")

if __name__ == '__main__':
    success = test_scoring_pipeline()
    if success:
        test_builtin_validators()
    
    sys.exit(0 if success else 1)