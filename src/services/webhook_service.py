"""
Webhook service for external system integration via webhooks and events.
Handles inbound webhooks from external systems and outbound webhook notifications.
"""

import json
import hmac
import hashlib
import logging
import requests
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from urllib.parse import urlparse
import threading
from concurrent.futures import ThreadPoolExecutor

try:
    from ..core.events import Event, EventType, create_event
    from .event_bus import EventBus
    from ..models import db
except ImportError:
    from core.events import Event, EventType, create_event
    from services.event_bus import EventBus
    from models import db


logger = logging.getLogger(__name__)


class WebhookStatus(Enum):
    """Status of webhook deliveries."""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class WebhookConfig:
    """Configuration for webhook endpoints."""
    
    name: str
    url: str
    secret: Optional[str] = None
    events: List[str] = None
    headers: Dict[str, str] = None
    timeout: int = 30
    max_retries: int = 3
    retry_delay: int = 60
    active: bool = True
    
    def __post_init__(self):
        if self.events is None:
            self.events = []
        if self.headers is None:
            self.headers = {}


def create_webhook_event(
    source_system: str,
    webhook_type: str,
    payload: Dict[str, Any],
    headers: Dict[str, str] = None,
    correlation_id: Optional[str] = None,
    user_id: Optional[str] = None
) -> Event:
    """Create a webhook event using the existing event system."""
    import uuid
    
    return create_event(
        EventType.USER_ACTION,  # Use existing event type
        source=f"webhook_{source_system}",
        correlation_id=correlation_id,
        user_id=user_id,
        webhook_source=source_system,
        webhook_type=webhook_type,
        webhook_payload=payload,
        webhook_headers=headers or {}
    )


def create_outbound_webhook_event(
    target_system: str,
    event_type: str,
    payload: Dict[str, Any],
    webhook_config: str,
    correlation_id: Optional[str] = None,
    user_id: Optional[str] = None
) -> Event:
    """Create an outbound webhook event."""
    import uuid
    
    return create_event(
        EventType.SYSTEM_HEALTH_CHECK,  # Use existing event type
        source="webhook_sender",
        correlation_id=correlation_id,
        user_id=user_id,
        target_system=target_system,
        original_event_type=event_type,
        webhook_payload=payload,
        webhook_config=webhook_config
    )


