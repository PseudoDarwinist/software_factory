// Software Factory - Business Process Designer
// Enterprise Chat-Focused Interface

class BusinessProcessDesigner {
    constructor() {
        this.businessContext = {
            domain: '',
            useCase: '',
            targetAudience: '',
            keyRequirements: '',
            successMetrics: ''
        };
        
        this.githubRepo = {
            connected: false,
            url: '',
            name: '',
            branch: '',
            token: ''
        };
        
        this.aiProvider = {
            type: 'goose', // 'goose' or 'model-garden'
            model: 'claude-opus-4' // for model-garden
        };
        
        this.chatHistory = [];
        this.isTyping = false;
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.initializeChat();
        this.loadBusinessContext();
        this.loadGithubRepo();
        this.loadAIProvider();
    }

    setupEventListeners() {
        // Business Context Form
        document.getElementById('businessDomain')?.addEventListener('input', (e) => this.updateContext('domain', e.target.value));
        document.getElementById('useCase')?.addEventListener('input', (e) => this.updateContext('useCase', e.target.value));
        document.getElementById('targetAudience')?.addEventListener('input', (e) => this.updateContext('targetAudience', e.target.value));
        document.getElementById('keyRequirements')?.addEventListener('input', (e) => this.updateContext('keyRequirements', e.target.value));
        document.getElementById('successMetrics')?.addEventListener('input', (e) => this.updateContext('successMetrics', e.target.value));
        
        // Context Save
        document.querySelector('.context-save')?.addEventListener('click', () => this.saveBusinessContext());
        
        // Chat Interface
        document.getElementById('sendMessage')?.addEventListener('click', () => this.sendMessage());
        document.getElementById('chatInput')?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Input Actions
        document.getElementById('voiceInput')?.addEventListener('click', () => this.startVoiceInput());
        document.getElementById('attachFile')?.addEventListener('click', () => this.attachFile());

        // Quick Suggestions
        document.querySelectorAll('.suggestion-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.handleSuggestion(e.target.textContent));
        });

        // Header Actions
        document.getElementById('exportChat')?.addEventListener('click', () => this.exportChat());
        document.getElementById('generatePrototype')?.addEventListener('click', () => this.generatePrototype());

        // Auto-resize chat input
        document.getElementById('chatInput')?.addEventListener('input', (e) => this.autoResizeTextarea(e.target));
        
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
        
