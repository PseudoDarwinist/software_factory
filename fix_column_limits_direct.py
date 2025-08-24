#!/usr/bin/env python3
"""
Direct fix for column limits - run each ALTER TABLE command individually
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.app import create_app
from sqlalchemy import text

def fix_column_limits():
    """Fix column limits directly"""
    print("🔧 Fixing column limits directly...")
    
    # Create Flask app
    app = create_app()
    
    with app.app_context():
        try:
            # Use the Flask app's database session directly
            from flask import current_app
            db_extension = current_app.extensions['sqlalchemy']
            
            # Define the ALTER TABLE commands
            commands = [
                "ALTER TABLE task ALTER COLUMN goal_line TYPE VARCHAR(1000)",
                "ALTER TABLE task ALTER COLUMN blueprint_section_ref TYPE VARCHAR(1000)", 
                "ALTER TABLE task ALTER COLUMN branch_name TYPE VARCHAR(500)"
            ]
            
            for i, command in enumerate(commands, 1):
                print(f"📝 Executing command {i}/{len(commands)}: {command}")
                try:
                    db_extension.session.execute(text(command))
                    print(f"   ✅ Success")
                except Exception as e:
                    print(f"   ⚠️  Warning: {e}")
                    # Continue with other commands even if one fails
            
            # Commit all changes
            db_extension.session.commit()
            print("✅ Column limit fixes completed!")
            
        except Exception as e:
            print(f"❌ Fix failed: {e}")
            from flask import current_app
            db_extension = current_app.extensions['sqlalchemy']
            db_extension.session.rollback()
            import traceback
            traceback.print_exc()
            return False
    
    return True

if __name__ == "__main__":
    success = fix_column_limits()
    sys.exit(0 if success else 1)