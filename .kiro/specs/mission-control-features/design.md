# Design Document

## Overview

The Mission Control Features design implements a sophisticated agent-driven workflow system that transforms the Software Factory into an intelligent development platform. The design centers around seven specialized agents that react to domain events, use context-aware AI, and maintain project state through a unified event-driven architecture.

The system leverages the existing Flask application, PostgreSQL with pgvector and graph extensions, Redis message queue, and WebSocket infrastructure to create seamless automation that feels magical to users while maintaining full transparency and human control.

## Architecture

### High-Level System Flow

```
Slack Message → Capture Agent → idea.captured → WebSocket → Think Stage UI
     ↓
User Drag → idea.promoted → Define Agent → pgvector context → Claude → spec.frozen
     ↓
Planner Agent → tasks.created → Plan Stage UI → User Drag → task.started
     ↓
Build Agent → pgvector context → Claude-Code → PR created → build.started
     ↓
GitHub Webhook → build.succeeded → Test Agent → quality analysis → user.ready
     ↓
User Simulation Agent → synthetic testing → user.friction → Learn Agent
     ↓
Learn Agent → insights generated → pattern.identified → new ideas
```

### Event-Driven Agent Coordination

The system uses a hub-and-spoke model where Redis serves as the central event bus, with each agent subscribing to specific event types and publishing new events based on their processing results. The Agent Manager prevents infinite loops and manages agent lifecycle.

### Context-Aware AI Integration

All AI interactions follow a consistent pattern:
1. Receive domain event with project context
2. Query pgvector for similar historical examples
3. Query graph database for related project artifacts
4. Combine context into structured prompt
5. Call appropriate AI model (Claude, Goose, Gemini)
6. Process response and emit result events

## Components and Interfaces

### 0. Project Onboarding Wizard (`OnboardingWizard.tsx`)

**Three-Screen Flow:**
1. **Connect Repository Screen** - User pastes GitHub HTTPS/SSH URL, system performs shallow clone and generates initial system map
2. **Upload Documentation Screen** - Drag-and-drop interface for PDFs and Markdown files, automatic chunking and pgvector embedding
3. **Link Communications Screen** - Slack channel selection with project mapping, optional webhook configuration for other tools

### 1. Agent Framework (`src/agents/`)

#### Base Agent Class (`base.py`)
```python
class BaseAgent:
    def __init__(self, agent_id: str, event_types: List[str])
    def subscribe_to_events(self, event_types: List[str])
    def publish_event(self, event_type: str, payload: dict)
    def get_project_context(self, project_id: str) -> ProjectContext
    def get_vector_context(self, query: str, project_id: str) -> List[Document]
    def get_graph_relationships(self, entity_id: str) -> GraphResult
    def increment_metric(self, event_type: str, status: str)
```

#### Agent Manager (`agent_manager.py`)
- Manages agent lifecycle and event subscriptions
- Prevents infinite event loops using sliding window detection
- Handles agent throttling and error recovery
- Provides agent health monitoring and metrics
- Respects per-project agent toggles (define_enabled, planner_enabled, build_enabled flags in Project table)

### 2. Specialized Agents

#### Capture Agent (`capture_agent.py`)
**Purpose:** Process incoming Slack messages and external inputs
**Events:** Subscribes to `slack.message.received`, publishes `idea.captured`
**Context:** Uses project system map for entity recognition
**AI Integration:** Claude for content analysis and categorization

#### Define Agent (`define_agent.py`)
**Purpose:** Generate comprehensive specifications from promoted ideas
**Events:** Subscribes to `idea.promoted`, publishes `spec.frozen`
**Context:** pgvector search for similar specs, project documentation
**AI Integration:** Claude with rich context for requirements, design, and task generation
**External Integration:** Optional Notion sync after `spec.frozen` (disabled by default, configured per project)

#### Planner Agent (`planner_agent.py`)
**Purpose:** Break down specifications into actionable tasks
**Events:** Subscribes to `spec.frozen`, publishes `tasks.created`
**Context:** Git blame analysis for owner suggestions, team expertise graph
**AI Integration:** Minimal - primarily rule-based task parsing and assignment

#### Build Agent (`build_agent.py`)
**Purpose:** Generate code and create pull requests
**Events:** Subscribes to `task.started`, publishes `build.started`
**Context:** pgvector for similar code, graph for dependencies
**AI Integration:** Claude-Code with comprehensive project context

#### Test Agent (`test_agent.py`)
**Purpose:** Generate tests and analyze quality
**Events:** Subscribes to `build.succeeded`, publishes `quality.analyzed`
**Context:** Code diff analysis, existing test patterns
**AI Integration:** Claude for test generation and failure analysis

#### User Simulation Agent (`user_simulation_agent.py`)
**Purpose:** Run synthetic user testing
**Events:** Subscribes to `deployment.completed`, publishes `user.friction`
**Context:** User personas, historical friction patterns
**AI Integration:** Behavioral analysis and friction detection

#### Learn Agent (`learn_agent.py`)
**Purpose:** Generate insights and continuous improvement recommendations
**Events:** Subscribes to project completion events, publishes `pattern.identified`
**Context:** Historical project data, success/failure patterns
**AI Integration:** Pattern recognition and insight generation

### 3. Context Services (`src/services/`)

