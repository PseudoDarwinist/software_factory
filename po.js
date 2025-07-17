// Software Factory - Product Owner Assistant
// Sprint Planning and User Story Generation

class ProductOwnerAssistant {
    constructor() {
        this.aiProvider = {
            type: 'goose', // 'goose' or 'model-garden'
            model: 'claude-opus-4' // for model-garden
        };
        
        console.log('ProductOwnerAssistant initialized with provider:', this.aiProvider);
        
        this.chatHistory = [];
        this.isTyping = false;
        this.isSplitScreen = false;
        this.documents = []; // Store generated documents
        
        // Evolution tracking
        this.evolutionState = {
            currentStage: 1, // 1: BRD, 2: PRD, 3: User Stories, 4: Implementation
            completedStages: [],
            businessSpecs: null,
            brd: null,
            prd: null,
            userStories: null,
            implementationChecklist: null
        };
        
        // Stage definitions
        this.stages = {
            1: { name: 'BRD', title: 'Business Requirements Document', description: 'Define business requirements and stakeholder needs' },
            2: { name: 'PRD', title: 'Product Requirements Document', description: 'Detailed product specifications and features' },
            3: { name: 'User Stories', title: 'User Stories', description: 'Breakdown into actionable user stories' },
            4: { name: 'Implementation', title: 'Implementation Checklist', description: 'Detailed implementation checklist for development' }
        };
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadAIProvider();
        this.loadEvolutionState();
        this.validateEvolutionState();
        this.hideWelcomeMessage();
        this.debugImages();
        this.setupSplitDivider();
        this.setupViewModes();
        this.updateStageUI();
    }

    // Ensure completedStages list only contains stages with existing documents
    validateEvolutionState() {
        const docKeys = {
            1: 'brd',
            2: 'prd',
            3: 'userStories',
            4: 'implementationChecklist'
        };

        // Filter out any stage numbers that have no corresponding document content
        this.evolutionState.completedStages = this.evolutionState.completedStages.filter(stageNum => {
            const key = docKeys[stageNum];
            return key && this.evolutionState[key];
        });

        // Persist any cleanup to localStorage
        this.saveEvolutionState();
    }

    debugImages() {
        // Debug image loading
        const images = document.querySelectorAll('.evolution-silhouette-small img');
        images.forEach((img, index) => {
            img.onerror = function() {
                console.error(`Failed to load image ${index}:`, this.src);
            };
            img.onload = function() {
                console.log(`Successfully loaded image ${index}:`, this.src);
            };
        });
    }

