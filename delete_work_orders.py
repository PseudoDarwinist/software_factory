#!/usr/bin/env python3
"""
Simple script to delete work orders for a specific spec
"""

import os
import sys

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def delete_work_orders():
    """Delete work orders using direct SQL to avoid Flask context issues"""
    try:
        import psycopg2
        from urllib.parse import urlparse
        
        # Get database URL from environment or use default
        database_url = os.getenv('DATABASE_URL', 'postgresql://localhost/software_factory')
        
        # Parse the URL
        parsed = urlparse(database_url)
        
        # Connect directly to PostgreSQL
        conn = psycopg2.connect(
            host=parsed.hostname or 'localhost',
            port=parsed.port or 5432,
            database=parsed.path.lstrip('/') if parsed.path else 'software_factory',
            user=parsed.username or os.getenv('USER', 'postgres'),
            password=parsed.password or ''
        )
        
        cursor = conn.cursor()
        
        # The spec ID from the logs
        spec_id = 'spec_slack_C095S2NQQMV_1755327474.872009_22cea1a2'
        project_id = 'project_1753319732860_xct3cc4z5'
        
        print(f"Looking for tasks with spec_id: {spec_id}")
        
        # First, check how many tasks exist
        cursor.execute(
            "SELECT COUNT(*) FROM task WHERE spec_id = %s AND project_id = %s",
            (spec_id, project_id)
        )
        count = cursor.fetchone()[0]
        print(f"Found {count} tasks to delete")
        
        if count > 0:
            # Delete the tasks
            cursor.execute(
                "DELETE FROM task WHERE spec_id = %s AND project_id = %s",
                (spec_id, project_id)
            )
            
            # Commit the changes
            conn.commit()
            print(f"✅ Successfully deleted {count} work orders")
        else:
            print("No work orders found to delete")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure PostgreSQL is running and accessible")

if __name__ == '__main__':
    delete_work_orders()