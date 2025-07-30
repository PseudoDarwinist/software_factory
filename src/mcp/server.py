#!/usr/bin/env python3
"""
MCP Server for Software Factory

This module implements a Model Context Protocol (MCP) server that exposes
tools for getting project context and saving generated specifications.

Usage:
    python -m src.mcp.server

The server uses stdio transport and can be registered with Claude Code using:
    claude mcp add software-factory -- python -m src.mcp.server
"""

# Standard library
import json
import logging
import sys
import os
from typing import Dict, Any, Optional, List, Union
import traceback

# Flask
from flask import current_app, has_app_context

# Add project root to path to ensure imports work when run as a module
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Load environment variables early
from dotenv import load_dotenv
load_dotenv()

# Diagnostic logging
db_url = os.getenv('DATABASE_URL', 'NOT_SET')
print(f"🔍 MCP Server DATABASE_URL: {db_url}", file=sys.stderr)
print(f"🔍 MCP Server working directory: {os.getcwd()}", file=sys.stderr)
print(f"🔍 MCP Server .env file exists: {os.path.exists('.env')}", file=sys.stderr)
print(f"🔍 MCP Server working directory: {os.getcwd()}", file=sys.stderr)
print(f"🔍 MCP Server .env file exists: {os.path.exists('.env')}", file=sys.stderr)

# Import MCP library
try:
    from mcp.server.fastmcp import FastMCP
    from mcp.types import Tool
except ImportError:
    print("Error: MCP library not found. Install with: pip install mcp", file=sys.stderr)
    sys.exit(1)

# Flag to track if we're using mock data
using_mock_data = False

# Global Flask app instance
flask_app = None

def get_flask_app():
    """Return a Flask application instance shared with the main Software-Factory app.

    If the MCP server is executed *inside* an already-running Flask application (e.g.
    launched from within the main Software Factory process) we re-use that
    application instance to guarantee that SQLAlchemy shares the exact same
    engine / session registry.  This prevents the MCP server from pointing at a
    different database and eliminates the "0 projects, 0 ideas" problem.

    When the MCP server is started as a **stand-alone** process (local tests
    executing `python -m src.mcp.server`) there is no active app-context, so we
    lazily create a fresh application via the normal `create_app()` factory.
    """
    global flask_app

    # 1️⃣  Re-use existing app if we are already running inside one
    if has_app_context():
        try:
            cp = current_app._get_current_object()  # type: ignore[attr-defined]
            return cp
        except Exception:
            # Something odd – fall back to using our global app
            pass

    # 2️⃣  Use the global app instance that was created at module import time
    if flask_app is not None:
        return flask_app

    # 3️⃣  Create a brand-new app (fallback case)
    try:
        from src.app import create_app
        flask_app = create_app()
        logger.info("Flask app initialized for MCP server (fallback instance)")
        return flask_app
    except Exception as e:
        logger.error(f"Failed to initialize Flask app: {e}")
        raise

# Import models and services
try:
    from src.models.mission_control_project import MissionControlProject
    from src.models.system_map import SystemMap
    from src.models.feed_item import FeedItem
    from src.models.specification_artifact import SpecificationArtifact, ArtifactType, ArtifactStatus
    from src.models.base import db
    from src.events.domain_events import SpecDraftedEvent
    from src.services.event_bus import get_event_bus
    
    # Initialize Flask app once - create_app() already calls db.init_app()
    from src.app import create_app
    flask_app = create_app()
    print("✅ Flask app and database initialized for MCP server", file=sys.stderr)
    
except ImportError as e:
    using_mock_data = True
    print(f"Warning: Using mock data for MCP server. Import error: {e}", file=sys.stderr)
    
    # Define mock classes and enums for testing
    class ArtifactType:
        REQUIREMENTS = "requirements"
        DESIGN = "design"
        TASKS = "tasks"
    
    class ArtifactStatus:
        DRAFT = "draft"
        APPROVED = "approved"
        REJECTED = "rejected"
    
    # Mock database session
    class MockDB:
        class Session:
            def commit(self):
                pass
            
            def rollback(self):
                pass
        
        func = type('obj', (object,), {
            'now': lambda: "2025-07-27T00:00:00"
        })
        
        session = Session()
    
    db = MockDB()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger("software-factory-mcp")

