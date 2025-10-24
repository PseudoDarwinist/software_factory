# Comprehensive System Architecture & Business Logic Analysis Prompt

## Analyze Software Factory Application - Complete Technical Documentation

You are a senior enterprise architect and technical documentation specialist. Your task is to perform a comprehensive analysis of the Software Factory codebase and generate detailed system architecture and business logic flow documentation.

---

## ANALYSIS OBJECTIVE

**Primary Goal**: Create a comprehensive technical design document that explains:
- How the Software Factory application works at every layer
- How components interact and communicate
- How business logic flows through the system
- How AI agents orchestrate the development lifecycle
- How the event-driven architecture enables real-time collaboration

**Target Audience**: Enterprise architects, senior developers, product managers, and system administrators who need to understand the complete system architecture and business logic flow.

**Output Format**: Generate a comprehensive design document with detailed explanations, diagrams (in text/Markdown format), and technical specifications.

---

## ANALYSIS FRAMEWORK

Follow this systematic analysis approach:

### 1. EXECUTIVE SUMMARY & SYSTEM OVERVIEW
```
Provide a high-level overview answering:
- What is Software Factory?
- What problem does it solve?
- What are the key architectural principles?
- How does AI integrate with traditional software development?
- What are the main benefits and use cases?
```

### 2. ARCHITECTURAL FOUNDATIONS
```
Analyze and document:
- Core architectural patterns (Event-Driven Architecture)
- Technology stack and rationale
- System boundaries and interfaces
- Deployment architecture
- Scalability and reliability considerations
```

### 3. COMPONENT ANALYSIS BY LAYER

#### EXTERNAL SYSTEMS LAYER
```
Document each external integration:
- Slack API integration
  * Webhook handling mechanisms
  * Message parsing and enrichment
  * Channel-to-project mapping
  * Real-time event streaming

- GitHub API integration
  * Repository access patterns
  * PR creation and management
  * Webhook event processing
  * Branch and commit management

- MCP (Model Context Protocol) Server
  * External AI tool integration
  * Context provision mechanisms
  * Specification storage and retrieval
  * Authentication and authorization

- IDE Integrations (Kiro, Cursor)
  * Integration patterns
  * Context sharing mechanisms
  * Workflow orchestration
```

#### PRESENTATION LAYER
```
Document the frontend architecture:
- Mission Control UI
  * Stage-based workflow (Think, Define, Plan, Build, Validate, User, Learn)
  * Real-time WebSocket integration
  * Component architecture
  * State management patterns

- WebSocket Client Architecture
  * Connection management
  * Event subscription patterns
  * Real-time UI updates
  * Error handling and reconnection

- User Experience Flows
  * Idea capture workflow
  * Specification creation process
  * Task planning and execution
  * Build and deployment monitoring
```

#### API GATEWAY LAYER
```
Document the backend entry points:
- Flask Application Architecture
  * Unified application structure
  * Blueprint organization
  * Middleware stack (CORS, Auth, Sessions)
  * Request routing and handling

- WebSocket Server Implementation
  * SocketIO integration
  * Namespace organization
  * Authentication mechanisms
  * Event broadcasting patterns

- MCP Server Implementation
  * Tool registration and discovery
  * Context provision APIs
  * Specification management endpoints
  * External integration patterns

- API Endpoint Analysis
  * RESTful API design patterns
  * Authentication and authorization
  * Error handling and response formats
  * Rate limiting and throttling
```

#### SERVICE LAYER
```
Document each core service:
- AI Broker Service
  * Model selection algorithms
  * Request queuing and prioritization
  * Context management and caching
  * Performance optimization strategies

- Event Bus (Redis-backed)
  * Publish/subscribe patterns
  * Event routing and filtering
  * Persistence and replay capabilities
  * Monitoring and observability

- Spec Generation Service
  * Asynchronous processing patterns
  * Progress tracking and reporting
  * Error handling and recovery
  * Resource management

- Coding Assistants (BYOA)
  * Assistant registry and discovery
  * Capability routing algorithms
  * Context preservation
  * Quality assurance mechanisms

- Vector Service (pgVector)
  * Embedding generation and storage
  * Semantic search implementation
  * Similarity algorithms
  * Performance optimization

- Authentication Service
  * JWT token management
  * Project-based access control
  * Role-based permissions
  * Session management
```

