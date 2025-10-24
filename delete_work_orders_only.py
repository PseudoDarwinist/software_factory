#!/usr/bin/env python3
"""
Delete only work orders (IDs starting with 'wo_') from task table
"""

import os
import sys
import psycopg2
from urllib.parse import urlparse

def delete_work_orders_only():
    """Delete only work orders (wo_ prefix) from task table"""
    try:
        # Get database URL
        database_url = os.getenv('DATABASE_URL', 'postgresql://localhost/software_factory')
        parsed = urlparse(database_url)
        
        # Connect to PostgreSQL
        conn = psycopg2.connect(
            host=parsed.hostname or 'localhost',
            port=parsed.port or 5432,
            database=parsed.path.lstrip('/') if parsed.path else 'software_factory',
            user=parsed.username or os.getenv('USER', 'postgres'),
            password=parsed.password or ''
        )
        
        cursor = conn.cursor()
        
        project_id = 'project_1753319732860_xct3cc4z5'
        
        print(f"Looking for work orders (wo_ prefix) in project: {project_id}")
        
        # First, check what we have
        cursor.execute("""
            SELECT id, title, created_at 
            FROM task 
            WHERE project_id = %s AND id LIKE 'wo_%%'
            ORDER BY created_at DESC
        """, (project_id,))
        
        work_orders = cursor.fetchall()
        print(f"Found {len(work_orders)} work orders:")
        
        for wo_id, title, created_at in work_orders:
            print(f"  {wo_id}: {title} ({created_at})")
        
        if work_orders:
            print(f"\nDeleting {len(work_orders)} work orders...")
            
            # Delete only work orders (wo_ prefix)
            cursor.execute("""
                DELETE FROM task 
                WHERE project_id = %s AND id LIKE 'wo_%%'
            """, (project_id,))
            
            conn.commit()
            print(f"✅ Deleted {len(work_orders)} work orders")
            
            # Verify regular tasks are still there
            cursor.execute("""
                SELECT COUNT(*) 
                FROM task 
                WHERE project_id = %s AND id NOT LIKE 'wo_%%'
            """, (project_id,))
            
            remaining_tasks = cursor.fetchone()[0]
            print(f"✅ {remaining_tasks} regular tasks remain untouched")
        else:
            print("No work orders found to delete")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    delete_work_orders_only()