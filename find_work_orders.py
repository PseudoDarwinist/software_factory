#!/usr/bin/env python3
"""
Find all work orders in the project to see what's actually there
"""

import os
import sys
import psycopg2
from urllib.parse import urlparse

def find_all_work_orders():
    """Find all work orders in the project"""
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
        
        print(f"Finding all work orders in project: {project_id}")
        
        # Get all tasks in this project
        cursor.execute(
            "SELECT id, spec_id, title, status, created_at FROM task WHERE project_id = %s ORDER BY created_at DESC LIMIT 10",
            (project_id,)
        )
        
        results = cursor.fetchall()
        print(f"\nFound {len(results)} recent tasks:")
        
        for task_id, spec_id, title, status, created_at in results:
            print(f"  ID: {task_id}")
            print(f"  Spec: {spec_id}")
            print(f"  Title: {title}")
            print(f"  Status: {status}")
            print(f"  Created: {created_at}")
            print("  ---")
        
        # Also check by different spec patterns
        print("\nChecking for work orders with different spec patterns:")
        
        # Check for spec_project pattern
        cursor.execute(
            "SELECT COUNT(*), spec_id FROM task WHERE project_id = %s AND spec_id LIKE 'spec_project%' GROUP BY spec_id",
            (project_id,)
        )
        
        project_specs = cursor.fetchall()
        for count, spec_id in project_specs:
            print(f"  {spec_id}: {count} tasks")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    find_all_work_orders()