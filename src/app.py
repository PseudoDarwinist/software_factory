#!/usr/bin/env python3
"""
Unified Flask Application - Architecture Simplification
Single-process application consolidating all functionality
"""

import os
import logging
import signal
import sys
import traceback
import time
from flask import Flask, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import atexit
import redis

# Grouped imports for better structure
try:
    from .models import db
    from .core import database
    from .services import (
        distributed_cache,
        background,
        event_bus,
        webhook_service,
        integration_setup,
        websocket_server,
        vector_service,
        ai_broker,
        context_aware_ai,
        ai_agents,
        auth_service
    )
    from .api import (
        projects,
        system,
        ai,
        ai_broker as ai_broker_api,
        mission_control,
        conversations,
        stages,
        events,
        graph,
        vector,
        webhooks,
        cache,
        intelligence,
        monitoring,
        github,
        kiro_endpoints,
        tasks
    )
except ImportError as e:
    # Handle direct execution for scripts, etc.
    print(f"Initial import failed, retrying for script context: {e}")
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from models import db
    import core.database as database
    import services.distributed_cache as distributed_cache
    import services.background as background
    import services.event_bus as event_bus
    import services.webhook_service as webhook_service
    import services.integration_setup as integration_setup
    import services.websocket_server as websocket_server
    import services.vector_service as vector_service
    import services.ai_broker as ai_broker
    import services.context_aware_ai as context_aware_ai
    import services.ai_agents as ai_agents
    import services.auth_service as auth_service
    from api import system, ai, mission_control, conversations, stages, events, graph, vector, webhooks, cache, intelligence, monitoring, github, kiro_endpoints, tasks
    from api import ai_broker as ai_broker_api

migrate = Migrate()
job_manager = None


class Config:
    """Application configuration management with environment variables"""
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'postgresql://sf_user:sf_password@localhost/software_factory')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_timeout': 20,
        'max_overflow': 0
    }
    SECRET_KEY = os.environ.get('SECRET_KEY', 'unified-flask-secret-key-change-in-production')
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    HOST = os.environ.get('FLASK_HOST', '0.0.0.0')
    PORT = int(os.environ.get('FLASK_PORT', 8000))
    MAX_WORKERS = int(os.environ.get('MAX_WORKERS', 4))
    STATIC_FOLDER = os.environ.get('STATIC_FOLDER', 'frontend/dist')
    GOOSE_SCRIPT_PATH = os.environ.get('GOOSE_SCRIPT_PATH', './scripts/goose-gemini')
    MODEL_GARDEN_API_URL = os.environ.get('MODEL_GARDEN_API_URL', 'https://quasarmarket.coforge.com/aistudio-llmrouter-api/api/v2/chat/completions')
    MODEL_GARDEN_API_KEY = os.environ.get('MODEL_GARDEN_API_KEY', 'b3540f69-5289-483e-91fe-942c4bfa458c')
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    REDIS_CACHE_DB = os.environ.get('REDIS_CACHE_DB', '1')
    CACHE_DEFAULT_TTL = int(os.environ.get('CACHE_DEFAULT_TTL', 300))
    SESSION_TTL = int(os.environ.get('SESSION_TTL', 3600))
    WEBSOCKET_ASYNC_MODE = os.environ.get('WEBSOCKET_ASYNC_MODE', 'eventlet')