        // GitHub Integration
        document.getElementById('connectRepo')?.addEventListener('click', () => this.showGithubForm());
        document.getElementById('saveRepo')?.addEventListener('click', () => this.connectGithubRepo());
        document.getElementById('cancelConnect')?.addEventListener('click', () => this.hideGithubForm());
        document.getElementById('disconnectRepo')?.addEventListener('click', () => this.disconnectGithubRepo());
    }

    initializeChat() {
        const welcomeMessage = {
            type: 'ai',
            content: `**Welcome to Software Factory!**

I'll help you design your business process. Let's start by understanding what you want to build.

**For example:**
*"I need a system that automatically notifies passengers when their flights are delayed or cancelled, sending personalized messages via email and SMS with rebooking options."*

Fill out the business context on the left, then describe your process here.`,
            timestamp: new Date()
        };
        
        this.addMessage(welcomeMessage);
    }

    updateContext(field, value) {
        this.businessContext[field] = value;
        this.autoSaveContext();
    }

    autoSaveContext() {
        // Auto-save context to localStorage
        clearTimeout(this.saveTimeout);
        this.saveTimeout = setTimeout(() => {
            localStorage.setItem('businessContext', JSON.stringify(this.businessContext));
        }, 1000);
    }

    saveBusinessContext() {
        localStorage.setItem('businessContext', JSON.stringify(this.businessContext));
        this.showNotification('Business context saved!', 'success');
        
        // Add context to chat
        if (this.hasValidContext()) {
            const contextMessage = {
                type: 'system',
                content: `**Business Context Updated:**
                
**Domain:** ${this.businessContext.domain}
**Use Case:** ${this.businessContext.useCase}
**Target Audience:** ${this.businessContext.targetAudience}
**Key Requirements:** ${this.businessContext.keyRequirements}
**Success Metrics:** ${this.businessContext.successMetrics}`,
                timestamp: new Date()
            };
            this.addMessage(contextMessage);
        }
    }

    loadBusinessContext() {
        const saved = localStorage.getItem('businessContext');
        if (saved) {
            this.businessContext = JSON.parse(saved);
            
            // Populate form fields
            document.getElementById('businessDomain').value = this.businessContext.domain || '';
            document.getElementById('useCase').value = this.businessContext.useCase || '';
            document.getElementById('targetAudience').value = this.businessContext.targetAudience || '';
            document.getElementById('keyRequirements').value = this.businessContext.keyRequirements || '';
            document.getElementById('successMetrics').value = this.businessContext.successMetrics || '';
        }
    }

    hasValidContext() {
        return this.businessContext.domain && this.businessContext.useCase;
    }

    async sendMessage() {
        const input = document.getElementById('chatInput');
        const message = input.value.trim();
        
        if (!message) return;

        // Add user message
        const userMessage = {
            type: 'user',
            content: message,
            timestamp: new Date()
        };
        
        this.addMessage(userMessage);
        input.value = '';
        this.autoResizeTextarea(input);

        // Show typing indicator
        this.showTypingIndicator();

        // Simulate AI response
        await this.generateAIResponse(message);
    }

    async generateAIResponse(userMessage) {
        try {
            // Show typing indicator while processing
            this.showTypingIndicator();
            
            // Prepare request data with business context, GitHub repo, and role
            const requestData = {
                instruction: userMessage,
                businessContext: this.businessContext,
                githubRepo: this.githubRepo.connected ? this.githubRepo : null,
                role: 'business'
            };
            
            let response;
            
            if (this.aiProvider.type === 'goose') {
                // Use Goose API
                response = await fetch('/api/goose/execute', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(requestData)
                });
            } else {
                // Use Model Garden API
                requestData.model = this.aiProvider.model;
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
                
                // Use the clean response
                aiResponse = `${result.output}

---
*AI-powered analysis with ${modelInfo}*`;
            } else {
                // Handle errors gracefully
                aiResponse = `**❌ AI Analysis Error:**

I encountered an issue while processing your request:
${result.error}

**Fallback Suggestion:**
Please try rephrasing your request or check that your business context is filled out on the left panel.

**Quick Actions:**
• Refine your question to be more specific
• Add more details in the business context fields
• Try a simpler request first

Would you like me to help you rephrase your request?`;
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
            
            // Handle network errors
            const errorMessage = {
                type: 'ai',
                content: `**🔌 Connection Error:**

I'm having trouble connecting to the AI backend. This might be because:

• The server is starting up (please wait a moment)
• Network connectivity issues
• The Goose integration needs configuration

**Technical Details:** ${error.message}

**What to try:**
1. Wait a few seconds and try again
2. Check that the server is running
3. Refresh the page if the issue persists

I'll fall back to basic assistance while the connection is restored.`,
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
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = message.type === 'user' ? '👤' : '🤖';
        
        const content = document.createElement('div');
        content.className = 'message-content';
        
        // Convert markdown-style formatting to HTML
        const formattedContent = this.formatMessageContent(message.content);
        content.innerHTML = formattedContent;
        
        const timestamp = document.createElement('div');
        timestamp.className = 'message-timestamp';
        timestamp.textContent = this.formatTimestamp(message.timestamp);
        
        messageElement.appendChild(avatar);
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
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = '🤖';
        
        const content = document.createElement('div');
        content.className = 'message-content';
        content.innerHTML = '<p>Thinking...</p>';
        
        typingElement.appendChild(avatar);
        typingElement.appendChild(content);
        
        messagesContainer.appendChild(typingElement);
        this.scrollToBottom();
    }

    hideTypingIndicator() {
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

    handleSuggestion(suggestion) {
        const input = document.getElementById('chatInput');
        
        if (suggestion.includes('improvements')) {
            input.value = 'Can you suggest improvements to my current process design?';
        } else if (suggestion.includes('requirements')) {
            input.value = 'Help me refine and add more detailed requirements to my process.';
        } else if (suggestion.includes('acceptance criteria')) {
            input.value = 'What acceptance criteria should I define for this process?';
        }
        
        this.autoResizeTextarea(input);
        input.focus();
    }

    startVoiceInput() {
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            this.showNotification('Speech recognition not supported in this browser', 'error');
            return;
        }

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const recognition = new SpeechRecognition();
        
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';

        recognition.onstart = () => {
            this.showNotification('Listening...', 'info');
        };

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            document.getElementById('chatInput').value = transcript;
            this.autoResizeTextarea(document.getElementById('chatInput'));
        };

        recognition.onerror = (event) => {
            this.showNotification('Speech recognition error: ' + event.error, 'error');
        };

        recognition.start();
    }

    attachFile() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.txt,.doc,.docx,.pdf';
        
        input.onchange = (e) => {
            const file = e.target.files[0];
            if (file) {
                this.showNotification(`File "${file.name}" ready to upload`, 'success');
                // In a real implementation, you'd upload the file here
            }
        };
        
        input.click();
    }

    exportChat() {
        const chatData = {
            businessContext: this.businessContext,
            chatHistory: this.chatHistory,
            exportDate: new Date()
        };
        
        const dataStr = JSON.stringify(chatData, null, 2);
        const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
        
        const exportFileDefaultName = `business-process-${Date.now()}.json`;
        
        const linkElement = document.createElement('a');
        linkElement.setAttribute('href', dataUri);
        linkElement.setAttribute('download', exportFileDefaultName);
        linkElement.click();
        
        this.showNotification('Chat exported successfully!', 'success');
    }

    generatePrototype() {
        if (!this.hasValidContext()) {
            this.showNotification('Please fill out business context first', 'warning');
            return;
        }

        this.showNotification('Generating prototype... (Feature coming soon)', 'info');
        
        // In a real implementation, this would integrate with JACoB
        const prototypeMessage = {
            type: 'system',
            content: `**🚀 Prototype Generation Initiated**

Based on your business context and requirements, I would now:

1. **Analyze** your process description
2. **Generate** wireframes and user flows  
3. **Create** interactive prototypes
4. **Integrate** with development workflow

*This feature will be available when JACoB integration is complete.*`,
            timestamp: new Date()
        };
        
        this.addMessage(prototypeMessage);
    }

    showNotification(message, type = 'info') {
        // Simple notification system
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        
        notification.style.cssText = `
            position: fixed;
            top: 100px;
            right: 20px;
            padding: 12px 20px;
            border-radius: 12px;
            background: var(--liquid-glass-primary);
            backdrop-filter: var(--glass-blur);
            border: 1px solid var(--liquid-glass-border);
            color: var(--text-primary);
            z-index: 10000;
            box-shadow: var(--depth-3);
            animation: slideIn 0.3s ease;
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    // GitHub Integration Methods
    loadGithubRepo() {
        const saved = localStorage.getItem('githubRepo');
        if (saved) {
            this.githubRepo = JSON.parse(saved);
            this.updateGithubUI();
        }
    }

    saveGithubRepo() {
        localStorage.setItem('githubRepo', JSON.stringify(this.githubRepo));
    }

    showGithubForm() {
        document.getElementById('githubForm').classList.remove('hidden');
        document.getElementById('githubStatus').classList.add('hidden');
    }

    hideGithubForm() {
        document.getElementById('githubForm').classList.add('hidden');
        document.getElementById('githubStatus').classList.remove('hidden');
        
        // Clear form
        document.getElementById('repoUrl').value = '';
        document.getElementById('githubToken').value = '';
    }

    async connectGithubRepo() {
        const repoUrl = document.getElementById('repoUrl').value.trim();
        const githubToken = document.getElementById('githubToken').value.trim();

        if (!repoUrl) {
            this.showNotification('Please enter a repository URL', 'error');
            return;
        }

        // Validate GitHub URL format
        const githubUrlPattern = /^https:\/\/github\.com\/[\w\-\.]+\/[\w\-\.]+\/?$/;
        if (!githubUrlPattern.test(repoUrl)) {
            this.showNotification('Please enter a valid GitHub repository URL', 'error');
            return;
        }

        try {
            // Extract repo info from URL
            const urlParts = repoUrl.replace('https://github.com/', '').replace('.git', '').split('/');
            const owner = urlParts[0];
            const repoName = urlParts[1];

            // Test GitHub API connection
            const apiUrl = `https://api.github.com/repos/${owner}/${repoName}`;
            const headers = {};
            if (githubToken) {
                headers['Authorization'] = `token ${githubToken}`;
            }

            const response = await fetch(apiUrl, { headers });
            
            if (!response.ok) {
                if (response.status === 404) {
                    throw new Error('Repository not found or private. Check URL and token.');
                } else if (response.status === 401) {
                    throw new Error('Invalid GitHub token.');
                } else {
                    throw new Error('Failed to connect to repository.');
                }
            }

            const repoData = await response.json();

            // Save repository info
            this.githubRepo = {
                connected: true,
                url: repoUrl,
                name: repoData.name,
                fullName: repoData.full_name,
                branch: repoData.default_branch,
                token: githubToken,
                private: repoData.private
            };

            this.saveGithubRepo();
            this.updateGithubUI();
            this.hideGithubForm();
            
            this.showNotification(`Connected to ${repoData.full_name}`, 'success');

            // Add context message to chat
            const contextMessage = {
                type: 'system',
                content: `**GitHub Repository Connected:**
                
**Repository:** ${repoData.full_name}
**Branch:** ${repoData.default_branch}
**Visibility:** ${repoData.private ? 'Private' : 'Public'}

I can now help you analyze and modify code in this repository.`,
                timestamp: new Date()
            };
            this.addMessage(contextMessage);

        } catch (error) {
            this.showNotification(error.message, 'error');
        }
    }

    disconnectGithubRepo() {
        this.githubRepo = {
            connected: false,
            url: '',
            name: '',
            branch: '',
            token: ''
        };

        this.saveGithubRepo();
        this.updateGithubUI();
        this.showNotification('Repository disconnected', 'success');

        // Add context message to chat
        const contextMessage = {
            type: 'system',
            content: `**GitHub Repository Disconnected**

Repository connection has been removed. I'll now work in general mode without repository context.`,
            timestamp: new Date()
        };
        this.addMessage(contextMessage);
    }

    updateGithubUI() {
        const statusIndicator = document.getElementById('githubStatus').querySelector('.status-indicator');
        const statusText = document.getElementById('githubStatus').querySelector('.status-text');
        const connectBtn = document.getElementById('connectRepo');
        const repoInfo = document.getElementById('repoInfo');

        if (this.githubRepo.connected) {
            statusIndicator.textContent = '●';
            statusIndicator.className = 'status-indicator connected';
            statusText.textContent = `Connected to ${this.githubRepo.fullName || this.githubRepo.name}`;
            connectBtn.style.display = 'none';
            
            // Update repo info section
            document.getElementById('repoName').textContent = this.githubRepo.fullName || this.githubRepo.name;
            document.getElementById('repoBranch').textContent = this.githubRepo.branch;
            
            repoInfo.classList.remove('hidden');
        } else {
            statusIndicator.textContent = '○';
            statusIndicator.className = 'status-indicator disconnected';
            statusText.textContent = 'No repository connected';
            connectBtn.style.display = 'inline-block';
            
            repoInfo.classList.add('hidden');
        }
    }
    
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
        } else {
            console.log('No saved AI provider, using default:', this.aiProvider);
        }
        this.updateModelSelectorUI();
    }

    saveAIProvider() {
        localStorage.setItem('aiProvider', JSON.stringify(this.aiProvider));
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
}

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    new BusinessProcessDesigner();
});

// Add CSS animations for notifications
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
    
    .typing-indicator .message-content p {
        animation: pulse 1.5s infinite;
    }
`;
document.head.appendChild(style);