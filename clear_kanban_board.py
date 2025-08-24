#!/usr/bin/env python3
"""
Clear Kanban Board - Remove completed tasks and failed Build phase jobs

This script helps clean up the kanban board by:
1. Removing tasks with DONE status
2. Clearing failed background jobs from Build phase
3. Providing backup and restore options
"""

import sys
import os
import json
from datetime import datetime, timedelta

# Add src to path for imports
sys.path.append('src')

def clear_completed_tasks():
    """Clear tasks with DONE status from the kanban board"""
    try:
        from models.task import Task, TaskStatus
        from models.base import db
        from app import create_app
        
        app = create_app()
        
        with app.app_context():
            print("🧹 CLEARING COMPLETED TASKS FROM KANBAN BOARD")
            print("=" * 60)
            
            # Get all DONE tasks
            done_tasks = Task.query.filter_by(status=TaskStatus.DONE).all()
            
            if not done_tasks:
                print("✅ No completed tasks found to clear")
                return True
            
            print(f"📋 Found {len(done_tasks)} completed tasks:")
            
            # Show tasks to be cleared
            for task in done_tasks:
                print(f"   • {task.task_number}: {task.title[:50]}...")
                print(f"     Project: {task.project_id}, Completed: {task.completed_at}")
                if task.pr_url:
                    print(f"     PR: {task.pr_url}")
                print()
            
            # Confirm deletion
            response = input("❓ Do you want to delete these completed tasks? (y/N): ").strip().lower()
            if response != 'y':
                print("❌ Operation cancelled")
                return False
            
            # Create backup before deletion
            backup_data = []
            for task in done_tasks:
                backup_data.append(task.to_dict())
            
            # Save backup
            backup_filename = f"completed_tasks_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(backup_filename, 'w') as f:
                json.dump(backup_data, f, indent=2, default=str)
            
            print(f"💾 Backup saved to: {backup_filename}")
            
            # Delete tasks
            deleted_count = 0
            for task in done_tasks:
                try:
                    db.session.delete(task)
                    deleted_count += 1
                except Exception as e:
                    print(f"❌ Failed to delete task {task.id}: {e}")
            
            # Commit changes
            db.session.commit()
            
            print(f"✅ Successfully deleted {deleted_count} completed tasks")
            print(f"💾 Backup available at: {backup_filename}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error clearing completed tasks: {e}")
        import traceback
        traceback.print_exc()
        return False


def clear_failed_build_jobs():
    """Clear failed background jobs from Build phase"""
    try:
        from models.background_job import BackgroundJob
        from models.base import db
        from app import create_app
        
        app = create_app()
        
        with app.app_context():
            print("\n🔧 CLEARING FAILED BUILD PHASE JOBS")
            print("=" * 60)
            
            # Get failed jobs (older than 1 hour to avoid clearing recent failures)
            cutoff_time = datetime.utcnow() - timedelta(hours=1)
            failed_jobs = BackgroundJob.query.filter(
                BackgroundJob.status == BackgroundJob.STATUS_FAILED,
                BackgroundJob.created_at < cutoff_time
            ).all()
            
            if not failed_jobs:
                print("✅ No old failed jobs found to clear")
                return True
            
            print(f"📋 Found {len(failed_jobs)} failed jobs (older than 1 hour):")
            
            # Show jobs to be cleared
            for job in failed_jobs:
                print(f"   • Job {job.id}: {job.job_type}")
                print(f"     Project: {job.project_id}, Created: {job.created_at}")
                print(f"     Error: {job.error_message[:100]}..." if job.error_message else "     No error message")
                print()
            
            # Confirm deletion
            response = input("❓ Do you want to delete these failed jobs? (y/N): ").strip().lower()
            if response != 'y':
                print("❌ Operation cancelled")
                return False
            
            # Create backup before deletion
            backup_data = []
            for job in failed_jobs:
                backup_data.append(job.to_dict())
            
            # Save backup
            backup_filename = f"failed_jobs_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(backup_filename, 'w') as f:
                json.dump(backup_data, f, indent=2, default=str)
            
            print(f"💾 Backup saved to: {backup_filename}")
            
            # Delete jobs
            deleted_count = 0
            for job in failed_jobs:
                try:
                    db.session.delete(job)
                    deleted_count += 1
                except Exception as e:
                    print(f"❌ Failed to delete job {job.id}: {e}")
            
            # Commit changes
            db.session.commit()
            
            print(f"✅ Successfully deleted {deleted_count} failed jobs")
            print(f"💾 Backup available at: {backup_filename}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error clearing failed jobs: {e}")
        import traceback
        traceback.print_exc()
        return False


