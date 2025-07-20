"""
API endpoints for webhook integration with external systems.
"""

import logging
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

        # After the challenge handshake, proceed with normal processing
        webhook_service = get_webhook_service()
        if not webhook_service:
            return jsonify({'error': 'Webhook service not initialized'}), 500

        headers = dict(request.headers)
        
        # Process the webhook
        result = webhook_service.process_inbound_webhook(
            source_system='slack',
            webhook_type=payload.get('type', 'unknown'),
            payload=payload,
            headers=headers,
            signature=headers.get('X-Slack-Signature'),
            secret=current_app.config.get('SLACK_SIGNING_SECRET')
        )
        
        if result['status'] == 'success':
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error handling Slack webhook: {e}")
        return jsonify({'error': 'Internal server error'}), 500


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