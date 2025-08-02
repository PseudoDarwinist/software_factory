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

# ===============================================================================
# BUILD PHASE MCP TOOLS - For Step 4: Build integration with external coding assistants
# ===============================================================================

@mcp.tool()
async def get_project_tasks(
    project_id: str,
    status_filter: str = None
) -> str:
    """Get all tasks for a project with their current status and context
    
    Args:
        project_id: The project ID to get tasks for
        status_filter: Optional status filter (ready, running, review, done, failed)
    """
    if using_mock_data:
        # Mock task data for testing
        mock_tasks = [
            {
                "id": f"{project_id}_task_1",
                "project_id": project_id,
                "spec_id": f"{project_id}_spec_oauth",
                "title": "Add OAuth login API endpoint",
                "description": "Implement OAuth 2.0 login endpoint with JWT token generation",
                "task_number": "1.1",
                "status": "ready",
                "priority": "high",
                "likely_touches": ["src/auth/oauth.py", "src/api/auth.py", "tests/test_auth.py"],
                "requirements_refs": ["REQ-AUTH-001", "REQ-SEC-002"],
                "goal_line": "Users can log in using OAuth and receive JWT tokens",
                "effort_estimate_hours": 4.0
            },
            {
                "id": f"{project_id}_task_2", 
                "project_id": project_id,
                "spec_id": f"{project_id}_spec_oauth",
                "title": "Update frontend login component",
                "description": "Modify login component to support OAuth flow",
                "task_number": "1.2",
                "status": "ready",
                "priority": "medium",
                "likely_touches": ["src/components/Login.tsx", "src/services/auth.ts"],
                "requirements_refs": ["REQ-UI-003"],
                "goal_line": "Login UI supports OAuth flow with proper error handling",
                "effort_estimate_hours": 2.5
            }
        ]
        
        if status_filter:
            mock_tasks = [t for t in mock_tasks if t["status"] == status_filter.lower()]
        
        return json.dumps({"tasks": mock_tasks, "count": len(mock_tasks)}, indent=2)
    else:
        try:
            app = get_flask_app()
            with app.app_context():
                from flask import current_app
                from src.models.task import Task, TaskStatus
                app_db = current_app.extensions['sqlalchemy']
                
                # Build query
                query = app_db.session.query(Task).filter_by(project_id=str(project_id))
                
                if status_filter:
                    try:
                        status_enum = TaskStatus(status_filter.lower())
                        query = query.filter_by(status=status_enum)
                    except ValueError:
                        return json.dumps({"error": f"Invalid status: {status_filter}"})
                
                tasks = query.order_by(Task.task_number).all()
                tasks_data = [task.to_dict() for task in tasks]
                
                return json.dumps({"tasks": tasks_data, "count": len(tasks_data)}, indent=2)
        except Exception as e:
            logger.error(f"Error getting project tasks: {e}")
            return json.dumps({"error": f"Error getting project tasks: {str(e)}"})

