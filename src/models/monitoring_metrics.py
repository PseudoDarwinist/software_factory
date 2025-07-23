"""
Monitoring metrics database models for time-series data storage and historical analysis.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from .base import db


class MonitoringMetrics(db.Model):
    """Time-series metrics storage for monitoring dashboard."""
    
    __tablename__ = 'monitoring_metrics'
    
    # Primary key
    id = db.Column(db.Integer, primary_key=True)
    
    # Metric identification
    metric_type = db.Column(db.String(100), nullable=False, index=True)  # event, agent, system, integration
    metric_name = db.Column(db.String(100), nullable=False, index=True)  # events_per_minute, cpu_usage, etc.
    source_id = db.Column(db.String(100), index=True)  # agent_id, component_name, etc.
    
    # Time-series data
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    value = db.Column(db.Float, nullable=False)
    
    # Additional metadata
    meta_data = db.Column(db.Text)  # JSON metadata
    
    # Audit fields
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Indexes for efficient querying
    __table_args__ = (
        db.Index('idx_metrics_type_name_time', 'metric_type', 'metric_name', 'timestamp'),
        db.Index('idx_metrics_source_time', 'source_id', 'timestamp'),
    )
    
    def __init__(self, **kwargs):
        # Ensure meta_data is JSON string
        if 'meta_data' in kwargs and isinstance(kwargs['meta_data'], dict):
            kwargs['meta_data'] = json.dumps(kwargs['meta_data'])
        
        super().__init__(**kwargs)
    
    @property
    def metadata_dict(self) -> Dict[str, Any]:
        """Get metadata as dictionary."""
        try:
            return json.loads(self.meta_data) if self.meta_data else {}
        except json.JSONDecodeError:
            return {}
    
    @metadata_dict.setter
    def metadata_dict(self, value: Dict[str, Any]) -> None:
        """Set metadata from dictionary."""
        self.meta_data = json.dumps(value) if value else None
    
    @classmethod
    def record_metric(
        cls,
        metric_type: str,
        metric_name: str,
        value: float,
        source_id: Optional[str] = None,
        meta_data: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
    ):
        """Record a metric value."""
        metric = cls(
            metric_type=metric_type,
            metric_name=metric_name,
            value=value,
            source_id=source_id,
            meta_data=json.dumps(meta_data) if meta_data else None,
            timestamp=timestamp or datetime.utcnow()
        )
        
        db.session.add(metric)
        return metric
    
    @classmethod
    def get_metrics(
        cls,
        metric_type: Optional[str] = None,
        metric_name: Optional[str] = None,
        source_id: Optional[str] = None,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List['MonitoringMetrics']:
        """Get metrics matching the specified criteria."""
        query = cls.query
        
        if metric_type:
            query = query.filter(cls.metric_type == metric_type)
        
        if metric_name:
            query = query.filter(cls.metric_name == metric_name)
        
        if source_id:
            query = query.filter(cls.source_id == source_id)
        
        if from_time:
            query = query.filter(cls.timestamp >= from_time)
        
        if to_time:
            query = query.filter(cls.timestamp <= to_time)
        
        return query.order_by(cls.timestamp.desc()).limit(limit).all()
    
    @classmethod
    def get_latest_metric(
        cls,
        metric_type: str,
        metric_name: str,
        source_id: Optional[str] = None
    ) -> Optional['MonitoringMetrics']:
        """Get the latest metric value."""
        query = cls.query.filter(
            cls.metric_type == metric_type,
            cls.metric_name == metric_name
        )
        
        if source_id:
            query = query.filter(cls.source_id == source_id)
        
        return query.order_by(cls.timestamp.desc()).first()
    
    @classmethod
    def get_metric_summary(
        cls,
        metric_type: str,
        metric_name: str,
        source_id: Optional[str] = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get metric summary for the specified time period."""
        from_time = datetime.utcnow() - timedelta(hours=hours)
        
        query = cls.query.filter(
            cls.metric_type == metric_type,
            cls.metric_name == metric_name,
            cls.timestamp >= from_time
        )
        
        if source_id:
            query = query.filter(cls.source_id == source_id)
        
        metrics = query.all()
        
        if not metrics:
            return {
                'count': 0,
                'min': None,
                'max': None,
                'avg': None,
                'latest': None
            }
        
        values = [m.value for m in metrics]
        
        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / len(values),
            'latest': metrics[0].value if metrics else None,
            'latest_timestamp': metrics[0].timestamp.isoformat() if metrics else None
        }
    
    @classmethod
    def cleanup_old_metrics(cls, days_old: int = 30) -> int:
        """Clean up metrics older than specified days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        # Count metrics to be deleted
        count = cls.query.filter(cls.timestamp < cutoff_date).count()
        
        # Delete old metrics
        cls.query.filter(cls.timestamp < cutoff_date).delete()
        db.session.commit()
        
        return count
    
    @classmethod
    def downsample_metrics(cls, hours_old: int = 168) -> int:  # 7 days
        """Downsample high-resolution metrics to hourly averages."""
        cutoff_date = datetime.utcnow() - timedelta(hours=hours_old)
        
        # This would implement downsampling logic
        # For now, just return 0 as placeholder
        return 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metric to dictionary."""
        return {
            'id': self.id,
            'metric_type': self.metric_type,
            'metric_name': self.metric_name,
            'source_id': self.source_id,
            'timestamp': self.timestamp.isoformat(),
            'value': self.value,
            'metadata': self.metadata_dict,
            'created_at': self.created_at.isoformat()
        }
    
    def __repr__(self):
        return f'<MonitoringMetrics {self.metric_type}.{self.metric_name}={self.value}>'


