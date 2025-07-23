# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Software Factory is a comprehensive software development lifecycle (SDLC) platform that revolutionizes how teams build production-quality products. This project creates a sophisticated marketing website showcasing the platform's capabilities with advanced glass-morphism design effects.

### What is Software Factory?

Software Factory is an AI-native system that unifies the entire software development lifecycle from PRD to production. Unlike traditional tools that create endless sprawl across multiple SaaS platforms, Software Factory provides:

**Core Value Proposition:**

- Keeps product and code in sync across the entire SDLC
- Enables teams to build like a multi-person team with the clarity of one
- Automates key SDLC components into one simple workflow
- Works horizontally across PRD → Eng Plan → GitHub Issues → QA → Production

**Key Benefits:**

1. **Unified Workflow**: Replaces multiple SaaS tools with one asynchronous, AI-native system
2. **Role Orchestration**: Dedicated spaces for Product Managers, Engineering Managers, Developers, and QA
3. **Knowledge Graph**: Makes product evolution effortless with instant onboarding for new team members
4. **10x Effectiveness**: Makes all experts more effective through intelligent automation

**Target Users:**

- Solo PM-Developers building complex products
- Small to large teams needing organized SDLC processes
- Teams wanting to write quality requirements, build thorough engineering plans, extract detailed tickets, write quality code, and QA thoroughly
- Organizations looking to automate repetitive SDLC tasks while maintaining quality

The platform is designed for complex environments while working elegantly for new projects, enabling teams to ship durable products quickly without missing opportunities.

## Software Factory + JACoB Integration Roadmap

### Vision: Rapid Prototyping SDLC Pipeline

Software Factory integrates with JACoB (Just Another Coding Bot) to create an revolutionary AI-native development pipeline where **every stage produces interactive prototypes instead of documents**, eliminating details lost in translation between roles.

### Core Workflow Architecture

**Stage 1: Business → PO (Interactive Prototype Handoff)**

- Business describes requirements in natural language
- JACoB generates interactive wireframe/prototype users can click through
- Business refines by interacting with actual prototype
- Handoff: Working prototype with clear functionality, not just words

**Stage 2: PO → Designer (MVP Prototype + Linear Integration)**

- PO takes Business prototype and adds detailed requirements
- JACoB creates more detailed MVP prototype with user flows
- **Linear API Integration**: Automatically generates user story tickets
- Handoff: Detailed MVP prototype + structured Linear tickets

**Stage 3: Designer → Developer (Design Assets)**

- **Path A - AI Designer**: JACoB calls GPT-4o to generate pixel-perfect designs from MVP prototype
- **Path B - Human Designer**: Upload Figma designs, JACoB validates against prototype context
- Handoff: Final designs + original prototype context + Linear tickets

**Stage 4: Developer Agent (Code Generation)**

- JACoB Developer Agent takes designs + prototype + Linear tickets
- Generates complete code, tests, and documentation
- Creates GitHub PR with full implementation
- Human developer reviews actual working code against original Business prototype

### Technical Integration Strategy

**Integration Architecture:**

```
Software Factory Frontend (Glass-morphism UI)
├── Role-based Dashboards
├── JACoB tRPC API Client
└── Unified Prototype Management

JACoB Backend Service
├── Interactive Prototype Generator
├── AI Design Engine (GPT-4o integration)
├── Linear API Integration
├── GitHub/Figma Integration
└── Developer Code Agent
```

**Implementation Phases:**

**Phase 1: Foundation Integration**

- Set up JACoB as microservice alongside Software Factory
- Create tRPC client for JACoB APIs in our frontend
- Implement authentication bridge between systems
- Basic role-based JACoB access integration

**Phase 2: Prototype Pipeline**

- Interactive prototype generation for Business role
- MVP prototype refinement for PO role
- Linear tickets auto-generation integration
- Prototype version control and handoff system

**Phase 3: AI Design & Development**

- GPT-4o integration for automated design generation
- Figma design validation against prototypes
- Enhanced JACoB Developer Agent integration
- GitHub PR automation with prototype context

**Phase 4: Enterprise Features**

- Human approval gates at each stage
- Prototype-to-production traceability
- Enterprise security and compliance features
- Advanced workflow customization

### Key Benefits

**Eliminates Translation Loss:**

- Every handoff uses interactive prototypes instead of documents
- Context preserved throughout entire SDLC
- Reduces miscommunication between roles

