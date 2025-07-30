"""
MCP (Model-Context Protocol) Router

This module implements the FastAPI router for MCP endpoints, allowing
external coding assistants to access context and generate specifications.
"""

import logging
import json
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query, Body, status
from pydantic import BaseModel

try:
    from ..models.mission_control_project import MissionControlProject
    from ..models.system_map import SystemMap
    from ..models.feed_item import FeedItem
    from ..models.specification_artifact import SpecificationArtifact, ArtifactType, ArtifactStatus
    from ..models.base import db
    from ..events.domain_events import SpecDraftedEvent
    from ..services.event_bus import get_event_bus
    from ..services.ai_broker import AIBroker, AIRequest, TaskType, Priority
except ImportError:
    # For local testing or when imports need to be adjusted
    logging.warning("Using relative imports in MCP router")
    from models.mission_control_project import MissionControlProject
    from models.system_map import SystemMap
    from models.feed_item import FeedItem
    from models.specification_artifact import SpecificationArtifact, ArtifactType, ArtifactStatus
    from models.base import db
    from events.domain_events import SpecDraftedEvent
    from services.event_bus import get_event_bus
    from services.ai_broker import AIBroker, AIRequest, TaskType, Priority

logger = logging.getLogger(__name__)
mcp_router = APIRouter(tags=["MCP"])

# --- Models ---

class MCPContextResponse(BaseModel):
    """Response model for context endpoint"""
    idea: Dict[str, Any]
    system_map: Dict[str, Any]
    repository_info: Optional[Dict[str, Any]] = None
    related_specs: Optional[List[Dict[str, Any]]] = None

class SpecDraftRequest(BaseModel):
    """Request model for spec draft generation"""
    assistant_type: str = "copilot"  # copilot, claude, cursor
    generate_requirements: bool = True
    generate_design: bool = True
    generate_tasks: bool = True
    custom_prompt: Optional[str] = None

class SpecDraftResponse(BaseModel):
    """Response model for spec draft generation"""
    status: str
    message: str
    job_id: Optional[str] = None
    artifacts: Optional[Dict[str, str]] = None

# --- Helper Functions ---

