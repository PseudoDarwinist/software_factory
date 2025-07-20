"""
Event store implementation for audit trail and event replay capabilities.
"""

import json
import sqlite3
from typing import List, Optional, Dict, Any, Iterator
from datetime import datetime, timedelta
from contextlib import contextmanager

from .base import BaseEvent, EventFilter
from .domain_events import *


class EventStore:
    """Event store for persisting and querying domain events."""
    
    def __init__(self, db_path: str = "instance/event_store.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize the event store database schema."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    event_type TEXT NOT NULL,
                    aggregate_id TEXT,
                    aggregate_type TEXT,
                    correlation_id TEXT NOT NULL,
                    actor TEXT,
                    trace_id TEXT,
                    timestamp DATETIME NOT NULL,
                    event_version TEXT NOT NULL,
                    source_service TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for efficient querying
            conn.execute("CREATE INDEX IF NOT EXISTS idx_event_type ON events(event_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_aggregate ON events(aggregate_id, aggregate_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_correlation ON events(correlation_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON events(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_actor ON events(actor)")
            
            # Create snapshots table for event replay optimization
            conn.execute("""
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    aggregate_id TEXT NOT NULL,
                    aggregate_type TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    snapshot_data TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(aggregate_id, aggregate_type, version)
                )
            """)
            
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """Get database connection with proper cleanup."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def append_event(self, event: BaseEvent) -> None:
        """Append an event to the store."""
        with self._get_connection() as conn:
            # Extract aggregate info for domain events
            aggregate_id = None
            aggregate_type = None
            if hasattr(event, 'aggregate_id'):
                aggregate_id = event.aggregate_id
                aggregate_type = event.aggregate_type
            
            conn.execute("""
                INSERT INTO events (
                    event_id, event_type, aggregate_id, aggregate_type,
                    correlation_id, actor, trace_id, timestamp,
                    event_version, source_service, payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.metadata.event_id,
                event.get_event_type(),
                aggregate_id,
                aggregate_type,
                event.metadata.correlation_id,
                event.metadata.actor,
                event.metadata.trace_id,
                event.metadata.timestamp,
                event.metadata.event_version,
                event.metadata.source_service,
                json.dumps(event.get_payload())
            ))
            conn.commit()
    
    def append_events(self, events: List[BaseEvent]) -> None:
        """Append multiple events atomically."""
        with self._get_connection() as conn:
            for event in events:
                aggregate_id = None
                aggregate_type = None
                if hasattr(event, 'aggregate_id'):
                    aggregate_id = event.aggregate_id
                    aggregate_type = event.aggregate_type
                
                conn.execute("""
                    INSERT INTO events (
                        event_id, event_type, aggregate_id, aggregate_type,
                        correlation_id, actor, trace_id, timestamp,
                        event_version, source_service, payload
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.metadata.event_id,
                    event.get_event_type(),
                    aggregate_id,
                    aggregate_type,
                    event.metadata.correlation_id,
                    event.metadata.actor,
                    event.metadata.trace_id,
                    event.metadata.timestamp,
                    event.metadata.event_version,
                    event.metadata.source_service,
                    json.dumps(event.get_payload())
                ))
            conn.commit()
    
    def get_events(
        self,
        event_filter: Optional[EventFilter] = None,
        from_timestamp: Optional[datetime] = None,
        to_timestamp: Optional[datetime] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get events matching the specified criteria."""
        query = "SELECT * FROM events WHERE 1=1"
        params = []
        
        # Apply timestamp filters
        if from_timestamp:
            query += " AND timestamp >= ?"
            params.append(from_timestamp)
        
        if to_timestamp:
            query += " AND timestamp <= ?"
            params.append(to_timestamp)
        
        # Apply event filter
        if event_filter:
            if event_filter.event_types:
                placeholders = ','.join('?' * len(event_filter.event_types))
                query += f" AND event_type IN ({placeholders})"
                params.extend(event_filter.event_types)
            
            if event_filter.aggregate_types:
                placeholders = ','.join('?' * len(event_filter.aggregate_types))
                query += f" AND aggregate_type IN ({placeholders})"
                params.extend(event_filter.aggregate_types)
            
            if event_filter.actors:
                placeholders = ','.join('?' * len(event_filter.actors))
                query += f" AND actor IN ({placeholders})"
                params.extend(event_filter.actors)
            
            if event_filter.correlation_ids:
                placeholders = ','.join('?' * len(event_filter.correlation_ids))
                query += f" AND correlation_id IN ({placeholders})"
                params.extend(event_filter.correlation_ids)
        
        # Add ordering and pagination
        query += " ORDER BY timestamp ASC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        if offset > 0:
            query += " OFFSET ?"
            params.append(offset)
        
        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_events_by_aggregate(
        self,
        aggregate_id: str,
        aggregate_type: str,
        from_version: int = 0
    ) -> List[Dict[str, Any]]:
        """Get all events for a specific aggregate."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM events 
                WHERE aggregate_id = ? AND aggregate_type = ?
                ORDER BY timestamp ASC
            """, (aggregate_id, aggregate_type))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_events_by_correlation(self, correlation_id: str) -> List[Dict[str, Any]]:
        """Get all events with the same correlation ID."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM events 
                WHERE correlation_id = ?
                ORDER BY timestamp ASC
            """, (correlation_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_event_stream(
        self,
        event_filter: Optional[EventFilter] = None,
        from_timestamp: Optional[datetime] = None,
        batch_size: int = 100
    ) -> Iterator[List[Dict[str, Any]]]:
        """Stream events in batches for processing large datasets."""
        offset = 0
        
        while True:
            events = self.get_events(
                event_filter=event_filter,
                from_timestamp=from_timestamp,
                limit=batch_size,
                offset=offset
            )
            
            if not events:
                break
            
            yield events
            offset += batch_size
    
    def replay_events(
        self,
        aggregate_id: str,
        aggregate_type: str,
        to_timestamp: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Replay events for an aggregate up to a specific point in time."""
        query = """
            SELECT * FROM events 
            WHERE aggregate_id = ? AND aggregate_type = ?
        """
        params = [aggregate_id, aggregate_type]
        
        if to_timestamp:
            query += " AND timestamp <= ?"
            params.append(to_timestamp)
        
        query += " ORDER BY timestamp ASC"
        
        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def save_snapshot(
        self,
        aggregate_id: str,
        aggregate_type: str,
        version: int,
        snapshot_data: Dict[str, Any]
    ) -> None:
        """Save a snapshot for event replay optimization."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO snapshots (
                    aggregate_id, aggregate_type, version, snapshot_data
                ) VALUES (?, ?, ?, ?)
            """, (
                aggregate_id,
                aggregate_type,
                version,
                json.dumps(snapshot_data)
            ))
            conn.commit()
    
    def get_latest_snapshot(
        self,
        aggregate_id: str,
        aggregate_type: str
    ) -> Optional[Dict[str, Any]]:
        """Get the latest snapshot for an aggregate."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM snapshots 
                WHERE aggregate_id = ? AND aggregate_type = ?
                ORDER BY version DESC
                LIMIT 1
            """, (aggregate_id, aggregate_type))
            
            row = cursor.fetchone()
            if row:
                return {
                    'aggregate_id': row['aggregate_id'],
                    'aggregate_type': row['aggregate_type'],
                    'version': row['version'],
                    'snapshot_data': json.loads(row['snapshot_data']),
                    'created_at': row['created_at']
                }
            return None
    
    def get_event_statistics(
        self,
        from_timestamp: Optional[datetime] = None,
        to_timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get statistics about events in the store."""
        query = "SELECT event_type, COUNT(*) as count FROM events WHERE 1=1"
        params = []
        
        if from_timestamp:
            query += " AND timestamp >= ?"
            params.append(from_timestamp)
        
        if to_timestamp:
            query += " AND timestamp <= ?"
            params.append(to_timestamp)
        
        query += " GROUP BY event_type ORDER BY count DESC"
        
        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            event_counts = dict(cursor.fetchall())
            
            # Get total count
            total_query = "SELECT COUNT(*) as total FROM events WHERE 1=1"
            if from_timestamp:
                total_query += " AND timestamp >= ?"
            if to_timestamp:
                total_query += " AND timestamp <= ?"
            
            cursor = conn.execute(total_query, params)
            total_count = cursor.fetchone()['total']
            
            return {
                'total_events': total_count,
                'event_type_counts': event_counts,
                'unique_event_types': len(event_counts)
            }
    
    def cleanup_old_events(self, older_than_days: int = 90) -> int:
        """Clean up events older than specified days."""
        cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
        
        with self._get_connection() as conn:
            cursor = conn.execute("""
                DELETE FROM events WHERE timestamp < ?
            """, (cutoff_date,))
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            return deleted_count