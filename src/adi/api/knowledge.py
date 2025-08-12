"""
Knowledge API

Endpoints for managing domain knowledge with semantic search capabilities.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import logging

try:
    from ..models.knowledge import Knowledge
    from ..services.knowledge_service import KnowledgeService, DomainKnowledge
    from ...models.base import db
except ImportError:
    try:
        from src.adi.models.knowledge import Knowledge
        from src.adi.services.knowledge_service import KnowledgeService, DomainKnowledge
        from src.models.base import db
    except ImportError:
        from adi.models.knowledge import Knowledge
        from adi.services.knowledge_service import KnowledgeService, DomainKnowledge
        from models.base import db

logger = logging.getLogger(__name__)

knowledge_bp = Blueprint('adi_knowledge', __name__, url_prefix='/api/adi/knowledge')


@knowledge_bp.route('/', methods=['GET'])
def get_knowledge():
    """
    Get knowledge items for a project.
    
    Query parameters:
    - project_id: Filter by project ID (required)
    - author: Filter by author
    - tags: Filter by tags (comma-separated)
    - limit: Maximum number of results (default: 50)
    - offset: Pagination offset (default: 0)
    """
    try:
        project_id = request.args.get('project_id')
        if not project_id:
            return jsonify({'error': 'project_id parameter is required'}), 400
        
        author = request.args.get('author')
        tags = request.args.get('tags')
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        
        # Build query
        query = Knowledge.query.filter(Knowledge.project_id == project_id)
        
        if author:
            query = query.filter(Knowledge.author == author)
        
        if tags:
            tag_list = [tag.strip() for tag in tags.split(',')]
            query = query.filter(Knowledge.tags.overlap(tag_list))
        
        # Get total count for pagination
        total_count = query.count()
        
        # Apply pagination and ordering
        knowledge_items = query.order_by(Knowledge.updated_at.desc()).offset(offset).limit(limit).all()
        
        return jsonify({
            'knowledge': [item.to_dict() for item in knowledge_items],
            'total_count': total_count,
            'limit': limit,
            'offset': offset
        })
        
    except ValueError as e:
        return jsonify({'error': f'Invalid parameter: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Error retrieving knowledge: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@knowledge_bp.route('/', methods=['POST'])
def create_knowledge():
    """
    Create a new knowledge item with automatic embedding generation.
    
    Expected payload:
    {
        "project_id": "string",
        "title": "string",
        "content": "string",
        "rule_yaml": "string (optional)",
        "scope_filters": {},
        "source_link": "string (optional)",
        "author": "string",
        "tags": ["string"]
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Validate required fields
        required_fields = ['project_id', 'title', 'content', 'author']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Create domain knowledge object
        domain_knowledge = DomainKnowledge(
            title=data['title'],
            content=data['content'],
            rule_yaml=data.get('rule_yaml'),
            scope_filters=data.get('scope_filters', {}),
            source_link=data.get('source_link'),
            author=data['author'],
            tags=data.get('tags', [])
        )
        
        # Use knowledge service to add with embedding
        knowledge_service = KnowledgeService()
        knowledge_id = knowledge_service.add_knowledge(data['project_id'], domain_knowledge)
        
        # Retrieve the created knowledge item
        knowledge = Knowledge.query.get(knowledge_id)
        
        logger.info(f"Knowledge created with embedding: {knowledge.title} for project {data['project_id']}")
        
        return jsonify(knowledge.to_dict()), 201
        
    except Exception as e:
        logger.error(f"Error creating knowledge: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@knowledge_bp.route('/<knowledge_id>', methods=['GET'])
def get_knowledge_item(knowledge_id):
    """Get a specific knowledge item by ID."""
    try:
        knowledge = Knowledge.query.get(knowledge_id)
        if not knowledge:
            return jsonify({'error': 'Knowledge item not found'}), 404
        
        return jsonify(knowledge.to_dict())
        
    except Exception as e:
        logger.error(f"Error retrieving knowledge {knowledge_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@knowledge_bp.route('/<knowledge_id>', methods=['PUT'])
def update_knowledge(knowledge_id):
    """
    Update a knowledge item.
    
    Creates a new version of the knowledge item.
    """
    try:
        knowledge = Knowledge.query.get(knowledge_id)
        if not knowledge:
            return jsonify({'error': 'Knowledge item not found'}), 404
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Update fields
        if 'title' in data:
            knowledge.title = data['title']
        if 'content' in data:
            knowledge.content = data['content']
        if 'rule_yaml' in data:
            knowledge.rule_yaml = data['rule_yaml']
        if 'scope_filters' in data:
            knowledge.scope_filters = data['scope_filters']
        if 'source_link' in data:
            knowledge.source_link = data['source_link']
        if 'tags' in data:
            knowledge.tags = data['tags']
        
        # Increment version and update timestamp
        knowledge.version += 1
        knowledge.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        logger.info(f"Knowledge updated: {knowledge_id} to version {knowledge.version}")
        
        return jsonify(knowledge.to_dict())
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating knowledge {knowledge_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@knowledge_bp.route('/<knowledge_id>', methods=['DELETE'])
def delete_knowledge(knowledge_id):
    """Delete a knowledge item."""
    try:
        knowledge = Knowledge.query.get(knowledge_id)
        if not knowledge:
            return jsonify({'error': 'Knowledge item not found'}), 404
        
        db.session.delete(knowledge)
        db.session.commit()
        
        logger.info(f"Knowledge deleted: {knowledge_id}")
        
        return jsonify({'message': 'Knowledge item deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting knowledge {knowledge_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@knowledge_bp.route('/search', methods=['GET'])
def search_knowledge():
    """
    Search knowledge items using semantic similarity.
    
    Query parameters:
    - project_id: Filter by project ID (required)
    - q: Search query (required)
    - limit: Maximum number of results (default: 10)
    """
    try:
        project_id = request.args.get('project_id')
        query_text = request.args.get('q')
        limit = int(request.args.get('limit', 10))
        
        if not project_id:
            return jsonify({'error': 'project_id parameter is required'}), 400
        if not query_text:
            return jsonify({'error': 'q parameter is required'}), 400
        
        # Use knowledge service for semantic search
        knowledge_service = KnowledgeService()
        knowledge_items = knowledge_service.search_knowledge(project_id, query_text, limit)
        
        # Convert to API response format
        results = []
        for item in knowledge_items:
            results.append({
                'id': item.id,
                'project_id': item.project_id,
                'title': item.title,
                'content': item.content,
                'author': item.author,
                'tags': item.tags,
                'version': item.version,
                'similarity_score': item.similarity_score,
                'created_at': item.created_at.isoformat() if item.created_at else None,
                'updated_at': item.updated_at.isoformat() if item.updated_at else None
            })
        
        return jsonify({
            'results': results,
            'query': query_text,
            'count': len(results)
        })
        
    except ValueError as e:
        return jsonify({'error': f'Invalid parameter: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Error searching knowledge: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@knowledge_bp.route('/context', methods=['POST'])
def get_relevant_context():
    """
    Get contextually relevant knowledge for a decision log case.
    
    Expected payload:
    {
        "project_id": "string",
        "case_data": {
            "event": {...},
            "decision": {...}
        }
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        project_id = data.get('project_id')
        case_data = data.get('case_data')
        
        if not project_id:
            return jsonify({'error': 'project_id is required'}), 400
        if not case_data:
            return jsonify({'error': 'case_data is required'}), 400
        
        # Get relevant context using knowledge service
        knowledge_service = KnowledgeService()
        relevant_knowledge = knowledge_service.get_relevant_context(project_id, case_data)
        
        # Convert to API response format
        results = []
        for item in relevant_knowledge:
            results.append({
                'id': item.id,
                'title': item.title,
                'content': item.content,
                'author': item.author,
                'tags': item.tags,
                'similarity_score': item.similarity_score,
                'created_at': item.created_at.isoformat() if item.created_at else None
            })
        
        return jsonify({
            'relevant_knowledge': results,
            'count': len(results)
        })
        
    except Exception as e:
        logger.error(f"Error getting relevant context: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@knowledge_bp.route('/recommendations', methods=['POST'])
def get_knowledge_recommendations():
    """
    Get knowledge recommendations for domain experts based on case patterns.
    
    Expected payload:
    {
        "project_id": "string",
        "case_data": {
            "event": {...},
            "decision": {...}
        }
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        project_id = data.get('project_id')
        case_data = data.get('case_data')
        
        if not project_id:
            return jsonify({'error': 'project_id is required'}), 400
        if not case_data:
            return jsonify({'error': 'case_data is required'}), 400
        
        # Get recommendations using knowledge service
        knowledge_service = KnowledgeService()
        recommendations = knowledge_service.build_knowledge_recommendation_system(project_id, case_data)
        
        return jsonify({
            'recommendations': recommendations,
            'count': len(recommendations)
        })
        
    except Exception as e:
        logger.error(f"Error getting knowledge recommendations: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@knowledge_bp.route('/analytics', methods=['GET'])
def get_knowledge_analytics():
    """
    Get analytics on knowledge usage and effectiveness.
    
    Query parameters:
    - project_id: Project ID (required)
    - days: Number of days to analyze (default: 30)
    """
    try:
        project_id = request.args.get('project_id')
        days = int(request.args.get('days', 30))
        
        if not project_id:
            return jsonify({'error': 'project_id parameter is required'}), 400
        
        # Get analytics using knowledge service
        knowledge_service = KnowledgeService()
        analytics = knowledge_service.get_knowledge_usage_analytics(project_id, days)
        
        return jsonify(analytics)
        
    except ValueError as e:
        return jsonify({'error': f'Invalid parameter: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Error getting knowledge analytics: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@knowledge_bp.route('/reindex', methods=['POST'])
def reindex_knowledge():
    """
    Regenerate embeddings for all knowledge items.
    
    Expected payload:
    {
        "project_id": "string (optional)"
    }
    """
    try:
        data = request.get_json() or {}
        project_id = data.get('project_id')
        
        # Reindex using knowledge service
        knowledge_service = KnowledgeService()
        stats = knowledge_service.reindex_all_knowledge(project_id)
        
        return jsonify({
            'message': 'Knowledge reindexing completed',
            'statistics': stats
        })
        
    except Exception as e:
        logger.error(f"Error reindexing knowledge: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@knowledge_bp.route('/usage-metrics', methods=['GET'])
def get_knowledge_usage_metrics():
    """
    Get knowledge usage metrics and analytics.
    
    Query parameters:
    - project_id: Project ID (required)
    - days: Number of days to analyze (default: 7)
    """
    try:
        project_id = request.args.get('project_id')
        days = int(request.args.get('days', 7))
        
        if not project_id:
            return jsonify({'error': 'project_id parameter is required'}), 400
        
        # Import here to avoid circular imports
        from ..services.knowledge_analytics import knowledge_analytics
        
        # Get usage metrics
        metrics = knowledge_analytics.get_usage_metrics(project_id, days)
        
        # Get recommendations
        recommendations = knowledge_analytics.get_knowledge_recommendations(project_id, metrics)
        
        return jsonify({
            'project_id': project_id,
            'period_days': days,
            'metrics': {
                'total_retrievals': metrics.total_retrievals,
                'unique_knowledge_items_used': metrics.unique_knowledge_items_used,
                'average_similarity_score': metrics.average_similarity_score,
                'most_used_knowledge': metrics.most_used_knowledge,
                'knowledge_effectiveness': metrics.knowledge_effectiveness,
                'usage_by_event_type': metrics.usage_by_event_type,
                'usage_by_author': metrics.usage_by_author
            },
            'recommendations': recommendations,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except ValueError as e:
        return jsonify({'error': f'Invalid parameter: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Error getting knowledge usage metrics: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@knowledge_bp.route('/effectiveness-feedback', methods=['POST'])
def log_knowledge_effectiveness():
    """
    Log knowledge effectiveness feedback.
    
    Expected payload:
    {
        "project_id": "string",
        "case_id": "string",
        "knowledge_id": "string",
        "effectiveness_score": 0.8,
        "feedback_type": "validator_success"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        required_fields = ['project_id', 'case_id', 'knowledge_id', 'effectiveness_score', 'feedback_type']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate effectiveness score
        score = float(data['effectiveness_score'])
        if not 0.0 <= score <= 1.0:
            return jsonify({'error': 'effectiveness_score must be between 0.0 and 1.0'}), 400
        
        # Import here to avoid circular imports
        from ..services.knowledge_analytics import knowledge_analytics
        
        # Log effectiveness feedback
        knowledge_analytics.log_knowledge_effectiveness(
            data['project_id'],
            data['case_id'],
            data['knowledge_id'],
            score,
            data['feedback_type']
        )
        
        return jsonify({
            'message': 'Knowledge effectiveness feedback logged successfully',
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except ValueError as e:
        return jsonify({'error': f'Invalid parameter: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Error logging knowledge effectiveness: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@knowledge_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for the knowledge service."""
    try:
        # Test vector service initialization
        knowledge_service = KnowledgeService()
        vector_status = "healthy" if knowledge_service.vector_service and knowledge_service.vector_service.model else "unhealthy"
        
        return jsonify({
            'status': 'healthy',
            'service': 'adi_knowledge',
            'vector_service': vector_status,
            'embedding_model': knowledge_service.embedding_model,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'service': 'adi_knowledge',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500