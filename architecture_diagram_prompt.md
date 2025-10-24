# Comprehensive Architecture Diagram Generation Prompt for Software Factory

## Create a Highly Detailed System Architecture Diagram

Generate a comprehensive, professional system architecture diagram for the **Software Factory** application. This is an AI-powered software development lifecycle platform that transforms ideas into production code through intelligent automation.

---

## OVERVIEW & CONTEXT

**Application Name**: Software Factory
**Domain**: AI-powered Software Development Lifecycle Platform
**Architecture Style**: Event-Driven Microservices with AI Agent Orchestration
**Technology Stack**: Python Flask, React, PostgreSQL, Redis, WebSocket, pgVector

---

## ARCHITECTURAL LAYERS (Draw as Horizontal Layers)

### 1. EXTERNAL SYSTEMS LAYER (Top Layer - Light Blue Background)
**Position**: Top of diagram, spanning full width

**Components to include:**
- **Slack API** (purple icon) - Message ingestion
- **GitHub API** (dark gray icon) - Code repository integration
- **MCP Server** (orange icon) - Model Context Protocol for external AI tools
- **Kiro IDE** (teal icon) - Advanced IDE integration
- **Cursor IDE** (green icon) - AI-powered code editor

**Visual Style**: Cloud-shaped icons with connection arrows pointing downward

---

### 2. PRESENTATION LAYER (Second Layer - Light Green Background)

**Components:**
- **Mission Control UI** (large central rectangle)
  - Sub-components: Think Stage, Define Stage, Plan Stage, Build Stage, Validate Stage, User Stage, Learn Stage
  - Features: Real-time updates, Kanban boards, Specification editors
- **Mission-Control-Dist** (smaller rectangle) - Deployed frontend
- **WebSocket Client** (bidirectional arrow icon) - Real-time communication

**Visual Style**: Modern web app interface mockup with browser windows

---

### 3. API GATEWAY LAYER (Third Layer - Yellow Background)

**Central Component:**
- **Flask Application** (large central hexagon)
  - Label: "Unified Flask App - Single Process Architecture"
  - Sub-components inside hexagon:
    - CORS Handler
    - Authentication Service
    - Session Management
    - Request Routing

**Supporting Components:**
- **WebSocket Server** (diamond shape) - Real-time bidirectional communication
- **MCP Server** (orange circle) - External AI tool integration
- **API Endpoints** (small rectangles around Flask app):
  - `/api/projects`
  - `/api/ideas`
  - `/api/specs`
  - `/api/tasks`
  - `/api/github`
  - `/api/mcp`

**Visual Style**: Hexagonal architecture with labeled endpoints

---

### 4. SERVICE LAYER (Fourth Layer - Orange Background)

**Core Services (arrange in a semicircle around center):**
- **AI Broker Service** (large brain icon)
  - Sub-labels: Model Selection, Request Queuing, Context Management
- **Event Bus** (message queue icon)
  - Label: "Redis-backed Event Bus"
- **Spec Generation Service** (document icon)
  - Label: "Asynchronous Spec Generation"
- **Coding Assistants** (robot icon)
  - Label: "BYOA (Bring Your Own Assistant)"
- **Auth Service** (lock icon)
  - Label: "JWT Bearer Token Validation"
- **Vector Service** (database icon)
  - Label: "pgVector Embeddings"
- **WebSocket Server** (signal icon)
  - Label: "Real-time Broadcasting"

**Visual Style**: Service icons with connecting lines showing interdependencies

---

### 5. AI AGENTS LAYER (Fifth Layer - Purple Background)

**AI Agent Orchestration Center (large central hub):**

**Specialized AI Agents (arrange in circle around center):**
- **Define Agent** (blue robot)
  - Generates: requirements.md, design.md, tasks.md
  - Capabilities: Repository Analysis, Context Integration
- **Planner Agent** (green robot)
  - Converts tasks.md → Database Tasks
  - Capabilities: Task Planning, Effort Estimation
- **Code Impact Analyzer** (orange robot)
  - Monitors architectural changes
  - Capabilities: Complexity Analysis, Security Scanning
- **Project Health Monitor** (red robot)
  - Predictive analytics
  - Capabilities: Activity Pattern Analysis, Health Scoring

