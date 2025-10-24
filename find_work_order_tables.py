#!/usr/bin/env python3
"""
Find what tables exist for work orders vs tasks
"""

import os
import sys
import psycopg2
from urllib.parse import urlparse

def find_work_order_tables():
    """Find what tables exist for work orders"""
    try:
        # Get database URL
        database_url = os.getenv('DATABASE_URL', 'postgresql://localhost/software_factory')
        parsed = urlparse(database_url)
        
        # Connect to PostgreSQL
        conn = psycopg2.connect(
            host=parsed.hostname or 'localhost',
            port=parsed.port or 5432,
            database=parsed.path.lstrip('/') if parsed.path else 'software_factory',
            user=parsed.username or os.getenv('USER', 'postgres'),
            password=parsed.password or ''
        )
        
        cursor = conn.cursor()
        
        print("Looking for tables that might contain work orders...")
        
        # Check what tables exist
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE '%work%' OR table_name LIKE '%order%'
            ORDER BY table_name
        """)
        
        work_tables = cursor.fetchall()
        print("Tables with 'work' or 'order' in name:")
        for (table_name,) in work_tables:
            print(f"  {table_name}")
        
        # Check if there's a separate work_order table
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """)
        
        all_tables = cursor.fetchall()
        print(f"\nAll tables in database:")
        for (table_name,) in all_tables:
            print(f"  {table_name}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    find_work_order_tables()