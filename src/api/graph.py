"""
Graph API - Entity Relationship Queries
Provides REST endpoints for graph database operations
"""

from flask import Blueprint, request, jsonify
import logging

# Handle both relative and absolute imports
try:
    from ..services.graph_service import GraphService, ProjectGraphService
except ImportError:
    try:
        from services.graph_service import GraphService, ProjectGraphService
    except ImportError:
        # For testing - will be mocked
        GraphService = None
        ProjectGraphService = None

logger = logging.getLogger(__name__)

graph_bp = Blueprint('graph', __name__, url_prefix='/api/graph')


@graph_bp.route('/relationships', methods=['POST'])
def add_relationship():
    """Add a relationship between two entities"""
    try:
        data = request.get_json()
        
        required_fields = ['source_entity_type', 'source_entity_id', 'target_entity_type', 'target_entity_id', 'relationship_type']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        success = GraphService.add_relationship(
            source_entity_type=data['source_entity_type'],
            source_entity_id=data['source_entity_id'],
            target_entity_type=data['target_entity_type'],
            target_entity_id=data['target_entity_id'],
            relationship_type=data['relationship_type'],
            metadata=data.get('metadata'),
            weight=data.get('weight', 1.0)
        )
        
        if success:
            return jsonify({'message': 'Relationship added successfully'}), 201
        else:
            return jsonify({'error': 'Failed to add relationship'}), 500
            
    except Exception as e:
        logger.error(f"Error adding relationship: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@graph_bp.route('/relationships', methods=['DELETE'])
def remove_relationship():
    """Remove a relationship between two entities"""
    try:
        data = request.get_json()
        
        required_fields = ['source_entity_type', 'source_entity_id', 'target_entity_type', 'target_entity_id']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        success = GraphService.remove_relationship(
            source_entity_type=data['source_entity_type'],
            source_entity_id=data['source_entity_id'],
            target_entity_type=data['target_entity_type'],
            target_entity_id=data['target_entity_id'],
            relationship_type=data.get('relationship_type')
        )
        
        if success:
            return jsonify({'message': 'Relationship removed successfully'}), 200
        else:
            return jsonify({'error': 'Failed to remove relationship'}), 500
            
    except Exception as e:
        logger.error(f"Error removing relationship: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@graph_bp.route('/entities/<entity_type>/<entity_id>/related', methods=['GET'])
def get_related_entities(entity_type, entity_id):
    """Get entities related to the specified entity"""
    try:
        # Parse query parameters
        relationship_types = request.args.getlist('relationship_types')
        max_depth = int(request.args.get('max_depth', 3))
        direction = request.args.get('direction', 'both')
        
        if relationship_types == []:
            relationship_types = None
        
        related_entities = GraphService.find_related_entities(
            entity_type=entity_type,
            entity_id=entity_id,
            relationship_types=relationship_types,
            max_depth=max_depth,
            direction=direction
        )
        
        return jsonify({
            'entity_type': entity_type,
            'entity_id': entity_id,
            'related_entities': related_entities,
            'total_count': len(related_entities)
        }), 200
        
    except ValueError as e:
        return jsonify({'error': f'Invalid parameter: {e}'}), 400
    except Exception as e:
        logger.error(f"Error getting related entities: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@graph_bp.route('/entities/<entity_type>/<entity_id>/relationships', methods=['GET'])
def get_entity_relationships(entity_type, entity_id):
    """Get all direct relationships for an entity"""
    try:
        include_incoming = request.args.get('include_incoming', 'true').lower() == 'true'
        include_outgoing = request.args.get('include_outgoing', 'true').lower() == 'true'
        
        relationships = GraphService.get_entity_relationships(
            entity_type=entity_type,
            entity_id=entity_id,
            include_incoming=include_incoming,
            include_outgoing=include_outgoing
        )
        
        return jsonify({
            'entity_type': entity_type,
            'entity_id': entity_id,
            'relationships': relationships,
            'total_count': len(relationships)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting entity relationships: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@graph_bp.route('/entities/<entity_type>/<entity_id>/centrality', methods=['GET'])
def get_entity_centrality(entity_type, entity_id):
    """Get centrality metrics for an entity"""
    try:
        centrality = GraphService.calculate_entity_centrality(
            entity_type=entity_type,
            entity_id=entity_id
        )
        
        if centrality:
            return jsonify({
                'entity_type': entity_type,
                'entity_id': entity_id,
                'centrality': centrality
            }), 200
        else:
            return jsonify({'error': 'Entity not found or no relationships'}), 404
        
    except Exception as e:
        logger.error(f"Error calculating entity centrality: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@graph_bp.route('/path', methods=['GET'])
def find_shortest_path():
    """Find shortest path between two entities"""
    try:
        source_type = request.args.get('source_type')
        source_id = request.args.get('source_id')
        target_type = request.args.get('target_type')
        target_id = request.args.get('target_id')
        max_depth = int(request.args.get('max_depth', 5))
        
        if not all([source_type, source_id, target_type, target_id]):
            return jsonify({'error': 'Missing required parameters: source_type, source_id, target_type, target_id'}), 400
        
        path = GraphService.find_shortest_path(
            source_type=source_type,
            source_id=source_id,
            target_type=target_type,
            target_id=target_id,
            max_depth=max_depth
        )
        
        if path:
            return jsonify({
                'source': {'type': source_type, 'id': source_id},
                'target': {'type': target_type, 'id': target_id},
                'path': path
            }), 200
        else:
            return jsonify({
                'source': {'type': source_type, 'id': source_id},
                'target': {'type': target_type, 'id': target_id},
                'path': None,
                'message': 'No path found'
            }), 404
        
    except ValueError as e:
        return jsonify({'error': f'Invalid parameter: {e}'}), 400
    except Exception as e:
        logger.error(f"Error finding shortest path: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@graph_bp.route('/statistics', methods=['GET'])
def get_relationship_statistics():
    """Get overall relationship statistics"""
    try:
        stats = GraphService.get_relationship_statistics()
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"Error getting relationship statistics: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@graph_bp.route('/entities/<entity_type>/<entity_id>', methods=['DELETE'])
def cleanup_entity_relationships(entity_type, entity_id):
    """Remove all relationships for an entity (cleanup when entity is deleted)"""
    try:
        success = GraphService.remove_entity_relationships(
            entity_type=entity_type,
            entity_id=entity_id
        )
        
        if success:
            return jsonify({'message': 'Entity relationships cleaned up successfully'}), 200
        else:
            return jsonify({'error': 'Failed to cleanup entity relationships'}), 500
            
    except Exception as e:
        logger.error(f"Error cleaning up entity relationships: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# Project-specific graph endpoints
@graph_bp.route('/projects/<int:project_id>/ecosystem', methods=['GET'])
def get_project_ecosystem(project_id):
    """Get the complete ecosystem around a project"""
    try:
        max_depth = int(request.args.get('max_depth', 2))
        
        ecosystem = ProjectGraphService.get_project_ecosystem(
            project_id=project_id,
            max_depth=max_depth
        )
        
        return jsonify(ecosystem), 200
        
    except ValueError as e:
        return jsonify({'error': f'Invalid parameter: {e}'}), 400
    except Exception as e:
        logger.error(f"Error getting project ecosystem: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@graph_bp.route('/projects/<int:project_id>/mission-control/<mission_control_id>', methods=['POST'])
def link_project_to_mission_control(project_id, mission_control_id):
    """Link a project to its mission control representation"""
    try:
        metadata = request.get_json() or {}
        
        success = ProjectGraphService.link_project_to_mission_control(
            project_id=project_id,
            mission_control_id=mission_control_id,
            metadata=metadata
        )
        
        if success:
            return jsonify({'message': 'Project linked to mission control successfully'}), 201
        else:
            return jsonify({'error': 'Failed to link project to mission control'}), 500
            
    except Exception as e:
        logger.error(f"Error linking project to mission control: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@graph_bp.route('/conversations/<int:conversation_id>/project/<int:project_id>', methods=['POST'])
def link_conversation_to_project(conversation_id, project_id):
    """Link a conversation to its project"""
    try:
        metadata = request.get_json() or {}
        
        success = ProjectGraphService.link_conversation_to_project(
            conversation_id=conversation_id,
            project_id=project_id,
            metadata=metadata
        )
        
        if success:
            return jsonify({'message': 'Conversation linked to project successfully'}), 201
        else:
            return jsonify({'error': 'Failed to link conversation to project'}), 500
            
    except Exception as e:
        logger.error(f"Error linking conversation to project: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@graph_bp.route('/system-maps/<int:system_map_id>/project/<int:project_id>', methods=['POST'])
def link_system_map_to_project(system_map_id, project_id):
    """Link a system map to its project"""
    try:
        metadata = request.get_json() or {}
        
        success = ProjectGraphService.link_system_map_to_project(
            system_map_id=system_map_id,
            project_id=project_id,
            metadata=metadata
        )
        
        if success:
            return jsonify({'message': 'System map linked to project successfully'}), 201
        else:
            return jsonify({'error': 'Failed to link system map to project'}), 500
            
    except Exception as e:
        logger.error(f"Error linking system map to project: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# Health check endpoint
@graph_bp.route('/health', methods=['GET'])
def graph_health():
    """Check graph database health"""
    try:
        # Test basic graph functionality
        stats = GraphService.get_relationship_statistics()
        
        return jsonify({
            'status': 'healthy',
            'message': 'Graph database is operational',
            'statistics': stats
        }), 200
        
    except Exception as e:
        logger.error(f"Graph health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'message': f'Graph database health check failed: {str(e)}'
        }), 500