**AI Assistant Integrations (smaller icons below agents):**
- **Kiro Assistant** (teal icon) - IDE integration
- **Claude Code Assistant** (purple icon) - Code generation
- **Cursor Assistant** (green icon) - Development workflow

**Visual Style**: Robot icons with capability labels, connected to central orchestration hub

---

### 6. DOMAIN LOGIC LAYER (Sixth Layer - Teal Background)

**Domain Pack System (central component):**
- **Domain Packs** (folder icon)
  - Default Pack
  - IRR Pack
  - Custom Packs

**Business Logic Components:**
- **Business Rules Engine** (gears icon)
- **Validation Rules** (checkmark icon)
  - Consent Compliance
  - Duplicate Suppression
  - Eligibility Validation
- **SLA Engine** (clock icon)
  - Event-based timing
  - Channel-specific rules

**Visual Style**: Business logic components with rule flow diagrams

---

### 7. DATA LAYER (Bottom Layer - Dark Blue Background)

**Primary Databases:**
- **PostgreSQL** (large cylinder)
  - Tables: projects, ideas, specs, tasks, users, events
  - Features: ACID compliance, JSON support

- **Redis** (smaller cylinder)
  - Usage: Event bus, caching, session storage
  - Features: Pub/Sub, high performance

- **pgVector** (specialized cylinder)
  - Usage: Semantic search, embeddings
  - Features: Vector similarity, AI context retrieval

**Supporting Storage:**
- **Event Store** (timeline icon) - Append-only event storage
- **File Storage** (folder icon) - PRDs, specifications, assets
- **Vector Embeddings** (neural network icon) - AI-generated embeddings

**Visual Style**: Database cylinders with labeled schemas and relationships

---

## DATA FLOW DIAGRAMS (Overlay on Architecture)

### Primary Workflows (Draw as Colored Arrows)

#### 1. IDEA CAPTURE FLOW (Red Arrows)
```
Slack → Webhook Service → Event Bus → Capture Agent → Database → WebSocket → UI
```
- **Style**: Red arrows with labels
- **Direction**: Left to right, top to bottom

#### 2. DEFINE PHASE FLOW (Blue Arrows)
```
UI → Spec Generation Service → Define Agent → AI Broker → Vector Service → Database → Event Bus → Planner Agent
```
- **Style**: Blue arrows with phase labels
- **Components**: requirements.md → design.md → tasks.md

#### 3. PLAN PHASE FLOW (Green Arrows)
```
Spec Frozen Event → Planner Agent → Task Creation → Database → WebSocket → Kanban Board
```
- **Style**: Green arrows with task status transitions

#### 4. BUILD PHASE FLOW (Orange Arrows)
```
Task Started → Build Agent → GitHub API → PR Creation → CI/CD → Validation Agent
```
- **Style**: Orange arrows with build statuses

#### 5. MCP INTEGRATION FLOW (Purple Arrows)
```
External AI Tool → MCP Server → Software Factory → Vector Service → Context Provision → Specification Storage
```
- **Style**: Purple arrows with MCP protocol labels

---

## EVENT-DRIVEN ARCHITECTURE PATTERNS (Show as Message Flows)

### Event Types (Label as Floating Text Boxes)
- **idea.received** - New idea from Slack
- **idea.captured** - Idea processed and stored
- **idea.promoted** - Idea moved to Define phase
- **spec.drafted** - Specification created
- **spec.frozen** - Specification approved
- **tasks.created** - Implementation tasks generated
- **task.started** - Development begins
- **build.started** - Code generation begins
- **build.succeeded** - Implementation complete
- **validation.started** - Testing begins
- **validation.passed** - Quality gates passed

### Event Flow Visualization
- **Event Bus** (central message hub)
- **Publishers** (components sending events)
- **Subscribers** (components receiving events)
- **WebSocket Broadcasting** (real-time UI updates)

---

## AI AGENT CAPABILITIES MATRIX (Bottom Right Corner)

Create a detailed matrix showing:

