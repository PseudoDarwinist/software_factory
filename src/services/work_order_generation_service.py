"""
Work Order Generation Service - AI-powered work order creation with streaming
Generates comprehensive work orders with implementation plans from frozen specifications
"""

import logging
import json
import uuid
import asyncio
import os
from datetime import datetime
from typing import Dict, Any, List, Optional, Generator
from dataclasses import dataclass
from sqlalchemy import desc
from flask import current_app

try:
    from ..models.task import Task, TaskStatus, TaskPriority
    from ..models.specification_artifact import SpecificationArtifact, ArtifactType, ArtifactStatus
    from ..models.mission_control_project import MissionControlProject
except ImportError:
    from models.task import Task, TaskStatus, TaskPriority
    from models.specification_artifact import SpecificationArtifact, ArtifactType, ArtifactStatus
    from models.mission_control_project import MissionControlProject
try:
    from ..models.base import db
except ImportError:
    from models.base import db
try:
    from ..services.claude_code_service import ClaudeCodeService
    from ..services.ai_broker import AIBroker, AIRequest, TaskType, Priority
    from ..services.websocket_server import get_websocket_server
except ImportError:
    from services.claude_code_service import ClaudeCodeService
    from services.ai_broker import AIBroker, AIRequest, TaskType, Priority
    from services.websocket_server import get_websocket_server

logger = logging.getLogger(__name__)


@dataclass
class WorkOrderData:
    """Complete work order data structure"""
    id: str
    title: str
    description: str
    status: str
    assignee: str
    category: str
    task_number: str
    purpose: str
    requirements: List[str]
    context: str
    implementation_plan: Optional[Dict[str, Any]] = None
    prd_reference: Optional[str] = None
    blueprint_reference: Optional[str] = None
    design_reference: Optional[str] = None
    created_at: str = None
    # Additional comprehensive fields
    out_of_scope: List[str] = None
    blueprint_context: str = None
    prd_context: str = None


