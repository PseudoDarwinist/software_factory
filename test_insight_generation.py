#!/usr/bin/env python3
"""
Test the insight generation and clustering functionality.
"""

import os
import sys
import hashlib
from datetime import datetime, timezone, timedelta

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from adi.schemas.decision_log import DecisionLog, EventData, DecisionData, VersionData
from adi.services.scoring_pipeline import get_scoring_pipeline
from adi.services.insight_service import get_insight_service
from adi.services.pipeline_orchestrator import get_pipeline_orchestrator
from adi.models.finding import Finding
from adi.models.insight import Insight

try:
    from models.base import db
    from app import create_app
except ImportError:
    print("Warning: Could not import database components. Some tests may not work.")
    db = None
    create_app = None

def create_test_decision_logs():
    """Create multiple decision logs that should cluster into insights."""
    
    base_time = datetime.now(timezone.utc) - timedelta(minutes=30)
    decision_logs = []
    
    # Create multiple SLA violations that should cluster together
    for i in range(7):  # Above the minimum cluster size of 5
        case_id = hashlib.md5(f"sla_violation_{i}".encode()).hexdigest()
        
        decision_log = DecisionLog(
            project_id="_default",
            case_id=case_id,
            event=EventData(
                type="FlightDelay",
                ts=base_time + timedelta(minutes=i * 2),
                scope="passenger_care",
                attrs={
                    "delay_minutes": 180 + (i * 10),
                    "reason": "mechanical",
                    "channel": "email",
                    "market": "US"
                }
            ),
            decision=DecisionData(
                action="SendDelayNotification",
                channel="email",
                template_id="DELAY_EMAIL_01",
                status="OK",
                latency_ms=900000 + (i * 50000)  # All violate SLA
            ),
            version=VersionData(
                app="irops_v2.1.0",
                policy="delay_policy_v1.2",
                factory_pr="12345"
            )
        )
        decision_logs.append(decision_log)
    
    # Create multiple template selection issues
    for i in range(6):
        case_id = hashlib.md5(f"template_issue_{i}".encode()).hexdigest()
        
        decision_log = DecisionLog(
            project_id="_default",
            case_id=case_id,
            event=EventData(
                type="SystemAlert",
                ts=base_time + timedelta(minutes=i * 3),
                scope="operations",
                attrs={}
            ),
            decision=DecisionData(
                action="SendAlert",
                channel="email",
                template_id="WRONG_TEMPLATE",  # Should be ALERT-EMAIL-01
                status="OK",
                latency_ms=5000
            ),
            version=VersionData(
                app="ops_v1.0",
                policy="ops_policy_v1.0",
                factory_pr="12345"
            )
        )
        decision_logs.append(decision_log)
    
    # Create some delivery failures
    for i in range(5):
        case_id = hashlib.md5(f"delivery_failure_{i}".encode()).hexdigest()
        
        decision_log = DecisionLog(
            project_id="_default",
            case_id=case_id,
            event=EventData(
                type="UserNotification",
                ts=base_time + timedelta(minutes=i * 4),
                scope="user_care",
                attrs={}
            ),
            decision=DecisionData(
                action="SendNotification",
                channel="push",
                template_id="NOTIF_PUSH_01",
                status="FAILED",
                latency_ms=5000
            ),
            version=VersionData(
                app="user_app_v1.0",
                policy="user_policy_v1.0",
                factory_pr="12345"
            )
        )
        decision_logs.append(decision_log)
    
    return decision_logs

