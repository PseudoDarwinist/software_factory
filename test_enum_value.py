#!/usr/bin/env python3
"""Test script to verify enum value handling in SQLAlchemy"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.models.task import TaskStatus, TaskPriority

# Test enum values
print("Testing TaskStatus enum values:")
print(f"TaskStatus.BACKLOG = {TaskStatus.BACKLOG}")
print(f"TaskStatus.BACKLOG.value = {TaskStatus.BACKLOG.value}")
print(f"TaskStatus.BACKLOG.name = {TaskStatus.BACKLOG.name}")
print()

print("Testing TaskPriority enum values:")
print(f"TaskPriority.MEDIUM = {TaskPriority.MEDIUM}")
print(f"TaskPriority.MEDIUM.value = {TaskPriority.MEDIUM.value}")
print(f"TaskPriority.MEDIUM.name = {TaskPriority.MEDIUM.name}")
print()

# Test what SQLAlchemy would receive
print("What SQLAlchemy sees:")
print(f"Type of TaskStatus.BACKLOG: {type(TaskStatus.BACKLOG)}")
print(f"String representation: {str(TaskStatus.BACKLOG)}")

# Test database interaction
try:
    from flask import Flask
    from src.app import create_app
    
    app = create_app()
    with app.app_context():
        from src.models.task import Task, db
        
        # Create a test task
        test_task = Task(
            id="test_enum_001",
            spec_id="spec_test",
            project_id="proj_test",
            title="Test Enum Value",
            status=TaskStatus.BACKLOG,
            priority=TaskPriority.MEDIUM,
            created_by="test_script"
        )
        
        # Check what values are being set
        print("\nTask object before save:")
        print(f"task.status = {test_task.status}")
        print(f"task.status type = {type(test_task.status)}")
        print(f"task.priority = {test_task.priority}")
        print(f"task.priority type = {type(test_task.priority)}")
        
        # Try to save
        try:
            db.session.add(test_task)
            db.session.commit()
            print("\n✅ Task saved successfully!")
            
            # Clean up
            db.session.delete(test_task)
            db.session.commit()
            print("✅ Test task cleaned up")
            
        except Exception as e:
            print(f"\n❌ Error saving task: {e}")
            db.session.rollback()
            
except Exception as e:
    print(f"\n⚠️ Could not test database interaction: {e}")
