#!/usr/bin/env python3
"""
SQLite to PostgreSQL Migration Script
Migrates all data from SQLite to PostgreSQL while preserving relationships
"""

import os
import sys
import sqlite3
import psycopg2
import logging
from datetime import datetime
from sqlalchemy import create_engine, MetaData, Table, select, insert
from sqlalchemy.orm import sessionmaker

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from models import db, Project, SystemMap, BackgroundJob, Conversation, Stage, FeedItem, MissionControlProject, StageTransition, ProductBrief, ChannelMapping
    from app import create_app
except ImportError as e:
    print(f"Error importing models: {e}")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DatabaseMigrator:
    """Handles migration from SQLite to PostgreSQL"""
    
    def __init__(self, sqlite_path, postgresql_uri):
        self.sqlite_path = sqlite_path
        self.postgresql_uri = postgresql_uri
        self.sqlite_engine = None
        self.postgresql_engine = None
        self.postgresql_session = None
        
    def connect_databases(self):
        """Connect to both SQLite and PostgreSQL databases"""
        try:
            # Connect to SQLite (source)
            sqlite_uri = f"sqlite:///{self.sqlite_path}"
            self.sqlite_engine = create_engine(sqlite_uri)
            logger.info(f"Connected to SQLite database: {self.sqlite_path}")
            
            # Connect to PostgreSQL (destination)
            self.postgresql_engine = create_engine(self.postgresql_uri)
            Session = sessionmaker(bind=self.postgresql_engine)
            self.postgresql_session = Session()
            logger.info(f"Connected to PostgreSQL database: {self.postgresql_uri}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to databases: {e}")
            return False
    
    def verify_sqlite_data(self):
        """Verify SQLite database has data to migrate"""
        try:
            with self.sqlite_engine.connect() as conn:
                # Get table list
                metadata = MetaData()
                metadata.reflect(bind=self.sqlite_engine)
                tables = metadata.tables.keys()
                
                logger.info(f"Found {len(tables)} tables in SQLite: {list(tables)}")
                
                # Count records in each table
                total_records = 0
                for table_name in tables:
                    table = Table(table_name, metadata, autoload_with=self.sqlite_engine)
                    from sqlalchemy import func
                    count_query = select(func.count()).select_from(table)
                    count = conn.execute(count_query).scalar()
                    logger.info(f"Table '{table_name}': {count} records")
                    total_records += count
                
                logger.info(f"Total records to migrate: {total_records}")
                return total_records > 0
                
        except Exception as e:
            logger.error(f"Error verifying SQLite data: {e}")
            return False
    
    def create_postgresql_schema(self):
        """Create PostgreSQL schema using SQLAlchemy models"""
        try:
            # Create Flask app context for models
            app = create_app()
            
            with app.app_context():
                # Override database URI for PostgreSQL
                app.config['SQLALCHEMY_DATABASE_URI'] = self.postgresql_uri
                db.init_app(app)
                
                # Create all tables
                db.create_all()
                logger.info("PostgreSQL schema created successfully")
                
                return True
                
        except Exception as e:
            logger.error(f"Error creating PostgreSQL schema: {e}")
            return False
    
    def migrate_table_data(self, table_name, model_class):
        """Migrate data from SQLite table to PostgreSQL"""
        try:
            # Get SQLite data
            sqlite_metadata = MetaData()
            sqlite_metadata.reflect(bind=self.sqlite_engine)
            
            if table_name not in sqlite_metadata.tables:
                logger.info(f"Table '{table_name}' not found in SQLite, skipping")
                return True
            
            sqlite_table = sqlite_metadata.tables[table_name]
            
            with self.sqlite_engine.connect() as sqlite_conn:
                # Fetch all data from SQLite
                result = sqlite_conn.execute(select(sqlite_table))
                rows = result.fetchall()
                
                if not rows:
                    logger.info(f"No data found in table '{table_name}', skipping")
                    return True
                
                logger.info(f"Migrating {len(rows)} records from table '{table_name}'")
                
                # Insert data into PostgreSQL
                migrated_count = 0
                for row in rows:
                    try:
                        # Convert row to dictionary
                        row_dict = dict(row._mapping)
                        
                        # Create model instance
                        instance = model_class(**row_dict)
                        
                        # Add to PostgreSQL session
                        self.postgresql_session.add(instance)
                        migrated_count += 1
                        
                        # Commit in batches
                        if migrated_count % 100 == 0:
                            self.postgresql_session.commit()
                            logger.info(f"Migrated {migrated_count} records from '{table_name}'")
                    
                    except Exception as e:
                        logger.error(f"Error migrating record from '{table_name}': {e}")
                        self.postgresql_session.rollback()
                        continue
                
                # Final commit
                self.postgresql_session.commit()
                logger.info(f"Successfully migrated {migrated_count} records from table '{table_name}'")
                
                return True
                
        except Exception as e:
            logger.error(f"Error migrating table '{table_name}': {e}")
            self.postgresql_session.rollback()
            return False
    
    def migrate_all_data(self):
        """Migrate all data from SQLite to PostgreSQL"""
        try:
            # Define migration order (respecting foreign key dependencies)
            migration_order = [
                ('project', Project),
                ('system_map', SystemMap),
                ('background_job', BackgroundJob),
                ('conversation', Conversation),
                ('stage', Stage),
                ('feed_item', FeedItem),
                ('mission_control_project', MissionControlProject),
                ('stage_transition', StageTransition),
                ('product_brief', ProductBrief),
                ('channel_mapping', ChannelMapping)
            ]
            
            total_migrated = 0
            
            for table_name, model_class in migration_order:
                if self.migrate_table_data(table_name, model_class):
                    total_migrated += 1
                else:
                    logger.error(f"Failed to migrate table: {table_name}")
            
            logger.info(f"Migration completed: {total_migrated}/{len(migration_order)} tables migrated")
            
            return total_migrated == len(migration_order)
            
        except Exception as e:
            logger.error(f"Error during migration: {e}")
            return False
    
    def verify_migration(self):
        """Verify that migration was successful"""
        try:
            logger.info("Verifying migration results...")
            
            # Check each table
            app = create_app()
            with app.app_context():
                app.config['SQLALCHEMY_DATABASE_URI'] = self.postgresql_uri
                db.init_app(app)
                
                models = [
                    ('Projects', Project),
                    ('SystemMaps', SystemMap),
                    ('BackgroundJobs', BackgroundJob),
                    ('Conversations', Conversation),
                    ('Stages', Stage),
                    ('FeedItems', FeedItem),
                    ('MissionControlProjects', MissionControlProject),
                    ('StageTransitions', StageTransition),
                    ('ProductBriefs', ProductBrief),
                    ('ChannelMappings', ChannelMapping)
                ]
                
                for name, model in models:
                    count = db.session.query(model).count()
                    logger.info(f"PostgreSQL {name}: {count} records")
                
                logger.info("Migration verification completed")
                return True
                
        except Exception as e:
            logger.error(f"Error verifying migration: {e}")
            return False
    
    def create_backup(self):
        """Create backup of SQLite database before migration"""
        try:
            if not os.path.exists(self.sqlite_path):
                logger.warning(f"SQLite database not found: {self.sqlite_path}")
                return True
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{self.sqlite_path}.backup_{timestamp}"
            
            import shutil
            shutil.copy2(self.sqlite_path, backup_path)
            logger.info(f"Created backup: {backup_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return False
    
    def run_migration(self):
        """Run the complete migration process"""
        logger.info("Starting SQLite to PostgreSQL migration...")
        
        # Step 1: Create backup
        if not self.create_backup():
            logger.error("Failed to create backup, aborting migration")
            return False
        
        # Step 2: Connect to databases
        if not self.connect_databases():
            logger.error("Failed to connect to databases, aborting migration")
            return False
        
        # Step 3: Verify SQLite data
        if not self.verify_sqlite_data():
            logger.warning("No data found in SQLite database")
            return True
        
        # Step 4: Create PostgreSQL schema
        if not self.create_postgresql_schema():
            logger.error("Failed to create PostgreSQL schema, aborting migration")
            return False
        
        # Step 5: Migrate data
        if not self.migrate_all_data():
            logger.error("Migration failed")
            return False
        
        # Step 6: Verify migration
        if not self.verify_migration():
            logger.error("Migration verification failed")
            return False
        
        logger.info("Migration completed successfully!")
        return True
    
    def close_connections(self):
        """Close all database connections"""
        if self.postgresql_session:
            self.postgresql_session.close()
        if self.sqlite_engine:
            self.sqlite_engine.dispose()
        if self.postgresql_engine:
            self.postgresql_engine.dispose()


def main():
    """Main migration function"""
    # Configuration
    sqlite_path = os.path.join(os.path.dirname(__file__), '..', 'instance', 'mission_control.db')
    postgresql_uri = "postgresql://sf_user:sf_password@localhost/software_factory"
    
    # Check if SQLite database exists
    if not os.path.exists(sqlite_path):
        print(f"SQLite database not found at: {sqlite_path}")
        print("Creating new PostgreSQL database without migration...")
        
        # Just create the schema
        try:
            app = create_app()
            with app.app_context():
                app.config['SQLALCHEMY_DATABASE_URI'] = postgresql_uri
                db.init_app(app)
                db.create_all()
                print("PostgreSQL schema created successfully")
                return True
        except Exception as e:
            print(f"Error creating PostgreSQL schema: {e}")
            return False
    
    # Run migration
    migrator = DatabaseMigrator(sqlite_path, postgresql_uri)
    
    try:
        success = migrator.run_migration()
        return success
    finally:
        migrator.close_connections()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)