class WorkOrderGenerationService:
    """Service for generating AI-enhanced work orders with streaming support"""
    
    def __init__(self):
        try:
            from src.services.ai_broker import AIBroker
            self.ai_broker = AIBroker()
            logger.info("AIBroker initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize AIBroker: {e}")
            self.ai_broker = None
        
        try:
            from src.services.websocket_server import get_websocket_server
            self.websocket_server = get_websocket_server()
            logger.info("WebSocket server obtained successfully")
        except Exception as e:
            logger.error(f"Failed to get WebSocket server: {e}")
            self.websocket_server = None
        
    def generate_work_orders_stream(self, spec_id: str, project_id: str, enhanced: bool = True) -> Generator[Dict[str, Any], None, None]:
        """
        Generate work orders and stream them in real-time
        
        Args:
            spec_id: Specification ID (e.g., "spec_123")
            project_id: Project ID
            enhanced: If True, generate enhanced work orders with full content. If False, generate basic work orders.
            
        Yields:
            Dict containing work order data or status updates
        """
        # Get Flask app instance at the start to use throughout the generator
        app_instance = current_app._get_current_object()
        
        try:
            with app_instance.app_context():
                # Check if tasks for this spec have already been generated
                existing_task_count = db.session.query(Task).filter_by(spec_id=spec_id).count()
                if existing_task_count > 0:
                    logger.warning(f"Tasks for spec {spec_id} have already been generated. Skipping generation.")
                    yield {
                        "type": "generation_skipped",
                        "message": "Tasks for this specification have already been generated.",
                        "spec_id": spec_id,
                        "project_id": project_id,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    return

                generation_type = "enhanced" if enhanced else "basic"
                logger.info(f"Starting {generation_type} work order generation for spec {spec_id}, project {project_id}")

                # Get project information with detailed error handling
                try:
                    project = db.session.query(MissionControlProject).get(project_id)
                    if not project:
                        logger.error(f"Project not found: {project_id}")
                        yield {
                            "type": "generation_error",
                            "error": "Project not found",
                            "spec_id": spec_id,
                            "project_id": project_id,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        return
                    logger.info(f"Found project: {project.name if project else 'None'}")
                except Exception as e:
                    logger.error(f"Error querying project {project_id}: {e}")
                    import traceback
                    traceback.print_exc()
                    yield {
                        "type": "generation_error",
                        "error": f"Database error querying project: {str(e)}",
                        "spec_id": spec_id,
                        "project_id": project_id,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    return

                # Get frozen specification artifacts with detailed error handling, with fallback to latest frozen spec in project
                try:
                    artifacts = self._get_frozen_spec_artifacts(spec_id, project_id)
                    if not artifacts:
                        logger.warning(f"No frozen artifacts for spec {spec_id}. Attempting fallback to latest frozen spec in project {project_id}.")
                        # Fallback search: find latest spec in this project with tasks frozen
                        try:
                            latest_tasks = db.session.query(SpecificationArtifact).filter_by(
                                project_id=project_id,
                                artifact_type=ArtifactType.TASKS,
                                status=ArtifactStatus.FROZEN
                            ).order_by(desc(SpecificationArtifact.updated_at)).first()
                        except Exception as qerr:
                            latest_tasks = None
                            logger.error(f"Fallback query failed: {qerr}")

                        if latest_tasks is not None:
                            fallback_spec_id = latest_tasks.spec_id
                            logger.info(f"Using fallback frozen spec: {fallback_spec_id}")
                            # Inform client that fallback is used
                            yield {
                                "type": "fallback_spec_used",
                                "original_spec_id": spec_id,
                                "fallback_spec_id": fallback_spec_id,
                                "project_id": project_id,
                                "timestamp": datetime.utcnow().isoformat()
                            }
                            # Switch spec_id for subsequent processing
                            spec_id = fallback_spec_id
                            artifacts = self._get_frozen_spec_artifacts(spec_id, project_id)
                        else:
                            logger.error(f"No frozen specification artifacts found in project {project_id}")
                            yield {
                                "type": "generation_error",
                                "error": "No frozen specification artifacts found",
                                "spec_id": spec_id,
                                "project_id": project_id,
                                "timestamp": datetime.utcnow().isoformat()
                            }
                            return

                    logger.info(f"Found {len(artifacts)} frozen artifacts: {list(artifacts.keys())}")
                except Exception as e:
                    logger.error(f"Error getting frozen spec artifacts: {e}")
                    import traceback
                    traceback.print_exc()
                    yield {
                        "type": "generation_error",
                        "error": f"Database error getting spec artifacts: {str(e)}",
                        "spec_id": spec_id,
                        "project_id": project_id,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    return
            
            # Parse tasks from tasks.md
            tasks_artifact = artifacts.get('tasks')
            if not tasks_artifact:
                yield {
                    "type": "generation_error",
                    "error": "Tasks artifact not found in specification",
                    "spec_id": spec_id,
                    "project_id": project_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
                return
            
            # Parse individual tasks from markdown
            parsed_tasks = self._parse_tasks_from_markdown(tasks_artifact.content)
            if not parsed_tasks:
                yield {
                    "type": "generation_error",
                    "error": "No tasks found in tasks.md",
                    "spec_id": spec_id,
                    "project_id": project_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
                return
            
            logger.info(f"Found {len(parsed_tasks)} tasks to convert to basic work orders")
            
            # Yield initial status
            yield {
                "type": "generation_started",
                "spec_id": spec_id,
                "project_id": project_id,
                "total_tasks": len(parsed_tasks),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Generate basic work orders quickly (no AI enhancement yet)
            for i, task_data in enumerate(parsed_tasks):
                try:
                    logger.info(f"Creating basic work order {i+1}/{len(parsed_tasks)}: {task_data.get('title', 'Unknown')}")
                    
                    # Yield progress update
                    yield {
                        "type": "work_order_generating",
                        "task_number": task_data.get('task_number', str(i+1)),
                        "title": task_data.get('title', 'Unknown Task'),
                        "progress": f"{i+1}/{len(parsed_tasks)}",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    # Generate intelligent work order with Description, Blueprint, PRD tabs populated
                    # (Implementation tab will be generated separately when user clicks "Generate with AI")
                    work_order = self._generate_intelligent_work_order(
                        task_data, artifacts, project, spec_id, project_id
                    )
                    
                    if work_order:
                        # Save to database with individual transaction handling
                        try:
                            self._save_work_order_to_database(work_order, spec_id, project_id)
                        except Exception as save_error:
                            logger.error(f"Failed to save work order {work_order.id}: {save_error}")
                            # Continue with next work order even if this one fails to save
                            yield {
                                "type": "work_order_failed",
                                "task_number": task_data.get('task_number', str(i+1)),
                                "title": task_data.get('title', 'Unknown Task'),
                                "error": f"Database save failed: {str(save_error)}",
                                "timestamp": datetime.utcnow().isoformat()
                            }
                            continue
                        
                        # Broadcast via WebSocket
                        if self.websocket_server:
                            self.websocket_server.socketio.emit('work_order_created', {
                                'spec_id': spec_id,
                                'project_id': project_id,
                                'work_order': work_order.to_dict()
                            })
                        
                        # Yield the completed work order
                        yield {
                            "type": "work_order_created",
                            "work_order": work_order.to_dict(),
                            "progress": f"{i+1}/{len(parsed_tasks)}",
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        
                        logger.info(f"Successfully created intelligent work order: {work_order.title}")
                    else:
                        logger.error(f"Failed to create work order for task: {task_data.get('title')}")
                        yield {
                            "type": "work_order_failed",
                            "task_number": task_data.get('task_number', str(i+1)),
                            "title": task_data.get('title', 'Unknown Task'),
                            "error": "Failed to create work order",
                            "timestamp": datetime.utcnow().isoformat()
                        }
                
                except Exception as e:
                    logger.error(f"Error creating work order {i+1}: {e}")
                    yield {
                        "type": "work_order_failed",
                        "task_number": task_data.get('task_number', str(i+1)),
                        "title": task_data.get('title', 'Unknown Task'),
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    }
            
            # Yield completion status
            yield {
                "type": "generation_completed",
                "spec_id": spec_id,
                "project_id": project_id,
                "total_generated": len(parsed_tasks),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Completed basic work order generation for spec {spec_id}")
            
        except Exception as e:
            logger.error(f"Error in work order generation stream: {e}")
            yield {
                "type": "generation_error",
                "spec_id": spec_id,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def _get_frozen_spec_artifacts(self, spec_id: str, project_id: str):
        """Get frozen specification artifacts with improved fallback logic"""
        try:
            
            logger.info(f"Getting spec artifacts for spec_id: {spec_id}, project_id: {project_id}")
            
            # First try with both spec_id and project_id
            artifacts = db.session.query(SpecificationArtifact).filter_by(
                spec_id=spec_id, 
                project_id=project_id
            ).all()
            logger.info(f"Found {len(artifacts)} total artifacts for spec={spec_id} project={project_id}")

            # Fallback 1: if none found for project, try spec_id only
            if not artifacts:
                logger.warning(f"No artifacts found for spec={spec_id} and project={project_id}. Trying spec_id-only lookup.")
                artifacts = db.session.query(SpecificationArtifact).filter_by(
                    spec_id=spec_id
                ).all()
                logger.info(f"Spec_id-only lookup found {len(artifacts)} artifacts for spec={spec_id}")
            
            # Fallback 2: Try without the 'spec_' prefix if it exists
            if not artifacts and spec_id.startswith('spec_'):
                clean_spec_id = spec_id[5:]  # Remove 'spec_' prefix
                logger.warning(f"Trying without 'spec_' prefix: {clean_spec_id}")
                artifacts = db.session.query(SpecificationArtifact).filter_by(
                    spec_id=clean_spec_id
                ).all()
                logger.info(f"Clean spec_id lookup found {len(artifacts)} artifacts")
            
            # Process artifacts and look for frozen ones (with flexible status checking)
            frozen_artifacts = {}
            all_artifacts = {}  # Keep track of all artifacts regardless of status
            
            for artifact in artifacts:
                artifact_type_key = artifact.artifact_type.value if hasattr(artifact.artifact_type, 'value') else str(artifact.artifact_type)
                all_artifacts[artifact_type_key] = artifact
                
                # Check frozen status with multiple approaches
                is_frozen = False
                if hasattr(artifact.status, 'value'):
                    is_frozen = artifact.status.value == 'frozen'
                    logger.info(f"Artifact {artifact_type_key}: status={artifact.status.value}")
                elif isinstance(artifact.status, str):
                    is_frozen = artifact.status == 'frozen'
                    logger.info(f"Artifact {artifact_type_key}: status={artifact.status} (string)")
                elif artifact.status == ArtifactStatus.FROZEN:
                    is_frozen = True
                    logger.info(f"Artifact {artifact_type_key}: status=FROZEN (enum)")
                else:
                    logger.warning(f"Artifact {artifact_type_key}: unknown status type {type(artifact.status)}")
                
                if is_frozen:
                    frozen_artifacts[artifact_type_key] = artifact
            
            # If no frozen artifacts found, but we have artifacts, use them anyway with a warning
            if not frozen_artifacts and all_artifacts:
                logger.warning(f"No frozen artifacts found, but {len(all_artifacts)} artifacts exist. Using them anyway.")
                frozen_artifacts = all_artifacts
            
            logger.info(f"Found {len(frozen_artifacts)} usable artifacts: {list(frozen_artifacts.keys())}")
            return frozen_artifacts
        except Exception as e:
            logger.error(f"Error in _get_frozen_spec_artifacts: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def _parse_tasks_from_markdown(self, tasks_content: str) -> List[Dict[str, Any]]:
        """Parse individual tasks from tasks.md markdown content"""
        # First try checkbox format
        tasks = self._parse_checkbox_tasks(tasks_content)
        
        # If no checkbox tasks found, try prose format
        if not tasks:
            tasks = self._parse_prose_tasks(tasks_content)
        
        return tasks
    
    def _parse_checkbox_tasks(self, tasks_content: str) -> List[Dict[str, Any]]:
        """Parse checkbox format tasks (- [ ] or - [x])"""
        tasks = []
        lines = tasks_content.split('\n')
        current_task = None
        
        for line in lines:
            line = line.strip()
            
            # Look for task items (- [ ] or - [x])
            if line.startswith('- [') and ('] ' in line):
                # Save previous task if exists
                if current_task:
                    tasks.append(current_task)
                
                # Extract task number and title
                task_content = line.split('] ', 1)[1] if '] ' in line else line
                
                # Parse task number (e.g., "1.", "2.1", etc.)
                task_number = ""
                title = task_content
                if task_content and task_content[0].isdigit():
                    parts = task_content.split(' ', 1)
                    if len(parts) > 1 and ('.' in parts[0]):
                        task_number = parts[0].rstrip('.')
                        title = parts[1]
                
                current_task = {
                    'task_number': task_number,
                    'title': title,
                    'description': '',
                    'requirements_refs': [],
                    'details': []
                }
            
            # Look for task details (indented lines)
            elif line.startswith('  -') or line.startswith('    -'):
                if current_task:
                    detail = line.strip('- ').strip()
                    current_task['details'].append(detail)
                    
                    # Extract requirements references
                    if '_Requirements:' in detail:
                        req_part = detail.split('_Requirements:')[1].strip()
                        refs = [ref.strip() for ref in req_part.split(',')]
                        current_task['requirements_refs'].extend(refs)
        
        # Add the last task
        if current_task:
            tasks.append(current_task)
        
        return tasks
    
    def _parse_prose_tasks(self, tasks_content: str) -> List[Dict[str, Any]]:
        """Parse prose format tasks from AI-generated content"""
        tasks = []
        lines = tasks_content.split('\n')
        
        # Look for numbered items that might be tasks
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Skip empty lines and headers
            if not line or line.startswith('#'):
                continue
                
            # Look for numbered items (1., 2., etc.) or bullet points with numbers
            if (line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')) or
                (line.startswith('- ') and len(line) > 3 and line[2].isdigit())):
                
                # Extract task number and title
                if line.startswith('- '):
                    # Format: "- 1. Task title"
                    content = line[2:].strip()
                else:
                    # Format: "1. Task title"
                    content = line
                
                # Parse number and title
                parts = content.split('.', 1)
                if len(parts) >= 2:
                    task_number = parts[0].strip()
                    title = parts[1].strip()
                    
                    # Create task entry
                    task = {
                        'task_number': task_number,
                        'title': title,
                        'description': title,  # Use title as description for prose format
                        'requirements_refs': [],
                        'details': []
                    }
                    
                    # Look ahead for description lines
                    for j in range(i + 1, min(i + 5, len(lines))):
                        next_line = lines[j].strip()
                        if not next_line:
                            continue
                        if (next_line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')) or
                            next_line.startswith('- ') or next_line.startswith('#')):
                            break
                        # Add as description if it's a continuation
                        if len(next_line) > 10:  # Reasonable description length
                            task['description'] = next_line
                            break
                    
                    tasks.append(task)
        
        return tasks
    
    def _generate_intelligent_work_order(self, task_data: Dict[str, Any], 
                                       artifacts: Dict[str, Any],
                                       project: Any,
                                       spec_id: str, project_id: str) -> Optional[Task]:
        """Generate intelligent work order with Description, Blueprint, PRD tabs populated (NO Implementation plan)"""
        try:
            # Generate Description tab content
            description_content = self._generate_description_tab(task_data, artifacts, project)
            
            # Generate Blueprint tab content  
            blueprint_content = self._generate_blueprint_tab(task_data, artifacts)
            
            # Generate PRD tab content
            prd_content = self._generate_prd_tab(task_data, project)
            
            # Create Task record with populated content (but NO implementation plan)
            task_id = f"WO-{task_data.get('task_number', uuid.uuid4().hex[:8])}"
            
            task = Task(
                id=task_id,
                title=task_data.get('title', 'Unknown Task'),
                description=task_data.get('description', ''),
                status=TaskStatus.BACKLOG,  # Start as Backlog - will become Ready when Implementation is generated
                project_id=project_id,
                spec_id=spec_id,
                task_number=task_data.get('task_number', ''),
                requirements_refs=task_data.get('requirements_refs', []),
                
                # Associate with idea (extract from spec_id or project context)
                related_idea=self._extract_related_idea(spec_id, project),
                
                # Populate the 3 tabs with AI-generated content
                description_content=description_content,
                blueprint_content=blueprint_content, 
                prd_content=prd_content,
                
                # NO implementation fields - these will be populated when user clicks "Generate with AI" in Implementation tab
                implementation_approach=None,
                implementation_goals=None,
                implementation_strategy=None,
                technical_dependencies=None,
                files_to_create=None,
                files_to_modify=None,
                
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            return task
            
        except Exception as e:
            logger.error(f"Error generating intelligent work order: {e}")
            return None
    
    def _extract_related_idea(self, spec_id: str, project: Any) -> str:
        """Extract the related idea name from spec_id or project context"""
        try:
            # Try to extract idea name from spec_id (e.g., "spec_wine_post_creation" -> "Wine Post Creation")
            if spec_id.startswith('spec_'):
                idea_name = spec_id[5:]  # Remove 'spec_' prefix
                # Convert underscores to spaces and title case
                idea_name = idea_name.replace('_', ' ').title()
                return idea_name
            
            # Fallback to project name if available
            if project and hasattr(project, 'name'):
                return f"{project.name} Feature"
            
            # Default fallback
            return "Core Functionality"
            
        except Exception as e:
            logger.warning(f"Error extracting related idea: {e}")
            return "Core Functionality"
    
    def generate_implementation_plan(self, work_order_id: str, spec_id: str, project_id: str) -> Dict[str, Any]:
        """
        Generate detailed implementation plan for a specific work order
        This is called when user clicks "Generate with AI" in the Implementation tab
        """
        try:
            
            logger.info(f"Generating implementation plan for work order {work_order_id}")
            
            # Get the work order from database
            task = Task.query.get(work_order_id)
            if not task:
                return {"success": False, "error": "Work order not found"}
            
            # Get project information
            project = MissionControlProject.query.get(project_id)
            if not project:
                return {"success": False, "error": "Project not found"}
            
            # Get frozen specification artifacts
            artifacts = self._get_frozen_spec_artifacts(spec_id, project_id)
            if not artifacts:
                return {"success": False, "error": "No frozen specification artifacts found"}
            
            # Prepare task data from database record
            task_data = {
                'task_number': task.task_number,
                'title': task.title,
                'description': task.description,
                'details': task.requirements_refs or []
            }
            
            # Generate comprehensive implementation plan with AI
            implementation_plan = self._generate_ai_implementation_plan(
                task_data, artifacts, project, spec_id, project_id
            )
            
            if implementation_plan:
                # Update the task with implementation plan
                task.implementation_approach = implementation_plan.get('approach')
                task.implementation_goals = implementation_plan.get('goals')
                task.implementation_strategy = implementation_plan.get('strategy')
                task.technical_dependencies = implementation_plan.get('dependencies')
                task.files_to_create = implementation_plan.get('files_to_create')
                task.files_to_modify = implementation_plan.get('files_to_modify')
                task.enhancement_status = 'approved'
                task.enhanced_at = datetime.utcnow()
                task.enhanced_by = 'ai_generator'
                task.approved_at = datetime.utcnow()
                task.approved_by = 'ai_generator'
                task.status = TaskStatus.READY  # Change status to Ready
                
                db.session.commit()
                
                # Broadcast via WebSocket
                if self.websocket_server:
                    self.websocket_server.broadcast_work_order_enhanced(work_order_id, implementation_plan)
                    self.websocket_server.broadcast_work_order_ready(work_order_id)
                
                logger.info(f"Successfully generated implementation plan for work order {work_order_id}")
                
                return {
                    "success": True,
                    "implementation_plan": implementation_plan,
                    "status": "READY"
                }
            else:
                return {"success": False, "error": "Failed to generate implementation plan"}
                
        except Exception as e:
            logger.error(f"Error generating implementation plan for work order {work_order_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_comprehensive_work_order_content(self, task_data: Dict[str, Any], 
                                                 artifacts: Dict[str, Any],
                                                 project: Any,
                                                 spec_id: str, project_id: str) -> Optional[Dict[str, Any]]:
        """Generate comprehensive work order content using AI (everything except implementation plan)"""
        try:
            # Prepare context for AI generation
            context = self._prepare_work_order_context(task_data, artifacts, project)
            
            # Create prompt for comprehensive work order content
            prompt = self._create_comprehensive_work_order_prompt(task_data, context)
            
            # Use Claude Code for generation
            repo_path = self._get_project_repository_path(project)
            claude_service = ClaudeCodeService(repo_path)
            
            if claude_service.is_available():
                logger.info(f"Using Claude Code SDK for comprehensive work order: {task_data.get('title')}")
                result = claude_service.execute_task(prompt)
                
                if result.get('success'):
                    # Parse the AI response
                    content_data = self._parse_comprehensive_work_order_response(result.get('output', ''))
                    return content_data
                else:
                    logger.error(f"Claude Code failed: {result.get('error')}")
            
            # Fallback to AI Broker
            logger.info("Falling back to AI Broker for comprehensive work order")
            ai_request = AIRequest(
                request_id=f"comp_wo_{uuid.uuid4().hex[:8]}",
                task_type=TaskType.DOCUMENTATION,
                instruction=prompt,
                priority=Priority.HIGH,
                max_tokens=12000,
                timeout_seconds=120.0,
                preferred_models=['claude-opus-4'],
                metadata={'agent': 'comprehensive_work_order_generator', 'task_number': task_data.get('task_number')}
            )
            
            # Use extended timeout for complex PRD analysis
            timeout_seconds = float(os.environ.get('CLAUDE_OPUS_TIMEOUT_SECONDS', 300))
            response = self.ai_broker.submit_request_sync(ai_request, timeout=timeout_seconds)
            
            if response.success:
                content_data = self._parse_comprehensive_work_order_response(response.content)
                return content_data
            else:
                logger.error(f"AI Broker failed: {response.error_message}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating comprehensive work order content: {e}")
            return None
    
    def _create_comprehensive_work_order_prompt(self, task_data: Dict[str, Any], context: str) -> str:
        """Create AI prompt for comprehensive work order content generation"""
        return f"""You are an expert business analyst and project manager. Generate comprehensive work order content for the following task, including detailed description, requirements, and context sections.

{context}

TASK TO CREATE WORK ORDER FOR:
Task Number: {task_data.get('task_number', 'Unknown')}
Title: {task_data.get('title', 'Unknown Task')}
Description: {task_data.get('description', '')}

INSTRUCTIONS:
Generate comprehensive work order content that includes:
1. **Purpose**: Clear explanation of what this work order accomplishes
2. **Requirements**: 6+ detailed, specific requirements for this task
3. **Out of Scope**: Items that are explicitly NOT included in this work order
4. **Context**: Detailed context explaining the business need and technical background
5. **Blueprint Context**: References to relevant requirements, design, and task sections
6. **PRD Context**: Relevant PRD information for this specific work order

Generate a JSON response with the following structure:

{{
    "purpose": "Clear, detailed explanation of what this work order accomplishes and its business value",
    "requirements": [
        "Specific, detailed requirement 1 with clear acceptance criteria",
        "Specific, detailed requirement 2 with measurable outcomes",
        "Specific, detailed requirement 3 with technical specifications",
        "Specific, detailed requirement 4 with integration requirements",
        "Specific, detailed requirement 5 with error handling specifications",
        "Specific, detailed requirement 6 with authentication/authorization requirements"
    ],
    "out_of_scope": [
        "Specific item 1 that is NOT included in this work order",
        "Specific item 2 that will be handled by other work orders",
        "Specific item 3 that is beyond the scope of this implementation",
        "Specific item 4 that requires separate infrastructure work"
    ],
    "context": "Comprehensive context explaining the business need, technical background, and how this work order fits into the overall project",
    "blueprint_context": "References to specific requirements, design sections, and task details that relate to this work order",
    "prd_context": "Relevant PRD information, user stories, and business goals that this work order addresses"
}}

CRITICAL REQUIREMENTS:
- Make requirements extremely detailed and specific
- Include technical specifications and acceptance criteria
- Ensure out of scope items are clearly defined
- Provide comprehensive context that explains the business value
- Reference specific sections from requirements, design, and PRD documents
- Make it detailed enough that a developer understands exactly what needs to be built"""
    
    def _parse_comprehensive_work_order_response(self, ai_response: str) -> Optional[Dict[str, Any]]:
        """Parse AI response for comprehensive work order content"""
        try:
            # Try to extract JSON from the response
            json_start = ai_response.find('{')
            json_end = ai_response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_content = ai_response[json_start:json_end]
                content_data = json.loads(json_content)
                
                # Validate required fields
                required_fields = ['purpose', 'requirements', 'out_of_scope', 'context', 'blueprint_context', 'prd_context']
                for field in required_fields:
                    if field not in content_data:
                        logger.warning(f"Missing required field in work order content: {field}")
                        if field in ['requirements', 'out_of_scope']:
                            content_data[field] = []
                        else:
                            content_data[field] = ""
                
                return content_data
            else:
                logger.error("No valid JSON found in comprehensive work order response")
                return None
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse comprehensive work order response as JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing comprehensive work order response: {e}")
            return None
    
    def _extract_out_of_scope_from_task(self, task_data: Dict[str, Any], 
                                      artifacts: Dict[str, Any]) -> List[str]:
        """Extract out of scope items for the task"""
        out_of_scope = []
        
        title = task_data.get('title', '').lower()
        if 'api' in title:
            out_of_scope.extend([
                "Frontend user interface implementation",
                "Database schema creation or migration scripts",
                "Integration with external services or third-party APIs",
                "Detailed reporting or analytics functionality"
            ])
        elif 'component' in title or 'ui' in title:
            out_of_scope.extend([
                "Backend API implementation",
                "Database operations and data persistence",
                "Authentication and authorization logic",
                "Integration with external services"
            ])
        elif 'model' in title or 'data' in title:
            out_of_scope.extend([
                "Frontend user interface components",
                "API endpoint implementation",
                "Business logic and validation rules",
                "Integration with external data sources"
            ])
        
        return out_of_scope[:4]  # Limit to 4 items
    
    def _extract_blueprint_context(self, task_data: Dict[str, Any], 
                                 artifacts: Dict[str, Any]) -> str:
        """Extract blueprint context from requirements, design, and tasks"""
        context_parts = []
        
        # Add requirements context
        if 'requirements' in artifacts:
            context_parts.append("Requirements: Based on project requirements for comprehensive functionality and user experience.")
        
        # Add design context
        if 'design' in artifacts:
            context_parts.append("Design: Follows established design patterns and architectural decisions.")
        
        # Add task context
        if 'tasks' in artifacts:
            context_parts.append("Tasks: Part of the overall implementation plan for the project.")
        
        # Add task-specific references
        if task_data.get('requirements_refs'):
            refs = ', '.join(task_data['requirements_refs'])
            context_parts.append(f"Specific Requirements: {refs}")
        
        return " ".join(context_parts) if context_parts else "Blueprint context from project specifications."
    
    def _extract_prd_context(self, task_data: Dict[str, Any], 
                           artifacts: Dict[str, Any]) -> str:
        """Extract PRD context for the work order"""
        # This would ideally pull from actual PRD data
        # For now, generate contextual PRD information based on task
        title = task_data.get('title', '').lower()
        
        if 'api' in title:
            return "PRD Context: Supports core platform functionality for data operations and business logic processing, enabling user interactions and system integrations."
        elif 'component' in title or 'ui' in title:
            return "PRD Context: Enhances user experience through intuitive interface components, supporting key user workflows and interaction patterns."
        elif 'model' in title or 'data' in title:
            return "PRD Context: Establishes data foundation for business operations, ensuring data integrity and supporting analytics and reporting requirements."
        else:
            return "PRD Context: Contributes to overall platform capabilities and user experience goals outlined in the product requirements."
    
    def _extract_purpose_from_task(self, task_data: Dict[str, Any], 
                                 artifacts: Dict[str, Any]) -> str:
        """Extract purpose from task data and requirements"""
        title = task_data.get('title', '')
        
        # Generate purpose based on title and context
        if 'api' in title.lower():
            return f"Create API functionality for {title.lower().replace('implement ', '').replace('api', '').strip()}"
        elif 'component' in title.lower():
            return f"Build UI component for {title.lower().replace('implement ', '').replace('component', '').strip()}"
        elif 'model' in title.lower() or 'data' in title.lower():
            return f"Implement data model and operations for {title.lower().replace('implement ', '').strip()}"
        else:
            return f"Implement {title.lower().replace('implement ', '').strip()}"
    
    def _extract_requirements_from_task(self, task_data: Dict[str, Any], 
                                      artifacts: Dict[str, Any]) -> List[str]:
        """Extract requirements from task details and referenced requirements"""
        requirements = []
        
        # Add requirements from task details
        for detail in task_data.get('details', []):
            if not detail.startswith('_Requirements:'):
                requirements.append(detail)
        
        # Add some default requirements based on task type
        title = task_data.get('title', '').lower()
        if 'api' in title:
            requirements.extend([
                "API must handle authentication and authorization",
                "API must implement proper error handling with HTTP status codes",
                "API must validate input data and return appropriate error messages"
            ])
        elif 'component' in title:
            requirements.extend([
                "Component must be responsive and accessible",
                "Component must follow existing design system patterns",
                "Component must handle loading and error states"
            ])
        
        return requirements[:6]  # Limit to 6 requirements
    
    def _extract_context_from_task(self, task_data: Dict[str, Any], 
                                 artifacts: Dict[str, Any]) -> str:
        """Extract context from task and specification artifacts"""
        context_parts = []
        
        # Add task description
        if task_data.get('description'):
            context_parts.append(task_data['description'])
        
        # Add context from requirements if available
        if 'requirements' in artifacts:
            req_content = artifacts['requirements'].content
            # Extract relevant section (simplified)
            context_parts.append("Based on project requirements for comprehensive functionality.")
        
        # Add context from design if available
        if 'design' in artifacts:
            context_parts.append("Follows established design patterns and architecture.")
        
        return " ".join(context_parts) if context_parts else f"Implementation of {task_data.get('title', 'task')}"
    
    def _generate_ai_implementation_plan(self, task_data: Dict[str, Any], 
                                       artifacts: Dict[str, Any],
                                       project: Any,
                                       spec_id: str, project_id: str) -> Optional[Dict[str, Any]]:
        """Generate detailed implementation plan using AI"""
        try:
            # Get Claude Code service for repository-aware generation
            repo_path = self._get_project_repository_path(project)
            claude_service = ClaudeCodeService(repo_path)
            
            # Prepare context for AI generation
            context = self._prepare_implementation_plan_context(task_data, artifacts, project)
            
            # Generate implementation plan prompt
            prompt = self._create_implementation_plan_prompt(task_data, context)
            
            # Use Claude Code for codebase-aware generation
            if claude_service.is_available():
                logger.info(f"Using Claude Code SDK for implementation plan: {task_data.get('title')}")
                result = claude_service.execute_task(prompt)
                
                if result.get('success'):
                    # Parse the AI response to extract implementation plan
                    implementation_plan = self._parse_ai_implementation_plan_response(
                        result.get('output', '')
                    )
                    return implementation_plan
                else:
                    logger.error(f"Claude Code failed: {result.get('error')}")
            
            # Fallback to AI Broker
            logger.info("Falling back to AI Broker for implementation plan generation")
            ai_request = AIRequest(
                request_id=f"impl_plan_{uuid.uuid4().hex[:8]}",
                task_type=TaskType.PLANNING,
                instruction=prompt,
                priority=Priority.HIGH,
                max_tokens=16000,
                timeout_seconds=180.0,
                preferred_models=['claude-opus-4'],
                metadata={'agent': 'implementation_planner', 'task_number': task_data.get('task_number')}
            )
            
            response = self.ai_broker.submit_request_sync(ai_request, timeout=120.0)
            
            if response.success:
                implementation_plan = self._parse_ai_implementation_plan_response(response.content)
                return implementation_plan
            else:
                logger.error(f"AI Broker failed: {response.error_message}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating AI implementation plan: {e}")
            return None
    
    def _prepare_work_order_context(self, task_data: Dict[str, Any], 
                                  artifacts: Dict[str, Any],
                                  project: Any) -> str:
        """Prepare comprehensive context for work order generation"""
        context_parts = []
        
        # Add requirements context
        if 'requirements' in artifacts:
            context_parts.append("=== REQUIREMENTS CONTEXT ===")
            context_parts.append(artifacts['requirements'].content[:2000])
            context_parts.append("")
        
        # Add design context
        if 'design' in artifacts:
            context_parts.append("=== DESIGN CONTEXT ===")
            context_parts.append(artifacts['design'].content[:2000])
            context_parts.append("")
        
        # Add project information
        context_parts.append("=== PROJECT CONTEXT ===")
        context_parts.append(f"Project: {project.name}")
        if project.repo_url:
            context_parts.append(f"Repository: {project.repo_url}")
        context_parts.append("")
        
        # Add task-specific details
        if task_data.get('details'):
            context_parts.append("=== TASK DETAILS ===")
            for detail in task_data['details']:
                context_parts.append(f"- {detail}")
            context_parts.append("")
        
        return "\n".join(context_parts)
    
    def _prepare_implementation_plan_context(self, task_data: Dict[str, Any], 
                                           artifacts: Dict[str, Any],
                                           project: Any) -> str:
        """Prepare comprehensive context for implementation plan generation"""
        context_parts = []
        
        # Add requirements context
        if 'requirements' in artifacts:
            context_parts.append("=== REQUIREMENTS CONTEXT ===")
            context_parts.append(artifacts['requirements'].content[:3000])
            context_parts.append("")
        
        # Add design context
        if 'design' in artifacts:
            context_parts.append("=== DESIGN CONTEXT ===")
            context_parts.append(artifacts['design'].content[:3000])
            context_parts.append("")
        
        # Add project information
        context_parts.append("=== PROJECT CONTEXT ===")
        context_parts.append(f"Project: {project.name}")
        if project.repo_url:
            context_parts.append(f"Repository: {project.repo_url}")
        context_parts.append("")
        
        # Add task-specific details
        if task_data.get('details'):
            context_parts.append("=== TASK DETAILS ===")
            for detail in task_data['details']:
                context_parts.append(f"- {detail}")
            context_parts.append("")
        
        return "\n".join(context_parts)
    
    def _create_implementation_plan_prompt(self, task_data: Dict[str, Any], context: str) -> str:
        """Create AI prompt for detailed implementation plan generation"""
        return f"""You are an expert software architect and senior developer. Generate a comprehensive, codebase-aware implementation plan for the following work order.

{context}

WORK ORDER TO IMPLEMENT:
Task Number: {task_data.get('task_number', 'Unknown')}
Title: {task_data.get('title', 'Unknown Task')}
Description: {task_data.get('description', '')}

INSTRUCTIONS:
1. **ANALYZE THE REPOSITORY FIRST**: Use your filesystem access to examine:
   - Project structure and existing patterns
   - Similar implementations and components
   - Technology stack and dependencies
   - Database models and API patterns
   - Component architectures and relationships

2. **GENERATE DETAILED IMPLEMENTATION PLAN**: Create a comprehensive plan that includes:
   - Specific approach and strategy
   - Clear implementation goals
   - Technical dependencies and requirements
   - Exact files to modify with detailed reasoning
   - New files to create with specific purposes

Generate a JSON response with the following structure:

{{
    "approach": "Detailed summary of the implementation approach based on repository analysis",
    "goals": [
        "Specific, measurable goal 1",
        "Specific, measurable goal 2",
        "Specific, measurable goal 3",
        "Specific, measurable goal 4"
    ],
    "strategy": "Comprehensive strategy explaining step-by-step how to implement this feature, referencing existing code patterns and architectural decisions found in the repository",
    "dependencies": [
        "Specific dependency 1 with explanation of why it's needed",
        "Specific dependency 2 with explanation of integration points",
        "Specific dependency 3 with explanation of existing code it builds upon"
    ],
    "files_to_modify": [
        {{
            "path": "exact/file/path/found/in/repo.py",
            "reason": "Detailed reason for modification based on repository analysis",
            "description": "Specific changes needed, referencing existing patterns and functions"
        }},
        {{
            "path": "another/existing/file.js",
            "reason": "Clear explanation of why this file needs changes",
            "description": "Detailed description of modifications needed"
        }}
    ],
    "files_to_create": [
        {{
            "path": "new/file/following/existing/patterns.py",
            "reason": "Detailed reason for creation, explaining how it fits into existing architecture",
            "description": "Comprehensive description of what this file will contain and how it integrates with existing code"
        }},
        {{
            "path": "another/new/component.tsx",
            "reason": "Clear explanation of why this new file is needed",
            "description": "Detailed description of the component and its integration points"
        }}
    ]
}}

CRITICAL REQUIREMENTS:
- Make the implementation plan extremely detailed and codebase-aware
- Reference actual files, classes, and patterns found in the repository
- Provide clear reasoning for each file operation based on repository analysis
- Ensure the plan is immediately actionable by a developer
- Include specific integration points with existing code
- Reference existing architectural patterns and conventions
- Make it comprehensive enough that a developer can execute without additional research"""
    
    def _parse_ai_implementation_plan_response(self, ai_response: str) -> Optional[Dict[str, Any]]:
        """Parse AI response and extract implementation plan data"""
        try:
            # Try to extract JSON from the response
            json_start = ai_response.find('{')
            json_end = ai_response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_content = ai_response[json_start:json_end]
                implementation_plan = json.loads(json_content)
                
                # Validate required fields
                required_fields = ['approach', 'goals', 'strategy', 'dependencies', 'files_to_modify', 'files_to_create']
                for field in required_fields:
                    if field not in implementation_plan:
                        logger.warning(f"Missing required field in implementation plan: {field}")
                        implementation_plan[field] = [] if field in ['goals', 'dependencies', 'files_to_modify', 'files_to_create'] else ""
                
                return implementation_plan
            else:
                logger.error("No valid JSON found in AI implementation plan response")
                return None
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI implementation plan response as JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing AI implementation plan response: {e}")
            return None
    
    def _create_work_order_generation_prompt(self, task_data: Dict[str, Any], context: str) -> str:
        """Create AI prompt for comprehensive work order generation"""
        return f"""You are an expert software architect and project manager. Generate a comprehensive work order with detailed implementation plan for the following task.

{context}

TASK TO CONVERT TO WORK ORDER:
Task Number: {task_data.get('task_number', 'Unknown')}
Title: {task_data.get('title', 'Unknown Task')}
Description: {task_data.get('description', '')}

INSTRUCTIONS:
1. Analyze the repository structure and existing patterns
2. Create a comprehensive work order with all required details
3. Generate a detailed, codebase-aware implementation plan
4. Include specific files to modify and create with reasoning

Generate a JSON response with the following structure:

{{
    "title": "Clear, descriptive work order title",
    "category": "API Implementation|UI Implementation|Data Model|Infrastructure|Testing",
    "purpose": "Clear explanation of what this work order accomplishes",
    "requirements": [
        "Specific requirement 1",
        "Specific requirement 2",
        "Specific requirement 3"
    ],
    "context": "Detailed context explaining why this work order is needed",
    "implementation_plan": {{
        "approach": "Detailed summary of the implementation approach",
        "goals": [
            "Specific goal 1",
            "Specific goal 2",
            "Specific goal 3"
        ],
        "strategy": "Comprehensive strategy explaining how to implement this feature",
        "dependencies": [
            "Dependency 1 with explanation",
            "Dependency 2 with explanation"
        ],
        "files_to_modify": [
            {{
                "path": "specific/file/path.py",
                "reason": "Detailed reason for modification",
                "description": "Specific changes needed"
            }}
        ],
        "files_to_create": [
            {{
                "path": "new/file/path.py",
                "reason": "Detailed reason for creation",
                "description": "What this new file will contain"
            }}
        ]
    }}
}}

IMPORTANT:
- Make the implementation plan extremely detailed and codebase-aware
- Include specific file paths that exist in the repository
- Provide clear reasoning for each file operation
- Ensure the work order is immediately actionable by a developer
- Status should be "READY" since this is fully AI-enhanced
- Make it comprehensive enough that a developer can execute without additional research"""
    
    def _parse_ai_work_order_response(self, ai_response: str, task_data: Dict[str, Any], 
                                    spec_id: str, project_id: str) -> Optional[WorkOrderData]:
        """Parse AI response and create WorkOrderData object"""
        try:
            # Try to extract JSON from the response
            json_start = ai_response.find('{')
            json_end = ai_response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_content = ai_response[json_start:json_end]
                parsed_data = json.loads(json_content)
                
                # Create work order data
                work_order = WorkOrderData(
                    id=f"wo_{spec_id}_{task_data.get('task_number', uuid.uuid4().hex[:8])}",
                    title=parsed_data.get('title', task_data.get('title', 'Unknown Task')),
                    description=parsed_data.get('context', ''),
                    status='ready',  # AI-enhanced work orders are immediately ready (use lowercase for enum)
                    assignee='AM Andrew Melbourne',  # Default assignee from screenshots
                    category=parsed_data.get('category', 'Implementation'),
                    task_number=task_data.get('task_number', ''),
                    purpose=parsed_data.get('purpose', ''),
                    requirements=parsed_data.get('requirements', []),
                    context=parsed_data.get('context', ''),
                    implementation_plan=parsed_data.get('implementation_plan'),
                    prd_reference=f"PRD for {spec_id}",
                    blueprint_reference=f"Design for {spec_id}",
                    design_reference=f"Requirements for {spec_id}",
                    created_at=datetime.utcnow().isoformat()
                )
                
                return work_order
            else:
                logger.error("No valid JSON found in AI response")
                return None
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing AI work order response: {e}")
            return None
    
    def _save_work_order_to_database(self, task: Task, spec_id: str, project_id: str):
        """Save a Task (work order) to the database"""
        try:
            # Check if task already exists
            existing_task = db.session.query(Task).get(task.id)
            
            if existing_task:
                # Update existing task with new content
                existing_task.title = task.title
                existing_task.description = task.description
                existing_task.description_content = task.description_content
                existing_task.blueprint_content = task.blueprint_content
                existing_task.prd_content = task.prd_content
                existing_task.updated_at = datetime.utcnow()
                logger.info(f"Updating existing work order: {existing_task.title}")
            else:
                # Add new task to session
                db.session.add(task)
                logger.info(f"Creating new intelligent work order: {task.title}")

            db.session.commit()
            logger.info(f"Successfully saved work order {task.id} to database")
            
        except Exception as e:
            logger.error(f"Error saving work order to database: {e}")
            db.session.rollback()
            raise
    
    def _get_project_repository_path(self, project: Any) -> str:
        """Get the local repository path for the project"""
        # This would need to be implemented based on how repositories are managed
        # For now, return current working directory
        import os
        return os.getcwd()
    
    def get_work_orders_for_spec(self, spec_id: str, project_id: str) -> List[Dict[str, Any]]:
        """Get all work orders for a specification"""
        try:
            # Get tasks that were created as work orders for this spec
            tasks = db.session.query(Task).filter_by(spec_id=spec_id, project_id=project_id).all()
            
            work_orders = []
            for task in tasks:
                work_order = {
                    'id': task.id,
                    'title': task.title,
                    'description': task.description,
                    'status': task.status.value,
                    'assignee': task.assigned_to or 'Unassigned',
                    'category': self._determine_category(task.title),
                    'task_number': task.task_number,
                    'purpose': task.goal_line,
                    'requirements': task.requirements_refs or [],
                    'context': task.description,
                    'implementation_plan': {
                        'approach': task.implementation_approach,
                        'goals': task.implementation_goals,
                        'strategy': task.implementation_strategy,
                        'dependencies': task.technical_dependencies,
                        'files_to_modify': task.files_to_modify,
                        'files_to_create': task.files_to_create
                    } if task.implementation_approach else None,
                    'created_at': task.created_at.isoformat() if task.created_at else None
                }
                work_orders.append(work_order)
            
            return work_orders
            
        except Exception as e:
            logger.error(f"Error getting work orders for spec {spec_id}: {e}")
            return []
    
    def get_work_order_generation_status(self, spec_id: str, project_id: str) -> Dict[str, Any]:
        """Get work order generation status for a specification"""
        try:
            tasks = db.session.query(Task).filter_by(spec_id=spec_id, project_id=project_id).all()
            
            if not tasks:
                return {
                    'status': 'not_started',
                    'total_work_orders': 0,
                    'generated_work_orders': 0,
                    'ready_work_orders': 0
                }
            
            ready_count = sum(1 for task in tasks if task.status == TaskStatus.READY)
            
            return {
                'status': 'completed' if ready_count == len(tasks) else 'in_progress',
                'total_work_orders': len(tasks),
                'generated_work_orders': len(tasks),
                'ready_work_orders': ready_count
            }
            
        except Exception as e:
            logger.error(f"Error getting work order status for spec {spec_id}: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _generate_description_tab(self, task_data: Dict[str, Any], 
                                artifacts: Dict[str, Any],
                                claude_service: Any = None) -> Optional[Dict[str, Any]]:
        """Generate description tab content using AI"""
        try:
            # Prepare context for description generation
            context = self._prepare_work_order_context(task_data, artifacts, None)
            
            # Create prompt for description tab
            prompt = self._create_description_tab_prompt(task_data, context)
            
            # Use Claude Code if available
            if claude_service and claude_service.is_available():
                logger.info(f"Using Claude Code SDK for description tab: {task_data.get('title')}")
                result = claude_service.execute_task(prompt)
                
                if result.get('success'):
                    # Parse the AI response
                    description_data = self._parse_description_tab_response(result.get('output', ''))
                    return description_data
                else:
                    logger.error(f"Claude Code failed for description tab: {result.get('error')}")
            
            # Fallback to AI Broker
            logger.info("Falling back to AI Broker for description tab generation")
            ai_request = AIRequest(
                request_id=f"desc_tab_{uuid.uuid4().hex[:8]}",
                task_type=TaskType.DOCUMENTATION,
                instruction=prompt,
                priority=Priority.HIGH,
                max_tokens=8000,
                timeout_seconds=90.0,
                preferred_models=['claude-opus-4'],
                metadata={'agent': 'description_tab_generator', 'task_number': task_data.get('task_number')}
            )
            
            response = self.ai_broker.submit_request_sync(ai_request, timeout=60.0)
            
            if response.success:
                description_data = self._parse_description_tab_response(response.content)
                return description_data
            else:
                logger.error(f"AI Broker failed for description tab: {response.error_message}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating description tab: {e}")
            return None
    
    def _create_description_tab_prompt(self, task_data: Dict[str, Any], context: str) -> str:
        """Create prompt for Description tab generation following existing prompt patterns"""
        return f"""You are an expert business analyst and project manager. Generate comprehensive description tab content for the following work order task.

{context}

TASK TO CREATE DESCRIPTION FOR:
Task Number: {task_data.get('task_number', 'Unknown')}
Title: {task_data.get('title', 'Unknown Task')}
Description: {task_data.get('description', '')}
Task Details: {', '.join(task_data.get('details', []))}

INSTRUCTIONS:
Generate description tab content that clearly explains the purpose, requirements, and scope boundaries for this work order. This content will help developers understand exactly what needs to be accomplished and what is explicitly out of scope.

Generate a JSON response with the following structure:

{{
    "purpose": "Clear, detailed explanation of what this work order accomplishes and its business value. Explain the technical objective and how it contributes to the overall project goals.",
    "requirements": [
        "Specific functional requirement 1 extracted from requirements.md that applies to this work order",
        "Specific functional requirement 2 with clear acceptance criteria",
        "Specific functional requirement 3 with measurable outcomes",
        "Specific functional requirement 4 with technical specifications",
        "Specific functional requirement 5 with integration requirements"
    ],
    "out_of_scope": [
        "Specific item 1 that is NOT included in this work order",
        "Specific item 2 that will be handled by other work orders or phases",
        "Specific item 3 that is beyond the scope of this implementation",
        "Specific item 4 that requires separate infrastructure or setup work"
    ]
}}

CRITICAL REQUIREMENTS:
- Make the purpose clear and business-focused, explaining both technical and business value
- Extract specific requirements from the requirements.md context that directly relate to this task
- Ensure requirements are detailed enough for developers to understand acceptance criteria
- Make out-of-scope items very specific to avoid confusion about what this work order covers
- Reference the original task from tasks.md and link to related requirements
- Organize requirements by importance and dependency order if multiple requirements are related
- Ensure the description provides clear context about why this work order is needed"""
    
    def _parse_description_tab_response(self, ai_response: str) -> Optional[Dict[str, Any]]:
        """Parse AI response to extract purpose, requirements, and out_of_scope sections"""
        try:
            # Try to extract JSON from the response
            json_start = ai_response.find('{')
            json_end = ai_response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_content = ai_response[json_start:json_end]
                description_data = json.loads(json_content)
                
                # Validate required fields
                required_fields = ['purpose', 'requirements', 'out_of_scope']
                for field in required_fields:
                    if field not in description_data:
                        logger.warning(f"Missing required field in description tab: {field}")
                        if field in ['requirements', 'out_of_scope']:
                            description_data[field] = []
                        else:
                            description_data[field] = ""
                
                # Ensure requirements and out_of_scope are lists
                if not isinstance(description_data.get('requirements'), list):
                    description_data['requirements'] = []
                if not isinstance(description_data.get('out_of_scope'), list):
                    description_data['out_of_scope'] = []
                
                return description_data
            else:
                logger.error("No valid JSON found in description tab response")
                return None
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse description tab response as JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing description tab response: {e}")
            return None
    
    def _generate_blueprint_tab(self, task_data: Dict[str, Any], 
                              artifacts: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate blueprint tab content by extracting relevant sections from requirements.md and design.md artifacts"""
        try:
            # Extract relevant sections from requirements.md and design.md
            requirements_sections = self._extract_relevant_requirements_sections(task_data, artifacts)
            design_sections = self._extract_relevant_design_sections(task_data, artifacts)
            task_context = self._extract_task_context_and_subtasks(task_data, artifacts)
            
            # Organize blueprint content
            blueprint_data = {
                "requirements_sections": requirements_sections,
                "design_sections": design_sections,
                "task_context": task_context,
                "original_task": {
                    "task_number": task_data.get('task_number', ''),
                    "title": task_data.get('title', ''),
                    "details": task_data.get('details', []),
                    "requirements_refs": task_data.get('requirements_refs', [])
                }
            }
            
            return blueprint_data
            
        except Exception as e:
            logger.error(f"Error generating blueprint tab: {e}")
            return None
    
    def _extract_relevant_requirements_sections(self, task_data: Dict[str, Any], 
                                              artifacts: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract relevant portions of requirements.md that relate to the specific work order"""
        requirements_sections = []
        
        if 'requirements' not in artifacts:
            return requirements_sections
        
        requirements_content = artifacts['requirements'].content
        task_title = task_data.get('title', '').lower()
        task_refs = task_data.get('requirements_refs', [])
        
        # Split requirements into sections
        sections = self._parse_requirements_sections(requirements_content)
        
        # Find relevant sections based on task title keywords and requirement references
        for section in sections:
            section_title = section.get('title', '').lower()
            section_content = section.get('content', '').lower()
            
            # Check if section is relevant based on keywords or references
            is_relevant = False
            
            # Check for keyword matches
            task_keywords = self._extract_keywords_from_title(task_title)
            for keyword in task_keywords:
                if keyword in section_title or keyword in section_content:
                    is_relevant = True
                    break
            
            # Check for requirement reference matches
            for ref in task_refs:
                if ref.lower() in section_content or ref.lower() in section_title:
                    is_relevant = True
                    break
            
            if is_relevant:
                requirements_sections.append({
                    "title": section.get('title', ''),
                    "content": section.get('content', ''),
                    "relevance_reason": f"Related to task: {task_data.get('title', '')}"
                })
        
        # If no specific sections found, include a general overview
        if not requirements_sections and sections:
            requirements_sections.append({
                "title": "General Requirements Context",
                "content": sections[0].get('content', '')[:1000] + "..." if len(sections[0].get('content', '')) > 1000 else sections[0].get('content', ''),
                "relevance_reason": "General project requirements context"
            })
        
        return requirements_sections
    
    def _extract_relevant_design_sections(self, task_data: Dict[str, Any], 
                                        artifacts: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract relevant sections from design.md that inform the implementation approach"""
        design_sections = []
        
        if 'design' not in artifacts:
            return design_sections
        
        design_content = artifacts['design'].content
        task_title = task_data.get('title', '').lower()
        
        # Split design into sections
        sections = self._parse_design_sections(design_content)
        
        # Find relevant sections based on task title keywords
        for section in sections:
            section_title = section.get('title', '').lower()
            section_content = section.get('content', '').lower()
            
            # Check if section is relevant based on keywords
            task_keywords = self._extract_keywords_from_title(task_title)
            is_relevant = False
            
            for keyword in task_keywords:
                if keyword in section_title or keyword in section_content:
                    is_relevant = True
                    break
            
            # Also include architecture and implementation sections
            if any(arch_keyword in section_title for arch_keyword in ['architecture', 'implementation', 'component', 'data model', 'api']):
                is_relevant = True
            
            if is_relevant:
                design_sections.append({
                    "title": section.get('title', ''),
                    "content": section.get('content', ''),
                    "relevance_reason": f"Design guidance for: {task_data.get('title', '')}"
                })
        
        # If no specific sections found, include architecture overview
        if not design_sections and sections:
            for section in sections:
                if 'architecture' in section.get('title', '').lower() or 'overview' in section.get('title', '').lower():
                    design_sections.append({
                        "title": section.get('title', ''),
                        "content": section.get('content', '')[:1000] + "..." if len(section.get('content', '')) > 1000 else section.get('content', ''),
                        "relevance_reason": "General design context"
                    })
                    break
        
        return design_sections
    
    def _extract_task_context_and_subtasks(self, task_data: Dict[str, Any], 
                                         artifacts: Dict[str, Any]) -> Dict[str, Any]:
        """Include original task context and sub-tasks in blueprint content"""
        task_context = {
            "original_task": {
                "task_number": task_data.get('task_number', ''),
                "title": task_data.get('title', ''),
                "description": task_data.get('description', ''),
                "details": task_data.get('details', [])
            },
            "sub_tasks": [],
            "acceptance_criteria": []
        }
        
        # Extract sub-tasks if this is a parent task
        if 'tasks' in artifacts:
            tasks_content = artifacts['tasks'].content
            sub_tasks = self._find_subtasks_for_task(task_data.get('task_number', ''), tasks_content)
            task_context["sub_tasks"] = sub_tasks
        
        # Extract acceptance criteria from task details
        for detail in task_data.get('details', []):
            if not detail.startswith('_Requirements:'):
                task_context["acceptance_criteria"].append(detail)
        
        return task_context
    
    def _parse_requirements_sections(self, requirements_content: str) -> List[Dict[str, Any]]:
        """Parse requirements.md into sections"""
        sections = []
        lines = requirements_content.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            # Look for section headers (## or ###)
            if line.startswith('## ') or line.startswith('### '):
                # Save previous section
                if current_section:
                    sections.append(current_section)
                
                # Start new section
                current_section = {
                    'title': line.lstrip('#').strip(),
                    'content': ''
                }
            elif current_section:
                # Add content to current section
                current_section['content'] += line + '\n'
        
        # Add the last section
        if current_section:
            sections.append(current_section)
        
        return sections
    
    def _parse_design_sections(self, design_content: str) -> List[Dict[str, Any]]:
        """Parse design.md into sections"""
        sections = []
        lines = design_content.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            # Look for section headers (## or ###)
            if line.startswith('## ') or line.startswith('### '):
                # Save previous section
                if current_section:
                    sections.append(current_section)
                
                # Start new section
                current_section = {
                    'title': line.lstrip('#').strip(),
                    'content': ''
                }
            elif current_section:
                # Add content to current section
                current_section['content'] += line + '\n'
        
        # Add the last section
        if current_section:
            sections.append(current_section)
        
        return sections
    
    def _extract_keywords_from_title(self, title: str) -> List[str]:
        """Extract relevant keywords from task title for matching"""
        # Remove common words and extract meaningful keywords
        common_words = {'implement', 'create', 'add', 'update', 'fix', 'the', 'a', 'an', 'and', 'or', 'for', 'with', 'to', 'in', 'on'}
        words = title.lower().split()
        keywords = [word for word in words if word not in common_words and len(word) > 2]
        return keywords
    
    def _find_subtasks_for_task(self, task_number: str, tasks_content: str) -> List[Dict[str, Any]]:
        """Find sub-tasks for a given task number in tasks.md"""
        sub_tasks = []
        lines = tasks_content.split('\n')
        
        # Look for sub-tasks that start with the task number (e.g., 1.1, 1.2 for task 1)
        for line in lines:
            line = line.strip()
            if line.startswith('- [') and ('] ' in line):
                # Extract task content
                task_content = line.split('] ', 1)[1] if '] ' in line else line
                
                # Check if this is a sub-task of the given task number
                if task_content and task_content[0].isdigit():
                    parts = task_content.split(' ', 1)
                    if len(parts) > 1 and ('.' in parts[0]):
                        sub_task_number = parts[0].rstrip('.')
                        sub_task_title = parts[1]
                        
                        # Check if this is a sub-task (e.g., 1.1 is sub-task of 1)
                        if sub_task_number.startswith(task_number + '.'):
                            sub_tasks.append({
                                'task_number': sub_task_number,
                                'title': sub_task_title
                            })
        
        return sub_tasks
    
    def _generate_prd_tab(self, task_data: Dict[str, Any], project: Any) -> Optional[Dict[str, Any]]:
        """Generate PRD tab content by finding relevant PRD sections from Think phase refinement process"""
        try:
            # Get related PRD content
            prd_content = self._get_related_prd_content(project.id, task_data)
            
            if not prd_content:
                # Provide fallback content when no PRD exists
                prd_content = {
                    "related_sections": [],
                    "user_stories": [],
                    "business_context": f"No PRD found for this feature. Consider creating one through the Think phase process to provide business context for: {task_data.get('title', '')}",
                    "message": "No PRD exists for the related feature. This work order is based on technical specifications only."
                }
            
            return prd_content
            
        except Exception as e:
            logger.error(f"Error generating PRD tab: {e}")
            return None
    
    def _get_related_prd_content(self, project_id: str, task_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find relevant PRD sections that relate to this work order from Think phase refinement process"""
        try:
            # Import PRD model to query PRDs
            try:
                from ..models.prd import PRD
            except ImportError:
                from models.prd import PRD
            
            # Get PRDs for this project
            # Handle project_id type mismatch - PRD expects UUID but we have string
            try:
                # Try to convert string to UUID if it's a valid UUID format
                import uuid
                if isinstance(project_id, str) and len(project_id) == 36:
                    project_uuid = uuid.UUID(project_id)
                    prds = db.session.query(PRD).filter_by(project_id=project_uuid).all()
                else:
                    # Project ID is not a UUID format, skip PRD lookup
                    logger.info(f"Project ID {project_id} is not UUID format, skipping PRD lookup")
                    prds = []
            except (ValueError, TypeError):
                # Invalid UUID format, skip PRD lookup
                logger.info(f"Project ID {project_id} is not valid UUID, skipping PRD lookup")
                prds = []
            
            if not prds:
                logger.info(f"No PRDs found for project {project_id}")
                return None
            
            # Find relevant PRD sections based on task content
            task_title = task_data.get('title', '').lower()
            task_keywords = self._extract_keywords_from_title(task_title)
            
            related_sections = []
            user_stories = []
            business_context_parts = []
            
            for prd in prds:
                # Check if PRD is relevant to this task
                prd_title = prd.title.lower() if prd.title else ''
                prd_content = prd.content.lower() if prd.content else ''
                
                # Check for keyword matches
                is_relevant = False
                for keyword in task_keywords:
                    if keyword in prd_title or keyword in prd_content:
                        is_relevant = True
                        break
                
                if is_relevant:
                    # Extract relevant sections from PRD content
                    prd_sections = self._extract_prd_sections(prd.content or '', task_keywords)
                    related_sections.extend(prd_sections)
                    
                    # Extract user stories
                    stories = self._extract_user_stories_from_prd(prd.content or '', task_keywords)
                    user_stories.extend(stories)
                    
                    # Add business context
                    business_context_parts.append(f"PRD: {prd.title} - {prd.summary or 'Business requirements and user needs'}")
            
            if related_sections or user_stories or business_context_parts:
                return {
                    "related_sections": related_sections,
                    "user_stories": user_stories,
                    "business_context": " | ".join(business_context_parts) if business_context_parts else f"Business context for {task_data.get('title', '')}",
                    "prd_count": len([prd for prd in prds if any(keyword in (prd.content or '').lower() for keyword in task_keywords)])
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting related PRD content: {e}")
            # Return fallback content instead of None
            return {
                "related_sections": [],
                "user_stories": [],
                "business_context": f"Unable to retrieve PRD content. Technical implementation for: {task_data.get('title', '')}",
                "message": "PRD content could not be retrieved. Proceeding with technical specifications only."
            }
    
    def _extract_prd_sections(self, prd_content: str, keywords: List[str]) -> List[Dict[str, Any]]:
        """Extract relevant sections from PRD content based on keywords"""
        sections = []
        
        # Split PRD into sections (similar to requirements parsing)
        lines = prd_content.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            # Look for section headers
            if line.startswith('## ') or line.startswith('### ') or line.startswith('# '):
                # Save previous section if it's relevant
                if current_section and self._is_section_relevant(current_section, keywords):
                    sections.append({
                        "title": current_section['title'],
                        "content": current_section['content'][:500] + "..." if len(current_section['content']) > 500 else current_section['content'],
                        "relevance": "Contains keywords related to the task"
                    })
                
                # Start new section
                current_section = {
                    'title': line.lstrip('#').strip(),
                    'content': ''
                }
            elif current_section:
                # Add content to current section
                current_section['content'] += line + '\n'
        
        # Check the last section
        if current_section and self._is_section_relevant(current_section, keywords):
            sections.append({
                "title": current_section['title'],
                "content": current_section['content'][:500] + "..." if len(current_section['content']) > 500 else current_section['content'],
                "relevance": "Contains keywords related to the task"
            })
        
        return sections
    
    def _extract_user_stories_from_prd(self, prd_content: str, keywords: List[str]) -> List[Dict[str, Any]]:
        """Extract user stories from PRD content that relate to the task"""
        user_stories = []
        lines = prd_content.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Look for user story patterns
            if 'as a' in line.lower() and ('i want' in line.lower() or 'i need' in line.lower()):
                # Check if user story is relevant to task keywords
                line_lower = line.lower()
                is_relevant = any(keyword in line_lower for keyword in keywords)
                
                if is_relevant:
                    user_stories.append({
                        "story": line,
                        "relevance": "Related to task functionality"
                    })
        
        return user_stories
    
    def _is_section_relevant(self, section: Dict[str, Any], keywords: List[str]) -> bool:
        """Check if a PRD section is relevant based on keywords"""
        title_lower = section.get('title', '').lower()
        content_lower = section.get('content', '').lower()
        
        # Check for keyword matches
        for keyword in keywords:
            if keyword in title_lower or keyword in content_lower:
                return True
        
        # Also include sections that commonly contain relevant business context
        relevant_section_types = ['user stories', 'requirements', 'acceptance criteria', 'business goals', 'objectives', 'features']
        for section_type in relevant_section_types:
            if section_type in title_lower:
                return True
        
        return False
    
    def enhance_work_order_with_ai(self, work_order_id: str, spec_id: str, project_id: str) -> Dict[str, Any]:
        """
        Generate content for ALL four tabs (Description, Implementation, Blueprint, PRD)
        This extends the existing generate_implementation_plan() method to populate all tabs
        """
        try:
            logger.info(f"Enhancing work order with AI for all tabs: {work_order_id}")
            
            # Get the work order from database
            task = Task.query.get(work_order_id)
            if not task:
                return {"success": False, "error": "Work order not found"}
            
            # Get project information
            project = MissionControlProject.query.get(project_id)
            if not project:
                return {"success": False, "error": "Project not found"}
            
            # Get frozen specification artifacts
            artifacts = self._get_frozen_spec_artifacts(spec_id, project_id)
            if not artifacts:
                return {"success": False, "error": "No frozen specification artifacts found"}
            
            # Prepare task data from database record
            task_data = {
                'task_number': task.task_number,
                'title': task.title,
                'description': task.description,
                'details': task.requirements_refs or []
            }
            
            # Generate all tab content using existing AI infrastructure
            all_content = self._generate_all_tabs_content(task_data, artifacts, project)
            
            if all_content:
                # Update task with all content (extend existing update logic)
                task.description_content = all_content.get('description')
                task.blueprint_content = all_content.get('blueprint')
                task.prd_content = all_content.get('prd')
                
                # Implementation content uses existing fields (from existing implementation plan generation)
                if all_content.get('implementation'):
                    impl_content = all_content['implementation']
                    task.implementation_approach = impl_content.get('approach')
                    task.implementation_goals = impl_content.get('goals')
                    task.implementation_strategy = impl_content.get('strategy')
                    task.technical_dependencies = impl_content.get('dependencies')
                    task.files_to_create = impl_content.get('files_to_create')
                    task.files_to_modify = impl_content.get('files_to_modify')
                
                # Use existing status update logic
                task.enhancement_status = 'enhanced'
                task.enhanced_at = datetime.utcnow()
                task.enhanced_by = 'ai_generator'
                task.approved_at = datetime.utcnow()
                task.approved_by = 'ai_generator'
                task.status = TaskStatus.READY  # Change status to Ready when all tabs populated
                
                db.session.commit()
                
                # Broadcast via WebSocket (extend existing WebSocket integration)
                if self.websocket_server:
                    self.websocket_server.broadcast_work_order_fully_enhanced(work_order_id, all_content)
                    self.websocket_server.broadcast_work_order_ready(work_order_id)
                
                logger.info(f"Successfully enhanced work order with all tabs: {work_order_id}")
                
                return {
                    "success": True,
                    "all_tabs_populated": True,
                    "description_content": all_content.get('description'),
                    "implementation_content": all_content.get('implementation'),
                    "blueprint_content": all_content.get('blueprint'),
                    "prd_content": all_content.get('prd'),
                    "status": "READY"
                }
            else:
                return {"success": False, "error": "Failed to generate content for all tabs"}
                
        except Exception as e:
            logger.error(f"Error enhancing work order with AI for all tabs {work_order_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_all_tabs_content(self, task_data: Dict[str, Any], 
                                 artifacts: Dict[str, Any], 
                                 project: Any) -> Optional[Dict[str, Any]]:
        """
        Generate content for all four tabs using existing AI infrastructure
        Extends existing _generate_ai_implementation_plan() pattern
        """
        try:
            # Use existing AI generation pattern
            repo_path = self._get_project_repository_path(project)  # Existing method
            claude_service = ClaudeCodeService(repo_path)           # Existing service
            
            # Extend existing context preparation to include PRD and blueprint context
            enhanced_context = self._prepare_enhanced_work_order_context(task_data, artifacts, project)
            
            # Generate each tab using existing prompt pattern
            description_content = self._generate_description_tab(task_data, artifacts, claude_service)
            implementation_content = self._generate_ai_implementation_plan(task_data, artifacts, project, '', '')  # Existing method
            blueprint_content = self._generate_blueprint_tab(task_data, artifacts)
            prd_content = self._generate_prd_tab(task_data, project)
            
            # Ensure all content was generated successfully
            if not description_content:
                logger.warning("Description tab generation failed, using fallback")
                description_content = self._create_fallback_description_content(task_data)
            
            if not blueprint_content:
                logger.warning("Blueprint tab generation failed, using fallback")
                blueprint_content = self._create_fallback_blueprint_content(task_data, artifacts)
            
            if not prd_content:
                logger.warning("PRD tab generation failed, using fallback")
                prd_content = self._create_fallback_prd_content(task_data)
            
            return {
                "description": description_content,
                "implementation": implementation_content,
                "blueprint": blueprint_content,
                "prd": prd_content
            }
            
        except Exception as e:
            logger.error(f"Error generating all tabs content: {e}")
            return None
    
    def _prepare_enhanced_work_order_context(self, task_data: Dict[str, Any], 
                                           artifacts: Dict[str, Any],
                                           project: Any) -> Dict[str, Any]:
        """
        Extend existing context preparation to include PRD and blueprint context
        Builds on existing _prepare_work_order_context() method
        """
        try:
            # Use existing context as base
            base_context = self._prepare_work_order_context(task_data, artifacts, project)
            
            # Add PRD context (NEW)
            prd_context = self._get_related_prd_content(project.id, task_data)
            
            # Add blueprint context (NEW) 
            blueprint_context = self._extract_relevant_spec_sections(artifacts, task_data)
            
            return {
                "base_context": base_context,
                "prd_context": prd_context,
                "blueprint_context": blueprint_context
            }
            
        except Exception as e:
            logger.error(f"Error preparing enhanced work order context: {e}")
            # Return base context as fallback
            return {
                "base_context": self._prepare_work_order_context(task_data, artifacts, project),
                "prd_context": None,
                "blueprint_context": None
            }
    
    def _extract_relevant_spec_sections(self, artifacts: Dict[str, Any], task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant sections from requirements.md and design.md for blueprint context"""
        try:
            requirements_sections = self._extract_relevant_requirements_sections(task_data, artifacts)
            design_sections = self._extract_relevant_design_sections(task_data, artifacts)
            
            return {
                "requirements_sections": requirements_sections,
                "design_sections": design_sections,
                "task_references": task_data.get('requirements_refs', [])
            }
            
        except Exception as e:
            logger.error(f"Error extracting relevant spec sections: {e}")
            return {
                "requirements_sections": [],
                "design_sections": [],
                "task_references": []
            }
    
    def _create_fallback_description_content(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create fallback description content when AI generation fails"""
        return {
            "purpose": f"Implement {task_data.get('title', 'task')} as specified in the project requirements",
            "requirements": [
                f"Complete the implementation of {task_data.get('title', 'task')}",
                "Follow existing code patterns and architectural decisions",
                "Ensure proper error handling and validation",
                "Include appropriate tests and documentation"
            ],
            "out_of_scope": [
                "Changes to existing unrelated functionality",
                "Infrastructure or deployment modifications",
                "Performance optimization beyond basic requirements",
                "Integration with external services not specified"
            ]
        }
    
    def _create_fallback_blueprint_content(self, task_data: Dict[str, Any], artifacts: Dict[str, Any]) -> Dict[str, Any]:
        """Create fallback blueprint content when extraction fails"""
        return {
            "requirements_sections": [{
                "title": "General Requirements",
                "content": "Refer to project requirements.md for detailed specifications",
                "relevance_reason": "General project context"
            }],
            "design_sections": [{
                "title": "General Design",
                "content": "Refer to project design.md for architectural guidance",
                "relevance_reason": "General design context"
            }],
            "task_context": {
                "original_task": {
                    "task_number": task_data.get('task_number', ''),
                    "title": task_data.get('title', ''),
                    "description": task_data.get('description', ''),
                    "details": task_data.get('details', [])
                },
                "sub_tasks": [],
                "acceptance_criteria": task_data.get('details', [])
            }
        }
    
    def _create_fallback_prd_content(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create fallback PRD content when no PRD is available"""
        return {
            "related_sections": [],
            "user_stories": [],
            "business_context": f"Technical implementation task: {task_data.get('title', '')}. No specific PRD available - refer to project specifications for business context.",
            "message": "No PRD content available. This work order is based on technical specifications."
        }

    def _determine_category(self, title: str) -> str:
        """Determine work order category based on title"""
        title_lower = title.lower()
        
        if 'api' in title_lower or 'endpoint' in title_lower:
            return 'API Implementation'
        elif 'ui' in title_lower or 'component' in title_lower or 'frontend' in title_lower:
            return 'UI Implementation'
        elif 'model' in title_lower or 'database' in title_lower or 'schema' in title_lower:
            return 'Data Model'
        elif 'test' in title_lower:
            return 'Testing'
        elif 'infrastructure' in title_lower or 'deploy' in title_lower:
            return 'Infrastructure'
        else:
            return 'Implementation'


# Global service instance
_work_order_service = None

def get_work_order_generation_service() -> WorkOrderGenerationService:
    """Get the global work order generation service instance"""
    global _work_order_service
    if _work_order_service is None:
        _work_order_service = WorkOrderGenerationService()
    return _work_order_service