"""
Setup and configuration for external system integrations.
"""

import logging
from typing import Optional

try:
    from .webhook_service import get_webhook_service, WebhookConfig
    from ..integrations import GitHubAdapter, JenkinsAdapter, SlackAdapter, FigmaAdapter
except ImportError:
    from services.webhook_service import get_webhook_service, WebhookConfig
    from integrations import GitHubAdapter, JenkinsAdapter, SlackAdapter, FigmaAdapter


logger = logging.getLogger(__name__)


def setup_integrations(app):
    """Set up all external system integrations."""
    webhook_service = get_webhook_service()
    if not webhook_service:
        logger.error("Webhook service not available for integration setup")
        return False
    
    try:
        # Set up GitHub integration
        setup_github_integration(webhook_service, app.config)
        
        # Set up Jenkins integration
        setup_jenkins_integration(webhook_service, app.config)
        
        # Set up Slack integration
        setup_slack_integration(webhook_service, app.config)
        
        # Set up Figma integration
        setup_figma_integration(webhook_service, app.config)
        
        logger.info("All integrations set up successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error setting up integrations: {e}")
        return False


def setup_github_integration(webhook_service, config):
    """Set up GitHub integration."""
    try:
        # Create and configure GitHub adapter
        github_adapter = GitHubAdapter()
        github_adapter.configure(
            webhook_secret=config.get('GITHUB_WEBHOOK_SECRET')
        )
        
        # Register the adapter as a webhook processor
        webhook_service.register_inbound_processor('github', github_adapter.process_webhook)
        
        # Set up outbound webhook if configured
        github_webhook_url = config.get('GITHUB_OUTBOUND_WEBHOOK_URL')
        if github_webhook_url:
            github_config = github_adapter.get_outbound_webhook_config(
                name='github_outbound',
                url=github_webhook_url,
                secret=config.get('GITHUB_OUTBOUND_WEBHOOK_SECRET'),
                events=[
                    'project.created',
                    'project.updated',
                    'build.completed',
                    'build.failed'
                ]
            )
            webhook_service.register_outbound_webhook(github_config)
            logger.info("GitHub outbound webhook configured")
        
        logger.info("GitHub integration set up successfully")
        
    except Exception as e:
        logger.error(f"Error setting up GitHub integration: {e}")


def setup_jenkins_integration(webhook_service, config):
    """Set up Jenkins integration."""
    try:
        # Create and configure Jenkins adapter
        jenkins_adapter = JenkinsAdapter()
        jenkins_adapter.configure(
            jenkins_url=config.get('JENKINS_URL'),
            api_token=config.get('JENKINS_API_TOKEN')
        )
        
        # Register the adapter as a webhook processor
        webhook_service.register_inbound_processor('jenkins', jenkins_adapter.process_webhook)
        
        # Set up outbound webhook if configured
        jenkins_webhook_url = config.get('JENKINS_WEBHOOK_URL')
        if jenkins_webhook_url:
            jenkins_config = jenkins_adapter.get_outbound_webhook_config(
                name='jenkins_outbound',
                url=jenkins_webhook_url,
                username=config.get('JENKINS_USERNAME'),
                api_token=config.get('JENKINS_API_TOKEN'),
                events=[
                    'project.created',
                    'project.updated',
                    'github.push',
                    'github.pull_request.opened',
                    'github.pull_request.merged'
                ]
            )
            webhook_service.register_outbound_webhook(jenkins_config)
            logger.info("Jenkins outbound webhook configured")
        
        logger.info("Jenkins integration set up successfully")
        
    except Exception as e:
        logger.error(f"Error setting up Jenkins integration: {e}")


def setup_slack_integration(webhook_service, config):
    """Set up Slack integration."""
    try:
        # Create and configure Slack adapter
        slack_adapter = SlackAdapter()
        slack_adapter.configure(
            bot_token=config.get('SLACK_BOT_TOKEN'),
            signing_secret=config.get('SLACK_SIGNING_SECRET'),
            webhook_url=config.get('SLACK_WEBHOOK_URL')
        )
        
        # Register the adapter as a webhook processor
        webhook_service.register_inbound_processor('slack', slack_adapter.process_webhook)
        
        # Set up outbound webhook if configured
        slack_webhook_url = config.get('SLACK_WEBHOOK_URL')
        if slack_webhook_url:
            slack_config = slack_adapter.get_outbound_webhook_config(
                name='slack_notifications',
                webhook_url=slack_webhook_url,
                events=[
                    'project.created',
                    'project.updated',
                    'build.completed',
                    'build.failed',
                    'github.pull_request.opened',
                    'github.pull_request.merged',
                    'jenkins.build.completed',
                    'jenkins.build.failed'
                ]
            )
            webhook_service.register_outbound_webhook(slack_config)
            logger.info("Slack notifications configured")
        
        logger.info("Slack integration set up successfully")
        
    except Exception as e:
        logger.error(f"Error setting up Slack integration: {e}")


def setup_figma_integration(webhook_service, config):
    """Set up Figma integration."""
    try:
        # Create and configure Figma adapter
        figma_adapter = FigmaAdapter()
        figma_adapter.configure(
            access_token=config.get('FIGMA_ACCESS_TOKEN'),
            team_id=config.get('FIGMA_TEAM_ID')
        )
        
        # Register the adapter as a webhook processor
        webhook_service.register_inbound_processor('figma', figma_adapter.process_webhook)
        
        logger.info("Figma integration set up successfully")
        
    except Exception as e:
        logger.error(f"Error setting up Figma integration: {e}")


def get_integration_status():
    """Get status of all integrations."""
    webhook_service = get_webhook_service()
    if not webhook_service:
        return {'status': 'error', 'message': 'Webhook service not available'}
    
    try:
        configs = webhook_service.get_webhook_configs()
        
        return {
            'status': 'active',
            'integrations': {
                'github': {
                    'inbound': True,  # Always available
                    'outbound': any(c['name'] == 'github_outbound' for c in configs)
                },
                'jenkins': {
                    'inbound': True,  # Always available
                    'outbound': any(c['name'] == 'jenkins_outbound' for c in configs)
                },
                'slack': {
                    'inbound': True,  # Always available
                    'outbound': any(c['name'] == 'slack_notifications' for c in configs)
                },
                'figma': {
                    'inbound': True,  # Always available
                    'outbound': False  # Figma doesn't typically receive webhooks
                }
            },
            'webhook_configs': len(configs),
            'active_configs': len([c for c in configs if c['active']])
        }
        
    except Exception as e:
        logger.error(f"Error getting integration status: {e}")
        return {'status': 'error', 'message': str(e)}