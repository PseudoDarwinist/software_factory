// Rich-Text PRD Editor - Nautex.ai Style
class PRDEditor {
    constructor(container) {
        this.container = container;
        this.document = {
            title: 'Product Requirements Document',
            sections: [],
            todos: []
        };
        this.todoCount = 0;
        this.currentEditingElement = null;
        this.outline = [];
        
        this.init();
    }

    init() {
        this.render();
        this.setupEventListeners();
    }

    // Method to load PRD data from JSON (like from the PO interface)
    loadFromJSON(jsonData) {
        if (!jsonData) return;
        
        try {
            // Handle different JSON structures
            let data = jsonData;
            if (typeof jsonData === 'string') {
                data = JSON.parse(jsonData);
            }
            
            // Extract title
            if (data.title) {
                this.document.title = data.title;
            }
            
            // Convert JSON structure to our section format
            this.document.sections = [];
            
            // Handle different JSON structures
            if (data.sections) {
                // Already in our format
                this.document.sections = data.sections;
            } else {
                // Convert from PRD JSON format
                const sectionMap = {
                    'problem': 'Problem Statement',
                    'audience': 'Target Audience',
                    'goals': 'Goals & Objectives',
                    'risks': 'Risks & Mitigation',
                    'competitive_scan': 'Competitive Analysis',
                    'open_questions': 'Open Questions'
                };
                
                Object.keys(sectionMap).forEach((key, index) => {
                    if (data[key]) {
                        const sectionData = data[key];
                        const content = [];
                        
                        if (sectionData.text) {
                            content.push({
                                type: 'paragraph',
                                content: this.cleanMarkdownText(sectionData.text)
                            });
                        }
                        
                        if (sectionData.items && Array.isArray(sectionData.items)) {
                            content.push({
                                type: 'list',
                                items: sectionData.items.map(item => this.cleanMarkdownText(item))
                            });
                        }
                        
                        this.document.sections.push({
                            id: key,
                            title: sectionMap[key],
                            level: 1,
                            collapsed: false,
                            content: content
                        });
                    }
                });
            }
            
            // Re-render with new data
            this.render();
            
        } catch (error) {
            console.error('Error loading PRD data:', error);
        }
    }

    render() {
        this.container.innerHTML = `
            <div class="prd-editor">
                <!-- Document Content -->
                <div class="prd-content" id="prdContent">
                    <h1 class="prd-main-title">Product Requirements Document</h1>
                    <div id="prdSections">
                        <!-- Document sections will be rendered here -->
                    </div>
                </div>
            </div>
        `;

        this.renderSections();
    }

    renderSections() {
        const contentContainer = document.getElementById('prdSections');
        
        // Default PRD structure if empty
        if (this.document.sections.length === 0) {
            this.document.sections = [
                {
                    id: 'introduction',
                    title: 'Introduction & Vision',
                    level: 1,
                    collapsed: false,
                    content: [
                        { type: 'paragraph', content: 'Define the product vision and high-level objectives.' },
                        { type: 'todo', content: 'Add specific vision statement and key objectives', completed: false }
                    ]
                },
                {
                    id: 'target-audience',
                    title: 'Target Audience & Personas',
                    level: 1,
                    collapsed: false,
                    content: [
                        { type: 'paragraph', content: 'Identify primary and secondary user personas.' },
                        { type: 'todo', content: 'Create detailed user personas with demographics and pain points', completed: false }
                    ]
                },
                {
                    id: 'user-stories',
                    title: 'User Stories',
                    level: 1,
                    collapsed: false,
                    content: [
                        { type: 'paragraph', content: 'Core user stories and acceptance criteria.' },
                        { type: 'todo', content: 'Define user stories with clear acceptance criteria', completed: false }
                    ]
                },
                {
                    id: 'functional-requirements',
                    title: 'Functional Requirements',
                    level: 1,
                    collapsed: false,
                    content: [
                        { type: 'paragraph', content: 'Detailed functional specifications.' },
                        { type: 'todo', content: 'Specify all functional requirements with priority levels', completed: false }
                    ]
                },
                {
                    id: 'success-metrics',
                    title: 'Success Metrics',
                    level: 1,
                    collapsed: false,
                    content: [
                        { type: 'paragraph', content: 'Key performance indicators and success criteria.' },
                        { type: 'todo', content: 'Define specific targets for success metrics', completed: false }
                    ]
                }
            ];
        }

        contentContainer.innerHTML = this.document.sections.map(section => this.renderSection(section)).join('');
        this.updateTodoCount();
    }