# Initialize MCP server
mcp = FastMCP("software-factory")

# Mock data for testing when database is not available
MOCK_IDEAS = {
    "idea_123": {
        "id": "idea_123",
        "project_id": "project_1",
        "title": "Add dark mode support",
        "summary": "Implement dark mode across the application to improve user experience in low-light environments.",
        "created_at": "2025-07-27T00:00:00",
        "metadata": {"priority": "medium", "requested_by": "UX team"}
    },
    "idea_456": {
        "id": "idea_456",
        "project_id": "project_1",
        "title": "Implement OAuth login",
        "summary": "Add support for OAuth authentication with Google, GitHub, and Microsoft accounts.",
        "created_at": "2025-07-26T00:00:00",
        "metadata": {"priority": "high", "requested_by": "Security team"}
    }
}

MOCK_PROJECTS = {
    "project_1": {
        "id": "project_1",
        "name": "Software Factory",
        "description": "AI-powered software development platform",
        "repo_url": "https://github.com/PseudoDarwinist/software_factory"
    }
}

MOCK_SYSTEM_MAPS = {
    "project_1": {
        "components": [
            {"name": "Frontend", "tech": "React", "description": "User interface"},
            {"name": "Backend", "tech": "Python/FastAPI", "description": "API server"},
            {"name": "Database", "tech": "PostgreSQL", "description": "Data storage"}
        ],
        "integrations": [
            {"name": "GitHub", "description": "Version control integration"},
            {"name": "AI Services", "description": "Claude and other AI models"}
        ]
    }
}

MOCK_ARTIFACTS = {}

