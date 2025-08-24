#!/usr/bin/env python3
"""
Test script for Decision Log Cleanup Service.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from datetime import datetime, timedelta
from src.adi.services.cleanup_service import get_cleanup_service, cleanup_now
from src.adi.models.decision_log import DecisionLog
from src.adi.schemas.decision_log import hash_case_id
from src.models.base import db


def create_test_logs():
    """Create test decision logs with different ages."""
    print("Creating test decision logs...")
    
    # Create logs of different ages
    test_logs = []
    
    # Recent logs (should not be deleted)
    for i in range(5):
        log = DecisionLog(
            project_id="test-project",
            case_id=hash_case_id(f"RECENT-{i}"),
            event_data={
                "type": "TestEvent",
                "ts": datetime.utcnow().isoformat(),
                "scope": "test",
                "attrs": {"test": True}
            },
            decision_data={
                "action": "TestAction",
                "channel": "test",
                "template_id": "TEST-001",
                "status": "OK",
                "latency_ms": 100
            },
            version_data={
                "app": "1.0.0",
                "policy": "1.0.0",
                "factory_pr": "123"
            }
        )
        # Set created_at to recent (within 30 days)
        log.created_at = datetime.utcnow() - timedelta(days=i)
        test_logs.append(log)
    
    # Old logs (should be deleted with default 60-day retention)
    for i in range(3):
        log = DecisionLog(
            project_id="test-project",
            case_id=hash_case_id(f"OLD-{i}"),
            event_data={
                "type": "TestEvent",
                "ts": (datetime.utcnow() - timedelta(days=70 + i)).isoformat(),
                "scope": "test",
                "attrs": {"test": True, "old": True}
            },
            decision_data={
                "action": "TestAction",
                "channel": "test",
                "template_id": "TEST-001",
                "status": "OK",
                "latency_ms": 100
            },
            version_data={
                "app": "1.0.0",
                "policy": "1.0.0",
                "factory_pr": "123"
            }
        )
        # Set created_at to old (older than 60 days)
        log.created_at = datetime.utcnow() - timedelta(days=70 + i)
        log.expires_at = datetime.utcnow() - timedelta(days=10 + i)  # Already expired
        test_logs.append(log)
    
    # Add all logs to database
    for log in test_logs:
        db.session.add(log)
    
    db.session.commit()
    print(f"Created {len(test_logs)} test logs")
    return test_logs


def test_cleanup_stats():
    """Test cleanup statistics."""
    print("\nTesting cleanup statistics...")
    
    service = get_cleanup_service()
    stats = service.get_cleanup_stats(max_age_days=60)
    
    print(f"Total logs: {stats['total_logs']}")
    print(f"Expired logs: {stats['total_expired']}")
    print(f"Cutoff date: {stats['cutoff_date']}")
    print(f"Expired by project: {stats['expired_by_project']}")
    
    return stats['total_expired'] > 0


def test_dry_run_cleanup():
    """Test dry run cleanup."""
    print("\nTesting dry run cleanup...")
    
    result = cleanup_now(max_age_days=60, dry_run=True)
    
    print(f"Dry run result: {result}")
    print(f"Would delete: {result['total_deleted']} logs")
    print(f"Success: {result['success']}")
    
    return result['success'] and result['total_deleted'] > 0


def test_actual_cleanup():
    """Test actual cleanup."""
    print("\nTesting actual cleanup...")
    
    # Get count before cleanup
    total_before = db.session.query(db.func.count(DecisionLog.id)).scalar()
    print(f"Total logs before cleanup: {total_before}")
    
    result = cleanup_now(max_age_days=60, dry_run=False)
    
    print(f"Cleanup result: {result}")
    print(f"Deleted: {result['total_deleted']} logs")
    print(f"Success: {result['success']}")
    
    # Get count after cleanup
    total_after = db.session.query(db.func.count(DecisionLog.id)).scalar()
    print(f"Total logs after cleanup: {total_after}")
    
    expected_remaining = total_before - result['total_deleted']
    if total_after == expected_remaining:
        print("✓ Log count matches expected")
        return True
    else:
        print(f"✗ Log count mismatch: expected {expected_remaining}, got {total_after}")
        return False


def test_background_job():
    """Test background cleanup job."""
    print("\nTesting background cleanup job...")
    
    service = get_cleanup_service()
    job_id = service.schedule_cleanup_job(max_age_days=60, batch_size=100)
    
    print(f"Scheduled cleanup job: {job_id}")
    
    # Wait a moment for job to process
    import time
    time.sleep(2)
    
    # Check job status
    jobs = service.get_recent_cleanup_jobs(limit=1)
    if jobs:
        latest_job = jobs[0]
        print(f"Latest job status: {latest_job['status']}")
        print(f"Job result: {latest_job.get('result', 'No result yet')}")
        return latest_job['status'] in ['completed', 'running']
    else:
        print("No cleanup jobs found")
        return False


def cleanup_test_data():
    """Clean up test data."""
    print("\nCleaning up test data...")
    
    # Delete all test logs
    deleted = db.session.query(DecisionLog).filter(
        DecisionLog.project_id == "test-project"
    ).delete()
    
    db.session.commit()
    print(f"Deleted {deleted} test logs")


def main():
    """Run all cleanup service tests."""
    print("Testing Decision Log Cleanup Service")
    print("=" * 40)
    
    try:
        # Create test data
        create_test_logs()
        
        tests = [
            test_cleanup_stats,
            test_dry_run_cleanup,
            test_actual_cleanup,
            test_background_job
        ]
        
        passed = 0
        for test in tests:
            try:
                if test():
                    passed += 1
                    print("✓ Test passed")
                else:
                    print("✗ Test failed")
            except Exception as e:
                print(f"✗ Test failed with exception: {e}")
        
        print(f"\n{passed}/{len(tests)} tests passed")
        
        # Clean up
        cleanup_test_data()
        
        if passed == len(tests):
            print("✓ All cleanup service tests passed!")
            return 0
        else:
            print("✗ Some cleanup service tests failed")
            return 1
            
    except Exception as e:
        print(f"Test suite failed: {e}")
        cleanup_test_data()
        return 1


if __name__ == "__main__":
    sys.exit(main())