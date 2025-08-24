#!/usr/bin/env python3
"""
Create database migration for BackgroundJob metadata field
"""

import sys
import os
sys.path.append('src')

from flask import Flask
from flask_migrate import Migrate, init, migrate, upgrade
from models import db

def create_migration():
    """Create and apply migration for BackgroundJob metadata field"""
    
    # Create Flask app
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///software_factory.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize database and migrations
    db.init_app(app)
    migrate_obj = Migrate(app, db)
    
    with app.app_context():
        try:
            # Check if migrations directory exists
            if not os.path.exists('migrations'):
                print("🔧 Initializing migrations...")
                init()
            
            # Create migration for metadata field
            print("🔧 Creating migration for BackgroundJob metadata field...")
            migrate(message="Add metadata field to BackgroundJob")
            
            # Apply migration
            print("🔧 Applying migration...")
            upgrade()
            
            print("✅ Migration completed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = create_migration()
    sys.exit(0 if success else 1)