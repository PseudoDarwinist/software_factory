# Architecture Simplification Design Document

## Overview

This design consolidates the current multi-server architecture (Flask + Express + Worker processes) into a single, unified Flask application. The new architecture eliminates Socket.IO complexity, reduces inter-process communication overhead, and provides a single source of truth for all data and operations.

The design maintains all existing functionality while dramatically reducing system complexity, improving debuggability, and simplifying deployment.

## Architecture

### Current Architecture Problems
- **3 separate servers**: Flask (Python), Express (Node.js), Worker (Node.js)
- **Complex event chains**: Frontend → Flask → Mission Control → Worker → back through chain
- **Multiple data stores**: JSON files + in-memory state across processes
- **Socket.IO complexity**: Events getting lost between layers
- **Debugging nightmare**: Logs scattered across multiple processes
- **Deployment complexity**: Multiple processes, ports, and dependencies

### New Unified Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 UNIFIED FLASK APPLICATION                    │
├─────────────────────────────────────────────────────────────┤
│  Static Files  │  API Routes  │  Background Jobs  │  AI     │
│  (React Build) │  (REST only) │  (Python threads)│  (Goose)│
└─────────────────────────────────────────────────────────────┘
                               │
                     ┌─────────────────┐
                     │  SQLite Database │
                     │  (Single source) │
                     └─────────────────┘
```

### Key Design Principles
1. **Single Process**: Everything runs in one Python process
2. **Single Port**: All traffic through port 8000
3. **Single Language**: Python only (no Node.js)
4. **Simple Communication**: REST API + polling (no Socket.IO)
5. **Unified Data**: SQLite database as single source of truth
6. **Background Jobs**: Python threading within main process

## Components and Interfaces

### 1. Main Application (app.py)
```python
# Flask application factory pattern
def create_app():
    app = Flask(__name__)
    
    # Database initialization
    db.init_app(app)
    
    # Register blueprints
    app.register_blueprint(api_projects)
    app.register_blueprint(api_ai)
    app.register_blueprint(api_system)
    
    # Background job manager
    job_manager.init_app(app)
    
    return app
