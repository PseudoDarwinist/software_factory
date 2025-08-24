#!/usr/bin/env python3
"""
Safe script to delete all tasks with 'ready' status from the Kanban board.
This script will:
1. Count ready tasks
2. Show what will be deleted
3. Ask for confirmation
4. Delete only ready status tasks
5. Confirm deletion
"""

import sys
import os

# Add the src directory to the path so we can import models
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from models.base import db
    from models.task import Task, TaskStatus
    from app import create_app
except ImportError:
    print("❌ Error: Could not import required modules.")
    print("Make sure you're running this from the project root directory.")
    sys.exit(1)

def main():
    print("🧹 Ready Tasks Cleanup Script")
    print("=" * 50)
    
    # Create Flask app context
    try:
        app = create_app()
        with app.app_context():
            # Step 1: Count ready tasks
            ready_tasks = Task.query.filter_by(status=TaskStatus.READY).all()
            
            if not ready_tasks:
                print("✅ No ready tasks found. Nothing to delete.")
                return
            
            print(f"📊 Found {len(ready_tasks)} tasks with 'ready' status")
            print("\nTasks to be deleted:")
            print("-" * 50)
            
            # Group by project for better visibility
            projects = {}
            for task in ready_tasks:
                if task.project_id not in projects:
                    projects[task.project_id] = []
                projects[task.project_id].append(task)
            
            for project_id, tasks in projects.items():
                print(f"\n📁 Project: {project_id} ({len(tasks)} tasks)")
                for task in tasks[:5]:  # Show first 5 tasks per project
                    print(f"   • {task.task_number}: {task.title[:60]}...")
                if len(tasks) > 5:
                    print(f"   ... and {len(tasks) - 5} more tasks")
            
            # Step 2: Ask for confirmation
            print(f"\n⚠️  WARNING: This will permanently delete {len(ready_tasks)} tasks with 'ready' status.")
            print("This action cannot be undone!")
            
            confirmation = input("\nDo you want to proceed? Type 'DELETE READY TASKS' to confirm: ")
            
            if confirmation != "DELETE READY TASKS":
                print("❌ Operation cancelled. No tasks were deleted.")
                return
            
            # Step 3: Perform deletion
            print(f"\n🗑️  Deleting {len(ready_tasks)} ready tasks...")
            
            deleted_count = 0
            for task in ready_tasks:
                try:
                    db.session.delete(task)
                    deleted_count += 1
                except Exception as e:
                    print(f"❌ Error deleting task {task.id}: {e}")
            
            # Commit the changes
            try:
                db.session.commit()
                print(f"✅ Successfully deleted {deleted_count} ready tasks!")
            except Exception as e:
                db.session.rollback()
                print(f"❌ Error committing changes: {e}")
                return
            
            # Step 4: Verify deletion
            remaining_ready_tasks = Task.query.filter_by(status=TaskStatus.READY).count()
            print(f"📊 Remaining ready tasks: {remaining_ready_tasks}")
            
            # Show remaining task counts by status
            print("\n📈 Current task status distribution:")
            for status in TaskStatus:
                count = Task.query.filter_by(status=status).count()
                print(f"   {status.value}: {count} tasks")
            
            print("\n🎉 Cleanup completed successfully!")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()