#### AI AGENTS LAYER
```
Document each AI agent in detail:
- Define Agent
  * Repository analysis capabilities
  * Context integration patterns
  * Specification generation workflows
  * Quality assurance mechanisms

- Planner Agent
  * Task parsing and creation
  * Effort estimation algorithms
  * Dependency mapping
  * Kanban board integration

- Code Impact Analyzer
  * Architectural complexity assessment
  * Security vulnerability detection
  * Performance impact analysis
  * Recommendation generation

- Project Health Monitor
  * Activity pattern analysis
  * Health scoring algorithms
  * Predictive analytics
  * Alert generation mechanisms

- AI Assistant Integrations
  * Kiro Assistant: IDE integration patterns
  * Claude Code Assistant: Code generation workflows
  * Cursor Assistant: Development assistance
  * Capability routing and orchestration
```

#### DOMAIN LOGIC LAYER
```
Document business logic implementation:
- Domain Pack System
  * Pack structure and organization
  * Configuration management
  * Rule engine implementation
  * Extensibility patterns

- Business Rules Engine
  * Rule definition and execution
  * Condition evaluation patterns
  * Action triggering mechanisms
  * Audit and compliance tracking

- Validation Rules
  * Consent compliance validation
  * Duplicate suppression logic
  * Eligibility verification
  * Business rule enforcement

- SLA Engine
  * Event-based timing mechanisms
  * Channel-specific SLA rules
  * Priority-based escalation
  * Performance monitoring
```

#### DATA LAYER
```
Document data architecture:
- PostgreSQL Database
  * Schema design and relationships
  * Table structures and constraints
  * Indexing strategies
  * Connection pooling

- Redis Implementation
  * Caching strategies and patterns
  * Pub/Sub implementation
  * Session management
  * Performance optimization

- pgVector Integration
  * Embedding storage and retrieval
  * Vector similarity search
  * AI context management
  * Performance characteristics

- Event Store
  * Event persistence patterns
  * Replay capabilities
  * Audit trail management
  * Data retention policies

- File Storage
  * PRD and specification storage
  * Asset management
  * CDN integration
  * Backup and recovery
```

### 4. BUSINESS LOGIC FLOW ANALYSIS

#### Idea Capture & Processing Flow
```
Document the complete journey:
1. Slack Message Ingestion
   - Webhook validation and parsing
   - Message enrichment and tagging
   - Channel-to-project mapping
   - Event publishing

2. Idea Enrichment
   - Entity extraction and classification
   - Context gathering from codebase
   - Priority assessment
   - Metadata attachment

3. Real-time UI Updates
   - WebSocket event broadcasting
   - UI state management
   - User notification patterns
   - Error handling and recovery

4. Idea Lifecycle Management
   - Status tracking and transitions
   - Assignment and ownership
   - Archival and cleanup
   - Analytics and reporting
```

#### Define Phase - Specification Generation
```
Document the AI-powered specification process:
1. Idea Promotion Trigger
   - User interaction patterns
   - Validation and authorization
   - Event publishing and routing
   - Resource allocation

2. Context Gathering
   - Repository analysis and scanning
   - PRD and documentation retrieval
   - Similar pattern identification
   - Context embedding generation

3. AI-Powered Generation
   - Requirements.md creation
     * Functional requirement extraction
     * Non-functional requirement analysis
     * Acceptance criteria definition
     * Technical constraint identification

   - Design.md creation
     * Architecture diagram generation
     * Component interaction modeling
     * Database schema design
     * API specification creation

   - Tasks.md creation
     * Implementation task breakdown
     * Effort estimation algorithms
     * Dependency mapping
     * Testing strategy definition

4. Quality Assurance
   - Specification validation
   - Consistency checking
   - Completeness verification
   - User feedback integration

5. Specification Freezing
   - Approval workflow
   - Version management
   - Change tracking
   - Audit trail creation
```

#### Plan Phase - Task Planning & Execution
```
Document task management workflow:
1. Specification Processing
   - Task extraction and parsing
   - Metadata enrichment
   - Priority assessment
   - Assignment recommendations

2. Kanban Board Integration
   - Task visualization
   - Status tracking
   - Drag-and-drop interactions
   - Real-time synchronization

3. Task Lifecycle Management
   - Status transitions (Ready → In Progress → Completed)
   - Time tracking and estimation
   - Blocker identification
   - Progress reporting

4. Team Collaboration
   - Comment and discussion threads
   - File attachment support
   - Notification mechanisms
   - Audit trail maintenance
```

