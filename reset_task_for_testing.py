#!/usr/bin/env python3
"""
Reset a task back to review status for testing the approval flow
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def reset_task_for_testing():
    """Reset a done task back to review status for testing"""
    
    print("🔄 Resetting task for testing...")
    
    try:
        from models.task import Task, TaskStatus
        from models.base import db
        from app import create_app
        
        # Create app context
        app = create_app()
        with app.app_context():
            # Find a done task with a PR
            done_tasks = Task.query.filter(
                Task.status == TaskStatus.DONE,
                Task.pr_number.isnot(None)
            ).all()
            
            if not done_tasks:
                print("   ❌ No done tasks with PRs found")
                return None
            
            # Use the first done task
            task = done_tasks[0]
            print(f"   📋 Found task: {task.id}")
            print(f"   Title: {task.title}")
            print(f"   PR: #{task.pr_number}")
            print(f"   Project: {task.project_id}")
            print(f"   Current status: {task.status.value}")
            
            # Reset to review status
            task.status = TaskStatus.REVIEW
            task.completed_at = None
            task.completed_by = None
            
            # Add a progress message
            task.add_progress_message("🔄 Reset to review status for testing", 90)
            
            db.session.commit()
            
            print(f"   ✅ Task reset to REVIEW status!")
            print(f"   Task ID: {task.id}")
            print(f"   PR Number: {task.pr_number}")
            print(f"   Project ID: {task.project_id}")
            
            return {
                'task_id': task.id,
                'pr_number': task.pr_number,
                'project_id': task.project_id,
                'title': task.title
            }
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_task_approval_flow(task_info):
    """Test the complete task approval flow"""
    
    print(f"\n🧪 Testing task approval flow...")
    print(f"Task ID: {task_info['task_id']}")
    print(f"Project ID: {task_info['project_id']}")
    print(f"PR Number: {task_info['pr_number']}")
    
    import requests
    import time
    
    # Step 1: Verify task is in review status
    print(f"\n1️⃣ Verifying task is in review status...")
    try:
        response = requests.get(f"http://localhost:8000/api/tasks/{task_info['task_id']}")
        if response.status_code == 200:
            task_data = response.json()
            print(f"   Status: {task_data.get('status')}")
            if task_data.get('status') != 'review':
                print(f"   ❌ Task is not in review status!")
                return False
        else:
            print(f"   ❌ Failed to get task: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Step 2: Clear existing events
    print(f"\n2️⃣ Clearing existing events...")
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        cleared = r.delete('phase_transition_events')
        print(f"   Cleared {cleared} existing events")
    except Exception as e:
        print(f"   ⚠️ Could not clear Redis: {e}")
    
    # Step 3: Approve the task
    print(f"\n3️⃣ Approving task...")
    try:
        response = requests.post(
            f"http://localhost:8000/api/tasks/{task_info['task_id']}/approve",
            json={'approvedBy': 'test_user'}
        )
        
        if response.status_code == 200:
            print(f"   ✅ Task approved successfully!")
            result = response.json()
            print(f"   Response: {result}")
        else:
            print(f"   ❌ Task approval failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Step 4: Check for phase transition events
    print(f"\n4️⃣ Checking for phase transition events...")
    time.sleep(2)  # Wait for event processing
    
    try:
        response = requests.get('http://localhost:8000/api/status')
        if response.status_code == 200:
            data = response.json()
            events = data.get('events', [])
            print(f"   Found {len(events)} events")
            
            phase_transition_found = False
            for event in events:
                print(f"   Event: {event}")
                if event.get('type') == 'phase.transition':
                    payload = event.get('payload', {})
                    if (payload.get('to_phase') == 'validate' and 
                        payload.get('project_id') == task_info['project_id']):
                        phase_transition_found = True
                        print(f"   🎉 SUCCESS: Phase transition event found!")
                        print(f"   Project ID: {payload.get('project_id')}")
                        print(f"   PR Number: {payload.get('pr_number')}")
                        break
            
            if not phase_transition_found:
                print(f"   ❌ Phase transition event not found!")
                return False
            
        else:
            print(f"   ❌ Status check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Step 5: Instructions for UI testing
    print(f"\n5️⃣ UI Testing Instructions:")
    print(f"   🎯 Now test in Mission Control UI:")
    print(f"   1. Open Mission Control")
    print(f"   2. Select project: {task_info['project_id']}")
    print(f"   3. Make sure you're on Build phase")
    print(f"   4. Wait up to 30 seconds for polling")
    print(f"   5. Check browser console for debug logs")
    print(f"   6. UI should automatically switch to Validate phase")
    print(f"   7. You should see notification about PR #{task_info['pr_number']}")
    
    return True

if __name__ == '__main__':
    print("🚀 Task Approval Flow Test")
    print("=" * 50)
    
    # Reset a task for testing
    task_info = reset_task_for_testing()
    
    if task_info:
        # Test the approval flow
        success = test_task_approval_flow(task_info)
        
        if success:
            print(f"\n✅ Task approval flow test completed!")
            print(f"📱 Now test the UI with project: {task_info['project_id']}")
        else:
            print(f"\n❌ Task approval flow test failed!")
    else:
        print(f"\n❌ Could not reset task for testing!")