"""
ADI Knowledge Service

Manages domain knowledge storage, retrieval, and semantic search for the ADI Engine.
Extends the existing vector service with ADI-specific functionality.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from sqlalchemy import text
import json

try:
    from ...services.vector_service import VectorService
    from ..models.knowledge import Knowledge
    from ...models.base import db
except ImportError:
    try:
        from src.services.vector_service import VectorService
        from src.adi.models.knowledge import Knowledge
        from src.models.base import db
    except ImportError:
        from services.vector_service import VectorService
        from adi.models.knowledge import Knowledge
        from models.base import db

logger = logging.getLogger(__name__)


@dataclass
class DomainKnowledge:
    """Domain knowledge data structure"""
    title: str
    content: str
    rule_yaml: Optional[str] = None
    scope_filters: Dict[str, Any] = field(default_factory=dict)
    source_link: Optional[str] = None
    author: str = ""
    tags: List[str] = field(default_factory=list)


@dataclass
class KnowledgeItem:
    """Knowledge item with similarity score"""
    id: str
    project_id: str
    title: str
    content: str
    rule_yaml: Optional[str]
    scope_filters: Dict[str, Any]
    source_link: Optional[str]
    author: str
    tags: List[str]
    version: int
    similarity_score: float
    created_at: datetime
    updated_at: datetime


class KnowledgeService:
    """Service for managing domain knowledge with semantic search capabilities"""
    
    def __init__(self, db_session=None):
        self.db = db_session or db
        try:
            self.vector_service = VectorService(db=self.db)
        except Exception as e:
            logger.warning(f"Vector service initialization failed: {e}")
            self.vector_service = None
        self.embedding_model = "all-MiniLM-L6-v2"  # 384 dimensions
        
    def add_knowledge(self, project_id: str, knowledge: DomainKnowledge) -> str:
        """
        Add new domain knowledge with automatic embedding generation.
        
        Args:
            project_id: Project identifier
            knowledge: Domain knowledge data
            
        Returns:
            Knowledge item ID
        """
        try:
            # Create knowledge record
            knowledge_record = Knowledge(
                project_id=project_id,
                title=knowledge.title,
                content=knowledge.content,
                rule_yaml=knowledge.rule_yaml,
                scope_filters=knowledge.scope_filters,
                source_link=knowledge.source_link,
                author=knowledge.author,
                tags=knowledge.tags
            )
            
            self.db.session.add(knowledge_record)
            self.db.session.flush()  # Get the ID
            
            # Generate embedding for the knowledge content
            self._generate_knowledge_embedding(knowledge_record)
            
            self.db.session.commit()
            
            logger.info(f"Knowledge added: {knowledge.title} for project {project_id}")
            return str(knowledge_record.id)
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Failed to add knowledge: {str(e)}")
            raise
    
    def search_knowledge(self, project_id: str, query: str, limit: int = 5) -> List[KnowledgeItem]:
        """
        Search knowledge items using semantic similarity.
        
        Args:
            project_id: Project identifier
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of knowledge items with similarity scores
        """
        try:
            if not self.vector_service or not self.vector_service.model:
                logger.info("Vector service not available, using text-based search fallback")
                return self._fallback_text_search(project_id, query, limit)
            
            # Generate embedding for the query
            query_embedding = self.vector_service.model.encode([query], convert_to_numpy=True)[0]
            
            # Check if pgvector is available by testing the function signature
            try:
                # Try pgvector format first
                embedding_str = '[' + ','.join(map(str, query_embedding.tolist())) + ']'
                search_query = text("""
                    SELECT * FROM adi_knowledge_semantic_search(
                        :query_embedding::vector,
                        :project_id,
                        :limit,
                        0.2
                    )
                """)
                
                result = self.db.session.execute(search_query, {
                    'query_embedding': embedding_str,
                    'project_id': project_id,
                    'limit': limit
                })
                
            except Exception as pgvector_error:
                logger.info("pgvector not available, using fallback array-based search")
                # Fallback to array-based search
                search_query = text("""
                    SELECT * FROM adi_knowledge_semantic_search(
                        :query_embedding,
                        :project_id,
                        :limit,
                        0.2
                    )
                """)
                
                result = self.db.session.execute(search_query, {
                    'query_embedding': query_embedding.tolist(),
                    'project_id': project_id,
                    'limit': limit
                })
            
            knowledge_items = []
            for row in result:
                knowledge_items.append(KnowledgeItem(
                    id=str(row.id),
                    project_id=row.project_id,
                    title=row.title,
                    content=row.content,
                    rule_yaml=None,  # Not returned by search function for performance
                    scope_filters={},  # Not returned by search function for performance
                    source_link=None,  # Not returned by search function for performance
                    author=row.author,
                    tags=row.tags or [],
                    version=row.version,
                    similarity_score=float(row.similarity_score),
                    created_at=row.created_at,
                    updated_at=row.updated_at
                ))
            
            logger.info(f"Knowledge search returned {len(knowledge_items)} results for query: {query[:50]}...")
            return knowledge_items
            
        except Exception as e:
            logger.error(f"Knowledge search failed: {str(e)}")
            return self._fallback_text_search(project_id, query, limit)
    
    def _fallback_text_search(self, project_id: str, query: str, limit: int = 5) -> List[KnowledgeItem]:
        """
        Fallback text search when vector search is not available.
        """
        try:
            # Simple text search using ILIKE
            knowledge_items = Knowledge.query.filter(
                Knowledge.project_id == project_id,
                self.db.or_(
                    Knowledge.title.ilike(f'%{query}%'),
                    Knowledge.content.ilike(f'%{query}%')
                )
            ).limit(limit).all()
            
            results = []
            for knowledge in knowledge_items:
                results.append(KnowledgeItem(
                    id=str(knowledge.id),
                    project_id=knowledge.project_id,
                    title=knowledge.title,
                    content=knowledge.content,
                    rule_yaml=knowledge.rule_yaml,
                    scope_filters=knowledge.scope_filters or {},
                    source_link=knowledge.source_link,
                    author=knowledge.author,
                    tags=knowledge.tags or [],
                    version=knowledge.version,
                    similarity_score=0.5,  # Default score for text search
                    created_at=knowledge.created_at,
                    updated_at=knowledge.updated_at
                ))
            
            logger.info(f"Fallback text search returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Fallback text search failed: {str(e)}")
            return []
    
    def get_relevant_context(self, project_id: str, case_data: Dict[str, Any]) -> List[KnowledgeItem]:
        """
        Get contextually relevant knowledge for a decision log case.
        
        Args:
            project_id: Project identifier
            case_data: Decision log case data
            
        Returns:
            List of relevant knowledge items
        """
        try:
            # Extract relevant information from case data to build context query
            context_parts = []
            
            # Add event type and attributes
            if 'event' in case_data:
                event = case_data['event']
                if 'type' in event:
                    context_parts.append(f"event type: {event['type']}")
                if 'attrs' in event:
                    # Add key attributes
                    for key, value in event['attrs'].items():
                        if isinstance(value, (str, int, float, bool)):
                            context_parts.append(f"{key}: {value}")
            
            # Add decision information
            if 'decision' in case_data:
                decision = case_data['decision']
                if 'action' in decision:
                    context_parts.append(f"action: {decision['action']}")
                if 'template_id' in decision:
                    context_parts.append(f"template: {decision['template_id']}")
                if 'status' in decision:
                    context_parts.append(f"status: {decision['status']}")
            
            # Build search query from context
            context_query = " ".join(context_parts)
            
            if not context_query.strip():
                logger.warning("No context available for knowledge retrieval")
                return []
            
            # Search for relevant knowledge
            return self.search_knowledge(project_id, context_query, limit=5)
            
        except Exception as e:
            logger.error(f"Failed to get relevant context: {str(e)}")
            return []
    
    def update_knowledge(self, knowledge_id: str, updates: Dict[str, Any]) -> None:
        """
        Update a knowledge item and regenerate embeddings if content changed.
        
        Args:
            knowledge_id: Knowledge item ID
            updates: Dictionary of fields to update
        """
        try:
            knowledge = Knowledge.query.get(knowledge_id)
            if not knowledge:
                raise ValueError(f"Knowledge item {knowledge_id} not found")
            
            content_changed = False
            
            # Update fields
            for field, value in updates.items():
                if hasattr(knowledge, field):
                    setattr(knowledge, field, value)
                    if field in ['title', 'content']:
                        content_changed = True
            
            # Increment version and update timestamp
            knowledge.version += 1
            knowledge.updated_at = datetime.utcnow()
            
            # Regenerate embedding if content changed
            if content_changed:
                self._generate_knowledge_embedding(knowledge)
            
            self.db.session.commit()
            
            logger.info(f"Knowledge updated: {knowledge_id} to version {knowledge.version}")
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Failed to update knowledge {knowledge_id}: {str(e)}")
            raise
    
    def version_knowledge(self, knowledge_id: str) -> str:
        """
        Create a new version of a knowledge item.
        
        Args:
            knowledge_id: Knowledge item ID
            
        Returns:
            New knowledge item ID
        """
        try:
            original = Knowledge.query.get(knowledge_id)
            if not original:
                raise ValueError(f"Knowledge item {knowledge_id} not found")
            
            # Create new version
            new_knowledge = Knowledge(
                project_id=original.project_id,
                title=original.title,
                content=original.content,
                rule_yaml=original.rule_yaml,
                scope_filters=original.scope_filters,
                source_link=original.source_link,
                author=original.author,
                tags=original.tags,
                version=original.version + 1
            )
            
            self.db.session.add(new_knowledge)
            self.db.session.flush()
            
            # Generate embedding
            self._generate_knowledge_embedding(new_knowledge)
            
            self.db.session.commit()
            
            logger.info(f"Knowledge versioned: {knowledge_id} -> {new_knowledge.id}")
            return str(new_knowledge.id)
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Failed to version knowledge {knowledge_id}: {str(e)}")
            raise
    
    def get_knowledge_usage_analytics(self, project_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Get analytics on knowledge usage and effectiveness.
        
        Args:
            project_id: Project identifier
            days: Number of days to analyze
            
        Returns:
            Analytics data
        """
        try:
            # This would integrate with the scoring pipeline to track knowledge usage
            # For now, return basic statistics
            
            total_query = text("""
                SELECT COUNT(*) as total_knowledge
                FROM adi_knowledge
                WHERE project_id = :project_id
            """)
            
            recent_query = text("""
                SELECT COUNT(*) as recent_knowledge
                FROM adi_knowledge
                WHERE project_id = :project_id
                    AND created_at >= NOW() - INTERVAL ':days days'
            """)
            
            total_result = self.db.session.execute(total_query, {'project_id': project_id})
            recent_result = self.db.session.execute(recent_query, {
                'project_id': project_id,
                'days': days
            })
            
            total_count = total_result.scalar() or 0
            recent_count = recent_result.scalar() or 0
            
            return {
                'total_knowledge_items': total_count,
                'recent_additions': recent_count,
                'period_days': days,
                'average_per_day': recent_count / days if days > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get knowledge analytics: {str(e)}")
            return {}
    
    def build_knowledge_recommendation_system(self, project_id: str, case_data: Dict[str, Any]) -> List[str]:
        """
        Build knowledge recommendations for domain experts based on case patterns.
        
        Args:
            project_id: Project identifier
            case_data: Decision log case data
            
        Returns:
            List of knowledge recommendations
        """
        try:
            # Get relevant knowledge
            relevant_knowledge = self.get_relevant_context(project_id, case_data)
            
            if not relevant_knowledge:
                return [
                    "Consider adding knowledge about this event type",
                    "Document common patterns for this scenario",
                    "Add rules for similar decision contexts"
                ]
            
            recommendations = []
            
            # Analyze knowledge gaps
            event_type = case_data.get('event', {}).get('type', 'unknown')
            decision_action = case_data.get('decision', {}).get('action', 'unknown')
            
            # Check if we have specific knowledge for this event type
            event_specific = any(event_type.lower() in k.content.lower() for k in relevant_knowledge)
            if not event_specific:
                recommendations.append(f"Add specific knowledge for {event_type} events")
            
            # Check if we have action-specific knowledge
            action_specific = any(decision_action.lower() in k.content.lower() for k in relevant_knowledge)
            if not action_specific:
                recommendations.append(f"Document best practices for {decision_action} actions")
            
            # Check knowledge recency
            recent_knowledge = [k for k in relevant_knowledge 
                              if (datetime.utcnow() - k.updated_at).days < 30]
            if len(recent_knowledge) < len(relevant_knowledge) / 2:
                recommendations.append("Update existing knowledge with recent insights")
            
            return recommendations or ["Knowledge base appears comprehensive for this case"]
            
        except Exception as e:
            logger.error(f"Failed to build knowledge recommendations: {str(e)}")
            return ["Unable to generate recommendations at this time"]
    
    def _generate_knowledge_embedding(self, knowledge: Knowledge) -> None:
        """
        Generate and store embedding for a knowledge item.
        
        Args:
            knowledge: Knowledge record to generate embedding for
        """
        try:
            if not self.vector_service or not self.vector_service.model:
                logger.warning("Vector service not available, skipping embedding generation")
                return
                
            # Combine title and content for embedding
            text_content = f"{knowledge.title}\n\n{knowledge.content}"
            
            # Generate embedding
            embedding = self.vector_service.model.encode([text_content], convert_to_numpy=True)[0]
            
            # Store embedding and metadata
            knowledge.embedding = embedding.tolist()
            knowledge.embedding_model = self.embedding_model
            knowledge.embedding_generated_at = datetime.utcnow()
            
            logger.debug(f"Generated embedding for knowledge: {knowledge.title}")
            
        except Exception as e:
            logger.error(f"Failed to generate embedding for knowledge {knowledge.id}: {str(e)}")
            # Don't raise - allow knowledge to be stored without embedding
            pass
    
    def reindex_all_knowledge(self, project_id: Optional[str] = None) -> Dict[str, int]:
        """
        Regenerate embeddings for all knowledge items.
        
        Args:
            project_id: Optional project filter
            
        Returns:
            Statistics about the reindexing process
        """
        try:
            query = Knowledge.query
            if project_id:
                query = query.filter(Knowledge.project_id == project_id)
            
            knowledge_items = query.all()
            
            success_count = 0
            error_count = 0
            
            for knowledge in knowledge_items:
                try:
                    self._generate_knowledge_embedding(knowledge)
                    success_count += 1
                except Exception as e:
                    logger.error(f"Failed to reindex knowledge {knowledge.id}: {str(e)}")
                    error_count += 1
            
            self.db.session.commit()
            
            logger.info(f"Knowledge reindexing completed: {success_count} success, {error_count} errors")
            
            return {
                'total_processed': len(knowledge_items),
                'success_count': success_count,
                'error_count': error_count
            }
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Knowledge reindexing failed: {str(e)}")
            raise