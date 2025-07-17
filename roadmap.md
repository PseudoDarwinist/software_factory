Please talk in plain english and without jargons and in full sentences.
I am trying to create an app called Software factory. Here is my Claude.md file:

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


For making my App agentic. I want to use an open source toll called goose(https://github.com/block/goose) because it talks to LLM and also integrates well with github, Figma, and integrates into CI/CD. Supports lots of MCP.
I also have another open source tool called JACoB(https://github.com/jacob-ai-bot/jacob/blob/main/README.md)



What is Software Factory?

While AI can help you write code, Software Factory helps you build a production-quality product. 

If you want to move fast, it is a system that keeps your product and code in sync and allows you to build like a multi-person team, but with the clarity of one. 

It works horizontally across the software development lifecycle from PRD to Eng Plan to GitHub Issues to QA and Production.

It is an asynchronous, AI native system that ties planning to specs to your build process with a clean, unified workflow that replaces many SaaS tools, giving you speed and clarity. 


Why this app? While AI can help you write code... it still doesn’t do a great job of helping you build a product.

Software Factory is not a chatbot. It's your productOS, syncing PRD → Specs → Code → QA.

Software Factory is built for people who want mission control, not tool sprawl and drift.

Think code-gen is enough? That’s just one part of a successful product org. 




Chamath Palihapitiya

@chamath
·
Jul 11
Cursor, Replit etc work exceptionally well for engineers writing code, but what about all the other personas involved in building products?

Product Managers? Engineering Managers? QA?

This is why we built Software Factory to help us ship production code more consistently, with higher quality and better accountability. 

It works for us and may be useful to you...

1. Software Factory automates key components of the SDLC into one simple workflow. It obviates the need for the endless sprawl of various tools that all these personas use today to ship product.

2. Software Factory also orchestrates workflow for all of the people involved in bringing great products to life. There is now a place for every Product manager, Engineering manager, developer and quality assurance person to play their role.

3. Software Factory unifies these workflows in a shared space- your Software Factory - and lets you ship a durable product quickly so you don't miss your opportunity.

4. Great products evolve, but evolving great products is hard. The knowledge graph inside Software Factory makes evolving your product effortless. Five new people could onboard tomorrow and start working on features with no warm-up.

Software Factory is the tool to make all experts 10x more effective.
Software Factory allows teams from solo PM-Developers up to large groups to organize themselves, write quality requirements, build thorough Eng plans, extract detailed tickets, write quality code, QA thoroughly and repeat this process in an increasingly automated way until the project works. It is tuned for complex environments, making it also work very elegantly for de novo projects. 

What do you think of my approach to use goose/jacob? good? bad? Analyse it critically and give me candid feedback.I dnt want to reinvent the wheel of building all the agentic interactions my app needs from ground up but i dnt know if goose a cli tool i think will even work or will i face different challemges.


First, sorry for the buzz-words last time.

I’ll keep it simple and in full sentences.

⸻

Part 1 – What the two helper tools really are

Name	In one sentence	Why you might like it
Goose	A program you run in a command window that can read your code, talk to a big language model, change files, run tests, and open pull-requests, all by itself.	It already knows how to do many “engineering chores,” so you do not have to write that logic from scratch. It is popular (16 k GitHub stars).  
JACoB	A smaller tool that watches for a Figma design link or a short issue, then writes the matching code and opens a pull-request for you.	It focuses on “turn design into code” and already plugs into GitHub and Figma.  

Both are open-source under the Apache 2 licence, so you can change anything.

⸻

Part 2 – A simple, concrete story

Team: You (Product + Code), Sam (Designer), and a QA tester.
Goal: Ship a “Budget-Tracker” web app.

	1.	You write the idea in Software Factory.
““I need a simple web page where users type expenses and see a chart.””
Your app stores this as the Business idea.
	2.	Software Factory asks Goose to build a click-through mock-up.
Behind the scenes it runs a Goose “recipe” that:
	•	Sends your plain text to the language model.
	•	Generates simple HTML files.
	•	Starts a local server so you can click the fake app.
	3.	You test the mock-up in your browser.
You notice the chart is missing a legend and type a note.
Goose updates the mock-up in seconds.
	4.	Hand-off to Sam, the Designer.
Sam opens the same screen in Software Factory and polishes the look in Figma.
	5.	Sam presses “Send to JACoB.”
JACoB grabs the new Figma file, writes real React + Tailwind code, and opens a pull-request in GitHub that you can review.
	6.	Goose runs the checks.
Goose sees the pull-request, installs the code, runs the tests and linter, and posts the results back.
	7.	QA tester clicks “Preview.”
Software Factory spins up a test site from the pull-request.
The tester logs a bug: “Chart breaks on mobile.”
	8.	Goose fixes the bug.
It reads the bug note, edits the code, and updates the pull-request.
	9.	You hit “Merge.”
GitHub merges to main.
Goose triggers the CI/CD pipeline and ships the new version.
	10.	Software Factory shows a green tick.
Everyone sees “Idea → Mock-up → Design → Code → Test → Live” in one place, no copy-paste between tools.

⸻

Part 3 – What glue you still need to write

I will list every step, in plain language, in the next message.
It will cover:
	•	Where to install Goose and JACoB.
	•	How your web site talks to the command-line tools.
	•	How to handle keys, logs, and costs.

Let me know if you are ready for that deeper dive or if you want to tweak the plan first.

Software Factory — Full, Plain-English Blueprint

A complete guide that an AI agent (or a human team) can follow to build the first public release

⸻

1.  Executive summary

The problem. Modern teams bounce between many single-purpose tools. Requirements live in Google Docs, designs in Figma, tasks in Linear or Jira, code on GitHub, tests in yet another place. Context is lost, people repeat work, and mistakes slip through.

The idea. Software Factory puts the whole journey—idea, design, code, test, deploy—on one web page and lets AI helpers do the busywork. A non-technical founder can type a need once and watch it appear live on a test site minutes later. Technical staff can still inspect every step and give final approval.

The helpers.
	•	Goose—a command-line agent that can read and change code, talk to GitHub, create tasks in Linear, pull designs from Figma, run tests, and open pull-requests.
	•	JACoB—a design-to-code helper that turns a polished Figma frame into working React + Tailwind and adds it to the same pull-request.

Both tools are open-source and use the “Model Context Protocol” (MCP) so new skills can be bolted on later without rewriting the core.

⸻

2.  Who will use it
	•	Solo makers who act as product manager, designer, and developer at once.
	•	Small teams (2-15 people) that want quick hand-offs and fewer meetings.
	•	Large organisations that need audit logs, approval gates, and single sign-on but also want to cut tool sprawl.

⸻

3.  A short, concrete story
	1.	Anya, the founder, types:
“Add a dashboard page that shows spending by category.”
	2.	Software Factory passes that sentence to Goose.
	3.	Goose creates a short BRD, a longer PRD, and Linear user-story tickets.
	4.	Goose generates a clickable mock-up (plain HTML) and launches a small local server.
	5.	Anya tries the mock-up, writes “needs a pie chart legend,” and hits Update.
	6.	Goose tweaks the mock-up, then hands off to Sam, the designer.
	7.	Sam opens the mock-up in Figma, polishes colours and spacing, and presses Send to Build.
	8.	JACoB pulls the Figma frame, writes React + Tailwind code, pushes a branch, and opens a pull-request.
	9.	Goose sees the pull-request, runs tests, fixes any failing ones, and posts progress logs back to Software Factory in real time.
	10.	Lee, the QA tester, clicks a preview link, logs a small mobile bug in Linear; Goose fixes it automatically.
	11.	Anya reviews the final diff, presses Merge and Deploy, and the change goes live.
	12.	The timeline in Software Factory shows every event—idea, design, code, tests, QA, deploy—with green checks.

⸻

4.  Major parts of the system

4.1  Browser front-end
	•	Built as a React Single-Page App with a liquid-glass look.
	•	Shows one timeline per feature card.
	•	Streams live logs while agents work (Server-Sent Events or WebSockets).
	•	Lets the user click Approve gates.

4.2  Backend API
	•	Holds user accounts, projects, and access tokens.
	•	Exposes a /goose endpoint: accepts a prompt, starts Goose, streams logs.
	•	Emits status events (task started, task finished) to the front-end.
	•	Sets up preview sites when new pull-requests appear.

4.3  Goose adapter
	•	A tiny Node or Python service that lives next to Goose.
	•	Launches Goose as a child process and pipes stdout to the backend.
	•	Injects environment variables so Goose can see the right GitHub, Figma, and Linear tokens.
	•	Cleans up temporary repo clones after each run.

4.4  Goose CLI with MCP servers
	•	GitHub server — clone, branch, commit, open PR, merge.
	•	Linear server — create, update, and close tickets.
	•	Figma server — pull design frames as SVG/JSON.
	•	Developer server — run tests, linter, coverage, security scans.
	•	More servers can be added later (Jira, Snowflake, Kubernetes, etc.).

4.5  JACoB service
	•	Watches for pull-requests that carry a needs-jacob label.
	•	Pulls the linked Figma design, writes code, and updates the same pull-request.
	•	Uses the same GitHub token that Goose uses.

4.6  CI/CD pipeline
	•	Standard GitHub Actions workflow file goose.yml.
	•	Triggers on pull-request events.
	•	Installs Goose, runs a brief instruction (“Summarise the PR and list any risks”) and posts a comment.
	•	Builds Docker image and deploys to the preview slot in the chosen cloud (Vercel, Netlify, or Kubernetes).

4.7  Knowledge Graph updater (phase two)
	•	After each merge, Goose writes a short summary file.
	•	Backend parses the file and updates a graph database so new teammates can search “Where is the dashboard code?” and get an instant answer.

⸻

5.  Functional requirements in plain English
	1.	Single sign-on.  Users log in with their work Google or Microsoft account.
	2.	Connect once.  A user links GitHub, Linear, and Figma one time; Software Factory stores the tokens securely and re-uses them for all future jobs.
	3.	Role dashboards.  Tabs for Business, Product Owner, Designer, Developer, and QA, each showing the tasks relevant to that role.
	4.	Real-time logs.  While Goose or JACoB run, the user sees progress lines appear live; no need to refresh the page.
	5.	Manual approval gates.  At least one human must press Approve before code merges to main.
	6.	Cost guard.  Each project has a daily token budget. If a job would exceed it, the system blocks the run and shows a warning.
	7.	Audit log.  Every agent action—file change, ticket update, PR creation—gets stored with timestamp and user ID.
	8.	Preview links.  Every pull-request spin-ups a test site and posts the URL back to the feature card.
	9.	Knowledge capture.  After a merge, a summary of what changed is stored and linked back to the feature card.
	10.	Error handling.  If Goose exits with a non-zero code, the log stream ends with a red X and the user may retry or cancel.

⸻

6.  Non-functional requirements
	•	Performance – first page load under two seconds on a fast connection.
	•	Reliability – backend and Goose adapter run behind a process supervisor; automatic restart on crash.
	•	Security – all secrets in Vault; tokens use least-privilege scopes; every API behind HTTPS.
	•	Scalability – Goose jobs run in separate containers so many users can work in parallel.
	•	Observability – logs from agents, backend, and adapter go to a central store with search.

⸻

7.  Installation plan for a single-server pilot
	1.	Choose a host – a $20/month DigitalOcean droplet, 4 vCPUs, 8 GB RAM, Ubuntu 22.04.
	2.	Install Docker and docker-compose.
	3.	Clone the software-factory repo (empty for now) and copy in docker-compose.yml that defines three services:
	•	backend (Node or Python) on port 3000
	•	goose-adapter on port 4000
	•	frontend (React static files) served by Nginx on port 80
	4.	Mount volumes for Goose cache and temp repo clones.
	5.	Add environment variables in a .env file: OpenAI keys, GitHub PAT, Figma token, Linear token, daily token budget.
	6.	Run docker-compose up -d.
	7.	Point your domain at the droplet and run Certbot for HTTPS.
	8.	Sign in, connect GitHub when prompted, and run the first test job (for example, “Generate a README”).

⸻

8.  Continuous integration recipe (GitHub Actions)

name: Goose review and preview
on:
  pull_request:
    types: [opened, synchronize, reopened]

permissions:
  contents: write       # commit suggestions if needed
  pull-requests: write  # add comments
  issues: write         # update Linear links

jobs:
  goose-review:
    runs-on: ubuntu-latest
    timeout-minutes: 30

    env:
      GOOSE_PROVIDER: openai
      GOOSE_MODEL: gpt-4o
      PROVIDER_API_KEY: ${{ secrets.OPENAI_API_KEY }}
      GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      PR_NUMBER: ${{ github.event.number }}

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Install Goose
        run: |
          curl -fsSL https://github.com/block/goose/releases/download/stable/download_cli.sh \
          | CONFIGURE=false INSTALL_PATH=/usr/local/bin bash

      - name: Write Goose config
        run: |
          mkdir -p ~/.config/goose
          echo "keyring: false" > ~/.config/goose/config.yaml

      - name: Write instruction file
        run: |
          echo "Summarise this pull-request and list any risks for production." > instructions.txt

      - name: Run Goose
        run: |
          goose run --instructions instructions.txt | \
          sed -E 's/\x1B\[[0-9;]*[mK]//g' > pr_comment.txt

      - name: Comment on PR
        run: |
          gh pr comment $PR_NUMBER --body-file pr_comment.txt


⸻

9.  Future roadmap
	•	More MCP servers – Jira, Bitbucket, Slack, Datadog, and a cloud-cost estimator.
	•	Blue-green deploys – Goose triggers Kubernetes roll-outs and checks health before swapping traffic.
	•	Template gallery – common recipes (admin dashboard, blog, auth flow) appear as one-click starters.
	•	Insight charts – the timeline can show token spend per feature, average test run time, and defect rates.
	•	Mobile projects – extend JACoB to SwiftUI and Jetpack Compose.

⸻

10.  Glossary in plain language
	•	Agent – a program that reads instructions and does work for you.
	•	Pull-request – a bundle of code changes waiting for review.
	•	Token – a small piece of text that proves you have permission to call an API.
	•	Linear ticket – a to-do item in the Linear task tracker.
	•	MCP server – a plug-in that lets Goose talk to one outside system.
	•	Preview site – a temporary copy of your app used for testing.
	•	Knowledge graph – a searchable network of facts about your code base.

⸻

11.  Closing note

Everything above is written so that an AI coding agent—or a human team—can build the first production-ready version of Software Factory without guessing any missing pieces. If more depth is required on any single part, remember you can add new sections or clarifying notes later and feed those back into the same AI worker.

Software Factory — Technical Deep-Dive

A builder’s manual for junior and senior engineers

⸻

0.  Reading map
	•	Section 1 is the 10-second recap of the product.
	•	Sections 2–5 describe the high-level shape: who uses it, what runs where, and how pieces talk.
	•	Sections 6–15 drill right down to configs, data models, failure modes, and scaling levers.
	•	Section 16 lists open questions and next steps.

Read end-to-end once, then jump to the part you are coding today.

⸻

1.  Problem and goal in one paragraph

Teams keep their ideas in Google Docs, their designs in Figma, their tasks in Linear, and their code on GitHub. Context drops between those islands. Software Factory is a single web app that shows one rolling timeline per feature and lets two open-source agents—Goose and JACoB—carry the work from idea to production code. A human can step in anywhere, but the busywork is automated.

⸻

2.  Cast of characters
	•	Business role – thinks up features.
	•	Product Owner (PO) – refines the idea.
	•	Designer – polishes look and feel in Figma.
	•	Developer agent (Goose) – edits code, runs tests, opens PRs.
	•	Design-to-code agent (JACoB) – turns Figma frames into React/Tailwind.
	•	QA – tests the preview site.
	•	CI/CD worker – builds containers and deploys.

⸻

3.  Bird’s-eye architecture

Browser ──► Backend API ──► Goose-Adapter ──► Goose CLI
                │                │
                │                ├──► MCP: GitHub
                │                ├──► MCP: Linear
                │                ├──► MCP: Figma
                │                └──► MCP: Developer tools
                │
                └──► JACoB Service ──► GitHub

The browser never calls an agent directly; everything flows through the backend so we can secure tokens and stream logs safely.

⸻

4.  Life of a single feature (sequence, told as bullets)
	1.	Business types a sentence and presses Create Task.
	2.	Backend writes the task in Postgres and fires POST /goose with {prompt, projectId}.
	3.	Goose-Adapter launches Goose:
goose run --repo git@github.com:acme/app.git "Create BRD, PRD, Linear stories, mock HTML"
	4.	Goose uses four MCP servers: GitHub, Linear, Figma (read-only), Developer. It:
	•	commits docs/brd.md and docs/prd.md;
	•	creates Linear tickets;
	•	writes a mock HTML folder;
	•	serves it on port 5050 and prints the URL.
	5.	Backend streams each log line to the browser over WebSocket.
	6.	PO clicks the mock link, types feedback, presses Update Mock.
	7.	Backend calls Goose again with the same repo and new prompt.
	8.	Designer opens the finished mock in Figma, polishes it, labels the PR needs-jacob.
	9.	JACoB Service sees that label, pulls the Figma frame through the Figma MCP server, writes React + Tailwind, and pushes to the PR.
	10.	Goose test runner re-checks; if tests fail, Goose edits until green or until the 30-minute cap triggers.
	11.	QA opens the preview site, logs bugs in Linear; Goose fixes them.
	12.	PO presses Approve & Merge.
	13.	GitHub merges, GitHub Actions workflow installs Goose inside the runner, asks it to “summarise risk”, posts the comment, then builds and deploys.
	14.	Backend notes the “deploy succeeded” webhook and marks the timeline green.

⸻

5.  Deployment topology for the first public beta
	•	One Kubernetes namespace (or a docker-compose.yml) with five containers:
	•	frontend (static React built with Vite, served by Nginx on 80/443);
	•	backend (FastAPI, port 3000);
	•	postgres (13 or newer);
	•	goose-adapter (Python, port 4000);
	•	jacob (Node 18).
	•	Goose CLI and its extensions live inside the goose-adapter image so the process fork is cheap.
	•	Volumes: /srv/goose/clones (temp repos) and /srv/goose/cache (model cache).
	•	Secrets loaded at pod start from Vault: OpenAI key, GitHub PAT, Linear token, Figma token.
	•	Logs shipped to Loki; metrics scraped by Prometheus.

⸻

6.  Goose setup in depth
	1.	Install in the Dockerfile:

RUN cargo install goose-cli


	2.	Config file written at container start:

keyring: false
provider: openai
model: gpt-4o


	3.	Add GitHub MCP server (one-time during image build):

npx -y @modelcontextprotocol/server-github \
     --install  # guided wizard adds to Goose config
# Needs env: GITHUB_PERSONAL_ACCESS_TOKEN
```  [oai_citation:0‡block.github.io](https://block.github.io/goose/docs/getting-started/using-extensions/?utm_source=chatgpt.com)  


	4.	Add Linear MCP server:

npx -y mcp-remote https://mcp.linear.app/sse --install
# Needs env: LINEAR_API_KEY
```  [oai_citation:1‡apidog](https://apidog.com/blog/linear-mcp-server/)  


	5.	Add Figma MCP server:

npx -y @hapins/figma-mcp --install
# Needs env: FIGMA_ACCESS_TOKEN
```  [oai_citation:2‡block.github.io](https://block.github.io/goose/docs/mcp/figma-mcp/?utm_source=chatgpt.com)  


	6.	Runtime caps passed by the adapter:
	•	GOOSE_MAX_TOKENS=120000
	•	GOOSE_MAX_RUNTIME_SECONDS=1800

Goose now understands the repo, the design file, and the ticket system—and can call each through the MCP protocol.

⸻

7.  Goose-adapter service (Python FastAPI sketch)

from fastapi import FastAPI, WebSocket, BackgroundTasks
import subprocess, uuid, os, json

app = FastAPI()
RUN_DIR = "/srv/goose/clones"

def launch_goose(job_id: str, repo: str, prompt: str):
    cmd = ["goose", "run", "--repo", repo, prompt]
    proc = subprocess.Popen(cmd, cwd=RUN_DIR,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, bufsize=1)
    with open(f"/tmp/{job_id}.log", "w") as log:
        for line in proc.stdout:
            log.write(line)
    open(f"/tmp/{job_id}.done", "w").close()

@app.post("/goose")
async def run_goose(body: dict, tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    tasks.add_task(launch_goose, job_id, body["repo"], body["prompt"])
    return {"job_id": job_id}

@app.websocket("/logs/{job_id}")
async def stream_logs(ws: WebSocket, job_id: str):
    await ws.accept()
    log_path = f"/tmp/{job_id}.log"
    while not os.path.exists(f"/tmp/{job_id}.done"):
        if os.path.exists(log_path):
            for line in open(log_path):
                await ws.send_text(line)
        await asyncio.sleep(1)
    await ws.close()


⸻

8.  Backend API
	•	POST /api/tasks – create a new feature card.
	•	POST /api/run – proxy to /goose and returns a job_id.
	•	GET /api/events?since=cursor` – long-poll list of task events (for server-side rendering).
	•	WebSocket /ws/logs/{job_id} – upgrade and forward to goose-adapter.

Database (Postgres):

table	columns (simplified)
users	id, email, name, role, oauth_subject
projects	id, owner_id, git_repo_url, linear_team_id, figma_team_id
tokens	id, project_id, kind, encrypted_value, expires_at
tasks	id, project_id, title, status, created_by, created_at
events	id, task_id, type, payload(json), created_at


⸻

9.  JACoB service glue
	•	Watches GitHub webhooks (pull_request, issue_comment, label events).
	•	If a PR has label needs-jacob and a Figma link in the body, JACoB:
	1.	Downloads the Figma frame via the Figma MCP server.
	2.	Generates code (jacob build --figma <file> --out src/components).
	3.	Commits and pushes to the same PR branch.
	•	Posts a status check called JACoB-build so GitHub shows a yellow dot while code is being generated.

⸻

10.  CI/CD pipeline details
	•	goose-review job (see Section 8 in the blueprint) installs Goose inside the GitHub runner and posts a risk summary.
	•	build-and-preview job builds the Docker image, tags it pr-<number>, pushes to the registry, and deploys to a preview slot.
	•	deploy-prod job triggers on main branch pushes, repeats the build, but updates the “live” slot.

Timeout guards:

defaults:
  run:
    timeout-minutes: 30

Secrets used:

name	purpose
OPENAI_API_KEY	LLM calls inside Goose and JACoB
GITHUB_PAT	PR write access for agents
LINEAR_API_KEY	Ticket creation
FIGMA_ACCESS_TOKEN	Design pull
REGISTRY_TOKEN	Push Docker images


⸻

11.  Observability stack
	•	Loki – log aggregation (backend, adapter, Goose, JACoB).
	•	Prometheus – job duration, token spend, number of runs per user.
	•	Grafana dashboards – show success/failure rate, long-running jobs, and top token consumers.
	•	Alertmanager – warn on 5xx surge or token budget > 90 %.

⸻

12.  Security notes
	•	OAuth for GitHub, Linear, Figma. Tokens stored AES-256-GCM encrypted in Postgres; key lives in Vault.
	•	Backend issues short-lived JWTs to the browser, forces HTTPS, sets SameSite=Lax.
	•	Goose runs inside a non-root user in a container; no Docker socket access.
	•	Hard memory limit (512 MB) and CPU quota (2 cores) per Goose job container.
	•	CSP headers on the Nginx front-end ban inline scripts.

⸻

13.  Performance and scaling knobs
	•	Each Goose run is CPU heavy during test compile and GPU heavy only if you host your own model. For launch, call the OpenAI API so server stays CPU-bound.
	•	Keep a pool of warm Goose-adapter pods (e.g. 3) to avoid cold starts.
	•	Use buffered cloning: keep a bare mirror of each repo in /srv/goose/mirrors and clone –reference to speed up jobs.
	•	Front-end streams logs in 256 KB chunks to avoid DOM overload.

⸻

14.  Testing strategy
	1.	Unit tests – backend service routes and database helpers (pytest).
	2.	Contract tests – mock Goose CLI and ensure /goose returns logs and exit codes correctly.
	3.	Integration tests – docker-compose up, seed a test repo, run a full “add page” flow with a fake OpenAI stub.
	4.	E2E – Playwright script opens the browser, creates a task, watches logs, and checks preview site displays the new page.

Test data lives in a separate GitHub org with throw-away repos.

⸻

15.  Open questions / next tasks
	1.	Pick FastAPI or NestJS for backend—decide before coding begins.
	2.	Secret store – Vault vs AWS Secrets Manager; agree with DevOps.
	3.	LLM cost alerts – page DevOps at 80 % daily budget or just cap?
	4.	Knowledge graph DB – Neo4j vs Postgres JSONB; prototype both.
	5.	Mobile code generation – plan an Android/iOS track after web pilot.
	6.	Per-tenant token limits – enforce in backend or in Goose config?
	7.	Accessibility – run axe-core in CI; Goose can auto-fix? evaluate.

⸻

16.  Closing reminder

All commands and configs above build the first production pass. Every file path, port number, and secret name is editable—what matters is the data flow and guard-rails. Keep the manual Approve & Merge gate alive until metrics show Goose and JACoB are stable.

If you hand this document to an AI coding agent, feed it section by section, starting with backend scaffolding, then Goose adapter, then front-end log streaming, and so on. Each section contains enough detail for an implement-then-test cycle of about four focused hours.


