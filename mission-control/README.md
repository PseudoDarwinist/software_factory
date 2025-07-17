# Mission Control - Software Factory

The "foyer" of Software Factory - a liquid glass interface that provides 10,000-foot view of all projects and immediate actions needed.

## Architecture Philosophy

**"Jony Ive on Acid"** - Revolutionary UI that feels alive, organic, and intelligent while maintaining absolute clarity.

### Core Principles
- **Liquid Glass Aesthetics**: Elements breathe, morph, and respond to content
- **Separation of Concerns**: Clean architecture with logical boundaries
- **AI-Agent Friendly**: Clear navigation map for both humans and AI
- **Progressive Enhancement**: Start simple, add complexity intelligently

## Project Structure

```
mission-control/
├── README.md                 # This file - project overview and navigation
├── package.json              # Dependencies and scripts
├── src/
│   ├── components/           # Reusable UI components
│   │   ├── core/            # Core UI primitives (buttons, cards, etc.)
│   │   ├── layout/          # Layout components (grid, sidebar, etc.)
│   │   └── features/        # Feature-specific components
│   ├── pages/               # Full page components
│   │   └── MissionControl/  # Main Mission Control page
│   ├── services/            # API and external service integrations
│   │   ├── api/            # Backend API client
│   │   ├── realtime/       # WebSocket/SSE for live updates
│   │   └── ai/             # AI provider integrations
│   ├── stores/              # State management
│   │   ├── projects/       # Project state
│   │   ├── feed/           # Feed state
│   │   └── conversations/  # Conversation state
│   ├── styles/              # Styling and design tokens
│   │   ├── tokens/         # Design system tokens
│   │   ├── themes/         # Theme configurations
│   │   └── components/     # Component-specific styles
│   ├── utils/               # Utility functions
│   │   ├── animations/     # Animation helpers
│   │   ├── formatting/     # Data formatting
│   │   └── validation/     # Input validation
│   └── types/               # TypeScript type definitions
├── server/                  # Backend server
│   ├── routes/             # API route handlers
│   ├── services/           # Business logic services
│   ├── middleware/         # Express middleware
│   └── models/             # Data models
└── docs/                    # Additional documentation
```

## Key Design Decisions

### 1. Component Architecture
- **Core Components**: Basic building blocks (Button, Card, Input)
- **Layout Components**: Structural elements (Grid, Sidebar, Panel)
- **Feature Components**: Business logic components (ProjectList, FeedCard)

### 2. State Management
- **Local State**: React hooks for component-level state
- **Global State**: Context/Zustand for shared state
- **Server State**: React Query for API state management

### 3. Styling Strategy
- **Design Tokens**: Semantic color, spacing, typography tokens
- **Component Styles**: Co-located CSS modules
- **Theme System**: Dark-first with light theme support

### 4. API Design
- **RESTful**: Standard HTTP methods for CRUD operations
- **Real-time**: WebSocket for live updates
- **Type-safe**: Full TypeScript coverage

## Getting Started

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Run tests
npm test

# Build for production
npm run build
```

## For AI Agents

When working on this codebase:

1. **Start Here**: This README provides the complete navigation map
2. **Component Discovery**: Check `src/components/` for reusable elements
3. **API Integration**: Look in `src/services/api/` for backend communication
4. **State Management**: Find global state in `src/stores/`
5. **Styling**: Design tokens in `src/styles/tokens/`

### Common Tasks
- **Add new component**: Create in appropriate `src/components/` subdirectory
- **Add API endpoint**: Create in `server/routes/` with corresponding client in `src/services/api/`
- **Modify styling**: Update tokens in `src/styles/tokens/` or component styles
- **Add new feature**: Create feature directory with components, services, and stores

## Integration Points

This Mission Control will integrate with:
- **Existing Business Interface** (`../business.html`) - For business analyst workflows
- **Existing PO Interface** (`../po.html`) - For product owner workflows
- **Goose AI** (`../run_server.py`) - For code generation
- **Model Garden** - For multi-LLM capabilities

## Next Steps

1. ✅ Project structure setup
2. 🔄 Mission Control UI implementation
3. ⏳ Backend API development
4. ⏳ Real-time updates
5. ⏳ AI agent integration
6. ⏳ Integration with existing interfaces

---

**Why This Structure?**

This architecture enables:
- **Scalability**: Easy to add new features without coupling
- **Maintainability**: Clear separation makes debugging simple
- **Collaboration**: Multiple developers can work without conflicts
- **AI-Friendly**: Clear patterns for AI agents to follow
- **Testing**: Isolated components are easy to test