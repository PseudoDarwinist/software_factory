"""
Graph Service - PostgreSQL Graph Query Operations
Handles entity relationships and graph traversal queries
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

# Handle both relative and absolute imports
try:
    from ..models.base import db
except ImportError:
    try:
        from models.base import db
    except ImportError:
        # For testing - will be mocked
        db = None

logger = logging.getLogger(__name__)


class GraphService:
    """Service for managing entity relationships and graph queries"""
    
    # Entity types
    ENTITY_PROJECT = 'project'
    ENTITY_MISSION_CONTROL_PROJECT = 'mission_control_project'
    ENTITY_CONVERSATION = 'conversation'
    ENTITY_SYSTEM_MAP = 'system_map'
    ENTITY_BACKGROUND_JOB = 'background_job'
    ENTITY_STAGE = 'stage'
    ENTITY_FEED_ITEM = 'feed_item'
    ENTITY_IDEA = 'idea'  # Feed items with kind='idea'
    ENTITY_SPEC = 'spec'  # Specification documents (requirements.md, design.md, tasks.md)
    ENTITY_TASK = 'task'  # Individual tasks from specifications
    ENTITY_COMMIT = 'commit'  # Git commits
    ENTITY_TEAM_MEMBER = 'team_member'  # Team members and contributors
    ENTITY_PRODUCT_BRIEF = 'product_brief'  # Product briefs from Define stage
    
    # Relationship types (matching PostgreSQL enum)
    REL_DEPENDS_ON = 'depends_on'
    REL_CONTAINS = 'contains'
    REL_IMPLEMENTS = 'implements'
    REL_EXTENDS = 'extends'
    REL_CALLS = 'calls'
    REL_IMPORTS = 'imports'
    REL_REFERENCES = 'references'
    REL_OWNS = 'owns'
    REL_MANAGES = 'manages'
    REL_TRIGGERS = 'triggers'
    REL_PROMOTES_TO = 'promotes_to'  # idea -> spec
    REL_BREAKS_DOWN_TO = 'breaks_down_to'  # spec -> task
    REL_AUTHORED_BY = 'authored_by'  # commit -> team_member
    REL_CONTRIBUTES_TO = 'contributes_to'  # team_member -> project/file
    REL_EXPERTISE_IN = 'expertise_in'  # team_member -> technology/domain
    REL_ASSIGNED_TO = 'assigned_to'  # task -> team_member
    REL_DERIVED_FROM = 'derived_from'  # spec -> idea
    REL_ADDRESSES = 'addresses'  # commit -> task
    
    @staticmethod
    def add_relationship(
        source_entity_type: str,
        source_entity_id: str,
        target_entity_type: str,
        target_entity_id: str,
        relationship_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        weight: float = 1.0
    ) -> bool:
        """Add a relationship between two entities"""
        try:
            import json
            
            query = text("""
                INSERT INTO entity_relationships 
                (source_entity_type, source_entity_id, target_entity_type, target_entity_id, 
                 relationship_type, metadata, weight)
                VALUES (:source_type, :source_id, :target_type, :target_id, 
                        :rel_type, CAST(:metadata AS jsonb), :weight)
                ON CONFLICT (source_entity_type, source_entity_id, target_entity_type, target_entity_id, relationship_type)
                DO UPDATE SET 
                    metadata = EXCLUDED.metadata,
                    weight = EXCLUDED.weight,
                    updated_at = NOW()
            """)
            
            db.session.execute(query, {
                'source_type': source_entity_type,
                'source_id': str(source_entity_id),
                'target_type': target_entity_type,
                'target_id': str(target_entity_id),
                'rel_type': relationship_type,
                'metadata': json.dumps(metadata or {}),
                'weight': weight
            })
            db.session.commit()
            
            logger.info(f"Added relationship: {source_entity_type}:{source_entity_id} -> {target_entity_type}:{target_entity_id} ({relationship_type})")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to add relationship: {e}")
            db.session.rollback()
            return False
    
    @staticmethod
    def remove_relationship(
        source_entity_type: str,
        source_entity_id: str,
        target_entity_type: str,
        target_entity_id: str,
        relationship_type: Optional[str] = None
    ) -> bool:
        """Remove relationship(s) between two entities"""
        try:
            if relationship_type:
                query = text("""
                    DELETE FROM entity_relationships 
                    WHERE source_entity_type = :source_type 
                        AND source_entity_id = :source_id
                        AND target_entity_type = :target_type 
                        AND target_entity_id = :target_id
                        AND relationship_type = :rel_type
                """)
                params = {
                    'source_type': source_entity_type,
                    'source_id': str(source_entity_id),
                    'target_type': target_entity_type,
                    'target_id': str(target_entity_id),
                    'rel_type': relationship_type
                }
            else:
                query = text("""
                    DELETE FROM entity_relationships 
                    WHERE source_entity_type = :source_type 
                        AND source_entity_id = :source_id
                        AND target_entity_type = :target_type 
                        AND target_entity_id = :target_id
                """)
                params = {
                    'source_type': source_entity_type,
                    'source_id': str(source_entity_id),
                    'target_type': target_entity_type,
                    'target_id': str(target_entity_id)
                }
            
            result = db.session.execute(query, params)
            db.session.commit()
            
            logger.info(f"Removed {result.rowcount} relationship(s)")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to remove relationship: {e}")
            db.session.rollback()
            return False
    
    @staticmethod
    def find_related_entities(
        entity_type: str,
        entity_id: str,
        relationship_types: Optional[List[str]] = None,
        max_depth: int = 3,
        direction: str = 'both'
    ) -> List[Dict[str, Any]]:
        """Find entities related to the given entity"""
        try:
            query = text("""
                SELECT * FROM find_related_entities(
                    :entity_type, :entity_id, :rel_types, :max_depth, :direction
                )
            """)
            
            result = db.session.execute(query, {
                'entity_type': entity_type,
                'entity_id': str(entity_id),
                'rel_types': relationship_types,
                'max_depth': max_depth,
                'direction': direction
            })
            
            relationships = []
            for row in result:
                relationships.append({
                    'entity_type': row.entity_type,
                    'entity_id': row.entity_id,
                    'relationship_path': list(row.relationship_path),
                    'depth': row.depth,
                    'total_weight': float(row.total_weight)
                })
            
            logger.info(f"Found {len(relationships)} related entities for {entity_type}:{entity_id}")
            return relationships
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to find related entities: {e}")
            return []
    
    @staticmethod
    def find_shortest_path(
        source_type: str,
        source_id: str,
        target_type: str,
        target_id: str,
        max_depth: int = 5
    ) -> Optional[Dict[str, Any]]:
        """Find shortest path between two entities"""
        try:
            query = text("""
                SELECT * FROM find_shortest_path(
                    :source_type, :source_id, :target_type, :target_id, :max_depth
                )
            """)
            
            result = db.session.execute(query, {
                'source_type': source_type,
                'source_id': str(source_id),
                'target_type': target_type,
                'target_id': str(target_id),
                'max_depth': max_depth
            })
            
            row = result.fetchone()
            if row:
                return {
                    'path_length': row.path_length,
                    'relationship_path': list(row.relationship_path),
                    'entity_path': list(row.entity_path),
                    'total_weight': float(row.total_weight)
                }
            
            return None
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to find shortest path: {e}")
            return None
    
    @staticmethod
    def calculate_entity_centrality(
        entity_type: str,
        entity_id: str
    ) -> Optional[Dict[str, Any]]:
        """Calculate centrality metrics for an entity"""
        try:
            query = text("""
                SELECT * FROM calculate_entity_centrality(:entity_type, :entity_id)
            """)
            
            result = db.session.execute(query, {
                'entity_type': entity_type,
                'entity_id': str(entity_id)
            })
            
            row = result.fetchone()
            if row:
                return {
                    'in_degree': row.in_degree,
                    'out_degree': row.out_degree,
                    'total_degree': row.total_degree,
                    'weighted_in_degree': float(row.weighted_in_degree),
                    'weighted_out_degree': float(row.weighted_out_degree),
                    'centrality_score': float(row.centrality_score)
                }
            
            return None
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to calculate centrality: {e}")
            return None
    
    @staticmethod
    def get_entity_relationships(
        entity_id: str,
        entity_type: str = "project",
        include_incoming: bool = True,
        include_outgoing: bool = True
    ) -> Dict[str, Any]:
        """
        Get entity relationships (simplified interface for agents).
        
        Args:
            entity_id: Entity identifier
            entity_type: Type of entity (default: project)
            include_incoming: Include incoming relationships
            include_outgoing: Include outgoing relationships
            
        Returns:
            Dictionary with relationship information
        """
        try:
            relationships = GraphService._get_direct_relationships(
                entity_type, entity_id, include_incoming, include_outgoing
            )
            
            # Group relationships by type
            grouped = {}
            for rel in relationships:
                rel_type = rel['relationship_type']
                if rel_type not in grouped:
                    grouped[rel_type] = []
                grouped[rel_type].append(rel)
            
            return {
                'entity_id': entity_id,
                'entity_type': entity_type,
                'total_relationships': len(relationships),
                'relationships_by_type': grouped,
                'all_relationships': relationships
            }
            
        except Exception as e:
            logger.error(f"Failed to get entity relationships: {e}")
            return {
                'entity_id': entity_id,
                'entity_type': entity_type,
                'total_relationships': 0,
                'relationships_by_type': {},
                'all_relationships': []
            }
    
    @staticmethod
    def _get_direct_relationships(
        entity_type: str,
        entity_id: str,
        include_incoming: bool = True,
        include_outgoing: bool = True
    ) -> List[Dict[str, Any]]:
        """Get all direct relationships for an entity (internal method)"""
        try:
            conditions = []
            params = {'entity_type': entity_type, 'entity_id': str(entity_id)}
            
            if include_outgoing:
                conditions.append("(source_entity_type = :entity_type AND source_entity_id = :entity_id)")
            
            if include_incoming:
                conditions.append("(target_entity_type = :entity_type AND target_entity_id = :entity_id)")
            
            if not conditions:
                return []
            
            query = text(f"""
                SELECT 
                    source_entity_type,
                    source_entity_id,
                    target_entity_type,
                    target_entity_id,
                    relationship_type,
                    metadata,
                    weight,
                    created_at,
                    updated_at
                FROM entity_relationships 
                WHERE {' OR '.join(conditions)}
                ORDER BY created_at DESC
            """)
            
            result = db.session.execute(query, params)
            
            relationships = []
            for row in result:
                relationships.append({
                    'source_entity_type': row.source_entity_type,
                    'source_entity_id': row.source_entity_id,
                    'target_entity_type': row.target_entity_type,
                    'target_entity_id': row.target_entity_id,
                    'relationship_type': row.relationship_type,
                    'metadata': row.metadata,
                    'weight': float(row.weight),
                    'created_at': row.created_at.isoformat(),
                    'updated_at': row.updated_at.isoformat()
                })
            
            return relationships
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get entity relationships: {e}")
            return []
    
    @staticmethod
    def remove_entity_relationships(entity_type: str, entity_id: str) -> bool:
        """Remove all relationships for an entity (cleanup when entity is deleted)"""
        try:
            query = text("""
                DELETE FROM entity_relationships 
                WHERE (source_entity_type = :entity_type AND source_entity_id = :entity_id)
                   OR (target_entity_type = :entity_type AND target_entity_id = :entity_id)
            """)
            
            result = db.session.execute(query, {
                'entity_type': entity_type,
                'entity_id': str(entity_id)
            })
            db.session.commit()
            
            logger.info(f"Removed {result.rowcount} relationships for {entity_type}:{entity_id}")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to remove entity relationships: {e}")
            db.session.rollback()
            return False
    
    @staticmethod
    def get_relationship_statistics() -> Dict[str, Any]:
        """Get overall relationship statistics"""
        try:
            query = text("""
                SELECT 
                    COUNT(*) as total_relationships,
                    COUNT(DISTINCT source_entity_type || ':' || source_entity_id) as unique_source_entities,
                    COUNT(DISTINCT target_entity_type || ':' || target_entity_id) as unique_target_entities,
                    COUNT(DISTINCT relationship_type) as unique_relationship_types,
                    AVG(weight) as average_weight
                FROM entity_relationships
            """)
            
            result = db.session.execute(query)
            row = result.fetchone()
            
            if row:
                return {
                    'total_relationships': row.total_relationships,
                    'unique_source_entities': row.unique_source_entities,
                    'unique_target_entities': row.unique_target_entities,
                    'unique_relationship_types': row.unique_relationship_types,
                    'average_weight': float(row.average_weight) if row.average_weight else 0.0
                }
            
            return {}
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get relationship statistics: {e}")
            return {}

    @staticmethod
    def get_idea_relationships(idea_id: str) -> Dict[str, Any]:
        """Get relationships for an idea (feed item with kind='idea')"""
        return GraphService.get_entity_relationships(
            entity_id=idea_id,
            entity_type=GraphService.ENTITY_IDEA
        )

    @staticmethod
    def get_spec_dependencies(spec_id: str) -> Dict[str, Any]:
        """Get dependencies and relationships for a specification"""
        relationships = GraphService.get_entity_relationships(
            entity_id=spec_id,
            entity_type=GraphService.ENTITY_SPEC
        )
        
        # Find related ideas, tasks, and team members
        related_entities = GraphService.find_related_entities(
            entity_type=GraphService.ENTITY_SPEC,
            entity_id=spec_id,
            relationship_types=[
                GraphService.REL_DERIVED_FROM,
                GraphService.REL_BREAKS_DOWN_TO,
                GraphService.REL_AUTHORED_BY
            ],
            max_depth=2
        )
        
        return {
            'spec_id': spec_id,
            'direct_relationships': relationships,
            'related_entities': related_entities,
            'dependency_graph': GraphService._build_dependency_graph(spec_id, GraphService.ENTITY_SPEC)
        }

    @staticmethod
    def get_task_connections(task_id: str) -> Dict[str, Any]:
        """Get connections for a task including assignees, related code, and dependencies"""
        relationships = GraphService.get_entity_relationships(
            entity_id=task_id,
            entity_type=GraphService.ENTITY_TASK
        )
        
        # Find related specs, commits, and team members
        related_entities = GraphService.find_related_entities(
            entity_type=GraphService.ENTITY_TASK,
            entity_id=task_id,
            relationship_types=[
                GraphService.REL_DERIVED_FROM,
                GraphService.REL_ASSIGNED_TO,
                GraphService.REL_ADDRESSES
            ],
            max_depth=2
        )
        
        return {
            'task_id': task_id,
            'direct_relationships': relationships,
            'related_entities': related_entities,
            'assignees': GraphService._get_task_assignees(task_id),
            'related_commits': GraphService._get_task_commits(task_id)
        }

    @staticmethod
    def get_team_expertise(project_id: str) -> Dict[str, Any]:
        """Analyze team expertise using Git blame and contribution history"""
        try:
            # Get all team members for the project
            team_members = GraphService._get_project_team_members(project_id)
            
            expertise_analysis = {}
            for member in team_members:
                member_id = member['member_id']
                
                # Get contribution patterns
                contributions = GraphService._analyze_member_contributions(member_id, project_id)
                
                # Get expertise areas based on file types and domains
                expertise_areas = GraphService._analyze_member_expertise(member_id, project_id)
                
                # Calculate expertise scores
                expertise_scores = GraphService._calculate_expertise_scores(member_id, project_id)
                
                expertise_analysis[member_id] = {
                    'member_info': member,
                    'contributions': contributions,
                    'expertise_areas': expertise_areas,
                    'expertise_scores': expertise_scores,
                    'suggested_tasks': GraphService._suggest_tasks_for_member(member_id, project_id)
                }
            
            return {
                'project_id': project_id,
                'team_size': len(team_members),
                'expertise_analysis': expertise_analysis,
                'team_coverage': GraphService._analyze_team_coverage(project_id),
                'collaboration_patterns': GraphService._analyze_collaboration_patterns(project_id)
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze team expertise: {e}")
            return {
                'project_id': project_id,
                'team_size': 0,
                'expertise_analysis': {},
                'team_coverage': {},
                'collaboration_patterns': {}
            }

    @staticmethod
    def create_relationship(from_entity: str, to_entity: str, rel_type: str, 
                          from_type: str = None, to_type: str = None, 
                          metadata: Dict[str, Any] = None, weight: float = 1.0) -> bool:
        """Create a relationship between two entities (convenience method)"""
        # Parse entity strings if they contain type:id format
        if ':' in from_entity and from_type is None:
            from_type, from_entity = from_entity.split(':', 1)
        if ':' in to_entity and to_type is None:
            to_type, to_entity = to_entity.split(':', 1)
        
        if not from_type or not to_type:
            logger.error("Entity types must be specified")
            return False
        
        return GraphService.add_relationship(
            source_entity_type=from_type,
            source_entity_id=from_entity,
            target_entity_type=to_type,
            target_entity_id=to_entity,
            relationship_type=rel_type,
            metadata=metadata,
            weight=weight
        )

    @staticmethod
    def get_visualization_data(entity_type: str, entity_id: str, max_depth: int = 2) -> Dict[str, Any]:
        """Get relationship data formatted for UI visualization"""
        try:
            # Get the central entity
            central_node = {
                'id': f"{entity_type}:{entity_id}",
                'type': entity_type,
                'entity_id': entity_id,
                'label': GraphService._get_entity_label(entity_type, entity_id),
                'central': True
            }
            
            # Get related entities
            related_entities = GraphService.find_related_entities(
                entity_type=entity_type,
                entity_id=entity_id,
                max_depth=max_depth
            )
            
            # Build nodes and edges for visualization
            nodes = [central_node]
            edges = []
            
            for entity in related_entities:
                node_id = f"{entity['entity_type']}:{entity['entity_id']}"
                
                # Add node if not already present
                if not any(n['id'] == node_id for n in nodes):
                    nodes.append({
                        'id': node_id,
                        'type': entity['entity_type'],
                        'entity_id': entity['entity_id'],
                        'label': GraphService._get_entity_label(entity['entity_type'], entity['entity_id']),
                        'depth': entity['depth'],
                        'weight': entity['total_weight']
                    })
                
                # Add edges from relationship path
                if entity['relationship_path']:
                    for i, rel_type in enumerate(entity['relationship_path']):
                        if i == 0:
                            source_id = f"{entity_type}:{entity_id}"
                            target_id = node_id
                        else:
                            # For multi-hop relationships, we'd need more path info
                            continue
                        
                        edges.append({
                            'id': f"{source_id}-{target_id}-{rel_type}",
                            'source': source_id,
                            'target': target_id,
                            'type': rel_type,
                            'weight': entity['total_weight'],
                            'label': rel_type.replace('_', ' ').title()
                        })
            
            return {
                'nodes': nodes,
                'edges': edges,
                'central_entity': central_node,
                'total_nodes': len(nodes),
                'total_edges': len(edges),
                'max_depth': max_depth
            }
            
        except Exception as e:
            logger.error(f"Failed to get visualization data: {e}")
            return {
                'nodes': [central_node] if 'central_node' in locals() else [],
                'edges': [],
                'central_entity': central_node if 'central_node' in locals() else None,
                'total_nodes': 0,
                'total_edges': 0,
                'max_depth': max_depth
            }

    # Helper methods for team expertise analysis
    @staticmethod
    def _get_project_team_members(project_id: str) -> List[Dict[str, Any]]:
        """Get team members associated with a project"""
        try:
            query = text("""
                SELECT DISTINCT 
                    target_entity_id as member_id,
                    metadata->>'name' as name,
                    metadata->>'email' as email,
                    COUNT(*) as relationship_count,
                    MAX(weight) as max_weight
                FROM entity_relationships 
                WHERE source_entity_type = :project_type 
                    AND source_entity_id = :project_id
                    AND target_entity_type = :member_type
                    AND relationship_type IN (:contributes, :owns, :manages)
                GROUP BY target_entity_id, metadata->>'name', metadata->>'email'
                ORDER BY relationship_count DESC, max_weight DESC
            """)
            
            result = db.session.execute(query, {
                'project_type': GraphService.ENTITY_PROJECT,
                'project_id': project_id,
                'member_type': GraphService.ENTITY_TEAM_MEMBER,
                'contributes': GraphService.REL_CONTRIBUTES_TO,
                'owns': GraphService.REL_OWNS,
                'manages': GraphService.REL_MANAGES
            })
            
            members = []
            for row in result:
                members.append({
                    'member_id': row.member_id,
                    'name': row.name or row.member_id,
                    'email': row.email,
                    'relationship_count': row.relationship_count,
                    'max_weight': float(row.max_weight) if row.max_weight else 0.0
                })
            
            return members
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get project team members: {e}")
            return []

    @staticmethod
    def _analyze_member_contributions(member_id: str, project_id: str) -> Dict[str, Any]:
        """Analyze a team member's contributions to a project"""
        try:
            # Get commits authored by this member
            commit_query = text("""
                SELECT 
                    source_entity_id as commit_id,
                    metadata->>'message' as commit_message,
                    metadata->>'timestamp' as commit_timestamp,
                    metadata->>'files_changed' as files_changed,
                    weight
                FROM entity_relationships 
                WHERE source_entity_type = :commit_type
                    AND target_entity_type = :member_type
                    AND target_entity_id = :member_id
                    AND relationship_type = :authored_by
                ORDER BY metadata->>'timestamp' DESC
                LIMIT 100
            """)
            
            result = db.session.execute(commit_query, {
                'commit_type': GraphService.ENTITY_COMMIT,
                'member_type': GraphService.ENTITY_TEAM_MEMBER,
                'member_id': member_id,
                'authored_by': GraphService.REL_AUTHORED_BY
            })
            
            commits = []
            total_weight = 0.0
            file_types = {}
            
            for row in result:
                commit_data = {
                    'commit_id': row.commit_id,
                    'message': row.commit_message,
                    'timestamp': row.commit_timestamp,
                    'files_changed': row.files_changed,
                    'weight': float(row.weight) if row.weight else 0.0
                }
                commits.append(commit_data)
                total_weight += commit_data['weight']
                
                # Analyze file types
                if row.files_changed:
                    for file_path in row.files_changed:
                        ext = file_path.split('.')[-1] if '.' in file_path else 'no_ext'
                        file_types[ext] = file_types.get(ext, 0) + 1
            
            return {
                'total_commits': len(commits),
                'total_contribution_weight': total_weight,
                'recent_commits': commits[:10],
                'file_type_distribution': file_types,
                'average_commit_weight': total_weight / len(commits) if commits else 0.0
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to analyze member contributions: {e}")
            return {
                'total_commits': 0,
                'total_contribution_weight': 0.0,
                'recent_commits': [],
                'file_type_distribution': {},
                'average_commit_weight': 0.0
            }

    @staticmethod
    def _analyze_member_expertise(member_id: str, project_id: str) -> List[Dict[str, Any]]:
        """Analyze expertise areas for a team member"""
        try:
            query = text("""
                SELECT 
                    target_entity_id as expertise_area,
                    metadata->>'domain' as domain,
                    metadata->>'technology' as technology,
                    metadata->>'confidence' as confidence,
                    weight,
                    COUNT(*) as evidence_count
                FROM entity_relationships 
                WHERE source_entity_type = :member_type
                    AND source_entity_id = :member_id
                    AND relationship_type = :expertise_in
                GROUP BY target_entity_id, metadata->>'domain', metadata->>'technology', metadata->>'confidence', weight
                ORDER BY weight DESC, evidence_count DESC
            """)
            
            result = db.session.execute(query, {
                'member_type': GraphService.ENTITY_TEAM_MEMBER,
                'member_id': member_id,
                'expertise_in': GraphService.REL_EXPERTISE_IN
            })
            
            expertise_areas = []
            for row in result:
                expertise_areas.append({
                    'area': row.expertise_area,
                    'domain': row.domain,
                    'technology': row.technology,
                    'confidence': float(row.confidence) if row.confidence else 0.0,
                    'weight': float(row.weight) if row.weight else 0.0,
                    'evidence_count': row.evidence_count
                })
            
            return expertise_areas
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to analyze member expertise: {e}")
            return []

    @staticmethod
    def _calculate_expertise_scores(member_id: str, project_id: str) -> Dict[str, float]:
        """Calculate expertise scores for different areas"""
        try:
            # This would typically involve more complex analysis of:
            # - Git blame data for code ownership
            # - Commit frequency and recency
            # - Code review participation
            # - Issue resolution patterns
            
            # For now, return a simplified calculation based on relationships
            query = text("""
                SELECT 
                    relationship_type,
                    COUNT(*) as count,
                    AVG(weight) as avg_weight,
                    SUM(weight) as total_weight
                FROM entity_relationships 
                WHERE source_entity_type = :member_type
                    AND source_entity_id = :member_id
                GROUP BY relationship_type
            """)
            
            result = db.session.execute(query, {
                'member_type': GraphService.ENTITY_TEAM_MEMBER,
                'member_id': member_id
            })
            
            scores = {}
            for row in result:
                rel_type = row.relationship_type
                score = float(row.total_weight) * (1 + float(row.count) * 0.1)
                scores[rel_type] = score
            
            # Calculate overall expertise score
            overall_score = sum(scores.values()) / len(scores) if scores else 0.0
            scores['overall'] = overall_score
            
            return scores
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to calculate expertise scores: {e}")
            return {'overall': 0.0}

    @staticmethod
    def _suggest_tasks_for_member(member_id: str, project_id: str) -> List[Dict[str, Any]]:
        """Suggest tasks that match a team member's expertise"""
        try:
            # Find unassigned tasks that match member's expertise areas
            query = text("""
                WITH member_expertise AS (
                    SELECT target_entity_id as expertise_area, weight
                    FROM entity_relationships 
                    WHERE source_entity_type = :member_type
                        AND source_entity_id = :member_id
                        AND relationship_type = :expertise_in
                ),
                available_tasks AS (
                    SELECT DISTINCT source_entity_id as task_id
                    FROM entity_relationships 
                    WHERE source_entity_type = :task_type
                        AND relationship_type = :references
                        AND target_entity_type = :project_type
                        AND target_entity_id = :project_id
                        AND source_entity_id NOT IN (
                            SELECT source_entity_id 
                            FROM entity_relationships 
                            WHERE relationship_type = :assigned_to
                        )
                )
                SELECT 
                    at.task_id,
                    me.expertise_area,
                    me.weight as expertise_weight
                FROM available_tasks at
                CROSS JOIN member_expertise me
                ORDER BY me.weight DESC
                LIMIT 10
            """)
            
            result = db.session.execute(query, {
                'member_type': GraphService.ENTITY_TEAM_MEMBER,
                'member_id': member_id,
                'task_type': GraphService.ENTITY_TASK,
                'project_type': GraphService.ENTITY_PROJECT,
                'project_id': project_id,
                'expertise_in': GraphService.REL_EXPERTISE_IN,
                'references': GraphService.REL_REFERENCES,
                'assigned_to': GraphService.REL_ASSIGNED_TO
            })
            
            suggestions = []
            for row in result:
                suggestions.append({
                    'task_id': row.task_id,
                    'matching_expertise': row.expertise_area,
                    'match_score': float(row.expertise_weight) if row.expertise_weight else 0.0
                })
            
            return suggestions
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to suggest tasks for member: {e}")
            return []

    @staticmethod
    def _analyze_team_coverage(project_id: str) -> Dict[str, Any]:
        """Analyze team coverage across different expertise areas"""
        try:
            query = text("""
                SELECT 
                    er.target_entity_id as expertise_area,
                    COUNT(DISTINCT er.source_entity_id) as team_members_count,
                    AVG(er.weight) as average_expertise_level,
                    MAX(er.weight) as max_expertise_level
                FROM entity_relationships er
                JOIN entity_relationships pr ON er.source_entity_id = pr.source_entity_id
                WHERE er.source_entity_type = :member_type
                    AND er.relationship_type = :expertise_in
                    AND pr.target_entity_type = :project_type
                    AND pr.target_entity_id = :project_id
                    AND pr.relationship_type IN (:contributes, :owns, :manages)
                GROUP BY er.target_entity_id
                ORDER BY team_members_count DESC, average_expertise_level DESC
            """)
            
            result = db.session.execute(query, {
                'member_type': GraphService.ENTITY_TEAM_MEMBER,
                'project_type': GraphService.ENTITY_PROJECT,
                'project_id': project_id,
                'expertise_in': GraphService.REL_EXPERTISE_IN,
                'contributes': GraphService.REL_CONTRIBUTES_TO,
                'owns': GraphService.REL_OWNS,
                'manages': GraphService.REL_MANAGES
            })
            
            coverage = {}
            total_areas = 0
            well_covered_areas = 0
            
            for row in result:
                area_coverage = {
                    'team_members_count': row.team_members_count,
                    'average_expertise_level': float(row.average_expertise_level) if row.average_expertise_level else 0.0,
                    'max_expertise_level': float(row.max_expertise_level) if row.max_expertise_level else 0.0,
                    'coverage_status': 'good' if row.team_members_count >= 2 else 'at_risk'
                }
                coverage[row.expertise_area] = area_coverage
                total_areas += 1
                if row.team_members_count >= 2:
                    well_covered_areas += 1
            
            return {
                'expertise_areas': coverage,
                'total_areas': total_areas,
                'well_covered_areas': well_covered_areas,
                'coverage_percentage': (well_covered_areas / total_areas * 100) if total_areas > 0 else 0.0,
                'at_risk_areas': [area for area, data in coverage.items() if data['coverage_status'] == 'at_risk']
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to analyze team coverage: {e}")
            return {
                'expertise_areas': {},
                'total_areas': 0,
                'well_covered_areas': 0,
                'coverage_percentage': 0.0,
                'at_risk_areas': []
            }

    @staticmethod
    def _analyze_collaboration_patterns(project_id: str) -> Dict[str, Any]:
        """Analyze collaboration patterns between team members"""
        try:
            # Find team members who have worked on similar tasks or commits
            query = text("""
                WITH project_members AS (
                    SELECT DISTINCT source_entity_id as member_id
                    FROM entity_relationships 
                    WHERE target_entity_type = :project_type
                        AND target_entity_id = :project_id
                        AND source_entity_type = :member_type
                        AND relationship_type IN (:contributes, :owns, :manages)
                ),
                member_collaborations AS (
                    SELECT 
                        er1.source_entity_id as member1,
                        er2.source_entity_id as member2,
                        COUNT(*) as shared_entities,
                        AVG(er1.weight + er2.weight) as collaboration_strength
                    FROM entity_relationships er1
                    JOIN entity_relationships er2 ON er1.target_entity_id = er2.target_entity_id
                        AND er1.target_entity_type = er2.target_entity_type
                        AND er1.source_entity_id < er2.source_entity_id
                    JOIN project_members pm1 ON er1.source_entity_id = pm1.member_id
                    JOIN project_members pm2 ON er2.source_entity_id = pm2.member_id
                    WHERE er1.source_entity_type = :member_type
                        AND er2.source_entity_type = :member_type
                    GROUP BY er1.source_entity_id, er2.source_entity_id
                    HAVING COUNT(*) > 1
                )
                SELECT * FROM member_collaborations
                ORDER BY collaboration_strength DESC, shared_entities DESC
                LIMIT 20
            """)
            
            result = db.session.execute(query, {
                'project_type': GraphService.ENTITY_PROJECT,
                'project_id': project_id,
                'member_type': GraphService.ENTITY_TEAM_MEMBER,
                'contributes': GraphService.REL_CONTRIBUTES_TO,
                'owns': GraphService.REL_OWNS,
                'manages': GraphService.REL_MANAGES
            })
            
            collaborations = []
            for row in result:
                collaborations.append({
                    'member1': row.member1,
                    'member2': row.member2,
                    'shared_entities': row.shared_entities,
                    'collaboration_strength': float(row.collaboration_strength) if row.collaboration_strength else 0.0
                })
            
            return {
                'collaborations': collaborations,
                'total_collaboration_pairs': len(collaborations),
                'average_collaboration_strength': sum(c['collaboration_strength'] for c in collaborations) / len(collaborations) if collaborations else 0.0
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to analyze collaboration patterns: {e}")
            return {
                'collaborations': [],
                'total_collaboration_pairs': 0,
                'average_collaboration_strength': 0.0
            }

    @staticmethod
    def _build_dependency_graph(entity_id: str, entity_type: str) -> Dict[str, Any]:
        """Build a dependency graph for an entity"""
        try:
            dependencies = GraphService.find_related_entities(
                entity_type=entity_type,
                entity_id=entity_id,
                relationship_types=[GraphService.REL_DEPENDS_ON, GraphService.REL_REFERENCES],
                max_depth=3
            )
            
            dependents = GraphService.find_related_entities(
                entity_type=entity_type,
                entity_id=entity_id,
                relationship_types=[GraphService.REL_DEPENDS_ON, GraphService.REL_REFERENCES],
                max_depth=3,
                direction='incoming'
            )
            
            return {
                'dependencies': dependencies,
                'dependents': dependents,
                'total_dependencies': len(dependencies),
                'total_dependents': len(dependents)
            }
            
        except Exception as e:
            logger.error(f"Failed to build dependency graph: {e}")
            return {
                'dependencies': [],
                'dependents': [],
                'total_dependencies': 0,
                'total_dependents': 0
            }

    @staticmethod
    def _get_task_assignees(task_id: str) -> List[Dict[str, Any]]:
        """Get assignees for a task"""
        try:
            query = text("""
                SELECT 
                    target_entity_id as member_id,
                    metadata->>'name' as name,
                    metadata->>'email' as email,
                    weight as assignment_weight,
                    created_at as assigned_at
                FROM entity_relationships 
                WHERE source_entity_type = :task_type
                    AND source_entity_id = :task_id
                    AND target_entity_type = :member_type
                    AND relationship_type = :assigned_to
                ORDER BY weight DESC, created_at ASC
            """)
            
            result = db.session.execute(query, {
                'task_type': GraphService.ENTITY_TASK,
                'task_id': task_id,
                'member_type': GraphService.ENTITY_TEAM_MEMBER,
                'assigned_to': GraphService.REL_ASSIGNED_TO
            })
            
            assignees = []
            for row in result:
                assignees.append({
                    'member_id': row.member_id,
                    'name': row.name or row.member_id,
                    'email': row.email,
                    'assignment_weight': float(row.assignment_weight) if row.assignment_weight else 1.0,
                    'assigned_at': row.assigned_at.isoformat() if row.assigned_at else None
                })
            
            return assignees
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get task assignees: {e}")
            return []

    @staticmethod
    def _get_task_commits(task_id: str) -> List[Dict[str, Any]]:
        """Get commits related to a task"""
        try:
            query = text("""
                SELECT 
                    source_entity_id as commit_id,
                    metadata->>'message' as commit_message,
                    metadata->>'author' as author,
                    metadata->>'timestamp' as commit_timestamp,
                    weight
                FROM entity_relationships 
                WHERE source_entity_type = :commit_type
                    AND target_entity_type = :task_type
                    AND target_entity_id = :task_id
                    AND relationship_type = :addresses
                ORDER BY metadata->>'timestamp' DESC
            """)
            
            result = db.session.execute(query, {
                'commit_type': GraphService.ENTITY_COMMIT,
                'task_type': GraphService.ENTITY_TASK,
                'task_id': task_id,
                'addresses': GraphService.REL_ADDRESSES
            })
            
            commits = []
            for row in result:
                commits.append({
                    'commit_id': row.commit_id,
                    'message': row.commit_message,
                    'author': row.author,
                    'timestamp': row.commit_timestamp,
                    'weight': float(row.weight) if row.weight else 1.0
                })
            
            return commits
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get task commits: {e}")
            return []

    @staticmethod
    def _get_entity_label(entity_type: str, entity_id: str) -> str:
        """Get a human-readable label for an entity"""
        try:
            # This would typically query the actual entity tables to get names/titles
            # For now, return a formatted version of the ID
            if entity_type == GraphService.ENTITY_IDEA:
                return f"Idea {entity_id}"
            elif entity_type == GraphService.ENTITY_SPEC:
                return f"Spec {entity_id}"
            elif entity_type == GraphService.ENTITY_TASK:
                return f"Task {entity_id}"
            elif entity_type == GraphService.ENTITY_COMMIT:
                return f"Commit {entity_id[:8]}"
            elif entity_type == GraphService.ENTITY_TEAM_MEMBER:
                return f"@{entity_id}"
            elif entity_type == GraphService.ENTITY_PROJECT:
                return f"Project {entity_id}"
            else:
                return f"{entity_type.title()} {entity_id}"
                
        except Exception as e:
            logger.error(f"Failed to get entity label: {e}")
            return f"{entity_type}:{entity_id}"


# Convenience functions for common relationship patterns
class ProjectGraphService:
    """Specialized graph service for project-related entities"""
    
    @staticmethod
    def link_project_to_mission_control(project_id: int, mission_control_id: str, metadata: Optional[Dict] = None):
        """Link a project to its mission control representation"""
        return GraphService.add_relationship(
            GraphService.ENTITY_PROJECT, str(project_id),
            GraphService.ENTITY_MISSION_CONTROL_PROJECT, mission_control_id,
            GraphService.REL_REFERENCES,
            metadata or {'sync_type': 'bidirectional'}
        )
    
    @staticmethod
    def link_conversation_to_project(conversation_id: int, project_id: int, metadata: Optional[Dict] = None):
        """Link a conversation to its project"""
        return GraphService.add_relationship(
            GraphService.ENTITY_CONVERSATION, str(conversation_id),
            GraphService.ENTITY_PROJECT, str(project_id),
            GraphService.REL_REFERENCES,
            metadata or {'context': 'project_conversation'}
        )
    
    @staticmethod
    def link_system_map_to_project(system_map_id: int, project_id: int, metadata: Optional[Dict] = None):
        """Link a system map to its project"""
        return GraphService.add_relationship(
            GraphService.ENTITY_SYSTEM_MAP, str(system_map_id),
            GraphService.ENTITY_PROJECT, str(project_id),
            GraphService.REL_REFERENCES,
            metadata or {'analysis_type': 'system_architecture'}
        )
    
    @staticmethod
    def link_idea_to_project(idea_id: str, project_id: str, metadata: Optional[Dict] = None):
        """Link an idea (feed item) to its project"""
        return GraphService.add_relationship(
            GraphService.ENTITY_IDEA, idea_id,
            GraphService.ENTITY_PROJECT, project_id,
            GraphService.REL_REFERENCES,
            metadata or {'context': 'project_idea'}
        )
    
    @staticmethod
    def promote_idea_to_spec(idea_id: str, spec_id: str, metadata: Optional[Dict] = None):
        """Create relationship when idea is promoted to specification"""
        return GraphService.add_relationship(
            GraphService.ENTITY_IDEA, idea_id,
            GraphService.ENTITY_SPEC, spec_id,
            GraphService.REL_PROMOTES_TO,
            metadata or {'promotion_type': 'manual', 'timestamp': datetime.utcnow().isoformat()}
        )
    
    @staticmethod
    def break_down_spec_to_tasks(spec_id: str, task_ids: List[str], metadata: Optional[Dict] = None):
        """Create relationships when spec is broken down into tasks"""
        success_count = 0
        for task_id in task_ids:
            if GraphService.add_relationship(
                GraphService.ENTITY_SPEC, spec_id,
                GraphService.ENTITY_TASK, task_id,
                GraphService.REL_BREAKS_DOWN_TO,
                metadata or {'breakdown_type': 'automatic', 'timestamp': datetime.utcnow().isoformat()}
            ):
                success_count += 1
        return success_count == len(task_ids)
    
    @staticmethod
    def assign_task_to_member(task_id: str, member_id: str, metadata: Optional[Dict] = None):
        """Assign a task to a team member"""
        return GraphService.add_relationship(
            GraphService.ENTITY_TASK, task_id,
            GraphService.ENTITY_TEAM_MEMBER, member_id,
            GraphService.REL_ASSIGNED_TO,
            metadata or {'assignment_type': 'manual', 'timestamp': datetime.utcnow().isoformat()}
        )
    
    @staticmethod
    def link_commit_to_author(commit_id: str, author_id: str, metadata: Optional[Dict] = None):
        """Link a commit to its author"""
        return GraphService.add_relationship(
            GraphService.ENTITY_COMMIT, commit_id,
            GraphService.ENTITY_TEAM_MEMBER, author_id,
            GraphService.REL_AUTHORED_BY,
            metadata or {'commit_type': 'git'}
        )
    
    @staticmethod
    def link_commit_to_task(commit_id: str, task_id: str, metadata: Optional[Dict] = None):
        """Link a commit to the task it addresses"""
        return GraphService.add_relationship(
            GraphService.ENTITY_COMMIT, commit_id,
            GraphService.ENTITY_TASK, task_id,
            GraphService.REL_ADDRESSES,
            metadata or {'link_type': 'automatic'}
        )
    
    @staticmethod
    def add_team_member_expertise(member_id: str, expertise_area: str, 
                                 confidence: float = 1.0, metadata: Optional[Dict] = None):
        """Add expertise area for a team member"""
        return GraphService.add_relationship(
            GraphService.ENTITY_TEAM_MEMBER, member_id,
            'expertise_area', expertise_area,  # Using string as target type for expertise areas
            GraphService.REL_EXPERTISE_IN,
            metadata or {'confidence': confidence, 'source': 'analysis'},
            weight=confidence
        )
    
    @staticmethod
    def get_project_ecosystem(project_id: int, max_depth: int = 2) -> Dict[str, Any]:
        """Get the complete ecosystem around a project"""
        relationships = GraphService.find_related_entities(
            GraphService.ENTITY_PROJECT, str(project_id),
            max_depth=max_depth
        )
        
        centrality = GraphService.calculate_entity_centrality(
            GraphService.ENTITY_PROJECT, str(project_id)
        )
        
        return {
            'project_id': project_id,
            'related_entities': relationships,
            'centrality_metrics': centrality,
            'ecosystem_size': len(relationships)
        }
    
    @staticmethod
    def get_project_workflow_status(project_id: str) -> Dict[str, Any]:
        """Get workflow status showing ideas -> specs -> tasks -> commits flow"""
        try:
            # Get ideas for the project
            ideas = GraphService.find_related_entities(
                entity_type=GraphService.ENTITY_PROJECT,
                entity_id=project_id,
                relationship_types=[GraphService.REL_REFERENCES],
                direction='incoming'
            )
            ideas = [e for e in ideas if e['entity_type'] == GraphService.ENTITY_IDEA]
            
            # Get specs derived from ideas
            specs = []
            for idea in ideas:
                idea_specs = GraphService.find_related_entities(
                    entity_type=GraphService.ENTITY_IDEA,
                    entity_id=idea['entity_id'],
                    relationship_types=[GraphService.REL_PROMOTES_TO]
                )
                specs.extend([e for e in idea_specs if e['entity_type'] == GraphService.ENTITY_SPEC])
            
            # Get tasks from specs
            tasks = []
            for spec in specs:
                spec_tasks = GraphService.find_related_entities(
                    entity_type=GraphService.ENTITY_SPEC,
                    entity_id=spec['entity_id'],
                    relationship_types=[GraphService.REL_BREAKS_DOWN_TO]
                )
                tasks.extend([e for e in spec_tasks if e['entity_type'] == GraphService.ENTITY_TASK])
            
            # Get commits addressing tasks
            commits = []
            for task in tasks:
                task_commits = GraphService.find_related_entities(
                    entity_type=GraphService.ENTITY_TASK,
                    entity_id=task['entity_id'],
                    relationship_types=[GraphService.REL_ADDRESSES],
                    direction='incoming'
                )
                commits.extend([e for e in task_commits if e['entity_type'] == GraphService.ENTITY_COMMIT])
            
            return {
                'project_id': project_id,
                'workflow_summary': {
                    'ideas_count': len(ideas),
                    'specs_count': len(specs),
                    'tasks_count': len(tasks),
                    'commits_count': len(commits)
                },
                'ideas': ideas[:10],  # Limit for performance
                'specs': specs[:10],
                'tasks': tasks[:20],
                'commits': commits[:20],
                'completion_rate': {
                    'ideas_to_specs': (len(specs) / len(ideas) * 100) if ideas else 0,
                    'specs_to_tasks': (len(tasks) / len(specs) * 100) if specs else 0,
                    'tasks_to_commits': (len(commits) / len(tasks) * 100) if tasks else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get project workflow status: {e}")
            return {
                'project_id': project_id,
                'workflow_summary': {'ideas_count': 0, 'specs_count': 0, 'tasks_count': 0, 'commits_count': 0},
                'ideas': [], 'specs': [], 'tasks': [], 'commits': [],
                'completion_rate': {'ideas_to_specs': 0, 'specs_to_tasks': 0, 'tasks_to_commits': 0}
            }