**Rapid Iteration:**

- Change prototype → downstream updates automatically
- Real-time collaboration with AI assistance
- Faster feedback loops at every stage

**Enterprise Flexibility:**

- Human intervention possible at any stage
- Maintains quality control for complex enterprise requirements
- Scalable from solo developers to large teams

**Unified Workflow:**

- Single platform replacing multiple SaaS tools
- AI-native but human-supervised
- Clear accountability and progress tracking

### Technical Requirements

**JACoB Enhancements Needed:**

1. Interactive prototype generation capabilities
2. Linear API integration for ticket management
3. GPT-4o integration for AI design generation
4. Prototype version control system
5. Enhanced context preservation between stages

**Software Factory Integration Points:**

1. Role-specific JACoB workflow interfaces
2. Prototype management and approval system
3. Real-time collaboration features
4. Enterprise authentication and security
5. Progress tracking and analytics dashboard

### UI/UX Design Philosophy: Flow-First with Liquid Glass Aesthetics

**Design Vision:**
Software Factory pioneers a **flow-first approach** over component-first thinking, enabling Business users to create complete user journeys rather than isolated components. The interface draws inspiration from Apple's revolutionary Liquid Glass design language (WWDC 2025) while maintaining our signature green glass-morphism aesthetic.

**Core Design Principles:**

**1. Flow-Centric Interface**

- Business users start with **user journey mapping** not component creation
- Visual flow diagrams showing complete business processes
- Each interaction creates context for downstream roles
- JACoB translates flows into interactive prototypes

**2. Liquid Glass Implementation**

- **Translucent Materials**: Real-time rendering with specular highlights
- **Dynamic Adaptation**: Interface responds to content and user context
- **Fluid Interactions**: Seamless transitions between flow states
- **Layered Depth**: Multiple glass layers create visual hierarchy
- **Intelligent Transparency**: Adjusts opacity based on content readability

**3. Software Factory Green Palette Integration**

- **Primary Glass**: `rgba(150, 179, 150, 0.15)` with dynamic highlights
- **Active States**: Enhanced green luminosity with liquid reflections
- **Flow Connections**: Animated liquid glass conduits between nodes
- **Depth Shadows**: Soft green glows creating spatial relationships

**4. Business User Experience**

- **Journey Canvas**: Central workspace for flow creation
- **Contextual Panels**: Left (user types), Right (business rules), Bottom (AI assistant)
- **Interactive Prototyping**: JACoB generates clickable flows in real-time
- **Validation Framework**: Test complete user journeys before handoff

**5. JACoB Integration Touch Points**

- **Flow Analysis**: JACoB suggests missing steps or optimizations
- **Prototype Generation**: Automatic creation of interactive wireframes
- **Business Logic Capture**: Natural language to technical requirements
- **Stakeholder Handoffs**: Context-preserved transfers between roles

This approach eliminates the traditional problem of "lost in translation" by maintaining a single, evolving prototype throughout the entire SDLC, with JACoB serving as the intelligent bridge between business intent and technical implementation.

## Architecture

The project has evolved from a simple static website to a comprehensive AI-native SDLC platform with role-based interfaces:

### Core Platform Files

- **index.html** - Main marketing homepage with hero section and feature showcase
- **styles.css** - Base styling with advanced glass-morphism effects
- **dashboard.html** - Central hub with role-based navigation

### Role-Based Interfaces (Operational)

- **business.html** - Business Analyst interface with dual AI providers
- **business.js** - Business logic and AI integration
- **business.css** - Glass-morphism styling for business interface
- **po.html** - Product Owner interface with factory.ai-inspired UX
- **po.js** - Document generation and management logic
- **po.css** - Dark theme styling inspired by factory.ai interface

### AI Integration Backend

- **run_server.py** - Enhanced Flask server with dual AI provider support:
  - `/api/goose/execute` - Goose AI with repository awareness
  - `/api/model-garden/execute` - Enterprise LLM proxy integration
  - Static file serving with automatic port detection

### AI Configuration

- **/.config/goose/config.yaml** - Goose configuration with MCP extensions:
  - Filesystem access for repository analysis
  - GitHub API integration for repository operations
  - Developer toolkit and MCP servers enabled

### Development Tools

- **test_model_display.html** - Testing utility for AI provider functionality
- **save_images.py** - Image placeholder generation
- **replace_images.py** - Asset replacement utility

