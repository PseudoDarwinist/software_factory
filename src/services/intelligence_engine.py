"""
Intelligence Engine - Graph-based Project Analysis and Recommendation System
Provides intelligent insights, recommendations, and pattern recognition
"""

import logging
import json
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from dataclasses import dataclass
from sqlalchemy import text, func
from sqlalchemy.exc import SQLAlchemyError

try:
    from ..models.base import db
    from ..models.project import Project
    from ..models.conversation import Conversation
    from ..models.system_map import SystemMap
    from ..services.graph_service import GraphService, ProjectGraphService
    from ..services.distributed_cache import get_distributed_cache
except ImportError:
    from models.base import db
    from models.project import Project
    from models.conversation import Conversation
    from models.system_map import SystemMap
    from services.graph_service import GraphService, ProjectGraphService
    from services.distributed_cache import get_distributed_cache

logger = logging.getLogger(__name__)


@dataclass
class ProjectInsight:
    """Project analysis insight"""
    insight_type: str
    title: str
    description: str
    confidence: float
    metadata: Dict[str, Any]
    created_at: datetime


@dataclass
class Recommendation:
    """Project recommendation"""
    recommendation_type: str
    title: str
    description: str
    target_project_id: Optional[int]
    confidence: float
    reasoning: str
    metadata: Dict[str, Any]
    created_at: datetime