def create_app(config_class=Config):
    """Flask application factory pattern"""
    app = Flask(__name__, static_folder='../frontend', static_url_path='')
    app.config.from_object(config_class)

    setup_logging(app)

    db.init_app(app)
    migrate.init_app(app, db)

    if app.config.get('SQLALCHEMY_ENGINE_OPTIONS'):
        with app.app_context():
            db.engine.pool._pre_ping = app.config['SQLALCHEMY_ENGINE_OPTIONS']['pool_pre_ping']

    database.init_database_system(app, db, migrate)

    cache_redis_url = f"redis://localhost:6379/{app.config['REDIS_CACHE_DB']}"
    distributed_cache.init_distributed_cache(redis_url=cache_redis_url, default_ttl=app.config['CACHE_DEFAULT_TTL'])
    app.logger.info("Distributed cache system initialized")

    global job_manager
    job_manager = background.init_job_manager(app, max_workers=app.config['MAX_WORKERS'])

    event_bus_instance = event_bus.init_event_bus(app.config['REDIS_URL'], max_workers=app.config['MAX_WORKERS'])
    webhook_service.init_webhook_service(event_bus_instance, max_workers=app.config['MAX_WORKERS'])

    # Initialize Slack feed bridge
    try:
        from .services.slack_feed_bridge import init_slack_feed_bridge
        init_slack_feed_bridge()
        app.logger.info("Slack feed bridge initialized successfully")
    except ImportError:
        from services.slack_feed_bridge import init_slack_feed_bridge
        init_slack_feed_bridge()
        app.logger.info("Slack feed bridge initialized successfully")
    except Exception as e:
        app.logger.warning(f"Slack feed bridge initialization failed: {e}")

    if not integration_setup.setup_integrations(app):
        app.logger.warning("Some integrations failed to initialize")

    # Initialize Auth Service FIRST, as WebSocketServer depends on it.
    auth_service.init_auth_service(app)
    app.logger.info("Authentication service initialized")

    # Initialize WebSocket server
    websocket_server.init_websocket_server(app)

    if not vector_service.init_vector_service(db):
        app.logger.warning("Vector service initialization failed")
    
    # Initialize Vector Context Service
    try:
        from .services import vector_context_service
        if vector_context_service.init_vector_context_service():
            app.logger.info("Vector context service initialized successfully")
        else:
            app.logger.warning("Vector context service initialization failed")
    except ImportError:
        from services import vector_context_service
        if vector_context_service.init_vector_context_service():
            app.logger.info("Vector context service initialized successfully")
        else:
            app.logger.warning("Vector context service initialization failed")
    except Exception as e:
        app.logger.warning(f"Vector context service initialization failed: {e}")

    try:
        ai_broker.init_ai_broker()
        app.logger.info("AI broker service initialized successfully")
    except Exception as e:
        app.logger.warning(f"AI broker initialization failed: {e}")

    try:
        context_aware_ai.init_context_aware_ai()
        app.logger.info("Context-aware AI system initialized successfully")
    except Exception as e:
        app.logger.warning(f"Context-aware AI system initialization failed: {e}")

    try:
        # Corrected function call
        ai_agents.init_ai_agents()
        app.logger.info("AI agents initialized and started successfully")
    except Exception as e:
        app.logger.warning(f"AI agents initialization failed: {e}")

    # Initialize DefineAgent bridge
    try:
        from .services.define_agent_bridge import init_define_agent_bridge
        init_define_agent_bridge()
        app.logger.info("DefineAgent bridge initialized successfully")
    except ImportError:
        from services.define_agent_bridge import init_define_agent_bridge
        init_define_agent_bridge()
        app.logger.info("DefineAgent bridge initialized successfully")
    except Exception as e:
        app.logger.warning(f"DefineAgent bridge initialization failed: {e}")

    # Initialize PlannerAgent
    try:
        from .services.planner_agent_bridge import init_planner_agent_bridge
        init_planner_agent_bridge(app)
        app.logger.info("PlannerAgent bridge initialized successfully")
    except ImportError:
        from services.planner_agent_bridge import init_planner_agent_bridge
        init_planner_agent_bridge(app)
        app.logger.info("PlannerAgent bridge initialized successfully")
    except Exception as e:
        app.logger.warning(f"PlannerAgent bridge initialization failed: {e}")

    # Initialize Prometheus metrics server
    try:
        from .services.metrics_service import start_metrics_server
        start_metrics_server(port=9100)
        app.logger.info("Prometheus metrics server started on port 9100")
    except ImportError:
        from services.metrics_service import start_metrics_server
        start_metrics_server(port=9100)
        app.logger.info("Prometheus metrics server started on port 9100")
    except Exception as e:
        app.logger.warning(f"Prometheus metrics server initialization failed: {e}")

    register_blueprints(app)
    register_frontend_routes(app)
    register_error_handlers(app)
    setup_lifecycle_handlers(app)

    app.logger.info("Unified Flask application created successfully")
    return app


def setup_logging(app):
    """Configure clean, focused logging"""
    try:
        from config.logging_config import setup_clean_logging
        setup_clean_logging(app)
    except ImportError:
        # Fallback to quiet logging
        import logging
        logging.basicConfig(
            level=logging.WARNING,  # Much quieter
            format='%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%H:%M:%S'
        )
        # Only log essential startup message
        app.logger.info("🚀 Software Factory started")