#### Vector Context Service (`vector_context_service.py`)
```python
class VectorContextService:
    def find_similar_specs(self, query: str, project_id: str, limit: int = 5)
    def find_similar_code(self, query: str, project_id: str, limit: int = 10)
    def find_related_docs(self, query: str, project_id: str, limit: int = 3)
    def embed_and_store(self, content: str, content_type: str, project_id: str)
```

#### Graph Relationship Service (`graph_service.py`)
```python
class GraphService:
    def get_idea_relationships(self, idea_id: str) -> Dict
    def get_spec_dependencies(self, spec_id: str) -> Dict
    def get_task_connections(self, task_id: str) -> Dict
    def get_team_expertise(self, project_id: str) -> Dict
    def create_relationship(self, from_entity: str, to_entity: str, rel_type: str)
```

### 4. UI Components (`mission-control/src/components/`)

#### Stage Navigation (`StageNav.tsx`)
- Implements seven-stage navigation with progression rules
- Shows health indicators and stage enablement status
- Handles stage transitions and URL routing

#### Think Stage (`ThinkStage.tsx`)
- Feed list with intelligent categorization
- Drag-to-define functionality with visual feedback
- Context panel with relationship display

#### Define Stage (`DefineStage.tsx`)
- Three-tab editor for requirements.md, design.md, tasks.md
- AI-draft vs Human-reviewed badge system
- Freeze specification workflow

#### Plan Stage (`PlanStage.tsx`)
- Kanban board with Ready/In Progress/Done lanes
- Task detail drawer with context and relationships
- Real-time updates via WebSocket

#### Build Stage (`BuildStage.tsx`)
- PR monitoring table with CI status
- Build failure analysis and recommendations
- Code preview and branch management

#### Validate Stage (`ValidateStage.tsx`)
- Test execution timeline and results
- Quality analysis and AI-powered insights
- Test coverage and performance metrics

#### User Stage (`UserStage.tsx`)
- User simulation grid with persona and status
- Friction point visualization and replay
- User behavior analysis and recommendations

#### Learn Stage (`LearnStage.tsx`)
- Insight carousel with actionable recommendations
- "Open as idea" functionality for continuous improvement
- Pattern recognition and trend analysis

### 5. Real-Time Communication (`src/services/websocket_server.py`)

#### WebSocket Event Bridge
- Subscribes to Redis events and filters by user permissions
- Broadcasts relevant events to connected clients
- Handles connection management and reconnection logic
- Provides user presence indicators

#### Event Filtering
```python
def filter_events_for_user(user_token: str, event: dict) -> bool:
    user_projects = decode_token(user_token).project_ids
    return event.payload.project_id in user_projects
```

## Data Models

### Event Schema
```python
@dataclass
class DomainEvent:
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: str
    event_type: str
    payload: dict
    source_agent: str
    project_id: str
```

### Project Context
```python
@dataclass
class ProjectContext:
    project_id: str
    system_map: dict
    documentation: List[Document]
    team_members: List[TeamMember]
    git_repository: str
    external_integrations: dict
```

### Specification Artifacts
```python
class SpecificationArtifact(db.Model):
    id = db.Column(db.String, primary_key=True)
    project_id = db.Column(db.String, db.ForeignKey('project.id'))
    artifact_type = db.Column(db.Enum('requirements', 'design', 'tasks'))
    content = db.Column(db.Text)
    status = db.Column(db.Enum('ai_draft', 'human_reviewed', 'frozen'))
    version = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
```

## Error Handling

### Agent Error Recovery
- Each agent implements circuit breaker pattern for external API calls
- Failed events are stored in dead letter queue for manual review
- Agent health checks ensure system resilience
- Automatic retry with exponential backoff for transient failures

### Event Processing Guarantees
- At-least-once delivery for critical events
- Idempotency checks prevent duplicate processing
- Event ordering preservation within project scope
- Graceful degradation when external services are unavailable

### User Experience Resilience
- WebSocket reconnection with missed event sync
- Optimistic UI updates with server confirmation
- Fallback to polling when WebSocket unavailable
- Clear error messaging and recovery suggestions

## Testing Strategy

### Agent Testing
- Unit tests for each agent's event processing logic
- Integration tests for agent coordination scenarios
- Mock external services (Slack, GitHub, AI models)
- Event replay testing for complex workflows

### Context Service Testing
- Vector similarity accuracy testing with known datasets
- Graph query performance testing with large datasets
- Context retrieval integration testing
- AI prompt quality validation

### UI Testing
- Component testing for each stage interface
- End-to-end testing for complete user workflows
- WebSocket event handling testing
- Mobile responsiveness and accessibility testing

### Performance Testing
- Event throughput testing under load
- WebSocket connection scaling testing
- Database query optimization validation
- AI response time monitoring

### Monitoring and Observability
- Prometheus metrics collection for all agent operations (success/failure counters by event_type)
- Grafana dashboards for system health, event throughput, and AI response times
- Agent health endpoints for load balancer integration
- Distributed tracing for complex event flows

## Security Considerations

### Authentication and Authorization
- JWT tokens with project-scoped permissions
- Agent-specific service accounts with minimal privileges
- External integration tokens with short expiration
- Audit logging for all security-relevant events

### Data Protection
- Encryption at rest for sensitive project data
- TLS encryption for all external communications
- PII scrubbing in logs and metrics
- GDPR compliance for user data handling

### Agent Security
- Sandboxed execution environment for code generation
- Input validation for all external data sources
- Rate limiting for AI model calls
- Secure credential management for external services

This design provides a comprehensive blueprint for implementing the intelligent Mission Control system while maintaining security, performance, and user experience standards.