```

**Responsibilities:**
- Application configuration and initialization
- Blueprint registration for API routes
- Database setup and migrations
- Background job manager initialization
- Static file serving for React frontend

### 2. Database Models (models.py)
```python
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    repository_url = db.Column(db.String(500))
    status = db.Column(db.String(50), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    system_maps = db.relationship('SystemMap', backref='project')
    conversations = db.relationship('Conversation', backref='project')

class SystemMap(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    content = db.Column(db.JSON)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)

class BackgroundJob(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_type = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='pending')
    progress = db.Column(db.Integer, default=0)
    result = db.Column(db.JSON)
    error_message = db.Column(db.Text)
```

**Responsibilities:**
- Define all data structures with proper relationships
- Provide SQLAlchemy ORM interfaces
- Handle data validation and constraints
- Support atomic transactions

### 3. API Routes

#### Projects API (api/projects.py)
```python
@projects_bp.route('/api/projects', methods=['GET'])
def list_projects():
    projects = Project.query.all()
    return jsonify([project.to_dict() for project in projects])

@projects_bp.route('/api/projects', methods=['POST'])
def create_project():
    data = request.get_json()
    project = Project(name=data['name'], repository_url=data.get('repository_url'))
    db.session.add(project)
    db.session.commit()
    
    # Start background job for repository processing
    job_manager.start_repository_processing(project.id)
    
    return jsonify(project.to_dict()), 201
```

#### AI API (api/ai.py)
```python
@ai_bp.route('/api/ai/goose', methods=['POST'])
def goose_interaction():
    data = request.get_json()
    result = ai_service.process_goose_request(data['prompt'])
    return jsonify(result)

@ai_bp.route('/api/ai/models', methods=['GET'])
def list_models():
    models = ai_service.get_available_models()
    return jsonify(models)
```

#### System API (api/system.py)
```python
@system_bp.route('/api/status', methods=['GET'])
def system_status():
    return jsonify({
        'jobs': job_manager.get_active_jobs(),
        'system_health': get_system_health(),
        'database_status': check_database_connection()
    })
```

### 4. Services Layer

#### Repository Service (services/repository.py)
```python
class RepositoryService:
    def clone_repository(self, url, project_id):
        """Clone repository using GitPython"""
        try:
            repo_path = f"./repos/{project_id}"
            repo = git.Repo.clone_from(url, repo_path)
            return self.analyze_repository(repo_path, project_id)
        except Exception as e:
            logger.error(f"Repository cloning failed: {e}")
            raise

    def analyze_repository(self, repo_path, project_id):
        """Generate system map from repository"""
        analyzer = SystemMapAnalyzer(repo_path)
        system_map = analyzer.generate_map()
        
        # Save to database
        map_record = SystemMap(project_id=project_id, content=system_map)
        db.session.add(map_record)
        db.session.commit()
        
        return system_map
```

#### AI Service (services/ai_service.py)
```python
class AIService:
    def process_goose_request(self, prompt):
        """Handle Goose AI interactions"""
        # Existing Goose integration logic
        pass
    
    def get_available_models(self):
        """Return list of available AI models"""
        # Existing model garden logic
        pass
```

#### Background Job Manager (services/background.py)
```python
class BackgroundJobManager:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.active_jobs = {}
    
    def start_repository_processing(self, project_id):
        """Start repository processing in background thread"""
        job = BackgroundJob(
            job_type='repository_processing',
            status='running'
        )
        db.session.add(job)
        db.session.commit()
        
        future = self.executor.submit(
            self._process_repository, 
            project_id, 
            job.id
        )
        self.active_jobs[job.id] = future
        
        return job.id
    
    def _process_repository(self, project_id, job_id):
        """Background repository processing"""
        try:
            project = Project.query.get(project_id)
            repository_service.clone_repository(project.repository_url, project_id)
            
            # Update job status
            job = BackgroundJob.query.get(job_id)
            job.status = 'completed'
            job.progress = 100
            db.session.commit()
            
        except Exception as e:
            job = BackgroundJob.query.get(job_id)
            job.status = 'failed'
            job.error_message = str(e)
            db.session.commit()
```

### 5. Frontend Communication

#### Polling Strategy
Replace Socket.IO with simple HTTP polling:

```javascript
// Frontend polling implementation
class StatusPoller {
    constructor() {
        this.pollInterval = 2000; // 2 seconds
        this.isPolling = false;
    }
    
    startPolling() {
        if (this.isPolling) return;
        this.isPolling = true;
        this.poll();
    }
    
    async poll() {
        try {
            const response = await fetch('/api/status');
            const status = await response.json();
            this.updateUI(status);
        } catch (error) {
            console.error('Polling failed:', error);
        }
        
        if (this.isPolling) {
            setTimeout(() => this.poll(), this.pollInterval);
        }
    }
}
```

## Data Models

### Database Schema
```sql
-- Projects table
CREATE TABLE project (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    repository_url VARCHAR(500),
    status VARCHAR(50) DEFAULT 'pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- System maps table
CREATE TABLE system_map (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER REFERENCES project(id),
    content JSON,
    generated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Background jobs table
CREATE TABLE background_job (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    result JSON,
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Conversations table
CREATE TABLE conversation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER REFERENCES project(id),
    messages JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Data Flow
1. **Project Creation**: Frontend → API → Database → Background Job
2. **Repository Processing**: Background Thread → Git Operations → System Map → Database
3. **Status Updates**: Frontend Polling → API → Database Query → JSON Response
4. **AI Interactions**: Frontend → API → AI Service → Database (for history)

## Error Handling

### Centralized Error Handling
```python
@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled exception: {e}", exc_info=True)
    
    if isinstance(e, ValidationError):
        return jsonify({'error': 'Validation failed', 'details': str(e)}), 400
    elif isinstance(e, DatabaseError):
        return jsonify({'error': 'Database error', 'details': 'Please try again'}), 500
    else:
        return jsonify({'error': 'Internal server error'}), 500
```

### Background Job Error Recovery
- Failed jobs are marked in database with error details
- Jobs can be retried through API endpoints
- Partial progress is preserved for resumable operations
- Dead letter queue for permanently failed jobs

### Frontend Error Handling
- Graceful degradation when polling fails
- Retry logic with exponential backoff
- User-friendly error messages
- Offline mode detection

## Testing Strategy

### Unit Testing
```python
# Test database models
def test_project_creation():
    project = Project(name="Test Project")
    db.session.add(project)
    db.session.commit()
    assert project.id is not None

# Test API endpoints
def test_create_project_api():
    response = client.post('/api/projects', 
                          json={'name': 'Test Project'})
    assert response.status_code == 201
    assert 'id' in response.json

# Test background jobs
def test_repository_processing():
    job_id = job_manager.start_repository_processing(1)
    # Wait for completion and verify results
```

### Integration Testing
- End-to-end API testing with test database
- Background job processing with mock repositories
- Frontend integration with mock API responses
- Database migration testing

### Performance Testing
- Load testing with multiple concurrent requests
- Background job performance under load
- Database query optimization verification
- Memory usage monitoring during long-running operations

## Migration Strategy

### Phase 1: Parallel Implementation ✅ COMPLETED
- Build new Flask app alongside existing system
- Implement core models and API endpoints
- Set up database and basic functionality

### Phase 2: Feature Parity ✅ COMPLETED
- Port all existing functionality to new system
- Implement background job processing
- Add comprehensive testing

### Phase 3: Frontend Migration ✅ COMPLETED
- Update React app to use new API endpoints
- Remove Socket.IO dependencies
- Implement polling-based updates

### Phase 4: Cutover ✅ COMPLETED
- Switch traffic to new unified application
- Migrate existing data to SQLite database
- Decommission old servers

### Phase 5: Cleanup ✅ COMPLETED
- Remove old code and dependencies
- Update documentation and deployment scripts
- Performance optimization and monitoring

## Event-Driven Architecture Evolution

### Current Architecture (Unified Flask)
```
┌─────────────────────────────────────────────────────────────┐
│                 UNIFIED FLASK APPLICATION                    │
├─────────────────────────────────────────────────────────────┤
│  Static Files  │  API Routes  │  Background Jobs  │  AI     │
│  (React Build) │  (REST only) │  (Python threads)│  (Goose)│
└─────────────────────────────────────────────────────────────┘
                               │
                     ┌─────────────────┐
                     │  SQLite Database │
                     │  (Single source) │
                     └─────────────────┘
```

### Target Architecture (Event-Driven)
```
┌─────────────────────────────────────────────────────────────┐
│                    EVENT BUS (Redis)                        │
├─────────────────────────────────────────────────────────────┤
│         idea.created │ spec.frozen │ tasks.created          │
└─────────────────────────────────────────────────────────────┘
           │                 │                 │
    ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
    │   Capture   │   │   Define    │   │   Planner   │
    │   Agent     │   │   Agent     │   │   Agent     │
    └─────────────┘   └─────────────┘   └─────────────┘
           │                 │                 │
    ┌─────────────────────────────────────────────────────────┐
    │              POSTGRESQL + GRAPH                         │
    │         Projects │ Dependencies │ Code Relations        │
    └─────────────────────────────────────────────────────────┘
           │                 │                 │
    ┌─────────────────────────────────────────────────────────┐
    │                 VECTOR STORE                            │
    │          Document Chunks │ Embeddings │ Context         │
    └─────────────────────────────────────────────────────────┘
```

### Event-Driven Components

#### 1. Event Bus (Redis Streams)
```python
# Event Publisher
class EventPublisher:
    def publish(self, event_type: str, payload: dict):
        redis_client.xadd(f"events:{event_type}", payload)

# Event Subscriber
class EventSubscriber:
    def subscribe(self, event_type: str, handler: callable):
        # Listen to Redis stream and call handler
        pass
```

**Event Schema:**
- `idea.created`: {"project_id": "proj-123", "content": "...", "actor": "user@example.com"}
- `spec.frozen`: {"project_id": "proj-123", "brief_id": "brief-456", "requirements": [...]}
- `tasks.created`: {"project_id": "proj-123", "tasks": [...], "dependencies": [...]}
- `pr.opened`: {"project_id": "proj-123", "pr_id": "pr-789", "branch": "feature/gate-change"}

#### 2. Intelligent Agents
```python
class BaseAgent:
    def __init__(self, event_types: List[str]):
        self.event_types = event_types
        self.subscriber = EventSubscriber()
        
    def start(self):
        for event_type in self.event_types:
            self.subscriber.subscribe(event_type, self.handle_event)
    
    def handle_event(self, event):
        # Override in subclasses
        pass

class DefineAgent(BaseAgent):
    def __init__(self):
        super().__init__(['idea.created'])
    
    def handle_event(self, event):
        # Create product brief from idea
        # Publish spec.frozen event
        pass
```

#### 3. WebSocket Real-time Updates
```python
from flask_socketio import SocketIO, emit

socketio = SocketIO(app)

class WebSocketEventBridge:
    def __init__(self):
        self.subscriber = EventSubscriber()
        self.subscriber.subscribe('*', self.broadcast_to_clients)
    
    def broadcast_to_clients(self, event):
        socketio.emit('event', event, broadcast=True)
```

#### 4. Graph Database Integration
```python
class GraphService:
    def create_relationship(self, from_node, to_node, relationship_type):
        # Use PostgreSQL graph extensions
        query = """
        MATCH (a), (b) 
        WHERE a.id = $from_id AND b.id = $to_id
        CREATE (a)-[:$relationship_type]->(b)
        """
        
    def find_related_items(self, node_id, max_depth=3):
        # Graph traversal query
        pass
```

#### 5. Vector Search Service
```python
class VectorService:
    def add_document(self, doc_id, content):
        # Chunk document and create embeddings
        chunks = self.chunk_document(content)
        embeddings = self.create_embeddings(chunks)
        self.store_embeddings(doc_id, embeddings)
    
    def semantic_search(self, query, top_k=10):
        query_embedding = self.create_embedding(query)
        similar_docs = self.find_similar(query_embedding, top_k)
        return similar_docs
```

### Architecture Benefits

1. **Real-time Reactivity**: Events trigger instant responses
2. **Scalable Processing**: Agents run independently and can scale
3. **Intelligent Relationships**: Graph queries reveal complex connections
4. **Contextual AI**: Vector search provides relevant context
5. **External Integration**: Webhooks translate to internal events
6. **Comprehensive Monitoring**: All events are observable

### Development Phases

**Phase 1: Event Foundation**
- Redis message queue setup
- Basic event publishing/subscribing
- WebSocket integration for real-time UI

**Phase 2: Database Evolution**
- PostgreSQL migration from SQLite
- Graph extensions for relationship queries
- Vector store for semantic search

**Phase 3: Intelligent Agents**
- Base agent framework
- Define, Planner, Build agents
- Event-driven workflow automation

**Phase 4: External Integration**
- GitHub, CI/CD webhook integration
- External system notifications
- Bidirectional event translation

**Phase 5: Production Readiness**
- Comprehensive monitoring
- Performance optimization
- Deployment automation

### Performance Targets

- **Event Processing**: < 100ms latency
- **Graph Queries**: < 1 second response time
- **Vector Search**: < 500ms for semantic queries
- **WebSocket Updates**: < 50ms to client
- **System Throughput**: 1000+ events/second