## Development Commands

### Local Development

```bash
# Start the AI-powered Software Factory platform
python3 run_server.py

# The server provides:
# - Marketing homepage at http://localhost:PORT/
# - Dashboard at http://localhost:PORT/dashboard.html
# - Business interface at http://localhost:PORT/business.html
# - Product Owner interface at http://localhost:PORT/po.html
# - API endpoints for Goose and Model Garden integration

# Test AI model functionality
open test_model_display.html

# Test image assets
python3 replace_images.py
```

### Key CSS Architecture Patterns

1. **Hero Section Effects**: Uses layered CSS backgrounds with grid patterns, radial gradients, and architectural lighting effects
2. **Neon Button**: Custom glowing button with radial gradients and multiple box-shadows for depth
3. **Glass-morphism Cards**: Semi-transparent backgrounds with backdrop-filter blur effects
4. **Text Highlighting**: Pill-shaped highlight tags with subtle green glass-morphism styling
5. **Responsive Design**: Mobile-first approach with grid layouts that collapse to single columns

## Design System

- **Colors**: Green glass-morphism theme with rgba(150, 179, 150, x) variations
- **Typography**: System fonts with CSS gradient text effects for hero content
- **Layout**: CSS Grid for main sections, Flexbox for internal alignment
- **Effects**: Backdrop-filter, box-shadow, and CSS gradients for visual depth

## Development Philosophy

Since Software Factory is about **unifying workflows and eliminating tool sprawl**, our codebase must exemplify those same principles:

### Core Architectural Principles

1. **Lean & Modular Architecture**

   - Each component serves a specific, single purpose
   - No redundant or overlapping functionality
   - Clean separation between presentation, logic, and data
   - Easy to add new features without bloating existing code

2. **Clear Separation of Concerns**

   - CSS organized by component/feature, not mixed responsibilities
   - JavaScript modules focused on single responsibilities
   - HTML structure semantic and purpose-driven
   - Business logic separated from presentation

3. **Unified Design System**

   - Consistent glass-morphism patterns across all components
   - Reusable CSS classes and CSS custom properties
   - Standardized spacing, colors, and effects
   - Component-based approach for scalability

4. **Scalable Structure**
   - Easy to add role-specific features (Business, PO, Designer, Developer)
   - Components that evolve with the platform requirements
   - Maintainable code that new developers can understand quickly
   - Future-proof architecture for SDLC integrations

### Feature Development Guidelines

When building new features (dashboards, workflows, integrations):

- Build as focused, reusable modules
- Integrate seamlessly without tight coupling
- Follow the established glass-morphism design patterns
- Maintain role-based component organization
- Ensure each feature demonstrates Software Factory's core values: organized, efficient, unified

## 🚀 UNIFIED ARCHITECTURE - MIGRATION COMPLETED

**CRITICAL UNDERSTANDING FOR ALL AI AGENTS**: This is now a UNIFIED Flask application. There is NO separate Node.js server.

### **CURRENT UNIFIED ARCHITECTURE**

- **Single Flask Server**: One `python app.py` command on port 8000
- **Flask serves EVERYTHING**: APIs, WebSockets, AND the Mission Control frontend
- **Single Process**: No separate Node.js servers exist
- **Built Frontend**: Mission Control React app is built and served by Flask from `/mission-control-dist`

### **DEPLOYMENT ARCHITECTURE**

```
Flask Server (port 8000) - THE ONLY SERVER
├── API Endpoints (/api/*)
├── Socket.IO WebSockets (/socket.io/*)
├── Mission Control Frontend (/) - served from mission-control-dist/
└── Static Assets (/static/*)
```

### **DEVELOPMENT vs PRODUCTION**

- **Development**: Mission Control runs on Vite dev server (port 5175) with proxy to Flask (port 8000)
- **Production**: Flask serves the built Mission Control from `mission-control-dist/`

### **CRITICAL RULES FOR AI AGENTS**

1. **NEVER assume separate Node.js servers exist**
2. **ALL API calls go to Flask on port 8000**
3. **ALL WebSocket connections go to Flask on port 8000**
4. **Mission Control frontend is served BY Flask, not a separate server**
5. **Only ONE server process runs: Flask**

### **How to Run the Complete System**

```bash
cd src && python app.py  # Starts EVERYTHING on port 8000
```

