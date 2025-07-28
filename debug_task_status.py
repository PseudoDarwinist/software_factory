#!/usr/bin/env python3
"""
Debug script to check task statuses and dependencies
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.app import create_app
from src.models.task import Task, TaskStatus
from src.models.base import db

def main():
    app = create_app()
    with app.app_context():
        print("=== Task Status Debug ===")
        
        # Get all tasks
        tasks = Task.query.all()
        print(f"Total tasks: {len(tasks)}")
        
        # Group by status
        status_counts = {}
        for task in tasks:
            status = task.status.value if task.status else 'None'
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print("\nStatus distribution:")
        for status, count in status_counts.items():
            print(f"  {status}: {count}")
        
        # Check first few tasks in detail
        print("\nFirst 5 tasks details:")
        for i, task in enumerate(tasks[:5]):
            print(f"\nTask {i+1}:")
            print(f"  ID: {task.id}")
            print(f"  Title: {task.title}")
            print(f"  Status: {task.status.value if task.status else 'None'}")
            print(f"  Dependencies: {task.depends_on}")
            print(f"  Can start: {task.can_start()}")
            
            if task.depends_on:
                print("  Dependency details:")
                deps = task.get_dependencies()
                for dep in deps:
                    print(f"    - {dep.id}: {dep.status.value}")

if __name__ == "__main__":
    main()