@mcp.tool()
async def get_task_context(task_id: str) -> str:
    """Get comprehensive context for a specific task including all implementation details
    
    Args:
        task_id: The ID of the task to get context for
    """
    if using_mock_data:
        # Mock task context for testing
        mock_context = {
            "task": {
                "id": task_id,
                "title": "Add OAuth login API endpoint",
                "description": "Implement OAuth 2.0 login endpoint with JWT token generation",
                "task_number": "1.1", 
                "status": "ready",
                "priority": "high",
                "likely_touches": ["src/auth/oauth.py", "src/api/auth.py", "tests/test_auth.py"],
                "requirements_refs": ["REQ-AUTH-001", "REQ-SEC-002"],
                "goal_line": "Users can log in using OAuth and receive JWT tokens",
                "effort_estimate_hours": 4.0
            },
            "project_context": {
                "name": "Software Factory",
                "repo_url": "https://github.com/example/software-factory",
                "tech_stack": ["Python", "FastAPI", "React", "TypeScript"]
            },
            "requirements": {
                "REQ-AUTH-001": "System must support OAuth 2.0 authentication flow",
                "REQ-SEC-002": "JWT tokens must expire after 24 hours"
            },
            "design_notes": "Follow existing auth patterns in src/auth/. Use Pydantic models for request/response validation.",
            "file_context": {
                "src/auth/oauth.py": "Create new file - OAuth provider configuration",
                "src/api/auth.py": "Add new endpoints - /oauth/login, /oauth/callback", 
                "tests/test_auth.py": "Add OAuth flow test cases"
            }
        }
        return json.dumps(mock_context, indent=2)
    else:
        try:
            app = get_flask_app()
            with app.app_context():
                from flask import current_app
                from src.models.task import Task
                from src.models.mission_control_project import MissionControlProject
                from src.models.specification_artifact import SpecificationArtifact
                app_db = current_app.extensions['sqlalchemy']
                
                # Get task
                task = app_db.session.query(Task).get(task_id)
                if not task:
                    return json.dumps({"error": f"Task {task_id} not found"})
                
                # Get project info
                project = app_db.session.query(MissionControlProject).get(task.project_id)
                
                # Get related spec artifacts
                spec_artifacts = app_db.session.query(SpecificationArtifact).filter_by(
                    spec_id=task.spec_id
                ).all()
                
                context = {
                    "task": task.to_dict(),
                    "project_context": {
                        "id": project.id,
                        "name": project.name,
                        "description": project.description if hasattr(project, 'description') else None,
                        "repo_url": project.repo_url if hasattr(project, 'repo_url') else None
                    },
                    "specification_artifacts": [
                        {
                            "type": artifact.artifact_type.value,
                            "content": artifact.content[:500] + "..." if len(artifact.content) > 500 else artifact.content
                        }
                        for artifact in spec_artifacts
                    ],
                    "implementation_context": {
                        "likely_files_to_modify": task.likely_touches or [],
                        "requirements_references": task.requirements_refs or [],
                        "goal": task.goal_line,
                        "estimated_effort_hours": task.effort_estimate_hours,
                        "dependencies": task.depends_on or []
                    }
                }
                
                return json.dumps(context, indent=2)
        except Exception as e:
            logger.error(f"Error getting task context: {e}")
            return json.dumps({"error": f"Error getting task context: {str(e)}"})

@mcp.tool()
async def get_task_repository_info(task_id: str) -> str:
    """Get repository access information for a task to enable local development
    
    Args:
        task_id: The ID of the task to get repository info for
    """
    if using_mock_data:
        mock_repo_info = {
            "task_id": task_id,
            "repository": {
                "url": "https://github.com/example/software-factory",
                "clone_url": "git@github.com:example/software-factory.git",
                "default_branch": "main",
                "access_method": "ssh_key_required"
            },
            "branch_info": {
                "suggested_branch_name": f"feature/{task_id}-oauth-login-implementation", 
                "base_branch": "main",
                "branch_exists": False
            },
            "development_setup": {
                "setup_commands": [
                    "git clone git@github.com:example/software-factory.git",
                    "cd software-factory",
                    "python -m venv venv",
                    "source venv/bin/activate",
                    "pip install -r requirements.txt"
                ],
                "test_command": "pytest tests/",
                "dev_server": "python -m src.app"
            }
        }
        return json.dumps(mock_repo_info, indent=2)
    else:
        try:
            app = get_flask_app()
            with app.app_context():
                from flask import current_app
                from src.models.task import Task
                from src.models.mission_control_project import MissionControlProject
                app_db = current_app.extensions['sqlalchemy']
                
                # Get task and project
                task = app_db.session.query(Task).get(task_id)
                if not task:
                    return json.dumps({"error": f"Task {task_id} not found"})
                
                project = app_db.session.query(MissionControlProject).get(task.project_id)
                if not project:
                    return json.dumps({"error": f"Project {task.project_id} not found"})
                
                # Generate branch name if not already set
                if not task.branch_name:
                    task_title_clean = task.title.lower().replace(' ', '-').replace('_', '-')
                    suggested_branch = f"feature/{task.id}-{task_title_clean}"
                else:
                    suggested_branch = task.branch_name
                
                repo_info = {
                    "task_id": task_id,
                    "repository": {
                        "url": project.repo_url if hasattr(project, 'repo_url') else None,
                        "default_branch": "main",
                        "access_method": "github_token_required" if hasattr(project, 'github_token') and project.github_token else "ssh_key_required"
                    },
                    "branch_info": {
                        "suggested_branch_name": suggested_branch,
                        "base_branch": "main",
                        "branch_exists": False  # TODO: Check with GitHub API
                    },
                    "development_context": {
                        "files_to_modify": task.likely_touches or [],
                        "test_files_pattern": "tests/test_*.py",
                        "related_components": task.related_components or []
                    }
                }
                
                return json.dumps(repo_info, indent=2)
        except Exception as e:
            logger.error(f"Error getting repository info: {e}")
            return json.dumps({"error": f"Error getting repository info: {str(e)}"})