    setupEventListeners() {
        // Chat Interface
        document.getElementById('sendMessage')?.addEventListener('click', () => this.sendMessage());
        document.getElementById('chatInput')?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Auto-resize chat input
        document.getElementById('chatInput')?.addEventListener('input', (e) => this.autoResizeTextarea(e.target));
        
        // AI Provider Selection
        document.getElementById('aiProviderSelect')?.addEventListener('change', (e) => this.selectAIProvider(e.target.value));
        document.getElementById('modelSelect')?.addEventListener('change', (e) => this.updateModel(e.target.value));
        
        // New AI Model Selector - Floating Logos
        document.getElementById('gooseProvider')?.addEventListener('click', () => this.showModelPopup('goose'));
        document.getElementById('aiStudioProvider')?.addEventListener('click', () => this.showModelPopup('ai-studio'));
        
        // Model Popup Controls
        document.getElementById('popupClose')?.addEventListener('click', () => this.hideModelPopup());
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('model-popup')) {
                this.hideModelPopup();
            }
        });
        
        // Model Selection in Popup
        document.querySelectorAll('.model-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const provider = e.currentTarget.getAttribute('data-provider');
                const model = e.currentTarget.getAttribute('data-model');
                this.selectModelFromPopup(provider, model);
            });
        });
        
        // Content Panel
        document.getElementById('closePanel')?.addEventListener('click', () => this.closeSplitScreen());
        
        // View Mode Buttons
        document.getElementById('codeViewBtn')?.addEventListener('click', () => this.switchToCodeView());
        document.getElementById('previewViewBtn')?.addEventListener('click', () => this.switchToPreviewView());
        
        // Document Actions
        document.getElementById('saveDocument')?.addEventListener('click', () => this.saveDocument());
        document.getElementById('exportDocument')?.addEventListener('click', () => this.exportDocument());
        document.getElementById('historyDocument')?.addEventListener('click', () => this.showHistory());
        document.getElementById('improveDocument')?.addEventListener('click', () => this.improveDocument());
        
        // Stage progression
        document.getElementById('approveStage')?.addEventListener('click', () => this.approveCurrentStage());
        document.getElementById('nextStage')?.addEventListener('click', () => this.moveToNextStage());
        document.getElementById('previousStage')?.addEventListener('click', () => this.moveToPreviousStage());
        
        // Format toolbar
        document.getElementById('formatSelector')?.addEventListener('change', (e) => this.changeFormat(e.target.value));
        document.getElementById('aiAssist')?.addEventListener('click', () => this.aiAssist());
        document.getElementById('boldBtn')?.addEventListener('click', () => this.toggleBold());
        document.getElementById('italicBtn')?.addEventListener('click', () => this.toggleItalic());
        document.getElementById('underlineBtn')?.addEventListener('click', () => this.toggleUnderline());
        document.getElementById('listBtn')?.addEventListener('click', () => this.toggleList());
        document.getElementById('numberedListBtn')?.addEventListener('click', () => this.toggleNumberedList());
        document.getElementById('checklistBtn')?.addEventListener('click', () => this.toggleChecklist());
    }

    hideWelcomeMessage() {
        // Hide welcome message when user starts typing
        const chatInput = document.getElementById('chatInput');
        const welcomeMessage = document.querySelector('.welcome-message');
        
        if (chatInput && welcomeMessage) {
            chatInput.addEventListener('focus', () => {
                welcomeMessage.style.display = 'none';
            });
        }
    }

    showSplitScreen() {
        const workspace = document.querySelector('.po-workspace');
        const documentPanel = document.getElementById('documentPanel');
        const floatingControls = document.querySelector('.floating-controls');
        
        workspace.classList.add('split-screen');
        documentPanel.classList.remove('hidden');
        floatingControls.classList.add('visible');
        this.isSplitScreen = true;
    }

    closeSplitScreen() {
        const workspace = document.querySelector('.po-workspace');
        const documentPanel = document.getElementById('documentPanel');
        const floatingControls = document.querySelector('.floating-controls');
        
        workspace.classList.remove('split-screen');
        documentPanel.classList.add('hidden');
        floatingControls.classList.remove('visible');
        this.isSplitScreen = false;
    }

    shouldShowSplitScreen(output) {
        // Only show split screen if AI generated an actual document (not questions)
        return this.isActualDocument(output) && !this.isAskingForMoreInformation(output);
    }
    
    isActualDocument(output) {
        // Check if output contains substantial structured content (not just questions)
        const hasHeaders = /^#+\s+/m.test(output);
        const hasStructure = /^\d+\.|^-\s+|^\*\s+/m.test(output);
        const hasSubstantialContent = output.length > 500;
        const hasDocumentTitle = /^#\s+(Business|Product)\s+Requirements\s+Document/m.test(output);
        
        return hasDocumentTitle || (hasHeaders && hasStructure && hasSubstantialContent);
    }

    enhanceInstruction(userMessage) {
        // Don't enhance simple greetings
        const isGreeting = /^(hi|hello|hey|good morning|good afternoon|good evening|test|testing)\.?$/i.test(userMessage.trim());
        if (isGreeting) {
            return userMessage;
        }

        // Always start with natural conversation - never force document generation
        // The AI will decide when to create documents based on conversation completeness
        return this.getNaturalConversationPrompt(userMessage);
    }
    
    getStagePrompt(userMessage) {
        const stage = this.stages[this.evolutionState.currentStage];
        return `**Current Stage: ${stage.name} - ${stage.title}**

${stage.description}

---

${userMessage}`;
    }
    
    // This method is no longer used in the new conversation-first approach
    // The AI now determines when it has enough information through natural conversation
    hasAdequateInformationForStage(userMessage, stage) {
        // Always return false to ensure conversation-first approach
        // The AI will determine when to create documents based on conversation context
        return false;
    }
    
    hasBusinessContext(userMessage) {
        // Look for business-related keywords that indicate real requirements
        const businessKeywords = [
            'users?', 'customers?', 'business', 'features?', 'functionality',
            'requirements?', 'needs?', 'goals?', 'objectives?', 'problems?',
            'solutions?', 'workflow', 'process', 'integration', 'platform',
            'system', 'dashboard', 'analytics', 'reports?', 'management',
            'tracking', 'monitoring', 'automation', 'api', 'database',
            'security', 'authentication', 'authorization', 'payments?',
            'notifications?', 'messaging', 'communications?', 'interface',
            'mobile', 'web', 'desktop', 'cloud', 'saas', 'enterprise'
        ];
        
        const keywordPattern = new RegExp(businessKeywords.join('|'), 'i');
        const hasKeywords = keywordPattern.test(userMessage);
        
        // Also check for descriptive length (substantial description)
        const hasSubstantialContent = userMessage.split(/\s+/).length >= 10;
        
        return hasKeywords && hasSubstantialContent;
    }
    
    getDocumentGenerationPrompt(userMessage) {
        const currentStage = this.stages[this.evolutionState.currentStage];
        
        if (this.evolutionState.currentStage === 1) {
            // Stage 1: Generate BRD from business specs
            return this.getBRDPrompt(userMessage);
        } else if (this.evolutionState.currentStage === 2) {
            // Stage 2: Generate PRD from BRD
            return this.getPRDPrompt(userMessage);
        } else if (this.evolutionState.currentStage === 3) {
            // Stage 3: Generate User Stories from PRD
            return this.getUserStoriesPrompt(userMessage);
        } else if (this.evolutionState.currentStage === 4) {
            // Stage 4: Generate Implementation Checklist from User Stories
            return this.getImplementationPrompt(userMessage);
        }
        
        // Fallback
        return `You are a Product Owner expert. The user provided detailed information:

"${userMessage}"

Create a comprehensive ${currentStage.title} based on this information. Start with: "Based on your detailed description, I can create a comprehensive ${currentStage.name}. Here it is:" followed by the actual document with proper markdown formatting.`;
    }
    
    getNaturalConversationPrompt(userMessage) {
        const currentStage = this.stages[this.evolutionState.currentStage];
        const conversationHistory = this.chatHistory.slice(-3).map(msg => `${msg.type}: ${msg.content}`).join('\n');
        
        return `You are a thoughtful Product Owner expert. The user's request needs more detail for creating a comprehensive document.

User's message: "${userMessage}"

Recent conversation context:
${conversationHistory}

Instructions:
1. **BE CONCISE**: Ask 2-3 focused questions (not a long list)
2. **FOCUS ON ESSENTIALS**: Ask about the most critical aspects:
   - What problem does your app solve?
   - Who are your target users?
   - What are the key features?

3. **NATURAL STYLE**: Be conversational, not formal or interrogative

4. **EFFICIENT PROGRESSION**: If user provides good detail in response, create the ${currentStage.name} immediately

5. **SMART TRIGGERING**: When you have sufficient information, start with "Based on your description, I can create a comprehensive ${currentStage.name}. Here it is:" followed by the actual document.

Ask focused questions to gather essential information efficiently.`;
    }
    
    getRequiredInformationForStage(stage) {
        switch(stage) {
            case 1: // BRD
                return `- What is the main purpose/goal of the application?
- Who are the target users/customers?
- What specific problems does it solve?
- What are the core features or functionality needed?
- Are there any business constraints or requirements?
- What is the expected business value or ROI?`;
            case 2: // PRD
                return `- Detailed feature specifications
- User workflows and journeys
- Technical requirements and constraints
- Performance and scalability needs
- Integration requirements`;
            case 3: // User Stories
                return `- Specific user roles and personas
- Detailed user goals and motivations
- Acceptance criteria for each feature
- Priority and dependencies`;
            case 4: // Implementation
                return `- Technical architecture decisions
- Development framework and tools
- Database schema requirements
- API specifications
- Testing strategy`;
            default:
                return `- Clear objectives and requirements
- Stakeholder needs and constraints
- Success criteria and metrics`;
        }
    }

    getBRDPrompt(businessSpecs) {
        // Store business specs for later use
        this.evolutionState.businessSpecs = businessSpecs;
        this.saveEvolutionState();
        
        return `You are a Senior Product Manager. Create a comprehensive Business Requirements Document (BRD) based on the high-level specs below.

<SPECS>
${businessSpecs}
</SPECS>

Follow these steps:

1. **Stakeholder & User Analysis (RACI Matrix + User Personas)**
   - Identify key stakeholders and their roles using a RACI (Responsible, Accountable, Consulted, Informed) matrix.
   - Develop user personas that highlight core needs and pain points.

2. **Value Proposition & Differentiation (Value Proposition Canvas)**
   - Use the Value Proposition Canvas to map out how the product solves user needs and stands out against alternatives.
   - Clearly articulate the unique selling points (USPs).

3. **Business Model & Market Context (Business Model Canvas)**
   - Populate a Business Model Canvas to outline revenue streams, cost structure, partners, and customer segments.
   - Include a brief competitive landscape overview (Porter's Five Forces) to identify major risks or barriers.

4. **Requirements Gathering & Prioritization (MoSCoW)**
   - Translate the high-level specs into clear business requirements.
   - Apply the MoSCoW (Must, Should, Could, Won't) framework to prioritize these requirements.

5. **Risk & Assumption Analysis (SWOT + Risk Register)**
   - Conduct a mini-SWOT (Strengths, Weaknesses, Opportunities, Threats) analysis to anticipate challenges.
   - Maintain a risk register with mitigation plans for top critical risks.

6. **Success Metrics & KPIs**
   - Propose quantifiable success metrics (e.g., user adoption rate, revenue targets, NPS, etc.).
   - Link each requirement to specific KPIs.

7. **Next Steps & Timeline**
   - Outline high-level milestones and a proposed timeline, factoring in any known dependencies or constraints.

Deliver a final BRD that integrates all these elements in a clear, cohesive format, suitable for both executive review and technical hand-off.

**IMPORTANT FORMATTING REQUIREMENTS:**
- Use proper markdown headers (# ## ### ####) for all sections
- Format all content in clean, readable markdown
- Use lists, tables, and code blocks where appropriate
- Include proper spacing and formatting
- Make it look professional and well-structured
- DO NOT use placeholder text or fictional information
- Base all content on the actual specs provided

Start with: # Business Requirements Document (BRD)
Then continue with all sections in proper markdown format.`;
    }

    getPRDPrompt(message) {
        const brdContent = this.evolutionState.brd || 'No BRD available. Please generate BRD first.';
        return `You are a Senior Product Manager. Create a comprehensive Product Requirements Document (PRD) based on the business requirements below.

<BRD>
${brdContent}
</BRD>

Follow these steps:

1. **Feature Definition & Prioritization (Kano Model)**
   - Break down the business requirements into specific features.
   - Use the Kano Model to classify features (Basic, Performance, Excitement).

2. **Functional & Non-Functional Requirements**
   - For each feature, define functional requirements (what the feature does).
   - Outline non-functional requirements (performance, security, scalability, compliance) in detail.

3. **User Workflows & Journeys (User Story Mapping)**
   - Construct detailed user journeys by mapping each feature to user goals and tasks.
   - Identify potential bottlenecks or friction points in the user flow.

4. **Technical Feasibility & Architecture (Conceptual Architecture Diagram)**
   - Propose a high-level architecture diagram (e.g., microservices vs. monolith, cloud components, APIs).
   - Discuss technical constraints or dependencies.

5. **Acceptance Criteria (Gherkin Syntax)**
   - Provide acceptance criteria for each feature in a clear "Given-When-Then" format (or a similar structured approach).
   - Ensure each requirement has a testable outcome.

6. **Release Strategy & Timeline (Incremental Roadmap)**
   - Outline how features will be rolled out over multiple releases.
   - Indicate any dependencies, gating factors, or parallel workstreams.

7. **Risk Management & Assumptions (RAID Log)**
   - Maintain a RAID (Risks, Assumptions, Issues, Dependencies) log.
   - Provide mitigation strategies for key risks.

Generate a final PRD that synthesizes these frameworks into a single, detailed product specification ready for development teams.`;
    }

    getUserStoriesPrompt(message) {
        const prdContent = this.evolutionState.prd || 'No PRD available. Please generate PRD first.';
        return `You are a Senior Product Manager. Create a detailed list of one-story-point user stories based on the following Product Requirements Document (PRD).

<PRD>
${prdContent}
</PRD>

Follow these steps:

1. **Epic & Feature Breakdown (User Story Mapping)**
   - Identify the major epics or features from the PRD.
   - Break each feature down into granular steps that can be completed in a single day or less.

2. **User Stories (INVEST Criteria)**
   - Write each user story following the INVEST model (Independent, Negotiable, Valuable, Estimable, Small, Testable).
   - Use the format: "As a [type of user], I want [action], so that [benefit]."

3. **Acceptance Criteria (Clear & Testable)**
   - Provide acceptance criteria for each user story, ensuring it is testable and unambiguous.
   - Example format: "Given [context], when [action], then [expected result]."

4. **Prioritization & Sequencing (WSJF or RICE)**
   - Apply a lightweight prioritization framework (e.g., Weighted Shortest Job First (WSJF) or RICE) to order stories.
   - Include a brief explanation of priority rankings.

5. **Dependency Identification**
   - Note any inter-story or external dependencies.
   - Indicate if certain stories must be completed before others can start.

6. **Quality & Testing Considerations (Definition of Done)**
   - Outline a Definition of Done that includes code review, testing, and documentation updates.
   - Ensure each story can be accepted independently once its criteria are met.

7. **Roadmap Integration**
   - Map the final list of one-story-point stories into sprints or iterations.
   - Clarify how these stories align with the overall release timeline and milestones.

Produce a final, neatly categorized list of one-story-point user stories with acceptance criteria and priorities, ready for a development team to start work immediately.`;
    }

    getImplementationPrompt(message) {
        const userStoriesContent = this.evolutionState.userStories || 'No User Stories available. Please generate User Stories first.';
        return `Create a very very very detailed markdown checklist of all of the stories for this project plan, with one-story-point tasks (with unchecked checkboxes) that break down each story. It is critically important that all of the details to implement this are in this list. Note that a very competent AI Coding Agent will be using this list to autonomously create this application, so be sure not to miss any details whatsoever, no matter how much time and thinking you must do to complete this very challenging but critically important task.

<USER_STORIES>
${userStoriesContent}
</USER_STORIES>

Break down each user story into granular implementation tasks with checkboxes that include:
- File creation/modification tasks
- Code implementation details
- Testing requirements
- UI/UX implementation
- Database schema changes
- API endpoint definitions
- Configuration updates
- Documentation updates

Format as markdown with checkboxes for each task.`;
    }

    updateContentPanel(docData) {
        const markdownEditor = document.getElementById('markdownEditor');
        const renderedContent = document.getElementById('renderedContent');
        
        if (markdownEditor && renderedContent) {
            let content = '';
            
            // Handle both document objects and plain content
            if (typeof docData === 'object' && docData.content) {
                content = docData.content;
            } else {
                content = docData;
            }
            
            // Update code view
            markdownEditor.value = content;
            
            // Update preview view
            this.updatePreview(content);
        }
    }

    extractDocuments(output) {
        const documents = [];
        
        // Smart document extraction - look for AI signals AND actual document structure
        const isReadySignal = /Based on (our conversation|your detailed? description).*I.*can.*create.*comprehensive/i.test(output);
        const hasDocumentStructure = this.isActualDocument(output);
        const isNotAskingQuestions = !this.isAskingForMoreInformation(output);
        
        // Must have readiness signal OR (document structure AND not asking questions)
        if (isReadySignal || (hasDocumentStructure && isNotAskingQuestions)) {
            // Look for document type indicators
            const brdPattern = /(?:business\s+requirements?\s+document|BRD)/i;
            const prdPattern = /(?:product\s+requirements?\s+document|PRD)/i;
            const userStoriesPattern = /user\s+stories?/i;
            const implementationPattern = /implementation\s+checklist/i;
            
            let docType = 'BRD';
            let docTitle = 'Business Requirements Document';
            
            if (prdPattern.test(output)) {
                docType = 'PRD';
                docTitle = 'Product Requirements Document';
            } else if (userStoriesPattern.test(output)) {
                docType = 'User Stories';
                docTitle = 'User Stories';
            } else if (implementationPattern.test(output)) {
                docType = 'Implementation';
                docTitle = 'Implementation Checklist';
            }
            
            documents.push({
                type: docType,
                title: docTitle,
                content: output.trim()
            });
        }
        
        return documents;
    }

    createDocumentCardsResponse(documents, modelInfo) {
        const cards = documents.map(doc => {
            const icon = doc.type === 'PRD' ? 
                '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/></svg>' :
                doc.type === 'BRD' ? 
                '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M19,3H5C3.9,3 3,3.9 3,5V19C3,20.1 3.9,21 5,21H19C20.1,21 21,20.1 21,19V5C21,3.9 20.1,3 19,3M19,19H5V5H19V19M17,12H7V10H17V12M15,16H7V14H15V16M17,8H7V6H17V8Z"/></svg>' :
                '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/></svg>';
            
            const shortTitle = doc.type === 'PRD' ? 'PRD' : doc.type === 'BRD' ? 'BRD' : 'Document';
            
            return `<span class="document-card hero-card" data-doc-type="${doc.type}"><span class="doc-icon">${icon}</span><span class="doc-info"><span class="doc-title">${shortTitle}</span></span></span>`;
        }).join('');

        return cards;
    }

    formatContent(content) {
        // Convert markdown to properly formatted HTML
        return content
            .replace(/^# (.+)$/gm, '<h1 class="doc-h1">$1</h1>')
            .replace(/^## (.+)$/gm, '<h2 class="doc-h2">$1</h2>')
            .replace(/^### (.+)$/gm, '<h3 class="doc-h3">$1</h3>')
            .replace(/^#### (.+)$/gm, '<h4 class="doc-h4">$1</h4>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/^- (.+)$/gm, '<li>$1</li>')
            .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
            .replace(/```([^`]+)```/g, '<pre><code>$1</code></pre>')
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            .replace(/\n\n/g, '</p><p>')
            .replace(/^(?!<[hul]|<\/[hul]|<pre>|<\/pre>)(.+)$/gm, '<p>$1</p>')
            .replace(/<p><h([1-6])/g, '<h$1')
            .replace(/<\/h([1-6])><\/p>/g, '</h$1>')
            .replace(/<p><ul>/g, '<ul>')
            .replace(/<\/ul><\/p>/g, '</ul>')
            .replace(/<p><pre>/g, '<pre>')
            .replace(/<\/pre><\/p>/g, '</pre>');
    }

    async sendMessage() {
        const chatInput = document.getElementById('chatInput');
        if (!chatInput) return;
        
        const userMessage = chatInput.value.trim();
        if (!userMessage) return;
        
        // Detect if the user is explicitly asking for the next stage (e.g., "Create PRD")
        this.autoAdvanceStageByKeywords(userMessage);

        // Add user message to chat
        const userChat = {
            type: 'user',
            content: userMessage,
            timestamp: new Date()
        };
        
        this.addMessage(userChat);
        chatInput.value = '';
        this.autoResizeTextarea(chatInput);

        await this.generateAIResponse(userMessage);
    }

    /**
     * Heuristically move to the appropriate stage when the user explicitly requests it
     * e.g. "Create PRD", "Generate user stories", etc.
     */
    autoAdvanceStageByKeywords(message) {
        const text = message.toLowerCase();
        const hasBRD = !!this.evolutionState.brd;
        const hasPRD = !!this.evolutionState.prd;
        // If still on BRD but user asks for PRD and we have a BRD, jump to stage 2
        if (this.evolutionState.currentStage === 1 && hasBRD && /\bprd\b/.test(text)) {
            this.evolutionState.currentStage = 2;
            this.saveEvolutionState();
            this.updateStageUI();
            return;
        }

        // If on PRD but user asks for user stories and PRD exists
        if (this.evolutionState.currentStage === 2 && hasPRD && /user\s*stories?/.test(text)) {
            this.evolutionState.currentStage = 3;
            this.saveEvolutionState();
            this.updateStageUI();
            return;
        }
    }

    async generateAIResponse(userMessage) {
        try {
            this.showTypingIndicator();
            
            // Add intelligent prompting for better responses
            const enhancedInstruction = this.enhanceInstruction(userMessage);
            
            let response;
            
            if (this.aiProvider.type === 'goose') {
                // Use Goose API
                const requestData = {
                    instruction: enhancedInstruction,
                    role: 'po'
                };
                
                response = await fetch('/api/goose/execute', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(requestData)
                });
            } else {
                // Use Model Garden API
                const requestData = {
                    instruction: enhancedInstruction,
                    model: this.aiProvider.model,
                    role: 'po'
                };
                
                response = await fetch('/api/model-garden/execute', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(requestData)
                });
            }
            
            this.hideTypingIndicator();
            
            if (!response.ok) {
                throw new Error(`API call failed: ${response.status}`);
            }
            
            const result = await response.json();
            
            let aiResponse = '';
            
            if (result.success) {
                let modelInfo;
                if (result.provider === 'model-garden') {
                    const displayName = this.getModelDisplayName(result.model);
                    modelInfo = `${displayName} (Model Garden)`;
                } else {
                    modelInfo = 'Gemini 2.5 Flash (Goose)';
                }


                // Check if this is a document creation response
                const documents = this.extractDocuments(result.output);
                
                if (documents.length > 0) {
                    // Store documents and create clean cards
                    this.documents = documents;
                    
                    // Store document in evolution state
                    this.storeDocumentInEvolutionState(documents[0], result.output);
                    
                    aiResponse = this.createDocumentCardsResponse(documents, modelInfo);
                    
                    // Show the hero card immediately (real document was generated)
                    const aiMessage = {
                        type: 'ai',
                        content: aiResponse,
                        timestamp: new Date(),
                        gooseResponse: result
                    };
                    
                    this.addMessage(aiMessage);
                    
                    // THEN do smooth transition to split screen
                    setTimeout(() => {
                        this.showSplitScreen();
                        this.updateContentPanel(documents[0]);
                        this.updateStageUI();
                    }, 500);
                    
                    return; // Exit early
                } else {
                    // Regular chat response - either conversation or other response
                    aiResponse = `${result.output}

---
*${modelInfo}*`;
                    
                    // Smart approach: conversation for vague inputs, documents for detailed inputs
                    console.log('Conversation mode: AI is gathering information or responding naturally');
                }
            } else {
                aiResponse = `**❌ Error:**

${result.error}

Please try rephrasing your request or ask for help with a specific product management task.`;
            }
            
            const aiMessage = {
                type: 'ai',
                content: aiResponse,
                timestamp: new Date(),
                gooseResponse: result
            };
            
            this.addMessage(aiMessage);
            
        } catch (error) {
            this.hideTypingIndicator();
            
            const errorMessage = {
                type: 'ai',
                content: `**🔌 Connection Error:**

Unable to connect to the Product Owner AI backend.

**Technical Details:** ${error.message}

**Fallback Actions:**
1. Verify the Software Factory server is running
2. Check your network connection
3. Try refreshing the page

While waiting, you can still use the context panel to organize your product information.`,
                timestamp: new Date(),
                error: error.message
            };
            
            this.addMessage(errorMessage);
        }
    }

    addMessage(message) {
        this.chatHistory.push(message);
        this.renderMessage(message);
        this.scrollToBottom();
    }

    renderMessage(message) {
        const messagesContainer = document.getElementById('chatMessages');
        const messageElement = document.createElement('div');
        
        messageElement.className = `message ${message.type}-message`;
        
        // Show avatar for AI messages (but not for special content types)
        const hasHeroCard = message.content && message.content.includes('hero-card');
        const hasGeneratingProcess = message.content && message.content.includes('generating-process');
        
        if ((message.type === 'ai' || message.type === 'system') && !hasHeroCard && !hasGeneratingProcess) {
            const avatar = document.createElement('div');
            avatar.className = 'message-avatar';
            
            if (message.type === 'system') {
                // Use a system/workflow icon for system messages
                avatar.innerHTML = '⚙️';
                avatar.style.display = 'flex';
                avatar.style.alignItems = 'center';
                avatar.style.justifyContent = 'center';
                avatar.style.fontSize = '16px';
            } else {
                // Show model-specific icon based on provider
                const avatarImg = document.createElement('img');
                if (this.aiProvider.type === 'goose') {
                    avatarImg.src = 'images/goose.png';
                    avatarImg.alt = 'Goose AI';
                    console.log('Setting Goose avatar');
                } else {
                    avatarImg.src = 'images/coforge.png';
                    avatarImg.alt = 'Coforge AI';
                    console.log('Setting Coforge avatar');
                }
                avatarImg.style.width = '100%';
                avatarImg.style.height = '100%';
                avatarImg.style.objectFit = 'cover';
                
                // Debug image loading
                avatarImg.onload = () => console.log('Avatar image loaded successfully:', avatarImg.src);
                avatarImg.onerror = () => console.error('Failed to load avatar image:', avatarImg.src);
                
                avatar.appendChild(avatarImg);
            }
            
            messageElement.appendChild(avatar);
        }
        
        const content = document.createElement('div');
        content.className = 'message-content';
        
        const formattedContent = this.formatMessageContent(message.content);
        content.innerHTML = formattedContent;
        
        // Add click handlers for document cards
        const documentCards = content.querySelectorAll('.document-card');
        documentCards.forEach(card => {
            card.addEventListener('click', (e) => {
                const docType = card.getAttribute('data-doc-type');
                const docData = this.documents.find(doc => doc.type === docType);
                if (docData) {
                    this.showSplitScreen();
                    this.updateContentPanel(docData);
                }
            });
        });
        
        const timestamp = document.createElement('div');
        timestamp.className = 'message-timestamp';
        timestamp.textContent = this.formatTimestamp(message.timestamp);
        
        messageElement.appendChild(content);
        content.appendChild(timestamp);
        
        messagesContainer.appendChild(messageElement);
    }

    formatMessageContent(content) {
        return content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/•/g, '•')
            .replace(/\n/g, '<br>');
    }

    formatTimestamp(timestamp) {
        return timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    showTypingIndicator() {
        const messagesContainer = document.getElementById('chatMessages');
        
        const typingElement = document.createElement('div');
        typingElement.className = 'message ai-message typing-indicator';
        typingElement.id = 'typingIndicator';
        
        const content = document.createElement('div');
        content.className = 'message-content';
        content.innerHTML = `<div class="generating-process">
            <div class="generation-header">
                <div class="generation-spinner"></div>
                <span class="generation-title">Generating document...</span>
            </div>
            <div class="generation-progress">
                <div class="progress-bar">
                    <div class="progress-fill"></div>
                </div>
                <span class="progress-text">Creating enhanced document with your expertise...</span>
            </div>
        </div>`;
        
        typingElement.appendChild(content);
        
        messagesContainer.appendChild(typingElement);
        this.scrollToBottom();
        
        // Start progress animation for real API call
        setTimeout(() => {
            const progressFill = document.querySelector('#typingIndicator .progress-fill');
            if (progressFill) {
                progressFill.style.width = '90%'; // Leave some room until actual completion
            }
        }, 300);
    }

    hideTypingIndicator() {
        // Clear processing steps interval
        if (this.processingInterval) {
            clearInterval(this.processingInterval);
            this.processingInterval = null;
        }
        
        const typingIndicator = document.getElementById('typingIndicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }

    scrollToBottom() {
        const messagesContainer = document.getElementById('chatMessages');
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    autoResizeTextarea(textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    }

    // Removed old methods for simplified interface

    // AI Provider Management Methods
    getModelDisplayName(modelId) {
        const modelNames = {
            'claude-opus-4': 'Claude Opus 4',
            'gemini-2-5-flash': 'Gemini 2.5 Flash',
            'gpt-4o': 'GPT-4o',
            'claude-sonnet-3-5': 'Claude Sonnet 3.5'
        };
        return modelNames[modelId] || modelId;
    }

    loadAIProvider() {
        const saved = localStorage.getItem('aiProvider');
        if (saved) {
            this.aiProvider = JSON.parse(saved);
            console.log('Loaded AI provider from localStorage:', this.aiProvider);
            this.updateAIProviderUI();
        } else {
            console.log('No saved AI provider, using default:', this.aiProvider);
        }
    }

    saveAIProvider() {
        localStorage.setItem('aiProvider', JSON.stringify(this.aiProvider));
    }

    selectAIProvider(type) {
        this.aiProvider.type = type;
        console.log('AI provider changed to:', type);
        this.saveAIProvider();
        this.updateAIProviderUI();
    }

    updateModel(model) {
        this.aiProvider.model = model;
        this.saveAIProvider();
    }

    updateAIProviderUI() {
        // Update provider selection dropdown
        const providerSelect = document.getElementById('aiProviderSelect');
        if (providerSelect) {
            providerSelect.value = this.aiProvider.type;
        }

        // Show/hide model selection dropdown
        const modelSelect = document.getElementById('modelSelect');
        if (this.aiProvider.type === 'model-garden') {
            modelSelect?.classList.remove('hidden');
            if (modelSelect) modelSelect.value = this.aiProvider.model;
        } else {
            modelSelect?.classList.add('hidden');
        }
        
        // Update new AI model selector
        this.updateModelSelectorUI();
    }
    
    // New AI Model Selector Methods - Minimal Floating Interface
    showModelPopup(clickedProvider) {
        const popup = document.getElementById('modelPopup');
        if (popup) {
            popup.classList.remove('hidden');
            
            // Update active states in popup
            this.updatePopupActiveStates();
        }
    }
    
    hideModelPopup() {
        const popup = document.getElementById('modelPopup');
        if (popup) {
            popup.classList.add('hidden');
        }
    }
    
    selectModelFromPopup(provider, model) {
        if (provider === 'goose') {
            this.aiProvider.type = 'goose';
        } else if (provider === 'ai-studio') {
            this.aiProvider.type = 'model-garden';
            this.aiProvider.model = model;
        }
        
        this.saveAIProvider();
        this.updateFloatingLogos();
        this.updatePopupActiveStates();
        this.hideModelPopup();
        
        console.log('Model selected:', provider, model, 'AI Provider:', this.aiProvider);
    }
    
    updateFloatingLogos() {
        const gooseProvider = document.getElementById('gooseProvider');
        const aiStudioProvider = document.getElementById('aiStudioProvider');
        
        // Update active states
        if (this.aiProvider.type === 'goose') {
            gooseProvider?.classList.add('active');
            aiStudioProvider?.classList.remove('active');
        } else if (this.aiProvider.type === 'model-garden') {
            gooseProvider?.classList.remove('active');
            aiStudioProvider?.classList.add('active');
        }
    }
    
    updatePopupActiveStates() {
        // Update active states in popup
        document.querySelectorAll('.model-item').forEach(item => {
            const provider = item.getAttribute('data-provider');
            const model = item.getAttribute('data-model');
            
            if (provider === 'goose' && this.aiProvider.type === 'goose') {
                item.classList.add('active');
            } else if (provider === 'ai-studio' && this.aiProvider.type === 'model-garden' && model === this.aiProvider.model) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });
    }
    
    updateModelSelectorUI() {
        // Update the floating logos
        this.updateFloatingLogos();
        this.updatePopupActiveStates();
    }


    // Document Management Methods
    saveDocument() {
        const markdownEditor = document.getElementById('markdownEditor');
        
        if (markdownEditor) {
            const content = markdownEditor.value;
            const title = 'Document';
            
            // Create a blob and download
            const blob = new Blob([content], { type: 'text/markdown' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${title.replace(/[^a-zA-Z0-9]/g, '_')}.md`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
    }

    exportDocument() {
        const markdownEditor = document.getElementById('markdownEditor');
        
        if (markdownEditor) {
            const content = markdownEditor.value;
            const title = 'Document';
            
            const blob = new Blob([content], { type: 'text/markdown' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${title.replace(/[^a-zA-Z0-9]/g, '_')}.md`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
    }

    // Split Screen Methods
    setupSplitDivider() {
        const divider = document.getElementById('splitDivider');
        if (!divider) return;
        
        let isResizing = false;
        let startX = 0;
        let startLeftWidth = 0;
        
        divider.addEventListener('mousedown', (e) => {
            isResizing = true;
            startX = e.clientX;
            
            const workspace = document.querySelector('.po-workspace');
            const chatInterface = document.querySelector('.chat-interface');
            const rect = workspace.getBoundingClientRect();
            const chatRect = chatInterface.getBoundingClientRect();
            
            startLeftWidth = ((chatRect.width / rect.width) * 100);
            
            divider.classList.add('dragging');
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
            
            // Add overlay to prevent iframe interference
            const overlay = document.createElement('div');
            overlay.id = 'resize-overlay';
            overlay.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: transparent;
                z-index: 9999;
                cursor: col-resize;
            `;
            document.body.appendChild(overlay);
            
            e.preventDefault();
        });
        
        document.addEventListener('mousemove', (e) => {
            if (!isResizing) return;
            
            const workspace = document.querySelector('.po-workspace');
            const rect = workspace.getBoundingClientRect();
            const deltaX = e.clientX - startX;
            const deltaPercentage = (deltaX / rect.width) * 100;
            
            let newLeftWidth = startLeftWidth + deltaPercentage;
            
            // Constrain between 25% and 75%
            newLeftWidth = Math.max(25, Math.min(75, newLeftWidth));
            const newRightWidth = 100 - newLeftWidth;
            
            const chatInterface = document.querySelector('.chat-interface');
            const documentPanel = document.querySelector('.document-panel');
            
            if (chatInterface && documentPanel) {
                chatInterface.style.flex = `0 0 ${newLeftWidth}%`;
                documentPanel.style.flex = `0 0 ${newRightWidth}%`;
            }
        });
        
        document.addEventListener('mouseup', () => {
            if (isResizing) {
                isResizing = false;
                divider.classList.remove('dragging');
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
                
                // Remove overlay
                const overlay = document.getElementById('resize-overlay');
                if (overlay) {
                    overlay.remove();
                }
            }
        });
    }
    
    setupViewModes() {
        const markdownEditor = document.getElementById('markdownEditor');
        if (markdownEditor) {
            markdownEditor.addEventListener('input', (e) => {
                this.updatePreview(e.target.value);
            });
        }
    }
    
    switchToCodeView() {
        const codeView = document.getElementById('codeView');
        const previewView = document.getElementById('previewView');
        const codeBtn = document.getElementById('codeViewBtn');
        const previewBtn = document.getElementById('previewViewBtn');
        
        if (codeView && previewView) {
            codeView.classList.remove('hidden');
            previewView.classList.add('hidden');
            
            // Update pill buttons
            codeBtn?.classList.add('active');
            previewBtn?.classList.remove('active');
        }
    }
    
    // Remove split view method since we only have CODE and PREVIEW now
    
    switchToPreviewView() {
        const codeView = document.getElementById('codeView');
        const previewView = document.getElementById('previewView');
        const codeBtn = document.getElementById('codeViewBtn');
        const previewBtn = document.getElementById('previewViewBtn');
        
        if (codeView && previewView) {
            codeView.classList.add('hidden');
            previewView.classList.remove('hidden');
            
            // Update pill buttons
            codeBtn?.classList.remove('active');
            previewBtn?.classList.add('active');
        }
    }
    
    updatePreview(markdownContent) {
        const renderedContent = document.getElementById('renderedContent');
        if (!renderedContent) return;
        
        // Simple markdown to HTML conversion
        const html = this.markdownToHTML(markdownContent);
        renderedContent.innerHTML = html;
    }
    
    markdownToHTML(markdown) {
        return markdown
            // Headers
            .replace(/^### (.*$)/gm, '<h3>$1</h3>')
            .replace(/^## (.*$)/gm, '<h2>$1</h2>')
            .replace(/^# (.*$)/gm, '<h1>$1</h1>')
            // Bold and italic
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            // Lists
            .replace(/^\s*\* (.+)$/gm, '<li>$1</li>')
            .replace(/^\s*- (.+)$/gm, '<li>$1</li>')
            .replace(/^\s*\d+\. (.+)$/gm, '<li>$1</li>')
            // Code blocks
            .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            // Line breaks
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>')
            // Wrap in paragraphs
            .replace(/^(?!<[hul]|<\/[hul]|<pre>|<\/pre>)(.+)$/gm, '<p>$1</p>')
            // Clean up lists
            .replace(/(<li>.*<\/li>)/s, (match) => {
                if (match.includes('<li>') && !match.startsWith('<ul>') && !match.startsWith('<ol>')) {
                    return '<ul>' + match + '</ul>';
                }
                return match;
            })
            // Clean up paragraphs around headers
            .replace(/<p>(<h[1-6]>.*<\/h[1-6]>)<\/p>/g, '$1')
            .replace(/<p>(<ul>.*<\/ul>)<\/p>/g, '$1')
            .replace(/<p>(<ol>.*<\/ol>)<\/p>/g, '$1')
            .replace(/<p>(<pre>.*<\/pre>)<\/p>/g, '$1');
    }
    
    // Document Toolbar Methods
    updateDocumentStats() {
        const markdownEditor = document.getElementById('markdownEditor');
        const wordCount = document.getElementById('wordCount');
        const charCount = document.getElementById('charCount');
        
        if (markdownEditor && wordCount && charCount) {
            const text = markdownEditor.value || '';
            const words = text.trim().split(/\s+/).filter(word => word.length > 0).length;
            const characters = text.length;
            
            wordCount.textContent = `${words} words`;
            charCount.textContent = `${characters} characters`;
        }
    }

    showHistory() {
        alert('Document history will show previous versions and changes.');
    }

    improveDocument() {
        alert('AI-powered document improvement coming soon!');
    }

    changeFormat(format) {
        // Format selection logic
        console.log('Format changed to:', format);
    }

    aiAssist() {
        alert('AI assistant for document editing coming soon!');
    }

    toggleBold() {
        document.execCommand('bold', false, null);
        this.updateFormatButtons();
    }

    toggleItalic() {
        document.execCommand('italic', false, null);
        this.updateFormatButtons();
    }

    toggleUnderline() {
        document.execCommand('underline', false, null);
        this.updateFormatButtons();
    }

    toggleList() {
        document.execCommand('insertUnorderedList', false, null);
        this.updateFormatButtons();
    }

    toggleNumberedList() {
        document.execCommand('insertOrderedList', false, null);
        this.updateFormatButtons();
    }

    toggleChecklist() {
        alert('Checklist formatting coming soon!');
    }

    updateFormatButtons() {
        // Update button states based on current selection
        const boldBtn = document.getElementById('boldBtn');
        const italicBtn = document.getElementById('italicBtn');
        const underlineBtn = document.getElementById('underlineBtn');

        if (boldBtn) boldBtn.classList.toggle('active', document.queryCommandState('bold'));
        if (italicBtn) italicBtn.classList.toggle('active', document.queryCommandState('italic'));
        if (underlineBtn) underlineBtn.classList.toggle('active', document.queryCommandState('underline'));
    }

    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    smoothTransitionToSplitScreen(document) {
        // Start transition
        this.showSplitScreen();
        
        // Update content with a slight delay for smoothness
        setTimeout(() => {
            this.updateContentPanel(document);
        }, 300);
    }
    
    // Stage progression methods
    storeDocumentInEvolutionState(document, fullContent) {
        const stage = this.evolutionState.currentStage;
        
        switch(stage) {
            case 1:
                this.evolutionState.brd = fullContent;
                break;
            case 2:
                this.evolutionState.prd = fullContent;
                break;
            case 3:
                this.evolutionState.userStories = fullContent;
                break;
            case 4:
                this.evolutionState.implementationChecklist = fullContent;
                break;
        }
        
        // Mark current stage as completed
        if (!this.evolutionState.completedStages.includes(stage)) {
            this.evolutionState.completedStages.push(stage);
        }
        
        this.saveEvolutionState();
    }
    
    approveCurrentStage() {
        const currentStage = this.evolutionState.currentStage;
        const hasDocument = this.hasDocumentForStage(currentStage);
        
        if (!hasDocument) {
            // Generate the document for the current stage
            this.generateDocumentForCurrentStage();
            return;
        }
        
        // Mark stage as approved and move to next
        if (!this.evolutionState.completedStages.includes(currentStage)) {
            this.evolutionState.completedStages.push(currentStage);
        }
        
        if (currentStage < 4) {
            this.moveToNextStage();
        } else {
            this.showMessage('🎉 Workflow complete! Your implementation checklist is ready for development.');
        }
    }
    
    generateDocumentForCurrentStage() {
        const currentStage = this.stages[this.evolutionState.currentStage];
        
        // Check if we have adequate information from previous stages or stored specs
        let prompt = '';
        
        if (this.evolutionState.currentStage === 1 && this.evolutionState.businessSpecs) {
            // Use stored business specs for BRD
            prompt = this.getBRDPrompt(this.evolutionState.businessSpecs);
        } else if (this.evolutionState.currentStage > 1) {
            // Use previous stage document
            prompt = this.getPromptForStage(this.evolutionState.currentStage);
        } else {
            // No adequate information - ask user to provide specs first
            this.showMessage(`Please provide detailed information about your project before generating the ${currentStage.title}. I need to understand your business requirements, target users, and core functionality.`);
            return;
        }
        
        // Trigger AI generation with proper prompt
        this.generateAIResponse(prompt);
    }
    
    getPromptForStage(stage) {
        switch(stage) {
            case 2: return this.getPRDPrompt('');
            case 3: return this.getUserStoriesPrompt('');
            case 4: return this.getImplementationPrompt('');
            default: return `Generate ${this.stages[stage].title} based on previous work`;
        }
    }
    
    moveToNextStage() {
        if (this.evolutionState.currentStage < 4) {
            this.evolutionState.currentStage += 1;
            this.saveEvolutionState();
            this.updateStageUI();
            this.showStageTransitionMessage();
        }
    }
    
    moveToPreviousStage() {
        if (this.evolutionState.currentStage > 1) {
            this.evolutionState.currentStage -= 1;
            this.saveEvolutionState();
            this.updateStageUI();
            this.showStageTransitionMessage();
        }
    }
    
    hasDocumentForStage(stage) {
        switch(stage) {
            case 1: return !!this.evolutionState.brd;
            case 2: return !!this.evolutionState.prd;
            case 3: return !!this.evolutionState.userStories;
            case 4: return !!this.evolutionState.implementationChecklist;
            default: return false;
        }
    }
    
    updateStageUI() {
        // Update stage indicator in the UI
        const currentStage = this.stages[this.evolutionState.currentStage];

        // Refresh compact progress bar at top of chat interface
        const progressBar = document.getElementById('stageProgressBar');
        if (progressBar) {
            progressBar.innerHTML = this.renderStageProgress();
        }

        // Update document title if in split screen
        const documentTitle = document.getElementById('documentTitle');
        if (documentTitle && this.isSplitScreen) {
            documentTitle.textContent = currentStage.title;
        }
        
        // Update stage progression buttons
        this.updateStageButtons();
        
        // Add stage progression indicator to welcome message if not in split screen
        if (!this.isSplitScreen) {
            this.updateWelcomeMessage();
        }
    }
    
    updateStageButtons() {
        const previousBtn = document.getElementById('previousStage');
        const approveBtn = document.getElementById('approveStage');
        const nextBtn = document.getElementById('nextStage');
        
        if (previousBtn && approveBtn && nextBtn) {
            // Enable/disable previous button
            previousBtn.disabled = this.evolutionState.currentStage <= 1;
            
            // Enable/disable next button
            nextBtn.disabled = this.evolutionState.currentStage >= 4;
            
            // Update approve button text based on stage
            const currentStage = this.stages[this.evolutionState.currentStage];
            const hasDocument = this.hasDocumentForStage(this.evolutionState.currentStage);
            
            if (this.evolutionState.currentStage === 4) {
                approveBtn.textContent = hasDocument ? 'Complete Workflow' : 'Generate Implementation';
            } else {
                approveBtn.textContent = hasDocument ? `Approve ${currentStage.name} & Continue` : `Generate ${currentStage.name}`;
            }
            
            // Show/hide stage controls only in split screen
            const stageControls = document.getElementById('stageControls');
            if (stageControls) {
                stageControls.style.display = this.isSplitScreen ? 'flex' : 'none';
            }
        }
    }
    
    updateWelcomeMessage() {
        const welcomeMessage = document.querySelector('.welcome-message');
        const currentStage = this.stages[this.evolutionState.currentStage];
        
        if (welcomeMessage) {
            // Keep the hero question only – progress now shown in compact bar
            welcomeMessage.innerHTML = `<h1>What will you build today?</h1>`;
        }
    }
    
    renderStageProgress() {
        let progressHTML = '<div class="progress-dots">';
        
        for (let i = 1; i <= 4; i++) {
            const isCompleted = this.evolutionState.completedStages.includes(i);
            const isCurrent = this.evolutionState.currentStage === i;
            const stageClass = isCompleted ? 'completed' : (isCurrent ? 'current' : 'pending');
            
            progressHTML += `<div class="progress-dot ${stageClass}" title="${this.stages[i].name}"></div>`;
        }
        
        progressHTML += '</div>';
        return progressHTML;
    }
    
    showStageTransitionMessage() {
        const currentStage = this.stages[this.evolutionState.currentStage];
        
        const transitionMessage = {
            type: 'system',
            content: `**Stage ${this.evolutionState.currentStage}: ${currentStage.title}**\n\n${currentStage.description}\n\nYou can now create the ${currentStage.name} by providing your requirements.`,
            timestamp: new Date()
        };
        
        this.addMessage(transitionMessage);
    }
    
    showMessage(message) {
        const systemMessage = {
            type: 'system',
            content: message,
            timestamp: new Date()
        };
        
        this.addMessage(systemMessage);
    }
    
    saveEvolutionState() {
        localStorage.setItem('evolutionState', JSON.stringify(this.evolutionState));
    }
    
    loadEvolutionState() {
        const saved = localStorage.getItem('evolutionState');
        if (saved) {
            this.evolutionState = JSON.parse(saved);
        }
    }
    
    isAskingForMoreInformation(aiResponse) {
        // Check if the AI response contains questions or requests for more information
        const questionPatterns = [
            /\?\s*$/m,  // Ends with question mark
            /\?.*\n/m,  // Question mark followed by newline
            /could you.*\?/i,
            /can you.*\?/i,
            /would you.*\?/i,
            /what.*\?/i,
            /how.*\?/i,
            /when.*\?/i,
            /where.*\?/i,
            /why.*\?/i,
            /which.*\?/i,
            /please provide/i,
            /please tell me/i,
            /i need.*information/i,
            /i'd like to know/i,
            /could you elaborate/i,
            /more details/i,
            /tell me more/i,
            /clarify/i,
            /specify/i,
            /help me understand/i,
            /let me know/i,
            /i'd be happy to help.*if you could/i,
            /to better assist you/i,
            /before i can create/i,
            /before generating/i,
            /first.*tell me/i,
            /need to understand/i
        ];
        
        // Also check if response is conversational (not a formal document)
        const isConversational = !/^#\s+/m.test(aiResponse) && // No markdown headers
                                 !/^\d+\.|^-\s+|^\*\s+/m.test(aiResponse.split('\n').slice(0, 3).join('\n')); // No immediate structure
        
        return questionPatterns.some(pattern => pattern.test(aiResponse)) || isConversational;
    }
}

// Initialize the Product Owner Assistant
document.addEventListener('DOMContentLoaded', () => {
    new ProductOwnerAssistant();
});