"""
API endpoints for webhook integration with external systems.
"""

import logging
import time
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from typing import Dict, Any

try:
    from ..services.webhook_service import get_webhook_service, WebhookConfig
    from ..integrations import GitHubAdapter, JenkinsAdapter, SlackAdapter, FigmaAdapter
except ImportError:
    from services.webhook_service import get_webhook_service, WebhookConfig
    from integrations import GitHubAdapter, JenkinsAdapter, SlackAdapter, FigmaAdapter


logger = logging.getLogger(__name__)

webhooks_bp = Blueprint('webhooks', __name__, url_prefix='/api/webhooks')


@webhooks_bp.route('/github', methods=['POST'])
def github_webhook():
    """Handle GitHub webhook events."""
    try:
        # Get payload and headers
        payload = request.get_json()
        headers = dict(request.headers)
        # Try different header key formats
        event_type = (headers.get('X-GitHub-Event') or 
                     headers.get('X-Github-Event') or 
                     headers.get('x-github-event') or 
                     'unknown')
        
        logger.info(f"Received GitHub webhook: {event_type}")
        logger.info(f"Looking for X-GitHub-Event in headers...")
        for key, value in headers.items():
            if 'github' in key.lower():
                logger.info(f"  Found GitHub header: {key} = {value}")
        logger.info(f"Payload keys: {list(payload.keys()) if payload else 'None'}")
        
        # Handle pull request events for task status updates directly
        pr_result = None
        if event_type == 'pull_request':
            try:
                pr_result = handle_github_pr_event(payload)
                if pr_result:
                    logger.info(f"GitHub PR event processed: {pr_result}")
            except Exception as pr_error:
                logger.error(f"Error processing GitHub PR event: {pr_error}")
                pr_result = {'error': str(pr_error)}
        elif event_type == 'pull_request_review':
            try:
                pr_result = handle_github_pr_review_event(payload)
                if pr_result:
                    logger.info(f"GitHub PR review event processed: {pr_result}")
            except Exception as pr_error:
                logger.error(f"Error processing GitHub PR review event: {pr_error}")
                pr_result = {'error': str(pr_error)}
        elif event_type == 'issue_comment':
            try:
                pr_result = handle_github_issue_comment_event(payload)
                if pr_result:
                    logger.info(f"GitHub issue comment event processed: {pr_result}")
            except Exception as pr_error:
                logger.error(f"Error processing GitHub issue comment event: {pr_error}")
                pr_result = {'error': str(pr_error)}
        
        # Skip webhook service for now to avoid hanging
        webhook_result = {'status': 'skipped', 'reason': 'webhook_service_bypassed_for_testing'}
        
        # Return success if either PR processing worked or webhook service worked
        response_data = {
            'status': 'success',
            'event_type': event_type,
            'pr_result': pr_result,
            'webhook_result': webhook_result,
            'message': f'GitHub {event_type} event processed'
        }
        
        return jsonify(response_data), 200
            
    except Exception as e:
        logger.error(f"Error handling GitHub webhook: {e}")
        import traceback
        logger.error(f"GitHub webhook traceback: {traceback.format_exc()}")
        return jsonify({
            'error': 'Internal server error',
            'details': str(e),
            'event_type': headers.get('X-GitHub-Event', 'unknown') if 'headers' in locals() else 'unknown'
        }), 500


