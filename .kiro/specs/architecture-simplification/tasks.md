# Implementation Plan

- [x] 1. Set up unified Flask application foundation

  - Create new app.py with Flask application factory pattern
  - Set up basic configuration management with environment variables
  - Implement application initialization and teardown handlers
  - _Requirements: 1.1, 1.2, 7.3_

- [x] 2. Implement SQLite database layer with SQLAlchemy

  - Create models.py with all data model classes (Project, SystemMap, BackgroundJob, Conversation)
  - Set up SQLAlchemy configuration and database initialization
  - Implement database migration system for schema updates
  - Create database utility functions for connection management
  - _Requirements: 3.1, 3.2, 3.3_

- [x] 3. Create core API blueprint structure

  - Implement api/projects.py with CRUD operations for projects
  - Create api/system.py with status and health check endpoints
  - Set up proper JSON serialization for database models
  - Add request validation and error handling middleware
  - _Requirements: 4.1, 4.2, 8.1_

- [x] 4. Implement background job management system

  - Create services/background.py with ThreadPoolExecutor-based job manager
  - Implement job status tracking and progress updates in database
  - Add job queue management with proper error handling and recovery
  - Create API endpoints for job status monitoring and control
  - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [x] 5. Port repository processing functionality

  - Create services/repository.py with GitPython-based repository operations
  - Implement repository cloning and analysis within background jobs
  - Port system map generation logic from Node.js worker to Python
  - Add proper error handling and cleanup for repository operations
  - _Requirements: 5.1, 8.2, 9.2_

- [x] 6. Consolidate AI service integrations

  - Create services/ai_service.py with unified AI interfaces
  - Port existing Goose integration from Flask backend
  - Implement Model Garden functionality with consistent error handling
  - Create api/ai.py with AI interaction endpoints
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 8.3_

- [x] 7. Implement status polling system

  - Create comprehensive /api/status endpoint with job progress and system health
  - Add project status tracking with real-time updates via polling
  - Implement efficient database queries for status information
  - Add caching layer for frequently requested status data
  - _Requirements: 4.1, 4.3, 9.1, 9.4_

- [x] 8. Set up static file serving for React frontend

  - Configure Flask to serve React build files from static directory
  - Implement proper MIME type handling and caching headers
  - Add fallback routing for React Router single-page application
  - Set up build integration for frontend assets
  - _Requirements: 1.1, 9.3_

- [x] 9. Update React frontend to remove Socket.IO dependencies

  - Remove all Socket.IO client code and dependencies
  - Implement polling-based status updates using fetch API
  - Create new API client service for REST endpoint communication
  - Update state management to work with polling instead of real-time events
  - _Requirements: 4.1, 4.3, 8.1_

- [x] 10. Document Mission Control architecture and APIs

  - Analyze existing Node.js server structure and API endpoints
  - Document all data structures from dataStore.js and server/index.js
  - Map Socket.IO event flows and real-time communication patterns
  - Catalog React components, dependencies, and state management (Zustand)
  - _Requirements: 8.1, 8.2, 8.3_

- [x] 11. Port Mission Control Node.js APIs to unified Flask

  - Migrate Express routes to Flask blueprints (projects, feed, conversations, stages)
  - Convert Node.js data operations to SQLAlchemy ORM models
  - Replace JSON file storage with SQLite database operations
  - Maintain API compatibility for existing Mission Control React components
  - _Requirements: 4.1, 4.2, 8.1, 8.2_

- [x] 12. Migrate background worker functionality to Python

  - Port ingestionWorker.js repository processing to Python services
  - Integrate worker functionality with existing services/background.py
  - Replace Socket.IO events with database status updates and polling
  - Add Goose integration for repository analysis and system map generation
  - _Requirements: 5.1, 5.2, 5.3, 8.2_

- [x] 13. Serve Mission Control React app from unified Flask

  - Configure unified Flask to serve Mission Control build files
  - Set up proper routing for React Router single-page application
  - Ensure all static assets (CSS, JS, fonts) load correctly from unified server
  - Test Mission Control UI loads and renders from unified Flask application
  - _Requirements: 1.1, 9.3, 8.1_

- [x] 14. Data migration from JSON files to SQLite database

  - Create migration scripts for existing Mission Control data (projects, feed items, conversations)
  - Convert JSON data structures to SQLite schema with proper relationships
  - Preserve all existing project data, artifacts, and system maps
  - Add data validation and cleanup utilities for migration process
  - _Requirements: 3.1, 3.3, 8.1, 8.2_

