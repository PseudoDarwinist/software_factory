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

import json
import logging
import sys
import os
from typing import Dict, Any, Optional, List, Union
import traceback

# Add project root to path to ensure imports work when run as a module
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import MCP library
try:
    # Server class lives in mcp.server. Result / error types live in mcp.types.
    from mcp.server import Server
    from mcp.types import Tool, CallToolResult
except ImportError:
    print("Error: MCP library not found. Install with: pip install mcp", file=sys.stderr)
    sys.exit(1)

# Flag to track if we're using mock data
using_mock_data = False

# Import models and services
try:
    from src.models.mission_control_project import MissionControlProject
    from src.models.system_map import SystemMap
    from src.models.feed_item import FeedItem
    from src.models.specification_artifact import SpecificationArtifact, ArtifactType, ArtifactStatus
    from src.models.base import db
    from src.events.domain_events import SpecDraftedEvent
    from src.events.event_router import get_event_bus
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
server = Server(name="software-factory")

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
        system_map = SystemMap.query.filter_by(project_id=project_id).first()
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
        feed_item = FeedItem.query.get(idea_id)
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
        project = MissionControlProject.query.get(project_id)
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
        artifact_id = f"{spec_id}_{artifact_type.value}"
        existing_artifact = SpecificationArtifact.query.get(artifact_id)
        
        if existing_artifact:
            # Update existing artifact
            existing_artifact.content = content
            existing_artifact.updated_at = db.func.now()
            existing_artifact.status = ArtifactStatus.DRAFT
            existing_artifact.ai_generated = True
            existing_artifact.ai_model_used = "mcp_assistant"
            db.session.commit()
            return artifact_id
        else:
            # Create new artifact
            artifact = SpecificationArtifact.create_artifact(
                spec_id=spec_id,
                project_id=project_id,
                artifact_type=artifact_type,
                content=content,
                created_by="mcp_service",
                ai_generated=True,
                ai_model_used="mcp_assistant",
                context_sources=["mcp_context"]
            )
            db.session.commit()
            return artifact.id
    except Exception as e:
        logger.error(f"Error storing spec artifact: {e}")
        db.session.rollback()
        return None

def publish_spec_drafted_event(spec_id: str, project_id: str, artifact_id: str):
    """Publish an event to notify the system that a spec has been drafted"""
    if using_mock_data:
        logger.info(f"Mock event published: SpecDraftedEvent for {spec_id}")
        return True
    
    try:
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

    logger.info("Starting Software Factory MCP server")
    
    if using_mock_data:
        logger.warning("Running with mock data - database connection not available")
    
    try:
        # Run the server (this blocks until the server exits)
        server.run()
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
            await server.run()
        except KeyboardInterrupt:
            logger.info("Server stopped by user")
        except Exception as e:
            logger.error(f"Server error: {e}")
            logger.error(traceback.format_exc())
            sys.exit(1)
    
    asyncio.run(run_server())

