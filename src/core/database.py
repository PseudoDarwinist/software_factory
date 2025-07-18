"""
Database utilities and migration system
Handles database initialization, migrations, and utility functions
"""

import os
import logging
from datetime import datetime, timedelta
from flask import current_app
from flask_migrate import Migrate, init as migrate_init, migrate as migrate_migrate, upgrade as migrate_upgrade
from sqlalchemy import text
import json
import shutil

# Import will be set by app initialization
db = None
migrate = None

logger = logging.getLogger(__name__)


def init_database_system(app, database, migration):
    """Initialize the database system with Flask app"""
    global db, migrate
    db = database
    migrate = migration
    
    # Check if migrations directory exists and is properly initialized
    migrations_dir = os.path.join(app.root_path, '..', 'migrations')  # Use existing migrations dir
    if not os.path.exists(migrations_dir):
        with app.app_context():
            try:
                migrate_init()
                app.logger.info("Flask-Migrate initialized")
            except Exception as e:
                app.logger.error(f"Failed to initialize Flask-Migrate: {e}")
    else:
        app.logger.info("Using existing migrations directory")
    
    app.logger.info("Database system initialized")


def create_all_tables(app):
    """Create all database tables"""
    with app.app_context():
        try:
            # Import models to ensure they're registered
            try:
                from .. import models
            except ImportError:
                import sys
                import os
                sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
                import models
            
            db.create_all()
            app.logger.info("All database tables created successfully")
            return True
        except Exception as e:
            app.logger.error(f"Failed to create database tables: {e}")
            return False


def check_database_health():
    """Check database connection and basic functionality"""
    try:
        # Test basic connection
        result = db.session.execute(text('SELECT 1')).scalar()
        if result != 1:
            return {'status': 'unhealthy', 'message': 'Database query returned unexpected result'}
        
        # Test table existence
        try:
            from ..models import Project, SystemMap, BackgroundJob, Conversation
        except ImportError:
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
            from models import Project, SystemMap, BackgroundJob, Conversation
        
        tables_exist = True
        missing_tables = []
        
        for model in [Project, SystemMap, BackgroundJob, Conversation]:
            try:
                db.session.execute(text(f'SELECT 1 FROM {model.__tablename__} LIMIT 1'))
            except Exception:
                tables_exist = False
                missing_tables.append(model.__tablename__)
        
        if not tables_exist:
            return {
                'status': 'unhealthy', 
                'message': f'Missing tables: {", ".join(missing_tables)}'
            }
        
        return {
            'status': 'healthy', 
            'message': 'Database connection and tables are working properly'
        }
        
    except Exception as e:
        return {
            'status': 'unhealthy', 
            'message': f'Database health check failed: {str(e)}'
        }


def get_database_statistics():
    """Get comprehensive database statistics"""
    try:
        try:
            from ..models import Project, SystemMap, BackgroundJob, Conversation
        except ImportError:
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
            from models import Project, SystemMap, BackgroundJob, Conversation
        
        stats = {
            'tables': {
                'projects': Project.query.count(),
                'system_maps': SystemMap.query.count(),
                'background_jobs': BackgroundJob.query.count(),
                'conversations': Conversation.query.count()
            },
            'background_jobs': {
                'pending': BackgroundJob.query.filter_by(status=BackgroundJob.STATUS_PENDING).count(),
                'running': BackgroundJob.query.filter_by(status=BackgroundJob.STATUS_RUNNING).count(),
                'completed': BackgroundJob.query.filter_by(status=BackgroundJob.STATUS_COMPLETED).count(),
                'failed': BackgroundJob.query.filter_by(status=BackgroundJob.STATUS_FAILED).count()
            },
            'projects_by_status': {}
        }
        
        # Get project status distribution
        project_statuses = db.session.query(Project.status, db.func.count(Project.id)).group_by(Project.status).all()
        for status, count in project_statuses:
            stats['projects_by_status'][status or 'unknown'] = count
        
        # Database file size (for SQLite)
        db_uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
        if db_uri.startswith('sqlite:///'):
            db_path = db_uri.replace('sqlite:///', '')
            if os.path.exists(db_path):
                stats['database_size_bytes'] = os.path.getsize(db_path)
                stats['database_size_mb'] = round(stats['database_size_bytes'] / (1024 * 1024), 2)
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get database statistics: {e}")
        return {'error': f'Failed to get database statistics: {str(e)}'}


def cleanup_old_background_jobs(days_old=7):
    """Clean up completed and failed background jobs older than specified days"""
    try:
        from ..models import BackgroundJob
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        # Find old completed and failed jobs
        old_jobs_query = BackgroundJob.query.filter(
            BackgroundJob.status.in_([BackgroundJob.STATUS_COMPLETED, BackgroundJob.STATUS_FAILED]),
            BackgroundJob.completed_at < cutoff_date
        )
        
        old_jobs = old_jobs_query.all()
        count = len(old_jobs)
        
        # Delete old jobs
        for job in old_jobs:
            db.session.delete(job)
        
        db.session.commit()
        
        logger.info(f"Cleaned up {count} old background jobs")
        return {
            'success': True, 
            'cleaned_jobs': count, 
            'message': f'Successfully cleaned up {count} old background jobs'
        }
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to cleanup old jobs: {e}")
        return {
            'success': False, 
            'error': f'Failed to cleanup old jobs: {str(e)}'
        }


