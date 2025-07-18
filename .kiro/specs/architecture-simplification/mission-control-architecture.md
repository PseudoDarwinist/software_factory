# Mission Control Architecture Documentation

## Overview

Mission Control is a sophisticated React/TypeScript application that provides a "liquid glass" command center interface for the Software Factory SDLC platform. It features real-time project management, feed systems, AI-powered conversations, and stage-based workflow orchestration.

## Current Architecture (3-Server Setup)

### 1. Node.js Express Server (`mission-control/server/index.js`)
**Port**: 5001  
**Purpose**: REST API and Socket.IO hub for real-time communication

#### API Endpoints
- **Health**: `GET /api/health` - Server health check
- **Projects**: 
  - `GET /api/projects` - List all projects
  - `GET /api/projects/:id` - Get specific project
  - `POST /api/projects` - Create new project (triggers ingestion)
  - `DELETE /api/projects/:id` - Delete project
  - `GET /api/projects/:id/system-map` - Get project system map
  - `POST /api/projects/docs` - Upload project documents
- **Feed System**:
  - `GET /api/feed` - Get feed items (with filtering)
  - `POST /api/feed/:id/mark-read` - Mark feed item as read
  - `POST /api/feed/:id/action` - Perform action on feed item
  - `POST /api/feed/import` - Import external feed items
- **Conversations**:
  - `GET /api/conversation/:feedItemId` - Get conversation for feed item
  - `POST /api/conversation/:feedItemId/prompt` - Submit AI prompt
- **SDLC Stages**:
  - `POST /api/idea/:id/move-stage` - Move item between stages
  - `GET /api/project/:projectId/stages` - Get stage data for project
- **Product Briefs**:
  - `GET /api/product-brief/:briefId` - Get product brief
  - `PUT /api/product-brief/:briefId` - Update product brief
  - `POST /api/product-brief/:briefId/freeze` - Freeze product brief
- **Channel Mapping**:
  - `GET /api/channel-mapping/:channelId` - Get project for channel
  - `POST /api/channel-mapping` - Create channel mapping

#### Socket.IO Events
**Outgoing Events** (Server → Client):
- `feed.update` - Feed item updated
- `feed.new` - New feed item created
- `conversation.update` - Conversation updated
- `project.update` - Project updated
- `project.indexed` - Project indexing complete
- `project.docs.indexed` - Document indexing complete
- `stage.moved` - Item moved between stages
- `brief.updated` - Product brief updated
- `brief.frozen` - Product brief frozen

**Incoming Events** (Client → Server):
- `project.created` - New project created (triggers ingestion)
- `project.docs.uploaded` - Documents uploaded (triggers processing)

### 2. Background Ingestion Worker (`mission-control/worker/ingestionWorker.js`)
**Purpose**: Repository processing and system map generation

#### Responsibilities
- Clone repositories from GitHub URLs
- Generate system maps using file system analysis
- Integrate with Goose AI for code analysis (planned)
- Emit progress events via Socket.IO
- Persist artifacts in `mission-control/artifacts/` directory

#### Event Flow
1. Server emits `project.created` event
2. Worker receives event and starts processing
3. Worker clones repository to temp directory
4. Worker generates basic system map (enhanced Goose integration pending)
5. Worker saves system map to artifacts directory
6. Worker updates project metadata in dataStore
7. Worker emits `project.indexed` event back to server

### 3. React Frontend (`mission-control/src/`)
**Port**: 5173 (Vite dev server)  
**Purpose**: Interactive UI with liquid glass aesthetics

## Data Architecture

### Data Store (`mission-control/server/dataStore.js`)
**Storage**: JSON file (`mission-control/server/data.json`)

#### Data Structure
```javascript
{
  projects: ProjectSummary[],
  feedItems: FeedItem[],
  conversations: Record<string, ConversationPayload>,
  stages: Record<projectId, Record<stage, itemIds[]>>,
  productBriefs: Record<briefId, ProductBrief>,
  stageTransitions: StageTransition[],
  channelMappings: Record<channelId, projectId>
}
```

#### Key Data Types
- **ProjectSummary**: Project metadata, health status, activity tracking
- **FeedItem**: SDLC events with severity, kind, and metadata
- **ConversationPayload**: AI conversation blocks and context
- **ProductBrief**: Detailed product specifications with user stories
- **StageTransition**: SDLC stage movement history

### Data Persistence
- **JSON File Storage**: All data persisted to `data.json` 
- **Race Condition Risk**: Multiple processes can corrupt data
- **Backup Strategy**: None implemented
- **Migration Support**: None implemented

## Frontend Architecture

### State Management (Zustand)
**Store**: `mission-control/src/stores/missionControlStore.ts`

#### State Structure
```typescript
interface MissionControlState {
  // Data
  projects: ProjectSummary[]
  feedItems: FeedItem[]
  conversation: ConversationPayload | null
  
  // UI State
  ui: UIState
  loading: LoadingState
  errors: ErrorState
  notifications: SystemNotification[]
  
  // Actions
  actions: { /* 20+ action methods */ }
}
```

#### Key Features
- **Optimistic Updates**: UI updates before server confirmation
- **Real-time Sync**: Socket.IO events update state automatically
- **Error Handling**: Comprehensive error state management
- **Loading States**: Granular loading indicators

### Component Architecture
**Layout Pattern**: Compound components with clear responsibilities

