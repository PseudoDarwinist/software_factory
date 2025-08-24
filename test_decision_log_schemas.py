#!/usr/bin/env python3
"""
Test script for Decision Log Pydantic schemas.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from datetime import datetime, timezone
from src.adi.schemas.decision_log import (
    DecisionLog, EventData, DecisionData, VersionData,
    validate_decision_log, hash_case_id, detect_pii_in_text
)


def get_current_timestamp():
    """Get current timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def test_valid_decision_log():
    """Test a valid decision log."""
    print("Testing valid decision log...")
    
    valid_log = {
        "project_id": "irops-prod",
        "case_id": hash_case_id("CASE-12345"),
        "event": {
            "type": "FlightDelay",
            "ts": get_current_timestamp(),
            "scope": "departure",
            "attrs": {
                "flight_number": "AA123",
                "delay_minutes": 45,
                "reason": "weather"
            }
        },
        "decision": {
            "action": "SendDelayNotification",
            "channel": "sms",
            "template_id": "DELAY-001",
            "status": "OK",
            "latency_ms": 250,
            "counts": {"passengers": 150}
        },
        "version": {
            "app": "1.2.3",
            "policy": "2.1.0",
            "factory_pr": "PR-456"
        },
        "links": {
            "flight_status": "https://example.com/flight/AA123"
        }
    }
    
    try:
        log = validate_decision_log(valid_log)
        print(f"✓ Valid log created: {log.case_id}")
        print(f"  Event: {log.event.type} at {log.event.ts}")
        print(f"  Decision: {log.decision.action} via {log.decision.channel}")
        print(f"  Version: {log.version.app} (PR {log.version.factory_pr})")
    except Exception as e:
        print(f"✗ Validation failed: {e}")
        return False
    
    return True


def test_pii_detection():
    """Test PII detection and rejection."""
    print("\nTesting PII detection...")
    
    # Test with PII in attrs
    invalid_log_with_pii = {
        "project_id": "irops-prod",
        "case_id": hash_case_id("CASE-12345"),
        "event": {
            "type": "FlightDelay",
            "ts": get_current_timestamp(),
            "scope": "departure",
            "attrs": {
                "passenger_email": "john.doe@example.com",  # PII!
                "flight_number": "AA123"
            }
        },
        "decision": {
            "action": "SendDelayNotification",
            "channel": "sms",
            "template_id": "DELAY-001",
            "status": "OK",
            "latency_ms": 250
        },
        "version": {
            "app": "1.2.3",
            "policy": "2.1.0",
            "factory_pr": "456"
        }
    }
    
    try:
        log = validate_decision_log(invalid_log_with_pii)
        print("✗ PII validation failed - should have rejected email")
        return False
    except ValueError as e:
        print(f"✓ PII correctly detected and rejected: {e}")
    
    # Test PII detection function
    test_text = "Contact john.doe@example.com or call 555-123-4567"
    detected = detect_pii_in_text(test_text)
    print(f"✓ PII patterns detected: {detected}")
    
    return True


def test_case_id_validation():
    """Test case ID must be hashed."""
    print("\nTesting case ID validation...")
    
    # Test with non-hashed case ID
    invalid_log = {
        "project_id": "irops-prod",
        "case_id": "CASE-12345",  # Not hashed!
        "event": {
            "type": "FlightDelay",
            "ts": get_current_timestamp(),
            "scope": "departure",
            "attrs": {"flight_number": "AA123"}
        },
        "decision": {
            "action": "SendDelayNotification",
            "channel": "sms",
            "template_id": "DELAY-001",
            "status": "OK",
            "latency_ms": 250
        },
        "version": {
            "app": "1.2.3",
            "policy": "2.1.0",
            "factory_pr": "456"
        }
    }
    
    try:
        log = validate_decision_log(invalid_log)
        print("✗ Case ID validation failed - should have rejected non-hash")
        return False
    except ValueError as e:
        print(f"✓ Non-hashed case ID correctly rejected: {e}")
    
    return True


def test_schema_versioning():
    """Test schema versioning support."""
    print("\nTesting schema versioning...")
    
    # Test with explicit schema version
    log_with_version = {
        "project_id": "irops-prod",
        "case_id": hash_case_id("CASE-12345"),
        "schema_version": "1.0.0",
        "event": {
            "type": "FlightDelay",
            "ts": get_current_timestamp(),
            "scope": "departure",
            "attrs": {"flight_number": "AA123"}
        },
        "decision": {
            "action": "SendDelayNotification",
            "channel": "sms",
            "template_id": "DELAY-001",
            "status": "OK",
            "latency_ms": 250
        },
        "version": {
            "app": "1.2.3",
            "policy": "2.1.0",
            "factory_pr": "456"
        }
    }
    
    try:
        log = validate_decision_log(log_with_version)
        print(f"✓ Schema version {log.schema_version} accepted")
    except Exception as e:
        print(f"✗ Schema version validation failed: {e}")
        return False
    
    # Test with invalid schema version
    log_with_invalid_version = log_with_version.copy()
    log_with_invalid_version["schema_version"] = "invalid"
    
    try:
        log = validate_decision_log(log_with_invalid_version)
        print("✗ Invalid schema version should have been rejected")
        return False
    except ValueError as e:
        print(f"✓ Invalid schema version correctly rejected: {e}")
    
    return True


def test_timestamp_validation():
    """Test timestamp validation."""
    print("\nTesting timestamp validation...")
    
    # Test with future timestamp (should fail)
    future_log = {
        "project_id": "irops-prod",
        "case_id": hash_case_id("CASE-12345"),
        "event": {
            "type": "FlightDelay",
            "ts": "2025-12-31T23:59:59",  # Far future
            "scope": "departure",
            "attrs": {"flight_number": "AA123"}
        },
        "decision": {
            "action": "SendDelayNotification",
            "channel": "sms",
            "template_id": "DELAY-001",
            "status": "OK",
            "latency_ms": 250
        },
        "version": {
            "app": "1.2.3",
            "policy": "2.1.0",
            "factory_pr": "456"
        }
    }
    
    try:
        log = validate_decision_log(future_log)
        print("✗ Future timestamp should have been rejected")
        return False
    except ValueError as e:
        print(f"✓ Future timestamp correctly rejected: {e}")
    
    return True


def main():
    """Run all tests."""
    print("Testing Decision Log Pydantic Schemas")
    print("=" * 40)
    
    tests = [
        test_valid_decision_log,
        test_pii_detection,
        test_case_id_validation,
        test_schema_versioning,
        test_timestamp_validation
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n{passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())