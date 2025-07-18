#!/usr/bin/env python3
"""
Unified Flask Application - Architecture Simplification
Single-process application consolidating all functionality
"""

import os
import logging
import signal
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from concurrent.futures import ThreadPoolExecutor
import atexit

# Import database instance from models
try:
    from .models import db
except ImportError:
    # Handle direct execution
    import sys
    import os
    sys.path.insert(0, os.path.dirname(__file__))
    from models import db
migrate = Migrate()

# Global background job manager
job_manager = None


class Config:
    """Application configuration management with environment variables"""
    
    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///mission_control.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'unified-flask-secret-key-change-in-production')
    
    # Application settings
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    HOST = os.environ.get('FLASK_HOST', '0.0.0.0')
    PORT = int(os.environ.get('FLASK_PORT', 8000))
    
    # Background job settings
    MAX_WORKERS = int(os.environ.get('MAX_WORKERS', 4))
    
    # Static files configuration
    STATIC_FOLDER = os.environ.get('STATIC_FOLDER', 'frontend/dist')
    
    # AI service configuration
    GOOSE_SCRIPT_PATH = os.environ.get('GOOSE_SCRIPT_PATH', './scripts/goose-gemini')
    MODEL_GARDEN_API_URL = os.environ.get('MODEL_GARDEN_API_URL', 'https://quasarmarket.coforge.com/aistudio-llmrouter-api/api/v2/chat/completions')
    MODEL_GARDEN_API_KEY = os.environ.get('MODEL_GARDEN_API_KEY', 'b3540f69-5289-483e-91fe-942c4bfa458c')


def create_app(config_class=Config):
    """Flask application factory pattern"""
    app = Flask(__name__, 
                static_folder='../frontend',  # Serve from frontend directory
                static_url_path='')         # Serve at root path
    app.config.from_object(config_class)
    
    # Configure logging
    setup_logging(app)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Initialize database system
    try:
        from .core import database
    except ImportError:
        from core import database
    database.init_database_system(app, db, migrate)
    
    # Initialize cache system
    try:
        from .services.cache import init_status_cache
    except ImportError:
        from services.cache import init_status_cache
    init_status_cache(default_ttl=30, cleanup_interval=60)
    
    # Initialize background job manager
    try:
        from .services.background import init_job_manager
    except ImportError:
        from services.background import init_job_manager
    global job_manager
    job_manager = init_job_manager(app, max_workers=app.config['MAX_WORKERS'])
    
    # Register blueprints
    register_blueprints(app)
    
    # Register frontend routes
    register_frontend_routes(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Setup application lifecycle handlers
    setup_lifecycle_handlers(app)
    
    app.logger.info("Unified Flask application created successfully")
    return app


def setup_logging(app):
    """Configure application logging"""
    if not app.debug:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s %(levelname)s %(name)s: %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )
    else:
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s %(levelname)s %(name)s: %(message)s'
        )
    
    app.logger.info("Logging configured")


def register_blueprints(app):
    """Register application blueprints"""
    try:
        try:
            from .api.projects import projects_bp
            from .api.system import system_bp
            from .api.ai import ai_bp
            from .api.mission_control import mission_control_bp
            from .api.conversations import conversations_bp
            from .api.stages import stages_bp
        except ImportError:
            from api.projects import projects_bp
            from api.system import system_bp
            from api.ai import ai_bp
            from api.mission_control import mission_control_bp
            from api.conversations import conversations_bp
            from api.stages import stages_bp
        
        app.register_blueprint(projects_bp)
        app.register_blueprint(system_bp)
        app.register_blueprint(ai_bp)
        app.register_blueprint(mission_control_bp)
        app.register_blueprint(conversations_bp)
        app.register_blueprint(stages_bp)
        
        app.logger.info("API blueprints registered successfully")
        
    except Exception as e:
        app.logger.error(f"Failed to register blueprints: {e}")
        raise


