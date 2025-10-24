"""
AI Broker Service - Intelligent model orchestration and request management
Manages multiple AI model connections with smart selection, queuing, and context management
"""

import asyncio
import logging
import os
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
            'claude-sonnet-3-5': ModelConfig(
                model_id='claude-sonnet-3-5',
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
            'claude-sonnet-4': ModelConfig(
                model_id='claude-sonnet-4',
                provider='model_garden',
                name='Claude Sonnet 4',
                capabilities=[
                    ModelCapability.REASONING,
                    ModelCapability.CREATIVITY,
                    ModelCapability.SPEED,
                    ModelCapability.ANALYSIS
                ],
                max_tokens=4096,
                cost_per_token=0.00004,
                avg_response_time=6.0,
                max_concurrent_requests=8,
                context_window=200000
            ),
            'gemini-2-5-flash': ModelConfig(
                model_id='gemini-2-5-flash',
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
            TaskType.CODE_GENERATION: ['claude-sonnet-4', 'goose-gemini', 'gpt-4o'],
            TaskType.CODE_REVIEW: ['claude-opus-4', 'claude-sonnet-4', 'gpt-4o'],
            TaskType.DOCUMENTATION: ['goose-gemini', 'claude-opus-4', 'gpt-4o', 'claude-sonnet-4'],
            TaskType.ANALYSIS: ['claude-opus-4', 'gpt-4o', 'claude-sonnet-4'],
            TaskType.CONVERSATION: ['claude-sonnet-4', 'gpt-4o', 'gemini-2-5-flash'],
            TaskType.PLANNING: ['claude-opus-4', 'gpt-4o', 'claude-sonnet-4'],
            TaskType.DEBUGGING: ['claude-sonnet-4', 'goose-gemini', 'gpt-4o'],
            TaskType.TESTING: ['claude-sonnet-4', 'gpt-4o', 'goose-gemini'],
            TaskType.ARCHITECTURE: ['claude-opus-4', 'gpt-4o', 'claude-sonnet-4'],
            TaskType.GENERAL: ['gemini-2-5-flash', 'claude-sonnet-4', 'gpt-4o']
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
            # Check if this is a document analysis request - don't add vector context that might confuse the AI
            instruction_lower = request.instruction.lower()
            if ("analyze" in instruction_lower and "document" in instruction_lower) or \
               ("prd" in instruction_lower) or ("requirements" in instruction_lower) or \
               ("irops" in instruction_lower) or ("irregular operation" in instruction_lower):
                # For document analysis, skip vector context to avoid hallucination
                logger.info(f"Document analysis detected in request {request.request_id} - skipping vector context")
                return None
            
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
    
    def analyze_uploaded_files(self, session_id: str, files: List[Dict[str, Any]], 
                              preferred_model: str = None) -> Dict[str, Any]:
        """
        Analyze uploaded files using AI models for PRD generation
        
        Args:
            session_id: Upload session ID
            files: List of file dictionaries with file_path, file_type, filename
            preferred_model: Preferred AI model (claude-opus-4, gemini-2.5-flash, gpt-4o)
            
        Returns:
            Dictionary with analysis results and metadata
        """
        try:
            import base64
            import os
            from pathlib import Path
            
            logger.info(f"Starting file analysis for session {session_id} with {len(files)} files")
            
            # Prepare files for AI processing
            processed_files = []
            for file_info in files:
                try:
                    file_data = self._prepare_file_for_ai(file_info)
                    if file_data:
                        processed_files.append(file_data)
                except Exception as e:
                    logger.error(f"Failed to prepare file {file_info.get('filename', 'unknown')}: {e}")
                    continue
            
            if not processed_files:
                logger.error(f"No files could be processed for AI analysis in session {session_id}")
                return {
                    'success': False,
                    'error': 'No files could be processed for AI analysis',
                    'model_used': None,
                    'analysis': None
                }
            
            # Select AI model with fallback chain
            model_chain = self._get_model_fallback_chain(preferred_model)
            logger.info(f"Trying models: {model_chain}")
            
            # Try each model in the fallback chain
            for model_id in model_chain:
                try:
                    logger.info(f"Attempting analysis with {model_id}")
                    result = self._execute_file_analysis(model_id, processed_files, session_id)
                    
                    if result['success']:
                        logger.info(f"Analysis successful with {model_id}")
                        return result
                    else:
                        logger.warning(f"Model {model_id} failed: {result.get('error')}")
                        continue
                        
                except Exception as e:
                    logger.error(f"Error with model {model_id}: {e}")
                    continue
            
            # All models failed - use local fallback
            logger.warning("All AI models failed, using local fallback PRD generation")
            return self._generate_fallback_prd(processed_files, session_id)
            
        except Exception as e:
            logger.error(f"File analysis failed for session {session_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'model_used': None,
                'analysis': None
            }
    
    def _generate_fallback_prd(self, files: List[Dict[str, Any]], session_id: str) -> Dict[str, Any]:
        """
        Generate a basic PRD when all AI models are unavailable
        
        Args:
            files: Prepared file data
            session_id: Upload session ID
            
        Returns:
            Fallback PRD analysis result
        """
        try:
            logger.info(f"Generating fallback PRD for session {session_id}")
            
            # Extract basic information from file content
            all_content = ""
            file_names = []
            
            for file_data in files:
                file_names.append(file_data['filename'])
                if 'content' in file_data:
                    content = file_data['content']
                    if isinstance(content, str):
                        all_content += f"\n\n--- {file_data['filename']} ---\n{content[:2000]}"  # Limit content
            
            # Generate basic PRD structure
            fallback_prd = f"""# Product Requirements Document

## Overview
This PRD was generated from the uploaded files when AI services were unavailable. Please review and enhance the content based on your specific requirements.

**Source Files:** {', '.join(file_names)}

## Problem Statement
Based on the uploaded content, this document outlines the requirements for a new product or feature. The specific problem statement should be refined based on stakeholder input and market analysis.

## Target Audience
- Primary users: To be defined based on market research
- Secondary users: To be identified through user interviews
- Stakeholders: Product team, engineering team, business stakeholders

## Goals and Objectives
1. Address the core user needs identified in the source materials
2. Deliver a solution that meets business objectives
3. Ensure technical feasibility and scalability
4. Maintain high standards for user experience

## Functional Requirements
### Core Features
- Feature 1: To be defined based on user needs analysis
- Feature 2: To be specified through requirements gathering
- Feature 3: To be determined through technical assessment

### User Stories
- As a user, I want to accomplish my primary task efficiently
- As a stakeholder, I want to track progress and outcomes
- As an administrator, I want to manage system configuration

## Technical Requirements
### Performance
- Response time: < 2 seconds for core operations
- Availability: 99.9% uptime target
- Scalability: Support for expected user load

### Security
- Data encryption in transit and at rest
- User authentication and authorization
- Compliance with relevant data protection regulations

## Implementation Plan
### Phase 1: Foundation
- Requirements analysis and validation
- Technical architecture design
- Core infrastructure setup

### Phase 2: Development
- Core feature implementation
- Testing and quality assurance
- User acceptance testing

### Phase 3: Launch
- Production deployment
- User training and documentation
- Performance monitoring and optimization

## Next Steps
1. Review and enhance this document with detailed requirements
2. Conduct stakeholder interviews for validation
3. Perform technical feasibility assessment
4. Create detailed implementation timeline

---
*Note: This PRD was auto-generated as a fallback when AI services were unavailable. Please review and customize based on your specific needs.*"""

            # Create structured JSON summary
            fallback_summary = {
                "full_prd": fallback_prd,
                "problem": {
                    "text": "Product requirements need to be defined based on uploaded materials and stakeholder input",
                    "sources": ["S1"]
                },
                "audience": {
                    "text": "Primary and secondary users to be identified through market research and user interviews",
                    "sources": ["S1"]
                },
                "goals": {
                    "items": [
                        "Address core user needs from source materials",
                        "Deliver solution meeting business objectives", 
                        "Ensure technical feasibility and scalability"
                    ],
                    "sources": ["S1", "S1", "S1"]
                },
                "risks": {
                    "items": [
                        "Requirements may need significant refinement",
                        "Technical complexity not fully assessed"
                    ],
                    "sources": ["S1", "S1"]
                },
                "competitive_scan": {
                    "items": [
                        "Competitive analysis needed based on market research",
                        "Feature comparison with existing solutions required"
                    ],
                    "sources": ["S1", "S1"]
                },
                "open_questions": {
                    "items": [
                        "What are the specific user pain points?",
                        "What is the target timeline for delivery?",
                        "What are the key success metrics?"
                    ],
                    "sources": ["S1", "S1", "S1"]
                }
            }
            
            import json
            fallback_json = json.dumps(fallback_summary, indent=2)
            
            return {
                'success': True,
                'analysis': fallback_json,
                'model_used': 'fallback-local',
                'provider': 'local',
                'processing_time': 1.0,
                'tokens_used': 0
            }
            
        except Exception as e:
            logger.error(f"Fallback PRD generation failed: {e}")
            return {
                'success': False,
                'error': f'Fallback PRD generation failed: {str(e)}',
                'model_used': 'fallback-local'
            }
    
    def _prepare_file_for_ai(self, file_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Prepare a single file for AI processing
        
        Args:
            file_info: File information dictionary
            
        Returns:
            Prepared file data or None if preparation failed
        """
        try:
            import base64
            import os
            from pathlib import Path
            
            file_path = file_info['file_path']
            file_type = file_info['file_type'].lower()
            filename = file_info['filename']
            
            # Check if file exists
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return None
            
            # Handle different file types
            if file_type == 'pdf':
                return self._prepare_pdf_file(file_path, filename)
            elif file_type in ['jpg', 'jpeg', 'png', 'gif']:
                return self._prepare_image_file(file_path, filename, file_type)
            elif file_type == 'url':
                return self._prepare_url_content(file_path, filename)
            elif file_type in ['md', 'txt', 'doc', 'docx']:
                return self._prepare_text_file(file_path, filename, file_type)
            else:
                logger.warning(f"Unsupported file type: {file_type}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to prepare file {file_info.get('filename', 'unknown')}: {e}")
            return None
    
    def _prepare_pdf_file(self, file_path: str, filename: str) -> Dict[str, Any]:
        """Prepare PDF file for AI processing - extract text for analysis"""
        try:
            import base64
            
            # First, try to extract text from the PDF for better analysis
            pdf_text = self._extract_pdf_text(file_path)
            
            if pdf_text and len(pdf_text.strip()) > 100:  # If we got meaningful text
                logger.info(f"Successfully extracted {len(pdf_text)} characters from PDF {filename}")
                return {
                    'filename': filename,
                    'file_type': 'pdf_text',  # Mark as extracted text
                    'content': pdf_text,
                    'media_type': 'text/plain',
                    'size': len(pdf_text.encode('utf-8'))
                }
            else:
                # Fallback: encode to base64 (though router may not handle it well)
                logger.warning(f"Could not extract text from PDF {filename}, falling back to base64")
                with open(file_path, 'rb') as f:
                    file_content = f.read()
                
                base64_content = base64.b64encode(file_content).decode('utf-8')
                
                return {
                    'filename': filename,
                    'file_type': 'pdf',
                    'content': base64_content,
                    'media_type': 'application/pdf',
                    'size': len(file_content)
                }
            
        except Exception as e:
            logger.error(f"Failed to prepare PDF {filename}: {e}")
            return None
    
    def _extract_pdf_text(self, file_path: str) -> Optional[str]:
        """Extract text content from a PDF file using various methods"""
        text = None
        
        # Try PyPDF2 first (most common, pure Python)
        try:
            import PyPDF2
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                text_parts = []
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                text = "\n".join(text_parts)
                if text and len(text.strip()) > 100:
                    logger.info(f"Extracted text using PyPDF2: {len(text)} chars")
                    return text
        except ImportError:
            logger.debug("PyPDF2 not available")
        except Exception as e:
            logger.debug(f"PyPDF2 extraction failed: {e}")
        
        # Try pdfplumber (better for tables and complex layouts)
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                text_parts = []
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                text = "\n".join(text_parts)
                if text and len(text.strip()) > 100:
                    logger.info(f"Extracted text using pdfplumber: {len(text)} chars")
                    return text
        except ImportError:
            logger.debug("pdfplumber not available")
        except Exception as e:
            logger.debug(f"pdfplumber extraction failed: {e}")
        
        # Try PyMuPDF/fitz (fastest, best quality)
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(file_path)
            text_parts = []
            for page_num in range(doc.page_count):
                page = doc[page_num]
                page_text = page.get_text()
                if page_text:
                    text_parts.append(page_text)
            doc.close()
            text = "\n".join(text_parts)
            if text and len(text.strip()) > 100:
                logger.info(f"Extracted text using PyMuPDF: {len(text)} chars")
                return text
        except ImportError:
            logger.debug("PyMuPDF not available")
        except Exception as e:
            logger.debug(f"PyMuPDF extraction failed: {e}")
        
        # If all methods failed, return None
        logger.warning(f"All PDF text extraction methods failed for {file_path}")
        return None
    
    def _prepare_image_file(self, file_path: str, filename: str, file_type: str) -> Dict[str, Any]:
        """Prepare image file for AI processing using base64 encoding"""
        try:
            import base64
            
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # Encode to base64 for API transmission
            base64_content = base64.b64encode(file_content).decode('utf-8')
            
            # Map file type to media type
            media_type_map = {
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
                'png': 'image/png',
                'gif': 'image/gif'
            }
            
            return {
                'filename': filename,
                'file_type': file_type,
                'content': base64_content,
                'media_type': media_type_map.get(file_type, 'image/jpeg'),
                'size': len(file_content)
            }
            
        except Exception as e:
            logger.error(f"Failed to prepare image {filename}: {e}")
            return None
    
    def _prepare_url_content(self, file_path: str, filename: str) -> Dict[str, Any]:
        """Prepare URL content for AI processing"""
        try:
            # For URLs, the file_path contains the URL content as text
            with open(file_path, 'r', encoding='utf-8') as f:
                url_content = f.read()
            
            return {
                'filename': filename,
                'file_type': 'url',
                'content': url_content,
                'media_type': 'text/plain',
                'size': len(url_content.encode('utf-8'))
            }
            
        except Exception as e:
            logger.error(f"Failed to prepare URL content {filename}: {e}")
            return None
    
    def _prepare_text_file(self, file_path: str, filename: str, file_type: str) -> Dict[str, Any]:
        """Prepare text-based files (md, txt, doc, docx) for AI processing"""
        try:
            # Handle different text file types
            if file_type in ['md', 'txt']:
                # Plain text files - read directly
                with open(file_path, 'r', encoding='utf-8') as f:
                    text_content = f.read()
            elif file_type in ['doc', 'docx']:
                # Word documents - would need python-docx library
                # For now, treat as plain text (user should convert to PDF)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        text_content = f.read()
                except UnicodeDecodeError:
                    logger.warning(f"Cannot read {file_type} file as text. Please convert to PDF or plain text.")
                    return None
            else:
                logger.warning(f"Unsupported text file type: {file_type}")
                return None
            
            return {
                'filename': filename,
                'file_type': file_type,
                'content': text_content,
                'media_type': 'text/plain',
                'size': len(text_content.encode('utf-8'))
            }
            
        except Exception as e:
            logger.error(f"Failed to prepare text file {filename}: {e}")
            return None
    
    def _get_model_fallback_chain(self, preferred_model: str = None) -> List[str]:
        """
        Get model fallback chain for file analysis
        
        Args:
            preferred_model: Preferred model to try first
            
        Returns:
            List of model IDs in fallback order
        """
        # Default fallback chain preferring Claude first (router-supported IDs)
        default_chain = ['claude-opus-4', 'gemini-2-5-flash', 'gpt-4o', 'claude-sonnet-4']
        
        if preferred_model and preferred_model in self.model_selector.model_configs:
            # Put preferred model first, then add others
            chain = [preferred_model]
            chain.extend([m for m in default_chain if m != preferred_model])
            return chain
        
        return default_chain
    
    def _execute_file_analysis(self, model_id: str, files: List[Dict[str, Any]], 
                              session_id: str) -> Dict[str, Any]:
        """
        Execute file analysis with a specific AI model
        
        Args:
            model_id: AI model to use
            files: Prepared file data
            session_id: Upload session ID
            
        Returns:
            Analysis result dictionary
        """
        try:
            model_config = self.model_selector.model_configs.get(model_id)
            if not model_config:
                return {
                    'success': False,
                    'error': f'Model {model_id} not found',
                    'model_used': model_id
                }
            
            # Use section-by-section approach for comprehensive PRDs
            try:
                result = self._generate_comprehensive_prd_sections(model_id, model_config, files)
            except Exception as e:
                logger.error(f"Section-by-section PRD generation failed: {e}")
                # Fallback to original approach
                prompt = self._create_prd_generation_prompt(files)
                
                # Execute based on provider
                if model_config.provider == 'model_garden':
                    result = self._execute_model_garden_analysis(model_id, prompt, files)
                else:
                    return {
                        'success': False,
                        'error': f'Provider {model_config.provider} not supported for file analysis',
                        'model_used': model_id
                    }
            
            if result['success']:
                return {
                    'success': True,
                    'analysis': result['content'],
                    'model_used': model_id,
                    'provider': model_config.provider,
                    'processing_time': result.get('processing_time', 0),
                    'tokens_used': result.get('tokens_used', 0)
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Unknown error'),
                    'model_used': model_id
                }
                
        except Exception as e:
            logger.error(f"File analysis execution failed with {model_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'model_used': model_id
            }
    
    def _create_section_based_prd_prompt(self, files: List[Dict[str, Any]], section: str = None, existing_content: str = None) -> str:
        """
        Create section-specific PRD generation prompt for comprehensive documents
        
        Args:
            files: List of prepared file data
            section: Specific section to generate ('product_spec', 'technical_spec', 'implementation', or None for overview)
            existing_content: Previously generated content for context
            
        Returns:
            Section-specific comprehensive PRD generation prompt
        """
        file_descriptions = []
        for i, file_data in enumerate(files, 1):
            file_descriptions.append(f"S{i}: {file_data['filename']} ({file_data['file_type'].upper()})")
        
        files_summary = "\n".join(file_descriptions)
        
        # Add actual file content to the prompt (ensure sufficient context for comprehensive PRD)
        MAX_PER_FILE_CHARS = 25000
        file_content_sections = []
        for i, file_data in enumerate(files, 1):
            fname = file_data.get('filename', f'S{i}')
            ftype = (file_data.get('file_type') or 'unknown').lower()
            if ftype in ['pdf', 'jpg', 'jpeg', 'png', 'gif']:
                # Do NOT inline binary/base64 content; it explodes token usage
                file_content_sections.append(f"""
**SOURCE FILE S{i}: {fname}**
Type: {ftype.upper()}
Content not inlined (binary). Use only textual sources and metadata above.
""")
            else:
                text = str(file_data.get('content', ''))
                if len(text) > MAX_PER_FILE_CHARS:
                    sliced = text[:MAX_PER_FILE_CHARS]
                    file_content_sections.append(f"""
**SOURCE FILE S{i}: {fname}**
Type: {ftype.upper()}
Content: {sliced}
[Content truncated at {MAX_PER_FILE_CHARS} characters]
""")
                else:
                    file_content_sections.append(f"""
**SOURCE FILE S{i}: {fname}**
Type: {ftype.upper()}
Content: {text}
""")
        
        files_content = "\n".join(file_content_sections)
        
        # Context from previous sections if building incrementally
        context_section = ""
        if existing_content:
            context_section = f"""
**PREVIOUSLY GENERATED CONTENT FOR CONTEXT:**
{existing_content[:5000]}  # Limit context to avoid token overflow
"""

        if section == "product_spec":
            return self._create_product_specification_prompt(files_summary, files_content, context_section)
        elif section == "technical_spec":
            return self._create_technical_specification_prompt(files_summary, files_content, context_section)
        elif section == "implementation":
            return self._create_implementation_plan_prompt(files_summary, files_content, context_section)
        else:
            # Generate overview and initial sections
            return self._create_overview_prompt(files_summary, files_content)

    def _create_product_specification_prompt(self, files_summary: str, files_content: str, context: str) -> str:
        """Create focused prompt for Product Specification section"""
        return f"""You are a Senior Product Manager creating the PRODUCT SPECIFICATION section of a comprehensive PRD. Generate ONLY the Product Specification section with maximum detail.

**SOURCE FILES:**
{files_summary}

{files_content}

{context}

**GENERATE ONLY THE PRODUCT SPECIFICATION SECTION WITH:**

1. **Introduction & Vision** (500+ words)
   - Comprehensive problem statement with market context
   - Detailed vision statement with success metrics
   - Business case with ROI projections

2. **Target Audience & User Personas** (2000+ words)
   - 8-12 detailed user personas, each with:
   - Complete demographic profiles (300+ words each)
   - Comprehensive background stories (2-3 paragraphs each)
   - 5-8 detailed goals per persona with business context
   - Pain points with current solutions
   - Workflow descriptions and day-in-the-life scenarios
   - Success criteria and KPIs for each persona

3. **User Stories & Use Cases** (2000+ words)
   - 30-50 comprehensive user stories with:
   - Complete context and business rationale
   - Detailed acceptance criteria (3-5 criteria each)
   - Priority levels (P0, P1, P2) with business justification
   - Business value and impact assessment
   - Dependencies and prerequisites
   - Success metrics and measurement criteria

4. **Functional Requirements** (1500+ words)
   - Exhaustive functional requirements with:
   - Numbered and sub-numbered hierarchical structure
   - Detailed specifications for each feature
   - Integration requirements with existing systems
   - Performance specifications and benchmarks
   - Security and compliance requirements
   - Accessibility requirements (WCAG compliance)

**REQUIREMENTS:**
- Each persona must be 300+ words with detailed background
- Each user story must have complete acceptance criteria
- Include specific metrics, KPIs, and success measurements
- Reference source documents extensively
- Use proper markdown formatting with clear hierarchy
- Generate at least 8,000 words total for this section

Return ONLY the Product Specification section content in markdown format."""

    def _create_technical_specification_prompt(self, files_summary: str, files_content: str, context: str) -> str:
        """Create focused prompt for Technical Specification section"""
        return f"""You are a Senior Technical Architect creating the TECHNICAL SPECIFICATION section of a comprehensive PRD. Generate ONLY the Technical Specification section with maximum detail.

**SOURCE FILES:**
{files_summary}

{files_content}

{context}

**GENERATE ONLY THE TECHNICAL SPECIFICATION SECTION WITH:**

1. **System Overview** (800+ words)
   - Comprehensive architecture description
   - Technology stack with detailed justifications
   - Scalability and performance requirements
   - Security architecture and compliance

2. **System Architecture** (1200+ words)
   - Detailed component diagrams with Mermaid
   - Service-oriented architecture description
   - Data flow diagrams with Mermaid
   - Integration patterns and APIs
   - Include multiple Mermaid diagrams:

```mermaid
flowchart TD
    A[System Component A] --> B[Component B]
    B --> C[Database]
    C --> D[External API]
```

3. **Database Design** (800+ words)
   - Complete entity relationship diagram with Mermaid:

```mermaid
erDiagram
    USERS ||--|{{ PROJECTS : creates
    PROJECTS ||--|{{ TASKS : contains
    TASKS ||--|{{ COMMENTS : has
```

   - Detailed schema specifications
   - Data modeling decisions and rationale
   - Performance and indexing strategies

4. **API Specifications** (800+ words)
   - Complete API endpoint documentation
   - Request/response schemas with examples
   - Authentication and authorization flows
   - Rate limiting and caching strategies

5. **Security Requirements** (600+ words)
   - Comprehensive security framework
   - Data protection and privacy measures
   - Authentication and authorization systems
   - Compliance requirements (SOC2, GDPR, etc.)

6. **Performance & Scalability** (600+ words)
   - Detailed performance benchmarks
   - Scalability planning and auto-scaling
   - Monitoring and alerting strategies
   - Disaster recovery and backup plans

**REQUIREMENTS:**
- Include at least 4 comprehensive Mermaid diagrams
- Provide detailed technical justifications
- Include specific performance metrics and benchmarks
- Reference architecture best practices
- Generate at least 8,000 words total for this section

Return ONLY the Technical Specification section content in markdown format with Mermaid diagrams."""

    def _create_implementation_plan_prompt(self, files_summary: str, files_content: str, context: str) -> str:
        """Create focused prompt for Implementation Plan section"""
        return f"""You are a Senior Engineering Manager creating the IMPLEMENTATION PLAN section of a comprehensive PRD. Generate ONLY the Implementation Plan section with maximum detail.

**SOURCE FILES:**
{files_summary}

{files_content}

{context}

**GENERATE ONLY THE IMPLEMENTATION PLAN SECTION WITH:**

1. **Development Phases** (1000+ words)
   - Detailed phase breakdown with milestones
   - Phase dependencies and critical path analysis
   - Resource allocation and team assignments
   - Timeline estimates with buffer time

2. **Sprint Planning** (800+ words)
   - 8-12 detailed sprints with specific deliverables
   - Sprint goals and success criteria
   - Story point estimates and velocity planning
   - Risk mitigation strategies per sprint

3. **Team Structure & Roles** (600+ words)
   - Detailed team composition requirements
   - Role definitions and responsibilities
   - Skill requirements and hiring needs
   - Communication and collaboration protocols

4. **Technology Implementation** (800+ words)
   - Detailed technology stack setup
   - Development environment configuration
   - CI/CD pipeline implementation
   - Testing strategy and quality assurance

5. **Risk Assessment & Mitigation** (600+ words)
   - Comprehensive risk analysis with probability/impact matrix
   - Detailed mitigation strategies
   - Contingency planning
   - Dependencies and external risks

6. **Success Metrics & KPIs** (400+ words)
   - Detailed success criteria for each phase
   - Key performance indicators with targets
   - Monitoring and reporting framework
   - Go/no-go criteria for each phase

**REQUIREMENTS:**
- Include detailed Gantt chart representation
- Provide specific timeline estimates
- Include resource requirements and budget considerations
- Reference industry best practices
- Generate at least 6,000 words total for this section

Return ONLY the Implementation Plan section content in markdown format."""

    def _create_overview_prompt(self, files_summary: str, files_content: str) -> str:
        """Create focused prompt for PRD overview and initial sections"""
        return f"""You are a Senior Product Manager creating the OVERVIEW and PROJECT INTRODUCTION for a comprehensive PRD. Generate a detailed project overview and introduction.

**SOURCE FILES:**
{files_summary}

{files_content}

**GENERATE THE FOLLOWING SECTIONS:**

# [Project Name Based on Source Documents]

## Executive Summary (400+ words)
- Comprehensive project overview
- Business case and market opportunity
- Key success metrics and ROI projections
- Strategic importance and competitive advantage

## Project Scope (300+ words)
- Detailed scope definition
- In-scope and out-of-scope items
- Success criteria and acceptance criteria
- Assumptions and constraints

## Business Context (400+ words)
- Market analysis and competitive landscape
- Current pain points and opportunity gaps
- Business goals and strategic objectives
- Expected business impact and outcomes

**REQUIREMENTS:**
- Extract project name and context from source documents
- Provide comprehensive business justification
- Include specific metrics and success criteria
- Generate at least 1,500 words total
- Use professional product management language

Return the overview sections in markdown format."""

    def _create_prd_generation_prompt(self, files: List[Dict[str, Any]]) -> str:
        """
        Create comprehensive PRD generation prompt using the full PRD template structure
        
        Args:
            files: List of prepared file data
            
        Returns:
            Comprehensive PRD generation prompt that creates detailed, complete PRDs
        """
        file_descriptions = []
        for i, file_data in enumerate(files, 1):
            file_descriptions.append(f"S{i}: {file_data['filename']} ({file_data['file_type'].upper()})")
        
        files_summary = "\n".join(file_descriptions)
        
        # Add actual file content to the prompt (ensure sufficient context for comprehensive PRD)
        MAX_PER_FILE_CHARS = 25000
        file_content_sections = []
        for i, file_data in enumerate(files, 1):
            fname = file_data.get('filename', f'S{i}')
            ftype = (file_data.get('file_type') or 'unknown').lower()
            if ftype in ['pdf', 'jpg', 'jpeg', 'png', 'gif']:
                # Do NOT inline binary/base64 content; it explodes token usage
                file_content_sections.append(f"""
**SOURCE FILE S{i}: {fname}**
Type: {ftype.upper()}
Content not inlined (binary). Use only textual sources and metadata above.
""")
            else:
                text = str(file_data.get('content', ''))
                if len(text) > MAX_PER_FILE_CHARS:
                    sliced = text[:MAX_PER_FILE_CHARS]
                    file_content_sections.append(f"""
**SOURCE FILE S{i}: {fname}**
Content (truncated to {MAX_PER_FILE_CHARS} chars):
{sliced}
... [truncated]
""")
                else:
                    file_content_sections.append(f"""
**SOURCE FILE S{i}: {fname}**
Content:
{text}
""")
        
        files_content = "\n".join(file_content_sections)
        
        # Log prompt generation for debugging
        logger.info(f"Creating PRD generation prompt with {len(files)} files")
        logger.info(f"Prompt will include Mermaid diagrams: True")
        
        prompt = f"""You are a Senior Product Manager and Technical Architect with 15+ years of experience creating production-grade documentation. Based on the uploaded documents, you must create a COMPREHENSIVE Product Requirements Document (PRD) that matches the depth and structure of professional enterprise PRDs.

**SOURCE FILES:**
{files_summary}

{files_content}

**MANDATORY REQUIREMENTS - YOUR RESPONSE MUST MEET ALL OF THESE:**

1. **MINIMUM LENGTH REQUIREMENT**: Your response must be AT LEAST 25,000 characters long (approximately 50+ pages) to be considered complete. This is not optional.

2. **REQUIRED COMPREHENSIVE SECTIONS**: You must include ALL of these sections with extensive detail:
   - Product Specification (5000+ words)
   - Technical Specification (5000+ words) 
   - Implementation Plan (3000+ words)
   - Multiple detailed Mermaid diagrams (flowcharts, ERD, class diagrams, architecture diagrams)

3. **USER PERSONAS**: Create 8-12 detailed user personas, each with:
   - Comprehensive background (2-3 paragraphs each)
   - Detailed goals (5-8 goals per persona)
   - Pain points and motivations
   - Workflow descriptions

4. **USER STORIES**: Generate 30-50 user stories with:
   - Complete context and rationale
   - Detailed acceptance criteria (3-5 criteria each)
   - Priority levels and business value

5. **FUNCTIONAL REQUIREMENTS**: Provide exhaustive functional requirements with:
   - Numbered and sub-numbered items
   - Detailed specifications for each feature
   - Integration requirements
   - Performance specifications

6. **TECHNICAL DEPTH**: Include comprehensive technical details:
   - System architecture with detailed explanations
   - Database schemas and relationships
   - API specifications
   - Security requirements
   - Scalability considerations

7. **IMPLEMENTATION DETAILS**: Provide detailed implementation planning:
   - Phase-by-phase breakdown
   - Timeline estimates
   - Resource requirements
   - Risk assessments and mitigations

8. **NO PLACEHOLDERS ALLOWED**: Every section must contain actual, substantive content. No "[continued...]", "[more details...]", or similar placeholders.

**CONTENT QUALITY STANDARDS:**
- Each major section: minimum 1000 words
- Each subsection: minimum 200 words  
- User personas: minimum 300 words each
- Technical specifications: include actual code examples, schemas, and architectural details
- All recommendations must be backed by specific reasoning from the source documents

**STRUCTURAL REQUIREMENTS:**
- Use proper markdown formatting with clear hierarchical headers
- Include multiple Mermaid diagrams throughout the document
- Provide detailed tables for requirements, features, and specifications
- Include comprehensive cross-references between sections

**GENERATE A COMPREHENSIVE PRD WITH THIS EXACT STRUCTURE:**

# Project

## Product Specification

### Introduction & Vision
Write at least 3-4 detailed paragraphs covering:
- A comprehensive overview of what the system/product is and its core purpose
- The specific business problem being solved and why it matters
- The vision statement describing the future state when this product is successful
- The strategic importance and expected impact on the organization or market
- How this product aligns with broader business objectives and strategy

### Target Audience & User Personas
Provide a detailed introduction paragraph about the target market, then create at least 5-7 comprehensive personas. Each persona must include:

#### [Specific Role/Title - e.g., Operations Manager, System Administrator, End User, etc.]
**Background & Context:** Write 2-3 sentences describing their professional background, experience level, and typical work environment.

**Demographics:** Age range, education level, technical proficiency, years of experience in role.

**Responsibilities:** List 4-5 key job responsibilities relevant to this product.

**Pain Points:** Describe 3-4 specific challenges they currently face that this product will address.

**Goals & Motivations:**
- Primary goal: What is their main objective when using this product?
- Efficiency goals: How do they want to improve their workflow?
- Professional goals: What career or performance objectives does this help achieve?
- Personal motivations: What drives them to adopt new solutions?

**Preferred Features:** List 3-4 features that would be most valuable to this persona.

**Success Criteria:** How will they measure success with this product?

[Repeat for each additional persona with equal detail]

### User Stories / Use Cases
Provide an introductory paragraph about the user journey, then list at least 20-30 detailed user stories organized by theme:

#### Core Functionality Stories
- As a [specific role], I want to [specific action with context], so that [detailed business benefit and outcome].
- Include acceptance criteria for each story
- Add priority level (High/Medium/Low) and estimated complexity

#### Integration & Workflow Stories
[Continue with 6-8 stories about system integration and workflow automation]

#### Reporting & Analytics Stories
[Continue with 5-7 stories about data, reporting, and insights]

#### Administration & Configuration Stories
[Continue with 5-7 stories about system setup and management]

### Functional Requirements
Provide comprehensive requirements with detailed descriptions:

#### [Major Feature Area 1 - be specific, e.g., "User Authentication & Access Control"]
##### Overview
Write 2-3 sentences describing this feature area and its importance.

##### Detailed Requirements
1. **[Specific Requirement Name]**
   - Description: Full explanation of the requirement (2-3 sentences)
   - Business Justification: Why this is needed
   - Technical Specifications: Any technical details or constraints
   - Dependencies: Related requirements or systems
   - Acceptance Criteria: How to verify this requirement is met

2. **[Next Requirement]**
   [Continue with same level of detail]

[Include at least 8-10 detailed requirements per feature area]

#### [Major Feature Area 2]
[Repeat structure with equal detail]

#### [Major Feature Area 3]
[Repeat structure with equal detail]

### Non-Functional Requirements

#### Performance Requirements
- **Response Time:** Specify exact metrics (e.g., "Page load time must be under 2 seconds for 95% of requests")
- **Throughput:** Define transaction volumes (e.g., "System must handle 10,000 concurrent users")
- **Resource Utilization:** Specify CPU, memory, and storage constraints
- **Scalability:** Define how the system should scale (vertical/horizontal) and growth projections
- **Peak Load Handling:** Describe behavior under peak conditions

#### Reliability & Availability
- **Uptime Requirements:** Specify exact SLA (e.g., "99.9% uptime, allowing for 8.76 hours downtime per year")
- **Mean Time Between Failures (MTBF):** Target reliability metrics
- **Mean Time To Recovery (MTTR):** Maximum acceptable recovery time
- **Backup & Recovery:** RPO and RTO requirements
- **Redundancy:** Failover and high availability requirements

#### Security Requirements
- **Authentication:** Multi-factor authentication, SSO requirements, password policies
- **Authorization:** Role-based access control, permission granularity
- **Data Encryption:** At-rest and in-transit encryption standards
- **Audit Logging:** What events must be logged, retention periods
- **Compliance:** Specific regulations (GDPR, HIPAA, SOC2, etc.)
- **Vulnerability Management:** Security scanning and patching requirements

#### Usability Requirements
- **User Interface Standards:** Design system compliance, accessibility standards (WCAG 2.1 AA)
- **Training Requirements:** Maximum training time for new users
- **Error Handling:** User-friendly error messages and recovery paths
- **Documentation:** User guides, API documentation, help system requirements
- **Localization:** Language and regional requirements

### Scope Definition

#### In Scope - MVP Release
Provide detailed bullet points (at least 10-15 items) of what IS included:
- Be specific about features, integrations, and capabilities
- Include any data migration or setup requirements
- Specify which user personas are supported in MVP
- Define geographical or organizational boundaries

#### Out of Scope - Future Releases
Clearly define what is NOT included in MVP (at least 8-10 items):
- Features planned for future phases
- Integrations deferred to later
- Advanced capabilities held for v2
- Any explicit exclusions important to clarify

### Success Metrics & KPIs
Define specific, measurable success criteria:

#### Business Metrics
- Revenue impact: Specific targets and timeframes
- Cost reduction: Quantified savings expected
- Efficiency gains: Time saved, process improvements
- Customer satisfaction: NPS, CSAT targets

#### Operational Metrics
- Adoption rate: User activation and engagement targets
- Usage patterns: Daily/monthly active users, feature utilization
- Performance metrics: System performance against benchmarks
- Quality metrics: Error rates, incident frequency

#### Leading Indicators
- Early warning signs of success or failure
- Milestone-based progress tracking
- Risk indicators to monitor

### Assumptions & Dependencies

#### Key Assumptions
List at least 8-10 assumptions with explanations:
- Technical assumptions about infrastructure or platforms
- Business assumptions about resources, budget, or timeline
- Market assumptions about user needs or competitive landscape
- Organizational assumptions about support and adoption

#### Critical Dependencies
Identify at least 5-7 dependencies with risk assessment:
- External system dependencies and integration points
- Third-party services or vendors
- Internal team or resource dependencies
- Regulatory or compliance dependencies
- Timeline dependencies and critical path items

### Risks and Mitigation Strategies

#### Technical Risks
1. **Risk:** Detailed description of the risk
   - **Probability:** High/Medium/Low
   - **Impact:** Critical/Major/Minor
   - **Mitigation Strategy:** Specific actions to reduce or eliminate risk
   - **Contingency Plan:** What to do if risk materializes

[Include at least 4-5 technical risks]

#### Business Risks
[Include at least 3-4 business risks with same format]

#### Operational Risks
[Include at least 3-4 operational risks with same format]

## Technical Specification

### System Overview
Write 2-3 comprehensive paragraphs describing:
- The overall technical architecture and system design
- Key technical components and their interactions
- Technology stack choices and rationale
- Deployment architecture and infrastructure requirements

### Architectural Drivers

#### Technical Goals
- List 4-5 specific technical objectives the architecture must achieve
- Include performance, scalability, maintainability goals
- Define technical success criteria

#### Technical Constraints
- Identify 3-4 technical limitations or boundaries
- Specify technology stack requirements
- Define integration constraints
- Resource or budget limitations

### High-Level Architecture
Provide detailed description of the system architecture including:
- Architectural pattern (microservices, monolith, serverless, etc.)
- Component separation and boundaries
- Communication patterns between components
- Data flow and processing pipeline

#### System Components Diagram
```mermaid
flowchart TB
    subgraph "External Systems"
        ExtAPI[External APIs]
        ThirdParty[Third Party Services]
        UserDevices[User Devices]
    end
    
    subgraph "Application Layer"
        WebApp[Web Application<br/>React/Angular/Vue]
        MobileApp[Mobile Apps<br/>iOS/Android]
        API[API Gateway<br/>REST/GraphQL]
    end
    
    subgraph "Business Logic Layer"
        AuthService[Authentication Service]
        CoreService[Core Business Service]
        NotificationService[Notification Service]
        AnalyticsService[Analytics Service]
    end
    
    subgraph "Data Layer"
        Database[(Primary Database<br/>PostgreSQL/MySQL)]
        Cache[(Cache Layer<br/>Redis/Memcached)]
        Queue[Message Queue<br/>RabbitMQ/Kafka]
        Storage[File Storage<br/>S3/Blob]
    end
    
    UserDevices --> WebApp
    UserDevices --> MobileApp
    WebApp --> API
    MobileApp --> API
    API --> AuthService
    API --> CoreService
    CoreService --> Database
    CoreService --> Cache
    CoreService --> Queue
    CoreService --> NotificationService
    NotificationService --> ExtAPI
    AnalyticsService --> Database
    Queue --> AnalyticsService
    CoreService --> Storage
    ThirdParty --> CoreService
```

### Data Architecture and Models
Describe the data architecture strategy:
- Database technology choices and rationale
- Data storage patterns (SQL vs NoSQL)
- Data partitioning and sharding strategy
- Backup and recovery approach

#### Entity Relationship Diagram (ERD)
```mermaid
erDiagram
    USERS ||--o{{ USER_PROFILES : has
    USERS ||--o{{ USER_SESSIONS : creates
    USERS ||--o{{ USER_ROLES : assigned
    USER_ROLES ||--o{{ PERMISSIONS : contains
    USERS ||--o{{ PROJECTS : owns
    PROJECTS ||--o{{ TASKS : contains
    PROJECTS ||--o{{ DOCUMENTS : includes
    TASKS ||--o{{ TASK_ASSIGNMENTS : has
    USERS ||--o{{ TASK_ASSIGNMENTS : assigned_to
    TASKS ||--o{{ COMMENTS : has
    USERS ||--o{{ COMMENTS : writes
    PROJECTS ||--o{{ PROJECT_MEMBERS : has
    USERS ||--o{{ PROJECT_MEMBERS : is
    
    USERS {{
        uuid id PK "Primary Key"
        string email UK "Unique Email"
        string password_hash
        string first_name
        string last_name
        timestamp created_at
        timestamp updated_at
        boolean is_active
        boolean is_verified
    }}
    
    USER_PROFILES {{
        uuid id PK
        uuid user_id FK "Foreign Key to Users"
        string avatar_url
        string phone
        string timezone
        json preferences
        text bio
    }}
    
    PROJECTS {{
        uuid id PK
        string name
        text description
        uuid owner_id FK
        string status
        date start_date
        date end_date
        json metadata
        timestamp created_at
    }}
    
    TASKS {{
        uuid id PK
        uuid project_id FK
        string title
        text description
        string priority
        string status
        date due_date
        integer estimated_hours
        integer actual_hours
    }}
    
    DOCUMENTS {{
        uuid id PK
        uuid project_id FK
        string document_type
        string title
        text content
        string version
        uuid created_by FK
        timestamp created_at
    }}
```

### Component Architecture
Describe the internal component structure:
- Service layer architecture
- Business logic organization
- API design patterns
- Error handling strategy

#### Class/Component Diagram
```mermaid
classDiagram
    class BaseController {{
        <<abstract>>
        #logger: Logger
        #validator: Validator
        +handleRequest(request): Response
        +validateInput(data): boolean
        #logError(error): void
    }}
    
    class UserController {{
        -userService: UserService
        -authService: AuthService
        +createUser(userData): User
        +getUser(userId): User
        +updateUser(userId, data): User
        +deleteUser(userId): boolean
        +authenticate(credentials): Token
    }}
    
    class ProjectController {{
        -projectService: ProjectService
        -permissionService: PermissionService
        +createProject(projectData): Project
        +getProject(projectId): Project
        +updateProject(projectId, data): Project
        +getProjectMembers(projectId): List~User~
        +addMember(projectId, userId): boolean
    }}
    
    class UserService {{
        <<service>>
        -userRepository: UserRepository
        -cacheService: CacheService
        -eventBus: EventBus
        +createUser(data): User
        +findById(id): User
        +findByEmail(email): User
        +updateUser(id, data): User
        +validatePassword(user, password): boolean
        -hashPassword(password): string
        -publishUserEvent(event): void
    }}
    
    class ProjectService {{
        <<service>>
        -projectRepository: ProjectRepository
        -taskService: TaskService
        -notificationService: NotificationService
        +createProject(data): Project
        +getProjectById(id): Project
        +updateProject(id, data): Project
        +assignMember(projectId, userId): boolean
        +getProjectStats(projectId): Stats
    }}
    
    class UserRepository {{
        <<repository>>
        -database: Database
        +create(userData): User
        +findById(id): User
        +findByEmail(email): User
        +update(id, data): User
        +delete(id): boolean
        +findAll(filters): List~User~
    }}
    
    BaseController <|-- UserController
    BaseController <|-- ProjectController
    UserController --> UserService
    UserController --> AuthService
    ProjectController --> ProjectService
    ProjectController --> PermissionService
    UserService --> UserRepository
    UserService --> CacheService
    UserService --> EventBus
    ProjectService --> ProjectRepository
    ProjectService --> TaskService
    ProjectService --> NotificationService
```

### API Design

#### REST API Endpoints
Define key API endpoints with methods and descriptions:
- Authentication endpoints (login, logout, refresh)
- Resource CRUD endpoints
- Specialized business logic endpoints
- Webhook endpoints

#### Data Flow Diagram
```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant API as API Gateway
    participant Auth as Auth Service
    participant BS as Business Service
    participant DB as Database
    participant Cache as Cache
    participant Queue as Message Queue
    
    U->>F: User Action
    F->>API: API Request
    API->>Auth: Validate Token
    Auth->>Cache: Check Session
    Cache-->>Auth: Session Data
    Auth-->>API: Authorized
    API->>BS: Process Request
    BS->>Cache: Check Cache
    Cache-->>BS: Cache Miss
    BS->>DB: Query Data
    DB-->>BS: Return Data
    BS->>Cache: Update Cache
    BS->>Queue: Publish Event
    BS-->>API: Response Data
    API-->>F: JSON Response
    F-->>U: Update UI
    
    Note over Queue: Async Processing
    Queue->>BS: Process Event
    BS->>DB: Update Analytics
```

### User Interface Architecture

#### UI Component Hierarchy
```mermaid
graph TD
    App[Application Root]
    App --> Layout[Layout Component]
    Layout --> Header[Header/Navigation]
    Layout --> Main[Main Content Area]
    Layout --> Sidebar[Sidebar]
    
    Header --> UserMenu[User Menu]
    Header --> Notifications[Notifications]
    Header --> Search[Global Search]
    
    Main --> Router[Router/Routes]
    Router --> Dashboard[Dashboard View]
    Router --> Projects[Projects View]
    Router --> Settings[Settings View]
    
    Dashboard --> Widgets[Dashboard Widgets]
    Projects --> ProjectList[Project List]
    Projects --> ProjectDetail[Project Detail]
    ProjectDetail --> Tasks[Task Management]
    ProjectDetail --> Documents[Document Management]
    
    Sidebar --> Navigation[Navigation Menu]
    Sidebar --> QuickActions[Quick Actions]
```

### Security Architecture

#### Security Layers
Describe the multi-layered security approach:
- Authentication mechanisms (OAuth, JWT, SSO)
- Authorization and RBAC implementation
- Data encryption (at-rest and in-transit)
- API security (rate limiting, CORS, CSP)
- Audit logging and monitoring

#### Authentication Flow
```mermaid
stateDiagram-v2
    [*] --> Unauthenticated
    Unauthenticated --> Login: User Credentials
    Login --> Validating: Submit
    Validating --> MFA: Valid Credentials
    Validating --> Login: Invalid
    MFA --> Authenticated: MFA Success
    MFA --> Login: MFA Failure
    Authenticated --> Active: Token Valid
    Active --> RefreshToken: Token Expiring
    RefreshToken --> Active: Refresh Success
    RefreshToken --> Login: Refresh Failed
    Active --> Logout: User Action
    Logout --> [*]
```

### Deployment Architecture

#### Infrastructure Diagram
```mermaid
flowchart LR
    subgraph "Internet"
        Users[Users]
        CDN[CDN/CloudFlare]
    end
    
    subgraph "Cloud Provider"
        subgraph "Network Layer"
            LB[Load Balancer]
            WAF[Web Application Firewall]
        end
        
        subgraph "Application Tier"
            Web1[Web Server 1]
            Web2[Web Server 2]
            Web3[Web Server 3]
        end
        
        subgraph "Service Tier"
            App1[App Service 1]
            App2[App Service 2]
            Worker[Background Workers]
        end
        
        subgraph "Data Tier"
            PrimaryDB[(Primary DB)]
            ReplicaDB[(Replica DB)]
            CacheCluster[Cache Cluster]
            QueueService[Message Queue]
        end
        
        subgraph "Storage"
            ObjectStorage[Object Storage]
            Backups[Backup Storage]
        end
    end
    
    Users --> CDN
    CDN --> WAF
    WAF --> LB
    LB --> Web1
    LB --> Web2
    LB --> Web3
    Web1 --> App1
    Web2 --> App1
    Web3 --> App2
    App1 --> PrimaryDB
    App2 --> PrimaryDB
    PrimaryDB --> ReplicaDB
    App1 --> CacheCluster
    App2 --> CacheCluster
    App1 --> QueueService
    Worker --> QueueService
    Worker --> PrimaryDB
    App1 --> ObjectStorage
    PrimaryDB --> Backups
```

### Testing Strategy
Define comprehensive testing approach:
- Unit testing coverage targets (80%+)
- Integration testing scenarios
- Performance testing benchmarks
- Security testing requirements
- User acceptance testing criteria

### Implementation Plan

#### Phase 1: Foundation (Weeks 1-4)
- Set up development environment and CI/CD pipeline
- Implement core database schema and models
- Build authentication and authorization framework
- Create basic API structure and documentation
- Deliverables: Working authentication, base API, database setup

#### Phase 2: Core Features (Weeks 5-12)
- Implement primary business logic and services
- Build essential UI components and views
- Integrate third-party services
- Implement caching and performance optimizations
- Deliverables: Functional MVP with core features

#### Phase 3: Enhancement & Testing (Weeks 13-16)
- Add advanced features and analytics
- Conduct comprehensive testing
- Performance optimization and security hardening
- Documentation and training materials
- Deliverables: Production-ready system

#### Phase 4: Deployment & Launch (Weeks 17-18)
- Production environment setup
- Data migration and system cutover
- User training and onboarding
- Post-launch monitoring and support
- Deliverables: Live system with support structure

**STRICT OUTPUT FORMAT (CRITICAL):**
- Output MUST be a single JSON object only.
- Do NOT include any prose before or after the JSON.
- Do NOT wrap the JSON in code fences or markdown.
- Escape all newlines in the `full_prd` string as `\\n`.

**RESPOND WITH THIS JSON STRUCTURE EXACTLY:**

{{
  "full_prd": "[The complete comprehensive PRD content above, properly escaped for JSON]",
  "problem": {{
    "text": "[Extract the actual problem statement from the documents]",
    "sources": ["S1"]
  }},
  "audience": {{
    "text": "[Extract the actual target audience from the documents]", 
    "sources": ["S1"]
  }},
  "goals": {{
    "items": [
      "[Extract actual goal 1 from the documents]",
      "[Extract actual goal 2 from the documents]", 
      "[Extract actual goal 3 from the documents]"
    ],
    "sources": ["S1", "S1", "S1"]
  }},
  "risks": {{
    "items": [
      "[Extract actual risk 1 from the documents]",
      "[Extract actual risk 2 from the documents]"
    ],
    "sources": ["S1", "S1"] 
  }},
  "competitive_scan": {{
    "items": [
      "[Extract actual competitive insight 1 from the documents]",
      "[Extract actual competitive insight 2 from the documents]"
    ],
    "sources": ["S1", "S1"]
  }},
  "open_questions": {{
    "items": [
      "[Generate actual question 1 based on gaps in the documents]",
      "[Generate actual question 2 based on gaps in the documents]",
      "[Generate actual question 3 based on gaps in the documents]"
    ],
    "sources": ["S1", "S1", "S1"]
  }}
}}

**IMPORTANT:** 
- Base your analysis entirely on the actual document content
- Generate a COMPLETE, DETAILED PRD with ALL sections fully written out
- Include all sections: Product Specification, Technical Specification, and Implementation Plan
- Write REAL CONTENT for every section - no placeholders or summaries
- The full_prd field should contain the complete comprehensive document
- The summary fields (problem, audience, goals, etc.) are for UI display only"""

        return prompt

    def _clean_truncation_messages(self, content: str) -> str:
        """Remove common truncation messages that Claude adds when content is cut off"""
        if not content:
            return content
            
        # List of common truncation patterns Claude uses
        truncation_patterns = [
            "[Content continues in next response due to length limits...]",
            "[Continued in next response due to length limits...]",
            "[Content continues due to length limits...]",
            "[Response continues in next message...]",
            "[Continuing in next response...]",
            "[More content follows in next response...]",
            "...[Content continues in next response due to length limits]...",
            "...[Continued due to length limits]...",
        ]
        
        cleaned_content = content.strip()
        for pattern in truncation_patterns:
            cleaned_content = cleaned_content.replace(pattern, "").strip()
            
        return cleaned_content

    def _generate_comprehensive_prd_sections(self, model_id: str, model_config: Any, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate comprehensive PRD using section-by-section approach
        
        Args:
            model_id: Model to use for generation
            model_config: Model configuration
            files: Prepared file data
            
        Returns:
            Combined comprehensive PRD result
        """
        logger.info(f"Starting section-by-section PRD generation with {model_id}")
        
        sections = ['overview', 'product_spec', 'technical_spec', 'implementation']
        accumulated_content = ""
        total_processing_time = 0
        total_tokens = 0
        
        for i, section in enumerate(sections):
            logger.info(f"Generating section {i+1}/{len(sections)}: {section}")
            
            # Create section-specific prompt
            prompt = self._create_section_based_prd_prompt(files, section, accumulated_content)
            
            # Execute section generation
            if model_config.provider == 'model_garden':
                section_result = self._execute_model_garden_analysis(model_id, prompt, files)
            else:
                raise Exception(f'Provider {model_config.provider} not supported')
            
            if not section_result['success']:
                logger.error(f"Failed to generate section {section}: {section_result.get('error')}")
                raise Exception(f"Section generation failed: {section_result.get('error')}")
            
            section_content = section_result['content']
            logger.info(f"Generated section {section}: {len(section_content)} characters")
            
            # Accumulate content
            if accumulated_content:
                accumulated_content += "\n\n" + section_content
            else:
                accumulated_content = section_content
                
            # Accumulate metrics
            total_processing_time += section_result.get('processing_time', 0)
            total_tokens += section_result.get('tokens_used', 0)
        
        logger.info(f"Section-by-section generation complete: {len(accumulated_content)} total characters")
        logger.info(f"Total processing time: {total_processing_time:.2f}s, Total tokens: {total_tokens}")
        
        # Format the comprehensive content into the expected JSON structure
        comprehensive_prd_json = self._format_comprehensive_prd_as_json(accumulated_content, files)
        
        return {
            'success': True,
            'content': comprehensive_prd_json,
            'processing_time': total_processing_time,
            'tokens_used': total_tokens,
            'sections_generated': len(sections)
        }

    def _format_comprehensive_prd_as_json(self, accumulated_content: str, files: List[Dict[str, Any]]) -> str:
        """
        Format the comprehensive PRD content into the expected JSON structure
        
        Args:
            accumulated_content: The complete PRD markdown content
            files: Source files for generating summary fields
            
        Returns:
            JSON string with full_prd and summary fields
        """
        # Extract basic summary information from the content
        lines = accumulated_content.split('\n')
        
        # Find project title (first # header)
        project_title = "Comprehensive Project Requirements"
        for line in lines:
            if line.strip().startswith('# ') and len(line.strip()) > 2:
                project_title = line.strip()[2:].strip()
                break
        
        # Generate summary fields based on content analysis
        file_sources = [f"S{i+1}" for i in range(len(files))]
        
        # Create the expected JSON structure
        prd_json = {
            "full_prd": accumulated_content.replace('\n', '\\n').replace('"', '\\"'),
            "problem": {
                "text": f"This comprehensive project addresses critical business requirements as outlined in the source documents, focusing on {project_title.lower()}",
                "sources": file_sources[:1]  # First source
            },
            "audience": {
                "text": "Primary stakeholders include business users, technical teams, and operations staff who require comprehensive system functionality",
                "sources": file_sources[:1]
            },
            "goals": {
                "items": [
                    "Deliver comprehensive solution meeting all specified requirements",
                    "Ensure scalability, maintainability, and performance",
                    "Achieve high user satisfaction and adoption rates",
                    "Maintain cost-effectiveness and ROI objectives"
                ],
                "sources": file_sources
            },
            "risks": {
                "items": [
                    "Technical complexity and integration challenges",
                    "Resource allocation and timeline management",
                    "User adoption and change management requirements",
                    "Scalability and performance optimization needs"
                ],
                "sources": file_sources
            },
            "competitive_scan": {
                "items": [
                    "Incorporates industry best practices and standards",
                    "Addresses gaps in existing market offerings",
                    "Provides competitive advantages through comprehensive features",
                    "Delivers superior user experience compared to alternatives"
                ],
                "sources": file_sources[:1]
            },
            "open_questions": {
                "items": [
                    "Detailed implementation timeline and milestones",
                    "Specific resource allocation and team structure",
                    "Integration requirements with existing systems",
                    "Performance benchmarks and success metrics"
                ],
                "sources": file_sources
            }
        }
        
        import json
        return json.dumps(prd_json)
    
    def _execute_model_garden_analysis(self, model_id: str, prompt: str, 
                                     files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Execute file analysis using Model Garden API
        
        Args:
            model_id: Model to use
            prompt: Analysis prompt
            files: Prepared file data
            
        Returns:
            Analysis result
        """
        try:
            import requests
            import time
            
            start_time = time.time()
            
            # Prepare API request based on model type
            if model_id in ['claude-opus-4', 'claude-sonnet-3.5', 'claude-sonnet-3-5', 'claude-sonnet-4']:
                return self._execute_claude_analysis(model_id, prompt, files)
            elif model_id == 'gemini-2-5-flash':
                return self._execute_gemini_analysis(prompt, files)
            elif model_id == 'gpt-4o':
                return self._execute_gpt4o_analysis(prompt, files)
            else:
                # Fallback to text-only analysis
                return self._execute_text_only_analysis(model_id, prompt, files)
                
        except Exception as e:
            logger.error(f"Model Garden analysis failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'content': None
            }
    
    def _execute_claude_analysis(self, model: str, prompt: str, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute analysis using Claude via router-compatible API"""
        try:
            import requests
            import time
            
            start_time = time.time()
            print(f"🤖 [AI] Starting Claude analysis ({model}) with {len(files)} files")
            logger.info(f"Starting Claude analysis ({model}) with {len(files)} files")
            
            # Use Model Garden API URL for Claude
            api_url = os.environ.get('MODEL_GARDEN_API_URL', 
                                   'https://quasarmarket.coforge.com/qag/llmrouter-api/v2/chat/completions')
            api_key = os.environ.get('MODEL_GARDEN_API_KEY', 
                                   '4b7103fd-77b1-4db6-9ab7-a88e92a0e835')
            if api_key:
                api_key = api_key.strip()
            
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "X-API-KEY": api_key
            }
            try:
                key_tail = api_key[-4:] if api_key else "None"
                logger.info(f"Model Garden headers set for {model}: X-API-KEY present, tail=****{key_tail}")
            except Exception:
                pass
            
            # Build plain text content for router compatibility
            # The router likely expects plain text in the "content" field, not Anthropic-style blocks
            content_parts = []
            
            # Process files based on type
            for i, file_data in enumerate(files, 1):
                file_type = file_data.get('file_type', '').lower()
                filename = file_data.get('filename', f'document_{i}')
                
                if file_type in ['txt', 'md', 'url', 'pdf_text']:
                    # Add text content directly (including extracted PDF text)
                    text_content = file_data.get('content', '')
                    if text_content and not text_content.startswith('data:'):  # Not base64
                        # Limit each file to prevent token overflow
                        limited_content = text_content[:15000]  # Increased limit for PDFs
                        content_parts.append(f"\n--- Content from {filename} ---\n{limited_content}")
                        if len(text_content) > 15000:
                            content_parts.append(f"\n... [truncated from {len(text_content)} chars]")
                        logger.info(f"Added text content for {filename} ({len(limited_content)} chars)")
                elif file_type in ['pdf', 'jpg', 'jpeg', 'png', 'gif']:
                    # For binary files where we couldn't extract text
                    content_parts.append(f"\n--- File: {filename} ({file_type.upper()}) ---")
                    content_parts.append(f"[Binary file - unable to extract text content. Size: {file_data.get('size', 0)} bytes]")
                    logger.warning(f"Could not extract text from {filename}, file will not be analyzed")
            
            # Add the PRD generation prompt
            full_content = prompt
            if content_parts:
                full_content = "\n".join(content_parts) + "\n\n" + prompt
            
            # Create simple message format expected by router
            messages = [{"role": "user", "content": full_content}]
            
            # Get model config to use proper max_tokens - increase for comprehensive PRD generation
            model_config = self.model_selector.model_configs.get(model)
            base_max_tokens = model_config.max_tokens if model_config else 4096
            # Use router-safe token limit for comprehensive PRD generation
            # Different models have different router limits
            if 'claude-sonnet-3' in model or 'claude-sonnet-v2' in model:
                max_tokens = min(7500, base_max_tokens)  # Stay well under 8192 router limit for Claude 3.5
            elif 'claude-sonnet-4' in model:
                max_tokens = min(12000, base_max_tokens * 2)  # Claude 4 might have higher limits
            else:
                max_tokens = min(16000, base_max_tokens * 2)  # Higher for other models
            
            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0.2,  # Leaner, more deterministic
                "top_p": 0.9,
                "max_tokens": max_tokens,  # Use model's configured limit
                # If router supports it, force JSON object output
                "response_format": {"type": "json_object"}
            }
            
            print(f"📡 [AI] Sending request to Claude API ({model})")
            logger.info(f"Sending request to Claude API ({model})...")
            
            # Configure session with SSL and connection settings for large requests
            session = requests.Session()
            session.headers.update(headers)
            
            # SSL and connection configuration for large payloads
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry
            
            # Configure retry strategy for SSL issues
            # Claude via router sometimes returns 504; fail fast to next model
            retry_strategy = Retry(
                total=0,  # No retries - fail immediately to try next model
                backoff_factor=0,
                status_forcelist=[],  # Don't retry on any status
                allowed_methods=["POST"]
            )
            
            adapter = HTTPAdapter(max_retries=retry_strategy)
            session.mount("https://", adapter)
            session.mount("http://", adapter)
            
            # Use model-specific timeout to handle thinking models properly
            opus_timeout = int(os.environ.get('CLAUDE_OPUS_TIMEOUT_SECONDS', 300))
            default_timeout = int(os.environ.get('DEFAULT_MODEL_TIMEOUT_SECONDS', 120))
            timeout_seconds = opus_timeout if model in ['claude-opus-4', 'claude-sonnet-3-5'] else default_timeout
            
            logger.info(f"AI Broker using {timeout_seconds}s timeout for model {model}")
            
            # Initial request
            response = session.post(api_url, json=payload, timeout=timeout_seconds)
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as http_err:
                err_text = ''
                try:
                    err_text = response.text[:1000]
                except Exception:
                    pass
                logger.error(f"Claude API HTTP error ({model}): {http_err} | body: {err_text}")
                raise
            
            result = response.json()
            content = result['choices'][0]['message']['content']
            total_tokens = result.get('usage', {}).get('total_tokens', 0)
            
            # Check if response was truncated (stop reason is 'length' or 'max_tokens')
            finish_reason = result.get('choices', [{}])[0].get('finish_reason', '')
            logger.info(f"Initial response - finish_reason: {finish_reason}, length: {len(content)} chars")
            
            # Implement aggressive continuation for comprehensive PRDs
            # Clean initial content of any truncation messages
            accumulated_content = self._clean_truncation_messages(content)
            continuation_count = 0
            max_continuations = 12  # Increase for comprehensive PRDs with smaller token limits
            
            # Continue if truncated OR if content is too short (less than 20,000 chars)
            while (finish_reason in ['length', 'max_tokens'] or len(accumulated_content) < 20000) and continuation_count < max_continuations:
                continuation_count += 1
                logger.info(f"Response truncated, requesting continuation {continuation_count}...")
                
                # Build continuation request
                continuation_messages = messages.copy()
                continuation_messages.append({"role": "assistant", "content": accumulated_content})
                # Create more specific continuation prompt
                if len(accumulated_content) < 20000:
                    continuation_prompt = f"CONTINUE GENERATING THE COMPREHENSIVE PRD. Current length is {len(accumulated_content)} characters but we need AT LEAST 25,000 characters. Continue with detailed sections including:\n- More detailed user personas with comprehensive backgrounds\n- Additional user stories with full acceptance criteria\n- Extensive functional requirements with sub-items\n- Complete technical specifications with code examples\n- Detailed implementation plans with timelines\n- Multiple Mermaid diagrams\nDO NOT summarize or use placeholders. Generate actual detailed content for all sections."
                else:
                    continuation_prompt = "Please continue from where you left off. Continue generating the PRD with all remaining sections in full detail."
                
                continuation_messages.append({"role": "user", "content": continuation_prompt})
                
                continuation_payload = {
                    "model": model,
                    "messages": continuation_messages,
                    "temperature": 0.2,
                    "top_p": 0.9,
                    "max_tokens": max_tokens,
                    "response_format": {"type": "json_object"} if continuation_count == max_continuations else None
                }
                
                # Send continuation request
                continuation_response = session.post(api_url, json=continuation_payload, timeout=timeout_seconds)
                try:
                    continuation_response.raise_for_status()
                except requests.exceptions.HTTPError as http_err:
                    logger.error(f"Continuation request failed: {http_err}")
                    break  # Stop trying continuations
                
                continuation_result = continuation_response.json()
                continuation_content = continuation_result['choices'][0]['message']['content']
                finish_reason = continuation_result.get('choices', [{}])[0].get('finish_reason', '')
                total_tokens += continuation_result.get('usage', {}).get('total_tokens', 0)
                
                # Clean continuation content and append
                cleaned_continuation = self._clean_truncation_messages(continuation_content)
                accumulated_content += cleaned_continuation
                logger.info(f"Continuation {continuation_count} - finish_reason: {finish_reason}, added {len(continuation_content)} chars")
            
            # Log the final response details
            logger.info(f"Claude final response length: {len(accumulated_content)} characters")
            logger.info(f"Total continuations: {continuation_count}")
            logger.info(f"Response contains 'mermaid': {'mermaid' in accumulated_content.lower()}")
            logger.info(f"Response contains 'flowchart': {'flowchart' in accumulated_content.lower()}")
            
            processing_time = time.time() - start_time
            
            return {
                'success': True,
                'content': accumulated_content,
                'processing_time': processing_time,
                'tokens_used': total_tokens
            }
            
        except Exception as e:
            print(f"❌ [AI] Claude analysis failed: {e}")
            logger.error(f"Claude analysis failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'content': None
            }
    
    def _execute_gemini_analysis(self, prompt: str, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute analysis using Gemini 2.5 Flash"""
        try:
            import requests
            import time
            
            start_time = time.time()
            
            # Use Model Garden API for Gemini
            api_url = os.environ.get('MODEL_GARDEN_API_URL', 
                                   'https://quasarmarket.coforge.com/qag/llmrouter-api/v2/chat/completions')
            api_key = os.environ.get('MODEL_GARDEN_API_KEY', 
                                   '4b7103fd-77b1-4db6-9ab7-a88e92a0e835')
            if api_key:
                api_key = api_key.strip()
            
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "X-API-KEY": api_key
            }
            
            # Prepare content with files
            content = prompt
            for file_data in files:
                if file_data['file_type'] == 'url':
                    content += f"\n\nFile: {file_data['filename']}\nContent:\n{file_data['content']}"
                else:
                    content += f"\n\nFile: {file_data['filename']} ({file_data['file_type'].upper()}) - {file_data['size']} bytes"
            
            payload = {
                "model": "gemini-2-5-flash",
                "messages": [{"role": "user", "content": content}],
                "temperature": 0.2,
                "top_p": 0.9,
                "max_tokens": 8000
            }
            
            # Configure session with SSL and connection settings for large requests
            session = requests.Session()
            session.headers.update(headers)
            
            # SSL and connection configuration for large payloads
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry
            
            # Configure retry strategy for SSL issues
            retry_strategy = Retry(
                total=1,  # Single retry for Gemini
                backoff_factor=0.5,
                status_forcelist=[429],  # Only retry on rate limit
                allowed_methods=["POST"]
            )
            
            adapter = HTTPAdapter(max_retries=retry_strategy)
            session.mount("https://", adapter)
            session.mount("http://", adapter)
            
            # Use configurable timeout for all models
            opus_timeout = int(os.environ.get('CLAUDE_OPUS_TIMEOUT_SECONDS', 300))
            default_timeout = int(os.environ.get('DEFAULT_MODEL_TIMEOUT_SECONDS', 180))
            timeout_seconds = opus_timeout if 'claude-opus-4' in str(payload) else default_timeout
            response = session.post(api_url, json=payload, timeout=timeout_seconds)
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as http_err:
                err_text = ''
                try:
                    err_text = response.text[:1000]
                except Exception:
                    pass
                logger.error(f"Gemini API HTTP error: {http_err} | body: {err_text}")
                raise
            
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            processing_time = time.time() - start_time
            tokens_used = result.get('usage', {}).get('total_tokens', 0)
            
            return {
                'success': True,
                'content': content,
                'processing_time': processing_time,
                'tokens_used': tokens_used
            }
            
        except Exception as e:
            logger.error(f"Gemini analysis failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'content': None
            }
    
    def _execute_gpt4o_analysis(self, prompt: str, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute analysis using GPT-4o"""
        try:
            import requests
            import time
            
            start_time = time.time()
            
            # Use Model Garden API for GPT-4o
            api_url = os.environ.get('MODEL_GARDEN_API_URL', 
                                   'https://quasarmarket.coforge.com/qag/llmrouter-api/v2/chat/completions')
            api_key = os.environ.get('MODEL_GARDEN_API_KEY', 
                                   '4b7103fd-77b1-4db6-9ab7-a88e92a0e835')
            if api_key:
                api_key = api_key.strip()
            
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "X-API-KEY": api_key
            }
            
            # Prepare content with files
            content = prompt
            for file_data in files:
                if file_data['file_type'] == 'url':
                    content += f"\n\nFile: {file_data['filename']}\nContent:\n{file_data['content']}"
                else:
                    content += f"\n\nFile: {file_data['filename']} ({file_data['file_type'].upper()}) - {file_data['size']} bytes"
            
            payload = {
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": content}],
                "temperature": 0.2,
                "top_p": 0.9,
                "max_tokens": 8000
            }
            
            # Configure session with SSL and connection settings for large requests
            session = requests.Session()
            session.headers.update(headers)
            
            # SSL and connection configuration for large payloads
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry
            
            # Configure retry strategy for SSL issues
            retry_strategy = Retry(
                total=1,  # Single retry for GPT-4o
                backoff_factor=1,
                status_forcelist=[429],  # Only retry on rate limit
                allowed_methods=["POST"]
            )
            
            adapter = HTTPAdapter(max_retries=retry_strategy)
            session.mount("https://", adapter)
            session.mount("http://", adapter)
            
            response = session.post(api_url, json=payload, timeout=300)  # 5 minutes for large files
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as http_err:
                err_text = ''
                try:
                    err_text = response.text[:1000]
                except Exception:
                    pass
                logger.error(f"GPT-4o API HTTP error: {http_err} | body: {err_text}")
                raise
            
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            processing_time = time.time() - start_time
            tokens_used = result.get('usage', {}).get('total_tokens', 0)
            
            return {
                'success': True,
                'content': content,
                'processing_time': processing_time,
                'tokens_used': tokens_used
            }
            
        except Exception as e:
            logger.error(f"GPT-4o analysis failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'content': None
            }
    
    def _execute_text_only_analysis(self, model_id: str, prompt: str, 
                                   files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Fallback text-only analysis for models that don't support files"""
        try:
            # Extract text content from files
            text_content = prompt + "\n\nFILE CONTENTS:\n"
            
            for file_data in files:
                if file_data['file_type'] == 'url':
                    text_content += f"\n\nFile: {file_data['filename']}\n{file_data['content']}\n"
                else:
                    text_content += f"\n\nFile: {file_data['filename']} ({file_data['file_type'].upper()}) - Binary file, {file_data['size']} bytes\n"
            
            # Use existing model garden integration
            model_garden = ModelGardenIntegration()
            result = model_garden.execute_task(
                instruction=text_content,
                model=model_id,
                role='po'
            )
            
            if result['success']:
                return {
                    'success': True,
                    'content': result['output'],
                    'processing_time': 0,
                    'tokens_used': 0
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Unknown error'),
                    'content': None
                }
                
        except Exception as e:
            logger.error(f"Text-only analysis failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'content': None
            }

    def enhance_idea_summary(self, idea_title: str, prd_content: str, project_context: str = "") -> str:
        """
        Generate a concise 2-3 line summary for an idea based on PRD content
        
        Args:
            idea_title: Original idea title
            prd_content: PRD content for the idea
            project_context: Optional project context
            
        Returns:
            Enhanced summary (2-3 lines max)
        """
        try:
            prompt = f"""Based on the PRD content below, create a concise 2-3 line summary for this idea:

IDEA TITLE: {idea_title}

PRD CONTENT:
{prd_content[:2000]}  # Limit to avoid token overflow

PROJECT CONTEXT:
{project_context[:500] if project_context else "No additional context"}

Generate a professional, business-focused summary that includes:
- What problem it solves
- Who it's for
- Key business value

Keep it to 2-3 lines maximum. Be concise and clear."""

            # Use model garden for summary generation
            response = self.model_garden.generate_response(
                prompt=prompt,
                model="gemini-2.5-flash",  # Fast model for simple summaries
                max_tokens=150,
                temperature=0.3
            )
            
            if response and response.get('content'):
                summary = response['content'].strip()
                # Ensure it's not too long
                lines = summary.split('\n')
                if len(lines) > 3:
                    summary = '\n'.join(lines[:3])
                return summary
            else:
                logger.warning(f"Failed to generate summary for idea: {idea_title}")
                return f"Business feature: {idea_title}. Details available in PRD."
                
        except Exception as e:
            logger.error(f"Error generating idea summary: {e}")
            return f"Business feature: {idea_title}. Details available in PRD."


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