def clear_old_completed_jobs():
    """Clear old completed jobs to free up space"""
    try:
        from models.background_job import BackgroundJob
        from models.base import db
        from app import create_app
        
        app = create_app()
        
        with app.app_context():
            print("\n📦 CLEARING OLD COMPLETED JOBS")
            print("=" * 60)
            
            # Get completed jobs older than 7 days
            cutoff_time = datetime.utcnow() - timedelta(days=7)
            old_completed_jobs = BackgroundJob.query.filter(
                BackgroundJob.status == BackgroundJob.STATUS_COMPLETED,
                BackgroundJob.completed_at < cutoff_time
            ).all()
            
            if not old_completed_jobs:
                print("✅ No old completed jobs found to clear")
                return True
            
            print(f"📋 Found {len(old_completed_jobs)} completed jobs (older than 7 days):")
            
            # Show summary by job type
            job_types = {}
            for job in old_completed_jobs:
                job_types[job.job_type] = job_types.get(job.job_type, 0) + 1
            
            for job_type, count in job_types.items():
                print(f"   • {job_type}: {count} jobs")
            
            # Confirm deletion
            response = input("❓ Do you want to delete these old completed jobs? (y/N): ").strip().lower()
            if response != 'y':
                print("❌ Operation cancelled")
                return False
            
            # Delete jobs without backup (they're old and completed successfully)
            deleted_count = 0
            for job in old_completed_jobs:
                try:
                    db.session.delete(job)
                    deleted_count += 1
                except Exception as e:
                    print(f"❌ Failed to delete job {job.id}: {e}")
            
            # Commit changes
            db.session.commit()
            
            print(f"✅ Successfully deleted {deleted_count} old completed jobs")
            
            return True
            
    except Exception as e:
        print(f"❌ Error clearing old completed jobs: {e}")
        import traceback
        traceback.print_exc()
        return False


def show_current_status():
    """Show current status of tasks and jobs"""
    try:
        from models.task import Task, TaskStatus
        from models.background_job import BackgroundJob
        from models.base import db
        from app import create_app
        
        app = create_app()
        
        with app.app_context():
            print("\n📊 CURRENT KANBAN BOARD STATUS")
            print("=" * 60)
            
            # Task status summary
            print("📋 Task Status Summary:")
            total_tasks = 0
            
            # Handle enum mismatch by querying each status safely
            valid_statuses = [TaskStatus.READY, TaskStatus.RUNNING, TaskStatus.REVIEW, TaskStatus.DONE, TaskStatus.FAILED]
            
            for status in valid_statuses:
                try:
                    count = Task.query.filter_by(status=status).count()
                    total_tasks += count
                    print(f"   {status.value.upper()}: {count} tasks")
                except Exception as e:
                    print(f"   {status.value.upper()}: Error querying ({str(e)[:50]}...)")
            
            # Check for any tasks with invalid status
            try:
                all_tasks_count = Task.query.count()
                if all_tasks_count != total_tasks:
                    invalid_count = all_tasks_count - total_tasks
                    print(f"   INVALID STATUS: {invalid_count} tasks")
                    total_tasks = all_tasks_count
            except Exception as e:
                print(f"   Error getting total count: {e}")
            
            print(f"   TOTAL: {total_tasks} tasks")
            
            # Background job status summary
            print("\n🔧 Background Job Status Summary:")
            total_jobs = 0
            for status in [BackgroundJob.STATUS_PENDING, BackgroundJob.STATUS_RUNNING, 
                          BackgroundJob.STATUS_COMPLETED, BackgroundJob.STATUS_FAILED, 
                          BackgroundJob.STATUS_CANCELLED]:
                count = BackgroundJob.query.filter_by(status=status).count()
                total_jobs += count
                print(f"   {status.upper()}: {count} jobs")
            
            print(f"   TOTAL: {total_jobs} jobs")
            
            # Recent activity
            print("\n🕒 Recent Activity (last 24 hours):")
            recent_cutoff = datetime.utcnow() - timedelta(hours=24)
            
            recent_tasks = Task.query.filter(Task.updated_at >= recent_cutoff).count()
            recent_jobs = BackgroundJob.query.filter(BackgroundJob.updated_at >= recent_cutoff).count()
            
            print(f"   Tasks updated: {recent_tasks}")
            print(f"   Jobs updated: {recent_jobs}")
            
    except Exception as e:
        print(f"❌ Error showing status: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main function with menu options"""
    print("🧹 KANBAN BOARD CLEANER")
    print("=" * 60)
    print("This tool helps clean up your kanban board and Build phase UI")
    print()
    
    while True:
        print("\nOptions:")
        print("1. Show current status")
        print("2. Clear completed tasks (DONE status)")
        print("3. Clear failed Build phase jobs")
        print("4. Clear old completed jobs (7+ days)")
        print("5. Clear all (tasks + failed jobs + old jobs)")
        print("6. Exit")
        
        choice = input("\nSelect an option (1-6): ").strip()
        
        if choice == '1':
            show_current_status()
        elif choice == '2':
            clear_completed_tasks()
        elif choice == '3':
            clear_failed_build_jobs()
        elif choice == '4':
            clear_old_completed_jobs()
        elif choice == '5':
            print("\n🧹 CLEARING ALL ITEMS")
            print("=" * 60)
            success = True
            success &= clear_completed_tasks()
            success &= clear_failed_build_jobs()
            success &= clear_old_completed_jobs()
            
            if success:
                print("\n✅ All cleanup operations completed successfully!")
                show_current_status()
            else:
                print("\n❌ Some cleanup operations failed. Check the logs above.")
        elif choice == '6':
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please select 1-6.")


if __name__ == "__main__":
    main()