- [ ] 15. Update Mission Control React to use unified APIs and polling

  - Replace Socket.IO client with REST API calls using fetch/axios
  - Update state management (Zustand) to work with polling instead of real-time events
  - Ensure all React components work with unified backend endpoints
  - Test complete Mission Control functionality (project management, feed system, stages)
  - _Requirements: 4.1, 4.3, 8.1, 8.3_

## Event-Driven Architecture Transformation

- [ ] 16. Implement Redis queue + WebSocket foundation (The Hallway)

  - Set up Redis server connection and configuration management
  - Create event publisher service for publishing domain events (idea.created, spec.frozen, tasks.created, build.failed)
  - Implement event subscriber service with proper error handling and retry logic
  - Add event schema validation and serialization utilities
  - Implement WebSocket server using Flask-SocketIO for real-time frontend communication
  - Create WebSocket event handlers that subscribe to Redis message queue
  - Replace frontend polling with WebSocket event listeners for instant updates
  - Add connection management, reconnection logic, and graceful degradation
  - Test real-time updates: Redis event → WebSocket → UI update
  - _Requirements: Event-driven communication foundation, real-time updates_

- [ ] 17. Migrate to PostgreSQL (Single-hop migration)

  - Set up PostgreSQL database with standard relational schema
  - Create PostgreSQL models matching existing SQLite structure
  - Implement data migration script: SQLite → PostgreSQL (one-time migration)
  - Update SQLAlchemy configuration to use PostgreSQL
  - Test all existing functionality works with PostgreSQL
  - Keep SQLite for local development/testing only
  - _Requirements: Production-ready database, foundation for event storage_

- [ ] 18. Create Docker infrastructure for event-driven services

  - Create Docker Compose setup for PostgreSQL, Redis, and Flask application
  - Set up development environment with hot reload and volume mounting
  - Add Docker networking for secure service-to-service communication
  - Create environment-specific configurations (dev, staging, prod)
  - Test complete stack running in containers with event flow
  - _Requirements: Foundation for multi-service architecture, development efficiency_

- [ ] 19. Add basic monitoring to event queue

  - Implement Redis queue depth monitoring
  - Add API latency metrics collection
  - Create simple log-based metrics for event processing
  - Add basic health check endpoints for Redis and PostgreSQL
  - Test monitoring shows queue stalls and performance issues
  - _Requirements: Event system observability, early problem detection_

- [ ] 20. Create intelligent agent framework with event subscriptions

  - Implement base agent class that can subscribe to specific event types
  - Create Capture agent that reacts to idea.created events for processing
  - Build Define agent that triggers on spec.frozen events for automatic processing
  - Add simple event-driven workflow: idea.created → capture → define → tasks.created
  - Test agent coordination and prevent infinite event loops
  - _Requirements: Reactive agents, automated workflow orchestration_

- [ ] 21. Implement external system integration via webhooks and events

  - Create webhook receiver service for GitHub, CI/CD, and other external systems
  - Implement webhook-to-event translation for external system notifications
  - Add outbound webhook system for notifying external systems of internal events
  - Create integration adapter for GitHub (webhook → event bus)
  - Test bidirectional integration with GitHub webhooks
  - _Requirements: External system integration, webhook-based communication_

- [ ] 22. Build AI broker service for model orchestration

  - Create AI broker service that manages multiple AI model connections (Goose, Gemini, Claude)
  - Implement model selection logic based on task type and context requirements
  - Add AI request queuing and load balancing across available models
  - Create context management system that provides relevant information to AI calls
  - Test AI broker with different model types and concurrent requests
  - _Requirements: Intelligent model selection, context-aware AI interactions_

- [ ] 23. Add graph extensions when needed (Feature-driven)

  - Identify specific use case requiring graph queries (e.g., "jump from idea to all related commits")
  - Add PostgreSQL graph extensions (pg_graph or similar) only if relational queries are insufficient
  - Create graph schema for identified relationships
  - Implement graph query service for specific use case
  - Test complex queries like "Show every pull request that fulfils the 'gate-change' spec"
  - _Requirements: Complex relationship queries (when needed)_

- [ ] 24. Add vector database when needed (Feature-driven)

  - Identify specific use case requiring semantic search (e.g., "find similar paragraphs for Claude context")
  - Set up pgvector in PostgreSQL for unified database
  - Implement document chunking and embedding generation for identified use case
  - Create semantic search service for specific functionality
  - Test semantic search for identified use case
  - _Requirements: Semantic search and AI context (when needed)_

