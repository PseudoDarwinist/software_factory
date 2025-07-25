"""
Context-Aware AI Service - Intelligent AI with Graph and Vector Context
Enhances AI responses with project relationships, semantic search, and domain knowledge
"""

import logging
import json
import re
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

try:
    from ..services.intelligence_engine import get_intelligence_engine, get_recommendation_engine
    from ..services.graph_service import GraphService, ProjectGraphService
    from ..services.vector_service import get_vector_service
    from ..services.ai_broker import get_ai_broker, TaskType, Priority
    from ..services.distributed_cache import get_distributed_cache
    from ..models.mission_control_project import MissionControlProject
    from ..models.conversation import Conversation
    from ..models.system_map import SystemMap
except ImportError:
    from services.intelligence_engine import get_intelligence_engine, get_recommendation_engine
    from services.graph_service import GraphService, ProjectGraphService
    from services.vector_service import get_vector_service
    from services.ai_broker import get_ai_broker, TaskType, Priority
    from services.distributed_cache import get_distributed_cache
    from models.mission_control_project import MissionControlProject
    from models.conversation import Conversation
    from models.system_map import SystemMap

logger = logging.getLogger(__name__)


class ContextType(Enum):
    """Types of context that can be provided to AI"""
    PROJECT_OVERVIEW = "project_overview"
    RELATED_PROJECTS = "related_projects"
    TECHNOLOGY_STACK = "technology_stack"
    CONVERSATION_HISTORY = "conversation_history"
    CODE_ANALYSIS = "code_analysis"
    SYSTEM_ARCHITECTURE = "system_architecture"
    RECOMMENDATIONS = "recommendations"
    SEMANTIC_SEARCH = "semantic_search"
    GRAPH_RELATIONSHIPS = "graph_relationships"


@dataclass
class AIContext:
    """Rich context object for AI requests"""
    project_id: Optional[int] = None
    conversation_id: Optional[int] = None
    user_query: str = ""
    context_types: List[ContextType] = None
    max_context_tokens: int = 4000
    include_graph_data: bool = True
    include_vector_search: bool = True
    include_recommendations: bool = True
    metadata: Dict[str, Any] = None


@dataclass
class EnrichedContext:
    """Enriched context with all relevant information"""
    project_context: Dict[str, Any] = None
    graph_context: Dict[str, Any] = None
    vector_context: Dict[str, Any] = None
    conversation_context: Dict[str, Any] = None
    recommendation_context: Dict[str, Any] = None
    technology_context: Dict[str, Any] = None
    total_tokens: int = 0
    context_summary: str = ""


