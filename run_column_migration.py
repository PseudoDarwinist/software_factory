#!/usr/bin/env python3
"""
Run the column limit increase migration
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.app import create_app
from src.models.base import db
from sqlalchemy import text

def run_migration():
    """Run the column limit increase migration"""
    print("🔧 Running column limit increase migration...")
    
    # Create Flask app
    app = create_app()
    
    with app.app_context():
        try:
            # Read the SQL migration file
            with open('increase_task_column_limits.sql', 'r') as f:
                sql_commands = f.read()
            
            # Split by semicolon and execute each command
            commands = [cmd.strip() for cmd in sql_commands.split(';') if cmd.strip() and not cmd.strip().startswith('--')]
            print(f"📋 Found {len(commands)} commands to execute:")
            for i, cmd in enumerate(commands, 1):
                print(f"   {i}. {cmd[:100]}...")
            
            # Use the Flask app's database session directly
            from flask import current_app
            db_extension = current_app.extensions['sqlalchemy']
            
            for i, command in enumerate(commands, 1):
                print(f"📝 Executing command {i}/{len(commands)}: {command[:50]}...")
                db_extension.session.execute(text(command))
            
            # Commit all changes
            db_extension.session.commit()
            print("✅ Migration completed successfully!")
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            # Use the Flask app's database session for rollback too
            from flask import current_app
            db_extension = current_app.extensions['sqlalchemy']
            db_extension.session.rollback()
            import traceback
            traceback.print_exc()
            return False
    
    return True

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)