class WebhookReceiver:
    """Service for receiving and processing inbound webhooks."""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.processors: Dict[str, Callable] = {}
        self._lock = threading.RLock()
    
    def register_processor(self, source_system: str, processor: Callable[[Dict[str, Any], Dict[str, str]], Event]):
        """Register a webhook processor for a specific source system."""
        with self._lock:
            self.processors[source_system] = processor
            logger.info(f"Registered webhook processor for {source_system}")
    
    def process_webhook(
        self,
        source_system: str,
        webhook_type: str,
        payload: Dict[str, Any],
        headers: Dict[str, str] = None,
        signature: Optional[str] = None,
        secret: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process an incoming webhook."""
        try:
            # Verify signature if provided
            if signature and secret:
                if not self._verify_signature(payload, signature, secret):
                    logger.warning(f"Invalid signature for webhook from {source_system}")
                    return {'status': 'error', 'message': 'Invalid signature'}
            
            # Create external webhook event
            webhook_event = create_webhook_event(
                source_system=source_system,
                webhook_type=webhook_type,
                payload=payload,
                headers=headers or {}
            )
            
            # Publish the webhook event
            result = self.event_bus.publish(webhook_event)
            
            # Process with registered processor if available
            if source_system in self.processors:
                try:
                    processed_event = self.processors[source_system](payload, headers or {})
                    if processed_event:
                        self.event_bus.publish(processed_event)
                        logger.info(f"Processed webhook from {source_system} and published {processed_event.event_type}")
                except Exception as e:
                    logger.error(f"Error processing webhook from {source_system}: {e}")
            
            logger.info(f"Successfully processed webhook from {source_system}: {webhook_type}")
            return {
                'status': 'success',
                'event_id': result['event_id'],
                'message': 'Webhook processed successfully'
            }
            
        except Exception as e:
            logger.error(f"Error processing webhook from {source_system}: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _verify_signature(self, payload: Dict[str, Any], signature: str, secret: str) -> bool:
        """Verify webhook signature."""
        try:
            payload_bytes = json.dumps(payload, sort_keys=True).encode('utf-8')
            expected_signature = hmac.new(
                secret.encode('utf-8'),
                payload_bytes,
                hashlib.sha256
            ).hexdigest()
            
            # Handle different signature formats
            if signature.startswith('sha256='):
                signature = signature[7:]
            
            return hmac.compare_digest(expected_signature, signature)
        except Exception as e:
            logger.error(f"Error verifying signature: {e}")
            return False


class WebhookSender:
    """Service for sending outbound webhooks to external systems."""
    
    def __init__(self, event_bus: EventBus, max_workers: int = 5):
        self.event_bus = event_bus
        self.webhook_configs: Dict[str, WebhookConfig] = {}
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._lock = threading.RLock()
        
        # Subscribe to events for outbound webhooks
        self.event_bus.subscribe(
            "project.created",
            self._handle_outbound_event
        )
        self.event_bus.subscribe(
            "project.updated", 
            self._handle_outbound_event
        )
        self.event_bus.subscribe(
            "build.completed",
            self._handle_outbound_event
        )
        self.event_bus.subscribe(
            "build.failed",
            self._handle_outbound_event
        )
    
    def register_webhook(self, config: WebhookConfig):
        """Register a webhook configuration."""
        with self._lock:
            self.webhook_configs[config.name] = config
            logger.info(f"Registered webhook configuration: {config.name}")
    
    def unregister_webhook(self, name: str) -> bool:
        """Unregister a webhook configuration."""
        with self._lock:
            if name in self.webhook_configs:
                del self.webhook_configs[name]
                logger.info(f"Unregistered webhook configuration: {name}")
                return True
            return False
    
    def send_webhook(
        self,
        config_name: str,
        event_type: str,
        payload: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send a webhook to an external system."""
        if config_name not in self.webhook_configs:
            return {'status': 'error', 'message': f'Webhook config {config_name} not found'}
        
        config = self.webhook_configs[config_name]
        if not config.active:
            return {'status': 'error', 'message': f'Webhook config {config_name} is inactive'}
        
        # Check if this event type should be sent to this webhook
        if config.events and event_type not in config.events:
            return {'status': 'skipped', 'message': f'Event type {event_type} not configured for {config_name}'}
        
        # Submit webhook delivery to thread pool
        future = self.executor.submit(
            self._deliver_webhook,
            config,
            event_type,
            payload,
            correlation_id
        )
        
        return {
            'status': 'queued',
            'message': f'Webhook delivery queued for {config_name}'
        }
    
    def _handle_outbound_event(self, event: Event):
        """Handle events that should trigger outbound webhooks."""
        try:
            event_type = event.event_type
            payload = event.data
            
            # Send to all configured webhooks that want this event type
            for config_name, config in self.webhook_configs.items():
                if config.active and (not config.events or event_type in config.events):
                    self.send_webhook(
                        config_name=config_name,
                        event_type=event_type,
                        payload=payload,
                        correlation_id=event.correlation_id
                    )
                    
        except Exception as e:
            logger.error(f"Error handling outbound event: {e}")
    
    def _deliver_webhook(
        self,
        config: WebhookConfig,
        event_type: str,
        payload: Dict[str, Any],
        correlation_id: Optional[str] = None
    ):
        """Deliver a webhook with retry logic."""
        webhook_payload = {
            'event_type': event_type,
            'timestamp': datetime.utcnow().isoformat(),
            'correlation_id': correlation_id,
            'data': payload
        }
        
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'SoftwareFactory-Webhook/1.0',
            **config.headers
        }
        
        # Add signature if secret is configured
        if config.secret:
            signature = self._generate_signature(webhook_payload, config.secret)
            headers['X-Signature-SHA256'] = f'sha256={signature}'
        
        for attempt in range(config.max_retries + 1):
            try:
                response = requests.post(
                    config.url,
                    json=webhook_payload,
                    headers=headers,
                    timeout=config.timeout
                )
                
                if response.status_code < 400:
                    logger.info(f"Successfully delivered webhook to {config.name}: {event_type}")
                    
                    # Publish success event
                    success_event = create_outbound_webhook_event(
                        target_system=config.name,
                        event_type=f"{event_type}.delivered",
                        payload={
                            'status_code': response.status_code,
                            'response_body': response.text[:1000]  # Truncate response
                        },
                        webhook_config=config.name,
                        correlation_id=correlation_id
                    )
                    self.event_bus.publish(success_event)
                    return
                else:
                    logger.warning(f"Webhook delivery failed to {config.name}: HTTP {response.status_code}")
                    
            except Exception as e:
                logger.error(f"Webhook delivery attempt {attempt + 1} failed to {config.name}: {e}")
            
            # Wait before retry (except on last attempt)
            if attempt < config.max_retries:
                threading.Event().wait(config.retry_delay)
        
        # All attempts failed
        logger.error(f"All webhook delivery attempts failed to {config.name} for event {event_type}")
        
        # Publish failure event
        failure_event = create_outbound_webhook_event(
            target_system=config.name,
            event_type=f"{event_type}.failed",
            payload={
                'attempts': config.max_retries + 1,
                'last_error': str(e) if 'e' in locals() else 'Unknown error'
            },
            webhook_config=config.name,
            correlation_id=correlation_id
        )
        self.event_bus.publish(failure_event)
    
    def _generate_signature(self, payload: Dict[str, Any], secret: str) -> str:
        """Generate HMAC signature for webhook payload."""
        payload_bytes = json.dumps(payload, sort_keys=True).encode('utf-8')
        return hmac.new(
            secret.encode('utf-8'),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
    
    def get_webhook_configs(self) -> List[Dict[str, Any]]:
        """Get all webhook configurations."""
        with self._lock:
            return [
                {
                    'name': config.name,
                    'url': config.url,
                    'events': config.events,
                    'active': config.active,
                    'timeout': config.timeout,
                    'max_retries': config.max_retries
                }
                for config in self.webhook_configs.values()
            ]


class WebhookService:
    """Main webhook service that combines receiver and sender."""
    
    def __init__(self, event_bus: EventBus, max_workers: int = 5):
        self.event_bus = event_bus
        self.receiver = WebhookReceiver(event_bus)
        self.sender = WebhookSender(event_bus, max_workers)
        self._initialized = False
    
    def initialize(self):
        """Initialize the webhook service."""
        if self._initialized:
            return
        
        logger.info("Initializing webhook service")
        self._initialized = True
    
    def process_inbound_webhook(
        self,
        source_system: str,
        webhook_type: str,
        payload: Dict[str, Any],
        headers: Dict[str, str] = None,
        signature: Optional[str] = None,
        secret: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process an inbound webhook."""
        return self.receiver.process_webhook(
            source_system=source_system,
            webhook_type=webhook_type,
            payload=payload,
            headers=headers,
            signature=signature,
            secret=secret
        )
    
    def register_inbound_processor(self, source_system: str, processor: Callable):
        """Register a processor for inbound webhooks from a specific system."""
        self.receiver.register_processor(source_system, processor)
    
    def register_outbound_webhook(self, config: WebhookConfig):
        """Register an outbound webhook configuration."""
        self.sender.register_webhook(config)
    
    def send_webhook(
        self,
        config_name: str,
        event_type: str,
        payload: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send an outbound webhook."""
        return self.sender.send_webhook(config_name, event_type, payload, correlation_id)
    
    def get_webhook_configs(self) -> List[Dict[str, Any]]:
        """Get all webhook configurations."""
        return self.sender.get_webhook_configs()


# Global webhook service instance
_webhook_service: Optional[WebhookService] = None


def init_webhook_service(event_bus: EventBus, max_workers: int = 5) -> WebhookService:
    """Initialize the global webhook service."""
    global _webhook_service
    if _webhook_service is None:
        _webhook_service = WebhookService(event_bus, max_workers)
        _webhook_service.initialize()
        logger.info("Webhook service initialized")
    return _webhook_service


def get_webhook_service() -> Optional[WebhookService]:
    """Get the global webhook service instance."""
    return _webhook_service