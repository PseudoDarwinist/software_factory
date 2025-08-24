#!/usr/bin/env python3
"""
Fix the taskstatus enum to use lowercase values to match the model
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.app import create_app
from sqlalchemy import text

def fix_enum_values():
    """Fix the taskstatus enum values"""
    print("🔧 Fixing taskstatus enum values...")
    
    # Create Flask app
    app = create_app()
    
    with app.app_context():
        try:
            # Use the Flask app's database session directly
            from flask import current_app
            db_extension = current_app.extensions['sqlalchemy']
            
            # First, let's see what we're working with
            print("📋 Checking current enum values...")
            result = db_extension.session.execute(text("""
                SELECT enumlabel 
                FROM pg_enum 
                WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'taskstatus')
                ORDER BY enumsortorder;
            """))
            current_values = [row[0] for row in result]
            print(f"   Current values: {current_values}")
            
            # Check if we need to fix anything
            expected_values = ['backlog', 'ready', 'running', 'review', 'done', 'failed', 'needs_rework']
            
            if set(current_values) == set(expected_values):
                print("✅ Enum values are already correct!")
                return True
            
            print("🔄 Need to update enum values to lowercase...")
            
            # Create a new enum type with lowercase values
            print("📝 Creating new enum type...")
            db_extension.session.execute(text("""
                CREATE TYPE taskstatus_new AS ENUM (
                    'backlog', 'ready', 'running', 'review', 'done', 'failed', 'needs_rework'
                );
            """))
            
            # Update the table to use the new enum
            print("📝 Updating table to use new enum...")
            db_extension.session.execute(text("""
                ALTER TABLE task 
                ALTER COLUMN status TYPE taskstatus_new 
                USING status::text::taskstatus_new;
            """))
            
            # Drop the old enum and rename the new one
            print("📝 Replacing old enum...")
            db_extension.session.execute(text("DROP TYPE taskstatus;"))
            db_extension.session.execute(text("ALTER TYPE taskstatus_new RENAME TO taskstatus;"))
            
            # Commit all changes
            db_extension.session.commit()
            print("✅ Enum values fixed successfully!")
            
        except Exception as e:
            print(f"❌ Error fixing enum values: {e}")
            from flask import current_app
            db_extension = current_app.extensions['sqlalchemy']
            db_extension.session.rollback()
            import traceback
            traceback.print_exc()
            return False
    
    return True

if __name__ == "__main__":
    success = fix_enum_values()
    sys.exit(0 if success else 1)