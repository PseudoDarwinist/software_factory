#!/usr/bin/env python3
"""
Create database migration for ADI Engine tables.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def create_migration():
    """Create migration for ADI Engine tables."""
    
    # Import the main app to ensure all models are registered
    from app import create_app
    
    app = create_app()
    
    with app.app_context():
        # Import ADI models individually to register them with SQLAlchemy
        from adi.models.decision_log import DecisionLog
        from adi.models.insight import Insight
        from adi.models.knowledge import Knowledge
        from adi.models.evaluation import EvalSet, EvalResult
        from adi.models.domain_pack import DomainPackSnapshot
        from adi.models.trend import Trend
        
        print("ADI models imported successfully:")
        print(f"- DecisionLog: {DecisionLog.__tablename__}")
        print(f"- Insight: {Insight.__tablename__}")
        print(f"- Knowledge: {Knowledge.__tablename__}")
        print(f"- EvalSet: {EvalSet.__tablename__}")
        print(f"- EvalResult: {EvalResult.__tablename__}")
        print(f"- DomainPackSnapshot: {DomainPackSnapshot.__tablename__}")
        print(f"- Trend: {Trend.__tablename__}")
        
        # Just create the tables directly for now
        try:
            from models.base import db
            db.create_all()
            print("\nADI Engine tables created successfully!")
            print("Tables are now available in the database.")
        except Exception as e:
            print(f"Error creating tables: {e}")
            return False
    
    return True

if __name__ == '__main__':
    create_migration()