@mcp.tool()
async def mark_task_complete(
    task_id: str,
    completion_notes: str = None,
    pr_url: str = None
) -> str:
    """Mark a task as completed after implementation
    
    Args:
        task_id: The ID of the task to mark as complete
        completion_notes: Optional notes about the implementation
        pr_url: Optional URL of the pull request created for this task
    """
    if using_mock_data:
        result = {
            "success": True,
            "task_id": task_id,
            "new_status": "done",
            "message": f"Task {task_id} marked as complete",
            "completion_notes": completion_notes,
            "pr_url": pr_url
        }
        return json.dumps(result, indent=2)
    else:
        try:
            app = get_flask_app()
            with app.app_context():
                from flask import current_app
                from src.models.task import Task, TaskStatus
                app_db = current_app.extensions['sqlalchemy']
                
                # Get task
                task = app_db.session.query(Task).get(task_id)
                if not task:
                    return json.dumps({"error": f"Task {task_id} not found"})
                
                # Mark as complete
                task.complete_task(completed_by="mcp_external_assistant", pr_url=pr_url)
                
                # Add completion notes if provided
                if completion_notes:
                    task.add_progress_message(f"Task completed via MCP: {completion_notes}", 100)
                
                app_db.session.commit()
                
                result = {
                    "success": True,
                    "task_id": task_id,
                    "new_status": task.status.value,
                    "message": f"Task {task_id} marked as complete",
                    "completion_notes": completion_notes,
                    "pr_url": pr_url,
                    "completed_at": task.completed_at.isoformat() if task.completed_at else None
                }
                
                return json.dumps(result, indent=2)
        except Exception as e:
            logger.error(f"Error marking task complete: {e}")
            return json.dumps({"error": f"Error marking task complete: {str(e)}"})

@mcp.tool()
async def update_task_status(
    task_id: str,
    new_status: str,
    progress_message: str = None
) -> str:
    """Update the status of a task during development
    
    Args:
        task_id: The ID of the task to update
        new_status: New status (ready, running, review, done, failed)
        progress_message: Optional progress message to add
    """
    if using_mock_data:
        result = {
            "success": True,
            "task_id": task_id,
            "old_status": "ready",
            "new_status": new_status,
            "message": f"Task {task_id} status updated to {new_status}",
            "progress_message": progress_message
        }
        return json.dumps(result, indent=2)
    else:
        try:
            app = get_flask_app()
            with app.app_context():
                from flask import current_app
                from src.models.task import Task, TaskStatus
                app_db = current_app.extensions['sqlalchemy']
                
                # Get task
                task = app_db.session.query(Task).get(task_id)
                if not task:
                    return json.dumps({"error": f"Task {task_id} not found"})
                
                old_status = task.status.value
                
                # Update status
                try:
                    task.status = TaskStatus(new_status.lower())
                except ValueError:
                    return json.dumps({"error": f"Invalid status: {new_status}"})
                
                # Add progress message if provided
                if progress_message:
                    task.add_progress_message(progress_message)
                
                app_db.session.commit()
                
                result = {
                    "success": True,
                    "task_id": task_id,
                    "old_status": old_status,
                    "new_status": task.status.value,
                    "message": f"Task {task_id} status updated from {old_status} to {task.status.value}",
                    "progress_message": progress_message
                }
                
                return json.dumps(result, indent=2)
        except Exception as e:
            logger.error(f"Error updating task status: {e}")
            return json.dumps({"error": f"Error updating task status: {str(e)}"})

# ===============================================================================
# THINK → DEFINE PHASE MCP TOOLS - For spec generation and management
# ===============================================================================

