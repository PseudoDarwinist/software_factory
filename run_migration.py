#!/usr/bin/env python3
"""
Run database migration to add related_idea field
"""

import os
import sys
sys.path.append('.')

from src.app import create_app
from flask_migrate import upgrade

def run_migration():
    """Run the migration"""
    try:
        app = create_app()
        with app.app_context():
            upgrade()
        print('✅ Migration completed successfully')
        return True
    except Exception as e:
        print(f'❌ Migration failed: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = run_migration()
    sys.exit(0 if success else 1)