def backup_database(backup_path=None):
    """Create a backup of the SQLite database"""
    try:
        # Get database path from configuration
        db_uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
        if not db_uri.startswith('sqlite:///'):
            return {
                'success': False, 
                'message': 'Backup only supported for SQLite databases'
            }
        
        db_path = db_uri.replace('sqlite:///', '')
        
        if not os.path.exists(db_path):
            return {
                'success': False, 
                'message': f'Database file not found: {db_path}'
            }
        
        # Generate backup path if not provided
        if not backup_path:
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            backup_path = f'mission_control_backup_{timestamp}.db'
        
        # Create backup
        shutil.copy2(db_path, backup_path)
        
        backup_size = os.path.getsize(backup_path)
        
        logger.info(f"Database backed up to {backup_path}")
        return {
            'success': True,
            'backup_path': backup_path,
            'backup_size_bytes': backup_size,
            'message': f'Database successfully backed up to {backup_path}'
        }
        
    except Exception as e:
        logger.error(f"Database backup failed: {e}")
        return {
            'success': False,
            'message': f'Database backup failed: {str(e)}'
        }


def restore_database(backup_path):
    """Restore database from backup"""
    try:
        if not os.path.exists(backup_path):
            return {
                'success': False,
                'message': f'Backup file not found: {backup_path}'
            }
        
        # Get current database path
        db_uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
        if not db_uri.startswith('sqlite:///'):
            return {
                'success': False,
                'message': 'Restore only supported for SQLite databases'
            }
        
        db_path = db_uri.replace('sqlite:///', '')
        
        # Create backup of current database before restore
        if os.path.exists(db_path):
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            current_backup = f'mission_control_pre_restore_{timestamp}.db'
            shutil.copy2(db_path, current_backup)
            logger.info(f"Current database backed up to {current_backup}")
        
        # Restore from backup
        shutil.copy2(backup_path, db_path)
        
        logger.info(f"Database restored from {backup_path}")
        return {
            'success': True,
            'message': f'Database successfully restored from {backup_path}'
        }
        
    except Exception as e:
        logger.error(f"Database restore failed: {e}")
        return {
            'success': False,
            'message': f'Database restore failed: {str(e)}'
        }


def migrate_json_data_to_database(json_file_path):
    """Migrate existing JSON data files to database models"""
    try:
        if not os.path.exists(json_file_path):
            return {
                'success': False,
                'message': f'JSON file not found: {json_file_path}'
            }
        
        from ..models import Project, SystemMap, Conversation
        
        with open(json_file_path, 'r') as f:
            data = json.load(f)
        
        migrated_projects = 0
        migrated_system_maps = 0
        migrated_conversations = 0
        
        # Migrate projects
        if 'projects' in data:
            for project_data in data['projects']:
                # Check if project already exists
                existing = Project.query.filter_by(name=project_data.get('name')).first()
                if not existing:
                    project = Project.create(
                        name=project_data.get('name'),
                        repository_url=project_data.get('repository_url'),
                        description=project_data.get('description')
                    )
                    
                    # Migrate associated system maps
                    if 'system_maps' in project_data:
                        for map_data in project_data['system_maps']:
                            SystemMap.create_for_project(
                                project_id=project.id,
                                content=map_data.get('content'),
                                version=map_data.get('version', '1.0')
                            )
                            migrated_system_maps += 1
                    
                    # Migrate associated conversations
                    if 'conversations' in project_data:
                        for conv_data in project_data['conversations']:
                            conversation = Conversation.create_for_project(
                                project_id=project.id,
                                title=conv_data.get('title'),
                                ai_model=conv_data.get('ai_model')
                            )
                            
                            # Add messages if they exist
                            if 'messages' in conv_data:
                                conversation.messages = conv_data['messages']
                            
                            migrated_conversations += 1
                    
                    migrated_projects += 1
        
        db.session.commit()
        
        result = {
            'success': True,
            'migrated_projects': migrated_projects,
            'migrated_system_maps': migrated_system_maps,
            'migrated_conversations': migrated_conversations,
            'message': f'Successfully migrated {migrated_projects} projects, {migrated_system_maps} system maps, and {migrated_conversations} conversations'
        }
        
        logger.info(f"JSON data migration completed: {result['message']}")
        return result
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"JSON data migration failed: {e}")
        return {
            'success': False,
            'message': f'JSON data migration failed: {str(e)}'
        }


def run_database_migration():
    """Run database schema migrations"""
    try:
        # Generate migration if there are model changes
        migrate_migrate(message='Auto-generated migration')
        
        # Apply migrations
        migrate_upgrade()
        
        logger.info("Database migration completed successfully")
        return {
            'success': True,
            'message': 'Database migration completed successfully'
        }
        
    except Exception as e:
        logger.error(f"Database migration failed: {e}")
        return {
            'success': False,
            'message': f'Database migration failed: {str(e)}'
        }


def reset_database():
    """Reset database by dropping and recreating all tables"""
    try:
        # Import models to ensure they're registered
        from .. import models
        
        # Drop all tables
        db.drop_all()
        logger.info("All database tables dropped")
        
        # Recreate all tables
        db.create_all()
        logger.info("All database tables recreated")
        
        return {
            'success': True,
            'message': 'Database reset completed successfully'
        }
        
    except Exception as e:
        logger.error(f"Database reset failed: {e}")
        return {
            'success': False,
            'message': f'Database reset failed: {str(e)}'
        }


def optimize_database():
    """Optimize SQLite database performance"""
    try:
        # Run SQLite optimization commands
        db.session.execute(text('VACUUM'))
        db.session.execute(text('ANALYZE'))
        db.session.commit()
        
        logger.info("Database optimization completed")
        return {
            'success': True,
            'message': 'Database optimization completed successfully'
        }
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Database optimization failed: {e}")
        return {
            'success': False,
            'message': f'Database optimization failed: {str(e)}'
        }