- [ ] 25. Implement distributed caching and session management

  - Set up Redis-based distributed caching for frequently accessed data
  - Implement session management for multi-user concurrent access
  - Add cache invalidation strategies based on domain events
  - Create cache warming mechanisms for predictive data loading
  - Test cache performance and consistency across multiple application instances
  - _Requirements: Performance optimization, multi-user support_

- [ ] 26. Expand monitoring and observability system

  - Implement distributed tracing for event flows and AI interactions
  - Add metrics collection for event processing, database queries, and AI response times
  - Expand health check endpoints for all system components (Redis, PostgreSQL, AI services)
  - Build monitoring dashboard for system health, event throughput, and performance metrics
  - Test monitoring system under load and failure scenarios
  - _Requirements: System observability, performance monitoring_

- [ ] 27. Integrate advanced AI capabilities with event context

  - Implement context-aware AI that uses available data (PostgreSQL + Redis) for enhanced responses
  - Create AI agents that can analyze code changes and predict impact across the system
  - Add intelligent code review agent that triggers on pull.request.created events
  - Implement AI-powered project health monitoring with predictive alerts
  - Test AI accuracy and response quality with available contextual information
  - _Requirements: Context-aware AI, predictive intelligence_

- [ ] 28. Build intelligent project analysis and recommendation engine

  - Implement project analysis using PostgreSQL relational queries (add graph later if needed)
  - Create recommendation engine that suggests related projects, code patterns, and team connections
  - Add intelligent project categorization based on code analysis and team activity
  - Implement trend analysis for technology adoption and project success patterns
  - Test recommendation accuracy and performance with real project data
  - _Requirements: Intelligent recommendations, project insights_

- [ ] 29. Implement event-driven testing and validation framework

  - Create event-driven test harness that can simulate complex event sequences
  - Implement integration tests for event flows and agent interactions
  - Add chaos testing for event system resilience and recovery
  - Create performance tests for event throughput and latency under load
  - Test complete event-driven workflows from external trigger to final outcome
  - _Requirements: Event system reliability, comprehensive testing_

- [ ] 30. Create event-driven deployment and scaling system

  - Implement container orchestration with event-driven scaling triggers
  - Create deployment pipeline that reacts to code.merged events for automated deployments
  - Add resource monitoring that triggers scaling events based on load patterns
  - Implement blue-green deployment strategy with event-driven cutover
  - Test automated scaling and deployment under various load conditions
  - _Requirements: Automated deployment, event-driven scaling_

- [ ] 31. Final event-driven system integration and performance optimization

  - Integrate all event-driven components into cohesive system architecture
  - Optimize event processing performance and reduce latency across the system
  - Implement comprehensive error recovery and system resilience mechanisms
  - Create production deployment scripts and monitoring for event-driven architecture
  - Test complete system under production-like load with multiple concurrent users and agents
  - _Requirements: System integration, production readiness, performance optimization_

## Robustness and Production Readiness

- [ ] 32. Implement comprehensive error handling and logging

  - Set up centralized error handling with proper HTTP status codes
  - Create unified logging system with structured log formatting
  - Add error recovery mechanisms for background jobs
  - Implement graceful shutdown handling for all components
  - _Requirements: 2.1, 2.2, 2.3, 5.4_

- [ ] 33. Add comprehensive testing suite

  - Create unit tests for all database models and API endpoints
  - Implement integration tests for background job processing
  - Add end-to-end tests for complete user workflows
  - Create performance tests for concurrent operations and database queries
  - _Requirements: 2.3, 9.1, 9.4, 10.3_

- [ ] 34. Implement configuration management and deployment setup

  - Create environment-based configuration system with validation
  - Set up Docker containerization for event-driven deployment
  - Implement health check endpoints for monitoring and load balancing
  - Add startup scripts and process management utilities
  - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [ ] 35. Performance optimization and monitoring

  - Implement database query optimization and indexing
  - Add request/response timing and performance metrics
  - Create memory usage monitoring for background jobs
  - Implement connection pooling and resource management
  - _Requirements: 9.1, 9.2, 9.3, 9.4_

- [ ] 36. Final integration and cutover preparation
  - Integrate all components and test complete system functionality
  - Create deployment scripts and documentation for production cutover
  - Implement data migration procedures from existing system
  - Add rollback procedures and system monitoring for production deployment
  - _Requirements: 1.1, 7.4, 8.1, 8.2, 8.3, 8.4_
