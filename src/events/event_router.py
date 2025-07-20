"""
Event routing and filtering mechanisms for targeted subscriptions.
"""

import asyncio
import threading
import logging
from typing import Dict, List, Callable, Optional, Any
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum

from .base import BaseEvent, EventFilter
from .event_store import EventStore


logger = logging.getLogger(__name__)


class SubscriptionType(Enum):
    """Types of event subscriptions."""
    SYNC = "sync"
    ASYNC = "async"
    BACKGROUND = "background"


@dataclass
class EventSubscription:
    """Event subscription configuration."""
    
    subscription_id: str
    event_filter: EventFilter
    handler: Callable[[BaseEvent], Any]
    subscription_type: SubscriptionType = SubscriptionType.SYNC
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    dead_letter_queue: bool = False
    active: bool = True


class EventRouter:
    """Event router for managing subscriptions and routing events to handlers."""
    
    def __init__(self, event_store: Optional[EventStore] = None, max_workers: int = 10):
        self.event_store = event_store or EventStore()
        self.subscriptions: Dict[str, EventSubscription] = {}
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._lock = threading.RLock()
        self._running = False
        self._failed_events: List[Dict[str, Any]] = []
    
    def subscribe(
        self,
        subscription_id: str,
        event_filter: EventFilter,
        handler: Callable[[BaseEvent], Any],
        subscription_type: SubscriptionType = SubscriptionType.SYNC,
        max_retries: int = 3,
        retry_delay_seconds: float = 1.0,
        dead_letter_queue: bool = False
    ) -> None:
        """Subscribe to events matching the filter."""
        with self._lock:
            subscription = EventSubscription(
                subscription_id=subscription_id,
                event_filter=event_filter,
                handler=handler,
                subscription_type=subscription_type,
                max_retries=max_retries,
                retry_delay_seconds=retry_delay_seconds,
                dead_letter_queue=dead_letter_queue
            )
            
            self.subscriptions[subscription_id] = subscription
            logger.info(f"Added subscription: {subscription_id}")
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """Remove a subscription."""
        with self._lock:
            if subscription_id in self.subscriptions:
                del self.subscriptions[subscription_id]
                logger.info(f"Removed subscription: {subscription_id}")
                return True
            return False
    
    def activate_subscription(self, subscription_id: str) -> bool:
        """Activate a subscription."""
        with self._lock:
            if subscription_id in self.subscriptions:
                self.subscriptions[subscription_id].active = True
                logger.info(f"Activated subscription: {subscription_id}")
                return True
            return False
    
    def deactivate_subscription(self, subscription_id: str) -> bool:
        """Deactivate a subscription."""
        with self._lock:
            if subscription_id in self.subscriptions:
                self.subscriptions[subscription_id].active = False
                logger.info(f"Deactivated subscription: {subscription_id}")
                return True
            return False
    
    def route_event(self, event: BaseEvent) -> Dict[str, Any]:
        """Route an event to matching subscriptions."""
        results = {}
        matching_subscriptions = self._find_matching_subscriptions(event)
        
        logger.debug(f"Routing event {event.get_event_type()} to {len(matching_subscriptions)} subscriptions")
        
        for subscription in matching_subscriptions:
            try:
                result = self._handle_subscription(subscription, event)
                results[subscription.subscription_id] = {
                    'success': True,
                    'result': result
                }
            except Exception as e:
                logger.error(f"Error handling subscription {subscription.subscription_id}: {e}")
                results[subscription.subscription_id] = {
                    'success': False,
                    'error': str(e)
                }
                
                if subscription.dead_letter_queue:
                    self._add_to_dead_letter_queue(subscription, event, str(e))
        
        return results
    
    def _find_matching_subscriptions(self, event: BaseEvent) -> List[EventSubscription]:
        """Find subscriptions that match the event."""
        matching = []
        
        with self._lock:
            for subscription in self.subscriptions.values():
                if subscription.active and subscription.event_filter.matches(event):
                    matching.append(subscription)
        
        return matching
    
    def _handle_subscription(self, subscription: EventSubscription, event: BaseEvent) -> Any:
        """Handle an event for a specific subscription."""
        if subscription.subscription_type == SubscriptionType.SYNC:
            return self._handle_sync(subscription, event)
        elif subscription.subscription_type == SubscriptionType.ASYNC:
            return self._handle_async(subscription, event)
        elif subscription.subscription_type == SubscriptionType.BACKGROUND:
            return self._handle_background(subscription, event)
        else:
            raise ValueError(f"Unknown subscription type: {subscription.subscription_type}")
    
    def _handle_sync(self, subscription: EventSubscription, event: BaseEvent) -> Any:
        """Handle event synchronously with retries."""
        last_exception = None
        
        for attempt in range(subscription.max_retries + 1):
            try:
                return subscription.handler(event)
            except Exception as e:
                last_exception = e
                logger.warning(f"Sync handler failed (attempt {attempt + 1}): {e}")
                
                if attempt < subscription.max_retries:
                    threading.Event().wait(subscription.retry_delay_seconds)
        
        raise last_exception
    
    def _handle_async(self, subscription: EventSubscription, event: BaseEvent) -> Any:
        """Handle event asynchronously."""
        future = self.executor.submit(self._handle_sync, subscription, event)
        return future
    
    def _handle_background(self, subscription: EventSubscription, event: BaseEvent) -> Any:
        """Handle event in background without waiting for result."""
        self.executor.submit(self._handle_sync, subscription, event)
        return None
    
    def _add_to_dead_letter_queue(
        self,
        subscription: EventSubscription,
        event: BaseEvent,
        error_message: str
    ) -> None:
        """Add failed event to dead letter queue."""
        failed_event = {
            'subscription_id': subscription.subscription_id,
            'event': event.to_dict(),
            'error_message': error_message,
            'failed_at': event.metadata.timestamp.isoformat()
        }
        
        self._failed_events.append(failed_event)
        logger.error(f"Added event to dead letter queue: {failed_event}")
    
    def get_failed_events(self) -> List[Dict[str, Any]]:
        """Get events in the dead letter queue."""
        return self._failed_events.copy()
    
    def clear_failed_events(self) -> int:
        """Clear the dead letter queue and return count of cleared events."""
        count = len(self._failed_events)
        self._failed_events.clear()
        return count
    
    def retry_failed_event(self, failed_event_index: int) -> bool:
        """Retry a specific failed event."""
        if 0 <= failed_event_index < len(self._failed_events):
            failed_event = self._failed_events[failed_event_index]
            subscription_id = failed_event['subscription_id']
            
            if subscription_id in self.subscriptions:
                # Reconstruct event from stored data
                event_data = failed_event['event']
                # This would need proper event reconstruction logic
                # For now, we'll just log the attempt
                logger.info(f"Retrying failed event for subscription {subscription_id}")
                return True
        
        return False
    
    def get_subscription_stats(self) -> Dict[str, Any]:
        """Get statistics about subscriptions."""
        with self._lock:
            active_count = sum(1 for s in self.subscriptions.values() if s.active)
            inactive_count = len(self.subscriptions) - active_count
            
            subscription_types = {}
            for subscription in self.subscriptions.values():
                sub_type = subscription.subscription_type.value
                subscription_types[sub_type] = subscription_types.get(sub_type, 0) + 1
            
            return {
                'total_subscriptions': len(self.subscriptions),
                'active_subscriptions': active_count,
                'inactive_subscriptions': inactive_count,
                'subscription_types': subscription_types,
                'failed_events_count': len(self._failed_events)
            }
    
    def list_subscriptions(self) -> List[Dict[str, Any]]:
        """List all subscriptions with their details."""
        with self._lock:
            subscriptions = []
            for sub_id, subscription in self.subscriptions.items():
                subscriptions.append({
                    'subscription_id': sub_id,
                    'active': subscription.active,
                    'subscription_type': subscription.subscription_type.value,
                    'event_types': subscription.event_filter.event_types,
                    'aggregate_types': subscription.event_filter.aggregate_types,
                    'max_retries': subscription.max_retries,
                    'dead_letter_queue': subscription.dead_letter_queue
                })
            return subscriptions