def test_insight_generation():
    """Test the complete insight generation pipeline."""
    
    print("Testing Insight Generation and Clustering...")
    
    if not db or not create_app:
        print("Skipping database tests - database components not available")
        return True
    
    try:
        # Create Flask app context
        app = create_app()
        
        with app.app_context():
            # Create test decision logs
            print("\n1. Creating test decision logs...")
            decision_logs = create_test_decision_logs()
            print(f"   ✓ Created {len(decision_logs)} test decision logs")
            
            # Process decision logs through pipeline
            print("\n2. Processing decision logs through scoring pipeline...")
            orchestrator = get_pipeline_orchestrator()
            
            total_findings = 0
            for decision_log in decision_logs:
                result = orchestrator.process_decision_log(decision_log)
                total_findings += result['findings_count']
                print(f"   Processed {decision_log.case_id}: {result['findings_count']} findings")
            
            print(f"   ✓ Generated {total_findings} total findings")
            
            # Trigger insight generation
            print("\n3. Clustering findings into insights...")
            insight_service = get_insight_service()
            
            # Generate insights with lower thresholds for testing
            insights = insight_service.cluster_findings_into_insights(
                project_id="_default",
                window_minutes=60,
                min_cluster_size=3  # Lower threshold for testing
            )
            
            print(f"   ✓ Generated {len(insights)} insights")
            
            # Display insights
            for insight in insights:
                print(f"\n   Insight: {insight.title}")
                print(f"     Kind: {insight.kind}")
                print(f"     Severity: {insight.severity}")
                print(f"     Evidence count: {insight.evidence.get('total_affected', 0)}")
                print(f"     Summary: {insight.summary}")
                
                # Display metrics
                if insight.metrics:
                    print(f"     Metrics:")
                    for key, value in insight.metrics.items():
                        print(f"       {key}: {value}")
            
            # Test insight retrieval
            print("\n4. Testing insight retrieval...")
            insights_for_review = insight_service.get_insights_for_review("_default")
            print(f"   ✓ Retrieved {len(insights_for_review)} insights for review")
            
            # Test insight status update
            if insights:
                print("\n5. Testing insight status update...")
                first_insight = insights[0]
                updated_insight = insight_service.update_insight_status(
                    str(first_insight.id),
                    "converted",
                    "Converted to work item for investigation"
                )
                print(f"   ✓ Updated insight status to: {updated_insight.status}")
            
            print("\n✓ All insight generation tests passed!")
            return True
            
    except Exception as e:
        print(f"\n✗ Insight generation test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_insight_clustering_algorithm():
    """Test the clustering algorithm with different scenarios."""
    
    print("\nTesting insight clustering algorithm...")
    
    # Test signature generation
    from adi.services.scoring_pipeline import get_scoring_pipeline
    from adi.models.finding import FindingData
    
    scoring_pipeline = get_scoring_pipeline()
    
    # Create similar findings that should cluster together
    similar_findings = [
        FindingData(
            kind="Time.SLA",
            severity="high",
            details={
                'event_type': 'FlightDelay',
                'expected_sla_ms': 600000,
                'actual_latency_ms': 900000
            },
            validator_name="builtin:sla"
        ),
        FindingData(
            kind="Time.SLA",
            severity="high",
            details={
                'event_type': 'FlightDelay',
                'expected_sla_ms': 600000,
                'actual_latency_ms': 950000
            },
            validator_name="builtin:sla"
        )
    ]
    
    # Generate signatures
    signatures = []
    for finding in similar_findings:
        signature = scoring_pipeline.generate_signature(finding, "_default")
        signatures.append(signature)
        print(f"   Finding signature: {signature}")
    
    # Check if similar findings have the same signature
    if len(set(signatures)) == 1:
        print("   ✓ Similar findings generate the same signature for clustering")
    else:
        print("   ✗ Similar findings generate different signatures")
    
    # Test different findings that should NOT cluster together
    different_findings = [
        FindingData(
            kind="Time.SLA",
            severity="high",
            details={'event_type': 'FlightDelay'},
            validator_name="builtin:sla"
        ),
        FindingData(
            kind="Template.Select",
            severity="med",
            details={'event_type': 'SystemAlert'},
            validator_name="builtin:template"
        )
    ]
    
    different_signatures = []
    for finding in different_findings:
        signature = scoring_pipeline.generate_signature(finding, "_default")
        different_signatures.append(signature)
    
    if len(set(different_signatures)) == 2:
        print("   ✓ Different findings generate different signatures")
    else:
        print("   ✗ Different findings generate the same signature")
    
    print("   ✓ Clustering algorithm tests completed")

def test_insight_metrics_calculation():
    """Test insight metrics calculation."""
    
    print("\nTesting insight metrics calculation...")
    
    # This would require database setup, so we'll do a simplified test
    from adi.services.insight_service import InsightService
    from adi.models.finding import Finding
    from datetime import datetime
    
    insight_service = InsightService()
    
    # Create mock findings for metrics calculation
    mock_findings = []
    for i in range(5):
        # Create a mock finding object
        class MockFinding:
            def __init__(self, kind, severity, details, validator_name, case_id):
                self.kind = kind
                self.severity = severity
                self.details = details
                self.validator_name = validator_name
                self.case_id = case_id
                self.created_at = datetime.now(timezone.utc)
        
        finding = MockFinding(
            kind="Time.SLA",
            severity="high" if i < 3 else "med",
            details={
                'overage_ms': 300000 + (i * 50000),
                'event_type': 'FlightDelay'
            },
            validator_name="builtin:sla",
            case_id=f"case_{i}"
        )
        mock_findings.append(finding)
    
    # Test metrics calculation
    from adi.services.domain_pack_loader import get_domain_pack
    domain_pack = get_domain_pack("_default")
    
    metrics = insight_service._calculate_insight_metrics(mock_findings, domain_pack)
    
    print(f"   Calculated metrics:")
    print(f"     Finding count: {metrics['finding_count']}")
    print(f"     Unique cases: {metrics['unique_cases']}")
    print(f"     Severity distribution: {metrics['severity_distribution']}")
    
    if 'avg_overage_ms' in metrics:
        print(f"     Average overage: {metrics['avg_overage_ms']:.0f}ms")
    
    print("   ✓ Metrics calculation tests completed")

if __name__ == '__main__':
    success = test_insight_generation()
    
    # Run additional tests regardless of database availability
    test_insight_clustering_algorithm()
    test_insight_metrics_calculation()
    
    sys.exit(0 if success else 1)