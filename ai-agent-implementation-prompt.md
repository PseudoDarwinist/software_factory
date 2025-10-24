# Comprehensive Implementation Prompt: Intelligent PRD Generation System

## Project Context and Background

You are implementing an **Intelligent PRD Generation System** for Software Factory, a Flask-based AI-native development platform. This system will transform the current basic PRD generation into a professional, Editor.js-based document editor with floating AI enhancement capabilities.

### Current System Architecture (Software Factory)
- **Backend**: Python Flask with SQLAlchemy ORM
- **Frontend**: Vanilla JavaScript with Tailwind CSS
- **Database**: PostgreSQL with pgvector extension
- **AI Integration**: Existing AI broker service with OpenAI/Anthropic providers and modelgarden LLMs
- **Authentication**: Flask session-based with enterprise SSO integration
- **Real-time**: Flask-SocketIO with eventlet for WebSocket communication

### Key Files to Reference:
- **AI Broker Service**: `src/services/ai_broker.py` - existing AI provider management
- **Current PRD Interface**: `frontend/po.html` and `frontend/po.js` - current split-screen chat
- **Existing PRD Components**: `frontend/prd-editor.js`, `frontend/prd-renderer.js`, `frontend/prd-sections.js`
- **Flask App Structure**: `src/app.py` - main application entry point
- **Database Models**: `src/models/` - existing data model patterns
- **API Blueprints**: `src/api/` - existing API endpoint patterns

## Complete User Journey and Context

### Phase 1: Think Stage (Existing System)
1. **User uploads documents** (PDFs, docs, etc.) into the "sources tray" component in the **refine sources** section of the Think stage
2. **PRD gets generated** using existing AI logic and stored in the database
3. **"Open PRD" button appears** in the Think stage interface
4. **Current behavior**: Clicking "Open PRD" opens `po.html` with split-screen chat interface

### Phase 2: New System (What You're Building)
1. **User clicks "Open PRD" button** from Think stage
2. **NEW BEHAVIOR**: Opens full-screen Editor.js-based PRD editor (`intelligent-prd-editor.html`)
3. **Existing PRD content loads** beautifully formatted into Editor.js blocks
4. **Floating AI chat** (green bubble, bottom-right) allows PRD enhancement
5. **AI transforms basic PRD** into comprehensive, diagram-rich document

## Technical Implementation Requirements

### 1. Full-Screen Editor.js Interface

**Create**: `frontend/intelligent-prd-editor.html`
```html
<!-- Full-screen layout, NO split-screen -->
<!-- Professional styling matching Notion/Linear quality -->
<!-- Editor.js container with custom PRD blocks -->
<!-- Floating AI chat bubble (green, bottom-right) -->
```

**Key Requirements**:
- **NO split-screen interface** - entire screen dedicated to PRD editing
- **Professional typography** and spacing matching enterprise tools
- **Responsive design** that works on desktop and tablet
- **Smooth animations** and micro-interactions

### 2. Editor.js Integration and Custom Blocks

**Create**: `frontend/intelligent-prd-editor.js`
```javascript
// Editor.js configuration with custom PRD blocks
// Content loading from existing PRD data
// Block-based editing system
// Integration with floating AI chat
```

**Custom Blocks Needed**:
- **Rich text blocks** for paragraphs and formatted content
- **Heading blocks** with proper hierarchy (H1, H2, H3, H4)
- **List blocks** for requirements and feature lists
- **Table blocks** for requirements matrices and data models
- **Mermaid diagram blocks** for embedded visualizations
- **Quote blocks** for user stories and acceptance criteria
- **Custom PRD section blocks** for structured content

### 3. PRD Content Loading System

**Integrate with existing Think stage**:
- **Load existing PRD data** from database/Think stage
- **Convert text content** into appropriate Editor.js blocks
- **Format content professionally** with proper styling
- **Handle various content types** (headings, lists, paragraphs, tables)

### 4. Floating AI Chat Assistant

**Reference existing chat from**: `frontend/po.js` (lines 400-600)
**DO NOT copy the implementation** - instead, **learn from the patterns** and create a much more sophisticated version.

**Key Improvements Over Existing Chat**:
- **Sophisticated conversation flow** with drilling questions (like the example provided)
- **Context-aware responses** that understand the existing PRD content
- **Progressive enhancement** - each conversation makes PRD more comprehensive
- **Real-time Editor.js updates** as AI generates content
- **Professional chat interface** with progress indicators

**Chat Interface Requirements**:
- **Green chat bubble** fixed in bottom-right corner
- **Slide-out sidebar** when clicked (like screenshot provided)
- **Progress indicators** for AI operations
- **Chat history** and context management
- **Smooth animations** for professional feel

### 5. AI Enhancement Logic

**Reference existing AI broker**: `src/services/ai_broker.py`
**Use existing patterns** but enhance for PRD-specific use cases.

**AI Conversation Flow** (Based on Example Provided):
```
1. Initial Analysis: "I can see your existing PRD. What aspects would you like me to enhance?"
2. Drilling Questions: "What's the current project stage? What integrations do you need?"
3. Technical Details: "What's your tech stack? Performance requirements?"
4. Comprehensive Generation: Create exhaustive PRD sections with diagrams
```

