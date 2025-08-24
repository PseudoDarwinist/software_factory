#!/usr/bin/env python3
"""
Create migration for ADI findings table.
"""

import os
import sys
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from flask import Flask
from flask_migrate import Migrate
from models.base import db

def create_migration():
    """Create a new migration for the ADI findings table."""
    
    # Create Flask app
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///instance/software_factory.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions
    db.init_app(app)
    migrate = Migrate(app, db)
    
    with app.app_context():
        # Import models to register them
        from adi.models.finding import Finding
        
        # Create migration
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        migration_name = f"019_add_adi_findings_table"
        
        print(f"Creating migration: {migration_name}")
        
        # Use Flask-Migrate to create the migration
        os.system(f'cd {os.path.dirname(__file__)} && flask db migrate -m "Add ADI findings table"')
        
        print("Migration created successfully!")
        print("Run 'flask db upgrade' to apply the migration.")

if __name__ == '__main__':
    create_migration()