@mcp.tool()
async def get_ideas_without_specs(project_id: str = None) -> str:
    """Get ideas that haven't had specifications generated yet (Think stage ideas ready for Define)
    
    Args:
        project_id: Optional project ID to filter ideas
    """
    if using_mock_data:
        mock_ideas = [
            {
                "id": "idea_oauth_mobile",
                "project_id": project_id or "project_1", 
                "title": "Add OAuth login to mobile app",
                "summary": "Users want to log in with Google/Apple accounts for easier access",
                "severity": "amber",
                "stage": "think", 
                "created_at": "2025-01-30T10:00:00Z",
                "has_specs": False,
                "ready_for_define": True
            },
            {
                "id": "idea_push_notifications",
                "project_id": project_id or "project_1",
                "title": "Implement push notifications", 
                "summary": "Send notifications for order updates and promotions",
                "severity": "red",
                "stage": "think",
                "created_at": "2025-01-30T09:00:00Z", 
                "has_specs": False,
                "ready_for_define": True
            }
        ]
        return json.dumps({"ideas_without_specs": mock_ideas, "count": len(mock_ideas)}, indent=2)
    else:
        try:
            app = get_flask_app()
            with app.app_context():
                from flask import current_app
                app_db = current_app.extensions['sqlalchemy']
                
                # Query for ideas that don't have specs yet
                query = app_db.session.query(FeedItem).filter_by(kind=FeedItem.KIND_IDEA)
                
                if project_id:
                    query = query.filter_by(project_id=project_id)
                
                ideas = query.all()
                
                # Check which ideas don't have specs
                ideas_without_specs = []
                for idea in ideas:
                    # Check if idea has any specification artifacts
                    spec_count = app_db.session.query(SpecificationArtifact).filter_by(
                        project_id=idea.project_id,
                        # Assuming spec_id is related to idea_id - adjust based on your schema
                        spec_id=f"spec_{idea.id}"
                    ).count()
                    
                    if spec_count == 0:
                        ideas_without_specs.append({
                            "id": idea.id,
                            "project_id": idea.project_id,
                            "title": idea.title,
                            "summary": idea.summary,
                            "severity": idea.severity,
                            "actor": idea.actor,
                            "created_at": idea.created_at.isoformat() if idea.created_at else None,
                            "metadata": idea.meta_data or {},
                            "has_specs": False,
                            "ready_for_define": True
                        })
                
                return json.dumps({
                    "ideas_without_specs": ideas_without_specs,
                    "count": len(ideas_without_specs)
                }, indent=2)
        except Exception as e:
            logger.error(f"Error getting ideas without specs: {e}")
            return json.dumps({"error": f"Error getting ideas without specs: {str(e)}"})

@mcp.tool()
async def get_ideas_with_incomplete_specs(project_id: str = None) -> str:
    """Get ideas in Define stage that are missing some specification documents
    
    Args:
        project_id: Optional project ID to filter ideas
    """
    if using_mock_data:
        mock_incomplete = [
            {
                "id": "idea_api_refactor",
                "project_id": project_id or "project_1",
                "title": "Refactor API architecture", 
                "summary": "Modernize API endpoints for better performance",
                "stage": "define",
                "existing_specs": ["requirements"],
                "missing_specs": ["design", "tasks"],
                "completion_percentage": 33
            }
        ]
        return json.dumps({"ideas_with_incomplete_specs": mock_incomplete, "count": len(mock_incomplete)}, indent=2)
    else:
        try:
            app = get_flask_app()
            with app.app_context():
                from flask import current_app
                app_db = current_app.extensions['sqlalchemy']
                
                # Get all ideas that have at least one spec but not all three
                ideas_query = app_db.session.query(FeedItem).filter_by(kind=FeedItem.KIND_IDEA)
                if project_id:
                    ideas_query = ideas_query.filter_by(project_id=project_id)
                
                ideas = ideas_query.all()
                incomplete_ideas = []
                
                for idea in ideas:
                    # Check which spec types exist for this idea
                    spec_query = app_db.session.query(SpecificationArtifact).filter_by(
                        project_id=idea.project_id,
                        spec_id=f"spec_{idea.id}"
                    )
                    existing_specs = spec_query.all()
                    
                    if len(existing_specs) > 0 and len(existing_specs) < 3:
                        existing_types = [spec.artifact_type.value for spec in existing_specs]
                        all_types = ["requirements", "design", "tasks"]
                        missing_types = [t for t in all_types if t not in existing_types]
                        
                        incomplete_ideas.append({
                            "id": idea.id,
                            "project_id": idea.project_id,
                            "title": idea.title,
                            "summary": idea.summary,
                            "stage": "define",
                            "existing_specs": existing_types,
                            "missing_specs": missing_types,
                            "completion_percentage": round((len(existing_types) / 3) * 100)
                        })
                
                return json.dumps({
                    "ideas_with_incomplete_specs": incomplete_ideas,
                    "count": len(incomplete_ideas)
                }, indent=2)
        except Exception as e:
            logger.error(f"Error getting incomplete specs: {e}")
            return json.dumps({"error": f"Error getting incomplete specs: {str(e)}"})

