"""
AI Broker Service - Intelligent model orchestration and request management
Manages multiple AI model connections with smart selection, queuing, and context management
"""

import asyncio
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from queue import Queue, PriorityQueue, Empty
from threading import Lock, RLock
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
import json

from .ai_service import AIService, GooseIntegration, ModelGardenIntegration
from .vector_service import get_vector_service

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Types of AI tasks for intelligent model selection"""
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    DOCUMENTATION = "documentation"
    ANALYSIS = "analysis"
    CONVERSATION = "conversation"
    PLANNING = "planning"
    DEBUGGING = "debugging"
    TESTING = "testing"
    ARCHITECTURE = "architecture"
    GENERAL = "general"


class ModelCapability(Enum):
    """AI model capabilities"""
    CODING = "coding"
    REASONING = "reasoning"
    CREATIVITY = "creativity"
    ANALYSIS = "analysis"
    SPEED = "speed"
    CONTEXT_LENGTH = "context_length"
    COST_EFFICIENCY = "cost_efficiency"


class Priority(Enum):
    """Request priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class ModelConfig:
    """Configuration for an AI model"""
    model_id: str
    provider: str
    name: str
    capabilities: List[ModelCapability]
    max_tokens: int
    cost_per_token: float
    avg_response_time: float
    max_concurrent_requests: int
    context_window: int
    is_available: bool = True
    current_load: int = 0
    total_requests: int = 0
    success_rate: float = 1.0
    avg_quality_score: float = 0.8


@dataclass
class AIRequest:
    """AI request with metadata and context"""
    request_id: str
    task_type: TaskType
    instruction: str
    context: Dict[str, Any] = field(default_factory=dict)
    priority: Priority = Priority.NORMAL
    max_tokens: Optional[int] = None
    timeout_seconds: float = 300.0
    retry_attempts: int = 3
    preferred_models: List[str] = field(default_factory=list)
    excluded_models: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def __lt__(self, other):
        """For priority queue ordering"""
        return self.priority.value > other.priority.value


@dataclass
class AIResponse:
    """AI response with metadata and performance metrics"""
    request_id: str
    success: bool
    content: str
    model_used: str
    provider: str
    processing_time: float
    tokens_used: int
    cost_estimate: float
    quality_score: Optional[float] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    completed_at: datetime = field(default_factory=datetime.utcnow)


