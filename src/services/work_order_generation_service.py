"""
Work Order Generation Service - AI-powered work order creation with streaming
Generates comprehensive work orders with implementation plans from frozen specifications
"""

import logging
import json
import uuid
import asyncio
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
        
    def generate_work_orders_stream(self, spec_id: str, project_id: str) -> Generator[Dict[str, Any], None, None]:
        """
        Generate basic work orders (Backlog status) and stream them in real-time
        Implementation plans are generated separately when user clicks "Generate with AI"
        
        Args:
            spec_id: Specification ID (e.g., "spec_123")
            project_id: Project ID
            
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

                logger.info(f"Starting basic work order generation for spec {spec_id}, project {project_id}")

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
                    logger.info(f"Found project: {project.name}")
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
                    
                    # Generate basic work order (no AI enhancement)
                    work_order = self._generate_basic_work_order(
                        task_data, artifacts, project, spec_id, project_id
                    )
                    
                    if work_order:
                        # Save to database
                        self._save_work_order_to_database(work_order, spec_id, project_id)
                        
                        # Broadcast via WebSocket
                        if self.websocket_server:
                            self.websocket_server.socketio.emit('work_order_created', {
                                'spec_id': spec_id,
                                'project_id': project_id,
                                'work_order': work_order.__dict__
                            })
                        
                        # Yield the completed work order
                        yield {
                            "type": "work_order_created",
                            "work_order": work_order.__dict__,
                            "progress": f"{i+1}/{len(parsed_tasks)}",
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        
                        logger.info(f"Successfully created basic work order: {work_order.title}")
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
    
    def _generate_basic_work_order(self, task_data: Dict[str, Any], 
                                 artifacts: Dict[str, Any],
                                 project: Any,
                                 spec_id: str, project_id: str) -> Optional[WorkOrderData]:
        """Generate a comprehensive work order with detailed context (Backlog status, no implementation plan)"""
        try:
            # Generate comprehensive work order content using AI
            comprehensive_data = self._generate_comprehensive_work_order_content(
                task_data, artifacts, project, spec_id, project_id
            )
            
            if not comprehensive_data:
                # Fallback to basic extraction if AI fails
                comprehensive_data = {
                    'purpose': self._extract_purpose_from_task(task_data, artifacts),
                    'requirements': self._extract_requirements_from_task(task_data, artifacts),
                    'out_of_scope': self._extract_out_of_scope_from_task(task_data, artifacts),
                    'context': self._extract_context_from_task(task_data, artifacts),
                    'blueprint_context': self._extract_blueprint_context(task_data, artifacts),
                    'prd_context': self._extract_prd_context(task_data, artifacts)
                }
            
            # Create comprehensive work order
            work_order = WorkOrderData(
                id=f"wo_{spec_id}_{task_data.get('task_number', uuid.uuid4().hex[:8])}",
                title=task_data.get('title', 'Unknown Task'),
                description=comprehensive_data.get('context', ''),
                status='backlog',  # Comprehensive work orders start as Backlog (use lowercase for enum)
                assignee='CS Chetan Singh',  # Default assignee from screenshots
                category=self._determine_category(task_data.get('title', '')),
                task_number=task_data.get('task_number', ''),
                purpose=comprehensive_data.get('purpose', ''),
                requirements=comprehensive_data.get('requirements', []),
                context=comprehensive_data.get('context', ''),
                implementation_plan=None,  # No implementation plan yet - this is Step 2
                prd_reference=comprehensive_data.get('prd_context', f"PRD for {spec_id}"),
                blueprint_reference=comprehensive_data.get('blueprint_context', f"Blueprint for {spec_id}"),
                design_reference=f"Requirements and Design for {spec_id}",
                created_at=datetime.utcnow().isoformat()
            )
            
            # Add additional comprehensive data
            work_order.out_of_scope = comprehensive_data.get('out_of_scope', [])
            work_order.blueprint_context = comprehensive_data.get('blueprint_context', '')
            work_order.prd_context = comprehensive_data.get('prd_context', '')
            
            return work_order
            
        except Exception as e:
            logger.error(f"Error generating comprehensive work order: {e}")
            return None
    
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
            # TEMPORARY: Skip AI generation for debugging
            logger.warning("AI generation temporarily disabled for debugging - using fallback extraction")
            return None  # This will trigger the fallback in _generate_basic_work_order
            
            # Original code commented out for debugging
            # # Prepare context for AI generation
            # context = self._prepare_work_order_context(task_data, artifacts, project)
            # 
            # # Create prompt for comprehensive work order content
            # prompt = self._create_comprehensive_work_order_prompt(task_data, context)
            # 
            # # Use Claude Code for generation
            # repo_path = self._get_project_repository_path(project)
            # claude_service = ClaudeCodeService(repo_path)
            # 
            # if claude_service.is_available():
            #     logger.info(f"Using Claude Code SDK for comprehensive work order: {task_data.get('title')}")
            #     result = claude_service.execute_task(prompt)
            #     
            #     if result.get('success'):
            #         # Parse the AI response
            #         content_data = self._parse_comprehensive_work_order_response(result.get('output', ''))
            #         return content_data
            #     else:
            #         logger.error(f"Claude Code failed: {result.get('error')}")
            # 
            # # Fallback to AI Broker
            # logger.info("Falling back to AI Broker for comprehensive work order")
            # ai_request = AIRequest(
            #     request_id=f"comp_wo_{uuid.uuid4().hex[:8]}",
            #     task_type=TaskType.DOCUMENTATION,
            #     instruction=prompt,
            #     priority=Priority.HIGH,
            #     max_tokens=12000,
            #     timeout_seconds=120.0,
            #     preferred_models=['claude-opus-4'],
            #     metadata={'agent': 'comprehensive_work_order_generator', 'task_number': task_data.get('task_number')}
            # )
            # 
            # response = self.ai_broker.submit_request_sync(ai_request, timeout=90.0)
            # 
            # if response.success:
            #     content_data = self._parse_comprehensive_work_order_response(response.content)
            #     return content_data
            # else:
            #     logger.error(f"AI Broker failed: {response.error_message}")
            #     return None
                
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
    
    def _save_work_order_to_database(self, work_order: WorkOrderData, spec_id: str, project_id: str):
        """Save a single work order to the database as a Task"""
        # Upsert logic: Check if task already exists
        task = db.session.query(Task).get(work_order.id)
        
        if task:
            # Update existing task
            task.title = work_order.title
            task.description = work_order.description
            task.task_number = work_order.task_number
            task.assigned_to = work_order.assignee
            task.goal_line = work_order.purpose
            task.requirements_refs = work_order.requirements
            task.blueprint_section_ref = work_order.blueprint_context
            task.codebase_context = {
                "prd_context": work_order.prd_context
            }
            task.updated_at = datetime.utcnow()
            logger.info(f"Updating existing work order: {task.title}")
        else:
            # Create new task
            # Map string status to enum if needed
            if isinstance(work_order.status, str):
                # Convert string status to enum
                status_map = {
                    'backlog': TaskStatus.BACKLOG,
                    'ready': TaskStatus.READY,
                    'running': TaskStatus.RUNNING,
                    'review': TaskStatus.REVIEW,
                    'done': TaskStatus.DONE,
                    'failed': TaskStatus.FAILED,
                    'needs_rework': TaskStatus.NEEDS_REWORK
                }
                task_status = status_map.get(work_order.status.lower(), TaskStatus.BACKLOG)
            else:
                task_status = work_order.status
            
            # Create task record with work order data
            task = Task(
                id=work_order.id,
                spec_id=spec_id,
                project_id=project_id,
                title=work_order.title,
                description=work_order.description,
                task_number=work_order.task_number,
                status=task_status,  # Use enum instance directly
                priority=TaskPriority.MEDIUM,  # Pass enum instance directly
                assigned_to=work_order.assignee,
                created_by='work_order_generator',
                
                # Work order specific fields
                goal_line=work_order.purpose,
                requirements_refs=work_order.requirements,
                
                # Comprehensive work order fields
                blueprint_section_ref=work_order.blueprint_context,
                codebase_context={
                    "prd_context": work_order.prd_context
                }
            )
            db.session.add(task)
            logger.info(f"Creating new work order: {task.title}")

        try:
            db.session.commit()
        except Exception as e:
            logger.error(f"Error saving work order to database: {e}")
            db.session.rollback()
    
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