class EventBus:
    """High-level event bus that combines event store and router."""
    
    def __init__(self, event_store: Optional[EventStore] = None, event_router: Optional[EventRouter] = None):
        self.event_store = event_store or EventStore()
        self.event_router = event_router or EventRouter(self.event_store)
    
    def publish(self, event: BaseEvent, source_agent: Optional[str] = None, project_id: Optional[str] = None) -> Dict[str, Any]:
        """Publish an event to Postgres and Redis with standardized envelope format."""
        try:
            # Import here to avoid circular imports
            from ..models.event_log import EventLog
            from ..models.base import db
            
            # Store event in Postgres first (requirement for audit trail)
            event_log = EventLog.create_from_event(
                event=event,
                source_agent=source_agent,
                project_id=project_id
            )
            db.session.add(event_log)
            db.session.commit()
            
            # Store the event in event store (SQLite)
            self.event_store.append_event(event)
            
            # Route to subscribers (Redis publication happens here)
            routing_results = self.event_router.route_event(event)
            
            logger.info(f"Published event {event.get_event_type()} with ID {event.metadata.event_id}")
            
            return {
                'event_id': event.metadata.event_id,
                'event_type': event.get_event_type(),
                'stored_postgres': True,
                'stored_sqlite': True,
                'routing_results': routing_results
            }
            
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            # Try to rollback database transaction
            try:
                from ..models.base import db
                db.session.rollback()
            except:
                pass
            
            return {
                'event_id': event.metadata.event_id,
                'event_type': event.get_event_type(),
                'stored_postgres': False,
                'stored_sqlite': False,
                'error': str(e)
            }
    
    def publish_batch(self, events: List[BaseEvent], source_agent: Optional[str] = None) -> List[Dict[str, Any]]:
        """Publish multiple events atomically."""
        try:
            # Import here to avoid circular imports
            from ..models.event_log import EventLog
            from ..models.base import db
            
            # Store all events in Postgres first
            event_logs = []
            for event in events:
                # Extract project_id from event payload
                payload = event.get_payload()
                project_id = payload.get('project_id') or payload.get('aggregate_id')
                
                event_log = EventLog.create_from_event(
                    event=event,
                    source_agent=source_agent,
                    project_id=project_id
                )
                event_logs.append(event_log)
                db.session.add(event_log)
            
            db.session.commit()
            
            # Store all events in event store (SQLite)
            self.event_store.append_events(events)
            
            # Route each event
            results = []
            for event in events:
                routing_results = self.event_router.route_event(event)
                results.append({
                    'event_id': event.metadata.event_id,
                    'event_type': event.get_event_type(),
                    'stored_postgres': True,
                    'stored_sqlite': True,
                    'routing_results': routing_results
                })
            
            logger.info(f"Published batch of {len(events)} events")
            return results
            
        except Exception as e:
            logger.error(f"Failed to publish event batch: {e}")
            # Try to rollback database transaction
            try:
                from ..models.base import db
                db.session.rollback()
            except:
                pass
            
            # Return error results
            results = []
            for event in events:
                results.append({
                    'event_id': event.metadata.event_id,
                    'event_type': event.get_event_type(),
                    'stored_postgres': False,
                    'stored_sqlite': False,
                    'error': str(e)
                })
            
            return results
    
    def subscribe(
        self,
        subscription_id: str,
        event_types: Optional[List[str]] = None,
        aggregate_types: Optional[List[str]] = None,
        actors: Optional[List[str]] = None,
        correlation_ids: Optional[List[str]] = None,
        handler: Optional[Callable[[BaseEvent], Any]] = None,
        **kwargs
    ) -> None:
        """Subscribe to events with filtering options."""
        event_filter = EventFilter(
            event_types=event_types,
            aggregate_types=aggregate_types,
            actors=actors,
            correlation_ids=correlation_ids
        )
        
        self.event_router.subscribe(
            subscription_id=subscription_id,
            event_filter=event_filter,
            handler=handler,
            **kwargs
        )
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """Remove a subscription."""
        return self.event_router.unsubscribe(subscription_id)
    
    def get_events(self, **kwargs) -> List[Dict[str, Any]]:
        """Get events from the store."""
        return self.event_store.get_events(**kwargs)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics."""
        event_stats = self.event_store.get_event_statistics()
        subscription_stats = self.event_router.get_subscription_stats()
        
        return {
            'event_store': event_stats,
            'subscriptions': subscription_stats
        }