**AI Capabilities Needed**:
- **Analyze existing PRD content** and identify enhancement opportunities
- **Ask sophisticated drilling questions** to understand requirements deeply
- **Generate comprehensive sections** (like the example PRD.md provided)
- **Create Mermaid diagrams** (ERD, class diagrams, flowcharts, sequence diagrams)
- **Update Editor.js blocks** in real-time as content is generated

### 6. Mermaid Diagram Integration

**Create custom Editor.js block** for Mermaid diagrams:
- **Live preview** of diagrams within Editor.js
- **Code editor mode** for direct Mermaid syntax editing
- **Visual editor mode** for user-friendly diagram creation
- **Diagram templates** for common PRD diagrams (ERD, architecture, etc.)
- **Export capabilities** (PNG, SVG, PDF)

**Diagram Types to Support**:
- **System Architecture** flowcharts
- **Entity Relationship Diagrams** (ERD) for data models
- **Class diagrams** for component structure
- **Sequence diagrams** for user workflows
- **Component diagrams** for system design

### 7. Backend Integration

**Create new Flask routes** in `src/api/`:
```python
# PRD Editor API endpoints
@prd_editor_bp.route('/api/prd-editor/<int:prd_id>')  # Load PRD content
@prd_editor_bp.route('/api/prd-editor/<int:prd_id>/enhance')  # AI enhancement
@prd_editor_bp.route('/api/prd-editor/<int:prd_id>/save')  # Save Editor.js content
```

**Database Integration**:
- **Store Editor.js content** in PostgreSQL (JSONB format)
- **Version control** for PRD changes
- **Link to existing Think stage** PRD records
- **User permissions** and access control

## Implementation Guidelines

### Phase 1: Core Editor.js Setup (Tasks 1-2)
1. **Create full-screen HTML interface** with Editor.js integration
2. **Build custom PRD blocks** for all content types
3. **Implement professional styling** matching enterprise tools
4. **Create content loading system** from existing PRD data
5. **Test with realistic PRD content** to validate all blocks work

### Phase 2: Floating AI Chat (Tasks 3-4)
1. **Create floating chat bubble** with slide-out sidebar
2. **Implement sophisticated conversation flow** (much better than existing po.js)
3. **Add progress tracking** and status indicators
4. **Build chat-to-Editor integration** for real-time content updates
5. **Test AI enhancement** with mock conversations

### Phase 3: Backend Integration (Tasks 5-6)
1. **Create Flask API endpoints** for PRD editor operations
2. **Integrate with existing Think stage** workflow
3. **Implement data persistence** for Editor.js content
4. **Add user authentication** and permissions
5. **Test complete workflow** from Think stage to enhanced PRD

### Phase 4: Advanced Features (Tasks 7-8)
1. **Implement Mermaid diagram blocks** with live preview
2. **Add AI diagram generation** capabilities
3. **Create export functionality** (PDF, Word, Markdown)
4. **Performance optimization** and polish
5. **Comprehensive testing** and bug fixes

## Key Success Criteria

### User Experience
- **"Open PRD" button** opens beautiful, full-screen Editor.js interface
- **Existing PRD content** loads professionally formatted
- **Floating AI chat** enables sophisticated PRD enhancement
- **Real-time updates** as AI generates comprehensive content
- **Professional quality** matching Notion/Linear/Figma

### Technical Quality
- **Editor.js integration** works smoothly with custom blocks
- **AI conversation flow** is sophisticated and context-aware
- **Mermaid diagrams** render correctly and are editable
- **Backend integration** preserves existing workflow
- **Performance** is fast and responsive

### Content Quality
- **Comprehensive PRD sections** generated by AI (like example PRD.md)
- **Professional diagrams** embedded throughout document
- **Technical specifications** with proper depth and detail
- **Framework compliance** (EARS, IEEE 830, industry standards)
- **Export quality** maintains formatting across all formats

## Important Notes

### What NOT to Do
- **Don't create split-screen interface** - full-screen only
- **Don't copy existing po.js chat** - create much more sophisticated version
- **Don't ignore existing AI broker** - use and enhance existing patterns
- **Don't break Think stage integration** - maintain seamless workflow

### What TO Do
- **Study existing codebase patterns** and follow established conventions
- **Reference provided example PRD.md** for content quality standards
- **Use existing AI broker service** but enhance for PRD-specific needs
- **Create professional UI** that matches enterprise tool quality
- **Implement progressive enhancement** - each AI conversation improves PRD

### Code Quality Standards
- **Follow existing Flask patterns** from `src/api/` and `src/services/`
- **Use existing database models** as reference for new PRD storage
- **Maintain existing authentication** and user management
- **Write comprehensive tests** for all new functionality
- **Document all new APIs** and components

## Screenshots and Visual References

*[You mentioned you'll provide screenshots to show the desired UI quality and layout]*

The AI agent should use these screenshots as visual references for:
- **Professional styling** and typography
- **Layout and spacing** standards
- **Color scheme** and visual hierarchy
- **Animation and interaction** patterns
- **Overall polish** and attention to detail

## Final Implementation Notes

This system will transform Software Factory's PRD generation from a basic tool into a professional-grade documentation system. The key is creating a seamless user experience where clicking "Open PRD" reveals a beautifully formatted document that can be enhanced through sophisticated AI conversation into a comprehensive, diagram-rich specification that rivals industry-leading documentation tools.

Focus on **incremental implementation** - get the basic Editor.js interface working first, then add the floating AI chat, then integrate with backend, then add advanced features. Each phase should be fully functional and testable before moving to the next.