    renderSection(section) {
        const contentHtml = section.content.map(item => this.renderContentItem(item)).join('');
        
        return `
            <div class="prd-section" data-section-id="${section.id}">
                <div class="prd-section-header" onclick="PRDEditor.toggleSection('${section.id}')">
                    <div class="section-toggle ${section.collapsed ? 'collapsed' : 'expanded'}">
                        <span class="toggle-arrow">▼</span>
                    </div>
                    <h${section.level + 1} class="section-title" contenteditable="true" 
                        onblur="PRDEditor.updateSectionTitle('${section.id}', this.textContent)">${section.title}</h${section.level + 1}>
                    <div class="section-actions">
                        <button class="section-action-btn" onclick="PRDEditor.addContent('${section.id}')" title="Add Content">
                            <span>+</span>
                        </button>
                        <button class="section-action-btn" onclick="PRDEditor.deleteSection('${section.id}')" title="Delete Section">
                            <span>🗑️</span>
                        </button>
                    </div>
                </div>
                <div class="prd-section-content ${section.collapsed ? 'collapsed' : 'expanded'}">
                    ${contentHtml}
                </div>
            </div>
        `;
    }

    renderContentItem(item) {
        // Handle different content types and parse markdown/JSON properly
        let content = item.content || item;
        
        // If content is a string that looks like JSON, try to parse it
        if (typeof content === 'string' && (content.startsWith('{') || content.startsWith('['))) {
            try {
                const parsed = JSON.parse(content);
                if (parsed.text) content = parsed.text;
                else if (Array.isArray(parsed)) content = parsed.join(', ');
                else content = JSON.stringify(parsed, null, 2);
            } catch (e) {
                // If parsing fails, clean up the raw text
                content = this.cleanMarkdownText(content);
            }
        } else if (typeof content === 'string') {
            content = this.cleanMarkdownText(content);
        }

        switch (item.type) {
            case 'paragraph':
                return `<div class="content-paragraph" contenteditable="true" 
                    onblur="PRDEditor.updateContent(this)">${content}</div>`;
            
            case 'todo':
                const todoClass = item.completed ? 'completed' : '';
                return `<div class="content-todo ${todoClass}" data-todo-id="${item.id || this.generateId()}">
                    <div class="todo-checkbox ${item.completed ? 'checked' : ''}" 
                        onclick="PRDEditor.toggleTodo(this)"></div>
                    <div class="todo-text" contenteditable="true" 
                        onblur="PRDEditor.updateTodoText(this)">${content}</div>
                    <div class="todo-actions">
                        <button class="todo-action-btn" onclick="PRDEditor.deleteTodo(this)" title="Delete TODO">×</button>
                    </div>
                </div>`;
            
            case 'list':
                let listItems;
                if (item.items) {
                    listItems = item.items.map(listItem => 
                        `<li contenteditable="true" onblur="PRDEditor.updateContent(this)">${this.cleanMarkdownText(listItem)}</li>`
                    ).join('');
                } else if (Array.isArray(content)) {
                    listItems = content.map(listItem => 
                        `<li contenteditable="true" onblur="PRDEditor.updateContent(this)">${this.cleanMarkdownText(listItem)}</li>`
                    ).join('');
                } else {
                    // Parse bullet points from text
                    const bullets = content.split(/[•\-\*]\s+/).filter(item => item.trim());
                    listItems = bullets.map(bullet => 
                        `<li contenteditable="true" onblur="PRDEditor.updateContent(this)">${this.cleanMarkdownText(bullet.trim())}</li>`
                    ).join('');
                }
                return `<ul class="content-list">${listItems}</ul>`;
            
            case 'heading':
                return `<h${item.level || 3} class="content-heading" contenteditable="true" 
                    onblur="PRDEditor.updateContent(this)">${content}</h${item.level || 3}>`;
            
            default:
                return `<div class="content-paragraph" contenteditable="true" 
                    onblur="PRDEditor.updateContent(this)">${content}</div>`;
        }
    }