#### Build Phase - Code Implementation
```
Document the build and deployment process:
1. Task Execution Trigger
   - Build environment setup
   - Repository cloning and preparation
   - Dependency resolution
   - Security scanning

2. AI-Powered Code Generation
   - Context analysis and understanding
   - Code pattern identification
   - Implementation generation
   - Testing strategy creation

3. Quality Assurance
   - Unit test generation and execution
   - Code review automation
   - Security vulnerability scanning
   - Performance testing

4. GitHub Integration
   - Branch creation and management
   - Pull request generation
   - Code review workflow
   - Merge automation

5. Deployment Pipeline
   - Continuous integration
   - Automated testing
   - Deployment orchestration
   - Rollback mechanisms
```

#### Validation & Learning Phases
```
Document quality assurance and optimization:
1. Validation Phase
   - Automated testing execution
   - Performance benchmarking
   - Security assessment
   - User acceptance testing

2. User Phase (Simulation)
   - Synthetic user journey testing
   - Usability assessment
   - Friction point identification
   - Accessibility evaluation

3. Learning Phase
   - Metrics collection and analysis
   - Performance trend analysis
   - Failure pattern identification
   - Optimization recommendations

4. Continuous Improvement
   - Feedback loop implementation
   - Process optimization
   - AI model fine-tuning
   - System performance enhancement
```

### 5. EVENT-DRIVEN ARCHITECTURE PATTERNS

#### Event Type Analysis
```
Document all event types and their flows:
- Idea Events (idea.received, idea.captured, idea.promoted)
- Specification Events (spec.drafted, spec.frozen, spec.approved)
- Task Events (task.created, task.started, task.completed)
- Build Events (build.started, build.succeeded, build.failed)
- Validation Events (validation.started, validation.passed)
- Learning Events (insight.generated, pattern.discovered)

For each event type, document:
- Trigger conditions
- Data payload structure
- Subscriber components
- Processing logic
- Error handling patterns
- Performance characteristics
```

#### Event Processing Patterns
```
Document event handling mechanisms:
- Synchronous Processing
  - Immediate response requirements
  - Blocking operations
  - Error propagation
  - Timeout handling

- Asynchronous Processing
  - Background job queuing
  - Progress tracking
  - Result aggregation
  - Failure recovery

- Event Chaining
  - Sequential processing patterns
  - Parallel execution
  - Conditional branching
  - Loop prevention

- Event Persistence
  - Event sourcing patterns
  - Replay capabilities
  - Audit trail maintenance
  - Data retention policies
```

### 6. SECURITY ARCHITECTURE

#### Authentication & Authorization
```
Document security implementation:
- JWT Token Management
  - Token generation and validation
  - Refresh token handling
  - Expiration management
  - Revocation mechanisms

- Project-Based Access Control
  - User-project associations
  - Permission inheritance
  - Role-based access
  - Resource-level authorization

- WebSocket Security
  - Connection authentication
  - Event filtering
  - Rate limiting
  - Session management

- External Integration Security
  - API key management
  - OAuth implementation
  - Webhook verification
  - Data encryption
```

#### Data Protection
```
Document data security measures:
- Database Security
  - Connection encryption
  - Query parameterization
  - Access logging
  - Backup encryption

- Application Security
  - Input validation and sanitization
  - XSS prevention
  - CSRF protection
  - Security headers

- Network Security
  - SSL/TLS implementation
  - Firewall configuration
  - Intrusion detection
  - Traffic encryption

- Compliance & Auditing
  - GDPR compliance mechanisms
  - Audit trail implementation
  - Data retention policies
  - Privacy protection
```

### 7. PERFORMANCE & SCALABILITY

#### Performance Characteristics
```
Document performance architecture:
- Response Time Requirements
  - WebSocket round-trip: < 150ms
  - AI response time: < 45 seconds
  - Database queries: < 50ms
  - API responses: < 200ms

- Throughput Requirements
  - Concurrent users supported
  - Event processing capacity
  - AI agent utilization
  - Database connection pooling

- Resource Utilization
  - Memory consumption patterns
  - CPU utilization tracking
  - Disk I/O optimization
  - Network bandwidth usage
```