**NO OTHER SERVERS NEEDED. Flask handles APIs, WebSockets, and frontend serving.**

## Implementation Progress

### ✅ Completed Features

**1. Dual AI Provider Integration**

- **Goose AI**: Repository-aware coding assistant with MCP extensions
- **Model Garden**: Enterprise LLM proxy with multiple models (Claude Opus 4, Gemini 2.5 Flash, GPT-4o, Claude Sonnet 3.5)
- **Smart Model Attribution**: Displays correct model names in responses
- **Persistent Provider Selection**: Saves user preferences across sessions

**2. Business Analyst Interface (business.html)**

- Glass-morphism design with liquid glass aesthetics
- Dual AI provider selection with model switching
- Business context management and GitHub repository integration
- Clean chat interface with enhanced prompting for quality responses

**3. Product Owner Interface (po.html)**

- **Factory.ai-inspired UX**: Clean, document-focused interface
- **Document Card System**: PRD/BRD generation with clickable cards
- **Split-screen Layout**: Chat on left, document viewer on right
- **Smart Document Detection**: Auto-detects and formats PRD/BRD content
- **Dark Theme**: Professional dark interface matching modern AI tools
- **Intelligent Prompting**: Creates actual deliverables instead of asking endless questions

**4. Enhanced Backend (run_server.py)**

- Flask server replacing simple HTTP server
- Dual API endpoints: `/api/goose/execute` and `/api/model-garden/execute`
- Company LLM proxy integration with proper authentication
- Goose output cleaning and context enhancement
- GitHub repository support for repository-aware assistance

**5. AI Configuration & Extensions**

- Goose configured with filesystem and GitHub MCP extensions
- Repository analysis and file manipulation capabilities
- Developer toolkit integration for enhanced coding assistance

### 🎯 Key UX Improvements

**Problem Solved: Verbose AI Responses**

- **Before**: AI would ask endless questions or provide generic templates
- **After**: AI creates actual deliverables with reasonable assumptions
- **Inspiration**: Factory.ai's clean document card approach

**Clean Document Management**

- **Document Cards**: Visual cards showing generated PRD/BRD documents
- **Clickable Interface**: Cards expand to show full formatted content
- **Professional Presentation**: Clean, minimal interface focusing on deliverables
- **Split-screen View**: Automatic document panel for viewing generated content

**Smart Context Enhancement**

- **Greeting Detection**: Simple greetings get natural responses
- **Document Requests**: Automatically creates professional deliverables
- **Quality Control**: Prevents hallucination while maintaining usefulness

### 🚧 Technical Architecture

**Frontend Structure:**

```
Software Factory Platform
├── Marketing Site (index.html)
├── Role Dashboard (dashboard.html)
├── Business Interface (business.html + business.js + business.css)
└── Product Owner Interface (po.html + po.js + po.css)
```

**Backend Integration:**

```
Flask Server (run_server.py)
├── Static File Serving
├── Goose AI Integration (/api/goose/execute)
├── Model Garden Integration (/api/model-garden/execute)
└── AI Response Processing & Cleanup
```

**AI Provider Architecture:**

```
Dual AI System
├── Goose AI (Repository-aware, MCP extensions)
└── Model Garden (Enterprise LLMs via company proxy)
```

### 📋 Current Status

**Operational Interfaces:**

- ✅ Business Analyst interface with AI integration
- ✅ Product Owner interface with conversation-first document generation
- 🚧 Designer interface (planned)
- 🚧 Developer interface (planned)

**AI Capabilities:**

- ✅ Dual AI provider support (Goose + Model Garden)
- ✅ Repository analysis and code generation
- ✅ Natural conversation-first document generation
- ✅ Context-aware responses with quality control
- ✅ Intelligent document creation triggering

**User Experience:**

- ✅ Factory.ai-inspired conversation-first approach
- ✅ Professional dark theme interfaces
- ✅ Clickable document cards with split-screen viewing
- ✅ Smart conversation flow that gathers requirements naturally
- ✅ Document creation only when sufficient information is gathered

### 🔧 Recent Major Architecture Changes

**Problem Solved: Hallucinated Document Generation**

- **Issue**: System was generating fake "documents" containing questions instead of having natural conversations
- **Root Cause**: Hard-coded document generation triggers forced premature document creation
- **Solution**: Complete redesign to conversation-first, document-later approach

**New Conversation-First Architecture:**