| AI Agent | Repository Access | Context Integration | Output Format | Key Capabilities |
|----------|------------------|-------------------|---------------|------------------|
| Define Agent | Full filesystem | PRD + Code patterns | requirements.md, design.md, tasks.md | Spec generation, pattern analysis |
| Planner Agent | Task conversion | Spec requirements | Database tasks | Effort estimation, dependency mapping |
| Code Impact Analyzer | Architecture scanning | Code changes | Alerts & recommendations | Complexity analysis, security scanning |
| Project Health Monitor | Activity analysis | Project metrics | Health scores | Predictive analytics, pattern detection |

---

## SECURITY ARCHITECTURE (Overlay Security Elements)

### Authentication & Authorization
- **JWT Tokens** (lock icons on API endpoints)
- **Bearer Token Validation** (security checkpoints)
- **Project-based Access Control** (permission gates)
- **WebSocket Security** (encrypted connections)

### Data Protection
- **SSL/TLS Encryption** (shield icons)
- **Input Validation** (filter icons)
- **SQL Injection Prevention** (database shields)
- **XSS Protection** (frontend shields)

---

## DOMAIN PACK CONFIGURATION (Top Right Corner)

Show domain pack structure:
```
📁 Domain Packs/
├── 📁 _default/
│   ├── 📄 pack.yaml (SLA rules, validation config)
│   ├── 📁 evals/ (Evaluation rules)
│   ├── 📁 mappings/ (Data transformation rules)
│   ├── 📁 policy/ (Business policies)
│   └── 📁 validators/ (Custom validation logic)
└── 📁 irr/
    ├── 📄 pack.yaml (Industry-specific config)
    └── 📁 [similar structure]
```

---

## TECHNICAL SPECIFICATIONS (Include as Legend)

### Performance Metrics
- **WebSocket round-trip**: < 150ms on LAN
- **AI response time**: < 45 seconds for spec generation
- **Event processing**: < 100ms for simple events
- **Database query**: < 50ms for typical operations

### Scalability Features
- **Horizontal scaling**: Multiple Flask instances
- **Database connection pooling**: PostgreSQL with pgpool
- **Redis clustering**: High availability setup
- **AI agent load balancing**: Round-robin distribution

### Monitoring & Observability
- **Prometheus metrics**: Performance monitoring
- **Structured logging**: ELK stack integration
- **Health checks**: Automated system monitoring
- **Alerting**: Real-time incident response

---

## VISUAL DESIGN REQUIREMENTS

### Color Scheme
- **External Systems**: Light blue (#E3F2FD)
- **Frontend**: Light green (#E8F5E8)
- **API Gateway**: Yellow (#FFF9C4)
- **Services**: Orange (#FFE0B2)
- **AI Agents**: Purple (#F3E5F5)
- **Domain Logic**: Teal (#E0F2F1)
- **Data Layer**: Dark blue (#E8EAF6)
- **Security Elements**: Red (#FFEBEE)
- **Event Flows**: Colored by workflow type

### Layout Requirements
- **Aspect Ratio**: 16:9 (landscape)
- **Component Spacing**: Consistent 2-inch gaps
- **Font Hierarchy**: Title (24pt), Section headers (18pt), Component labels (12pt)
- **Icon Consistency**: Use consistent icon style throughout
- **Connection Lines**: Curved arrows with labels, avoid crossing lines
- **Legend**: Comprehensive legend explaining all symbols and colors

### Detail Level
- **Component Labels**: Every component clearly labeled
- **Data Flow Labels**: Every arrow labeled with data type/purpose
- **Technology Stack**: Show primary technologies for each layer
- **Scalability Indicators**: Show load balancing and clustering
- **Security Indicators**: Show security checkpoints and encryption

---

## FINAL OUTPUT REQUIREMENTS

1. **High Resolution**: 4K resolution (3840x2160) for clarity
2. **Professional Style**: Enterprise-grade architecture diagram
3. **Clear Labeling**: Every component, connection, and flow clearly labeled
4. **Comprehensive Coverage**: Include all architectural layers and components
5. **Color Coding**: Use consistent color scheme throughout
6. **Scalable Format**: SVG or high-resolution PNG format

The resulting diagram should be a comprehensive, professional-grade system architecture visualization that clearly shows how the Software Factory platform orchestrates AI-powered software development from initial ideas to production deployment.