class ModelSelector:
    """Intelligent model selection based on task requirements"""
    
    def __init__(self):
        self.model_configs = self._initialize_model_configs()
        self.task_model_preferences = self._initialize_task_preferences()
        self.performance_history = {}
        self._lock = Lock()
    
    def _initialize_model_configs(self) -> Dict[str, ModelConfig]:
        """Initialize model configurations"""
        return {
            'goose-gemini': ModelConfig(
                model_id='goose-gemini',
                provider='goose',
                name='Gemini 2.5 Flash (via Goose)',
                capabilities=[
                    ModelCapability.CODING,
                    ModelCapability.ANALYSIS,
                    ModelCapability.SPEED,
                    ModelCapability.COST_EFFICIENCY
                ],
                max_tokens=8192,
                cost_per_token=0.00001,
                avg_response_time=15.0,
                max_concurrent_requests=3,
                context_window=32768
            ),
            'claude-opus-4': ModelConfig(
                model_id='claude-opus-4',
                provider='model_garden',
                name='Claude Opus 4',
                capabilities=[
                    ModelCapability.REASONING,
                    ModelCapability.CREATIVITY,
                    ModelCapability.ANALYSIS,
                    ModelCapability.CONTEXT_LENGTH
                ],
                max_tokens=4096,
                cost_per_token=0.00015,
                avg_response_time=8.0,
                max_concurrent_requests=5,
                context_window=200000
            ),
            'claude-sonnet-3.5': ModelConfig(
                model_id='claude-sonnet-3.5',
                provider='model_garden',
                name='Claude Sonnet 3.5',
                capabilities=[
                    ModelCapability.CODING,
                    ModelCapability.REASONING,
                    ModelCapability.SPEED,
                    ModelCapability.ANALYSIS
                ],
                max_tokens=4096,
                cost_per_token=0.00003,
                avg_response_time=5.0,
                max_concurrent_requests=8,
                context_window=200000
            ),
            'gemini-2.5-flash': ModelConfig(
                model_id='gemini-2.5-flash',
                provider='model_garden',
                name='Gemini 2.5 Flash',
                capabilities=[
                    ModelCapability.SPEED,
                    ModelCapability.COST_EFFICIENCY,
                    ModelCapability.CODING
                ],
                max_tokens=8192,
                cost_per_token=0.000075,
                avg_response_time=3.0,
                max_concurrent_requests=10,
                context_window=1000000
            ),
            'gpt-4o': ModelConfig(
                model_id='gpt-4o',
                provider='model_garden',
                name='GPT-4o',
                capabilities=[
                    ModelCapability.REASONING,
                    ModelCapability.CREATIVITY,
                    ModelCapability.ANALYSIS,
                    ModelCapability.CODING
                ],
                max_tokens=4096,
                cost_per_token=0.00005,
                avg_response_time=7.0,
                max_concurrent_requests=6,
                context_window=128000
            )
        }
    
    def _initialize_task_preferences(self) -> Dict[TaskType, List[str]]:
        """Initialize task-specific model preferences"""
        return {
            TaskType.CODE_GENERATION: ['claude-sonnet-3.5', 'goose-gemini', 'gpt-4o'],
            TaskType.CODE_REVIEW: ['claude-opus-4', 'claude-sonnet-3.5', 'gpt-4o'],
            TaskType.DOCUMENTATION: ['goose-gemini', 'claude-opus-4', 'gpt-4o', 'claude-sonnet-3.5'],
            TaskType.ANALYSIS: ['claude-opus-4', 'gpt-4o', 'claude-sonnet-3.5'],
            TaskType.CONVERSATION: ['claude-sonnet-3.5', 'gpt-4o', 'gemini-2.5-flash'],
            TaskType.PLANNING: ['claude-opus-4', 'gpt-4o', 'claude-sonnet-3.5'],
            TaskType.DEBUGGING: ['claude-sonnet-3.5', 'goose-gemini', 'gpt-4o'],
            TaskType.TESTING: ['claude-sonnet-3.5', 'gpt-4o', 'goose-gemini'],
            TaskType.ARCHITECTURE: ['claude-opus-4', 'gpt-4o', 'claude-sonnet-3.5'],
            TaskType.GENERAL: ['gemini-2.5-flash', 'claude-sonnet-3.5', 'gpt-4o']
        }
    
    def select_model(self, request: AIRequest) -> Optional[str]:
        """
        Select the best model for a request based on multiple factors
        
        Args:
            request: The AI request to process
            
        Returns:
            Selected model ID or None if no suitable model available
        """
        with self._lock:
            # Get candidate models
            candidates = self._get_candidate_models(request)
            
            if not candidates:
                logger.warning(f"No candidate models found for request {request.request_id}")
                return None
            
            # Score each candidate model
            scored_models = []
            for model_id in candidates:
                score = self._score_model(model_id, request)
                if score > 0:
                    scored_models.append((model_id, score))
            
            if not scored_models:
                logger.warning(f"No suitable models found for request {request.request_id}")
                return None
            
            # Sort by score (highest first)
            scored_models.sort(key=lambda x: x[1], reverse=True)
            
            # Select the best available model
            for model_id, score in scored_models:
                model_config = self.model_configs[model_id]
                if (model_config.is_available and 
                    model_config.current_load < model_config.max_concurrent_requests):
                    logger.info(f"Selected model {model_id} (score: {score:.2f}) for request {request.request_id}")
                    return model_id
            
            logger.warning(f"All suitable models are at capacity for request {request.request_id}")
            return None
    
    def _get_candidate_models(self, request: AIRequest) -> List[str]:
        """Get candidate models for a request"""
        # Start with preferred models if specified
        if request.preferred_models:
            candidates = [m for m in request.preferred_models if m in self.model_configs]
        else:
            # Use task-specific preferences
            candidates = self.task_model_preferences.get(request.task_type, list(self.model_configs.keys()))
        
        # Remove excluded models
        candidates = [m for m in candidates if m not in request.excluded_models]
        
        # Filter by availability
        candidates = [m for m in candidates if self.model_configs[m].is_available]
        
        return candidates
    
    def _score_model(self, model_id: str, request: AIRequest) -> float:
        """
        Score a model for a specific request
        
        Factors considered:
        - Task type compatibility
        - Current load
        - Performance history
        - Cost efficiency
        - Response time
        - Context requirements
        """
        model_config = self.model_configs[model_id]
        score = 0.0
        
        # Base score from task preferences
        task_preferences = self.task_model_preferences.get(request.task_type, [])
        if model_id in task_preferences:
            position = task_preferences.index(model_id)
            score += (len(task_preferences) - position) * 10
        
        # Load factor (prefer less loaded models)
        load_factor = 1.0 - (model_config.current_load / model_config.max_concurrent_requests)
        score += load_factor * 20
        
        # Performance history
        score += model_config.success_rate * 15
        score += model_config.avg_quality_score * 10
        
        # Response time (prefer faster models for high priority)
        if request.priority in [Priority.HIGH, Priority.URGENT]:
            time_score = max(0, 10 - model_config.avg_response_time)
            score += time_score
        
        # Cost efficiency (prefer cheaper models for low priority)
        if request.priority == Priority.LOW:
            cost_score = max(0, 10 - (model_config.cost_per_token * 100000))
            score += cost_score
        
        # Context window requirements
        estimated_context_tokens = len(request.instruction.split()) * 1.3  # Rough estimate
        if request.context:
            estimated_context_tokens += sum(len(str(v).split()) * 1.3 for v in request.context.values())
        
        if estimated_context_tokens > model_config.context_window:
            score = 0  # Model cannot handle the context
        
        return max(0, score)
    
    def update_model_performance(self, model_id: str, response: AIResponse):
        """Update model performance metrics based on response"""
        with self._lock:
            if model_id not in self.model_configs:
                return
            
            config = self.model_configs[model_id]
            
            # Update success rate (exponential moving average)
            alpha = 0.1
            config.success_rate = (1 - alpha) * config.success_rate + alpha * (1.0 if response.success else 0.0)
            
            # Update average response time
            config.avg_response_time = (1 - alpha) * config.avg_response_time + alpha * response.processing_time
            
            # Update quality score if available
            if response.quality_score is not None:
                config.avg_quality_score = (1 - alpha) * config.avg_quality_score + alpha * response.quality_score
            
            # Update total requests
            config.total_requests += 1
    
    def get_model_status(self) -> Dict[str, Dict[str, Any]]:
        """Get current status of all models"""
        with self._lock:
            return {
                model_id: {
                    'name': config.name,
                    'provider': config.provider,
                    'is_available': config.is_available,
                    'current_load': config.current_load,
                    'max_concurrent': config.max_concurrent_requests,
                    'success_rate': config.success_rate,
                    'avg_response_time': config.avg_response_time,
                    'avg_quality_score': config.avg_quality_score,
                    'total_requests': config.total_requests,
                    'capabilities': [cap.value for cap in config.capabilities]
                }
                for model_id, config in self.model_configs.items()
            }


