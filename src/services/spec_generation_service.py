"""
Spec Generation Service - Asynchronous specification generation management
Handles background job orchestration for DefineAgent spec generation
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from flask import current_app
from flask_socketio import emit

try:
    from .background import get_job_manager, JobResult, JobContext
    from ..models import BackgroundJob, FeedItem, db
    from ..agents.define_agent import DefineAgent
    from ..events.domain_events import IdeaPromotedEvent
    from ..events.event_router import EventBus
    from ..services.ai_broker import AIBroker
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from services.background import get_job_manager, JobResult, JobContext
    from models import BackgroundJob, FeedItem, db
    from agents.define_agent import DefineAgent
    from events.domain_events import IdeaPromotedEvent
    from events.event_router import EventBus
    from services.ai_broker import AIBroker

logger = logging.getLogger(__name__)


class SpecGenerationService:
    """Service for managing asynchronous specification generation"""
    
    def __init__(self):
        self.job_manager = None
        self.event_bus = EventBus()
        self.ai_broker = None
    
    def _extract_item_id_from_spec_id(self, spec_id: str) -> str:
        """Extract the original feed item ID from spec_id"""
        # spec_id format is "spec_{item_id}", so we remove the "spec_" prefix
        return spec_id.replace("spec_", "") if spec_id.startswith("spec_") else spec_id
    
    def init_app(self, app):
        """Initialize with Flask app"""
        self.job_manager = get_job_manager()
        
        # Initialize AI broker with app context
        with app.app_context():
            self.ai_broker = AIBroker()
            self.ai_broker.start()
        
        # Register job handlers
        self.job_manager.register_job_handler('spec_generation', self._handle_spec_generation_job)
        self.job_manager.register_job_handler('design_generation', self._handle_design_generation_job)
        self.job_manager.register_job_handler('tasks_generation', self._handle_tasks_generation_job)
        logger.info("SpecGenerationService initialized with all job handlers")
    
    def start_spec_generation(self, item_id: str, project_id: str, provider: str = 'claude') -> Dict[str, Any]:
        """
        Start asynchronous spec generation for an idea
        
        Args:
            item_id: Feed item ID to generate specs for
            project_id: Project ID
            provider: AI provider ('claude' or 'model-garden')
        
        Returns:
            Dict with job_id and status information
        """
        try:
            logger.info(f"🚀 ASYNC SPEC GENERATION STARTED")
            logger.info(f"   📋 Item ID: {item_id}")
            logger.info(f"   🏗️  Project ID: {project_id}")
            logger.info(f"   🤖 AI Provider: {provider.upper()}")
            
            # Validate that the feed item exists
            feed_item = FeedItem.query.get(item_id)
            if not feed_item:
                logger.error(f"❌ Feed item {item_id} not found")
                raise ValueError(f"Feed item {item_id} not found")
            
            logger.info(f"   💡 Idea Title: '{feed_item.title}'")
            logger.info(f"   📝 Idea Summary: '{feed_item.summary[:100]}...' ({len(feed_item.summary or '')} chars)")
            
            # Check if there's already a running job for this item
            # Note: Using a simpler approach since metadata.contains() may not be available
            running_jobs = BackgroundJob.query.filter_by(
                job_type='spec_generation',
                status=BackgroundJob.STATUS_RUNNING
            ).all()
            
            existing_job = None
            for job in running_jobs:
                if job.job_metadata and job.job_metadata.get('item_id') == item_id:
                    existing_job = job
                    break
            
            if existing_job:
                logger.warning(f"⚠️  Job already running for item {item_id} (Job ID: {existing_job.id})")
                return {
                    'job_id': existing_job.id,
                    'status': 'already_running',
                    'message': 'Spec generation already in progress for this idea'
                }
            
            logger.info(f"✅ No existing job found - proceeding with new generation")
            
            # Submit background job
            logger.info(f"🔧 Submitting background job to ThreadPoolExecutor...")
            job_id = self.job_manager.submit_job(
                job_type='spec_generation',
                project_id=int(project_id) if project_id.isdigit() else None,
                item_id=item_id,
                provider=provider
            )
            
            logger.info(f"✅ Background job submitted successfully - Job ID: {job_id}")
            
            # Update job metadata
            job = BackgroundJob.query.get(job_id)
            if job:
                job.job_metadata = {
                    'item_id': item_id,
                    'project_id': project_id,
                    'provider': provider,
                    'idea_title': feed_item.title,
                    'started_by': 'user'  # TODO: get actual user
                }
                db.session.commit()
            
            logger.info(f"🎉 ASYNC SPEC GENERATION SETUP COMPLETE")
            logger.info(f"   🆔 Job ID: {job_id}")
            logger.info(f"   ⏱️  Estimated Duration: 45 seconds")
            logger.info(f"   🤖 Provider: {provider}")
            logger.info(f"   📊 Job will generate: requirements.md only (sequential workflow)")
            
            return {
                'job_id': job_id,
                'status': 'started',
                'estimated_duration': 45,  # seconds
                'provider': provider
            }
            
        except Exception as e:
            logger.error(f"Failed to start spec generation for {item_id}: {e}")
            raise
    
    def get_generation_status(self, job_id: int) -> Optional[Dict[str, Any]]:
        """Get current status of a spec generation job"""
        try:
            job = BackgroundJob.query.get(job_id)
            if not job or job.job_type != 'spec_generation':
                return None
            
            status_data = {
                'job_id': job_id,
                'status': job.status,
                'progress': job.progress or 0,
                'created_at': job.created_at.isoformat() if job.created_at else None,
                'started_at': job.started_at.isoformat() if job.started_at else None,
                'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                'error_message': job.error_message,
                'metadata': job.job_metadata or {}
            }
            
            # Add estimated completion time for running jobs
            if job.status == BackgroundJob.STATUS_RUNNING and job.started_at:
                elapsed = (datetime.utcnow() - job.started_at).total_seconds()
                estimated_total = 45  # seconds
                remaining = max(0, estimated_total - elapsed)
                status_data['estimated_completion'] = remaining
            
            return status_data
            
        except Exception as e:
            logger.error(f"Failed to get status for job {job_id}: {e}")
            return None
    
    def cancel_generation(self, job_id: int) -> bool:
        """Cancel a running spec generation job"""
        try:
            success = self.job_manager.cancel_job(job_id)
            if success:
                # Emit cancellation event
                job = BackgroundJob.query.get(job_id)
                if job and job.job_metadata:
                    self._emit_progress_event(
                        job_id=job_id,
                        item_id=job.job_metadata.get('item_id'),
                        event_type='cancelled',
                        data={'message': 'Spec generation cancelled by user'}
                    )
                logger.info(f"Cancelled spec generation job {job_id}")
            return success
            
        except Exception as e:
            logger.error(f"Failed to cancel job {job_id}: {e}")
            return False
    
    def _handle_spec_generation_job(self, context: JobContext, project_id: int, **kwargs) -> JobResult:
        """Background job handler for spec generation"""
        item_id = kwargs.get('item_id')
        provider = kwargs.get('provider', 'claude')
        
        try:
            logger.info(f"🔥 BACKGROUND JOB STARTED")
            logger.info(f"   🆔 Job ID: {context.job_id}")
            logger.info(f"   💡 Item ID: {item_id}")
            logger.info(f"   🏗️  Project ID: {project_id}")
            logger.info(f"   🤖 AI Provider: {provider.upper()}")
            logger.info(f"   🧵 Thread: Background ThreadPoolExecutor")
            
            # Update progress: Starting
            context.update_progress(5, "Initializing spec generation...")
            self._emit_progress_event(
                job_id=context.job_id,
                item_id=item_id,
                event_type='progress',
                data={
                    'progress': 5,
                    'stage': 'initializing',
                    'message': 'Initializing spec generation...'
                }
            )
            
            logger.info(f"📡 Emitted progress event: 5% - Initializing")
            
            # Get feed item
            feed_item = FeedItem.query.get(item_id)
            if not feed_item:
                logger.error(f"❌ Feed item {item_id} not found in database")
                return JobResult(success=False, error=f"Feed item {item_id} not found")
            
            logger.info(f"✅ Feed item retrieved: '{feed_item.title}'")
            
            # Update progress: Creating event
            context.update_progress(10, "Creating promotion event...")
            self._emit_progress_event(
                job_id=context.job_id,
                item_id=item_id,
                event_type='progress',
                data={
                    'progress': 10,
                    'stage': 'creating_event',
                    'message': 'Creating promotion event...'
                }
            )
            
            logger.info(f"📡 Emitted progress event: 10% - Creating promotion event")
            
            # Create IdeaPromotedEvent with provider information
            idea_promoted_event = IdeaPromotedEvent(
                idea_id=item_id,
                project_id=str(project_id),
                promoted_by='async_spec_generation',
                provider=provider  # Pass provider to the event
            )
            
            # Add idea content to event for DefineAgent
            idea_promoted_event.idea_content = f"Title: {feed_item.title}\n\nDescription: {feed_item.summary or 'No description provided'}"
            
            # Update progress: Initializing DefineAgent
            context.update_progress(20, "Initializing AI agent...")
            self._emit_progress_event(
                job_id=context.job_id,
                item_id=item_id,
                event_type='progress',
                data={
                    'progress': 20,
                    'stage': 'initializing_agent',
                    'message': 'Initializing AI agent...'
                }
            )
            
            # Initialize DefineAgent
            logger.info(f"🤖 Initializing DefineAgent with {provider.upper()} provider...")
            define_agent = DefineAgent(self.event_bus, self.ai_broker)
            logger.info(f"✅ DefineAgent initialized successfully")
            
            # Create progress callback for DefineAgent
            def progress_callback(progress: int, message: str, stage: str = None):
                # Map DefineAgent progress to our job progress (20-90%)
                mapped_progress = 20 + int((progress / 100) * 70)
                context.update_progress(mapped_progress, message)
                logger.info(f"🔄 DefineAgent progress: {progress}% → Job progress: {mapped_progress}% - {message}")
                self._emit_progress_event(
                    job_id=context.job_id,
                    item_id=item_id,
                    event_type='progress',
                    data={
                        'progress': mapped_progress,
                        'stage': stage or 'processing',
                        'message': message
                    }
                )
            
            # Add progress callback to DefineAgent if it supports it
            if hasattr(define_agent, 'set_progress_callback'):
                define_agent.set_progress_callback(progress_callback)
                logger.info(f"✅ Progress callback attached to DefineAgent")
            else:
                logger.warning(f"⚠️  DefineAgent doesn't support progress callbacks")
            
            # Process the event with DefineAgent
            context.update_progress(30, "Processing idea with AI agent...")
            self._emit_progress_event(
                job_id=context.job_id,
                item_id=item_id,
                event_type='progress',
                data={
                    'progress': 30,
                    'stage': 'processing',
                    'message': 'Processing idea with AI agent...'
                }
            )
            
            logger.info(f"🚀 Starting DefineAgent.process_event() - This will call {provider.upper()} AI service")
            logger.info(f"   📋 Event Type: IdeaPromotedEvent")
            logger.info(f"   💡 Idea Content: '{idea_promoted_event.idea_content[:100]}...'")
            
            result = define_agent.process_event(idea_promoted_event)
            
            logger.info(f"✅ DefineAgent.process_event() completed")
            logger.info(f"   🎯 Success: {result.success}")
            logger.info(f"   ⏱️  Processing Time: {result.processing_time_seconds:.2f}s")
            
            if result.success:
                # Update progress: Finalizing
                context.update_progress(95, "Finalizing specification...")
                self._emit_progress_event(
                    job_id=context.job_id,
                    item_id=item_id,
                    event_type='progress',
                    data={
                        'progress': 95,
                        'stage': 'finalizing',
                        'message': 'Finalizing specification...'
                    }
                )
                
                # Complete
                context.update_progress(100, "Specification generated successfully!")
                
                # Emit completion event
                self._emit_progress_event(
                    job_id=context.job_id,
                    item_id=item_id,
                    event_type='complete',
                    data={
                        'spec_id': result.result_data.get('spec_id') if result.result_data else f"spec_{item_id}",
                        'artifacts_created': result.result_data.get('specifications_generated', []) if result.result_data else [],
                        'processing_time': result.processing_time_seconds,
                        'provider': provider
                    }
                )
                
                logger.info(f"Spec generation job {context.job_id} completed successfully")
                
                return JobResult(
                    success=True,
                    data={
                        'spec_id': result.result_data.get('spec_id') if result.result_data else f"spec_{item_id}",
                        'processing_time': result.processing_time_seconds,
                        'artifacts_created': len(result.result_data.get('specifications_generated', [])) if result.result_data else 1
                    }
                )
            else:
                # Emit failure event
                self._emit_progress_event(
                    job_id=context.job_id,
                    item_id=item_id,
                    event_type='failed',
                    data={
                        'error': result.error_message,
                        'provider': provider,
                        'retry_available': True
                    }
                )
                
                logger.error(f"Spec generation job {context.job_id} failed: {result.error_message}")
                
                return JobResult(success=False, error=result.error_message)
                
        except Exception as e:
            error_message = f"Spec generation job failed: {str(e)}"
            logger.error(f"Job {context.job_id} failed with exception: {e}")
            
            # Emit failure event
            self._emit_progress_event(
                job_id=context.job_id,
                item_id=item_id,
                event_type='failed',
                data={
                    'error': error_message,
                    'provider': provider,
                    'retry_available': True
                }
            )
            
            return JobResult(success=False, error=error_message)
    
    def _handle_design_generation_job(self, context: JobContext, project_id: int, **kwargs) -> JobResult:
        """Background job handler for design generation"""
        spec_id = kwargs.get('spec_id')
        provider = kwargs.get('provider', 'claude')
        
        try:
            logger.info(f"🎨 DESIGN GENERATION JOB STARTED")
            logger.info(f"   🆔 Job ID: {context.job_id}")
            logger.info(f"   📋 Spec ID: {spec_id}")
            logger.info(f"   🤖 AI Provider: {provider.upper()}")
            logger.info(f"   🎯 Provider will be passed to DefineAgent")
            
            # Extract the original feed item ID from spec_id
            original_item_id = self._extract_item_id_from_spec_id(spec_id)
            
            # Update progress: Starting
            context.update_progress(10, "Starting design generation...")
            self._emit_progress_event(
                job_id=context.job_id,
                item_id=original_item_id,  # Use original feed item ID
                event_type='progress',
                data={
                    'progress': 10,
                    'stage': 'starting',
                    'message': 'Starting design generation...',
                    'generation_type': 'design'
                }
            )
            
            # Import required modules
            try:
                from ..models.specification_artifact import SpecificationArtifact, ArtifactType
                from ..agents.define_agent import DefineAgent
                from ..services.ai_broker import AIBroker
                from ..events.event_router import EventBus
                from ..api.stages import _generate_design_document_core
            except ImportError:
                from models.specification_artifact import SpecificationArtifact, ArtifactType
                from agents.define_agent import DefineAgent
                from services.ai_broker import AIBroker
                from events.event_router import EventBus
                from api.stages import _generate_design_document_core
            
            # Get requirements artifact
            context.update_progress(20, "Loading requirements document...")
            self._emit_progress_event(
                job_id=context.job_id,
                item_id=original_item_id,
                event_type='progress',
                data={
                    'progress': 20,
                    'stage': 'loading',
                    'message': 'Loading requirements document...',
                    'generation_type': 'design'
                }
            )
            
            requirements_artifact = SpecificationArtifact.query.filter_by(
                spec_id=spec_id,
                artifact_type=ArtifactType.REQUIREMENTS
            ).first()
            
            if not requirements_artifact:
                raise Exception("Requirements document not found. Generate requirements first.")
            
            # Initialize DefineAgent
            context.update_progress(30, "Initializing AI agent...")
            self._emit_progress_event(
                job_id=context.job_id,
                item_id=original_item_id,
                event_type='progress',
                data={
                    'progress': 30,
                    'stage': 'initializing',
                    'message': 'Initializing AI agent...',
                    'generation_type': 'design'
                }
            )
            
            event_bus = EventBus()
            ai_broker = AIBroker()
            ai_broker.start()
            define_agent = DefineAgent(event_bus, ai_broker)
            
            # Generate design document
            context.update_progress(50, "Generating design document...")
            self._emit_progress_event(
                job_id=context.job_id,
                item_id=original_item_id,
                event_type='progress',
                data={
                    'progress': 50,
                    'stage': 'generating',
                    'message': 'Generating design document...',
                    'generation_type': 'design'
                }
            )
            
            design_content = _generate_design_document_core(
                spec_id=spec_id,
                project_id=str(project_id),
                requirements_artifact=requirements_artifact,
                define_agent=define_agent,
                provider=provider
            )
            
            context.update_progress(90, "Saving design document...")
            self._emit_progress_event(
                job_id=context.job_id,
                item_id=original_item_id,
                event_type='progress',
                data={
                    'progress': 90,
                    'stage': 'saving',
                    'message': 'Saving design document...',
                    'generation_type': 'design'
                }
            )
            
            # Save the generated design document to the database
            logger.info(f"💾 Saving design document to database...")
            define_agent._store_specifications(spec_id, str(project_id), {'design': design_content})
            logger.info(f"✅ Design document saved to database")
            
            # Complete
            context.update_progress(100, "Design document generated successfully!")
            
            # Extract the original feed item ID from spec_id
            original_item_id = self._extract_item_id_from_spec_id(spec_id)
            logger.info(f"🎉 Emitting completion event with item_id: {original_item_id}, spec_id: {spec_id}")
            
            # Emit completion event
            self._emit_progress_event(
                job_id=context.job_id,
                item_id=original_item_id,  # Use original feed item ID
                event_type='complete',
                data={
                    'spec_id': spec_id,
                    'generation_type': 'design',
                    'provider': provider,
                    'artifact_data': design_content.to_dict() if hasattr(design_content, 'to_dict') else design_content
                }
            )
            
            logger.info(f"Design generation job {context.job_id} completed successfully")
            
            return JobResult(
                success=True,
                data={
                    'spec_id': spec_id,
                    'generation_type': 'design',
                    'provider': provider,
                    'artifact_data': design_content.to_dict() if hasattr(design_content, 'to_dict') else design_content
                }
            )
            
        except Exception as e:
            error_message = f"Design generation job failed: {str(e)}"
            logger.error(f"Job {context.job_id} failed with exception: {e}")
            import traceback
            traceback.print_exc()
            
            # Find the original feed item ID for error reporting
            try:
                from ..models.specification_artifact import SpecificationArtifact
            except ImportError:
                from models.specification_artifact import SpecificationArtifact
            
            any_artifact = SpecificationArtifact.query.filter_by(spec_id=spec_id).first()
            original_item_id = self._extract_item_id_from_spec_id(spec_id)
            
            # Emit failure event
            self._emit_progress_event(
                job_id=context.job_id,
                item_id=original_item_id,
                event_type='failed',
                data={
                    'error': error_message,
                    'generation_type': 'design',
                    'provider': provider,
                    'retry_available': True
                }
            )
            
            return JobResult(success=False, error=error_message)
    
    def _handle_tasks_generation_job(self, context: JobContext, project_id: int, **kwargs) -> JobResult:
        """Background job handler for tasks generation"""
        spec_id = kwargs.get('spec_id')
        provider = kwargs.get('provider', 'claude')
        
        try:
            logger.info(f"📋 TASKS GENERATION JOB STARTED")
            logger.info(f"   🆔 Job ID: {context.job_id}")
            logger.info(f"   📋 Spec ID: {spec_id}")
            logger.info(f"   🤖 AI Provider: {provider.upper()}")
            logger.info(f"   🎯 Provider will be passed to DefineAgent")
            
            # Extract the original feed item ID from spec_id
            original_item_id = self._extract_item_id_from_spec_id(spec_id)
            
            # Update progress: Starting
            context.update_progress(10, "Starting tasks generation...")
            self._emit_progress_event(
                job_id=context.job_id,
                item_id=original_item_id,  # Use original feed item ID
                event_type='progress',
                data={
                    'progress': 10,
                    'stage': 'starting',
                    'message': 'Starting tasks generation...',
                    'generation_type': 'tasks'
                }
            )
            
            # Import required modules
            try:
                from ..models.specification_artifact import SpecificationArtifact, ArtifactType
                from ..agents.define_agent import DefineAgent
                from ..services.ai_broker import AIBroker
                from ..events.event_router import EventBus
                from ..api.stages import _generate_tasks_document_core
            except ImportError:
                from models.specification_artifact import SpecificationArtifact, ArtifactType
                from agents.define_agent import DefineAgent
                from services.ai_broker import AIBroker
                from events.event_router import EventBus
                from api.stages import _generate_tasks_document_core
            
            # Get requirements and design artifacts
            context.update_progress(20, "Loading requirements and design documents...")
            self._emit_progress_event(
                job_id=context.job_id,
                item_id=original_item_id,
                event_type='progress',
                data={
                    'progress': 20,
                    'stage': 'loading',
                    'message': 'Loading requirements and design documents...',
                    'generation_type': 'tasks'
                }
            )
            
            requirements_artifact = SpecificationArtifact.query.filter_by(
                spec_id=spec_id,
                artifact_type=ArtifactType.REQUIREMENTS
            ).first()
            
            design_artifact = SpecificationArtifact.query.filter_by(
                spec_id=spec_id,
                artifact_type=ArtifactType.DESIGN
            ).first()
            
            if not requirements_artifact:
                raise Exception("Requirements document not found. Generate requirements first.")
            
            if not design_artifact:
                raise Exception("Design document not found. Generate design first.")
            
            # Initialize DefineAgent
            context.update_progress(30, "Initializing AI agent...")
            self._emit_progress_event(
                job_id=context.job_id,
                item_id=original_item_id,
                event_type='progress',
                data={
                    'progress': 30,
                    'stage': 'initializing',
                    'message': 'Initializing AI agent...',
                    'generation_type': 'tasks'
                }
            )
            
            event_bus = EventBus()
            ai_broker = AIBroker()
            ai_broker.start()
            define_agent = DefineAgent(event_bus, ai_broker)
            
            # Generate tasks document
            context.update_progress(50, "Generating tasks document...")
            self._emit_progress_event(
                job_id=context.job_id,
                item_id=original_item_id,
                event_type='progress',
                data={
                    'progress': 50,
                    'stage': 'generating',
                    'message': 'Generating tasks document...',
                    'generation_type': 'tasks'
                }
            )
            
            tasks_content = _generate_tasks_document_core(
                spec_id=spec_id,
                project_id=str(project_id),
                requirements_artifact=requirements_artifact,
                design_artifact=design_artifact,
                define_agent=define_agent,
                provider=provider
            )
            
            context.update_progress(90, "Saving tasks document...")
            self._emit_progress_event(
                job_id=context.job_id,
                item_id=original_item_id,
                event_type='progress',
                data={
                    'progress': 90,
                    'stage': 'saving',
                    'message': 'Saving tasks document...',
                    'generation_type': 'tasks'
                }
            )
            
            # Save the generated tasks document to the database
            logger.info(f"💾 Saving tasks document to database...")
            define_agent._store_specifications(spec_id, str(project_id), {'tasks': tasks_content})
            logger.info(f"✅ Tasks document saved to database")
            
            # Complete
            context.update_progress(100, "Tasks document generated successfully!")
            
            # Emit completion event
            self._emit_progress_event(
                job_id=context.job_id,
                item_id=original_item_id,
                event_type='complete',
                data={
                    'spec_id': spec_id,
                    'generation_type': 'tasks',
                    'provider': provider,
                    'artifact_data': tasks_content.to_dict() if hasattr(tasks_content, 'to_dict') else tasks_content
                }
            )
            
            logger.info(f"Tasks generation job {context.job_id} completed successfully")
            
            return JobResult(
                success=True,
                data={
                    'spec_id': spec_id,
                    'generation_type': 'tasks',
                    'provider': provider,
                    'artifact_data': tasks_content.to_dict() if hasattr(tasks_content, 'to_dict') else tasks_content
                }
            )
            
        except Exception as e:
            error_message = f"Tasks generation job failed: {str(e)}"
            logger.error(f"Job {context.job_id} failed with exception: {e}")
            import traceback
            traceback.print_exc()
            
            # Find the original feed item ID for error reporting
            try:
                from ..models.specification_artifact import SpecificationArtifact
            except ImportError:
                from models.specification_artifact import SpecificationArtifact
            
            any_artifact = SpecificationArtifact.query.filter_by(spec_id=spec_id).first()
            original_item_id = self._extract_item_id_from_spec_id(spec_id)
            
            # Emit failure event
            self._emit_progress_event(
                job_id=context.job_id,
                item_id=original_item_id,
                event_type='failed',
                data={
                    'error': error_message,
                    'generation_type': 'tasks',
                    'provider': provider,
                    'retry_available': True
                }
            )
            
            return JobResult(success=False, error=error_message)
    
    def _emit_progress_event(self, job_id: int, item_id: str, event_type: str, data: Dict[str, Any]):
        """Emit WebSocket event for spec generation progress"""
        try:
            from flask import current_app
            
            event_name = f'spec.generation.{event_type}'
            event_data = {
                'job_id': job_id,
                'item_id': item_id,
                'timestamp': datetime.utcnow().isoformat(),
                **data
            }
            
            # Get SocketIO instance from app extensions
            socketio = current_app.extensions.get('socketio')
            if socketio:
                # Use the correct method for broadcasting to all clients
                socketio.emit(event_name, event_data, namespace='/')
                logger.info(f"Emitted {event_name} event for job {job_id}")
            else:
                logger.warning("SocketIO not available - cannot emit progress event")
            
        except Exception as e:
            logger.error(f"Failed to emit progress event: {e}")


    def start_design_generation(self, spec_id: str, project_id: str, provider: str = 'claude') -> Dict[str, Any]:
        """
        Start asynchronous design generation for a specification
        
        Args:
            spec_id: Specification ID to generate design for
            project_id: Project ID
            provider: AI provider ('claude' or 'model-garden')
        
        Returns:
            Dict with job_id and status information
        """
        try:
            logger.info(f"🎨 ASYNC DESIGN GENERATION STARTED")
            logger.info(f"   📋 Spec ID: {spec_id}")
            logger.info(f"   🏗️  Project ID: {project_id}")
            logger.info(f"   🤖 AI Provider: {provider.upper()}")
            
            # Submit background job
            job_id = self.job_manager.submit_job(
                job_type='design_generation',
                project_id=int(project_id) if project_id.isdigit() else None,
                spec_id=spec_id,
                provider=provider
            )
            
            # Update job metadata
            job = BackgroundJob.query.get(job_id)
            if job:
                job.job_metadata = {
                    'spec_id': spec_id,
                    'project_id': project_id,
                    'provider': provider,
                    'generation_type': 'design',
                    'started_by': 'user'
                }
                db.session.commit()
            
            logger.info(f"✅ Design generation job submitted - Job ID: {job_id}")
            
            return {
                'job_id': job_id,
                'status': 'started',
                'estimated_duration': 60,  # seconds
                'provider': provider
            }
            
        except Exception as e:
            logger.error(f"Failed to start design generation for {spec_id}: {e}")
            raise
    
    def start_tasks_generation(self, spec_id: str, project_id: str, provider: str = 'claude') -> Dict[str, Any]:
        """
        Start asynchronous tasks generation for a specification
        
        Args:
            spec_id: Specification ID to generate tasks for
            project_id: Project ID
            provider: AI provider ('claude' or 'model-garden')
        
        Returns:
            Dict with job_id and status information
        """
        try:
            logger.info(f"📋 ASYNC TASKS GENERATION STARTED")
            logger.info(f"   📋 Spec ID: {spec_id}")
            logger.info(f"   🏗️  Project ID: {project_id}")
            logger.info(f"   🤖 AI Provider: {provider.upper()}")
            
            # Submit background job
            job_id = self.job_manager.submit_job(
                job_type='tasks_generation',
                project_id=int(project_id) if project_id.isdigit() else None,
                spec_id=spec_id,
                provider=provider
            )
            
            # Update job metadata
            job = BackgroundJob.query.get(job_id)
            if job:
                job.job_metadata = {
                    'spec_id': spec_id,
                    'project_id': project_id,
                    'provider': provider,
                    'generation_type': 'tasks',
                    'started_by': 'user'
                }
                db.session.commit()
            
            logger.info(f"✅ Tasks generation job submitted - Job ID: {job_id}")
            
            return {
                'job_id': job_id,
                'status': 'started',
                'estimated_duration': 45,  # seconds
                'provider': provider
            }
            
        except Exception as e:
            logger.error(f"Failed to start tasks generation for {spec_id}: {e}")
            raise


# Global service instance
_spec_generation_service = None


def get_spec_generation_service() -> SpecGenerationService:
    """Get the global spec generation service instance"""
    global _spec_generation_service
    if _spec_generation_service is None:
        _spec_generation_service = SpecGenerationService()
    return _spec_generation_service


def init_spec_generation_service(app) -> SpecGenerationService:
    """Initialize the global spec generation service"""
    service = get_spec_generation_service()
    service.init_app(app)
    return service