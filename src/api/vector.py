"""
Vector Search API endpoints
Provides semantic search and document processing capabilities
"""

import logging
from flask import Blueprint, request, jsonify, current_app
try:
    from ..services.vector_service import get_vector_service
except ImportError:
    from services.vector_service import get_vector_service

logger = logging.getLogger(__name__)

vector_bp = Blueprint('vector', __name__)


@vector_bp.route('/api/vector/search', methods=['POST'])
def semantic_search():
    """Perform semantic search across document chunks"""
    try:
        data = request.get_json()
        
        if not data or 'query' not in data:
            return jsonify({'error': 'Query is required'}), 400
        
        query = data['query']
        document_types = data.get('document_types')
        limit = data.get('limit', 10)
        similarity_threshold = data.get('similarity_threshold', 0.3)
        
        vector_service = get_vector_service()
        if not vector_service:
            return jsonify({'error': 'Vector service not available'}), 503
        
        results = vector_service.semantic_search(
            query=query,
            document_types=document_types,
            limit=limit,
            similarity_threshold=similarity_threshold
        )
        
        return jsonify({
            'query': query,
            'results': results,
            'count': len(results)
        })
        
    except Exception as e:
        logger.error(f"Semantic search failed: {e}")
        return jsonify({'error': 'Search failed', 'details': str(e)}), 500


@vector_bp.route('/api/vector/hybrid-search', methods=['POST'])
def hybrid_search():
    """Perform hybrid search combining semantic and keyword search"""
    try:
        data = request.get_json()
        
        if not data or 'query' not in data:
            return jsonify({'error': 'Query is required'}), 400
        
        query = data['query']
        document_types = data.get('document_types')
        limit = data.get('limit', 10)
        semantic_weight = data.get('semantic_weight', 0.7)
        keyword_weight = data.get('keyword_weight', 0.3)
        
        vector_service = get_vector_service()
        if not vector_service:
            return jsonify({'error': 'Vector service not available'}), 503
        
        results = vector_service.hybrid_search(
            query=query,
            document_types=document_types,
            limit=limit,
            semantic_weight=semantic_weight,
            keyword_weight=keyword_weight
        )
        
        return jsonify({
            'query': query,
            'results': results,
            'count': len(results)
        })
        
    except Exception as e:
        logger.error(f"Hybrid search failed: {e}")
        return jsonify({'error': 'Search failed', 'details': str(e)}), 500


@vector_bp.route('/api/vector/related/<document_type>/<document_id>', methods=['GET'])
def find_related_context(document_type, document_id):
    """Find contextually related documents"""
    try:
        limit = request.args.get('limit', 5, type=int)
        
        vector_service = get_vector_service()
        if not vector_service:
            return jsonify({'error': 'Vector service not available'}), 503
        
        results = vector_service.find_related_context(
            document_id=document_id,
            document_type=document_type,
            limit=limit
        )
        
        return jsonify({
            'source_document': {
                'document_id': document_id,
                'document_type': document_type
            },
            'related_documents': results,
            'count': len(results)
        })
        
    except Exception as e:
        logger.error(f"Find related context failed: {e}")
        return jsonify({'error': 'Failed to find related context', 'details': str(e)}), 500


@vector_bp.route('/api/vector/context', methods=['POST'])
def get_ai_context():
    """Get relevant context for AI model calls"""
    try:
        data = request.get_json()
        
        if not data or 'query' not in data:
            return jsonify({'error': 'Query is required'}), 400
        
        query = data['query']
        max_tokens = data.get('max_tokens', 2000)
        document_types = data.get('document_types')
        
        vector_service = get_vector_service()
        if not vector_service:
            return jsonify({'error': 'Vector service not available'}), 503
        
        context = vector_service.get_ai_context(
            query=query,
            max_tokens=max_tokens,
            document_types=document_types
        )
        
        return jsonify({
            'query': query,
            'context': context,
            'token_estimate': len(context.split()) * 1.3  # Rough token estimate
        })
        
    except Exception as e:
        logger.error(f"Get AI context failed: {e}")
        return jsonify({'error': 'Failed to get AI context', 'details': str(e)}), 500


@vector_bp.route('/api/vector/process-document', methods=['POST'])
def process_document():
    """Process a document for semantic search"""
    try:
        data = request.get_json()
        
        required_fields = ['content', 'document_id', 'document_type']
        for field in required_fields:
            if not data or field not in data:
                return jsonify({'error': f'{field} is required'}), 400
        
        content = data['content']
        document_id = data['document_id']
        document_type = data['document_type']
        
        vector_service = get_vector_service()
        if not vector_service:
            return jsonify({'error': 'Vector service not available'}), 503
        
        success = vector_service.process_document(
            content=content,
            document_id=document_id,
            document_type=document_type
        )
        
        if success:
            return jsonify({
                'message': 'Document processed successfully',
                'document_id': document_id,
                'document_type': document_type
            })
        else:
            return jsonify({'error': 'Failed to process document'}), 500
        
    except Exception as e:
        logger.error(f"Process document failed: {e}")
        return jsonify({'error': 'Failed to process document', 'details': str(e)}), 500


@vector_bp.route('/api/vector/process-repository', methods=['POST'])
def process_repository():
    """Process a code repository for semantic search"""
    try:
        data = request.get_json()
        
        if not data or 'repo_path' not in data or 'project_id' not in data:
            return jsonify({'error': 'repo_path and project_id are required'}), 400
        
        repo_path = data['repo_path']
        project_id = data['project_id']
        
        vector_service = get_vector_service()
        if not vector_service:
            return jsonify({'error': 'Vector service not available'}), 503
        
        success = vector_service.process_code_repository(
            repo_path=repo_path,
            project_id=project_id
        )
        
        if success:
            return jsonify({
                'message': 'Repository processed successfully',
                'project_id': project_id,
                'repo_path': repo_path
            })
        else:
            return jsonify({'error': 'Failed to process repository'}), 500
        
    except Exception as e:
        logger.error(f"Process repository failed: {e}")
        return jsonify({'error': 'Failed to process repository', 'details': str(e)}), 500


@vector_bp.route('/api/vector/statistics', methods=['GET'])
def get_statistics():
    """Get vector database statistics"""
    try:
        vector_service = get_vector_service()
        if not vector_service:
            return jsonify({'error': 'Vector service not available'}), 503
        
        stats = vector_service.get_document_statistics()
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Get statistics failed: {e}")
        return jsonify({'error': 'Failed to get statistics', 'details': str(e)}), 500


@vector_bp.route('/api/vector/health', methods=['GET'])
def health_check():
    """Check vector service health"""
    try:
        vector_service = get_vector_service()
        if not vector_service:
            return jsonify({
                'status': 'unhealthy',
                'message': 'Vector service not initialized'
            }), 503
        
        # Test basic functionality
        test_results = vector_service.semantic_search(
            query="test query",
            limit=1,
            similarity_threshold=0.9  # High threshold to avoid matches
        )
        
        return jsonify({
            'status': 'healthy',
            'message': 'Vector service is operational',
            'model_loaded': vector_service.model is not None,
            'tokenizer_loaded': vector_service.tokenizer is not None
        })
        
    except Exception as e:
        logger.error(f"Vector service health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'message': f'Health check failed: {str(e)}'
        }), 500