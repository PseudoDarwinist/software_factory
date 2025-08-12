#!/usr/bin/env python3
"""
WebSocket Server - Real-time Frontend Communication with User Permission Filtering
Bridges Redis events to WebSocket connections for live UI updates with project-scoped security
"""

import json
import logging
from typing import Dict, Any, Optional, Set, List
from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
import eventlet
from datetime import datetime, timedelta

try:
    from ..core.events import Event, EventType
    from .event_bus import get_event_bus, EventBus
    from .auth_service import get_auth_service, UserPermissions, decode_token
except ImportError:
    try:
        from core.events import Event, EventType
        from services.event_bus import get_event_bus, EventBus
        from services.auth_service import get_auth_service, UserPermissions, decode_token
    except ImportError:
        # For testing, create minimal implementations
        Event = None
        EventType = None
        get_event_bus = lambda: None
        EventBus = None
        get_auth_service = lambda: None
        UserPermissions = None
        decode_token = lambda x: None


logger = logging.getLogger(__name__)


class WebSocketServer:
    """WebSocket server for real-time event broadcasting with user permission filtering"""
    
    def __init__(self, app: Flask):
        self.app = app
        self.socketio = SocketIO(
            app,
            cors_allowed_origins="*",
            async_mode='eventlet',
            logger=True,
            engineio_logger=True,
            max_http_buffer_size=10000000,  # 10MB (default is 1MB)
            ping_timeout=60,
            ping_interval=25
        )
        self.event_bus = get_event_bus() if get_event_bus else None
        self.auth_service = get_auth_service() if get_auth_service else None
        self.connected_clients: Dict[str, Dict[str, Any]] = {}
        self.room_subscriptions: Dict[str, Set[str]] = {}
        self.user_presence: Dict[str, Set[str]] = {}  # user_id -> set of client_ids
        
        # Connection management
        self.heartbeat_interval = 30  # seconds
        self.connection_timeout = 300  # 5 minutes
        self.max_connections_per_user = 10
        
        # Statistics
        self.stats = {
            'connections': 0,
            'authenticated_connections': 0,
            'messages_sent': 0,
            'events_processed': 0,
            'events_filtered': 0,
            'authentication_failures': 0,
            'errors': 0
        }
        
        self._setup_event_handlers()
        self._setup_event_subscriptions()
        self._setup_heartbeat()
    
    def _setup_event_handlers(self):
        """Setup WebSocket event handlers"""
        
        @self.socketio.on('connect')
        def handle_connect(auth=None):
            """Handle client connection"""
            client_id = request.sid
            client_info = {
                'id': client_id,
                'connected_at': datetime.utcnow(),
                'last_heartbeat': datetime.utcnow(),
                'user_id': None,
                'permissions': None,
                'authenticated': False,
                'project_ids': set(),
                'subscriptions': set(),
                'ip_address': request.environ.get('REMOTE_ADDR', 'unknown')
            }
            
            self.connected_clients[client_id] = client_info
            self.stats['connections'] += 1
            
            logger.debug(f"Client connected: {client_id} from {client_info['ip_address']}")
            
            # Send welcome message with authentication requirement
            emit('welcome', {
                'client_id': client_id,
                'server_time': datetime.utcnow().isoformat(),
                'message': 'Connected to Software Factory Event Stream',
                'authentication_required': True,
                'heartbeat_interval': self.heartbeat_interval
            })

            # Attempt auto-authentication using Socket.IO 'auth' handshake payload
            try:
                token = None
                if isinstance(auth, dict):
                    token = auth.get('token') or auth.get('Authorization') or auth.get('authorization')
                # Some clients pass Bearer prefix
                if isinstance(token, str) and token.lower().startswith('bearer '):
                    token = token.split(' ', 1)[1]
                if token and self.auth_service is not None:
                    permissions = self.auth_service.decode_token(token)
                    if permissions:
                        client_info['user_id'] = permissions.user_id
                        client_info['permissions'] = permissions
                        client_info['authenticated'] = True
                        client_info['project_ids'] = permissions.project_ids
                        # Track presence
                        user_id = permissions.user_id
                        if user_id not in self.user_presence:
                            self.user_presence[user_id] = set()
                        self.user_presence[user_id].add(client_id)
                        self.stats['authenticated_connections'] += 1
                        logger.info(f"Client {client_id} auto-authenticated on connect (user {permissions.user_id})")
                        emit('authenticated', {
                            'user_id': permissions.user_id,
                            'username': permissions.username,
                            'project_ids': list(permissions.project_ids),
                            'roles': list(permissions.roles),
                            'is_admin': permissions.is_admin,
                            'expires_at': permissions.expires_at.isoformat() if permissions.expires_at else None
                        })
                    else:
                        logger.warning(f"Client {client_id} provided invalid token in connect auth payload")
                else:
                    logger.debug(f"Client {client_id} connected without auth token; awaiting explicit authenticate event")
            except Exception as e:
                logger.warning(f"Auto-auth on connect failed for client {client_id}: {e}")
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection"""
            client_id = request.sid
            
            if client_id in self.connected_clients:
                client_info = self.connected_clients[client_id]
                user_id = client_info.get('user_id')
                
                # Leave all rooms
                for room in client_info['subscriptions']:
                    leave_room(room)
                    if room in self.room_subscriptions:
                        self.room_subscriptions[room].discard(client_id)
                
                # Update user presence
                if user_id and user_id in self.user_presence:
                    self.user_presence[user_id].discard(client_id)
                    if not self.user_presence[user_id]:
                        del self.user_presence[user_id]
                        # Broadcast user offline status
                        self._broadcast_presence_update(user_id, 'offline')
                
                del self.connected_clients[client_id]
                
                logger.info(f"Client disconnected: {client_id} (user: {user_id})")
        
        @self.socketio.on('authenticate')
        def handle_authenticate(data):
            """Handle client authentication with JWT token"""
            client_id = request.sid
            
            if client_id not in self.connected_clients:
                emit('error', {'message': 'Client not registered'})
                return
            
            try:
                token = data.get('token')
                if not token:
                    emit('auth_error', {'message': 'Token required'})
                    self.stats['authentication_failures'] += 1
                    return
                
                # Decode and validate token
                permissions = self.auth_service.decode_token(token)
                if not permissions:
                    emit('auth_error', {'message': 'Invalid or expired token'})
                    self.stats['authentication_failures'] += 1
                    return
                
                # Check connection limits per user
                user_id = permissions.user_id
                if user_id in self.user_presence:
                    if len(self.user_presence[user_id]) >= self.max_connections_per_user:
                        emit('auth_error', {'message': 'Too many connections for user'})
                        self.stats['authentication_failures'] += 1
                        return
                
                # Update client info
                client_info = self.connected_clients[client_id]
                client_info['user_id'] = user_id
                client_info['permissions'] = permissions
                client_info['authenticated'] = True
                client_info['project_ids'] = permissions.project_ids
                
                # Update user presence
                if user_id not in self.user_presence:
                    self.user_presence[user_id] = set()
                self.user_presence[user_id].add(client_id)
                
                self.stats['authenticated_connections'] += 1
                
                logger.info(f"Client {client_id} authenticated as user {user_id}")
                
                # Broadcast user online status
                self._broadcast_presence_update(user_id, 'online')
                
                # Send authentication success
                emit('authenticated', {
                    'user_id': user_id,
                    'username': permissions.username,
                    'project_ids': list(permissions.project_ids),
                    'roles': list(permissions.roles),
                    'is_admin': permissions.is_admin,
                    'expires_at': permissions.expires_at.isoformat() if permissions.expires_at else None
                })
                
            except Exception as e:
                logger.error(f"Error handling authentication: {e}")
                emit('auth_error', {'message': 'Authentication failed'})
                self.stats['authentication_failures'] += 1
                self.stats['errors'] += 1
        
        @self.socketio.on('subscribe')
        def handle_subscribe(data):
            """Handle subscription to event types or rooms with permission checking"""
            client_id = request.sid
            
            if client_id not in self.connected_clients:
                emit('error', {'message': 'Client not registered'})
                return
            
            client_info = self.connected_clients[client_id]
            # Allow subscription in dev/test environments even without full auth. If an
            # auth service is configured we still enforce it, but when auth_service is
            # None (e.g. local development) we skip the check so the frontend can
            # receive live task progress without JWT setup.
            if self.auth_service is not None and not client_info.get('authenticated'):
                emit('error', {'message': 'Authentication required'})
                return
            
            try:
                subscription_type = data.get('type')  # 'event', 'project', 'user'
                subscription_id = data.get('id')
                
                if not subscription_type or not subscription_id:
                    emit('error', {'message': 'Invalid subscription data'})
                    return
                
                # Check permissions for project subscriptions
                if subscription_type == 'project':
                    permissions = client_info['permissions']
                    if not permissions.has_project_access(subscription_id):
                        emit('error', {'message': 'Access denied to project'})
                        return
                
                room = f"{subscription_type}:{subscription_id}"
                
                # Join room
                join_room(room)
                
                # Update client info
                client_info['subscriptions'].add(room)
                
                # Track room subscriptions
                if room not in self.room_subscriptions:
                    self.room_subscriptions[room] = set()
                self.room_subscriptions[room].add(client_id)
                
                logger.info(f"Client {client_id} subscribed to {room}")
                
                emit('subscribed', {
                    'type': subscription_type,
                    'id': subscription_id,
                    'room': room
                })
                
            except Exception as e:
                logger.error(f"Error handling subscription: {e}")
                emit('error', {'message': 'Subscription failed'})
                self.stats['errors'] += 1
        
        @self.socketio.on('unsubscribe')
        def handle_unsubscribe(data):
            """Handle unsubscription from event types or rooms"""
            client_id = request.sid
            
            if client_id not in self.connected_clients:
                emit('error', {'message': 'Client not registered'})
                return
            
            try:
                subscription_type = data.get('type')
                subscription_id = data.get('id')
                
                if not subscription_type or not subscription_id:
                    emit('error', {'message': 'Invalid unsubscription data'})
                    return
                
                room = f"{subscription_type}:{subscription_id}"
                
                # Leave room
                leave_room(room)
                
                # Update client info
                client_info = self.connected_clients[client_id]
                client_info['subscriptions'].discard(room)
                
                # Update room subscriptions
                if room in self.room_subscriptions:
                    self.room_subscriptions[room].discard(client_id)
                    if not self.room_subscriptions[room]:
                        del self.room_subscriptions[room]
                
                logger.info(f"Client {client_id} unsubscribed from {room}")
                
                emit('unsubscribed', {
                    'type': subscription_type,
                    'id': subscription_id,
                    'room': room
                })
                
            except Exception as e:
                logger.error(f"Error handling unsubscription: {e}")
                emit('error', {'message': 'Unsubscription failed'})
                self.stats['errors'] += 1
        
        @self.socketio.on('heartbeat')
        def handle_heartbeat(data):
            """Handle heartbeat for connection health check"""
            client_id = request.sid
            
            if client_id in self.connected_clients:
                client_info = self.connected_clients[client_id]
                client_info['last_heartbeat'] = datetime.utcnow()
                
                emit('heartbeat_ack', {
                    'timestamp': datetime.utcnow().isoformat(),
                    'client_data': data
                })
            else:
                emit('error', {'message': 'Client not registered'})
        
        @self.socketio.on('ping')
        def handle_ping(data):
            """Handle ping for connection health check (legacy support)"""
            emit('pong', {
                'timestamp': datetime.utcnow().isoformat(),
                'client_data': data
            })
        
        @self.socketio.on('subscribe_task')
        def handle_task_subscription(data):
            """Handle client subscription to task progress"""
            client_id = request.sid
            
            if client_id not in self.connected_clients:
                emit('error', {'message': 'Client not registered'})
                return
            
            client_info = self.connected_clients[client_id]
            # Allow subscription in dev/test environments even without full auth. If an
            # auth service is configured we still enforce it, but when auth_service is
            # None (e.g. local development) we skip the check so the frontend can
            # receive live task progress without JWT setup.
            if self.auth_service is not None and not client_info.get('authenticated'):
                emit('error', {'message': 'Authentication required'})
                return
            
            try:
                task_id = data.get('taskId')
                if not task_id:
                    emit('error', {'message': 'taskId is required'})
                    return
                
                # TODO: Add permission check for task access based on project
                # For now, allow all authenticated users
                
                room = f'task_{task_id}'
                join_room(room)
                client_info['subscriptions'].add(room)
                
                if room not in self.room_subscriptions:
                    self.room_subscriptions[room] = set()
                self.room_subscriptions[room].add(client_id)
                
                logger.info(f"Client {client_id} subscribed to task {task_id}")
                
                emit('task_subscribed', {
                    'taskId': task_id,
                    'room': room
                })
                
            except Exception as e:
                logger.error(f"Error handling task subscription: {e}")
                emit('error', {'message': 'Task subscription failed'})
                self.stats['errors'] += 1
        
        @self.socketio.on('unsubscribe_task')
        def handle_task_unsubscription(data):
            """Handle client unsubscription from task progress"""
            client_id = request.sid
            
            if client_id not in self.connected_clients:
                emit('error', {'message': 'Client not registered'})
                return
            
            try:
                task_id = data.get('taskId')
                if not task_id:
                    emit('error', {'message': 'taskId is required'})
                    return
                
                room = f'task_{task_id}'
                leave_room(room)
                
                client_info = self.connected_clients[client_id]
                client_info['subscriptions'].discard(room)
                
                if room in self.room_subscriptions:
                    self.room_subscriptions[room].discard(client_id)
                    if not self.room_subscriptions[room]:
                        del self.room_subscriptions[room]
                
                logger.info(f"Client {client_id} unsubscribed from task {task_id}")
                
                emit('task_unsubscribed', {
                    'taskId': task_id,
                    'room': room
                })
                
            except Exception as e:
                logger.error(f"Error handling task unsubscription: {e}")
                emit('error', {'message': 'Task unsubscription failed'})
                self.stats['errors'] += 1
        
        @self.socketio.on('get_presence')
        def handle_get_presence(data):
            """Handle request for user presence information"""
            client_id = request.sid
            
            if client_id not in self.connected_clients:
                emit('error', {'message': 'Client not registered'})
                return
            
            client_info = self.connected_clients[client_id]
            if not client_info.get('authenticated'):
                emit('error', {'message': 'Authentication required'})
                return
            
            try:
                project_id = data.get('project_id')
                permissions = client_info['permissions']
                
                # Check project access if specified
                if project_id and not permissions.has_project_access(project_id):
                    emit('error', {'message': 'Access denied to project'})
                    return
                
                # Get presence for users with access to the same projects
                presence_data = self._get_presence_data(permissions.project_ids, project_id)
                
                emit('presence_data', presence_data)
                
            except Exception as e:
                logger.error(f"Error handling presence request: {e}")
                emit('error', {'message': 'Failed to get presence data'})
                self.stats['errors'] += 1
        
        @self.socketio.on('get_stats')
        def handle_get_stats():
            """Handle stats request"""
            emit('stats', self.get_stats())
    
    def _setup_event_subscriptions(self):
        """Setup subscriptions to event bus"""
        
        if self.event_bus is None or EventType is None:
            logger.warning("Event bus or EventType not available, skipping event subscriptions")
            return
        
        # Subscribe to all event types for broadcasting
        try:
            for event_type in EventType:
                self.event_bus.subscribe(
                    event_type.value,
                    self._handle_event_from_bus
                )
            
            logger.info("WebSocket server subscribed to all event types")
        except Exception as e:
            logger.error(f"Failed to setup event subscriptions: {e}")
            logger.info("WebSocket server will operate without event subscriptions")
    
    def _handle_event_from_bus(self, event):
        """Handle event received from event bus"""
        try:
            self.stats['events_processed'] += 1
            
            # Prepare event data for WebSocket
            event_data = {
                'event_type': event.event_type,
                'event_id': event.event_id,
                'timestamp': event.timestamp,
                'source': event.source,
                'data': event.data,
                'metadata': event.metadata or {},
                'correlation_id': event.correlation_id,
                'user_id': event.user_id,
                'project_id': event.project_id
            }
            
            # Broadcast to relevant rooms
            self._broadcast_event(event_data)
            
        except Exception as e:
            logger.error(f"Error handling event from bus: {e}")
            self.stats['errors'] += 1
    
    def _broadcast_event(self, event_data: Dict[str, Any]):
        """Broadcast event to appropriate WebSocket rooms with permission filtering"""
        
        event_project_id = event_data.get('project_id')
        event_user_id = event_data.get('user_id')
        
        # Get list of clients that should receive this event
        authorized_clients = self._get_authorized_clients_for_event(event_data)
        
        if not authorized_clients:
            self.stats['events_filtered'] += 1
            return
        
        # Broadcast to authorized clients only
        for client_id in authorized_clients:
            try:
                self.socketio.emit('event', event_data, room=client_id)
                self.stats['messages_sent'] += 1
            except Exception as e:
                logger.error(f"Error broadcasting to client {client_id}: {e}")
                self.stats['errors'] += 1
        
        # Also broadcast to specific rooms if they exist and have authorized subscribers
        self._broadcast_to_authorized_rooms(event_data, authorized_clients)
    
    def _get_authorized_clients_for_event(self, event_data: Dict[str, Any]) -> Set[str]:
        """Get list of client IDs authorized to receive this event"""
        authorized_clients = set()
        event_project_id = event_data.get('project_id')
        event_user_id = event_data.get('user_id')
        
        for client_id, client_info in self.connected_clients.items():
            if not client_info.get('authenticated'):
                continue
            
            permissions = client_info.get('permissions')
            if not permissions:
                continue
            
            # Admin users get all events
            if permissions.is_admin:
                authorized_clients.add(client_id)
                continue
            
            # Check project-specific access
            if event_project_id:
                if permissions.has_project_access(event_project_id):
                    authorized_clients.add(client_id)
                    continue
            
            # Check user-specific access
            if event_user_id:
                if permissions.user_id == event_user_id:
                    authorized_clients.add(client_id)
                    continue
            
            # For events without specific project/user, check if user has any project access
            if not event_project_id and not event_user_id:
                if permissions.project_ids or permissions.is_admin:
                    authorized_clients.add(client_id)
        
        return authorized_clients
    
    def _broadcast_to_authorized_rooms(self, event_data: Dict[str, Any], authorized_clients: Set[str]):
        """Broadcast to specific rooms with authorization check"""
        event_type = event_data['event_type']
        event_project_id = event_data.get('project_id')
        event_user_id = event_data.get('user_id')
        
        # Broadcast to event type subscribers
        event_room = f"event:{event_type}"
        if event_room in self.room_subscriptions:
            room_clients = self.room_subscriptions[event_room]
            authorized_room_clients = room_clients.intersection(authorized_clients)
            if authorized_room_clients:
                for client_id in authorized_room_clients:
                    self.socketio.emit('event', event_data, room=client_id)
        
        # Broadcast to project-specific subscribers
        if event_project_id:
            project_room = f"project:{event_project_id}"
            if project_room in self.room_subscriptions:
                room_clients = self.room_subscriptions[project_room]
                authorized_room_clients = room_clients.intersection(authorized_clients)
                if authorized_room_clients:
                    for client_id in authorized_room_clients:
                        self.socketio.emit('event', event_data, room=client_id)
        
        # Broadcast to user-specific subscribers
        if event_user_id:
            user_room = f"user:{event_user_id}"
            if user_room in self.room_subscriptions:
                room_clients = self.room_subscriptions[user_room]
                authorized_room_clients = room_clients.intersection(authorized_clients)
                if authorized_room_clients:
                    for client_id in authorized_room_clients:
                        self.socketio.emit('event', event_data, room=client_id)
    
    def _setup_heartbeat(self):
        """Setup heartbeat monitoring for connection health"""
        def heartbeat_monitor():
            # Push application context for the entire thread
            ctx = self.app.app_context()
            ctx.push()
            
            try:
                while True:
                    try:
                        current_time = datetime.utcnow()
                        timeout_threshold = current_time - timedelta(seconds=self.connection_timeout)
                        
                        # Check for timed out connections
                        timed_out_clients = []
                        for client_id, client_info in self.connected_clients.items():
                            last_heartbeat = client_info.get('last_heartbeat')
                            if last_heartbeat and last_heartbeat < timeout_threshold:
                                timed_out_clients.append(client_id)
                        
                        # Disconnect timed out clients
                        for client_id in timed_out_clients:
                            logger.warning(f"Disconnecting timed out client: {client_id}")
                            try:
                                self.disconnect_client(client_id, "Connection timeout")
                            except Exception as disconnect_error:
                                logger.error(f"Error disconnecting client {client_id}: {disconnect_error}")
                        
                        # Sleep until next check
                        eventlet.sleep(self.heartbeat_interval)
                        
                    except Exception as e:
                        logger.error(f"Error in heartbeat monitor: {e}")
                        eventlet.sleep(self.heartbeat_interval)
            finally:
                # Clean up context when thread exits
                ctx.pop()
        
        # Start heartbeat monitor in background
        eventlet.spawn(heartbeat_monitor)
    
    def _broadcast_presence_update(self, user_id: str, status: str):
        """Broadcast user presence update to relevant clients"""
        presence_data = {
            'type': 'presence_update',
            'user_id': user_id,
            'status': status,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Find clients that should receive this presence update
        # (users who share projects with this user)
        target_clients = set()
        
        for client_id, client_info in self.connected_clients.items():
            if not client_info.get('authenticated'):
                continue
            
            permissions = client_info.get('permissions')
            if not permissions:
                continue
            
            # Admin users get all presence updates
            if permissions.is_admin:
                target_clients.add(client_id)
                continue
            
            # Users who share projects get presence updates
            if user_id in self.user_presence:
                user_projects = set()
                for user_client_id in self.user_presence[user_id]:
                    if user_client_id in self.connected_clients:
                        user_client_info = self.connected_clients[user_client_id]
                        user_client_permissions = user_client_info.get('permissions')
                        if user_client_permissions:
                            user_projects.update(user_client_permissions.project_ids)
                
                # Check if current client shares any projects
                if permissions.project_ids.intersection(user_projects):
                    target_clients.add(client_id)
        
        # Broadcast to target clients
        for client_id in target_clients:
            try:
                self.socketio.emit('presence_update', presence_data, room=client_id)
            except Exception as e:
                logger.error(f"Error broadcasting presence update to {client_id}: {e}")
    
    def _get_presence_data(self, user_project_ids: Set[str], specific_project_id: str = None) -> Dict[str, Any]:
        """Get presence data for users with shared project access"""
        presence_data = {
            'online_users': [],
            'project_id': specific_project_id,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Collect users who share project access
        for user_id, client_ids in self.user_presence.items():
            if not client_ids:  # No active connections
                continue
            
            # Get user's project access from any of their connections
            user_projects = set()
            user_info = None
            
            for client_id in client_ids:
                if client_id in self.connected_clients:
                    client_info = self.connected_clients[client_id]
                    permissions = client_info.get('permissions')
                    if permissions:
                        user_projects.update(permissions.project_ids)
                        if not user_info:
                            user_info = {
                                'user_id': user_id,
                                'username': permissions.username,
                                'connection_count': len(client_ids)
                            }
            
            # Check if user shares projects
            if specific_project_id:
                if specific_project_id in user_projects:
                    presence_data['online_users'].append(user_info)
            else:
                if user_project_ids.intersection(user_projects):
                    presence_data['online_users'].append(user_info)
        
        return presence_data
    
    def broadcast_system_message(self, message: str, level: str = 'info', project_id: str = None):
        """Broadcast a system message to authorized clients"""
        system_data = {
            'type': 'system',
            'level': level,
            'message': message,
            'project_id': project_id,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Get authorized clients
        if project_id:
            # Broadcast to users with access to specific project
            authorized_clients = set()
            for client_id, client_info in self.connected_clients.items():
                if not client_info.get('authenticated'):
                    continue
                permissions = client_info.get('permissions')
                if permissions and permissions.has_project_access(project_id):
                    authorized_clients.add(client_id)
            
            for client_id in authorized_clients:
                self.socketio.emit('system_message', system_data, room=client_id)
                self.stats['messages_sent'] += 1
        else:
            # Broadcast to all authenticated clients
            for client_id, client_info in self.connected_clients.items():
                if client_info.get('authenticated'):
                    self.socketio.emit('system_message', system_data, room=client_id)
                    self.stats['messages_sent'] += 1
        
        logger.info(f"System message broadcasted: {message} (project: {project_id})")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get WebSocket server statistics"""
        authenticated_count = sum(1 for info in self.connected_clients.values() if info.get('authenticated'))
        
        return {
            'connected_clients': len(self.connected_clients),
            'authenticated_clients': authenticated_count,
            'online_users': len(self.user_presence),
            'active_rooms': len(self.room_subscriptions),
            'stats': self.stats.copy(),
            'room_details': {
                room: len(clients) for room, clients in self.room_subscriptions.items()
            },
            'auth_cache_stats': self.auth_service.get_cache_stats(),
            'heartbeat_interval': self.heartbeat_interval,
            'connection_timeout': self.connection_timeout
        }
    
    def get_connected_clients(self) -> Dict[str, Dict[str, Any]]:
        """Get information about connected clients"""
        return {
            client_id: {
                'connected_at': info['connected_at'].isoformat() if info['connected_at'] else None,
                'last_heartbeat': info['last_heartbeat'].isoformat() if info.get('last_heartbeat') else None,
                'user_id': info.get('user_id'),
                'authenticated': info.get('authenticated', False),
                'project_count': len(info.get('project_ids', set())),
                'subscriptions': list(info.get('subscriptions', set())),
                'ip_address': info.get('ip_address')
            }
            for client_id, info in self.connected_clients.items()
        }
    
    def get_user_presence(self) -> Dict[str, Any]:
        """Get user presence information"""
        presence_info = {}
        
        for user_id, client_ids in self.user_presence.items():
            if not client_ids:
                continue
            
            # Get user info from any connection
            user_info = None
            for client_id in client_ids:
                if client_id in self.connected_clients:
                    client_info = self.connected_clients[client_id]
                    permissions = client_info.get('permissions')
                    if permissions:
                        user_info = {
                            'user_id': user_id,
                            'username': permissions.username,
                            'connection_count': len(client_ids),
                            'project_count': len(permissions.project_ids),
                            'is_admin': permissions.is_admin,
                            'status': 'online'
                        }
                        break
            
            if user_info:
                presence_info[user_id] = user_info
        
        return presence_info
    
    def disconnect_client(self, client_id: str, reason: str = "Server initiated"):
        """Disconnect a specific client"""
        if client_id in self.connected_clients:
            try:
                # Inform client first
                self.socketio.emit('disconnect_notice', {
                    'reason': reason,
                    'timestamp': datetime.utcnow().isoformat()
                }, room=client_id)

                # Use server-side disconnect via SocketIO's server context to avoid
                # relying on Flask request context in background threads.
                # This matches the engineio server API for disconnecting a session.
                self.socketio.server.disconnect(sid=client_id, namespace='/')
                logger.info(f"Disconnected client {client_id}: {reason}")
            except Exception as e:
                logger.error(f"Failed to disconnect client {client_id}: {e}")
    
    def disconnect_user(self, user_id: str, reason: str = "Server initiated"):
        """Disconnect all connections for a specific user"""
        if user_id in self.user_presence:
            client_ids = list(self.user_presence[user_id])
            for client_id in client_ids:
                self.disconnect_client(client_id, reason)
            logger.info(f"Disconnected all connections for user {user_id}: {reason}")
    
    def broadcast_to_project(self, project_id: str, event_type: str, data: Dict[str, Any]):
        """Broadcast a custom event to all users with access to a project"""
        event_data = {
            'event_type': event_type,
            'project_id': project_id,
            'data': data,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        authorized_clients = set()
        for client_id, client_info in self.connected_clients.items():
            if not client_info.get('authenticated'):
                continue
            
            permissions = client_info.get('permissions')
            if permissions and permissions.has_project_access(project_id):
                authorized_clients.add(client_id)
        
        for client_id in authorized_clients:
            try:
                self.socketio.emit('custom_event', event_data, room=client_id)
                self.stats['messages_sent'] += 1
            except Exception as e:
                logger.error(f"Error broadcasting to project {project_id}, client {client_id}: {e}")
                self.stats['errors'] += 1
        
        logger.info(f"Broadcasted {event_type} to {len(authorized_clients)} clients in project {project_id}")
    
    def broadcast_to_user(self, user_id: str, event_type: str, data: Dict[str, Any]):
        """Broadcast a custom event to all connections of a specific user"""
        if user_id not in self.user_presence:
            logger.warning(f"User {user_id} not online for broadcast")
            return
        
        event_data = {
            'event_type': event_type,
            'user_id': user_id,
            'data': data,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        client_ids = self.user_presence[user_id]
        for client_id in client_ids:
            try:
                self.socketio.emit('custom_event', event_data, room=client_id)
                self.stats['messages_sent'] += 1
            except Exception as e:
                logger.error(f"Error broadcasting to user {user_id}, client {client_id}: {e}")
                self.stats['errors'] += 1
        
        logger.info(f"Broadcasted {event_type} to {len(client_ids)} connections for user {user_id}")
    
    def broadcast_task_progress(self, task_id: str, progress_data: Dict[str, Any]):
        """Broadcast task progress update to subscribed clients"""
        try:
            room = f'task_{task_id}'
            
            # Check if anyone is subscribed to this task
            if room not in self.room_subscriptions or not self.room_subscriptions[room]:
                logger.debug(f"No subscribers for task {task_id}")
                return
            
            # Broadcast to the task room
            self.socketio.emit('task_progress', {
                'taskId': task_id,
                'timestamp': datetime.utcnow().isoformat(),
                **progress_data
            }, room=room)
            
            self.stats['messages_sent'] += 1
            logger.debug(f"Broadcasted task progress for {task_id} to {len(self.room_subscriptions[room])} clients")
            
        except Exception as e:
            logger.error(f"Error broadcasting task progress for {task_id}: {e}")
            self.stats['errors'] += 1
    
    def broadcast_phase_transition(self, project_id: str, transition_data: Dict[str, Any]):
        """Broadcast phase transition event to project subscribers"""
        try:
            # Broadcast to project room
            project_room = f'project:{project_id}'
            
            # Also broadcast to all authenticated clients in the project
            authorized_clients = []
            for client_id, client_info in self.connected_clients.items():
                if not client_info.get('authenticated'):
                    continue
                
                permissions = client_info.get('permissions')
                if permissions and (permissions.is_admin or permissions.has_project_access(project_id)):
                    authorized_clients.append(client_id)
            
            # If no authorized clients (common in local dev without auth), fall back to all connected clients
            target_clients = authorized_clients if authorized_clients else list(self.connected_clients.keys())

            if not authorized_clients:
                logger.info(
                    f"No authorized clients for phase transition in project {project_id}; broadcasting to all {len(target_clients)} connected clients (dev fallback)."
                )

            # Broadcast to target clients
            for client_id in target_clients:
                payload = {
                    'timestamp': datetime.utcnow().isoformat(),
                    **transition_data
                }
                # Legacy underscore event name (backend consumers)
                self.socketio.emit('phase_transition', payload, room=client_id)
                # New dot-style event name used by Mission Control frontend
                self.socketio.emit('phase.transition', payload, room=client_id)
            
            self.stats['messages_sent'] += len(target_clients)
            logger.info(f"Broadcasted phase transition to {len(authorized_clients)} clients in project {project_id}")
            
        except Exception as e:
            logger.error(f"Error broadcasting phase transition for project {project_id}: {e}")
            self.stats['errors'] += 1

    def broadcast_validation_run(self, project_id: str, run_data: Dict[str, Any]):
        """Broadcast a validation run update to authorized clients for a project.
        Emits on topic 'validation.runs' which the Mission Control Validate UI listens to.
        """
        try:
            # Determine which connected clients may receive this project's updates
            authorized_clients = []
            for client_id, client_info in self.connected_clients.items():
                if not client_info.get('authenticated'):
                    continue
                permissions = client_info.get('permissions')
                if permissions and (permissions.is_admin or permissions.has_project_access(project_id)):
                    authorized_clients.append(client_id)

            target_clients = authorized_clients if authorized_clients else list(self.connected_clients.keys())
            if not authorized_clients:
                logger.info(
                    f"No authorized clients for validation.runs in project {project_id}; broadcasting to all {len(target_clients)} connected clients (dev fallback)."
                )

            for client_id in target_clients:
                self.socketio.emit('validation.runs', run_data, room=client_id)

            self.stats['messages_sent'] += len(target_clients)
            logger.info(f"Broadcasted validation.runs to {len(authorized_clients)} clients in project {project_id}")
        except Exception as e:
            logger.error(f"Error broadcasting validation run for project {project_id}: {e}")
            self.stats['errors'] += 1

    def broadcast_validation_checks(self, project_id: str, checks_data: Any):
        """Broadcast one or more validation check updates for a project on 'validation.checks'."""
        try:
            authorized_clients = []
            for client_id, client_info in self.connected_clients.items():
                if not client_info.get('authenticated'):
                    continue
                permissions = client_info.get('permissions')
                if permissions and (permissions.is_admin or permissions.has_project_access(project_id)):
                    authorized_clients.append(client_id)

            target_clients = authorized_clients if authorized_clients else list(self.connected_clients.keys())
            if not authorized_clients:
                logger.info(
                    f"No authorized clients for validation.checks in project {project_id}; broadcasting to all {len(target_clients)} connected clients (dev fallback)."
                )

            for client_id in target_clients:
                self.socketio.emit('validation.checks', checks_data, room=client_id)

            self.stats['messages_sent'] += len(target_clients)
            logger.info(f"Broadcasted validation.checks to {len(authorized_clients)} clients in project {project_id}")
        except Exception as e:
            logger.error(f"Error broadcasting validation checks for project {project_id}: {e}")
            self.stats['errors'] += 1
    
    def health_check(self) -> bool:
        """Check if WebSocket server is healthy"""
        try:
            # Check if event bus is healthy (if available)
            if self.event_bus and hasattr(self.event_bus, 'health_check'):
                if not self.event_bus.health_check():
                    return False
            
            # Check if auth service is available
            if self.auth_service is None:
                logger.warning("Auth service not available")
                return False
            
            # WebSocket server is healthy if it can accept connections
            return True
            
        except Exception as e:
            logger.error(f"WebSocket health check failed: {e}")
            return False


# Global WebSocket server instance
_websocket_server = None


def init_websocket_server(app: Flask) -> WebSocketServer:
    """Initialize the WebSocket server"""
    global _websocket_server
    _websocket_server = WebSocketServer(app)
    return _websocket_server


def get_websocket_server() -> Optional[WebSocketServer]:
    """Get the global WebSocket server instance"""
    return _websocket_server