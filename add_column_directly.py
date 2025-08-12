#!/usr/bin/env python3
"""
Directly add job_metadata column to BackgroundJob table
"""

import sys
import os
sys.path.append('src')

def add_metadata_column():
    """Add job_metadata column directly to the database"""
    
    try:
        # Import database connection
        from flask import Flask
        from models import db
        
        # Create Flask app
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///software_factory.db')
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        # Initialize database
        db.init_app(app)
        
        with app.app_context():
            # Check if column already exists
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('background_job')]
            
            if 'job_metadata' in columns:
                print("✅ job_metadata column already exists")
                return True
            
            print("🔧 Adding job_metadata column to background_job table...")
            
            # Add the column using raw SQL
            if 'sqlite' in str(db.engine.url):
                # SQLite
                db.engine.execute('ALTER TABLE background_job ADD COLUMN job_metadata TEXT')
                print("✅ Added job_metadata column (SQLite TEXT)")
            else:
                # PostgreSQL or other
                db.engine.execute('ALTER TABLE background_job ADD COLUMN job_metadata JSON')
                print("✅ Added job_metadata column (JSON)")
            
            # Verify the column was added
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('background_job')]
            
            if 'job_metadata' in columns:
                print("✅ Column successfully added and verified")
                return True
            else:
                print("❌ Column was not added successfully")
                return False
                
    except Exception as e:
        print(f"❌ Failed to add column: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = add_metadata_column()
    if success:
        print("\n🎉 Database updated successfully! You can now test async spec generation.")
    else:
        print("\n💥 Database update failed. You may need to add the column manually.")
    sys.exit(0 if success else 1)