# Helper functions
def get_system_map(project_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve system map for a project"""
    if using_mock_data:
        return MOCK_SYSTEM_MAPS.get(project_id)
    
    try:
        app = get_flask_app()
        with app.app_context():
            from flask import current_app
            app_db = current_app.extensions['sqlalchemy']
            system_map = app_db.session.query(SystemMap).filter_by(project_id=project_id).first()
            if system_map and system_map.content:
                if isinstance(system_map.content, str):
                    return json.loads(system_map.content)
                return system_map.content
            return None
    except Exception as e:
        logger.error(f"Error retrieving system map: {e}")
        return None

def get_idea_details(idea_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve idea details"""
    if using_mock_data:
        return MOCK_IDEAS.get(idea_id)
    
    try:
        app = get_flask_app()
        with app.app_context():
            from flask import current_app
            app_db = current_app.extensions['sqlalchemy']
            feed_item = app_db.session.query(FeedItem).get(idea_id)
            if not feed_item:
                return None
            
            return {
                "id": feed_item.id,
                "project_id": feed_item.project_id,
                "title": feed_item.title,
                "summary": feed_item.summary,
                "created_at": feed_item.created_at.isoformat() if hasattr(feed_item.created_at, 'isoformat') else str(feed_item.created_at),
                "metadata": feed_item.metadata if hasattr(feed_item, 'metadata') else {}
            }
    except Exception as e:
        logger.error(f"Error retrieving idea details: {e}")
        return None

def get_repository_info(project_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve repository information for a project"""
    if using_mock_data:
        return MOCK_PROJECTS.get(project_id)
    
    try:
        app = get_flask_app()
        with app.app_context():
            from flask import current_app
            app_db = current_app.extensions['sqlalchemy']
            project = app_db.session.query(MissionControlProject).get(project_id)
            if not project:
                return None
            
            return {
                "repo_url": project.repo_url if hasattr(project, 'repo_url') else None,
                "name": project.name,
                "description": project.description if hasattr(project, 'description') else None
            }
    except Exception as e:
        logger.error(f"Error retrieving repository info: {e}")
        return None

def store_spec_artifact(spec_id: str, project_id: str, artifact_type: ArtifactType, content: str) -> Optional[str]:
    """Store specification artifact in the database"""
    if using_mock_data:
        artifact_id = f"{spec_id}_{artifact_type.value}"
        MOCK_ARTIFACTS[artifact_id] = {
            "id": artifact_id,
            "spec_id": spec_id,
            "project_id": project_id,
            "type": artifact_type.value,
            "content": content,
            "status": ArtifactStatus.DRAFT,
            "created_at": "2025-07-27T00:00:00",
            "updated_at": "2025-07-27T00:00:00"
        }
        logger.info(f"Mock artifact stored: {artifact_id}")
        return artifact_id
    
    try:
        app = get_flask_app()
        with app.app_context():
            from flask import current_app
            app_db = current_app.extensions['sqlalchemy']
            try:
                # Ensure associated MissionControlProject exists to satisfy FK constraints
                existing_project = app_db.session.query(MissionControlProject).get(project_id)
                if existing_project is None:
                    # Create a minimal placeholder project so that specs can be stored
                    new_project = MissionControlProject(
                        id=project_id,
                        name=f"{project_id} (auto-created)",
                        description="Autogenerated placeholder project for specification artifacts created via MCP tests"
                    )
                    app_db.session.add(new_project)
                    app_db.session.commit()

                artifact_id = f"{spec_id}_{artifact_type.value}"
                existing_artifact = app_db.session.query(SpecificationArtifact).get(artifact_id)
                
                if existing_artifact:
                    # Update existing artifact
                    existing_artifact.content = content
                    existing_artifact.updated_at = app_db.func.now()
                    # Reset status to AI_DRAFT since content is being overwritten by the assistant
                    existing_artifact.status = ArtifactStatus.AI_DRAFT
                    existing_artifact.ai_generated = True
                    existing_artifact.ai_model_used = "mcp_assistant"
                    app_db.session.commit()
                    return artifact_id
                else:
                    # Create new artifact directly using app_db session
                    artifact_id = f"{spec_id}_{artifact_type.value}"
                    artifact = SpecificationArtifact(
                        id=artifact_id,
                        spec_id=spec_id,
                        project_id=str(project_id),
                        artifact_type=artifact_type,
                        content=content,
                        created_by="mcp_service",
                        ai_generated=True,
                        ai_model_used="mcp_assistant",
                        context_sources=["mcp_context"]
                    )
                    app_db.session.add(artifact)
                    app_db.session.commit()
                    return artifact.id
            except Exception as db_error:
                logger.error(f"Database error in store_spec_artifact: {db_error}")
                app_db.session.rollback()
                raise db_error
    except Exception as e:
        logger.error(f"Error storing spec artifact: {e}")
        return None

def publish_spec_drafted_event(spec_id: str, project_id: str, artifact_id: str):
    """Publish an event to notify the system that a spec has been drafted"""
    if using_mock_data:
        logger.info(f"Mock event published: SpecDraftedEvent for {spec_id}")
        return True
    
    try:
        app = get_flask_app()
        with app.app_context():
            event_bus = get_event_bus()
            event = SpecDraftedEvent(
                spec_id=spec_id,
                project_id=project_id,
                drafted_by="mcp_assistant",
                artifact_ids=[artifact_id]
            )
            event_bus.publish(event)
            return True
    except Exception as e:
        logger.error(f"Error publishing spec drafted event: {e}")
        return False

# Define MCP tools

@mcp.tool()
async def list_projects() -> str:
    """List all Software Factory projects with basic information"""
    if using_mock_data:
        projects = list(MOCK_PROJECTS.values())
    else:
        try:
            app = get_flask_app()
            
            # Push app context explicitly
            ctx = app.app_context()
            ctx.push()
            
            try:
                # Get the actual SQLAlchemy extension from the Flask app
                from flask import current_app
                app_db = current_app.extensions['sqlalchemy']
                
                # Debug: Show actual database URL being used
                print(f"🔍 Flask app DATABASE_URL: {app_db.engine.url}", file=sys.stderr)
                print(f"🔍 Flask app config DATABASE_URL: {app.config.get('SQLALCHEMY_DATABASE_URI', 'NOT_SET')}", file=sys.stderr)
                
                # Try to get table info first
                try:
                    table_exists = app_db.engine.dialect.has_table(app_db.engine, 'mission_control_project')
                    print(f"🔍 Table 'mission_control_project' exists: {table_exists}", file=sys.stderr)
                except Exception as table_error:
                    print(f"❌ Error checking table existence: {table_error}", file=sys.stderr)
                
                # Try the query using the app's db session
                projects_query = app_db.session.query(MissionControlProject).all()
                print(f"🔍 Query executed, found {len(projects_query)} projects", file=sys.stderr)
                
                # Debug: Try direct SQL query to compare
                result = app_db.session.execute(app_db.text("SELECT id, name FROM mission_control_project"))
                direct_projects = result.fetchall()
                print(f"🔍 Direct SQL query found {len(direct_projects)} projects: {[p[0] for p in direct_projects]}", file=sys.stderr)
                
                projects = [
                    {
                        "id": p.id,
                        "name": p.name,
                        "description": getattr(p, 'description', None),
                        "repo_url": getattr(p, 'repo_url', None),
                        "health": getattr(p, 'health', 'unknown')
                    }
                    for p in projects_query
                ]
            finally:
                ctx.pop()
        except Exception as e:
            logger.error(f"Error fetching projects: {e}")
            print(f"❌ Exception in list_projects: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            projects = []

    return json.dumps({
        "projects": projects,
        "count": len(projects)
    }, indent=2)


# ------------------------------------------------------------
# Idea utilities
# ------------------------------------------------------------


@mcp.tool()
async def list_ideas(project_id: str) -> str:
    """List all ideas (FeedItems) for a project."""
    try:
        app = get_flask_app()
        with app.app_context():
            from flask import current_app
            app_db = current_app.extensions['sqlalchemy']
            ideas_query = app_db.session.query(FeedItem).filter_by(project_id=project_id).order_by(FeedItem.created_at.desc()).all()

            ideas = [
                {
                    "id": i.id,
                    "title": i.title,
                    "summary": i.summary,
                    "created_at": i.created_at.isoformat() if hasattr(i.created_at, 'isoformat') else str(i.created_at),
                    "metadata": getattr(i, 'meta_data', {}) or {}
                }
                for i in ideas_query
            ]

            return json.dumps({"ideas": ideas, "count": len(ideas)}, indent=2)
    except Exception as e:
        logger.error(f"Error fetching ideas: {e}")
        return json.dumps({"ideas": [], "count": 0})

@mcp.tool()
async def get_project_context(
    project_id: str,
    include_ideas: bool = True,
    include_system_map: bool = True,
    include_existing_specs: bool = True
) -> str:
    """Get comprehensive context for a project including ideas, PRDs, and system architecture
    
    Args:
        project_id: The project ID to get context for
        include_ideas: Include project ideas and PRDs
        include_system_map: Include system architecture map
        include_existing_specs: Include existing specifications
    """
    context = {"project_id": project_id}
    
    # Get project basic info
    repo_info = get_repository_info(project_id)
    if repo_info:
        context["project_info"] = repo_info
    
    # Get system map
    if include_system_map:
        system_map = get_system_map(project_id)
        if system_map:
            context["system_map"] = system_map
    
    # Get ideas/PRDs
    if include_ideas:
        if using_mock_data:
            ideas = [idea for idea in MOCK_IDEAS.values() if idea["project_id"] == project_id]
        else:
            try:
                app = get_flask_app()
                with app.app_context():
                    from flask import current_app
                    app_db = current_app.extensions['sqlalchemy']
                    # Get only ideas (not all feed items)
                    ideas_query = app_db.session.query(FeedItem).filter_by(
                        project_id=project_id, 
                        kind=FeedItem.KIND_IDEA
                    ).all()
                    logger.info(f"ORM query found {len(ideas_query)} ideas for project {project_id}")
                    
                    # Debug: Try direct SQL query to compare
                    result = app_db.session.execute(app_db.text(
                        "SELECT id, title, kind FROM feed_item WHERE project_id = :project_id AND kind = 'idea'"
                    ), {"project_id": project_id})
                    direct_ideas = result.fetchall()
                    logger.info(f"Direct SQL query found {len(direct_ideas)} ideas: {[i[0] for i in direct_ideas]}")
                    
                    ideas = [
                        {
                            "id": item.id,
                            "title": item.title,
                            "summary": item.summary,
                            "kind": item.kind,
                            "severity": item.severity,
                            "actor": item.actor,
                            "unread": item.unread,
                            "created_at": item.created_at.isoformat() if item.created_at else None,
                            "metadata": item.meta_data or {}
                        }
                        for item in ideas_query
                    ]
            except Exception as e:
                logger.error(f"Error fetching ideas: {e}")
                ideas = []
        
        context["ideas"] = ideas
    
    # Get existing specs
    if include_existing_specs:
        if using_mock_data:
            specs = [spec for spec in MOCK_ARTIFACTS.values() if spec["project_id"] == project_id]
        else:
            try:
                app = get_flask_app()
                with app.app_context():
                    from flask import current_app
                    app_db = current_app.extensions['sqlalchemy']
                    specs_query = app_db.session.query(SpecificationArtifact).filter_by(project_id=project_id).all()
                    specs = [spec.to_dict() for spec in specs_query]
            except Exception as e:
                logger.error(f"Error fetching specs: {e}")
                specs = []
        
        context["existing_specs"] = specs
    
    return json.dumps(context, indent=2)

@mcp.tool()
async def create_requirements(
    project_id: str,
    feature_name: str,
    requirements_content: str,
    idea_id: str = None
) -> str:
    """Create and save requirements.md for a feature in Software Factory
    
    Args:
        project_id: The project ID where the requirements belong
        feature_name: Name of the feature (used for spec ID generation)
        requirements_content: The complete requirements.md content
        idea_id: Optional ID of the original idea this spec is based on
    """
    # Generate spec ID from feature name
    spec_id = f"spec_{feature_name.lower().replace(' ', '_').replace('-', '_')}"
    
    # Store the requirements artifact
    if using_mock_data:
        artifact_id = store_spec_artifact(spec_id, project_id, ArtifactType.REQUIREMENTS, requirements_content)
    else:
        try:
            from src.models.specification_artifact import SpecificationArtifact, ArtifactType
            artifact_id = store_spec_artifact(spec_id, project_id, ArtifactType.REQUIREMENTS, requirements_content)
        except Exception as e:
            logger.error(f"Error storing requirements: {e}")
            return json.dumps({"error": f"Error storing requirements: {str(e)}"})
    
    if not artifact_id:
        return json.dumps({"error": "Failed to store requirements artifact"})
    
    # Publish event
    publish_spec_drafted_event(spec_id, project_id, artifact_id)
    
    # Create file system representation for Kiro workflow
    spec_dir = f".kiro/specs/{feature_name.lower().replace(' ', '-')}"
    file_path = f"{spec_dir}/requirements.md"
    
    result = {
        "success": True,
        "spec_id": spec_id,
        "artifact_id": artifact_id,
        "file_path": file_path,
        "message": f"Requirements created successfully for {feature_name}",
        "next_steps": [
            "Review the requirements in Software Factory UI",
            "Generate design.md using create_design tool",
            "Generate tasks.md using create_tasks tool"
        ]
    }
    
    return json.dumps(result, indent=2)

@mcp.tool()
async def create_design(
    project_id: str,
    spec_id: str,
    design_content: str
) -> str:
    """Create and save design.md for a feature specification
    
    Args:
        project_id: The project ID where the design belongs
        spec_id: The specification ID this design belongs to
        design_content: The complete design.md content
    """
    # Store the design artifact
    if using_mock_data:
        artifact_id = store_spec_artifact(spec_id, project_id, ArtifactType.DESIGN, design_content)
    else:
        try:
            from src.models.specification_artifact import SpecificationArtifact, ArtifactType
            artifact_id = store_spec_artifact(spec_id, project_id, ArtifactType.DESIGN, design_content)
        except Exception as e:
            logger.error(f"Error storing design: {e}")
            return json.dumps({"error": f"Error storing design: {str(e)}"})
    
    if not artifact_id:
        return json.dumps({"error": "Failed to store design artifact"})
    
    # Publish event
    publish_spec_drafted_event(spec_id, project_id, artifact_id)
    
    result = {
        "success": True,
        "spec_id": spec_id,
        "artifact_id": artifact_id,
        "message": f"Design document created successfully for {spec_id}",
        "next_steps": [
            "Review the design in Software Factory UI",
            "Generate tasks.md using create_tasks tool"
        ]
    }
    
    return json.dumps(result, indent=2)

@mcp.tool()
async def create_tasks(
    project_id: str,
    spec_id: str,
    tasks_content: str
) -> str:
    """Create and save tasks.md for a feature specification
    
    Args:
        project_id: The project ID where the tasks belong
        spec_id: The specification ID these tasks belong to
        tasks_content: The complete tasks.md content
    """
    # Store the tasks artifact
    if using_mock_data:
        artifact_id = store_spec_artifact(spec_id, project_id, ArtifactType.TASKS, tasks_content)
    else:
        try:
            from src.models.specification_artifact import SpecificationArtifact, ArtifactType
            artifact_id = store_spec_artifact(spec_id, project_id, ArtifactType.TASKS, tasks_content)
        except Exception as e:
            logger.error(f"Error storing tasks: {e}")
            return json.dumps({"error": f"Error storing tasks: {str(e)}"})
    
    if not artifact_id:
        return json.dumps({"error": "Failed to store tasks artifact"})
    
    # Publish event
    publish_spec_drafted_event(spec_id, project_id, artifact_id)
    
    result = {
        "success": True,
        "spec_id": spec_id,
        "artifact_id": artifact_id,
        "message": f"Tasks document created successfully for {spec_id}",
        "next_steps": [
            "Review the complete specification in Software Factory UI",
            "Mark as human-reviewed when ready",
            "Begin task execution in Build phase"
        ]
    }
    
    return json.dumps(result, indent=2)

@mcp.tool()
async def get_idea_details(idea_id: str) -> str:
    """Get detailed information about a specific idea or PRD
    
    Args:
        idea_id: The ID of the idea to retrieve
    """
    idea_details = get_idea_details(idea_id)
    if not idea_details:
        return json.dumps({"error": f"Idea {idea_id} not found"})
    
    return json.dumps(idea_details, indent=2)

# Tool handlers are now defined using @mcp.tool() decorators above

def main():
    """Run the MCP server"""
    logger.info("Starting Software Factory MCP server")
    
    if using_mock_data:
        logger.warning("Running with mock data - database connection not available")
    
    try:
        # Run the FastMCP server
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()

def main():
    """Run the MCP server"""
    import asyncio
    
    async def run_server():
        """Run the MCP server asynchronously"""
        logger.info("Starting Software Factory MCP server")
        
        if using_mock_data:
            logger.warning("Running with mock data - database connection not available")
        
        try:
            # Run the server
            await mcp.run()
        except KeyboardInterrupt:
            logger.info("Server stopped by user")
        except Exception as e:
            logger.error(f"Server error: {e}")
            logger.error(traceback.format_exc())
            sys.exit(1)
    
    asyncio.run(run_server())

