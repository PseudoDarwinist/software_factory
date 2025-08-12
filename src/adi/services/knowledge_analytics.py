"""
Knowledge Analytics Service

Tracks knowledge usage and effectiveness in the ADI scoring pipeline.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict, Counter
from dataclasses import dataclass
from sqlalchemy import text

try:
    from ...models.base import db
except ImportError:
    try:
        from src.models.base import db
    except ImportError:
        from models.base import db

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeUsageMetrics:
    """Metrics about knowledge usage"""
    total_retrievals: int
    unique_knowledge_items_used: int
    average_similarity_score: float
    most_used_knowledge: List[Dict[str, Any]]
    knowledge_effectiveness: Dict[str, float]
    usage_by_event_type: Dict[str, int]
    usage_by_author: Dict[str, int]


class KnowledgeAnalytics:
    """Service for tracking and analyzing knowledge usage in the ADI pipeline"""
    
    def __init__(self):
        self.usage_log = []  # In-memory log for current session
        
    def log_knowledge_retrieval(self, project_id: str, case_id: str, 
                               knowledge_items: List[Dict[str, Any]], 
                               context: Dict[str, Any]) -> None:
        """
        Log knowledge retrieval for analytics.
        
        Args:
            project_id: Project identifier
            case_id: Case identifier
            knowledge_items: List of retrieved knowledge items
            context: Context information about the retrieval
        """
        try:
            usage_entry = {
                'timestamp': datetime.utcnow(),
                'project_id': project_id,
                'case_id': case_id,
                'knowledge_count': len(knowledge_items),
                'knowledge_items': knowledge_items,
                'context': context
            }
            
            self.usage_log.append(usage_entry)
            
            # Keep only recent entries to prevent memory bloat
            if len(self.usage_log) > 1000:
                self.usage_log = self.usage_log[-500:]
                
            logger.debug(f"Logged knowledge retrieval for case {case_id}: {len(knowledge_items)} items")
            
        except Exception as e:
            logger.warning(f"Failed to log knowledge retrieval: {str(e)}")
    
    def log_knowledge_effectiveness(self, project_id: str, case_id: str,
                                  knowledge_id: str, effectiveness_score: float,
                                  feedback_type: str) -> None:
        """
        Log knowledge effectiveness feedback.
        
        Args:
            project_id: Project identifier
            case_id: Case identifier
            knowledge_id: Knowledge item identifier
            effectiveness_score: Score from 0.0 to 1.0
            feedback_type: Type of feedback (e.g., 'validator_success', 'insight_quality')
        """
        try:
            # For now, store in memory. In production, this would go to a database
            effectiveness_entry = {
                'timestamp': datetime.utcnow(),
                'project_id': project_id,
                'case_id': case_id,
                'knowledge_id': knowledge_id,
                'effectiveness_score': effectiveness_score,
                'feedback_type': feedback_type
            }
            
            # Add to usage log with special marker
            effectiveness_entry['_type'] = 'effectiveness'
            self.usage_log.append(effectiveness_entry)
            
            logger.debug(f"Logged knowledge effectiveness for {knowledge_id}: {effectiveness_score}")
            
        except Exception as e:
            logger.warning(f"Failed to log knowledge effectiveness: {str(e)}")
    
    def get_usage_metrics(self, project_id: str, days: int = 7) -> KnowledgeUsageMetrics:
        """
        Get knowledge usage metrics for a project.
        
        Args:
            project_id: Project identifier
            days: Number of days to analyze
            
        Returns:
            Knowledge usage metrics
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=days)
            
            # Filter usage log for the project and time period
            relevant_entries = [
                entry for entry in self.usage_log
                if (entry.get('project_id') == project_id and 
                    entry.get('timestamp', datetime.min) >= cutoff_time and
                    entry.get('_type') != 'effectiveness')
            ]
            
            if not relevant_entries:
                return KnowledgeUsageMetrics(
                    total_retrievals=0,
                    unique_knowledge_items_used=0,
                    average_similarity_score=0.0,
                    most_used_knowledge=[],
                    knowledge_effectiveness={},
                    usage_by_event_type={},
                    usage_by_author={}
                )
            
            # Calculate metrics
            total_retrievals = len(relevant_entries)
            
            # Collect all knowledge items used
            all_knowledge_items = []
            similarity_scores = []
            event_types = []
            authors = []
            
            for entry in relevant_entries:
                knowledge_items = entry.get('knowledge_items', [])
                all_knowledge_items.extend(knowledge_items)
                
                # Collect similarity scores
                for item in knowledge_items:
                    if 'similarity_score' in item:
                        similarity_scores.append(item['similarity_score'])
                
                # Collect context information
                context = entry.get('context', {})
                if 'event_type' in context:
                    event_types.append(context['event_type'])
                
                for item in knowledge_items:
                    if 'author' in item:
                        authors.append(item['author'])
            
            # Calculate unique knowledge items
            unique_knowledge_ids = set(item.get('id') for item in all_knowledge_items if item.get('id'))
            unique_knowledge_items_used = len(unique_knowledge_ids)
            
            # Calculate average similarity score
            average_similarity_score = sum(similarity_scores) / len(similarity_scores) if similarity_scores else 0.0
            
            # Find most used knowledge items
            knowledge_usage_count = Counter(item.get('id') for item in all_knowledge_items if item.get('id'))
            most_used_knowledge = []
            for knowledge_id, count in knowledge_usage_count.most_common(5):
                # Find a representative item
                representative_item = next(
                    (item for item in all_knowledge_items if item.get('id') == knowledge_id),
                    {'id': knowledge_id, 'title': 'Unknown'}
                )
                most_used_knowledge.append({
                    'id': knowledge_id,
                    'title': representative_item.get('title', 'Unknown'),
                    'usage_count': count
                })
            
            # Get effectiveness scores
            effectiveness_entries = [
                entry for entry in self.usage_log
                if (entry.get('project_id') == project_id and 
                    entry.get('timestamp', datetime.min) >= cutoff_time and
                    entry.get('_type') == 'effectiveness')
            ]
            
            knowledge_effectiveness = {}
            effectiveness_by_knowledge = defaultdict(list)
            for entry in effectiveness_entries:
                knowledge_id = entry.get('knowledge_id')
                score = entry.get('effectiveness_score', 0.0)
                if knowledge_id:
                    effectiveness_by_knowledge[knowledge_id].append(score)
            
            for knowledge_id, scores in effectiveness_by_knowledge.items():
                knowledge_effectiveness[knowledge_id] = sum(scores) / len(scores)
            
            # Usage by event type and author
            usage_by_event_type = dict(Counter(event_types))
            usage_by_author = dict(Counter(authors))
            
            return KnowledgeUsageMetrics(
                total_retrievals=total_retrievals,
                unique_knowledge_items_used=unique_knowledge_items_used,
                average_similarity_score=average_similarity_score,
                most_used_knowledge=most_used_knowledge,
                knowledge_effectiveness=knowledge_effectiveness,
                usage_by_event_type=usage_by_event_type,
                usage_by_author=usage_by_author
            )
            
        except Exception as e:
            logger.error(f"Failed to calculate knowledge usage metrics: {str(e)}")
            return KnowledgeUsageMetrics(
                total_retrievals=0,
                unique_knowledge_items_used=0,
                average_similarity_score=0.0,
                most_used_knowledge=[],
                knowledge_effectiveness={},
                usage_by_event_type={},
                usage_by_author={}
            )
    
    def get_knowledge_recommendations(self, project_id: str, 
                                    usage_metrics: Optional[KnowledgeUsageMetrics] = None) -> List[str]:
        """
        Generate recommendations for improving knowledge base based on usage patterns.
        
        Args:
            project_id: Project identifier
            usage_metrics: Optional pre-calculated usage metrics
            
        Returns:
            List of recommendations
        """
        try:
            if not usage_metrics:
                usage_metrics = self.get_usage_metrics(project_id)
            
            recommendations = []
            
            # Low usage recommendations
            if usage_metrics.total_retrievals < 10:
                recommendations.append("Consider adding more domain knowledge to improve decision context")
            
            # Low similarity score recommendations
            if usage_metrics.average_similarity_score < 0.3:
                recommendations.append("Review knowledge content relevance - similarity scores are low")
            
            # Effectiveness recommendations
            low_effectiveness_items = [
                k_id for k_id, score in usage_metrics.knowledge_effectiveness.items()
                if score < 0.4
            ]
            if low_effectiveness_items:
                recommendations.append(f"Review and update {len(low_effectiveness_items)} knowledge items with low effectiveness scores")
            
            # Coverage recommendations
            if len(usage_metrics.usage_by_event_type) < 3:
                recommendations.append("Consider adding knowledge for more event types to improve coverage")
            
            # Author diversity recommendations
            if len(usage_metrics.usage_by_author) < 2:
                recommendations.append("Encourage knowledge contributions from multiple team members")
            
            # High-usage item recommendations
            if usage_metrics.most_used_knowledge:
                top_item = usage_metrics.most_used_knowledge[0]
                if top_item['usage_count'] > usage_metrics.total_retrievals * 0.5:
                    recommendations.append(f"Consider expanding on highly-used knowledge: '{top_item['title']}'")
            
            return recommendations or ["Knowledge usage patterns look healthy"]
            
        except Exception as e:
            logger.error(f"Failed to generate knowledge recommendations: {str(e)}")
            return ["Unable to generate recommendations at this time"]


# Global instance for the application
knowledge_analytics = KnowledgeAnalytics()