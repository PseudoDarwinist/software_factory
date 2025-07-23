"""
API endpoints for webhook integration with external systems.
"""

import logging
import time
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
        webhook_service = get_webhook_service()
        if not webhook_service:
            return jsonify({'error': 'Webhook service not initialized'}), 500
        
        # Get payload and headers
        payload = request.get_json()
        headers = dict(request.headers)
        
        # Get signature for verification
        signature = headers.get('X-Hub-Signature-256', headers.get('x-hub-signature-256'))
        
        # Process the webhook
        result = webhook_service.process_inbound_webhook(
            source_system='github',
            webhook_type=headers.get('X-GitHub-Event', 'unknown'),
            payload=payload,
            headers=headers,
            signature=signature,
            secret=current_app.config.get('GITHUB_WEBHOOK_SECRET')
        )
        
        if result['status'] == 'success':
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error handling GitHub webhook: {e}")
        return jsonify({'error': 'Internal server error'}), 500


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
            
            # Create feed item using direct database operations
            try:
                # Import models using the pattern that works with Flask app context
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
                        return jsonify({'status': 'ignored', 'reason': 'project_not_found'}), 200
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
                
                # Create unique feed item ID
                import time
                feed_item_id = f"slack_{channel}_{timestamp or int(time.time())}"
                
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
                try:
                    db.session.rollback()
                except:
                    pass
                
                # Fallback: just log the message and return success
                logger.info(f"Slack message received (DB failed): {text[:100]}...")
                return jsonify({
                    'status': 'success',
                    'message': 'Slack message logged (database error)',
                    'slack_text': text[:100]
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