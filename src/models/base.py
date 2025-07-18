"""
Database base configuration
"""

from flask_sqlalchemy import SQLAlchemy

# Database instance - will be initialized by app
db = SQLAlchemy()