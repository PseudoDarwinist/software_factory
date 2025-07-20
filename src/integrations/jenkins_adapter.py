"""
Jenkins integration adapter for CI/CD webhook processing and event translation.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

try:
    from ..core.events import Event, EventType, create_event
    from ..services.webhook_service import WebhookConfig
except ImportError:
    from core.events import Event, EventType, create_event
    from services.webhook_service import WebhookConfig


logger = logging.getLogger(__name__)


def create_jenkins_build_event(
    job_name: str,
    build_number: int,
    build_status: str,
    build_data: Dict[str, Any],
    correlation_id: Optional[str] = None
) -> Event:
    """Create a Jenkins build event."""
    # Map build status to appropriate event type
    if build_status.upper() in ['SUCCESS', 'COMPLETED']:
        event_type = EventType.BUILD_COMPLETED
    elif build_status.upper() in ['FAILURE', 'FAILED']:
        event_type = EventType.BUILD_FAILED
    else:
        event_type = EventType.BUILD_STARTED
    
    return create_event(
        event_type,
        source="jenkins",
        correlation_id=correlation_id,
        user_id="jenkins",
        job_name=job_name,
        build_number=build_number,
        build_status=build_status,
        build_url=build_data.get('build', {}).get('full_url'),
        duration=build_data.get('build', {}).get('duration'),
        timestamp=build_data.get('build', {}).get('timestamp'),
        scm=build_data.get('build', {}).get('scm', {}),
        parameters=build_data.get('build', {}).get('parameters', []),
        artifacts=build_data.get('build', {}).get('artifacts', [])
    )


def create_jenkins_job_event(
    job_name: str,
    action: str,
    job_data: Dict[str, Any],
    correlation_id: Optional[str] = None
) -> Event:
    """Create a Jenkins job event."""
    return create_event(
        EventType.USER_ACTION,
        source="jenkins",
        correlation_id=correlation_id,
        user_id="jenkins",
        jenkins_event_type="job",
        job_name=job_name,
        action=action,
        job_url=job_data.get('url'),
        display_name=job_data.get('displayName'),
        description=job_data.get('description')
    )


class JenkinsAdapter:
    """Adapter for Jenkins webhook integration."""
    
    def __init__(self):
        self.jenkins_url = None
        self.api_token = None
    
    def configure(self, jenkins_url: Optional[str] = None, api_token: Optional[str] = None):
        """Configure the Jenkins adapter."""
        self.jenkins_url = jenkins_url
        self.api_token = api_token
        logger.info("Jenkins adapter configured")
    
    def process_webhook(self, payload: Dict[str, Any], headers: Dict[str, str]) -> Optional[Event]:
        """Process Jenkins webhook payload and return appropriate event."""
        try:
            logger.info("Processing Jenkins webhook")
            
            # Jenkins webhooks can have different formats depending on the plugin
            # Handle Generic Webhook Trigger plugin format
            if 'build' in payload:
                return self._handle_build_event(payload)
            elif 'job' in payload:
                return self._handle_job_event(payload)
            else:
                # Try to detect event type from payload structure
                return self._detect_and_handle_event(payload)
                
        except Exception as e:
            logger.error(f"Error processing Jenkins webhook: {e}")
            return None
    
    def _handle_build_event(self, payload: Dict[str, Any]) -> Optional[Event]:
        """Handle Jenkins build events."""
        build = payload.get('build', {})
        
        job_name = build.get('jobName') or build.get('job_name')
        build_number = build.get('number') or build.get('build_number')
        build_status = build.get('status') or build.get('result', 'UNKNOWN')
        
        if not job_name or build_number is None:
            logger.warning("Invalid Jenkins build event payload")
            return None
        
        return create_jenkins_build_event(
            job_name=job_name,
            build_number=int(build_number),
            build_status=build_status,
            build_data=payload
        )
    
    def _handle_job_event(self, payload: Dict[str, Any]) -> Optional[Event]:
        """Handle Jenkins job events."""
        job = payload.get('job', {})
        action = payload.get('action', 'updated')
        
        job_name = job.get('name') or job.get('displayName')
        
        if not job_name:
            logger.warning("Invalid Jenkins job event payload")
            return None
        
        return create_jenkins_job_event(
            job_name=job_name,
            action=action,
            job_data=job
        )
    
    def _detect_and_handle_event(self, payload: Dict[str, Any]) -> Optional[Event]:
        """Detect event type from payload structure and handle accordingly."""
        # Check for common Jenkins webhook fields
        if 'name' in payload and 'number' in payload:
            # Looks like a build event
            return create_jenkins_build_event(
                job_name=payload.get('name'),
                build_number=int(payload.get('number')),
                build_status=payload.get('status', 'UNKNOWN'),
                build_data={'build': payload}
            )
        elif 'jobName' in payload and 'buildNumber' in payload:
            # Another build event format
            return create_jenkins_build_event(
                job_name=payload.get('jobName'),
                build_number=int(payload.get('buildNumber')),
                build_status=payload.get('buildStatus', 'UNKNOWN'),
                build_data={'build': payload}
            )
        else:
            logger.warning(f"Unknown Jenkins webhook format: {list(payload.keys())}")
            return None
    
    def get_outbound_webhook_config(
        self,
        name: str,
        url: str,
        username: Optional[str] = None,
        api_token: Optional[str] = None,
        events: Optional[list] = None
    ) -> WebhookConfig:
        """Get webhook configuration for sending events to Jenkins."""
        if events is None:
            events = [
                'project.created',
                'project.updated',
                'github.push',
                'github.pull_request.opened',
                'github.pull_request.merged'
            ]
        
        headers = {
            'User-Agent': 'SoftwareFactory-Jenkins-Integration/1.0',
            'Content-Type': 'application/json'
        }
        
        # Add authentication if provided
        if username and api_token:
            import base64
            auth_string = f"{username}:{api_token}"
            auth_bytes = auth_string.encode('ascii')
            auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
            headers['Authorization'] = f'Basic {auth_b64}'
        
        return WebhookConfig(
            name=name,
            url=url,
            events=events,
            headers=headers,
            timeout=60,  # Jenkins can be slow
            max_retries=3,
            retry_delay=120
        )
    
    def format_outbound_payload(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Format payload for outbound Jenkins webhooks."""
        # Format for Jenkins Generic Webhook Trigger plugin
        jenkins_payload = {
            'event_type': event_type,
            'timestamp': datetime.utcnow().isoformat(),
            'source': 'software-factory'
        }
        
        # Map common fields to Jenkins-friendly names
        if 'project' in payload:
            project = payload['project']
            jenkins_payload.update({
                'project_name': project.get('name'),
                'project_id': project.get('id'),
                'repository_url': project.get('repository_url')
            })
        
        if 'repository' in payload:
            repo = payload['repository']
            jenkins_payload.update({
                'repo_name': repo.get('name'),
                'repo_full_name': repo.get('full_name'),
                'repo_url': repo.get('html_url'),
                'clone_url': repo.get('clone_url')
            })
        
        if 'pull_request' in payload:
            pr = payload['pull_request']
            jenkins_payload.update({
                'pr_number': pr.get('number'),
                'pr_title': pr.get('title'),
                'pr_branch': pr.get('head', {}).get('ref'),
                'pr_base_branch': pr.get('base', {}).get('ref'),
                'pr_sha': pr.get('head', {}).get('sha')
            })
        
        if 'commits' in payload:
            commits = payload['commits']
            if commits:
                latest_commit = commits[-1]
                jenkins_payload.update({
                    'commit_sha': latest_commit.get('id'),
                    'commit_message': latest_commit.get('message'),
                    'commit_author': latest_commit.get('author', {}).get('name')
                })
        
        # Add original payload as well
        jenkins_payload['original_payload'] = payload
        
        return jenkins_payload
    
    def trigger_build(
        self,
        job_name: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Trigger a Jenkins build programmatically."""
        if not self.jenkins_url or not self.api_token:
            return {'status': 'error', 'message': 'Jenkins not configured'}
        
        try:
            import requests
            
            # Build the trigger URL
            if parameters:
                url = f"{self.jenkins_url}/job/{job_name}/buildWithParameters"
            else:
                url = f"{self.jenkins_url}/job/{job_name}/build"
            
            # Prepare authentication
            auth = None
            if self.api_token:
                # Assuming username is extracted from token or configured separately
                auth = ('admin', self.api_token)  # This should be configurable
            
            # Make the request
            response = requests.post(
                url,
                data=parameters or {},
                auth=auth,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                return {
                    'status': 'success',
                    'message': f'Build triggered for job {job_name}',
                    'queue_url': response.headers.get('Location')
                }
            else:
                return {
                    'status': 'error',
                    'message': f'Failed to trigger build: HTTP {response.status_code}'
                }
                
        except Exception as e:
            logger.error(f"Error triggering Jenkins build: {e}")
            return {'status': 'error', 'message': str(e)}