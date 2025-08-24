#!/usr/bin/env python3
"""
Query ideas from the PostgreSQL database
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from app import create_app
    from models.feed_item import FeedItem
    from models.base import db
except ImportError:
    # Fallback for direct execution
    from src.app import create_app
    from src.models.feed_item import FeedItem
    from src.models.base import db

def query_ideas():
    """Query and display ideas from the database"""
    app = create_app()
    
    with app.app_context():
        try:
            # Query for ideas, ordered by creation date (newest first)
            ideas = FeedItem.query.filter_by(kind=FeedItem.KIND_IDEA).order_by(FeedItem.created_at.desc()).limit(10).all()
            
            if not ideas:
                print("No ideas found in the database.")
                return
            
            print(f"Found {len(ideas)} ideas:")
            print("-" * 80)
            
            for idea in ideas:
                print(f"ID: {idea.id}")
                print(f"Title: {idea.title}")
                print(f"Project ID: {idea.project_id}")
                print(f"Kind: {idea.kind}")
                print(f"Summary: {idea.summary or 'No summary'}")
                print(f"Actor: {idea.actor or 'Unknown'}")
                print(f"Created: {idea.created_at}")
                print(f"Unread: {idea.unread}")
                if idea.meta_data:
                    print(f"Metadata: {idea.meta_data}")
                print("-" * 80)
                
        except Exception as e:
            print(f"Error querying database: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    query_ideas()