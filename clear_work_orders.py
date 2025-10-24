#!/usr/bin/env python3
"""
Utility script to clear existing work orders for a specific spec
"""

from src.app import create_app
from src.models.task import Task
from src.models.base import db

def clear_work_orders(spec_id, project_id):
    """Clear all work orders for a given spec"""
    app = create_app()
    with app.app_context():
        print(f'Looking for tasks with spec_id: {spec_id}')
        
        # Get existing tasks for this spec
        existing_tasks = db.session.query(Task).filter_by(spec_id=spec_id, project_id=project_id).all()
        
        print(f'Found {len(existing_tasks)} existing tasks')
        
        if existing_tasks:
            print('Existing tasks:')
            for task in existing_tasks:
                print(f'  - {task.id}: {task.title} (Status: {task.status.value if task.status else "None"})')
            
            # Delete all tasks
            for task in existing_tasks:
                db.session.delete(task)
            
            db.session.commit()
            print(f'✅ Deleted {len(existing_tasks)} tasks')
        else:
            print('No existing tasks found for this spec')

if __name__ == '__main__':
    # From the logs, these are the IDs being used
    spec_id = 'spec_slack_C095S2NQQMV_1755327474.872009_22cea1a2'
    project_id = 'project_1753319732860_xct3cc4z5'
    
    clear_work_orders(spec_id, project_id)