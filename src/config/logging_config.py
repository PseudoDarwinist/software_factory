"""
Clean, focused logging configuration
Reduces log spam and focuses on what matters
"""

import logging
import os
from logging.handlers import RotatingFileHandler

def setup_clean_logging(app):
    """Setup clean, focused logging configuration"""
    
    # Get environment
    env = os.getenv('FLASK_ENV', 'production')
    debug_mode = env == 'development'
    
    # Root logger level
    root_level = logging.DEBUG if debug_mode else logging.INFO
    
    # Configure root logger
    logging.basicConfig(
        level=root_level,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Silence noisy third-party libraries
    silence_loggers = [
        'sentence_transformers',           # Very verbose ML library
        'sqlalchemy.engine',              # Database query spam
        'sqlalchemy.pool',                # Connection pool spam
        'engineio.server',                # Socket.IO spam
        'socketio.server',                # Socket.IO spam
        'urllib3.connectionpool',         # HTTP request spam
        'requests.packages.urllib3',      # HTTP request spam
        'transformers',                   # ML model spam
        'torch',                          # PyTorch spam
        'utils.setup_graph_database',     # Database setup spam
    ]
    
    for logger_name in silence_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)
    
    # App-specific loggers - keep these informative
    app_loggers = [
        'app',                           # Main app events
        'api.mission_control',           # Project operations
        'api.webhooks',                  # Webhook events
        'services.background',           # Background jobs
        'services.ai_broker',            # AI operations
    ]
    
    for logger_name in app_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)
    
    # File logging for production
    if not debug_mode:
        if not os.path.exists('logs'):
            os.makedirs('logs')
        
        file_handler = RotatingFileHandler(
            'logs/app.log', 
            maxBytes=10240000,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        ))
        app.logger.addHandler(file_handler)
    
    # Clean startup message
    app.logger.info("🚀 Software Factory started successfully")
    
    return app.logger

def get_clean_logger(name):
    """Get a logger with clean configuration"""
    logger = logging.getLogger(name)
    
    # Don't propagate to root if it's a noisy library
    noisy_prefixes = [
        'sentence_transformers',
        'sqlalchemy',
        'engineio',
        'socketio',
        'urllib3',
        'requests',
        'transformers',
        'torch',
    ]
    
    for prefix in noisy_prefixes:
        if name.startswith(prefix):
            logger.setLevel(logging.WARNING)
            break
    
    return logger