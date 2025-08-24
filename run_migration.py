#!/usr/bin/env python3
"""
Run database migration to add work order enhancement fields
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def run_migration():
    """Run the database migration"""
    
    # Database connection parameters
    db_params = {
        'host': 'localhost',
        'database': 'software_factory',
        'user': 'sf_user',
        'password': 'sf_password',
        'port': 5432
    }
    
    try:
        # Connect to database
        print("Connecting to database...")
        conn = psycopg2.connect(**db_params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Read migration SQL
        print("Reading migration SQL...")
        with open('add_work_order_enhancement_fields.sql', 'r') as f:
            migration_sql = f.read()
        
        # Execute migration
        print("Executing migration...")
        cursor.execute(migration_sql)
        
        print("✅ Migration completed successfully!")
        
        # Verify the changes
        print("\nVerifying new columns...")
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default 
            FROM information_schema.columns 
            WHERE table_name = 'task' 
            AND column_name IN (
                'enhancement_status', 'implementation_approach', 'implementation_goals',
                'implementation_strategy', 'technical_dependencies', 'files_to_create',
                'files_to_modify', 'blueprint_section_ref', 'codebase_context',
                'enhanced_at', 'enhanced_by', 'approved_at', 'approved_by'
            )
            ORDER BY column_name;
        """)
        
        results = cursor.fetchall()
        if results:
            print("New columns added:")
            for row in results:
                print(f"  - {row[0]} ({row[1]})")
        else:
            print("❌ No new columns found!")
        
        # Check if BACKLOG status was added to enum
        print("\nChecking taskstatus enum...")
        cursor.execute("""
            SELECT enumlabel 
            FROM pg_enum 
            WHERE enumtypid = (
                SELECT oid FROM pg_type WHERE typname = 'taskstatus'
            )
            ORDER BY enumlabel;
        """)
        
        enum_values = [row[0] for row in cursor.fetchall()]
        print(f"TaskStatus enum values: {enum_values}")
        
        if 'backlog' in enum_values:
            print("✅ BACKLOG status added to enum")
        else:
            print("❌ BACKLOG status not found in enum")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_migration()