@mcp.tool()
async def update_specification_artifact(
    project_id: str,
    spec_id: str,
    artifact_type: str,
    new_content: str,
    update_reason: str = None
) -> str:
    """Update an existing specification artifact (requirements.md, design.md, or tasks.md)
    
    Args:
        project_id: The project ID 
        spec_id: The specification ID
        artifact_type: Type of artifact to update ('requirements', 'design', or 'tasks')
        new_content: The updated content
        update_reason: Optional reason for the update
    """
    if using_mock_data:
        result = {
            "success": True,
            "spec_id": spec_id,
            "artifact_type": artifact_type,
            "updated_by": "mcp_assistant",
            "update_reason": update_reason,
            "previous_status": "human_reviewed",
            "new_status": "ai_draft",
            "message": f"Updated {artifact_type}.md specification - will need human review"
        }
        return json.dumps(result, indent=2)
    else:
        try:
            from src.models.specification_artifact import ArtifactType, ArtifactStatus
            
            # Validate artifact type
            valid_types = ["requirements", "design", "tasks"]
            if artifact_type not in valid_types:
                return json.dumps({"error": f"Invalid artifact_type. Must be one of: {valid_types}"})
            
            app = get_flask_app()
            with app.app_context():
                from flask import current_app
                app_db = current_app.extensions['sqlalchemy']
                
                # Find existing artifact
                artifact_id = f"{spec_id}_{artifact_type}"
                artifact = app_db.session.query(SpecificationArtifact).get(artifact_id)
                
                if not artifact:
                    return json.dumps({"error": f"Specification artifact {artifact_id} not found"})
                
                # Store previous status
                previous_status = artifact.status.value if artifact.status else "unknown"
                
                # Update the artifact
                artifact.content = new_content
                artifact.updated_at = app_db.func.now()
                artifact.status = ArtifactStatus.AI_DRAFT  # Reset to AI draft when updated via MCP
                artifact.ai_generated = True
                artifact.ai_model_used = "mcp_assistant"
                
                # Add update reason to context sources
                if update_reason:
                    context_sources = artifact.context_sources or []
                    context_sources.append(f"MCP_UPDATE: {update_reason}")
                    artifact.context_sources = context_sources
                
                app_db.session.commit()
                
                result = {
                    "success": True,
                    "spec_id": spec_id,
                    "artifact_id": artifact_id,
                    "artifact_type": artifact_type,
                    "updated_by": "mcp_assistant", 
                    "update_reason": update_reason,
                    "previous_status": previous_status,
                    "new_status": artifact.status.value,
                    "message": f"Updated {artifact_type}.md - status reset to AI draft for human review"
                }
                
                return json.dumps(result, indent=2)
        except Exception as e:
            logger.error(f"Error updating specification artifact: {e}")
            return json.dumps({"error": f"Error updating specification: {str(e)}"})

@mcp.tool()
async def generate_missing_specs_for_idea(
    idea_id: str,
    project_id: str,
    missing_spec_types: list = None,
    generation_context: str = None
) -> str:
    """Generate missing specification documents for an idea
    
    Args:
        idea_id: The idea ID to generate specs for
        project_id: The project ID
        missing_spec_types: List of spec types to generate ['requirements', 'design', 'tasks']
        generation_context: Additional context for AI generation
    """
    if using_mock_data:
        spec_types = missing_spec_types or ["requirements", "design", "tasks"]
        generated_specs = []
        
        for spec_type in spec_types:
            generated_specs.append({
                "artifact_type": spec_type,
                "artifact_id": f"spec_{idea_id}_{spec_type}",
                "status": "ai_draft",
                "generated": True
            })
        
        result = {
            "success": True,
            "idea_id": idea_id,
            "spec_id": f"spec_{idea_id}",
            "generated_specs": generated_specs,
            "message": f"Generated {len(spec_types)} specification documents"
        }
        return json.dumps(result, indent=2)
    else:
        try:
            # Get idea details first
            app = get_flask_app()
            with app.app_context():
                from flask import current_app
                app_db = current_app.extensions['sqlalchemy']
                
                idea = app_db.session.query(FeedItem).get(idea_id)
                if not idea:
                    return json.dumps({"error": f"Idea {idea_id} not found"})
                
                spec_id = f"spec_{idea_id}"
                spec_types = missing_spec_types or ["requirements", "design", "tasks"]
                generated_specs = []
                
                # Generate each missing spec type
                for spec_type in spec_types:
                    if spec_type == "requirements":
                        # Use existing create_requirements function
                        result = await create_requirements(
                            project_id=project_id,
                            feature_name=idea.title,
                            requirements_content=f"# Requirements for {idea.title}\n\n{idea.summary}\n\n{generation_context or ''}",
                            idea_id=idea_id
                        )
                    elif spec_type == "design":
                        # Use existing create_design function  
                        result = await create_design(
                            project_id=project_id,
                            spec_id=spec_id,
                            design_content=f"# Design for {idea.title}\n\n{generation_context or 'AI-generated design document'}"
                        )
                    elif spec_type == "tasks":
                        # Use existing create_tasks function
                        result = await create_tasks(
                            project_id=project_id,
                            spec_id=spec_id,
                            tasks_content=f"# Tasks for {idea.title}\n\n{generation_context or 'AI-generated task breakdown'}"
                        )
                    
                    generated_specs.append({
                        "artifact_type": spec_type,
                        "result": json.loads(result) if isinstance(result, str) else result
                    })
                
                return json.dumps({
                    "success": True,
                    "idea_id": idea_id,
                    "spec_id": spec_id,
                    "generated_specs": generated_specs,
                    "message": f"Generated {len(spec_types)} specification documents for idea: {idea.title}"
                }, indent=2)
        except Exception as e:
            logger.error(f"Error generating missing specs: {e}")
            return json.dumps({"error": f"Error generating specs: {str(e)}"})