    cleanMarkdownText(text) {
        if (!text || typeof text !== 'string') return text || '';
        
        return text
            // Remove JSON-like syntax
            .replace(/^\{|\}$/g, '')
            .replace(/^"(.*)"$/g, '$1')
            // Clean up markdown syntax
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/#{1,6}\s*/g, '')
            // Remove extra quotes and braces
            .replace(/[{}]/g, '')
            .replace(/^["']|["']$/g, '')
            // Clean up whitespace
            .replace(/\s+/g, ' ')
            .trim();
    }

    // updateOutline() method removed - no longer needed

    updateTodoCount() {
        this.todoCount = 0;
        this.document.sections.forEach(section => {
            section.content.forEach(item => {
                if (item.type === 'todo' && !item.completed) {
                    this.todoCount++;
                }
            });
        });
        // TODO count updated - no UI element to update since header was removed
    }

    generateId() {
        return 'item-' + Math.random().toString(36).substr(2, 9);
    }

    setupEventListeners() {
        // Handle keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch (e.key) {
                    case 's':
                        e.preventDefault();
                        this.saveDocument();
                        break;
                    case 'e':
                        e.preventDefault();
                        PRDEditor.exportDocument();
                        break;
                }
            }
        });

        // Handle content editing
        document.addEventListener('input', (e) => {
            if (e.target.contentEditable === 'true') {
                this.markDocumentDirty();
            }
        });
    }

    markDocumentDirty() {
        // Document has unsaved changes - could add visual indicator if needed
        console.log('Document has unsaved changes');
    }

    saveDocument() {
        // Save document to backend
        console.log('Saving document...', this.document);
    }

    // Static methods for global access
    static toggleSection(sectionId) {
        const section = document.querySelector(`[data-section-id="${sectionId}"]`);
        const content = section.querySelector('.prd-section-content');
        const toggle = section.querySelector('.section-toggle');
        const arrow = toggle.querySelector('.toggle-arrow');
        
        if (content.classList.contains('collapsed')) {
            content.classList.remove('collapsed');
            content.classList.add('expanded');
            toggle.classList.remove('collapsed');
            toggle.classList.add('expanded');
            arrow.style.transform = 'rotate(0deg)';
        } else {
            content.classList.remove('expanded');
            content.classList.add('collapsed');
            toggle.classList.remove('expanded');
            toggle.classList.add('collapsed');
            arrow.style.transform = 'rotate(-90deg)';
        }
    }

    static scrollToSection(sectionId) {
        const section = document.querySelector(`[data-section-id="${sectionId}"]`);
        if (section) {
            section.scrollIntoView({ behavior: 'smooth', block: 'start' });
            section.classList.add('highlight');
            setTimeout(() => section.classList.remove('highlight'), 2000);
        }
    }

    static scrollToNextTodo() {
        const todos = document.querySelectorAll('.content-todo:not(.completed)');
        if (todos.length > 0) {
            todos[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
            todos[0].classList.add('highlight');
            setTimeout(() => todos[0].classList.remove('highlight'), 2000);
        }
    }

    static toggleTodo(checkbox) {
        const todoItem = checkbox.closest('.content-todo');
        const isCompleted = checkbox.classList.contains('checked');
        
        if (isCompleted) {
            checkbox.classList.remove('checked');
            todoItem.classList.remove('completed');
        } else {
            checkbox.classList.add('checked');
            todoItem.classList.add('completed');
        }
        
        // Update todo count
        const editor = window.prdEditorInstance;
        if (editor) {
            editor.updateTodoCount();
        }
    }

    static updateSectionTitle(sectionId, newTitle) {
        const editor = window.prdEditorInstance;
        if (editor) {
            const section = editor.document.sections.find(s => s.id === sectionId);
            if (section) {
                section.title = newTitle;
                editor.markDocumentDirty();
            }
        }
    }

    static updateContent(element) {
        const editor = window.prdEditorInstance;
        if (editor) {
            editor.markDocumentDirty();
        }
    }

    static updateTodoText(element) {
        const editor = window.prdEditorInstance;
        if (editor) {
            editor.markDocumentDirty();
        }
    }

    static addContent(sectionId) {
        const section = document.querySelector(`[data-section-id="${sectionId}"] .prd-section-content`);
        const newParagraph = document.createElement('div');
        newParagraph.className = 'content-paragraph';
        newParagraph.contentEditable = true;
        newParagraph.textContent = 'New content...';
        newParagraph.onblur = () => PRDEditor.updateContent(newParagraph);
        
        section.appendChild(newParagraph);
        newParagraph.focus();
        
        // Select all text for easy editing
        const range = document.createRange();
        range.selectNodeContents(newParagraph);
        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
    }

    static deleteSection(sectionId) {
        if (confirm('Are you sure you want to delete this section?')) {
            const section = document.querySelector(`[data-section-id="${sectionId}"]`);
            section.remove();
            
            const editor = window.prdEditorInstance;
            if (editor) {
                editor.document.sections = editor.document.sections.filter(s => s.id !== sectionId);
                editor.updateTodoCount();
                editor.markDocumentDirty();
            }
        }
    }

    static deleteTodo(button) {
        const todoItem = button.closest('.content-todo');
        todoItem.remove();
        
        const editor = window.prdEditorInstance;
        if (editor) {
            editor.updateTodoCount();
            editor.markDocumentDirty();
        }
    }

    static exportDocument() {
        const editor = window.prdEditorInstance;
        if (editor) {
            const markdown = editor.exportToMarkdown();
            const blob = new Blob([markdown], { type: 'text/markdown' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${editor.document.title.replace(/\s+/g, '-').toLowerCase()}.md`;
            a.click();
            URL.revokeObjectURL(url);
        }
    }

    exportToMarkdown() {
        let markdown = `# ${this.document.title}\n\n`;
        
        this.document.sections.forEach(section => {
            markdown += `${'#'.repeat(section.level + 1)} ${section.title}\n\n`;
            
            section.content.forEach(item => {
                switch (item.type) {
                    case 'paragraph':
                        markdown += `${item.content}\n\n`;
                        break;
                    case 'todo':
                        const checkbox = item.completed ? '[x]' : '[ ]';
                        markdown += `- ${checkbox} ${item.content}\n`;
                        break;
                    case 'list':
                        item.items.forEach(listItem => {
                            markdown += `- ${listItem}\n`;
                        });
                        markdown += '\n';
                        break;
                    case 'heading':
                        markdown += `${'#'.repeat(item.level)} ${item.content}\n\n`;
                        break;
                }
            });
        });
        
        return markdown;
    }
}

// Make it globally available
window.PRDEditor = PRDEditor;