class RequestQueue:
    """Priority-based request queue with load balancing"""
    
    def __init__(self):
        self.queue = PriorityQueue()
        self.pending_requests = {}
        self.processing_requests = {}
        self._lock = RLock()
    
    def enqueue(self, request: AIRequest):
        """Add request to queue"""
        with self._lock:
            self.queue.put(request)
            self.pending_requests[request.request_id] = request
            logger.debug(f"Enqueued request {request.request_id} with priority {request.priority.name}")
    
    def dequeue(self, timeout: float = 1.0) -> Optional[AIRequest]:
        """Get next request from queue"""
        try:
            request = self.queue.get(timeout=timeout)
            with self._lock:
                self.pending_requests.pop(request.request_id, None)
                self.processing_requests[request.request_id] = request
            return request
        except Empty:
            return None
    
    def complete_request(self, request_id: str):
        """Mark request as completed"""
        with self._lock:
            self.processing_requests.pop(request_id, None)
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        with self._lock:
            return {
                'pending_count': len(self.pending_requests),
                'processing_count': len(self.processing_requests),
                'queue_size': self.queue.qsize(),
                'pending_by_priority': self._count_by_priority(self.pending_requests.values()),
                'processing_by_priority': self._count_by_priority(self.processing_requests.values())
            }
    
    def _count_by_priority(self, requests) -> Dict[str, int]:
        """Count requests by priority"""
        counts = {priority.name: 0 for priority in Priority}
        for request in requests:
            counts[request.priority.name] += 1
        return counts