#### Scalability Architecture
```
Document scaling strategies:
- Horizontal Scaling
  - Load balancer configuration
  - Session management
  - Data consistency
  - Service discovery

- Database Scaling
  - Read/write splitting
  - Sharding strategies
  - Replication setup
  - Connection pooling

- AI Agent Scaling
  - Agent load balancing
  - Queue management
  - Resource allocation
  - Performance monitoring

- Caching Strategies
  - Multi-level caching
  - Cache invalidation
  - Cache warming
  - Performance optimization
```

### 8. MONITORING & OBSERVABILITY

#### Metrics Collection
```
Document monitoring implementation:
- Application Metrics
  - Request/response metrics
  - Error rates and patterns
  - Performance histograms
  - Resource utilization

- Business Metrics
  - Idea processing rates
  - Specification generation times
  - Task completion rates
  - User engagement metrics

- AI Agent Metrics
  - Model performance tracking
  - Response time analysis
  - Success/failure rates
  - Resource consumption
```

#### Logging & Alerting
```
Document observability patterns:
- Structured Logging
  - Log levels and formats
  - Context propagation
  - Correlation IDs
  - Log aggregation

- Alerting System
  - Threshold-based alerts
  - Anomaly detection
  - Escalation procedures
  - Automated responses

- Tracing & Debugging
  - Distributed tracing
  - Performance profiling
  - Error tracking
  - Root cause analysis
```

### 9. DEPLOYMENT & OPERATIONS

#### Deployment Architecture
```
Document deployment patterns:
- Container Orchestration
  - Docker containerization
  - Kubernetes deployment
  - Service mesh implementation
  - Configuration management

- Environment Management
  - Development environment
  - Staging environment
  - Production environment
  - Rollback procedures

- CI/CD Pipeline
  - Automated testing
  - Deployment automation
  - Rollback mechanisms
  - Release management
```

#### Operational Procedures
```
Document operational aspects:
- Backup & Recovery
  - Database backup strategies
  - Application backup procedures
  - Disaster recovery plans
  - Data retention policies

- Maintenance Procedures
  - Regular maintenance tasks
  - Security patching
  - Performance optimization
  - Capacity planning

- Incident Response
  - Incident detection
  - Response procedures
  - Communication plans
  - Post-mortem analysis
```

---

## OUTPUT REQUIREMENTS

### Document Structure
```
Generate a comprehensive design document with:

1. EXECUTIVE SUMMARY
   - System overview and purpose
   - Key architectural decisions
   - Business value proposition

2. ARCHITECTURAL OVERVIEW
   - System context and boundaries
   - Architectural patterns and styles
   - Technology stack rationale

3. DETAILED COMPONENT ANALYSIS
   - Layer-by-layer breakdown
   - Component interactions
   - Interface specifications

4. BUSINESS LOGIC FLOWS
   - End-to-end workflow analysis
   - Decision points and branching logic
   - Error handling and recovery patterns

5. EVENT-DRIVEN ARCHITECTURE
   - Event type catalog
   - Processing patterns
   - Performance characteristics

6. SECURITY ARCHITECTURE
   - Authentication and authorization
   - Data protection mechanisms
   - Compliance considerations

7. PERFORMANCE & SCALABILITY
   - Performance requirements
   - Scaling strategies
   - Resource optimization

8. MONITORING & OPERATIONS
   - Observability patterns
   - Operational procedures
   - Maintenance practices

9. APPENDICES
   - API specifications
   - Database schemas
   - Configuration files
   - Performance benchmarks
```

### Documentation Standards
```
Follow these documentation standards:
- Use clear, technical language appropriate for senior developers and architects
- Include Mermaid diagrams for complex workflows and architectures
- Provide code examples where relevant
- Include performance benchmarks and scalability metrics
- Reference specific files and components from the codebase
- Explain design decisions and trade-offs
- Include troubleshooting and maintenance guides
```

### Quality Assurance
```
Ensure the documentation:
- Is comprehensive but not overwhelming
- Balances high-level architecture with implementation details
- Explains both "what" and "why" for architectural decisions
- Provides practical guidance for operations and maintenance
- Includes troubleshooting information for common issues
- References real implementation details from the codebase
```

---

## FINAL DELIVERABLE

Generate a comprehensive design document that serves as the authoritative technical reference for the Software Factory application. The document should enable readers to understand:

- How the system works at every layer
- How components interact and communicate
- How business logic flows through the system
- How to operate and maintain the system
- How to extend and enhance the system

The resulting document should be suitable for use by enterprise architects, senior developers, DevOps engineers, and product managers who need to understand the complete system architecture and business logic flow of the Software Factory platform.