def register_blueprints(app):
    """Register application blueprints"""
    # projects.projects_bp removed - using mission_control.mission_control_bp instead
    app.register_blueprint(system.system_bp)
    app.register_blueprint(ai.ai_bp)
    app.register_blueprint(ai_broker_api.ai_broker_bp)
    app.register_blueprint(mission_control.mission_control_bp)
    app.register_blueprint(conversations.conversations_bp)
    app.register_blueprint(stages.stages_bp)
    app.register_blueprint(events.events_bp)
    app.register_blueprint(graph.graph_bp)
    app.register_blueprint(vector.vector_bp)
    app.register_blueprint(webhooks.webhooks_bp)
    app.register_blueprint(cache.cache_bp)
    app.register_blueprint(intelligence.intelligence_bp)
    app.register_blueprint(monitoring.monitoring_bp)
    app.register_blueprint(kiro_endpoints.kiro_bp)
    app.register_blueprint(tasks.tasks_bp)
    app.register_blueprint(github.github_bp)
    app.logger.info("API blueprints registered successfully")


def register_frontend_routes(app):
    """Serve frontend application and static files"""
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))
    # Correct the path to point to the mission-control-dist directory
    mission_control_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'mission-control-dist'))

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve(path):
        if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        else:
            return send_from_directory(app.static_folder, 'index.html')

    @app.route('/mission-control/', defaults={'path': 'index.html'})
    @app.route('/mission-control/<path:path>')
    def serve_mission_control(path):
        app.logger.debug(f"Mission Control request for path: {path}")
        app.logger.debug(f"Mission Control directory: {mission_control_dir}")
        app.logger.debug(f"Directory exists: {os.path.exists(mission_control_dir)}")
        
        if path != "" and os.path.exists(os.path.join(mission_control_dir, path)):
            app.logger.debug(f"Serving file: {path}")
            return send_from_directory(mission_control_dir, path)
        else:
            app.logger.debug(f"Serving index.html for path: {path}")
            index_path = os.path.join(mission_control_dir, 'index.html')
            if os.path.exists(index_path):
                return send_from_directory(mission_control_dir, 'index.html')
            else:
                app.logger.error(f"Mission Control index.html not found at: {index_path}")
                return f"Mission Control not found. Expected at: {mission_control_dir}", 404

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
        try:
            with open("error.log", "a") as f:
                f.write(f"--- ERROR AT {time.time()} ---\n")
                f.write(str(e) + "\n")
                traceback.print_exc(file=f)
                f.write("-------------------------------------\n")
        except Exception as log_e:
            print(f"FAILED TO WRITE TO LOG FILE: {log_e}", file=sys.stderr)

        app.logger.error(f"Unhandled exception: {e}", exc_info=True)
        db.session.rollback()
        return {'error': 'An unexpected error occurred'}, 500

    app.logger.info("Error handlers registered")


def setup_lifecycle_handlers(app):
    """Setup application initialization and teardown handlers"""
    with app.app_context():
        try:
            if database.create_all_tables(app):
                app.logger.info("Database tables created/verified successfully")
            else:
                app.logger.error("Database table creation failed")
        except Exception as e:
            app.logger.error(f"Database initialization failed: {e}")

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        if exception:
            db.session.rollback()
        db.session.remove()

    def cleanup_application():
        app.logger.info("Starting application cleanup...")
        if job_manager:
            job_manager.shutdown()

        bus = event_bus.get_event_bus()
        if bus:
            bus.stop()

        broker = ai_broker.get_ai_broker()
        if broker:
            broker.stop()

        cache_instance = distributed_cache.get_distributed_cache()
        if cache_instance:
            cache_instance.cleanup_l1_cache()

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
    print("🏭 Software Factory - Event-Driven Architecture")
    print("=" * 60)

    try:
        app = create_app()

        print(f"🌐 Server: http://{app.config['HOST']}:{app.config['PORT']}")
        print(f"🗄️  Database: {app.config['SQLALCHEMY_DATABASE_URI']}")
        print(f"📡 Redis: {app.config['REDIS_URL']}")
        print("Press Ctrl+C to stop the server\n")

        bus = event_bus.get_event_bus()
        if bus:
            bus.start()
            print("📡 Event bus started successfully")

        ws = websocket_server.get_websocket_server()
        if ws:
            ws.socketio.run(
                app,
                host=app.config['HOST'],
                port=app.config['PORT'],
                debug=app.config['DEBUG']
            )
        else:
            # Fallback to regular Flask app
            app.run(
                host=app.config['HOST'],
                port=app.config['PORT'],
                debug=app.config['DEBUG'],
                threaded=True
            )
    except KeyboardInterrupt:
        print("\n🏭 Software Factory application stopped.")
    except Exception as e:
        print(f"\n❌ Application failed to start: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()