class ContextManager:
    """Manages context retrieval and enhancement for AI requests"""
    
    def __init__(self):
        self.vector_service = get_vector_service()
    
    def enhance_request_context(self, request: AIRequest) -> AIRequest:
        """
        Enhance request with relevant context from vector database and other sources
        
        Args:
            request: The original AI request
            
        Returns:
            Enhanced request with additional context
        """
        try:
            enhanced_request = request
            
            # Get vector context if available
            if self.vector_service:
                vector_context = self._get_vector_context(request)
                if vector_context:
                    enhanced_request.context['vector_context'] = vector_context
            
            # Add task-specific context
            task_context = self._get_task_specific_context(request)
            if task_context:
                enhanced_request.context.update(task_context)
            
            # Add role-based context
            role_context = self._get_role_based_context(request)
            if role_context:
                enhanced_request.context['role_context'] = role_context
            
            logger.debug(f"Enhanced context for request {request.request_id}")
            return enhanced_request
            
        except Exception as e:
            logger.error(f"Failed to enhance context for request {request.request_id}: {e}")
            return request
    
    def _get_vector_context(self, request: AIRequest) -> Optional[str]:
        """Get relevant context from vector database"""
        try:
            # Determine document types based on task type
            document_types = self._get_relevant_document_types(request.task_type)
            
            # Get context with appropriate token limit
            max_context_tokens = min(1500, request.max_tokens // 3 if request.max_tokens else 1500)
            
            context = self.vector_service.get_ai_context(
                query=request.instruction,
                max_tokens=max_context_tokens,
                document_types=document_types
            )
            
            return context if context.strip() else None
            
        except Exception as e:
            logger.warning(f"Failed to get vector context: {e}")
            return None
    
    def _get_relevant_document_types(self, task_type: TaskType) -> Optional[List[str]]:
        """Get relevant document types for a task type"""
        type_mapping = {
            TaskType.CODE_GENERATION: ['code_file', 'documentation'],
            TaskType.CODE_REVIEW: ['code_file', 'documentation'],
            TaskType.DOCUMENTATION: ['code_file', 'documentation', 'conversation'],
            TaskType.ANALYSIS: ['code_file', 'system_map', 'conversation'],
            TaskType.CONVERSATION: ['conversation', 'documentation'],
            TaskType.PLANNING: ['system_map', 'documentation', 'conversation'],
            TaskType.DEBUGGING: ['code_file', 'conversation'],
            TaskType.TESTING: ['code_file', 'documentation'],
            TaskType.ARCHITECTURE: ['system_map', 'code_file', 'documentation']
        }
        
        return type_mapping.get(task_type)
    
    def _get_task_specific_context(self, request: AIRequest) -> Dict[str, Any]:
        """Get task-specific context and instructions"""
        context = {}
        
        task_instructions = {
            TaskType.CODE_GENERATION: {
                'guidelines': [
                    'Follow best practices and coding standards',
                    'Include proper error handling',
                    'Add meaningful comments and documentation',
                    'Consider security implications',
                    'Write testable code'
                ]
            },
            TaskType.CODE_REVIEW: {
                'focus_areas': [
                    'Code quality and maintainability',
                    'Security vulnerabilities',
                    'Performance implications',
                    'Best practices adherence',
                    'Test coverage'
                ]
            },
            TaskType.DOCUMENTATION: {
                'requirements': [
                    'Clear and concise explanations',
                    'Include examples where appropriate',
                    'Structure information logically',
                    'Consider the target audience',
                    'Keep documentation up-to-date'
                ]
            }
        }
        
        if request.task_type in task_instructions:
            context['task_guidelines'] = task_instructions[request.task_type]
        
        return context
    
    def _get_role_based_context(self, request: AIRequest) -> Optional[str]:
        """Get role-based context from request metadata"""
        role = request.metadata.get('role', 'general')
        
        role_contexts = {
            'business': 'Focus on business value, user impact, and strategic alignment.',
            'po': 'Consider product requirements, user stories, and acceptance criteria.',
            'developer': 'Emphasize technical implementation, code quality, and best practices.',
            'designer': 'Focus on user experience, design patterns, and accessibility.',
            'architect': 'Consider system design, scalability, and architectural patterns.'
        }
        
        return role_contexts.get(role)


class AIBroker:
    """
    Main AI Broker service that orchestrates multiple AI models
    with intelligent selection, queuing, and context management
    """
    
    def __init__(self):
        self.ai_service = AIService()
        self.model_selector = ModelSelector()
        self.request_queue = RequestQueue()
        self.context_manager = ContextManager()
        self.executor = ThreadPoolExecutor(max_workers=20)
        self.active_requests = {}
        self.completed_requests = {}
        self.request_callbacks = {}
        self._lock = RLock()
        self._running = False
        self._worker_futures = []
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'avg_response_time': 0.0,
            'total_tokens_used': 0,
            'total_cost': 0.0,
            'started_at': None
        }
    
    def start(self):
        """Start the AI broker service"""
        with self._lock:
            if self._running:
                return
            
            # Create new executor if the old one was shut down
            if hasattr(self.executor, '_shutdown') and self.executor._shutdown:
                self.executor = ThreadPoolExecutor(max_workers=20)
            
            self._running = True
            self.stats['started_at'] = datetime.utcnow()
            self._worker_futures = []  # Reset worker futures list
            
            # Start worker threads
            for i in range(5):  # 5 worker threads
                future = self.executor.submit(self._worker_loop)
                self._worker_futures.append(future)
            
            logger.info("AI Broker service started")
    
    def stop(self):
        """Stop the AI broker service"""
        with self._lock:
            if not self._running:
                return
            
            self._running = False
            
            # Wait for workers to finish
            for future in self._worker_futures:
                try:
                    future.result(timeout=5)
                except Exception as e:
                    logger.warning(f"Worker thread error during shutdown: {e}")
            
            # Don't shutdown executor immediately, just mark as stopped
            # This allows for restart without recreating the executor
            logger.info("AI Broker service stopped")
    
    def submit_request(self, request: AIRequest, 
                      callback: Optional[Callable[[AIResponse], None]] = None) -> str:
        """
        Submit an AI request for processing
        
        Args:
            request: The AI request to process
            callback: Optional callback function for async processing
            
        Returns:
            Request ID for tracking
        """
        with self._lock:
            # Enhance request with context
            enhanced_request = self.context_manager.enhance_request_context(request)
            
            # Store callback if provided
            if callback:
                self.request_callbacks[request.request_id] = callback
            
            # Add to queue
            self.request_queue.enqueue(enhanced_request)
            self.stats['total_requests'] += 1
            
            logger.info(f"Submitted request {request.request_id} for {request.task_type.value}")
            return request.request_id
    
    def submit_request_sync(self, request: AIRequest, timeout: float = 300.0) -> AIResponse:
        """
        Submit an AI request and wait for response synchronously
        
        Args:
            request: The AI request to process
            timeout: Maximum time to wait for response
            
        Returns:
            AI response
        """
        import threading
        
        response_event = threading.Event()
        response_container = {'response': None}
        
        def callback(response: AIResponse):
            response_container['response'] = response
            response_event.set()
        
        # Submit request with callback
        self.submit_request(request, callback)
        
        # Wait for response
        if response_event.wait(timeout):
            return response_container['response']
        else:
            # Timeout occurred
            return AIResponse(
                request_id=request.request_id,
                success=False,
                content='',
                model_used='',
                provider='',
                processing_time=timeout,
                tokens_used=0,
                cost_estimate=0.0,
                error_message='Request timed out'
            )
    
    def get_request_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific request"""
        with self._lock:
            if request_id in self.completed_requests:
                response = self.completed_requests[request_id]
                return {
                    'status': 'completed',
                    'success': response.success,
                    'model_used': response.model_used,
                    'processing_time': response.processing_time,
                    'completed_at': response.completed_at.isoformat()
                }
            elif request_id in self.active_requests:
                return {
                    'status': 'processing',
                    'started_at': self.active_requests[request_id].isoformat()
                }
            elif request_id in self.request_queue.pending_requests:
                return {
                    'status': 'queued',
                    'queue_position': self._get_queue_position(request_id)
                }
            else:
                return None
    
    def _get_queue_position(self, request_id: str) -> int:
        """Get position of request in queue (approximate)"""
        # This is a simplified implementation
        return self.request_queue.queue.qsize()
    
    def _worker_loop(self):
        """Main worker loop for processing requests"""
        while self._running:
            try:
                # Get next request from queue
                request = self.request_queue.dequeue(timeout=1.0)
                if not request:
                    continue
                
                # Process the request
                self._process_request(request)
                
            except Exception as e:
                logger.error(f"Worker loop error: {e}")
    
    def _process_request(self, request: AIRequest):
        """Process a single AI request"""
        start_time = time.time()
        
        try:
            with self._lock:
                self.active_requests[request.request_id] = datetime.utcnow()
            
            # Select best model for this request
            selected_model = self.model_selector.select_model(request)
            
            if not selected_model:
                # No suitable model available
                response = AIResponse(
                    request_id=request.request_id,
                    success=False,
                    content='',
                    model_used='',
                    provider='',
                    processing_time=time.time() - start_time,
                    tokens_used=0,
                    cost_estimate=0.0,
                    error_message='No suitable model available'
                )
            else:
                # Update model load
                with self._lock:
                    self.model_selector.model_configs[selected_model].current_load += 1
                
                try:
                    # Execute request with selected model
                    response = self._execute_request(request, selected_model)
                finally:
                    # Decrease model load
                    with self._lock:
                        self.model_selector.model_configs[selected_model].current_load -= 1
            
            # Update statistics
            self._update_statistics(response)
            
            # Update model performance
            if response.model_used:
                self.model_selector.update_model_performance(response.model_used, response)
            
            # Store completed request
            with self._lock:
                self.completed_requests[request.request_id] = response
                self.active_requests.pop(request.request_id, None)
                
                # Limit completed requests history
                if len(self.completed_requests) > 1000:
                    # Remove oldest 200 requests
                    oldest_requests = sorted(
                        self.completed_requests.items(),
                        key=lambda x: x[1].completed_at
                    )[:200]
                    for req_id, _ in oldest_requests:
                        self.completed_requests.pop(req_id, None)
            
            # Call callback if provided
            callback = self.request_callbacks.pop(request.request_id, None)
            if callback:
                try:
                    callback(response)
                except Exception as e:
                    logger.error(f"Callback error for request {request.request_id}: {e}")
            
            # Mark request as completed in queue
            self.request_queue.complete_request(request.request_id)
            
            logger.info(f"Completed request {request.request_id} using {response.model_used} "
                       f"in {response.processing_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Failed to process request {request.request_id}: {e}")
            
            # Create error response
            response = AIResponse(
                request_id=request.request_id,
                success=False,
                content='',
                model_used='',
                provider='',
                processing_time=time.time() - start_time,
                tokens_used=0,
                cost_estimate=0.0,
                error_message=str(e)
            )
            
            # Update statistics and complete request
            self._update_statistics(response)
            
            with self._lock:
                self.completed_requests[request.request_id] = response
                self.active_requests.pop(request.request_id, None)
            
            self.request_queue.complete_request(request.request_id)
    
    def _execute_request(self, request: AIRequest, model_id: str) -> AIResponse:
        """Execute request with specific model"""
        start_time = time.time()
        
        try:
            model_config = self.model_selector.model_configs[model_id]
            
            # Prepare instruction with context
            enhanced_instruction = self._prepare_instruction(request)
            
            # Execute based on provider
            if model_config.provider == 'goose':
                result = self.ai_service.execute_goose_task(
                    instruction=enhanced_instruction,
                    business_context=request.context.get('business_context', {}),
                    github_repo=request.context.get('github_repo'),
                    role=request.metadata.get('role', 'general')
                )
            elif model_config.provider == 'model_garden':
                result = self.ai_service.execute_model_garden_task(
                    instruction=enhanced_instruction,
                    product_context=request.context.get('product_context', {}),
                    model=model_id,
                    role=request.metadata.get('role', 'po')
                )
            else:
                raise ValueError(f"Unknown provider: {model_config.provider}")
            
            processing_time = time.time() - start_time
            
            # Estimate tokens and cost
            tokens_used = self._estimate_tokens(enhanced_instruction, result.get('output', ''))
            cost_estimate = tokens_used * model_config.cost_per_token
            
            return AIResponse(
                request_id=request.request_id,
                success=result['success'],
                content=result.get('output', ''),
                model_used=model_id,
                provider=model_config.provider,
                processing_time=processing_time,
                tokens_used=tokens_used,
                cost_estimate=cost_estimate,
                error_message=result.get('error'),
                metadata={
                    'enhanced_instruction': result.get('enhanced_instruction'),
                    'original_result': result
                }
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Failed to execute request {request.request_id} with model {model_id}: {e}")
            
            return AIResponse(
                request_id=request.request_id,
                success=False,
                content='',
                model_used=model_id,
                provider=model_config.provider if 'model_config' in locals() else '',
                processing_time=processing_time,
                tokens_used=0,
                cost_estimate=0.0,
                error_message=str(e)
            )
    
    def _prepare_instruction(self, request: AIRequest) -> str:
        """Prepare instruction - pass DefineAgent prompts through unchanged"""
        
        # Check if this is a DefineAgent request that should be passed through unchanged
        if (request.metadata and 
            request.metadata.get('agent') == 'define_agent' and 
            request.metadata.get('type') in ['requirements', 'design', 'tasks']):
            
            logger.info(f"DefineAgent request detected - passing prompt through unchanged")
            logger.info(f"Original prompt length: {len(request.instruction)}")
            return request.instruction  # Pass DefineAgent prompt unchanged
        
        # For other requests, apply normal context enhancement
        instruction_parts = []
        
        # Add vector context if available
        if 'vector_context' in request.context and request.context['vector_context']:
            instruction_parts.append(request.context['vector_context'])
        
        # Add role context if available
        if 'role_context' in request.context and request.context['role_context']:
            instruction_parts.append(f"Role Context: {request.context['role_context']}")
        
        # Add task guidelines if available
        if 'task_guidelines' in request.context:
            guidelines = request.context['task_guidelines']
            if isinstance(guidelines, dict):
                for key, values in guidelines.items():
                    if isinstance(values, list):
                        instruction_parts.append(f"{key.title()}:\n" + "\n".join(f"- {v}" for v in values))
        
        # Add the main instruction
        instruction_parts.append(f"Task: {request.instruction}")
        
        return "\n\n".join(instruction_parts)
    
    def _estimate_tokens(self, instruction: str, response: str) -> int:
        """Estimate token usage for request and response"""
        # Rough estimation: 1 token ≈ 0.75 words
        word_count = len(instruction.split()) + len(response.split())
        return int(word_count / 0.75)
    
    def _update_statistics(self, response: AIResponse):
        """Update broker statistics"""
        with self._lock:
            if response.success:
                self.stats['successful_requests'] += 1
            else:
                self.stats['failed_requests'] += 1
            
            # Update average response time (exponential moving average)
            alpha = 0.1
            if self.stats['avg_response_time'] == 0:
                self.stats['avg_response_time'] = response.processing_time
            else:
                self.stats['avg_response_time'] = (
                    (1 - alpha) * self.stats['avg_response_time'] + 
                    alpha * response.processing_time
                )
            
            self.stats['total_tokens_used'] += response.tokens_used
            self.stats['total_cost'] += response.cost_estimate
    
    def get_broker_status(self) -> Dict[str, Any]:
        """Get comprehensive broker status"""
        with self._lock:
            return {
                'service_status': {
                    'running': self._running,
                    'started_at': self.stats['started_at'].isoformat() if self.stats['started_at'] else None,
                    'worker_threads': len(self._worker_futures)
                },
                'statistics': self.stats.copy(),
                'queue_status': self.request_queue.get_queue_status(),
                'model_status': self.model_selector.get_model_status(),
                'active_requests': len(self.active_requests),
                'completed_requests': len(self.completed_requests)
            }
    
    def create_request(self, instruction: str, task_type: TaskType = TaskType.GENERAL,
                      priority: Priority = Priority.NORMAL, **kwargs) -> AIRequest:
        """
        Convenience method to create an AI request
        
        Args:
            instruction: The instruction/prompt for the AI
            task_type: Type of task for model selection
            priority: Request priority
            **kwargs: Additional request parameters
            
        Returns:
            Configured AI request
        """
        return AIRequest(
            request_id=str(uuid.uuid4()),
            task_type=task_type,
            instruction=instruction,
            priority=priority,
            **kwargs
        )


# Global broker instance
ai_broker = None


def get_ai_broker() -> AIBroker:
    """Get the global AI broker instance"""
    global ai_broker
    if ai_broker is None:
        ai_broker = AIBroker()
    return ai_broker


def init_ai_broker():
    """Initialize and start the AI broker service"""
    broker = get_ai_broker()
    broker.start()
    logger.info("AI Broker initialized and started")
    return broker