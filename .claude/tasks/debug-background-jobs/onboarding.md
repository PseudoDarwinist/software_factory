# Task Onboarding: Debug Background Jobs Issue

## Current Situation Analysis

### Problem Statement
The user is experiencing issues with background jobs in their Software Factory application. Specifically:
1. Background jobs appear to be stuck in "pending" status
2. Mission Control dashboard shows projects with system map status "pending"
3. Repository processing jobs are not completing
4. Docker services are not running (PostgreSQL dependency issue)

### Context from Previous Session
From the conversation history, I understand that:
1. **Architecture Refactor Completed**: The system was successfully refactored from a dual project system (Regular Projects + Mission Control Projects) to a unified Mission Control Project system
2. **Clean Slate Reset**: All test data was wiped and the system was reset
3. **Unified Project System**: The codebase now uses only `MissionControlProject` model
4. **Background Jobs**: There's a background job system that processes repository analysis

### Current Technical Stack
- **Backend**: Python Flask with SQLAlchemy
- **Database**: PostgreSQL with pgvector extension
- **Cache/Queue**: Redis for event bus and caching
- **Frontend**: React TypeScript (Mission Control) + Vanilla JS interfaces
- **Containerization**: Docker Compose for services

### Key Files and Components

#### Database Models
- `src/models/mission_control_project.py` - Unified project model
- `src/models/background_job.py` - Background job tracking
- `src/models/system_map.py` - System mapping data
- `src/models/conversation.py` - Chat/conversation data

#### Services
- `src/services/background.py` - Background job manager
- `src/services/repository.py` - Repository processing service
- `src/app.py` - Main Flask application

#### APIs
- `src/api/mission_control.py` - Mission Control project management
- `src/api/webhooks.py` - External integrations (Slack, GitHub, etc.)

### Current Issues Identified

#### 1. Docker Services Not Running
```bash
docker-compose ps
# Error: Cannot connect to the Docker daemon
```
This means PostgreSQL and Redis services are not available.

#### 2. Database Connection Issues
The app expects PostgreSQL but services aren't running:
- Default DATABASE_URL: `postgresql://sf_user:sf_password@localhost/software_factory`
- Redis URL: `redis://localhost:6379/0`

#### 3. Background Job Status Check Failures
Scripts like `check_jobs.py` are failing due to:
- Flask-SQLAlchemy context issues
- Import path problems after refactor
- Database connection failures

### Root Cause Analysis

The primary issue appears to be **infrastructure dependency failure**:
1. Docker daemon is not running
2. PostgreSQL service is not available
3. Redis service is not available
4. Background jobs cannot process without database connectivity
5. Repository analysis jobs are stuck because they can't connect to services

### Immediate Action Plan

#### Phase 1: Infrastructure Setup
1. **Start Docker Services**
   ```bash
   # Start Docker daemon
   # Run: docker-compose up -d postgresql redis
   ```

2. **Verify Database Connectivity**
   - Check PostgreSQL is accessible
   - Verify tables exist and are properly migrated
   - Test Redis connectivity

#### Phase 2: Background Job System Diagnosis
1. **Check Job Queue Status**
   - Identify stuck jobs
   - Clear failed/orphaned jobs if needed
   - Restart job processing

2. **Repository Processing Analysis**
   - Verify repository service can connect to external APIs
   - Check if GitHub/external integrations are working
   - Test repository analysis workflow

#### Phase 3: System Validation
1. **End-to-End Testing**
   - Create a test project
   - Trigger repository processing
   - Verify system map generation
   - Confirm Mission Control UI updates

### Key Questions for User
1. **Docker Environment**: Do you have Docker Desktop running? Can you start it?
2. **Database Preference**: Would you prefer to use PostgreSQL (requires Docker) or switch to SQLite for local development?
3. **External Dependencies**: Are there any network restrictions that might block GitHub API calls or other external services?
4. **Priority**: What's the most important thing to fix first - the background jobs or the overall system health?

### Success Criteria
- [ ] Docker services running (PostgreSQL + Redis)
- [ ] Database tables properly created and accessible
- [ ] Background job system processing jobs successfully
- [ ] Repository analysis completing without errors
- [ ] Mission Control UI showing correct project status
- [ ] System map generation working end-to-end

### Files to Monitor/Fix
- `check_jobs.py` - Fix Flask context and import issues
- `src/services/background.py` - Ensure job processing is working
- `src/services/repository.py` - Verify repository analysis logic
- `docker-compose.yml` - Ensure services are properly configured
- `.env` - Verify environment variables are correct

## Next Steps
1. Start with infrastructure (Docker services)
2. Create reliable diagnostic tools
3. Fix background job processing
4. Validate end-to-end workflow