@mcp.tool()
async def get_spec_generation_status(idea_id: str, project_id: str) -> str:
    """Get the current status of specification generation for an idea
    
    Args:
        idea_id: The idea ID to check
        project_id: The project ID
    """
    if using_mock_data:
        status = {
            "idea_id": idea_id,
            "project_id": project_id,
            "idea_title": "Add OAuth login to mobile app",
            "spec_id": f"spec_{idea_id}",
            "specifications": {
                "requirements": {"exists": True, "status": "human_reviewed", "last_updated": "2025-01-30T10:00:00Z"},
                "design": {"exists": True, "status": "ai_draft", "last_updated": "2025-01-30T11:00:00Z"},
                "tasks": {"exists": False, "status": None, "last_updated": None}
            },
            "completion_status": {
                "total_specs": 3,
                "completed_specs": 2,
                "completion_percentage": 67,
                "ready_for_freeze": False,
                "missing_specs": ["tasks"]
            }
        }
        return json.dumps(status, indent=2)
    else:
        try:
            app = get_flask_app()
            with app.app_context():
                from flask import current_app
                app_db = current_app.extensions['sqlalchemy']
                
                # Get idea details
                idea = app_db.session.query(FeedItem).get(idea_id)
                if not idea:
                    return json.dumps({"error": f"Idea {idea_id} not found"})
                
                spec_id = f"spec_{idea_id}"
                
                # Check each spec type
                spec_types = ["requirements", "design", "tasks"]
                specifications = {}
                completed_count = 0
                
                for spec_type in spec_types:
                    artifact_id = f"{spec_id}_{spec_type}"
                    artifact = app_db.session.query(SpecificationArtifact).get(artifact_id)
                    
                    if artifact:
                        specifications[spec_type] = {
                            "exists": True,
                            "status": artifact.status.value if artifact.status else "unknown",
                            "last_updated": artifact.updated_at.isoformat() if artifact.updated_at else None,
                            "ai_generated": artifact.ai_generated,
                            "ai_model": artifact.ai_model_used
                        }
                        completed_count += 1
                    else:
                        specifications[spec_type] = {
                            "exists": False,
                            "status": None,
                            "last_updated": None
                        }
                
                missing_specs = [spec_type for spec_type, info in specifications.items() if not info["exists"]]
                completion_percentage = round((completed_count / len(spec_types)) * 100)
                
                # Check if ready for freeze (all specs exist and at least human reviewed)
                ready_for_freeze = (
                    completed_count == len(spec_types) and
                    all(spec["status"] in ["human_reviewed", "frozen"] for spec in specifications.values() if spec["exists"])
                )
                
                status = {
                    "idea_id": idea_id,
                    "project_id": project_id,
                    "idea_title": idea.title,
                    "idea_summary": idea.summary,
                    "spec_id": spec_id,
                    "specifications": specifications,
                    "completion_status": {
                        "total_specs": len(spec_types),
                        "completed_specs": completed_count,
                        "completion_percentage": completion_percentage,
                        "ready_for_freeze": ready_for_freeze,
                        "missing_specs": missing_specs
                    }
                }
                
                return json.dumps(status, indent=2)
        except Exception as e:
            logger.error(f"Error getting spec status: {e}")
            return json.dumps({"error": f"Error getting spec status: {str(e)}"})

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