class AgentStatus(db.Model):
    """Agent status tracking for monitoring dashboard."""
    
    __tablename__ = 'agent_status'
    
    # Primary key
    id = db.Column(db.Integer, primary_key=True)
    
    # Agent identification
    agent_id = db.Column(db.String(100), nullable=False, index=True)
    
    # Status information
    status = db.Column(db.String(50), nullable=False)  # running, stopped, error, paused
    heartbeat_status = db.Column(db.String(20), nullable=False, default='unknown')  # green, yellow, red
    
    # Performance metrics
    events_processed = db.Column(db.Integer, default=0)
    success_rate = db.Column(db.Float, default=0.0)
    average_processing_time = db.Column(db.Float, default=0.0)
    current_load = db.Column(db.Integer, default=0)
    
    # Timestamps
    last_activity = db.Column(db.DateTime)
    last_heartbeat = db.Column(db.DateTime)
    
    # Additional metadata
    meta_data = db.Column(db.Text)  # JSON metadata
    
    # Audit fields
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __init__(self, **kwargs):
        # Ensure meta_data is JSON string
        if 'meta_data' in kwargs and isinstance(kwargs['meta_data'], dict):
            kwargs['meta_data'] = json.dumps(kwargs['meta_data'])
        
        super().__init__(**kwargs)
    
    @property
    def metadata_dict(self) -> Dict[str, Any]:
        """Get metadata as dictionary."""
        try:
            return json.loads(self.meta_data) if self.meta_data else {}
        except json.JSONDecodeError:
            return {}
    
    @metadata_dict.setter
    def metadata_dict(self, value: Dict[str, Any]) -> None:
        """Set metadata from dictionary."""
        self.meta_data = json.dumps(value) if value else None
    
    @classmethod
    def update_agent_status(
        cls,
        agent_id: str,
        status: Optional[str] = None,
        heartbeat_status: Optional[str] = None,
        events_processed: Optional[int] = None,
        success_rate: Optional[float] = None,
        average_processing_time: Optional[float] = None,
        current_load: Optional[int] = None,
        last_activity: Optional[datetime] = None,
        last_heartbeat: Optional[datetime] = None,
        meta_data: Optional[Dict[str, Any]] = None
    ):
        """Update or create agent status."""
        agent_status = cls.query.filter_by(agent_id=agent_id).first()
        
        if not agent_status:
            agent_status = cls(agent_id=agent_id)
            db.session.add(agent_status)
        
        # Update fields if provided
        if status is not None:
            agent_status.status = status
        if heartbeat_status is not None:
            agent_status.heartbeat_status = heartbeat_status
        if events_processed is not None:
            agent_status.events_processed = events_processed
        if success_rate is not None:
            agent_status.success_rate = success_rate
        if average_processing_time is not None:
            agent_status.average_processing_time = average_processing_time
        if current_load is not None:
            agent_status.current_load = current_load
        if last_activity is not None:
            agent_status.last_activity = last_activity
        if last_heartbeat is not None:
            agent_status.last_heartbeat = last_heartbeat
        if meta_data is not None:
            agent_status.metadata_dict = meta_data
        
        agent_status.updated_at = datetime.utcnow()
        
        return agent_status
    
    @classmethod
    def get_all_agents(cls) -> List['AgentStatus']:
        """Get all agent statuses."""
        return cls.query.order_by(cls.agent_id).all()
    
    @classmethod
    def get_active_agents(cls, minutes: int = 10) -> List['AgentStatus']:
        """Get agents that have been active within the specified minutes."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        return cls.query.filter(cls.last_activity >= cutoff_time).all()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert agent status to dictionary."""
        return {
            'id': self.id,
            'agent_id': self.agent_id,
            'status': self.status,
            'heartbeat_status': self.heartbeat_status,
            'events_processed': self.events_processed,
            'success_rate': self.success_rate,
            'average_processing_time': self.average_processing_time,
            'current_load': self.current_load,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'last_heartbeat': self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            'metadata': self.metadata_dict,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<AgentStatus {self.agent_id} {self.status}>'


class SystemHealth(db.Model):
    """System health tracking for monitoring dashboard."""
    
    __tablename__ = 'system_health'
    
    # Primary key
    id = db.Column(db.Integer, primary_key=True)
    
    # Health metrics
    overall_score = db.Column(db.Float, nullable=False, default=0.0)
    
    # Component health (JSON)
    components = db.Column(db.Text)  # JSON data for component health
    resources = db.Column(db.Text)   # JSON data for resource usage
    performance = db.Column(db.Text) # JSON data for performance metrics
    
    # Timestamps
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __init__(self, **kwargs):
        # Ensure JSON fields are strings
        for field in ['components', 'resources', 'performance']:
            if field in kwargs and isinstance(kwargs[field], dict):
                kwargs[field] = json.dumps(kwargs[field])
        
        super().__init__(**kwargs)
    
    @property
    def components_dict(self) -> Dict[str, Any]:
        """Get components as dictionary."""
        try:
            return json.loads(self.components) if self.components else {}
        except json.JSONDecodeError:
            return {}
    
    @components_dict.setter
    def components_dict(self, value: Dict[str, Any]) -> None:
        """Set components from dictionary."""
        self.components = json.dumps(value) if value else None
    
    @property
    def resources_dict(self) -> Dict[str, Any]:
        """Get resources as dictionary."""
        try:
            return json.loads(self.resources) if self.resources else {}
        except json.JSONDecodeError:
            return {}
    
    @resources_dict.setter
    def resources_dict(self, value: Dict[str, Any]) -> None:
        """Set resources from dictionary."""
        self.resources = json.dumps(value) if value else None
    
    @property
    def performance_dict(self) -> Dict[str, Any]:
        """Get performance as dictionary."""
        try:
            return json.loads(self.performance) if self.performance else {}
        except json.JSONDecodeError:
            return {}
    
    @performance_dict.setter
    def performance_dict(self, value: Dict[str, Any]) -> None:
        """Set performance from dictionary."""
        self.performance = json.dumps(value) if value else None
    
    @classmethod
    def record_health(
        cls,
        overall_score: float,
        components: Dict[str, Any],
        resources: Dict[str, Any],
        performance: Dict[str, Any],
        timestamp: Optional[datetime] = None
    ):
        """Record system health snapshot."""
        health = cls(
            overall_score=overall_score,
            components=json.dumps(components),
            resources=json.dumps(resources),
            performance=json.dumps(performance),
            timestamp=timestamp or datetime.utcnow()
        )
        
        db.session.add(health)
        return health
    
    @classmethod
    def get_latest_health(cls) -> Optional['SystemHealth']:
        """Get the latest system health record."""
        return cls.query.order_by(cls.timestamp.desc()).first()
    
    @classmethod
    def get_health_history(cls, hours: int = 24) -> List['SystemHealth']:
        """Get system health history for the specified hours."""
        from_time = datetime.utcnow() - timedelta(hours=hours)
        return cls.query.filter(cls.timestamp >= from_time).order_by(cls.timestamp.desc()).all()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert system health to dictionary."""
        return {
            'id': self.id,
            'overall_score': self.overall_score,
            'components': self.components_dict,
            'resources': self.resources_dict,
            'performance': self.performance_dict,
            'timestamp': self.timestamp.isoformat(),
            'created_at': self.created_at.isoformat()
        }
    
    def __repr__(self):
        return f'<SystemHealth score={self.overall_score}>'


class AlertHistory(db.Model):
    """Alert history tracking for monitoring dashboard."""
    
    __tablename__ = 'alert_history'
    
    # Primary key
    id = db.Column(db.Integer, primary_key=True)
    
    # Alert identification
    alert_id = db.Column(db.String(100), nullable=False, index=True)
    
    # Alert details
    alert_type = db.Column(db.String(20), nullable=False)  # critical, warning, info
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    source = db.Column(db.String(100), nullable=False)
    
    # Alert status
    acknowledged = db.Column(db.Boolean, default=False, nullable=False)
    acknowledged_by = db.Column(db.String(100))
    acknowledged_at = db.Column(db.DateTime)
    resolved = db.Column(db.Boolean, default=False, nullable=False)
    resolved_at = db.Column(db.DateTime)
    
    # Additional metadata
    meta_data = db.Column(db.Text)  # JSON metadata
    
    # Timestamps
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Indexes for efficient querying
    __table_args__ = (
        db.Index('idx_alert_type_time', 'alert_type', 'timestamp'),
        db.Index('idx_alert_source_time', 'source', 'timestamp'),
        db.Index('idx_alert_status', 'acknowledged', 'resolved'),
    )
    
    def __init__(self, **kwargs):
        # Ensure meta_data is JSON string
        if 'meta_data' in kwargs and isinstance(kwargs['meta_data'], dict):
            kwargs['meta_data'] = json.dumps(kwargs['meta_data'])
        
        super().__init__(**kwargs)
    
    @property
    def metadata_dict(self) -> Dict[str, Any]:
        """Get metadata as dictionary."""
        try:
            return json.loads(self.meta_data) if self.meta_data else {}
        except json.JSONDecodeError:
            return {}
    
    @metadata_dict.setter
    def metadata_dict(self, value: Dict[str, Any]) -> None:
        """Set metadata from dictionary."""
        self.meta_data = json.dumps(value) if value else None
    
    @classmethod
    def create_alert(
        cls,
        alert_id: str,
        alert_type: str,
        title: str,
        description: str,
        source: str,
        meta_data: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
    ):
        """Create a new alert."""
        alert = cls(
            alert_id=alert_id,
            alert_type=alert_type,
            title=title,
            description=description,
            source=source,
            meta_data=json.dumps(meta_data) if meta_data else None,
            timestamp=timestamp or datetime.utcnow()
        )
        
        db.session.add(alert)
        return alert
    
    @classmethod
    def acknowledge_alert(cls, alert_id: str, acknowledged_by: str) -> Optional['AlertHistory']:
        """Acknowledge an alert."""
        alert = cls.query.filter_by(alert_id=alert_id, acknowledged=False).first()
        if alert:
            alert.acknowledged = True
            alert.acknowledged_by = acknowledged_by
            alert.acknowledged_at = datetime.utcnow()
            alert.updated_at = datetime.utcnow()
        return alert
    
    @classmethod
    def resolve_alert(cls, alert_id: str) -> Optional['AlertHistory']:
        """Resolve an alert."""
        alert = cls.query.filter_by(alert_id=alert_id, resolved=False).first()
        if alert:
            alert.resolved = True
            alert.resolved_at = datetime.utcnow()
            alert.updated_at = datetime.utcnow()
        return alert
    
    @classmethod
    def get_active_alerts(cls) -> List['AlertHistory']:
        """Get all active (unresolved) alerts."""
        return cls.query.filter_by(resolved=False).order_by(cls.timestamp.desc()).all()
    
    @classmethod
    def get_alert_history(cls, hours: int = 24, alert_type: Optional[str] = None) -> List['AlertHistory']:
        """Get alert history for the specified time period."""
        from_time = datetime.utcnow() - timedelta(hours=hours)
        query = cls.query.filter(cls.timestamp >= from_time)
        
        if alert_type:
            query = query.filter(cls.alert_type == alert_type)
        
        return query.order_by(cls.timestamp.desc()).all()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            'id': self.id,
            'alert_id': self.alert_id,
            'alert_type': self.alert_type,
            'title': self.title,
            'description': self.description,
            'source': self.source,
            'acknowledged': self.acknowledged,
            'acknowledged_by': self.acknowledged_by,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            'resolved': self.resolved,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'metadata': self.metadata_dict,
            'timestamp': self.timestamp.isoformat(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<AlertHistory {self.alert_id} {self.alert_type}>'


class IntegrationStatus(db.Model):
    """Integration status tracking for external services."""
    
    __tablename__ = 'integration_status'
    
    # Primary key
    id = db.Column(db.Integer, primary_key=True)
    
    # Integration identification
    integration_name = db.Column(db.String(100), nullable=False, index=True)
    integration_type = db.Column(db.String(50), nullable=False)  # slack, github, ai_service, etc.
    
    # Status information
    status = db.Column(db.String(20), nullable=False)  # healthy, warning, error, unknown
    last_success = db.Column(db.DateTime)
    last_error = db.Column(db.DateTime)
    error_message = db.Column(db.Text)
    
    # Performance metrics
    success_rate = db.Column(db.Float, default=0.0)
    average_response_time = db.Column(db.Float, default=0.0)
    api_usage_count = db.Column(db.Integer, default=0)
    rate_limit_remaining = db.Column(db.Integer)
    rate_limit_reset = db.Column(db.DateTime)
    
    # Additional metadata
    meta_data = db.Column(db.Text)  # JSON metadata
    
    # Timestamps
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Indexes for efficient querying
    __table_args__ = (
        db.Index('idx_integration_type_time', 'integration_type', 'timestamp'),
        db.Index('idx_integration_status', 'status'),
    )
    
    def __init__(self, **kwargs):
        # Ensure meta_data is JSON string
        if 'meta_data' in kwargs and isinstance(kwargs['meta_data'], dict):
            kwargs['meta_data'] = json.dumps(kwargs['meta_data'])
        
        super().__init__(**kwargs)
    
    @property
    def metadata_dict(self) -> Dict[str, Any]:
        """Get metadata as dictionary."""
        try:
            return json.loads(self.meta_data) if self.meta_data else {}
        except json.JSONDecodeError:
            return {}
    
    @metadata_dict.setter
    def metadata_dict(self, value: Dict[str, Any]) -> None:
        """Set metadata from dictionary."""
        self.meta_data = json.dumps(value) if value else None
    
    @classmethod
    def update_integration_status(
        cls,
        integration_name: str,
        integration_type: str,
        status: str,
        last_success: Optional[datetime] = None,
        last_error: Optional[datetime] = None,
        error_message: Optional[str] = None,
        success_rate: Optional[float] = None,
        average_response_time: Optional[float] = None,
        api_usage_count: Optional[int] = None,
        rate_limit_remaining: Optional[int] = None,
        rate_limit_reset: Optional[datetime] = None,
        meta_data: Optional[Dict[str, Any]] = None
    ):
        """Update or create integration status."""
        integration = cls.query.filter_by(integration_name=integration_name).first()
        
        if not integration:
            integration = cls(
                integration_name=integration_name,
                integration_type=integration_type
            )
            db.session.add(integration)
        
        # Update fields
        integration.status = status
        integration.integration_type = integration_type
        
        if last_success is not None:
            integration.last_success = last_success
        if last_error is not None:
            integration.last_error = last_error
        if error_message is not None:
            integration.error_message = error_message
        if success_rate is not None:
            integration.success_rate = success_rate
        if average_response_time is not None:
            integration.average_response_time = average_response_time
        if api_usage_count is not None:
            integration.api_usage_count = api_usage_count
        if rate_limit_remaining is not None:
            integration.rate_limit_remaining = rate_limit_remaining
        if rate_limit_reset is not None:
            integration.rate_limit_reset = rate_limit_reset
        if meta_data is not None:
            integration.metadata_dict = meta_data
        
        integration.timestamp = datetime.utcnow()
        integration.updated_at = datetime.utcnow()
        
        return integration
    
    @classmethod
    def get_all_integrations(cls) -> List['IntegrationStatus']:
        """Get all integration statuses."""
        return cls.query.order_by(cls.integration_name).all()
    
    @classmethod
    def get_integration_by_name(cls, integration_name: str) -> Optional['IntegrationStatus']:
        """Get integration status by name."""
        return cls.query.filter_by(integration_name=integration_name).first()
    
    @classmethod
    def get_integrations_by_status(cls, status: str) -> List['IntegrationStatus']:
        """Get integrations by status."""
        return cls.query.filter_by(status=status).all()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert integration status to dictionary."""
        return {
            'id': self.id,
            'integration_name': self.integration_name,
            'integration_type': self.integration_type,
            'status': self.status,
            'last_success': self.last_success.isoformat() if self.last_success else None,
            'last_error': self.last_error.isoformat() if self.last_error else None,
            'error_message': self.error_message,
            'success_rate': self.success_rate,
            'average_response_time': self.average_response_time,
            'api_usage_count': self.api_usage_count,
            'rate_limit_remaining': self.rate_limit_remaining,
            'rate_limit_reset': self.rate_limit_reset.isoformat() if self.rate_limit_reset else None,
            'metadata': self.metadata_dict,
            'timestamp': self.timestamp.isoformat(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<IntegrationStatus {self.integration_name} {self.status}>'


class DashboardConfig(db.Model):
    """Dashboard configuration and user preferences."""
    
    __tablename__ = 'dashboard_config'
    
    # Primary key
    id = db.Column(db.Integer, primary_key=True)
    
    # Configuration identification
    config_key = db.Column(db.String(100), nullable=False, unique=True, index=True)
    config_type = db.Column(db.String(50), nullable=False)  # alert_threshold, user_preference, system_setting
    
    # Configuration data
    config_value = db.Column(db.Text)  # JSON configuration data
    
    # Metadata
    description = db.Column(db.String(500))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __init__(self, **kwargs):
        # Ensure config_value is JSON string
        if 'config_value' in kwargs and isinstance(kwargs['config_value'], dict):
            kwargs['config_value'] = json.dumps(kwargs['config_value'])
        
        super().__init__(**kwargs)
    
    @property
    def config_dict(self) -> Dict[str, Any]:
        """Get configuration as dictionary."""
        try:
            return json.loads(self.config_value) if self.config_value else {}
        except json.JSONDecodeError:
            return {}
    
    @config_dict.setter
    def config_dict(self, value: Dict[str, Any]) -> None:
        """Set configuration from dictionary."""
        self.config_value = json.dumps(value) if value else None
    
    @classmethod
    def set_config(
        cls,
        config_key: str,
        config_type: str,
        config_value: Dict[str, Any],
        description: Optional[str] = None
    ):
        """Set or update configuration."""
        config = cls.query.filter_by(config_key=config_key).first()
        
        if not config:
            config = cls(
                config_key=config_key,
                config_type=config_type
            )
            db.session.add(config)
        
        config.config_dict = config_value
        config.config_type = config_type
        if description is not None:
            config.description = description
        
        config.updated_at = datetime.utcnow()
        
        return config
    
    @classmethod
    def get_config(cls, config_key: str) -> Optional[Dict[str, Any]]:
        """Get configuration by key."""
        config = cls.query.filter_by(config_key=config_key).first()
        return config.config_dict if config else None
    
    @classmethod
    def get_configs_by_type(cls, config_type: str) -> List['DashboardConfig']:
        """Get all configurations by type."""
        return cls.query.filter_by(config_type=config_type).all()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'id': self.id,
            'config_key': self.config_key,
            'config_type': self.config_type,
            'config_value': self.config_dict,
            'description': self.description,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<DashboardConfig {self.config_key}>'