#### Main Layout (`MissionControlLayout.tsx`)
- **ProjectRail**: Left sidebar with project list
- **FeedColumn**: Center column with feed items
- **ConversationColumn**: Right column with AI conversations
- **StageBar**: Top navigation for SDLC stages

#### Key Components
- **LiquidCard**: Reusable glass-morphism card component
- **HealthDot**: Project health indicator with animations
- **AddProjectModal**: Project creation with GitHub integration
- **DefineStage**: SDLC stage management with drag-and-drop

### API Client (`missionControlApi.ts`)
**Pattern**: Singleton service with type-safe methods

#### Features
- **Axios Integration**: HTTP client with interceptors
- **Error Handling**: Automatic retry and error transformation
- **Socket.IO Management**: Real-time connection handling
- **Type Safety**: Full TypeScript coverage

## Real-time Communication

### Socket.IO Event Flow
1. **Client Connection**: React app connects to Express server
2. **Event Subscription**: Client subscribes to relevant events
3. **Server Events**: Background processes emit events
4. **State Updates**: Client updates Zustand store
5. **UI Rendering**: React components re-render automatically

### Event Types
- **Data Updates**: `feed.update`, `project.update`
- **New Data**: `feed.new`, `conversation.update`
- **Process Events**: `project.indexed`, `stage.moved`
- **System Events**: `brief.updated`, `brief.frozen`

## Dependencies

### Backend Dependencies
```json
{
  "express": "^4.21.2",
  "socket.io": "^4.8.1",
  "socket.io-client": "^4.6.1",
  "cors": "^2.8.5",
  "simple-git": "^3.22.0"
}
```

### Frontend Dependencies
```json
{
  "react": "^18.2.0",
  "react-router-dom": "^6.8.0",
  "zustand": "^4.3.6",
  "axios": "^1.3.4",
  "socket.io-client": "^4.6.1",
  "framer-motion": "^10.0.1",
  "react-dnd": "^16.0.1",
  "react-query": "^3.39.3",
  "@react-three/fiber": "^8.12.0",
  "three": "^0.150.1"
}
```

### Build Tools
- **Vite**: Frontend build tool and dev server
- **TypeScript**: Type safety and IDE support
- **ESLint**: Code linting and formatting
- **Concurrently**: Multi-process development

## Current Problems

### 1. **Multi-Server Complexity**
- 3 separate processes (Express + Worker + Vite)
- Complex port management (5001 + 5173 + worker)
- Difficult debugging across processes
- Deployment complexity

### 2. **Data Consistency Issues**
- JSON file-based storage with race conditions
- No transaction support
- No backup/restore mechanisms
- Schema migration challenges

### 3. **Socket.IO Reliability**
- Event ordering not guaranteed
- Connection drops cause state inconsistency
- No event replay or persistence
- Complex error recovery

### 4. **Development Workflow**
- Requires multiple terminal windows
- Complex startup dependencies
- Hot reload issues across processes
- Difficult to mock/test real-time features

## Migration Strategy

### Phase 1: Port Node.js APIs to Flask
- Migrate all Express routes to Flask blueprints
- Maintain exact API compatibility
- Convert dataStore operations to SQLAlchemy
- Preserve all Socket.IO event contracts

### Phase 2: Replace Socket.IO with Polling
- Implement `/api/status` endpoint with comprehensive data
- Add polling-based state synchronization
- Remove Socket.IO dependencies from React app
- Maintain real-time feel through efficient polling

### Phase 3: Serve React App from Flask
- Configure Flask to serve Vite build files
- Set up SPA routing fallbacks
- Integrate build process with Flask deployment
- Test all static assets load correctly

### Phase 4: Data Migration
- Convert JSON data to SQLite schema
- Implement data migration scripts
- Add proper relationships and constraints
- Test data integrity throughout migration

### Phase 5: Background Job Integration
- Port ingestion worker to Python
- Integrate with existing Flask background job system
- Replace Socket.IO events with database updates
- Test repository processing and system map generation

## Success Criteria

### ✅ **Functional Parity**
- All existing features work identically
- No degradation in user experience
- All API endpoints maintain compatibility
- Real-time updates continue working

### ✅ **Simplified Architecture**
- Single Python process (`python app.py`)
- Single database (SQLite)
- Single language (Python backend)
- Single deployment artifact

### ✅ **Enhanced Reliability**
- Eliminate race conditions
- Improve error handling
- Add data backup/restore
- Implement proper logging

### ✅ **Better Developer Experience**
- One command startup
- Simplified debugging
- Easier testing
- Clear deployment process

## Integration Points

### Current Flask App Integration
- Mission Control will be served from unified Flask app
- AI services (Goose + Model Garden) will be accessible
- Background job system will handle repository processing
- SQLite database will store all Mission Control data

### Existing Interface Integration
- Business interface (`business.html`) - already working
- Product Owner interface (`po.html`) - already working
- Dashboard (`dashboard.html`) - already working
- Mission Control will be accessible at `/mission-control`

## Next Steps (Steps 11-15)

1. **Step 11**: Port Mission Control APIs to Flask blueprints
2. **Step 12**: Migrate background worker to Python
3. **Step 13**: Serve React app from unified Flask
4. **Step 14**: Data migration from JSON to SQLite
5. **Step 15**: Update React app to use polling instead of Socket.IO

This architecture documentation provides the complete understanding needed to successfully migrate Mission Control to the unified Flask application while preserving all functionality and enhancing reliability.