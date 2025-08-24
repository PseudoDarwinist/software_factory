#!/usr/bin/env python3
"""
Fix both taskstatus and taskpriority enums in the database to use lowercase values.
This resolves the issue where SQLAlchemy can't match database enum values to Python enum values.
"""

import os
import psycopg2
from psycopg2 import sql

# Get database connection from environment
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://sf_user:sf_password@localhost/software_factory')

def fix_enums():
    """Fix the enum values in the database"""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    try:
        # Start transaction
        conn.autocommit = False
        
        # First, let's check what we're dealing with
        print("Current enum values:")
        cur.execute("SELECT enum_range(NULL::taskstatus) AS status_values, enum_range(NULL::taskpriority) AS priority_values;")
        result = cur.fetchone()
        print(f"TaskStatus: {result[0]}")
        print(f"TaskPriority: {result[1]}")
        
        # Check current data
        print("\nChecking current task data...")
        cur.execute("SELECT COUNT(*) FROM task WHERE id LIKE 'wo_spec_%';")
        wo_count = cur.fetchone()[0]
        print(f"Found {wo_count} work order tasks")
        
        # Fix priority enum (if needed)
        if 'MEDIUM' in str(result[1]) or 'LOW' in str(result[1]):
            print("\n=== Fixing taskpriority enum ===")
            
            # Create new enum type with lowercase values
            print("Creating new taskpriority enum...")
            cur.execute("CREATE TYPE taskpriority_new AS ENUM ('low', 'medium', 'high', 'critical');")
            
            # Update the column to use the new enum, converting values to lowercase
            print("Updating priority column...")
            cur.execute("""
                ALTER TABLE task 
                ALTER COLUMN priority TYPE taskpriority_new 
                USING LOWER(priority::text)::taskpriority_new;
            """)
            
            # Drop old enum and rename new one
            cur.execute("DROP TYPE taskpriority;")
            cur.execute("ALTER TYPE taskpriority_new RENAME TO taskpriority;")
            print("✓ Fixed taskpriority enum")
        else:
            print("\n✓ taskpriority enum already has lowercase values")
        
        # Fix status enum (if needed)
        if 'READY' in str(result[0]) or 'RUNNING' in str(result[0]):
            print("\n=== Fixing taskstatus enum ===")
            
            # Create new enum type with lowercase values
            print("Creating new taskstatus enum...")
            cur.execute("CREATE TYPE taskstatus_new AS ENUM ('backlog', 'ready', 'running', 'review', 'done', 'failed', 'needs_rework');")
            
            # Update the column to use the new enum, handling various cases
            print("Updating status column...")
            cur.execute("""
                ALTER TABLE task 
                ALTER COLUMN status TYPE taskstatus_new 
                USING CASE 
                    WHEN status::text = 'READY' THEN 'ready'
                    WHEN status::text = 'RUNNING' THEN 'running'
                    WHEN status::text = 'REVIEW' THEN 'review'
                    WHEN status::text = 'DONE' THEN 'done'
                    WHEN status::text = 'FAILED' THEN 'failed'
                    WHEN status::text = 'IN_PROGRESS' THEN 'running'
                    WHEN status::text = 'BLOCKED' THEN 'backlog'
                    WHEN status::text = 'needs_rework' THEN 'needs_rework'
                    WHEN status::text = 'backlog' THEN 'backlog'
                    ELSE LOWER(status::text)
                END::taskstatus_new;
            """)
            
            # Drop old enum and rename new one
            cur.execute("DROP TYPE taskstatus;")
            cur.execute("ALTER TYPE taskstatus_new RENAME TO taskstatus;")
            print("✓ Fixed taskstatus enum")
        else:
            print("\n✓ taskstatus enum already has lowercase values")
        
        # Recreate indexes that reference these columns
        print("\nRecreating indexes...")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_status_priority ON task(status, priority);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_assigned_status ON task(assigned_to, status);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_task_project_id_status ON task(project_id, status);")
        print("✓ Indexes recreated")
        
        # Commit transaction
        conn.commit()
        print("\n✅ All changes committed successfully!")
        
        # Verify the fix
        print("\n=== Verification ===")
        cur.execute("SELECT enum_range(NULL::taskstatus) AS status_values, enum_range(NULL::taskpriority) AS priority_values;")
        result = cur.fetchone()
        print(f"New TaskStatus values: {result[0]}")
        print(f"New TaskPriority values: {result[1]}")
        
        # Check some data
        print("\nSample work order tasks after fix:")
        cur.execute("SELECT id, status, priority FROM task WHERE id LIKE 'wo_spec_%' ORDER BY created_at DESC LIMIT 3;")
        for row in cur.fetchall():
            print(f"  {row[0][:50]}...: status={row[1]}, priority={row[2]}")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    fix_enums()
    print("\n✅ Enum fix completed!")
