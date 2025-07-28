#!/usr/bin/env python3
"""
Script to apply database migrations
"""

import os
import sys
from flask_migrate import upgrade
from src.app import create_app

def apply_migrations():
    """Apply pending database migrations"""
    try:
        print("🔄 Creating Flask app...")
        app = create_app()
        
        with app.app_context():
            print("🔄 Applying database migrations...")
            upgrade()
            print("✅ Database migrations applied successfully!")
            
    except Exception as e:
        print(f"❌ Error applying migrations: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    apply_migrations()