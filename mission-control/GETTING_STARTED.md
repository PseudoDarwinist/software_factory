# Getting Started with Mission Control

This guide will help you get Mission Control up and running on your local machine.

## Prerequisites

- Node.js 18+ installed
- npm or yarn package manager

## Installation

1. **Navigate to the Mission Control directory:**
   ```bash
   cd mission-control
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

## Running the Application

1. **Start the development server:**
   ```bash
   npm start
   ```

   This will start both the backend API server (port 5000) and the frontend development server (port 3000) concurrently.

2. **Open your browser and go to:**
   ```
   http://localhost:3000
   ```

## What You'll See

When you first open Mission Control, you'll experience:

### 🎨 **Liquid Glass Aesthetics**
- Breathing health indicators that pulse based on project status
- Morphing cards that respond to content and urgency
- Magnetic field interactions between related elements
- Organic animations with "Jony Ive on acid" visual effects

### 🏗️ **Three-Column Layout**
- **Left Rail**: Projects with breathing health dots
- **Center Feed**: Decision items and untriaged thoughts
- **Right Panel**: Contextual conversation and evidence

### 🔄 **Interactive Features**
- Drag untriaged thoughts to the "Define" stage
- Click on feed items to see detailed context
- Submit prompts to interact with AI agents
- Real-time updates via WebSocket connections

## Architecture Overview

```
mission-control/
├── src/
│   ├── components/          # Reusable UI components
│   │   ├── core/           # LiquidCard, HealthDot, etc.
│   │   └── layout/         # Main layout components
│   ├── pages/              # Main pages
│   ├── services/           # API and external services
│   ├── stores/             # State management
│   ├── styles/             # Design tokens and themes
│   └── types/              # TypeScript definitions
├── server/                 # Backend API server
└── dist/                   # Built application
```

## Key Features Implemented

### ✅ **Revolutionary UI Components**
- **LiquidCard**: Morphing cards with breathing animations
- **HealthDot**: Breathing health indicators with different pulse speeds
- **StageBar**: Liquid glass navigation with drag-and-drop
- **ProjectRail**: Collapsible project sidebar with search
- **FeedColumn**: Smart feed with filtering and magnetic interactions
- **ConversationColumn**: Context-aware conversation panel

### ✅ **State Management**
- Zustand store with clear separation of concerns
- Real-time updates via WebSocket
- Optimistic UI updates
- Type-safe state management

### ✅ **Backend API**
- RESTful endpoints for projects, feed, and conversations
- WebSocket support for real-time updates
- Mock data for development
- Clean API architecture

### ✅ **Design System**
- Comprehensive design tokens
- Liquid glass morphism theme
- Responsive design
- Accessibility features

## Development Scripts

```bash
# Start development server
npm run dev

# Start backend only
npm run server

# Build for production
npm run build

# Run tests
npm test

# Type checking
npm run typecheck

# Linting
npm run lint
```

## Integration with Existing Software Factory

This Mission Control is designed to integrate with your existing:
- **business.html** - Business Analyst interface
- **po.html** - Product Owner interface
- **run_server.py** - Goose AI integration
- **Model Garden** - Multi-LLM capabilities

## Next Steps

1. **Run the application** and explore the liquid glass interface
2. **Try the interactions** - drag items, click feed cards, submit prompts
3. **Customize the design** by modifying tokens in `src/styles/tokens/`
4. **Add real data** by connecting to your actual backend APIs
5. **Extend functionality** by adding new components and features

## Troubleshooting

**Port conflicts?**
- Backend runs on port 5000
- Frontend runs on port 3000
- Change ports in `package.json` and `vite.config.ts`

**Dependencies issues?**
- Delete `node_modules` and `package-lock.json`
- Run `npm install` again

**Build errors?**
- Check TypeScript types in `src/types/`
- Ensure all imports are correct

## Questions?

Check the comprehensive documentation in each component file - every component includes:
- Purpose and why it exists
- How to use it
- Notes for AI agents
- Integration points

The codebase is designed to be AI-agent friendly with clear navigation maps and extensive documentation.

---

**🚀 Ready to experience the future of Software Factory Mission Control!**