def get_system_map(project_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve system map for a project"""
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
    try:
        artifact_id = f"{spec_id}_{artifact_type.value}"
        existing_artifact = SpecificationArtifact.query.get(artifact_id)
        
        if existing_artifact:
            # Update existing artifact
            existing_artifact.content = content
            existing_artifact.updated_at = db.func.now()
            existing_artifact.status = ArtifactStatus.DRAFT
            existing_artifact.ai_generated = True
            existing_artifact.ai_model_used = "external_mcp"
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
                ai_model_used="external_mcp",
                context_sources=["mcp_context"]
            )
            db.session.commit()
            return artifact.id
    except Exception as e:
        logger.error(f"Error storing spec artifact: {e}")
        db.session.rollback()
        return None

# --- Mock External Assistant Integration ---

async def mock_external_assistant_call(prompt: str, system_map: Dict[str, Any], assistant_type: str) -> Dict[str, str]:
    """
    Mock function to simulate calling an external assistant API
    In a real implementation, this would call GitHub Copilot, Claude, etc.
    """
    # This is a placeholder - in production, implement actual API calls
    import time
    time.sleep(1)  # Simulate API latency
    
    return {
        "requirements": f"# Requirements Document\n\n## Overview\nThis is a mock requirements document generated by {assistant_type}.\n\n## Functional Requirements\n1. Requirement 1\n2. Requirement 2\n\n## Non-Functional Requirements\n1. Performance\n2. Security",
        "design": f"# Design Document\n\n## Architecture\nThis is a mock design document generated by {assistant_type}.\n\n## Components\n- Component 1\n- Component 2\n\n## Data Model\n- Entity 1\n- Entity 2",
        "tasks": f"# Implementation Tasks\n\n- [ ] Task 1: Implement component 1\n- [ ] Task 2: Create database schema\n- [ ] Task 3: Write unit tests\n- [ ] Task 4: Update documentation"
    }

# --- Endpoints ---

@mcp_router.get("/context/{idea_id}", response_model=MCPContextResponse)
async def get_mcp_context(
    idea_id: str,
    include_repo: bool = Query(True, description="Include repository information"),
    include_related: bool = Query(False, description="Include related specifications")
):
    """
    Get context information for an idea, following MCP protocol
    
    This endpoint provides context that external coding assistants can use
    to generate specifications or code.
    """
    idea_details = get_idea_details(idea_id)
    if not idea_details:
        raise HTTPException(status_code=404, detail=f"Idea {idea_id} not found")
    
    project_id = idea_details.get("project_id")
    if not project_id:
        raise HTTPException(status_code=400, detail="Idea has no associated project")
    
    system_map = get_system_map(project_id) or {}
    
    response = {
        "idea": idea_details,
        "system_map": system_map
    }
    
    if include_repo:
        response["repository_info"] = get_repository_info(project_id)
    
    # TODO: Implement related specs retrieval if needed
    if include_related:
        response["related_specs"] = []
    
    return response

@mcp_router.post("/spec-draft/{idea_id}", response_model=SpecDraftResponse)
async def generate_spec_draft(
    idea_id: str,
    request: SpecDraftRequest = Body(...),
    background_tasks: BackgroundTasks = None
):
    """
    Generate specification drafts using an external coding assistant
    
    This endpoint triggers the generation of requirements, design, and tasks
    documents using an external assistant like GitHub Copilot or Claude.
    """
    idea_details = get_idea_details(idea_id)
    if not idea_details:
        raise HTTPException(status_code=404, detail=f"Idea {idea_id} not found")
    
    project_id = idea_details.get("project_id")
    if not project_id:
        raise HTTPException(status_code=400, detail="Idea has no associated project")
    
    system_map = get_system_map(project_id) or {}
    
    # Create a spec ID based on the idea ID
    spec_id = f"spec_{idea_id}"
    
    try:
        # In a real implementation, this would be an async call to an external service
        # For now, we'll use a mock function
        prompt = request.custom_prompt or f"Generate specification documents for: {idea_details.get('title')} - {idea_details.get('summary')}"
        
        # For demo purposes, generate the specs synchronously
        # In production, this should be an async background task
        specs = await mock_external_assistant_call(prompt, system_map, request.assistant_type)
        
        # Store the generated artifacts
        artifacts = {}
        if request.generate_requirements and "requirements" in specs:
            req_id = store_spec_artifact(spec_id, project_id, ArtifactType.REQUIREMENTS, specs["requirements"])
            if req_id:
                artifacts["requirements"] = req_id
        
        if request.generate_design and "design" in specs:
            design_id = store_spec_artifact(spec_id, project_id, ArtifactType.DESIGN, specs["design"])
            if design_id:
                artifacts["design"] = design_id
        
        if request.generate_tasks and "tasks" in specs:
            tasks_id = store_spec_artifact(spec_id, project_id, ArtifactType.TASKS, specs["tasks"])
            if tasks_id:
                artifacts["tasks"] = tasks_id
        
        # Publish an event to notify the system that specs have been drafted
        # This allows the UI to update accordingly
        try:
            event_bus = get_event_bus()
            event = SpecDraftedEvent(
                spec_id=spec_id,
                project_id=project_id,
                drafted_by=f"mcp_{request.assistant_type}",
                artifact_ids=list(artifacts.values())
            )
            event_bus.publish(event)
        except Exception as e:
            logger.error(f"Error publishing spec drafted event: {e}")
        
        return {
            "status": "success",
            "message": f"Specifications generated successfully using {request.assistant_type}",
            "job_id": f"mcp_job_{idea_id}_{request.assistant_type}",
            "artifacts": artifacts
        }
    
    except Exception as e:
        logger.error(f"Error generating specifications: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate specifications: {str(e)}"
        )

# --- Status Endpoint ---

@mcp_router.get("/status")
async def mcp_status():
    """Check if the MCP service is running"""
    return {
        "status": "operational",
        "version": "1.0",
        "protocol": "MCP v1",
        "supported_assistants": ["copilot", "claude", "cursor"]
    }
