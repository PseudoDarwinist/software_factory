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

## Architecture

The project follows a simple static website structure:

### Core Files
- **index.html** - Main HTML structure with hero section and alternating feature sections
- **styles.css** - Complete styling with advanced CSS effects:
  - Grid background patterns and architectural visual effects for hero section
  - Neon button glow effects using CSS gradients and box-shadow
  - Glass-morphism cards with backdrop-filter and subtle green tinting
  - Text highlight pills for important keywords
  - Responsive design with mobile-first approach
  - Dark mode support via CSS media queries

### Asset Management
- **images/** - Contains all visual assets (hero-image.png, feature images, background images)
- **save_images.py** - Script to create placeholder images during development
- **replace_images.py** - Utility to replace placeholder images with actual assets

### Development Tools
- **run_server.py** - Local development server with automatic port detection
- **test_images.html** - Image testing utility to verify asset loading

## Development Commands

### Local Development
```bash
# Start local development server (automatically finds free port 8000-8099)
python3 run_server.py

# Test image loading
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

## Common Development Tasks

When working on this project:
1. Use the local development server for testing
2. Maintain the glass-morphism design consistency across new features
3. Follow the established pattern for feature sections (alternating layout with .reverse class)
4. Use the highlight-tag class for important keyword emphasis
5. Test responsiveness across mobile and desktop viewports
6. Build modular, reusable components that scale with platform growth
7. Keep separation of concerns clear in all new code