def register_frontend_routes(app):
    """Register frontend static file routes"""
    from flask import send_from_directory, send_file, request
    import os
    
    # Frontend directory paths
    frontend_dir = os.path.join(app.root_path, '..', 'frontend')
    mission_control_dir = os.path.join(app.root_path, '..', 'mission-control-dist')
    
    @app.route('/')
    def index():
        """Serve the main landing page"""
        return send_from_directory(frontend_dir, 'index.html')
    
    @app.route('/dashboard.html')
    @app.route('/dashboard')
    def dashboard():
        """Serve the role-based dashboard"""
        return send_from_directory(frontend_dir, 'dashboard.html')
    
    @app.route('/business.html')
    @app.route('/business')
    def business():
        """Serve the Business Analyst interface with liquid glass aesthetics"""
        return send_from_directory(frontend_dir, 'business.html')
    
    @app.route('/po.html')
    @app.route('/po')
    def product_owner():
        """Serve the Product Owner interface"""
        return send_from_directory(frontend_dir, 'po.html')
    
    @app.route('/designer.html')
    @app.route('/designer')
    def designer():
        """Serve the Designer interface (placeholder)"""
        return send_from_directory(frontend_dir, 'dashboard.html')  # Fallback to dashboard
    
    @app.route('/developer.html')
    @app.route('/developer')
    def developer():
        """Serve the Developer interface (placeholder)"""
        return send_from_directory(frontend_dir, 'dashboard.html')  # Fallback to dashboard
    
    # Mission Control React App Routes
    @app.route('/mission-control')
    @app.route('/mission-control/')
    def mission_control_root():
        """Serve Mission Control React SPA root"""
        return send_from_directory(mission_control_dir, 'index.html')
    
    @app.route('/mission-control/<path:path>')
    def mission_control_spa(path):
        """Serve Mission Control React SPA - handle React Router routes"""
        app.logger.debug(f"Mission Control SPA route called with path: {path}")
        
        # Check if it's a static asset request
        if path.startswith('assets/'):
            # Serve assets directly from mission-control-dist/assets/
            asset_file = path[7:]  # Remove 'assets/' prefix
            asset_path = os.path.join(mission_control_dir, 'assets', asset_file)
            app.logger.debug(f"Serving asset: {asset_path}, exists: {os.path.exists(asset_path)}")
            return send_from_directory(os.path.join(mission_control_dir, 'assets'), asset_file)
        elif path.startswith('fonts/'):
            # Serve fonts directly from mission-control-dist/fonts/
            font_file = path[6:]  # Remove 'fonts/' prefix
            font_path = os.path.join(mission_control_dir, 'fonts', font_file)
            app.logger.debug(f"Serving font: {font_path}, exists: {os.path.exists(font_path)}")
            return send_from_directory(os.path.join(mission_control_dir, 'fonts'), font_file)
        elif path in ['favicon.svg', 'favicon.ico']:
            # Serve favicon from mission control directory if it exists, otherwise from main frontend
            try:
                return send_from_directory(mission_control_dir, path)
            except:
                return send_from_directory(frontend_dir, path)
        else:
            # All other paths are React Router routes, serve index.html
            app.logger.debug(f"Serving index.html for path: {path}")
            return send_from_directory(mission_control_dir, 'index.html')
    
    
    # Serve CSS files with proper MIME type
    @app.route('/<path:filename>')
    def static_files(filename):
        """Serve static files (CSS, JS, images, fonts)"""
        return send_from_directory(frontend_dir, filename)
    
    app.logger.info("Frontend routes registered successfully")


def register_error_handlers(app):
    """Register global error handlers"""
    
    @app.errorhandler(404)
    def not_found_error(error):
        app.logger.warning(f"404 error: {error}")
        return {'error': 'Resource not found'}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"500 error: {error}")
        db.session.rollback()
        return {'error': 'Internal server error'}, 500
    
    @app.errorhandler(Exception)
    def handle_exception(e):
        app.logger.error(f"Unhandled exception: {e}", exc_info=True)
        db.session.rollback()
        return {'error': 'An unexpected error occurred'}, 500
    
    app.logger.info("Error handlers registered")


def setup_lifecycle_handlers(app):
    """Setup application initialization and teardown handlers"""
    
    with app.app_context():
        try:
            try:
                from .core import database
            except ImportError:
                from core import database
            if database.create_all_tables(app):
                app.logger.info("Database tables created/verified successfully")
            else:
                app.logger.error("Database table creation failed")
        except Exception as e:
            app.logger.error(f"Database initialization failed: {e}")
    
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        if exception:
            app.logger.error(f"Request ended with exception: {exception}")
            db.session.rollback()
        else:
            db.session.remove()
    
    def cleanup_application():
        app.logger.info("Starting application cleanup...")
        
        # Shutdown background job manager
        if job_manager:
            job_manager.shutdown()
        
        # Shutdown cache system
        try:
            try:
                from .services.cache import get_status_cache
            except ImportError:
                from services.cache import get_status_cache
            cache = get_status_cache()
            cache.shutdown()
            app.logger.info("Cache system shutdown complete")
        except Exception as e:
            app.logger.error(f"Error shutting down cache system: {e}")
        
        # Close database connections
        try:
            with app.app_context():
                db.session.close()
            app.logger.info("Database connections closed")
        except Exception as e:
            app.logger.error(f"Error closing database connections: {e}")
        
        app.logger.info("Application cleanup complete")
    
    atexit.register(cleanup_application)
    
    def signal_handler(signum, frame):
        app.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        cleanup_application()
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    app.logger.info("Lifecycle handlers configured")


def main():
    """Main application entry point"""
    print("🏭 Unified Flask Application - Architecture Simplification")
    print("=" * 60)
    print("🔧 Single-process architecture")
    print("🗄️  SQLite database with SQLAlchemy ORM")
    print("🔄 Background job processing with Python threading")
    print("🌐 REST API with polling-based frontend communication")
    print("🎯 All functionality consolidated into one application")
    print("")
    
    app = create_app()
    
    print(f"🌐 Server: http://{app.config['HOST']}:{app.config['PORT']}")
    print(f"🗄️  Database: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print(f"👷 Background workers: {app.config['MAX_WORKERS']}")
    print(f"📁 Static files: {app.config['STATIC_FOLDER']}")
    print(f"🐛 Debug mode: {app.config['DEBUG']}")
    print("")
    print("Press Ctrl+C to stop the server")
    print("")
    
    try:
        app.run(
            host=app.config['HOST'],
            port=app.config['PORT'],
            debug=app.config['DEBUG'],
            threaded=True
        )
    except KeyboardInterrupt:
        print("\n🏭 Unified Flask application stopped.")
    except Exception as e:
        print(f"\n❌ Application failed to start: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()