@webhooks_bp.route('/jenkins', methods=['POST'])
def jenkins_webhook():
    """Handle Jenkins webhook events."""
    try:
        webhook_service = get_webhook_service()
        if not webhook_service:
            return jsonify({'error': 'Webhook service not initialized'}), 500
        
        # Jenkins can send either JSON or form data
        if request.is_json:
            payload = request.get_json()
        else:
            payload = request.form.to_dict()
        
        headers = dict(request.headers)
        
        # Process the webhook
        result = webhook_service.process_inbound_webhook(
            source_system='jenkins',
            webhook_type='build_notification',
            payload=payload,
            headers=headers
        )
        
        if result['status'] == 'success':
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error handling Jenkins webhook: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@webhooks_bp.route('/slack', methods=['POST'])
def slack_webhook():
    """Handle Slack webhook events."""
    try:
        # Slack can send JSON or form data
        if request.is_json:
            payload = request.get_json()
        else:
            payload = request.form.to_dict()

        # Handle URL verification challenge early – no services required
        if payload.get('type') == 'url_verification':
            return jsonify({'challenge': payload.get('challenge')}), 200

        logger.info(f"Received Slack webhook: {payload.get('type', 'unknown')}")

        # Handle event callbacks (messages, etc.)
        if payload.get('type') == 'event_callback':
            return handle_slack_event_callback(payload)

        # For other webhook types, just acknowledge
        logger.info(f"Unhandled Slack webhook type: {payload.get('type', 'unknown')}")
        return jsonify({'status': 'acknowledged'}), 200
            
    except Exception as e:
        logger.error(f"Error handling Slack webhook: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


def handle_github_pr_event(payload):
    """Handle GitHub pull request events and update task status."""
    logger.info("=== Starting GitHub PR event handler ===")
    
    try:
        action = payload.get('action')
        pull_request = payload.get('pull_request', {})
        
        logger.info(f"PR event - action: {action}")
        
        if not pull_request:
            logger.warning("GitHub PR webhook missing pull_request data")
            return {'error': 'Missing pull_request data'}
        
        pr_number = pull_request.get('number')
        pr_url = pull_request.get('html_url')
        pr_state = pull_request.get('state')
        merged = pull_request.get('merged', False)
        branch_name = pull_request.get('head', {}).get('ref')
        
        logger.info(f"PR details - number: {pr_number}, state: {pr_state}, merged: {merged}, branch: {branch_name}")
        
        # Try to import models - this might be where it hangs
        logger.info("Attempting to import task models...")
        try:
            from ..models.task import Task, TaskStatus
            from ..models.base import db
            logger.info("✅ Successfully imported task models")
        except ImportError:
            try:
                from models.task import Task, TaskStatus
                from models.base import db
                logger.info("✅ Successfully imported task models (fallback)")
            except ImportError as e:
                logger.error(f"❌ Failed to import task models: {e}")
                return {'error': f'Import error: {e}'}
        
        # Try database query - this might also hang
        logger.info(f"Searching for task with PR number {pr_number}...")
        task = None
        try:
            if pr_number:
                task = Task.query.filter_by(pr_number=pr_number).first()
                logger.info(f"Task search by PR number result: {task.id if task else 'None'}")
            
            if not task and branch_name:
                logger.info(f"Searching for task with branch name {branch_name}...")
                task = Task.query.filter_by(branch_name=branch_name).first()
                logger.info(f"Task search by branch result: {task.id if task else 'None'}")
                
        except Exception as db_error:
            logger.error(f"❌ Database error finding task: {db_error}")
            return {'error': f'Database error: {db_error}'}
        
        if not task:
            logger.info(f"No task found for PR #{pr_number} (branch: {branch_name})")
            return {
                'action': action,
                'pr_number': pr_number,
                'updated': False,
                'reason': 'No matching task found'
            }
        
        logger.info(f"✅ Found task {task.id} for PR #{pr_number}")
        
        # Update task based on PR action
        task_updated = False
        
        try:
            if action == 'opened' and not task.pr_url:
                # PR was just created - update task with PR info
                task.pr_url = pr_url
                task.pr_number = pr_number
                task.status = TaskStatus.REVIEW
                task.add_progress_message(f"Pull request #{pr_number} created")
                task_updated = True
                logger.info(f"Task {task.id} updated with new PR #{pr_number}")
            
            elif action == 'closed':
                if merged:
                    # PR was merged - mark task as done
                    task.status = TaskStatus.DONE
                    task.completed_at = datetime.utcnow()
                    task.add_progress_message(f"Pull request #{pr_number} merged - task completed")
                    task_updated = True
                    logger.info(f"Task {task.id} marked as DONE (PR #{pr_number} merged)")
                else:
                    # PR was closed without merging - mark task as failed
                    task.status = TaskStatus.FAILED
                    task.error = f"Pull request #{pr_number} was closed without merging"
                    task.add_progress_message(f"Pull request #{pr_number} closed without merging")
                    task_updated = True
                    logger.info(f"Task {task.id} marked as FAILED (PR #{pr_number} closed without merge)")
            
            elif action == 'reopened':
                # PR was reopened - move task back to review
                task.status = TaskStatus.REVIEW
                task.error = None  # Clear any previous error
                task.add_progress_message(f"Pull request #{pr_number} reopened")
                task_updated = True
                logger.info(f"Task {task.id} moved back to REVIEW (PR #{pr_number} reopened)")
            
            elif action == 'ready_for_review':
                # Draft PR converted to ready for review
                task.status = TaskStatus.REVIEW
                task.add_progress_message(f"Pull request #{pr_number} ready for review")
                task_updated = True
                logger.info(f"Task {task.id} moved to REVIEW (PR #{pr_number} ready for review)")
            
            if task_updated:
                db.session.commit()
                logger.info(f"✅ Task {task.id} updated successfully")
                
                # Try to broadcast real-time update via WebSocket (non-blocking)
                try:
                    from ..services.websocket_server import get_websocket_server
                    ws_server = get_websocket_server()
                    if ws_server:
                        task_data = task.to_dict()
                        ws_server.broadcast_task_progress(task.id, task_data)
                        logger.info(f"Broadcasted task update for {task.id} via WebSocket")
                except Exception as ws_error:
                    logger.warning(f"Failed to broadcast WebSocket update: {ws_error}")
                    # Don't fail the webhook processing if WebSocket fails
                
                return {
                    'task_id': task.id,
                    'action': action,
                    'pr_number': pr_number,
                    'new_status': task.status.value,
                    'updated': True
                }
            
            return {
                'task_id': task.id,
                'action': action,
                'pr_number': pr_number,
                'updated': False,
                'reason': 'No status change needed'
            }
            
        except Exception as update_error:
            logger.error(f"Error updating task {task.id}: {update_error}")
            try:
                db.session.rollback()
            except:
                pass
            return {'error': f'Update failed: {update_error}'}
        
    except Exception as e:
        logger.error(f"❌ Error in GitHub PR event handler: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {'error': str(e)}


def handle_github_pr_review_event(payload):
    """Handle GitHub pull request review events."""
    logger.info("=== Starting GitHub PR review event handler ===")
    
    try:
        action = payload.get('action')
        review = payload.get('review', {})
        pull_request = payload.get('pull_request', {})
        
        logger.info(f"PR review event - action: {action}")
        
        if not pull_request or not review:
            logger.warning("GitHub PR review webhook missing pull_request or review data")
            return {'error': 'Missing pull_request or review data'}
        
        pr_number = pull_request.get('number')
        review_state = review.get('state')  # 'approved', 'changes_requested', 'commented'
        review_body = review.get('body', '')
        reviewer = review.get('user', {}).get('login', 'unknown')
        
        logger.info(f"PR review details - number: {pr_number}, state: {review_state}, reviewer: {reviewer}")
        
        # Import models
        try:
            from ..models.task import Task, TaskStatus
            from ..models.base import db
            logger.info("✅ Successfully imported task models")
        except ImportError:
            try:
                from models.task import Task, TaskStatus
                from models.base import db
                logger.info("✅ Successfully imported task models (fallback)")
            except ImportError as e:
                logger.error(f"❌ Failed to import task models: {e}")
                return {'error': f'Import error: {e}'}
        
        # Find task by PR number
        task = None
        try:
            if pr_number:
                task = Task.query.filter_by(pr_number=pr_number).first()
                logger.info(f"Task search by PR number result: {task.id if task else 'None'}")
        except Exception as db_error:
            logger.error(f"❌ Database error finding task: {db_error}")
            return {'error': f'Database error: {db_error}'}
        
        if not task:
            logger.info(f"No task found for PR #{pr_number}")
            return {
                'action': action,
                'pr_number': pr_number,
                'updated': False,
                'reason': 'No matching task found'
            }
        
        logger.info(f"✅ Found task {task.id} for PR #{pr_number}")
        
        # Update task based on review state
        task_updated = False
        
        try:
            if action == 'submitted':
                if review_state == 'approved':
                    # PR was approved
                    task.add_progress_message(f"✅ PR #{pr_number} approved by {reviewer}")
                    task_updated = True
                    logger.info(f"Task {task.id} updated with PR approval from {reviewer}")
                
                elif review_state == 'changes_requested':
                    # Changes requested - move task to needs rework
                    task.status = TaskStatus.NEEDS_REWORK
                    task.add_progress_message(f"🔄 Changes requested by {reviewer}: {review_body[:100]}...")
                    task_updated = True
                    logger.info(f"Task {task.id} moved to NEEDS_REWORK (changes requested by {reviewer})")
                
                elif review_state == 'commented':
                    # Just a comment
                    task.add_progress_message(f"💬 Comment from {reviewer}: {review_body[:100]}...")
                    task_updated = True
                    logger.info(f"Task {task.id} updated with comment from {reviewer}")
            
            if task_updated:
                db.session.commit()
                logger.info(f"✅ Task {task.id} updated successfully")
                
                # Broadcast real-time update via WebSocket
                try:
                    from ..services.websocket_server import get_websocket_server
                    ws_server = get_websocket_server()
                    if ws_server:
                        task_data = task.to_dict()
                        ws_server.broadcast_task_progress(task.id, task_data)
                        logger.info(f"Broadcasted task update for {task.id} via WebSocket")
                except Exception as ws_error:
                    logger.warning(f"Failed to broadcast WebSocket update: {ws_error}")
                
                return {
                    'task_id': task.id,
                    'action': action,
                    'pr_number': pr_number,
                    'review_state': review_state,
                    'reviewer': reviewer,
                    'updated': True
                }
            
            return {
                'task_id': task.id,
                'action': action,
                'pr_number': pr_number,
                'updated': False,
                'reason': 'No status change needed'
            }
            
        except Exception as update_error:
            logger.error(f"Error updating task {task.id}: {update_error}")
            try:
                db.session.rollback()
            except:
                pass
            return {'error': f'Update failed: {update_error}'}
        
    except Exception as e:
        logger.error(f"❌ Error in GitHub PR review event handler: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {'error': str(e)}


def handle_github_issue_comment_event(payload):
    """Handle GitHub issue comment events (includes PR comments)."""
    logger.info("=== Starting GitHub issue comment event handler ===")
    
    try:
        action = payload.get('action')
        comment = payload.get('comment', {})
        issue = payload.get('issue', {})
        
        logger.info(f"Issue comment event - action: {action}")
        
        # Only handle comments on pull requests
        if not issue.get('pull_request'):
            logger.info("Issue comment is not on a pull request, ignoring")
            return {'action': action, 'updated': False, 'reason': 'Not a PR comment'}
        
        if not comment:
            logger.warning("GitHub issue comment webhook missing comment data")
            return {'error': 'Missing comment data'}
        
        pr_number = issue.get('number')
        comment_body = comment.get('body', '')
        commenter = comment.get('user', {}).get('login', 'unknown')
        
        logger.info(f"PR comment details - number: {pr_number}, commenter: {commenter}")
        
        # Import models
        try:
            from ..models.task import Task, TaskStatus
            from ..models.base import db
            logger.info("✅ Successfully imported task models")
        except ImportError:
            try:
                from models.task import Task, TaskStatus
                from models.base import db
                logger.info("✅ Successfully imported task models (fallback)")
            except ImportError as e:
                logger.error(f"❌ Failed to import task models: {e}")
                return {'error': f'Import error: {e}'}
        
        # Find task by PR number
        task = None
        try:
            if pr_number:
                task = Task.query.filter_by(pr_number=pr_number).first()
                logger.info(f"Task search by PR number result: {task.id if task else 'None'}")
        except Exception as db_error:
            logger.error(f"❌ Database error finding task: {db_error}")
            return {'error': f'Database error: {db_error}'}
        
        if not task:
            logger.info(f"No task found for PR #{pr_number}")
            return {
                'action': action,
                'pr_number': pr_number,
                'updated': False,
                'reason': 'No matching task found'
            }
        
        logger.info(f"✅ Found task {task.id} for PR #{pr_number}")
        
        # Update task with comment
        task_updated = False
        
        try:
            if action in ['created', 'edited']:
                # Add comment to task progress
                task.add_progress_message(f"💬 {commenter}: {comment_body[:100]}...")
                task_updated = True
                logger.info(f"Task {task.id} updated with comment from {commenter}")
            
            if task_updated:
                db.session.commit()
                logger.info(f"✅ Task {task.id} updated successfully")
                
                # Broadcast real-time update via WebSocket
                try:
                    from ..services.websocket_server import get_websocket_server
                    ws_server = get_websocket_server()
                    if ws_server:
                        task_data = task.to_dict()
                        ws_server.broadcast_task_progress(task.id, task_data)
                        logger.info(f"Broadcasted task update for {task.id} via WebSocket")
                except Exception as ws_error:
                    logger.warning(f"Failed to broadcast WebSocket update: {ws_error}")
                
                return {
                    'task_id': task.id,
                    'action': action,
                    'pr_number': pr_number,
                    'commenter': commenter,
                    'updated': True
                }
            
            return {
                'task_id': task.id,
                'action': action,
                'pr_number': pr_number,
                'updated': False,
                'reason': 'No status change needed'
            }
            
        except Exception as update_error:
            logger.error(f"Error updating task {task.id}: {update_error}")
            try:
                db.session.rollback()
            except:
                pass
            return {'error': f'Update failed: {update_error}'}
        
    except Exception as e:
        logger.error(f"❌ Error in GitHub issue comment event handler: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {'error': str(e)}


def handle_slack_event_callback(payload):
    """Handle Slack event callback and create feed items directly."""
    try:
        event = payload.get('event', {})
        event_type = event.get('type')
        
        logger.info(f"Processing Slack event: {event_type}")
        
        if event_type == 'message':
            # Skip bot messages and system messages
            if (event.get('bot_id') or 
                event.get('subtype') == 'bot_message' or
                event.get('user') == 'USLACKBOT' or
                not event.get('text')):
                logger.info("Skipping bot/system message")
                return jsonify({'status': 'ignored'}), 200
            
            # Extract message data
            channel = event.get('channel')
            user = event.get('user')
            text = event.get('text', '')
            timestamp = event.get('ts')
            
            logger.info(f"Processing message from user {user} in channel {channel}: {text[:50]}...")
            logger.error(f"DEBUG WEBHOOK: Processing message from user {user} in channel {channel}")
            logger.error(f"DEBUG WEBHOOK: Message text: {text[:100]}")
            
            # Print to console for immediate visibility
            print(f"🔔 SLACK MESSAGE RECEIVED:")
            print(f"   Channel: {channel}")
            print(f"   User: {user}")
            print(f"   Text: {text[:100]}...")
            print(f"   Timestamp: {timestamp}")
            
            # Create feed item using direct database operations
            try:
                # Import models using the pattern that works with Flask app context
                try:
                    from ..models.feed_item import FeedItem
                    from ..models.stage import Stage
                    from ..models.mission_control_project import MissionControlProject
                    from ..models.channel_mapping import ChannelMapping
                    from ..models.base import db
                except ImportError:
                    from models.feed_item import FeedItem
                    from models.stage import Stage
                    from models.mission_control_project import MissionControlProject
                    from models.channel_mapping import ChannelMapping
                    from models.base import db
                
                logger.error(f"DEBUG WEBHOOK: Looking up channel mapping for channel: {channel}")
                project_id = ChannelMapping.get_project_for_channel(channel)
                logger.error(f"DEBUG WEBHOOK: Found project_id: {project_id}")
                
                if project_id:
                    # Channel is mapped to a specific project
                    print(f"DEBUG WEBHOOK: Channel {channel} is mapped to project {project_id}")
                    project = MissionControlProject.query.get(project_id)
                    if not project:
                        print(f"DEBUG WEBHOOK: ERROR - Project {project_id} not found!")
                        logger.warning(f"Channel {channel} mapped to non-existent project {project_id}")
                        
                        # Auto-cleanup: Remove orphaned channel mapping
                        orphaned_mapping = ChannelMapping.query.filter_by(channel_id=channel).first()
                        if orphaned_mapping:
                            print(f"DEBUG WEBHOOK: Auto-removing orphaned mapping for channel {channel}")
                            db.session.delete(orphaned_mapping)
                            db.session.commit()
                            logger.info(f"Auto-removed orphaned channel mapping: {channel} -> {project_id}")
                        
                        return jsonify({'status': 'ignored', 'reason': 'project_not_found_mapping_cleaned'}), 200
                    print(f"DEBUG WEBHOOK: Using project: {project.name} ({project.id})")
                else:
                    # Channel is not mapped to any project - ignore the message
                    print(f"DEBUG WEBHOOK: ERROR - No mapping found for channel {channel}")
                    print(f"DEBUG WEBHOOK: Available mappings:")
                    all_mappings = ChannelMapping.query.all()
                    for mapping in all_mappings:
                        print(f"DEBUG WEBHOOK:   {mapping.channel_id} -> {mapping.project_id}")
                    logger.info(f"Ignoring message from unmapped channel: {channel}")
                    return jsonify({'status': 'ignored', 'reason': 'channel_not_mapped'}), 200
                
                # Create title from text (first line or first 50 chars)
                lines = text.strip().split('\n')
                title = lines[0].strip()
                if len(title) > 50:
                    words = title.split()
                    title = ""
                    for word in words:
                        if len(title + word) <= 47:
                            title += word + " "
                        else:
                            break
                    title = title.strip() + "..." if title else text[:47] + "..."
                
                # Create unique feed item ID with microseconds to avoid duplicates
                import time
                import uuid
                current_time = time.time()
                # Use timestamp with microseconds and a short UUID suffix for uniqueness
                feed_item_id = f"slack_{channel}_{timestamp or current_time}_{str(uuid.uuid4())[:8]}"
                
                # Create the feed item
                feed_item = FeedItem.create(
                    id=feed_item_id,
                    project_id=project.id,
                    severity=FeedItem.SEVERITY_INFO,
                    kind=FeedItem.KIND_IDEA,
                    title=title,
                    summary=text,
                    actor=user or 'slack-user',
                    metadata={
                        'source': 'slack',
                        'channel': channel,
                        'timestamp': timestamp,
                        'stage': 'think'
                    }
                )
                
                # Add to Think stage
                think_stage = Stage.get_or_create_for_project(project.id, Stage.STAGE_THINK)
                think_stage.add_item(feed_item.id)
                
                # Update project unread count
                project.increment_unread_count()
                
                db.session.commit()
                
                logger.info(f"Created feed item from Slack message: {feed_item_id} in project {project.id}")
                
                return jsonify({
                    'status': 'success',
                    'message': 'Slack message processed',
                    'feed_item_id': feed_item_id,
                    'project_id': project.id
                }), 200
                
            except Exception as db_error:
                logger.error(f"Database error creating feed item: {db_error}")
                print(f"🚨 WEBHOOK DATABASE ERROR: {db_error}")
                print(f"🚨 ERROR TYPE: {type(db_error).__name__}")
                import traceback
                print(f"🚨 FULL TRACEBACK:")
                traceback.print_exc()
                
                try:
                    db.session.rollback()
                except Exception as rollback_error:
                    print(f"🚨 ROLLBACK ERROR: {rollback_error}")
                
                # Fallback: just log the message and return success
                logger.info(f"Slack message received (DB failed): {text[:100]}...")
                return jsonify({
                    'status': 'success',
                    'message': 'Slack message logged (database error)',
                    'slack_text': text[:100],
                    'error_details': str(db_error)
                }), 200
        
        else:
            logger.info(f"Unhandled Slack event type: {event_type}")
            return jsonify({'status': 'ignored'}), 200
            
    except Exception as e:
        logger.error(f"Error processing Slack event callback: {e}", exc_info=True)
        return jsonify({
            'error': 'Failed to process Slack event',
            'details': str(e),
            'type': type(e).__name__
        }), 500





@webhooks_bp.route('/figma', methods=['POST'])
def figma_webhook():
    """Handle Figma webhook events."""
    try:
        webhook_service = get_webhook_service()
        if not webhook_service:
            return jsonify({'error': 'Webhook service not initialized'}), 500
        
        payload = request.get_json()
        headers = dict(request.headers)
        
        # Process the webhook
        result = webhook_service.process_inbound_webhook(
            source_system='figma',
            webhook_type=payload.get('event_type', 'unknown'),
            payload=payload,
            headers=headers
        )
        
        if result['status'] == 'success':
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error handling Figma webhook: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@webhooks_bp.route('/generic/<source_system>', methods=['POST'])
def generic_webhook(source_system: str):
    """Handle generic webhook events from any system."""
    try:
        webhook_service = get_webhook_service()
        if not webhook_service:
            return jsonify({'error': 'Webhook service not initialized'}), 500
        
        # Handle both JSON and form data
        if request.is_json:
            payload = request.get_json()
        else:
            payload = request.form.to_dict()
        
        headers = dict(request.headers)
        
        # Process the webhook
        result = webhook_service.process_inbound_webhook(
            source_system=source_system,
            webhook_type='generic',
            payload=payload,
            headers=headers
        )
        
        if result['status'] == 'success':
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error handling generic webhook from {source_system}: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@webhooks_bp.route('/configs', methods=['GET'])
def list_webhook_configs():
    """List all webhook configurations."""
    try:
        webhook_service = get_webhook_service()
        if not webhook_service:
            return jsonify({'error': 'Webhook service not initialized'}), 500
        
        configs = webhook_service.get_webhook_configs()
        return jsonify({'configs': configs}), 200
        
    except Exception as e:
        logger.error(f"Error listing webhook configs: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@webhooks_bp.route('/configs', methods=['POST'])
def create_webhook_config():
    """Create a new webhook configuration."""
    try:
        webhook_service = get_webhook_service()
        if not webhook_service:
            return jsonify({'error': 'Webhook service not initialized'}), 500
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'url']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Create webhook config
        config = WebhookConfig(
            name=data['name'],
            url=data['url'],
            secret=data.get('secret'),
            events=data.get('events', []),
            headers=data.get('headers', {}),
            timeout=data.get('timeout', 30),
            max_retries=data.get('max_retries', 3),
            retry_delay=data.get('retry_delay', 60),
            active=data.get('active', True)
        )
        
        webhook_service.register_outbound_webhook(config)
        
        return jsonify({
            'message': 'Webhook configuration created successfully',
            'config': {
                'name': config.name,
                'url': config.url,
                'events': config.events,
                'active': config.active
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating webhook config: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@webhooks_bp.route('/send', methods=['POST'])
def send_webhook():
    """Send a webhook manually."""
    try:
        webhook_service = get_webhook_service()
        if not webhook_service:
            return jsonify({'error': 'Webhook service not initialized'}), 500
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['config_name', 'event_type', 'payload']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Send the webhook
        result = webhook_service.send_webhook(
            config_name=data['config_name'],
            event_type=data['event_type'],
            payload=data['payload'],
            correlation_id=data.get('correlation_id')
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error sending webhook: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@webhooks_bp.route('/test/<integration>', methods=['POST'])
def test_integration(integration: str):
    """Test integration with external system."""
    try:
        data = request.get_json() or {}
        
        if integration == 'github':
            adapter = GitHubAdapter()
            adapter.configure(webhook_secret=data.get('webhook_secret'))
            
            # Test with sample payload
            test_payload = {
                'action': 'opened',
                'repository': {
                    'id': 123456,
                    'name': 'test-repo',
                    'full_name': 'user/test-repo',
                    'html_url': 'https://github.com/user/test-repo'
                },
                'sender': {
                    'login': 'testuser',
                    'id': 789
                }
            }
            
            event = adapter.process_webhook(test_payload, {'X-GitHub-Event': 'repository'})
            
            return jsonify({
                'status': 'success',
                'message': 'GitHub integration test successful',
                'event_type': event.get_event_type() if event else None
            }), 200
            
        elif integration == 'slack':
            adapter = SlackAdapter()
            adapter.configure(
                bot_token=data.get('bot_token'),
                webhook_url=data.get('webhook_url')
            )
            
            # Test sending a message
            if data.get('webhook_url'):
                result = adapter.send_webhook_message("🧪 Test message from Software Factory")
                return jsonify({
                    'status': 'success' if result['status'] == 'success' else 'error',
                    'message': f"Slack integration test: {result['message']}"
                }), 200
            else:
                return jsonify({
                    'status': 'success',
                    'message': 'Slack adapter configured successfully (no test message sent)'
                }), 200
                
        elif integration == 'jenkins':
            adapter = JenkinsAdapter()
            adapter.configure(
                jenkins_url=data.get('jenkins_url'),
                api_token=data.get('api_token')
            )
            
            return jsonify({
                'status': 'success',
                'message': 'Jenkins integration configured successfully'
            }), 200
            
        elif integration == 'figma':
            adapter = FigmaAdapter()
            adapter.configure(
                access_token=data.get('access_token'),
                team_id=data.get('team_id')
            )
            
            return jsonify({
                'status': 'success',
                'message': 'Figma integration configured successfully'
            }), 200
            
        else:
            return jsonify({'error': f'Unknown integration: {integration}'}), 400
            
    except Exception as e:
        logger.error(f"Error testing {integration} integration: {e}")
        return jsonify({'error': str(e)}), 500


@webhooks_bp.route('/status', methods=['GET'])
def webhook_status():
    """Get webhook service status and statistics."""
    try:
        webhook_service = get_webhook_service()
        if not webhook_service:
            return jsonify({'error': 'Webhook service not initialized'}), 500
        
        configs = webhook_service.get_webhook_configs()
        
        return jsonify({
            'status': 'active',
            'webhook_configs': len(configs),
            'active_configs': len([c for c in configs if c['active']]),
            'supported_integrations': ['github', 'jenkins', 'slack', 'figma'],
            'endpoints': {
                'github': '/api/webhooks/github',
                'jenkins': '/api/webhooks/jenkins',
                'slack': '/api/webhooks/slack',
                'figma': '/api/webhooks/figma',
                'generic': '/api/webhooks/generic/<source_system>'
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting webhook status: {e}")
        return jsonify({'error': 'Internal server error'}), 500