1. **Natural Conversation Flow**: AI always starts with natural dialogue to understand requirements
2. **Intelligent Question Asking**: AI asks clarifying questions to gather comprehensive information
3. **Smart Document Triggering**: Documents are only created when AI has gathered sufficient information
4. **Quality Control**: Documents contain actual content, not questions disguised as documents
5. **Split-Screen Intelligence**: Split-screen only activates when real documents are generated

**Technical Implementation:**

- Redesigned `enhanceInstruction()` to always use conversation-first prompting
- Enhanced `extractDocuments()` to only trigger on explicit AI readiness signals
- Improved `isAskingForMoreInformation()` to detect conversational vs. document content
- Updated `shouldShowSplitScreen()` to validate actual document structure
- Modified AI prompting to match Factory.ai's conversation-first approach

**Key Behavioral Changes:**

- ❌ **Before**: "Generate BRD for my app" → Creates fake BRD with questions
- ✅ **After**: "Generate BRD for my app" → AI asks clarifying questions naturally
- ❌ **Before**: Split-screen opens immediately with question-filled "documents"
- ✅ **After**: Split-screen only opens when AI creates actual structured documents
- ❌ **Before**: Hard-coded triggers force document mode
- ✅ **After**: AI determines when enough information is gathered through conversation

## Common Development Tasks

When working on this project:

1. **Run the AI-powered server**: `python3 run_server.py` for full functionality
2. **Maintain design consistency**: Follow factory.ai-inspired clean document approach
3. **Use dual AI providers**: Leverage both Goose (repository-aware) and Model Garden (enterprise LLMs)
4. **Focus on conversation-first approach**: Ensure AI gathers requirements naturally before creating documents
5. **Test both AI backends**: Verify Goose and Model Garden integration work properly
6. **Preserve role-based architecture**: Keep interfaces focused on specific SDLC roles
7. **Clean document management**: Use card-based approach for generated content
8. **Validate conversation flow**: Test that AI asks clarifying questions before document generation
9. **Check document quality**: Ensure generated documents contain actual content, not questions
10. **Monitor split-screen behavior**: Verify split-screen only opens for real documents

## Testing the Conversation-First Approach

**Test Case 1: Vague Input**

- Input: "Hello, generate a BRD for my app"
- Expected: AI asks clarifying questions about the app's purpose, users, features
- Expected: No immediate document generation or split-screen activation

**Test Case 2: Detailed Input**

- Input: Comprehensive description of business requirements
- Expected: AI may still ask follow-up questions for clarity
- Expected: AI generates document only when confident it has sufficient information

**Test Case 3: Progressive Conversation**

- Input: Series of messages with increasing detail
- Expected: AI tracks conversation context and determines when ready to create document
- Expected: Split-screen activates only when real document is generated

**Test Case 4: Document Quality**

- Generated documents should contain actual business requirements, not questions
- Documents should be comprehensive and actionable
- Documents should follow proper markdown formatting with headers and structure

## Conversation-First AI Guidelines

When working with AI interfaces in this project:

1. Always implement conversation-first approach - AI should gather requirements naturally
2. Never force immediate document generation from vague inputs
3. Ensure AI asks clarifying questions before creating documents
4. Validate that generated documents contain actual content, not questions
5. Split-screen should only activate for real documents, not conversational responses
6. Test the conversation flow thoroughly to prevent hallucinated document generation

## Architecture Changes Summary

### Problem Solved: Hallucinated Document Generation

- **Root Cause**: Hard-coded triggers forced premature document creation
- **Solution**: Complete redesign to conversation-first, document-later approach
- **Key Changes**:
  - Redesigned `enhanceInstruction()` to always use conversation-first prompting
  - Enhanced `extractDocuments()` to only trigger on explicit AI readiness signals
  - Improved `isAskingForMoreInformation()` to detect conversational vs. document content
  - Updated `shouldShowSplitScreen()` to validate actual document structure

### New Workflow

1. **Conversation Phase**: AI asks clarifying questions to gather requirements
2. **Assessment Phase**: AI determines when sufficient information is gathered
3. **Document Generation**: AI creates real documents only when ready
4. **Split-Screen Activation**: Interface responds to real document generation

### Key Benefits

- No more hallucinated documents containing questions
- Natural conversation flow matches Factory.ai approach
- Documents contain actual requirements and specifications
- Split-screen activation is intelligent and purposeful
- User experience is conversational and intuitive
