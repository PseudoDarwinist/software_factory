"""
Conversations API Blueprint
REST endpoints for Mission Control conversation management
"""

from flask import Blueprint, request, jsonify, current_app
from sqlalchemy.exc import SQLAlchemyError
try:
    from ..models import FeedItem, db
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from models import FeedItem, db
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Create blueprint
conversations_bp = Blueprint('conversations', __name__)


# Mock conversation storage (in Node.js this was in-memory)
# In a full implementation, this would be a proper Conversation model
mock_conversations = {}


@conversations_bp.route('/api/conversation/<feed_item_id>', methods=['GET'])
def get_conversation(feed_item_id):
    """Get conversation for a feed item"""
    try:
        # Check if feed item exists
        feed_item = FeedItem.query.get(feed_item_id)
        if not feed_item:
            return jsonify({
                'success': False,
                'error': 'Feed item not found',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 404
        
        # Get or create conversation
        conversation = mock_conversations.get(feed_item_id, {
            'id': feed_item_id,
            'feedItemId': feed_item_id,
            'blocks': [],
            'createdAt': datetime.utcnow().isoformat(),
            'updatedAt': datetime.utcnow().isoformat()
        })
        
        return jsonify({
            'success': True,
            'data': conversation,
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        })
        
    except Exception as e:
        logger.error(f"Failed to get conversation for feed item {feed_item_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve conversation',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        }), 500


@conversations_bp.route('/api/conversation/<feed_item_id>/prompt', methods=['POST'])
def send_conversation_prompt(feed_item_id):
    """Send a prompt to the conversation"""
    try:
        data = request.get_json()
        prompt = data.get('prompt') if data else None
        
        if not prompt:
            return jsonify({
                'success': False,
                'error': 'Prompt is required',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 400
        
        # Check if feed item exists
        feed_item = FeedItem.query.get(feed_item_id)
        if not feed_item:
            return jsonify({
                'success': False,
                'error': 'Feed item not found',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 404
        
        # Get or create conversation
        if feed_item_id not in mock_conversations:
            mock_conversations[feed_item_id] = {
                'id': feed_item_id,
                'feedItemId': feed_item_id,
                'blocks': [],
                'createdAt': datetime.utcnow().isoformat(),
                'updatedAt': datetime.utcnow().isoformat()
            }
        
        conversation = mock_conversations[feed_item_id]
        
        logger.info(f"Received prompt for {feed_item_id}: {prompt}")
        
        # Add user prompt to conversation
        user_block = {
            'type': 'user_prompt',
            'content': prompt,
            'timestamp': datetime.utcnow().isoformat()
        }
        conversation['blocks'].append(user_block)
        
        # Simulate AI response (in real implementation, this would call AI service)
        ai_response = {
            'type': 'llm_suggestion',
            'command': prompt,
            'explanation': f'Processed command: {prompt}',
            'confidence': 0.88,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        conversation['blocks'].append(ai_response)
        conversation['updatedAt'] = datetime.utcnow().isoformat()
        
        return jsonify({
            'success': True,
            'data': ai_response,
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        })
        
    except Exception as e:
        logger.error(f"Failed to send prompt to conversation {feed_item_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to send prompt',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        }), 500


@conversations_bp.route('/api/conversation/<feed_item_id>/clear', methods=['POST'])
def clear_conversation(feed_item_id):
    """Clear conversation history"""
    try:
        if feed_item_id in mock_conversations:
            mock_conversations[feed_item_id]['blocks'] = []
            mock_conversations[feed_item_id]['updatedAt'] = datetime.utcnow().isoformat()
        
        return jsonify({
            'success': True,
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        })
        
    except Exception as e:
        logger.error(f"Failed to clear conversation {feed_item_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to clear conversation',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        }), 500


# Error handlers for this blueprint
@conversations_bp.errorhandler(404)
def conversation_not_found(error):
    return jsonify({
        'success': False,
        'error': 'Conversation not found',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0',
    }), 404


@conversations_bp.errorhandler(400)
def conversation_bad_request(error):
    return jsonify({
        'success': False,
        'error': 'Bad request',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0',
    }), 400


@conversations_bp.errorhandler(SQLAlchemyError)
def conversation_database_error(error):
    db.session.rollback()
    logger.error(f"Database error in conversations API: {error}")
    return jsonify({
        'success': False,
        'error': 'Database operation failed',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0',
    }), 500