class ProjectAnalyzer:
    """Analyzes individual projects for patterns and insights"""
    
    def __init__(self):
        self.cache = get_distributed_cache()
        
    def analyze_project_complexity(self, project_id: int) -> Dict[str, Any]:
        """Analyze project complexity based on graph relationships"""
        try:
            # Get project ecosystem
            ecosystem = ProjectGraphService.get_project_ecosystem(project_id, max_depth=3)
            
            if not ecosystem:
                return {'complexity_score': 0, 'factors': []}
            
            # Calculate complexity factors
            factors = {}
            
            # Entity diversity (how many different types of entities)
            entity_types = set()
            for entity in ecosystem.get('related_entities', []):
                entity_types.add(entity['entity_type'])
            factors['entity_diversity'] = len(entity_types)
            
            # Relationship density (connections per entity)
            total_entities = ecosystem.get('ecosystem_size', 1)
            total_relationships = len(ecosystem.get('related_entities', []))
            factors['relationship_density'] = total_relationships / max(total_entities, 1)
            
            # Conversation complexity (number of conversations and their depth)
            conversations = [e for e in ecosystem.get('related_entities', []) 
                           if e['entity_type'] == 'conversation']
            factors['conversation_count'] = len(conversations)
            
            # System map complexity
            system_maps = [e for e in ecosystem.get('related_entities', []) 
                          if e['entity_type'] == 'system_map']
            factors['system_map_count'] = len(system_maps)
            
            # Calculate overall complexity score (0-100)
            complexity_score = min(100, (
                factors['entity_diversity'] * 10 +
                factors['relationship_density'] * 15 +
                factors['conversation_count'] * 5 +
                factors['system_map_count'] * 20
            ))
            
            return {
                'complexity_score': complexity_score,
                'factors': factors,
                'ecosystem_size': total_entities,
                'centrality_score': ecosystem.get('centrality_metrics', {}).get('centrality_score', 0)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing project complexity for {project_id}: {e}")
            return {'complexity_score': 0, 'factors': {}}
    
    def extract_technology_stack(self, project_id: int) -> List[str]:
        """Extract technology stack from project conversations and system maps"""
        try:
            # Common technology patterns to look for
            tech_patterns = {
                'python': r'\b(python|django|flask|fastapi|sqlalchemy)\b',
                'javascript': r'\b(javascript|node\.?js|react|vue|angular)\b',
                'typescript': r'\b(typescript|ts)\b',
                'database': r'\b(postgresql|mysql|mongodb|redis|sqlite)\b',
                'cloud': r'\b(aws|azure|gcp|docker|kubernetes)\b',
                'frontend': r'\b(html|css|sass|tailwind|bootstrap)\b',
                'backend': r'\b(api|rest|graphql|microservices)\b',
                'ai_ml': r'\b(ai|ml|machine learning|neural|llm|gpt|claude)\b'
            }
            
            # Get project conversations
            conversations = Conversation.query.filter_by(project_id=project_id).all()
            
            # Combine all text content
            text_content = []
            for conv in conversations:
                if conv.messages:
                    for message in conv.messages:
                        if isinstance(message, dict) and 'content' in message:
                            text_content.append(message['content'].lower())
                        elif isinstance(message, str):
                            text_content.append(message.lower())
            
            # Get system maps
            system_maps = SystemMap.query.filter_by(project_id=project_id).all()
            for sys_map in system_maps:
                if sys_map.map_data:
                    text_content.append(str(sys_map.map_data).lower())
            
            combined_text = ' '.join(text_content)
            
            # Extract technologies
            detected_technologies = []
            for tech_category, pattern in tech_patterns.items():
                matches = re.findall(pattern, combined_text, re.IGNORECASE)
                if matches:
                    detected_technologies.extend(list(set(matches)))
            
            return list(set(detected_technologies))
            
        except Exception as e:
            logger.error(f"Error extracting technology stack for {project_id}: {e}")
            return []
    
    def analyze_project_activity(self, project_id: int) -> Dict[str, Any]:
        """Analyze project activity patterns"""
        try:
            # Get recent conversations
            recent_conversations = Conversation.query.filter(
                Conversation.project_id == project_id,
                Conversation.created_at >= datetime.utcnow() - timedelta(days=30)
            ).all()
            
            # Calculate activity metrics
            activity_score = len(recent_conversations) * 10
            
            # Check for recent system maps
            recent_system_maps = SystemMap.query.filter(
                SystemMap.project_id == project_id,
                SystemMap.created_at >= datetime.utcnow() - timedelta(days=30)
            ).count()
            
            activity_score += recent_system_maps * 20
            
            # Determine activity level
            if activity_score >= 100:
                activity_level = 'high'
            elif activity_score >= 50:
                activity_level = 'medium'
            elif activity_score >= 10:
                activity_level = 'low'
            else:
                activity_level = 'dormant'
            
            return {
                'activity_score': min(100, activity_score),
                'activity_level': activity_level,
                'recent_conversations': len(recent_conversations),
                'recent_system_maps': recent_system_maps
            }
            
        except Exception as e:
            logger.error(f"Error analyzing project activity for {project_id}: {e}")
            return {'activity_score': 0, 'activity_level': 'dormant'}


class RecommendationEngine:
    """Generates intelligent recommendations based on graph analysis"""
    
    def __init__(self):
        self.cache = get_distributed_cache()
        self.analyzer = ProjectAnalyzer()
    
    def find_similar_projects(self, project_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """Find projects similar to the given project"""
        try:
            # Get target project technology stack
            target_tech = self.analyzer.extract_technology_stack(project_id)
            target_complexity = self.analyzer.analyze_project_complexity(project_id)
            
            if not target_tech:
                return []
            
            # Get all other projects
            all_projects = Project.query.filter(Project.id != project_id).all()
            
            similarities = []
            for project in all_projects:
                # Get project technology stack
                project_tech = self.analyzer.extract_technology_stack(project.id)
                project_complexity = self.analyzer.analyze_project_complexity(project.id)
                
                if not project_tech:
                    continue
                
                # Calculate technology similarity (Jaccard similarity)
                common_tech = set(target_tech) & set(project_tech)
                total_tech = set(target_tech) | set(project_tech)
                tech_similarity = len(common_tech) / len(total_tech) if total_tech else 0
                
                # Calculate complexity similarity
                target_score = target_complexity.get('complexity_score', 0)
                project_score = project_complexity.get('complexity_score', 0)
                complexity_diff = abs(target_score - project_score)
                complexity_similarity = max(0, 1 - (complexity_diff / 100))
                
                # Combined similarity score
                overall_similarity = (tech_similarity * 0.7 + complexity_similarity * 0.3)
                
                if overall_similarity > 0.1:  # Minimum threshold
                    similarities.append({
                        'project': project,
                        'similarity_score': overall_similarity,
                        'common_technologies': list(common_tech),
                        'tech_similarity': tech_similarity,
                        'complexity_similarity': complexity_similarity
                    })
            
            # Sort by similarity and return top results
            similarities.sort(key=lambda x: x['similarity_score'], reverse=True)
            return similarities[:limit]
            
        except Exception as e:
            logger.error(f"Error finding similar projects for {project_id}: {e}")
            return []
    
    def generate_project_recommendations(self, project_id: int) -> List[Recommendation]:
        """Generate comprehensive recommendations for a project"""
        recommendations = []
        
        try:
            # Get project analysis
            complexity = self.analyzer.analyze_project_complexity(project_id)
            activity = self.analyzer.analyze_project_activity(project_id)
            technologies = self.analyzer.extract_technology_stack(project_id)
            similar_projects = self.find_similar_projects(project_id)
            
            # Recommendation 1: Complexity management
            if complexity['complexity_score'] > 70:
                recommendations.append(Recommendation(
                    recommendation_type='complexity_management',
                    title='Consider Breaking Down Complex Project',
                    description=f'This project has a high complexity score ({complexity["complexity_score"]}/100). Consider breaking it into smaller, more manageable components.',
                    target_project_id=project_id,
                    confidence=0.8,
                    reasoning=f'High complexity detected: {complexity["factors"]}',
                    metadata={'complexity_analysis': complexity},
                    created_at=datetime.utcnow()
                ))
            
            # Recommendation 2: Activity-based suggestions
            if activity['activity_level'] == 'dormant':
                recommendations.append(Recommendation(
                    recommendation_type='reactivation',
                    title='Reactivate Dormant Project',
                    description='This project has been dormant. Consider reviewing and updating its status or archiving if no longer needed.',
                    target_project_id=project_id,
                    confidence=0.7,
                    reasoning=f'No recent activity: {activity}',
                    metadata={'activity_analysis': activity},
                    created_at=datetime.utcnow()
                ))
            elif activity['activity_level'] == 'high':
                recommendations.append(Recommendation(
                    recommendation_type='optimization',
                    title='High Activity Project - Consider Optimization',
                    description='This project has high activity. Consider optimizing workflows or adding automation to improve efficiency.',
                    target_project_id=project_id,
                    confidence=0.6,
                    reasoning=f'High activity detected: {activity}',
                    metadata={'activity_analysis': activity},
                    created_at=datetime.utcnow()
                ))
            
            # Recommendation 3: Similar projects
            if similar_projects:
                top_similar = similar_projects[0]
                recommendations.append(Recommendation(
                    recommendation_type='similar_project',
                    title=f'Explore Similar Project: {top_similar["project"].name}',
                    description=f'Found a similar project with {top_similar["similarity_score"]:.1%} similarity. Common technologies: {", ".join(top_similar["common_technologies"])}',
                    target_project_id=top_similar["project"].id,
                    confidence=top_similar["similarity_score"],
                    reasoning=f'Technology and complexity similarity analysis',
                    metadata={'similarity_analysis': top_similar},
                    created_at=datetime.utcnow()
                ))
            
            # Recommendation 4: Technology stack suggestions
            if 'ai' in ' '.join(technologies).lower() and 'database' not in ' '.join(technologies).lower():
                recommendations.append(Recommendation(
                    recommendation_type='technology_stack',
                    title='Consider Adding Vector Database',
                    description='AI projects often benefit from vector databases for semantic search and context management.',
                    target_project_id=project_id,
                    confidence=0.6,
                    reasoning='AI technology detected without specialized database',
                    metadata={'detected_technologies': technologies},
                    created_at=datetime.utcnow()
                ))
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations for {project_id}: {e}")
            return []
    
    def generate_insights(self, project_id: int) -> List[ProjectInsight]:
        """Generate analytical insights about a project"""
        insights = []
        
        try:
            # Get project ecosystem
            ecosystem = ProjectGraphService.get_project_ecosystem(project_id, max_depth=2)
            complexity = self.analyzer.analyze_project_complexity(project_id)
            technologies = self.analyzer.extract_technology_stack(project_id)
            
            # Insight 1: Ecosystem overview
            if ecosystem:
                insights.append(ProjectInsight(
                    insight_type='ecosystem_overview',
                    title='Project Ecosystem Analysis',
                    description=f'This project has {ecosystem["ecosystem_size"]} connected entities with a centrality score of {ecosystem.get("centrality_metrics", {}).get("centrality_score", 0):.2f}',
                    confidence=0.9,
                    metadata={'ecosystem': ecosystem},
                    created_at=datetime.utcnow()
                ))
            
            # Insight 2: Technology diversity
            if technologies:
                tech_diversity = len(set(technologies))
                insights.append(ProjectInsight(
                    insight_type='technology_analysis',
                    title=f'Technology Stack Diversity: {tech_diversity} Technologies',
                    description=f'Detected technologies: {", ".join(technologies[:5])}{"..." if len(technologies) > 5 else ""}',
                    confidence=0.8,
                    metadata={'technologies': technologies, 'diversity_score': tech_diversity},
                    created_at=datetime.utcnow()
                ))
            
            # Insight 3: Relationship patterns
            if ecosystem and ecosystem.get('related_entities'):
                entity_types = Counter([e['entity_type'] for e in ecosystem['related_entities']])
                dominant_type = entity_types.most_common(1)[0] if entity_types else None
                
                if dominant_type:
                    insights.append(ProjectInsight(
                        insight_type='relationship_pattern',
                        title=f'Dominant Entity Type: {dominant_type[0]}',
                        description=f'This project is heavily connected to {dominant_type[0]} entities ({dominant_type[1]} connections)',
                        confidence=0.7,
                        metadata={'entity_distribution': dict(entity_types)},
                        created_at=datetime.utcnow()
                    ))
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating insights for {project_id}: {e}")
            return []


class TrendAnalyzer:
    """Analyzes trends across projects and technologies"""
    
    def __init__(self):
        self.cache = get_distributed_cache()
        self.analyzer = ProjectAnalyzer()
    
    def analyze_technology_trends(self, days: int = 90) -> Dict[str, Any]:
        """Analyze technology adoption trends over time"""
        try:
            # Get projects created in the specified timeframe
            since_date = datetime.utcnow() - timedelta(days=days)
            recent_projects = Project.query.filter(Project.created_at >= since_date).all()
            
            if not recent_projects:
                return {'trends': [], 'total_projects': 0}
            
            # Extract technologies for each project
            technology_timeline = []
            for project in recent_projects:
                technologies = self.analyzer.extract_technology_stack(project.id)
                for tech in technologies:
                    technology_timeline.append({
                        'technology': tech,
                        'project_id': project.id,
                        'created_at': project.created_at
                    })
            
            # Analyze trends
            tech_counts = Counter([item['technology'] for item in technology_timeline])
            
            # Calculate growth rates (simplified)
            trends = []
            for tech, count in tech_counts.most_common(10):
                trend_data = {
                    'technology': tech,
                    'usage_count': count,
                    'adoption_rate': (count / len(recent_projects)) * 100,
                    'projects': [item['project_id'] for item in technology_timeline if item['technology'] == tech]
                }
                trends.append(trend_data)
            
            return {
                'trends': trends,
                'total_projects': len(recent_projects),
                'analysis_period_days': days,
                'most_popular': trends[0]['technology'] if trends else None
            }
            
        except Exception as e:
            logger.error(f"Error analyzing technology trends: {e}")
            return {'trends': [], 'total_projects': 0}
    
    def analyze_project_patterns(self) -> Dict[str, Any]:
        """Analyze patterns across all projects"""
        try:
            all_projects = Project.query.all()
            
            if not all_projects:
                return {'patterns': {}}
            
            patterns = {
                'total_projects': len(all_projects),
                'complexity_distribution': {},
                'activity_distribution': {},
                'technology_diversity': {},
                'creation_timeline': {}
            }
            
            # Analyze each project
            for project in all_projects:
                # Complexity distribution
                complexity = self.analyzer.analyze_project_complexity(project.id)
                score = complexity.get('complexity_score', 0)
                if score < 25:
                    complexity_level = 'low'
                elif score < 50:
                    complexity_level = 'medium'
                elif score < 75:
                    complexity_level = 'high'
                else:
                    complexity_level = 'very_high'
                
                patterns['complexity_distribution'][complexity_level] = patterns['complexity_distribution'].get(complexity_level, 0) + 1
                
                # Activity distribution
                activity = self.analyzer.analyze_project_activity(project.id)
                activity_level = activity.get('activity_level', 'dormant')
                patterns['activity_distribution'][activity_level] = patterns['activity_distribution'].get(activity_level, 0) + 1
                
                # Technology diversity
                technologies = self.analyzer.extract_technology_stack(project.id)
                tech_count = len(technologies)
                if tech_count == 0:
                    diversity_level = 'none'
                elif tech_count <= 2:
                    diversity_level = 'low'
                elif tech_count <= 5:
                    diversity_level = 'medium'
                else:
                    diversity_level = 'high'
                
                patterns['technology_diversity'][diversity_level] = patterns['technology_diversity'].get(diversity_level, 0) + 1
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error analyzing project patterns: {e}")
            return {'patterns': {}}


# Global instances
intelligence_engine = None
recommendation_engine = None
trend_analyzer = None


def get_intelligence_engine():
    """Get global intelligence engine instance"""
    global intelligence_engine
    if intelligence_engine is None:
        intelligence_engine = ProjectAnalyzer()
    return intelligence_engine


def get_recommendation_engine():
    """Get global recommendation engine instance"""
    global recommendation_engine
    if recommendation_engine is None:
        recommendation_engine = RecommendationEngine()
    return recommendation_engine


def get_trend_analyzer():
    """Get global trend analyzer instance"""
    global trend_analyzer
    if trend_analyzer is None:
        trend_analyzer = TrendAnalyzer()
    return trend_analyzer