class ContextAwareAI:
    """AI service with rich contextual understanding"""
    
    def __init__(self):
        self.intelligence_engine = get_intelligence_engine()
        self.recommendation_engine = get_recommendation_engine()
        self.cache = get_distributed_cache()
        self.ai_broker = get_ai_broker()
        
    def create_context(self, user_query: str, project_id: Optional[int] = None,
                      conversation_id: Optional[int] = None, **kwargs) -> AIContext:
        """Create AI context from user request"""
        return AIContext(
            project_id=project_id,
            conversation_id=conversation_id,
            user_query=user_query,
            context_types=kwargs.get('context_types', []),
            max_context_tokens=kwargs.get('max_context_tokens', 4000),
            include_graph_data=kwargs.get('include_graph_data', True),
            include_vector_search=kwargs.get('include_vector_search', True),
            include_recommendations=kwargs.get('include_recommendations', True),
            metadata=kwargs.get('metadata', {})
        )
    
    def enrich_context(self, context: AIContext) -> EnrichedContext:
        """Enrich basic context with all available intelligence"""
        try:
            enriched = EnrichedContext()
            total_tokens = 0
            
            # Check cache first
            cache_key = f"enriched_context_{context.project_id}_{hash(context.user_query)}"
            cached_context = self.cache.get(cache_key, namespace='ai_context')
            
            if cached_context and not self._is_context_stale(cached_context):
                logger.debug(f"Using cached enriched context")
                return EnrichedContext(**cached_context)
            
            # 1. Project Context
            if context.project_id:
                enriched.project_context = self._build_project_context(context.project_id)
                total_tokens += self._estimate_tokens(enriched.project_context)
            
            # 2. Graph Context (relationships and ecosystem)
            if context.include_graph_data and context.project_id:
                enriched.graph_context = self._build_graph_context(context.project_id)
                total_tokens += self._estimate_tokens(enriched.graph_context)
            
            # 3. Vector Search Context (semantic similarity)
            if context.include_vector_search and context.user_query:
                enriched.vector_context = self._build_vector_context(
                    context.user_query, context.project_id
                )
                total_tokens += self._estimate_tokens(enriched.vector_context)
            
            # 4. Conversation Context
            if context.conversation_id:
                enriched.conversation_context = self._build_conversation_context(
                    context.conversation_id
                )
                total_tokens += self._estimate_tokens(enriched.conversation_context)
            
            # 5. Recommendation Context
            if context.include_recommendations and context.project_id:
                enriched.recommendation_context = self._build_recommendation_context(
                    context.project_id
                )
                total_tokens += self._estimate_tokens(enriched.recommendation_context)
            
            # 6. Technology Context
            if context.project_id:
                enriched.technology_context = self._build_technology_context(
                    context.project_id
                )
                total_tokens += self._estimate_tokens(enriched.technology_context)
            
            # 7. Generate Context Summary
            enriched.context_summary = self._generate_context_summary(enriched)
            enriched.total_tokens = total_tokens
            
            # Cache enriched context for 5 minutes
            self.cache.set(
                cache_key, 
                enriched.__dict__, 
                ttl=300, 
                namespace='ai_context'
            )
            
            logger.info(f"Enriched context built: {total_tokens} tokens")
            return enriched
            
        except Exception as e:
            logger.error(f"Error enriching context: {e}")
            return EnrichedContext()
    
    def _build_project_context(self, project_id: int) -> Dict[str, Any]:
        """Build project-specific context"""
        try:
            project = Project.query.get(project_id)
            if not project:
                return {}
            
            # Get project analysis
            analysis = self.intelligence_engine.analyze_project_complexity(project_id)
            activity = self.intelligence_engine.analyze_project_activity(project_id)
            technologies = self.intelligence_engine.extract_technology_stack(project_id)
            
            return {
                'project_info': {
                    'id': project.id,
                    'name': project.name,
                    'description': project.description,
                    'status': project.status,
                    'repository_url': project.repository_url
                },
                'complexity_analysis': analysis,
                'activity_analysis': activity,
                'technology_stack': technologies,
                'created_at': project.created_at.isoformat(),
                'last_updated': project.updated_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error building project context: {e}")
            return {}
    
    def _build_graph_context(self, project_id: int) -> Dict[str, Any]:
        """Build graph relationship context"""
        try:
            # Get project ecosystem
            ecosystem = ProjectGraphService.get_project_ecosystem(project_id, max_depth=2)
            
            if not ecosystem:
                return {}
            
            # Get direct relationships
            relationships = GraphService.get_entity_relationships(
                entity_type='project',
                entity_id=str(project_id)
            )
            
            # Get centrality metrics
            centrality = GraphService.calculate_entity_centrality(
                entity_type='project',
                entity_id=str(project_id)
            )
            
            return {
                'ecosystem': ecosystem,
                'direct_relationships': relationships[:10],  # Limit for context
                'centrality_metrics': centrality,
                'relationship_summary': self._summarize_relationships(relationships)
            }
            
        except Exception as e:
            logger.error(f"Error building graph context: {e}")
            return {}
    
    def _build_vector_context(self, query: str, project_id: Optional[int] = None) -> Dict[str, Any]:
        """Build semantic search context"""
        try:
            vector_service = get_vector_service()
            if not vector_service:
                return {}
            
            # Perform semantic search
            similar_content = vector_service.semantic_search(
                query=query,
                limit=5,
                entity_type='conversation' if project_id else None,
                entity_id=str(project_id) if project_id else None
            )
            
            if not similar_content:
                return {}
            
            return {
                'similar_conversations': similar_content[:3],  # Top 3 results
                'semantic_keywords': self._extract_semantic_keywords(query),
                'search_summary': f"Found {len(similar_content)} semantically similar conversations"
            }
            
        except Exception as e:
            logger.error(f"Error building vector context: {e}")
            return {}
    
    def _build_conversation_context(self, conversation_id: int) -> Dict[str, Any]:
        """Build conversation history context"""
        try:
            conversation = Conversation.query.get(conversation_id)
            if not conversation:
                return {}
            
            # Get recent messages (last 10)
            recent_messages = conversation.messages[-10:] if conversation.messages else []
            
            return {
                'conversation_info': {
                    'id': conversation.id,
                    'title': conversation.title,
                    'project_id': conversation.project_id,
                    'created_at': conversation.created_at.isoformat()
                },
                'recent_messages': recent_messages,
                'message_count': len(conversation.messages) if conversation.messages else 0,
                'conversation_summary': self._summarize_conversation(recent_messages)
            }
            
        except Exception as e:
            logger.error(f"Error building conversation context: {e}")
            return {}
    
    def _build_recommendation_context(self, project_id: int) -> Dict[str, Any]:
        """Build recommendation context"""
        try:
            # Get recommendations
            recommendations = self.recommendation_engine.generate_project_recommendations(project_id)
            
            # Get similar projects
            similar_projects = self.recommendation_engine.find_similar_projects(project_id, limit=3)
            
            return {
                'recommendations': [
                    {
                        'type': rec.recommendation_type,
                        'title': rec.title,
                        'description': rec.description,
                        'confidence': rec.confidence,
                        'reasoning': rec.reasoning
                    }
                    for rec in recommendations[:5]  # Top 5 recommendations
                ],
                'similar_projects': [
                    {
                        'name': sp['project'].name,
                        'similarity_score': sp['similarity_score'],
                        'common_technologies': sp['common_technologies']
                    }
                    for sp in similar_projects
                ],
                'recommendation_summary': f"Generated {len(recommendations)} recommendations"
            }
            
        except Exception as e:
            logger.error(f"Error building recommendation context: {e}")
            return {}
    
    def _build_technology_context(self, project_id: int) -> Dict[str, Any]:
        """Build technology and architectural context"""
        try:
            # Get system maps
            system_maps = SystemMap.query.filter_by(project_id=project_id).all()
            
            # Get technology stack
            technologies = self.intelligence_engine.extract_technology_stack(project_id)
            
            # Get architectural patterns from system maps
            architectural_patterns = []
            for sys_map in system_maps:
                if sys_map.map_data:
                    patterns = self._extract_architectural_patterns(sys_map.map_data)
                    architectural_patterns.extend(patterns)
            
            return {
                'technology_stack': technologies,
                'system_maps_count': len(system_maps),
                'architectural_patterns': list(set(architectural_patterns)),
                'latest_system_map': system_maps[-1].map_data if system_maps else None
            }
            
        except Exception as e:
            logger.error(f"Error building technology context: {e}")
            return {}
    
    def _generate_context_summary(self, enriched: EnrichedContext) -> str:
        """Generate a human-readable context summary"""
        summary_parts = []
        
        if enriched.project_context:
            project_info = enriched.project_context.get('project_info', {})
            complexity = enriched.project_context.get('complexity_analysis', {})
            summary_parts.append(
                f"Project '{project_info.get('name', 'Unknown')}' "
                f"(complexity: {complexity.get('complexity_score', 0)}/100)"
            )
        
        if enriched.technology_context:
            technologies = enriched.technology_context.get('technology_stack', [])
            if technologies:
                summary_parts.append(f"Technologies: {', '.join(technologies[:3])}")
        
        if enriched.recommendation_context:
            rec_count = len(enriched.recommendation_context.get('recommendations', []))
            if rec_count > 0:
                summary_parts.append(f"{rec_count} active recommendations")
        
        if enriched.graph_context:
            ecosystem_size = enriched.graph_context.get('ecosystem', {}).get('ecosystem_size', 0)
            if ecosystem_size > 0:
                summary_parts.append(f"ecosystem size: {ecosystem_size} entities")
        
        return "; ".join(summary_parts) if summary_parts else "Basic context available"
    
    def _summarize_relationships(self, relationships: List[Dict]) -> str:
        """Summarize graph relationships"""
        if not relationships:
            return "No direct relationships"
        
        rel_types = [rel['relationship_type'] for rel in relationships]
        rel_counts = {}
        for rel_type in rel_types:
            rel_counts[rel_type] = rel_counts.get(rel_type, 0) + 1
        
        summary = ", ".join([f"{count} {rel_type}" for rel_type, count in rel_counts.items()])
        return f"Relationships: {summary}"
    
    def _summarize_conversation(self, messages: List[Dict]) -> str:
        """Summarize conversation messages"""
        if not messages:
            return "No conversation history"
        
        # Simple summary based on message count and roles
        user_messages = len([m for m in messages if m.get('role') == 'user'])
        assistant_messages = len([m for m in messages if m.get('role') == 'assistant'])
        
        return f"Conversation history: {user_messages} user messages, {assistant_messages} AI responses"
    
    def _extract_semantic_keywords(self, query: str) -> List[str]:
        """Extract semantic keywords from query"""
        # Simple keyword extraction (could be enhanced with NLP)
        keywords = re.findall(r'\b\w{3,}\b', query.lower())
        tech_keywords = [
            'python', 'javascript', 'react', 'flask', 'postgresql', 'redis',
            'docker', 'api', 'database', 'frontend', 'backend', 'ai', 'ml'
        ]
        
        found_keywords = [kw for kw in keywords if kw in tech_keywords]
        return found_keywords[:5]  # Limit to 5 keywords
    
    def _extract_architectural_patterns(self, map_data: Any) -> List[str]:
        """Extract architectural patterns from system map data"""
        patterns = []
        
        if isinstance(map_data, dict):
            data_str = json.dumps(map_data).lower()
        else:
            data_str = str(map_data).lower()
        
        # Look for common architectural patterns
        pattern_keywords = {
            'microservices': ['microservice', 'service', 'api'],
            'mvc': ['model', 'view', 'controller'],
            'rest': ['rest', 'restful', 'endpoint'],
            'event_driven': ['event', 'queue', 'message'],
            'layered': ['layer', 'tier', 'separation']
        }
        
        for pattern, keywords in pattern_keywords.items():
            if any(keyword in data_str for keyword in keywords):
                patterns.append(pattern)
        
        return patterns
    
    def _estimate_tokens(self, data: Any) -> int:
        """Estimate token count for context data"""
        if not data:
            return 0
        
        # Simple estimation: 4 characters ≈ 1 token
        text_representation = json.dumps(data) if isinstance(data, (dict, list)) else str(data)
        return len(text_representation) // 4
    
    def _is_context_stale(self, cached_context: Dict, max_age_minutes: int = 5) -> bool:
        """Check if cached context is stale"""
        if 'cached_at' not in cached_context:
            return True
        
        cached_time = datetime.fromisoformat(cached_context['cached_at'])
        return datetime.utcnow() - cached_time > timedelta(minutes=max_age_minutes)
    
    def generate_contextual_response(self, context: AIContext) -> Dict[str, Any]:
        """Generate AI response with full contextual awareness"""
        try:
            # Enrich context with all available intelligence
            enriched_context = self.enrich_context(context)
            
            # Build contextual prompt
            contextual_prompt = self._build_contextual_prompt(
                context.user_query, 
                enriched_context
            )
            
            # Determine best AI model for this task
            task_type = self._classify_task_type(context.user_query)
            
            # Generate response using AI broker
            ai_response = self.ai_broker.process_request(
                prompt=contextual_prompt,
                task_type=task_type,
                priority=Priority.NORMAL,
                context={
                    'project_id': context.project_id,
                    'conversation_id': context.conversation_id,
                    'enriched_context': enriched_context.__dict__
                }
            )
            
            # Enhance response with metadata
            return {
                'response': ai_response,
                'context_summary': enriched_context.context_summary,
                'context_tokens': enriched_context.total_tokens,
                'task_type': task_type.value,
                'generated_at': datetime.utcnow().isoformat(),
                'project_id': context.project_id,
                'conversation_id': context.conversation_id
            }
            
        except Exception as e:
            logger.error(f"Error generating contextual response: {e}")
            return {
                'response': f"I apologize, but I encountered an error while processing your request: {str(e)}",
                'error': True,
                'generated_at': datetime.utcnow().isoformat()
            }
    
    def _build_contextual_prompt(self, user_query: str, enriched_context: EnrichedContext) -> str:
        """Build a contextually-aware prompt for the AI"""
        prompt_parts = []
        
        # System context
        prompt_parts.append("You are an AI assistant for Software Factory, an intelligent SDLC platform.")
        prompt_parts.append("You have access to comprehensive project context including:")
        prompt_parts.append("- Project analysis and complexity metrics")
        prompt_parts.append("- Technology stack and architectural patterns")
        prompt_parts.append("- Graph relationships and project ecosystem")
        prompt_parts.append("- Semantic search results from related conversations")
        prompt_parts.append("- Intelligent recommendations and insights")
        prompt_parts.append("")
        
        # Add specific context sections
        if enriched_context.project_context:
            prompt_parts.append("## Project Context")
            project_info = enriched_context.project_context.get('project_info', {})
            prompt_parts.append(f"Project: {project_info.get('name')} ({project_info.get('status')})")
            
            complexity = enriched_context.project_context.get('complexity_analysis', {})
            prompt_parts.append(f"Complexity Score: {complexity.get('complexity_score', 0)}/100")
            
            technologies = enriched_context.project_context.get('technology_stack', [])
            if technologies:
                prompt_parts.append(f"Technology Stack: {', '.join(technologies)}")
            prompt_parts.append("")
        
        if enriched_context.recommendation_context:
            prompt_parts.append("## Active Recommendations")
            recommendations = enriched_context.recommendation_context.get('recommendations', [])
            for rec in recommendations[:3]:  # Top 3 recommendations
                prompt_parts.append(f"- {rec['title']}: {rec['description']}")
            prompt_parts.append("")
        
        if enriched_context.graph_context:
            prompt_parts.append("## Project Ecosystem")
            ecosystem = enriched_context.graph_context.get('ecosystem', {})
            prompt_parts.append(f"Ecosystem size: {ecosystem.get('ecosystem_size', 0)} connected entities")
            rel_summary = enriched_context.graph_context.get('relationship_summary', '')
            if rel_summary:
                prompt_parts.append(f"Relationships: {rel_summary}")
            prompt_parts.append("")
        
        if enriched_context.vector_context:
            prompt_parts.append("## Related Context (Semantic Search)")
            similar_convs = enriched_context.vector_context.get('similar_conversations', [])
            if similar_convs:
                prompt_parts.append("Similar previous discussions:")
                for conv in similar_convs[:2]:  # Top 2 similar conversations
                    prompt_parts.append(f"- {conv.get('title', 'Untitled')}: {conv.get('summary', '')}")
            prompt_parts.append("")
        
        # User query
        prompt_parts.append("## User Query")
        prompt_parts.append(user_query)
        prompt_parts.append("")
        
        # Instructions
        prompt_parts.append("## Instructions")
        prompt_parts.append("Please provide a helpful, contextual response that:")
        prompt_parts.append("1. Leverages the provided project context and relationships")
        prompt_parts.append("2. References relevant recommendations when applicable")
        prompt_parts.append("3. Considers the project's technology stack and complexity")
        prompt_parts.append("4. Builds upon related conversations and patterns")
        prompt_parts.append("5. Provides actionable insights specific to this project")
        
        return "\n".join(prompt_parts)
    
    def _classify_task_type(self, query: str) -> TaskType:
        """Classify the type of task based on user query"""
        query_lower = query.lower()
        
        # Code-related keywords
        if any(keyword in query_lower for keyword in ['code', 'function', 'class', 'implement', 'debug', 'fix']):
            if any(keyword in query_lower for keyword in ['review', 'check', 'analyze']):
                return TaskType.CODE_REVIEW
            elif any(keyword in query_lower for keyword in ['debug', 'error', 'fix', 'problem']):
                return TaskType.DEBUGGING
            else:
                return TaskType.CODE_GENERATION
        
        # Documentation keywords
        elif any(keyword in query_lower for keyword in ['document', 'docs', 'readme', 'explain']):
            return TaskType.DOCUMENTATION
        
        # Analysis keywords
        elif any(keyword in query_lower for keyword in ['analyze', 'analysis', 'insights', 'understand']):
            return TaskType.ANALYSIS
        
        # Architecture keywords
        elif any(keyword in query_lower for keyword in ['architecture', 'design', 'structure', 'system']):
            return TaskType.ARCHITECTURE
        
        # Planning keywords
        elif any(keyword in query_lower for keyword in ['plan', 'strategy', 'roadmap', 'approach']):
            return TaskType.PLANNING
        
        # Testing keywords
        elif any(keyword in query_lower for keyword in ['test', 'testing', 'unit test', 'integration']):
            return TaskType.TESTING
        
        # Default to conversation
        else:
            return TaskType.CONVERSATION


# Global instance
context_aware_ai = None


def get_context_aware_ai() -> ContextAwareAI:
    """Get the global context-aware AI instance"""
    global context_aware_ai
    if context_aware_ai is None:
        context_aware_ai = ContextAwareAI()
    return context_aware_ai


def init_context_aware_ai() -> ContextAwareAI:
    """Initialize the context-aware AI system"""
    global context_aware_ai
    context_aware_ai = ContextAwareAI()
    logger.info("Context-aware AI system initialized")
    return context_aware_ai