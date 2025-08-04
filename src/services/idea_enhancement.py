"""
Simple idea summary enhancement service
Updates feed item summaries when PRDs are created/updated
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from .ai_broker import get_ai_broker
    from ..models import db, FeedItem, PRD
except ImportError:
    from services.ai_broker import get_ai_broker
    from models import db, FeedItem, PRD


def enhance_idea_summary(feed_item_id: str) -> bool:
    """
    Enhance the summary of a feed item based on its PRD content
    
    Args:
        feed_item_id: ID of the feed item to enhance
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get the feed item
        feed_item = FeedItem.query.filter_by(id=feed_item_id).first()
        if not feed_item:
            logger.warning(f"Feed item not found: {feed_item_id}")
            return False
            
        # Get the idea-specific PRD
        prd = PRD.query.filter_by(
            project_id=feed_item.project_id,
            feed_item_id=feed_item_id
        ).first()
        
        if not prd or not prd.content:
            logger.info(f"No PRD content found for idea: {feed_item_id}")
            return False
            
        # Get AI broker
        ai_broker = get_ai_broker()
        
        # Generate enhanced summary
        enhanced_summary = ai_broker.enhance_idea_summary(
            idea_title=feed_item.title,
            prd_content=prd.content,
            project_context=""  # Could add project context later if needed
        )
        
        # Update the feed item summary
        feed_item.summary = enhanced_summary
        db.session.commit()
        
        logger.info(f"Enhanced summary for idea: {feed_item.title}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to enhance idea summary for {feed_item_id}: {e}")
        db.session.rollback()
        return False